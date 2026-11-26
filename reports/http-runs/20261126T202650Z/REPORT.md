# HTTP benchmark report — measured local results

Indicative measurements of these lab implementations on one workstation. Not universal framework rankings.

- Run: `20261126T202650Z`  
- Host: 13th Gen Intel(R) Core(TM) i7-13700H, 20 logical CPUs, Windows-11-10.0.26300-SP0  
- Backend container quota: `cpus` per phase (default 4), `mem_limit` 2g. k6 grafana/k6:1.3.0 in a container on the Compose network.  
- Each k6 row: constant-arrival-rate, 10 s unreported warm-up, then the measured duration. Latency in ms. Container CPU/memory sampled once mid-run.

## Runtime identification

| Phase | /lab/threads/info |
|---|---|
| spring-j25-platform-snapshot | `{"thread": "http-nio-0.0.0.0-8080-exec-2", "virtual": false, "runtime": "25.0.5.1"}` |
| spring-j25-events-inline | `{"virtual": false, "thread": "http-nio-0.0.0.0-8080-exec-3", "runtime": "25.0.5.1"}` |
| spring-j25-virtual-snapshot | `{"thread": "tomcat-handler-1", "runtime": "25.0.5.1", "virtual": true}` |
| spring-j17-platform-snapshot | `{"thread": "http-nio-0.0.0.0-8080-exec-2", "runtime": "17.0.21.1", "virtual": false}` |
| spring-j25-platform-synchronized | `{"virtual": false, "runtime": "25.0.5.1", "thread": "http-nio-0.0.0.0-8080-exec-3"}` |
| spring-j25-platform-concurrent | `{"virtual": false, "runtime": "25.0.5.1", "thread": "http-nio-0.0.0.0-8080-exec-2"}` |
| spring-j25-platform-caffeine | `{"virtual": false, "runtime": "25.0.5.1", "thread": "http-nio-0.0.0.0-8080-exec-2"}` |
| jakarta-j25-snapshot | `{"thread": "default task-2", "runtime": "25.0.4.1"}` |
| dotnet10-snapshot | `{"runtime": "10.0.15", "processors": 4, "threadPool": 5}` |

## k6 results

