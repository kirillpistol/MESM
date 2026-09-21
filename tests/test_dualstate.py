from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mesm.models.dualstate import (
    dual_fusion_score,
    dual_state,
    dual_state_code,
    probability_state,
)


def test_matrix():
    assert dual_state(False, False) == "NORMAL"
    assert dual_state(False, True) == "EARLY_WARNING"
    assert dual_state(True, False) == "FISCAL_DIVERGENCE"
    assert dual_state(True, True) == "SYSTEMIC_STRESS"


def test_fusion_code_is_explicit():
    assert dual_state_code(False, False) == 0
    assert dual_state_code(False, True) == 1
    assert dual_state_code(True, False) == 2
    assert dual_state_code(True, True) == 3


def test_dual_fusion_score_noisy_or():
    assert dual_fusion_score(0.0, 0.0) == 0.0
    assert dual_fusion_score(1.0, 0.2) == 1.0
    assert abs(dual_fusion_score(0.4, 0.5) - 0.7) < 1e-12


def test_dual_fusion_score_rejects_invalid_range():
    try:
        dual_fusion_score(1.1, 0.2)
    except ValueError:
        pass
    else:
        raise AssertionError("ожидался ValueError")


def test_uncertain_margin():
    assert probability_state({"NORMAL": 0.43, "WARNING": 0.41, "STRESS": 0.16}) == "UNCERTAIN"
