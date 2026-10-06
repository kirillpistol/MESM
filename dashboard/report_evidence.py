from mesm.data.intake import load_current_dataset, resolve_dataset_path
"""Дополнения к пяти вопросам отчёта: происхождение, контекст и проверяемость."""
import html,json
from pathlib import Path
import pandas as pd


def esc(value):return html.escape(str(value),quote=True)
def num(value):return f'{float(value):,.2f}'.replace(',',' ').replace('.',',') if pd.notna(value) else 'Нет данных'
def table(headers,rows):return '<table><tr>'+''.join(f'<th>{esc(v)}</th>' for v in headers)+'</tr>'+''.join('<tr>'+''.join(f'<td>{v}</td>' for v in row)+'</tr>' for row in rows)+'</table>'


def bars(labels,values,title,unit='%'):
    maximum=max([abs(float(v)) for v in values]+[1])
    rows=[]
    for i,(label,value) in enumerate(zip(labels,values)):
        y=40+i*58;width=abs(float(value))/maximum*420
        rows.append(f'<text x="12" y="{y+14}">{esc(label)}</text><rect x="240" y="{y}" width="{width:.2f}" height="22" fill="#4676C9"/><text x="240" y="{y+43}">{esc(num(value))} {esc(unit)}</text>')
    return f'<h3>{esc(title)}</h3><svg role="img" aria-label="{esc(title)}" viewBox="0 0 760 {len(rows)*58+55}" style="width:100%;font:14px Arial">'+''.join(rows)+'</svg>'


