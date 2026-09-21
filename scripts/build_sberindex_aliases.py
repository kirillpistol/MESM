from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from mesm.geo.oktmo import normalize_name, read_municipality_registry
from mesm.ingest.sberindex_spending import read_sberindex_export

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "data" / "reference" / "municipality_registry.csv"
DEFAULT_OUTPUT = ROOT / "data" / "reference" / "sberindex_municipality_aliases.auto.csv"
DEFAULT_REVIEW = ROOT / "data" / "reports" / "sberindex_oktmo_review.csv"
SOURCE_ID = "sberindex_cashless_spending_municipal"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create conservative exact-name SberIndex -> OKTMO aliases.")
    parser.add_argument("sberindex_input", type=Path)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    args = parser.parse_args()

    raw = read_sberindex_export(args.sberindex_input)
    registry = read_municipality_registry(args.registry)

    names = pd.DataFrame({"source_municipality_name": sorted(raw["mo"].astype(str).str.strip().unique())})
    names["_name_key"] = names["source_municipality_name"].map(normalize_name)

    candidates = registry[["oktmo", "municipality_name", "_name_key"]].copy()
    counts = candidates.groupby("_name_key")["oktmo"].nunique()
    unique_keys = set(counts[counts == 1].index)
    exact = candidates[candidates["_name_key"].isin(unique_keys)].drop_duplicates("_name_key")

    merged = names.merge(exact, on="_name_key", how="left")
    approved = merged[merged["oktmo"].notna()].copy()
    approved["source_id"] = SOURCE_ID
    approved["match_method"] = "EXACT_UNIQUE_NAME"
    approved["status"] = "APPROVED"
    approved["source_url"] = "https://sberindex.ru/ru/dashboards/potrebitelskie-beznalicnye-rashody-na-urovne-munizipalnyh-obrazovanij"
    approved["notes"] = "Auto-approved only because normalized official name is unique in OKTMO registry."
    approved = approved[[
        "source_id", "source_municipality_name", "oktmo",
        "match_method", "status", "source_url", "notes"
    ]]

    review = merged[merged["oktmo"].isna()][["source_municipality_name"]].copy()
    review["status"] = "REVIEW_REQUIRED"
    review["reason"] = "No unique exact name match; fuzzy matching must not auto-approve OKTMO."

    args.output.parent.mkdir(parents=True, exist_ok=True)
    approved.to_csv(args.output, index=False, encoding="utf-8-sig")
    args.review.parent.mkdir(parents=True, exist_ok=True)
    review.to_csv(args.review, index=False, encoding="utf-8-sig")
    print(f"Auto-approved aliases: {len(approved)}")
    print(f"Manual review required: {len(review)}")


if __name__ == "__main__":
    main()
