# Implementation coverage and remaining work

Status as of 2026-11-26. "Verified" means it was built, run, and checked by a test, probe or benchmark ([VALIDATION_STATUS.md](VALIDATION_STATUS.md)).

| Topic | Spring Boot | Jakarta EE | ASP.NET Core | Verified |
|---|---|---|---|---|
| 01 Cache / MySQL | 5 strategies, CRUD, journal + watermark, Testcontainers IT | shared 5 strategies, CRUD, journal/watermark/full | 5 strategies, CRUD, journal/watermark/full | all three: smoke + k6; Spring: IT + JMH |
| 02 Concurrency | shared kernel (unsafe / lock / CAS) | shared kernel, managed executor | unsafe / lock / Interlocked | probes + JMH + BDN + k6 |
| 03 Async HTTP | blocking, sequential-async, concurrent, concurrent-blocking | shared kernel, `CompletionStage` | sync-over-async, sequential `await`, `WhenAll` | k6, all three |
| 04 Threads / runtimes | Java 17 / 25, platform / virtual | platform only (Undertow workers) | .NET 10 / 11 | k6, all configurations |
| 05 CPU | shared kernel + JMH | shared kernel, managed executor | `Parallel.For` + BDN | JMH + BDN + CPU probe at 1/2/4/8 CPUs |
| 06 DI | request scope / singleton | `@RequestScoped` / `@ApplicationScoped` | scoped / singleton | identity probe + k6 |
| 07 Events | MySQL, `direct`, async AFTER_COMMIT `event`, negative `event-inline` | in-memory CDI observer | in-memory C# event | manual DB checks + k6 |
| 08 Resources | semaphore pool + single-flight | same kernel | `SemaphoreSlim` + single-flight | probes, all three |
| Redis | standalone TTL script | same | same | **not run** |
| Observability | Actuator / optional Java agent | optional Java agent | conditional OTLP | **not run** |

## Remaining work

1. **Still missing variants**
   - WildFly managed virtual-thread executor (Lab 04) and an explicit pinning experiment (`synchronized` around blocking I/O on JDK 21 vs 24+).
   - Captive-dependency and leaked-mutable-state endpoints for Lab 06.
   - Transactional events for Jakarta (`@Observes(during = AFTER_SUCCESS)` with JTA) and .NET (outbox), so that they match the Spring edition.
   - A transactional outbox example for Lab 07 (would close the audit gap documented there).
   - A real JDBC/ADO.NET pool-saturation benchmark (Lab 08); today the pool is a semaphore simulation. Lab 07 `event-inline` already shows real Hikari exhaustion.
   - .NET cache microbenchmarks (BDN) equivalent to the JMH `CacheBenchmark`.
2. **Performance follow-ups found by the benchmarks**
   - Pre-sorted page index published with the snapshot, so pages stop sorting 100K entries per request (Lab 01; .NET `catalog-page` p50 47 ms).
   - Profile the WildFly request path: ≈ 3.7 ms CPU per `catalog-get` versus ≈ 0.44 ms on Spring Boot at 4 CPUs (async-profiler / JFR). Check heap (`-Xmx512m` default), Yasson and RESTEasy settings.
   - .NET `di-request`: the payload array lands on the LOH. A pooled or chunked payload would show the difference.
3. **Measurement quality**
   - Repeat every k6 configuration ≥ 5 times on a dedicated host and report the spread ([EXPERIMENT_PROTOCOL.md](EXPERIMENT_PROTOCOL.md)).
   - Run Redis and the monitoring stack and check that OTel data from all three editions is ingested.
   - Run the GitHub Actions workflow on a real remote.
4. Do not claim full framework parity: the Jakarta/.NET event examples remain in-memory until item 1 is done.
