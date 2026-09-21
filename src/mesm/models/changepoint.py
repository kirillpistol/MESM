"""Небольшой набор детекторов структурных изменений.

CUSUM работает без дополнительных зависимостей. PELT подключается отдельно, чтобы
мы не подменяли один алгоритм другим незаметно для пользователя.
"""
from __future__ import annotations

from statistics import mean, pstdev


def cusum_flags(values: list[float], threshold: float = 5.0, drift: float = 0.5, warmup: int = 12) -> list[bool]:
    if warmup < 2 or len(values) <= warmup:
        return [False] * len(values)
    baseline = values[:warmup]
    mu = mean(baseline)
    sigma = pstdev(baseline)
    if sigma == 0:
        sigma = 1.0
    pos = neg = 0.0
    flags = [False] * len(values)
    for i, value in enumerate(values):
        if i < warmup:
            continue
        z = (value - mu) / sigma
        pos = max(0.0, pos + z - drift)
        neg = min(0.0, neg + z + drift)
        if pos > threshold or abs(neg) > threshold:
            flags[i] = True
    return flags


def first_cusum_alarm(values: list[float], threshold: float = 5.0, drift: float = 0.5, warmup: int = 12) -> int | None:
    flags = cusum_flags(values, threshold=threshold, drift=drift, warmup=warmup)
    return next((i for i, flag in enumerate(flags) if flag), None)


def pelt_breakpoints(values: list[float], penalty: float = 3.0) -> list[int]:
    """Запускаем PELT только при установленном необязательном пакете ruptures."""
    try:
        import numpy as np
        import ruptures as rpt
    except ImportError as exc:  # pragma: no cover — необязательная зависимость проверяется отдельным тестом
        raise RuntimeError("Для PELT установите дополнительную зависимость: pip install mesm[changepoint]") from exc
    signal = np.asarray(values, dtype=float).reshape(-1, 1)
    return list(rpt.Pelt(model="rbf").fit(signal).predict(pen=penalty))


def page_hinkley_flags(
    values: list[float],
    *,
    threshold: float = 8.0,
    delta: float = 0.05,
    warmup: int = 12,
) -> list[bool]:
    """Two-sided Page-Hinkley online detector.

    Baseline mean is updated online after warmup. The detector is used only for
    development comparison; thresholds must be calibrated on a null path before
    interpreting alarms.
    """
    if warmup < 2 or len(values) <= warmup:
        return [False] * len(values)

    flags=[False]*len(values)
    mean_value=sum(values[:warmup])/warmup
    pos=neg=0.0
    pos_min=neg_min=0.0

    for i,value in enumerate(values):
        if i < warmup:
            continue
        n=i+1
        mean_value += (value-mean_value)/n

        pos += value-mean_value-delta
        pos_min=min(pos_min,pos)
        neg += -value+mean_value-delta
        neg_min=min(neg_min,neg)

        if (pos-pos_min)>threshold or (neg-neg_min)>threshold:
            flags[i]=True
    return flags


def first_page_hinkley_alarm(
    values: list[float],
    *,
    threshold: float = 8.0,
    delta: float = 0.05,
    warmup: int = 12,
) -> int | None:
    flags=page_hinkley_flags(values,threshold=threshold,delta=delta,warmup=warmup)
    return next((i for i,flag in enumerate(flags) if flag),None)
