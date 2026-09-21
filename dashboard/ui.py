from __future__ import annotations

import html
from typing import Iterable, Sequence

import streamlit as st


_TONE_CLASS = {
    "neutral": "neutral",
    "info": "info",
    "positive": "positive",
    "warning": "warning",
    "danger": "danger",
    "muted": "muted",
}


def inject_control_room_css() -> None:
    st.markdown(
        """
<style>
:root {
  --bg: #F5F5F5;
  --card: #FFFFFF;
  --ink: #1A1A1A;
  --muted: #6F6F6F;
  --line: #DDDDDD;
  --red: #D71920;
  --green: #2F7D59;
  --amber: #9A6700;
  --blue: #315EAA;
}
html, body, [class*="css"] {
  font-family: Arial, "Segoe UI", sans-serif !important;
}
[data-testid="stAppViewContainer"] {
  background: var(--bg);
  color: var(--ink);
}
[data-testid="stHeader"] {
  background: var(--bg);
}
.block-container {
  max-width: 1380px;
  padding-top: 1rem;
  padding-bottom: 3rem;
}
h1, h2, h3, h4 {
  font-family: Arial, "Segoe UI", sans-serif !important;
  color: var(--ink);
  letter-spacing: 0;
}
h1 {
  font-size: 2rem !important;
  font-weight: 700 !important;
  margin-bottom: .15rem !important;
}
[data-testid="stSidebar"] {
  background: #202124;
  border-right: 1px solid #33363A;
}
[data-testid="stSidebar"] * { color: #F2F2F2; }
[data-testid="stSidebar"] label { color: #D0D0D0 !important; }
[data-testid="stSidebar"] [data-baseweb="select"] > div {
  background: #292B2F !important;
  border-color: #45484D !important;
}
[data-testid="stSidebar"] [role="radiogroup"] label {
  border-radius: 6px;
  padding: .4rem .55rem;
  margin: .04rem 0;
}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
  background: #342326;
  border-left: 3px solid var(--red);
}
[data-testid="stMetric"],
[data-testid="stDataFrame"],
[data-testid="stExpander"],
[data-testid="stPlotlyChart"] {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: none;
}
[data-testid="stMetric"] { padding: .75rem .9rem; }
[data-testid="stPlotlyChart"] { padding: .2rem .3rem 0; }
.stButton > button, .stDownloadButton > button {
  border-radius: 6px;
  border: 1px solid #CCCCCC;
  font-weight: 600;
}
.stButton > button:hover, .stDownloadButton > button:hover {
  border-color: var(--red);
  color: var(--red);
}
.mesm-sidebar-brand {
  margin: .15rem 0 1rem;
  padding: .15rem .1rem .9rem;
  border-bottom: 1px solid #3A3D42;
}
.mesm-sidebar-logo {
  font-size: 1.35rem;
  font-weight: 700;
}
.mesm-sidebar-sub {
  color: #AAAAAA !important;
  font-size: .72rem;
  margin-top: .22rem;
}
.mesm-sidebar-label {
  color: #A7A7A7 !important;
  font-size: .68rem;
  font-weight: 700;
  margin: .9rem 0 .3rem;
}
.mesm-eyebrow {
  color: var(--red);
  font-size: .72rem;
  font-weight: 700;
  margin-bottom: .2rem;
}
.mesm-app-subtitle {
  color: #444444;
  font-size: .98rem;
}
.mesm-app-meta {
  color: #808080;
  font-size: .78rem;
  margin-top: .1rem;
}
.mesm-systembar {
  display: flex;
  align-items: center;
  gap: .45rem;
  flex-wrap: wrap;
  background: #FFFFFF;
  color: var(--ink);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: .58rem .72rem;
  margin: .75rem 0 1rem;
}
.mesm-systembar .context {
  font-weight: 700;
  margin-right: auto;
}
.mesm-chip {
  display: inline-flex;
  align-items: center;
  gap: .3rem;
  font-size: .68rem;
  font-weight: 600;
  border-radius: 5px;
  padding: .25rem .42rem;
  border: 1px solid #D5D5D5;
  color: #444444;
  background: #FAFAFA;
}
.mesm-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #888888;
  display: inline-block;
}
.mesm-dot.positive { background: var(--green); }
.mesm-dot.info { background: var(--blue); }
.mesm-dot.warning { background: #D9A321; }
.mesm-hero {
  background: #FFFFFF;
  color: var(--ink);
  border: 1px solid var(--line);
  border-top: 3px solid var(--red);
  border-radius: 8px;
  padding: 1rem;
  margin: .55rem 0 1rem;
}
.mesm-hero-kicker {
  color: var(--red);
  font-size: .7rem;
  font-weight: 700;
}
.mesm-hero-title {
  font-size: 1.3rem;
  line-height: 1.2;
  font-weight: 700;
  margin-top: .28rem;
}
.mesm-hero-subtitle {
  color: #5C5C5C;
  font-size: .82rem;
  margin-top: .3rem;
}
.mesm-hero-grid {
  display: grid;
  grid-template-columns: repeat(4,minmax(130px,1fr));
  gap: .5rem;
  margin-top: .8rem;
}
.mesm-hero-stat {
  border: 1px solid var(--line);
  background: #FAFAFA;
  border-radius: 6px;
  padding: .6rem .65rem;
}
.mesm-hero-stat-label {
  color: var(--muted);
  font-size: .64rem;
  font-weight: 700;
}
.mesm-hero-stat-value {
  font-size: 1.05rem;
  font-weight: 700;
  margin-top: .22rem;
}
.mesm-hero-stat-meta {
  color: #7A7A7A;
  font-size: .66rem;
  margin-top: .15rem;
}
.mesm-section {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1rem;
  margin: 1.2rem 0 .55rem;
}
.mesm-section-title {
  font-size: 1.02rem;
  font-weight: 700;
}
.mesm-section-caption {
  color: var(--muted);
  font-size: .78rem;
  margin-top: .12rem;
}
.mesm-section-tag {
  color: var(--red);
  font-size: .68rem;
  font-weight: 700;
}
.mesm-card {
  min-height: 112px;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: .8rem .85rem;
}
.mesm-card.info { border-left: 3px solid var(--blue); }
.mesm-card.positive { border-left: 3px solid var(--green); }
.mesm-card.warning { border-left: 3px solid #D99A18; }
.mesm-card.danger { border-left: 3px solid var(--red); }
.mesm-card.muted { border-left: 3px solid #A0A0A0; }
.mesm-card-label {
  color: var(--muted);
  font-size: .66rem;
  font-weight: 700;
}
.mesm-card-value {
  color: var(--ink);
  font-size: 1.38rem;
  font-weight: 700;
  line-height: 1.1;
  margin-top: .45rem;
}
.mesm-card-meta {
  color: #808080;
  font-size: .7rem;
  margin-top: .34rem;
}
.mesm-banner {
  border-radius: 8px;
  padding: .8rem .9rem;
  border: 1px solid var(--line);
  background: #FFFFFF;
  margin: .65rem 0 1rem;
}
.mesm-banner.info { border-left: 3px solid var(--blue); }
.mesm-banner.positive { border-left: 3px solid var(--green); }
.mesm-banner.warning { border-left: 3px solid #D99A18; }
.mesm-banner.danger { border-left: 3px solid var(--red); }
.mesm-banner.muted { border-left: 3px solid #A0A0A0; }
.mesm-banner-status {
  font-size: .66rem;
  font-weight: 700;
  color: var(--muted);
}
.mesm-banner-headline {
  font-weight: 700;
  font-size: .94rem;
  margin-top: .2rem;
}
.mesm-banner-copy {
  color: #5F5F5F;
  font-size: .8rem;
  margin-top: .15rem;
}
.mesm-pipeline,
.mesm-budget-path {
  display: grid;
  grid-template-columns: repeat(auto-fit,minmax(160px,1fr));
  gap: .5rem;
  margin: .6rem 0 1rem;
}
.mesm-stage,
.mesm-budget-node {
  background: #FFF;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: .65rem .7rem;
  min-height: 78px;
}
.mesm-stage-no {
  color: var(--red);
  font-size: .62rem;
  font-weight: 700;
}
.mesm-stage-title {
  font-size: .8rem;
  font-weight: 700;
  margin-top: .24rem;
}
.mesm-stage-copy {
  color: var(--muted);
  font-size: .72rem;
  margin-top: .15rem;
}
.mesm-budget-node:last-child {
  border-left: 3px solid var(--red);
}
.mesm-budget-node-label {
  color: var(--muted);
  font-size: .67rem;
  font-weight: 700;
}
.mesm-budget-node-value {
  font-size: 1.05rem;
  font-weight: 700;
  margin-top: .35rem;
}
.mesm-budget-node-meta {
  color: #808080;
  font-size: .68rem;
  margin-top: .2rem;
}
.mesm-source {
  display: grid;
  grid-template-columns: 1.25fr 2fr 1fr;
  gap: .75rem;
  background: #FFF;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: .8rem .9rem;
  margin-bottom: .7rem;
}
.mesm-source-label {
  color: var(--muted);
  font-size: .64rem;
  font-weight: 700;
}
.mesm-source-value {
  font-size: .78rem;
  margin-top: .2rem;
}
.mesm-source a {
  color: var(--red);
  text-decoration: none;
  font-weight: 600;
}
@media (max-width: 900px) {
  .mesm-hero-grid { grid-template-columns: 1fr 1fr; }
  .mesm-source { grid-template-columns: 1fr; }
}
</style>
        """,
        unsafe_allow_html=True,
    )


