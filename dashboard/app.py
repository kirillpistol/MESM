from __future__ import annotations

import html
import math
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from random import Random
from statistics import mean, pstdev

import pandas as pd
import streamlit as st

from mesm.budget.normalization import BudgetInputs, calculate_budget
from mesm.budget.project import group_structure
from mesm.data.intake import load_current_dataset, resolve_dataset_path
from mesm.evaluation.forecast_benchmark import benchmark_metrics, expanding_forecast_table
from mesm.models.changepoint import cusum_flags, pelt_breakpoints
from mesm.models.economic_interpretation import current_domain_assessments
from mesm.models.interpretation import reference_screening_flags, screening_conclusion
from mesm.models.state_machine import HysteresisStateMachine, StateMachineConfig
from mesm.predictive.external import coverage as external_coverage, extract_series
from mesm.reporting.decision_memo import build_decision_memo
from charts import (
    bo_history_chart,
    budget_waterfall_chart,
    expenditure_structure_chart,
    forecast_actual_chart,
    reference_trend_chart,
    shock_monitor_chart,
    model_tournament_chart,
    competition_forecast_chart,
    shock_benchmark_chart,
    shock_calibration_chart,
)
from intake_ui import render_data_intake
from source_monitor import load_source_manifest, pipeline_snapshot, source_status_frame
from ui import (
    app_header,
    budget_path,
    inject_control_room_css,
    hero_panel,
    metric_grid,
    pipeline,
    section_header,
    sidebar_brand,
    source_card,
    status_banner,
    system_bar,
    tone_for_status,
)

ROOT = Path(__file__).resolve().parents[1]
PANEL_PATH = ROOT / "data" / "processed" / "fiscal_reference_panel.csv"
BO_PATH = resolve_dataset_path("budget_provision", ROOT)
MODEL_TOURNAMENT_PATH = ROOT / "data" / "reports" / "competition" / "surgut_2024_dev_benchmark.csv"
PROPHET_PREDICTIONS_PATH = ROOT / "data" / "reports" / "competition" / "surgut_2024_prophet_predictions.csv"
GROW_PREDICTIONS_PATH = ROOT / "data" / "reports" / "competition" / "surgut_2024_grow_predictions.csv"
SHOCK_SUMMARY_PATH = ROOT / "data" / "reports" / "competition" / "shock_benchmark_summary.csv"
SHOCK_CALIBRATION_PATH = ROOT / "data" / "reports" / "competition" / "shock_calibration_summary.csv"


def ensure_panel() -> None:
    if PANEL_PATH.exists():
        return
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_fiscal_reference_panel.py")],
        cwd=ROOT,
        check=True,
    )


def pct(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:.1%}"


def number(value: float | None, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:,.{digits}f}".replace(",", " ")


def latest_value(frame: pd.DataFrame, column: str) -> float | None:
    if frame.empty or column not in frame:
        return None
    series = frame[column].dropna()
    return None if series.empty else float(series.iloc[-1])


def peer_values(frame: pd.DataFrame, year: int | None, column: str) -> list[float]:
    if year is None or column not in frame:
        return []
    return [float(v) for v in frame.loc[frame["year"] == year, column].dropna().tolist()]


def stress_demo(shock_sigma: float, duration: int, direction: str) -> pd.DataFrame:
    rng = Random(42)
    base = [rng.gauss(0.0, 1.0) for _ in range(48)]
    start = 30
    sign = -1.0 if direction == "Падение" else 1.0
    values = list(base)
    for i in range(start, min(start + duration, len(values))):
        values[i] += sign * shock_sigma

    warmup = 12
    mu = mean(values[:warmup])
    sigma = pstdev(values[:warmup]) or 1.0
    z = [(v - mu) / sigma for v in values]
    cusum = cusum_flags(values, threshold=5.0, drift=0.5, warmup=warmup)

    try:
        raw_breaks = pelt_breakpoints(values, penalty=3.0)
        pelt = [bp for bp in raw_breaks if bp < len(values)]
    except RuntimeError:
        pelt = []

    sm = HysteresisStateMachine(
        StateMachineConfig(
            on_threshold=2.0,
            off_threshold=1.0,
            k_on=2,
            k_off=2,
            break_persistence=3,
            min_confirmations=2,
        )
    )

    rows = []
    for i, value in enumerate(values):
        pelt_near = any(abs(i - bp) <= 1 for bp in pelt)
        confirmations = int(cusum[i]) + int(pelt_near)
        update = sm.update(abs(z[i]), confirmations=confirmations)
        rows.append(
            {
                "period": i + 1,
                "residual": value,
                "z_score": z[i],
                "cusum_alarm": cusum[i],
                "pelt_near": pelt_near,
                "confirmations": confirmations,
                "state": update.state.value,
                "reason": update.reason,
                "shock_window": start <= i < start + duration,
            }
        )
    return pd.DataFrame(rows)


