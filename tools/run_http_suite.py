#!/usr/bin/env python3
"""HTTP benchmark suite for all eight labs and all three backends.

For every *phase* (one backend configuration) the script:
  1. stops every other lab backend, recreates the selected one under docker-compose.cpu.yml limits;
  2. waits until the catalogue is warm and records /lab/threads/info;
  3. runs each k6 experiment twice: an unreported warm-up and the measured run (constant arrival rate);
  4. samples `docker stats` of the backend container in the middle of the measured run;
  5. runs deterministic correctness probes and the CPU-scaling probe where configured.

Raw k6 summaries, probe output, environment and a Markdown report are written to reports/http-runs/<UTC>/.
k6 runs in a container on the Compose network, so no local k6 installation is needed.
"""
import argparse, collections, concurrent.futures, datetime, json, os, platform, statistics, subprocess, sys, threading, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.name
NETWORK = f'{PROJECT}_default'
K6_IMAGE = 'grafana/k6:1.3.0'
BACKENDS = {  # service, host port env, host port, compose profile; second instance for the Redis experiments (Lab 08)
    'spring':  dict(service='app',     port_env='LAB_PORT',     port=18080, profile=None,      second='app2',     port2_env='LAB_PORT2',     port2=18083),
    'jakarta': dict(service='jakarta', port_env='JAKARTA_PORT', port=18081, profile='jakarta', second='jakarta2', port2_env='JAKARTA_PORT2', port2=18084),
    'dotnet':  dict(service='dotnet',  port_env='DOTNET_PORT',  port=18082, profile='dotnet',  second='dotnet2',  port2_env='DOTNET_PORT2',  port2=18085),
}
PORT2 = {b['port']: b['port2'] for b in BACKENDS.values()}

# ---- experiment catalogue ------------------------------------------------------------------------
def k6(id, lab, path, rate, method='GET', duration='30s', vus=100, max_vus=1000, note=''):
    return dict(kind='k6', id=id, lab=lab, path=path, rate=rate, method=method, duration=duration, vus=vus, max_vus=max_vus, note=note)

CATALOG = [k6('catalog-get', '01', '/api/products/42', 2000, vus=200),
           k6('catalog-page', '01', '/api/products?page=500&size=20', 50)]
IO = [k6(f'io-{m}', '03', f'/lab/io/{m}', 50) for m in ('blocking', 'sequential-async', 'concurrent')]
SATURATION = [k6('io-blocking-400rps', '04', '/lab/io/blocking', 400, vus=400, max_vus=3000,
                 note='0.6 s blocking upstream chain; needs ~240 requests in flight')]
DI = [k6(f'di-{m}', '06', f'/lab/di/instances?mode={m}', 50) for m in ('request', 'shared')]
EVENTS = [k6(f'events-{m}', '07', f'/lab/events/price-change?mode={m}&id=7&cents=999', 200, method='POST') for m in ('direct', 'event')]
RESERVE = [k6(f'reserve-{m}', '02', f'/lab/concurrency/reserve?mode={m}&stock=1000&requests=2000', 50, method='POST') for m in ('atomic', 'lock')]
# Saturation runs last: an overloaded server keeps draining its queue after k6 stops and would contaminate later rows.
FULL = CATALOG + IO + DI + EVENTS + RESERVE + SATURATION

DBPOOL = [k6(f'dbpool-{p}-{r}rps', '08', f'/lab/resources/db?pool={p}&ms=30', r, vus=100, max_vus=1500,
             note=f'real pool of {p}, 30 ms per connection: capacity ~{p * 1000 // 30} req/s') for p in (5, 20) for r in (100, 300)]
EVENTS_INLINE = [k6('events-event-inline', '07', '/lab/events/price-change?mode=event-inline&id=7&cents=999', 200, method='POST', duration='20s',
                    note='Spring: pool deadlock; Jakarta: compare JTA behaviour')]
JAKARTA_VT = [k6(f'io-blocking-async-{x}-400rps', '04', f'/lab/io/blocking-async?executor={x}', 400, vus=400, max_vus=3000,
                 note='blocking chain on a managed executor, JAX-RS async response') for x in ('virtual', 'default')]
REDIS_GET = [k6('redis-get', '08', '/lab/redis/product/42?mode=distributed', 2000, vus=200, note='cache hit served from Redis (network hop)')]

def phase(id, backend, env=None, experiments=(), probes=(), cpus=4, title='', repeat=1, extra_ports=()):
    return dict(id=id, backend=backend, env=env or {}, experiments=list(experiments), probes=list(probes), cpus=cpus, title=title or id,
                repeat=repeat, extra_ports=list(extra_ports))

