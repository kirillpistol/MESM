"""Готовый пакет MESM L3 для внешнего менеджера. Расчёты принадлежат MESM."""
import hashlib,json,re,sys
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
from mesm import __version__

def descriptor(root,store):
    node=json.loads((root/"config/l3_node.json").read_text(encoding="utf-8"))
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}",node["node_id"]):raise ValueError("Invalid node identity")
    if node.get("role")!="L3" or node.get("contract")!="mesm.l3/1":raise ValueError("Invalid node contract")
    return {**node,"software_version":__version__,"snapshot_id":store.metadata()["snapshot_id"],"capabilities":["catalog","data","report_package","source_trace","processing_sessions"],"municipalities":store.municipalities(),"calculations_owned_by":"MESM","methodology_id":store.metadata()["evidence"]["methodology"]["methodology_id"],"methodology_endpoint":"/v1/methodology"}

def report_package(root,store,municipality):
    if municipality not in {m["name"] for m in store.municipalities()}:raise ValueError("Unknown municipality")
    sys.path.insert(0,str(root/"dashboard"))
    from final_report import build_question_report
    fiscal=store.rows("fiscal_panel",municipality=municipality,limit=1000)["rows"]
    frame=pd.DataFrame(fiscal)
    latest=frame.sort_values("year").tail(1) if not frame.empty else frame
    year=int(latest.iloc[-1]["year"]) if not latest.empty else None
    plans=store.rows("budget_calculations",municipality=municipality,period=str(year),limit=1000)["rows"] if year else []
    html=build_question_report(root,municipality,latest)
    products={d["id"]:d for d in store.datasets()}
    node=descriptor(root,store)
    return {"contract":"genesis.l3-report/1","producer_contract":"mesm.report-package/1","source_node":node["node_id"],"software_version":__version__,"municipality":municipality,
            "period":year,"snapshot_id":store.metadata()["snapshot_id"],"generated_at":datetime.now(timezone.utc).isoformat(),
            "methodology":{"methodology_id":store.metadata()["evidence"]["methodology"]["methodology_id"],
                           "formula_registry":store.metadata()["evidence"]["methodology"]["formula_registry"],
                           "documents":[{"path":d["path"],"sha256":d["sha256"]} for d in store.metadata()["evidence"]["methodology"]["documents"]],
                           "endpoint":"/v1/methodology","updates_notice":"MESM периодически обновляется; проверяйте версии перед каждым циклом."},
            "financial_snapshot":json.loads(latest.to_json(orient="records",force_ascii=False)),"budget_calculations":plans,
            "evidence_status":{"financial_snapshot":products["fiscal_panel"]["evidence_status"],"budget_calculations":products["budget_calculations"]["evidence_status"]},
            "report":{"format":"html","sha256":hashlib.sha256(html.encode()).hexdigest(),"content":html},
            "limitations":["Plan arithmetic is not cash execution or a legal verdict","Early warning is not proven","Session-only cash imports are not included"],
            "genesis_required":False}
