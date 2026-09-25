"""Расчет дефицита, нормализационного разрыва и сценариев бюджета."""
from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class BudgetInputs:
    revenue_base: float
    transfers: float
    expenditure: float
    deficit_base: float | None = None
    eligible_exceptions: float = 0.0
    recurring_revenue: float = 0.0
    recurring_expenditure: float = 0.0
    current_debt: float = 0.0
    planned_net_borrowing: float = 0.0
    debt_service: float = 0.0
    expenditure_ex_subventions: float = 0.0
    financing_sources: float = 0.0
    deficit_limit_ratio: float = 0.10
    debt_limit_ratio: float = 1.00
    debt_service_limit_ratio: float = 0.15


@dataclass(frozen=True)
class BudgetResult:
    total_revenue: float
    balance: float
    deficit: float
    deficit_ratio: float
    base_deficit_limit: float
    allowed_deficit: float
    raw_normalization_gap: float
    normalization_gap: float
    recurring_balance: float
    structural_gap: float
    financing_gap: float
    debt_after: float
    debt_ratio: float
    debt_headroom: float
    debt_service_ratio: float
    deficit_within_configured_limit: bool
    debt_within_configured_limit: bool
    debt_service_within_configured_limit: bool


@dataclass(frozen=True)
class ScenarioAdjustment:
    revenue_base_change: float = 0.0
    transfer_change: float = 0.0
    expenditure_change: float = 0.0
    eligible_exceptions_change: float = 0.0
    financing_sources_change: float = 0.0
    net_borrowing_change: float = 0.0


def _ratio(num: float, den: float) -> float:
    if den <= 0:
        return 0.0
    return num / den


def calculate_budget(inputs: BudgetInputs) -> BudgetResult:
    values = (
        inputs.revenue_base,
        inputs.transfers,
        inputs.expenditure,
        inputs.eligible_exceptions,
        inputs.current_debt,
        inputs.debt_service,
        inputs.financing_sources,
    )
    if any(v < 0 for v in values):
        raise ValueError("бюджетные величины не могут быть отрицательными")
    if not 0 <= inputs.deficit_limit_ratio <= 1:
        raise ValueError("deficit_limit_ratio должен быть в диапазоне [0, 1]")
    if not 0 <= inputs.debt_limit_ratio <= 2:
        raise ValueError("debt_limit_ratio должен быть в диапазоне [0, 2]")
    if not 0 <= inputs.debt_service_limit_ratio <= 1:
        raise ValueError("debt_service_limit_ratio должен быть в диапазоне [0, 1]")

    total_revenue = inputs.revenue_base + inputs.transfers
    balance = total_revenue - inputs.expenditure
    deficit = max(-balance, 0.0)
    deficit_base = inputs.revenue_base if inputs.deficit_base is None else inputs.deficit_base
    if deficit_base < 0:
        raise ValueError("deficit_base не может быть отрицательной")
    deficit_ratio = _ratio(deficit, deficit_base)

    base_limit = deficit_base * inputs.deficit_limit_ratio
    raw_normalization_gap = max(deficit - base_limit, 0.0)
    allowed_deficit = base_limit + inputs.eligible_exceptions
    normalization_gap = max(deficit - allowed_deficit, 0.0)

    recurring_balance = inputs.recurring_revenue - inputs.recurring_expenditure
    structural_gap = max(-recurring_balance, 0.0)
    financing_gap = max(deficit - inputs.financing_sources, 0.0)

    debt_after = max(inputs.current_debt + inputs.planned_net_borrowing, 0.0)
    debt_ratio = _ratio(debt_after, inputs.revenue_base)
    debt_limit = inputs.revenue_base * inputs.debt_limit_ratio
    debt_headroom = debt_limit - debt_after

    service_base = (
        inputs.expenditure_ex_subventions
        if inputs.expenditure_ex_subventions > 0
        else inputs.expenditure
    )
    debt_service_ratio = _ratio(inputs.debt_service, service_base)

    return BudgetResult(
        total_revenue=total_revenue,
        balance=balance,
        deficit=deficit,
        deficit_ratio=deficit_ratio,
        base_deficit_limit=base_limit,
        allowed_deficit=allowed_deficit,
        raw_normalization_gap=raw_normalization_gap,
        normalization_gap=normalization_gap,
        recurring_balance=recurring_balance,
        structural_gap=structural_gap,
        financing_gap=financing_gap,
        debt_after=debt_after,
        debt_ratio=debt_ratio,
        debt_headroom=debt_headroom,
        debt_service_ratio=debt_service_ratio,
        deficit_within_configured_limit=deficit <= allowed_deficit,
        debt_within_configured_limit=debt_ratio <= inputs.debt_limit_ratio,
        debt_service_within_configured_limit=debt_service_ratio <= inputs.debt_service_limit_ratio,
    )


def apply_scenario(inputs: BudgetInputs, adjustment: ScenarioAdjustment) -> BudgetInputs:
    return replace(
        inputs,
        revenue_base=max(inputs.revenue_base + adjustment.revenue_base_change, 0.0),
        transfers=max(inputs.transfers + adjustment.transfer_change, 0.0),
        expenditure=max(inputs.expenditure + adjustment.expenditure_change, 0.0),
        eligible_exceptions=max(
            inputs.eligible_exceptions + adjustment.eligible_exceptions_change,
            0.0,
        ),
        financing_sources=max(
            inputs.financing_sources + adjustment.financing_sources_change,
            0.0,
        ),
        planned_net_borrowing=inputs.planned_net_borrowing + adjustment.net_borrowing_change,
    )


