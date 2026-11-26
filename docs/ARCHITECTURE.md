> Scope: original Spring Boot cache edition (v0.1). For the expanded implementation, see the [root README](../README.md), [coverage](ROADMAP.md) and [extended protocol](EXPERIMENT_PROTOCOL.md).

# Architecture and developer guide

## Decision record

| Decision | Reason | Cost / alternative |
|---|---|---|
| One Spring Boot application | Establish a small, reproducible baseline | No cross-framework implementation yet |
| A pure Java `cache-core` module | JMH measures the exact production cache algorithms without HTTP/DI/DB | Extra Maven module, no extra deployment |
| Spring JDBC instead of JPA | The experiment depends on precise SQL, transaction snapshots, trigger visibility and acknowledgement | Manual mapping; JPA is a later comparison, not inherently worse |
| Immutable record values | No concurrent mutation of a cached product | Replacing a product allocates a new value |
| Cache interface + one DI bean | Same consumer code for all strategies; shared application lifetime | Scope alone does not guarantee thread safety |
| Fixed-delay refresh | Avoid building up scheduled overlapping executions | Actual refresh cadence includes execution time |
| Explicit writer lock | Manual and timer paths cannot refresh concurrently | One cache refresh at a time; no distributed writer lock |
| MySQL journal | Demonstrates a commit-visible change mechanism on the existing three-column product model | Triggers, storage and cleanup overhead; single consumer |
| SQL startup schema | Small disposable local environment; transparent DDL | No production versioned migration management |
| Java 25, Boot 4.2.0 | Modern baseline; fixed framework version | Exact image digests and JDK patch not locked yet |

No message broker, frontend SPA, Redis, ORM, domain event framework or enterprise identity provider is required for this release.

## Source map

```text
implementations/spring-boot/
  pom.xml                       # Maven reactor and version management
  cache-core/
    src/main/java/de/backendlab/cache/
      Product.java              # immutable product; nullable timestamp
      ProductCache.java         # common access + refresh contract
      ProductPage.java          # shared filter, sort and slice
      Changes.java              # disjoint upsert and delete sets
      UnsafeCache.java          # deliberate negative example
      LockedCache.java          # global synchronized monitor
      ConcurrentCache.java      # concurrent map + serialized writers
      SnapshotCache.java        # immutable map publication
      CaffeineCache.java        # unbounded library cache
      CacheFactory.java         # named strategy construction
      ProductGenerator.java     # deterministic fixture
      Watermark.java            # teaching cursor
    src/test/java/...           # unit and concurrency tests
  app/
    src/main/java/de/backendlab/
      BackendLabApplication.java
      config/LabConfiguration.java
      catalog/ProductController.java
      catalog/ProductStore.java
      labs/cache/RefreshCoordinator.java
      labs/cache/CacheLifecycle.java
      labs/cache/CacheStatusController.java
      labs/cache/LabController.java
    src/main/resources/application.yml
    src/main/resources/schema.sql
    src/test/java/.../CatalogIT.java
  benchmarks-jmh/
    src/main/java/.../CacheBenchmark.java
```

## Runtime request flow

1. Spring creates one `ProductCache` bean from configuration. The default bean lifetime is singleton.
2. `ProductStore` uses Spring JDBC and a managed datasource. The cache holds detached immutable values, never a JDBC connection or ORM entity session.
3. `CacheLifecycle.run` seeds a new empty database once, reads a consistent snapshot, publishes the cache and marks it ready.
4. GET requests use the cache only. Pagination returns immutable response items and an observed total.
5. POST/PUT/DELETE requests write to MySQL. The triggers are part of the same database transaction. The cache catches up later.
6. The fixed-delay scheduled job calls `RefreshCoordinator.refresh`. The manual endpoint is only registered under the `lab` profile. Both share one writer lock.
7. Application shutdown discards the cache. Startup reconstructs it from authoritative data.

## Dependency injection and design principles

`ProductController` and `RefreshCoordinator` depend on the `ProductCache` abstraction. `LabConfiguration` is the composition root choosing the concrete strategy. Changing the strategy should not require changes to the consumer code. This illustrates Dependency Inversion and Open/Closed in a bounded example, not a claim that a factory switch can never change: adding a strategy requires registration.

Constructor injection exposes required dependencies. A request is not allowed to create a new 100,000-product cache. Conversely, using a singleton does not make arbitrary shared fields safe. Cache implementations choose the appropriate synchronization primitive. Request-specific search and pagination are method parameters, not fields on the singleton controller.

## Cache guarantees

`LockedCache` protects page construction and whole-batch modification with the same monitor. `SnapshotCache` serializes writers and atomically publishes a new immutable map; readers capture a single reference before traversing it. `ConcurrentCache` and `CaffeineCache` serialize writers but intentionally permit readers during batch application. Their values remain safe, but a page can observe an old and a new value together. `UnsafeCache` deliberately shares a mutable HashMap with no synchronization; concurrent traversal can fail.

The common page implementation copies matching entries into a sorted list, slices the result and returns an immutable list. It uses the same algorithm for every strategy to keep the first experiment focused on synchronization. It is O(n log n) in the worst case, and no snapshot consistency is guaranteed across multiple page requests. An optimized sorted index is a separate experiment.

## Adding a cache strategy

1. Implement all `ProductCache` methods with explicit semantics for batch updates, replacement, traversal and deletion.
2. Validate immutable value and duplicate-ID assumptions.
3. Register a name in `CacheFactory`. Guard intentionally unsafe implementations in `LabConfiguration`.
4. Add it to the sequential contract tests. Add appropriate concurrent correctness tests; do not assert stronger guarantees than the implementation offers.
5. Add it to JMH only if it satisfies the correctness requirements for the measured workload. Do not use a faster broken implementation as a winner.
6. Document limitations in `labs/01-product-cache/EVALUATION.md`.

## Adding later labs

Add a feature package inside `app/src/main/java/de/backendlab/labs/`, and a plain Java module only where isolation or microbenchmark reuse justifies it. Use separate experiment endpoints under `/lab/`; keep them behind the lab profile. Keep test fixtures and API contracts portable. Add JMH classes in the same benchmark module when the code can be invoked directly. Future framework editions will live under separate `implementations/` directories and run independently.

## Security and configuration

Local-only binding is a safety boundary, not authentication. Keep `.env` outside version control. The schema setup uses a MySQL user with schema-level privileges, and the local server enables `log_bin_trust_function_creators` to allow the trigger setup. The supplied JDBC URLs also disable TLS and allow public-key retrieval for isolated local MySQL connectivity. Do not reuse these policies on a production server. Use proper migrations, least-privilege accounts, authentication, TLS and explicit operational procedures in a real deployment.
