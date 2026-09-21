#!/usr/bin/env python3
"""Собираем Fiscal Reference Panel из активных или встроенных входных данных."""
from __future__ import annotations

import csv
from pathlib import Path

from mesm.data.intake import resolve_dataset_path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "processed" / "fiscal_reference_panel.csv"


def number(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = str(value).strip().replace(" ", "").replace(",", ".")
    if not cleaned or cleaned.startswith("#"):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def load_inputs(path: Path | None = None) -> dict[tuple[int, str], dict[str, float | None]]:
    path = path or resolve_dataset_path("reference_core", ROOT)
    grouped: dict[tuple[int, str], dict[str, float | None]] = {}
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            municipality = row["municipality_name"].strip()
            if not municipality or municipality.isdigit():
                continue
            grouped[(int(row["year"]), municipality)] = {
                key: number(row.get(key))
                for key in (
                    "tax_initial",
                    "nontax_initial",
                    "tax_actual",
                    "nontax_actual",
                    "program_expense",
                    "total_expense",
                    "budget_amendments",
                    "municipal_debt",
                    "own_revenue_base",
                )
            }
    return grouped


def load_rankings(path: Path | None = None) -> dict[tuple[int, str], dict]:
    path = path or resolve_dataset_path("quality_rankings", ROOT)
    if not path.exists():
        return {}

    rankings: dict[tuple[int, str], dict] = {}
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            municipality = row["municipality_name"].strip()
            if not municipality or municipality.isdigit():
                continue
            rankings[(int(row["year"]), municipality)] = row
    return rankings


def build(
    inputs_path: Path | None = None,
    rankings_path: Path | None = None,
) -> list[dict]:
    inputs = load_inputs(inputs_path)
    rankings = load_rankings(rankings_path)
    output: list[dict] = []

    for (year, municipality), values in sorted(inputs.items()):
        tax_initial = values.get("tax_initial")
        nontax_initial = values.get("nontax_initial")
        tax_actual = values.get("tax_actual")
        nontax_actual = values.get("nontax_actual")

        income_plan_deviation = None
        if None not in (tax_initial, nontax_initial, tax_actual, nontax_actual):
            planned = tax_initial + nontax_initial
            actual = tax_actual + nontax_actual
            if planned:
                income_plan_deviation = (actual - planned) / planned

        program_expense = values.get("program_expense")
        total_expense = values.get("total_expense")
        program_expense_share = (
            program_expense / total_expense
            if program_expense is not None and total_expense
            else None
        )

        debt = values.get("municipal_debt")
        income = values.get("own_revenue_base")
        debt_load = debt / income if debt is not None and income else None

        ranking = rankings.get((year, municipality), {})
        output.append(
            {
                "year": year,
                "municipality_name": municipality,
                "municipality_oktmo": "",
                "period_end": f"{year}-12-31",
                "frequency": "YEAR",
                "income_plan_deviation": income_plan_deviation,
                "program_expense_share": program_expense_share,
                "budget_amendments": values.get("budget_amendments"),
                "debt_load": debt_load,
                "quality_rank": number(ranking.get("rank")),
                "article136_high_subsidy_flag": number(ranking.get("article136_high_subsidy_flag")),
                "source_file": ranking.get("source_file", ""),
                "publication_date": "",
                "data_status": "derived_from_active_or_official_public",
            }
        )
    return output


def write_panel(rows: list[dict], output: Path = OUTPUT) -> None:
    fieldnames = [
        "year",
        "municipality_name",
        "municipality_oktmo",
        "period_end",
        "frequency",
        "income_plan_deviation",
        "program_expense_share",
        "budget_amendments",
        "debt_load",
        "quality_rank",
        "article136_high_subsidy_flag",
        "source_file",
        "publication_date",
        "data_status",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = build()
    write_panel(rows)
    print(f"Записано строк: {len(rows)} -> {OUTPUT}")


if __name__ == "__main__":
    main()
