# HTTP benchmark report — measured local results

Indicative measurements of these lab implementations on one workstation. Not universal framework rankings.

- Run: `20261127T011057Z`  
- Host: 13th Gen Intel(R) Core(TM) i7-13700H, 20 logical CPUs, Windows-11-10.0.26300-SP0  
- Backend container quota: `cpus` per phase (default 4), `mem_limit` 2g. k6 grafana/k6:1.3.0 in a container on the Compose network.  
- Each k6 row: constant-arrival-rate, 10 s unreported warm-up, then the measured duration. Latency in ms. Container CPU/memory sampled once mid-run.

## Runtime identification

| Phase | /lab/threads/info |
|---|---|
| v2-rep5-jakarta | `{"thread": "default task-2", "runtime": "25.0.4.1", "virtual": false, "image": "backend-engineering-lab-full-jakarta sha256:09d844d1ae0e71794f9645d83a999f58e0e1f12da53827094a139c098aa8e029", "db_image": "mysql:8.4"}` |
| v2-rep5-dotnet10 | `{"runtime": "10.0.15", "processors": 4, "threadPool": 5, "image": "backend-engineering-lab-full-dotnet sha256:d15d83080c1accd1481a78a6c2c9f6d8ccc82d5d212296ec62885f0be0302d4a", "db_image": "mysql:8.4"}` |
| v2-new-spring | `{"thread": "http-nio-0.0.0.0-8080-exec-3", "runtime": "25.0.5.1", "virtual": false, "image": "backend-engineering-lab-full-app sha256:df7139e7a20f3f43cc250474ecd7a6d30ead4f5d2f91158d18c8bf7bdb631626", "db_image": "mysql:8.4"}` |
| v2-new-jakarta | `{"runtime": "25.0.4.1", "virtual": false, "thread": "default task-2", "image": "backend-engineering-lab-full-jakarta sha256:09d844d1ae0e71794f9645d83a999f58e0e1f12da53827094a139c098aa8e029", "db_image": "mysql:8.4"}` |
| v2-new-dotnet10 | `{"runtime": "10.0.15", "processors": 4, "threadPool": 5, "image": "backend-engineering-lab-full-dotnet sha256:d15d83080c1accd1481a78a6c2c9f6d8ccc82d5d212296ec62885f0be0302d4a", "db_image": "mysql:8.4"}` |
| v2-pinning-j21 | `{"thread": "http-nio-0.0.0.0-8080-exec-2", "runtime": "21.0.13.1", "virtual": false, "image": "backend-engineering-lab-full-app sha256:fabc56d3a04fb58b6e528a8bfcc0fb29767f3ffd6829805fcb16372440ee049c", "db_image": "mysql:8.4"}` |
| v2-pinning-j25 | `{"runtime": "25.0.5.1", "thread": "http-nio-0.0.0.0-8080-exec-3", "virtual": false, "image": "backend-engineering-lab-full-app sha256:df7139e7a20f3f43cc250474ecd7a6d30ead4f5d2f91158d18c8bf7bdb631626", "db_image": "mysql:8.4"}` |
| v2-redis-spring | `{"virtual": false, "runtime": "25.0.5.1", "thread": "http-nio-0.0.0.0-8080-exec-5", "image": "backend-engineering-lab-full-app sha256:df7139e7a20f3f43cc250474ecd7a6d30ead4f5d2f91158d18c8bf7bdb631626", "db_image": "mysql:8.4"}` |
| v3-spring | `{"virtual": false, "runtime": "25.0.5.1", "thread": "http-nio-0.0.0.0-8080-exec-2", "image": "backend-engineering-lab-full-app sha256:df7139e7a20f3f43cc250474ecd7a6d30ead4f5d2f91158d18c8bf7bdb631626", "db_image": "mysql:8.4"}` |
| v3-jakarta | `{"virtual": false, "runtime": "25.0.4.1", "thread": "default task-2", "image": "backend-engineering-lab-full-jakarta sha256:09d844d1ae0e71794f9645d83a999f58e0e1f12da53827094a139c098aa8e029", "db_image": "mysql:8.4"}` |
| v3-dotnet10 | `{"runtime": "10.0.15", "processors": 4, "threadPool": 5, "image": "backend-engineering-lab-full-dotnet sha256:d15d83080c1accd1481a78a6c2c9f6d8ccc82d5d212296ec62885f0be0302d4a", "db_image": "mysql:8.4"}` |
| v3-redis-spring | `{"runtime": "25.0.5.1", "thread": "http-nio-0.0.0.0-8080-exec-2", "virtual": false, "image": "backend-engineering-lab-full-app sha256:df7139e7a20f3f43cc250474ecd7a6d30ead4f5d2f91158d18c8bf7bdb631626", "db_image": "mysql:8.4"}` |

