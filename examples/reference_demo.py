from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mesm.features.fiscal import official_i13, official_i15, official_i26
from mesm.models.dualstate import dual_state

# Публичные показатели Сургута за 2025 год из официальной таблицы оценки качества.
i13 = official_i13(
    initial_tax=19_230_756.2,
    initial_nontax=1_258_440.4,
    actual_tax=21_628_115.2,
    actual_nontax=1_126_274.6,
)
i15 = official_i15(45_970_377.8, 49_453_472.8)
i26 = official_i26(5_713.5, 49_453_472.8)

print({
    "municipality": "Сургут",
    "year": 2025,
    "official_i13": i13,
    "official_i15": i15,
    "official_i26": i26,
    "dual_state_example": dual_state(False, True),
})
