#!/usr/bin/env python3
"""Local manual-refresh smoke test. Requires lab profile and an isolated database."""
import argparse,json,time,uuid
from urllib.request import Request,urlopen
from urllib.error import HTTPError
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',default='http://localhost:8080');args=p.parse_args()
def request(method,path,body=None):
    data=None if body is None else json.dumps(body).encode()
    try:
        with urlopen(Request(args.base+path,data=data,method=method,headers={'Content-Type':'application/json'}),timeout=15) as r:
            raw=r.read();return r.status,json.loads(raw) if raw else None
    except HTTPError as e: return e.code,None
for _ in range(120):
    try:
        status,info=request('GET','/api/cache/status')
        if status==200 and info['ready']: break
    except OSError: pass
    time.sleep(2)
else: raise SystemExit('cache not ready')
assert info['sync']=='journal','smoke requires journal mode'
assert info['strategy']!='unsafe','smoke requires a safe strategy'
assert request('GET','/api/products?page=1&size=10')[0]==200
assert request('GET','/api/products?page=0')[0]==400
name='Smoke '+uuid.uuid4().hex
status,result=request('POST','/api/products',{'name':name});assert status==201
id=result['id'];path=f'/api/products/{id}'
def refresh():
    for _ in range(20):
        status,_=request('POST','/lab/cache/refresh')
        if status==200:return
        if status!=409:raise RuntimeError('manual refresh requires lab profile: '+str(status))
        time.sleep(.2)
    raise RuntimeError('refresh busy')
try:
    refresh();status,product=request('GET',path);assert status==200 and product['name']==name and product['lastUpdatedTime'] is None
    assert request('PUT',path,{'name':name+' renamed'})[0]==204
    refresh();status,product=request('GET',path);assert status==200 and product['name']==name+' renamed' and product['lastUpdatedTime'] is not None
finally:
    assert request('DELETE',path)[0]==204
    refresh()
assert request('GET',path)[0]==404
print('PASS local HTTP create/null timestamp, refresh, rename, delete, pagination')
