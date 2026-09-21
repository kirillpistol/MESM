from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pytest
from mesm.data.ytd import ytd_to_flow
from mesm.validation.temporal import assert_as_of, validate_as_of


def test_as_of_detects_future_publication():
    rows = [{"publication_date": "2024-07-10"}, {"publication_date": "2024-06-20"}]
    violations = validate_as_of(rows, "2024-07-01")
    assert len(violations) == 1
    with pytest.raises(ValueError):
        assert_as_of(rows, "2024-07-01")


def test_ytd_conversion_only_when_compatible():
    base = {
        "municipality_id": "71876000",
        "indicator": "revenue",
        "method_version": "v1",
        "classification_version": "2024",
        "scope": "consolidated",
        "unit": "thousand_rub",
    }
    rows = [
        {**base, "period_end": "2024-06-30", "value": 100.0},
        {**base, "period_end": "2024-07-31", "value": 130.0},
        {**base, "period_end": "2024-08-31", "value": 170.0, "classification_version": "2025"},
    ]
    out = ytd_to_flow(rows)
    assert out[0]["flow_derived"] is None
    assert out[1]["flow_derived"] == 30.0
    assert out[2]["flow_derived"] is None
    assert out[2]["flow_derivation_status"] == "incompatible_snapshot"
