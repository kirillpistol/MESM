from __future__ import annotations

import math
from datetime import date

import plotly.graph_objects as go
import streamlit as st

from mesm.budget.cash_execution import ManualCorrection, CashMonth
from ui import section_header


def revenue_steps(month: CashMonth, corrections: list[ManualCorrection], *,
                  municipality: str, as_of: date) -> list[tuple[str, float]]:
    """Показать только поправки, использованные для выбранного месячного результата."""
    steps = []
    labels = {'REFUND_REALLOCATION': 'Перенос возврата', 'ADVANCE_REALLOCATION': 'Перенос аванса', 'ONE_OFF': 'Разовое поступление'}
    for row in corrections:
        if row.municipality != municipality or row.side != 'REVENUE' or row.approved_at > as_of:
            continue
        if row.effective_date is not None and row.effective_date > as_of:
            continue
        delta = row.amount if row.kind == 'REFUND_REALLOCATION' else -row.amount
        if row.cash_month == month.month:
            steps.append((f'{labels.get(row.kind, row.kind)} · {row.correction_id}', delta))
        if row.target_month == month.month:
            steps.append((f'Отнесено к месяцу · {row.correction_id}', -delta))
    if not math.isclose(month.raw_revenue + sum(v for _, v in steps), month.normalized_revenue, rel_tol=1e-9, abs_tol=1e-8):
        raise ValueError('Расшифровка поправок не совпала с расчётом регулярных доходов')
    return steps


def render_cash_calculation(result: list[CashMonth], corrections: list[ManualCorrection], *,
                            municipality: str, as_of: date, unit: str, opening_balance: float) -> None:
    section_header('От суммы к результату', 'РАСШИФРОВКА', 'Выберите месяц: каждый шаг графика соответствует утверждённой поправке.')
    selected = st.selectbox('Месяц для разбора расчёта', range(len(result)), index=len(result)-1,
                            format_func=lambda i: result[i].month.strftime('%m.%Y'), key='cash_explain_month')
    month = result[selected]
    try:
        steps = revenue_steps(month, corrections, municipality=municipality, as_of=as_of)
    except ValueError as error:
        st.error(str(error))
        return
    fig = go.Figure(go.Waterfall(
        x=['Кассовые доходы'] + [label for label, _ in steps] + ['Регулярные доходы'],
        measure=['absolute'] + ['relative']*len(steps) + ['total'],
        y=[month.raw_revenue] + [value for _, value in steps] + [0],
        text=[f'{month.raw_revenue:,.1f}'] + [f'{value:+,.1f}' for _, value in steps] + [f'{month.normalized_revenue:,.1f}'],
        textposition='outside', increasing={'marker': {'color':'#4676C9'}},
        decreasing={'marker': {'color':'#CA5358'}}, totals={'marker': {'color':'#555D6A'}},
    ))
    fig.update_layout(height=440, template='plotly_white', showlegend=False,
                      margin={'l':45,'r':30,'t':45,'b':150}, yaxis_title=unit)
    fig.update_xaxes(tickangle=-25, automargin=True)
    st.plotly_chart(fig, width='stretch')
    delta = month.normalized_revenue-month.raw_revenue
    st.write(f'**Расчёт:** {month.raw_revenue:,.1f} + ({delta:+,.1f}) = **{month.normalized_revenue:,.1f} {unit}**.')
    st.caption('Синий шаг увеличивает аналитический ряд, красный уменьшает. Это изменение отнесения поступлений, а не оценка «хорошо / плохо». Исходные кассовые доходы сохранены.')
    st.latex(r'R^{regular}_t = R^{cash}_t + \sum_j \Delta_{j,t}')
    balance = go.Figure()
    balance.add_trace(go.Scatter(x=[r.month for r in result], y=[r.cash_balance for r in result],
                                name='Кассовый остаток', mode='lines+markers', line={'color':'#4676C9'}))
    balance.add_trace(go.Bar(x=[r.month for r in result], y=[r.reserve_need for r in result],
                            name='Потребность в покрытии', marker_color='#CA5358'))
    balance.add_hline(y=0, line_color='#555D6A', line_dash='dash')
    balance.update_layout(height=370, template='plotly_white', yaxis_title=unit,
                          margin={'l':45,'r':25,'t':35,'b':100}, legend={'orientation':'h','y':-.22,'yanchor':'top'})
    st.plotly_chart(balance, width='stretch')
    st.latex(r'B_t = B_{t-1}+R_t+F_t-E_t-C_t,\qquad Need_t=\max(-B_t,0)')
    st.caption(f'B — остаток; R — кассовые доходы; F — финансирование; E — кассовые расходы; C — исключение повторно учтённых переходящих остатков. Начальная база: {opening_balance:,.1f} {unit}.')
    st.write(f'**Вывод за {month.month:%m.%Y}:** остаток {month.cash_balance:,.1f} {unit}; потребность в покрытии {month.reserve_need:,.1f} {unit}.')
    if opening_balance == 0:
        st.warning('Нулевая начальная база: вывод условный, пока реальный начальный остаток не подтверждён. Отрицательный остаток не является доказательством фактического кассового разрыва администрации.')
