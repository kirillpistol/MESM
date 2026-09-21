from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from mesm.data.intake import (
    DATASET_SPECS,
    compare_frames,
    compare_to_current,
    dataset_status,
    list_excel_sheets,
    persist_dataset,
    read_uploaded_table,
    recent_intake_log,
    template_csv,
    validate_dataset,
)

PANEL_PATH = Path("data/processed/fiscal_reference_panel.csv")


def _rerun_reference(root: Path) -> None:
    subprocess.run(
        [sys.executable, str(root / "scripts" / "build_fiscal_reference_panel.py")],
        cwd=root,
        check=True,
    )


def _read_panel(root: Path) -> pd.DataFrame:
    path = root / PANEL_PATH
    return pd.read_csv(path, encoding="utf-8-sig") if path.exists() else pd.DataFrame()


def _impact_after_accept(
    dataset_key: str,
    before_panel: pd.DataFrame,
    after_panel: pd.DataFrame,
    candidate_diff: dict[str, object],
) -> dict[str, object]:
    if dataset_key in {"reference_core", "quality_rankings"}:
        panel_diff = compare_frames(before_panel, after_panel, ("year", "municipality_name"))
        return {
            "reference_recalculated": True,
            "report_updated": True,
            "changed_rows": panel_diff["changed_keys"],
            "changed_municipalities": panel_diff["changed_municipalities"],
        }
    return {
        "reference_recalculated": False,
        "report_updated": True,
        "changed_rows": candidate_diff["changed_keys"],
        "changed_municipalities": candidate_diff["changed_municipalities"],
    }


def _show_last_result() -> None:
    result = st.session_state.get("mesm_last_intake")
    if not result:
        return
    st.success(f"Последняя загрузка принята: {result['source_filename']} → {result['dataset_title']}.")
    cols = st.columns(5)
    cols[0].metric("Строк после", result["rows"])
    cols[1].metric("Изменено ключей", result["changed_rows"])
    cols[2].metric("Затронуто МО", len(result["changed_municipalities"]))
    cols[3].metric("Reference Panel", "YES" if result["reference_recalculated"] else "NO")
    cols[4].metric("Отчет", "UPDATED" if result["report_updated"] else "NO")
    if result["changed_municipalities"]:
        st.caption("Изменились/добавились МО: " + ", ".join(result["changed_municipalities"][:22]))


