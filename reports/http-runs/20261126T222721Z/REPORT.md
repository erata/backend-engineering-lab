# HTTP benchmark report — measured local results

Indicative measurements of these lab implementations on one workstation. Not universal framework rankings.

- Run: `20261126T222721Z`  
- Host: 13th Gen Intel(R) Core(TM) i7-13700H, 20 logical CPUs, Windows-11-10.0.26300-SP0  
- Backend container quota: `cpus` per phase (default 4), `mem_limit` 2g. k6 grafana/k6:1.3.0 in a container on the Compose network.  
- Each k6 row: constant-arrival-rate, 10 s unreported warm-up, then the measured duration. Latency in ms. Container CPU/memory sampled once mid-run.

## Runtime identification

| Phase | /lab/threads/info |
|---|---|
| spring-j25-platform-snapshot | `{"virtual": false, "runtime": "25.0.5.1", "thread": "http-nio-0.0.0.0-8080-exec-2"}` |
| jakarta-j25-snapshot | `{"thread": "default task-2", "runtime": "25.0.4.1"}` |
| dotnet10-snapshot | `{"runtime": "10.0.15", "processors": 4, "threadPool": 5}` |
| dotnet11-snapshot | `{"runtime": "11.0.0", "processors": 4, "threadPool": 5}` |
| cpu1-spring | `{"virtual": false, "thread": "http-nio-0.0.0.0-8080-exec-3", "runtime": "25.0.5.1"}` |
| cpu1-jakarta | `{"thread": "default task-4", "runtime": "25.0.4.1"}` |
| cpu1-dotnet | `{"runtime": "10.0.15", "processors": 1, "threadPool": 2}` |
| cpu2-spring | `{"virtual": false, "runtime": "25.0.5.1", "thread": "http-nio-0.0.0.0-8080-exec-3"}` |
| cpu2-jakarta | `{"thread": "default task-2", "runtime": "25.0.4.1"}` |
| cpu2-dotnet | `{"runtime": "10.0.15", "processors": 2, "threadPool": 4}` |
| cpu8-spring | `{"thread": "http-nio-0.0.0.0-8080-exec-2", "virtual": false, "runtime": "25.0.5.1"}` |
| cpu8-jakarta | `{"runtime": "25.0.4.1", "thread": "default task-4"}` |
| cpu8-dotnet | `{"runtime": "10.0.15", "processors": 8, "threadPool": 8}` |

## k6 results

