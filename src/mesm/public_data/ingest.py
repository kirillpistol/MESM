from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import pandas as pd
from .cache import AsyncSnapshotCache
from .schemas import validate_raw, validate_canonical, features_as_of


def normalize_csv(path: str | Path, config: dict) -> pd.DataFrame:
    if config["source"] not in {"fns_5_ndfl", "fns_7_ndfl", "fns_kkt", "rosstat_pmo", "other_public"}:
        raise ValueError("Unknown source identifier")
    frame = pd.read_csv(path, sep=config.get("separator", ","), encoding=config.get("encoding", "utf-8"), dtype=str)
    mapping = config["columns"]
    required = {"oktmo", "period", "indicator", "value", "unit"}
    if set(mapping) != required:
        raise ValueError(f"Mapping must define exactly {sorted(required)}")
    missing = set(mapping.values()) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing source columns: {sorted(missing)}")
    raw = frame.rename(columns={original: canonical for canonical, original in mapping.items()})[list(mapping)]
    raw["value"] = pd.to_numeric(raw["value"].str.replace(" ", "", regex=False).str.replace(",", ".", regex=False), errors="raise")
    raw = validate_raw(raw)
    canonical = raw.copy()
    canonical["period"] = pd.to_datetime(canonical["period"], format=config["period_format"], errors="raise")
    canonical["available_at"] = pd.Timestamp(config["available_at"])
    canonical["source"] = config["source"]
    canonical["category"] = config["category"]
    canonical["is_estimated"] = False
    if config["source"] in {"fns_5_ndfl", "fns_7_ndfl"} and config["category"] != "all":
        raise ValueError("Personal income is an all-category structural feature")
    return validate_canonical(canonical)


async def run(config_path: Path, output: Path, cache_root: Path, as_of: str | None) -> None:
    from .pipeline import update_public_data
    settings = json.loads(config_path.read_text(encoding="utf-8"))
    report = await update_public_data(settings, output, cache_root, as_of)
    print(json.dumps({"status": report.status, "rows": report.rows,
                      "sources": [item.__dict__ for item in report.sources]}, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and validate public aggregate CSVs")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/processed/public_aggregates.csv"))
    parser.add_argument("--cache", type=Path, default=Path("data/cache/http"))
    parser.add_argument("--as-of", help="Prediction date YYYY-MM-DD")
    args = parser.parse_args()
    asyncio.run(run(args.config, args.output, args.cache, args.as_of))


if __name__ == "__main__":
    main()
