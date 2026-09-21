from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pytest
from mesm.backtest.split import expanding_window_plan


def test_expanding_window_locks_final_holdout():
    plan = expanding_window_plan(60, min_train=24, horizon=1, holdout=12, step=1)
    assert plan.holdout_start == 48
    assert plan.holdout_end == 60
    assert plan.development_folds[0].train_end == 24
    assert plan.development_folds[-1].test_end <= plan.holdout_start


def test_backtest_rejects_short_history():
    with pytest.raises(ValueError):
        expanding_window_plan(30, min_train=24, horizon=1, holdout=12)