| Phase | Experiment | Lab | Target rps | Achieved rps | p50 | p95 | p99 | max | Failed | Dropped | Max VUs | CPU | Memory |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| spring-j25-platform-snapshot | catalog-get | 01 | 2000 | 1999.8 | 0.69 | 1.62 | 8.07 | 54.2 | 0.00% | 0 | 200 | 88.59% | 485.7MiB / 2GiB |
| spring-j25-platform-snapshot | catalog-page | 01 | 50 | 50.0 | 6.21 | 8.85 | 12.09 | 25.2 | 0.00% | 0 | 100 | 44.58% | 452.7MiB / 2GiB |
| spring-j25-platform-snapshot | io-blocking | 03 | 50 | 49.0 | 605.92 | 609.77 | 612.89 | 620.7 | 0.00% | 0 | 100 | 28.74% | 472.4MiB / 2GiB |
| spring-j25-platform-snapshot | io-sequential-async | 03 | 50 | 49.0 | 604.81 | 606.67 | 607.72 | 612.3 | 0.00% | 0 | 100 | 34.11% | 493.1MiB / 2GiB |
| spring-j25-platform-snapshot | io-concurrent | 03 | 50 | 49.5 | 302.86 | 304.42 | 305.23 | 307.7 | 0.00% | 0 | 100 | 26.22% | 494.7MiB / 2GiB |
| spring-j25-platform-snapshot | di-request | 06 | 50 | 50.0 | 2.65 | 6.65 | 8.38 | 12.1 | 0.00% | 0 | 100 | 19.97% | 495MiB / 2GiB |
| spring-j25-platform-snapshot | di-shared | 06 | 50 | 50.0 | 1.60 | 2.62 | 2.99 | 8.2 | 0.00% | 0 | 100 | 6.07% | 493.5MiB / 2GiB |
| spring-j25-platform-snapshot | events-direct | 07 | 200 | 152.1 | 3948.41 | 4598.50 | 4629.87 | 5482.8 | 0.00% | 787 | 870 | 37.40% | 511.1MiB / 2GiB |
| spring-j25-platform-snapshot | events-event | 07 | 200 | 200.0 | 2.73 | 4.41 | 6.48 | 28.4 | 0.00% | 0 | 100 | 49.24% | 508MiB / 2GiB |
| spring-j25-platform-snapshot | reserve-atomic | 02 | 50 | 50.0 | 1.62 | 2.58 | 3.53 | 35.8 | 0.00% | 0 | 100 | 16.12% | 513.2MiB / 2GiB |
| spring-j25-platform-snapshot | reserve-lock | 02 | 50 | 50.0 | 1.75 | 2.58 | 3.28 | 6.3 | 0.00% | 0 | 100 | 15.98% | 513MiB / 2GiB |
| spring-j25-platform-snapshot | io-blocking-400rps | 04 | 400 | 322.4 | 2506.70 | 3978.54 | 4115.41 | 4142.4 | 0.00% | 1016 | 1369 | 102.09% | 547.5MiB / 2GiB |
| jakarta-j25-snapshot | catalog-get | 01 | 2000 | 1206.6 | 754.46 | 1186.94 | 1501.34 | 2988.1 | 0.00% | 23135 | 1000 | 452.95% | 629.1MiB / 2GiB |
| jakarta-j25-snapshot | catalog-page | 01 | 50 | 50.0 | 8.45 | 11.81 | 15.00 | 30.6 | 0.00% | 0 | 100 | 48.80% | 629.9MiB / 2GiB |
| jakarta-j25-snapshot | io-blocking | 03 | 50 | 49.0 | 606.01 | 608.85 | 610.48 | 612.1 | 0.00% | 0 | 100 | 33.42% | 637.1MiB / 2GiB |
| jakarta-j25-snapshot | io-sequential-async | 03 | 50 | 49.0 | 605.50 | 607.62 | 608.97 | 627.4 | 0.00% | 0 | 100 | 42.23% | 638.1MiB / 2GiB |
| jakarta-j25-snapshot | io-concurrent | 03 | 50 | 49.5 | 303.43 | 304.88 | 305.92 | 325.0 | 0.00% | 0 | 100 | 22.34% | 635.1MiB / 2GiB |
| jakarta-j25-snapshot | di-request | 06 | 50 | 50.0 | 3.60 | 8.28 | 12.44 | 71.1 | 0.00% | 0 | 100 | 64.09% | 635.6MiB / 2GiB |
| jakarta-j25-snapshot | di-shared | 06 | 50 | 50.0 | 1.59 | 2.14 | 2.72 | 7.3 | 0.00% | 0 | 100 | 7.57% | 633.8MiB / 2GiB |
| jakarta-j25-snapshot | events-direct | 07 | 200 | 200.0 | 1.52 | 2.32 | 3.07 | 11.1 | 0.00% | 0 | 100 | 28.89% | 635.5MiB / 2GiB |
| jakarta-j25-snapshot | events-event | 07 | 200 | 200.0 | 2.41 | 4.65 | 10.00 | 61.4 | 0.00% | 0 | 100 | 46.59% | 635MiB / 2GiB |
| jakarta-j25-snapshot | reserve-atomic | 02 | 50 | 50.0 | 4.15 | 6.36 | 8.34 | 38.1 | 0.00% | 0 | 100 | 29.83% | 642.2MiB / 2GiB |
| jakarta-j25-snapshot | reserve-lock | 02 | 50 | 50.0 | 4.35 | 6.71 | 8.68 | 16.1 | 0.00% | 0 | 100 | 37.37% | 639.8MiB / 2GiB |
| jakarta-j25-snapshot | io-blocking-400rps | 04 | 400 | 210.0 | 10000.16 | 10000.96 | 10001.40 | 10032.6 | 88.28% | 3599 | 3000 | 47.08% | 658.7MiB / 2GiB |
| dotnet10-snapshot | catalog-get | 01 | 2000 | 1999.9 | 1.00 | 9.38 | 37.83 | 105.7 | 0.00% | 0 | 200 | 171.01% | 140.1MiB / 2GiB |
| dotnet10-snapshot | catalog-page | 01 | 50 | 50.0 | 47.42 | 72.35 | 97.59 | 159.6 | 0.00% | 0 | 100 | 260.98% | 92.62MiB / 2GiB |
| dotnet10-snapshot | io-blocking | 03 | 50 | 28.7 | 9999.97 | 10000.77 | 10000.96 | 10001.4 | 100.00% | 351 | 451 | 1.46% | 151.9MiB / 2GiB |
| dotnet10-snapshot | io-sequential-async | 03 | 50 | 49.0 | 603.73 | 605.75 | 607.03 | 614.5 | 0.00% | 0 | 100 | 15.13% | 208.1MiB / 2GiB |
| dotnet10-snapshot | io-concurrent | 03 | 50 | 49.5 | 302.51 | 303.71 | 304.50 | 305.9 | 0.00% | 0 | 100 | 14.54% | 223.9MiB / 2GiB |
| dotnet10-snapshot | di-request | 06 | 50 | 50.0 | 5.77 | 42.98 | 61.98 | 95.1 | 0.00% | 0 | 100 | 62.27% | 249.8MiB / 2GiB |
| dotnet10-snapshot | di-shared | 06 | 50 | 50.0 | 0.79 | 1.48 | 2.16 | 16.5 | 0.00% | 0 | 100 | 4.06% | 303.5MiB / 2GiB |
| dotnet10-snapshot | events-direct | 07 | 200 | 200.0 | 0.86 | 1.51 | 1.92 | 34.1 | 0.00% | 0 | 100 | 19.53% | 283.9MiB / 2GiB |
| dotnet10-snapshot | events-event | 07 | 200 | 200.0 | 0.79 | 1.31 | 1.63 | 7.1 | 0.00% | 0 | 100 | 23.34% | 284.2MiB / 2GiB |
| dotnet10-snapshot | reserve-atomic | 02 | 50 | 50.0 | 0.87 | 1.39 | 1.85 | 43.8 | 0.00% | 0 | 100 | 5.49% | 286.2MiB / 2GiB |
| dotnet10-snapshot | reserve-lock | 02 | 50 | 50.0 | 0.93 | 1.58 | 2.33 | 3.8 | 0.00% | 0 | 100 | 13.22% | 296.4MiB / 2GiB |
| dotnet10-snapshot | io-blocking-400rps | 04 | 400 | 204.1 | 0.00 | 10000.19 | 10000.74 | 10001.4 | 100.00% | 3837 | 3000 | 4.01% | 328.6MiB / 2GiB |
| dotnet11-snapshot | catalog-get | 01 | 2000 | 1999.9 | 0.93 | 17.46 | 48.07 | 136.9 | 0.00% | 0 | 200 | 163.73% | 113.6MiB / 2GiB |
| dotnet11-snapshot | io-blocking-400rps | 04 | 400 | 204.4 | 2854.07 | 10000.21 | 10000.77 | 10001.5 | 100.00% | 3823 | 3000 | 1.99% | 160.8MiB / 2GiB |

