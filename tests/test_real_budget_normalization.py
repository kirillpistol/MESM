from pathlib import Path

import pandas as pd

from mesm.budget.normalization import BudgetInputs, calculate_budget

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "official_budget_plan_surgut_2025_2027.csv"


def _result(year: int):
    frame = pd.read_csv(DATA, encoding="utf-8-sig")
    row = frame[frame["year"] == year].iloc[0]
    inputs = BudgetInputs(
        revenue_base=float(row["revenue_base"]),
        transfers=float(row["transfers"]),
        expenditure=float(row["expenditure"]),
        eligible_exceptions=float(row["eligible_exceptions"]),
        financing_sources=float(row["financing_sources"]),
        current_debt=float(row["debt_upper_limit"]),
        debt_service=float(row["debt_service"]),
        expenditure_ex_subventions=float(row["expenditure"]),
    )
    return row, calculate_budget(inputs)


def test_real_2025_budget_is_normalized_after_verified_exception():
    row, result = _result(2025)
    assert abs(result.deficit - float(row["deficit"])) < 0.01
    assert result.raw_normalization_gap > 0
    assert result.normalization_gap == 0.0
    assert result.financing_gap == 0.0


def test_real_2026_budget_is_normalized_after_verified_exception():
    _, result = _result(2026)
    assert result.raw_normalization_gap > 0
    assert result.normalization_gap == 0.0


def test_real_2027_budget_fits_base_limit_without_exception():
    row, result = _result(2027)
    assert float(row["eligible_exceptions"]) == 0.0
    assert result.raw_normalization_gap == 0.0
    assert result.normalization_gap == 0.0
