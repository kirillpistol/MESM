import json
import streamlit as st
from mesm.access.store import catalogue
from ui import section_header


def render_data_access(root):
    section_header("Данные и подключение ИИ", "MESM · УЗЕЛ L3", "Что можно получить, откуда это взято и насколько проверено.")
    items=[item for item,frame in catalogue(root)]
    labels={"official_public":"Публичный источник; нужна проверка документа", "derived_official":"Расчёт по официальным таблицам", "connected_not_validated":"Получено; сверка не завершена", "external_unvalidated":"Внешний ряд; валидация отдельно", "synthetic":"Синтетический сценарий", "user_import_requires_source_verification":"Импорт пользователя; требуется сверка источника"}
    st.dataframe([{"Набор":d["title"],"Код для ИИ":d["id"],"Строк":d["row_count"],"Доступность":"Есть данные" if d["available"] else "Нет данных", "Основание":labels.get(d["evidence_status"],d["evidence_status"]),"Частота":d["frequency"],"Единица":d["unit"],"Что выдаёт":d["meaning"]} for d in items],width="stretch",hide_index=True)
    st.download_button("Скачать каталог JSON",json.dumps({"schema_version":1,"datasets":items},ensure_ascii=False,indent=2),"MESM_data_catalog.json","application/json")
    word=root/"docs/MESM_Data_Requirements_1.12.0.docx"
    if word.exists():
        st.download_button("Требуемые и использованные данные — Word",word.read_bytes(),word.name,"application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    selected=st.selectbox("Поля набора данных",[d["id"] for d in items])
    item=next(d for d in items if d["id"]==selected)
    st.write("Поля:",", ".join(item["columns"]) or "Нет загруженной таблицы")
    st.caption("Источник: "+item["source_path"])
    st.info("API только читает данные. Статус источника и наличие файла не доказывают пригодность для раннего предупреждения. Кассовые файлы, открытые только в сессии браузера, в базу не попадают.")
    st.markdown("**Независимый запуск:** `START_MESM_L3.bat`, затем внешний потребитель обращается к `http://127.0.0.1:8765/v1/catalog` с заголовком `Authorization: Bearer <MESM_API_TOKEN>`. Для разных серверов используйте HTTPS/mTLS по серверной инструкции.")
    st.code("GET /v1/municipalities\nGET /v1/data?dataset=fiscal_panel&municipality=Сургут&limit=100\nGET /v1/report?municipality=Сургут\nGET /v1/sources\nGET /v1/trace",language="text")
    doc=root/"docs/35_data_access_and_replication.md"
    st.download_button("Инструкция подключения и переноса",doc.read_bytes(),doc.name,"text/markdown")

    st.markdown("**Роль MESM:** самостоятельная система L3. Панель нужна менеджеру для проверки данных и отчёта; сервер API работает независимо от панели и GENESIS.")
    st.code("GET /v1/node\nGET /v1/report-package?municipality=Сургут",language="text")
    st.info("Менеджер собирает готовые отчётные пакеты нескольких L3. Формулы бюджета выполняет MESM; ядро GENESIS здесь не запускается.")
    doc=root/"docs/38_l3_manager_architecture.md"
    st.download_button("Архитектура L3 и сборка отчётов",doc.read_bytes(),doc.name,"text/markdown")
