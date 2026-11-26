# Lab 03 — Blocking, sequential-async and concurrent I/O

> Use case: **"A product-detail page needs data from three independent services: product (100 ms), inventory (200 ms) and pricing (300 ms). How fast can it answer?"**

## 1. Scenario

The [mock upstream](../../infrastructure/mock-api/server.py) answers `/product`, `/inventory` and `/pricing` after fixed delays of 100/200/300 ms. The aggregator returns the three bodies in order.

| Mode | What the code does | Expected latency of one request |
|---|---|---|
| `blocking` | call 1 → wait → call 2 → wait → call 3, blocking the thread | 100 + 200 + 300 = **600 ms** |
| `sequential-async` | same order, but each call is non-blocking (`thenCompose` / `await`) | still **600 ms**: async does not reorder dependent waits |
| `concurrent` | start all three, then join (`allOf` / `Task.WhenAll`) | max(100, 200, 300) = **300 ms** |

Async and concurrency are different things. Async frees the **thread** while waiting; concurrency overlaps the **waits**. Only the second shortens a single request.

## 2. Implementation

| Edition | Code | Notes |
|---|---|---|
| Spring Boot | `Experiments.io` via [EngineeringController](../../implementations/spring-boot/app/src/main/java/de/backendlab/labs/EngineeringController.java) | JDK `HttpClient.send` / `sendAsync`; the controller returns a `CompletionStage`, so Spring MVC completes the request asynchronously. Extra route `/lab/io/concurrent-blocking?threadModel=platform|virtual` (blocking calls fanned out to an executor) |
| Jakarta EE | same kernel via [Endpoints](../../implementations/jakarta-ee/src/main/java/de/backendlab/ee/Endpoints.java) | JAX-RS resource returns `CompletionStage` |
| ASP.NET Core | `/lab/io/{mode}` in [Program.cs](../../implementations/aspnet-core/Lab.Api/Program.cs) | `IHttpClientFactory`; `blocking` = `GetStringAsync(...).GetAwaiter().GetResult()` (**sync-over-async**), `sequential-async` = `await` in a loop, `concurrent` = `Task.WhenAll` |

Correctness: every mode returns exactly three bodies in the order product, inventory, pricing (checked by `compare_http.py` and by k6's JSON check).

## 3. Benchmark

k6, 50 req/s for 30 s per mode, backend limited to 4 CPUs. 50 req/s keeps the Java servers well below their thread limits (≈ 30 requests in flight). The overload case is [Lab 04](../04-virtual-threads/README.md).

## 4. Results

Run [20261126T222721Z](../../reports/http-runs/20261126T222721Z/REPORT.md), latency in ms.

| Edition | blocking p50 / p99 | sequential-async p50 / p99 | concurrent p50 / p99 | CPU (blocking / seq / conc) |
|---|---|---|---|---|
| Spring Boot (Java 25) | 605.9 / 612.9 | 604.8 / 607.7 | **302.9 / 305.2** | 29% / 34% / 26% |
| Jakarta EE (Java 25) | 606.0 / 610.5 | 605.5 / 609.0 | **303.4 / 305.9** | 33% / 42% / 22% |
| ASP.NET Core (.NET 10) | **100% failed** (10 s timeouts, 28.7 of 50 req/s) | 603.7 / 607.0 | **302.5 / 304.5** | 1.5% / 15% / 15% |

## 5. Interpretation

- **Concurrency halves latency; async alone doesn't change it.** All three stacks land within 5 ms of the theoretical 300 ms / 600 ms. The ~3–6 ms above theory is HTTP and scheduling overhead.
- **Blocking and sequential-async look identical at low load** (605 vs 605 ms). The difference is invisible until threads run out (Lab 04: 268–322 req/s ceiling for blocking on Tomcat).
- **.NET sync-over-async collapses at only 50 req/s.** The container used **1.5% CPU** while every request timed out. That is the signature of **ThreadPool starvation**. `.GetAwaiter().GetResult()` blocks a pool thread, and the HTTP continuation that would unblock it also needs a pool thread. The pool starts at about 4 threads (1 per CPU) and injects new ones slowly (roughly 1–2/s). Thirty requests in flight exhaust it, and everything queues behind blocked threads. The same .NET code in `sequential-async` mode is perfectly healthy. Java has no equivalent failure because its blocking socket call doesn't need a pool thread to complete.
- **A harness lesson from this lab:** the first runs showed .NET at ~735 ms instead of 605 ms, +40 ms per upstream call. The cause was the mock server: with HTTP/1.1 keep-alive it wrote headers and body as two small TCP segments, and Nagle's algorithm with the client's delayed ACK added ~40 ms. Fixing the mock (`TCP_NODELAY`) removed it. Always check that the measuring tool isn't the bottleneck.

## 6. Trade-offs

| Style | Pros | Cons |
|---|---|---|
| Blocking, sequential | simplest code, stack traces readable | one thread per in-flight request; serial latency |
| Async, sequential | frees threads (scales concurrency) | same latency; more complex code; .NET: never mix with `.Result` |
| Concurrent fan-out | latency = slowest dependency | must handle partial failure, timeouts and cancellation for each branch; multiplies load on downstream services |

## 7. Reproduce

```powershell
docker compose up -d mock-api app
Invoke-RestMethod http://localhost:8080/lab/io/concurrent
$env:BASE_URL='http://localhost:8080'; $env:LAB_PATH='/lab/io/sequential-async'; $env:RATE='50'
k6 run benchmarks/k6/workload.js          # or: python tools/run_http_suite.py --only spring-j25-platform-snapshot
```