| Phase | Experiment | Lab | Target rps | Achieved rps | p50 | p95 | p99 | max | Failed | Dropped | Max VUs | CPU | Memory |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| spring-j25-platform-snapshot | catalog-get | 01 | 2000 | 1994.1 | 1.02 | 28.40 | 79.21 | 259.6 | 0.00% | 164 | 238 | 110.45% | 351.2MiB / 2GiB |
| spring-j25-platform-snapshot | catalog-page | 01 | 50 | 50.0 | 7.85 | 12.56 | 17.84 | 33.2 | 0.00% | 0 | 100 | 90.99% | 367.1MiB / 2GiB |
| spring-j25-platform-snapshot | io-blocking | 03 | 50 | 49.0 | 605.17 | 607.22 | 608.71 | 617.0 | 0.00% | 0 | 100 | 25.75% | 384.2MiB / 2GiB |
| spring-j25-platform-snapshot | io-sequential-async | 03 | 50 | 49.0 | 604.91 | 606.72 | 608.21 | 620.3 | 0.00% | 0 | 100 | 29.60% | 397.2MiB / 2GiB |
| spring-j25-platform-snapshot | io-concurrent | 03 | 50 | 49.5 | 303.25 | 304.69 | 305.55 | 316.5 | 0.00% | 0 | 100 | 18.62% | 397.5MiB / 2GiB |
| spring-j25-platform-snapshot | io-blocking-400rps | 04 | 400 | 268.1 | 4498.73 | 7734.38 | 8002.26 | 8039.0 | 0.00% | 1810 | 2192 | 90.73% | 481.9MiB / 2GiB |
| spring-j25-platform-snapshot | di-request | 06 | 50 | 50.0 | 2.81 | 5.54 | 7.43 | 9.7 | 0.00% | 0 | 100 | 14.65% | 513.9MiB / 2GiB |
| spring-j25-platform-snapshot | di-shared | 06 | 50 | 50.0 | 1.05 | 1.86 | 2.25 | 3.8 | 0.00% | 0 | 100 | 4.33% | 511.8MiB / 2GiB |
| spring-j25-platform-snapshot | events-direct | 07 | 200 | 199.6 | 36.64 | 221.94 | 272.95 | 474.7 | 0.00% | 0 | 100 | 24.88% | 515.3MiB / 2GiB |
| spring-j25-platform-snapshot | events-event | 07 | 200 | 200.0 | 2.25 | 3.58 | 4.75 | 22.9 | 0.00% | 0 | 100 | 39.15% | 516.1MiB / 2GiB |
| spring-j25-platform-snapshot | reserve-atomic | 02 | 50 | 50.0 | 1.53 | 2.46 | 3.63 | 7.8 | 0.00% | 0 | 100 | 15.51% | 518.8MiB / 2GiB |
| spring-j25-platform-snapshot | reserve-lock | 02 | 50 | 50.0 | 1.59 | 2.54 | 3.18 | 6.1 | 0.00% | 0 | 100 | 14.18% | 518.4MiB / 2GiB |
| spring-j25-events-inline | events-event-inline | 07 | 200 | 67.8 | 10000.36 | 10000.97 | 10001.17 | 10002.8 | 100.00% | 2001 | 1000 | 268.75% | 354.2MiB / 2GiB |
| spring-j25-virtual-snapshot | catalog-get | 01 | 2000 | 1999.9 | 0.43 | 0.82 | 1.30 | 10.4 | 0.00% | 0 | 200 | 57.87% | 339.2MiB / 2GiB |
| spring-j25-virtual-snapshot | io-blocking | 03 | 50 | 49.0 | 604.79 | 606.43 | 607.28 | 610.0 | 0.00% | 0 | 100 | 53.08% | 375.6MiB / 2GiB |
| spring-j25-virtual-snapshot | io-blocking-400rps | 04 | 400 | 392.1 | 604.76 | 613.09 | 624.10 | 662.3 | 0.00% | 0 | 400 | 98.31% | 483MiB / 2GiB |
| spring-j17-platform-snapshot | catalog-get | 01 | 2000 | 1958.2 | 0.68 | 1.69 | 70.50 | 917.0 | 0.00% | 1251 | 215 | 116.41% | 428.9MiB / 2GiB |
| spring-j17-platform-snapshot | io-blocking-400rps | 04 | 400 | 267.5 | 4484.49 | 7748.73 | 7995.25 | 8074.2 | 0.00% | 1837 | 2195 | 109.18% | 542.1MiB / 2GiB |
| spring-j25-platform-synchronized | catalog-get | 01 | 2000 | 1998.7 | 0.87 | 16.54 | 47.57 | 152.5 | 0.00% | 36 | 217 | 88.86% | 423.2MiB / 2GiB |
| spring-j25-platform-synchronized | catalog-page | 01 | 50 | 50.0 | 10.47 | 35.45 | 120.81 | 170.0 | 0.00% | 0 | 100 | 68.75% | 424MiB / 2GiB |
| spring-j25-platform-concurrent | catalog-get | 01 | 2000 | 1987.0 | 1.16 | 52.63 | 100.97 | 396.1 | 0.00% | 384 | 299 | 215.70% | 368.1MiB / 2GiB |
| spring-j25-platform-concurrent | catalog-page | 01 | 50 | 50.0 | 8.36 | 13.51 | 19.78 | 46.1 | 0.00% | 0 | 100 | 77.44% | 370MiB / 2GiB |
| spring-j25-platform-caffeine | catalog-get | 01 | 2000 | 1999.8 | 0.92 | 19.80 | 50.47 | 140.3 | 0.00% | 5 | 202 | 139.22% | 381.7MiB / 2GiB |
| spring-j25-platform-caffeine | catalog-page | 01 | 50 | 50.0 | 8.20 | 12.59 | 16.07 | 20.8 | 0.00% | 0 | 100 | 87.86% | 388.6MiB / 2GiB |
| jakarta-j25-snapshot | catalog-get | 01 | 2000 | 1001.3 | 904.97 | 1288.64 | 1563.86 | 2583.0 | 0.00% | 29333 | 1000 | 409.73% | 520.6MiB / 2GiB |
| jakarta-j25-snapshot | catalog-page | 01 | 50 | 50.0 | 9.39 | 17.17 | 27.29 | 65.0 | 0.00% | 0 | 100 | 141.59% | 649.6MiB / 2GiB |
| jakarta-j25-snapshot | io-blocking | 03 | 50 | 49.0 | 607.82 | 611.82 | 616.58 | 634.3 | 0.00% | 0 | 100 | 39.04% | 639MiB / 2GiB |
| jakarta-j25-snapshot | io-sequential-async | 03 | 50 | 49.0 | 605.77 | 608.67 | 610.63 | 617.2 | 0.00% | 0 | 100 | 29.23% | 637.8MiB / 2GiB |
| jakarta-j25-snapshot | io-concurrent | 03 | 50 | 49.5 | 304.06 | 306.08 | 307.92 | 337.0 | 0.00% | 0 | 100 | 93.35% | 636.1MiB / 2GiB |
| jakarta-j25-snapshot | io-blocking-400rps | 04 | 400 | 197.5 | 10000.10 | 10001.26 | 10010.04 | 10052.6 | 97.56% | 4098 | 3000 | 109.52% | 654.8MiB / 2GiB |
| jakarta-j25-snapshot | di-request | 06 | 50 | 28.7 | 10000.15 | 10001.09 | 10001.84 | 10005.7 | 100.00% | 351 | 451 | 45.35% | 670.6MiB / 2GiB |
| jakarta-j25-snapshot | di-shared | 06 | 50 | 28.7 | 10000.03 | 10001.00 | 10001.56 | 10006.2 | 100.00% | 351 | 451 | 385.69% | 884.8MiB / 2GiB |
| jakarta-j25-snapshot | events-direct | 07 | 200 | 200.0 | 1.42 | 2.22 | 2.84 | 13.9 | 0.00% | 0 | 100 | 29.70% | 875.6MiB / 2GiB |
| jakarta-j25-snapshot | events-event | 07 | 200 | 200.0 | 1.39 | 2.33 | 3.15 | 17.1 | 0.00% | 0 | 100 | 26.87% | 774.7MiB / 2GiB |
| jakarta-j25-snapshot | reserve-atomic | 02 | 50 | 50.0 | 4.53 | 6.42 | 7.73 | 16.0 | 0.00% | 0 | 100 | 29.44% | 729.9MiB / 2GiB |
| jakarta-j25-snapshot | reserve-lock | 02 | 50 | 50.0 | 5.57 | 8.22 | 11.33 | 20.7 | 0.00% | 0 | 100 | 35.25% | 703.3MiB / 2GiB |
| dotnet10-snapshot | catalog-get | 01 | 2000 | 1999.9 | 1.05 | 7.95 | 20.33 | 59.9 | 0.00% | 0 | 200 | 186.49% | 138.4MiB / 2GiB |
| dotnet10-snapshot | catalog-page | 01 | 50 | 50.0 | 45.61 | 90.41 | 154.15 | 205.8 | 0.00% | 0 | 100 | 244.98% | 125.9MiB / 2GiB |
| dotnet10-snapshot | io-blocking | 03 | 50 | 28.7 | 10000.04 | 10000.97 | 10001.31 | 10001.7 | 100.00% | 351 | 451 | 1.85% | 165.3MiB / 2GiB |
| dotnet10-snapshot | io-sequential-async | 03 | 50 | 48.8 | 733.77 | 741.50 | 745.31 | 746.2 | 0.00% | 0 | 100 | 19.90% | 214.7MiB / 2GiB |
| dotnet10-snapshot | io-concurrent | 03 | 50 | 49.5 | 343.44 | 348.09 | 351.41 | 355.0 | 0.00% | 0 | 100 | 14.17% | 235.2MiB / 2GiB |
| dotnet10-snapshot | io-blocking-400rps | 04 | 400 | 201.6 | 0.00 | 7967.59 | 9992.90 | 10001.5 | 100.00% | 3937 | 3000 | 2.75% | 259.9MiB / 2GiB |
| dotnet10-snapshot | di-request | 06 | 50 | 30.7 | 7810.93 | 10000.39 | 10000.65 | 10001.0 | 69.83% | 341 | 441 | 2.07% | 323.1MiB / 2GiB |
| dotnet10-snapshot | di-shared | 06 | 50 | 50.0 | 0.85 | 1.38 | 1.68 | 2.9 | 0.00% | 0 | 100 | 5.39% | 1.13GiB / 2GiB |
| dotnet10-snapshot | events-direct | 07 | 200 | 200.0 | 0.80 | 1.35 | 1.81 | 5.4 | 0.00% | 0 | 100 | 14.11% | 1.13GiB / 2GiB |
| dotnet10-snapshot | events-event | 07 | 200 | 200.0 | 0.83 | 1.36 | 1.74 | 15.7 | 0.00% | 0 | 100 | 20.32% | 1.129GiB / 2GiB |
| dotnet10-snapshot | reserve-atomic | 02 | 50 | 50.0 | 0.93 | 1.73 | 2.36 | 11.7 | 0.00% | 0 | 100 | 6.73% | 1.129GiB / 2GiB |
| dotnet10-snapshot | reserve-lock | 02 | 50 | 50.0 | 1.74 | 3.04 | 3.60 | 13.7 | 0.00% | 0 | 100 | 12.37% | 1.129GiB / 2GiB |

## CPU probe (Lab 05) — elapsed ms per request, median of 15 after 5 warm-ups (count=100000, rounds=500)

| Phase | CPU quota | Visible processors | sequential | parallel-2 | parallel-4 | parallel-8 | Speed-up 8 vs seq | Checksums equal |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| spring-j25-platform-snapshot | 4 | 4 | 82.1 | 44.8 | 23.3 | 16.3 | 5.04x | True |
| spring-j17-platform-snapshot | 4 | 4 | 123.5 | 66.8 | 32.5 | 25.9 | 4.76x | True |
| jakarta-j25-snapshot | 4 | 4 | 122.4 | 75.2 | 30.4 | 22.6 | 5.42x | True |
| dotnet10-snapshot | 4 | 4 | 124.8 | 52.3 | 29.7 | 25.1 | 4.98x | True |

## Correctness probes (Labs 02, 06, 08)

### spring-j25-platform-snapshot

```json
{
 "reserve_unsafe": {
  "runs": 30,
  "incorrect": 19,
  "max_accepted": 128,
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
  "rejected_max": 54
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
  "incorrect": 30,
  "max_accepted": 142,
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
  "rejected_min": 3,
  "rejected_max": 6
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
  "incorrect": 8,
  "max_accepted": 157,
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
