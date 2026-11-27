# Backend Engineering Lab — Benchmark report

**Final state:** 2026-11-27 · **Scope:** 8 labs × 3 backends (Spring Boot 4.2 / Jakarta EE 11 on WildFly 42 / ASP.NET Core .NET 10 and 11) · **Tools:** JMH 1.37, BenchmarkDotNet 0.15.6, k6 1.3.0, custom probes.

These are **indicative measurements of these lab implementations on one workstation**. They explain mechanisms and orders of magnitude; they are not a framework ranking. Every number below links to its raw data. Methodology: [docs/BENCHMARKS.md](../docs/BENCHMARKS.md). Validation and defects: [docs/VALIDATION_STATUS.md](../docs/VALIDATION_STATUS.md). Unexpected results and how they were resolved: [investigations](investigations/2026-11-27-anomalies.md).

---

## 1. Key findings

| # | Finding | Lab | Evidence (repetitions) |
|---|---|---|---|
| 1 | **Virtual threads remove the blocking-I/O thread ceiling.** 400 req/s of 600 ms blocking calls: platform threads 324 req/s at p50 2.4 s, virtual threads 392 req/s (all requests) at p50 606 ms, 0 errors. Java 17 = Java 25 with platform threads | 04 | §3.4 (5 runs each) |
| 2 | **WildFly's Concurrency 3.1 virtual executor works, but only with `maxAsync` set:** without it, a semaphore in the implementation capped concurrency (100 % timeouts); with it, 392 req/s at p50 606 ms | 04 | §3.4 (3 runs), investigation 3 |
| 3 | **JDK 21 pins virtual threads in `synchronized`** (1,254 ms vs theory 1,250 ms); JDK 25 does not (51 ms) | 04 | §3.4 (10 runs) |
| 4 | **.NET sync-over-async starves the ThreadPool on a cold start** (up to 100 % failures at 0.9–3 % CPU) and survives once the pool has grown; async code never failed | 03, 04 | §3.3–3.4, investigation 4 |
| 5 | **Concurrent fan-out halves latency** (303 ms vs 605 ms) on all stacks; async alone does not | 03 | §3.3 (5 runs) |
| 6 | **Snapshot cache: fastest reads (88 M/s, 19× a global lock), most expensive writes** (33 batches/s) | 01 | §3.1 (JMH) |
| 7 | **Unsafe check-then-act oversold in 11–29 of 30 runs**; lock/CAS 0 of 180. CAS 6× faster than `lock` in .NET, equal in Java | 02 | §3.2 |
| 8 | **Singletons holding request state returned the wrong user in 95–98 % of concurrent responses** on all three frameworks; captive dependencies and wrong ownership verified in each framework's own idiom | 06 | §3.6 |
| 9 | **After-commit side effects are not durable:** a failing handler lost 10/10 audits in Spring and Jakarta; the .NET outbox delivered 10/10 after retries. A shared executor delayed Jakarta audits by ~130 s | 07 | §3.7 |
| 10 | **Spring `AFTER_COMMIT` + `REQUIRES_NEW` deadlocks the Hikari pool** (100 % failures); the same pattern did not deadlock on WildFly/JTA | 07 | §3.7 |
| 11 | **Hot-row contention:** keeping the audit in the price transaction collapses Spring at 200 req/s (p50 1.6–8.7 s across 5 runs); moving it after commit gives p50 2.7 ms. The outbox keeps the transaction long (p50 658 ms) | 07 | §3.7 |
| 12 | **Pools behave as Little's law predicts:** pool 5 × 30 ms ≈ 160 successful req/s in all three editions; they differ in failure mode (fail fast vs queue) | 08 | §3.8 |
| 13 | **Stampede size = effective concurrency** (8 / 32 / 100 loads); single-flight → 1; across 2 instances local single-flight → 2, Redis lock → 1 | 08 | §3.8 |

## 2. Environment and method

| Item | Value |
|---|---|
| Host | Intel Core i7-13700H (6 P + 8 E cores, 20 threads), 32 GB RAM, Windows 11 Pro 26300 |
| Containers | Docker 29.5 (Rancher Desktop, WSL2). Backend limited to `cpus: 4`, `mem_limit: 2g` unless stated. Unrelated idle containers of another project were running |
| Java | Temurin 25.0.4.1 (host JMH); images 25.0.5.1, 21.0.13.1, 17.0.21.1 (Spring), 25.0.4.1 (WildFly 42) |
| .NET | 10.0.15 (host BDN, image), 11.0.0 (image) |
| Data | 100,000 products; `snapshot` cache and `journal` sync unless stated |
| Upstream mock | asyncio, 100 / 200 / 300 ms, HTTP/1.1 keep-alive (final version; see F6/F8) |
| Load | k6 `constant-arrival-rate` in a container on the Compose network; warm-up 10 s (30 s at ≥ 1,000 req/s), measured 30 s; the suite waits until the backend has drained before each run; up to 5 repetitions |
| Metadata | each run's `environment.json` records the git commit, dirty files, image IDs, workload and repetitions |

