from mesm.models.economic_interpretation import (
    DomainStatus,
    EvidenceLevel,
    current_domain_assessments,
    fiscal_domain_assessment,
)
from mesm.models.interpretation import ReferenceFlag


def flag(code: str, active: bool = True) -> ReferenceFlag:
    return ReferenceFlag(code=code, title=code, active=active, explanation="test")


def test_fiscal_signal_is_not_promoted_to_warning():
    result = fiscal_domain_assessment(
        income_plan_deviation=-0.12,
        debt_load=0.31,
        budget_amendments=15,
        flags=[
            flag("income_shortfall"),
            flag("debt_peer_high"),
            flag("amendments_peer_high"),
        ],
    )
    assert result.status == DomainStatus.SCREENING_SIGNAL
    assert result.evidence == EvidenceLevel.MEDIUM
    assert "не подтвержденный structural break" in result.interpretation


def test_no_flags_means_context_not_normal():
    result = fiscal_domain_assessment(
        income_plan_deviation=0.08,
        debt_load=0.0,
        budget_amendments=2,
        flags=[],
    )
    assert result.status == DomainStatus.CONTEXT
    assert "не доказывает NORMAL" in result.interpretation


def test_unavailable_domains_remain_no_data():
    assessments = current_domain_assessments(
        income_plan_deviation=0.08,
        debt_load=0.0,
        budget_amendments=2,
        flags=[],
    )
    by_name = {item.domain: item for item in assessments}
    assert by_name["Consumer Demand"].status == DomainStatus.NO_DATA
    assert by_name["Municipal Finance"].status == DomainStatus.CONTEXT
