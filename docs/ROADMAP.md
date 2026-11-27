# Completion matrix, remaining work and release assessment

Status as of 2026-11-27. Legend:

| Mark | Meaning |
|---|---|
| ✅ | implemented and verified (test, probe or benchmark with raw data) |
| ◐ | implemented but not verified |
| ◑ | partially implemented |
| ✖ | not implemented |
| – | not applicable to this framework |

## 1. Completion matrix

| Lab / feature | Spring Boot | Jakarta EE | ASP.NET Core | Evidence |
|---|:---:|:---:|:---:|---|
| **01** five cache strategies | ✅ | ✅ (shared core) | ✅ | unit tests, `compare_http.py`, k6 |
| 01 journal sync incl. NULL timestamps, late commit | ✅ | ✅ | ✅ | `CatalogIT` (Spring); smoke + staleness probe (all) |
| 01 watermark sync baseline | ✅ | ◐ | ◐ | `CatalogIT`; ports not tested |
| 01 full-reload sync | – | ◐ | ◐ | implemented, not tested |
| 01 cache microbenchmarks | ✅ JMH | ✅ (same code) | ✖ | JMH run |
| 01 staleness window | ✅ | ✅ | ✅ | `v3-*` probes |
| **02** unsafe / lock / CAS reservation | ✅ | ✅ | ✅ | 30-run probes, JMH, BDN, k6 |
| 02 multi-instance (database) reservation | ✖ | ✖ | ✖ | documented as the real-world answer only |
| **03** blocking / sequential-async / concurrent I/O | ✅ | ✅ | ✅ (blocking = sync-over-async) | k6, 5 runs |
| 03 concurrent-blocking on platform / virtual pool | ◐ | – | – | endpoint exists, not benchmarked |
| **04** platform vs virtual threads, 400 req/s | ✅ | ✅ (worker vs managed virtual executor) | – | k6, 5 / 3 runs |
| 04 runtime versions | ✅ Java 17 vs 25 | – | ✅ .NET 10 vs 11 | k6 |
| 04 pinning (JDK 21 vs 25) | ✅ | – | – | probe, 10 runs |
| 04 ThreadPool starvation | – | – | ✅ | k6, investigation 4 |
| **05** CPU parallelism + checksum | ✅ | ✅ | ✅ | probes at 1/2/4/8 CPUs, JMH, BDN |
| **06** payload lifetime (request vs singleton) | ✅ | ✅ | ✅ | k6 |
| 06 captive dependency | ✅ | ✅ | ✅ | `di2` probe |
| 06 shared mutable request state | ✅ | ✅ | ✅ | 3 × 200 concurrent requests |
| 06 resource ownership | ✅ prototype | ✅ `Instance` | ✅ root vs scope | `ownership` probe |
| 06 request context in background work | – | ✅ `@ActivateRequestContext` | ✅ scope per unit of work | probes |
| 06 DbContext / EntityManager lifecycle | ✖ | ✖ | ✖ | no ORM in this lab |
| **07** direct vs after-commit event, rollback | ✅ | ✅ (JTA) | ✅ (outbox) | probes, k6 |
| 07 handler failure | ✅ | ✅ | ✅ | `failure` probe |
| 07 inline after-commit (negative) | ✅ (deadlock) | ✅ (no deadlock) | – | k6 |
| 07 transactional outbox | ✖ | ✖ | ✅ | `failure` probe |
| **08** in-process stampede / semaphore | ✅ | ✅ | ✅ | probes |
| 08 real connection pool | ✅ Hikari | ✅ WildFly | ✅ MySqlConnector | k6 |
| 08 Redis shared cache (2 instances, lock, invalidation, failure) | ✅ | ✅ | ✅ | `redis`, `redis2` probes, k6; clients Lettuce / Jedis / StackExchange.Redis compared |
| 08 Redis TTL demo | ◐ | ◐ | ◐ | script, not run separately |
| Observability: metrics + traces | ✅ | ✅ | ✅ | [validation](../reports/observability/2026-11-27-validation.md) |
| Observability: Grafana dashboard | ✅ | ◑ (Explore only) | ◑ (Explore only) | same |
| CI workflow | ✓ | ✓ | ✓ | all three jobs green on 99c5f6a (v1.0.0), checked by the maintainer in the GitHub UI |

