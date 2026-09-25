from pathlib import Path
import pandas as pd
import pytest

from mesm.public_data.cache import AsyncSnapshotCache
from mesm.public_data.ingest import normalize_csv
from mesm.public_data.schemas import features_as_of, validate_canonical


def test_annual_income_mapping_and_publication_gate(tmp_path: Path):
    path = tmp_path / "income.csv"
    path.write_text("code;year;metric;amount;unit\n71876000;2025-12-31;income;120,5;rub\n", encoding="utf-8")
    config = {"source": "fns_7_ndfl", "category": "all", "separator": ";", "available_at": "2026-06-09",
              "period_format": "%Y-%m-%d", "columns": {"oktmo": "code", "period": "year", "indicator": "metric", "value": "amount", "unit": "unit"}}
    frame = normalize_csv(path, config)
    assert frame.iloc[0]["value"] == 120.5
    assert features_as_of(frame, "2026-06-08").empty
    assert len(features_as_of(frame, "2026-06-09")) == 1
    with pytest.raises(Exception):
        validate_canonical(pd.concat([frame, frame], ignore_index=True))


def test_reject_future_release_and_bad_url(tmp_path: Path):
    path = tmp_path / "income.csv"
    path.write_text("code;year;metric;amount;unit\n71876000;2025-12-31;income;120;rub\n", encoding="utf-8")
    config = {"source": "fns_5_ndfl", "category": "all", "separator": ";", "available_at": "2025-01-01",
              "period_format": "%Y-%m-%d", "columns": {"oktmo": "code", "period": "year", "indicator": "metric", "value": "amount", "unit": "unit"}}
    with pytest.raises(Exception):
        normalize_csv(path, config)
    import asyncio
    with pytest.raises(ValueError):
        asyncio.run(AsyncSnapshotCache(tmp_path).fetch("source", "http://example.test/file", period="2025", available_at="2026-01-01"))
