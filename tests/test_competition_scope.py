import pandas as pd
import pytest

from mesm.data.competition_scope import CompetitionScope, apply_competition_scope, split_target_holdout


def test_scope_keeps_hmao_and_surgut_target_only():
    frame = pd.DataFrame([
        {"oktmo": "71876000", "period_start": "2023-01-01", "model_eligible": True, "identity_status": "OKTMO_RESOLVED"},
        {"oktmo": "71876000", "period_start": "2024-01-01", "model_eligible": True, "identity_status": "OKTMO_RESOLVED"},
        {"oktmo": "71871000", "period_start": "2024-01-01", "model_eligible": True, "identity_status": "OKTMO_RESOLVED"},
        {"oktmo": "45701000", "period_start": "2024-01-01", "model_eligible": True, "identity_status": "OKTMO_RESOLVED"},
    ])
    hmao, target = apply_competition_scope(frame)

    assert set(hmao["oktmo"]) == {"71876000", "71871000"}
    assert set(target["oktmo"]) == {"71876000"}

    train, holdout = split_target_holdout(target)
    assert pd.to_datetime(train["period_start"]).dt.year.unique().tolist() == [2023]
    assert pd.to_datetime(holdout["period_start"]).dt.year.unique().tolist() == [2024]


def test_scope_rejects_missing_target():
    frame = pd.DataFrame([
        {"oktmo": "71871000", "period_start": "2024-01-01", "model_eligible": True, "identity_status": "OKTMO_RESOLVED"},
    ])
    with pytest.raises(ValueError):
        apply_competition_scope(frame, CompetitionScope())
