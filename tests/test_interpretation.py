from mesm.models.interpretation import (
    percentile_rank,
    reference_screening_flags,
    screening_conclusion,
)


def test_percentile_rank():
    assert percentile_rank([1, 2, 3, 4], 3) == 0.75


def test_reference_flags_do_not_claim_state():
    flags = reference_screening_flags(
        income_plan_deviation=0.10,
        debt_load=0.0,
        debt_peer_values=[0.0, 0.1, 0.2, 0.3],
        budget_amendments=4,
        amendment_peer_values=[2, 3, 4, 10],
        quality_rank=10,
        quality_peer_values=list(range(1, 14)),
    )
    text = screening_conclusion(flags)
    assert "NORMAL" in text or "структурный шок" in text
    assert any(flag.code == "quality_rank_peer" for flag in flags)