## k6 results

| Phase | Experiment | Lab | Target rps | Achieved rps | p50 | p95 | p99 | max | Failed | Dropped | Max VUs | CPU | Memory |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| v2-rep5-jakarta | catalog-get | 01 | 2000 | 1531.9 | 562.87 | 934.32 | 1130.60 | 2708.5 | 0.00% | 13729 | 1000 | 417.34% | 607.7MiB / 2GiB |
| v2-rep5-jakarta | catalog-get | 01 | 2000 | 1987.5 | 2.05 | 93.79 | 217.96 | 746.3 | 0.00% | 363 | 344 | 346.92% | 609.4MiB / 2GiB |
| v2-rep5-jakarta | catalog-get | 01 | 2000 | 1989.0 | 1.43 | 41.59 | 153.33 | 540.4 | 0.00% | 328 | 327 | 241.29% | 609.6MiB / 2GiB |
| v2-rep5-jakarta | catalog-get | 01 | 2000 | 1993.2 | 1.44 | 34.22 | 105.60 | 509.8 | 0.00% | 188 | 268 | 313.21% | 607.8MiB / 2GiB |
| v2-rep5-jakarta | catalog-get | 01 | 2000 | 1965.8 | 1.65 | 199.69 | 343.36 | 1165.3 | 0.00% | 1021 | 496 | 452.47% | 610.3MiB / 2GiB |
| v2-rep5-jakarta | io-concurrent | 03 | 50 | 49.5 | 303.74 | 305.25 | 306.26 | 307.7 | 0.00% | 0 | 100 | 43.59% | 619.2MiB / 2GiB |
| v2-rep5-jakarta | io-concurrent | 03 | 50 | 49.5 | 303.78 | 309.18 | 376.81 | 846.2 | 0.00% | 0 | 100 | 33.73% | 613.4MiB / 2GiB |
| v2-rep5-jakarta | io-concurrent | 03 | 50 | 49.5 | 303.49 | 305.90 | 307.06 | 310.8 | 0.00% | 0 | 100 | 35.18% | 613MiB / 2GiB |
| v2-rep5-jakarta | io-concurrent | 03 | 50 | 49.5 | 303.59 | 305.37 | 306.49 | 309.2 | 0.00% | 0 | 100 | 18.63% | 613.2MiB / 2GiB |
| v2-rep5-jakarta | io-concurrent | 03 | 50 | 49.5 | 304.01 | 307.38 | 308.90 | 312.0 | 0.00% | 0 | 100 | 32.20% | 613.4MiB / 2GiB |
| v2-rep5-dotnet10 | catalog-get | 01 | 2000 | 1999.4 | 0.91 | 8.22 | 29.09 | 133.6 | 0.00% | 0 | 200 | 181.67% | 145.4MiB / 2GiB |
| v2-rep5-dotnet10 | catalog-get | 01 | 2000 | 2000.0 | 0.93 | 5.43 | 21.42 | 95.6 | 0.00% | 0 | 200 | 176.42% | 104.8MiB / 2GiB |
| v2-rep5-dotnet10 | catalog-get | 01 | 2000 | 1988.8 | 0.81 | 12.41 | 54.40 | 276.8 | 0.00% | 330 | 233 | 126.37% | 104.9MiB / 2GiB |
| v2-rep5-dotnet10 | catalog-get | 01 | 2000 | 1999.9 | 0.94 | 11.59 | 40.10 | 106.1 | 0.00% | 0 | 200 | 181.63% | 112.9MiB / 2GiB |
| v2-rep5-dotnet10 | catalog-get | 01 | 2000 | 1999.9 | 0.94 | 11.22 | 35.48 | 107.8 | 0.00% | 0 | 200 | 184.75% | 115.7MiB / 2GiB |
| v2-rep5-dotnet10 | io-sequential-async | 03 | 50 | 49.0 | 603.79 | 605.49 | 607.61 | 627.8 | 0.00% | 0 | 100 | 16.61% | 109.9MiB / 2GiB |
| v2-rep5-dotnet10 | io-sequential-async | 03 | 50 | 49.0 | 603.71 | 605.35 | 606.85 | 611.2 | 0.00% | 0 | 100 | 14.71% | 117.7MiB / 2GiB |
| v2-rep5-dotnet10 | io-sequential-async | 03 | 50 | 49.0 | 603.51 | 605.13 | 606.01 | 610.2 | 0.00% | 0 | 100 | 12.40% | 122.7MiB / 2GiB |
| v2-rep5-dotnet10 | io-sequential-async | 03 | 50 | 49.0 | 603.45 | 605.51 | 607.20 | 623.0 | 0.00% | 0 | 100 | 15.24% | 130.9MiB / 2GiB |
| v2-rep5-dotnet10 | io-sequential-async | 03 | 50 | 49.0 | 603.47 | 604.99 | 605.90 | 613.2 | 0.00% | 0 | 100 | 13.68% | 134.9MiB / 2GiB |
| v2-rep5-dotnet10 | io-concurrent | 03 | 50 | 49.5 | 302.24 | 303.32 | 304.09 | 307.8 | 0.00% | 0 | 100 | 12.78% | 138MiB / 2GiB |
| v2-rep5-dotnet10 | io-concurrent | 03 | 50 | 49.5 | 302.39 | 303.89 | 304.73 | 309.8 | 0.00% | 0 | 100 | 13.67% | 140.8MiB / 2GiB |
| v2-rep5-dotnet10 | io-concurrent | 03 | 50 | 49.5 | 302.31 | 303.49 | 304.28 | 305.2 | 0.00% | 0 | 100 | 15.01% | 144.9MiB / 2GiB |
| v2-rep5-dotnet10 | io-concurrent | 03 | 50 | 49.5 | 302.23 | 303.29 | 304.10 | 356.1 | 0.00% | 0 | 100 | 12.58% | 149.2MiB / 2GiB |
| v2-rep5-dotnet10 | io-concurrent | 03 | 50 | 49.5 | 302.33 | 303.40 | 304.40 | 307.0 | 0.00% | 0 | 100 | 13.61% | 157.7MiB / 2GiB |
| v2-new-spring | dbpool-5-100rps | 08 | 100 | 99.9 | 31.88 | 33.22 | 35.33 | 40.1 | 0.00% | 0 | 100 | 23.30% | 359.4MiB / 2GiB |
| v2-new-spring | dbpool-5-300rps | 08 | 300 | 212.1 | 3484.14 | 6084.27 | 6301.20 | 6377.5 | 23.44% | 1284 | 1383 | 44.93% | 452.2MiB / 2GiB |
| v2-new-spring | dbpool-20-100rps | 08 | 100 | 99.9 | 31.33 | 31.79 | 32.22 | 36.5 | 0.00% | 0 | 100 | 8.88% | 463.4MiB / 2GiB |
| v2-new-spring | dbpool-20-300rps | 08 | 300 | 299.7 | 31.10 | 31.61 | 31.99 | 39.4 | 0.00% | 0 | 100 | 18.01% | 465.4MiB / 2GiB |
| v2-new-jakarta | dbpool-5-100rps | 08 | 100 | 99.9 | 32.68 | 33.74 | 35.00 | 49.4 | 0.00% | 0 | 100 | 25.57% | 447.7MiB / 2GiB |
| v2-new-jakarta | dbpool-5-300rps | 08 | 300 | 162.3 | 6053.55 | 9234.85 | 9253.77 | 9257.6 | 0.00% | 2635 | 1500 | 28.33% | 482.2MiB / 2GiB |
| v2-new-jakarta | dbpool-20-100rps | 08 | 100 | 99.9 | 31.94 | 32.54 | 33.26 | 48.6 | 0.00% | 0 | 100 | 15.04% | 479.1MiB / 2GiB |
| v2-new-jakarta | dbpool-20-300rps | 08 | 300 | 299.7 | 31.67 | 32.96 | 34.36 | 59.9 | 0.00% | 0 | 100 | 36.29% | 475.2MiB / 2GiB |
| v2-new-jakarta | events-direct | 07 | 200 | 200.0 | 14.54 | 195.67 | 220.55 | 244.2 | 0.00% | 0 | 100 | 91.97% | 484.9MiB / 2GiB |
| v2-new-jakarta | events-event | 07 | 200 | 200.0 | 2.96 | 5.08 | 8.67 | 25.5 | 0.00% | 0 | 100 | 53.98% | 484.3MiB / 2GiB |
| v2-new-jakarta | events-event-inline | 07 | 200 | 200.0 | 7.65 | 17.01 | 34.79 | 106.7 | 0.00% | 0 | 100 | 45.41% | 480.5MiB / 2GiB |
| v2-new-jakarta | io-blocking-async-virtual-400rps | 04 | 400 | 203.7 | 10000.10 | 10000.96 | 10001.89 | 10065.2 | 100.00% | 3850 | 3000 | 57.74% | 552.8MiB / 2GiB |
| v2-new-jakarta | io-blocking-async-default-400rps | 04 | 400 | 180.0 | 9990.44 | 10000.93 | 10020.62 | 10225.1 | 100.00% | 4798 | 3000 | 147.89% | 768.6MiB / 2GiB |
| v2-new-dotnet10 | dbpool-5-100rps | 08 | 100 | 99.9 | 31.89 | 32.78 | 33.53 | 77.2 | 0.00% | 0 | 100 | 20.67% | 99.13MiB / 2GiB |
| v2-new-dotnet10 | dbpool-5-300rps | 08 | 300 | 283.3 | 1019.53 | 1031.78 | 1033.61 | 1071.3 | 44.37% | 213 | 313 | 53.17% | 142.7MiB / 2GiB |
| v2-new-dotnet10 | dbpool-20-100rps | 08 | 100 | 99.9 | 31.83 | 32.52 | 33.07 | 41.0 | 0.00% | 0 | 100 | 17.42% | 151.4MiB / 2GiB |
| v2-new-dotnet10 | dbpool-20-300rps | 08 | 300 | 299.7 | 31.64 | 32.44 | 33.07 | 37.4 | 0.00% | 0 | 100 | 53.20% | 152.1MiB / 2GiB |
| v2-new-dotnet10 | events-direct | 07 | 200 | 178.1 | 1675.83 | 2130.26 | 2176.47 | 2202.2 | 0.00% | 331 | 423 | 63.38% | 157.1MiB / 2GiB |
| v2-new-dotnet10 | events-event | 07 | 200 | 190.9 | 658.10 | 928.41 | 955.56 | 977.7 | 0.00% | 89 | 189 | 65.03% | 160.3MiB / 2GiB |
| v2-redis-spring | catalog-get | 01 | 2000 | 2000.0 | 0.54 | 1.34 | 5.59 | 95.7 | 0.00% | 0 | 200 | 76.96% | 440.4MiB / 2GiB |
| v2-redis-spring | redis-get | 08 | 2000 | 1998.2 | 1.00 | 6.63 | 43.96 | 143.9 | 0.00% | 51 | 225 | 119.20% | 492.5MiB / 2GiB |

