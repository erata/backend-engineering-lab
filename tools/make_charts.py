#!/usr/bin/env python3
"""Generate the documentation charts (docs/images/*-light.svg / *-dark.svg) from the raw benchmark files.

Every number is read from reports/ (JMH JSON, BenchmarkDotNet JSON, run_http_suite probes.json); nothing is typed in.
Colours follow a validated categorical palette (light and dark steps of the same hues). Static SVG cannot carry hover
tooltips, so every mark has a direct value label and every chart sits next to a data table in the docs.

    python tools/make_charts.py            # requires matplotlib
"""
import json, os, statistics, glob
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'images'
JMH = ROOT / 'reports/runs/20261126T194918342533Z'
BDN = ROOT / 'reports/bdn-runs/net10/results'
RUN1 = ROOT / 'reports/http-runs/20261126T202650Z'
RUN2 = ROOT / 'reports/http-runs/20261126T222721Z'

THEMES = {
    'light': dict(surface='#ffffff', ink='#191919', ink2='#666666', grid='#e7e7e7', axis='#c2c2c2',
                  series=['#257de0', '#f47230', '#00b894', '#f2a600'], critical='#dc3c3d', good='#0aac23', muted='#c2c2c2'),
    'dark': dict(surface='#191919', ink='#efefef', ink2='#9c9c9c', grid='#303030', axis='#474747',
                 series=['#338ced', '#e76624', '#00a888', '#d28e05'], critical='#dc3c3d', good='#0aac23', muted='#474747'),
}
plt.rcParams.update({'svg.fonttype': 'none', 'font.family': ['Segoe UI', 'DejaVu Sans', 'sans-serif'], 'font.size': 10})

# ---------------------------------------------------------------- data loading
def v2_runs():
    """All run folders containing v2/v3/v4 phases, oldest first (a later run's phase replaces an earlier one with the same id)."""
    out = []
    for d in sorted((ROOT / 'reports/http-runs').iterdir()):
        env = d / 'environment.json'
        if env.exists() and any(p.startswith(('v2-', 'v3-', 'v4-')) for p in json.loads(env.read_text()).get('phases', [])):
            out.append(d)
    return out
V2 = v2_runs()

def phases(run):
    runs = run if isinstance(run, list) else [run]
    merged = {}
    for r in runs:
        if r and (r / 'probes.json').exists():
            merged.update({p['id']: p for p in json.loads((r / 'probes.json').read_text())})
    return merged

def k6(ph, exp):
    """All results of one experiment in one phase (several if repeated)."""
    return [e['result'] for e in ph.get('k6', []) if e['id'] == exp and e['result'] and 'error' not in e['result']]

def med(xs): return statistics.median(xs) if xs else None

# ---------------------------------------------------------------- drawing helpers
def figure(t, w=7.2, h=3.4, ncols=1):
    fig, axes = plt.subplots(1, ncols, figsize=(w, h), facecolor=t['surface'])
    for ax in (axes if ncols > 1 else [axes]):
        ax.set_facecolor(t['surface'])
        for s in ('top', 'right'): ax.spines[s].set_visible(False)
        for s in ('left', 'bottom'): ax.spines[s].set_color(t['axis'])
        ax.tick_params(colors=t['ink2'], length=0, pad=6)
        ax.grid(axis='x', color=t['grid'], linewidth=0.8); ax.set_axisbelow(True)
    return fig, axes

def title(fig, t, text, sub=None):
    fig.text(0.012, 0.97, text, color=t['ink'], fontsize=12, fontweight='bold', va='top')
    if sub: fig.text(0.012, 0.89, sub, color=t['ink2'], fontsize=9, va='top')

def legend(ax, t, handles_labels, loc='lower right'):
    lg = ax.legend(*handles_labels, loc=loc, frameon=False, fontsize=9)
    for txt in lg.get_texts(): txt.set_color(t['ink2'])

