"""Deterministic slow upstream for Lab 03/04: /product 100 ms, /inventory 200 ms, /pricing 300 ms.

The server must never be the bottleneck of an experiment: a large listen backlog avoids SYN drops
under hundreds of concurrent connections (socketserver's default backlog is only 5), and HTTP/1.1
keep-alive lets clients reuse connections, and TCP_NODELAY avoids Nagle/delayed-ACK stalls.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import time, json

DELAYS = {'/product': .1, '/inventory': .2, '/pricing': .3}

class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    # Headers and body are separate small writes; with Nagle on, a delayed-ACK client waits ~40 ms per response.
    disable_nagle_algorithm = True
    def do_GET(self):
        delay = DELAYS.get(self.path)
        if delay is None:
            self.send_error(404); return
        time.sleep(delay)
        data = json.dumps({'source': self.path[1:], 'value': 1}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def log_message(self, *args): pass

class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 4096

Server(('0.0.0.0', 8090), Handler).serve_forever()
