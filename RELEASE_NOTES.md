# Release notes

## Unreleased (after v1.0.0)

- **Lab 08: Redis on all three editions.** The shared-cache experiment now runs on Jakarta EE (Jedis 8, pooled connections) and ASP.NET Core (StackExchange.Redis 3, one multiplexed connection) as well as Spring (Lettuce), with a second instance of each edition in `docker-compose.redis.yml`.
- **New measurement: Redis client behaviour.** Hit latency at 2,000 req/s, and an outage probe (Redis stopped / paused) with identical 500 ms timeouts. Main result: the clients differ little on a hit but a lot during an outage (507 / 4 / 1,000 ms per request; Jedis recovery 9.5 s, caused by the JVM's negative DNS cache and confirmed by an A/B run). See [Lab 08 §7.4](labs/08-resource-management/README.md#74-redis-clients-compared) and [report §3.8](reports/BENCHMARK_REPORT.md).
- README technology table and CI status brought up to date.

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
- NuGet packages with moderate advisories (NU1902) should be updated before the code is reused elsewhere.
- The OpenTelemetry Java agent is not committed; download it as described in [OBSERVABILITY.md](docs/OBSERVABILITY.md).
