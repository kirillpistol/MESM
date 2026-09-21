import pandas as pd
import pytest

from mesm.models.competition_challengers import prepare_hmao_source_panel, score_forecast


def test_score_forecast_has_required_competition_metrics():
    result=score_forecast([10,12,14],[9,13,15],insample=[5,7,8,10])
    assert result.mae == pytest.approx(1.0)
    assert result.observations == 3
    assert result.r2 < 1.0


def test_hmao_source_panel_fails_closed_on_name_collision():
    frame=pd.DataFrame([
        {"period":"2024-01-01","value":10,"category_15":"Все категории","mo":"A"},
        {"period":"2024-01-01","value":11,"category_15":"Все категории","mo":"A"},
    ])
    with pytest.raises(ValueError):
        prepare_hmao_source_panel(frame,peer_oktmo_map={"A":"71876000"})


def test_hmao_source_panel_maps_training_identity_to_oktmo():
    frame=pd.DataFrame([
        {"period":"2024-01-01","value":10,"category_15":"Все категории","mo":"Сургут source"},
    ])
    panel=prepare_hmao_source_panel(frame,peer_oktmo_map={"Сургут source":"71876000"})
    assert panel["oktmo"].tolist()==["71876000"]
