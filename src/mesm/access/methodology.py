"""Versioned methodology snapshot: documentation is not a legal approval."""
import hashlib,json
from pathlib import Path
DOCUMENTS=("docs/30_function_reference.md","docs/05_formula_registry.md","docs/31_cash_schema_and_audit.md","docs/39_methodology_and_updates.md","docs/40_current_code_index.md","docs/41_manual_search_directory.md","docs/adr/0001-mesm-as-independent-l3.md")
def build_methodology(root:Path):
    path=root/"config/formula_registry.json"
    registry=json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"contract":"mesm.formula-registry/1","registry_version":None,"formulas":[]}
    documents=[]
    for rel in DOCUMENTS:
        path=root/rel
        if path.exists():
            raw=path.read_bytes().replace(b"\r\n",b"\n")
            documents.append({"path":rel,"sha256":hashlib.sha256(raw).hexdigest(),"content":raw.decode("utf-8")})
    code_hashes={}
    for rel in sorted({f["implementation"] for f in registry["formulas"]}):
        path=root/rel
        code_hashes[rel]=hashlib.sha256(path.read_bytes().replace(b"\r\n",b"\n")).hexdigest() if path.exists() else None
    obj={"contract":"mesm.methodology/1","formula_registry":registry,"documents":documents,"implementation_sha256":code_hashes,
         "notice":"Проект периодически обновляется через проверенные версии. Наличие документации и SHA-256 не является утверждением официальной методики или доказательством эффекта."}
    obj["methodology_id"]=hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    return obj
