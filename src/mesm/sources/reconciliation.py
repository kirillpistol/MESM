from __future__ import annotations

from datetime import date
from math import isfinite

import pandas as pd


def reconcile(left: pd.DataFrame, right: pd.DataFrame, *, as_of: date,
              threshold: float = .7, min_periods: int = 8) -> dict:
    """Сверка только опубликованных наблюдений, без интерполяции годовых рядов."""
    if not 0 <= threshold <= 1 or min_periods < 3:
        raise ValueError('Некорректные параметры сверки')
    required = {'period', 'oktmo', 'value', 'available_at', 'frequency', 'unit', 'measure'}
    cleaned = []
    for frame in (left, right):
        if not required <= set(frame):
            raise ValueError('Не хватает полей сопоставимости')
        frame = frame.copy()
        frame['available_at'] = pd.to_datetime(frame['available_at'], errors='raise')
        frame = frame[frame['available_at'] <= pd.Timestamp(as_of)]
        frame['value'] = pd.to_numeric(frame['value'], errors='raise')
        if not all(isfinite(v) for v in frame['value']):
            raise ValueError('Неконечные значения ряда')
        if frame.duplicated(['period', 'oktmo']).any():
            raise ValueError('Неоднозначные версии или дубликаты периодов')
        cleaned.append(frame)
    left, right = cleaned
    for field in ['frequency', 'unit', 'measure']:
        values = set(left[field]) | set(right[field])
        if len(values) > 1:
            raise ValueError(f'Несопоставимые {field}: нужна явная трансформация')
    joined = left.merge(right, on=['period', 'oktmo'], suffixes=('_left', '_right'))
    reports = []
    for oktmo, group in joined.groupby('oktmo'):
        n = len(group)
        correlation = None
        if n >= min_periods and group.value_left.nunique() > 1 and group.value_right.nunique() > 1:
            correlation = float(group.value_left.corr(group.value_right))
        status = 'insufficient' if correlation is None else 'consistent' if correlation >= threshold else 'inconsistent'
        reports.append(dict(oktmo=oktmo, n=n, correlation=correlation, status=status))
    return dict(as_of=str(as_of), threshold=threshold, min_periods=min_periods,
                overlap_rows=len(joined), municipalities=reports,
                detector_ready=False, limitation='Корреляция не доказывает опережение или эффект внедрения')
