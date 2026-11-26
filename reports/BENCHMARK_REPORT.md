# Backend Engineering Lab — Benchmark report

**Date:** 2026-11-26 · **Scope:** 8 labs × 3 backends (Spring Boot 4.2 / Jakarta EE 11 on WildFly 42 / ASP.NET Core) · **Tools:** JMH 1.37, BenchmarkDotNet 0.15.6, k6 1.3.0
**Status:** all builds, unit/integration tests and HTTP contract smoke tests passed before measurement ([validation](../docs/VALIDATION_STATUS.md)).

These are **indicative** measurements of these lab implementations on one workstation, mostly one run per configuration. They show mechanisms and orders of magnitude, not a universal framework ranking. Methodology: [docs/BENCHMARKS.md](../docs/BENCHMARKS.md).

---

## 1. Key findings

| # | Finding | Lab | Evidence |
|---|---|---|---|
| 1 | **Virtual threads remove the blocking-I/O ceiling.** At 400 req/s of 600 ms blocking calls: platform Tomcat 268–322 req/s with p50 2.5–4.5 s; virtual threads 392 req/s at p50 605 ms, 0 dropped. Java 17 vs 25 with platform threads: identical | 04 | §3.4 |
| 2 | **.NET sync-over-async starves the ThreadPool**: 100% timeouts at only 50 req/s, with **1.5% CPU**. The same code with `await` is healthy | 03, 04 | §3.3 |
| 3 | **Concurrent fan-out halves latency** (303 ms vs 605 ms) on all stacks; async alone doesn't change single-request latency | 03 | §3.3 |
| 4 | **Snapshot cache: fastest reads, most expensive writes.** 88 M reads/s (19× a global lock), but only 33 batches/s and 2.2 s of GC under continuous writes | 01 | §3.1 |
| 5 | **The unsafe reservation oversold in 11–29 of 30 runs** (up to 185 of 100 units). Lock and CAS: 0 failures in 180 runs. CAS is 6× faster than lock in .NET; in Java task overhead hides the difference | 02 | §3.2 |
| 6 | **Connection-pool deadlock** in a common Spring pattern: an AFTER_COMMIT listener with `REQUIRES_NEW` on the request thread → `active=10, idle=0, waiting=198`, 100% failures, the whole app frozen. Fixed by an async listener | 07 | §3.7 |
| 7 | **Hot-row contention:** keeping the audit insert inside the price transaction caps a single-row workload at ~150–200 tx/s (p50 up to 3.9 s). Moving it after commit: p99 6.5 ms | 07 | §3.7 |
| 8 | **Stampede size = effective concurrency**: without single-flight 8 (WildFly executor), 32 (Spring pool) or 100 (.NET async) loads; with single-flight always 1 | 08 | §3.8 |
| 9 | **CPU quota is time, not cores:** at `cpus: 4`, 8 workers still beat 4 workers for a 27 ms burst; at 1 CPU parallelism gives ≤ 1.2× | 05 | §3.5 |
| 10 | **Per-request heavy objects** cost 3–15× CPU; on .NET an 800 KB array per request hits the LOH and lifts p95 to 43 ms | 06 | §3.6 |
| 11 | **WildFly request path** costs ≈ 3.7 ms CPU per catalogue read (vs ≈ 0.44 ms on Spring): it saturates 4 CPUs at ~1,200 req/s and needs > 30 s of JIT warm-up | 01 | §3.1 |

## 2. Environment and method

| Item | Value |
|---|---|
| Host | Intel Core i7-13700H (6P + 8E cores, 20 threads), 32 GB RAM, Windows 11 Pro 26300 |
| Containers | Docker 29.5 (Rancher Desktop, WSL2 VM). Backend limited to `cpus: 4`, `mem_limit: 2g` unless stated |
| Java | Temurin 25.0.4.1 (host JMH), 25.0.5.1 / 17.0.21.1 (Spring images), 25.0.4.1 (WildFly 42 image) |
| .NET | 10.0.15 (host BDN and image), 11.0.0 (image) |
| Data | 100,000 products, same seed, `snapshot` cache and `journal` sync unless stated |
| Upstream | Python mock, 100 / 200 / 300 ms fixed delays, HTTP/1.1 keep-alive, TCP_NODELAY |
| Load | k6 `constant-arrival-rate`, k6 in a container on the Compose network, warm-up 10 s (30 s for ≥ 1,000 req/s), measured 30 s |
| Isolation | one backend running at a time; unrelated idle containers of another project were present on the host |

