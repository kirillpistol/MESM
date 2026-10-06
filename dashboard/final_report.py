from __future__ import annotations
from mesm.data.intake import load_current_dataset, resolve_dataset_path

import html
from datetime import datetime
from math import isfinite
from pathlib import Path

import pandas as pd


def _escape(value) -> str:
    return html.escape(str(value), quote=True)


def _number(value) -> str:
    try:
        value = float(value)
        return f'{value:,.2f}'.replace(',', ' ').replace('.', ',') if isfinite(value) else 'Нет данных'
    except (TypeError, ValueError):
        return 'Нет данных'


def build_question_report(root: Path, municipality: str | None, latest: pd.DataFrame) -> str:
    """Отчёт на основании общего среза, без зависимости от страницы и демосценария."""
    place = municipality or 'Муниципалитет не выбран'
    year = int(latest.iloc[-1]['year']) if not latest.empty else None
    facts, calculations, findings = [], [], []
    plan_path = resolve_dataset_path('budget_official_plan',root)
    plan = load_current_dataset('budget_official_plan', root)
    if not plan.empty and year is not None:
        matches = plan[plan['municipality_name'].eq(place) & plan['year'].eq(year)]
        if not matches.empty:
            row = matches.iloc[-1]
            source = row.get('source_url', '')
            link = f'<a href="{_escape(source)}">Открыть документ</a>' if str(source).startswith('https://') else 'Ссылка не указана'
            idx = matches.index[-1]
            facts.append(f'<p><b>План бюджета на {year} год</b>, стадия: {_escape(row.get("stage", ""))}. Это плановые назначения, не фактическое исполнение.</p><p>Документ: {_escape(row.get("source_document", ""))}; публикация: {_escape(row.get("publication_date", ""))}. {link}.</p><p>Извлечено из <code>{_escape(plan_path.relative_to(root))}</code>, строка {int(idx)+2} CSV с учётом заголовка. Единица: тыс. руб. Точная привязка доступных показателей к PDF приведена ниже в таблице прослеживаемости. Неподтверждённые привязки обозначены отдельно.</p>')
            fields = [('total_revenue','Плановые доходы'),('expenditure','Плановые расходы'),('financing_sources','Источники финансирования дефицита'),('revenue_base','Доходная база без трансфертов'),('legal_deficit_base','База расчёта ограничения дефицита')]
            facts.append('<table><tr><th>Показатель / поле</th><th>тыс. руб.</th></tr>'+''.join(f'<tr><td>{label} <code>{key}</code></td><td>{_number(row.get(key))}</td></tr>' for key,label in fields)+'</table>')
            revenue, expense, financing = [float(row[k]) for k in ('total_revenue','expenditure','financing_sources')]
            if not all(isfinite(v) for v in (revenue,expense,financing)):
                calculations.append('<p>Расчёт не выполнен: исходные суммы неконечны.</p>')
            else:
                deficit = expense-revenue
                gap = max(deficit-financing,0)
                calculations.append(f'<h3>Покрывает ли плановое финансирование превышение расходов над доходами?</h3><p><b>D = E − R</b>, где E — плановые расходы, R — плановые доходы.</p><p>D = {_number(expense)} − {_number(revenue)} = <b>{_number(deficit)} тыс. руб.</b></p><p><b>G = max(D − F, 0)</b>, где F — источники финансирования дефицита, G — непокрытая плановая потребность.</p><p>G = max({_number(deficit)} − {_number(financing)}, 0) = <b>{_number(gap)} тыс. руб.</b></p>')
                findings.append(f'<p><b>Вывод 1.</b> По плановым назначениям расходы превышают доходы на {_number(deficit)} тыс. руб.' if deficit>0 else f'<p><b>Вывод 1.</b> По плановым назначениям расходы не превышают доходы; разность E − R составляет {_number(deficit)} тыс. руб.')
                findings[-1] += f' После учёта предусмотренного финансирования непокрытая плановая потребность составляет {_number(gap)} тыс. руб.</p>'
                findings.append('<p><b>Основание вывода:</b> три исходные суммы и две подстановки, приведённые выше. Это проверка арифметической увязки плана. Она не доказывает поступление финансирования, отсутствие кассовых разрывов внутри года или соблюдение всех бюджетных ограничений.</p><p><b>Что проверить:</b> график поступления финансирования, фактическое месячное исполнение и начальный остаток.</p>')
    if not latest.empty:
        row = latest.iloc[-1]
        facts.append(f'<h3>Официальный годовой аналитический срез</h3><p>Период: {_escape(row.get("period_end", year))}. Файл-источник: {_escape(row.get("source_file", "не указан"))}. Статус: {_escape(row.get("data_status", "не указан"))}. Дата публикации: {_escape(row.get("publication_date", "не указана")) or "не указана"}.</p>')
        labels = [('income_plan_deviation','Отклонение доходов от первоначального плана'),('program_expense_share','Доля программных расходов'),('debt_load','Долговая нагрузка')]
        facts.append('<table><tr><th>Показатель</th><th>Значение</th></tr>'+''.join(f'<tr><td>{label}</td><td>{_number(float(row[key])*100) if pd.notna(row.get(key)) else "Нет данных"}%</td></tr>' for key,label in labels)+'</table>')
        calculations.append('<h3>Как получены долевые показатели?</h3><p>Отклонение доходов = (факт − первоначальный план) / первоначальный план. Доля программных расходов = программные расходы / общие расходы. Представление доли в процентах: доля × 100.</p><p>В текущем годовом срезе сохранены готовые коэффициенты. Исходные числители и знаменатели здесь отсутствуют, поэтому их подстановка не выдумывается. Формулу долговой нагрузки необходимо сверить с методикой файла-источника; автоматически подменять её отношением долга к любым доходам нельзя.</p>')
        findings.append('<p><b>Вывод 2.</b> Годовые коэффициенты позволяют описать опубликованный финансовый срез. Полная проверка расчёта требует исходных сумм из указанного документа. Эти коэффициенты сами по себе не устанавливают причину отклонения или дату начала изменения.</p>')
    if not facts:
        facts.append('<p>Для выбранного муниципалитета нет фактов в текущем срезе. Числовой вывод не формируется.</p>')
    if not calculations:
        calculations.append('<p>Нет достаточных исходных чисел для воспроизводимого расчёта.</p>')
    if not findings:
        findings.append('<p>Подтверждённый числовой вывод невозможен до получения исходных данных.</p>')
    sections = [
      ('Какую проблему решаем?', '<p>Финансовому органу необходимо понять, какие изменения доходов, расходов и финансирования требуют проверки и управленческого решения. Годовой план показывает назначенные суммы, но не раскрывает движение денег внутри года. MESM связывает показатель с источником и расчётом, чтобы сформировать проверяемый вывод и список необходимых действий.</p><p>В данном отчёте решается доступная по данным задача: проверка арифметической увязки плановых доходов, расходов и финансирования и описание официального годового среза.</p>'),
      ('Какие факты используем?', ''.join(facts)),
      ('Что рассчитываем?', ''.join(calculations)),
      ('Что означает результат?', ''.join(findings)+'<p>Реальный месячный кассовый разрыв и раннее обнаружение структурного изменения этим отчётом не установлены. Локально загруженные кассовые файлы и учебная лаборатория в общий отчёт автоматически не включаются.</p>'),
      ('В чём новизна?', '<p>Проектное решение MESM — воспроизводимая связь источника, показателя, преобразования и вывода в одном аналитическом процессе. Здесь эта связь показана на арифметической проверке бюджета: читатель может восстановить результат из приведённых чисел.</p><p>Прозрачное происхождение каждого вывода — реализованное свойство отчёта. Измеренный эффект внедрения и научная новизна пока не установлены. Возможность раннего предупреждения остаётся гипотезой до проверки на реальном временном ряду. Выводы этого отчёта не используются как доказательство этой гипотезы.</p>')]
    from report_evidence import enrich_report
    extra = enrich_report(root, municipality, latest)
    sections = [(title, text + extra.get(key, '')) for (title,text),key in zip(sections, ['', 'facts', 'calculation', 'result', 'novelty'])]
    body=''.join(f'<section><h2>{_escape(title)}</h2>{text}</section>' for title,text in sections)
    return f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>MESM — L3 · итоговый отчёт</title><style>body{{font:16px/1.65 Arial,sans-serif;color:#202329;max-width:1000px;margin:40px auto;padding:0 24px}}h1,h2{{line-height:1.3}}section{{margin:32px 0;border-top:1px solid #ddd;padding-top:16px}}table{{border-collapse:collapse;width:100%;margin:16px 0}}td,th{{border:1px solid #ddd;padding:10px;text-align:left;overflow-wrap:anywhere}}p,code,a{{overflow-wrap:anywhere}}@media print{{body{{margin:0;font-size:11pt}}h2{{break-after:avoid}}tr{{break-inside:avoid}}}}</style></head><body><h1>MESM — L3 · итоговый аналитический отчёт</h1><p>Муниципалитет: <b>{_escape(place)}</b> · год среза: {_escape(year or "не указан")}<br>Сформирован: {datetime.now():%d.%m.%Y %H:%M}</p>{body}</body></html>'
