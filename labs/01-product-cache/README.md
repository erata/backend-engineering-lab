# Lab 01 — Product cache and incremental synchronization

> Use case: **"Show a 100,000-product catalogue, 10 at a time, from memory, while a background job keeps it in sync with MySQL."**
> Related reading: [EVALUATION.md](EVALUATION.md) (design discussion), [SYNCHRONIZATION.md](../../docs/SYNCHRONIZATION.md) (journal vs watermark), [consolidated benchmark report](../../reports/BENCHMARK_REPORT.md).

## 1. Scenario

A product has `id`, `name` and a nullable `lastUpdatedTime`. On startup every product is loaded into an in-memory cache. Every 10 seconds a refresh job applies the database changes since the previous refresh (inserts, renames, deletes). HTTP readers keep reading **during** the refresh. Newly inserted rows have `lastUpdatedTime = NULL`, which breaks naive timestamp-based change detection.

Two independent questions are studied:

| Question | Where it is answered |
|---|---|
| *Which changes must the refresh apply?* (change detection) | Journal vs watermark vs full reload — [SYNCHRONIZATION.md](../../docs/SYNCHRONIZATION.md) |
| *How are those changes published safely to concurrent readers?* (in-memory structure) | Five cache strategies — this document |

## 2. Invariants (what "correct" means)

1. After the first load, `size() == 100000` and pages are sorted by id (`page=2,size=10` starts at id 11).
2. A product inserted with a NULL timestamp, a rename and a delete all become visible after the next refresh.
3. A reader never sees a corrupted structure or an exception caused by concurrent writes.
4. **Batch atomicity (strategy-dependent):** `synchronized` and `snapshot` guarantee that a page reflects either the whole previous batch or the whole next batch. `concurrent` and `caffeine` guarantee per-key safety only (weakly consistent pages). `unsafe` guarantees nothing and exists as a negative example.

## 3. Strategies and implementations

| Strategy | Java (Spring + Jakarta share it) | .NET | Read path | Write path |
|---|---|---|---|---|
| `unsafe` | [UnsafeCache](../../implementations/spring-boot/cache-core/src/main/java/de/backendlab/cache/UnsafeCache.java) – plain `HashMap` | `Dictionary` without lock | no synchronization | mutate in place — **data race** |
| `synchronized` | [LockedCache](../../implementations/spring-boot/cache-core/src/main/java/de/backendlab/cache/LockedCache.java) – one monitor | `Dictionary` + `lock` | takes the global monitor | mutate under monitor |
| `concurrent` | [ConcurrentCache](../../implementations/spring-boot/cache-core/src/main/java/de/backendlab/cache/ConcurrentCache.java) – `ConcurrentHashMap` | `ConcurrentDictionary` | lock-free get | per-key put/remove |
| `snapshot` (default) | [SnapshotCache](../../implementations/spring-boot/cache-core/src/main/java/de/backendlab/cache/SnapshotCache.java) – `AtomicReference<Map>` of an immutable map | `ImmutableDictionary` + `Interlocked.Exchange` | one volatile read, no lock | copy whole map, apply batch, publish new reference |
| `caffeine` / `library` | [CaffeineCache](../../implementations/spring-boot/cache-core/src/main/java/de/backendlab/cache/CaffeineCache.java) (no eviction/TTL) | `IMemoryCache` + key set | library lookup | per-key put/invalidate |

Framework wiring:

- **Spring Boot**: `LAB_CACHE_STRATEGY` selects the bean in [LabConfiguration](../../implementations/spring-boot/app/src/main/java/de/backendlab/config/LabConfiguration.java); [RefreshCoordinator](../../implementations/spring-boot/app/src/main/java/de/backendlab/labs/cache/RefreshCoordinator.java) serializes writers with a `ReentrantLock` and acknowledges journal rows; [CacheLifecycle](../../implementations/spring-boot/app/src/main/java/de/backendlab/labs/cache/CacheLifecycle.java) runs the `@Scheduled` refresh.
- **Jakarta EE**: [Catalog](../../implementations/jakarta-ee/src/main/java/de/backendlab/ee/Catalog.java) is an `@ApplicationScoped` CDI bean that uses the same Java cache classes, plain JDBC and `ManagedScheduledExecutorService`.
- **ASP.NET Core**: `Catalog` and `RefreshWorker` (a `BackgroundService` with `PeriodicTimer`) in [Program.cs](../../implementations/aspnet-core/Lab.Api/Program.cs), using ADO.NET via MySqlConnector.

