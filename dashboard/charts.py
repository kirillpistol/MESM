from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

RED = "#D71920"
BLUE = "#315EAA"
GREEN = "#237A57"
AMBER = "#B7791F"
INK = "#17191E"
MUTED = "#737A84"
GRID = "#E6E8EC"
LIGHT = "#F4F5F7"


def _finish(fig: go.Figure, *, height: int = 360, percent_y: bool = False) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=22, r=22, t=34, b=26),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family='Inter, "Segoe UI", Arial, sans-serif', color=INK, size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.015, xanchor="left", x=0, font=dict(size=11)),
        hoverlabel=dict(bgcolor="white", bordercolor=GRID, font_color=INK),
        bargap=0.34,
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, zeroline=False, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, tickfont=dict(color=MUTED))
    if percent_y:
        fig.update_yaxes(tickformat=".0%")
    return fig


def reference_trend_chart(frame: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    specs = [
        ("income_plan_deviation", "Доходы / план", RED),
        ("program_expense_share", "Программные расходы", BLUE),
        ("debt_load", "Долговая нагрузка", GREEN),
    ]
    for column, name, color in specs:
        if column not in frame:
            continue
        data = frame[["year", column]].dropna()
        if data.empty:
            continue
        fig.add_trace(go.Scatter(
            x=data["year"],
            y=data[column],
            mode="lines+markers",
            name=name,
            line=dict(width=2.5, color=color),
            marker=dict(size=7),
            hovertemplate=f"{name}: %{{y:.1%}}<extra></extra>",
        ))
    return _finish(fig, height=350, percent_y=True)


def budget_waterfall_chart(revenue_base: float, transfers: float, expenditure: float) -> go.Figure:
    scale = 1_000_000.0
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["relative", "relative", "relative", "total"],
        x=["Собственные доходы", "Трансферты", "Расходы", "Баланс"],
        y=[revenue_base / scale, transfers / scale, -expenditure / scale, 0],
        text=[
            f"{revenue_base / scale:.2f}",
            f"{transfers / scale:.2f}",
            f"−{expenditure / scale:.2f}",
            "",
        ],
        textposition="outside",
        connector=dict(line=dict(color="#C9CDD4", width=1)),
        increasing=dict(marker=dict(color=GREEN)),
        decreasing=dict(marker=dict(color=RED)),
        totals=dict(marker=dict(color=INK)),
        hovertemplate="%{x}: %{y:.3f} млрд ₽<extra></extra>",
    ))
    fig.update_yaxes(title="млрд ₽")
    return _finish(fig, height=380)


def expenditure_structure_chart(frame: pd.DataFrame, top_n: int = 12) -> go.Figure:
    if frame.empty:
        return _finish(go.Figure(), height=320)
    data = frame.copy()
    label_col = "group" if "group" in data else ("item_name" if "item_name" in data else data.columns[0])
    data["amount"] = pd.to_numeric(data["amount"], errors="coerce")
    data = data.dropna(subset=["amount"]).sort_values("amount", ascending=False).head(top_n)
    data = data.sort_values("amount", ascending=True)
    fig = go.Figure(go.Bar(
        x=data["amount"] / 1_000_000,
        y=data[label_col],
        orientation="h",
        marker=dict(color=RED),
        text=[f"{v / 1_000_000:.2f}" for v in data["amount"]],
        textposition="outside",
        hovertemplate="%{y}: %{x:.3f} млрд ₽<extra></extra>",
    ))
    fig.update_xaxes(title="млрд ₽")
    return _finish(fig, height=max(340, 36 * len(data) + 80))


def forecast_actual_chart(frame: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    specs = [
        ("actual", "Факт", INK, 3.0, None),
        ("seasonal_naive", "Сезонный наивный", BLUE, 2.0, "dash"),
        ("linear_trend", "Линейный тренд", RED, 2.0, "dot"),
    ]
    for column, name, color, width, dash in specs:
        if column not in frame:
            continue
        fig.add_trace(go.Scatter(
            x=frame["period"],
            y=frame[column],
            mode="lines",
            name=name,
            line=dict(color=color, width=width, dash=dash),
            hovertemplate=f"{name}: %{{y:.3f}}<extra></extra>",
        ))
    return _finish(fig, height=370)


def shock_monitor_chart(frame: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=frame["period"], y=frame["residual"], name="Residual",
            mode="lines", line=dict(color=INK, width=2.2),
            hovertemplate="Residual: %{y:.3f}<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=frame["period"], y=frame["z_score"], name="Z-score",
            mode="lines", line=dict(color=RED, width=2.0),
            hovertemplate="Z-score: %{y:.2f}σ<extra></extra>",
        ),
        secondary_y=True,
    )
    alarms = frame[frame["cusum_alarm"].astype(bool)]
    if not alarms.empty:
        fig.add_trace(
            go.Scatter(
                x=alarms["period"], y=alarms["z_score"], name="CUSUM",
                mode="markers", marker=dict(color=AMBER, size=9, symbol="diamond"),
                hovertemplate="CUSUM · period %{x}<extra></extra>",
            ),
            secondary_y=True,
        )
    shocked = frame[frame["shock_window"].astype(bool)]
    if not shocked.empty:
        fig.add_vrect(
            x0=float(shocked["period"].min()) - 0.5,
            x1=float(shocked["period"].max()) + 0.5,
            fillcolor=RED,
            opacity=0.07,
            line_width=0,
            annotation_text="shock window",
            annotation_position="top left",
        )
    for threshold in (2.0, -2.0):
        fig.add_trace(
            go.Scatter(
                x=frame["period"],
                y=[threshold] * len(frame),
                mode="lines",
                name=f"{threshold:+.0f}σ",
                line=dict(color="#AEB4BD", width=1, dash="dot"),
                hoverinfo="skip",
                showlegend=False,
            ),
            secondary_y=True,
        )
    fig.update_yaxes(title_text="Residual", secondary_y=False)
    fig.update_yaxes(title_text="Z-score, σ", secondary_y=True)
    return _finish(fig, height=390)


