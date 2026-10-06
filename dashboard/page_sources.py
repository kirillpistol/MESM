from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from ui import section_header, source_card

PAGE_FILES = {
    'Данные и ИИ': ['config/data_products.json', 'docs/35_data_access_and_replication.md', 'docs/36_data_inventory.md', 'docs/37_genesis_connection.md', 'docs/38_l3_manager_architecture.md'],
    'Обзор': ['docs/16_methodology_v1.md', 'docs/29_source_evidence_register.md'],
    'Модели': ['docs/24_competition_core.md', 'config/backtest.yaml'],
    'Бюджет': ['docs/20_budget_normalization.md', 'config/budget_normalization.yaml'],
    'Кассовый контур': ['docs/31_cash_schema_and_audit.md', 'docs/28_cash_execution_bridge.md'],
    'Монитор шоков': ['docs/32_external_validation.md', 'data/reports/competition/shock_benchmark_summary.csv', 'data/reports/competition/shock_calibration_summary.csv'],
    'БО': ['docs/05_formula_registry.md', 'docs/30_function_reference.md'],
    'Отчёт': ['docs/16_methodology_v1.md', 'docs/29_source_evidence_register.md'],
    'Источники': ['config/external_sources.json', 'config/official_sources.json', 'docs/32_external_validation.md'],
    'Данные': ['docs/04_data_contracts.md', 'config/source_registry.yaml'],
    'Ввод данных': ['docs/04_data_contracts.md', 'docs/22_budget_project_import.md'],
    'Методика': ['docs/16_methodology_v1.md', 'docs/05_formula_registry.md', 'docs/33_project_logic_review.md', 'docs/34_author_structure_comments.md'],
}


def render_page_sources(root: Path, page: str) -> None:
    st.divider()
    section_header('Источники и основания раздела', 'ПРОИСХОЖДЕНИЕ ДАННЫХ',
                   'Ссылки на документы, методику и файлы расчёта. Наличие ссылки само по себе не означает, что данные подключены.')
    if page in {'Обзор', 'Бюджет', 'БО', 'Отчёт', 'Данные', 'Ввод данных'}:
        official = json.loads((root / 'config/official_sources.json').read_text(encoding='utf-8'))
        for item in official['sources'].values():
            source_card(authority=item['authority'], document=item['decision'],
                        publication=item['publication_date'], stage='Официальная страница документа',
                        verification='Ссылка из каталога проекта; применимость к текущему срезу проверяется отдельно',
                        url=item['page_url'])
    if page in {'Кассовый контур', 'Монитор шоков', 'Источники', 'Данные'}:
        registry = json.loads((root / 'config/external_sources.json').read_text(encoding='utf-8'))
        labels = {'candidate': 'Кандидат', 'connected': 'Получен, сверка не завершена', 'validated': 'Проверен по отчёту сверки', 'rejected': 'Отклонён'}
        for item in registry['external_sources']:
            source_card(authority='Реестр внешних источников MESM', document=item['title'],
                        publication=f"Добавлен в реестр: {item['added_at']}",
                        stage=labels[item['status']], verification=item['blocker'], url=item['url'])
    if page in {'Модели', 'Монитор шоков'}:
        st.caption('Контрольные сценарии и лаборатория — синтетические расчёты MESM. Их показатели не являются измеренным эффектом внедрения в Сургуте.')
    if page == 'Кассовый контур':
        st.caption('Источник текущего расчёта — выбранный демонстрационный набор или CSV пользователя. Идентификатор и документ строки находятся в исходной выгрузке.')
    st.markdown('**Методика и файлы проекта**')
    for relative in PAGE_FILES.get(page, []):
        file = root / relative
        if file.is_file():
            st.download_button(f'Открыть / скачать · {file.name}', file.read_bytes(), file_name=file.name,
                               key=f'page_source_{page}_{file.name}')
        else:
            st.caption(f'{relative} — файл пока отсутствует в сборке')
