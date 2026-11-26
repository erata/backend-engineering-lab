# Lab 05 — Multicore CPU processing

> Use case: **"Nightly, every product's price must be recalculated by a CPU-heavy formula. How much faster is it on 2, 4 or 8 cores, and what does a container CPU limit change?"**

## 1. Scenario

A deterministic integer kernel stands in for the price formula: for each item `i`, start at `i+1` and apply `rounds` xorshift steps (`x ^= x<<13; x ^= x>>>7; x ^= x<<17`). The results are summed with signed 64-bit wrap-around. No I/O, no sleeps, no shared mutable state except the final sum.

**Correctness invariant:** the checksum must be identical for sequential and every parallel configuration, and identical in Java and .NET. Measured: `-980176603291609351` for `count=100000, rounds=500` in all 13 configurations and both runtimes.

## 2. Implementation

| Edition | Code | Parallelism |
|---|---|---|
| Java (Spring + Jakarta) | `Experiments.cpu` / `work` in [Experiments.java](../../implementations/spring-boot/cache-core/src/main/java/de/backendlab/experiments/Experiments.java) | `workers` `CompletableFuture`s, each summing a strided slice `i = k, k+workers, …`; Spring: fixed 32-thread pool, Jakarta: `ManagedExecutorService` |
| .NET | `Lab.Cpu` / `Work` in [Program.cs](../../implementations/aspnet-core/Lab.Api/Program.cs) | `Parallel.For(0, workers, MaxDegreeOfParallelism = workers)`, local sums + `Interlocked.Add` |

Endpoint: `GET /lab/cpu/sequential|parallel?count=100000&rounds=500&workers=N` → `{checksum, elapsedNs, processors}`. `elapsedNs` is measured **inside** the server, so HTTP overhead is excluded. `processors` is what the runtime believes it has (`availableProcessors()` / `Environment.ProcessorCount`).

## 3. Benchmarks

| Benchmark | Tool | Settings |
|---|---|---|
| `EngineeringBenchmark.cpu` | JMH, host JVM (20 logical CPUs, no quota) | count 100,000, rounds 100, workers 1/2/4/8 |
| `CpuBench.Recalculate` | BenchmarkDotNet, host .NET 10 | same workload |
| CPU probe | `run_http_suite.py`, inside Docker with `cpus: 1/2/4/8` | count 100,000, rounds 500; 5 warm-up + 15 measured calls; median of server-side `elapsedNs` |

## 4. Results

### 4.1 Microbenchmarks on the host (no CPU limit), rounds = 100

| Workers | JMH Java 25 (ms) | speed-up | BDN .NET 10 (ms) | speed-up |
|---:|---:|---:|---:|---:|
| 1 | 22.41 ± 3.95 | 1.0× | 27.47 ± 1.12 | 1.0× |
| 2 | 13.33 ± 1.71 | 1.7× | 14.22 ± 0.62 | 1.9× |
| 4 | 7.30 ± 0.56 | 3.1× | 8.71 ± 0.27 | 3.2× |
| 8 | 5.57 ± 0.48 | 4.0× | 5.27 ± 0.14 | 5.2× |

Allocation stays tiny (Java 0.3–1.8 KB per op, .NET 1.6–3.1 KB), so GC plays no role.

### 4.2 Inside containers with a CPU quota, rounds = 500 (median ms, run [20261126T222721Z](../../reports/http-runs/20261126T222721Z/REPORT.md))