Raw data:

| Data set | Location |
|---|---|
| JMH (cache + engineering) | [runs/20261126T194918342533Z](runs/20261126T194918342533Z/REPORT.md) |
| BenchmarkDotNet (.NET 10) | [bdn-runs/net10/results](bdn-runs/net10/results/) |
| k6 run 1: Spring variants (virtual, Java 17, cache strategies, event-inline) | [http-runs/20261126T202650Z](http-runs/20261126T202650Z/REPORT.md) |
| k6 run 2: baselines for all three editions, .NET 11, CPU quotas (improved harness) | [http-runs/20261126T222721Z](http-runs/20261126T222721Z/REPORT.md) |

Run 1 is used only for the Spring variant phases. Its Jakarta/.NET rows are superseded by run 2. In run 1, those phases suffered from harness problems that were fixed before run 2: queue spill-over after the saturation test, Nagle delay in the mock, and too short a JIT warm-up for WildFly.

---

## 3. Results by lab

### 3.1 Lab 01 — Product cache

**JMH, 100K products** ([details](../labs/01-product-cache/README.md#7-measured-results))

| Strategy | read-only, 4 threads (ops/s) | mixed: reader ops/s | mixed: writer batches/s | consistency |
|---|---:|---:|---:|---|
| synchronized | 4.62 M ± 0.46 M | 1.49 M | 902 K | atomic pages |
| concurrent | 62.8 M ± 4.8 M | 34.3 M | 615 K | per key |
| **snapshot** | **88.1 M ± 7.2 M** | **43.0 M** | **33.4** | atomic pages |
| caffeine | 48.0 M ± 17.3 M (noisy) | 43.2 M | 626 K | per key |

**HTTP, same snapshot strategy, 4 CPUs (run 2)**

| Edition | `catalog-get` 2,000/s achieved | p50 / p95 / p99 (ms) | CPU | `catalog-page` 50/s p50 / p99 (ms) | page CPU | memory |
|---|---:|---|---:|---|---:|---:|
| Spring Boot (Java 25) | 1,999.8 | 0.69 / 1.62 / 8.07 | 89% | 6.2 / 12.1 | 45% | ~450–550 MiB |
| Jakarta EE (WildFly 42) | **1,206.6** (23,135 dropped) | 754 / 1,187 / 1,501 | **453%** | 8.5 / 15.0 | 49% | ~630 MiB |
| ASP.NET Core (.NET 10) | 1,999.9 | 1.00 / 9.38 / 37.8 | 171% | **47.4 / 97.6** | **261%** | ~90–330 MiB |
| ASP.NET Core (.NET 11) | 1,999.9 | 0.93 / 17.5 / 48.1 | 164% | – | – | ~110–160 MiB |

Strategy comparison over HTTP (Spring, run 1): single-key reads are dominated by HTTP overhead, so the strategies are indistinguishable within noise. `synchronized` serializes page requests: p99 121 ms vs 16–20 ms for the others.

Notes: .NET pages copy an `ImmutableDictionary` (a tree) to an array on every request before sorting, which costs 5× Java's page CPU. WildFly needs a long JIT warm-up. In a separate warmed-up sweep it held 1,000 req/s at p50 1.4 ms and 2,000 req/s at p50 29 ms / p99 363 ms; under the suite's warm-up it saturated. The root cause of its higher CPU per request was not profiled ([ROADMAP](../docs/ROADMAP.md)).

### 3.2 Lab 02 — Concurrency and stock reservation ([details](../labs/02-concurrency/README.md))

| Edition | unsafe: incorrect of 30 | max accepted (stock 100) | lock / atomic incorrect | HTTP 50 exp/s atomic p50 / p99 (ms) | lock p50 / p99 (ms) |
|---|---:|---:|---|---|---|
| Spring Boot | 21 | 150 | 0 / 0 | 1.62 / 3.53 | 1.75 / 3.28 |
| Jakarta EE | 29 | 144 | 0 / 0 | 4.15 / 8.34 | 4.35 / 8.68 |
| ASP.NET Core | 11 | 185 | 0 / 0 | 0.87 / 1.85 | 0.93 / 2.33 |

| Kernel (stock 1,000, 2,000 attempts) | atomic | lock |
|---|---:|---:|
| JMH, Java 25 (32-thread pool) | 0.81 ± 0.11 ms | 0.86 ± 0.10 ms |
| BDN, .NET 10 (`Parallel.For`) | 0.167 ± 0.005 ms | 1.039 ± 0.028 ms |

### 3.3 Lab 03 — Async I/O, 50 req/s ([details](../labs/03-async-io/README.md))

| Edition | blocking p50 / p99 | sequential-async p50 / p99 | concurrent p50 / p99 |
|---|---|---|---|
| Spring Boot | 605.9 / 612.9 | 604.8 / 607.7 | 302.9 / 305.2 |
| Jakarta EE | 606.0 / 610.5 | 605.5 / 609.0 | 303.4 / 305.9 |
| ASP.NET Core | **100% timeout** (sync-over-async, CPU 1.5%) | 603.7 / 607.0 | 302.5 / 304.5 |

Theory: 600 ms sequential, 300 ms concurrent. All latencies in ms.

### 3.4 Lab 04 — Thread models at 400 req/s blocking I/O ([details](../labs/04-virtual-threads/README.md))

| Configuration | achieved req/s | p50 (ms) | p99 (ms) | dropped | failed | run |
|---|---:|---:|---:|---:|---:|---|
| Spring, Java 25, platform | 268.1 | 4,499 | 8,002 | 1,810 | 0% | 1 |
| Spring, Java 25, platform (repeat) | 322.4 | 2,507 | 4,115 | 1,016 | 0% | 2 |
| Spring, Java 17, platform | 267.5 | 4,484 | 7,995 | 1,837 | 0% | 1 |
| **Spring, Java 25, virtual** | **392.1** | **605** | **624** | **0** | 0% | 1 |
| Jakarta, WildFly (64 workers) | 210.0 | 10,000 | 10,001 | 3,599 | 88% | 2 |
| .NET 10 (sync-over-async) | 204.1 | – | 10,001 | 3,837 | 100% | 2 |
| .NET 11 (sync-over-async) | 204.4 | 2,854 | 10,001 | 3,823 | 100% | 2 |

Theoretical ceilings (threads / 0.6 s): Tomcat 200 → 333 req/s; WildFly 64 → 107 req/s.

### 3.5 Lab 05 — CPU parallelism ([details](../labs/05-cpu-parallelism/README.md))

Host microbenchmarks (rounds = 100): JMH 22.4 → 13.3 → 7.3 → 5.6 ms for 1/2/4/8 workers (4.0×); BDN 27.5 → 14.2 → 8.7 → 5.3 ms (5.2×).

Containers, server-side median ms (rounds = 500):

| Quota | Spring seq → best | Jakarta seq → best | .NET 10 seq → best |
|---:|---|---|---|
| 1 CPU | 122 → 103 (4 w) | 128 → 109 (4 w) | 126 → 108 (2 w) |
| 2 CPU | 126 → 64 (2 w) | 168 → 68 (2 w) | 143 → 77 (2 w) |
| 4 CPU | 114 → 27 (8 w) | 114 → 27 (8 w) | 122 → 25 (8 w) |
| 8 CPU | 132 → 29 (8 w) | 131 → 36 (8 w) | 159 → 27 (8 w) |

Checksum `-980176603291609351` identical in all 13 configurations, Java and .NET.

### 3.6 Lab 06 — DI lifetimes, 50 req/s ([details](../labs/06-dependency-injection/README.md))

| Edition | request-scoped p50 / p95 / p99 (ms) | shared p50 / p95 / p99 (ms) | CPU request / shared |
|---|---|---|---|
| Spring Boot | 2.65 / 6.65 / 8.38 | 1.60 / 2.62 / 2.99 | 20% / 6% |
| Jakarta EE | 3.60 / 8.28 / 12.44 | 1.59 / 2.14 / 2.72 | 64% / 8% |
| ASP.NET Core | 5.77 / 42.98 / 61.98 | 0.79 / 1.48 / 2.16 | 62% / 4% |

Identity probe: shared → same id, request → new id, on all three editions.

### 3.7 Lab 07 — Domain events, 200 req/s on one product row ([details](../labs/07-domain-events/README.md))

| Edition / mode | achieved req/s | p50 | p95 | p99 | failed |
|---|---:|---:|---:|---:|---:|
| Spring `direct` (run 2) | 152.1 | 3,948 | 4,599 | 4,630 | 0% |
| Spring `direct` (run 1) | 199.6 | 36.6 | 221.9 | 273.0 | 0% |
| Spring `event` (async after commit, run 2) | 200.0 | 2.73 | 4.41 | 6.48 | 0% |
| Spring `event-inline` (negative example, run 1) | 67.8 | 10,000 | 10,001 | 10,001 | **100%** |
| Jakarta `direct` / `event` (in-memory) | 200 / 200 | 1.52 / 2.41 | 2.32 / 4.65 | 3.07 / 10.0 | 0% |
| .NET `direct` / `event` (in-memory) | 200 / 200 | 0.86 / 0.79 | 1.51 / 1.31 | 1.92 / 1.63 | 0% |

### 3.8 Lab 08 — Stampede and capacity ([details](../labs/08-resource-management/README.md))

| Edition | loads without single-flight (N = 32 / 100) | with single-flight | pool N = 32: peak / rejected | N = 100: peak / rejected |
|---|---|---|---|---|
| Spring Boot | 32 / 32 | 1 / 1 | 5 / 12 | 5 / 51–53 |
| Jakarta EE | 8 / 8 | 1 / 1 | 5 / 0–3 | 5 / 4–8 |
| ASP.NET Core | 32 / 100 | 1 / 1 | 5 / 12 | 5 / 80 |

---

## 4. Defects found by benchmarking

Running the benchmarks surfaced defects that the unit tests had not found. All are fixed and listed in [VALIDATION_STATUS.md](../docs/VALIDATION_STATUS.md):

- Spring connection-pool deadlock under concurrent domain events (F4). Kept as the documented negative mode `event-inline`.
- Jakarta CDI deployment failure (F2) and wrong state read through CDI proxies (F3).
- JMH build configuration clash with the Spring Boot parent (F1); .NET 11 multi-targeting breaking BenchmarkDotNet (F5).
- Benchmark harness: mock upstream backlog and Nagle delay (F6); saturation spill-over between experiments, insufficient JIT warm-up, and Windows `localhost` → IPv6 fallback delays in the orchestrator. All fixed in [`tools/run_http_suite.py`](../tools/run_http_suite.py).

## 5. Limitations

- One workstation, mostly one run per configuration. The two repeated Spring baselines differ by up to 2× near saturation (Lab 04, Lab 07), and CPU timings show ±20% noise. Treat differences under ~20% as noise.
- Docker CPU quotas on a hybrid-core laptop are not pinned cores. k6 and the mock share the host with the backend.
- Container CPU/memory figures are a single `docker stats` sample per run.
- Cross-framework rows compare these lab implementations (different JSON stacks, thread pools and code paths), not the frameworks in general.
- Not measured: Redis, the observability stack, and the advanced variants listed in [ROADMAP.md](../docs/ROADMAP.md).
