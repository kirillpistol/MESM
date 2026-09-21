"""Controlled structural-change benchmark for MESM detectors."""
from __future__ import annotations

from dataclasses import dataclass
from random import Random
from statistics import median

import pandas as pd

from mesm.models.changepoint import (
    first_cusum_alarm,
    first_page_hinkley_alarm,
    pelt_breakpoints,
)


@dataclass(frozen=True)
class DetectorCalibration:
    detector: str
    parameter: float
    null_path_fpr: float
    target_met: bool


def robust_standardize(values: list[float]) -> list[float]:
    if not values:
        raise ValueError("Residual pool is empty.")
    med = median(values)
    abs_dev = [abs(value - med) for value in values]
    mad = median(abs_dev)
    scale = 1.4826 * mad
    if scale == 0:
        mean_value = sum(values) / len(values)
        variance = sum((value - mean_value) ** 2 for value in values) / len(values)
        scale = variance**0.5 or 1.0
    return [(value - med) / scale for value in values]


def _bootstrap_path(pool: list[float], length: int, rng: Random) -> list[float]:
    return [rng.choice(pool) for _ in range(length)]


def _inject(
    path: list[float],
    start: int,
    duration: int,
    magnitude: float,
) -> list[float]:
    out = list(path)
    for index in range(start, min(start + duration, len(out))):
        out[index] += magnitude
    return out


def _calibrate_online(
    pool: list[float],
    *,
    detector: str,
    candidates: tuple[float, ...],
    target_fpr: float,
    path_length: int,
    warmup: int,
    runs: int,
    seed: int,
) -> DetectorCalibration:
    rng = Random(seed)
    last_parameter = float(candidates[-1])
    last_fpr = 1.0

    for parameter in candidates:
        alarms = 0
        for _ in range(runs):
            path = _bootstrap_path(pool, path_length, rng)
            if detector == "CUSUM":
                alarm = first_cusum_alarm(
                    path,
                    threshold=parameter,
                    drift=0.5,
                    warmup=warmup,
                )
            elif detector == "PAGE_HINKLEY":
                alarm = first_page_hinkley_alarm(
                    path,
                    threshold=parameter,
                    delta=0.05,
                    warmup=warmup,
                )
            else:
                raise ValueError(detector)
            alarms += int(alarm is not None)

        fpr = alarms / runs
        last_parameter = float(parameter)
        last_fpr = float(fpr)
        if fpr <= target_fpr:
            return DetectorCalibration(
                detector=detector,
                parameter=float(parameter),
                null_path_fpr=float(fpr),
                target_met=True,
            )

    return DetectorCalibration(
        detector=detector,
        parameter=last_parameter,
        null_path_fpr=last_fpr,
        target_met=False,
    )


def _calibrate_pelt(
    pool: list[float],
    *,
    candidates: tuple[float, ...],
    target_fpr: float,
    path_length: int,
    runs: int,
    seed: int,
) -> DetectorCalibration:
    rng = Random(seed)
    last_penalty = float(candidates[-1])
    last_fpr = 1.0

    for penalty in candidates:
        false_paths = 0
        for _ in range(runs):
            path = _bootstrap_path(pool, path_length, rng)
            breaks = [
                point
                for point in pelt_breakpoints(path, penalty=penalty)
                if point < len(path)
            ]
            false_paths += int(bool(breaks))

        fpr = false_paths / runs
        last_penalty = float(penalty)
        last_fpr = float(fpr)
        if fpr <= target_fpr:
            return DetectorCalibration(
                detector="PELT",
                parameter=float(penalty),
                null_path_fpr=float(fpr),
                target_met=True,
            )

    return DetectorCalibration(
        detector="PELT",
        parameter=last_penalty,
        null_path_fpr=last_fpr,
        target_met=False,
    )


