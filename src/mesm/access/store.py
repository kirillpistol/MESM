from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from mesm import __version__
from mesm.data.intake import DATASET_SPECS, load_current_dataset

EXTRA_PATHS = {
    "fiscal_panel": "data/processed/fiscal_reference_panel.csv",
    "fns_5ndfl": "data/external/fns_5ndfl_surgut.csv",
    "shock_calibration": "data/reports/competition/shock_calibration_summary.csv",
}


def catalogue(root: Path):
    products = json.loads((root / "config/data_products.json").read_text(encoding="utf-8"))["products"]
    for item in products:
        key = item["id"]
        if key == "budget_calculations":
            source = load_current_dataset("budget_official_plan",root)
            columns = ["municipality_name","year","stage","total_revenue","expenditure","financing_sources"]
            frame = source[columns].copy() if not source.empty else pd.DataFrame(columns=columns)
            for field in ("total_revenue","expenditure","financing_sources"):
                frame[field] = pd.to_numeric(frame[field],errors="coerce")
            frame["calculated_deficit"] = frame["expenditure"]-frame["total_revenue"]
            frame["uncovered_plan_need"] = (frame["calculated_deficit"]-frame["financing_sources"]).clip(lower=0)
            frame["unit"] = "thousand_rub"
            frame["interpretation"] = "plan_arithmetic_not_cash_or_legal_compliance"
            item["source_path"] = "data/intake/active/budget_official_plan.csv" if (root/"data/intake/active/budget_official_plan.csv").exists() else DATASET_SPECS["budget_official_plan"].fallback_path
        elif key in DATASET_SPECS:
            frame = load_current_dataset(key, root)
            item["source_path"] = DATASET_SPECS[key].fallback_path
            active = root / "data/intake/active" / f"{key}.csv"
            if active.exists():
                item["source_path"] = active.relative_to(root).as_posix()
        else:
            path = root / EXTRA_PATHS[key]
            frame = pd.read_csv(path, encoding="utf-8-sig", dtype={"object_oktmo": str}) if path.exists() else pd.DataFrame()
            item["source_path"] = EXTRA_PATHS[key]
        item["row_count"] = len(frame)
        item["available"] = not frame.empty
        item["columns"] = list(frame.columns)
        item["detector_ready"] = False
        # Загруженный пользователем файл не становится автоматически официальным.
        if str(item["source_path"]).startswith("data/intake/active/"):
            item["evidence_status"] = "user_import_requires_source_verification"
        yield_item = (item, frame)
        yield yield_item


def build_store(root: Path, target: Path) -> dict:
    """Атомарный снимок активных таблиц. Никакие произвольные файлы не публикуются."""
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(suffix=".sqlite", dir=target.parent)
    os.close(handle)
    digest = hashlib.sha256()
    registry = root / "data/reference/municipality_registry.csv"
    codes = {}
    if registry.exists():
        for row in pd.read_csv(registry, dtype=str).fillna("").to_dict("records"):
            codes[row["municipality_name"]] = row["oktmo"]
    counts = {}
    evidence = {}
    for key,rel in {"sources":"config/external_sources.json", "trace":"data/manifest/report_trace_2025.json"}.items():
        path=root/rel
        evidence[key]=json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        digest.update(json.dumps(evidence[key],sort_keys=True,ensure_ascii=False).encode())
    try:
        with sqlite3.connect(temp) as conn:
            conn.executescript("CREATE TABLE metadata (key TEXT PRIMARY KEY,value TEXT); CREATE TABLE datasets (id TEXT PRIMARY KEY,descriptor TEXT); CREATE TABLE records (dataset TEXT,municipality TEXT,oktmo TEXT,period TEXT,payload TEXT); CREATE INDEX record_filter ON records(dataset,municipality,period); CREATE TABLE municipalities (name TEXT PRIMARY KEY,oktmo TEXT);")
            for item, frame in catalogue(root):
                descriptor = json.dumps(item, ensure_ascii=False, sort_keys=True)
                digest.update(descriptor.encode())
                conn.execute("INSERT INTO datasets VALUES (?,?)", (item["id"],descriptor))
                counts[item["id"]] = len(frame)
                # pandas сериализует отсутствующие значения в JSON null, а не NaN.
                for row in json.loads(frame.to_json(orient="records",force_ascii=False)):
                    name = str(row.get("municipality_name") or row.get("geography_name") or row.get("object_name") or "")
                    code = str(row.get("oktmo") or row.get("municipality_oktmo") or row.get("object_oktmo") or codes.get(name, ""))
                    period = str(row.get("period") or row.get("year") or row.get("report_year") or "")
                    payload = json.dumps(row, ensure_ascii=False, allow_nan=False,sort_keys=True)
                    digest.update(payload.encode())
                    conn.execute("INSERT INTO records VALUES (?,?,?,?,?)", (item["id"],name,code,period,payload))
                    if name:
                        conn.execute("INSERT OR IGNORE INTO municipalities VALUES (?,?)", (name,codes.get(name,code)))
            meta = {"schema_version":1,"snapshot_id":digest.hexdigest(),"built_at":datetime.now(timezone.utc).isoformat(),"read_only":True,"row_counts":counts,"evidence":evidence,"software_version":__version__}
            conn.executemany("INSERT INTO metadata VALUES (?,?)", [(k,json.dumps(v,ensure_ascii=False)) for k,v in meta.items()])
        os.replace(temp,target)
        return meta
    finally:
        if Path(temp).exists(): Path(temp).unlink()


class DataStore:
    def __init__(self, path: Path):
        self.path = Path(path)
    def connect(self):
        return sqlite3.connect(self.path.resolve().as_uri()+"?mode=ro",uri=True)
    def metadata(self):
        with self.connect() as conn:
            return {k:json.loads(v) for k,v in conn.execute("SELECT key,value FROM metadata")}
    def datasets(self):
        with self.connect() as conn:
            return [json.loads(row[0]) for row in conn.execute("SELECT descriptor FROM datasets ORDER BY id")]
    def municipalities(self):
        with self.connect() as conn:
            return [dict(name=n,oktmo=o or None,identity_status="code_present_requires_verification" if o else "code_missing") for n,o in conn.execute("SELECT name,oktmo FROM municipalities ORDER BY name")]
    def rows(self, dataset: str, municipality: str | None = None, period: str | None = None, limit: int = 100, offset: int = 0):
        if not 1 <= limit <= 1000 or offset < 0:
            raise ValueError("limit: 1..1000; offset >= 0")
        if dataset not in {d["id"] for d in self.datasets()}:
            raise KeyError(dataset)
        sql, args = " FROM records WHERE dataset=?", [dataset]
        if municipality is not None:
            sql += " AND municipality=?"; args.append(municipality)
        if period is not None:
            sql += " AND period=?"; args.append(period)
        with self.connect() as conn:
            count = conn.execute("SELECT COUNT(*)"+sql,args).fetchone()[0]
            data = [json.loads(row[0]) for row in conn.execute("SELECT payload"+sql+" ORDER BY rowid LIMIT ? OFFSET ?",[*args,limit,offset])]
        return {"dataset":dataset,"total":count,"limit":limit,"offset":offset,"rows":data,"snapshot_id":self.metadata()["snapshot_id"]}