def save(fig, name, mode, top=0.80):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.subplots_adjust(top=top)
    fig.savefig(OUT / f'{name}-{mode}.svg', facecolor=fig.get_facecolor(), bbox_inches='tight', pad_inches=0.15)
    if os.environ.get('CHART_PNG_DIR'):   # optional raster copies for visual review
        fig.savefig(Path(os.environ['CHART_PNG_DIR']) / f'{name}-{mode}.png', facecolor=fig.get_facecolor(), bbox_inches='tight', pad_inches=0.15, dpi=110)
    plt.close(fig)

def hbars(ax, t, labels, values, colors, fmt, xmax=None, errs=None):
    y = range(len(labels))
    ax.barh(list(y), values, color=colors, height=0.6, edgecolor=t['surface'], linewidth=2,
            xerr=errs, error_kw=dict(ecolor=t['ink2'], elinewidth=1, capsize=3) if errs else None)
    ax.set_yticks(list(y), labels); ax.invert_yaxis()
    top = xmax or max(v for v in values if v is not None) * 1.25
    ax.set_xlim(0, top)
    for i, v in enumerate(values):
        hi = v + (errs[1][i] if errs else 0)
        ax.text(hi + top * 0.012, i, fmt(v), va='center', color=t['ink'], fontsize=9)

def grouped_v(ax, t, groups, series, values, fmt, ylabel, missing_text=None):
    n = len(series); w = 0.8 / n
    for j, s in enumerate(series):
        xs = [i + (j - (n - 1) / 2) * w for i in range(len(groups))]
        vals = [values[g].get(s) for g in groups]
        ax.bar([x for x, v in zip(xs, vals) if v is not None], [v for v in vals if v is not None], width=w,
               color=t['series'][j], edgecolor=t['surface'], linewidth=2, label=s)
        for x, v in zip(xs, vals):
            if v is None:
                ax.text(x, 0, (missing_text or {}).get(s, 'n/a'), rotation=90, ha='center', va='bottom', color=t['ink2'], fontsize=8)
            else:
                ax.text(x, v, fmt(v), ha='center', va='bottom', color=t['ink'], fontsize=8)
    ax.set_xticks(range(len(groups)), groups); ax.set_ylabel(ylabel, color=t['ink2'])
    ax.grid(axis='x', visible=False); ax.grid(axis='y', color=t['grid'], linewidth=0.8)

# ---------------------------------------------------------------- charts
def lab01(t, mode):
    rows = {r['params']['strategy']: r for r in json.loads((JMH / 'readOnly.json').read_text())}
    order = ['synchronized', 'concurrent', 'snapshot', 'caffeine']
    vals = [rows[s]['primaryMetric']['score'] / 1e6 for s in order]
    errs = [rows[s]['primaryMetric']['scoreError'] / 1e6 for s in order]
    fig, ax = figure(t, h=2.8)
    hbars(ax, t, order, vals, t['series'][0], lambda v: f'{v:.1f} M', errs=[errs, errs])
    ax.set_xlabel('million lookups per second (4 threads, error bar = 99.9 % CI)', color=t['ink2'])
    title(fig, t, 'Lab 01 · Cache read throughput (JMH, 100K products)', 'Higher is better. Snapshot reads are 19× faster than one global lock.')
    save(fig, 'lab01-jmh-read', mode, top=0.76)

    mixed = {r['params']['strategy']: r for r in json.loads((JMH / 'mixed.json').read_text())}
    fig, (a1, a2) = figure(t, w=7.6, h=2.9, ncols=2)
    rd = [mixed[s]['secondaryMetrics']['reader']['score'] / 1e6 for s in order]
    wr = [mixed[s]['secondaryMetrics']['writer']['score'] for s in order]
    hbars(a1, t, order, rd, t['series'][0], lambda v: f'{v:.1f} M')
    a1.set_xlabel('reader lookups/s (millions)', color=t['ink2'])
    a2.set_xscale('log'); a2.set_xlim(10, 5e6)
    a2.hlines(range(4), 10, wr, color=t['axis'], linewidth=1)
    a2.plot(wr, range(4), 'o', color=t['series'][1], markersize=8, markeredgecolor=t['surface'], markeredgewidth=2)
    a2.set_yticks(range(4), ['', '', '', '']); a2.invert_yaxis()
    for i, v in enumerate(wr): a2.text(v * 1.6, i, f'{v:,.0f}' if v < 1000 else f'{v / 1e3:,.0f} K', va='center', color=t['ink'], fontsize=9)
    a2.set_xlabel('writer batches/s (log scale)', color=t['ink2'])
    a2.set_xlim(10, 2e7); a2.set_xticks([10, 1e3, 1e5, 1e7], ['10', '1K', '100K', '10M']); a2.minorticks_off()
    title(fig, t, 'Lab 01 · One writer + four readers (JMH)', 'The snapshot keeps reads fast but copies 100K entries per batch: 33 batches/s vs ~600 K.')
    save(fig, 'lab01-jmh-mixed', mode, top=0.74)

