# Developer guide

## Repository

```text
implementations/spring-boot/cache-core/     Pure Java cache and experiment kernels
implementations/spring-boot/app/            Spring Boot controllers, JDBC, scheduler, events
implementations/spring-boot/benchmarks-jmh/ JMH runs against shared production kernels
implementations/jakarta-ee/                 CDI, JAX-RS and managed scheduler/executor WAR
implementations/aspnet-core/Lab.Api/        Independent .NET app and experiment kernels
implementations/aspnet-core/Lab.Tests/      xUnit correctness tests
implementations/aspnet-core/Lab.Benchmarks/ BenchmarkDotNet CPU/reservation tests
labs/                                      Problem, experiment and trade-offs
shared/                                    Contracts and workload specification
infrastructure/mock-api/                   Common deterministic HTTP dependency
benchmarks/k6/                             Common end-to-end workload
observability/                             Optional monitoring configuration
reports/                                   Raw evidence and generated reports
tools/                                     Offline tests, smoke, reporting, Redis demo
```

## Design boundaries

The `ProductCache` interface separates callers from cache strategy; immutable Product values prevent mutation after publication. `RefreshCoordinator` serializes writers and acknowledges exact journal IDs after applying changes. The single-consumer restriction is essential. The Jakarta port uses explicit JDBC transactions and managed executors rather than creating unmanaged application worker pools. Its HttpClient owns internal networking resources; a fully container-managed HTTP client and lifecycle can be a further improvement. The .NET Catalog currently keeps cache selection and SQL logic together for a compact lab; splitting adapters behind interfaces would be useful as complexity grows. Do not claim all examples are Clean Architecture.

The shared Java kernel accepts an Executor from its caller. Spring supplies a fixed pool; Jakarta supplies a managed executor. .NET uses runtime-managed tasks and Parallel.For. HTTP methods return the same three ordered response bodies. CPU checksums are decimal strings to preserve signed 64-bit precision across JSON clients. The Java and .NET xorshift kernel uses identical bit operations, including unsigned shift and wrapping integer sum.

## Add an experiment

1. Define an invariant and a workload in a lab README before writing the implementation.
2. Keep pure algorithms independent of the server where practical; pass runtime-owned resources in.
3. Add a local-only `/lab/...` route, input bounds and failure behavior. Do not activate negative strategies in a normal profile.
4. Add a correctness test, a common smoke assertion and an appropriate method or HTTP benchmark. Reset state between repetitions.
5. Update coverage and validation documents; record actual measurements only after execution. Capture commit, runtime, tool versions and machine settings.

The original Spring-specific architectural discussion is preserved in [ARCHITECTURE.md](ARCHITECTURE.md). This is one monorepo with independently deployable editions, not a microservice system.