Change detection is the same in all three editions: MySQL triggers write every insert/update/delete into `product_changes` ([schema.sql](../../implementations/spring-boot/app/src/main/resources/schema.sql)). The refresh reads a bounded batch, re-reads those products, applies upserts and deletes as one `Changes` batch, and deletes exactly the journal rows it consumed, all in one REPEATABLE READ transaction.

## 4. Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | `/api/products?page=1&size=10&search=` | Sorted, filtered page from the cache. `size` 1..100 |
| GET | `/api/products/{id}` | Single cached product, 404 if absent |
| POST/PUT/DELETE | `/api/products[/{id}]` | Writes go to MySQL; visible in the cache **after the next refresh** |
| GET | `/api/cache/status` | Size and sync strategy |
| POST | `/lab/cache/refresh` | Manual refresh (lab profile only) |

## 5. How to run

```powershell
$env:SPRING_PROFILES_ACTIVE='lab'; $env:LAB_CACHE_STRATEGY='snapshot'   # or synchronized | concurrent | caffeine
docker compose up -d --build --force-recreate mysql mock-api app
python tools/compare_http.py --url http://localhost:8080                # functional contract first
```

## 6. Benchmarks in this lab

### 6.1 JMH `CacheBenchmark` (method level, no HTTP)

Source: [CacheBenchmark.java](../../implementations/spring-boot/benchmarks-jmh/src/main/java/de/backendlab/bench/CacheBenchmark.java). Runner: `python tools/run_benchmark.py --suite cache --count 100000`.

| Benchmark | Threads | What one "op" is | Why it exists |
|---|---|---|---|
| `readOnly` | 4 readers | one `get(id)` for a pseudo-random id (fixed seed, 4096-key trace per thread) | cost of the read path when there is no writer |
| `mixed` (group) | 4 readers + 1 writer | reader op = one `get(id)`; writer op = one **batch** of 16 upserts | how much a continuously running writer hurts readers, and what a batch costs |

Settings: 2 forks, 3×2 s warm-up, 5×2 s measurement, `-Xms1g -Xmx1g`, `-prof gc`. The writer runs flat out, which is a stress case. The real refresh runs once every 10 s. `unsafe` is excluded because a fast wrong answer is not a result.

### 6.2 k6 HTTP benchmarks (end to end)

Run by `tools/run_http_suite.py`, backend limited to 4 CPUs / 2 GB:

| Experiment | Request | Rate | What it shows |
|---|---|---|---|
| `catalog-get` | `GET /api/products/42` | 2,000 req/s, 30 s | framework + JSON + cache lookup latency |
| `catalog-page` | `GET /api/products?page=500&size=20` | 50 req/s, 30 s | cost of building a sorted page over 100K entries per request |

## 7. Measured results

Environment for all numbers: Intel i7-13700H (20 logical CPUs), 32 GB RAM, Windows 11, Temurin 25.0.4.1. Raw data: [reports/runs/20261126T194918342533Z](../../reports/runs/20261126T194918342533Z/).

### 7.1 JMH read-only (4 threads, 100K products)

| Strategy | Throughput (ops/s) | ± error (99.9%) | Alloc (B/op) | Relative to `synchronized` |
|---|---:|---:|---:|---:|
| synchronized | 4.62 M | 0.46 M | 40 | 1.0× |
| concurrent | 62.8 M | 4.8 M | 40 | 13.6× |
| **snapshot** | **88.1 M** | 7.2 M | 16 | **19.1×** |
| caffeine | 48.0 M | 17.3 M | 40 | 10.4× |

Caffeine's wide error comes from two low iterations (≈29 M ops/s) among otherwise 50–61 M iterations. That is a sign of run-to-run noise on this workstation, not a stable property. Repeat the run before relying on the Caffeine number.