## Repeatability — median [min – max] over repetitions

| Phase | Experiment | Lab | Target rps | n | Achieved rps | p50 ms | p99 ms | Dropped | Failed % |
|---|---|---|---:|---:|---|---|---|---|---|
| v2-rep5-jakarta | catalog-get | 01 | 2000 | 5 | 1987.5 [1531.9 – 1993.2] | 1.65 [1.43 – 562.87] | 217.96 [105.60 – 1130.60] | 363 [188 – 13729] | 0.00 [0.00 – 0.00] |
| v2-rep5-jakarta | io-concurrent | 03 | 50 | 5 | 49.5 [49.5 – 49.5] | 303.74 [303.49 – 304.01] | 307.06 [306.26 – 376.81] | 0 [0 – 0] | 0.00 [0.00 – 0.00] |
| v2-rep5-dotnet10 | catalog-get | 01 | 2000 | 5 | 1999.9 [1988.8 – 2000.0] | 0.93 [0.81 – 0.94] | 35.48 [21.42 – 54.40] | 0 [0 – 330] | 0.00 [0.00 – 0.00] |
| v2-rep5-dotnet10 | io-sequential-async | 03 | 50 | 5 | 49.0 [49.0 – 49.0] | 603.51 [603.45 – 603.79] | 606.85 [605.90 – 607.61] | 0 [0 – 0] | 0.00 [0.00 – 0.00] |
| v2-rep5-dotnet10 | io-concurrent | 03 | 50 | 5 | 49.5 [49.5 – 49.5] | 302.31 [302.23 – 302.39] | 304.28 [304.09 – 304.73] | 0 [0 – 0] | 0.00 [0.00 – 0.00] |

