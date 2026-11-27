# Interview discussion guide

How to use this guide: run the lab, read its README, then practise explaining the mechanism **before** the number. Every number quoted in an interview should be one you can trace to [the benchmark report](../reports/BENCHMARK_REPORT.md), stated with its environment ("on my 4-CPU Docker setup…"). Measured numbers are indicative, not universal rankings.

## 1. Concurrency fundamentals

| Question | Answer in two sentences | Evidence in this repo |
|---|---|---|
| Concurrency vs parallelism? | Concurrency = several tasks *in progress* (they may interleave on one core). Parallelism = several tasks *executing at the same instant* on different cores. | Lab 03 overlaps waits with no extra CPU (concurrency); Lab 05 needs more cores for more speed (parallelism) |
| Thread vs task? | A thread is an OS/runtime execution resource with a stack; a task (`Task`, `CompletableFuture`) is a unit of work and its result, which only occupies a thread while it runs. | Lab 03 `sequential-async` frees the thread while waiting; Lab 04 virtual threads make threads cheap instead |
| Blocking vs non-blocking I/O? | Blocking I/O parks the calling thread until data arrives; non-blocking I/O registers a continuation and frees the thread. Latency is the same; thread usage is not. | Lab 03: blocking and sequential-async both ≈ 605 ms at 50 req/s; Lab 04: blocking collapses at 400 req/s on platform threads |
| Sequential-async vs concurrent-async? | `await a; await b; await c` is still sequential; starting all three before awaiting overlaps them. | Lab 03: 605 ms vs 303 ms |
| Is a thread-safe collection enough? | No: each operation is atomic, but a *sequence* (check-then-act, multi-key batch) is not. | Lab 01 (weakly consistent pages), Lab 02 (oversell) |
| Lock vs CAS? | A lock serializes a critical section; CAS retries a conditional update of one variable. Both are correct; which is faster depends on contention and on what else the operation costs. | Lab 02: CAS 6× faster than `lock` in .NET's tight loop, identical in Java where task submission dominates |

## 2. Runtimes and threads

| Question | Answer | Evidence |
|---|---|---|
| What problem do virtual threads solve? | Thread-per-request code that **blocks on I/O** stops being limited by the number of OS threads: a blocked virtual thread unmounts from its carrier. | Lab 04: 400 req/s of 600 ms blocking calls, platform pool saturates, virtual threads keep up at upstream latency |
| What don't they solve? | CPU-bound work, downstream limits (DB pool, rate limits), and code that pins carriers (JDK 21: blocking inside `synchronized`). | Lab 05 (CPU), Lab 08 (real pool), Lab 04 pinning experiment |
| Java 17 vs Java 25 – faster? | For a thread-bound workload, no: the bottleneck is the pool size, not the JIT or GC. The gain came from the thread model. | Lab 04: Java 17 and 25 with platform threads behave the same |
| What is ThreadPool starvation in .NET? | Blocking a pool thread on an async operation (`.Result`, `.GetAwaiter().GetResult()`) while the continuation needs a pool thread too; the pool grows slowly, so requests queue with idle CPU. | Lab 03/04: sync-over-async failed up to 100 % of requests at 1–3 % CPU on every cold start, and survived on a warmed-up pool |
| How do you size a thread pool? | I/O: by Little's law (throughput × latency = concurrency) *and* the downstream limit. CPU: ≈ number of usable cores under sustained load. | Lab 04 ceiling ≈ 200 / 0.6 s; Lab 05 quota results |

## 3. Caching and consistency

