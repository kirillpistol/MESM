from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Fold:
    train_start: int
    train_end: int  # правая граница не включается
    test_start: int
    test_end: int   # правая граница не включается


@dataclass(frozen=True)
class BacktestPlan:
    development_folds: tuple[Fold, ...]
    holdout_start: int
    holdout_end: int


def expanding_window_plan(
    n_periods: int,
    min_train: int = 24,
    horizon: int = 1,
    holdout: int = 12,
    step: int = 1,
) -> BacktestPlan:
    """Строим expanding-window фолды, финальный holdout в настройке не используем."""
    if min(min_train, horizon, holdout, step) < 1:
        raise ValueError("min_train, horizon, holdout и step должны быть >= 1")
    if n_periods < min_train + horizon + holdout:
        raise ValueError("недостаточно истории для выбранного backtest")

    holdout_start = n_periods - holdout
    folds: list[Fold] = []
    train_end = min_train
    while train_end + horizon <= holdout_start:
        folds.append(Fold(0, train_end, train_end, train_end + horizon))
        train_end += step

    return BacktestPlan(tuple(folds), holdout_start, n_periods)
