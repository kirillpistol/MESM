from datetime import date
import pytest

from mesm.budget.cash_execution import (CashLine, ManualCorrection, cash_vs_monthly_plan,
                                        monthly_from_ytd, normalize_cash)
from mesm.budget.normalization import BudgetInputs, calculate_budget

JAN = date(2026, 1, 1)
FEB = date(2026, 2, 1)
MAR = date(2026, 3, 1)
APR = date(2026, 4, 1)
AS_OF = date(2026, 5, 20)


def line(month, kbk, side, amount, source="REPORT_0503117", available=AS_OF, basis="MONTH"):
    return CashLine("Surgut", month, kbk, side, amount, source, available, "Отчёт 0503117", basis)


def correction(identifier, kind, month, kbk, side, amount, target=None):
    return ManualCorrection(identifier, kind, "Surgut", kbk, side, month, amount,
                            "Экспертное основание", "Документ 42", "Финорган", AS_OF, target)


def test_ytd_to_monthly_and_asof_revision():
    ytd = [line(JAN, "NDFL", "REVENUE", 100, basis="YTD"),
           line(FEB, "NDFL", "REVENUE", 90, basis="YTD")]
    monthly = monthly_from_ytd(ytd)
    assert [row.amount for row in monthly] == [100, -10]
    revised = line(FEB, "NDFL", "REVENUE", -12, available=date(2026, 5, 19))
    out = normalize_cash([monthly[0], monthly[1], revised], [], as_of=AS_OF,
                         municipality="Surgut", source="REPORT_0503117")
    assert out[1].raw_revenue == -10
    with pytest.raises(ValueError):
        monthly_from_ytd([line(FEB, "NDFL", "REVENUE", 90, basis="YTD")])


def test_adjustments_conserve_cash_and_keep_legal_formula_separate():
    lines = [line(JAN, "NDFL", "REVENUE", 100), line(JAN, "EXP", "EXPENDITURE", 70),
             line(FEB, "NDFL", "REVENUE", -20), line(FEB, "EXP", "EXPENDITURE", 80),
             line(MAR, "NDFL", "REVENUE", 100), line(MAR, "ASSET", "REVENUE", 60),
             line(MAR, "BAL", "FINANCING", 30), line(MAR, "EXP", "EXPENDITURE", 100),
             line(APR, "NDFL", "REVENUE", 20), line(APR, "EXP", "EXPENDITURE", 50)]
    fixes = [correction("refund", "REFUND_REALLOCATION", FEB, "NDFL", "REVENUE", 20, JAN),
             correction("asset", "ONE_OFF", MAR, "ASSET", "REVENUE", 60),
             correction("advance", "ADVANCE_REALLOCATION", MAR, "NDFL", "REVENUE", 40, APR),
             correction("balance", "CARRYOVER", MAR, "BAL", "FINANCING", 30)]
    official = calculate_budget(BudgetInputs(revenue_base=1000, transfers=100,
                                             expenditure=1200, recurring_revenue=900,
                                             recurring_expenditure=1100))
    out = normalize_cash(lines, fixes, as_of=AS_OF, municipality="Surgut",
                         source="REPORT_0503117", opening_balance=10,
                         deflators={MAR: 1.25},
                         season_factors={(m, kbk): 1.0 for m in (JAN, FEB, MAR, APR)
                                         for kbk in ("NDFL", "EXP", "ASSET")})
    assert [row.normalized_revenue for row in out] == [80, 0, 60, 60]
    assert out[2].raw_revenue == 160
    assert out[2].real_recurring_balance == (60 - 100) / 1.25
    assert out[2].seasonal_balance == -40
    assert out[2].cash_balance == 0
    assert sum(row.raw_revenue for row in out) == 260
    assert sum(row.normalized_revenue for row in out) == 200
    assert official.normalization_gap == 0
    signal = cash_vs_monthly_plan(out[2], planned_revenue=120, planned_expenditure=90)
    assert signal.raw_revenue_execution_rate == 160 / 120
    assert signal.normalized_revenue_gap == -0.5
    assert signal.basis == "ANALYTICAL_MONTHLY"


def test_reject_unapproved_future_and_double_allocation():
    rows = [line(JAN, "NDFL", "REVENUE", 100), line(FEB, "NDFL", "REVENUE", -20)]
    first = correction("a", "REFUND_REALLOCATION", FEB, "NDFL", "REVENUE", 15, JAN)
    second = correction("b", "REFUND_REALLOCATION", FEB, "NDFL", "REVENUE", 15, JAN)
    with pytest.raises(ValueError):
        normalize_cash(rows, [first, second], as_of=AS_OF, municipality="Surgut", source="REPORT_0503117")
    pending = ManualCorrection("late", "REFUND_REALLOCATION", "Surgut", "NDFL", "REVENUE", FEB,
                               20, "Основание", "Документ", "Финорган", date(2026, 6, 1), JAN)
    result = normalize_cash(rows, [pending], as_of=AS_OF, municipality="Surgut", source="REPORT_0503117")
    assert result[1].normalized_revenue == -20
    with pytest.raises(ValueError):
        normalize_cash(rows, [correction("bad", "CARRYOVER", JAN, "NDFL", "REVENUE", 20)],
                       as_of=AS_OF, municipality="Surgut", source="REPORT_0503117")
    with pytest.raises(ValueError):
        normalize_cash(rows + [line(MAR, "NDFL", "REVENUE", 100), line(APR, "NDFL", "REVENUE", 0)],
                       [correction("one", "ONE_OFF", MAR, "NDFL", "REVENUE", 70),
                        correction("two", "ADVANCE_REALLOCATION", MAR, "NDFL", "REVENUE", 40, APR)],
                       as_of=AS_OF, municipality="Surgut", source="REPORT_0503117")
