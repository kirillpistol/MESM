from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def load_source_manifest(root: str | Path) -> pd.DataFrame:
    path = Path(root) / "data" / "manifest" / "source_manifest.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


def source_status_frame(root: str | Path) -> pd.DataFrame:
    root = Path(root)
    config_path = root / "config" / "official_sources.json"
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    manifest = load_source_manifest(root)
    rows = []
    for source_id, spec in payload.get("sources", {}).items():
        count = 0
        last_download = ""
        if not manifest.empty and "source_id" in manifest:
            matched = manifest[manifest["source_id"].astype(str) == source_id]
            count = len(matched)
            if count and "downloaded_at_utc" in matched:
                values = matched["downloaded_at_utc"].dropna().astype(str)
                last_download = values.max() if not values.empty else ""
        rows.append({
            "source_id": source_id,
            "authority": spec.get("authority", ""),
            "municipality_name": spec.get("municipality_name", ""),
            "document_type": spec.get("document_type", ""),
            "decision": spec.get("decision", ""),
            "publication_date": spec.get("publication_date", ""),
            "page_url": spec.get("page_url", ""),
            "manifest_files": count,
            "last_download": last_download,
            "status": "DOWNLOADED" if count else "CONFIGURED",
        })
    return pd.DataFrame(rows)


def pipeline_snapshot(root: str | Path) -> dict[str, object]:
    root = Path(root)
    status = source_status_frame(root)
    manifest = load_source_manifest(root)
    return {
        "configured_sources": int(len(status)),
        "manifest_files": int(len(manifest)),
        "raw_sources": int(manifest["source_id"].nunique()) if not manifest.empty and "source_id" in manifest else 0,
        "budget_snapshot_ready": (root / "data" / "processed" / "official_budget_plan_surgut_2025_2027.csv").exists(),
        "budget_structure_ready": (root / "data" / "processed" / "official_budget_project_surgut_2025.csv").exists(),
        "fiscal_panel_ready": (root / "data" / "processed" / "fiscal_reference_panel.csv").exists(),
    }