def make_report_html(
    municipality: str,
    latest_year: int | None,
    latest: pd.DataFrame,
    flags,
    conclusion: str,
    selected_bo: pd.DataFrame,
    decision_memo=None,
    budget_result=None,
) -> str:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    municipality_display = (str(municipality).strip() if municipality is not None else "") or "Муниципалитет не выбран"
    metrics = [
        ("Отклонение доходов от первоначального плана", pct(latest_value(latest, "income_plan_deviation"))),
        ("Доля программных расходов", pct(latest_value(latest, "program_expense_share"))),
        ("Изменений бюджета", number(latest_value(latest, "budget_amendments"), 0)),
        ("Долговая нагрузка", pct(latest_value(latest, "debt_load"))),
        ("Официальный ранг", number(latest_value(latest, "quality_rank"), 0)),
    ]
    metrics_html = "".join(
        f"<tr><td>{html.escape(name)}</td><td><b>{html.escape(value)}</b></td></tr>"
        for name, value in metrics
    )
    flags_html = "".join(
        f"<li><b>{'ФЛАГ' if flag.active else 'нет флага'} — {html.escape(flag.title)}</b>: "
        f"{html.escape(flag.explanation)}</li>"
        for flag in flags
    )

    memo_html = "<p>Decision-ready summary пока не сформирован.</p>"
    if decision_memo is not None:
        checks = "".join(f"<li>{html.escape(item)}</li>" for item in decision_memo.next_checks)
        memo_html = (
            f"<p><b>{html.escape(decision_memo.headline)}</b></p>"
            f"<p>{html.escape(decision_memo.what_changed)}</p>"
            f"<p>{html.escape(decision_memo.evidence)}</p>"
            f"<p>{html.escape(decision_memo.interpretation)}</p>"
            f"<p><b>Что проверить дальше</b></p><ul>{checks}</ul>"
            f"<p><i>{html.escape(decision_memo.limitation)}</i></p>"
        )

    budget_html = "<p>Расчет нормализации бюджета не задан.</p>"
    if budget_result is not None:
        budget_html = (
            "<table>"
            f"<tr><td>Дефицит</td><td><b>{number(budget_result.deficit)}</b></td></tr>"
            f"<tr><td>Дефицит / база</td><td><b>{pct(budget_result.deficit_ratio)}</b></td></tr>"
            f"<tr><td>Допустимый дефицит</td><td><b>{number(budget_result.allowed_deficit)}</b></td></tr>"
            f"<tr><td>Разрыв нормализации</td><td><b>{number(budget_result.normalization_gap)}</b></td></tr>"
            f"<tr><td>Структурный разрыв</td><td><b>{number(budget_result.structural_gap)}</b></td></tr>"
            f"<tr><td>Разрыв финансирования</td><td><b>{number(budget_result.financing_gap)}</b></td></tr>"
            "</table>"
        )

    bo_html = "<p>История БО для выбранного муниципалитета отсутствует в текущем наборе.</p>"
    if not selected_bo.empty:
        rows = []
        for _, row in selected_bo.iterrows():
            rows.append(
                "<tr>"
                f"<td>{int(row['year'])}</td>"
                f"<td>{html.escape(str(row['period']))}</td>"
                f"<td>{number(row.get('bo_actual'), 3)}</td>"
                f"<td>{number(row.get('bo_calculated'), 3)}</td>"
                f"<td>{number(row.get('revenue_shortfall'), 1)}</td>"
                "</tr>"
            )
        bo_html = (
            "<table><tr><th>Год</th><th>Период</th><th>БО факт</th><th>БО расчет</th>"
            "<th>Недостаток доходов</th></tr>"
            + "".join(rows)
            + "</table>"
        )

    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>MESM — {html.escape(municipality_display)}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 36px; color: #202124; }}