def run_shock_benchmark(
    residuals: list[float],
    *,
    shock_sigmas: tuple[float, ...] = (1.0, 1.5, 2.0, 3.0),
    durations: tuple[int, ...] = (1, 3, 6, 12),
    directions: tuple[int, ...] = (-1, 1),
    path_length: int = 60,
    warmup: int = 12,
    runs: int = 300,
    target_fpr: float = 0.10,
    seed: int = 20260921,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if path_length <= warmup + max(durations) + 3:
        raise ValueError("path_length is too short for selected benchmark.")
    if any(direction not in (-1, 1) for direction in directions):
        raise ValueError("directions must contain only -1 or 1.")

    pool = robust_standardize(residuals)
    calibrations = [
        _calibrate_online(
            pool,
            detector="CUSUM",
            candidates=(3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 12.0, 15.0, 20.0, 30.0),
            target_fpr=target_fpr,
            path_length=path_length,
            warmup=warmup,
            runs=runs,
            seed=seed,
        ),
        _calibrate_online(
            pool,
            detector="PAGE_HINKLEY",
            candidates=(3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0, 20.0, 30.0),
            target_fpr=target_fpr,
            path_length=path_length,
            warmup=warmup,
            runs=runs,
            seed=seed + 1,
        ),
        _calibrate_pelt(
            pool,
            candidates=(1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0, 20.0, 30.0, 50.0, 100.0),
            target_fpr=target_fpr,
            path_length=path_length,
            runs=max(100, runs // 2),
            seed=seed + 2,
        ),
    ]
    calibration_frame = pd.DataFrame([calibration.__dict__ for calibration in calibrations])

    rng = Random(seed + 10)
    rows: list[dict[str, object]] = []
    for magnitude in shock_sigmas:
        for duration in durations:
            event_type = "TRANSIENT_SHOCK" if duration <= 3 else "REGIME_SHIFT"
            for direction in directions:
                for calibration in calibrations:
                    detected = 0
                    false_early = 0
                    delays: list[int] = []
                    localization: list[int] = []

                    for _ in range(runs):
                        null = _bootstrap_path(pool, path_length, rng)
                        start = rng.randint(
                            warmup + 1,
                            path_length - duration - 3,
                        )
                        path = _inject(
                            null,
                            start,
                            duration,
                            direction * magnitude,
                        )

                        if calibration.detector == "CUSUM":
                            alarm = first_cusum_alarm(
                                path,
                                threshold=calibration.parameter,
                                drift=0.5,
                                warmup=warmup,
                            )
                            if alarm is not None and alarm < start:
                                false_early += 1
                            if alarm is not None and start <= alarm <= start + duration + 2:
                                detected += 1
                                delays.append(alarm - start)

                        elif calibration.detector == "PAGE_HINKLEY":
                            alarm = first_page_hinkley_alarm(
                                path,
                                threshold=calibration.parameter,
                                delta=0.05,
                                warmup=warmup,
                            )
                            if alarm is not None and alarm < start:
                                false_early += 1
                            if alarm is not None and start <= alarm <= start + duration + 2:
                                detected += 1
                                delays.append(alarm - start)

                        else:
                            breaks = [
                                point
                                for point in pelt_breakpoints(
                                    path,
                                    penalty=calibration.parameter,
                                )
                                if point < len(path)
                            ]
                            if breaks:
                                nearest = min(abs(point - start) for point in breaks)
                                localization.append(nearest)
                                if nearest <= 2:
                                    detected += 1

                    rows.append(
                        {
                            "detector": calibration.detector,
                            "event_type": event_type,
                            "direction": "DOWN" if direction < 0 else "UP",
                            "shock_sigma": magnitude,
                            "duration_periods": duration,
                            "runs": runs,
                            "detection_rate": detected / runs,
                            "false_early_rate": (
                                false_early / runs
                                if calibration.detector != "PELT"
                                else None
                            ),
                            "median_delay_periods": (
                                median(delays) if delays else None
                            ),
                            "median_localization_error": (
                                median(localization) if localization else None
                            ),
                            "calibrated_parameter": calibration.parameter,
                            "null_path_fpr": calibration.null_path_fpr,
                            "calibration_target_met": calibration.target_met,
                        }
                    )

    return calibration_frame, pd.DataFrame(rows)
