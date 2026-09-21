from __future__ import annotations

from datetime import date

DEFAULT_COMPATIBILITY_KEYS = (
    "municipality_id",
    "indicator",
    "method_version",
    "classification_version",
    "scope",
    "unit",
)


def _year(value: str) -> int:
    return date.fromisoformat(value[:10]).year


def ytd_to_flow(records: list[dict], value_field: str = "value", compatibility_keys: tuple[str, ...] = DEFAULT_COMPATIBILITY_KEYS) -> list[dict]:
    """Переводим совместимые накопительные срезы YTD в поток за период.

    Первый срез года остается без производного потока. Если методика, классификация
    или единицы отличаются, разность не считаем.
    """
    rows = sorted(records, key=lambda r: r["period_end"])
    output: list[dict] = []
    previous: dict | None = None
    for row in rows:
        result = dict(row)
        result["flow_derived"] = None
        result["flow_derivation_status"] = "no_prior_snapshot"
        if previous is not None and _year(previous["period_end"]) == _year(row["period_end"]):
            compatible = all(previous.get(k) == row.get(k) for k in compatibility_keys)
            if compatible:
                result["flow_derived"] = float(row[value_field]) - float(previous[value_field])
                result["flow_derivation_status"] = "derived"
            else:
                result["flow_derivation_status"] = "incompatible_snapshot"
        output.append(result)
        previous = row
    return output
