"""python scripts/build_pdf_trace.py decision713.pdf — доказательства 2025 из проверенного PDF."""
import argparse,json,hashlib,re
from pathlib import Path
from decimal import Decimal
import pdfplumber

if __name__ == '__main__':
 p=argparse.ArgumentParser();p.add_argument('pdf');args=p.parse_args()
 root=Path(__file__).resolve().parents[1]
 targets=[('total_revenue',1,'49 278 363 595,19','Пункт 1: общий объём доходов'),('expenditure',1,'51 520 222 170,54','Пункт 1: общий объём расходов'),('financing_sources',14,'2 241 858 575,35','Приложение 2: источники финансирования дефицита'),('revenue_base',10,'20 489 196 601,16','Приложение 1: налоговые и неналоговые доходы')]
 import csv
 row=next(r for r in csv.DictReader((root/'data/processed/official_budget_plan_surgut_2025_2027.csv').open()) if r['year']=='2025')
 evidence=[]
 with pdfplumber.open(args.pdf) as pdf:
  for field,page,raw,label in targets:
   matches=pdf.pages[page-1].search(re.escape(raw).replace(r'\ ',r'\s+'))
   if not matches:raise ValueError(f'Не найдено {field}')
   value=Decimal(raw.replace(' ','').replace(',','.'))/1000
   if abs(value-Decimal(row[field]))>Decimal('.00001'):raise ValueError(f'Сумма не совпала: {field}')
   match=matches[0]
   evidence.append(dict(field=field,value=str(value),unit='тыс. руб.',raw_value=raw,raw_unit='руб.',page=page,table_index=None,row_label=label,col_label='2025 год' if page>1 else 'Пункт 1',extractor='pdfplumber search',extractor_version=pdfplumber.__version__,raw_text_bbox=[match[k] for k in ['x0','top','x1','bottom']],method='точное текстовое совпадение; рубли / 1000',status='verified_pdf'))
 evidence.append(dict(field='legal_deficit_base',value=row['legal_deficit_base'],unit='тыс. руб.',page=None,table_index=None,row_label=None,col_label=None,raw_text_bbox=None,extractor=None,extractor_version=None,method='revenue_base − additional_ndfl; исходное значение additional_ndfl требует отдельного документа',status='needs_operand_trace'))
 output=dict(municipality='Сургут',year=2025,source_url=row['source_url'],source_document=row['source_document'],source_sha256=hashlib.sha256(Path(args.pdf).read_bytes()).hexdigest(),checked_at='2026-10-06',evidence=evidence)
 target=root/'data/manifest/report_trace_2025.json';target.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(target)
