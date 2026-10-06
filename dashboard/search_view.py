"""Manual search preparation; external AI and parser execution are future work."""
import json
import streamlit as st
from mesm.sources.search_directory import load_directory, save_task, build_query
from ui import section_header


def render_search_directory(root):
    section_header("Справочник поиска информации", "ЧЕЛОВЕК · ИСТОЧНИК · ПАРСЕР", "Следующий этап развития MESM: небольшие поисковые модули для конкретных показателей.")
    st.markdown("**1. Требования → 2. Запрос ИИ → 3. Проверка источника → 4. Парсер → 5. Сверка извлечения → 6. Допуск данных.**")
    st.info("Сейчас доступны ручной справочник, подтверждение требований и подготовка запроса. Запросы к другим ИИ, запуск парсеров и подтверждение извлечений — следующий этап; ответ ИИ не подтверждает источник.")
    directory = load_directory(root)
    ids = [t["id"] for t in directory["tasks"]]
    selected = st.selectbox("Поисковая задача", ["Новая задача"] + ids)
    task = next((t for t in directory["tasks"] if t["id"] == selected), {})
    c = task.get("criteria", {})
    with st.form("manual_search"):
        task_id = st.text_input("Код задачи", value=task.get("id", ""))
        labels = {"title":"Название", "municipality":"Муниципалитет / ОКТМО", "indicator":"Показатель", "period":"Период", "unit":"Единица измерения", "primary_source":"Ожидаемый первичный источник", "query":"Что найти и проверить"}
        criteria = {key: st.text_input(label, value=c.get(key, "")) for key, label in labels.items()}
        actor = st.text_input("Кто проверил требования")
        confirm = st.checkbox("Я проверил введённые требования; подтверждение относится только к ним")
        submit = st.form_submit_button("Сохранить требования")
    if submit:
        try:
            if not task_id.strip():
                raise ValueError("Укажите код задачи")
            task = save_task(root, task_id.strip(), criteria, actor, confirm)
            directory = load_directory(root)
            st.success("Сохранено. Изменение требований сбрасывает предыдущее подтверждение.")
        except ValueError as exc:
            st.error(str(exc))
    if task:
        try:
            query = build_query(task)
            st.code(query, language="text")
            st.download_button("Скачать запрос для другого ИИ", query, "MESM_search_request.txt", "text/plain")
        except ValueError as exc:
            st.warning(str(exc))
        st.caption("Журнал подтверждений требований")
        st.dataframe(task.get("history", []), width="stretch", hide_index=True)
    st.download_button("Скачать справочник JSON", json.dumps(directory, ensure_ascii=False, indent=2), "MESM_search_directory.json", "application/json")
