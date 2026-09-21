import pandas as pd

from mesm.evaluation.forecast_benchmark import expanding_forecast_table, benchmark_metrics


def test_forecast_vs_actual_table_and_metrics():
    frame = pd.DataFrame({
        "period": pd.date_range("2024-01-01", periods=18, freq="MS"),
        "value": [100 + i for i in range(18)],
    })
    table = expanding_forecast_table(frame, min_train=12, seasonality=12)
    assert len(table) == 6
    assert {"actual", "last_value", "seasonal_naive", "linear_trend"}.issubset(table.columns)

    metrics = benchmark_metrics(frame, table, min_train=12, seasonality=12)
    by_name = {m.model: m for m in metrics}
    assert by_name["Linear Trend"].mae < by_name["Seasonal Naive"].mae
    assert by_name["Linear Trend"].rmse < by_name["Seasonal Naive"].rmse
    assert by_name["Linear Trend"].r2 > by_name["Seasonal Naive"].r2
