# Investigations of unexpected results (2026-11-27)

Both investigations were run interactively, outside `run_http_suite.py`, with no other lab backend running. Commands are reproduced so the tests can be repeated. The console output below is the raw record; there is no other raw file.

## 1. Virtual threads slower than platform threads at 400 req/s (Lab 04)

**Symptom.** Run 1 ([20261126T202650Z](../http-runs/20261126T202650Z/REPORT.md)): Spring / Java 25 / virtual threads reached 392 req/s at p50 605 ms on `io-blocking-400rps`. The 5× repetition ([20261127T003011Z](../http-runs/20261127T003011Z/REPORT.md)) gave 260 req/s [212 – 282], p50 4.4 s, **28 % failed**, worse than platform threads (320 req/s, 0 % failed).

**Observations during a reproduction** (same compose setup, 4 CPUs, k6 400 req/s):

| Sample | app CPU | mock-api CPU | mock-api PIDs |
|---|---:|---:|---:|
| t = 4 s | 410 % | 419 % | 1,029 |
| t = 12 s | 464 % | 1,039 % | 1,309 |
| t = 20 s | 420 % | 807 % | 1,289 |

A thread dump of the app showed 378 `HttpClient-…-Worker` platform threads (JDK `HttpClient`'s internal executor) and saturated carrier threads.

**A/B tests** (warm-up 15 s, then 30 s measured; k6 400 req/s on `/lab/io/blocking`, virtual threads):

| App image | Upstream mock | achieved req/s | p50 | failed |
|---|---|---:|---:|---:|
| code of commit `01799f5` (state of run 1) | threaded, TCP_NODELAY | 246.7 / 279.5 | 5.02 s / 3.05 s | 30.4 % / 27.5 % |
| current code | threaded, TCP_NODELAY | 251.0 / 277.1 | 5.01 s / 2.17 s | 32.7 % / 31.8 % |
| current code | threaded, **without** TCP_NODELAY | 214.9 / 288.4 | 5.22 s / 2.31 s | 42.1 % / 31.5 % |
| current code | **asyncio, single thread** | **392.1 / 392.1** | **609.7 ms / 607.1 ms** | **0 % / 0 %** |

Direct k6 test of the threaded mock (`/product`, 100 ms): 1,194 req/s at p50 100.7 ms. k6 uses ~120 keep-alive connections, so the mock looks healthy in isolation.

**Conclusion.** Not a backend regression: old and new application code behave the same. The upstream mock (`ThreadingHTTPServer`) creates one OS thread per open keep-alive connection. A virtual-thread client keeps hundreds of connections open, and the mock grew to more than 3,000 Python threads; GIL contention made it slow, the backend hit its 5 s upstream timeout and returned errors. Platform threads cap concurrency at 200 and therefore protected the mock. Why run 1 was not affected is not explained. Most likely the number of concurrent connections stayed under the contention threshold in that run, but that was not verified.

**Action.** The mock was rewritten as a single-threaded asyncio server (F8 in [VALIDATION_STATUS.md](../../docs/VALIDATION_STATUS.md)), and every experiment that calls it under load was rerun (`v4-*` phases). The v2 rows for `io-blocking-400rps` and `io-blocking-async-*` are superseded and must not be quoted.

## 2. Jakarta: 100 of 200 audits missing in the events probe (Lab 07)

**Symptom.** Phase `v2-new-jakarta` ([20261127T011057Z](../http-runs/20261127T011057Z/REPORT.md)): 200 committed changes (100 `direct`, 100 `event`), but only 100 audit rows; rollbacks were correct. The probe ran directly after `io-blocking-async-default-400rps`, which floods the same `java:comp/DefaultManagedExecutorService` that executes the after-commit audit.

**Controlled test** (Jakarta kept running throughout; 100 concurrent `event` changes on a fresh product; audit count polled):

| Case | timeline of audit rows (seconds after the changes → count) |
|---|---|
| A: no other load | 0 s → 44, 1 s → **100** |
| B: k6 400 req/s on `/lab/io/blocking-async?executor=default` started 8 s earlier | 0 … 120 s → **0**, 130 s → **100** |

**Conclusion.** The audits are **delayed, not lost**, while the server keeps running. They wait in the in-memory queue of the shared default executor behind thousands of blocking tasks. In the suite the Jakarta container was stopped seconds after the probe, and queued tasks died with the process. Two properties of the after-commit-via-executor design are therefore measured:

1. latency coupling: unrelated work on the same executor delayed the audit by about two minutes;
2. no durability: work queued in memory is lost on shutdown or crash.

The .NET transactional outbox does not have the second property (failed handlers were retried and all 10 audits arrived, `v3-dotnet10`). A dedicated executor for the audit would remove the first property but not the second.

## 3. WildFly managed virtual-thread executor: 100 % timeouts at 400 req/s (Lab 04)

**Symptom.** Phase `v4-rep3-jakarta-saturation` ([20261127T063929Z](../http-runs/20261127T063929Z/REPORT.md)): `/lab/io/blocking-async?executor=virtual` failed 100 % in all three runs, exactly like the platform default executor, although single calls had run on real virtual threads (`VirtualThread[#270]/runnable@ForkJoinPool-1-worker-1`).

**Rate sweep** (15 s each): virtual executor 20 req/s → p50 4.41 s, 0 % failed (latency already growing); 50 req/s → 65 % failed; 100 req/s → 85 % failed. The default executor behaved identically (20 req/s → p50 4.44 s; 50 req/s → 65 % failed). Both executors were limited to roughly 10 concurrent tasks.

**Thread dump including virtual threads** (`jcmd <pid> Thread.dump_to_file`, 50 req/s): 2,843 virtual threads, 346 of them parked on the same `java.util.concurrent.Semaphore$FairSync`, in

```
org.glassfish.concurro.virtualthreads.VirtualThreadsManagedFutureTask.acquireIfNotNull(VirtualThreadsManagedFutureTask.java:110)
org.glassfish.concurro.virtualthreads.VirtualThreadsManagedFutureTask.runPooled(VirtualThreadsManagedFutureTask.java:72)
```

**Conclusion.** WildFly's Jakarta Concurrency implementation (Concurro) bounds the number of concurrently running tasks of a virtual managed executor with a semaphore sized from `maxAsync`. With `maxAsync` left at its default in `@ManagedExecutorDefinition`, only a few tasks ran at a time; the virtual threads were created and then queued at the semaphore. **Fix:** `@ManagedExecutorDefinition(..., virtual = true, maxAsync = 2000)` (F9). Retest: 50 req/s → p50 609.8 ms, 0 % failed; 400 req/s → 385.8 req/s, p50 683 ms, 0 % failed. The phase was rerun. The exact default value was not looked up in the Concurro source; the measured behaviour is what matters for the lab.

## 4. .NET sync-over-async: bistable, not always failing (Labs 03/04)

**Observation** (phases `v4-rep5-dotnet10`, `v4-rep3-dotnet-saturation`, `v4-dotnet11-saturation`, [20261127T063929Z](../http-runs/20261127T063929Z/REPORT.md)), per run in execution order:

| Experiment | run 1 | run 2 | run 3 | runs 4–5 |
|---|---|---|---|---|
| .NET 10, 50 req/s | 84.6 % failed, CPU 0.9 % | 0 %, p50 604 ms | 0 %, p50 605 ms | 0 %, 604 ms |
| .NET 10, 400 req/s | 100 % failed, CPU 1.9 % | 83.8 % failed | **0 %, 392 req/s, p50 605 ms** | – |
| .NET 11, 400 req/s | 100 % failed, CPU 3.2 % | 17.8 % failed | **0 %, 392 req/s, p50 604 ms** | – |

With the earlier threaded mock (slower under load), the same experiment failed in every run ([20261126T222721Z](../http-runs/20261126T222721Z/REPORT.md)).

**Explanation (consistent with the data, not traced in the runtime).** The first run after a cold start always starves: the ThreadPool starts with about one thread per CPU and its hill-climbing injects new threads slowly. Threads injected during a failing run are kept for a while, so the next run starts with a larger pool and can keep up. Starvation therefore depends on the pool's recent history. That is exactly why it is dangerous in production: it appears after deployments and restarts, and disappears when someone looks at a warmed-up instance. The fix remains async all the way (sequential-async: 0 % failed in every run).