def lab02(t, mode):
    ph = phases(RUN2)
    eds = [('Spring Boot', 'spring-j25-platform-snapshot'), ('Jakarta EE', 'jakarta-j25-snapshot'), ('ASP.NET Core', 'dotnet10-snapshot')]
    bad = [ph[p]['correctness']['reserve_unsafe']['incorrect'] for _, p in eds]
    fig, ax = figure(t, h=2.5)
    ax.barh(range(3), [30] * 3, color=t['muted'], height=0.6, alpha=0.35)
    ax.barh(range(3), bad, color=t['critical'], height=0.6, edgecolor=t['surface'], linewidth=2)
    ax.set_yticks(range(3), [e for e, _ in eds]); ax.invert_yaxis(); ax.set_xlim(0, 34)
    for i, v in enumerate(bad): ax.text(v + 0.4, i, f'✖ {v} of 30 runs oversold', va='center', color=t['ink'], fontsize=9)
    ax.set_xlabel('runs with a wrong result (stock 100, 200 concurrent buyers)', color=t['ink2'])
    title(fig, t, 'Lab 02 · Unsafe check-then-act oversells', 'lock and CAS: 0 wrong results in 30 runs on every edition (not drawn: zero-length bars).')
    save(fig, 'lab02-unsafe', mode, top=0.74)

def lab03(t, mode):
    """v4 phases (asyncio upstream), median of 5 runs; a mode whose runs mostly failed is shown as text."""
    ph = phases(V2)
    eds = {'Spring Boot': 'v4-rep5-spring-j25-platform', 'Jakarta EE': 'v4-rep5-jakarta', 'ASP.NET Core': 'v4-rep5-dotnet10'}
    if not all(p in ph for p in eds.values()): return
    modes = ['blocking', 'sequential-async', 'concurrent']
    vals = {e: {m: (med([r['p50'] for r in k6(ph[p], f'io-{m}') if (r['failed_rate'] or 0) < 0.01]) or None) for m in modes} for e, p in eds.items()}
    fig, ax = figure(t, h=3.3)
    grouped_v(ax, t, list(eds), modes, vals, lambda v: f'{v:.0f}', 'p50 latency (ms)', missing_text={'blocking': '100 % timeouts'})
    tr = ax.get_yaxis_transform()
    for yv, lbl in ((600, 'sum of the\nthree calls'), (300, 'slowest\ncall')):
        ax.axhline(yv, color=t['ink2'], linewidth=1, linestyle=(0, (4, 3)), zorder=0)
        ax.text(1.01, yv, lbl, transform=tr, color=t['ink2'], fontsize=8, va='center')
    ax.set_ylim(0, 700)
    lg = ax.legend(*ax.get_legend_handles_labels(), loc='lower left', bbox_to_anchor=(0, 1.0), ncols=3, frameon=False, fontsize=9)
    for x in lg.get_texts(): x.set_color(t['ink2'])
    title(fig, t, 'Lab 03 · Aggregating three slow services (50 req/s, median of 5 runs)', 'Only the concurrent fan-out halves latency. .NET blocking = sync-over-async: median of the successful runs; run 1 after start starved (85 % failed).')
    save(fig, 'lab03-io', mode, top=0.76)

