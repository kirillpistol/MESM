from pathlib import Path
import json,threading,urllib.request,urllib.error
from http.server import ThreadingHTTPServer
import pytest
from mesm.access.store import build_store,DataStore
from mesm.access.server import handler_factory
ROOT=Path(__file__).resolve().parents[1]
def test_repeatable_cycle_and_closed_scope(tmp_path):
    build_store(ROOT,tmp_path/'source.sqlite');store=DataStore(tmp_path/'source.sqlite');token='local-cycle-test-token-1234567890'
    server=ThreadingHTTPServer(('127.0.0.1',0),handler_factory(store,token,ROOT));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def req(path,body=None):
        raw=None if body is None else json.dumps(body).encode()
        request=urllib.request.Request(f'http://127.0.0.1:{server.server_port}'+path,data=raw,headers={'Authorization':'Bearer '+token})
        with urllib.request.urlopen(request,timeout=20) as res:return json.load(res)
    try:
        node=req('/v1/node');packages=[]
        for _ in range(2):
            session=req('/v1/sessions/open',{'municipality':'Сургут','snapshot_id':node['snapshot_id']})
            route='/v1/report-package?municipality=%D0%A1%D1%83%D1%80%D0%B3%D1%83%D1%82&session_id='+session['session_id']
            packages.append(req(route))
            assert req('/v1/sessions/close',{'session_id':session['session_id']})['source_data_preserved']
            assert req('/v1/sessions/close',{'session_id':session['session_id']})['status']=='closed'
            with pytest.raises(urllib.error.HTTPError) as err:req(route)
            assert err.value.code==400
        assert packages[0]['snapshot_id']==packages[1]['snapshot_id']
        assert packages[0]['budget_calculations']==packages[1]['budget_calculations']
        assert packages[0]['contract']=='genesis.l3-report/1'
    finally:server.shutdown();server.server_close();thread.join()


def test_completed_cycles_do_not_exhaust_active_capacity():
    from mesm.access.sessions import Sessions
    sessions=Sessions()
    for _ in range(300):
        value=sessions.open("Сургут","a"*64)
        assert sessions.close(value["session_id"])["source_state"]=="standby"
