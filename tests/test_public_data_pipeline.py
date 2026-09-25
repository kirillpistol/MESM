import asyncio
from hashlib import sha256
import json
from pathlib import Path

import pandas as pd

from mesm.public_data.cache import Snapshot
from mesm.public_data.pipeline import update_public_data


def _config(source: str, field: str = "amount") -> dict:
    return {"enabled": True, "source": source, "url": f"https://example.test/{source}.csv",
            "period": "2025", "available_at": "2026-06-09", "schema_version": "2", "category": "all",
            "separator": ";", "period_format": "%Y-%m-%d",
            "columns": {"oktmo": "code", "period": "year", "indicator": "metric", "value": field, "unit": "unit"}}


def test_bad_input_preserves_last_good_and_reports_error(tmp_path: Path):
    cache_root = tmp_path / "cache"
    output = tmp_path / "published.csv"
    payloads = {"fns_7_ndfl": b"code;year;metric;amount;unit\n71876000;2025-12-31;income;120;rub\n"}

    async def fetch(source, url, *, period, available_at, schema_version):
        payload = payloads[source]
        digest = sha256(payload).hexdigest()
        path = cache_root / "raw" / digest
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return Snapshot(source, url, "2026-06-09", available_at, period, digest,
                        None, None, 200, schema_version, f"raw/{digest}")

    settings = {"sources": [_config("fns_7_ndfl")]}
    report = asyncio.run(update_public_data(settings, output, cache_root, "2026-09-25", fetch))
    assert report.status == "fresh"
    good = output.read_bytes()
    assert len(pd.read_csv(output)) == 1

    payloads["fns_7_ndfl"] = b"code;year;metric;amount;unit\n71876000;2025-12-31;income;-10;rub\n"
    report = asyncio.run(update_public_data(settings, output, cache_root, "2026-09-25", fetch))
    assert report.status == "stale"
    assert output.read_bytes() == good
    assert report.sources[0].status == "quarantined"
    assert json.loads(output.with_suffix(".status.json").read_text())["status"] == "stale"

    payloads["fns_7_ndfl"] = b"code;year;metric;amount;unit\n71876000;2025-12-31;income;120;rub\n"
    changed = _config("fns_7_ndfl")
    changed["category"] = "food"
    report = asyncio.run(update_public_data({"sources": [changed]}, output, cache_root, fetcher=fetch))
    assert report.status == "stale"
    assert "schema_version" in report.sources[0].error


def test_schema_drift_and_source_outage_do_not_publish_partial(tmp_path: Path):
    cache_root = tmp_path / "cache"
    output = tmp_path / "published.csv"
    output.write_text("last verified version\n")

    async def fetch(source, url, *, period, available_at, schema_version):
        if source == "rosstat_pmo":
            raise TimeoutError("source unavailable")
        payload = b"code;year;metric;amount;unit\n71876000;2025-12-31;income;120;rub\n"
        digest = sha256(payload).hexdigest()
        path = cache_root / "raw" / digest
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return Snapshot(source, url, "2026-06-09", available_at, period, digest,
                        None, None, 200, schema_version, f"raw/{digest}")

    settings = {"sources": [_config("fns_7_ndfl"), _config("rosstat_pmo")]}
    report = asyncio.run(update_public_data(settings, output, cache_root, fetcher=fetch))
    assert report.status == "partial"
    assert output.read_text() == "last verified version\n"
    assert [s.status for s in report.sources] == ["accepted", "quarantined"]

    settings["sources"] = [_config("fns_7_ndfl", "renamed_column")]
    report = asyncio.run(update_public_data(settings, output, cache_root, fetcher=fetch))
    assert report.status == "stale"
    assert "Missing source columns" in report.sources[0].error
    assert output.read_text() == "last verified version\n"
