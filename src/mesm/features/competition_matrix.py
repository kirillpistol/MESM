"""Leakage-safe feature matrix for municipal consumption forecasting."""
from __future__ import annotations

from math import cos, pi, sin
from typing import Iterable

import pandas as pd


DEFAULT_LAGS = (1, 2, 3, 6, 12)
DEFAULT_ROLLING_WINDOWS = (3, 6)


def build_consumption_model_matrix(
    frame: pd.DataFrame,
    *,
    category_codes: Iterable[str] | None = None,
    lags: tuple[int, ...] = DEFAULT_LAGS,
    rolling_windows: tuple[int, ...] = DEFAULT_ROLLING_WINDOWS,
) -> pd.DataFrame:
    required = {"oktmo", "period_start", "category_code", "spending_nominal"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError("Consumption matrix missing columns: " + ", ".join(sorted(missing)))

    data = frame.copy()
    if "model_eligible" in data.columns:
        data = data[data["model_eligible"].astype(bool)].copy()
    if "identity_status" in data.columns:
        data = data[data["identity_status"].astype(str).eq("OKTMO_RESOLVED")].copy()

    data["oktmo"] = data["oktmo"].astype(str).str.strip()
    data["period_start"] = pd.to_datetime(data["period_start"], errors="raise")
    data["spending_nominal"] = pd.to_numeric(data["spending_nominal"], errors="raise").astype(float)

    if category_codes is not None:
        wanted = {str(value) for value in category_codes}
        data = data[data["category_code"].astype(str).isin(wanted)].copy()

    keys = ["oktmo", "category_code"]
    data = data.sort_values(keys + ["period_start"]).reset_index(drop=True)
    if data.duplicated(keys + ["period_start"]).any():
        raise ValueError("Model matrix requires unique OKTMO + category + period rows.")

    data["target"] = data["spending_nominal"]
    data["month"] = data["period_start"].dt.month.astype(int)
    data["quarter"] = data["period_start"].dt.quarter.astype(int)
    data["year"] = data["period_start"].dt.year.astype(int)
    data["month_sin"] = data["month"].map(lambda m: sin(2 * pi * m / 12))
    data["month_cos"] = data["month"].map(lambda m: cos(2 * pi * m / 12))
    data["history_points"] = data.groupby(keys).cumcount()

    grouped = data.groupby(keys, sort=False)["target"]
    for lag in lags:
        if lag <= 0:
            raise ValueError("All lags must be positive.")
        data[f"lag_{lag}"] = grouped.shift(lag)

    shifted = grouped.shift(1)
    for window in rolling_windows:
        if window <= 0:
            raise ValueError("Rolling windows must be positive.")
        data[f"rolling_mean_{window}"] = (
            shifted.groupby([data["oktmo"], data["category_code"]])
            .transform(lambda s: s.rolling(window=window, min_periods=1).mean())
        )
        data[f"rolling_std_{window}"] = (
            shifted.groupby([data["oktmo"], data["category_code"]])
            .transform(lambda s: s.rolling(window=window, min_periods=2).std())
        )

    if "lag_12" in data.columns:
        denominator = data["lag_12"].where(data["lag_12"] != 0)
        data["yoy_change_lagged"] = data["lag_1"] / denominator - 1.0

    return data
