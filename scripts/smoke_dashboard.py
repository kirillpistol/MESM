"""Quick startup check without rendering every Streamlit page."""

from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "dashboard"))

import plotly
import streamlit

from cash_view import demo_cash
from mesm.budget.cash_execution import normalize_cash


def main() -> None:
    lines, corrections = demo_cash()
    result = normalize_cash(lines, corrections, as_of=date(2026, 5, 20),
                            municipality="Сургут", source="UFK_CASH")
    if [row.normalized_revenue for row in result] != [80, 0, 60, 60]:
        raise RuntimeError("Cash calculation did not pass the startup check")
    print("Dashboard dependencies and cash calculations: OK")


if __name__ == "__main__":
    main()