## 2. Remaining defects and limitations

**Open observations (measured, not explained)**
1. Jakarta handled the 200 req/s hot-row `direct` workload (p50 14.5 ms) where Spring and .NET collapsed.
2. Why run 1's virtual-thread measurement was not affected by the threaded mock.
3. WildFly needs more CPU per catalogue request than Spring (it saturates near 2,000 req/s at 4 CPUs); not profiled.
4. The .NET client-span count in the observability check (17 vs 15 expected).

**Known limitations**
- One machine, mostly single runs outside the repeated experiments; Docker quotas on a hybrid laptop.
- In-process outbox dispatcher only; Redis lock is a lab simplification (no fencing).
- Jakarta/.NET dashboards, agent overhead and .NET 11 local unit tests were not covered.
- NuGet packages with moderate advisories (NU1902) should be bumped before reuse.

**Failed / superseded experiments (kept as raw data, not quoted)**
- v2 `io-blocking-400rps` and `io-blocking-async-*` rows (threaded mock, F8).
- `v4-rep3-jakarta-saturation` in run 20261127T063929Z (before F9).
- Jakarta/.NET rows of run 1 (harness spill-over, Nagle, warm-up).
- Run 20261127T021849Z stopped by host standby after two complete phases (data of those phases valid).

## 3. Clean-checkout reproduction

Performed on 2026-11-27 from a fresh `git clone` of the committed state into an empty directory (Compose project `clean-lab`, new volumes, so every database was seeded from scratch; host ports 28080–28083 to avoid clashes):

| Step | Command (from the clone) | Result |
|---|---|---|
| Java build + unit + integration tests | `mvn -B -f implementations/spring-boot/pom.xml clean verify` (JDK 25) | **BUILD SUCCESS**: 12/12 unit, `CatalogIT` 1/1, all 5 modules |
| .NET tests and benchmark build | `dotnet test Lab.Tests -c Release`, `dotnet build Lab.Benchmarks` (`LabTargetFrameworks=net10.0`) | 4/4, 0 errors |
| Dependency-free checks, report-tool tests | `check_offline.py`, `check_extended.py`, `python -m unittest test_report_generator` | pass |
| JMH smoke + report generation | `python tools/run_benchmark.py --smoke --count 10000 --suite cache` | report written |
| Suite definition | `python tools/run_http_suite.py --list` | 42 phases listed |
| Compose: Spring (default) | `docker compose up -d --build mysql mock-api app`; `compare_http.py`; `smoke_api.py` | both **pass** |
| Compose: Jakarta (`--profile jakarta`) | `compare_http.py` | **failed (404)** → defect **F14** found and fixed; repeated from a new clone: **pass** |
| Compose: .NET (`--profile dotnet`) | `compare_http.py` | **pass** |
| Compose: Redis overlay | `-f docker-compose.redis.yml up … redis app app2` (Jakarta: `jakarta jakarta2`, .NET: `dotnet dotnet2`); load via instance A, read via instance B | B served from Redis, 1 load |
| Chart regeneration | `python tools/make_charts.py` | content identical; output made deterministic (hash salt, no date) and verified byte-identical across two generations |
| Reset | `docker compose … down -v` | volumes removed; the next start re-seeds 100,000 products |

Not reproducible from the clone without extra downloads: the OpenTelemetry Java agent (`observability/agent.jar`, git-ignored, see [OBSERVABILITY.md](OBSERVABILITY.md)).

## 4. Release assessment

The project is a **reproducible engineering lab and reference**, not a production application and not a framework ranking. All eight labs have implemented, tested and measured core scenarios in all three frameworks where the scenario applies. The gaps (✖ above) are deliberate scope limits or listed future work, not hidden failures.