### 7.2 JMH mixed (4 readers + 1 writer)

| Strategy | Reader ops/s | Writer batches/s | GC time during run | Comment |
|---|---:|---:|---:|---|
| synchronized | 1.49 M | 902 K | 16 ms | readers and the writer fight for one monitor; reads drop 3× vs read-only |
| concurrent | 34.3 M | 615 K | 122 ms | readers almost unaffected; batches are not atomic |
| **snapshot** | **43.0 M** | **33.4** | **2,163 ms** | readers are fastest, but each batch copies 100K entries (~30 ms per batch) |
| caffeine | 43.2 M | 626 K | 114 ms | similar to concurrent; batches are not atomic |

### 7.3 k6 HTTP, Spring Boot / Java 25 / platform threads (4 CPUs, 2 GB)

All rows come from the same suite run ([reports/http-runs/20261126T202650Z](../../reports/http-runs/20261126T202650Z/REPORT.md)), with a 10 s warm-up before each measured 30 s window. Latency in ms.

| Strategy | `catalog-get` 2,000/s: p50 / p95 / p99 | dropped | `catalog-page` 50/s: p50 / p95 / p99 |
|---|---|---:|---|
| synchronized | 0.87 / 16.5 / 47.6 | 36 | 10.5 / 35.5 / **120.8** |
| concurrent | 1.16 / 52.6 / 101.0 | 384 | 8.4 / 13.5 / 19.8 |
| snapshot | 1.02 / 28.4 / 79.2 | 164 | 7.9 / 12.6 / 17.8 |
| caffeine | 0.92 / 19.8 / 50.5 | 5 | 8.2 / 12.6 / 16.1 |

Cross-framework, same snapshot strategy: see the [consolidated report](../../reports/BENCHMARK_REPORT.md#31-lab-01--product-cache).

**How to read this:** at the HTTP level a single-key lookup (nanoseconds) is invisible next to Tomcat, Jackson and the network (about a millisecond). The `catalog-get` spread between strategies is run-to-run noise in the p95/p99 tail, not a ranking. For example, `concurrent` is the fastest map in JMH and has the worst tail here. Paging is different: `synchronized` holds its monitor during the ~8 ms filter-and-sort, so concurrent page requests queue behind each other and p99 rises to 121 ms. The lock-free strategies stay below 20 ms.

## 8. Interpretation

- **A single monitor caps read scalability.** Even with no writer, four threads reach only 4.6 M ops/s, against 63–88 M ops/s for the lock-free reads, because every `get` serializes. In the mixed run the writer keeps the monitor hot and readers lose another 3×.
- **Snapshot gives the best read path and atomic batches, and pays at write time.** One volatile read plus an immutable-map lookup is the cheapest read measured. But a 16-product batch copies the whole 100K map: 33 batches/s and about 2.2 s of GC per measurement window under continuous writes. With the real 10-second refresh, that is one ~30 ms copy every 10 s, which is negligible. If the catalogue changed hundreds of times per second, the snapshot would be the wrong choice.
- **Concurrent / Caffeine are the balanced choice when pages may be weakly consistent.** Writers are ~18,000× cheaper than snapshot batches, and reads remain within 20% of snapshot.
- **Paging is the real hot spot, not the map.** `ProductPage.from` filters and sorts all 100K entries on every page request, whatever the strategy (see `catalog-page`). A pre-sorted array published together with the snapshot would remove that cost. It is listed as a follow-up in [ROADMAP.md](../../docs/ROADMAP.md).

## 9. Trade-offs and decision

| Need | Choose |
|---|---|
| Atomic, consistent pages; rare refreshes; read-heavy | **snapshot** (default) |
| Frequent writes; per-product independence acceptable | concurrent (or Caffeine if eviction/TTL/statistics are needed later) |
| Simplest correct code; low concurrency | synchronized |
| Never | unsafe |

## 10. Limitations

- JMH measures cache classes only; there is no JMH/BDN equivalent for the .NET cache variants yet.
- One machine, one JMH run per configuration, shared with other idle containers; treat differences below ~10–15% as noise.
- The page benchmark uses one fixed page/size; search terms were not benchmarked.
