from __future__ import annotations

from datetime import date, datetime


def _as_date(value: str | date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value[:10])


def validate_as_of(records: list[dict], forecast_date: str | date | datetime, publication_field: str = "publication_date") -> list[dict]:
    """Возвращаем записи, которые на дату прогноза еще не были опубликованы."""
    cutoff = _as_date(forecast_date)
    violations = []
    for row in records:
        value = row.get(publication_field)
        if value in (None, ""):
            continue
        if _as_date(value) > cutoff:
            violations.append(row)
    return violations


def assert_as_of(records: list[dict], forecast_date: str | date | datetime, publication_field: str = "publication_date") -> None:
    violations = validate_as_of(records, forecast_date, publication_field)
    if violations:
        raise ValueError(f"временная утечка: {len(violations)} записей опубликованы позже даты прогноза")
