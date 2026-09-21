import pandas as pd

from mesm.evaluation.competition_forecast import evaluate_target_baselines


def test_surgut_baseline_tournament_returns_mae_and_r2():
    values = [
        100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 150, 155,
        160, 165, 170, 175, 180, 185, 190, 195, 200, 205, 210, 215,
    ]
    frame = pd.DataFrame({
        "oktmo": ["71876000"] * 24,
        "period_start": pd.date_range("2023-01-01", periods=24, freq="MS"),
        "category_code": ["ALL"] * 24,
        "spending_nominal": values,
    })

    forecasts, metrics = evaluate_target_baselines(frame)

    assert len(forecasts) == 12
    assert pd.to_datetime(forecasts["period"]).dt.year.unique().tolist() == [2024]
    assert {"model", "mae", "r2", "wape", "rmse", "mase", "rank_mae"}.issubset(metrics.columns)
    assert metrics.iloc[0]["model"] == "Linear Trend"
    assert metrics.iloc[0]["mae"] == 0.0