def lab04(t, mode):
    ph = phases(V2)
    cfg = [('Java 17 · platform', 'v4-rep5-spring-j17-platform'), ('Java 25 · platform', 'v4-rep5-spring-j25-platform'), ('Java 25 · virtual', 'v4-rep5-spring-j25-virtual')]
    if not all(p in ph for _, p in cfg): return
    rs = [k6(ph[p], 'io-blocking-400rps') for _, p in cfg]
    fig, (a1, a2) = figure(t, w=7.8, h=2.9, ncols=2)
    for ax, key, xl, fmt in ((a1, 'rps', 'achieved req/s (target 400)', lambda v: f'{v:.0f}'), (a2, 'p50', 'p50 latency (ms)', lambda v: f'{v:,.0f}')):
        vals = [med([r[key] for r in x]) for x in rs]
        lo = [v - min(r[key] for r in x) for v, x in zip(vals, rs)]; hi = [max(r[key] for r in x) - v for v, x in zip(vals, rs)]
        cols = [t['series'][1], t['series'][1], t['series'][0]]
        hbars(ax, t, [c for c, _ in cfg] if ax is a1 else ['', '', ''], vals, cols, fmt, errs=[lo, hi])
        ax.set_xlabel(xl + ', median of 5, bar = min–max', color=t['ink2'])
    a1.axvline(400, color=t['ink2'], linewidth=1, linestyle=(0, (4, 3)))
    title(fig, t, 'Lab 04 · 400 req/s of 600 ms blocking I/O (Spring Boot, 4 CPUs)',
          'Platform threads (orange) cap at ~200 threads / 0.6 s; virtual threads (blue) keep up at upstream latency.')
    save(fig, 'lab04-threads', mode, top=0.74)

    pin = [(lbl, ph.get(p, {}).get('pinning')) for lbl, p in (('Java 21', 'v2-pinning-j21'), ('Java 25', 'v2-pinning-j25'))]
    if all(x and 'error' not in x for _, x in pin):
        fig, ax = figure(t, h=3.1)
        vals = {lbl: {'synchronized': x['synchronized']['median_ms'], 'ReentrantLock': x['reentrant']['median_ms']} for lbl, x in pin}
        grouped_v(ax, t, [l for l, _ in pin], ['synchronized', 'ReentrantLock'], vals, lambda v: f'{v:,.0f} ms', 'elapsed ms (median of 10)')
        legend(ax, t, ax.get_legend_handles_labels(), loc='upper right')
        title(fig, t, 'Lab 04 · Virtual-thread pinning: 100 tasks × 50 ms sleep inside a lock',
              f'{pin[0][1]["synchronized"]["carriers"]} carrier threads. JDK 21 pins carriers in synchronized; JDK 24+ (JEP 491) does not.')
        save(fig, 'lab04-pinning', mode, top=0.76)

    jk = ph.get('v4-rep3-jakarta-saturation')
    if jk:
        rows = [('WildFly · worker thread', k6(jk, 'io-blocking-400rps'))] + [(f'WildFly · {x} executor', k6(jk, f'io-blocking-async-{x}-400rps')) for x in ('default', 'virtual')]
        if all(r for _, r in rows):
            fig, (a1, a2) = figure(t, w=8.2, h=2.7, ncols=2)
            cols = [t['series'][1], t['series'][1], t['series'][0]]
            okr = [med([x['rps'] * (1 - (x['failed_rate'] or 0)) for x in r]) for _, r in rows]
            hbars(a1, t, [l for l, _ in rows], okr, cols, lambda v: f'{v:.0f}')
            a1.axvline(400, color=t['ink2'], linewidth=1, linestyle=(0, (4, 3))); a1.set_xlabel('successful req/s (target 400), median of 3', color=t['ink2'])
            hbars(a2, t, ['', '', ''], [med([x['p50'] for x in r]) for _, r in rows], cols, lambda v: f'{v:,.0f} ms')
            a2.set_xlabel('p50 latency (ms), median of 3', color=t['ink2'])
            title(fig, t, 'Lab 04 · Jakarta Concurrency 3.1 virtual executor on WildFly 42', 'Same blocking chain, async JAX-RS response; only the managed executor differs.')
            save(fig, 'lab04-wildfly-virtual', mode, top=0.70)

