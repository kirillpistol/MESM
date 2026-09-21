import pandas as pd

from mesm.features.competition_matrix import build_consumption_model_matrix


def test_model_matrix_uses_only_past_values_for_features():
    frame = pd.DataFrame({
        "oktmo": ["71876000"] * 14,
        "period_start": pd.date_range("2023-01-01", periods=14, freq="MS"),
        "category_code": ["ALL"] * 14,
        "spending_nominal": [100.0 + i for i in range(14)],
        "model_eligible": [True] * 14,
        "identity_status": ["OKTMO_RESOLVED"] * 14,
    })
    matrix = build_consumption_model_matrix(frame, category_codes=["ALL"])

    row = matrix.iloc[12]
    assert row["target"] == 112.0
    assert row["lag_1"] == 111.0
    assert row["lag_12"] == 100.0
    assert row["rolling_mean_3"] == (109.0 + 110.0 + 111.0) / 3
    assert row["history_points"] == 12


def test_model_matrix_rejects_duplicate_period_keys():
    frame = pd.DataFrame({
        "oktmo": ["71876000", "71876000"],
        "period_start": ["2024-01-01", "2024-01-01"],
        "category_code": ["ALL", "ALL"],
        "spending_nominal": [100.0, 101.0],
    })
    try:
        build_consumption_model_matrix(frame)
    except ValueError as exc:
        assert "unique" in str(exc).lower()
    else:
        raise AssertionError("duplicate key must be rejected")
