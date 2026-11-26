# Reproducible experiment protocol

## 1. Preflight

Run correctness checks and confirm the selected runtime and cache strategy. Use an isolated disposable database per edition, exactly one backend under measurement and a fixed product seed. Record actual dataset size, CPU model, OS, Docker/VM resource limits, CPU quota, memory, Java vendor/version, .NET runtime, framework dependencies, Git SHA and dirty status. Ensure the mock API is reachable and not saturated. Do not compare startup measurements with warmed steady state.

## 2. Core comparisons

| Factor | Keep fixed | Change |
|---|---|---|
| Cache | Runtime, seed, operation/key distribution | Strategy |
| Runtime | Same application binary, platform threads, HTTP workload | Java 17 vs 25 |
| Thread model | Java 25, same blocking I/O endpoint | Platform vs virtual |
| I/O aggregation | Same mock responses and delay | Sequential vs concurrent |
| CPU | Same checksum, count, rounds, CPU quota | Workers 1 vs 2/4/8 |
| DI | Same 100K data construction and endpoint result | Request vs shared lifetime |
| Events | Same framework, price-change workload | Direct vs event |
| Resource | Same request count and service time | Permits or single-flight flag |

## 3. Method-level measurement

JMH read-only and mixed groups use actual Java cache classes. Mixed reader/writer operation counts are not a specified fixed ratio; report the separate subresults. Snapshot write-batch costs include copying. Run `tools/run_benchmark.py` and retain every JSON file. The additional EngineeringBenchmark measures total CPU experiment operation time. BenchmarkDotNet CPU and reservation benchmarks use the .NET kernels. For cross-language comparison, the CPU checksum and workload should agree; their thread scheduling and harness overhead are not identical.

## 4. HTTP measurement

Use constant arrival rate k6 workload with fixed RATE, DURATION, VUS and MAX_VUS. Warm up using an unreported run; increase rate in separate runs until SLO breach or dropped iterations. Keep raw results for at least five independent repetitions when doing a serious comparison. Track p50/p95/p99, successful throughput, errors and dropped iterations. A single smoke is a functional check only.

```powershell
$env:BASE_URL='http://localhost:8080'
$env:LAB_PATH='/lab/io/blocking'
$env:RATE='50'; $env:DURATION='60s'; $env:VUS='100'; $env:MAX_VUS='500'
k6 run --summary-export reports/io-platform-run1.json benchmarks/k6/workload.js
```

Use `METHOD=POST` for reservation/event endpoints, but do not benchmark the unsafe mode as a successful implementation. The load script checks HTTP status and JSON validity; run contract checks before interpreting performance.

## 5. CPU quota experiment

```powershell
$env:LAB_CPUS='1'
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d --force-recreate app
# Run sequential and parallel with identical count/rounds and confirm checksums.
$env:LAB_CPUS='4'
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d --force-recreate app
```

Distinguish single-request elapsed time from many concurrent requests. CPU quotas are scheduler bandwidth limits, not guaranteed pinning to physical cores. For strict hardware experiments use dedicated CPU sets/hosts. Record actual runtime processor visibility. Virtual threads are not a CPU accelerator. Avoid making general claims from Docker Desktop scheduling on a noisy workstation.

## 6. Report template

Record experiment ID, date, commit, runtime versions, CPU/memory, dataset, tool arguments, warm-up, repetitions, correctness, raw file paths, metrics and limitations. A hypothesis is not a result. Use `NOT RUN` for missing data. Investigate profiling evidence before attributing causation to GC, locks, scheduler or networking. Indicate cross-framework measurements as indicative only.
