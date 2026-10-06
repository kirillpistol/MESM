from pathlib import Path
import importlib.util,json,threading,urllib.request,urllib.error
import pytest
from http.server import ThreadingHTTPServer
from mesm.access.store import build_store,DataStore
from mesm.access.server import handler_factory
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def store(tmp_path):
    build_store(ROOT,tmp_path/"test.sqlite")
    return DataStore(tmp_path/"test.sqlite")

def test_store_snapshot_and_filters(store,tmp_path):
    assert store.metadata()["read_only"]
    calc=store.rows("budget_calculations",municipality="Сургут",period="2025")["rows"][0]
    assert calc["calculated_deficit"] == pytest.approx(2241858.57535)
    assert calc["uncovered_plan_need"] == pytest.approx(0,abs=1e-7)
    assert store.rows("budget_official_plan",municipality="Несуществующий город")["rows"]==[]
    rows=store.rows("budget_official_plan",municipality="Сургут",period="2025")["rows"]
    assert len(rows)==1 and rows[0]["year"]==2025
    other=build_store(ROOT,tmp_path/"other.sqlite")
    assert other["snapshot_id"]==store.metadata()["snapshot_id"]
    with pytest.raises(ValueError):store.rows("fiscal_panel",limit=1001)
    with pytest.raises(KeyError):store.rows("../../secrets")
    with store.connect() as conn:
        with pytest.raises(Exception):conn.execute("DELETE FROM records")

def test_api_auth_filters_and_report(store):
    token="test-local-token-0123456789012345"
    server=ThreadingHTTPServer(("127.0.0.1",0),handler_factory(store,token,ROOT))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f"http://127.0.0.1:{server.server_port}"
    def get(path,auth=True):
        headers={"Authorization":"Bearer "+token} if auth else {}
        return urllib.request.urlopen(urllib.request.Request(base+path,headers=headers),timeout=30)
    try:
        with pytest.raises(urllib.error.HTTPError) as err:get("/v1/catalog",False)
        assert err.value.code==401
        with get("/v1/data?dataset=budget_official_plan&municipality=Missing") as res:assert json.load(res)["total"]==0
        with pytest.raises(urllib.error.HTTPError) as err:get("/v1/data?dataset=fiscal_panel&limit=0")
        assert err.value.code==400
        with get("/v1/report?municipality=%D0%A1%D1%83%D1%80%D0%B3%D1%83%D1%82") as res:
            assert "Какую проблему решаем?" in res.read().decode()
    finally:server.shutdown();server.server_close();thread.join()

def test_other_municipality_profile(tmp_path):
    spec=importlib.util.spec_from_file_location("init_city",ROOT/"scripts/init_municipality.py")
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    profile=module.create_profile("Другой город","12345678","Другой регион",tmp_path)
    assert json.loads(profile.read_text())["municipality_name"]=="Другой город"
    assert len((tmp_path/"reference_core.csv").read_text(encoding="utf-8-sig").splitlines())==1
    with pytest.raises(ValueError):module.create_profile("Город","bad","Регион",tmp_path/"bad")

def test_data_access_screen_renders():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(ROOT/"dashboard/app.py"),default_timeout=90).run()
    app.sidebar.radio[0].set_value("Данные и ИИ");app.run()
    assert not app.exception
    assert any("Данные и подключение ИИ" in x.value for x in app.markdown)


def test_active_plan_other_city_is_used_in_report(tmp_path):
    import shutil,sys,pandas as pd
    root=tmp_path/"project";root.mkdir()
    shutil.copytree(ROOT/"config",root/"config")
    (root/"data/intake/active").mkdir(parents=True)
    source=pd.read_csv(ROOT/"data/processed/official_budget_plan_surgut_2025_2027.csv").head(1)
    source["municipality_name"]="Другой город"
    source["total_revenue"]=100;source["expenditure"]=120;source["financing_sources"]=15
    source.to_csv(root/"data/intake/active/budget_official_plan.csv",index=False)
    from mesm.access.store import catalogue
    data=dict((item["id"],frame) for item,frame in catalogue(root))
    assert data["budget_calculations"].iloc[0]["uncovered_plan_need"]==5
    sys.path.insert(0,str(ROOT/"dashboard"))
    from final_report import build_question_report
    html=build_question_report(root,"Другой город",pd.DataFrame([{"year":2025}]))
    assert "5,00 тыс. руб." in html
    assert "20.12.2024" not in html
    assert "Постановление Сургута" not in html
