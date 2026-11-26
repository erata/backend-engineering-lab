# Lab 08 — Cache stampede, single-flight and capacity limits

> Use cases:
> 1. **"A popular product's cache entry expires and 100 requests arrive at once. How many of them hit the database?"** (stampede / single-flight)
> 2. **"The database allows only 5 concurrent connections. What happens to the 6th through 100th caller?"** (bounded resource with a wait budget)

## 1. Experiments

### 1.1 Stampede (`GET /lab/resources/stampede?single=true|false&requests=N`)

`N` concurrent tasks read a cold cache entry. A miss calls a loader that takes 20 ms and counts its invocations.

- `single=false`: every task that sees a miss loads → **N loads** in the worst case.
- `single=true`: double-checked loading under a lock (`synchronized` in Java, `SemaphoreSlim(1)` in .NET) → **exactly 1 load**.

### 1.2 Pool (`GET /lab/resources/pool?requests=N&permits=5`)

`N` concurrent tasks each try to acquire one of 5 permits (`Semaphore.tryAcquire(100 ms)` / `SemaphoreSlim.WaitAsync(100)`), hold it for 30 ms and release it. Reported: the highest number of permits held at once (`peak`) and the callers that gave up after 100 ms (`rejected`).

Code: `Experiments.stampede` / `Experiments.pool` ([Experiments.java](../../implementations/spring-boot/cache-core/src/main/java/de/backendlab/experiments/Experiments.java)), `Lab.Stampede` / `Lab.Pool` ([Program.cs](../../implementations/aspnet-core/Lab.Api/Program.cs)). Java tasks run on the caller's executor: Spring uses a fixed 32-thread pool, Jakarta its `ManagedExecutorService`. .NET uses `async` tasks with `Task.Delay`.

### 1.3 Redis (optional, not part of the measured suite)

`docker compose -f docker-compose.redis.yml up -d; python tools/redis_lab.py` shows two clients sharing a key and observing its TTL expiry. It is not a distributed single-flight or a Redis-backed product cache.

## 2. Invariants

- `single=true` ⇒ `loads == 1` for every N.
- `peak <= permits` always.
- Expected rejections: with 5 permits × 30 ms, about 5 × (100 / 30 + 1) ≈ 20 callers can be served within the 100 ms wait budget, **if all N callers really arrive at once**.

## 3. Results

Suite probe, 10 repetitions (stampede) and 5 repetitions (pool) per setting, run [20261126T222721Z](../../reports/http-runs/20261126T222721Z/REPORT.md).

| Edition | stampede N=32 single=false | N=100 single=false | N=32 / 100 single=true | pool N=32: peak / rejected | pool N=100: peak / rejected |
|---|---:|---:|---:|---|---|
| Spring Boot (32-thread pool) | 32 loads | **32** loads | 1 / 1 | 5 / 12 | 5 / 51–53 |
| Jakarta EE (managed executor) | **8** loads | **8** loads | 1 / 1 | 5 / 0–3 | 5 / 4–8 |
| ASP.NET Core (async tasks) | 32 loads | **100** loads | 1 / 1 | 5 / 12 | 5 / 80 |

All invariants held in every repetition: single-flight produced exactly one load, and the peak never exceeded 5 permits.

## 4. Interpretation

- **Single-flight works identically in all editions:** 1 load instead of 8–100. For an expensive query that is the difference between one DB call and a thundering herd.
- **The size of a stampede equals the *effective concurrency*, not the number of requests.**
  - .NET's async tasks really are 100 concurrent waiters → 100 loads, and 80 of 100 rejected in the pool test (≈ 20 served, as predicted).
  - Spring's 32-thread executor admits only 32 tasks at a time. The other 68 run after the first wave has filled the cache → 32 loads; pool: 51–53 rejected.
  - WildFly's default managed executor runs only **8** tasks concurrently here, so the "stampede" was 8 loads and almost nobody was rejected from the pool, because the executor queue acted as a second, invisible limiter.
- **Two limiters in series hide each other.** The Jakarta pool numbers look great (0–3 rejections) only because the executor already throttles concurrency to 8. Put the same code on virtual threads or async tasks and the semaphore suddenly rejects most callers. Always know *which* limit is the active one.
- **A semaphore does not add capacity, it decides who waits and who fails.** With 5 permits and 30 ms of work, throughput is capped at about 166 operations/s whatever the thread model.

## 5. Trade-offs

| Technique | Protects against | Cost / risk |
|---|---|---|
| Single-flight (per key) | stampede on cold/expired keys | callers wait for the leader; a failing leader must not poison the waiters |
| Stale-while-revalidate / early refresh | expiry spikes | serves slightly stale data |
| Bounded semaphore with timeout | overloading a scarce dependency | rejected callers need a fallback (HTTP 503, retry with backoff) |
| Unbounded queues | – | latency grows without limit; memory exhaustion |

## 6. Limitations

- Single-flight and the pool are in-process. Several application instances would still produce one load each (distributed single-flight needs a shared lock or request coalescing at a proxy).
- The pool is a simulation (`Semaphore` + sleep), not a real JDBC/ADO.NET pool benchmark. A real pool-exhaustion example is in [Lab 07 §5.2](../07-domain-events/README.md).
