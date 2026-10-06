from pathlib import Path
from math import isclose
import json
import pandas as pd
from mesm.access.store import build_store,DataStore
from mesm.access.methodology import build_methodology
from mesm.access.package import report_package
ROOT=Path(__file__).resolve().parents[1]
def test_exported_formulas_match_public_snapshot(tmp_path):
    build_store(ROOT,tmp_path/'source.sqlite');store=DataStore(tmp_path/'source.sqlite')
    registry=store.metadata()['evidence']['methodology']['formula_registry']
    assert len({f['id'] for f in registry['formulas']})==5
    assert all(f['version']=='1.0.0' and f['checks'] and f['limitations'] for f in registry['formulas'])
    for row in store.rows('budget_calculations',limit=1000)['rows']:
        deficit=row['expenditure']-row['total_revenue']
        assert isclose(deficit,row['calculated_deficit'],abs_tol=1e-7)
        assert isclose(max(deficit-row['financing_sources'],0),row['uncovered_plan_need'],abs_tol=1e-7)
    core=pd.read_csv(ROOT/'data/processed/official_quality_core_inputs_2023_2025.csv')
    for row in store.rows('fiscal_panel',limit=1000)['rows']:
        values=core[(core.year==row['year'])&(core.municipality_name==row['municipality_name'])].iloc[0]
        planned=values.tax_initial+values.nontax_initial
        expected=(values.tax_actual+values.nontax_actual-planned)/planned if planned else None
        if expected is not None:assert isclose(expected,row['income_plan_deviation'],rel_tol=1e-7,abs_tol=1e-9)
        if values.total_expense:assert isclose(values.program_expense/values.total_expense,row['program_expense_share'],rel_tol=1e-7,abs_tol=1e-9)
        if values.own_revenue_base:assert isclose(values.municipal_debt/values.own_revenue_base,row['debt_load'],rel_tol=1e-7,abs_tol=1e-9)
    package=report_package(ROOT,store,'Сургут')
    assert package['methodology']['formula_registry']==registry
    assert package['methodology']['methodology_id']==store.metadata()['evidence']['methodology']['methodology_id']

def test_document_revision_changes_methodology_id(tmp_path):
    (tmp_path/'docs').mkdir()
    path=tmp_path/'docs/39_methodology_and_updates.md';path.write_text('version one')
    first=build_methodology(tmp_path)
    path.write_text('version two')
    second=build_methodology(tmp_path)
    assert first['methodology_id']!=second['methodology_id']
    assert first['documents'][0]['content']=='version one'
