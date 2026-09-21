"""Transparent rolling-origin forecast benchmark for MESM."""
from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

import pandas as pd


@dataclass(frozen=True)
class BenchmarkMetrics:
    model: str
    observations: int
    mae: float
    r2: float
    wape: float
    rmse: float
    mase: float


def _linear_trend(history: list[float]) -> float:
    n = len(history)
    if n < 2:
        return history[-1]
    x_mean = (n - 1) / 2
    y_mean = sum(history) / n
    denom = sum((i - x_mean) ** 2 for i in range(n))
    if denom == 0:
        return history[-1]
    slope = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(history)) / denom
    intercept = y_mean - slope * x_mean
    return intercept + slope * n


def expanding_forecast_table(
    series: pd.DataFrame,
    *,
    min_train: int = 12,
    seasonality: int = 12,
) -> pd.DataFrame:
    if not {"period", "value"}.issubset(series.columns):
        raise ValueError("series должна содержать period и value")

    frame = series[["period", "value"]].copy()
    frame["period"] = pd.to_datetime(frame["period"], errors="raise")
    frame["value"] = pd.to_numeric(frame["value"], errors="raise")
    frame = frame.sort_values("period").drop_duplicates("period", keep="last").reset_index(drop=True)

    if len(frame) <= min_train:
        raise ValueError(
            f"для benchmark нужно больше {min_train} наблюдений; сейчас {len(frame)}"
        )

    rows: list[dict] = []
    values = frame["value"].astype(float).tolist()
    for i in range(min_train, len(frame)):
        history = values[:i]
        last_value = history[-1]
        seasonal_naive = history[-seasonality] if len(history) >= seasonality else last_value
        trend = _linear_trend(history)
        rows.append(
            {
                "period": frame.loc[i, "period"],
                "actual": values[i],
                "last_value": float(last_value),
                "seasonal_naive": float(seasonal_naive),
                "linear_trend": float(trend),
            }
        )
    return pd.DataFrame(rows)


def _metrics(
    actual: list[float],
    predicted: list[float],
    insample: list[float],
    seasonality: int,
) -> tuple[float, float, float, float, float]:
    if not actual:
        return (float("nan"),) * 5

    errors = [a - p for a, p in zip(actual, predicted)]
    absolute_errors = [abs(e) for e in errors]
    mae = sum(absolute_errors) / len(actual)
    rmse = sqrt(sum(e ** 2 for e in errors) / len(actual))

    actual_mean = sum(actual) / len(actual)
    sse = sum(e ** 2 for e in errors)
    sst = sum((a - actual_mean) ** 2 for a in actual)
    r2 = 1.0 - sse / sst if sst else float("nan")

    denom = sum(abs(v) for v in actual)
    wape = sum(absolute_errors) / denom if denom else float("nan")

    lag = seasonality if len(insample) > seasonality else 1
    scale_terms = [abs(insample[i] - insample[i - lag]) for i in range(lag, len(insample))]
    scale = sum(scale_terms) / len(scale_terms) if scale_terms else 0.0
    mase = mae / scale if scale else float("nan")
    return mae, r2, wape, rmse, mase


def benchmark_metrics(
    full_series: pd.DataFrame,
    forecast_table: pd.DataFrame,
    *,
    min_train: int = 12,
    seasonality: int = 12,
) -> list[BenchmarkMetrics]:
    ordered = full_series.sort_values("period").drop_duplicates("period", keep="last")
    insample = pd.to_numeric(ordered["value"], errors="raise").astype(float).tolist()[:min_train]
    actual = forecast_table["actual"].astype(float).tolist()

    results: list[BenchmarkMetrics] = []
    for column, name in (
        ("last_value", "Last Value"),
        ("seasonal_naive", "Seasonal Naive"),
        ("linear_trend", "Linear Trend"),
    ):
        pred = forecast_table[column].astype(float).tolist()
        mae, r2, wape, rmse, mase = _metrics(actual, pred, insample, seasonality)
        results.append(BenchmarkMetrics(name, len(actual), mae, r2, wape, rmse, mase))
    return results
