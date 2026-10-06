"""Bounded expiring processing sessions; source storage survives disconnect."""
import threading,time,uuid
class Sessions:
    def __init__(self,ttl=900):
        self.ttl=ttl;self.lock=threading.Lock();self.items={}
    def open(self,municipality,snapshot_id):
        with self.lock:
            now=time.monotonic()
            self.items={k:v for k,v in self.items.items() if v['expires']>now}
            if sum(v['status']=='active' for v in self.items.values())>=256:raise ValueError('Session capacity reached')
            if len(self.items)>=4096:
                closed=next((k for k,v in self.items.items() if v['status']=='closed'),None)
                if closed:self.items.pop(closed)
            key=uuid.uuid4().hex
            self.items[key]=dict(municipality=municipality,snapshot_id=snapshot_id,status='active',expires=now+self.ttl)
            return dict(session_id=key,municipality=municipality,snapshot_id=snapshot_id,status='active',ttl_seconds=self.ttl)
    def require(self,key,municipality,snapshot_id):
        with self.lock:
            value=self.items.get(key)
            if not value or value['expires']<=time.monotonic() or value['status']!='active' or value['municipality']!=municipality or value['snapshot_id']!=snapshot_id:
                raise ValueError('Closed, expired or incompatible session')
    def close(self,key):
        with self.lock:
            if key not in self.items:raise ValueError('Unknown session')
            self.items[key]['status']='closed'
            return dict(session_id=key,status='closed',source_state='standby' if not any(v['status']=='active' and v['expires']>time.monotonic() for v in self.items.values()) else 'serving_other_sessions',source_data_preserved=True)