J25P = {'JAVA_VERSION': '25', 'LAB_VIRTUAL_THREADS': 'false', 'LAB_CACHE_STRATEGY': 'snapshot'}
# v2: repeatability (5 runs per configuration) and the experiments added after the first report.
V2_PHASES = [
    phase('v2-rep5-spring-j25-platform', 'spring', J25P, CATALOG[:1] + IO[::2] + EVENTS + SATURATION, repeat=5, title='Spring / Java 25 / platform, 5 repetitions'),
    phase('v2-rep5-spring-j25-virtual', 'spring', {**J25P, 'LAB_VIRTUAL_THREADS': 'true'}, CATALOG[:1] + SATURATION, repeat=5, title='Spring / Java 25 / virtual, 5 repetitions'),
    phase('v2-rep5-spring-j17-platform', 'spring', {**J25P, 'JAVA_VERSION': '17'}, CATALOG[:1] + SATURATION, repeat=5, title='Spring / Java 17 / platform, 5 repetitions'),
    phase('v2-rep5-jakarta', 'jakarta', {'LAB_CACHE_STRATEGY': 'snapshot'}, CATALOG[:1] + IO[2:], repeat=5, title='Jakarta EE, 5 repetitions'),
    phase('v2-rep5-dotnet10', 'dotnet', {'DOTNET_VERSION': '10.0', 'LAB_CACHE_STRATEGY': 'snapshot'}, CATALOG[:1] + IO[1:], repeat=5, title='.NET 10, 5 repetitions'),
    phase('v2-new-spring', 'spring', J25P, DBPOOL, ['di2', 'events'], title='Spring: real DB pool, DI captive/mutable, transactional events'),
    phase('v2-new-jakarta', 'jakarta', {}, DBPOOL + EVENTS + EVENTS_INLINE + JAKARTA_VT, ['di2', 'events'], title='Jakarta: real DB pool, JTA events, managed virtual threads, DI'),
    phase('v2-new-dotnet10', 'dotnet', {'DOTNET_VERSION': '10.0'}, DBPOOL + EVENTS, ['di2', 'events'], title='.NET 10: real DB pool, outbox events, DI'),
    phase('v2-pinning-j21', 'spring', {**J25P, 'JAVA_VERSION': '21'}, [], ['pinning'], title='Spring / Java 21: virtual-thread pinning'),
    phase('v2-pinning-j25', 'spring', J25P, [], ['pinning'], title='Spring / Java 25: virtual-thread pinning'),
    phase('v2-redis-spring', 'spring', J25P, CATALOG[:1] + REDIS_GET, ['redis'], extra_ports=[18083], title='Spring x2 + Redis: shared cache'),
    # v4: every experiment that calls the mock upstream, rerun after the mock became a thread-free asyncio server
    # (the threaded mock was the bottleneck for high-concurrency clients; see docs/VALIDATION_STATUS.md, F8).
    phase('v4-rep5-spring-j25-platform', 'spring', J25P, IO + SATURATION, repeat=5, title='Spring / Java 25 / platform, I/O, 5 repetitions'),
    phase('v4-rep5-spring-j25-virtual', 'spring', {**J25P, 'LAB_VIRTUAL_THREADS': 'true'}, IO[:1] + SATURATION, repeat=5, title='Spring / Java 25 / virtual, I/O, 5 repetitions'),
    phase('v4-rep5-spring-j17-platform', 'spring', {**J25P, 'JAVA_VERSION': '17'}, SATURATION, repeat=5, title='Spring / Java 17 / platform, I/O, 5 repetitions'),
    phase('v4-rep5-jakarta', 'jakarta', {}, IO, repeat=5, title='Jakarta EE, I/O, 5 repetitions'),
    phase('v4-rep3-jakarta-saturation', 'jakarta', {}, SATURATION + JAKARTA_VT, repeat=3, title='Jakarta EE, 400 req/s blocking: worker vs managed executors, 3 repetitions'),
    phase('v4-rep5-dotnet10', 'dotnet', {'DOTNET_VERSION': '10.0'}, IO, repeat=5, title='.NET 10, I/O, 5 repetitions'),
    phase('v4-rep3-dotnet-saturation', 'dotnet', {'DOTNET_VERSION': '10.0'}, SATURATION, repeat=3, title='.NET 10, 400 req/s sync-over-async, 3 repetitions'),
    phase('v4-dotnet11-saturation', 'dotnet', {'DOTNET_VERSION': '11.0'}, IO[1:] + SATURATION, repeat=3, title='.NET 11, I/O, 3 repetitions'),
    # v3: functional probes added in the final review (no load tests).
    phase('v3-spring', 'spring', J25P, [], ['ownership', 'failure', 'staleness', 'di2'], title='Spring: ownership, handler failure, cache staleness'),
    phase('v3-jakarta', 'jakarta', {}, [], ['ownership', 'failure', 'staleness'], title='Jakarta: ownership, request context in workers, handler failure, staleness'),
    phase('v3-dotnet10', 'dotnet', {'DOTNET_VERSION': '10.0'}, [], ['ownership', 'failure', 'staleness'], title='.NET 10: ownership, outbox retry, staleness'),
    phase('v3-redis-spring', 'spring', J25P, [], ['redis2'], extra_ports=[18083], title='Spring x2 + Redis: consistency, invalidation, failure'),
    # v5: the same Redis experiments on all three editions, to compare the clients (Lettuce, Jedis, StackExchange.Redis):
    # hit throughput, stampede coordination, consistency, and behaviour while Redis is stopped or frozen.
    phase('v5-redis-spring', 'spring', J25P, REDIS_GET, ['redis', 'redis2'], repeat=3, extra_ports=[18083], title='Spring x2 + Redis (Lettuce)'),
    phase('v5-redis-jakarta', 'jakarta', {}, REDIS_GET, ['redis', 'redis2'], repeat=3, extra_ports=[18084], title='Jakarta x2 + Redis (Jedis, pool 8)'),
    phase('v5-redis-jakarta-pool64', 'jakarta', {'REDIS_POOL_MAX': '64'}, REDIS_GET, ['redis'], repeat=3, extra_ports=[18084], title='Jakarta x2 + Redis (Jedis, pool 64)'),
    phase('v5-redis-dotnet10', 'dotnet', {'DOTNET_VERSION': '10.0'}, REDIS_GET, ['redis', 'redis2'], repeat=3, extra_ports=[18085], title='.NET 10 x2 + Redis (StackExchange.Redis)'),
    # v5b: WildFly is still warming up during the first 2,000 req/s run (also without Redis), so Jedis gets 5 repetitions;
    # and a check of the slow Jedis recovery after `docker stop` with the JVM negative DNS cache disabled (default 10 s).
    phase('v5b-redis-jakarta-rep5', 'jakarta', {}, REDIS_GET, [], repeat=5, extra_ports=[18084], title='Jakarta x2 + Redis (Jedis, pool 8), 5 repetitions'),
    phase('v5b-redis-jakarta-pool64-rep5', 'jakarta', {'REDIS_POOL_MAX': '64'}, REDIS_GET, [], repeat=5, extra_ports=[18084], title='Jakarta x2 + Redis (Jedis, pool 64), 5 repetitions'),
    phase('v5b-redis-jakarta-dns0', 'jakarta', {'LAB_JAVA_TOOL_OPTIONS': '-Dsun.net.inetaddr.negative.ttl=0'}, [], ['redis2'], extra_ports=[18084],
          title='Jakarta x2 + Redis (Jedis), JVM negative DNS cache off'),
    # v6: outage behaviour, 5 repetitions x 3 outage kinds (stop / pause / process kill), plus one setting per client
    # that the v5 explanations depend on: Lettuce disconnected behaviour, Jedis DNS cache, StackExchange.Redis heartbeat.
    phase('v6-outage-spring-queue', 'spring', J25P, [], ['outage'], extra_ports=[18083], title='Lettuce, default (queue while disconnected)'),
    phase('v6-outage-spring-reject', 'spring', {**J25P, 'LAB_REDIS_DISCONNECTED': 'reject'}, [], ['outage'], extra_ports=[18083], title='Lettuce, REJECT_COMMANDS'),
    phase('v6-outage-jakarta', 'jakarta', {}, [], ['outage'], extra_ports=[18084], title='Jedis, default JVM DNS cache'),
    # Invalid A/B kept for the record: the JDK's java.security sets networkaddress.cache.negative.ttl=10, so this
    # system property is ignored (same for v5b-redis-jakarta-dns0). v6b sets the security property itself.
    phase('v6-outage-jakarta-dns0', 'jakarta', {'LAB_JAVA_TOOL_OPTIONS': '-Dsun.net.inetaddr.negative.ttl=0'}, [], ['outage'], extra_ports=[18084],
          title='Jedis, sun.net.inetaddr.negative.ttl=0 (ignored by the JDK, see v6b)'),
    *[phase(f'v6-outage-dotnet-hb{hb}', 'dotnet', {'DOTNET_VERSION': '10.0', 'REDIS_HEARTBEAT_MS': str(hb)}, [], ['outage'], extra_ports=[18085],
            title=f'StackExchange.Redis, heartbeat {hb} ms') for hb in (1000, 500, 100)],
    # v6b: the JVM DNS cache A/B done correctly, through the security property (infrastructure/jvm/*.security).
    phase('v6b-outage-jakarta-neg0', 'jakarta', {'LAB_JAVA_TOOL_OPTIONS': '-Djava.security.properties=/lab-jvm/negative-ttl-0.security'}, [], ['outage'],
          extra_ports=[18084], title='Jedis, networkaddress.cache.negative.ttl=0'),
    phase('v6b-outage-jakarta-nocache', 'jakarta', {'LAB_JAVA_TOOL_OPTIONS': '-Djava.security.properties=/lab-jvm/no-dns-cache.security'}, [], ['outage'],
          extra_ports=[18084], title='Jedis, no JVM DNS cache (positive and negative TTL 0)'),
    # v7: regression checks after the v1.1.0 code review (atomic lock release, JSON serialization, single-flight under
    # an outage). Functional only; no load tests, so earlier benchmark results are unaffected.
    phase('v7-redis-regression-spring', 'spring', J25P, [], ['redis_regression'], extra_ports=[18083], title='Spring: Redis regression checks'),
    phase('v7-redis-regression-jakarta', 'jakarta', {}, [], ['redis_regression'], extra_ports=[18084], title='Jakarta: Redis regression checks'),
    phase('v7-redis-regression-dotnet10', 'dotnet', {'DOTNET_VERSION': '10.0'}, [], ['redis_regression'], extra_ports=[18085], title='.NET 10: Redis regression checks'),
]

