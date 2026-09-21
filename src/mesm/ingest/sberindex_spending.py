"""СберИндекс cashless spending ingestion for the MESM competition core."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
import zipfile

import pandas as pd

from mesm.geo.oktmo import normalize_name, resolve_source_names


REQUIRED_COLUMNS = (
    "period",
    "value",
    "obs_status",
    "source",
    "category_15",
    "mo",
    "freq",
    "decimals",
    "unit_measure",
    "unit_mult",
)

CATEGORY_CODES = {
    "Все категории": "ALL",
    "Продовольствие": "FOOD",
    "Здоровье": "HEALTH",
    "Общественное питание": "DINING",
    "Маркетплейсы": "MARKETPLACES",
    "Транспорт": "TRANSPORT",
}


@dataclass(frozen=True)
class SberindexProfile:
    input_rows: int
    exact_duplicates_removed: int
    canonical_rows: int
    quarantined_rows: int
    municipalities_model_eligible: int
    oktmo_resolved_rows: int
    unresolved_rows: int
    ambiguous_names: int
    periods: int
    categories: int
    period_start: str
    period_end: str


def file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_sberindex_export(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if len(names) != 1:
                raise ValueError(f"Expected exactly one CSV inside ZIP, found {len(names)}.")
            with archive.open(names[0]) as handle:
                frame = pd.read_csv(handle, sep=";", quotechar='"', encoding="utf-8")
    elif path.suffix.lower() == ".csv":
        frame = pd.read_csv(path, sep=";", quotechar='"', encoding="utf-8")
    else:
        raise ValueError("SberIndex input must be .csv or .csv.zip.")

    frame.columns = [str(col).strip().lstrip("\ufeff") for col in frame.columns]
    missing = [col for col in REQUIRED_COLUMNS if col not in frame.columns]
    if missing:
        raise ValueError("Missing SberIndex columns: " + ", ".join(missing))
    return frame


def canonicalize_sberindex_spending(
    frame: pd.DataFrame,
    *,
    registry: pd.DataFrame,
    aliases: pd.DataFrame,
    source_id: str = "sberindex_cashless_spending_municipal",
) -> tuple[pd.DataFrame, pd.DataFrame, SberindexProfile]:
    raw = frame.copy()
    input_rows = len(raw)

    raw["mo"] = raw["mo"].astype("string").str.strip()
    raw["category_15"] = raw["category_15"].astype("string").str.strip()
    raw["period"] = pd.to_datetime(raw["period"], errors="coerce")
    raw["value"] = pd.to_numeric(raw["value"], errors="coerce")

    if raw["period"].isna().any():
        raise ValueError(f"Invalid period values: {int(raw['period'].isna().sum())}.")
    if raw["value"].isna().any():
        raise ValueError(f"Invalid spending values: {int(raw['value'].isna().sum())}.")
    if raw["mo"].isna().any() or raw["mo"].eq("").any():
        raise ValueError("Blank municipality names are not allowed.")
    if (raw["value"] < 0).any():
        raise ValueError("Negative spending values are not allowed.")

    unknown_categories = sorted(set(raw["category_15"].dropna()) - set(CATEGORY_CODES))
    if unknown_categories:
        raise ValueError("Unknown SberIndex categories: " + ", ".join(unknown_categories))

    exact_duplicates = int(raw.duplicated().sum())
    raw = raw.drop_duplicates().copy()

    logical_key = ["period", "category_15", "mo"]
    duplicate_mask = raw.duplicated(logical_key, keep=False)
    ambiguous_names = set(raw.loc[duplicate_mask, "mo"].astype(str))

    resolutions = resolve_source_names(
        raw["mo"],
        source_id=source_id,
        registry=registry,
        aliases=aliases,
    )
    resolution_map = resolutions.set_index("_name_key")
    raw["_name_key"] = raw["mo"].map(normalize_name)
    raw["oktmo"] = raw["_name_key"].map(resolution_map["oktmo"]).fillna("")
    raw["official_municipality_name"] = raw["_name_key"].map(
        resolution_map["municipality_name"]
    ).fillna("")
    raw["identity_status"] = raw["_name_key"].map(
        resolution_map["identity_status"]
    ).fillna("UNRESOLVED")
    raw["identity_reason"] = raw["_name_key"].map(
        resolution_map["identity_reason"]
    ).fillna("NO_APPROVED_OKTMO_ALIAS")

    raw.loc[raw["mo"].astype(str).isin(ambiguous_names), "identity_status"] = "AMBIGUOUS_SOURCE_NAME"
    raw.loc[raw["mo"].astype(str).isin(ambiguous_names), "identity_reason"] = (
        "DUPLICATE_PERIOD_CATEGORY_NAME_IN_SOURCE"
    )

    resolved_mask = raw["identity_status"].eq("OKTMO_RESOLVED")
    clean = raw[resolved_mask].copy()
    quarantine = raw[~resolved_mask].copy()

    clean["municipality_id"] = clean["oktmo"].astype(str)
    clean["municipality_name"] = clean["official_municipality_name"].astype(str)
    clean["source_municipality_name"] = clean["mo"].astype(str)
    clean["period_start"] = clean["period"].dt.to_period("M").dt.start_time.dt.strftime("%Y-%m-%d")
    clean["period_end"] = clean["period"].dt.to_period("M").dt.end_time.dt.strftime("%Y-%m-%d")
    clean["frequency"] = "MONTH"
    clean["category"] = clean["category_15"].astype(str)
    clean["category_code"] = clean["category"].map(CATEGORY_CODES)
    clean["spending_nominal"] = clean["value"].astype(float)
    clean["data_status"] = "official_public"
    clean["identity_status"] = "OKTMO_RESOLVED"
    clean["model_eligible"] = True
    clean["source"] = clean["source"].astype(str)
    clean["obs_status"] = clean["obs_status"].astype(str)
    clean["unit"] = clean["unit_measure"].astype(str)

    canonical_columns = [
        "municipality_id",
        "municipality_name",
        "source_municipality_name",
        "oktmo",
        "period_start",
        "period_end",
        "frequency",
        "category",
        "category_code",
        "spending_nominal",
        "data_status",
        "identity_status",
        "model_eligible",
        "source",
        "obs_status",
        "unit",
    ]
    clean = clean[canonical_columns].sort_values(
        ["municipality_id", "category_code", "period_start"]
    ).reset_index(drop=True)

    if clean.duplicated(["oktmo", "category_code", "period_start"]).any():
        raise ValueError("Canonical SberIndex OKTMO keys are not unique after identity resolution.")

    quarantine = quarantine.sort_values(["mo", "category_15", "period"]).reset_index(drop=True)
    profile = SberindexProfile(
        input_rows=input_rows,
        exact_duplicates_removed=exact_duplicates,
        canonical_rows=len(clean),
        quarantined_rows=len(quarantine),
        municipalities_model_eligible=int(clean["oktmo"].nunique()),
        oktmo_resolved_rows=len(clean),
        unresolved_rows=int((quarantine["identity_status"] == "UNRESOLVED").sum()),
        ambiguous_names=len(ambiguous_names),
        periods=int(clean["period_start"].nunique()),
        categories=int(clean["category_code"].nunique()),
        period_start=str(clean["period_start"].min()) if not clean.empty else "",
        period_end=str(clean["period_start"].max()) if not clean.empty else "",
    )
    return clean, quarantine, profile


def profile_dict(profile: SberindexProfile) -> dict[str, object]:
    return asdict(profile)
