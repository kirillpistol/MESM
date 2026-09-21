#!/usr/bin/env python3
"""Fetch official public documents into immutable data/raw and update manifest."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mesm.ingest.official_web import fetch_source_bundle, load_source_config

CONFIG = ROOT / "config" / "official_sources.json"
RAW_ROOT = ROOT / "data" / "raw" / "official"
MANIFEST = ROOT / "data" / "manifest" / "source_manifest.csv"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "source_id",
        nargs="?",
        default="surgut_budget_adopted_2025_2027",
        help="source id from config/official_sources.json",
    )
    args = parser.parse_args()
    config = load_source_config(CONFIG, args.source_id)
    rows = fetch_source_bundle(args.source_id, config, RAW_ROOT, MANIFEST)
    print(f"Downloaded {len(rows)} official files -> {RAW_ROOT / args.source_id}")
    print(f"Manifest -> {MANIFEST}")


if __name__ == "__main__":
    main()