def normalization_components(inputs: BudgetInputs, result: BudgetResult) -> dict[str, float]:
    return {
        "Доходная база": inputs.revenue_base,
        "Трансферты": inputs.transfers,
        "Расходы": inputs.expenditure,
        "Дефицит": result.deficit,
        "Базовый предел": result.base_deficit_limit,
        "Допустимые исключения": inputs.eligible_exceptions,
        "Допустимый дефицит": result.allowed_deficit,
        "Разрыв нормализации": result.normalization_gap,
        "Структурный разрыв": result.structural_gap,
        "Разрыв финансирования": result.financing_gap,
    }


@dataclass(frozen=True)
class GapStructure:
    normalization_gap: float
    structural_overlap: float
    non_structural_remainder: float
    revenue_base_to_close: float
    transfers_to_close: float
    expenditure_cut_to_close: float
    exception_to_close: float


@dataclass(frozen=True)
class BudgetCriterion:
    code: str
    title: str
    status: str
    value: float
    limit: float | None
    headroom: float | None


@dataclass(frozen=True)
class AutoScenario:
    name: str
    adjustment: ScenarioAdjustment
    result: BudgetResult


def gap_structure(inputs: BudgetInputs, result: BudgetResult) -> GapStructure:
    """Механическая структура разрыва без причинной интерпретации."""
    gap = result.normalization_gap
    structural_overlap = min(result.structural_gap, gap)
    non_structural = max(gap - structural_overlap, 0.0)
    revenue_effect = 1.0 + inputs.deficit_limit_ratio
    revenue_needed = gap / revenue_effect if revenue_effect > 0 else gap
    return GapStructure(
        normalization_gap=gap,
        structural_overlap=structural_overlap,
        non_structural_remainder=non_structural,
        revenue_base_to_close=revenue_needed,
        transfers_to_close=gap,
        expenditure_cut_to_close=gap,
        exception_to_close=gap,
    )


def budget_criteria(inputs: BudgetInputs, result: BudgetResult) -> tuple[BudgetCriterion, ...]:
    deficit_status = "OK" if result.normalization_gap <= 0 else "BREACH"
    structural_status = "OK" if result.structural_gap <= 0 else "WATCH"
    financing_status = "OK" if result.financing_gap <= 0 else "WATCH"
    debt_status = "OK" if result.debt_within_configured_limit else "BREACH"
    service_status = "OK" if result.debt_service_within_configured_limit else "BREACH"

    return (
        BudgetCriterion(
            code="deficit",
            title="Дефицит",
            status=deficit_status,
            value=result.deficit_ratio,
            limit=inputs.deficit_limit_ratio + _ratio(inputs.eligible_exceptions, inputs.revenue_base),
            headroom=result.allowed_deficit - result.deficit,
        ),
        BudgetCriterion(
            code="structural",
            title="Регулярный баланс",
            status=structural_status,
            value=result.recurring_balance,
            limit=0.0,
            headroom=result.recurring_balance,
        ),
        BudgetCriterion(
            code="financing",
            title="Финансирование",
            status=financing_status,
            value=result.financing_gap,
            limit=0.0,
            headroom=-result.financing_gap,
        ),
        BudgetCriterion(
            code="debt",
            title="Долг",
            status=debt_status,
            value=result.debt_ratio,
            limit=inputs.debt_limit_ratio,
            headroom=result.debt_headroom,
        ),
        BudgetCriterion(
            code="debt_service",
            title="Обслуживание долга",
            status=service_status,
            value=result.debt_service_ratio,
            limit=inputs.debt_service_limit_ratio,
            headroom=(
                inputs.debt_service_limit_ratio - result.debt_service_ratio
            ),
        ),
    )


def automatic_closure_scenarios(inputs: BudgetInputs) -> tuple[AutoScenario, ...]:
    """Три нейтральных механических способа закрыть normalization gap.

    Это не рекомендации: сценарии показывают требуемый масштаб изменения параметров.
    """
    base = calculate_budget(inputs)
    gap = base.normalization_gap
    if gap <= 0:
        empty = ScenarioAdjustment()
        return (
            AutoScenario("Доходы", empty, base),
            AutoScenario("Расходы", empty, base),
            AutoScenario("Сбалансированный", empty, base),
        )

    revenue_needed = gap / (1.0 + inputs.deficit_limit_ratio)

    revenue_adj = ScenarioAdjustment(revenue_base_change=revenue_needed)
    expense_adj = ScenarioAdjustment(expenditure_change=-gap)

    third = gap / 3.0
    balanced_adj = ScenarioAdjustment(
        revenue_base_change=third / (1.0 + inputs.deficit_limit_ratio),
        transfer_change=third,
        expenditure_change=-third,
    )

    scenarios = (
        ("Доходы", revenue_adj),
        ("Расходы", expense_adj),
        ("Сбалансированный", balanced_adj),
    )
    return tuple(
        AutoScenario(name, adjustment, calculate_budget(apply_scenario(inputs, adjustment)))
        for name, adjustment in scenarios
    )