| Quota | Edition | visible CPUs | sequential | 2 workers | 4 workers | 8 workers | best speed-up |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | Spring | 1 | 122.0 | 106.3 | 102.7 | 181.9 | 1.2× |
| 1 | Jakarta | 1 | 127.5 | 111.5 | 108.5 | 119.0 | 1.2× |
| 1 | .NET 10 | 1 | 125.6 | 108.2 | 123.4 | 124.2 | 1.2× |
| 2 | Spring | 2 | 126.0 | **64.0** | 82.0 | 88.4 | 2.0× |
| 2 | Jakarta | 2 | 167.5 | **68.3** | 80.5 | 69.1 | 2.5× |
| 2 | .NET 10 | 2 | 142.9 | **76.8** | 83.8 | 85.2 | 1.9× |
| 4 | Spring | 4 | 114.3 | 62.4 | 33.8 | **27.4** | 4.2× |
| 4 | Jakarta | 4 | 113.7 | 62.5 | 40.9 | **26.9** | 4.2× |
| 4 | .NET 10 | 4 | 122.2 | 65.9 | 36.5 | **25.4** | 4.8× |
| 4 | .NET 11 | 4 | 132.6 | 69.6 | 43.3 | **30.8** | 4.3× |
| 8 | Spring | 8 | 132.3 | 74.4 | 48.8 | **28.6** | 4.6× |
| 8 | Jakarta | 8 | 131.2 | 65.5 | 47.5 | **36.4** | 3.6× |
| 8 | .NET 10 | 8 | 159.1 | 108.7 | 50.9 | **26.6** | 6.0× |

The sequential baseline itself varies between 114 and 168 ms across phases. That ±20% is the noise floor of this workstation (turbo boost, hybrid P/E cores, background containers), so read the table for trends, not for the last digit.

## 5. Interpretation

- **Parallelism helps until the workers outnumber the available CPU time.** With a 1-CPU quota nothing scales (≤ 1.2×), and 8 workers on 1 CPU can be *slower* than sequential (Spring 182 ms: context switches and quota throttling). With 2 CPUs, 2 workers is optimal (≈ 2×), and more workers only add overhead.
- **A CPU quota is time, not cores.** Docker's `cpus: 4` gives the container 400 ms of CPU time per 100 ms scheduling period, spread over *any* of the host's 20 logical CPUs. A 27 ms burst on 8 threads uses ~216 ms of CPU, which fits into one period's budget. That's why 8 workers beat 4 workers at a quota of 4 (27 ms vs 34–43 ms). Under sustained load (many concurrent requests) the quota would throttle, and the 4-worker figure would be the sustainable one. Measure the load shape you actually have.
- **The runtimes respect the quota.** Every runtime reported `processors` equal to the quota (1/2/4/8), so default pool sizes (`ForkJoinPool`, `Parallel.For` without a limit, GC threads) adapt automatically.
- **Speed-up is sub-linear even without a quota:** 4.0× (Java) and 5.2× (.NET) for 8 workers on the host. The i7-13700H mixes 6 performance and 8 efficiency cores with hyper-threading. A strided split hands equal work to fast and slow cores, so the slowest worker sets the end time. Turbo frequency also drops when more cores are busy. Amdahl's serial part (submitting and joining tasks) is small here.
- **Java vs .NET** are within noise on the same kernel. .NET's `Parallel.For` scaled slightly better at 8 workers in both the host and the 8-CPU container.

## 6. Trade-offs

| Decision | Guideline |
|---|---|
| Number of workers | ≈ the number of CPUs the process can use **under sustained load**; more only helps for short bursts under a quota |
| Parallelizing inside a request | improves one request's latency but competes with other requests for the same cores; under high request concurrency, sequential per request is often better for throughput |
| Work splitting | strided/static splits are simple; work-stealing (`ForkJoinPool`, `Parallel.For` with partitioner) handles uneven cores better |
| Virtual threads / async | don't speed up CPU work at all; they solve waiting, not computing ([Lab 04](../04-virtual-threads/README.md)) |

## 7. Reproduce

```powershell
python tools/run_benchmark.py --suite engineering
$env:LabTargetFrameworks='net10.0'; dotnet run -c Release -f net10.0 --project implementations/aspnet-core/Lab.Benchmarks -- --filter '*CpuBench*'
python tools/run_http_suite.py --only cpu1,cpu2,spring-j25-platform-snapshot,cpu8
```
