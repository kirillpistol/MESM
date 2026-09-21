from __future__ import annotations

from datetime import date
from math import sqrt


def wape(y_true: list[float], y_pred: list[float]) -> float:
    denom = sum(abs(v) for v in y_true)
    if denom == 0:
        raise ValueError("знаменатель WAPE равен нулю")
    return sum(abs(a - b) for a, b in zip(y_true, y_pred)) / denom


def rmse(y_true: list[float], y_pred: list[float]) -> float:
    if not y_true or len(y_true) != len(y_pred):
        raise ValueError("векторы должны быть одинаковой ненулевой длины")
    return sqrt(sum((a - b) ** 2 for a, b in zip(y_true, y_pred)) / len(y_true))


def mase(y_true: list[float], y_pred: list[float], insample: list[float], seasonality: int = 1) -> float:
    if len(insample) <= seasonality:
        raise ValueError("для MASE недостаточно истории insample")
    scale = sum(abs(insample[i] - insample[i - seasonality]) for i in range(seasonality, len(insample))) / (len(insample) - seasonality)
    if scale == 0:
        raise ValueError("масштаб MASE равен нулю")
    mae = sum(abs(a - b) for a, b in zip(y_true, y_pred)) / len(y_true)
    return mae / scale


def precision_recall(y_true: list[int], y_pred: list[int]) -> tuple[float, float]:
    tp = sum(1 for y, p in zip(y_true, y_pred) if y == 1 and p == 1)
    fp = sum(1 for y, p in zip(y_true, y_pred) if y == 0 and p == 1)
    fn = sum(1 for y, p in zip(y_true, y_pred) if y == 1 and p == 0)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return precision, recall


def roc_auc(y_true: list[int], scores: list[float]) -> float:
    """ROC-AUC через средние ранги, включая одинаковые значения score."""
    if len(y_true) != len(scores) or not y_true:
        raise ValueError("векторы должны быть одинаковой ненулевой длины")
    n_pos = sum(y_true)
    n_neg = len(y_true) - n_pos
    if n_pos == 0 or n_neg == 0:
        raise ValueError("для ROC-AUC нужны оба класса")

    indexed = sorted(enumerate(scores), key=lambda x: x[1])
    ranks = [0.0] * len(scores)
    i = 0
    while i < len(indexed):
        j = i + 1
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        avg_rank = ((i + 1) + j) / 2.0
        for k in range(i, j):
            ranks[indexed[k][0]] = avg_rank
        i = j
    sum_pos_ranks = sum(rank for rank, y in zip(ranks, y_true) if y == 1)
    return (sum_pos_ranks - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def average_precision(y_true: list[int], scores: list[float]) -> float:
    """Average Precision как сводная PR-AUC метрика для редких событий."""
    if len(y_true) != len(scores) or not y_true:
        raise ValueError("векторы должны быть одинаковой ненулевой длины")
    positives = sum(y_true)
    if positives == 0:
        raise ValueError("для Average Precision нужен хотя бы один положительный класс")
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    tp = 0
    precision_sum = 0.0
    for rank, idx in enumerate(order, start=1):
        if y_true[idx] == 1:
            tp += 1
            precision_sum += tp / rank
    return precision_sum / positives


def lead_time_days(signal_date: str, confirmation_date: str) -> int:
    s = date.fromisoformat(signal_date[:10])
    c = date.fromisoformat(confirmation_date[:10])
    return (c - s).days


def false_alarms_per_entity_year(records: list[dict]) -> float:
    """Считаем ложные тревоги на одну пару муниципалитет-год."""
    units = {(r["entity"], r["year"]) for r in records}
    if not units:
        return 0.0
    fp = sum(1 for r in records if int(r["alarm"]) == 1 and int(r["truth"]) == 0)
    return fp / len(units)