PHASES = [
    phase('spring-j25-platform-snapshot', 'spring', {'JAVA_VERSION': '25', 'LAB_VIRTUAL_THREADS': 'false', 'LAB_CACHE_STRATEGY': 'snapshot'}, FULL, ['correctness', 'cpu'],
          title='Spring Boot / Java 25 / platform threads / snapshot'),
    # Negative example in its own phase: the inline AFTER_COMMIT + REQUIRES_NEW listener exhausts the Hikari pool.
    phase('spring-j25-events-inline', 'spring', {'JAVA_VERSION': '25', 'LAB_VIRTUAL_THREADS': 'false'},
          [k6('events-event-inline', '07', '/lab/events/price-change?mode=event-inline&id=7&cents=999', 200, method='POST', duration='20s',
              note='negative example: connection-pool deadlock')], title='Spring Boot / inline after-commit listener (negative example)'),
    phase('spring-j25-virtual-snapshot', 'spring', {'JAVA_VERSION': '25', 'LAB_VIRTUAL_THREADS': 'true', 'LAB_CACHE_STRATEGY': 'snapshot'}, CATALOG[:1] + IO[:1] + SATURATION,
          title='Spring Boot / Java 25 / virtual threads / snapshot'),
    phase('spring-j17-platform-snapshot', 'spring', {'JAVA_VERSION': '17', 'LAB_VIRTUAL_THREADS': 'false', 'LAB_CACHE_STRATEGY': 'snapshot'}, CATALOG[:1] + SATURATION, ['cpu'],
          title='Spring Boot / Java 17 / platform threads / snapshot'),
    *[phase(f'spring-j25-platform-{s}', 'spring', {'JAVA_VERSION': '25', 'LAB_VIRTUAL_THREADS': 'false', 'LAB_CACHE_STRATEGY': s}, CATALOG,
            title=f'Spring Boot / Java 25 / platform threads / {s}') for s in ('synchronized', 'concurrent', 'caffeine')],
    phase('jakarta-j25-snapshot', 'jakarta', {'LAB_CACHE_STRATEGY': 'snapshot'}, FULL, ['correctness', 'cpu'], title='Jakarta EE (WildFly 42) / Java 25 / snapshot'),
    phase('dotnet10-snapshot', 'dotnet', {'DOTNET_VERSION': '10.0', 'LAB_CACHE_STRATEGY': 'snapshot'}, FULL, ['correctness', 'cpu'], title='ASP.NET Core / .NET 10 / snapshot'),
    phase('dotnet11-snapshot', 'dotnet', {'DOTNET_VERSION': '11.0', 'LAB_CACHE_STRATEGY': 'snapshot'}, CATALOG[:1] + SATURATION, ['cpu'], title='ASP.NET Core / .NET 11 / snapshot'),
    *[phase(f'cpu{c}-{b}', b, env, [], ['cpu'], cpus=c, title=f'{b} CPU quota {c}')
      for c in (1, 2, 8)
      for b, env in (('spring', {'JAVA_VERSION': '25', 'LAB_VIRTUAL_THREADS': 'false'}), ('jakarta', {}), ('dotnet', {'DOTNET_VERSION': '10.0'}))],
    *V2_PHASES,
]

# ---- helpers ---------------------------------------------------------------------------------------
def sh(args, env=None, check=True, timeout=1800):
    p = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    if check and p.returncode != 0:
        raise RuntimeError(f'{" ".join(args)} failed ({p.returncode}):\n{p.stdout[-3000:]}\n{p.stderr[-3000:]}')
    return p

def compose_env(ph):
    env = dict(os.environ)
    env.update({'SPRING_PROFILES_ACTIVE': 'lab', 'LAB_CPUS': str(ph['cpus']), 'LAB_MEMORY': '2g', 'LAB_CACHE_STRATEGY': 'snapshot',
                'REDIS_PORT': '16379', 'REDIS_POOL_MAX': '8'})
    for b in BACKENDS.values():
        env[b['port_env']] = str(b['port']); env[b['port2_env']] = str(b['port2'])
    env.update(ph['env'])
    return env

def compose(env, *args, profiles=('jakarta', 'dotnet'), timeout=1800):
    # The Redis overlay is always included so that app2/redis can be stopped; they only start when named explicitly.
    base = ['docker', 'compose', '-f', 'docker-compose.yml', '-f', 'docker-compose.cpu.yml', '-f', 'docker-compose.redis.yml']
    for p in profiles:
        base += ['--profile', p]
    return sh(base + list(args), env=env, timeout=timeout)

def call(url, method='GET', timeout=120):
    req = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
        return json.loads(body) if body else None

def wait_ready(port, limit=300):
    end = time.time() + limit
    while time.time() < end:
        try:
            call(f'http://127.0.0.1:{port}/api/products/1', timeout=5); return
        except Exception:
            time.sleep(2)
    raise RuntimeError(f'backend on {port} not ready after {limit}s')

def start(ph):
    env = compose_env(ph); b = BACKENDS[ph['backend']]
    redis = bool(ph['extra_ports'])
    others = [s for k, x in BACKENDS.items() if k != ph['backend'] for s in (x['service'], x['second'])] + ([] if redis else [b['second'], 'redis'])
    compose(env, 'stop', *others)
    compose(env, 'up', '-d', '--build', '--force-recreate', b['service'], 'mock-api', *(['redis', b['second']] if redis else []), timeout=3600)
    wait_ready(b['port'])
    for p in ph['extra_ports']:
        wait_ready(p)
    info = call(f'http://127.0.0.1:{b["port"]}/lab/threads/info')
    img = sh(['docker', 'inspect', '--format', '{{.Config.Image}} {{.Image}}', container(ph)], check=False).stdout.strip()
    db = sh(['docker', 'inspect', '--format', '{{.Config.Image}}', f'{PROJECT}-{ {"spring": "mysql", "jakarta": "jakarta-db", "dotnet": "dotnet-db"}[ph["backend"]] }-1'], check=False).stdout.strip()
    info = {**(info or {}), 'image': img, 'db_image': db}
    return env, info