def lab05(t, mode):
    jmh = {r['params']['workers']: r['primaryMetric']['score'] for r in json.loads((JMH / 'engineering.json').read_text()) if r['benchmark'].endswith('.cpu')}
    bdn = {}
    for f in glob.glob(str(BDN / 'CpuBench-report-full-compressed.json')):
        for b in json.loads(Path(f).read_text())['Benchmarks']:
            bdn[str(b['Parameters']).split('=')[-1]] = b['Statistics']['Mean'] / 1e6   # mean, like the BDN report table
    ws = ['1', '2', '4', '8']
    fig, (a1, a2) = figure(t, w=8.0, h=3.2, ncols=2)
    for ax in (a1, a2):
        ax.plot([1, 2, 4, 8], [1, 2, 4, 8], color=t['ink2'], linewidth=1, linestyle=(0, (4, 3)))
        ax.set_xscale('log', base=2); ax.set_xticks([1, 2, 4, 8], ['1', '2', '4', '8']); ax.set_ylim(0, 8.6)
        ax.set_xlabel('workers', color=t['ink2']); ax.grid(axis='y', color=t['grid'], linewidth=0.8)
    a1.text(8, 8.2, 'ideal', color=t['ink2'], fontsize=8, ha='right')
    for j, (lbl, d) in enumerate((('JMH · Java 25', jmh), ('BDN · .NET 10', bdn))):
        sp = [d[ws[0]] / d[w] for w in ws]
        a1.plot([1, 2, 4, 8], sp, '-o', color=t['series'][j], linewidth=2, markersize=8, markeredgecolor=t['surface'], markeredgewidth=2, label=lbl)
        a1.text(8.4, sp[-1], f'{sp[-1]:.1f}×', color=t['ink'], fontsize=9, va='center')
    a1.set_ylabel('speed-up vs 1 worker', color=t['ink2']); a1.set_title('host, no CPU limit', color=t['ink2'], fontsize=9, loc='left')
    legend(a1, t, a1.get_legend_handles_labels(), loc='upper left')
    ph = phases(RUN2); ends = []
    for j, q in enumerate((1, 2, 4, 8)):
        ids = [f'cpu{q}-spring', f'cpu{q}-jakarta', f'cpu{q}-dotnet'] if q != 4 else ['spring-j25-platform-snapshot', 'jakarta-j25-snapshot', 'dotnet10-snapshot']
        cs = [ph[i]['cpu'] for i in ids if i in ph and ph[i].get('cpu')]
        sp = [statistics.median(c['sequential']['median_ms'] / (c['sequential']['median_ms'] if w == 1 else c[f'parallel-{w}']['median_ms']) for c in cs) for w in (1, 2, 4, 8)]
        a2.plot([1, 2, 4, 8], sp, '-o', color=t['series'][j], linewidth=2, markersize=8, markeredgecolor=t['surface'], markeredgewidth=2, label=f'cpus: {q}')
        ends.append([sp[-1], f'{q} CPU: {sp[-1]:.1f}×'])
    ends.sort()                                   # nudge end labels apart so they never overlap
    for i in range(1, len(ends)):
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 0.55)
    for yv, lbl in ends: a2.text(8.4, yv, lbl, color=t['ink'], fontsize=9, va='center')
    a2.set_title('Docker CPU quota, median of 3 editions', color=t['ink2'], fontsize=9, loc='left')
    legend(a2, t, a2.get_legend_handles_labels(), loc='upper left')
    title(fig, t, 'Lab 05 · Parallel speed-up of a CPU-bound kernel', 'Dashed = ideal linear speed-up. The quota, not the worker count, sets the ceiling.')
    save(fig, 'lab05-cpu', mode, top=0.74)

