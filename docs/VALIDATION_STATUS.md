# Validation status

Last full validation: **2026-11-26** on Windows 11 (Intel i7-13700H, 20 logical CPUs, 32 GB). Toolchain: Temurin JDK 25.0.4.1, Maven 3.9.6, .NET SDK 10.0.404, Docker 29.5 (Rancher Desktop), Python 3.13, k6 1.3.0 (container).

## 1. Build and test evidence

| Check | Command | Result |
|---|---|---|
| Maven reactor (cache-core, app, JMH, Jakarta WAR) | `mvn -B -f implementations/spring-boot/pom.xml verify` (JAVA_HOME = JDK 25) | **Pass** after fix F1 |
| cache-core unit tests (5 strategies, race, watermark) | surefire | **12 / 12 pass** |
| Spring MySQL integration test (Testcontainers, journal, null timestamps, late commit) | failsafe `CatalogIT` | **1 / 1 pass** (131 s) |
| .NET 10 build + xUnit | `dotnet test Lab.Tests` with `LabTargetFrameworks=net10.0` | **4 / 4 pass** |
| .NET 11 | Docker `sdk:11.0` / `aspnet:11.0` images | **builds and runs** (HTTP suite phase `dotnet11-snapshot`); local xUnit not run, because no .NET 11 SDK is installed |
| Python report tool tests | `python -m unittest test_report_generator` (in `tools/`) | **2 / 2 pass** |
| Common HTTP contract smoke, Spring (Docker) | `python tools/compare_http.py --url http://localhost:18080` | **Pass** |
| Common HTTP contract smoke, Jakarta / WildFly 42 | same, port 18081 | **Pass** after fixes F2, F3 |
| Common HTTP contract smoke, ASP.NET Core .NET 10 | same, port 18082 | **Pass** |
| Domain events semantics (direct / event / rollback) | manual + MySQL audit count | **Pass** on all three after fixes F3, F4 |
| JMH full suite | `tools/run_benchmark.py --suite all` | **Completed**, see [report](../reports/BENCHMARK_REPORT.md) |
| BenchmarkDotNet (.NET 10) | `Lab.Benchmarks --filter *` | **Completed** after fix F5 |
| k6 HTTP suite, 3 backends, Java 17/25, platform/virtual, .NET 10/11, CPU quotas 1/2/4/8 | `tools/run_http_suite.py` | **Completed**, see [report](../reports/BENCHMARK_REPORT.md) |

## 2. Defects found and fixed during validation

| # | Area | Symptom | Cause | Fix |
|---|---|---|---|---|
| F1 | JMH build | `Cannot find 'resource' in class ManifestResourceTransformer` | `spring-boot-starter-parent` pre-configures shade transformers. Maven merged them into the JMH module's list | `<transformers combine.self="override">` in [benchmarks-jmh/pom.xml](../implementations/spring-boot/benchmarks-jmh/pom.xml) |
| F2 | Jakarta deployment | WildFly: `WELD-000075 Normal scoped managed bean implementation class has a public field: Catalog.sync`. Nothing deployed (404) | CDI forbids public fields on normal-scoped beans, because clients only hold a proxy | field made private + `sync()` accessor ([Catalog.java](../implementations/jakarta-ee/src/main/java/de/backendlab/ee/Catalog.java)) |
| F3 | Jakarta events | `auditCount` always 0 | `EventResource` read `book.count` / `book.prices` **fields** through the `@ApplicationScoped` client proxy, so it saw the proxy's own copy, not the bean's state | accessor methods `price()`, `auditCount()` ([EventResource.java](../implementations/jakarta-ee/src/main/java/de/backendlab/ee/EventResource.java)) |
| F4 | Spring events under load | at 200 req/s every request hung for 10 s+; the app stopped serving even non-DB routes | **connection-pool deadlock**: the AFTER_COMMIT listener used `REQUIRES_NEW` on the request thread while the committed outer connection was still checked out. 10 concurrent requests held all 10 Hikari connections and each waited for an 11th (`active=10, idle=0, waiting=198`) | `event` mode now runs the listener `@Async` on a bounded 2-thread executor. The old behaviour is kept as the documented negative mode `event-inline` ([EventController.java](../implementations/spring-boot/app/src/main/java/de/backendlab/labs/EventController.java), [Lab 07](../labs/07-domain-events/README.md)) |
| F5 | .NET build without .NET 11 SDK | `NETSDK1045` for `net11.0`. BenchmarkDotNet's generated project failed, so 0 benchmarks executed | hard-coded `net10.0;net11.0` multi-targeting | overridable `LabTargetFrameworks` property (default unchanged) in all three `.csproj` |
| F6 | Benchmark harness | under load the mock upstream could refuse connections | Python `socketserver` backlog of 5, HTTP/1.0 (no keep-alive) | backlog 4096, HTTP/1.1, daemon threads ([server.py](../infrastructure/mock-api/server.py)) |
| F7 | Local ports | `Bind for 127.0.0.1:8080 failed: port is already allocated` | Jakarta/.NET host ports were hard-coded | `JAKARTA_PORT`, `DOTNET_PORT` overrides next to the existing `LAB_PORT` |

## 3. Environment notes

- Maven must run on JDK 25 (`maven.compiler.testRelease=25`). On a machine where `JAVA_HOME` points to an older JDK the build fails with `Releaseversion 25 nicht unterstützt` / `release version 25 not supported`.
- An empty `log4j-bom-2.26.1.pom` in the local Maven repository (from an interrupted download) breaks POM processing. Deleting the folder fixes it.
- NuGet reports moderate advisories for `MySqlConnector 2.4.0` and `OpenTelemetry.* 1.12.0` (NU1902). They don't affect the lab, but bump the versions before reusing the code elsewhere.

## 4. Still not validated

- Redis TTL demo (`tools/redis_lab.py`) and the Grafana/Tempo/Prometheus stack: not executed in this validation.
- GitHub Actions workflow: not executed (no remote repository).
- .NET 11 xUnit tests locally (only exercised through the Docker image).
- Advanced variants listed in [ROADMAP.md](ROADMAP.md) are not implemented, so they could not be validated.