## CPU probe (Lab 05) — elapsed ms per request, median of 15 after 5 warm-ups (count=100000, rounds=500)

| Phase | CPU quota | Visible processors | sequential | parallel-2 | parallel-4 | parallel-8 | Speed-up 8 vs seq | Checksums equal |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| spring-j25-platform-snapshot | 4 | 4 | 114.3 | 62.4 | 33.8 | 27.4 | 4.17x | True |
| jakarta-j25-snapshot | 4 | 4 | 113.7 | 62.5 | 40.9 | 26.9 | 4.22x | True |
| dotnet10-snapshot | 4 | 4 | 122.2 | 65.9 | 36.5 | 25.4 | 4.81x | True |
| dotnet11-snapshot | 4 | 4 | 132.6 | 69.6 | 43.3 | 30.8 | 4.31x | True |
| cpu1-spring | 1 | 1 | 122.0 | 106.3 | 102.7 | 181.9 | 0.67x | True |
| cpu1-jakarta | 1 | 1 | 127.5 | 111.5 | 108.5 | 119.0 | 1.07x | True |
| cpu1-dotnet | 1 | 1 | 125.6 | 108.2 | 123.4 | 124.2 | 1.01x | True |
| cpu2-spring | 2 | 2 | 126.0 | 64.0 | 82.0 | 88.4 | 1.43x | True |
| cpu2-jakarta | 2 | 2 | 167.5 | 68.3 | 80.5 | 69.1 | 2.42x | True |
| cpu2-dotnet | 2 | 2 | 142.9 | 76.8 | 83.8 | 85.2 | 1.68x | True |
| cpu8-spring | 8 | 8 | 132.3 | 74.4 | 48.8 | 28.6 | 4.62x | True |
| cpu8-jakarta | 8 | 8 | 131.2 | 65.5 | 47.5 | 36.4 | 3.61x | True |
| cpu8-dotnet | 8 | 8 | 159.1 | 108.7 | 50.9 | 26.6 | 5.98x | True |

