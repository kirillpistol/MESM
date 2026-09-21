from mesm.models.economic_interpretation import DomainAssessment, DomainStatus, EvidenceLevel
from mesm.reporting.decision_memo import build_decision_memo


def test_decision_memo_keeps_predictive_limit_visible():
    fiscal = DomainAssessment(
        domain="Municipal Finance",
        status=DomainStatus.SCREENING_SIGNAL,
        evidence=EvidenceLevel.MEDIUM,
        headline="signal",
        interpretation="Есть фискальные признаки.",
    )
    memo = build_decision_memo(fiscal, external_loaded=False)
    assert "NO_DATA" in memo.evidence
    assert "не рассчитывается" in memo.interpretation
