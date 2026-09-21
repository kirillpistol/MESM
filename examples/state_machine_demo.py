from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mesm.models.state_machine import HysteresisStateMachine
from mesm.models.dualstate import dual_state

scores = [0.4, 1.2, 2.2, 2.4, 2.6, 1.6, 0.8, 0.7]
confirmations = [0, 0, 0, 1, 2, 2, 0, 0]
sm = HysteresisStateMachine()
print("score\tcontour_state\tdual_with_normal_reference")
for score, conf in zip(scores, confirmations):
    update = sm.update(score, confirmations=conf)
    print(f"{score:.1f}\t{update.state.value}\t{dual_state('NORMAL', update.state)}")
