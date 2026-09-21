import pandas as pd

from mesm.budget.project import (
    flexible_cut_capacity,
    group_structure,
    normalization_exposure,
    summarize_budget_project,
)


def sample_project() -> pd.DataFrame:
    return pd.DataFrame([
        {"year": 2027, "municipality_name": "Тест", "budget_side": "REVENUE", "group": "Налоги", "item_name": "НДФЛ", "amount": 100.0, "is_transfer": 0, "is_recurring": 1},
        {"year": 2027, "municipality_name": "Тест", "budget_side": "REVENUE", "group": "Трансферты", "item_name": "Дотация", "amount": 20.0, "is_transfer": 1, "is_recurring": 1},
        {"year": 2027, "municipality_name": "Тест", "budget_side": "EXPENDITURE", "group": "Социальная сфера", "item_name": "Учреждения", "amount": 80.0, "is_recurring": 1, "flexibility": "FIXED"},
        {"year": 2027, "municipality_name": "Тест", "budget_side": "EXPENDITURE", "group": "Капвложения", "item_name": "Стройка", "amount": 50.0, "is_recurring": 0, "flexibility": "FLEXIBLE"},
        {"year": 2027, "municipality_name": "Тест", "budget_side": "EXPENDITURE", "group": "Долг", "item_name": "Проценты", "amount": 5.0, "is_recurring": 1, "is_debt_service": 1, "flexibility": "FIXED"},
        {"year": 2027, "municipality_name": "Тест", "budget_side": "FINANCING", "group": "Заимствования", "item_name": "Кредит", "amount": 10.0, "is_borrowing": 1},
        {"year": 2027, "municipality_name": "Тест", "budget_side": "EXCEPTION", "group": "Исключения", "item_name": "Подтвержденное исключение", "amount": 2.0},
    ])


def test_project_summary():
    result = summarize_budget_project(sample_project(), "Тест", 2027)
    assert result.revenue_base == 100.0
    assert result.transfers == 20.0
    assert result.expenditure == 135.0
    assert result.recurring_revenue == 120.0
    assert result.recurring_expenditure == 85.0
    assert result.financing_sources == 10.0
    assert result.planned_net_borrowing == 10.0
    assert result.debt_service == 5.0
    assert result.eligible_exceptions == 2.0


def test_group_structure_and_exposure():
    structure = group_structure(sample_project(), "Тест", 2027, "EXPENDITURE")
    assert abs(float(structure["share"].sum()) - 1.0) < 1e-12

    exposure = normalization_exposure(sample_project(), "Тест", 2027, 13.0)
    assert abs(float(exposure["gap_exposure"].sum()) - 13.0) < 1e-12


def test_flexible_cut_capacity_uses_only_explicit_flexibility():
    table, remaining = flexible_cut_capacity(sample_project(), "Тест", 2027, 30.0)
    cap = {row["group"]: row["mechanical_cut"] for _, row in table.iterrows()}
    assert cap["Капвложения"] == 30.0
    assert cap["Социальная сфера"] == 0.0
    assert remaining == 0.0
