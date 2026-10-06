from __future__ import annotations
import argparse
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from mesm.access.store import DataStore, build_store


def handler_factory(store: DataStore, token: str, root: Path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # URL и токен не пишутся в журналы.
        def respond(self, code, content, mime="application/json; charset=utf-8"):
            body = content.encode("utf-8") if isinstance(content,str) else json.dumps(content,ensure_ascii=False,allow_nan=False).encode("utf-8")
            self.send_response(code); self.send_header("Content-Type",mime)
            self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-store")
            self.end_headers(); self.wfile.write(body)
        def do_GET(self):
            if not hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer "+token):
                return self.respond(401,{"error":"Требуется Bearer token"})
            url = urlsplit(self.path)
            query = parse_qs(url.query)
            if any(len(v)!=1 for v in query.values()):
                return self.respond(400,{"error":"Повторные параметры запрещены"})
            q = {k:v[0] for k,v in query.items()}
            try:
                if url.path == "/v1/health":
                    return self.respond(200,store.metadata())
                if url.path == "/v1/catalog":
                    return self.respond(200,{"datasets":store.datasets(),"snapshot":store.metadata()})
                if url.path == "/v1/municipalities":
                    return self.respond(200,store.municipalities())
                if url.path == "/v1/data":
                    if set(q)-{"dataset","municipality","period","limit","offset"}:
                        raise ValueError("Неизвестный параметр")
                    return self.respond(200,store.rows(q.get("dataset",""),q.get("municipality"),q.get("period"),int(q.get("limit",100)),int(q.get("offset",0))))
                if url.path == "/v1/report":
                    name = q.get("municipality")
                    if not name or name not in {m["name"] for m in store.municipalities()}:
                        raise ValueError("Укажите municipality из /v1/municipalities")
                    # Отчёт и таблицы должны принадлежать одному снимку.
                    from mesm.access.store import build_store
                    from tempfile import TemporaryDirectory
                    with TemporaryDirectory() as temp:
                        check = build_store(root,Path(temp)/"check.sqlite")
                    if check["snapshot_id"] != store.metadata()["snapshot_id"]:
                        return self.respond(409,{"error":"Данные изменились. Перезапустите API для обновления снимка."})
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
    parser = argparse.ArgumentParser(description="MESM: локальный API чтения для ИИ")
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[3])
    parser.add_argument("--port",type=int,default=8765)
    args=parser.parse_args()
    token=os.environ.get("MESM_API_TOKEN","")
    if len(token)<24: parser.error("Задайте MESM_API_TOKEN длиной не менее 24 символов")
    if not 1 <= args.port <= 65535: parser.error("Некорректный порт")
    path=args.root/"data/api/mesm.sqlite"
    meta=build_store(args.root,path)
    server=ThreadingHTTPServer(("127.0.0.1",args.port),handler_factory(DataStore(path),token,args.root))
    print(f"MESM API http://127.0.0.1:{args.port}/v1/catalog ; snapshot={meta['snapshot_id'][:12]}",flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=="__main__": main()
