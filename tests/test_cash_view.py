from pathlib import Path
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))

from cash_view import demo_cash, parse_cash_csv, parse_corrections_csv
from mesm.budget.cash_execution import normalize_cash


def test_demo_is_labeled_sample_and_exercises_adjustments():
    lines, corrections = demo_cash()
    assert all(line.source_document == "Синтетический пример" for line in lines)
    result = normalize_cash(lines, corrections, as_of=__import__("datetime").date(2026, 5, 20),
                            municipality="Сургут", source="UFK_CASH")
    assert [row.normalized_revenue for row in result] == [80, 0, 60, 60]
    assert result[-1].reserve_need > 0
    cash_csv = pd.DataFrame([row.__dict__ for row in lines]).to_csv(index=False).encode("utf-8-sig")
    adjustment_csv = pd.DataFrame([row.__dict__ for row in corrections]).to_csv(index=False).encode("utf-8-sig")
    assert parse_cash_csv(cash_csv) == lines
    assert parse_corrections_csv(adjustment_csv) == corrections


def test_uploaded_csv_checks_headers_and_values():
    content = ("municipality,month,kbk,side,amount,source,available_at,source_document,period_basis,preliminary\n"
               "Сургут,2026-01-01,182101,REVENUE,100,UFK_CASH,2026-01-08,Экспорт,MONTH,false\n").encode()
    assert parse_cash_csv(content)[0].amount == 100
    with pytest.raises(ValueError, match="Нет полей"):
        parse_cash_csv(b"month,amount\n2026-01-01,100\n")
    with pytest.raises(ValueError, match="допустимы"):
        parse_cash_csv(content.replace(b"UFK_CASH", b"UNVERIFIED"))
    with pytest.raises(ValueError, match="Нет полей"):
        parse_corrections_csv(b"correction_id,amount\na,1\n")


def test_cash_page_renders_without_exception():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=35)
    app.run()
    app.sidebar.radio[0].set_value("Кассовый контур")
    app.run()
    assert not app.exception
    assert any("Кассовое исполнение" in item.value for item in app.subheader)
    assert any("ДЕМО" in item.value for item in app.markdown)
    assert app.get("plotly_chart")
