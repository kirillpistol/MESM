from __future__ import annotations

from datetime import date, timedelta
from io import BytesIO

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from mesm.budget.cash_execution import CashLine, ManualCorrection, monthly_from_ytd, normalize_cash
from ui import metric_grid, section_header, status_banner


CASH_COLUMNS = ["municipality", "month", "kbk", "side", "amount", "source", "available_at", "source_document", "period_basis", "preliminary"]
CORRECTION_COLUMNS = ["correction_id", "kind", "municipality", "kbk", "side", "cash_month", "amount", "reason", "evidence", "approved_by", "approved_at", "target_month"]


def _date(value: str) -> date:
    return date.fromisoformat(value.strip())


def parse_cash_csv(content: bytes) -> list[CashLine]:
    frame = pd.read_csv(BytesIO(content), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    missing = set(CASH_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Нет полей кассовой выгрузки: {', '.join(sorted(missing))}")
    result = []
    for row in frame.to_dict("records"):
        if row["side"].strip() not in {"REVENUE", "EXPENDITURE", "FINANCING"}:
            raise ValueError("side должен быть REVENUE, EXPENDITURE или FINANCING")
        if row["source"].strip() not in {"UFK_CASH", "REPORT_0503117"}:
            raise ValueError("Для кассового экрана допустимы UFK_CASH и REPORT_0503117")
        if row["period_basis"].strip() not in {"MONTH", "YTD"}:
            raise ValueError("period_basis должен быть MONTH или YTD")
        if row["preliminary"].strip().lower() not in {"true", "false"}:
            raise ValueError("preliminary принимает true или false")
        result.append(CashLine(row["municipality"].strip(), _date(row["month"]), row["kbk"].strip(),
                               row["side"].strip(), float(row["amount"].replace(",", ".")),
                               row["source"].strip(), _date(row["available_at"]),
                               row["source_document"].strip(), row["period_basis"].strip(),
                               row["preliminary"].strip().lower() == "true"))
    if not result:
        raise ValueError("Кассовая выгрузка пуста")
    return result


def parse_corrections_csv(content: bytes) -> list[ManualCorrection]:
    frame = pd.read_csv(BytesIO(content), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    missing = set(CORRECTION_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Нет полей корректировок: {', '.join(sorted(missing))}")
    return [ManualCorrection(row["correction_id"].strip(), row["kind"].strip(), row["municipality"].strip(),
                             row["kbk"].strip(), row["side"].strip(), _date(row["cash_month"]),
                             float(row["amount"].replace(",", ".")), row["reason"].strip(),
                             row["evidence"].strip(), row["approved_by"].strip(),
                             _date(row["approved_at"]), _date(row["target_month"]) if row["target_month"].strip() else None)
            for row in frame.to_dict("records")]


def demo_cash() -> tuple[list[CashLine], list[ManualCorrection]]:
    months = [date(2026, month, 1) for month in (1, 2, 3, 4)]
    receipts = [100.0, -20.0, 100.0, 20.0]
    expenses = [70.0, 80.0, 100.0, 50.0]
    lines = []
    for month, revenue, expense in zip(months, receipts, expenses):
        available = month + timedelta(days=8)
        lines.extend([
            CashLine("Сургут", month, "NDFL_DEMO", "REVENUE", revenue, "UFK_CASH", available, "Синтетический пример"),
            CashLine("Сургут", month, "EXP_DEMO", "EXPENDITURE", expense, "UFK_CASH", available, "Синтетический пример"),
        ])
    lines.append(CashLine("Сургут", months[2], "ASSET_DEMO", "REVENUE", 60.0,
                          "UFK_CASH", months[2] + timedelta(days=8), "Синтетический пример"))
    def correction(identifier, kind, cash_month, kbk, amount, target=None):
        return ManualCorrection(identifier, kind, "Сургут", kbk, "REVENUE", cash_month,
                                amount, "Сценарий для проверки интерфейса", "Демонстрационный документ",
                                "Демо", date(2026, 5, 1), target)
    return lines, [correction("D1", "REFUND_REALLOCATION", months[1], "NDFL_DEMO", 20, months[0]),
                   correction("D2", "ONE_OFF", months[2], "ASSET_DEMO", 60),
                   correction("D3", "ADVANCE_REALLOCATION", months[2], "NDFL_DEMO", 40, months[3])]


def render_cash_dashboard() -> None:
    st.subheader("Кассовое исполнение")
    section_header("Оперативный кассовый контур", "ПРОВЕРКА",
                   "Сырые движения, утверждённые корректировки и месячный баланс по КБК.")
    demo = st.toggle("Показать демонстрационный набор", value=True, key="cash_demo")
    if demo:
        status_banner("ДЕМО · СИНТЕТИЧЕСКИЕ ДАННЫЕ", "Четыре условных месяца 2026 года.",
                      "Суммы в млн ₽ придуманы для проверки расчёта. Они не отражают бюджет Сургута.", tone="warning")
        lines, corrections = demo_cash()
        sample = pd.DataFrame([row.__dict__ for row in lines])
        st.download_button("Скачать шаблон кассовых строк CSV", sample.to_csv(index=False).encode("utf-8-sig"),
                           "mesm_cash_example.csv", "text/csv")
        correction_sample = pd.DataFrame([row.__dict__ for row in corrections])
        st.download_button("Скачать шаблон корректировок CSV", correction_sample.to_csv(index=False).encode("utf-8-sig"),
                           "mesm_corrections_example.csv", "text/csv")
    else:
        status_banner("ЛОКАЛЬНАЯ ПРОВЕРКА", "Загруженные файлы используются только в текущем сеансе.",
                      "Проверяйте единицы измерения, КБК и даты публикации. Файлы не сохраняются в репозитории.", tone="info")
        cash_file = st.file_uploader("Кассовые строки CSV", type="csv", key="cash_lines")
        corrections_file = st.file_uploader("Утверждённые корректировки CSV", type="csv", key="cash_corrections")
        if cash_file is None:
            st.info("Загрузите строки исполнения. Для примера включите демонстрационный набор и скачайте шаблоны.")
            return
        try:
            lines = parse_cash_csv(cash_file.getvalue())
            corrections = parse_corrections_csv(corrections_file.getvalue()) if corrections_file else []
        except (ValueError, UnicodeError, pd.errors.ParserError) as exc:
            st.error(f"Файл не принят: {exc}")
            return
    unit = st.selectbox("Единицы сумм", ["руб.", "тыс. руб.", "млн руб."],
                        index=2 if demo else 0, key="cash_unit")
    as_of = st.date_input("Данные, доступные на дату", value=date.today(), key="cash_asof")
    try:
        eligible = [row for row in lines if row.available_at <= as_of]
        if not eligible:
            st.warning("На выбранную дату ни одна строка ещё не была доступна.")
            return
        municipalities = sorted({row.municipality for row in eligible})
        selected = st.selectbox("Муниципалитет", municipalities, key="cash_municipality")
        sources = sorted({row.source for row in eligible if row.municipality == selected})
        source = st.selectbox("Источник кассовых строк", sources, key="cash_source")
        monthly = monthly_from_ytd([row for row in eligible if row.municipality == selected and row.source == source])
        result = normalize_cash(monthly, corrections, as_of=as_of, municipality=selected, source=source)
    except ValueError as exc:
        st.error(f"Расчёт остановлен: {exc}")
        return
    if not result:
        st.warning("Нет строк для выбранного источника.")
        return
    latest = result[-1]
    metric_grid([
        {"label": "Кассовые доходы", "value": f"{latest.raw_revenue:,.1f}", "meta": f"за месяц · {unit}", "tone": "info"},
        {"label": "Регулярные доходы", "value": f"{latest.normalized_revenue:,.1f}", "meta": "после утверждённых поправок", "tone": "positive"},
        {"label": "Кассовый остаток", "value": f"{latest.cash_balance:,.1f}", "meta": "начальный остаток 0 · условно", "tone": "warning" if latest.cash_balance < 0 else "info"},
        {"label": "Потребность в покрытии", "value": f"{latest.reserve_need:,.1f}", "meta": "при отрицательном остатке", "tone": "danger" if latest.reserve_need else "muted"},
    ])
    frame = pd.DataFrame([row.__dict__ for row in result])
    fig = go.Figure()
    for name, column, color, dash in [("Доходы касса", "raw_revenue", "#6F6F6F", "solid"),
                                      ("Доходы регулярные", "normalized_revenue", "#D71920", "solid"),
                                      ("Расходы касса", "raw_expenditure", "#315EAA", "dash")]:
        fig.add_trace(go.Scatter(x=frame["month"], y=frame[column], name=name,
                                 mode="lines+markers", line=dict(color=color, width=3, dash=dash)))
    fig.update_layout(title="Движение по месяцам", height=370, template="plotly_white",
                      margin=dict(l=20, r=20, t=50, b=20), yaxis_title=unit,
                      legend=dict(orientation="h", y=1.14))
    st.plotly_chart(fig, use_container_width=True)
    section_header("Проверка расчёта", "АУДИТ", "Кассовые суммы сохраняются отдельно от аналитического ряда.")
    display = frame.rename(columns={"month": "Месяц", "raw_revenue": "Доходы касса",
                                    "normalized_revenue": "Доходы регулярные", "raw_expenditure": "Расходы касса",
                                    "cash_balance": "Остаток", "reserve_need": "Потребность", "status": "Статус"})
    st.dataframe(display[["Месяц", "Доходы касса", "Доходы регулярные", "Расходы касса",
                          "Остаток", "Потребность", "Статус"]], hide_index=True, use_container_width=True)
    if corrections:
        with st.expander(f"Журнал корректировок · {len(corrections)}"):
            st.dataframe(pd.DataFrame([row.__dict__ for row in corrections]), hide_index=True, use_container_width=True)
    st.caption("Месячный план и реальный начальный остаток подключаются после согласования источника. «Разрыв нормализации» бюджетных лимитов здесь не пересчитывается.")