def sidebar_brand() -> None:
    st.sidebar.markdown(
        """
<div class="mesm-sidebar-brand">
  <div class="mesm-sidebar-logo">MESM</div>
  <div class="mesm-sidebar-sub">Муниципальный экономический монитор</div>
</div>
<div class="mesm-sidebar-label">РАЗДЕЛЫ</div>
        """,
        unsafe_allow_html=True,
    )


def app_header(title: str, subtitle: str, meta: str = "") -> None:
    st.markdown('<div class="mesm-eyebrow">Муниципальная аналитическая система</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<div class="mesm-app-subtitle">{html.escape(subtitle)}</div>', unsafe_allow_html=True)
    if meta:
        st.markdown(f'<div class="mesm-app-meta">{html.escape(meta)}</div>', unsafe_allow_html=True)


def hero_panel(kicker: str, title: str, subtitle: str, stats: Sequence[dict]) -> None:
    blocks = []
    for item in stats[:4]:
        blocks.append(
            f"""
<div class="mesm-hero-stat">
  <div class="mesm-hero-stat-label">{html.escape(str(item.get("label", "")))}</div>
  <div class="mesm-hero-stat-value">{html.escape(str(item.get("value", "—")))}</div>
  <div class="mesm-hero-stat-meta">{html.escape(str(item.get("meta", "")))}</div>
</div>
            """
        )
    st.markdown(
        f"""
<div class="mesm-hero">
  <div class="mesm-hero-kicker">{html.escape(kicker)}</div>
  <div class="mesm-hero-title">{html.escape(title)}</div>
  <div class="mesm-hero-subtitle">{html.escape(subtitle)}</div>
  <div class="mesm-hero-grid">{''.join(blocks)}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def system_bar(municipality: str, year: int | None, data_status: str, pipeline_status: str) -> None:
    year_text = str(year) if year is not None else "—"
    st.markdown(
        f"""
<div class="mesm-systembar">
  <div class="context">{html.escape(str(municipality))} / {html.escape(year_text)}</div>
  <span class="mesm-chip"><span class="mesm-dot info"></span>{html.escape(data_status)}</span>
  <span class="mesm-chip"><span class="mesm-dot positive"></span>КОНТУР {html.escape(pipeline_status)}</span>
  <span class="mesm-chip">ОКТМО</span>
</div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, tag: str = "", caption: str = "") -> None:
    st.markdown(
        f"""
<div class="mesm-section">
  <div>
    <div class="mesm-section-title">{html.escape(title)}</div>
    <div class="mesm-section-caption">{html.escape(caption)}</div>
  </div>
  <div class="mesm-section-tag">{html.escape(tag)}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def metric_grid(cards: Sequence[dict], columns: int = 4) -> None:
    if not cards:
        return
    for start in range(0, len(cards), columns):
        chunk = cards[start:start + columns]
        cols = st.columns(len(chunk))
        for col, card in zip(cols, chunk):
            tone = _TONE_CLASS.get(str(card.get("tone", "neutral")), "neutral")
            with col:
                st.markdown(
                    f"""
<div class="mesm-card {tone}">
  <div class="mesm-card-label">{html.escape(str(card.get("label", "")))}</div>
  <div class="mesm-card-value">{html.escape(str(card.get("value", "—")))}</div>
  <div class="mesm-card-meta">{html.escape(str(card.get("meta", "")))}</div>
</div>
                    """,
                    unsafe_allow_html=True,
                )


def status_banner(status: str, headline: str, copy: str, tone: str = "neutral") -> None:
    tone = _TONE_CLASS.get(tone, "neutral")
    st.markdown(
        f"""
<div class="mesm-banner {tone}">
  <div class="mesm-banner-status">{html.escape(str(status)).upper()}</div>
  <div class="mesm-banner-headline">{html.escape(str(headline))}</div>
  <div class="mesm-banner-copy">{html.escape(str(copy))}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def pipeline(stages: Iterable[tuple[str, str]]) -> None:
    blocks = []
    for idx, (title, copy) in enumerate(stages, start=1):
        blocks.append(
            f"""
<div class="mesm-stage">
  <div class="mesm-stage-no">{idx}</div>
  <div class="mesm-stage-title">{html.escape(title)}</div>
  <div class="mesm-stage-copy">{html.escape(copy)}</div>
</div>
            """
        )
    st.markdown('<div class="mesm-pipeline">' + "".join(blocks) + "</div>", unsafe_allow_html=True)


def budget_path(items: Sequence[tuple[str, float, str]]) -> None:
    blocks = []
    for label, value, meta in items:
        blocks.append(
            f"""
<div class="mesm-budget-node">
  <div class="mesm-budget-node-label">{html.escape(label)}</div>
  <div class="mesm-budget-node-value">{value:,.3f} млрд ₽</div>
  <div class="mesm-budget-node-meta">{html.escape(meta)}</div>
</div>
            """
        )
    st.markdown('<div class="mesm-budget-path">' + "".join(blocks) + "</div>", unsafe_allow_html=True)


def source_card(
    authority: str,
    document: str,
    publication: str,
    stage: str,
    verification: str,
    url: str = "",
) -> None:
    link = ""
    if url:
        safe_url = html.escape(url, quote=True)
        link = f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer">Открыть официальный источник ↗</a>'
    st.markdown(
        f"""
<div class="mesm-source">
  <div>
    <div class="mesm-source-label">Орган</div>
    <div class="mesm-source-value">{html.escape(authority)}</div>
  </div>
  <div>
    <div class="mesm-source-label">Документ</div>
    <div class="mesm-source-value">{html.escape(document)}</div>
    <div class="mesm-source-value">{link}</div>
  </div>
  <div>
    <div class="mesm-source-label">Проверка</div>
    <div class="mesm-source-value">{html.escape(publication)} · {html.escape(stage)}</div>
    <div class="mesm-source-value">✓ {html.escape(verification or "официальный файл")}</div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def tone_for_status(value: str) -> str:
    text = str(value or "").upper()
    if any(token in text for token in ("BREAK", "CRITICAL", "ALARM", "HIGH_RISK", "RED")):
        return "danger"
    if any(token in text for token in ("WARNING", "OBSERVE", "MEDIUM", "LIMITED")):
        return "warning"
    if any(token in text for token in ("NORMAL", "STRONG", "READY", "OK", "CONFIRMED")):
        return "positive"
    if any(token in text for token in ("NO DATA", "NOT CALCULATED", "UNKNOWN", "NONE")):
        return "muted"
    return "info"