## Probe: DI captive / mutable state (Lab 06)

### v2-new-spring

```json
{
 "captive_captured": {
  "calls": 5,
  "distinct_ids": 1
 },
 "captive_provider": {
  "calls": 5,
  "distinct_ids": 5
 },
 "mutable_singleton": {
  "requests": 600,
  "wrong_user_returned": 586
 },
 "mutable_request": {
  "requests": 600,
  "wrong_user_returned": 0
 }
}
```

### v2-new-jakarta

```json
{
 "captive_captured": {
  "calls": 5,
  "distinct_ids": 1
 },
 "captive_provider": {
  "calls": 5,
  "distinct_ids": 5
 },
 "mutable_singleton": {
  "requests": 600,
  "wrong_user_returned": 568
 },
 "mutable_request": {
  "requests": 600,
  "wrong_user_returned": 0
 }
}
```

### v2-new-dotnet10

```json
{
 "captive_captured": {
  "calls": 5,
  "distinct_ids": 1
 },
 "captive_scoped": {
  "calls": 5,
  "distinct_ids": 5
 },
 "mutable_singleton": {
  "requests": 600,
  "wrong_user_returned": 582
 },
 "mutable_request": {
  "requests": 600,
  "wrong_user_returned": 0
 }
}
```

### v3-spring

