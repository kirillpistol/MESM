import pandas as pd
import pytest

from mesm.models.competition_challengers import prophet_expanding_forecast


def test_prophet_runs_on_competition_fixture():
    pytest.importorskip("prophet")
    frame=pd.read_csv("data/processed/competition/surgut_all_2023_2024.csv")[["period","value"]]
    forecasts,metrics=prophet_expanding_forecast(frame)
    assert len(forecasts)==12
    assert metrics.observations==12
    assert metrics.mae > 0
