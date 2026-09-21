import json
from pathlib import Path

import pandas as pd

from dashboard.source_monitor import load_source_manifest, pipeline_snapshot, source_status_frame


def test_source_monitor_distinguishes_configured_and_downloaded(tmp_path: Path):
    (tmp_path / "config").mkdir()
    (tmp_path / "data" / "manifest").mkdir(parents=True)
    (tmp_path / "data" / "processed").mkdir(parents=True)

    payload = {
        "sources": {
            "a": {
                "authority": "Authority",
                "municipality_name": "City",
                "document_type": "BUDGET",
                "decision": "Decision",
                "publication_date": "2026-01-01",
                "page_url": "https://example.org/a",
            },
            "b": {
                "authority": "Authority",
                "municipality_name": "City",
                "document_type": "EXECUTION",
                "decision": "Decision B",
                "publication_date": "2026-02-01",
                "page_url": "https://example.org/b",
            },
        }
    }
    (tmp_path / "config" / "official_sources.json").write_text(json.dumps(payload), encoding="utf-8")
    pd.DataFrame([{
        "source_id": "a",
        "downloaded_at_utc": "2026-09-20T12:00:00+00:00",
        "sha256": "0" * 64,
    }]).to_csv(tmp_path / "data" / "manifest" / "source_manifest.csv", index=False, encoding="utf-8-sig")
    (tmp_path / "data" / "processed" / "fiscal_reference_panel.csv").write_text("x\n1\n", encoding="utf-8")

    manifest = load_source_manifest(tmp_path)
    status = source_status_frame(tmp_path)
    snap = pipeline_snapshot(tmp_path)

    assert len(manifest) == 1
    assert status.set_index("source_id").loc["a", "status"] == "DOWNLOADED"
    assert status.set_index("source_id").loc["b", "status"] == "CONFIGURED"
    assert snap["configured_sources"] == 2
    assert snap["manifest_files"] == 1
    assert snap["fiscal_panel_ready"] is True
