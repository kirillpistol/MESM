import pytest
from mesm.models.state_machine import HysteresisStateMachine, StateMachineConfig


@pytest.mark.parametrize('score', [float('nan'), float('inf'), -1])
def test_invalid_score_does_not_change_state(score):
    machine = HysteresisStateMachine()
    before = (machine.state, machine.above_streak, machine.below_streak)
    with pytest.raises(ValueError): machine.update(score)
    assert before == (machine.state, machine.above_streak, machine.below_streak)


@pytest.mark.parametrize('confirmations', [float('nan'), float('inf'), -.5, 1.5])
def test_invalid_confirmation_rejected(confirmations):
    with pytest.raises(ValueError): HysteresisStateMachine().update(3, confirmations)


def test_infinite_threshold_rejected():
    with pytest.raises(ValueError): StateMachineConfig(on_threshold=float('inf'))
