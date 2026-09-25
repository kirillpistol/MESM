from mesm.budget.normalization import (
    BudgetInputs,
    ScenarioAdjustment,
    apply_scenario,
    calculate_budget,
    gap_structure,
    budget_criteria,
    automatic_closure_scenarios,
)


def test_normalization_gap():
    result = calculate_budget(BudgetInputs(
        revenue_base=100.0,
        transfers=20.0,
        expenditure=140.0,
        deficit_limit_ratio=0.10,
    ))
    assert result.deficit == 20.0
    assert result.allowed_deficit == 10.0
    assert result.normalization_gap == 10.0
    assert not result.deficit_within_configured_limit


def test_eligible_exception_reduces_normalization_gap_not_deficit():
    base = BudgetInputs(
        revenue_base=100.0,
        transfers=20.0,
        expenditure=140.0,
        eligible_exceptions=5.0,
    )
    result = calculate_budget(base)
    assert result.deficit == 20.0
    assert result.allowed_deficit == 15.0
    assert result.normalization_gap == 5.0


def test_transfer_reduces_deficit_but_not_revenue_base_limit():
    inputs = BudgetInputs(revenue_base=100.0, transfers=20.0, expenditure=140.0)
    scenario = apply_scenario(inputs, ScenarioAdjustment(transfer_change=10.0))
    result = calculate_budget(scenario)
    assert result.deficit == 10.0
    assert result.base_deficit_limit == 10.0
    assert result.normalization_gap == 0.0


def test_expenditure_reduction_closes_gap():
    inputs = BudgetInputs(revenue_base=100.0, transfers=20.0, expenditure=140.0)
    scenario = apply_scenario(inputs, ScenarioAdjustment(expenditure_change=-10.0))
    result = calculate_budget(scenario)
    assert result.deficit == 10.0
    assert result.normalization_gap == 0.0


def test_structural_and_financing_gaps_are_separate():
    result = calculate_budget(BudgetInputs(
        revenue_base=100.0,
        transfers=20.0,
        expenditure=140.0,
        recurring_revenue=90.0,
        recurring_expenditure=105.0,
        financing_sources=12.0,
    ))
    assert result.structural_gap == 15.0
    assert result.financing_gap == 8.0


def test_debt_ratios():
    result = calculate_budget(BudgetInputs(
        revenue_base=100.0,
        transfers=20.0,
        expenditure=120.0,
        current_debt=70.0,
        planned_net_borrowing=20.0,
        debt_service=10.0,
        expenditure_ex_subventions=100.0,
        debt_limit_ratio=1.0,
        debt_service_limit_ratio=0.15,
    ))
    assert result.debt_ratio == 0.9
    assert result.debt_headroom == 10.0
    assert result.debt_service_ratio == 0.1
    assert result.debt_within_configured_limit
    assert result.debt_service_within_configured_limit



def test_gap_structure_separates_structural_overlap():
    inputs = BudgetInputs(
        revenue_base=100.0,
        transfers=20.0,
        expenditure=140.0,
        recurring_revenue=90.0,
        recurring_expenditure=105.0,
    )
    result = calculate_budget(inputs)
    structure = gap_structure(inputs, result)
    assert structure.normalization_gap == 10.0
    assert structure.structural_overlap == 10.0
    assert structure.non_structural_remainder == 0.0
    assert abs(structure.revenue_base_to_close - (10.0 / 1.1)) < 1e-9


def test_automatic_scenarios_close_normalization_gap():
    inputs = BudgetInputs(
        revenue_base=100.0,
        transfers=20.0,
        expenditure=140.0,
        deficit_limit_ratio=0.10,
    )
    scenarios = automatic_closure_scenarios(inputs)
    assert {s.name for s in scenarios} == {"Доходы", "Расходы", "Сбалансированный"}
    for scenario in scenarios:
        assert abs(scenario.result.normalization_gap) < 1e-9


def test_budget_criteria_marks_breach_and_watch():
    inputs = BudgetInputs(
        revenue_base=100.0,
        transfers=20.0,
        expenditure=140.0,
        recurring_revenue=90.0,
        recurring_expenditure=105.0,
        financing_sources=5.0,
    )
    result = calculate_budget(inputs)
    criteria = {c.code: c for c in budget_criteria(inputs, result)}
    assert criteria["deficit"].status == "BREACH"
    assert criteria["structural"].status == "WATCH"
    assert criteria["financing"].status == "WATCH"



def test_raw_gap_before_exceptions():
    result = calculate_budget(BudgetInputs(
        revenue_base=100.0,
        transfers=20.0,
        expenditure=135.0,
        eligible_exceptions=8.0,
        deficit_limit_ratio=0.10,
    ))
    assert result.raw_normalization_gap == 5.0
    assert result.normalization_gap == 0.0



def test_deficit_base_can_differ_from_revenue_base():
    result = calculate_budget(BudgetInputs(
        revenue_base=120.0,
        transfers=30.0,
        deficit_base=100.0,
        expenditure=165.0,
        deficit_limit_ratio=0.10,
    ))
    assert result.deficit == 15.0
    assert result.deficit_ratio == 0.15
    assert result.base_deficit_limit == 10.0
