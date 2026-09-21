from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]


def _rows() -> list[dict]:
    path = ROOT / "data" / "processed" / "fiscal_reference_panel.csv"
    return list(csv.DictReader(path.open(encoding="utf-8-sig")))


def test_panel_has_22_municipalities_for_three_years():
    rows = _rows()
    assert len(rows) == 66
    assert len({r["municipality_name"] for r in rows}) == 22
    assert {r["year"] for r in rows} == {"2023", "2024", "2025"}


def test_surgut_indicators_reproduce_public_inputs():
    r = next(x for x in _rows() if x["municipality_name"] == "Сургут" and x["year"] == "2025")
    assert round(float(r["income_plan_deviation"]), 6) == 0.110555
    assert round(float(r["program_expense_share"]), 6) == 0.929568
    assert float(r["budget_amendments"]) == 4.0


def test_budget_provision_history_keeps_natural_frequency():
    path = ROOT / "data" / "processed" / "budget_provision_history_2021_2023.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    assert len(rows) == 44
    assert {r["year"] for r in rows} == {"2021", "2023"}
    assert {r["period"] for r in rows} == {"Q3"}

    surgut = next(r for r in rows if r["municipality_name"] == "Сургут" and r["year"] == "2023")
    assert round(float(surgut["bo_actual"]), 6) == 1.182836
    assert round(float(surgut["bo_calculated"]), 6) == 1.103715
