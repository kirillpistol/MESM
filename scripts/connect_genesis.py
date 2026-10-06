"""Explicit local MESM + GENESIS worker; no changes to existing secure workers."""
import argparse,json,secrets,sys,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description='MESM -> GENESIS local connection')
 parent=ROOT.parent
 p.add_argument('--core-repo',type=Path,default=parent/'pistol-genesis-ai')
 p.add_argument('--level2-repo',type=Path,default=parent/'genesis-level-2')
 p.add_argument('--level3-repo',type=Path,default=parent/'genesis-level-3')
 p.add_argument('--municipality',default='Сургут')
 p.add_argument('--mesm-port',type=int,default=8765);p.add_argument('--core-port',type=int,default=8080)
 p.add_argument('--once',action='store_true',help='Check, save results and stop')
 a=p.parse_args()
 for repo,module in [(a.core_repo,'level1_core'),(a.level2_repo,'level2_algorithms'),(a.level3_repo,'level3_data')]:
  if not (repo/module).is_dir():p.error(f'Не найден {module}: {repo}. Используйте общую сборку или укажите путь к репозиторию.')
  sys.path.insert(0,str(repo.resolve()))
 sys.path.insert(0,str(ROOT/'src'))
 from http.server import ThreadingHTTPServer
 from mesm.access.store import build_store,DataStore
 from mesm.access.server import handler_factory
 from level1_core.runtime import Core
 from level1_core.server import Server
 from level2_algorithms.mesm_budget import REGISTRY
 from level3_data.mesm import MesmClient,DevLocalCoreClient,deliver
 build_store(ROOT,ROOT/'data/api/mesm.sqlite')
 token=secrets.token_urlsafe(32)
 source=ThreadingHTTPServer(('127.0.0.1',a.mesm_port),handler_factory(DataStore(ROOT/'data/api/mesm.sqlite'),token,ROOT))
 servers=[source];threads=[]
 try:
  core=Server(('127.0.0.1',a.core_port),Core(REGISTRY),dev=True);servers.append(core)
  for server in servers:
   t=threading.Thread(target=server.serve_forever,daemon=True);t.start();threads.append(t)
  source_url=f'http://127.0.0.1:{source.server_port}';endpoint=f'http://127.0.0.1:{core.server_port}'
  client=DevLocalCoreClient()
  client.request(endpoint,'/v1/algorithms/attach',{'api_version':'1.0','name':'mesm_budget'})
  mesm=MesmClient(source_url,token)
  results=deliver(mesm,client,endpoint,a.municipality)
  output=ROOT/'data/genesis';output.mkdir(parents=True,exist_ok=True)
  (output/'MESM_GENESIS_results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
  mesm.save_report(a.municipality,output/'MESM_report.html')
  print('Подключено MESM -> GENESIS. Записей:',len(results),flush=True)
  print('Ядро:',endpoint+'/v1/status',flush=True)
  print('MESM:',source_url+'/v1/catalog',flush=True)
  print('Отчёт:',output/'MESM_report.html',flush=True)
  if not a.once:
   print('MESM Bearer token для вашего локального клиента:',token,flush=True)
   print('Локальный режим тестирования; Ctrl+C завершает эту связку. Без автоматического повторения задач.',flush=True)
   while True:threading.Event().wait(.5)
 finally:
  # shutdown must be called only for servers that actually started serving.
  for server in servers[:len(threads)]:server.shutdown()
  for server in servers:server.server_close()
  for thread in threads:thread.join()

if __name__=='__main__':
 try:main()
 except KeyboardInterrupt:pass
 except Exception as e:
  print('Подключение не завершено:',type(e).__name__,str(e));sys.exit(1)