```json
{
 "captive_captured": {
  "calls": 5,
  "distinct_ids": 1
 },
 "captive_provider": {
  "calls": 5,
  "distinct_ids": 5
 },
 "mutable_singleton": {
  "requests": 600,
  "wrong_user_returned": 577
 },
 "mutable_request": {
  "requests": 600,
  "wrong_user_returned": 0
 }
}
```


## Probe: Transactional events (Lab 07)

### v2-new-spring

```json
{
 "product": 843265,
 "committed_changes": 200,
 "request_errors": 0,
 "audit_delta": 200,
 "rollbacks_sent": 20,
 "rollback_http_errors": 20,
 "final_cents": 500,
 "rolled_back_price_visible": false,
 "p50_ms": 185.9437000239268
}
```

### v2-new-jakarta

```json
{
 "product": 843786,
 "committed_changes": 200,
 "request_errors": 0,
 "audit_delta": 100,
 "rollbacks_sent": 20,
 "rollback_http_errors": 20,
 "final_cents": 500,
 "rolled_back_price_visible": false,
 "p50_ms": 113.08945005293936
}
```

### v2-new-dotnet10

```json
{
 "product": 844124,
 "committed_changes": 200,
 "request_errors": 0,
 "audit_delta": 200,
 "rollbacks_sent": 20,
 "rollback_http_errors": 20,
 "final_cents": 500,
 "rolled_back_price_visible": false,
 "p50_ms": 233.48545003682375
}
```


## Probe: Virtual-thread pinning (Lab 04)

### v2-pinning-j21

```json
{
 "synchronized": {
  "median_ms": 1254.5,
  "min_ms": 1254,
  "max_ms": 1256,
  "carriers": "4",
  "runtime": "21.0.13.1"
 },
 "reentrant": {
  "median_ms": 50.0,
  "min_ms": 50,
  "max_ms": 51,
  "carriers": "4",
  "runtime": "21.0.13.1"
 }
}
```

### v2-pinning-j25

```json
{
 "synchronized": {
  "median_ms": 51.0,
  "min_ms": 50,
  "max_ms": 51,
  "carriers": "4",
  "runtime": "25.0.5.1"
 },
 "reentrant": {
  "median_ms": 50.0,
  "min_ms": 50,
  "max_ms": 54,
  "carriers": "4",
  "runtime": "25.0.5.1"
 }
}
```


## Probe: Redis shared cache stampede (Lab 08)

### v2-redis-spring

```json
{
 "none": {
  "requests_per_round": 100,
  "instances": 2,
  "loads_min": 50,
  "loads_max": 100,
  "loads": [
   50,
   89,
   97,
   100,
   100
  ],
  "client_p50_ms_median": 199.2557499324903
 },
 "local": {
  "requests_per_round": 100,
  "instances": 2,
  "loads_min": 2,
  "loads_max": 2,
  "loads": [
   2,
   2,
   2,
   2,
   2
  ],
  "client_p50_ms_median": 165.46265000943094
 },
 "distributed": {
  "requests_per_round": 100,
  "instances": 2,
  "loads_min": 1,
  "loads_max": 1,
  "loads": [
   1,
   1,
   1,
   1,
   1
  ],
  "client_p50_ms_median": 175.0816999701783
 }
}
```


Raw k6 summaries (`*.json`), `probes.json` and `environment.json` are stored next to this report.
