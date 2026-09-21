import pandas as pd
import pytest

from mesm.geo.oktmo import (
    normalize_name,
    normalize_oktmo,
    resolve_source_names,
    validate_identity_tables,
)


def _registry():
    return pd.DataFrame([{
        "oktmo": "71876000",
        "municipality_name": "Сургут",
        "_name_key": normalize_name("Сургут"),
    }])


def _aliases():
    return pd.DataFrame([{
        "source_id": "sberindex_cashless_spending_municipal",
        "source_municipality_name": "городской округ город Сургут",
        "oktmo": "71876000",
        "status": "VERIFIED",
        "_name_key": normalize_name("городской округ город Сургут"),
    }])


def test_oktmo_normalization_is_strict():
    assert normalize_oktmo("71 876 000") == "71876000"
    assert normalize_oktmo("71876000000") == "71876000"
    with pytest.raises(ValueError):
        normalize_oktmo("Сургут")


def test_source_alias_resolves_to_official_oktmo():
    result = resolve_source_names(
        pd.Series(["городской округ город Сургут", "Неизвестный округ"]),
        source_id="sberindex_cashless_spending_municipal",
        registry=_registry(),
        aliases=_aliases(),
    ).set_index("source_name")
    assert result.loc["городской округ город Сургут", "oktmo"] == "71876000"
    assert result.loc["Неизвестный округ", "identity_status"] == "UNRESOLVED"


def test_alias_collision_is_rejected():
    aliases = pd.concat([
        _aliases(),
        pd.DataFrame([{
            "source_id": "sberindex_cashless_spending_municipal",
            "source_municipality_name": "городской округ город Сургут",
            "oktmo": "71875000",
            "status": "APPROVED",
            "_name_key": normalize_name("городской округ город Сургут"),
        }]),
    ], ignore_index=True)
    registry = pd.concat([
        _registry(),
        pd.DataFrame([{
            "oktmo": "71875000",
            "municipality_name": "Другой",
            "_name_key": normalize_name("Другой"),
        }]),
    ], ignore_index=True)
    with pytest.raises(ValueError):
        validate_identity_tables(registry, aliases)
