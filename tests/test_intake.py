from pathlib import Path

import pandas as pd

from mesm.data.intake import (
    compare_frames,
    dataset_status,
    persist_dataset,
    resolve_dataset_path,
    validate_dataset,
)


def valid_core() -> pd.DataFrame:
    return pd.DataFrame([{
        "year": 2025,
        "municipality_name": "Тест",
        "tax_initial": 100,
        "nontax_initial": 10,
        "tax_actual": 110,
        "nontax_actual": 11,
        "program_expense": 90,
        "total_expense": 100,
        "budget_amendments": 3,
        "municipal_debt": 5,
        "own_revenue_base": 121,
    }])


def test_validate_reference_core():
    result = validate_dataset("reference_core", valid_core())
    assert result.valid
    assert result.quality_status == "ACCEPTED"
    assert result.municipality_count == 1
    assert result.period_label == "2025"


def test_missing_required_column_fails():
    result = validate_dataset("reference_core", valid_core().drop(columns=["tax_initial"]))
    assert not result.valid
    assert result.quality_status == "REJECTED"
    assert any("tax_initial" in item for item in result.errors)


def test_duplicate_key_requires_review():
    result = validate_dataset(
        "reference_core",
        pd.concat([valid_core(), valid_core()], ignore_index=True),
    )
    assert result.valid
    assert result.quality_status == "REVIEW"
    assert result.duplicate_keys == 2


def test_compare_frames_detects_changed_municipality():
    before = valid_core()
    after = valid_core().copy()
    after.loc[0, "tax_actual"] = 120
    diff = compare_frames(before, after, ("year", "municipality_name"))
    assert diff["changed_keys"] == 1
    assert diff["changed_municipalities"] == ["Тест"]


def test_persist_creates_active_version(tmp_path: Path):
    record = persist_dataset("reference_core", valid_core(), "input.xlsx", b"source-bytes", tmp_path)
    active = resolve_dataset_path("reference_core", tmp_path)
    assert active.exists()
    assert "data/intake/active" in str(active).replace("\\", "/")
    assert record["rows"] == 1

    status = dataset_status("reference_core", tmp_path)
    assert status["mode"] == "загруженный"
    assert status["quality"] == "ACCEPTED"


def test_numeric_municipality_name_is_rejected():
    frame = valid_core()
    frame.loc[0, "municipality_name"] = "71876000"
    result = validate_dataset("reference_core", frame)
    assert not result.valid
    assert any("числовых кодов" in item for item in result.errors)



def test_validate_budget_project():
    frame = pd.DataFrame([{
        "year": 2027,
        "municipality_name": "Тест",
        "budget_side": "EXPENDITURE",
        "group": "Образование",
        "item_name": "Школы",
        "amount": 100.0,
        "flexibility": "PARTIAL",
    }])
    result = validate_dataset("budget_project", frame)
    assert result.valid
    assert result.quality_status == "ACCEPTED"


def test_budget_project_rejects_unknown_side():
    frame = pd.DataFrame([{
        "year": 2027,
        "municipality_name": "Тест",
        "budget_side": "WRONG",
        "group": "X",
        "item_name": "Y",
        "amount": 100.0,
    }])
    result = validate_dataset("budget_project", frame)
    assert not result.valid
    assert any("budget_side" in item for item in result.errors)



def test_budget_project_missing_amount_is_rejected():
    frame = pd.DataFrame([{
        "year": 2027,
        "municipality_name": "Тест",
        "budget_side": "EXPENDITURE",
        "group": "X",
        "item_name": "Y",
    }])
    result = validate_dataset("budget_project", frame)
    assert not result.valid
    assert any("amount" in item for item in result.errors)



def test_validate_official_budget_plan():
    frame = pd.DataFrame([{
        "year": 2025,
        "municipality_name": "Сургут",
        "stage": "ADOPTED",
        "total_revenue": 120.0,
        "revenue_base": 80.0,
        "transfers": 40.0,
        "expenditure": 130.0,
        "deficit": 10.0,
        "financing_sources": 10.0,
        "eligible_exceptions": 3.0,
        "source_url": "https://example.test",
        "publication_date": "2024-12-25",
    }])
    result = validate_dataset("budget_official_plan", frame)
    assert result.valid
