# Benchmark guide

This guide lists every benchmark in the repository: what it measures, how it is configured, how to reproduce it and how to read the output. Measured numbers are kept separately in the [consolidated benchmark report](../reports/BENCHMARK_REPORT.md) and in each lab README.

## 1. Three measurement layers

| Layer | Tool | Measures | Does **not** measure |
|---|---|---|---|
| Method / kernel | **JMH** (Java), **BenchmarkDotNet** (.NET) | the algorithm alone: cache lookup, batch apply, CPU kernel, reservation kernel | HTTP, JSON, framework, DB, network |
| End-to-end HTTP | **k6** in a container, driven by [`tools/run_http_suite.py`](../tools/run_http_suite.py) | latency distribution (p50/p95/p99/max), achieved throughput, errors, dropped iterations, container CPU/memory | where inside the process time is spent |
| Functional probes | `run_http_suite.py` probes, [`compare_http.py`](../tools/compare_http.py) | invariants under concurrency (lost updates, single-flight loads, pool peak), DI identity, CPU checksum equality, server-side elapsed CPU time | performance ranking |

Rule used everywhere: **correctness first.** A benchmark row only counts if the corresponding correctness check passed for that build.

## 2. Benchmark catalogue

### 2.1 JMH — `implementations/spring-boot/benchmarks-jmh`

| Benchmark | Lab | Params | Mode / unit | One operation |
|---|---|---|---|---|
| `CacheBenchmark.readOnly` | 01 | strategy ∈ synchronized, concurrent, snapshot, caffeine; count = 100000; 4 threads | throughput, ops/s | one `get(id)` with a pseudo-random id |
| `CacheBenchmark.mixed` (`reader`, `writer`) | 01 | same; 4 reader + 1 writer threads | throughput, ops/s per sub-group | reader: one `get`; writer: one 16-product batch |
| `EngineeringBenchmark.cpu` | 05 | workers ∈ 1, 2, 4, 8 | average time, ms/op | full checksum over 100,000 items × 100 xorshift rounds |
| `EngineeringBenchmark.reserve` | 02 | mode ∈ atomic, lock | average time, ms/op | one full experiment: 2,000 reservation tasks against stock 1,000 |

Defaults: `@Fork(2)`, `@Warmup(3 × 2 s)`, `@Measurement(5 × 2 s)`, cache forks `-Xms1g -Xmx1g`, GC profiler on.

### 2.2 BenchmarkDotNet — `implementations/aspnet-core/Lab.Benchmarks`

| Benchmark | Lab | Params | One operation |
|---|---|---|---|
| `CpuBench.Recalculate` | 05 | Workers ∈ 1, 2, 4, 8 | same kernel and checksum as JMH `cpu` (`Parallel.For` with `MaxDegreeOfParallelism`) |
| `ReservationBench.Reserve` | 02 | Mode ∈ atomic, lock | same experiment as JMH `reserve` (`Parallel.For` + `Interlocked.CompareExchange` / `lock`) |

BenchmarkDotNet default job (automatic warm-up and iteration count), `[MemoryDiagnoser]`.

### 2.3 k6 HTTP experiments — `benchmarks/k6/workload.js`

All experiments use the `constant-arrival-rate` executor: k6 sends requests at the configured rate whether or not earlier responses have returned. A slow server therefore shows up as higher latency and **dropped iterations**, not as a lower request rate that hides queueing (coordinated omission). Thresholds: `http_req_failed < 1%`, `checks > 99%` (HTTP 200 + valid JSON).

| Experiment id | Lab | Request | Target rate | Duration |
|---|---|---|---:|---|
| `catalog-get` | 01 | `GET /api/products/42` | 2,000/s | 30 s |
| `catalog-page` | 01 | `GET /api/products?page=500&size=20` | 50/s | 30 s |
| `reserve-atomic`, `reserve-lock` | 02 | `POST /lab/concurrency/reserve?mode=…&stock=1000&requests=2000` | 50/s | 30 s |
| `io-blocking`, `io-sequential-async`, `io-concurrent` | 03 | `GET /lab/io/{mode}`, 3 upstream calls of 100/200/300 ms | 50/s | 30 s |
| `io-blocking-400rps` | 04 | `GET /lab/io/blocking` | 400/s | 30 s |
| `di-request`, `di-shared` | 06 | `GET /lab/di/instances?mode=…` | 50/s | 30 s |
| `events-direct`, `events-event`, `events-event-inline` | 07 | `POST /lab/events/price-change?mode=…` (one hot row) | 200/s | 30 s (inline 20 s) |
| `io-blocking-async-{default,virtual}-400rps` | 04 | Jakarta `GET /lab/io/blocking-async?executor=…` | 400/s | 30 s |
| `dbpool-{5,20}-{100,300}rps` | 08 | `GET /lab/resources/db?pool=…&ms=30` (real pool) | 100 / 300/s | 30 s |
| `redis-get` | 08 | `GET /lab/redis/product/42?mode=distributed` (Redis hit) | 2,000/s | 30 s |