def bo_history_chart(frame: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    specs = [
        ("bo_actual", "Фактическая БО", INK),
        ("bo_calculated", "Расчетная БО", RED),
    ]
    for column, name, color in specs:
        if column not in frame:
            continue
        fig.add_trace(go.Scatter(
            x=frame["year"],
            y=frame[column],
            mode="lines+markers",
            name=name,
            line=dict(color=color, width=2.5),
            marker=dict(size=7),
            hovertemplate=f"{name}: %{{y:.3f}}<extra></extra>",
        ))
    return _finish(fig, height=350)


def model_tournament_chart(frame: pd.DataFrame) -> go.Figure:
    if frame.empty:
        return _finish(go.Figure(), height=320)
    data=frame.copy()
    data["mae"]=pd.to_numeric(data["mae"],errors="coerce")
    data=data.dropna(subset=["mae"]).sort_values("mae",ascending=False)
    best_name=str(data.loc[data["mae"].idxmin(),"model"])
    colors=[RED if name==best_name else INK if name=="Prophet" else "#AAB3C2" for name in data["model"]]
    fig=go.Figure(go.Bar(
        x=data["mae"],
        y=data["model"],
        orientation="h",
        marker=dict(color=colors),
        text=[f"{value:,.0f} ₽".replace(",", " ") for value in data["mae"]],
        textposition="outside",
        hovertemplate="%{y}: MAE %{x:.2f} ₽<extra></extra>",
    ))
    fig.update_xaxes(title="MAE, ₽ · меньше лучше")
    return _finish(fig,height=max(330,52*len(data)+90))


def competition_forecast_chart(
    prophet: pd.DataFrame,
    grow: pd.DataFrame,
) -> go.Figure:
    left=prophet.copy()
    right=grow.copy()
    left["period"]=pd.to_datetime(left["period"],errors="coerce")
    right["period"]=pd.to_datetime(right["period"],errors="coerce")
    merged=left.merge(
        right[["period","grow_prediction"]],
        on="period",
        how="outer",
    ).sort_values("period")
    fig=go.Figure()
    fig.add_trace(go.Scatter(
        x=merged["period"],y=merged["actual"],mode="lines+markers",
        name="Факт",line=dict(color=INK,width=3.2),marker=dict(size=6),
        hovertemplate="Факт: %{y:,.0f} ₽<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=merged["period"],y=merged["grow_prediction"],mode="lines+markers",
        name="Grow",line=dict(color=RED,width=2.4),marker=dict(size=5),
        hovertemplate="Grow: %{y:,.0f} ₽<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=merged["period"],y=merged["prophet"],mode="lines",
        name="Prophet",line=dict(color=BLUE,width=2.0,dash="dot"),
        hovertemplate="Prophet: %{y:,.0f} ₽<extra></extra>",
    ))
    fig.update_yaxes(title="Расходы, ₽")
    return _finish(fig,height=410)


def shock_benchmark_chart(frame: pd.DataFrame) -> go.Figure:
    if frame.empty:
        return _finish(go.Figure(),height=330)
    data=frame.copy()
    data["detection_rate"]=pd.to_numeric(data["detection_rate"],errors="coerce")
    fig=go.Figure()
    palette={"CUSUM":"#AAB3C2","PAGE_HINKLEY":RED,"PELT":INK}
    labels={"CUSUM":"CUSUM","PAGE_HINKLEY":"Page-Hinkley","PELT":"PELT"}
    for detector in ("CUSUM","PAGE_HINKLEY","PELT"):
        part=data[data["detector"].astype(str).eq(detector)]
        if part.empty:
            continue
        fig.add_trace(go.Bar(
            x=part["event_type"],
            y=part["detection_rate"],
            name=labels[detector],
            marker=dict(color=palette[detector]),
            text=[f"{v:.1%}" for v in part["detection_rate"]],
            textposition="outside",
            hovertemplate=f"{labels[detector]}: %{{y:.1%}}<extra></extra>",
        ))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="Доля выявленных изменений",tickformat=".0%",range=[0,max(.45,float(data["detection_rate"].max())*1.25)])
    return _finish(fig,height=370)


def shock_calibration_chart(frame: pd.DataFrame, target: float = 0.10) -> go.Figure:
    if frame.empty:
        return _finish(go.Figure(),height=300)
    data=frame.copy().sort_values("null_path_fpr",ascending=True)
    data["null_path_fpr"]=pd.to_numeric(data["null_path_fpr"],errors="coerce")
    colors=[RED if name=="PAGE_HINKLEY" else INK if name=="PELT" else "#AAB3C2" for name in data["detector"]]
    fig=go.Figure(go.Bar(
        x=data["null_path_fpr"],y=data["detector"],orientation="h",
        marker=dict(color=colors),
        text=[f"{v:.1%}" for v in data["null_path_fpr"]],
        textposition="outside",
        hovertemplate="%{y}: %{x:.1%}<extra></extra>",
    ))
    fig.add_vline(x=target,line=dict(color=AMBER,width=1.5,dash="dash"))
    fig.update_xaxes(title="FPR на данных без шока · меньше лучше",tickformat=".0%",range=[0,max(.12,float(data["null_path_fpr"].max())*1.35)])
    return _finish(fig,height=300)