def settle(port, limit=300, fast_ms=200, needed=3):
    """Wait until the backend has drained queued work: `needed` consecutive fast catalogue reads."""
    end, ok = time.time() + limit, 0
    while time.time() < end and ok < needed:
        t = time.perf_counter()
        try:
            call(f'http://127.0.0.1:{port}/api/products/1', timeout=15)
            ok = ok + 1 if (time.perf_counter() - t) * 1000 < fast_ms else 0
        except Exception:
            ok = 0
        time.sleep(1)
    return ok >= needed

def container(ph):
    return f'{PROJECT}-{BACKENDS[ph["backend"]]["service"]}-1'

def docker_stats(name):
    p = sh(['docker', 'stats', '--no-stream', '--format', '{{json .}}', name], check=False, timeout=60)
    try:
        s = json.loads(p.stdout.strip().splitlines()[-1]); return {'cpu': s.get('CPUPerc'), 'mem': s.get('MemUsage')}
    except Exception:
        return {}

def run_k6(ph, exp, out_dir, measured=True, rep=None):
    b = BACKENDS[ph['backend']]
    name = f'{ph["id"]}__{exp["id"]}' + (f'__r{rep}' if rep else '')
    # High-rate runs need a longer warm-up: WildFly's larger code path is still being JIT-compiled after 10 s.
    duration = exp['duration'] if measured else ('30s' if exp['rate'] >= 1000 else '10s')
    args = ['docker', 'run', '--rm', '--network', NETWORK, '-v', f'{ROOT / "benchmarks" / "k6"}:/scripts:ro', '-v', f'{out_dir}:/out',
            '-e', f'BASE_URL=http://{b["service"]}:8080', '-e', f'LAB_PATH={exp["path"]}', '-e', f'METHOD={exp["method"]}',
            '-e', f'RATE={exp["rate"]}', '-e', f'DURATION={duration}', '-e', f'VUS={exp["vus"]}', '-e', f'MAX_VUS={exp["max_vus"]}',
            K6_IMAGE, 'run', '--quiet', '--summary-export', f'/out/{name}.json' if measured else '/out/warmup.json', '/scripts/workload.js']
    sample = {}
    if measured:
        secs = int(exp['duration'].rstrip('s'))
        t = threading.Timer(secs / 2, lambda: sample.update(docker_stats(container(ph)))); t.start()
    p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=1800)
    if not measured:
        (out_dir / 'warmup.json').unlink(missing_ok=True); return None
    t.join()
    path = out_dir / f'{name}.json'
    if not path.exists():
        return {'error': f'k6 exit {p.returncode}: {p.stderr[-800:]}'}
    m = json.loads(path.read_text())['metrics']
    d = m.get('http_req_duration', {}); reqs = m.get('http_reqs', {}); failed = m.get('http_req_failed', {}); drop = m.get('dropped_iterations', {})
    return {'k6_exit': p.returncode, 'p50': d.get('med'), 'p95': d.get('p(95)'), 'p99': d.get('p(99)'), 'max': d.get('max'), 'avg': d.get('avg'),
            'rps': reqs.get('rate'), 'requests': reqs.get('count'), 'failed_rate': failed.get('value'), 'dropped': drop.get('count', 0),
            'vus_max': m.get('vus_max', {}).get('value'), 'container': sample}

def parallel(urls, method='GET', workers=100):
    """Fire all URLs at once (barrier) and return (json results, elapsed ms per call)."""
    barrier = threading.Barrier(min(len(urls), workers))
    def one(u):
        try: barrier.wait(timeout=30)
        except threading.BrokenBarrierError: pass
        t = time.perf_counter()
        try: r = call(u, method, timeout=60)
        except Exception as e: r = {'error': str(e)}
        return r, (time.perf_counter() - t) * 1000
    with concurrent.futures.ThreadPoolExecutor(min(len(urls), workers)) as ex:
        out = list(ex.map(one, urls))
    return [o[0] for o in out], [o[1] for o in out]

def probe_di2(port):
    """Lab 06: captive dependency identity and shared mutable state under 200 concurrent requests."""
    base = f'http://127.0.0.1:{port}'; res = {}
    fresh_mode = 'scoped' if port == BACKENDS['dotnet']['port'] else 'provider'
    for mode in ('captured', fresh_mode):
        ids = [call(f'{base}/lab/di/captive?mode={mode}')['id'] for _ in range(5)]
        res[f'captive_{mode}'] = {'calls': 5, 'distinct_ids': len(set(map(str, ids)))}
    for mode in ('singleton', 'request'):
        bad = total = 0
        for rnd in range(3):
            urls = [f'{base}/lab/di/mutable?mode={mode}&user=u{rnd}-{i}&delayMs=5' for i in range(200)]
            rs, _ = parallel(urls)
            ok = [r for r in rs if 'correct' in r]
            bad += sum(not r['correct'] for r in ok); total += len(ok)
        res[f'mutable_{mode}'] = {'requests': total, 'wrong_user_returned': bad}
    return res

def probe_events(port):
    """Lab 07: 100 concurrent event + 100 direct changes and 20 rollbacks on a fresh product id; audit must be exactly 200."""
    base = f'http://127.0.0.1:{port}'; pid = int(time.time()) % 1_000_000 + 100_000
    before = call(f'{base}/lab/events/state?id={pid}')
    urls = [f'{base}/lab/events/price-change?id={pid}&cents=500&mode={"event" if i % 2 else "direct"}' for i in range(200)]
    rs, ms = parallel(urls, 'POST', workers=50)
    errors = sum('error' in r for r in rs)
    rb, _ = parallel([f'{base}/lab/events/price-change?id={pid}&cents=777&mode=event&rollback=true' for _ in range(20)], 'POST', workers=20)
    end = time.time() + 15; state = None
    while time.time() < end:
        state = call(f'{base}/lab/events/state?id={pid}')
        if state['auditCount'] - before['auditCount'] >= 200 - errors: break
        time.sleep(0.5)
    time.sleep(1); state = call(f'{base}/lab/events/state?id={pid}')
    return {'product': pid, 'committed_changes': 200 - errors, 'request_errors': errors, 'audit_delta': state['auditCount'] - before['auditCount'],
            'rollbacks_sent': 20, 'rollback_http_errors': sum('error' in r for r in rb), 'final_cents': state['cents'],
            'rolled_back_price_visible': state['cents'] == 777, 'p50_ms': statistics.median(ms)}

