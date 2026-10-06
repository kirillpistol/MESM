from __future__ import annotations
import argparse
import hmac
import json
import os
import ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from mesm.access.store import DataStore, build_store


def handler_factory(store: DataStore, token: str, root: Path):
    from mesm.access.sessions import Sessions
    sessions=Sessions()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # URL и токен не пишутся в журналы.
        def respond(self, code, content, mime="application/json; charset=utf-8"):
            body = content.encode("utf-8") if isinstance(content,str) else json.dumps(content,ensure_ascii=False,allow_nan=False).encode("utf-8")
            self.send_response(code); self.send_header("Content-Type",mime)
            self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-store")
            self.end_headers(); self.wfile.write(body)
        def do_POST(self):
            if not hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer "+token):
                return self.respond(401,{"error":"Требуется Bearer token"})
            try:
                size=int(self.headers.get("Content-Length","0"))
                if not 0<size<=4096:raise ValueError("Invalid body length")
                body=json.loads(self.rfile.read(size))
                if self.path=="/v1/sessions/open":
                    if set(body)!={"municipality","snapshot_id"}:raise ValueError("Unexpected session fields")
                    if body["municipality"] not in {m["name"] for m in store.municipalities()} or body["snapshot_id"]!=store.metadata()["snapshot_id"]:
                        raise ValueError("Source scope mismatch")
                    return self.respond(200,sessions.open(body["municipality"],body["snapshot_id"]))
                if self.path=="/v1/sessions/close":
                    if set(body)!={"session_id"}:raise ValueError("Unexpected close fields")
                    return self.respond(200,sessions.close(body["session_id"]))
                return self.respond(404,{"error":"Маршрут не найден"})
            except (ValueError,TypeError,KeyError):
                return self.respond(400,{"error":"Некорректная или закрытая сессия"})
        def do_GET(self):
            if not hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer "+token):
                return self.respond(401,{"error":"Требуется Bearer token"})
            url = urlsplit(self.path)
            query = parse_qs(url.query)
            if any(len(v)!=1 for v in query.values()):
                return self.respond(400,{"error":"Повторные параметры запрещены"})
            q = {k:v[0] for k,v in query.items()}
            try:
                if url.path == "/v1/node":
                    from mesm.access.package import descriptor
                    return self.respond(200,descriptor(root,store))
                if url.path == "/v1/health":
                    return self.respond(200,store.metadata())
                if url.path == "/v1/catalog":
                    return self.respond(200,{"datasets":store.datasets(),"snapshot":store.metadata()})
                if url.path == "/v1/municipalities":
                    return self.respond(200,store.municipalities())
                if url.path == "/v1/data":
                    if set(q)-{"dataset","municipality","period","limit","offset","session_id"}:
                        raise ValueError("Неизвестный параметр")
                    if "session_id" in q:
                        sessions.require(q["session_id"],q.get("municipality"),store.metadata()["snapshot_id"])
                    return self.respond(200,store.rows(q.get("dataset",""),q.get("municipality"),q.get("period"),int(q.get("limit",100)),int(q.get("offset",0))))
                if url.path in {"/v1/report", "/v1/report-package"}:
                    name = q.get("municipality")
                    if not name or name not in {m["name"] for m in store.municipalities()}:
                        raise ValueError("Укажите municipality из /v1/municipalities")
                    if "session_id" in q:
                        sessions.require(q["session_id"],name,store.metadata()["snapshot_id"])
                    # Отчёт и таблицы должны принадлежать одному снимку.
                    from mesm.access.store import build_store
                    from tempfile import TemporaryDirectory
                    with TemporaryDirectory() as temp:
                        check = build_store(root,Path(temp)/"check.sqlite")
                    if check["snapshot_id"] != store.metadata()["snapshot_id"]:
                        return self.respond(409,{"error":"Данные изменились. Перезапустите API для обновления снимка."})
                    if url.path == "/v1/report-package":
                        from mesm.access.package import report_package
                        return self.respond(200,report_package(root,store,name))
                    import sys
                    import pandas as pd
                    sys.path.insert(0,str(root/"dashboard"))
                    from final_report import build_question_report
                    records = store.rows("fiscal_panel",municipality=name,limit=1000)["rows"]
                    frame = pd.DataFrame(records)
                    latest = frame.sort_values("year").tail(1) if not frame.empty else frame
                    return self.respond(200,build_question_report(root,name,latest),"text/html; charset=utf-8")
                if url.path == "/v1/sources":
                    return self.respond(200,store.metadata()["evidence"]["sources"])
                if url.path == "/v1/trace":
                    return self.respond(200,store.metadata()["evidence"]["trace"])
                self.respond(404,{"error":"Маршрут не найден"})
            except KeyError:
                self.respond(404,{"error":"Набор данных не найден"})
            except (ValueError,TypeError):
                self.respond(400,{"error":"Некорректные параметры запроса"})
            except Exception:
                self.respond(500,{"error":"Ошибка данных; проверьте снимок и исходные таблицы"})
    return Handler


def main():
    parser = argparse.ArgumentParser(description="MESM: независимый сервер L3")
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[3])
    parser.add_argument("--port",type=int,default=8765)
    parser.add_argument("--host",default="127.0.0.1")
    parser.add_argument("--tls-cert")
    parser.add_argument("--tls-key")
    parser.add_argument("--tls-ca",help="CA для обязательных клиентских сертификатов mTLS")
    args=parser.parse_args()
    token=os.environ.get("MESM_API_TOKEN","")
    if len(token)<24: parser.error("Задайте MESM_API_TOKEN длиной не менее 24 символов")
    if not 1 <= args.port <= 65535: parser.error("Некорректный порт")
    if bool(args.tls_cert)!=bool(args.tls_key):parser.error("Укажите cert и key вместе")
    if args.tls_ca and not args.tls_cert:parser.error("mTLS требует серверный сертификат")
    if args.host not in {"127.0.0.1","localhost","::1"} and not args.tls_cert:
        parser.error("Внешний интерфейс требует TLS")
    path=args.root/"data/api/mesm.sqlite"
    meta=build_store(args.root,path)
    server=ThreadingHTTPServer((args.host,args.port),handler_factory(DataStore(path),token,args.root))
    if args.tls_cert:
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version=ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(args.tls_cert,args.tls_key)
        if args.tls_ca:
            context.load_verify_locations(cafile=args.tls_ca);context.verify_mode=ssl.CERT_REQUIRED
        server.socket=context.wrap_socket(server.socket,server_side=True)
    scheme="https" if args.tls_cert else "http"
    print(f"MESM L3 {scheme}://{args.host}:{args.port}/v1/node ; snapshot={meta['snapshot_id'][:12]}",flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=="__main__": main()
