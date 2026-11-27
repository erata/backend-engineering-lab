# Release notes

## v1.1.0 — 2026-11-27

Same scope as v1.0.0 (eight labs, three editions). This release completes the Redis part of Lab 08 on every edition, corrects one wrongly confirmed explanation, fixes the dependency advisories and adds Dependabot. No other features.

### Added
- **Lab 08: Redis on all three editions.** The shared-cache experiment now runs on Jakarta EE (Jedis 8, pooled connections) and ASP.NET Core (StackExchange.Redis 3, one multiplexed connection) as well as Spring (Lettuce), with a second instance of each edition in `docker-compose.redis.yml`.
- **Redis client measurements.** Hit latency at 2,000 req/s (3–5 runs) and outages (Redis stopped, paused, process killed; 5 runs each) with 500 ms timeouts in every client, plus one A/B per client: Lettuce queue vs `REJECT_COMMANDS`, Jedis with JVM DNS cache settings, StackExchange.Redis heartbeat 1,000 / 500 / 100 ms. Result: the clients differ little on a hit but a lot during an outage (~510 / 8–510 / ~1,000 ms per request); each explanation is classified as confirmed, hypothesis or unresolved. See [Lab 08 §7.4–7.5](labs/08-resource-management/README.md#75-redis-outages) and [report §3.8](reports/BENCHMARK_REPORT.md).
- Lab 08: effective client settings table and diagrams (connection models, Lettuce disconnected behaviour, Jedis DNS paths, StackExchange.Redis heartbeat); two new charts.
- Every lab README states the test machine and why it limits the results.
- `.github/dependabot.yml`: weekly updates for Maven, NuGet, Dockerfiles, Compose images and GitHub Actions. Major upgrades of libraries and images are ignored because they would change the benchmarked system; security alerts still apply.

### Fixed
- **Correction (F15):** the first single outage run reported a Jedis/DNS root cause as confirmed, based on a JVM system property that the JDK ignores. Repeated runs and a correctly applied setting changed the conclusion; see [VALIDATION_STATUS.md](docs/VALIDATION_STATUS.md) and [Lab 08](labs/08-resource-management/README.md#correction-what-the-first-single-outage-run-got-wrong).
- **Security:** the NuGet advisories of v1.0.0 (NU1902) — MySqlConnector 2.4.0 → 2.6.2 (latest 2.x, no major upgrade), OpenTelemetry 1.12.0 → 1.21.0. `dotnet list package --vulnerable --include-transitive` is clean; contract test and end-to-end telemetry re-run after the upgrade.
- README technology table, API table and CI status were out of date.

### Changed
- CI jobs named `spring` / `jakarta` / `dotnet` (the Spring job was called `verify`); GitHub Actions on their current major versions (Node 24).

### Verified
- Maven `clean verify` (12 unit + MySQL/Testcontainers), .NET xUnit 4/4, offline checks; HTTP contract on all three editions in Docker and in CI; Redis invariants on all editions (`distributed` → 1 load every round, stale until invalidation, DB fallback with 0 HTTP errors in 7,200 outage requests).
- Every new number in the docs recomputed from the raw runs; links and anchors checked; charts regenerate byte for byte; new Mermaid diagrams rendered.

### Known limitations (in addition to v1.0.0)
- Redis: one client per edition, so hit latency is an end-to-end framework + client measurement; outages are Docker-induced (stop, pause, process kill), not real network partitions or managed-service failovers.
- Open points: StackExchange.Redis's exact timeout rounding (500 ms heartbeat still gave 1,000 ms), the 2.3–2.8 s failing DNS lookup on Docker/WSL2, Lettuce's slow recovery after a killed process (hypothesis: reconnect back-off).
- The Redis lock is tested only with a healthy holder and a lease longer than the load; it has no fencing token.
- Java dependencies are covered by Dependabot alerts, not by a scanner in the build.

## v1.0.0

**Backend Engineering Lab: an engineering learning and reference laboratory.** It is not a production application and not a framework performance ranking.

### Scope

One product-catalogue scenario, implemented three times and used for eight labs:

| Edition | Stack |
|---|---|
| Spring Boot | Spring Boot 4.2, Java 25 (bytecode 17; also run on Java 17 and 21), Tomcat, Spring JDBC, Hikari, optional Redis |
| Jakarta EE | Jakarta EE 11 on WildFly 42, Java 25, JAX-RS, CDI, JTA datasources, Jakarta Concurrency 3.1 |
| ASP.NET Core | .NET 10 and .NET 11, minimal APIs, MySqlConnector |

| Lab | Topic |
|---|---|
| 01 | in-memory catalogue cache, five strategies, journal-based synchronization |
| 02 | race conditions: unsafe vs lock vs CAS |
| 03 | blocking vs sequential-async vs concurrent I/O |
| 04 | platform vs virtual threads, Java 17/21/25, WildFly virtual executor, .NET 10/11, pinning, ThreadPool starvation |
| 05 | multicore CPU parallelism under container CPU quotas |
| 06 | DI lifetimes, captive dependencies, shared mutable state, resource ownership, background contexts |
| 07 | direct orchestration vs after-commit events vs transactional outbox; rollback and handler failure |
| 08 | cache stampede, real connection pools, Redis shared cache across two instances |

The exact coverage per lab and framework, including what was deliberately left out, is in the [completion matrix](docs/ROADMAP.md).

### Verified

- Builds and tests from a fresh clone: Maven `clean verify` (12 unit tests + MySQL/Testcontainers integration test), .NET xUnit (4), dependency-free checks.
- The common HTTP contract test passes against all three editions in Docker, each Compose profile on its own.
- Measured results: JMH, BenchmarkDotNet and k6, with up to 5 repetitions for headline comparisons. All raw data is in `reports/`, and 31 headline numbers were recomputed from it for this release.
- Correctness probes for every lab invariant; OpenTelemetry metrics and traces verified end to end for all three editions.
- 14 defects found during validation and fixed ([VALIDATION_STATUS.md](docs/VALIDATION_STATUS.md)); unexpected results investigated ([investigations](reports/investigations/2026-11-27-anomalies.md)).
- Generated charts are reproducible byte for byte from the raw data; all 14 Mermaid diagrams render.

### Main results

See [reports/BENCHMARK_REPORT.md](reports/BENCHMARK_REPORT.md). Every number there is environment-specific: one laptop, Docker CPU quotas. Section 4 of the report separates confirmed root causes from hypotheses and unresolved findings.

### Known limitations

- Single workstation; headline comparisons repeated 3–5 times, other rows single runs.
- Transactional outbox in .NET only; Redis shared cache in Spring only (extended to all editions after v1.0.0, see above); no ORM experiments.
- Open observations (listed in the report and the roadmap): Jakarta's better hot-row behaviour, WildFly's CPU per request, and two smaller unexplained details.
- Lab endpoints are local-only and unauthenticated; negative modes exist on purpose.
- NuGet packages with moderate advisories (NU1902) should be updated before the code is reused elsewhere (done after v1.0.0, see above).
- The OpenTelemetry Java agent is not committed; download it as described in [OBSERVABILITY.md](docs/OBSERVABILITY.md).