h1 {{ margin-bottom: 0; }} h2 {{ margin-top: 28px; }}
table {{ border-collapse: collapse; width: 100%; margin: 14px 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
.note {{ background: #f3f4f6; padding: 14px; border-left: 4px solid #777; }}
</style>
</head>
<body>
<h1>MESM</h1>
<p><b>Municipal Economic Shock Monitor</b></p>
<p>Муниципалитет: <b>{html.escape(municipality_display)}</b><br>
Последний год в Reference Panel: <b>{latest_year or '—'}</b><br>
Сформировано: {generated}</p>

<h2>0. Decision-ready summary</h2>
{memo_html}

<h2>1. Нормализация бюджета</h2>
{budget_html}

<h2>2. Текущий Reference-срез</h2>
<table>{metrics_html}</table>

<h2>3. Скрининговые сигналы</h2>
<ul>{flags_html}</ul>

<h2>4. Интерпретация</h2>
<div class="note">{html.escape(conclusion)}</div>

<h2>5. Бюджетная обеспеченность (БО)</h2>
{bo_html}

<h2>6. Экономическая интерпретация</h2>
<p>Текущий публичный контур полноценно покрывает прежде всего Municipal Finance.
Отсутствие данных по Consumer Demand, Income & Labour, Cost of Living, Business Activity
и Economic Structure не трактуется как NORMAL.</p>

<h2>7. Что означает вывод</h2>
<p>Скрининговый флаг не равен структурному шоку. Для перехода к WARNING или
BREAK_CONFIRMED MESM должен увидеть временную устойчивость сигнала и независимое
подтверждение детекторами. Predictive-контур с реальными высокочастотными данными
пока не подключен.</p>

<h2>8. Ограничения</h2>
<p>Текущая версия — исследовательский прототип на публичных бюджетных данных.
ReferenceScore еще не откалиброван на полноценном историческом backtest, поэтому
отчет не присваивает фиктивное состояние NORMAL/WARNING.</p>
</body>
</html>"""


st.set_page_config(page_title="MESM Control Room", page_icon="📊", layout="wide")
inject_control_room_css()

ensure_panel()

panel = pd.read_csv(PANEL_PATH, encoding="utf-8-sig")
panel["year"] = panel["year"].astype(int)
panel = panel.sort_values(["municipality_name", "year"])

bo = pd.read_csv(BO_PATH, encoding="utf-8-sig") if BO_PATH.exists() else pd.DataFrame()
if not bo.empty:
    bo["year"] = bo["year"].astype(int)
    bo = bo.sort_values(["municipality_name", "year"])

external = load_current_dataset("external_monthly", ROOT)
external_cov = external_coverage(external) if not external.empty else None
reference_core = load_current_dataset("reference_core", ROOT)
budget_official_plan = load_current_dataset("budget_official_plan", ROOT)
budget_project = load_current_dataset("budget_project", ROOT)

sidebar_brand()
page = st.sidebar.radio(
    "Навигация",
    ["Обзор", "Модели", "Бюджет", "Монитор шоков", "БО", "Отчёт", "Источники", "Данные", "Ввод данных", "Методика"],
    index=0,
    label_visibility="collapsed",
)
st.sidebar.markdown('<div class="mesm-sidebar-label">КОНТЕКСТ</div>', unsafe_allow_html=True)

app_header(
    "MESM",
    "Муниципальный монитор экономических изменений",
    "Прогноз · структурные изменения · официальные данные",
)

municipalities = sorted({str(v).strip() for v in panel["municipality_name"].dropna().tolist() if str(v).strip()})
if municipalities:
    default_index = municipalities.index("Сургут") if "Сургут" in municipalities else 0
    municipality = st.sidebar.selectbox("Муниципалитет", municipalities, index=default_index)
else:
    municipality = None
    st.sidebar.error("В активном Reference Panel нет корректных municipality_name. Исправьте данные во вкладке «Ввод данных».")
st.sidebar.markdown("---")
st.sidebar.caption("Публичный исследовательский интерфейс. Банковские данные в репозиторий не входят.")

current = panel[panel["municipality_name"] == municipality].copy()
latest = current.sort_values("year").tail(1)
latest_year = int(latest["year"].iloc[0]) if not latest.empty else None
selected_bo = bo[bo["municipality_name"] == municipality].copy() if not bo.empty else pd.DataFrame()

flags = reference_screening_flags(
    income_plan_deviation=latest_value(latest, "income_plan_deviation"),
    debt_load=latest_value(latest, "debt_load"),
    debt_peer_values=peer_values(panel, latest_year, "debt_load"),
    budget_amendments=latest_value(latest, "budget_amendments"),
    amendment_peer_values=peer_values(panel, latest_year, "budget_amendments"),
    quality_rank=latest_value(latest, "quality_rank"),
    quality_peer_values=peer_values(panel, latest_year, "quality_rank"),
)
conclusion = screening_conclusion(flags)
domains = current_domain_assessments(
    income_plan_deviation=latest_value(latest, "income_plan_deviation"),
    debt_load=latest_value(latest, "debt_load"),
    budget_amendments=latest_value(latest, "budget_amendments"),
    flags=flags,
)
fiscal = next(item for item in domains if item.domain == "Municipal Finance")
benchmark_ready = False
if not external.empty:
    grouped_sizes = external.groupby(["geography_name", "variable"]).size()
    benchmark_ready = bool((grouped_sizes >= 25).any())

decision_memo = build_decision_memo(
    fiscal,
    external_loaded=not external.empty,
    external_variables=external_cov.variables if external_cov is not None else 0,
    benchmark_ready=benchmark_ready,
)

budget_result = None
source_status = source_status_frame(ROOT)
source_manifest = load_source_manifest(ROOT)
pipeline_state = pipeline_snapshot(ROOT)

competition_tournament = pd.DataFrame()
if MODEL_TOURNAMENT_PATH.exists():
    competition_tournament = pd.read_csv(MODEL_TOURNAMENT_PATH, encoding="utf-8-sig")
    competition_tournament["mae"] = pd.to_numeric(competition_tournament["mae"], errors="coerce")
    competition_tournament["r2"] = pd.to_numeric(competition_tournament["r2"], errors="coerce")

shock_summary = pd.read_csv(SHOCK_SUMMARY_PATH, encoding="utf-8-sig") if SHOCK_SUMMARY_PATH.exists() else pd.DataFrame()
shock_calibration = pd.read_csv(SHOCK_CALIBRATION_PATH, encoding="utf-8-sig") if SHOCK_CALIBRATION_PATH.exists() else pd.DataFrame()

selected_official_plan = pd.DataFrame()
if not budget_official_plan.empty and municipality is not None:
    selected_official_plan = budget_official_plan[
        budget_official_plan["municipality_name"].astype(str).str.strip().eq(str(municipality).strip())
    ].copy()

system_bar(
    municipality=municipality or "—",
    year=latest_year,
    data_status="ОФИЦИАЛЬНЫЕ" if not selected_official_plan.empty else "СПРАВОЧНЫЕ",
    pipeline_status="ГОТОВ" if pipeline_state["fiscal_panel_ready"] else "ПРОВЕРКА",
)

if page == "Ввод данных":
    render_data_intake(ROOT)

if page == "Обзор":
    if municipality is None:
        st.warning("Нет выбранного муниципалитета. Сначала загрузите корректный Reference Core во вкладке «Ввод данных».")
    st.subheader(f"{municipality or 'Муниципалитет не выбран'}: экономический срез")

    leader_name="—"
    leader_mae="—"
    prophet_delta="—"
    if not competition_tournament.empty:
        ranked_overview=competition_tournament.dropna(subset=["mae"]).sort_values("mae")
        if not ranked_overview.empty:
            leader_overview=ranked_overview.iloc[0]
            leader_name=str(leader_overview["model"])
            leader_mae=f"{float(leader_overview['mae']):,.0f} ₽".replace(",", " ")
            prophet_overview=ranked_overview[ranked_overview["model"].astype(str).eq("Prophet")]
            if not prophet_overview.empty:
                prophet_value=float(prophet_overview["mae"].iloc[0])
                prophet_delta=f"{(prophet_value-float(leader_overview['mae']))/prophet_value:.1%}"

    online_leader="—"
    if not shock_summary.empty:
        online=shock_summary[
            shock_summary["event_type"].astype(str).eq("REGIME_SHIFT")
            & shock_summary["detector"].astype(str).isin(["CUSUM","PAGE_HINKLEY"])
        ].copy()
        if not online.empty:
            online["detection_rate"]=pd.to_numeric(online["detection_rate"],errors="coerce")
            online_leader=str(online.sort_values("detection_rate",ascending=False).iloc[0]["detector"]).replace("_"," ").title()

    hero_panel(
        "Основной контур · Сургут",
        "Прогноз потребительских расходов и выявление структурных изменений",
        "Сургут — основной кейс. ХМАО — обучающая сеть. Все модельные сравнения проходят на одинаковом temporal holdout 2024.",
        [
            {"label":"Объект","value":"71876000","meta":"ОКТМО · Сургут"},
            {"label":"Лучшая модель","value":leader_name,"meta":f"MAE {leader_mae}"},
            {"label":"Улучшение к Prophet","value":prophet_delta,"meta":"снижение MAE"},
            {"label":"Online-детектор","value":online_leader,"meta":"устойчивый сдвиг"},
        ],
    )
    pipeline([
        ("ДАННЫЕ", "СберИндекс + официальные муниципальные данные"),
        ("ПРОГНОЗ", "ожидаемая траектория расходов"),
        ("ИЗМЕНЕНИЕ", "поиск устойчивого отклонения и подтверждение"),
    ])

    section_header(
        "Текущее состояние",
        "ОБЗОР",
        "Сначала состояние и доказательность, затем технический drill-down.",
    )
    metric_grid([
        {"label": "Муниципальные финансы", "value": fiscal.status.value, "meta": "reference layer", "tone": tone_for_status(fiscal.status.value)},
        {"label": "Доказательность", "value": fiscal.evidence.value, "meta": "confidence", "tone": tone_for_status(fiscal.evidence.value)},
        {"label": "Внешние данные", "value": "НЕТ ДАННЫХ" if external_cov is None else f"{external_cov.variables} vars", "meta": "high-frequency layer", "tone": "muted" if external_cov is None else "info"},
        {"label": "Прогнозный статус", "value": "НЕ РАССЧИТАН", "meta": "temporal confirmation", "tone": "muted"},
    ])
    status_banner(
        fiscal.status.value,
        fiscal.headline,
        fiscal.interpretation,
        tone=tone_for_status(fiscal.status.value),
    )

    section_header("Экономические области", "ОБЛАСТИ", "Покрытие и доказательность по ключевым областям экономики.")
    domain_frame = pd.DataFrame([
        {
            "Область": item.domain,
            "Статус": item.status.value,
            "Доказательность": item.evidence.value,
            "Вывод": item.headline,
        }
        for item in domains
    ])
    st.dataframe(domain_frame, use_container_width=True, hide_index=True)

    with st.expander("Технические Reference-показатели"):
        cols = st.columns(5)
        cols[0].metric("Доходы к первоначальному плану", pct(latest_value(latest, "income_plan_deviation")))
        cols[1].metric("Программные расходы", pct(latest_value(latest, "program_expense_share")))
        cols[2].metric("Изменений бюджета", number(latest_value(latest, "budget_amendments"), 0))
        cols[3].metric("Долговая нагрузка", pct(latest_value(latest, "debt_load")))
        cols[4].metric("Официальный ранг", number(latest_value(latest, "quality_rank"), 0))
        st.write(conclusion)
        for flag in flags:
            icon = "⚠️" if flag.active else "✓"
            st.markdown(f"**{icon} {flag.title}** — {flag.explanation}")

    section_header("Динамика Reference-признаков", "ДИНАМИКА", "Годовые признаки публичного Reference Layer.")
    st.plotly_chart(
        reference_trend_chart(current),
        use_container_width=True,
        config={"displayModeBar": False, "responsive": True},
    )

if page == "Модели":
    st.subheader("Модельный турнир · Сургут")
    hero_panel(
        "Сравнение моделей · 2024 OOS",
        "Одинаковый период проверки для всех моделей",
        "Главная метрика — MAE. Prophet используется как конкурсный baseline, Grow — текущий development challenger.",
        [
            {"label":"Объект","value":"Сургут","meta":"ОКТМО 71876000"},
            {"label":"Проверка","value":"12 мес.","meta":"янв–дек 2024"},
            {"label":"Метрика","value":"MAE","meta":"основная метрика"},
            {"label":"Сетка","value":"19 ОКТМО","meta":"муниципалитеты ХМАО"},
        ],
    )
    section_header(
        "Сравнение прогнозов",
        "2024 OOS",
        "Одинаковые 12 фактических месяцев 2024 года; основная метрика конкурса — MAE.",
    )
    if not MODEL_TOURNAMENT_PATH.exists():
        st.warning("Файл model tournament пока не сформирован.")
    else:
        tournament = pd.read_csv(MODEL_TOURNAMENT_PATH, encoding="utf-8-sig")
        tournament["mae"] = pd.to_numeric(tournament["mae"], errors="coerce")
        tournament["r2"] = pd.to_numeric(tournament["r2"], errors="coerce")
        ranked = tournament.sort_values("mae").reset_index(drop=True)
        leader = ranked.iloc[0]
        prophet_rows = ranked[ranked["model"].astype(str).eq("Prophet")]
        prophet_mae = float(prophet_rows["mae"].iloc[0]) if not prophet_rows.empty else None
        improvement = (
            (prophet_mae - float(leader["mae"])) / prophet_mae
            if prophet_mae and prophet_mae != 0 else None
        )
        metric_grid([
            {"label": "Текущий лидер", "value": str(leader["model"]), "meta": "минимальный MAE за 2024", "tone": "positive"},
            {"label": "MAE лидера", "value": f"{float(leader['mae']):,.0f} ₽".replace(",", " "), "meta": "12 OOS months", "tone": "positive"},
            {"label": "Prophet MAE", "value": "—" if prophet_mae is None else f"{prophet_mae:,.0f} ₽".replace(",", " "), "meta": "тот же период проверки", "tone": "neutral"},
            {"label": "к Prophet", "value": "—" if improvement is None else f"{improvement:.1%}", "meta": "снижение MAE", "tone": "positive" if improvement and improvement > 0 else "warning"},
        ])
        st.plotly_chart(
            model_tournament_chart(ranked),
            use_container_width=True,
            config={"displayModeBar": False, "responsive": True},
        )
        if PROPHET_PREDICTIONS_PATH.exists() and GROW_PREDICTIONS_PATH.exists():
            section_header(
                "Факт и прогноз",
                "СРАВНЕНИЕ",
                "Месячный факт СберИндекса против двух основных конкурсных моделей.",
            )
            prophet_predictions=pd.read_csv(PROPHET_PREDICTIONS_PATH,encoding="utf-8-sig")
            grow_predictions=pd.read_csv(GROW_PREDICTIONS_PATH,encoding="utf-8-sig")
            st.plotly_chart(
                competition_forecast_chart(prophet_predictions,grow_predictions),
                use_container_width=True,
                config={"displayModeBar": False, "responsive": True},
            )
        display = ranked[["model", "observations", "mae", "r2", "wape", "rmse", "mase", "status"]].copy()
        st.dataframe(
            display.style.format({
                "mae": "{:,.2f}",
                "r2": "{:.3f}",
                "wape": "{:.2%}",
                "rmse": "{:,.2f}",
                "mase": "{:.3f}",
            }),
            use_container_width=True,
            hide_index=True,
        )
        status_banner(
            "ТЕКУЩИЙ ЛИДЕР",
            "Grow уже снижает MAE относительно Prophet.",
            "Финальный champion не фиксируется, пока peer-сетка ХМАО не разрешена по официальным ОКТМО и результат не повторен на полном reproducible pipeline.",
            tone="warning",
        )

if page == "Бюджет":
    st.subheader("Нормализация бюджета")

    official_rows = pd.DataFrame()
    if not budget_official_plan.empty and municipality is not None:
        official_rows = budget_official_plan[
            budget_official_plan["municipality_name"].astype(str).str.strip()
            == str(municipality).strip()
        ].copy()

    if official_rows.empty:
        st.warning("Нет официальных параметров бюджета для выбранного муниципалитета.")
    else:
        official_rows["year"] = pd.to_numeric(official_rows["year"], errors="coerce").astype(int)
        years = sorted(official_rows["year"].unique().tolist())
        budget_year = st.selectbox("Год", years, index=0)
        selected_plan = official_rows[official_rows["year"] == budget_year].iloc[-1]

        revenue_base = float(selected_plan["revenue_base"])
        transfers = float(selected_plan["transfers"])
        expenditure = float(selected_plan["expenditure"])
        eligible_exceptions = float(selected_plan["eligible_exceptions"])
        financing_sources = float(selected_plan["financing_sources"])
        debt_upper_limit = float(selected_plan.get("debt_upper_limit", 0.0) or 0.0)
        debt_service = float(selected_plan.get("debt_service", 0.0) or 0.0)

        budget_inputs = BudgetInputs(
            revenue_base=revenue_base,
            transfers=transfers,
            expenditure=expenditure,
            eligible_exceptions=eligible_exceptions,
            current_debt=debt_upper_limit,
            debt_service=debt_service,
            expenditure_ex_subventions=expenditure,
            financing_sources=financing_sources,
            deficit_limit_ratio=0.10,
            debt_limit_ratio=1.00,
            debt_service_limit_ratio=0.15,
        )
        budget_result = calculate_budget(budget_inputs)

        section_header("Budget snapshot", "OFFICIAL PLAN", f"Официальный бюджетный контур · {budget_year}")
        metric_grid([
            {"label": "Revenue", "value": f"{float(selected_plan['total_revenue']) / 1_000_000:.3f} млрд ₽", "meta": "total revenue", "tone": "neutral"},
            {"label": "Expenditure", "value": f"{expenditure / 1_000_000:.3f} млрд ₽", "meta": "total expenditure", "tone": "neutral"},
            {"label": "Deficit", "value": f"{budget_result.deficit / 1_000_000:.3f} млрд ₽", "meta": pct(budget_result.deficit_ratio), "tone": "warning" if budget_result.deficit > 0 else "positive"},
            {"label": "Normalization gap", "value": f"{budget_result.normalization_gap / 1_000_000:.3f} млрд ₽", "meta": "after exceptions", "tone": "positive" if budget_result.normalization_gap <= 0 else "danger"},
        ])

        budget_path([
            ("Revenue base", revenue_base / 1_000_000, "база"),
            ("10% base limit", budget_result.base_deficit_limit / 1_000_000, "лимит"),
            ("Actual deficit", budget_result.deficit / 1_000_000, "факт"),
            ("Eligible exceptions", eligible_exceptions / 1_000_000, "исключения"),
            ("Normalization gap", budget_result.normalization_gap / 1_000_000, "итог"),
        ])

        metric_grid([
            {"label": "Financing sources", "value": f"{financing_sources / 1_000_000:.3f} млрд ₽", "meta": "official financing", "tone": "info"},
            {"label": "Financing gap", "value": f"{budget_result.financing_gap / 1_000_000:.3f} млрд ₽", "meta": "uncovered", "tone": "positive" if budget_result.financing_gap <= 0 else "danger"},
            {"label": "Debt / base", "value": pct(budget_result.debt_ratio), "meta": "upper debt limit", "tone": "warning" if budget_result.debt_ratio > 0.5 else "neutral"},
            {"label": "Debt service", "value": pct(budget_result.debt_service_ratio), "meta": "share of expenditure", "tone": "warning" if budget_result.debt_service_ratio > 0.10 else "neutral"},
        ])

        section_header("Доходы → баланс", "BUDGET FLOW", "Как собственные доходы и трансферты соотносятся с расходами.")
        st.plotly_chart(
            budget_waterfall_chart(revenue_base, transfers, expenditure),
            use_container_width=True,
            config={"displayModeBar": False, "responsive": True},
        )

        formula_table = pd.DataFrame([
            {"Показатель": "Доходная база", "Значение": revenue_base},
            {"Показатель": "Безвозмездные поступления", "Значение": transfers},
            {"Показатель": "Дефицит", "Значение": budget_result.deficit},
            {"Показатель": "10% доходной базы", "Значение": budget_result.base_deficit_limit},
            {"Показатель": "Разрыв до исключений", "Значение": budget_result.raw_normalization_gap},
            {"Показатель": "Допустимые исключения", "Значение": eligible_exceptions},
            {"Показатель": "Допустимый дефицит", "Значение": budget_result.allowed_deficit},
            {"Показатель": "Разрыв после исключений", "Значение": budget_result.normalization_gap},
        ])
        section_header("Расчет", "FORMULA TRACE", "Промежуточные значения, из которых MESM получает итоговый разрыв.")
        st.dataframe(
            formula_table.style.format({"Значение": "{:,.2f}"}),
            use_container_width=True,
            hide_index=True,
        )

        project_rows = pd.DataFrame()
        if not budget_project.empty:
            project_rows = budget_project[
                (budget_project["municipality_name"].astype(str).str.strip() == str(municipality).strip())
                & (pd.to_numeric(budget_project["year"], errors="coerce") == budget_year)
            ].copy()

        if not project_rows.empty:
            section_header("Структура расходов", "EXPENDITURE MIX", "Крупнейшие разделы функциональной классификации бюджета.")
            expense_structure = group_structure(
                budget_project,
                municipality,
                budget_year,
                "EXPENDITURE",
            )
            st.plotly_chart(
                expenditure_structure_chart(expense_structure),
                use_container_width=True,
                config={"displayModeBar": False, "responsive": True},
            )
            with st.expander("Структура расходов — таблица"):
                st.dataframe(
                    expense_structure.style.format({
                        "amount": "{:,.2f}",
                        "share": "{:.1%}",
                    }),
                    use_container_width=True,
                    hide_index=True,
                )

        section_header("Источник", "DATA LINEAGE", "Документ, из которого построен текущий budget snapshot.")
        source_card(
            authority="Дума города Сургута / официальный бюджетный источник",
            document=str(selected_plan.get("source_document", "")),
            publication=str(selected_plan.get("publication_date", "")),
            stage=str(selected_plan.get("stage", "")),
            verification=str(selected_plan.get("exceptions_status", "")),
            url=str(selected_plan.get("source_url", "")),
        )

if page == "Монитор шоков":
    st.subheader("Монитор шоков")
    hero_panel(
        "Контур структурных изменений",
        "От ошибки прогноза к предупреждению и подтверждённому изменению режима",
        "Краткие аномалии и устойчивые regime shifts оцениваются отдельно. Online detection не смешивается с offline confirmation.",
        [
            {"label":"Online-лидер","value":"Page-Hinkley","meta":"32,3% · среднее выявление режима"},
            {"label":"Подтверждение","value":"PELT","meta":"38,5% · среднее выявление режима"},
            {"label":"Ложные тревоги","value":"≤ 10%","meta":"единый лимит FPR"},
            {"label":"Сильный сдвиг","value":"98,7%","meta":"Page-Hinkley · 3σ × 12 мес."},
        ],
    )
    section_header("Логика выявления", "МОНИТОР", "От отклонения от ожидания до подтвержденного изменения режима.")
    pipeline([
        ("ОЖИДАНИЕ", "прогноз лучшей модели"),
        ("ОШИБКА", "факт − прогноз"),
        ("Z-ОЦЕНКА", "масштаб отклонения"),
        ("ONLINE", "Page-Hinkley / CUSUM"),
        ("ПОДТВЕРЖДЕНИЕ", "PELT + интерпретация"),
    ])

    if not shock_summary.empty and not shock_calibration.empty:
        section_header(
            "Сравнение детекторов",
            "КОНТРОЛЬНЫЕ СЦЕНАРИИ",
            "Одинаковый false-alarm budget; transient shock и regime shift оцениваются раздельно.",
        )
        st.plotly_chart(
            shock_benchmark_chart(shock_summary),
            use_container_width=True,
            config={"displayModeBar": False, "responsive": True},
        )
        cols=st.columns([1.25,1])
        with cols[0]:
            st.plotly_chart(
                shock_calibration_chart(shock_calibration),
                use_container_width=True,
                config={"displayModeBar": False, "responsive": True},
            )
        with cols[1]:
            regime=shock_summary[shock_summary["event_type"].astype(str).eq("REGIME_SHIFT")].copy()
            regime["detection_rate"]=pd.to_numeric(regime["detection_rate"],errors="coerce")
            online=regime[regime["detector"].astype(str).isin(["CUSUM","PAGE_HINKLEY"])].sort_values("detection_rate",ascending=False)
            pelt=regime[regime["detector"].astype(str).eq("PELT")]
            metric_grid([
                {
                    "label":"Лучший online",
                    "value":"—" if online.empty else str(online.iloc[0]["detector"]).replace("_"," ").title(),
                    "meta":"устойчивый сдвиг",
                    "tone":"positive",
                },
                {
                    "label":"Выявление online",
                    "value":"—" if online.empty else f"{float(online.iloc[0]['detection_rate']):.1%}",
                    "meta":"среднее по сценарию",
                    "tone":"info",
                },
                {
                    "label":"Выявление PELT",
                    "value":"—" if pelt.empty else f"{float(pelt.iloc[0]['detection_rate']):.1%}",
                    "meta":"подтверждение после факта",
                    "tone":"neutral",
                },
                {
                    "label":"Точность PELT",
                    "value":"—" if pelt.empty else f"{float(pelt.iloc[0]['median_localization_error']):.1f} мес.",
                    "meta":"медианная ошибка",
                    "tone":"positive",
                },
            ], columns=2)

    st.markdown("#### Real External Data Layer")
    if external.empty:
        st.warning("External Data Layer: NO DATA")
    else:
        ext_cols = st.columns(4)
        ext_cols[0].metric("Строк", external_cov.rows)
        ext_cols[1].metric("Географий", external_cov.geographies)
        ext_cols[2].metric("Переменных", external_cov.variables)
        ext_cols[3].metric("Период", f"{external_cov.start_period[:7]} — {external_cov.end_period[:7]}")

        geographies = sorted(external["geography_name"].dropna().astype(str).unique().tolist())
        selected_geo = st.selectbox("География для benchmark", geographies, key="benchmark_geo")
        variables = sorted(
            external.loc[external["geography_name"].astype(str) == selected_geo, "variable"]
            .dropna().astype(str).unique().tolist()
        )
        selected_variable = st.selectbox("Показатель", variables, key="benchmark_variable")
        series = extract_series(external, selected_geo, selected_variable)

        if len(series) < 25:
            st.warning(f"Недостаточно данных: {len(series)} / 25 наблюдений")
        else:
            forecast_table = expanding_forecast_table(series, min_train=24, seasonality=12)
            metric_rows = benchmark_metrics(
                series[["period", "value"]],
                forecast_table,
                min_train=24,
                seasonality=12,
            )
            metrics_frame = pd.DataFrame([
                {
                    "Model": row.model,
                    "OOS observations": row.observations,
                    "MAE": row.mae,
                    "R²": row.r2,
                    "WAPE": row.wape,
                    "RMSE": row.rmse,
                    "MASE": row.mase,
                }
                for row in metric_rows
            ])
            st.markdown("**Forecast vs Actual — expanding one-step benchmark**")
            st.dataframe(metrics_frame.round(4), use_container_width=True, hide_index=True)

            st.plotly_chart(
                forecast_actual_chart(forecast_table),
                use_container_width=True,
                config={"displayModeBar": False, "responsive": True},
            )
            with st.expander("Forecast vs Actual — таблица"):
                st.dataframe(forecast_table.round(4), use_container_width=True, hide_index=True)

    st.markdown("#### Synthetic Demo")
    control_a, control_b = st.columns(2)
    shock_sigma = control_a.slider("Размер шока, σ", 0.5, 4.0, 2.5, 0.5)
    duration = control_b.slider("Длительность шока, периодов", 1, 6, 3, 1)
    direction = st.radio("Направление", ["Падение", "Рост"], horizontal=True)

    demo = stress_demo(shock_sigma, duration, direction)
    first_cusum = demo.loc[demo["cusum_alarm"], "period"]
    break_rows = demo.loc[demo["state"] == "BREAK_CONFIRMED", "period"]

    metric_grid([
        {"label": "Начало шока", "value": "период 31", "meta": "тестовый сценарий", "tone": "neutral"},
        {"label": "Первый сигнал CUSUM", "value": "—" if first_cusum.empty else f"период {int(first_cusum.iloc[0])}", "meta": "детектор", "tone": "info"},
        {"label": "BREAK_CONFIRMED", "value": "—" if break_rows.empty else f"период {int(break_rows.iloc[0])}", "meta": "смена состояния", "tone": "danger" if not break_rows.empty else "muted"},
        {"label": "Итоговое состояние", "value": str(demo.iloc[-1]["state"]), "meta": "state machine", "tone": tone_for_status(str(demo.iloc[-1]["state"]))},
    ])

    st.plotly_chart(
        shock_monitor_chart(demo),
        use_container_width=True,
        config={"displayModeBar": False, "responsive": True},
    )

    st.markdown("#### Расчеты детектора")
    st.dataframe(
        demo[[
            "period",
            "residual",
            "z_score",
            "cusum_alarm",
            "pelt_near",
            "confirmations",
            "state",
            "reason",
        ]].round({"residual": 3, "z_score": 3}),
        use_container_width=True,
        hide_index=True,
    )

if page == "БО":
    st.subheader("Бюджетная обеспеченность (БО)")
    if selected_bo.empty:
        st.warning("История БО для выбранного муниципалитета пока не загружена.")
    else:
        latest_bo = selected_bo.tail(1)
        metric_grid([
            {"label": "Фактическая БО", "value": number(latest_value(latest_bo, "bo_actual"), 3), "meta": "actual", "tone": "neutral"},
            {"label": "Расчетная БО", "value": number(latest_value(latest_bo, "bo_calculated"), 3), "meta": "calculated", "tone": "info"},
            {"label": "Недостаток доходов", "value": number(latest_value(latest_bo, "revenue_shortfall"), 1), "meta": "тыс. ₽", "tone": "warning"},
            {"label": "Население", "value": number(latest_value(latest_bo, "population"), 0), "meta": "people", "tone": "neutral"},
        ])

        st.plotly_chart(
            bo_history_chart(selected_bo),
            use_container_width=True,
            config={"displayModeBar": False, "responsive": True},
        )
        st.dataframe(
            selected_bo[[
                "year",
                "period",
                "population",
                "estimated_revenue",
                "estimated_obligations",
                "revenue_shortfall",
                "bo_actual",
                "bo_calculated",
                "equalization_support",
            ]],
            use_container_width=True,
            hide_index=True,
        )

if page == "Отчёт":
    st.subheader("Отчет MESM")
    section_header("Decision-ready summary", "EXECUTIVE OUTPUT", "Краткий вывод, пригодный для аналитической записки.")
    st.write(f"**{decision_memo.headline}**")
    st.write(decision_memo.what_changed)
    st.caption(decision_memo.evidence)
    st.write(decision_memo.interpretation)
    with st.expander("Что проверить дальше"):
        for item in decision_memo.next_checks:
            st.markdown(f"- {item}")
        st.caption(decision_memo.limitation)

    st.markdown("#### Reference-вывод")
    st.write(conclusion)

    report_html = make_report_html(
        municipality=municipality,
        latest_year=latest_year,
        latest=latest,
        flags=flags,
        conclusion=conclusion,
        selected_bo=selected_bo,
        decision_memo=decision_memo,
        budget_result=budget_result,
    )
    safe_name = ((str(municipality).strip() if municipality is not None else "") or "municipality").replace(" ", "_").replace("/", "_")
    st.download_button(
        "Скачать отчет HTML",
        data=report_html.encode("utf-8"),
        file_name=f"MESM_{safe_name}_{latest_year or 'current'}.html",
        mime="text/html",
        use_container_width=True,
    )
    st.download_button(
        "Скачать данные муниципалитета CSV",
        data=current.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"MESM_{safe_name}_reference.csv",
        mime="text/csv",
        use_container_width=True,
    )

if page == "Источники":
    st.subheader("Источники и pipeline")
    section_header(
        "Data lineage monitor",
        "PROVENANCE",
        "Настроенные официальные источники, локальный raw-слой и готовность расчетного контура.",
    )
    metric_grid([
        {"label": "Configured sources", "value": pipeline_state["configured_sources"], "meta": "official source pages", "tone": "info"},
        {"label": "Manifest files", "value": pipeline_state["manifest_files"], "meta": "downloaded raw files", "tone": "positive" if pipeline_state["manifest_files"] else "muted"},
        {"label": "Budget snapshot", "value": "READY" if pipeline_state["budget_snapshot_ready"] else "MISSING", "meta": "processed budget plan", "tone": "positive" if pipeline_state["budget_snapshot_ready"] else "danger"},
        {"label": "Fiscal panel", "value": "READY" if pipeline_state["fiscal_panel_ready"] else "MISSING", "meta": "reference panel", "tone": "positive" if pipeline_state["fiscal_panel_ready"] else "danger"},
    ])
    pipeline([
        ("SOURCE", "официальная веб-страница"),
        ("RAW", "XLS / XLSX / DOCX"),
        ("HASH", "SHA-256 manifest"),
        ("PROCESSED", "канонические CSV"),
        ("MODEL", "формулы и dashboard"),
    ])

    if source_manifest.empty:
        status_banner(
            "LOCAL RAW NOT LOADED",
            "Конфигурация источников есть, но manifest отсутствует в текущей локальной среде.",
            "Это штатно для GitHub: raw-файлы не коммитятся. Запустите UPDATE_OFFICIAL_DATA.bat, чтобы скачать оригиналы и записать SHA-256.",
            tone="muted",
        )
    else:
        status_banner(
            "RAW VERIFIED",
            f"В manifest зарегистрировано {len(source_manifest)} файлов.",
            "Каждый локальный raw-файл привязан к прямому URL и SHA-256.",
            tone="positive",
        )

    section_header("Официальные источники", "SOURCE REGISTRY", "Конфигурация и состояние каждого источника.")
    st.dataframe(
        source_status[[
            "source_id", "municipality_name", "document_type", "publication_date",
            "status", "manifest_files", "decision"
        ]],
        use_container_width=True,
        hide_index=True,
    )

    for row in source_status.to_dict("records"):
        source_card(
            authority=str(row["authority"]),
            document=str(row["decision"]),
            publication=str(row["publication_date"]),
            stage=str(row["document_type"]),
            verification=str(row["status"]),
            url=str(row["page_url"]),
        )

    if not source_manifest.empty:
        manifest_view = source_manifest.copy()
        if "sha256" in manifest_view:
            manifest_view["sha256"] = manifest_view["sha256"].astype(str).str.slice(0, 16) + "…"
        section_header("Raw manifest", "SHA-256", "Фактически скачанные файлы и их отпечатки.")
        st.dataframe(manifest_view, use_container_width=True, hide_index=True)

if page == "Данные":
    st.subheader("Канонические данные")
    st.dataframe(current, use_container_width=True, hide_index=True)
    if not selected_bo.empty:
        with st.expander("Расчетные данные БО"):
            st.dataframe(selected_bo, use_container_width=True, hide_index=True)
    if not external.empty:
        with st.expander("External Data Layer"):
            st.dataframe(external, use_container_width=True, hide_index=True)
    if not budget_official_plan.empty:
        with st.expander("Официальные параметры бюджета"):
            st.dataframe(budget_official_plan, use_container_width=True, hide_index=True)
    if not budget_project.empty:
        with st.expander("Структура бюджета"):
            st.dataframe(budget_project, use_container_width=True, hide_index=True)

if page == "Методика":
    st.subheader("Методология MESM")

    st.markdown(
        """
**Главная последовательность**

`Observation → Expected path → Residual → Z-score → Persistence → Change-point → Economic interpretation`

**Anomaly** — одиночное необычное наблюдение.  
**Signal** — отклонение достаточно велико, чтобы продолжить наблюдение.  
**Early warning** — отклонение устойчиво и получает независимое подтверждение.  
**Structural shift** — изменяется режим поведения: уровень, тренд, волатильность, структура или связь факторов.

Для одного временного контура используются состояния:

`NORMAL → OBSERVE → WARNING → BREAK_CONFIRMED`

Но текущий годовой Reference-скрининг **не присваивает WARNING или BREAK_CONFIRMED**:
для этого нужен temporal backtest и подтверждение во времени.

### Экономические области

MESM оценивает Consumer Demand, Income & Labour, Cost of Living, Business Activity,
Municipal Finance и Economic Structure. Если данных нет, область получает `NO_DATA`,
а не искусственный `NORMAL`.

### Что является доказательством

`BREAK_CONFIRMED = Persistence ∧ DetectorConfirmation ∧ EconomicInterpretability`

Один плохой показатель или один детектор не подтверждает structural break.

### Lead Time

`LeadTime = Reference confirmation date − Predictive signal date`

Положительный Lead Time означает, что Predictive Layer увидел изменение раньше
официальной Reference-точки.

Полная версия методологии сохранена в `docs/16_methodology_v1.md`.
        """
    )
