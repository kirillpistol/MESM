"""Decision-ready текст без подмены доказательств рекомендациями."""
from __future__ import annotations

from dataclasses import dataclass

from mesm.models.economic_interpretation import DomainAssessment, DomainStatus


@dataclass(frozen=True)
class DecisionMemo:
    headline: str
    what_changed: str
    evidence: str
    interpretation: str
    next_checks: tuple[str, ...]
    limitation: str


def build_decision_memo(
    fiscal: DomainAssessment,
    *,
    external_loaded: bool,
    external_variables: int = 0,
    benchmark_ready: bool = False,
) -> DecisionMemo:
    if fiscal.status == DomainStatus.SCREENING_SIGNAL:
        headline = "Фискальный сигнал требует наблюдения"
        what_changed = fiscal.interpretation
    else:
        headline = "Фискальный контекст без подтвержденного сигнала"
        what_changed = fiscal.interpretation

    evidence = f"Fiscal evidence: {fiscal.evidence.value}."
    if external_loaded:
        evidence += f" External inputs loaded: {external_variables} variables."
    else:
        evidence += " External inputs: NO_DATA."

    if benchmark_ready:
        interpretation = (
            "Временной ряд внешнего/целевого показателя уже можно проверять через "
            "Forecast vs Actual benchmark. Это еще не подтверждает structural shift."
        )
    elif external_loaded:
        interpretation = (
            "External Layer подключен, но истории пока недостаточно для полноценного "
            "Forecast vs Actual benchmark либо не выбран целевой ряд."
        )
    else:
        interpretation = (
            "Ранний Predictive signal пока не рассчитывается: нет достаточного "
            "высокочастотного временного ряда."
        )

    next_checks = (
        "Проверить качество и дату публикации новых наблюдений.",
        "Сравнить факт с ожидаемой траекторией после накопления достаточной истории.",
        "Только после persistence и независимого detector confirmation повышать состояние.",
    )

    return DecisionMemo(
        headline=headline,
        what_changed=what_changed,
        evidence=evidence,
        interpretation=interpretation,
        next_checks=next_checks,
        limitation=(
            "Вывод является decision support. Корреляционные признаки не интерпретируются "
            "как доказанная причина экономического изменения."
        ),
    )
