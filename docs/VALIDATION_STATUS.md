# Validation status

Last full validation: **2026-11-27** on Windows 11 (Intel i7-13700H, 20 logical CPUs, 32 GB). Toolchain: Temurin JDK 25.0.4.1, Maven 3.9.6, .NET SDK 10.0.404, Docker 29.5 (Rancher Desktop), Python 3.13, k6 1.3.0 (container), OpenTelemetry Java agent 2.34.0.

## 1. Evidence

| Check | How | Result |
|---|---|---|
| Maven reactor (cache-core, app, JMH, Jakarta WAR) | `mvn -B -f implementations/spring-boot/pom.xml clean verify` (JDK 25) | **pass**, also from a fresh clone (§3) |
| cache-core unit tests | surefire | **12 / 12** |
| Spring MySQL integration test (Testcontainers: journal, NULL timestamps, late commit, rollback) | failsafe `CatalogIT` | **1 / 1** |
| .NET 10 build + xUnit | `dotnet test Lab.Tests` (`LabTargetFrameworks=net10.0`) | **4 / 4** |
| .NET 11 | `sdk:11.0` / `aspnet:11.0` images | builds and runs (`runtime 11.0.0`); local xUnit not run (no .NET 11 SDK installed) |
| Dependency-free checks | `tools/check_offline.py`, `tools/check_extended.py` (JDK 25) | **pass** |
| Report tool tests | `python -m unittest test_report_generator` (in `tools/`) | **2 / 2** |
| Common HTTP contract (incl. DI captive/mutable, real DB pool, transactional events + rollback) | `tools/compare_http.py --url …` against Spring, Jakarta, .NET in Docker | **pass** on all three |
| Correctness probes: reservation, stampede, pool, DI identity/mutable/ownership, events, handler failure, staleness, pinning, Redis | `tools/run_http_suite.py` probes | all invariants hold; results in [BENCHMARK_REPORT.md](../reports/BENCHMARK_REPORT.md) |
| Virtual-thread execution actually happens | `/lab/threads/info` (Spring `virtual=true`), `/lab/threads/executor` (WildFly `VirtualThread[#…]`) | **verified** |
| Observability: metrics + traces for all three editions | [observability validation](../reports/observability/2026-11-27-validation.md) | **verified ingestion** in Prometheus, Tempo and Grafana |
| Benchmarks: JMH, BDN, k6 (8 labs, 3 editions, repetitions) | see report | completed |
| Redis on all editions (after v1.0.0): Jakarta/Jedis and .NET/StackExchange.Redis ports | Maven `clean package` (JDK 25), .NET build + xUnit 4/4, manual smoke on two instances each, then `run_http_suite.py --only v5` / `v5b` | **pass**: same invariants as Spring (`distributed` → 1 load on every round, stale read until invalidation, DB fallback during outages) |
| Redis TTL demo | `tools/redis_lab.py` | not run separately (the Redis shared-cache experiment supersedes it) |
| GitHub Actions | `.github/workflows/ci.yml` | passed: all three jobs (verify, dotnet, jakarta) green on 99c5f6a, the v1.0.0 commit, as checked in the GitHub UI on 2026-11-27 |

## 2. Defects found and fixed

