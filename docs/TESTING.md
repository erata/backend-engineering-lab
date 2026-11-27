> Scope: original Spring Boot cache edition (v0.1). For the expanded implementation, see the [root README](../README.md), [coverage](ROADMAP.md) and [extended protocol](EXPERIMENT_PROTOCOL.md).

# Correctness and integration testing

Correctness is a prerequisite to interpreting performance. A passing negative test means the expected defect was demonstrated, not that the broken strategy is suitable for production.

## Test catalogue

| Test | Intended assertion | Execution status in delivered package |
|---|---|---|
| `CacheContractTest.singleThreadContract` | All five strategies agree on seed, pagination, search, insert/update/delete, immutability and invalid input | Passed (JDK 25, 2026-11-26) |
| `unsafeIteratorFailsWithControlledWriter` | Structural modification invalidates the existing HashMap iterator | Offline equivalent passed |
| `atomicBatchPagesNeverMixGenerations` | Readers see a complete version with locked and snapshot caches | Offline equivalent passed |
| `concurrentReadersAndWriterPreserveIndividualRecords` | ConcurrentHashMap/Caffeine preserve tested record-level properties and final state | Passed, including Caffeine |
| `RaceConditionTest` | Two reads of zero followed by writes produce a lost update; atomic and locked increments preserve both | Offline equivalent passed |
| `WatermarkTest` | A new null-timestamp product advances ID without changing timestamp | Passed; not a DB test |
| `CatalogIT` | MySQL startup, actual HTTP pagination, insert null timestamp, rename, delete, late commit contrast, rollback | Passed |
| `CacheBenchmark` | JMH read-only and mixed workload | Executed, see [benchmark report](../reports/BENCHMARK_REPORT.md) |

The race uses a barrier to force both workers to read before either writes. This is a controlled interleaving, not a flaky test that hopes a race occurs on a fast laptop. The unsafe iterator test uses a completed Future to make the structural modification observable before the next traversal step. HashMap fail-fast behaviour is best-effort in unconstrained concurrent use; this does not imply every race throws.

For the atomic page test, a batch assigns one generation name to all ten records. Concurrent readers require that the page has ten items and one generation. The tests exercise concurrent reads and writes but are not a formal proof for every JVM schedule. The weakly consistent caches are not required to produce a mixed page in a particular run. They are tested against weaker invariants and documented separately.

## Repeat locally

From repository root with JDK 25 and Maven:

```bash
mvn -B -f implementations/spring-boot/pom.xml test
mvn -B -f implementations/spring-boot/pom.xml -pl app -am verify
mvn -B -f implementations/spring-boot/pom.xml verify
```

`test` runs Surefire unit tests. `verify` also runs Failsafe `*IT` integration tests and builds the benchmark artifact if the full reactor is selected. Docker must be running for Testcontainers. The integration test does not skip itself when Docker is unavailable; a full validation must fail clearly rather than silently omit the database test.

To focus on the pure Java tests:

```bash
mvn -B -f implementations/spring-boot/pom.xml -pl cache-core test
```

Inspect `target/surefire-reports` and `target/failsafe-reports` beneath the relevant modules. GitHub Actions runs Java 25 `verify`, uploads test reports, attempts a short JMH smoke run, and then executes a Docker Compose HTTP smoke test. It does not publish framework rankings from shared CI runners.

## Offline fallback

```bash
python tools/check_offline.py
```

Requires `java` and `javac` on PATH (JDK 21+). It compiles only dependency-free cache sources and the standalone `OfflineChecks` harness to a temporary directory. It excludes Caffeine and `CacheFactory` because Maven dependencies are required for them. It does not run the Spring server, JUnit, Testcontainers or JMH. The observed output is available in `reports/OFFLINE_CHECKS.txt`.

## Integration environment

`CatalogIT` runs a fresh MySQL 8.4 container and Spring Boot random-port server. It starts with 100,000 products and uses a one-hour scheduler interval to control refresh manually. The late commit test explicitly allocates lower and higher IDs in separate transactions; only the higher transaction commits before the first refresh. The second refresh should demonstrate the baseline miss and journal recovery. No external live database or production records are used.

## Manual smoke run

Use a new Compose database and the safe journal strategy. Enable `SPRING_PROFILES_ACTIVE=lab`, run the app, then run `python tools/smoke_api.py`. It waits for readiness, checks pagination and invalid input, creates a new product with a null timestamp, manually refreshes, renames and deletes it. Run it only on disposable data with no competing writers.

## Report formatter tests

Run `python -m unittest discover -s tools -p 'test_*.py' -v`. Two unit tests exercise Markdown formatting and undefined score errors using synthetic temporary fixtures. They are not benchmark measurements.

## Not yet covered

Full database outage/restart injection, large backlogs, real load and latency percentiles, multiple consumer coordination, JVM stress tools such as JCStress, distributed cache consistency, and production security are planned experiments. Passing a small test suite does not establish these guarantees.
