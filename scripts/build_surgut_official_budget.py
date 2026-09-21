#!/usr/bin/env python3
"""Rebuild Surgut 2025-2027 budget datasets from downloaded official workbooks."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mesm.ingest.surgut_budget import build_adopted_outputs

SOURCE_ID = "surgut_budget_adopted_2025_2027"
CONFIG = ROOT / "config" / "official_sources.json"
RAW = ROOT / "data" / "raw" / "official" / SOURCE_ID
PLAN = ROOT / "data" / "processed" / "official_budget_plan_surgut_2025_2027.csv"
STRUCTURE = ROOT / "data" / "processed" / "official_budget_project_surgut_2025.csv"


def main() -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))["sources"][SOURCE_ID]
    if not RAW.exists():
        raise SystemExit(
            "Raw official files are missing. Run first:\n"
            "  python scripts/fetch_official_sources.py surgut_budget_adopted_2025_2027"
        )
    plan_rows, structure_rows = build_adopted_outputs(
        RAW,
        PLAN,
        STRUCTURE,
        source_page_url=payload["page_url"],
        publication_date=payload["publication_date"],
        source_document=payload["decision"],
    )
    print(f"Plan rows: {len(plan_rows)} -> {PLAN}")
    print(f"Structure rows: {len(structure_rows)} -> {STRUCTURE}")


if __name__ == "__main__":
    main()
