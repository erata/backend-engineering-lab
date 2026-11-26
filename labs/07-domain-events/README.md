# Lab 07 — Direct orchestration versus domain events

> Use case: **"When a product price changes, an audit record must be written. Call the audit code directly, or publish a `PriceChanged` event?"**

## 1. Scenario

`POST /lab/events/price-change?id=7&cents=999&mode=…[&rollback=true]` updates a price and produces one audit entry.

| Mode | Spring Boot (MySQL, real transactions) | Jakarta EE | ASP.NET Core |
|---|---|---|---|
| `direct` | price upsert **and** audit insert in one `@Transactional` method → atomic | in-memory map + counter | in-memory dictionary + `Interlocked` counter |
| `event` | price upsert, `publishEvent(PriceChanged)`; listener `@TransactionalEventListener(AFTER_COMMIT)` + `@Async` on a bounded 2-thread executor, writes audit in its own transaction | CDI `Event<PriceChanged>.fire()` → synchronous `@Observes` | C# `event Action` delegate |
| `event-inline` (Spring only, **negative example**) | AFTER_COMMIT listener with `REQUIRES_NEW` running **on the request thread** | – | – |
| `rollback=true` | exception after the update → transaction rolls back, **no** event delivered | simulated abort (400) before any change | simulated abort (400) |

Code: [EventController.java](../../implementations/spring-boot/app/src/main/java/de/backendlab/labs/EventController.java), [EventResource.java](../../implementations/jakarta-ee/src/main/java/de/backendlab/ee/EventResource.java), `PriceBook` in [Program.cs](../../implementations/aspnet-core/Lab.Api/Program.cs). Tables `lab_prices`, `lab_price_audit` in [schema.sql](../../implementations/spring-boot/app/src/main/resources/schema.sql).

## 2. Correctness

Verified manually against MySQL and the in-memory counters (see [VALIDATION_STATUS.md](../../docs/VALIDATION_STATUS.md)):

| Check | Spring | Jakarta | .NET |
|---|---|---|---|
| `direct` → exactly 1 audit | ✔ | ✔ (after fix F3) | ✔ |
| `event` → exactly 1 audit (after commit) | ✔ | ✔ | ✔ |
| `rollback=true` → 0 audit rows and price unchanged | ✔ (HTTP 500, real rollback) | simulated | simulated |

## 3. Benchmark

k6, 200 req/s, 30 s, all requests on **the same product id 7** (a hot row). The negative example runs in its own phase at 200 req/s for 20 s.

## 4. Results

Latency in ms. Spring rows come from both suite runs to show the run-to-run behaviour near the limit.

| Edition / mode | achieved req/s | p50 | p95 | p99 | failed |
|---|---:|---:|---:|---:|---:|
| Spring `direct` (run 2, [20261126T222721Z](../../reports/http-runs/20261126T222721Z/REPORT.md)) | **152 / 200** | **3,948** | 4,599 | 4,630 | 0% (787 dropped) |
| Spring `direct` (run 1, [20261126T202650Z](../../reports/http-runs/20261126T202650Z/REPORT.md)) | 199.6 | 36.6 | 221.9 | 273.0 | 0% |
| Spring `event` (async, run 2) | 200.0 | 2.73 | 4.41 | 6.48 | 0% |
| Spring `event` (async, run 1) | 200.0 | 2.25 | 3.58 | 4.75 | 0% |
| **Spring `event-inline`** (run 1) | 67.8 | **10,000 (timeout)** | 10,001 | 10,001 | **100%** |
| Jakarta `direct` / `event` | 200 / 200 | 1.52 / 2.41 | 2.32 / 4.65 | 3.07 / 10.0 | 0% |
| .NET `direct` / `event` | 200 / 200 | 0.86 / 0.79 | 1.51 / 1.31 | 1.92 / 1.63 | 0% |

## 5. Interpretation

### 5.1 The hot-row bottleneck (Spring `direct`)

Every request writes the same `lab_prices` row, so InnoDB serializes them on that row's lock. In `direct` mode the lock is held across two statements and the commit (fsync): price upsert → audit insert → COMMIT. Throughput is capped at `1 / (time the row lock is held)`, about 150–200 tx/s on this Docker/WSL disk. Run 1 sat just under the limit (p95 222 ms); in run 2 the limit dropped slightly below 200/s and requests queued (p50 4 s). Near a capacity knee, small environmental changes flip the result from "slow" to "collapsed".

In `event` mode the request transaction contains **only** the price upsert. The audit insert happens after commit on another thread, so the row lock is held for a shorter time and the request returns sooner. That's why `event` is about 1,000× faster here. The gain comes from **shortening the critical section**, not from events being inherently fast.

### 5.2 The connection-pool deadlock (`event-inline`)

The original implementation, now kept as `event-inline`, ran the AFTER_COMMIT listener with `REQUIRES_NEW` on the request thread. During `afterCommit` Spring has committed but **not yet released** the request's JDBC connection, and `REQUIRES_NEW` asks Hikari for a second one. With 10 concurrent requests (Hikari's pool size) each holding one connection and waiting for another, nobody can proceed. Thread dump during the test: `HikariPool-1 - Connection is not available, request timed out after 30001ms (total=10, active=10, idle=0, waiting=198)`. Result: 100% failures, and the whole application (even non-DB endpoints) stopped answering because all Tomcat threads were parked.

General rule: **a thread that holds a pooled resource must never block waiting for a second unit of the same pool.** Fixes: run the listener asynchronously (implemented), use `BEFORE_COMMIT` / same transaction (makes the audit atomic again), or size the pool to at least `threads × connections per thread`.

### 5.3 The in-memory ports

Jakarta and .NET stay at 1–3 ms because there is no database. They show the **programming model** (CDI observer, C# delegate), not transactional behaviour.

## 6. Trade-offs

| Approach | Consistency | Coupling | Failure mode |
|---|---|---|---|
| Direct call in the same transaction | audit is atomic with the price | caller knows every side effect | longer transactions → lock contention |
| After-commit event (async) | price committed first; audit **may be lost** if the listener fails or the process crashes | publisher doesn't know listeners | silent audit gap; needs monitoring/retry |
| Transactional outbox (not implemented) | event row committed with the price, delivered later at-least-once | decoupled and durable | extra table, relay process, idempotent consumers |

## 7. Limitations

- Jakarta and .NET examples are in-memory, so they have no transactional parity with Spring ([ROADMAP.md](../../docs/ROADMAP.md)).
- The async listener's queue is bounded (10,000) with `AbortPolicy`. On overflow the audit is **dropped**, after the price has been committed, and the error is logged. Caller-runs backpressure was rejected on purpose: it would execute the audit on the request thread inside `afterCommit` and recreate the deadlock from 5.2.
- All requests hit one product id, which deliberately maximizes contention. With random ids, `direct` would not hit the hot-row ceiling.