### 2.4 Phases (backend configurations)

`run_http_suite.py` runs each experiment set against one backend configuration at a time. All other lab backends are stopped first.

| Phase | Backend | Varies |
|---|---|---|
| `spring-j25-platform-snapshot` | Spring Boot, Java 25 | baseline; all experiments + probes |
| `spring-j25-virtual-snapshot` | Spring Boot, Java 25 | `LAB_VIRTUAL_THREADS=true` (Tomcat on virtual threads) |
| `spring-j17-platform-snapshot` | Spring Boot, Java 17 | JRE only (same jar, compiled for release 17) |
| `spring-j25-platform-{synchronized,concurrent,caffeine}` | Spring Boot, Java 25 | cache strategy |
| `jakarta-j25-snapshot` | WildFly 42, Java 25 | framework; all experiments + probes |
| `dotnet10-snapshot` | ASP.NET Core, .NET 10 | framework; all experiments + probes |
| `dotnet11-snapshot` | ASP.NET Core, .NET 11 | runtime only |
| `cpu{1,2,8}-{spring,jakarta,dotnet}` | each backend | CPU quota (`docker-compose.cpu.yml`, `cpus`) |
| `v2-rep5-*` | Spring 25/virtual/17, Jakarta, .NET 10 | 5 repetitions of catalogue, I/O and event experiments |
| `v2-new-*` | each backend | real DB pool, events (JTA / outbox), Jakarta virtual executor, DI probes |
| `v2-pinning-j21`, `v2-pinning-j25` | Spring | pinning probe on Java 21 and 25 |
| `v2-redis-spring`, `v3-redis-spring` | Spring × 2 + Redis | shared-cache stampede; consistency, invalidation, Redis down |
| `v3-*` | each backend | ownership, handler failure, staleness probes |
| `v4-*` | each backend | **all I/O experiments rerun** with the asyncio upstream (5 or 3 repetitions) |

Controls held fixed: `cpus: 4` (except the CPU phases), `mem_limit: 2g`, same 100K seed, same mock upstream, same k6 image (`grafana/k6:1.3.0`) on the same Docker network, one unrecorded warm-up per experiment (10 s; 30 s at ≥ 1,000 req/s), then the measured runs.

Harness rules learned the hard way (each one invalidated results before it existed, see [VALIDATION_STATUS.md](VALIDATION_STATUS.md) F6, F8, F11–F13):

- The upstream mock must not limit concurrency: it is a single-threaded asyncio server.
- Saturation experiments run last in a phase, and the suite waits until the backend answers fast again before every run (an overloaded server keeps draining its queue).
- Probes use `127.0.0.1`, not `localhost` (IPv6 fallback costs ~2 s per call on Windows).
- The host must not sleep during a run; `run_http_suite.py` does not prevent standby by itself.
- Verify with `mvn clean …`: incremental compilation once hid a compile error that the Docker build found.

### 2.5 Probes

