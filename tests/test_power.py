from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mesm.simulation.power import (
    calibrate_cusum_threshold,
    estimate_null_alarm_rate,
    inject_shock,
)


def test_inject_shock_is_localized():
    x = [0.0] * 10
    y = inject_shock(x, 3, 2, 5.0)
    assert y[2] == 0.0
    assert y[3:5] == [5.0, 5.0]
    assert y[5] == 0.0


def test_threshold_calibration_respects_target_on_deterministic_sample():
    baseline = [-1.0, -0.5, 0.0, 0.5, 1.0] * 8
    threshold, fpr = calibrate_cusum_threshold(
        baseline,
        target_fpr=0.25,
        candidates=(4.0, 6.0, 8.0, 10.0, 12.0),
        runs=200,
        warmup=6,
        seed=7,
    )
    assert threshold >= 4.0
    assert fpr <= 0.25
    assert estimate_null_alarm_rate(
        baseline,
        threshold=threshold,
        runs=200,
        warmup=6,
        seed=7,
    ) <= 0.25