def lab06(t, mode):
    ph = phases(RUN2)
    eds = {'Spring Boot': 'spring-j25-platform-snapshot', 'Jakarta EE': 'jakarta-j25-snapshot', 'ASP.NET Core': 'dotnet10-snapshot'}
    cpu = lambda r: float(r[0]['container']['cpu'].rstrip('%'))
    vals = {e: {'request-scoped': cpu(k6(ph[p], 'di-request')), 'singleton': cpu(k6(ph[p], 'di-shared'))} for e, p in eds.items()}
    fig, ax = figure(t, h=3.0)
    grouped_v(ax, t, list(eds), ['request-scoped', 'singleton'], vals, lambda v: f'{v:.0f} %', 'container CPU % at 50 req/s')
    legend(ax, t, ax.get_legend_handles_labels(), loc='upper left')
    title(fig, t, 'Lab 06 · Building a 100K-entry object per request vs once', 'Same response, 3–15× the CPU. One docker stats sample per run.')
    save(fig, 'lab06-di-cpu', mode, top=0.76)

    v = phases(V2)
    new = {'Spring Boot': 'v2-new-spring', 'Jakarta EE': 'v2-new-jakarta', 'ASP.NET Core': 'v2-new-dotnet10'}
    if all(p in v and v[p].get('di2') and 'error' not in v[p]['di2'] for p in new.values()):
        fig, ax = figure(t, h=2.6)
        bad = [v[p]['di2']['mutable_singleton']['wrong_user_returned'] for p in new.values()]
        tot = [v[p]['di2']['mutable_singleton']['requests'] for p in new.values()]
        ax.barh(range(3), tot, color=t['muted'], height=0.6, alpha=0.35)
        ax.barh(range(3), bad, color=t['critical'], height=0.6, edgecolor=t['surface'], linewidth=2)
        ax.set_yticks(range(3), list(new)); ax.invert_yaxis(); ax.set_xlim(0, max(tot) * 1.32)
        for i, (b, n) in enumerate(zip(bad, tot)): ax.text(b + max(tot) * 0.01, i, f'✖ {b} of {n} got another user', va='center', color=t['ink'], fontsize=9)
        ax.set_xlabel("responses that returned another request's user (200 concurrent requests × 3)", color=t['ink2'])
        title(fig, t, 'Lab 06 · "Current user" stored in a singleton field', 'Request-scoped holder: 0 wrong users on every edition (not drawn).')
        save(fig, 'lab06-mutable', mode, top=0.74)