| # | Area | Symptom | Cause | Fix |
|---|---|---|---|---|
| F1 | JMH build | `Cannot find 'resource' in class ManifestResourceTransformer` | Spring Boot parent's shade transformers merged into the JMH module | `<transformers combine.self="override">` |
| F2 | Jakarta deployment | `WELD-000075 … public field: Catalog.sync`, nothing deployed | CDI forbids public fields on normal-scoped beans | private field + accessor |
| F3 | Jakarta events | `auditCount` always 0 | fields read through the CDI client proxy | accessor methods |
| F4 | Spring events under load | all requests hung, app frozen | **Hikari pool deadlock**: AFTER_COMMIT listener with `REQUIRES_NEW` on the request thread needs a 2nd connection while the 1st is still held (`active=10, waiting=198`) | async listener on a bounded executor (`AbortPolicy`, not `CallerRunsPolicy`, which would recreate the deadlock); negative mode `event-inline` kept |
| F5 | .NET build without .NET 11 SDK | `NETSDK1045`, BenchmarkDotNet built nothing | hard-coded multi-targeting | overridable `LabTargetFrameworks` |
| F6 | Harness: mock upstream | refused connections; +40 ms per call for .NET | backlog 5; two small writes + Nagle + delayed ACK | large backlog, one write, `TCP_NODELAY` |
| F7 | Local ports | `port is already allocated` | hard-coded Jakarta/.NET ports | `JAKARTA_PORT`, `DOTNET_PORT`, `LAB_PORT2` |
| F8 | Harness: mock upstream | virtual threads "slower" than platform threads (260 vs 320 req/s, 28 % failures) | `ThreadingHTTPServer` = 1 OS thread per keep-alive connection; >3,000 Python threads under virtual-thread clients | single-threaded asyncio mock; all affected I/O benchmarks rerun (v4) — [investigation 1](../reports/investigations/2026-11-27-anomalies.md) |
| F9 | Jakarta managed virtual executor | 100 % timeouts at ≥ 50 req/s | Concurro bounds concurrent tasks with a semaphore from `maxAsync` | `@ManagedExecutorDefinition(virtual=true, maxAsync=2000)`; phase rerun — [investigation 3](../reports/investigations/2026-11-27-anomalies.md) |
| F10 | Jakarta build | Docker build failed: `ActivateRequestContext` not found | missing import of `jakarta.enterprise.context.control.ActivateRequestContext`; the local check had passed because Maven's incremental build did not recompile the class | import fixed; verification now uses `clean package` |
| F11 | Harness: suite | 11 minutes per experiment | `localhost` resolved to `::1` first on Windows, ~2 s per refused attempt | probes use `127.0.0.1` |
| F12 | Harness: suite | contaminated rows after saturation runs; WildFly measured during JIT warm-up | overloaded servers keep draining their queue; 10 s warm-up too short at 2,000 req/s | saturation runs last, drain check before each run, 30 s warm-up at ≥ 1,000 req/s |
| F14 | Jakarta routing | `/lab/resources/stampede` and `/pool` returned 404 (since the DB-pool lab was added) | a resource class annotated `@Path("lab/resources")` takes precedence for every URI under that prefix | DB-pool endpoint moved into `Endpoints`; found by the clean-checkout contract test, re-verified from a new clone |
| F15 | Lab 08 DNS experiment | a JVM DNS A/B (v5b, v6 `-dns0`) changed nothing, yet one v5b run was reported as confirming the negative-cache explanation | `-Dsun.net.inetaddr.negative.ttl` is ignored when `networkaddress.cache.negative.ttl` is set in `java.security`, which the JDK does; the single "confirming" run was the usual path by chance | security property set through `-Djava.security.properties` (`infrastructure/jvm/*.security`), verified with `java -XshowSettings:security:properties`; outage runs repeated 5×; Lab 08 and the report corrected |
| F13 | Harness: host | run aborted with a negative subprocess timeout | laptop entered Modern Standby for 4 h | keep-awake request (`SetThreadExecutionState`) for the duration of a suite run |

## 3. Clean-checkout reproduction

Commands and results of the fresh-clone build and tests: [ROADMAP.md §3](ROADMAP.md#3-clean-checkout-reproduction).

## 4. Environment notes

- Maven must run on JDK 25 (`maven.compiler.testRelease=25`); with an older `JAVA_HOME` the build fails with "release version 25 not supported".
- An empty `log4j-bom-2.26.1.pom` in the local Maven repository (interrupted download) breaks POM processing; delete the folder.
- NuGet reports moderate advisories for `MySqlConnector 2.4.0` and `OpenTelemetry.* 1.12.0` (NU1902). Not relevant for the lab; bump before reusing the code.
- Keep the machine awake during benchmark runs; standby invalidates a run.

## 5. Not validated

- GitHub Actions results (see §1).
- .NET 11 unit tests on a local SDK.
- Agent/SDK overhead on benchmark numbers (benchmarks ran without instrumentation).
- Redis cluster/replication, multiple outbox dispatchers, other Redis clients (Redisson, Lettuce on Jakarta).