### Raw data and which run supersedes which

| Data set | Content | Status |
|---|---|---|
| [runs/20261126T194918342533Z](runs/20261126T194918342533Z/REPORT.md) | JMH cache + engineering kernels | valid |
| [bdn-runs/net10](bdn-runs/net10/results/) | BenchmarkDotNet CPU + reservation | valid |
| [http-runs/20261126T202650Z](http-runs/20261126T202650Z/REPORT.md) | run 1: Spring variants (cache strategies, Java 17, virtual, event-inline) | valid for those rows; its Jakarta/.NET rows were harness-contaminated (queue spill-over, Nagle, short warm-up) |
| [http-runs/20261126T222721Z](http-runs/20261126T222721Z/REPORT.md) | run 2: baselines for all editions, .NET 11, CPU quotas, correctness probes | valid; I/O rows superseded by v4 |
| [http-runs/20261127T003011Z](http-runs/20261127T003011Z/REPORT.md) | v2: Spring 5× repetitions | valid except `io-blocking-400rps` (threaded mock, **superseded** by v4) |
| [http-runs/20261127T011057Z](http-runs/20261127T011057Z/REPORT.md) | v2/v3: Jakarta/.NET repetitions, DB pools, events, DI, pinning, Redis, ownership, failure, staleness | valid except `io-blocking-async-*` rows (superseded) |
| [http-runs/20261127T021849Z](http-runs/20261127T021849Z/REPORT.md) | v4: Spring Java 25 platform/virtual I/O (asyncio mock) | valid; run stopped later by host standby |
| [http-runs/20261127T063929Z](http-runs/20261127T063929Z/REPORT.md) | v4: Java 17, Jakarta I/O, .NET 10/11 I/O | valid except the Jakarta saturation phase (before F9) |
| [http-runs/20261127T074359Z](http-runs/20261127T074359Z/REPORT.md) | v4: Jakarta saturation after F9 | valid |

---

## 3. Results by lab

### 3.1 Lab 01 — product cache ([details](../labs/01-product-cache/README.md))

| Strategy (JMH, 100K) | read-only ops/s | mixed: reader ops/s | mixed: writer batches/s |
|---|---:|---:|---:|
| synchronized | 4.61 M ± 0.46 M | 1.49 M | 902 K |
| concurrent | 62.8 M ± 4.8 M | 34.3 M | 615 K |
| **snapshot** | **88.1 M ± 7.2 M** | **43.0 M** | **33.4** |
| caffeine | 48.0 M ± 17.3 M | 43.2 M | 626 K |

| HTTP `catalog-get` 2,000 req/s, 5 runs | achieved req/s | p50 ms | p99 ms |
|---|---|---|---|
| Spring Boot | 1,999.9 [1,974 – 1,999.9] | 0.62 [0.48 – 0.79] | 5.2 [1.5 – 104.9] |
| Jakarta EE | 1,987.5 [1,532 – 1,993] | 1.65 [1.43 – 562.9] | 218 [106 – 1,131] |
| ASP.NET Core | 1,999.9 [1,989 – 2,000] | 0.93 [0.81 – 0.94] | 35.5 [21.4 – 54.4] |

Paging (50 req/s): Spring p50 6.2 ms, Jakarta 8.5 ms, .NET 47.4 ms (261 % CPU). Staleness with a 10 s journal refresh: 3.2–8.3 s, median 4.9–5.4 s on all editions.

### 3.2 Lab 02 — concurrency ([details](../labs/02-concurrency/README.md))

| Edition | unsafe wrong runs | lock / atomic wrong | kernel atomic vs lock |
|---|---:|---|---|
| Spring Boot | 21 / 30 | 0 / 0 | JMH: 0.81 vs 0.86 ms |
| Jakarta EE | 29 / 30 | 0 / 0 | (same Java kernel) |
| ASP.NET Core | 11 / 30 | 0 / 0 | BDN: 0.167 vs 1.039 ms |

### 3.3 Lab 03 — async I/O, 50 req/s, 5 runs, p50 ms ([details](../labs/03-async-io/README.md))