def render_data_intake(root: Path) -> None:
    st.subheader("Ввод и контроль данных")
    _show_last_result()

    st.markdown("#### Мониторинг активных источников")
    status_rows = [dataset_status(key, root) for key in DATASET_SPECS]
    st.dataframe(
        pd.DataFrame(status_rows)[
            ["title", "mode", "period", "municipalities", "rows", "quality", "modified", "sha256", "path"]
        ],
        use_container_width=True,
        hide_index=True,
    )

    for dataset_key, spec in DATASET_SPECS.items():
        with st.container(border=True):
            st.markdown(f"### {spec.title}")

            with st.expander("Контракт данных"):
                st.markdown("**Обязательные колонки**")
                st.code("\n".join(spec.required_columns))
                if spec.optional_columns:
                    st.markdown("**Дополнительные колонки**")
                    st.code("\n".join(spec.optional_columns))
                st.markdown("**Логический ключ**")
                st.code(" + ".join(spec.key_columns))

            st.download_button(
                "Скачать шаблон CSV",
                data=template_csv(dataset_key),
                file_name=f"MESM_template_{dataset_key}.csv",
                mime="text/csv",
                key=f"template_{dataset_key}",
            )

            uploaded = st.file_uploader(
                "Загрузите файл",
                type=["csv", "xlsx", "xlsm", "xls"],
                key=f"upload_{dataset_key}",
            )
            if uploaded is None:
                continue

            content = uploaded.getvalue()
            sheet_name = None
            try:
                sheets = list_excel_sheets(uploaded.name, content)
                if sheets:
                    sheet_name = st.selectbox("Лист Excel", sheets, key=f"sheet_{dataset_key}")
                frame = read_uploaded_table(uploaded.name, content, sheet_name=sheet_name)
                validation = validate_dataset(dataset_key, frame)
                diff = compare_to_current(dataset_key, frame, root)
            except Exception as exc:
                st.error(f"Файл не удалось прочитать: {exc}")
                continue

            st.markdown("#### Протокол входного контроля")
            protocol = {
                "Файл": uploaded.name,
                "Тип данных": spec.title.split(". ", 1)[-1],
                "Период": validation.period_label,
                "Объектов / географий": validation.municipality_count,
                "Строк": validation.row_count,
                "Колонок": validation.column_count,
                "Пропуски в обязательных полях": validation.missing_required_cells,
                "Дубли логического ключа": validation.duplicate_keys,
                "Внутренние проверки": validation.consistency_status,
                "Сверка с source total": "N/A — контрольная сумма не передана",
                "Статус": validation.quality_status,
            }
            st.dataframe(
                pd.DataFrame([{"Проверка": k, "Значение": v} for k, v in protocol.items()]),
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("#### Изменение относительно текущей версии")
            diff_cols = st.columns(5)
            diff_cols[0].metric("Строк было", diff["before_rows"])
            diff_cols[1].metric("Строк станет", diff["after_rows"], delta=diff["row_delta"])
            diff_cols[2].metric("Новых ключей", diff["added_keys"])
            diff_cols[3].metric("Удаленных ключей", diff["removed_keys"])
            diff_cols[4].metric("Измененных ключей", diff["changed_keys"])
            if diff["changed_municipalities"]:
                st.caption("Затронутые МО: " + ", ".join(diff["changed_municipalities"][:22]))

            for error in validation.errors:
                st.error(error)
            for warning in validation.warnings:
                st.warning(warning)

            with st.expander("Preview первых 20 строк", expanded=validation.valid):
                st.dataframe(frame.head(20), use_container_width=True, hide_index=True)

            if not validation.valid:
                st.error("REJECTED: активный набор не изменен.")
                continue

            accept_allowed = True
            if validation.quality_status == "REVIEW":
                accept_allowed = st.checkbox(
                    "Я просмотрел предупреждения и подтверждаю прием файла",
                    key=f"review_{dataset_key}",
                )

            button_text = (
                "Принять после проверки и пересчитать MESM"
                if validation.quality_status == "REVIEW"
                else "Принять файл и пересчитать MESM"
            )
            if st.button(
                button_text,
                type="primary",
                disabled=not accept_allowed,
                key=f"accept_{dataset_key}",
                use_container_width=True,
            ):
                before_panel = _read_panel(root)
                with st.spinner("Версионирую файл и пересчитываю MESM..."):
                    record = persist_dataset(
                        dataset_key=dataset_key,
                        frame=frame,
                        original_name=uploaded.name,
                        original_content=content,
                        root=root,
                    )
                    if dataset_key in {"reference_core", "quality_rankings"}:
                        _rerun_reference(root)
                    after_panel = _read_panel(root)

                impact = _impact_after_accept(dataset_key, before_panel, after_panel, diff)
                st.session_state["mesm_last_intake"] = {
                    "source_filename": uploaded.name,
                    "dataset_title": spec.title,
                    "rows": record["rows"],
                    **impact,
                }
                st.rerun()

    st.markdown("#### Журнал принятых версий")
    log = recent_intake_log(root)
    if log.empty:
        st.caption("Пользовательских загрузок пока нет.")
    else:
        st.dataframe(log, use_container_width=True, hide_index=True)

    st.markdown("#### Pipeline")
    st.code(
        "Upload → Contract check → Quality protocol → Compare → Accept/Reject → "
        "Version + SHA-256 → Active dataset → Recalculation → Dashboard → HTML report"
    )
