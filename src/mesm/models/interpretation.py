"""Интерпретация Reference-признаков без подмены калиброванного состояния.

Этот модуль не присваивает NORMAL/WARNING. Он только отмечает прозрачные
скрининговые флаги, которые помогают понять, на что смотреть до полноценного
temporal backtest и калибровки ReferenceScore.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReferenceFlag:
    code: str
    title: str
    active: bool
    explanation: str


def percentile_rank(values: list[float], value: float) -> float:
    clean = sorted(float(v) for v in values)
    if not clean:
        return 0.0
    below_or_equal = sum(v <= value for v in clean)
    return below_or_equal / len(clean)


def reference_screening_flags(
    *,
    income_plan_deviation: float | None,
    debt_load: float | None,
    debt_peer_values: list[float],
    budget_amendments: float | None,
    amendment_peer_values: list[float],
    quality_rank: float | None,
    quality_peer_values: list[float],
) -> list[ReferenceFlag]:
    flags: list[ReferenceFlag] = []

    shortfall = income_plan_deviation is not None and income_plan_deviation < 0
    flags.append(
        ReferenceFlag(
            code="income_shortfall",
            title="Доходы ниже первоначального плана",
            active=shortfall,
            explanation=(
                f"Отклонение {income_plan_deviation:.1%}: требуется внимание к доходной части."
                if shortfall
                else "Отрицательного отклонения от первоначального плана по доступному году нет."
            ),
        )
    )

    if debt_load is None or not debt_peer_values:
        debt_active = False
        debt_text = "Недостаточно данных для peer-сравнения долговой нагрузки."
    else:
        debt_pct = percentile_rank(debt_peer_values, debt_load)
        debt_active = debt_pct >= 0.75 and debt_load > 0
        debt_text = f"Долговая нагрузка находится примерно на {debt_pct:.0%} перцентиле среди 22 МО."
    flags.append(
        ReferenceFlag(
            code="debt_peer_high",
            title="Повышенная долговая нагрузка относительно peers",
            active=debt_active,
            explanation=debt_text,
        )
    )

    if budget_amendments is None or not amendment_peer_values:
        amend_active = False
        amend_text = "Недостаточно данных для peer-сравнения числа изменений бюджета."
    else:
        amend_pct = percentile_rank(amendment_peer_values, budget_amendments)
        amend_active = amend_pct >= 0.75
        amend_text = f"Число изменений бюджета находится примерно на {amend_pct:.0%} перцентиле среди 22 МО."
    flags.append(
        ReferenceFlag(
            code="amendments_peer_high",
            title="Высокая частота изменений бюджета относительно peers",
            active=amend_active,
            explanation=amend_text,
        )
    )

    if quality_rank is None or not quality_peer_values:
        quality_active = False
        quality_text = "Официальный ранг для сравнения недоступен."
    else:
        quality_pct = percentile_rank(quality_peer_values, quality_rank)
        quality_active = quality_pct >= 0.75
        quality_text = (
            f"Официальный ранг находится примерно на {quality_pct:.0%} перцентиле; "
            "это контекстный флаг, а не доказательство экономического шока."
        )
    flags.append(
        ReferenceFlag(
            code="quality_rank_peer",
            title="Контекстный флаг официального ранга",
            active=quality_active,
            explanation=quality_text,
        )
    )

    return flags


def screening_conclusion(flags: list[ReferenceFlag]) -> str:
    active = [flag for flag in flags if flag.active]
    if not active:
        return (
            "По доступным Reference-признакам скрининговых флагов не выявлено. "
            "Это не означает состояние NORMAL: для него нужны временная устойчивость, "
            "калиброванный порог и подтверждение детекторами."
        )

    names = "; ".join(flag.title for flag in active)
    return (
        f"Есть {len(active)} скрининговых флаг(а): {names}. "
        "Это повод для наблюдения, но не подтвержденный структурный шок. "
        "Для WARNING/BREAK_CONFIRMED нужны persistence и независимое подтверждение."
    )
