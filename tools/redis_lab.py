"""Two independent Redis clients and TTL expiry. No external Python dependencies."""
import socket,time,json,os
class Redis:
 def __init__(self): self.sock=socket.create_connection(('127.0.0.1',int(os.environ.get('REDIS_PORT','6379'))),timeout=5);self.reader=self.sock.makefile('rb')
 def call(self,*parts):
  args=[str(x).encode() for x in parts];self.sock.sendall(b'*'+str(len(args)).encode()+b'\r\n'+b''.join(b'$'+str(len(x)).encode()+b'\r\n'+x+b'\r\n' for x in args));line=self.reader.readline();kind,rest=line[:1],line[1:-2]
  if kind==b'+':return rest.decode()
  if kind==b':':return int(rest)
  if kind==b'$':
   if rest==b'-1':return None
   value=self.reader.read(int(rest));self.reader.read(2);return value.decode()
  raise RuntimeError(line)
 def close(self):self.reader.close();self.sock.close()
a,b=Redis(),Redis()
try:
 key='backendlab:ttl-demo';a.call('SET',key,json.dumps({'id':42,'name':'Product 42'}),'PX',1000);assert json.loads(b.call('GET',key))['id']==42;time.sleep(1.2);assert b.call('GET',key) is None;print('PASS: separate Redis clients share value; TTL expiry verified')
finally:a.close();b.close()