def probe_pinning(port):
    base = f'http://127.0.0.1:{port}'; res = {}
    for mode in ('synchronized', 'reentrant'):
        url = f'{base}/lab/threads/pinning?mode={mode}&tasks=100&sleepMs=50'
        for _ in range(3): call(url)
        runs = [call(url) for _ in range(10)]
        res[mode] = {'median_ms': statistics.median(r['elapsedMs'] for r in runs), 'min_ms': min(r['elapsedMs'] for r in runs),
                     'max_ms': max(r['elapsedMs'] for r in runs), 'carriers': runs[0]['carriers'], 'runtime': runs[0]['runtime']}
    return res

def probe_redis(port):
    """Lab 08: 50 concurrent misses on each of two instances (100 total) per mode; count loads in Redis."""
    port2 = PORT2[port]
    # Fallbacks to MySQL since startup, i.e. during the k6 runs of this phase (Redis errors or, for Jedis, pool waits > 500 ms).
    res = {'client_stats_after_k6': call(f'http://127.0.0.1:{port}/lab/redis/loads?id=1')}
    for mode in ('none', 'local', 'distributed'):
        loads, p50 = [], []
        for _ in range(5):
            call(f'http://127.0.0.1:{port}/lab/redis/reset?id=42', 'POST')
            urls = [f'http://127.0.0.1:{p}/lab/redis/product/42?mode={mode}' for p in (port, port2) for _ in range(50)]
            rs, ms = parallel(urls)
            loads.append(call(f'http://127.0.0.1:{port}/lab/redis/loads?id=42')['loads']); p50.append(statistics.median(ms))
        res[mode] = {'requests_per_round': 100, 'instances': 2, 'loads_min': min(loads), 'loads_max': max(loads), 'loads': loads,
                     'client_p50_ms_median': statistics.median(p50)}
    return res

def probe_ownership(port):
    """Lab 06: who disposes container-created objects? 100 objects per mode; counts created vs closed/disposed."""
    base = f'http://127.0.0.1:{port}'
    modes = {BACKENDS['spring']['port']: ('container', 'caller'), BACKENDS['jakarta']['port']: ('leak', 'destroy'), BACKENDS['dotnet']['port']: ('root', 'scope')}[port]
    res = {m: call(f'{base}/lab/di/ownership?mode={m}&n=100') for m in modes}
    if port == BACKENDS['jakarta']['port']:
        res['background_plain'] = call(f'{base}/lab/di/background?mode=plain')
        res['background_activated'] = call(f'{base}/lab/di/background?mode=activated')
    return res

def probe_failure(port):
    """Lab 07: the audit side effect fails (failAudit=true) for 10 direct and 10 event changes on fresh products."""
    base = f'http://127.0.0.1:{port}'; out = {}
    for mode in ('direct', 'event'):
        pid = int(time.time() * 1000) % 1_000_000 + 3_000_000
        codes = []
        for i in range(10):
            try: call(f'{base}/lab/events/price-change?id={pid}&cents={100 + i}&mode={mode}&failAudit=true', 'POST'); codes.append(200)
            except urllib.error.HTTPError as e: codes.append(e.code)
        time.sleep(5)       # > outbox retry interval; after-commit listeners are long done
        st = call(f'{base}/lab/events/state?id={pid}')
        out[mode] = {'http_status': sorted(set(codes)), 'price_committed': st['cents'] != -1, 'final_cents': st['cents'],
                     'audit_rows': st['auditCount'], 'outbox_pending': st.get('outboxPending')}
    return out

def probe_staleness(port, samples=5):
    """Lab 01: time from a committed rename until the cache serves it (journal refresh every 10 s, no manual refresh)."""
    base = f'http://127.0.0.1:{port}'; out = []
    for i in range(samples):
        name = f'Staleness {int(time.time() * 1000)}'
        body = json.dumps({'name': name}).encode()
        req = urllib.request.Request(f'{base}/api/products/77', data=body, method='PUT', headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=30).read(); t0 = time.perf_counter()
        while time.perf_counter() - t0 < 30:
            if call(f'{base}/api/products/77')['name'] == name: break
            time.sleep(0.05)
        out.append(round((time.perf_counter() - t0) * 1000))
        time.sleep(1.7 * (i + 1))   # de-correlate the samples from the 10 s refresh period
    return {'samples_ms': out, 'median_ms': statistics.median(out), 'max_ms': max(out), 'refresh_interval_s': 10}

def outage(a, kind):
    """Redis stopped (container gone: connection refused / name not resolvable) or paused (TCP still accepted, no
    replies): latency of the fallback path for 10 sequential and 50 concurrent requests, then the time until the
    client serves from Redis again."""
    redis_c = f'{PROJECT}-redis-1'; url = f'{a}/lab/redis/product/42?mode=distributed'
    call(f'{a}/lab/redis/reset?id=42', 'POST'); call(url)             # warm connection(s), value cached
    sh(['docker', kind, redis_c], check=False, timeout=120)
    try:
        seq = []
        for _ in range(10):
            t = time.perf_counter(); r = call(url); seq.append(((time.perf_counter() - t) * 1000, r['source'], r.get('error')))
        rs, ms = parallel([url] * 50)
        catalog_ok = call(f'{a}/api/products/42')['id'] == 42
    finally:
        sh(['docker', {'stop': 'start', 'pause': 'unpause'}[kind], redis_c], check=False, timeout=120)
    t0 = time.perf_counter(); polls = 0; recovered = None
    while time.perf_counter() - t0 < 60:
        polls += 1
        try:
            if call(url, timeout=10)['source'] != 'db-fallback':
                recovered = round((time.perf_counter() - t0) * 1000); break
        except Exception:
            pass
        time.sleep(0.05)
    seq_ms = [x[0] for x in seq]
    return {'sequential_10': {'first_ms': round(seq_ms[0], 1), 'median_ms': round(statistics.median(seq_ms), 1), 'max_ms': round(max(seq_ms), 1),
                              'sources': sorted({x[1] for x in seq}), 'errors': sorted({str(x[2]) for x in seq})},
            'concurrent_50': {'p50_ms': round(statistics.median(ms), 1), 'max_ms': round(max(ms), 1),
                              'sources': sorted({str(r.get('source', 'http-error')) for r in rs}), 'errors': sorted({str(r.get('error')) for r in rs})},
            'catalog_api_still_ok': catalog_ok, 'recovery_ms_after_restore': recovered, 'recovery_polls': polls}

