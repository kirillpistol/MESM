from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mesm.features.fiscal import (
    revision_rate, execution_rate, coverage_gap,
    official_i13, official_i15, official_i26,
)

def test_revision_rate():
    assert revision_rate(100.0, 110.0) == 0.1

def test_execution_rate():
    assert execution_rate(200.0, 190.0) == 0.95

def test_coverage_gap():
    assert round(coverage_gap(98.0, 100.0), 6) == -0.02

def test_surgut_public_2025_i13():
    value = official_i13(19_230_756.2, 1_258_440.4, 21_628_115.2, 1_126_274.6)
    assert round(value, 6) == 0.110555

def test_surgut_public_2025_i15():
    value = official_i15(45_970_377.8, 49_453_472.8)
    assert round(value, 6) == 0.929568

def test_surgut_public_2025_i26():
    value = official_i26(5_713.5, 49_453_472.8)
    assert round(value, 9) == 0.000115533