| Question | Answer | Evidence |
|---|---|---|
| Why does `LastUpdatedTime > watermark` miss rows? | NULL timestamps never compare greater; IDs and timestamps are assigned before commit, so a late commit can fall behind the watermark. | [SYNCHRONIZATION.md](SYNCHRONIZATION.md), `CatalogIT` |
| Snapshot vs concurrent map? | Snapshot: atomic, consistent views and the cheapest reads, but every batch copies the map. Concurrent map: cheap writes, per-key consistency only. | Lab 01 JMH: 88 M vs 63 M reads/s, 33 vs ~600 K batches/s |
| What is a cache stampede and how do you stop it? | Many concurrent misses load the same key; single-flight lets one caller load while the others wait. Across instances you need a shared lock (or request coalescing). | Lab 08: 8–100 loads → 1; Redis lock across two instances |
| What does a distributed cache *not* give you? | Freshness: other instances serve the old value until invalidation or TTL; availability depends on the cache, so decide fail-open vs fail-closed. | Lab 08 consistency / Redis-down probe |

## 4. Dependency injection

| Question | Answer | Evidence |
|---|---|---|
| Is a singleton thread-safe? | Lifetime says nothing about thread safety. A singleton must be stateless or immutable, or synchronize its state. | Lab 06: "current user" in a singleton field was wrong in 95–98 % of concurrent responses |
| What is a captive dependency? | A short-lived dependency held by a longer-lived object, which silently extends its lifetime (.NET scoped-in-singleton, Spring prototype-in-singleton, CDI `@Dependent` in `@ApplicationScoped`). | Lab 06 `captive` |
| Who disposes container-created objects? | .NET: the scope that resolved them (root = application lifetime). Spring: never for prototypes – the caller owns them. CDI: the owner of the `@Dependent` object, or `Instance.destroy()`. | Lab 06 `ownership` |
| How do background workers get scoped services? | .NET: `IServiceScopeFactory.CreateScope()` per unit of work. CDI: `@ActivateRequestContext`. Spring: inject thread-safe singletons; request scope does not exist outside a request. | Lab 06 `ownership`, `background` |
| Why can Spring inject a request-scoped bean into a singleton? | It injects a scoped **proxy** that resolves the current request's instance on every call; CDI does the same for normal scopes. .NET injects the instance itself. | [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) §3 |

## 5. Transactions and events

| Question | Answer | Evidence |
|---|---|---|
| Direct call or domain event? | Direct call in the same transaction = atomic, but longer transactions and tighter coupling. After-commit event = decoupled and shorter transaction, but the side effect can be lost. | Lab 07 hot-row results |
| What can go wrong with `AFTER_COMMIT` + `REQUIRES_NEW`? | The request still holds its connection when the listener asks for a second one; at pool-size concurrency every thread waits forever (until the pool timeout). | Lab 07 `event-inline`: Hikari `active=10, waiting=198` |
| How do you make events durable? | Transactional outbox: write the event row in the same transaction as the state change and dispatch it afterwards (at-least-once, consumers idempotent). | Lab 07 .NET outbox: failed handler retried, audit recovered |
| What happens on rollback? | Nothing after-commit runs; direct side effects roll back with the transaction. | Lab 07 probes on all three editions |

## 6. Performance methodology

| Question | Answer |
|---|---|
| Why constant arrival rate? | A closed-loop load generator slows down with the server and hides queueing (coordinated omission); fixed arrival exposes it as latency and dropped iterations. |
| Why p99 and not average? | Users feel the tail; averages hide bimodal behaviour (Lab 07 `events-direct`). |
| Why repeat runs? | Near a capacity knee one run can swing from "fine" to "collapsed"; five runs show the spread (see the repeatability chart in the report). |
| Why is "framework X is faster" a weak claim here? | Different JSON stacks, thread pools and code paths; one machine; Docker on a laptop. The *mechanisms* transfer, the ratios don't. |

## Portfolio sentence

"I built a private backend engineering lab that implements the same product-catalogue scenarios in Spring Boot, Jakarta EE and ASP.NET Core, and measured caching, concurrency, async I/O, virtual threads, DI lifetimes, transactional events and resource limits under controlled load. The benchmarks also exposed real defects — a connection-pool deadlock and ThreadPool starvation — which I fixed and documented. The numbers are environment-specific; the mechanisms are what I learned."
