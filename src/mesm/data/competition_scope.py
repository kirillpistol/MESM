"""Competition geographic scope: Surgut target, HMAO training network."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class CompetitionScope:
    target_oktmo: str = "71876000"
    region_oktmo_prefix: str = "71"
    primary_holdout_year: int = 2024


def apply_competition_scope(
    frame: pd.DataFrame,
    scope: CompetitionScope = CompetitionScope(),
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = {"oktmo", "period_start"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError("Competition scope requires columns: " + ", ".join(sorted(missing)))

    data = frame.copy()
    data["oktmo"] = data["oktmo"].astype(str).str.strip()
    if "model_eligible" in data.columns:
        data = data[data["model_eligible"].astype(bool)].copy()
    if "identity_status" in data.columns:
        data = data[data["identity_status"].astype(str).eq("OKTMO_RESOLVED")].copy()

    hmao = data[data["oktmo"].str.startswith(scope.region_oktmo_prefix)].copy()
    target = hmao[hmao["oktmo"].eq(scope.target_oktmo)].copy()

    if target.empty:
        raise ValueError(
            f"Target municipality OKTMO {scope.target_oktmo} is absent from the scoped panel."
        )

    return (
        hmao.sort_values(["oktmo", "period_start"]).reset_index(drop=True),
        target.sort_values("period_start").reset_index(drop=True),
    )


def split_target_holdout(
    target: pd.DataFrame,
    scope: CompetitionScope = CompetitionScope(),
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if "period_start" not in target.columns:
        raise ValueError("period_start is required for temporal holdout.")
    data = target.copy()
    periods = pd.to_datetime(data["period_start"], errors="raise")
    train = data[periods.dt.year < scope.primary_holdout_year].copy()
    holdout = data[periods.dt.year == scope.primary_holdout_year].copy()
    if train.empty or holdout.empty:
        raise ValueError(
            f"Need observations before and during holdout year {scope.primary_holdout_year}."
        )
    return train.reset_index(drop=True), holdout.reset_index(drop=True)
