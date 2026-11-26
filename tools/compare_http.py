"""Smoke contract checks against exactly one running edition; no performance ranking."""
import argparse,json,urllib.request,urllib.error,time
p=argparse.ArgumentParser();p.add_argument('--url',default='http://localhost:8080');a=p.parse_args();base=a.url.rstrip('/')
def call(path,method='GET',body=None):
 req=urllib.request.Request(base+path,method=method,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=120) as response:
  data=response.read();return json.loads(data) if data else None
for attempt in range(60):
 try: page=call('/api/products?page=2&size=10');break
 except Exception:
  if attempt==59:raise
  time.sleep(2)
assert len(page['items'])==10 and page['items'][0]['id']==11
for mode in ['atomic','lock']:
 assert call('/lab/concurrency/reserve?mode='+mode+'&stock=100&requests=200','POST')['correct']
a=call('/lab/cpu/sequential?count=10000&rounds=100');b=call('/lab/cpu/parallel?count=10000&rounds=100&workers=4');assert a['checksum']==b['checksum']
assert call('/lab/resources/stampede?single=true')['loads']==1
assert call('/lab/resources/pool?permits=5')['peak']<=5
assert len(call('/lab/io/concurrent'))==3
assert call('/lab/di/instances?mode=shared')['id']==call('/lab/di/instances?mode=shared')['id']
assert call('/lab/di/instances?mode=request')['id']!=call('/lab/di/instances?mode=request')['id']
def refresh():
 for i in range(20):
  try: return call('/lab/cache/refresh','POST')
  except urllib.error.HTTPError as e:
   if e.code!=409: raise
   time.sleep(.5)
 raise RuntimeError('refresh busy')
new=call('/api/products','POST',{'name':'Null timestamp smoke'});id=new['id'];refresh();assert call(f'/api/products/{id}')['name']=='Null timestamp smoke';call(f'/api/products/{id}','DELETE');refresh()
print('PASS: HTTP pagination, stock, checksum, single-flight, pool, I/O, DI, null insert')
