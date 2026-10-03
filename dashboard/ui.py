from __future__ import annotations

import html
from pathlib import Path
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
    stylesheet = Path(__file__).with_name("theme.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{stylesheet}</style>", unsafe_allow_html=True)


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
    columns = max(1, min(int(columns), 4))
    blocks = []
    for card in cards:
        tone = _TONE_CLASS.get(str(card.get("tone", "neutral")), "neutral")
        blocks.append(f'<div class="mesm-card {tone}"><div class="mesm-card-label">{html.escape(str(card.get("label", "")))}</div><div class="mesm-card-value">{html.escape(str(card.get("value", "—")))}</div><div class="mesm-card-meta">{html.escape(str(card.get("meta", "")))}</div></div>')
    st.markdown(f'<div class="mesm-metric-grid" style="--columns:{columns}">{"".join(blocks)}</div>', unsafe_allow_html=True)


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