def probe_redis2(port):
    """Lab 08: cross-instance consistency, explicit invalidation and Redis failure behaviour."""
    port2 = PORT2[port]
    a, b = f'http://127.0.0.1:{port}', f'http://127.0.0.1:{port2}'; res = {}
    original = call(f'{a}/api/products/42')['name']
    def rename(n):
        req = urllib.request.Request(f'{a}/api/products/42', data=json.dumps({'name': n}).encode(), method='PUT', headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=30).read()
    call(f'{a}/lab/redis/reset?id=42', 'POST'); call(f'{a}/lab/redis/product/42')          # A loads and caches the old name
    new = f'Product 42 v{int(time.time())}'; rename(new)                                   # DB write, no cache invalidation
    stale = json.loads(call(f'{b}/lab/redis/product/42')['value'])['name']
    call(f'{a}/lab/redis/invalidate?id=42', 'POST')
    fresh = json.loads(call(f'{b}/lab/redis/product/42')['value'])['name']
    res['consistency'] = {'db_value': new, 'instance_b_before_invalidate': stale, 'stale_read': stale != new,
                          'instance_b_after_invalidate': fresh, 'fresh_after_invalidate': fresh == new, 'ttl_s': 30}
    rename(original); call(f'{a}/lab/redis/reset?id=42', 'POST')
    res['redis_stopped'] = outage(a, 'stop')
    res['redis_paused'] = outage(a, 'pause')
    res['client'] = call(f'{a}/lab/redis/loads?id=42').get('client')
    return res

OUTAGE_KINDS = {
    # kind: (break Redis, restore Redis). DNS = whether the name `redis` still resolves during the outage.
    'stop':  (['docker', 'stop', '{c}'], ['docker', 'start', '{c}']),                                  # container gone, DNS fails
    'pause': (['docker', 'pause', '{c}'], ['docker', 'unpause', '{c}']),                               # DNS ok, TCP open, no replies
    'kill':  (['docker', 'exec', '{c}', 'redis-cli', 'shutdown', 'nosave'], ['docker', 'exec', '-d', '{c}', 'redis-server']),  # DNS ok, connection refused
}