| Edition | blocking | sequential-async | concurrent |
|---|---|---|---|
| Spring Boot | 605.8 [605.7 – 607.1] | 605.6 [605.5 – 605.8] | 303.1 [302.7 – 303.4] |
| Jakarta EE | 606.8 [605.8 – 607.6] | 605.8 [605.3 – 607.1] | 303.0 [303.0 – 303.0] |
| ASP.NET Core 10 | sync-over-async: run 1 84.6 % failed; runs 2–5 604.5 | 604.1 [604.1 – 604.2] | 302.0 [302.0 – 302.1] |

### 3.4 Lab 04 — threads and runtimes, 400 req/s ([details](../labs/04-virtual-threads/README.md))

| Configuration | achieved req/s | p50 | failed | runs |
|---|---|---|---|---|
| Spring, Java 17, platform | 324.2 [319.5 – 324.6] | 2,434 ms | 0 % | 5 |
| Spring, Java 25, platform | 324.2 [323.9 – 324.3] | 2,431 ms | 0 % | 5 |
| **Spring, Java 25, virtual** | **392.1 [391.8 – 392.1]** | **606 ms** | 0 % | 5 |
| WildFly, Undertow worker | 213.4 (≈ 40 successful) | 10 s timeout | 81 % | 3 |
| WildFly, default managed executor | 204.8 (0 successful) | 10 s | 100 % | 3 |
| **WildFly, virtual managed executor (`maxAsync=2000`)** | **392.1 [392.0 – 392.1]** | **606 ms** | 0 % | 3 |
| .NET 10 / 11, sync-over-async | run 1: 100 % failed; run 3: 392 req/s, 0 % | – | bistable | 3 each |

Pinning (100 tasks × 50 ms, 4 carriers): JDK 21 `synchronized` 1,254.5 ms, `ReentrantLock` 50 ms; JDK 25 51 / 50 ms.

### 3.5 Lab 05 — CPU ([details](../labs/05-cpu-parallelism/README.md))

Host: JMH 22.4 → 5.6 ms (4.0×) and BDN 27.5 → 5.3 ms (5.2×) from 1 to 8 workers. Docker quota (median of 3 editions, best configuration): 1 CPU ≤ 1.2×, 2 CPUs ≈ 2× with 2 workers, 4 CPUs ≈ 4.2× with 8 workers, 8 CPUs ≈ 4.6×. Checksum identical in all 13 configurations and both runtimes.

### 3.6 Lab 06 — dependency injection ([details](../labs/06-dependency-injection/README.md))

| Check | Spring | Jakarta | .NET |
|---|---|---|---|
| singleton "current user": wrong / 600 | 586 | 568 | 582 |
| request-scoped: wrong / 600 | 0 | 0 | 0 |
| captive: distinct ids in 5 calls (captured / fresh) | 1 / 5 | 1 / 5 | 1 / 5 |
| ownership: cleaned up of 100 (wrong / right) | 0 / 100 | 0 / 100 | 0 / 100 |
| request scope in background task | – | `ContextNotActiveException` / ok with `@ActivateRequestContext` | – |
| CPU per-request payload vs singleton (50 req/s) | 20 % / 6 % | 64 % / 8 % | 62 % / 4 % |

### 3.7 Lab 07 — events ([details](../labs/07-domain-events/README.md))

| Edition / mode (200 req/s, one row) | achieved req/s | p50 | failed |
|---|---|---|---|
| Spring direct (5 runs) | 129.8 [93.2 – 143.3] | 5,172 ms [1,564 – 8,658] | 0 [0 – 24.8] % |
| Spring event (5 runs) | 200.0 | 2.73 ms [1.95 – 3.20] | 0 % |
| Spring event-inline | 67.8 | timeouts | 100 % |
| Jakarta direct / event / event-inline | 200 / 200 / 200 | 14.5 / 3.0 / 7.7 ms | 0 % |
| .NET direct / event (outbox) | 178.1 / 190.9 | 1,676 / 658 ms | 0 % |

Correctness: 200/200 audits and 0 visible rollbacks (Spring, .NET; Jakarta in isolation). Handler failure: Spring/Jakarta event 0/10 audits (lost), .NET outbox 10/10.

### 3.8 Lab 08 — resources ([details](../labs/08-resource-management/README.md))

