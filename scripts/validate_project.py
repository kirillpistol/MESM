from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

errors: list[str] = []
for path in (ROOT / "schemas").glob("*.json"):
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"{path.name}: {exc}")

panel = ROOT / "data/processed/fiscal_reference_panel.csv"
if panel.exists():
    rows = list(csv.DictReader(panel.open(encoding="utf-8-sig")))
    if len(rows) != 66:
        errors.append(f"в fiscal_reference_panel.csv ожидалось 66 строк, получено {len(rows)}")
    if len({r['municipality_name'] for r in rows}) != 22:
        errors.append("fiscal_reference_panel.csv должен содержать 22 муниципалитета")
    if {r['year'] for r in rows} != {"2023", "2024", "2025"}:
        errors.append("fiscal_reference_panel.csv должен содержать 2023–2025 годы")
else:
    errors.append("отсутствует fiscal_reference_panel.csv")

bo_history = ROOT / "data/processed/budget_provision_history_2021_2023.csv"
if bo_history.exists():
    rows = list(csv.DictReader(bo_history.open(encoding="utf-8-sig")))
    if len(rows) != 44:
        errors.append(f"в budget_provision_history_2021_2023.csv ожидалось 44 строки, получено {len(rows)}")
else:
    errors.append("отсутствует budget_provision_history_2021_2023.csv")

required = [
    ROOT / "config/dual_state.yaml",
    ROOT / "config/backtest.yaml",
    ROOT / "config/evaluation.yaml",
    ROOT / "data/events/event_registry.csv",
]
for path in required:
    if not path.exists():
        errors.append(f"отсутствует {path.relative_to(ROOT)}")

if errors:
    raise SystemExit("\n".join(errors))

print("OK: JSON Schema синтаксически корректны.")
print("OK: Fiscal Reference Panel = 66 строк / 22 муниципалитета / 2023–2025.")
print("OK: Budget Provision History = 44 строки / Q3 2021 и Q3 2023.")
print("OK: конфигурации эксперимента MESM на месте.")
