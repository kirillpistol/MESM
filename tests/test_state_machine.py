from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mesm.models.state_machine import ContourState, HysteresisStateMachine, StateMachineConfig
from mesm.models.dualstate import dual_state


def test_hysteresis_activation_and_release():
    sm = HysteresisStateMachine(StateMachineConfig(on_threshold=2, off_threshold=1, k_on=2, k_off=2, break_persistence=3, min_confirmations=2))
    assert sm.update(2.2).state == ContourState.OBSERVE
    assert sm.update(2.3).state == ContourState.WARNING
    assert sm.update(1.5).state == ContourState.WARNING  # внутри зоны гистерезиса сохраняем тревогу
    assert sm.update(0.8).state == ContourState.WARNING
    assert sm.update(0.7).state == ContourState.NORMAL


def test_break_requires_confirmation():
    sm = HysteresisStateMachine(StateMachineConfig(on_threshold=2, off_threshold=1, k_on=2, k_off=2, break_persistence=3, min_confirmations=2))
    sm.update(2.2, confirmations=1)
    sm.update(2.3, confirmations=1)
    assert sm.update(2.5, confirmations=1).state == ContourState.WARNING
    assert sm.update(2.6, confirmations=2).state == ContourState.BREAK_CONFIRMED


def test_dual_state_accepts_contour_states():
    assert dual_state(ContourState.NORMAL, ContourState.WARNING) == "EARLY_WARNING"
    assert dual_state(ContourState.WARNING, ContourState.WARNING) == "SYSTEMIC_STRESS"
