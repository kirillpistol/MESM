from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mesm.evaluation.metrics import average_precision, false_alarms_per_entity_year, lead_time_days, roc_auc, rmse, wape
from mesm.evaluation.dual_value import compare_dual_value


def test_forecast_metrics():
    assert round(wape([100, 100], [90, 110]), 6) == 0.1
    assert round(rmse([1, 3], [1, 1]), 6) == 1.414214


def test_auc_metrics_perfect_order():
    y = [0, 0, 1, 1]
    s = [0.1, 0.2, 0.8, 0.9]
    assert roc_auc(y, s) == 1.0
    assert average_precision(y, s) == 1.0


def test_dual_delta_against_best_single_contour():
    y = [0, 1, 0, 1, 0, 1]
    r = [0.1, 0.6, 0.2, 0.55, 0.3, 0.65]
    p = [0.2, 0.55, 0.4, 0.8, 0.1, 0.7]
    d = [0.1, 0.7, 0.2, 0.9, 0.05, 0.85]
    result = compare_dual_value(y, r, p, d)
    assert result.delta_roc_auc >= 0
    assert result.delta_pr_auc >= 0


def test_lead_time_and_false_alarm_budget():
    assert lead_time_days("2024-04-15", "2024-07-01") == 77
    records = [
        {"entity": "A", "year": 2024, "alarm": 1, "truth": 0},
        {"entity": "A", "year": 2024, "alarm": 0, "truth": 0},
        {"entity": "B", "year": 2024, "alarm": 0, "truth": 1},
    ]
    assert false_alarms_per_entity_year(records) == 0.5