def pct(xs, p):
    """Nearest-rank percentile."""
    xs = sorted(xs); return xs[min(len(xs) - 1, max(0, -(-p * len(xs) // 100) - 1))]

def dist(xs):
    return {'n': len(xs), 'median_ms': round(statistics.median(xs), 1), 'p95_ms': round(pct(xs, 95), 1), 'p99_ms': round(pct(xs, 99), 1),
            'min_ms': round(min(xs), 1), 'max_ms': round(max(xs), 1)}

def probe_outage(port, reps=5):
    """Lab 08: each outage kind `reps` times. Per repetition: 10 sequential + 50 concurrent requests while Redis is
    down, then poll every 50 ms after the restore command has returned until a response is served from Redis
    (recovery time). DB fallback queries = growth of the instance's fallback counter (each fallback is one MySQL
    query; the recovery polls are included). Connected clients are read from Redis after recovery."""
    a = f'http://127.0.0.1:{port}'; url = f'{a}/lab/redis/product/42?mode=distributed'; c = f'{PROJECT}-redis-1'
    def run(cmd): sh([x.format(c=c) for x in cmd], check=False, timeout=120)
    def one(u):
        t = time.perf_counter()
        try: r = call(u, timeout=30)
        except Exception as e: r = {'error_http': type(e).__name__}
        return r, (time.perf_counter() - t) * 1000
    out = {'client': call(f'{a}/lab/redis/loads?id=42')}
    for kind, (brk, restore) in OUTAGE_KINDS.items():
        runs = []
        for _ in range(reps):
            call(f'{a}/lab/redis/reset?id=42', 'POST'); call(url); time.sleep(0.5)
            fb0 = call(f'{a}/lab/redis/loads?id=42')['fallbacks']
            run(brk)
            try:
                seq = [one(url) for _ in range(10)]
                rs, ms = parallel([url] * 50)
            finally:
                run(restore)
            t0 = time.perf_counter(); polls = 0; recovered = None
            while time.perf_counter() - t0 < 60:
                polls += 1; r, _ = one(url)
                if r.get('source') in ('redis', 'loaded-or-waited'):
                    recovered = (time.perf_counter() - t0) * 1000; break
                time.sleep(0.05)
            fb1 = call(f'{a}/lab/redis/loads?id=42')['fallbacks']
            info = sh(['docker', 'exec', c, 'redis-cli', 'info', 'clients'], check=False).stdout
            clients = next((int(l.split(':')[1]) for l in info.splitlines() if l.startswith('connected_clients:')), None)
            all_r = [x[0] for x in seq] + rs
            runs.append({'seq_ms': [x[1] for x in seq], 'conc_ms': ms, 'recovery_ms': recovered, 'polls': polls,
                         'http_errors': sum(1 for r in all_r if 'error_http' in r or 'error' in r and 'source' not in r),
                         'db_fallback_responses': sum(1 for r in all_r if r.get('source') == 'db-fallback'),
                         'db_fallback_queries': fb1 - fb0, 'exceptions': sorted({str(r.get('error')) for r in all_r if r.get('error')}),
                         'connected_clients_after': clients})
            time.sleep(2)
        rec = [r['recovery_ms'] for r in runs if r['recovery_ms'] is not None]
        out[kind] = {'repetitions': reps, 'requests_per_rep': 60,
                     'sequential': dist([x for r in runs for x in r['seq_ms']]), 'first_request_ms': [round(r['seq_ms'][0], 1) for r in runs],
                     'concurrent_50': dist([x for r in runs for x in r['conc_ms']]),
                     'recovery_ms': {'values': [round(x) for x in rec], 'median': round(statistics.median(rec)) if rec else None,
                                     'min': round(min(rec)) if rec else None, 'max': round(max(rec)) if rec else None, 'not_recovered': reps - len(rec)},
                     'http_error_rate': sum(r['http_errors'] for r in runs) / (60 * reps),
                     'db_fallback_responses': sum(r['db_fallback_responses'] for r in runs),
                     'db_fallback_queries_incl_polls': sum(r['db_fallback_queries'] for r in runs),
                     'exceptions': sorted({e for r in runs for e in r['exceptions']}),
                     'connected_clients_after': [r['connected_clients_after'] for r in runs]}
    return out

def probe_redis_regression(port):
    """Lab 08 regression checks after the v1.1.0 review:
    1. lock release is atomic: a stale owner (expired lease) must not delete the next owner's lock;
    2. product names with quotes, backslashes, control characters and non-ASCII survive the Redis and the DB-fallback
       path as valid JSON;
    3. single-flight under an outage: 50 concurrent `local` misses, Redis is frozen while the leader loads; every
       follower must fall back to MySQL (no HTTP 500 from a wrapped leader exception);
    4. `distributed` still loads once per round across both instances."""
    a = f'http://127.0.0.1:{port}'; b = f'http://127.0.0.1:{PORT2[port]}'; c = f'{PROJECT}-redis-1'; res = {}
    res['lock_release'] = call(f'{a}/lab/redis/lock-check?id=42', 'POST')

    def rename(n):
        req = urllib.request.Request(f'{a}/api/products/42', data=json.dumps({'name': n}).encode(), method='PUT',
                                     headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=30).read()
    original = call(f'{a}/api/products/42')['name']
    tricky = 'Laptop "Pro" \\ 15″\ttab\nline üß€'
    try:
        rename(tricky)
        call(f'{a}/lab/redis/reset?id=42', 'POST')
        via_redis = call(f'{a}/lab/redis/product/42?mode=distributed')
        cached = call(f'{b}/lab/redis/product/42?mode=distributed')          # second instance reads the cached JSON
        sh(['docker', 'pause', c], check=False, timeout=60)
        try:
            via_db = call(f'{a}/lab/redis/product/42?mode=distributed')
        finally:
            sh(['docker', 'unpause', c], check=False, timeout=60)
        def ok(r):
            try: return json.loads(r['value'])['name'] == tricky
            except Exception: return False
        res['json_special_characters'] = {'loaded_ok': ok(via_redis), 'cached_ok': ok(cached) and cached['source'] == 'redis',
                                          'db_fallback_ok': ok(via_db) and via_db['source'] == 'db-fallback'}
    finally:
        rename(original)
        time.sleep(1)

    rounds = []
    for _ in range(3):
        call(f'{a}/lab/redis/reset?id=42', 'POST'); time.sleep(0.5)
        urls = [f'{a}/lab/redis/product/42?mode=local'] * 50
        out = {}
        def fire(): out['r'] = parallel(urls, workers=50)
        t = threading.Thread(target=fire); t.start()
        time.sleep(0.05)                                                    # leader is inside its 100 ms load
        sh(['docker', 'pause', c], check=False, timeout=60)
        t.join()
        sh(['docker', 'unpause', c], check=False, timeout=60)
        rs, ms = out['r']
        rounds.append({'http_errors': sum('error' in r and 'source' not in r for r in rs),
                       'sources': dict(collections.Counter(str(r.get('source')) for r in rs)),
                       'fallback_p50_ms': round(statistics.median([m for r, m in zip(rs, ms) if r.get('source') == 'db-fallback'] or [0]), 1)})
        time.sleep(1.5)
    res['single_flight_outage'] = rounds

    loads = []
    for _ in range(3):
        call(f'{a}/lab/redis/reset?id=42', 'POST')
        parallel([f'{p}/lab/redis/product/42?mode=distributed' for p in (a, b) for _ in range(50)])
        loads.append(call(f'{a}/lab/redis/loads?id=42')['loads'])
    res['distributed_loads'] = loads
    res['passed'] = (res['lock_release'].get('correct') is True and all(res['json_special_characters'].values())
                     and all(r['http_errors'] == 0 for r in rounds) and loads == [1, 1, 1])
    return res

def probe_correctness(port):
    base = f'http://127.0.0.1:{port}'
    res = {}
    runs = [call(f'{base}/lab/concurrency/reserve?mode=unsafe&stock=100&requests=200', 'POST') for _ in range(30)]
    res['reserve_unsafe'] = {'runs': 30, 'incorrect': sum(not r['correct'] for r in runs), 'max_accepted': max(r['accepted'] for r in runs),
                             'min_remaining': min(r['remaining'] for r in runs)}
    for mode in ('lock', 'atomic'):
        runs = [call(f'{base}/lab/concurrency/reserve?mode={mode}&stock=100&requests=200', 'POST') for _ in range(30)]
        res[f'reserve_{mode}'] = {'runs': 30, 'incorrect': sum(not r['correct'] for r in runs)}
    for single in ('false', 'true'):
        for n in (32, 100):
            loads = [call(f'{base}/lab/resources/stampede?single={single}&requests={n}')['loads'] for _ in range(10)]
            res[f'stampede_single_{single}_{n}'] = {'requests': n, 'loads_min': min(loads), 'loads_max': max(loads)}
    for n in (32, 100):
        r = [call(f'{base}/lab/resources/pool?requests={n}&permits=5') for _ in range(5)]
        res[f'pool_{n}_permits5'] = {'peak_max': max(x['peak'] for x in r), 'rejected_min': min(x['rejected'] for x in r), 'rejected_max': max(x['rejected'] for x in r)}
    a = call(f'{base}/lab/di/instances?mode=shared'); b = call(f'{base}/lab/di/instances?mode=shared')
    c = call(f'{base}/lab/di/instances?mode=request'); d = call(f'{base}/lab/di/instances?mode=request')
    res['di'] = {'shared_same_id': a['id'] == b['id'], 'request_distinct_id': c['id'] != d['id']}
    return res

def probe_cpu(port, warm=5, n=15, count=100000, rounds=500):
    base = f'http://127.0.0.1:{port}'
    out = {}
    for label, q in [('sequential', 'sequential?'), *[(f'parallel-{w}', f'parallel?workers={w}&') for w in (2, 4, 8)]]:
        url = f'{base}/lab/cpu/{q}count={count}&rounds={rounds}'
        for _ in range(warm): call(url)
        samples = [call(url) for _ in range(n)]
        ms = sorted(float(s['elapsedNs']) / 1e6 for s in samples)
        out[label] = {'median_ms': statistics.median(ms), 'min_ms': ms[0], 'max_ms': ms[-1], 'checksum': samples[0]['checksum'],
                      'checksums_equal': len({s['checksum'] for s in samples}) == 1, 'processors': samples[0]['processors']}
    out['all_checksums_equal'] = len({v['checksum'] for v in out.values() if isinstance(v, dict)}) == 1
    return out

# ---- report ----------------------------------------------------------------------------------------
def f(v, d=1):
    return 'n/a' if v is None else (f'{v:.{d}f}' if isinstance(v, (int, float)) else str(v))

def write_report(out, meta, results):
    L = ['# HTTP benchmark report — measured local results', '',
         'Indicative measurements of these lab implementations on one workstation. Not universal framework rankings.', '',
         f'- Run: `{out.name}`  ', f'- Host: {meta["processor"]}, {meta["logical_cpu_count"]} logical CPUs, {meta["os"]}  ',
         f'- Backend container quota: `cpus` per phase (default 4), `mem_limit` 2g. k6 {K6_IMAGE} in a container on the Compose network.  ',
         '- Each k6 row: constant-arrival-rate, 10 s unreported warm-up, then the measured duration. Latency in ms. Container CPU/memory sampled once mid-run.', '']
    L += ['## Runtime identification', '', '| Phase | /lab/threads/info |', '|---|---|']
    for ph in results:
        L.append(f'| {ph["id"]} | `{json.dumps(ph.get("info"))}` |')
    L += ['', '## k6 results', '', '| Phase | Experiment | Lab | Target rps | Achieved rps | p50 | p95 | p99 | max | Failed | Dropped | Max VUs | CPU | Memory |',
          '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for ph in results:
        for e in ph['k6']:
            r = e['result'] or {}
            if 'error' in r:
                L.append(f'| {ph["id"]} | {e["id"]} | {e["lab"]} | {e["rate"]} | ERROR: {r["error"][:120]} |||||||||'); continue
            c = r.get('container', {})
            L.append(f'| {ph["id"]} | {e["id"]} | {e["lab"]} | {e["rate"]} | {f(r["rps"])} | {f(r["p50"],2)} | {f(r["p95"],2)} | {f(r["p99"],2)} | {f(r["max"],1)} | '
                     f'{f((r["failed_rate"] or 0)*100,2)}% | {r["dropped"]} | {f(r["vus_max"],0)} | {c.get("cpu","n/a")} | {c.get("mem","n/a")} |')
    groups = {}
    for ph in results:
        for e in ph['k6']:
            if e.get('rep') and 'error' not in (e['result'] or {}):
                groups.setdefault((ph['id'], e['id'], e['lab'], e['rate']), []).append(e['result'])
    if groups:
        L += ['', '## Repeatability — median [min – max] over repetitions', '',
              '| Phase | Experiment | Lab | Target rps | n | Achieved rps | p50 ms | p99 ms | Dropped | Failed % |', '|---|---|---|---:|---:|---|---|---|---|---|']
        def mm(vals, d=1):
            vals = [v for v in vals if v is not None]
            return f'{f(statistics.median(vals), d)} [{f(min(vals), d)} – {f(max(vals), d)}]' if vals else 'n/a'
        for (pid, eid, lab, rate), rs in groups.items():
            L.append(f'| {pid} | {eid} | {lab} | {rate} | {len(rs)} | {mm([x["rps"] for x in rs])} | {mm([x["p50"] for x in rs], 2)} | {mm([x["p99"] for x in rs], 2)} | '
                     f'{mm([x["dropped"] for x in rs], 0)} | {mm([(x["failed_rate"] or 0) * 100 for x in rs], 2)} |')
    for key, title in (('di2', 'DI captive / mutable state (Lab 06)'), ('events', 'Transactional events (Lab 07)'), ('pinning', 'Virtual-thread pinning (Lab 04)'), ('redis', 'Redis shared cache stampede (Lab 08)'), ('redis2', 'Redis consistency and outage (Lab 08)')):
        rows = [(ph, ph[key]) for ph in results if ph.get(key)]
        if rows:
            L += ['', f'## Probe: {title}', '']
            for ph, c in rows:
                L += [f'### {ph["id"]}', '', '```json', json.dumps(c, indent=1), '```', '']
    cpu_rows = [(ph, ph['cpu']) for ph in results if ph.get('cpu') and 'error' not in ph['cpu']]
    if cpu_rows:
        L += ['', '## CPU probe (Lab 05) — elapsed ms per request, median of 15 after 5 warm-ups (count=100000, rounds=500)', '',
              '| Phase | CPU quota | Visible processors | sequential | parallel-2 | parallel-4 | parallel-8 | Speed-up 8 vs seq | Checksums equal |', '|---|---:|---:|---:|---:|---:|---:|---:|---|']
        for ph, c in cpu_rows:
            L.append(f'| {ph["id"]} | {ph["cpus"]} | {c["sequential"]["processors"]} | ' + ' | '.join(f(c[k]["median_ms"], 1) for k in ('sequential', 'parallel-2', 'parallel-4', 'parallel-8')) +
                     f' | {c["sequential"]["median_ms"]/c["parallel-8"]["median_ms"]:.2f}x | {c["all_checksums_equal"]} |')
    cor = [(ph, ph['correctness']) for ph in results if ph.get('correctness')]
    if cor:
        L += ['', '## Correctness probes (Labs 02, 06, 08)', '']
        for ph, c in cor:
            L += [f'### {ph["id"]}', '', '```json', json.dumps(c, indent=1), '```', '']
    L += ['', 'Raw k6 summaries (`*.json`), `probes.json` and `environment.json` are stored next to this report.']
    (out / 'REPORT.md').write_text('\n'.join(L) + '\n', encoding='utf-8')

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--only', default='', help='comma-separated phase ids (prefix match)')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--note', default='')
    a = ap.parse_args()
    phases = [p for p in PHASES if not a.only or any(p['id'].startswith(x) for x in a.only.split(','))]
    if a.list:
        for p in phases: print(p['id'], '-', p['title'], '-', [e['id'] for e in p['experiments']], p['probes'])
        return
    out = ROOT / 'reports' / 'http-runs' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'); out.mkdir(parents=True)
    meta = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'os': platform.platform(), 'processor': a.note or platform.processor(),
            'logical_cpu_count': os.cpu_count(), 'docker': sh(['docker', 'version', '--format', '{{.Server.Version}}'], check=False).stdout.strip(),
            'k6_image': K6_IMAGE, 'phases': [p['id'] for p in phases], 'status': 'running',
            'git_commit': sh(['git', 'rev-parse', 'HEAD'], check=False).stdout.strip(),
            'git_dirty_files': len([l for l in sh(['git', 'status', '--porcelain'], check=False).stdout.splitlines() if l.strip()]),
            'workload': {'products': 100000, 'warmup': '10 s (30 s for >= 1000 req/s), one per experiment', 'measure': 'per experiment, usually 30 s',
                         'executor': 'k6 constant-arrival-rate', 'backend_limits': 'cpus per phase (default 4), mem_limit 2g',
                         'upstream_mock': '100/200/300 ms', 'repetitions': {p['id']: p.get('repeat', 1) for p in phases}}}
    (out / 'environment.json').write_text(json.dumps(meta, indent=2))
    sh(['docker', 'pull', '-q', K6_IMAGE], check=False, timeout=600)
    results = []
    try:
        for ph in phases:
            print(f'== {ph["id"]}', flush=True)
            env, info = start(ph)
            port = BACKENDS[ph['backend']]['port']
            r = {'id': ph['id'], 'title': ph['title'], 'cpus': ph['cpus'], 'env': ph['env'], 'info': info, 'k6': []}
            reps = ph.get('repeat', 1)
            for e in ph['experiments']:
                settle(port)
                run_k6(ph, e, out, measured=False)          # one warm-up per experiment, then `reps` measured runs
                for i in range(1, reps + 1):
                    if i > 1: settle(port)
                    res = run_k6(ph, e, out, rep=i if reps > 1 else None)
                    res['settled_after'] = settle(port)
                    print(f'   {e["id"]}{f" r{i}" if reps > 1 else ""}: {json.dumps(res)}', flush=True)
                    r['k6'].append({**e, 'rep': i if reps > 1 else None, 'result': res})
            settle(port)
            probes = {'correctness': probe_correctness, 'cpu': probe_cpu, 'di2': probe_di2, 'events': probe_events, 'pinning': probe_pinning, 'redis': probe_redis,
                      'ownership': probe_ownership, 'failure': probe_failure, 'staleness': probe_staleness, 'redis2': probe_redis2,
                      'outage': probe_outage, 'redis_regression': probe_redis_regression}
            for name in ph['probes']:
                try: r[name] = probes[name](port)
                except Exception as ex: r[name] = {'error': repr(ex)}
                print(f'   probe {name}: {json.dumps(r[name])[:400]}', flush=True)
            results.append(r)
            (out / 'probes.json').write_text(json.dumps(results, indent=1))
            write_report(out, meta, results)
        meta['status'] = 'completed'
    except BaseException as ex:
        meta['status'] = f'failed: {ex}'; raise
    finally:
        meta['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (out / 'environment.json').write_text(json.dumps(meta, indent=2))
        if results: write_report(out, meta, results)
        print(out / 'REPORT.md')

if __name__ == '__main__':
    main()
