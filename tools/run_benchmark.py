#!/usr/bin/env python3
"""Run JMH in separate forks; preserve raw JSON, command, environment, and Markdown."""
import argparse, datetime, hashlib, json, os, platform, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
JAR = ROOT/'implementations/spring-boot/benchmarks-jmh/target/benchmarks.jar'
def capture(args):
    try:
        p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=20)
        return (p.stdout + p.stderr).strip() if p.returncode == 0 else 'unavailable: ' + p.stderr.strip()
    except (OSError, subprocess.TimeoutExpired):
        return 'unavailable'
def fmt(value):
    return f'{value:.4g}' if isinstance(value, (int,float)) and abs(value) != float('inf') and value == value else 'n/a'
KEEP = ('reader','writer','gc.alloc.rate.norm','gc.count','gc.time')
def _metrics(row):
    metrics = {'primary':row['primaryMetric'], **row.get('secondaryMetrics',{})}
    return [(n,m) for n,m in metrics.items() if n=='primary' or n.endswith(':reader') or n.endswith(':writer') or n in KEEP]
def write_report(out, meta, files):
    cache, other = [], []
    for file in files:
        for row in json.loads(file.read_text()):
            (cache if 'strategy' in row.get('params',{}) else other).append(row)
    lines=['# JMH benchmark — measured local results', '', 'These are indicative measurements of these implementations on one machine, not universal framework rankings.', '', f"Run: `{out.name}`"]
    if cache:
        lines += ['', '## Cache (Lab 01)', '', '| Benchmark | Strategy | Products | Threads | Score | Error | Unit |', '|---|---|---:|---:|---:|---:|---|']
        for row in cache:
            for name,m in _metrics(row):
                lines.append(f"| {row['benchmark'].split('.')[-1]} / {name} | {row['params']['strategy']} | {row['params']['count']} | {row['threads']} | {fmt(m['score'])} | {fmt(m.get('scoreError'))} | {m['scoreUnit']} |")
        lines += ['', 'Mixed group: four reader threads and one writer thread; this is not a fixed 80/20 operation ratio. Writer score counts batches, not products. Compare subgroup scores, not just aggregate throughput.']
    if other:
        lines += ['', '## Engineering kernels (Lab 02 / Lab 05)', '', '| Benchmark | Params | Threads | Score | Error | Unit |', '|---|---|---:|---:|---:|---|']
        for row in other:
            params=', '.join(f'{k}={v}' for k,v in row.get('params',{}).items())
            for name,m in _metrics(row):
                lines.append(f"| {row['benchmark'].split('.')[-1]} / {name} | {params} | {row['threads']} | {fmt(m['score'])} | {fmt(m.get('scoreError'))} | {m['scoreUnit']} |")
    lines += ['', 'Review correctness guarantees before interpreting scores. See `docs/BENCHMARKS.md`. Raw JSON and `environment.json` are stored alongside this report.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count',type=int,choices=[10000,100000,1000000],default=100000)
    parser.add_argument('--smoke',action='store_true',help='short run; not a publishable benchmark')
    parser.add_argument('--note',default='',help='CPU model, power mode, other environment notes')
    parser.add_argument('--java',default='java',help='path to Java 25 executable')
    parser.add_argument('--suite',choices=['cache','engineering','all'],default='cache',help='cache = Lab 01 CacheBenchmark; engineering = Lab 02/05 kernels')
    args=parser.parse_args()
    if not JAR.is_file(): parser.error('Build the Maven reactor first (mvn ... package).')
    out=ROOT/'reports/runs'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
    meta={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'os':platform.platform(),'machine':platform.machine(),'processor':platform.processor(),'logical_cpu_count':os.cpu_count(),'note':args.note,'smoke':args.smoke,'java':capture([args.java,'-version']),'java_system':capture([args.java,'-XshowSettings:system','-version']),'git_commit':capture(['git','rev-parse','HEAD']),'git_status':capture(['git','status','--porcelain']),'jar_sha256':hashlib.sha256(JAR.read_bytes()).hexdigest(),'commands':[],'status':'running'}
    env=out/'environment.json'
    def save(): env.write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    save();files=[]
    try:
        runs=[]
        if args.suite in ('cache','all'):
            runs += [(name,['.*CacheBenchmark.'+name+'$','-p',f'count={args.count}','-t',str(threads)]) for name,threads in [('readOnly',4),('mixed',5)]]
        if args.suite in ('engineering','all'):
            runs += [('engineering',['.*EngineeringBenchmark.*'])]
        for name,selector in runs:
            file=out/(name+'.json')
            cmd=[args.java,'-jar',str(JAR),*selector,'-rf','json','-rff',str(file),'-prof','gc']
            if args.smoke: cmd += ['-f','1','-wi','1','-i','1','-w','1s','-r','1s']
            meta['commands'].append(cmd);save()
            subprocess.run(cmd,cwd=ROOT,check=True);files.append(file)
        meta['status']='completed';write_report(out,meta,files)
        if args.smoke:
            path=out/'REPORT.md';path.write_text('> **Smoke run only. Do not use these scores as benchmark evidence.**\n\n'+path.read_text(encoding='utf-8'),encoding='utf-8')
    except BaseException:
        meta['status']='failed';raise
    finally: save()
    print(out/'REPORT.md')
if __name__=='__main__': main()
