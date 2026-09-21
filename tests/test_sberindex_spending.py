import pandas as pd

from mesm.geo.oktmo import normalize_name
from mesm.ingest.sberindex_spending import canonicalize_sberindex_spending


def _row(period: str, value: int, category: str, municipality: str) -> dict:
    return {
        "period": period,
        "value": value,
        "obs_status": "A",
        "source": "Данные СберИндекса",
        "category_15": category,
        "mo": municipality,
        "freq": "Месяц",
        "decimals": 3,
        "unit_measure": "руб.",
        "unit_mult": 0,
    }


def _registry() -> pd.DataFrame:
    return pd.DataFrame([{
        "oktmo": "71876000",
        "municipality_name": "Сургут",
        "_name_key": normalize_name("Сургут"),
    }])


def _aliases() -> pd.DataFrame:
    return pd.DataFrame([{
        "source_id": "sberindex_cashless_spending_municipal",
        "source_municipality_name": "городской округ город Сургут",
        "oktmo": "71876000",
        "status": "VERIFIED",
        "_name_key": normalize_name("городской округ город Сургут"),
    }])


def test_sberindex_canonicalizer_requires_resolved_oktmo():
    rows = [
        _row("2023-01-01", 100, "Все категории", "городской округ город Сургут"),
        _row("2023-02-01", 110, "Все категории", "городской округ город Сургут"),
        _row("2023-01-01", 200, "Все категории", "Неизвестный городской округ"),
    ]
    canonical, quarantine, profile = canonicalize_sberindex_spending(
        pd.DataFrame(rows),
        registry=_registry(),
        aliases=_aliases(),
    )

    assert len(canonical) == 2
    assert canonical["oktmo"].unique().tolist() == ["71876000"]
    assert canonical["municipality_id"].unique().tolist() == ["71876000"]
    assert canonical["municipality_name"].unique().tolist() == ["Сургут"]
    assert canonical["identity_status"].eq("OKTMO_RESOLVED").all()
    assert len(quarantine) == 1
    assert profile.oktmo_resolved_rows == 2
    assert profile.unresolved_rows == 1


def test_source_name_collision_is_quarantined_even_with_alias():
    rows = [
        _row("2023-01-01", 100, "Все категории", "городской округ город Сургут"),
        _row("2023-01-01", 200, "Все категории", "городской округ город Сургут"),
    ]
    canonical, quarantine, profile = canonicalize_sberindex_spending(
        pd.DataFrame(rows),
        registry=_registry(),
        aliases=_aliases(),
    )

    assert canonical.empty
    assert len(quarantine) == 2
    assert quarantine["identity_status"].eq("AMBIGUOUS_SOURCE_NAME").all()
    assert profile.ambiguous_names == 1
