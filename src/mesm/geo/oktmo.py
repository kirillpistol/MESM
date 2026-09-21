"""Strict OKTMO identity layer for MESM."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata

import pandas as pd


OKTMO8_RE = re.compile(r"^[0-9]{8}$")
OKTMO11_RE = re.compile(r"^[0-9]{11}$")

REGISTRY_COLUMNS = (
    "oktmo",
    "oktmo_full",
    "municipality_name",
    "municipality_type",
    "region_name",
    "region_code",
    "parent_oktmo",
    "valid_from",
    "valid_to",
    "source_id",
    "source_url",
    "source_version",
    "status",
)

ALIAS_COLUMNS = (
    "source_id",
    "source_municipality_name",
    "oktmo",
    "match_method",
    "status",
    "source_url",
    "notes",
)


@dataclass(frozen=True)
class IdentityResolution:
    source_name: str
    oktmo: str | None
    municipality_name: str | None
    status: str
    reason: str


def normalize_name(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower().replace("ё", "е")
    text = re.sub(r"[^0-9a-zа-я]+", " ", text)
    return " ".join(text.split())


def normalize_oktmo(value: object, *, municipal_level: bool = True) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if municipal_level and OKTMO11_RE.fullmatch(digits):
        digits = digits[:8]
    if not OKTMO8_RE.fullmatch(digits):
        raise ValueError(f"Municipal OKTMO must contain 8 digits, got {value!r}.")
    return digits


def read_municipality_registry(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Municipality registry not found: {path}")
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    missing = [col for col in REGISTRY_COLUMNS if col not in frame.columns]
    if missing:
        raise ValueError("Municipality registry missing columns: " + ", ".join(missing))
    frame = frame[list(REGISTRY_COLUMNS)].copy()
    frame["oktmo"] = frame["oktmo"].map(normalize_oktmo)
    if frame["oktmo"].duplicated().any():
        dup = sorted(frame.loc[frame["oktmo"].duplicated(keep=False), "oktmo"].unique())
        raise ValueError("Duplicate OKTMO in municipality registry: " + ", ".join(dup[:10]))
    frame["_name_key"] = frame["municipality_name"].map(normalize_name)
    return frame


def read_alias_registry(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Alias registry not found: {path}")
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    missing = [col for col in ALIAS_COLUMNS if col not in frame.columns]
    if missing:
        raise ValueError("Alias registry missing columns: " + ", ".join(missing))
    frame = frame[list(ALIAS_COLUMNS)].copy()
    frame["oktmo"] = frame["oktmo"].map(normalize_oktmo)
    frame["_name_key"] = frame["source_municipality_name"].map(normalize_name)
    return frame


def validate_identity_tables(registry: pd.DataFrame, aliases: pd.DataFrame) -> None:
    known = set(registry["oktmo"])
    unknown = sorted(set(aliases["oktmo"]) - known)
    if unknown:
        raise ValueError("Aliases reference unknown OKTMO: " + ", ".join(unknown[:10]))

    approved = aliases[aliases["status"].str.upper().isin({"APPROVED", "VERIFIED"})].copy()
    collisions = (
        approved.groupby(["source_id", "_name_key"])["oktmo"].nunique().reset_index(name="codes")
    )
    bad = collisions[collisions["codes"] > 1]
    if not bad.empty:
        raise ValueError(
            "One approved source alias maps to multiple OKTMO values: "
            + ", ".join(bad["_name_key"].astype(str).head(10))
        )


def resolve_source_names(
    names: pd.Series,
    *,
    source_id: str,
    registry: pd.DataFrame,
    aliases: pd.DataFrame,
) -> pd.DataFrame:
    validate_identity_tables(registry, aliases)
    registry_by_code = registry.set_index("oktmo")
    approved = aliases[
        (aliases["source_id"].astype(str) == source_id)
        & aliases["status"].str.upper().isin({"APPROVED", "VERIFIED"})
    ].copy()

    alias_map = approved.set_index("_name_key")["oktmo"].to_dict()
    rows = []
    for source_name in pd.Series(names, dtype="string").drop_duplicates().astype(str):
        key = normalize_name(source_name)
        oktmo = alias_map.get(key)
        if oktmo and oktmo in registry_by_code.index:
            official = registry_by_code.loc[oktmo]
            rows.append({
                "source_name": source_name,
                "_name_key": key,
                "oktmo": oktmo,
                "municipality_name": str(official["municipality_name"]),
                "identity_status": "OKTMO_RESOLVED",
                "identity_reason": "APPROVED_SOURCE_ALIAS",
            })
        else:
            rows.append({
                "source_name": source_name,
                "_name_key": key,
                "oktmo": "",
                "municipality_name": "",
                "identity_status": "UNRESOLVED",
                "identity_reason": "NO_APPROVED_OKTMO_ALIAS",
            })
    return pd.DataFrame(rows)
