"""Parser for the official Rosstat OKTMO open-data export."""
from __future__ import annotations

from io import StringIO
from pathlib import Path
import re

import pandas as pd

from mesm.geo.oktmo import normalize_oktmo


FIELD_ALIASES = {
    "ter": {"ter", "тер"},
    "kod1": {"kod1", "код1"},
    "kod2": {"kod2", "код2"},
    "kod3": {"kod3", "код3"},
    "name": {"name1", "name", "наименование", "наименование территории"},
    "change": {"nomakt", "номер изменения", "nom_akt"},
    "status": {"status", "статус", "тип изменения"},
}


def _canonical_field(column: str) -> str | None:
    key = re.sub(r"\s+", " ", str(column).strip().lower())
    for target, aliases in FIELD_ALIASES.items():
        if key in aliases:
            return target
    return None


def read_rosstat_oktmo_csv(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    raw_bytes = path.read_bytes()
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "cp1251", "utf-8"):
        try:
            text = raw_bytes.decode(encoding)
            return pd.read_csv(StringIO(text), sep=None, engine="python", dtype=str, keep_default_na=False)
        except Exception as exc:
            last_error = exc
    raise ValueError(f"Could not read Rosstat OKTMO CSV: {last_error}")


def build_municipality_registry(
    frame: pd.DataFrame,
    *,
    source_url: str,
    source_version: str,
) -> pd.DataFrame:
    rename = {}
    for column in frame.columns:
        target = _canonical_field(column)
        if target:
            rename[column] = target
    data = frame.rename(columns=rename).copy()
    required = ["ter", "kod1", "kod2", "name"]
    missing = [col for col in required if col not in data.columns]
    if missing:
        raise ValueError("Rosstat OKTMO export missing fields: " + ", ".join(missing))

    def digits(value: object, width: int) -> str:
        text = re.sub(r"\D", "", str(value or ""))
        return text.zfill(width) if text else ""

    data["ter"] = data["ter"].map(lambda value: digits(value, 2))
    data["kod1"] = data["kod1"].map(lambda value: digits(value, 3))
    data["kod2"] = data["kod2"].map(lambda value: digits(value, 3))
    data["kod3"] = data["kod3"].map(lambda value: digits(value, 3)) if "kod3" in data else ""

    data = data[
        data["ter"].str.fullmatch(r"\d{2}")
        & data["kod1"].str.fullmatch(r"\d{3}")
        & data["kod2"].str.fullmatch(r"\d{3}")
        & data["name"].astype(str).str.strip().ne("")
    ].copy()

    data["oktmo"] = (data["ter"] + data["kod1"] + data["kod2"]).map(normalize_oktmo)
    if "kod3" in data:
        full = data["oktmo"] + data["kod3"].where(data["kod3"].str.fullmatch(r"\d{3}"), "000")
    else:
        full = data["oktmo"] + "000"
    data["oktmo_full"] = full

    registry = pd.DataFrame({
        "oktmo": data["oktmo"],
        "oktmo_full": data["oktmo_full"],
        "municipality_name": data["name"].astype(str).str.strip(),
        "municipality_type": "",
        "region_name": "",
        "region_code": data["ter"],
        "parent_oktmo": "",
        "valid_from": "",
        "valid_to": "",
        "source_id": "rosstat_oktmo",
        "source_url": source_url,
        "source_version": source_version,
        "status": "ACTIVE",
    })

    registry = registry.drop_duplicates(["oktmo", "municipality_name"]).copy()
    conflicting = registry.groupby("oktmo")["municipality_name"].nunique()
    bad_codes = conflicting[conflicting > 1].index.tolist()
    if bad_codes:
        raise ValueError("Conflicting names for OKTMO: " + ", ".join(bad_codes[:10]))

    return registry.drop_duplicates("oktmo").sort_values("oktmo").reset_index(drop=True)
