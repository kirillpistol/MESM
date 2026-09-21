import pandas as pd

from dashboard.charts import (
    bo_history_chart,
    budget_waterfall_chart,
    expenditure_structure_chart,
    reference_trend_chart,
    shock_monitor_chart,
    model_tournament_chart,
    competition_forecast_chart,
    shock_benchmark_chart,
    shock_calibration_chart,
)


def test_visual_charts_build_without_external_data():
    reference = pd.DataFrame({
        "year": [2023, 2024, 2025],
        "income_plan_deviation": [0.95, 1.01, 1.03],
        "program_expense_share": [0.80, 0.82, 0.84],
        "debt_load": [0.10, 0.12, 0.15],
    })
    assert len(reference_trend_chart(reference).data) == 3
    assert len(budget_waterfall_chart(20_000_000, 28_000_000, 51_000_000).data) == 1

    expense = pd.DataFrame({
        "group": ["Education", "Economy"],
        "amount": [28_000_000, 9_000_000],
        "share": [0.75, 0.25],
    })
    assert len(expenditure_structure_chart(expense).data) == 1

    demo = pd.DataFrame({
        "period": [1, 2, 3],
        "residual": [0.1, -0.3, 2.1],
        "z_score": [0.1, -0.3, 2.2],
        "cusum_alarm": [False, False, True],
        "shock_window": [False, True, True],
    })
    assert len(shock_monitor_chart(demo).data) >= 4

    bo = pd.DataFrame({"year": [2021, 2023], "bo_actual": [0.8, 0.9], "bo_calculated": [0.82, 0.88]})
    assert len(bo_history_chart(bo).data) == 2


def test_model_tournament_chart_builds():
    tournament = pd.DataFrame({
        "model": ["Prophet", "CatBoost HMAO Growth"],
        "mae": [2404.56, 2007.82],
    })
    assert len(model_tournament_chart(tournament).data) == 1


def test_competition_visuals_build():
    prophet = pd.DataFrame({
        "period": ["2024-01-01", "2024-02-01"],
        "actual": [100.0, 110.0],
        "prophet": [102.0, 108.0],
    })
    grow = pd.DataFrame({
        "period": ["2024-01-01", "2024-02-01"],
        "actual": [100.0, 110.0],
        "grow_prediction": [101.0, 109.0],
    })
    assert len(competition_forecast_chart(prophet, grow).data) == 3

    summary = pd.DataFrame({
        "detector": ["CUSUM", "PAGE_HINKLEY", "PELT"],
        "event_type": ["REGIME_SHIFT"] * 3,
        "detection_rate": [0.22, 0.32, 0.38],
    })
    assert len(shock_benchmark_chart(summary).data) == 3

    calibration = pd.DataFrame({
        "detector": ["CUSUM", "PAGE_HINKLEY", "PELT"],
        "null_path_fpr": [0.08, 0.03, 0.08],
    })
    assert len(shock_calibration_chart(calibration).data) == 1