def enrich_report(root:Path,municipality,latest):
    out={'facts':'','calculation':'','result':'','novelty':''}
    year=int(latest.iloc[-1]['year']) if not latest.empty else None
    trace=root/'data/manifest/report_trace_2025.json'
    if trace.exists() and municipality=='Сургут' and year==2025 and not (root/'data/intake/active/budget_official_plan.csv').exists():
        evidence=json.loads(trace.read_text(encoding='utf-8'))
        rows=[]
        for item in evidence['evidence']:
            page=item.get('page');link=f'<a href="{esc(evidence["source_url"])}#page={page}">PDF, стр. {page}</a>' if page else 'Не установлена'
            rows.append([esc(item['field']),esc(num(item['value'])),link,esc(item.get('row_label') or 'Производный показатель'),esc(item['method']),esc({'verified_pdf':'Сверено с PDF','needs_operand_trace':'Не хватает источника компонента'}.get(item['status'],item['status']))])
        out['facts']+='<h3>Прослеживаемость каждого числа</h3>'+table(['Поле','тыс. руб.','Страница PDF','Место / строка','Метод','Статус'],rows)
        out['facts']+=f'<p>SHA-256 проверенного PDF: <code>{esc(evidence["source_sha256"])}</code>. Координаты фрагментов и версия извлекателя сохранены в <code>data/manifest/report_trace_2025.json</code>. Это номера страниц файла PDF (с 1). Страницы подтверждены чтением документа; номера таблиц и ячеек не выдумываются при текстовом извлечении.</p>'
    plan_path=root/'data/processed/official_budget_plan_surgut_2025_2027.csv'
    plan=load_current_dataset('budget_official_plan',root)
    if plan.empty: plan=pd.DataFrame(columns=['municipality_name','year'])
    matched=plan[plan.municipality_name.eq(municipality)&plan.year.eq(year)]
    if not matched.empty:
        row=matched.iloc[-1];r,e,f=[float(row[k]) for k in ['total_revenue','expenditure','financing_sources']];d=e-r
        values=[r,-e,f,0];levels=[0,r,r-e,r-e+f];scale=max(abs(v) for v in levels+[r,e,f,1]);baseline=270
        svg=[]
        for i,(label,value) in enumerate(zip(['Доходы','Расходы','Финансирование','Итог R−E+F'],values)):
            if i==3:start=0;end=r-e+f
            else:start=levels[i];end=levels[i+1]
            top=baseline-max(start,end)/scale*200;height=max(abs(end-start)/scale*200,2);x=25+i*190
            svg.append(f'<rect x="{x}" y="{top:.2f}" width="140" height="{height:.2f}" fill="{"#CA5358" if value<0 else "#4676C9"}"/><text x="{x}" y="310">{label}</text><text x="{x}" y="335">{num(end-start)} </text>')
        out['calculation']+='<h3>Арифметическая увязка плана, тыс. руб.</h3><svg role="img" aria-label="Доходы минус расходы плюс финансирование" viewBox="0 0 800 360" style="width:100%;font:13px Arial"><line x1="10" x2="790" y1="270" y2="270" stroke="#777"/>'+''.join(svg)+'</svg><p>Высота шагов отражает суммы. Итог — арифметическая увязка, а не остаток на банковском счёте.</p>'
        out['calculation']+=bars(['Плановый дефицит','Предусмотренное финансирование'],[max(d,0),f],'Покрытие планового дефицита','тыс. руб.')
        if municipality=='Сургут' and year==2025:
            out['facts']+='<h3>Хронология документа</h3>'+table(['Дата','Событие','Основание'],[['20.12.2024','Принят на заседании Думы','PDF решения №713, стр. 1'],['23.12.2024','Дата решения №713-VII ДГ','Реквизиты приложений PDF'],[esc(row.publication_date),'Дата публикации в каталоге проекта','Поле publication_date; исходная страница требует отдельной архивной сверки']])+'<p>Уточнения и даты исполнения не добавлены: подтверждённых событий в этом отчёте пока нет.</p>'
    inputs_path=resolve_dataset_path('reference_core',root)
    if inputs_path.exists():
        core=load_current_dataset('reference_core',root);selected=core[core.municipality_name.eq(municipality)]
        if year is not None:
            previous=selected[selected.year.eq(year-1)]
            if not previous.empty and not matched.empty:
                previous=previous.iloc[-1];current=matched.iloc[-1]
                rows=[]
                for label,planned,actual in [('Налоговые и неналоговые доходы',current.revenue_base,previous.tax_actual+previous.nontax_actual),('Общие расходы',current.expenditure,previous.total_expense)]:
                    delta=(planned/actual-1)*100 if actual else None
                    rows.append([label,num(planned),num(actual),num(delta)+'%' if delta is not None else 'База равна нулю'])
                out['facts']+=f'<h3>Контекст: план {year} и факт {year-1}</h3>'+table(['Показатель',f'{year} план, тыс. руб.',f'{year-1} факт, тыс. руб.','Δ к указанной базе'],rows)+f'<p>Факт взят из <code>{esc(inputs_path.relative_to(root))}</code>. Это сопоставление плана с прошлогодним фактом, не темп роста исполнения и не доказательство причин изменения. Полные фактические доходы и дефицит прошлогоднего бюджета здесь отсутствуют; они не заменяются собственными доходами.</p>'
        peer_year=year-1 if year is not None else None
        peer=core[core.year.eq(peer_year)].copy()
        peer['debt_ratio']=peer.municipal_debt/peer.own_revenue_base.replace(0,float('nan'))*100
        names=[municipality,'Нижневартовск','Нефтеюганск']
        display=peer[peer.municipality_name.isin(names)].dropna(subset=['debt_ratio'])
        if not display.empty:
            labels=display.municipality_name.tolist();values=display.debt_ratio.tolist()
            median=peer.debt_ratio.dropna().median()
            labels.append('Медиана имеющейся выборки');values.append(median)
            out['facts']+=bars(labels,values,f'Контекст долга, {peer_year}: долг / own_revenue_base')
            out['facts']+='<p>Медиана рассчитана по строкам муниципалитетов текущего набора, не объявляется медианой всего ХМАО. Доходы на душу не рассчитаны: нет проверенной численности населения. Ранжирование само по себе не определяет «норму» и не объясняет нулевую непокрытую потребность.</p>'
    norms=[('БК РФ, ст. 92.1','https://www.consultant.ru/document/cons_doc_LAW_19702/6f11e8bb720f79997a479fc6c1e98b78f23c3755/','Ограничения дефицита; нужны применимая редакция, база и допустимые исключения.'),('Приказ Минфина №191н','https://base.garant.ru/12181732/','Инструкция по бюджетной отчётности, включая форму 0503117.'),('Приказ Минфина №82н','https://base.garant.ru/404917355/','Бюджетная классификация, не утверждение формы 0503117.'),('Постановление Сургута №4058','https://base.garant.ru/29125624/','Порядок ведения РРО; не правило аналитического сглаживания поступлений.')]
    if municipality != 'Сургут':
        norms=[n for n in norms if 'Сургута' not in n[0]]
    out['result']+='<h3>Нормативные основания и предел вывода</h3><ul>'+''.join(f'<li><a href="{url}">{esc(name)}</a>: {esc(role)}</li>' for name,url,role in norms)+'</ul><p>Нулевой разрыв финансирования не равен соблюдению ст. 92.1. Формула legal_deficit_base в текущих данных: revenue_base − additional_ndfl. Повторное вычитание трансфертов из revenue_base ошибочно: эта база уже содержит только налоговые и неналоговые доходы. Доказательство правового соответствия требует отдельной проверки редакции норм, категории муниципалитета и состава исключений.</p>'
    hypotheses=[('H1','Качество прогноза относительно baseline','Не проверяется этим отчётом: нет результатов отдельного теста ошибок'),('H2','Полезное опережение Reference','Не проверяется: нет согласованных событий и дат доступности'),('H3','Дополнительная ценность двух контуров','Не проверяется: нет теста совместного результата'),('H4','Экономическая полезность','Не проверяется: нет оценок выгод и стоимости ошибок'),('H5','Польза адаптации модели','Не проверяется: нет сопоставимого adaptive/frozen теста')]
    out['novelty']+='<h3>Связь с гипотезами проекта</h3>'+table(['ID','Определение из docs/14_hypothesis_tests.md','Статус в этом отчёте'],hypotheses)
    cal=root/'data/reports/competition/shock_calibration_summary.csv'
    if cal.exists():
        frame=pd.read_csv(cal)
        out['novelty']+='<h3>Отдельная проверка калибровки, не гипотеза H5</h3>'+table(['Детектор','Доля ложных тревог на контрольных траекториях'],[[esc(row.detector),num(row.null_path_fpr*100)+'%'] for row in frame.itertuples()])+'<p>Это результаты синтетического development-набора. Они показывают достижение заданного порога на этой выборке, но не подтверждают FPR на реальных муниципальных данных или на независимом holdout.</p>'
    return out