| Probe | Lab | Procedure | Pass criterion |
|---|---|---|---|
| reservation | 02 | 30 × unsafe, lock and atomic, stock 100 / 200 requests | lock/atomic: 0 incorrect; unsafe: failures are the expected result |
| stampede | 08 | 10 × `single=false/true`, 32 and 100 concurrent requests | `single=true` → exactly 1 load |
| pool | 08 | 5 × 32 and 100 requests, 5 permits, 100 ms wait budget, 30 ms work | peak ≤ 5 |
| DI identity | 06 | two calls per mode | shared: same id; request: different id |
| CPU | 05 | `/lab/cpu/{sequential,parallel?workers=2,4,8}`, count 100000, rounds 500; 5 warm-up + 15 measured calls | all checksums equal; median `elapsedNs` reported |
| `di2` | 06 | captive identity (5 calls per mode); 3 × 200 concurrent `mutable` requests per mode | captured: 1 id; fresh: 5 ids; request-scoped: 0 wrong users |
| `ownership` | 06 | 100 objects per mode; Jakarta also `background` plain / activated | correct mode cleans up all 100 |
| `events` | 07 | 100 direct + 100 event changes concurrently on a fresh product, 20 rollbacks | audit delta = 200, rolled-back price never visible |
| `failure` | 07 | 10 × `failAudit=true` per mode | direct: rolled back; event: committed, audit lost or (outbox) retried |
| `staleness` | 01 | rename product 77, poll until served, 5 samples | ≤ refresh interval (10 s) |
| `pinning` | 04 | 3 warm-up + 10 × 100 virtual threads sleeping 50 ms in a lock | pinned ≈ 1,250 ms, not pinned ≈ 50 ms |
| `redis` | 08 | 5 rounds × 100 requests split over 2 instances per mode | `distributed` → 1 load |
| `redis2` | 08 | stale read before/after invalidation; `docker stop` Redis | fallback to DB; catalogue unaffected |

## 3. How to reproduce

```powershell
# Prerequisites: Docker, JDK 25 (JAVA_HOME!), Maven 3.9+, .NET 10 SDK, Python 3.
$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-25...'      # Maven must run on JDK 25
mvn -B -f implementations/spring-boot/pom.xml verify                 # unit + Testcontainers integration tests

# JMH (about 10 minutes) -> reports/runs/<UTC>/REPORT.md
python tools/run_benchmark.py --suite all --count 100000 --note "CPU; RAM; power mode"

# BenchmarkDotNet; without a .NET 11 SDK restrict the target frameworks:
$env:LabTargetFrameworks='net10.0'
dotnet run -c Release -f net10.0 --project implementations/aspnet-core/Lab.Benchmarks -- --filter '*' --exporters json markdown --artifacts reports/bdn-runs/net10

# HTTP suite -> reports/http-runs/<UTC>/REPORT.md (all phases: several hours; keep the machine awake)
python tools/run_http_suite.py --list
python tools/run_http_suite.py                         # everything
python tools/run_http_suite.py --only v4-,v3-               # subset by phase-id prefix

# Charts (docs/images) from the raw data
python -m pip install matplotlib; python tools/make_charts.py
```

Host ports default to 18080 (Spring), 18081 (Jakarta) and 18082 (.NET) in the suite, to avoid clashes with other local services. For manual runs set `LAB_PORT`, `JAKARTA_PORT` and `DOTNET_PORT`.

## 4. Reading the results

| Metric | Meaning | Pitfall |
|---|---|---|
| JMH ops/s ± error | mean throughput with a 99.9% confidence half-width | a wide error usually means noisy iterations; look at the raw data in the JSON |
| `gc.alloc.rate.norm` | bytes allocated per operation | in `mixed` it averages reader and writer operations |
| `gc.time` | total GC pause time over the measurement | depends on heap and duration; compare only within one run |
| k6 p50 / p95 / p99 / max | latency percentiles of **successful and failed** requests | a single 30 s run; p99 with ~1,500 samples is still noisy |
| achieved rps | completed requests per second | below target rps ⇒ server could not keep up |
| dropped | iterations k6 could not start because all VUs were busy | any non-zero value means the target rate was not sustained |
| failed | share of non-2xx/timeout responses | a fast error is not throughput |
| CPU / Memory | one `docker stats` sample mid-run | a single sample, indicative only (CPU% is relative to one core: 400% = 4 CPUs) |

## 5. Known limits of this setup

- Single workstation (Windows + Docker/WSL VM), unrelated idle containers present. Headline comparisons were repeated 3–5 times (reported as median [min – max]); other rows are single runs. Use the results for **mechanisms and orders of magnitude**, not precise ratios.
- k6 and the mock upstream share the host with the backend. They are not CPU-limited, so they are unlikely to be the bottleneck at these rates, but they do compete for host CPU.
- Cross-framework rows compare these lab implementations, not frameworks in general. The editions differ in JSON libraries, thread pools and code paths (see each lab README).
- The protocol for a publication-quality study (five repetitions, dedicated host, pinned CPU sets) is in [EXPERIMENT_PROTOCOL.md](EXPERIMENT_PROTOCOL.md).