| Real pool (successful req/s) | pool 5 @ 100 | pool 5 @ 300 | pool 20 @ 300 |
|---|---:|---:|---:|
| Spring (Hikari, 1 s) | 99.9 | 162 (23 % 503, p50 3.5 s) | 299.7 |
| Jakarta (WildFly, 30 s) | 99.9 | 162 (0 % failed, p50 6.1 s) | 299.7 |
| .NET (MySqlConnector, 1 s) | 99.9 | 158 (44 % 503, p50 1.0 s) | 299.7 |

Stampede, 100 requests: in-process 32 / 8 / 100 loads without coordination, 1 with single-flight. Redis, 2 instances: `none` 50–100, `local` 2, `distributed` 1. Redis hit p50 1.00 ms vs in-process 0.54 ms; stale read across instances until invalidation; Redis down → DB fallback after 511 ms.

---

## 4. Status of explanations

Every result above is a **measured observation**. This table classifies the *explanations* given in the lab documents.

| Finding | Status | Basis |
|---|---|---|
| Threaded mock upstream made virtual threads look slower (F8) | **confirmed root cause** | A/B tests: old and new app code identical; asyncio mock removes the effect ([investigation 1](investigations/2026-11-27-anomalies.md)) |
| WildFly virtual executor capped by a semaphore (F9) | **confirmed root cause** | thread dump of 346 virtual threads in `VirtualThreadsManagedFutureTask`; `maxAsync` fixes it |
| Hikari deadlock with `AFTER_COMMIT` + `REQUIRES_NEW` (F4) | **confirmed root cause** | thread dump `active=10, waiting=198`; async listener fixes it |
| JAX-RS routing hid stampede/pool on Jakarta (F14) | **confirmed root cause** | 404 reproduced, fixed, re-verified from a fresh clone |
| JDK 21 pinning in `synchronized`, removed in JDK 24+ | **confirmed** | measured 1,254.5 ms vs theory 1,250 ms; 51 ms on JDK 25 |
| Jakarta after-commit audits delayed by a shared executor | **confirmed** (delay) | controlled test: 0 audits for 120 s, all 100 at 130 s |
| … and lost when the process stops | **consistent with the design, not directly observed** | audits missing after the container was stopped; in-memory queue |
| .NET sync-over-async bistable because the ThreadPool keeps injected threads | **hypothesis** | run order pattern (run 1 fails, later runs pass); not traced in the runtime |
| Hot-row collapse caused by row-lock hold time | **hypothesis** (well supported) | same SQL in both modes, only lock hold time differs; InnoDB lock waits not monitored |
| 8 workers beat 4 under a 4-CPU quota because the quota is time, not cores | **hypothesis** | CFS semantics; `cpu.stat` not captured for those runs |
| .NET per-request payload p95 caused by LOH / gen-2 GCs | **hypothesis** | GC design; no GC log captured |
| WildFly default executor size ≈ 2 × CPUs | **observation** | 8 tasks at 4 CPUs, 40 at 20 CPUs; default not read from the source |
| Inline after-commit pattern does not deadlock on WildFly | **hypothesis** | JTA connection handling; not verified in WildFly code |
| Jakarta `direct` handles the hot row better than Spring and .NET | **unresolved** | measured once (p50 14.5 ms) |
| Why run 1 virtual threads were not affected by the threaded mock | **unresolved** | – |
| WildFly needs more CPU per catalogue request | **unresolved** | not profiled |
| .NET client-span count 17 instead of 15 | **unresolved** | – |
## 5. Defects found by benchmarking

Benchmarks and probes found defects that unit tests had missed. All are fixed and listed in [VALIDATION_STATUS.md](../docs/VALIDATION_STATUS.md): the Hikari deadlock (F4), CDI proxy defects (F2, F3), the bounded WildFly virtual executor (F9), a JAX-RS routing defect found by the clean-checkout test (F14), and harness defects that would otherwise have been reported as backend results (F6 Nagle, F8 threaded mock, suite spill-over, IPv6 `localhost` delays, host standby).

## 6. Limitations

- One workstation; up to 5 repetitions per configuration; single `docker stats` CPU samples. Treat differences below ~20 % as noise unless a repetition range shows otherwise.
- Docker CPU quotas on a hybrid-core laptop are not pinned cores. k6, the mock and MySQL share the host.
- Cross-framework rows compare these implementations (different JSON stacks, pools and code paths), not the frameworks in general.
- Open, unexplained observations: Jakarta `direct` handling the hot row better than Spring and .NET; why run 1's virtual-thread result was not affected by the threaded mock; WildFly's higher CPU per catalogue request.
- Not measured: agent/SDK overhead, Redis cluster behaviour, Jakarta/.NET Redis, more than one outbox dispatcher.
