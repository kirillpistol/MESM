from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from mesm.geo.oktmo import read_alias_registry, read_municipality_registry
from mesm.ingest.sberindex_spending import (
    canonicalize_sberindex_spending,
    file_sha256,
    profile_dict,
    read_sberindex_export,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "sberindex_spending_monthly.csv"
DEFAULT_QUARANTINE = ROOT / "data" / "quarantine" / "sberindex_spending_ambiguous.csv"
DEFAULT_PROFILE = ROOT / "data" / "reports" / "sberindex_spending_profile.json"
DEFAULT_MANIFEST = ROOT / "data" / "manifest" / "competition_dataset_manifest.csv"
DEFAULT_REGISTRY = ROOT / "data" / "reference" / "municipality_registry.csv"
DEFAULT_ALIASES = ROOT / "data" / "reference" / "sberindex_municipality_aliases.csv"
SOURCE_URL = "https://sberindex.ru/ru/dashboards/potrebitelskie-beznalicnye-rashody-na-urovne-munizipalnyh-obrazovanij"


def append_manifest(path: Path, input_path: Path, digest: str, rows: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    fields = [
        "source_id", "source_url", "local_path", "sha256",
        "downloaded_or_received_at_utc", "rows", "data_status",
    ]
    record = {
        "source_id": "sberindex_cashless_spending_municipal",
        "source_url": SOURCE_URL,
        "local_path": str(input_path),
        "sha256": digest,
        "downloaded_or_received_at_utc": datetime.now(timezone.utc).isoformat(),
        "rows": rows,
        "data_status": "OFFICIAL_PUBLIC_EXPORT",
    }
    with path.open("a", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow(record)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build canonical SberIndex municipal spending panel.")
    parser.add_argument("input", type=Path, help="Path to SberIndex .csv or .csv.zip export.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--quarantine", type=Path, default=DEFAULT_QUARANTINE)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--aliases", type=Path, default=DEFAULT_ALIASES)
    args = parser.parse_args()

    frame = read_sberindex_export(args.input)
    registry = read_municipality_registry(args.registry)
    aliases = read_alias_registry(args.aliases)
    canonical, quarantine, profile = canonicalize_sberindex_spending(
        frame,
        registry=registry,
        aliases=aliases,
    )
    digest = file_sha256(args.input)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    canonical.to_csv(args.output, index=False, encoding="utf-8-sig")

    args.quarantine.parent.mkdir(parents=True, exist_ok=True)
    quarantine.to_csv(args.quarantine, index=False, encoding="utf-8-sig")

    args.profile.parent.mkdir(parents=True, exist_ok=True)
    report = profile_dict(profile) | {
        "source_id": "sberindex_cashless_spending_municipal",
        "source_url": SOURCE_URL,
        "input_sha256": digest,
    }
    args.profile.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    append_manifest(args.manifest, args.input, digest, profile.input_rows)

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
