# Lab 04 — Platform threads, virtual threads and runtime versions

> Use case: **"The product-detail endpoint calls three slow upstream services with blocking code. What happens when traffic grows, and does a newer JVM or virtual threads help?"**

## 1. Scenario

`GET /lab/io/blocking` calls `/product` (100 ms), `/inventory` (200 ms) and `/pricing` (300 ms) on the mock upstream **one after the other, with blocking calls**. A request therefore holds its server thread for ≈ 600 ms while doing almost no CPU work.

By Little's law, sustaining *λ* requests/s with a residence time of *W* = 0.6 s needs *L = λ·W* requests in flight. At 400 req/s that is **≈ 240 concurrent requests, each pinning one thread**.

| Server | Request threads by default |
|---|---|
| Spring Boot / Tomcat, platform | `server.tomcat.threads.max` = **200** |
| Spring Boot / Tomcat, virtual (`spring.threads.virtual.enabled=true`) | one new virtual thread per request (no fixed cap) |
| WildFly 42 / Undertow | worker ("default task") pool = 16 × CPUs = **64** at 4 CPUs |
| ASP.NET Core / Kestrel | .NET ThreadPool: starts with ≈ CPU-count threads, injects more slowly when threads block |

Hypothesis: the platform servers cap throughput at *threads / 0.6 s* (Tomcat ≈ 333 req/s, WildFly ≈ 107 req/s). Virtual threads remove the cap because a blocked virtual thread releases its carrier. Java 17 vs Java 25 should **not** matter for this workload, because the bottleneck is the thread count, not the JIT or GC.

## 2. Implementation

| Edition | Code | Thread-model switch |
|---|---|---|
| Spring Boot | [EngineeringController](../../implementations/spring-boot/app/src/main/java/de/backendlab/labs/EngineeringController.java) → `Experiments.io(…, "blocking", …)` uses `HttpClient.send` on the Tomcat request thread | `LAB_VIRTUAL_THREADS=true/false`; `JAVA_VERSION=17/25` selects the runtime image (same jar, bytecode release 17) |
| Jakarta EE | [Endpoints](../../implementations/jakarta-ee/src/main/java/de/backendlab/ee/Endpoints.java) – same kernel on an Undertow worker thread | none (a managed virtual-thread executor is not configured, see ROADMAP) |
| ASP.NET Core | [Program.cs](../../implementations/aspnet-core/Lab.Api/Program.cs) – `GetStringAsync(...).GetAwaiter().GetResult()` (**sync-over-async**) | `DOTNET_VERSION=10.0/11.0` |

`GET /lab/threads/info` shows which runtime and thread type served the request. Recorded values: `http-nio-…-exec-2, virtual=false, 25.0.5.1`; `tomcat-handler-1, virtual=true, 25.0.5.1`; `exec-2, virtual=false, 17.0.21.1`; WildFly `default task-2, 25.0.4.1`; .NET `10.0.15, processors=4, threadPool=5`.

## 3. Benchmarks

| Experiment | Load | Purpose |
|---|---|---|
| `io-blocking` | 50 req/s, 30 s | below the thread limit: latency should equal the upstream chain (~605 ms) |
| `io-blocking-400rps` | 400 req/s, 30 s (k6 allowed up to 3,000 VUs) | above the platform thread limit: shows queueing, dropped iterations, timeouts |
| `catalog-get` | 2,000 req/s | sanity check that the thread model does not hurt a CPU-light endpoint |

All backends were limited to 4 CPUs / 2 GB. The suite runs the saturation test last in each phase and waits until the backend has drained its queue before running anything else.

## 4. Results — Spring Boot

Run [20261126T202650Z](../../reports/http-runs/20261126T202650Z/REPORT.md). Latency in ms.

| Configuration | `io-blocking-400rps` achieved / target | p50 | p95 | p99 | dropped | failed | container CPU |
|---|---:|---:|---:|---:|---:|---:|---:|
| Java 25, platform threads | 268 / 400 | 4,499 | 7,734 | 8,002 | 1,810 | 0% | 91% |
| Java 17, platform threads | 268 / 400 | 4,484 | 7,749 | 7,995 | 1,837 | 0% | 109% |
| **Java 25, virtual threads** | **392 / 400** | **605** | **613** | **624** | **0** | 0% | 98% |