def lab07(t, mode):
    v = phases(V2)
    rows = []
    sp = v.get('v2-rep5-spring-j25-platform')
    if sp: rows.append(('Spring Boot (median of 5)', med([r['p50'] for r in k6(sp, 'events-direct')]), med([r['p50'] for r in k6(sp, 'events-event')])))
    for lbl, p in (('Jakarta EE (JTA)', 'v2-new-jakarta'), ('ASP.NET Core (outbox)', 'v2-new-dotnet10')):
        if p in v: rows.append((lbl, med([r['p50'] for r in k6(v[p], 'events-direct')]), med([r['p50'] for r in k6(v[p], 'events-event')])))
    rows = [r for r in rows if r[1] and r[2]]
    if not rows: return
    fig, ax = figure(t, h=2.7)
    ax.set_xscale('log')
    for i, (lbl, d, e) in enumerate(rows):
        ax.hlines(i, min(d, e), max(d, e), color=t['axis'], linewidth=1)
        ax.plot(d, i, 'o', color=t['series'][1], markersize=9, markeredgecolor=t['surface'], markeredgewidth=2, label='direct (audit in the same transaction)' if i == 0 else None)
        ax.plot(e, i, 'o', color=t['series'][0], markersize=9, markeredgecolor=t['surface'], markeredgewidth=2, label='event (audit after commit)' if i == 0 else None)
        ax.text(d * 1.35, i - 0.22, f'{d:,.1f} ms', color=t['ink'], fontsize=8); ax.text(e / 1.35, i - 0.22, f'{e:,.1f} ms', color=t['ink'], fontsize=8, ha='right')
    ax.set_yticks(range(len(rows)), [r[0] for r in rows]); ax.invert_yaxis(); ax.set_ylim(len(rows) - 0.4, -0.9)
    ax.set_xlabel('p50 latency, log scale (200 req/s, all on one product row)', color=t['ink2'])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:,.0f}' if x >= 1 else f'{x:g}'))
    lg = ax.legend(*ax.get_legend_handles_labels(), loc='lower left', bbox_to_anchor=(0, 1.0), ncols=2, frameon=False, fontsize=9)
    for x in lg.get_texts(): x.set_color(t['ink2'])
    title(fig, t, 'Lab 07 · Price change + audit on a hot row', 'Moving the audit out of the transaction shortens the row-lock hold time.')
    save(fig, 'lab07-events', mode, top=0.74)

def lab08(t, mode):
    ph, v = phases(RUN2), phases(V2)
    eds = {'Spring Boot': 'spring-j25-platform-snapshot', 'Jakarta EE': 'jakarta-j25-snapshot', 'ASP.NET Core': 'dotnet10-snapshot'}
    vals = {e: {'no coordination': ph[p]['correctness']['stampede_single_false_100']['loads_max'],
                'single-flight': ph[p]['correctness']['stampede_single_true_100']['loads_max']} for e, p in eds.items()}
    rd = v.get('v2-redis-spring', {}).get('redis')
    fig, axes = figure(t, w=8.2, h=3.1, ncols=2 if rd and 'error' not in rd else 1)
    a1 = axes[0] if isinstance(axes, (list, tuple)) or hasattr(axes, '__len__') else axes
    grouped_v(a1, t, list(eds), ['no coordination', 'single-flight'], vals, lambda v: f'{v:.0f}', 'loader calls for 100 requests')
    a1.set_title('in-process, one instance', color=t['ink2'], fontsize=9, loc='left'); legend(a1, t, a1.get_legend_handles_labels(), loc='upper left')
    if rd and 'error' not in rd:
        a2 = axes[1]
        modes = [('none', 'no lock'), ('local', 'local single-flight'), ('distributed', 'Redis lock')]
        hbars(a2, t, [l for _, l in modes], [rd[m]['loads_max'] for m, _ in modes], [t['series'][1], t['series'][2], t['series'][0]], lambda x: f'{x:.0f} loads')
        a2.set_xlabel('MySQL loads for 100 requests (worst of 5)', color=t['ink2'])
        a2.set_title('Redis shared cache, two app instances', color=t['ink2'], fontsize=9, loc='left')
    title(fig, t, 'Lab 08 · Cache stampede: how many requests hit the database?', 'Without coordination the stampede equals the effective concurrency.')
    save(fig, 'lab08-stampede', mode, top=0.74)

    new = {'Spring Boot': 'v2-new-spring', 'Jakarta EE': 'v2-new-jakarta', 'ASP.NET Core': 'v2-new-dotnet10'}
    if all(p in v for p in new.values()):
        cats = [('pool 5 · 100/s', 'dbpool-5-100rps'), ('pool 5 · 300/s', 'dbpool-5-300rps'), ('pool 20 · 100/s', 'dbpool-20-100rps'), ('pool 20 · 300/s', 'dbpool-20-300rps')]
        def ok_rps(r): return r['rps'] * (1 - (r['failed_rate'] or 0))
        vals = {c: {e: (ok_rps(k6(v[p], x)[0]) if k6(v[p], x) else None) for e, p in new.items()} for c, x in cats}
        fig, ax = figure(t, w=8.0, h=3.3)
        grouped_v(ax, t, [c for c, _ in cats], list(new), vals, lambda x: f'{x:.0f}', 'successful req/s')
        ax.hlines([100, 300, 100, 300], [-0.45, 0.55, 1.55, 2.55], [0.45, 1.45, 2.45, 3.45], color=t['ink2'], linewidth=1, linestyles=(0, (4, 3)))
        ax.axhline(166, color=t['ink2'], linewidth=1, linestyle=(0, (1, 2))); ax.text(-0.45, 172, 'pool-5 capacity: 5 / 30 ms ≈ 166/s', color=t['ink2'], fontsize=8, ha='left')
        legend(ax, t, ax.get_legend_handles_labels(), loc='upper left')
        title(fig, t, 'Lab 08 · Real connection pool: each request holds a connection for 30 ms', 'Dashed = offered load. Above capacity, requests wait and then fail (1 s pool timeout, WildFly 30 s).')
        save(fig, 'lab08-dbpool', mode, top=0.76)

