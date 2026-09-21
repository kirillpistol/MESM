from __future__ import annotations

from dataclasses import dataclass
from random import Random
from statistics import median, pstdev

from mesm.models.changepoint import first_cusum_alarm


@dataclass(frozen=True)
class PowerResult:
    shock_sigma: float
    duration: int
    runs: int
    detection_rate: float
    false_early_rate: float
    median_delay: float | None


def inject_shock(series: list[float], start: int, duration: int, magnitude: float) -> list[float]:
    out = list(series)
    for i in range(start, min(start + duration, len(out))):
        out[i] += magnitude
    return out


def estimate_null_alarm_rate(
    baseline_residuals: list[float],
    *,
    threshold: float,
    runs: int = 1000,
    warmup: int = 12,
    drift: float = 0.5,
    seed: int = 123,
) -> float:
    """Path-level FPR на bootstrap null-paths."""
    if len(baseline_residuals) <= warmup:
        raise ValueError("недостаточно baseline residuals")
    rng = Random(seed)
    alarms = 0
    for _ in range(runs):
        sample = [rng.choice(baseline_residuals) for _ in baseline_residuals]
        if first_cusum_alarm(sample, threshold=threshold, drift=drift, warmup=warmup) is not None:
            alarms += 1
    return alarms / runs


def calibrate_cusum_threshold(
    baseline_residuals: list[float],
    *,
    target_fpr: float = 0.10,
    candidates: tuple[float, ...] = tuple(float(v) for v in range(4, 16)),
    runs: int = 2000,
    warmup: int = 12,
    drift: float = 0.5,
    seed: int = 123,
) -> tuple[float, float]:
    """Минимальный threshold, который укладывается в target simulation FPR."""
    if not 0.0 < target_fpr < 1.0:
        raise ValueError("target_fpr должен быть между 0 и 1")
    for threshold in candidates:
        fpr = estimate_null_alarm_rate(
            baseline_residuals,
            threshold=threshold,
            runs=runs,
            warmup=warmup,
            drift=drift,
            seed=seed,
        )
        if fpr <= target_fpr:
            return threshold, fpr
    raise ValueError("ни один candidate threshold не достиг target_fpr")


def estimate_cusum_power(
    baseline_residuals: list[float],
    shock_sigmas: tuple[float, ...] = (0.5, 1.0, 1.5, 2.0),
    durations: tuple[int, ...] = (1, 2, 3, 6),
    runs: int = 200,
    warmup: int = 12,
    threshold: float = 5.0,
    drift: float = 0.5,
    seed: int = 42,
) -> list[PowerResult]:
    if len(baseline_residuals) < warmup + max(durations) + 3:
        raise ValueError("недостаточно длинный baseline для выбранной симуляции")
    rng = Random(seed)
    sigma = pstdev(baseline_residuals) or 1.0
    results: list[PowerResult] = []

    for shock_sigma in shock_sigmas:
        for duration in durations:
            detected = 0
            early = 0
            delays: list[int] = []
            for _ in range(runs):
                sample = [rng.choice(baseline_residuals) for _ in baseline_residuals]
                max_start = len(sample) - duration - 1
                start = rng.randint(warmup + 1, max_start)
                shocked = inject_shock(sample, start, duration, shock_sigma * sigma)
                alarm = first_cusum_alarm(
                    shocked,
                    threshold=threshold,
                    drift=drift,
                    warmup=warmup,
                )
                if alarm is not None and alarm < start:
                    early += 1
                if alarm is not None and start <= alarm <= start + duration + 2:
                    detected += 1
                    delays.append(alarm - start)

            results.append(
                PowerResult(
                    shock_sigma=shock_sigma,
                    duration=duration,
                    runs=runs,
                    detection_rate=detected / runs,
                    false_early_rate=early / runs,
                    median_delay=median(delays) if delays else None,
                )
            )
    return results