| Configuration | `io-blocking` 50/s p50 / p99 | `catalog-get` 2,000/s p50 / p99 |
|---|---|---|
| Java 25 platform | 605 / 609 | 1.02 / 79.2 |
| Java 25 virtual | 605 / 607 | 0.43 / 1.30 |
| Java 17 platform | – | 0.68 / 70.5 |

Repeat of the platform baseline in run [20261126T222721Z](../../reports/http-runs/20261126T222721Z/REPORT.md) (30 s warm-up on high-rate tests): **322 / 400 req/s, p50 2,507 ms, p99 4,115 ms, 1,016 dropped**. The ceiling sits closer to the theoretical 333 req/s this time. The difference between the two runs shows how much a single run near saturation can move.

## 4b. Results — Jakarta EE and ASP.NET Core (same run, same load)

| Configuration | achieved / target | p50 | p99 | failed (10 s timeout) | container CPU |
|---|---:|---:|---:|---:|---:|
| WildFly 42, 64 worker threads | 210 / 400 | 10,000 | 10,001 | **88%** | 47% |
| .NET 10, sync-over-async | 204 / 400 | – | 10,001 | **100%** | 4% |
| .NET 11, sync-over-async | 204 / 400 | 2,854 | 10,001 | **100%** | 2% |

- **WildFly** hits the ceiling earliest: 64 worker threads / 0.6 s ≈ 107 req/s. The queue grows until requests exceed the 10 s client timeout.
- **.NET** fails completely, with the CPU almost idle. This isn't a thread *limit* but ThreadPool **starvation**: blocked threads wait for continuations that need the same pool ([Lab 03](../03-async-io/README.md) shows the same at only 50 req/s). .NET 11 behaves like .NET 10. The fix in .NET is `await`, not more threads.

## 5. Interpretation

- **The platform-thread ceiling is exactly where Little's law puts it.** 200 Tomcat threads / 0.6 s ≈ 333 req/s in theory. Measured: 268 req/s, with a 4.5 s median, as requests wait in Tomcat's accept queue. k6 had to drop 1,810 iterations because it ran out of its 3,000 VUs. No request failed; they were all just late, and that is the dangerous part.
- **Virtual threads remove the ceiling without any code change.** 392 req/s at the target rate, with latency equal to the upstream chain (605 ms p50, 624 ms p99), at about the same CPU. The JDK parks the virtual thread on the blocking socket read and reuses the carrier thread.
- **Java 17 vs Java 25 makes no difference here** (268 vs 268 req/s, near-identical percentiles). Runtime improvements can't fix a thread-count bottleneck. That is the control experiment showing the gain comes from the thread model, not from the JDK version.
- **Virtual threads are not free speed.** They don't make the upstream faster (p50 is still 605 ms), and they don't add CPU. They also remove natural backpressure: with 240+ requests in flight, a downstream with its own limits (a DB pool, a rate-limited API) becomes the next bottleneck (see [Lab 08](../08-resource-management/README.md)). The catalog p99 improvement on the virtual-thread run (1.3 ms vs 79 ms) is a single-run observation. The platform runs' tails vary between runs, so don't treat it as an effect of virtual threads without repeating it.

## 6. Trade-offs

| Option | Good for | Watch out for |
|---|---|---|
| Platform thread pool | predictable concurrency limit = built-in backpressure | blocking I/O capacity = pool size / latency |
| Virtual threads (Java 21+) | blocking-style code with high I/O concurrency | pinning (`synchronized` around blocking calls before JDK 24, native calls), unbounded concurrency hitting downstream limits, ThreadLocal-heavy libraries |
| Async/reactive ([Lab 03](../03-async-io/README.md)) | maximum concurrency, explicit composition | code complexity, harder debugging |
| .NET: never block on async | keeping the ThreadPool healthy | one `.Result` / `.GetAwaiter().GetResult()` on a hot path can starve the whole pool |

## 7. Limitations

- One run per configuration on a shared workstation.
- No pinning stress test (e.g. blocking inside `synchronized` on JDK 21 vs 24+) and no managed virtual-thread executor for WildFly; see [ROADMAP.md](../../docs/ROADMAP.md).
- Tomcat thread count was left at its default. Raising `server.tomcat.threads.max` would move the platform ceiling, which is itself a valid experiment.