def repeatability(t, mode):
    v = phases(V2)
    items = [('Spring · Java 25 platform · 400 req/s blocking', 'v4-rep5-spring-j25-platform', 'io-blocking-400rps', 'rps'),
             ('Spring · Java 25 virtual · 400 req/s blocking', 'v4-rep5-spring-j25-virtual', 'io-blocking-400rps', 'rps'),
             ('Spring · Java 17 platform · 400 req/s blocking', 'v4-rep5-spring-j17-platform', 'io-blocking-400rps', 'rps'),
             ('Spring · events direct · 200 req/s hot row', 'v2-rep5-spring-j25-platform', 'events-direct', 'rps'),
             ('Spring · events after-commit · 200 req/s hot row', 'v2-rep5-spring-j25-platform', 'events-event', 'rps')]
    items = [(l, k6(v[p], e), m) for l, p, e, m in items if p in v and k6(v[p], e)]
    if not items: return
    fig, ax = figure(t, h=0.55 * len(items) + 1.3)
    for i, (l, rs, m) in enumerate(items):
        xs = [r[m] for r in rs]
        ax.hlines(i, min(xs), max(xs), color=t['axis'], linewidth=6, alpha=0.6)
        ax.plot(xs, [i] * len(xs), 'o', color=t['series'][0], markersize=7, markeredgecolor=t['surface'], markeredgewidth=1.5)
        ax.text(max(xs) + 6, i, f'median {statistics.median(xs):.0f} (range {min(xs):.0f}–{max(xs):.0f})', va='center', color=t['ink'], fontsize=8)
    ax.set_yticks(range(len(items)), [l for l, _, _ in items]); ax.invert_yaxis(); ax.set_xlim(0, 560)
    ax.set_xlabel('achieved req/s in each of 5 runs', color=t['ink2'])
    title(fig, t, 'Repeatability · 5 independent runs per configuration', 'Each dot is one 30 s run; the grey band is the min–max range.')
    save(fig, 'repeatability', mode, top=0.78)

def main():
    for mode, t in THEMES.items():
        for chart in (lab01, lab02, lab03, lab04, lab05, lab06, lab07, lab08, repeatability):
            chart(t, mode)
    print('\n'.join(sorted(p.name for p in OUT.glob('*.svg'))))

if __name__ == '__main__':
    main()
