# Lab 02 — Race conditions and stock reservation

> Use case: **"A flash sale has 100 units of a product and 200 customers press *Buy* at the same moment. Exactly 100 must succeed and the stock must never go negative."**

## 1. Scenario and invariant

One experiment = `requests` concurrent reservation attempts against `stock` units, each attempt "if stock > 0 then stock -= 1 and accept".

Invariant checked on **every** run: `accepted == min(stock, requests)` and `remaining == max(0, stock - requests)`. The endpoint returns `correct: true/false`.

The read-check-write sequence is a **compound operation**. Making each step thread-safe is not enough; the whole sequence must be atomic.

## 2. Variants and implementation

| Mode | Java ([Experiments.reserve](../../implementations/spring-boot/cache-core/src/main/java/de/backendlab/experiments/Experiments.java)) | .NET (`Lab.Reserve` in [Program.cs](../../implementations/aspnet-core/Lab.Api/Program.cs)) | Guarantee |
|---|---|---|---|
| `unsafe` | read `int[]`, `Thread.yield()`, write | read `int`, `Thread.Yield()`, write | none: two threads read the same value → **lost update / oversell** |
| `lock` | `synchronized(lock) { check; decrement }` | `lock(gate) { … }` | mutual exclusion of the compound step |
| `atomic` | CAS loop on `AtomicInteger.compareAndSet(old, old-1)` | `Interlocked.CompareExchange` loop | lock-free conditional decrement |

The `yield` in `unsafe` widens the race window on purpose, so the failure shows up reliably instead of once a month in production.

Task scheduling per edition: Spring submits each attempt as a `CompletableFuture` to a fixed 32-thread pool; Jakarta uses the container's `ManagedExecutorService`; .NET uses `Parallel.For` on the ThreadPool, which partitions the 2,000 iterations over a few worker threads.

Endpoint: `POST /lab/concurrency/reserve?mode=atomic|lock|unsafe&stock=100&requests=200` (bounds: stock ≥ 0, requests 1..2000). Each call creates fresh state.

## 3. Benchmarks

| Benchmark | Tool | Workload |
|---|---|---|
| Correctness probe | `run_http_suite.py` | 30 runs per mode, stock 100 / 200 requests, count incorrect results |
| `EngineeringBenchmark.reserve` | JMH | one full experiment, stock 1,000 / 2,000 attempts, 32-thread pool |
| `ReservationBench.Reserve` | BenchmarkDotNet | same experiment with `Parallel.For` |
| `reserve-atomic`, `reserve-lock` | k6 | 50 experiments/s over HTTP (= 100,000 attempts/s), 30 s |

## 4. Results

### 4.1 Correctness (30 runs each, run [20261126T222721Z](../../reports/http-runs/20261126T222721Z/REPORT.md))

| Edition | unsafe: incorrect runs | worst oversell (accepted of 100) | lock: incorrect | atomic: incorrect |
|---|---:|---:|---:|---:|
| Spring Boot | **21 / 30** | 150 | 0 / 30 | 0 / 30 |
| Jakarta EE | **29 / 30** | 144 | 0 / 30 | 0 / 30 |
| ASP.NET Core | **11 / 30** | 185 | 0 / 30 | 0 / 30 |

`unsafe` sold up to **85% more units than existed**. The failure rate depends on how many threads actually run in parallel, so it differs between executors. That variability is exactly why a race "that passed the tests" is not evidence of safety.

### 4.2 Kernel cost (stock 1,000, 2,000 attempts)

| Mode | JMH (Java 25, 32-thread pool) | BenchmarkDotNet (.NET 10, Parallel.For) |
|---|---:|---:|
| atomic (CAS) | 0.81 ± 0.11 ms, 355 KB alloc | **0.167 ± 0.005 ms**, 4.9 KB alloc |
| lock | 0.86 ± 0.10 ms, 362 KB alloc | **1.039 ± 0.028 ms**, 6.5 KB alloc |

### 4.3 HTTP (50 experiments/s, 4 CPUs)

| Edition | atomic p50 / p95 / p99 (ms) | lock p50 / p95 / p99 (ms) | CPU (atomic / lock) |
|---|---|---|---|
| Spring Boot | 1.62 / 2.58 / 3.53 | 1.75 / 2.58 / 3.28 | 16% / 16% |
| Jakarta EE | 4.15 / 6.36 / 8.34 | 4.35 / 6.71 / 8.68 | 30% / 37% |
| ASP.NET Core | 0.87 / 1.39 / 1.85 | 0.93 / 1.58 / 2.33 | 5% / 13% |

## 5. Interpretation

- **Both lock and CAS are correct, and in Java they cost the same** (0.81 vs 0.86 ms). The Java experiment is dominated by creating and joining 2,000 `CompletableFuture`s (≈ 180 bytes and one queue hand-off each), not by the decrement. The synchronization primitive is noise compared with the task overhead.
- **In .NET the primitive matters: CAS is 6× faster than `lock`.** `Parallel.For` runs the loop body inline on a few workers with almost no per-iteration allocation (4.9 KB total), so the remaining cost really is contention. A contended `lock` makes threads spin and then block in the kernel; a failed CAS just retries.
- **Lesson:** measure the operation you care about. "CAS is faster than locks" is true for the primitive and invisible in a workload whose overhead lies elsewhere.
- Jakarta's higher HTTP latency comes from the managed executor plus the heavier request path (see Lab 01). It does not mean the algorithm is slower; the kernel is the same Java code as Spring's.

## 6. Trade-offs

| Approach | When | Limit |
|---|---|---|
| `synchronized` / `lock` | compound invariants over several fields; simplest to reason about | blocks under contention; never hold it across I/O |
| CAS / `AtomicInteger` / `Interlocked` | a single variable with a conditional update | retry storms under extreme contention; more than one variable needs a lock or an immutable state object |
| Database (`UPDATE … SET stock = stock - 1 WHERE id = ? AND stock > 0`) | **multi-instance** deployments, the real-world answer | round-trip per reservation; row-lock contention on hot products (see Lab 07 hot-row result) |

This lab is single-process by design. With two application instances, in-memory locks protect nothing; the invariant must live in the database or a distributed coordinator.

## 7. Reproduce

```powershell
Invoke-RestMethod -Method Post 'http://localhost:8080/lab/concurrency/reserve?mode=unsafe&stock=100&requests=200'
python tools/run_benchmark.py --suite engineering
dotnet run -c Release -f net10.0 --project implementations/aspnet-core/Lab.Benchmarks -- --filter '*ReservationBench*'
```