## Correctness probes (Labs 02, 06, 08)

### spring-j25-platform-snapshot

```json
{
 "reserve_unsafe": {
  "runs": 30,
  "incorrect": 21,
  "max_accepted": 150,
  "min_remaining": 0
 },
 "reserve_lock": {
  "runs": 30,
  "incorrect": 0
 },
 "reserve_atomic": {
  "runs": 30,
  "incorrect": 0
 },
 "stampede_single_false_32": {
  "requests": 32,
  "loads_min": 32,
  "loads_max": 32
 },
 "stampede_single_false_100": {
  "requests": 100,
  "loads_min": 32,
  "loads_max": 32
 },
 "stampede_single_true_32": {
  "requests": 32,
  "loads_min": 1,
  "loads_max": 1
 },
 "stampede_single_true_100": {
  "requests": 100,
  "loads_min": 1,
  "loads_max": 1
 },
 "pool_32_permits5": {
  "peak_max": 5,
  "rejected_min": 12,
  "rejected_max": 12
 },
 "pool_100_permits5": {
  "peak_max": 5,
  "rejected_min": 51,
  "rejected_max": 53
 },
 "di": {
  "shared_same_id": true,
  "request_distinct_id": true
 }
}
```

### jakarta-j25-snapshot

```json
{
 "reserve_unsafe": {
  "runs": 30,
  "incorrect": 29,
  "max_accepted": 144,
  "min_remaining": 0
 },
 "reserve_lock": {
  "runs": 30,
  "incorrect": 0
 },
 "reserve_atomic": {
  "runs": 30,
  "incorrect": 0
 },
 "stampede_single_false_32": {
  "requests": 32,
  "loads_min": 8,
  "loads_max": 8
 },
 "stampede_single_false_100": {
  "requests": 100,
  "loads_min": 8,
  "loads_max": 8
 },
 "stampede_single_true_32": {
  "requests": 32,
  "loads_min": 1,
  "loads_max": 1
 },
 "stampede_single_true_100": {
  "requests": 100,
  "loads_min": 1,
  "loads_max": 1
 },
 "pool_32_permits5": {
  "peak_max": 5,
  "rejected_min": 0,
  "rejected_max": 3
 },
 "pool_100_permits5": {
  "peak_max": 5,
  "rejected_min": 4,
  "rejected_max": 8
 },
 "di": {
  "shared_same_id": true,
  "request_distinct_id": true
 }
}
```

### dotnet10-snapshot

```json
{
 "reserve_unsafe": {
  "runs": 30,
  "incorrect": 11,
  "max_accepted": 185,
  "min_remaining": 0
 },
 "reserve_lock": {
  "runs": 30,
  "incorrect": 0
 },
 "reserve_atomic": {
  "runs": 30,
  "incorrect": 0
 },
 "stampede_single_false_32": {
  "requests": 32,
  "loads_min": 32,
  "loads_max": 32
 },
 "stampede_single_false_100": {
  "requests": 100,
  "loads_min": 100,
  "loads_max": 100
 },
 "stampede_single_true_32": {
  "requests": 32,
  "loads_min": 1,
  "loads_max": 1
 },
 "stampede_single_true_100": {
  "requests": 100,
  "loads_min": 1,
  "loads_max": 1
 },
 "pool_32_permits5": {
  "peak_max": 5,
  "rejected_min": 12,
  "rejected_max": 12
 },
 "pool_100_permits5": {
  "peak_max": 5,
  "rejected_min": 80,
  "rejected_max": 80
 },
 "di": {
  "shared_same_id": true,
  "request_distinct_id": true
 }
}
```


Raw k6 summaries (`*.json`), `probes.json` and `environment.json` are stored next to this report.
