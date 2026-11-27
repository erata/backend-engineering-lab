# Experimental API reference

Lab routes are local-only. Enable them with Spring `SPRING_PROFILES_ACTIVE=lab`; the Jakarta and .NET Compose services set `LAB_ENABLED=true`. Default host ports are 8080 (Spring), 8081 (Jakarta), 8082 (.NET) and 8083 (second Spring instance, Redis overlay); override them with `LAB_PORT`, `JAKARTA_PORT`, `DOTNET_PORT` and `LAB_PORT2`. The benchmark suite uses 18080–18083.

Field names match across editions wherever the experiment exists in more than one; error payloads differ.

## Lab 01 – cache

| Method / route | Editions | Notes |
|---|---|---|
| `GET /api/products?page&size&search`, `GET /api/products/{id}` | all | served from the in-memory cache |
| `POST/PUT/DELETE /api/products[/{id}]` | all | MySQL; visible in the cache after the next refresh (≤ 10 s) |
| `GET /api/cache/status`, `POST /lab/cache/refresh` | all | status / manual refresh |

## Lab 02 – concurrency

| `POST /lab/concurrency/reserve?mode=unsafe\|lock\|atomic&stock&requests` | all | `{accepted, remaining, correct}`; new state per call |
|---|---|---|

## Labs 03 / 04 – I/O and threads

| Route | Editions | Notes |
|---|---|---|
| `GET /lab/io/{blocking\|sequential-async\|concurrent}` | all | three upstream calls (100/200/300 ms). .NET `blocking` = sync-over-async |
| `GET /lab/io/concurrent-blocking?threadModel=platform\|virtual` | Spring | blocking calls fanned out to a platform pool or virtual threads |
| `GET /lab/io/blocking-async?executor=default\|virtual` | Jakarta | blocking chain on a managed executor (`virtual` = Concurrency 3.1 `@ManagedExecutorDefinition(virtual=true)`), async JAX-RS response |
| `GET /lab/threads/info` | all | runtime version, request thread, `virtual` flag (Java), processors and ThreadPool size (.NET) |
| `GET /lab/threads/executor?executor=default\|virtual` | Jakarta | thread name and `virtual` flag **inside** a task on the managed executor |
| `GET /lab/threads/pinning?mode=synchronized\|reentrant&tasks=100&sleepMs=50` | Spring, Java 21+ | `tasks` virtual threads sleep while holding a private lock; `elapsedMs`, `carriers` |

## Lab 05 – CPU

| `GET /lab/cpu/{sequential\|parallel}?count&rounds&workers` | all | `{checksum, elapsedNs, processors}`; checksum identical in Java and .NET |
|---|---|---|

## Lab 06 – dependency injection

| Route | Spring | Jakarta (CDI) | .NET |
|---|---|---|---|
| `GET /lab/di/instances?mode=request\|shared` | `@RequestScope` / singleton | `@RequestScoped` / `@ApplicationScoped` | scoped / singleton |
| `GET /lab/di/captive?mode=…` | `captured` (prototype in singleton) / `provider` (`ObjectProvider`) | `captured` (`@Dependent` in `@ApplicationScoped`) / `provider` (`Instance<T>`) | `captured` (scoped in singleton) / `scoped` |
| `GET /lab/di/mutable?mode=singleton\|request&user=X&delayMs=5` | singleton field / request-scoped bean | application- / request-scoped bean | singleton / scoped | 
| `GET /lab/di/ownership?mode=…&n=100` | `container` / `caller` (prototype `@PreDestroy`) | `leak` / `destroy` (`Instance.get()` vs `destroy()`) | `root` / `scope` (disposable transient) |
| `GET /lab/di/background?mode=plain\|activated` | – | request-scoped bean used from a managed-executor task, without / with `@ActivateRequestContext` | – |

`mutable` returns `{expected, actual, correct}`; `ownership` returns `{created, closed|destroyed|disposed}`.

## Lab 07 – events

| Route | Spring (Hikari + Spring TX) | Jakarta (JTA) | .NET (MySqlConnector) |
|---|---|---|---|
| `POST /lab/events/price-change?id&cents&mode&rollback&failAudit` | `direct`, `event` (async AFTER_COMMIT), `event-inline` (negative) | `direct`, `event` (AFTER_SUCCESS → managed executor), `event-inline` | `direct`, `event` (transactional outbox) |
| `GET /lab/events/state?id` | `{auditCount, cents}` | same | `+ outboxPending` |

`rollback=true` throws after the update (HTTP 500, nothing persists). `failAudit=true` makes the audit side effect fail: in `direct` mode the whole change rolls back; after commit it is lost (Spring/Jakarta) or retried from the outbox (.NET).

## Lab 08 – resources and caching

| Route | Editions | Notes |
|---|---|---|
| `GET /lab/resources/stampede?single&requests` | all | in-process single-flight |
| `GET /lab/resources/pool?requests&permits` | all | semaphore model of a scarce resource |
| `GET /lab/resources/db?pool=5\|20&ms=30` | all | **real** JDBC/ADO.NET pool; holds a connection for `SELECT SLEEP(ms)`; 503 when no connection is free in time |
| `GET /lab/redis/product/{id}?mode=none\|local\|distributed` | Spring + Redis overlay | Redis cache-aside, MySQL + 100 ms on a miss; falls back to MySQL when Redis is down (`source: db-fallback`) |
| `POST /lab/redis/invalidate?id`, `POST /lab/redis/reset?id`, `GET /lab/redis/loads?id` | Spring + Redis | invalidation, reset, cross-instance load counter |

The common catalogue contract is [OpenAPI](../shared/contracts/openapi.yaml). `tools/compare_http.py` exercises the shared lab routes on every edition.
