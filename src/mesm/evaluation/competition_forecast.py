"""Competition baseline tournament focused on Surgut."""
from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

import pandas as pd

from mesm.evaluation.forecast_benchmark import (
    benchmark_metrics,
    expanding_forecast_table,
)


def _target_series(
    frame: pd.DataFrame,
    *,
    target_oktmo: str,
    category_code: str,
    holdout_year: int,
) -> pd.DataFrame:
    required = {"oktmo", "period_start", "category_code", "spending_nominal"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError("Competition benchmark missing columns: " + ", ".join(sorted(missing)))

    data = frame.copy()
    data["oktmo"] = data["oktmo"].astype(str).str.strip()
    data["period_start"] = pd.to_datetime(data["period_start"], errors="raise")
    data = data[
        data["oktmo"].eq(str(target_oktmo))
        & data["category_code"].astype(str).eq(str(category_code))
        & (data["period_start"].dt.year <= holdout_year)
    ].copy()

    if data.empty:
        raise ValueError(f"No target data for OKTMO={target_oktmo}, category={category_code}.")

    return (
        data[["period_start", "spending_nominal"]]
        .rename(columns={"period_start": "period", "spending_nominal": "value"})
        .sort_values("period")
        .reset_index(drop=True)
    )


def evaluate_target_baselines(
    frame: pd.DataFrame,
    *,
    target_oktmo: str = "71876000",
    category_code: str = "ALL",
    holdout_year: int = 2024,
    min_train: int = 12,
    seasonality: int = 12,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    series = _target_series(
        frame,
        target_oktmo=target_oktmo,
        category_code=category_code,
        holdout_year=holdout_year,
    )
    forecasts = expanding_forecast_table(series, min_train=min_train, seasonality=seasonality)
    forecasts = forecasts[pd.to_datetime(forecasts["period"]).dt.year == holdout_year].reset_index(drop=True)

    if forecasts.empty:
        raise ValueError(f"No forecasts produced for holdout year {holdout_year}.")

    metrics = benchmark_metrics(
        series,
        forecasts,
        min_train=min_train,
        seasonality=seasonality,
    )
    metric_frame = pd.DataFrame([asdict(row) for row in metrics]).sort_values(
        ["mae", "rmse", "model"]
    ).reset_index(drop=True)
    metric_frame["rank_mae"] = range(1, len(metric_frame) + 1)
    return forecasts, metric_frame


def evaluate_categories(
    frame: pd.DataFrame,
    *,
    categories: Iterable[str],
    target_oktmo: str = "71876000",
    holdout_year: int = 2024,
    min_train: int = 12,
    seasonality: int = 12,
) -> pd.DataFrame:
    rows = []
    for category_code in categories:
        _, metrics = evaluate_target_baselines(
            frame,
            target_oktmo=target_oktmo,
            category_code=str(category_code),
            holdout_year=holdout_year,
            min_train=min_train,
            seasonality=seasonality,
        )
        best = metrics.iloc[0].to_dict()
        best["category_code"] = str(category_code)
        rows.append(best)
    return pd.DataFrame(rows).sort_values("mae").reset_index(drop=True)
