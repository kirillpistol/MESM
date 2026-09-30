from datetime import date
import json
import pandas as pd
import pytest
from mesm.sources.reconciliation import reconcile
from mesm.sources.registry import transition


def frame(values, available='2020-01-01'):
    return pd.DataFrame(dict(period=[str(2000+i) for i in range(len(values))], oktmo=['001']*len(values),
        value=values, available_at=[available]*len(values), frequency=['annual']*len(values),
        unit=['rub']*len(values), measure=['ndfl_cash']*len(values)))


def test_two_years_cannot_validate_correlation():
    report = reconcile(frame([1,2]),frame([2,4]),as_of=date(2026,1,1))
    assert report['municipalities'][0]['status'] == 'insufficient'
    assert not report['detector_ready']


def test_published_overlap_and_constant_series():
    assert reconcile(frame(range(8)),frame(range(8)),as_of=date(2026,1,1))['municipalities'][0]['correlation'] == pytest.approx(1)
    assert reconcile(frame(range(8)),frame([1]*8),as_of=date(2026,1,1))['municipalities'][0]['status'] == 'insufficient'
    assert reconcile(frame(range(8)),frame(range(8),'2027-01-01'),as_of=date(2026,1,1))['overlap_rows'] == 0


def test_duplicates_and_incompatible_measure_rejected():
    f=frame(range(8))
    with pytest.raises(ValueError): reconcile(pd.concat([f,f]),f,as_of=date(2026,1,1))
    g=f.copy(); g['measure']='ndfl_assessed'
    with pytest.raises(ValueError): reconcile(f,g,as_of=date(2026,1,1))


def test_registry_requires_evidence_and_records_history(tmp_path):
    from mesm.sources.registry import load_registry
    registry=load_registry('config/external_sources.json')
    s=registry['external_sources'][0];s['status']='candidate';s['artifact_sha256']=None
    path=tmp_path/'registry.json';path.write_text(json.dumps(registry))
    with pytest.raises(ValueError): transition(path,s['id'],'connected',actor='kirill',evidence='test')
    s['artifact_sha256']='a'*64;path.write_text(json.dumps(registry))
    transition(path,s['id'],'connected',actor='kirill',evidence='Downloaded file')
    assert load_registry(path)['history'][-1]['status']=='connected'
