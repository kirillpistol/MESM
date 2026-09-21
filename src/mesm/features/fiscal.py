from __future__ import annotations


def _safe_div(num: float | None, den: float | None) -> float | None:
    if num is None or den in (None, 0):
        return None
    return num / den


def revision_rate(initial: float | None, revised: float | None) -> float | None:
    if initial is None or revised is None:
        return None
    return _safe_div(revised - initial, initial)


def revision_magnitude(initial: float | None, revised: float | None) -> float | None:
    if initial in (None, 0) or revised is None:
        return None
    return abs(revised - initial) / abs(initial)


def execution_rate(revised: float | None, actual: float | None) -> float | None:
    return _safe_div(actual, revised)


def execution_gap(revised: float | None, actual: float | None) -> float | None:
    if revised in (None, 0) or actual is None:
        return None
    return (actual - revised) / revised


def coverage_gap(planned_resources: float | None, estimated_cost: float | None) -> float | None:
    value = _safe_div(planned_resources, estimated_cost)
    return None if value is None else value - 1.0


def official_i13(initial_tax: float, initial_nontax: float, actual_tax: float, actual_nontax: float) -> float | None:
    initial = initial_tax + initial_nontax
    actual = actual_tax + actual_nontax
    value = _safe_div(actual - initial, initial)
    return None if value is None else max(value, 0.0)


def official_i15(program_expense: float, total_expense: float) -> float | None:
    return _safe_div(program_expense, total_expense)


def official_i25(q1: float, q2: float, q3: float, q4: float) -> float | None:
    average_q1_q3 = (q1 + q2 + q3) / 3.0
    return _safe_div(q4, average_q1_q3)


def official_i26(utility_compensation: float, total_expense: float) -> float | None:
    return _safe_div(utility_compensation, total_expense)


def official_i27(overdue_payables: float, total_expense: float) -> float | None:
    return _safe_div(overdue_payables, total_expense)


def official_i33(municipal_debt: float, own_revenue_base: float) -> float | None:
    return _safe_div(municipal_debt, own_revenue_base)
