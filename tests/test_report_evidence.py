from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"dashboard"))
import pandas as pd
from final_report import build_question_report

ROOT=Path(__file__).resolve().parents[1]


def test_trace_matches_snapshot_and_has_coordinates():
    trace=json.loads((ROOT/'data/manifest/report_trace_2025.json').read_text())
    plan=pd.read_csv(ROOT/'data/processed/official_budget_plan_surgut_2025_2027.csv').iloc[0]
    for item in trace['evidence']:
        assert abs(float(item['value'])-float(plan[item['field']]))<1e-5
        if item['status']=='verified_pdf':
            assert item['page']>=1 and len(item['raw_text_bbox'])==4
    assert next(e for e in trace['evidence'] if e['field']=='legal_deficit_base')['page'] is None


def test_report_preserves_hypotheses_and_evidence_limits():
    panel=pd.read_csv(ROOT/'data/processed/fiscal_reference_panel.csv')
    latest=panel[panel.municipality_name.eq('Сургут')].sort_values('year').tail(1)
    report=build_question_report(ROOT,'Сургут',latest)
    assert '#page=14' in report
    assert 'Польза адаптации модели' in report
    assert 'Нулевой разрыв финансирования не равен соблюдению' in report
    assert 'план 2025 и факт 2024' in report
    assert '<svg' in report
