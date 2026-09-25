from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from typing import Callable

import pandas as pd

from .cache import AsyncSnapshotCache, Snapshot
from .ingest import normalize_csv
from .schemas import features_as_of, validate_canonical


@dataclass(frozen=True)
class SourceResult:
    source: str
    period: str
    schema_version: str
    status: str
    rows: int
    digest: str | None
    contract_digest: str | None
    error: str | None


@dataclass(frozen=True)
class PipelineResult:
    status: str
    generated_at: str
    rows: int
    sources: list[SourceResult]


def _write_temp(path: Path, content: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        return Path(tmp.name)


def _publish(files: dict[Path, bytes]) -> None:
    staged: dict[Path, Path] = {}
    previous: dict[Path, bytes | None] = {}
    published: list[Path] = []
    try:
        for path, content in files.items():
            staged[path] = _write_temp(path, content)
            previous[path] = path.read_bytes() if path.exists() else None
        for path, temp in staged.items():
            os.replace(temp, path)
            published.append(path)
    except OSError:
        for path in reversed(published):
            old = previous[path]
            if old is None:
                path.unlink(missing_ok=True)
            else:
                os.replace(_write_temp(path, old), path)
        raise
    finally:
        for temp in staged.values():
            temp.unlink(missing_ok=True)


async def update_public_data(settings: dict, output: Path, cache_root: Path,
                             as_of: str | None = None,
                             fetcher: Callable | None = None) -> PipelineResult:
    sources = [entry for entry in settings.get("sources", []) if entry.get("enabled")]
    if not sources:
        raise ValueError("No enabled sources")
    cache = AsyncSnapshotCache(cache_root)
    fetch = fetcher or cache.fetch
    contract_path = output.with_suffix(".contracts.json")
    try:
        contracts = json.loads(contract_path.read_text(encoding="utf-8")) if contract_path.exists() else {}
    except (OSError, ValueError):
        contracts = None

    async def process(config: dict) -> tuple[SourceResult, pd.DataFrame | None]:
        source = str(config.get("source", "UNKNOWN"))
        period = str(config.get("period", "UNKNOWN"))
        version = str(config.get("schema_version", "1"))
        try:
            if contracts is None:
                raise ValueError("Contract registry is unreadable")
            if not version.strip():
                raise ValueError("Missing schema_version")
            fields = {key: config.get(key) for key in ("columns", "category", "period_format", "separator", "encoding")}
            contract_digest = sha256(json.dumps(fields, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            contract_key = f"{source}:{version}"
            if contract_key in contracts and contracts[contract_key] != contract_digest:
                raise ValueError("Source mapping changed without schema_version update")
            snapshot: Snapshot = await fetch(source, config["url"], period=period,
                                             available_at=config["available_at"], schema_version=version)
            frame = normalize_csv(cache_root / snapshot.path, config)
            if frame.empty:
                raise ValueError("Empty source table")
            return SourceResult(source, period, version, "accepted", len(frame), snapshot.sha256, contract_digest, None), frame
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            return SourceResult(source, period, version, "quarantined", 0, None, None, message[:500]), None

    results = await asyncio.gather(*(process(config) for config in sources))
    accepted = [frame for _, frame in results if frame is not None]
    source_results = [result for result, _ in results]
    now = datetime.now(timezone.utc).isoformat()
    status = "stale" if not accepted else "partial" if len(accepted) != len(sources) else "fresh"
    files: dict[Path, bytes] = {}
    rows = 0
    if accepted and (status == "fresh" or settings.get("allow_partial_publish") is True):
        try:
            canonical = validate_canonical(pd.concat(accepted, ignore_index=True))
            rows = len(canonical)
            files[output] = canonical.to_csv(index=False).encode("utf-8")
            if as_of:
                features = features_as_of(canonical, as_of)
                files[output.with_name("grow_features_asof.csv")] = features.to_csv(index=False).encode("utf-8")
            next_contracts = dict(contracts)
            next_contracts.update({f"{item.source}:{item.schema_version}": item.contract_digest
                                   for item in source_results if item.status == "accepted"})
            files[contract_path] = json.dumps(next_contracts, ensure_ascii=False, indent=2).encode("utf-8")
        except Exception as exc:
            status = "stale"
            source_results.append(SourceResult("merged", "", "", "quarantined", 0, None, None,
                                               f"{type(exc).__name__}: {exc}"[:500]))
            files.clear()
            rows = 0
    report = PipelineResult(status, now, rows, source_results)
    files[output.with_suffix(".status.json")] = json.dumps(asdict(report), ensure_ascii=False, indent=2).encode("utf-8")
    _publish(files)
    return report
