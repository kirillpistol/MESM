#!/usr/bin/env python3
"""Воспроизводимый synthetic power benchmark для CUSUM development setup."""
from __future__ import annotations

import csv
from pathlib import Path
from random import Random

from mesm.simulation.power import calibrate_cusum_threshold, estimate_cusum_power

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "simulation" / "power_results_dev.csv"


def main() -> None:
    rng = Random(20260920)
    baseline = [rng.gauss(0.0, 1.0) for _ in range(60)]

    threshold, null_fpr = calibrate_cusum_threshold(
        baseline,
        target_fpr=0.10,
        runs=5000,
    )
    results = estimate_cusum_power(
        baseline,
        shock_sigmas=(0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0),
        durations=(1, 2, 3, 6),
        runs=5000,
        threshold=threshold,
        seed=42,
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "shock_sigma",
            "duration_periods",
            "runs",
            "detection_power",
            "false_early_rate",
            "median_delay",
            "calibrated_threshold",
            "null_path_fpr",
        ])
        for row in results:
            writer.writerow([
                row.shock_sigma,
                row.duration,
                row.runs,
                f"{row.detection_rate:.3f}",
                f"{row.false_early_rate:.3f}",
                row.median_delay,
                threshold,
                f"{null_fpr:.4f}",
            ])

    print(f"threshold={threshold:.1f}, null_path_fpr={null_fpr:.4f}")
    print(f"written: {OUT}")


if __name__ == "__main__":
    main()
