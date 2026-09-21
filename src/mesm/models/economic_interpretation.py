"""Экономическая интерпретация доступных контуров MESM.

Сейчас реальные публичные данные покрывают главным образом Municipal Finance.
Модуль не присваивает WARNING/BREAK без temporal backtest.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from mesm.models.interpretation import ReferenceFlag


class DomainStatus(str, Enum):
    NO_DATA = "NO_DATA"
    CONTEXT = "CONTEXT"
    SCREENING_SIGNAL = "SCREENING_SIGNAL"


class EvidenceLevel(str, Enum):
    INSUFFICIENT = "INSUFFICIENT"
    LOW = "LOW"
    MEDIUM = "MEDIUM"


@dataclass(frozen=True)
class DomainAssessment:
    domain: str
    status: DomainStatus
    evidence: EvidenceLevel
    headline: str
    interpretation: str


def fiscal_domain_assessment(
    *,
    income_plan_deviation: float | None,
    debt_load: float | None,
    budget_amendments: float | None,
    flags: list[ReferenceFlag],
) -> DomainAssessment:
    active = [flag for flag in flags if flag.active]
    active_codes = {flag.code for flag in active}

    parts: list[str] = []
    if income_plan_deviation is not None:
        if income_plan_deviation < 0:
            parts.append(
                f"фактические доходы ниже первоначального плана на {abs(income_plan_deviation):.1%}"
            )
        else:
            parts.append(
                f"фактические доходы выше первоначального плана на {income_plan_deviation:.1%}"
            )

    if "debt_peer_high" in active_codes and debt_load is not None:
        parts.append(f"долговая нагрузка повышена относительно peer-группы ({debt_load:.1%})")

    if "amendments_peer_high" in active_codes and budget_amendments is not None:
        parts.append(
            f"число изменений бюджета повышено относительно peer-группы ({budget_amendments:.0f})"
        )

    if not active:
        return DomainAssessment(
            domain="Municipal Finance",
            status=DomainStatus.CONTEXT,
            evidence=EvidenceLevel.LOW,
            headline="Фискальный контекст без активных скрининговых флагов",
            interpretation=(
                "По доступному годовому Reference-срезу активных скрининговых флагов нет. "
                "Это не доказывает NORMAL: текущие данные слишком редкие для подтверждения "
                "отсутствия структурного сдвига."
            ),
        )

    strong_codes = {"income_shortfall", "debt_peer_high", "amendments_peer_high"}
    strong_count = len(active_codes & strong_codes)
    evidence = EvidenceLevel.MEDIUM if strong_count >= 2 else EvidenceLevel.LOW

    detail = "; ".join(parts) if parts else "есть активные фискальные скрининговые признаки"
    return DomainAssessment(
        domain="Municipal Finance",
        status=DomainStatus.SCREENING_SIGNAL,
        evidence=evidence,
        headline="Есть фискальные признаки, требующие наблюдения",
        interpretation=(
            f"В текущем Reference-срезе {detail}. "
            "Это фискальный screening signal, а не подтвержденный structural break. "
            "Для WARNING нужны временная устойчивость и независимое подтверждение."
        ),
    )


def unavailable_domain(domain: str) -> DomainAssessment:
    return DomainAssessment(
        domain=domain,
        status=DomainStatus.NO_DATA,
        evidence=EvidenceLevel.INSUFFICIENT,
        headline="Недостаточно данных",
        interpretation=(
            "В текущей публичной сборке нет достаточного временного ряда, "
            "чтобы присвоить этой экономической области состояние."
        ),
    )


def current_domain_assessments(
    *,
    income_plan_deviation: float | None,
    debt_load: float | None,
    budget_amendments: float | None,
    flags: list[ReferenceFlag],
) -> list[DomainAssessment]:
    return [
        unavailable_domain("Consumer Demand"),
        unavailable_domain("Income & Labour"),
        unavailable_domain("Cost of Living"),
        unavailable_domain("Business Activity"),
        fiscal_domain_assessment(
            income_plan_deviation=income_plan_deviation,
            debt_load=debt_load,
            budget_amendments=budget_amendments,
            flags=flags,
        ),
        unavailable_domain("Economic Structure"),
    ]
