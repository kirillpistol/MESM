"""External Data Layer: прозрачная работа с месячными/недельными факторами."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ExternalCoverage:
    rows: int
    geographies: int
    variables: int
    start_period: str | None
    end_period: str | None


def normalize_external(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "period", "geography_name", "geography_level", "variable",
        "value", "unit", "source", "publication_date", "as_of_date",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError("не хватает колонок: " + ", ".join(missing))

    out = frame.copy()
    out["period"] = pd.to_datetime(out["period"], errors="raise")
    out["publication_date"] = pd.to_datetime(out["publication_date"], errors="raise")
    out["as_of_date"] = pd.to_datetime(out["as_of_date"], errors="raise")
    out["value"] = pd.to_numeric(out["value"], errors="raise")
    out["geography_name"] = out["geography_name"].astype(str).str.strip()
    out["variable"] = out["variable"].astype(str).str.strip()
    return out.sort_values(["geography_name", "variable", "period"]).reset_index(drop=True)


def coverage(frame: pd.DataFrame) -> ExternalCoverage:
    if frame.empty:
        return ExternalCoverage(0, 0, 0, None, None)
    out = normalize_external(frame)
    return ExternalCoverage(
        rows=len(out),
        geographies=int(out["geography_name"].nunique()),
        variables=int(out["variable"].nunique()),
        start_period=out["period"].min().strftime("%Y-%m-%d"),
        end_period=out["period"].max().strftime("%Y-%m-%d"),
    )


def extract_series(frame: pd.DataFrame, geography_name: str, variable: str) -> pd.DataFrame:
    out = normalize_external(frame)
    selected = out[
        (out["geography_name"] == geography_name)
        & (out["variable"] == variable)
    ][["period", "value", "unit", "source", "publication_date", "as_of_date"]].copy()
    if selected.empty:
        raise ValueError("ряд для выбранной географии и переменной не найден")
    return selected.sort_values("period").reset_index(drop=True)
