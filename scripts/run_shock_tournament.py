from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from mesm.evaluation.shock_benchmark import run_shock_benchmark

ROOT=Path(__file__).resolve().parents[1]
CFG=ROOT/"config"/"competition_shock.yaml"
OUT=ROOT/"data"/"reports"/"competition"/"shock_benchmark_dev.csv"
CAL=ROOT/"data"/"reports"/"competition"/"shock_calibration_dev.csv"


def main() -> None:
    cfg=yaml.safe_load(CFG.read_text(encoding="utf-8"))
    source=ROOT/cfg["source"]["predictions"]
    frame=pd.read_csv(source,encoding="utf-8-sig")
    residuals=pd.to_numeric(frame[cfg["source"]["residual_column"]],errors="raise").astype(float).tolist()
    sim=cfg["simulation"]
    calibration,results=run_shock_benchmark(
        residuals,
        shock_sigmas=tuple(float(v) for v in sim["shock_sigmas"]),
        durations=tuple(int(v) for v in sim["durations"]),
        directions=tuple(int(v) for v in sim["directions"]),
        path_length=int(sim["path_length"]),
        warmup=int(sim["warmup"]),
        runs=int(sim["runs"]),
        target_fpr=float(sim["target_null_path_fpr"]),
        seed=int(sim["seed"]),
    )
    OUT.parent.mkdir(parents=True,exist_ok=True)
    calibration.to_csv(CAL,index=False,encoding="utf-8-sig")
    results.to_csv(OUT,index=False,encoding="utf-8-sig")
    print("SHOCK_CALIBRATION")
    print(calibration.to_string(index=False))
    print("SHOCK_SUMMARY")
    summary=(
        results.groupby(["detector","event_type"],as_index=False)
        .agg(
            mean_detection_rate=("detection_rate","mean"),
            mean_false_early_rate=("false_early_rate","mean"),
            median_delay=("median_delay_periods","median"),
            median_localization_error=("median_localization_error","median"),
        )
    )
    print(summary.to_string(index=False))


if __name__=="__main__":
    main()
