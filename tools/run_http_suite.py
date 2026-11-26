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
import argparse, datetime, json, os, platform, statistics, subprocess, sys, threading, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.name
NETWORK = f'{PROJECT}_default'
K6_IMAGE = 'grafana/k6:1.3.0'
BACKENDS = {  # service, host port env, host port, compose profile
    'spring':  dict(service='app',     port_env='LAB_PORT',     port=18080, profile=None),
    'jakarta': dict(service='jakarta', port_env='JAKARTA_PORT', port=18081, profile='jakarta'),
    'dotnet':  dict(service='dotnet',  port_env='DOTNET_PORT',  port=18082, profile='dotnet'),
}

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

def phase(id, backend, env=None, experiments=(), probes=(), cpus=4, title=''):
    return dict(id=id, backend=backend, env=env or {}, experiments=list(experiments), probes=list(probes), cpus=cpus, title=title or id)

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
]

# ---- helpers ---------------------------------------------------------------------------------------
def sh(args, env=None, check=True, timeout=1800):
    p = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    if check and p.returncode != 0:
        raise RuntimeError(f'{" ".join(args)} failed ({p.returncode}):\n{p.stdout[-3000:]}\n{p.stderr[-3000:]}')
    return p

def compose_env(ph):
    env = dict(os.environ)
    env.update({'SPRING_PROFILES_ACTIVE': 'lab', 'LAB_CPUS': str(ph['cpus']), 'LAB_MEMORY': '2g', 'LAB_CACHE_STRATEGY': 'snapshot'})
    for b in BACKENDS.values():
        env[b['port_env']] = str(b['port'])
    env.update(ph['env'])
    return env

def compose(env, *args, profiles=('jakarta', 'dotnet'), timeout=1800):
    base = ['docker', 'compose', '-f', 'docker-compose.yml', '-f', 'docker-compose.cpu.yml']
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
    others = [x['service'] for k, x in BACKENDS.items() if k != ph['backend']]
    compose(env, 'stop', *others)
    compose(env, 'up', '-d', '--build', '--force-recreate', b['service'], 'mock-api', timeout=3600)
    wait_ready(b['port'])
    info = call(f'http://127.0.0.1:{b["port"]}/lab/threads/info')
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

def run_k6(ph, exp, out_dir, measured=True):
    b = BACKENDS[ph['backend']]
    name = f'{ph["id"]}__{exp["id"]}'
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
    cpu_rows = [(ph, ph['cpu']) for ph in results if ph.get('cpu')]
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
            'k6_image': K6_IMAGE, 'phases': [p['id'] for p in phases], 'status': 'running'}
    (out / 'environment.json').write_text(json.dumps(meta, indent=2))
    sh(['docker', 'pull', '-q', K6_IMAGE], check=False, timeout=600)
    results = []
    try:
        for ph in phases:
            print(f'== {ph["id"]}', flush=True)
            env, info = start(ph)
            port = BACKENDS[ph['backend']]['port']
            r = {'id': ph['id'], 'title': ph['title'], 'cpus': ph['cpus'], 'env': ph['env'], 'info': info, 'k6': []}
            for e in ph['experiments']:
                settle(port)
                run_k6(ph, e, out, measured=False)
                res = run_k6(ph, e, out)
                res['settled_after'] = settle(port)
                print(f'   {e["id"]}: {json.dumps(res)}', flush=True)
                r['k6'].append({**e, 'result': res})
            settle(port)
            if 'correctness' in ph['probes']: r['correctness'] = probe_correctness(port)
            if 'cpu' in ph['probes']: r['cpu'] = probe_cpu(port)
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
