"""Канонический проект бюджета и автоматическое агрегирование для Normalization."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from mesm.budget.normalization import BudgetInputs


BOOLEAN_COLUMNS = (
    "is_transfer",
    "is_recurring",
    "is_subvention",
    "is_debt_service",
    "is_borrowing",
)

FLEXIBILITY_FACTORS = {
    "FIXED": 0.0,
    "PARTIAL": 0.5,
    "FLEXIBLE": 1.0,
    "UNKNOWN": 0.0,
}


@dataclass(frozen=True)
class BudgetProjectSummary:
    municipality_name: str
    year: int
    rows: int
    revenue_base: float
    transfers: float
    expenditure: float
    recurring_revenue: float
    recurring_expenditure: float
    financing_sources: float
    eligible_exceptions: float
    planned_net_borrowing: float
    debt_service: float
    expenditure_ex_subventions: float

    def to_budget_inputs(
        self,
        *,
        current_debt: float = 0.0,
        deficit_limit_ratio: float = 0.10,
        debt_limit_ratio: float = 1.00,
        debt_service_limit_ratio: float = 0.15,
    ) -> BudgetInputs:
        return BudgetInputs(
            revenue_base=self.revenue_base,
            transfers=self.transfers,
            expenditure=self.expenditure,
            eligible_exceptions=self.eligible_exceptions,
            recurring_revenue=self.recurring_revenue,
            recurring_expenditure=self.recurring_expenditure,
            current_debt=current_debt,
            planned_net_borrowing=self.planned_net_borrowing,
            debt_service=self.debt_service,
            expenditure_ex_subventions=self.expenditure_ex_subventions,
            financing_sources=self.financing_sources,
            deficit_limit_ratio=deficit_limit_ratio,
            debt_limit_ratio=debt_limit_ratio,
            debt_service_limit_ratio=debt_service_limit_ratio,
        )


def _as_bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce").fillna(0).ne(0)
    normalized = series.astype("string").str.lower().str.strip()
    return normalized.isin({"1", "1.0", "true", "yes", "y", "да", "истина"})


def normalize_budget_project(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"year", "municipality_name", "budget_side", "group", "item_name", "amount"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError("не хватает колонок: " + ", ".join(missing))

    out = frame.copy()
    out["year"] = pd.to_numeric(out["year"], errors="raise").astype(int)
    out["municipality_name"] = out["municipality_name"].astype(str).str.strip()
    out["budget_side"] = out["budget_side"].astype(str).str.upper().str.strip()
    out["group"] = out["group"].astype(str).str.strip()
    out["item_name"] = out["item_name"].astype(str).str.strip()
    out["amount"] = pd.to_numeric(out["amount"], errors="raise").astype(float)

    allowed_sides = {"REVENUE", "EXPENDITURE", "FINANCING", "EXCEPTION"}
    unknown_sides = sorted(set(out["budget_side"]) - allowed_sides)
    if unknown_sides:
        raise ValueError("неизвестные budget_side: " + ", ".join(unknown_sides))
    if (out["amount"] < 0).any():
        raise ValueError("amount не может быть отрицательным")

    for column in BOOLEAN_COLUMNS:
        if column in out.columns:
            out[column] = _as_bool(out[column])
        else:
            out[column] = False

    if "flexibility" not in out.columns:
        out["flexibility"] = "UNKNOWN"
    out["flexibility"] = out["flexibility"].fillna("UNKNOWN").astype(str).str.upper().str.strip()
    bad_flex = sorted(set(out["flexibility"]) - set(FLEXIBILITY_FACTORS))
    if bad_flex:
        raise ValueError("неизвестные flexibility: " + ", ".join(bad_flex))

    return out.sort_values(["municipality_name", "year", "budget_side", "group", "item_name"]).reset_index(drop=True)


def select_budget_project(frame: pd.DataFrame, municipality_name: str, year: int) -> pd.DataFrame:
    out = normalize_budget_project(frame)
    selected = out[
        (out["municipality_name"] == str(municipality_name).strip())
        & (out["year"] == int(year))
    ].copy()
    if selected.empty:
        raise ValueError("проект бюджета для выбранного муниципалитета и года не найден")
    return selected


def summarize_budget_project(frame: pd.DataFrame, municipality_name: str, year: int) -> BudgetProjectSummary:
    selected = select_budget_project(frame, municipality_name, year)

    revenue = selected[selected["budget_side"] == "REVENUE"]
    expenditure = selected[selected["budget_side"] == "EXPENDITURE"]
    financing = selected[selected["budget_side"] == "FINANCING"]
    exceptions = selected[selected["budget_side"] == "EXCEPTION"]

    transfer_mask = revenue["is_transfer"]
    recurring_revenue_mask = revenue["is_recurring"]
    recurring_expense_mask = expenditure["is_recurring"]
    subvention_mask = expenditure["is_subvention"]
    borrowing_mask = financing["is_borrowing"]
    debt_service_mask = expenditure["is_debt_service"]

    return BudgetProjectSummary(
        municipality_name=str(municipality_name).strip(),
        year=int(year),
        rows=len(selected),
        revenue_base=float(revenue.loc[~transfer_mask, "amount"].sum()),
        transfers=float(revenue.loc[transfer_mask, "amount"].sum()),
        expenditure=float(expenditure["amount"].sum()),
        recurring_revenue=float(revenue.loc[recurring_revenue_mask, "amount"].sum()),
        recurring_expenditure=float(expenditure.loc[recurring_expense_mask, "amount"].sum()),
        financing_sources=float(financing["amount"].sum()),
        eligible_exceptions=float(exceptions["amount"].sum()),
        planned_net_borrowing=float(financing.loc[borrowing_mask, "amount"].sum()),
        debt_service=float(expenditure.loc[debt_service_mask, "amount"].sum()),
        expenditure_ex_subventions=float(expenditure.loc[~subvention_mask, "amount"].sum()),
    )


def group_structure(
    frame: pd.DataFrame,
    municipality_name: str,
    year: int,
    side: str,
) -> pd.DataFrame:
    selected = select_budget_project(frame, municipality_name, year)
    side = str(side).upper().strip()
    selected = selected[selected["budget_side"] == side]
    if selected.empty:
        return pd.DataFrame(columns=["group", "amount", "share"])

    grouped = (
        selected.groupby("group", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
        .reset_index(drop=True)
    )
    total = float(grouped["amount"].sum())
    grouped["share"] = grouped["amount"] / total if total else 0.0
    return grouped


def normalization_exposure(
    frame: pd.DataFrame,
    municipality_name: str,
    year: int,
    normalization_gap: float,
) -> pd.DataFrame:
    """Механически распределяет gap по доле групп расходов; это не causal attribution."""
    structure = group_structure(frame, municipality_name, year, "EXPENDITURE")
    if structure.empty:
        return pd.DataFrame(columns=["group", "amount", "share", "gap_exposure"])
    out = structure.copy()
    out["gap_exposure"] = out["share"] * max(float(normalization_gap), 0.0)
    return out


def flexible_cut_capacity(
    frame: pd.DataFrame,
    municipality_name: str,
    year: int,
    normalization_gap: float,
) -> tuple[pd.DataFrame, float]:
    """Распределяет gap только по явно размеченной гибкости расходов."""
    selected = select_budget_project(frame, municipality_name, year)
    expenses = selected[selected["budget_side"] == "EXPENDITURE"].copy()
    if expenses.empty:
        return pd.DataFrame(columns=["group", "amount", "capacity", "mechanical_cut"]), max(float(normalization_gap), 0.0)

    expenses["factor"] = expenses["flexibility"].map(FLEXIBILITY_FACTORS).fillna(0.0)
    expenses["capacity"] = expenses["amount"] * expenses["factor"]

    grouped = expenses.groupby("group", as_index=False).agg(
        amount=("amount", "sum"),
        capacity=("capacity", "sum"),
    )
    total_capacity = float(grouped["capacity"].sum())
    gap = max(float(normalization_gap), 0.0)
    if total_capacity <= 0:
        grouped["mechanical_cut"] = 0.0
        return grouped.sort_values("amount", ascending=False).reset_index(drop=True), gap

    used = min(gap, total_capacity)
    grouped["mechanical_cut"] = grouped["capacity"] / total_capacity * used
    remaining = max(gap - total_capacity, 0.0)
    return grouped.sort_values("mechanical_cut", ascending=False).reset_index(drop=True), remaining
