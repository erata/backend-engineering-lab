"""Deterministic slow upstream for Lab 03/04: /product 100 ms, /inventory 200 ms, /pricing 300 ms.

The upstream must never be the bottleneck of an experiment. It is a single-threaded asyncio server (standard library
only): every connection is a coroutine, so thousands of concurrent keep-alive connections cost no OS threads.
History (see docs/VALIDATION_STATUS.md, F6/F8):
  * socketserver's default backlog of 5 refused connections under load (fixed with a large backlog);
  * two small writes + Nagle + delayed ACK added ~40 ms per call (fixed: one write per response, TCP_NODELAY);
  * ThreadingHTTPServer used one OS thread per open keep-alive connection; with virtual-thread clients (hundreds of
    concurrent connections) it grew to >3,000 Python threads, GIL contention made it slow and the backend timed out.
"""
import asyncio, json, socket

DELAYS = {'/product': .1, '/inventory': .2, '/pricing': .3}

async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    sock = writer.get_extra_info('socket')
    if sock is not None:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    try:
        while True:
            request_line = await reader.readline()
            if not request_line:
                break
            keep_alive = True
            while True:                                   # headers; GET requests carry no body
                header = await reader.readline()
                if header in (b'\r\n', b'\n', b''):
                    break
                if header.lower().startswith(b'connection:') and b'close' in header.lower():
                    keep_alive = False
            parts = request_line.decode('latin-1').split()
            path = parts[1] if len(parts) > 1 else '/'
            delay = DELAYS.get(path)
            if delay is None:
                status, body = '404 Not Found', b'{"error":"not found"}'
            else:
                await asyncio.sleep(delay)
                status, body = '200 OK', json.dumps({'source': path[1:], 'value': 1}).encode()
            writer.write(f'HTTP/1.1 {status}\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\n'
                         f'Connection: {"keep-alive" if keep_alive else "close"}\r\n\r\n'.encode() + body)
            await writer.drain()
            if not keep_alive:
                break
    except (ConnectionError, asyncio.IncompleteReadError):
        pass
    finally:
        writer.close()

async def main():
    server = await asyncio.start_server(handle, '0.0.0.0', 8090, backlog=4096)
    async with server:
        await server.serve_forever()

asyncio.run(main())
