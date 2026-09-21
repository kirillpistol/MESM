from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from mesm.evaluation.competition_forecast import evaluate_target_baselines

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "processed" / "sberindex_spending_monthly.csv"
DEFAULT_METRICS = ROOT / "data" / "reports" / "surgut_baseline_metrics.csv"
DEFAULT_FORECASTS = ROOT / "data" / "reports" / "surgut_baseline_forecasts.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run leakage-safe 2024 baseline tournament for Surgut.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--category", default="ALL")
    parser.add_argument("--target-oktmo", default="71876000")
    parser.add_argument("--holdout-year", type=int, default=2024)
    parser.add_argument("--metrics-output", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--forecasts-output", type=Path, default=DEFAULT_FORECASTS)
    args = parser.parse_args()

    frame = pd.read_csv(args.input, dtype={"oktmo": str}, encoding="utf-8-sig")
    forecasts, metrics = evaluate_target_baselines(
        frame,
        target_oktmo=args.target_oktmo,
        category_code=args.category,
        holdout_year=args.holdout_year,
    )

    args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
    args.forecasts_output.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(args.metrics_output, index=False, encoding="utf-8-sig")
    forecasts.to_csv(args.forecasts_output, index=False, encoding="utf-8-sig")

    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
