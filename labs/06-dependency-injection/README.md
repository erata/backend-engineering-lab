# Lab 06 — Dependency-injection lifetimes and allocation cost

> Use case: **"A service needs a large reference table (100,000 product entries). Should it be built per request or once per application?"**

## 1. Scenario

Two beans/services hold the same heavy payload of 100,000 entries:

| Mode | Spring Boot | Jakarta EE (CDI) | ASP.NET Core |
|---|---|---|---|
| `request` | `@RequestScope` bean (scoped proxy) | `@RequestScoped` bean (client proxy) | `AddScoped<RequestData>()` |
| `shared` | singleton `@Component` | `@ApplicationScoped` bean | `AddSingleton<SharedData>()` |
| payload | `ProductGenerator.generate(100000)`: 100K `Product` records in a `List` | same Java generator | `string[100000]` of `"Product n"` |

Code: [DiController](../../implementations/spring-boot/app/src/main/java/de/backendlab/labs/DiController.java), [DiResource](../../implementations/jakarta-ee/src/main/java/de/backendlab/ee/DiResource.java), `RequestData`/`SharedData` in [Program.cs](../../implementations/aspnet-core/Lab.Api/Program.cs).

Endpoint: `GET /lab/di/instances?mode=request|shared` → `{id, count}`.

## 2. Correctness check

Identity, verified by the suite probe on all three editions: two `shared` calls return the **same** id, and two `request` calls return **different** ids. If `request` returned the same id twice, the scope would be broken (for example a request-scoped bean captured by a singleton, the "captive dependency" bug).

## 3. Benchmark

k6, 50 req/s, 30 s per mode, 4 CPUs / 2 GB. Each `request` call constructs the full payload, so 50 req/s means 5 million objects/s (Java) or 5 million strings plus 50 × 800 KB arrays/s (.NET).

## 4. Results

Run [20261126T222721Z](../../reports/http-runs/20261126T222721Z/REPORT.md), latency in ms.

| Edition | request p50 / p95 / p99 | shared p50 / p95 / p99 | CPU request / shared |
|---|---|---|---|
| Spring Boot | 2.65 / 6.65 / 8.38 | 1.60 / 2.62 / 2.99 | 20% / 6% |
| Jakarta EE | 3.60 / 8.28 / 12.44 | 1.59 / 2.14 / 2.72 | 64% / 8% |
| ASP.NET Core | 5.77 / **42.98 / 61.98** | 0.79 / 1.48 / 2.16 | 62% / 4% |

## 5. Interpretation

- **Per-request construction costs 3–15× more CPU** for the same answer: Spring 20% vs 6%, Jakarta 64% vs 8%, .NET 62% vs 4%. At 50 req/s it's affordable; at 2,000 req/s the request-scoped variant would need about 40× more CPU than the shared one.
- **Tail latency is where allocation hurts.** The median rises by 1–5 ms, but .NET's p95 jumps to 43 ms. A `string[100000]` is 800 KB, above the 85 KB Large Object Heap threshold, so every request allocates on the LOH, and LOH allocations are collected only by gen-2 GCs. The Java payloads are many small objects that die young in the TLAB/young generation. That's cheaper, but still visible (Spring p99 8.4 vs 3.0 ms).
- **The lifetime decision is about semantics first, cost second:**
  - Use *shared* for immutable, thread-safe data. A shared **mutable** object is a race condition (Lab 02).
  - Use *request* for per-user or per-transaction state, never for expensive immutable data.
  - Proxies matter: Spring and CDI inject a **proxy** for request/application-scoped beans. Accessing a *field* through a CDI proxy reads the proxy's own copy, not the bean's; validation fixes F2/F3 were exactly this bug ([VALIDATION_STATUS.md](../../docs/VALIDATION_STATUS.md)).

## 6. Trade-offs

| Lifetime | Use for | Danger |
|---|---|---|
| Singleton / application | stateless services, immutable caches, clients with pools (HTTP, DB) | shared mutable state; holding request data |
| Request / scoped | user context, unit of work, DbContext (.NET) | expensive construction per request; captive dependency when injected into a singleton |
| Transient / prototype | cheap, stateful helpers | disposal and ownership confusion |

## 7. Limitations

- Captive-dependency and leaked-mutable-state experiments are described but not implemented as separate endpoints ([ROADMAP.md](../../docs/ROADMAP.md)).
- The .NET payload (strings) differs from the Java payload (records). Compare the request-vs-shared ratio within one edition, not absolute numbers across editions.
