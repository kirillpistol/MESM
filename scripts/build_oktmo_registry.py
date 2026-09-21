from __future__ import annotations

import argparse
from pathlib import Path

from mesm.ingest.rosstat_oktmo import build_municipality_registry, read_rosstat_oktmo_csv

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "reference" / "municipality_registry.csv"
SOURCE_PAGE = "https://rosstat.gov.ru/opendata/7708234640-oktmo"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build MESM municipality registry from official Rosstat OKTMO CSV.")
    parser.add_argument("input", type=Path, help="Official Rosstat OKTMO CSV.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--source-version", required=True, help="Official dataset version/date, e.g. 2026-09-01.")
    args = parser.parse_args()

    frame = read_rosstat_oktmo_csv(args.input)
    registry = build_municipality_registry(
        frame,
        source_url=SOURCE_PAGE,
        source_version=args.source_version,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    registry.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"OKTMO registry: {len(registry)} active municipal keys -> {args.output}")


if __name__ == "__main__":
    main()
