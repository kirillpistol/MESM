from __future__ import annotations
from pathlib import Path

RULES = (
    ("budget_quality", ("расчет по итогам",)),
    ("article136", ("ст.136", "ст 136")),
    ("prospective_financial_plan", ("перспективный финансовый план",)),
    ("expenditure_obligations", ("реестр расходных обязательств", "свод реестров")),
    ("classification_mapping", ("сопоставительная таблица", "приложение к порядку")),
    ("budget_execution_archive", ("исполн", "бюджет")),
)

def classify_source(path: str | Path) -> str:
    name = Path(path).name.lower()
    for parser_id, tokens in RULES:
        if any(token in name for token in tokens):
            return parser_id
    return "unknown"

def dispatch(path: str | Path) -> dict:
    parser_id = classify_source(path)
    return {
        "path": str(path),
        "parser_id": parser_id,
        "status": "READY" if parser_id != "unknown" else "QUARANTINE",
    }
