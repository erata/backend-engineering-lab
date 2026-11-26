# Experimental API reference

Enable Spring `SPRING_PROFILES_ACTIVE=lab`; port Compose services set `LAB_ENABLED=true`. All commands use local host port 8080 (Spring), 8081 (Jakarta) or 8082 (.NET). Use query parameters below; JSON response field names are intended to match for common experiments. Invalid-input handling is not identical across editions.

| Endpoint | Parameters and interpretation |
|---|---|
| POST `/lab/concurrency/reserve` | mode unsafe/lock/atomic, stock >= 0, requests 1–2000; accepted, remaining, correct. Each HTTP call starts new experiment state. |
| GET `/lab/io/{mode}` | blocking, sequential-async, concurrent. Spring also concurrent-blocking with threadModel=platform/virtual. .NET blocking is deliberately sync-over-async; it is not a true synchronous socket benchmark. |
| GET `/lab/threads/info` | Spring runtime, thread name and virtual boolean. Jakarta thread name. .NET runtime, processor count, ThreadPool count. |
| GET `/lab/cpu/{mode}` | sequential or parallel; count 1–100000, rounds 1–1000, workers 1–32. Returns checksum string, elapsedNs and processors. |
| GET `/lab/di/instances` | mode=request/shared; compare IDs across requests. Payload count is 100000. |
| POST `/lab/events/price-change` | mode=direct/event, id, cents, rollback=true/false. Spring uses DB transaction and actual rollback; ports simulate abort in memory. Spring `event` = async AFTER_COMMIT listener; Spring-only `event-inline` = negative example that deadlocks the connection pool under concurrency ([Lab 07](../labs/07-domain-events/README.md)). |
| GET `/lab/resources/stampede` | single=true/false, requests 1–100. Counts loader invocations within one experiment. |
| GET `/lab/resources/pool` | requests 1–100, permits 1–50. Returns peak active and rejected after wait budget. Simulated pool, not a database connection pool. |

Example PowerShell:

```powershell
$base='http://localhost:8080'
Invoke-RestMethod -Method Post "$base/lab/concurrency/reserve?mode=atomic&stock=100&requests=200"
Invoke-RestMethod "$base/lab/cpu/parallel?count=10000&rounds=100&workers=4"
Invoke-RestMethod "$base/lab/io/concurrent"
```

The common catalogue specification is [OpenAPI](../shared/contracts/openapi.yaml). Its full Spring status/error descriptions are not strict cross-port compatibility guarantees. The HTTP smoke script exercises selected fields across editions. Use the source code for exact experimental route implementations.
