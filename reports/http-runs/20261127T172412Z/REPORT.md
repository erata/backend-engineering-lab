# HTTP benchmark report — measured local results

Indicative measurements of these lab implementations on one workstation. Not universal framework rankings.

- Run: `20261127T172412Z`  
- Host: v5 Redis client comparison, 20 logical CPUs, Windows-11-10.0.26300-SP0  
- Backend container quota: `cpus` per phase (default 4), `mem_limit` 2g. k6 grafana/k6:1.3.0 in a container on the Compose network.  
- Each k6 row: constant-arrival-rate, 10 s unreported warm-up, then the measured duration. Latency in ms. Container CPU/memory sampled once mid-run.

## Runtime identification

| Phase | /lab/threads/info |
|---|---|
| v5-redis-spring | `{"runtime": "25.0.5.1", "thread": "http-nio-0.0.0.0-8080-exec-3", "virtual": false, "image": "backend-engineering-lab-full-app sha256:e69d9b93619de1ac8edcab524a1a07887c9399d9e6d4df2a9c83a3fb15840c8f", "db_image": "mysql:8.4"}` |
| v5-redis-jakarta | `{"thread": "default task-4", "virtual": false, "runtime": "25.0.4.1", "image": "backend-engineering-lab-full-jakarta sha256:088cd90f4372cb93f18912f1a36cdf630b488aa01864d1934584cd02c5e2e76f", "db_image": "mysql:8.4"}` |
| v5-redis-jakarta-pool64 | `{"virtual": false, "runtime": "25.0.4.1", "thread": "default task-3", "image": "backend-engineering-lab-full-jakarta sha256:088cd90f4372cb93f18912f1a36cdf630b488aa01864d1934584cd02c5e2e76f", "db_image": "mysql:8.4"}` |
| v5-redis-dotnet10 | `{"runtime": "10.0.15", "processors": 4, "threadPool": 5, "image": "backend-engineering-lab-full-dotnet sha256:1bea8196c15b5a67685499cb1bcc92b2ed565e1719291ab778d027cd9c3d497b", "db_image": "mysql:8.4"}` |

## k6 results

| Phase | Experiment | Lab | Target rps | Achieved rps | p50 | p95 | p99 | max | Failed | Dropped | Max VUs | CPU | Memory |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| v5-redis-spring | redis-get | 08 | 2000 | 1986.7 | 1.78 | 71.07 | 152.59 | 387.9 | 0.00% | 394 | 323 | 250.78% | 498.8MiB / 2GiB |
| v5-redis-spring | redis-get | 08 | 2000 | 1997.5 | 1.37 | 4.94 | 30.79 | 228.5 | 0.00% | 71 | 226 | 233.65% | 513MiB / 2GiB |
| v5-redis-spring | redis-get | 08 | 2000 | 1980.5 | 1.23 | 27.46 | 94.01 | 437.0 | 0.00% | 570 | 369 | 212.19% | 513.8MiB / 2GiB |
| v5-redis-jakarta | redis-get | 08 | 2000 | 1542.9 | 518.73 | 963.85 | 1088.47 | 1580.3 | 0.00% | 13201 | 1000 | 419.58% | 550.3MiB / 2GiB |
| v5-redis-jakarta | redis-get | 08 | 2000 | 1876.4 | 120.07 | 580.14 | 810.71 | 1372.8 | 0.00% | 3407 | 1000 | 369.41% | 565.6MiB / 2GiB |
| v5-redis-jakarta | redis-get | 08 | 2000 | 1962.3 | 31.34 | 290.93 | 382.15 | 759.9 | 0.00% | 1125 | 665 | 381.43% | 564.1MiB / 2GiB |
| v5-redis-jakarta-pool64 | redis-get | 08 | 2000 | 1275.3 | 631.84 | 1285.32 | 1489.58 | 2086.4 | 0.00% | 20814 | 1000 | 422.34% | 546.6MiB / 2GiB |
| v5-redis-jakarta-pool64 | redis-get | 08 | 2000 | 1953.3 | 44.94 | 287.91 | 401.04 | 742.5 | 0.00% | 1197 | 687 | 287.22% | 548.9MiB / 2GiB |
| v5-redis-jakarta-pool64 | redis-get | 08 | 2000 | 1972.7 | 1.96 | 160.90 | 278.97 | 567.1 | 0.00% | 817 | 501 | 344.59% | 549MiB / 2GiB |
| v5-redis-dotnet10 | redis-get | 08 | 2000 | 1999.8 | 1.31 | 18.24 | 45.90 | 114.2 | 0.00% | 4 | 203 | 226.79% | 161.1MiB / 2GiB |
| v5-redis-dotnet10 | redis-get | 08 | 2000 | 1999.2 | 1.29 | 16.54 | 40.96 | 114.5 | 0.00% | 20 | 209 | 225.15% | 125.1MiB / 2GiB |
| v5-redis-dotnet10 | redis-get | 08 | 2000 | 1999.2 | 1.30 | 18.80 | 50.82 | 130.6 | 0.00% | 22 | 210 | 173.60% | 128.1MiB / 2GiB |

## Repeatability — median [min – max] over repetitions

| Phase | Experiment | Lab | Target rps | n | Achieved rps | p50 ms | p99 ms | Dropped | Failed % |
|---|---|---|---:|---:|---|---|---|---|---|
| v5-redis-spring | redis-get | 08 | 2000 | 3 | 1986.7 [1980.5 – 1997.5] | 1.37 [1.23 – 1.78] | 94.01 [30.79 – 152.59] | 394 [71 – 570] | 0.00 [0.00 – 0.00] |
| v5-redis-jakarta | redis-get | 08 | 2000 | 3 | 1876.4 [1542.9 – 1962.3] | 120.07 [31.34 – 518.73] | 810.71 [382.15 – 1088.47] | 3407 [1125 – 13201] | 0.00 [0.00 – 0.00] |
| v5-redis-jakarta-pool64 | redis-get | 08 | 2000 | 3 | 1953.3 [1275.3 – 1972.7] | 44.94 [1.96 – 631.84] | 401.04 [278.97 – 1489.58] | 1197 [817 – 20814] | 0.00 [0.00 – 0.00] |
| v5-redis-dotnet10 | redis-get | 08 | 2000 | 3 | 1999.2 [1999.2 – 1999.8] | 1.30 [1.29 – 1.31] | 45.90 [40.96 – 50.82] | 20 [4 – 22] | 0.00 [0.00 – 0.00] |

## Probe: Redis shared cache stampede (Lab 08)

### v5-redis-spring

```json
{
 "client_stats_after_k6": {
  "loads": 0,
  "fallbacks": 133,
  "id": 1,
  "client": "Lettuce"
 },
 "none": {
  "requests_per_round": 100,
  "instances": 2,
  "loads_min": 50,
  "loads_max": 100,
  "loads": [
   50,
   92,
   100,
   100,
   84
  ],
  "client_p50_ms_median": 205.4373499704525
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
  "client_p50_ms_median": 151.8552500056103
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
  "client_p50_ms_median": 167.89895005058497
 }
}
```

### v5-redis-jakarta

```json
{
 "client_stats_after_k6": {
  "fallbacks": 263,
  "loads": 0,
  "poolMax": 8,
  "client": "Jedis",
  "id": 1
 },
 "none": {
  "requests_per_round": 100,
  "instances": 2,
  "loads_min": 50,
  "loads_max": 100,
  "loads": [
   50,
   100,
   74,
   97,
   100
  ],
  "client_p50_ms_median": 198.37460003327578
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
  "client_p50_ms_median": 155.59774998109788
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
  "client_p50_ms_median": 160.19630001392215
 }
}
```

### v5-redis-jakarta-pool64

```json
{
 "client_stats_after_k6": {
  "loads": 0,
  "poolMax": 64,
  "client": "Jedis",
  "id": 1,
  "fallbacks": 0
 },
 "none": {
  "requests_per_round": 100,
  "instances": 2,
  "loads_min": 50,
  "loads_max": 100,
  "loads": [
   50,
   100,
   88,
   56,
   100
  ],
  "client_p50_ms_median": 188.96769999992102
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
  "client_p50_ms_median": 160.68430000450462
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
  "client_p50_ms_median": 153.9307499770075
 }
}
```

### v5-redis-dotnet10

```json
{
 "client_stats_after_k6": {
  "id": 1,
  "loads": 0,
  "fallbacks": 0,
  "client": "StackExchange.Redis"
 },
 "none": {
  "requests_per_round": 100,
  "instances": 2,
  "loads_min": 50,
  "loads_max": 100,
  "loads": [
   50,
   100,
   100,
   99,
   100
  ],
  "client_p50_ms_median": 219.39114993438125
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
  "client_p50_ms_median": 140.42684994637966
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
  "client_p50_ms_median": 166.89275007229298
 }
}
```


## Probe: Redis consistency and outage (Lab 08)

### v5-redis-spring

```json
{
 "consistency": {
  "db_value": "Product 42 v1795800493",
  "instance_b_before_invalidate": "Product 42",
  "stale_read": true,
  "instance_b_after_invalidate": "Product 42 v1795800493",
  "fresh_after_invalidate": true,
  "ttl_s": 30
 },
 "redis_stopped": {
  "sequential_10": {
   "first_ms": 506.3,
   "median_ms": 506.9,
   "max_ms": 532.0,
   "sources": [
    "db-fallback"
   ],
   "errors": [
    "QueryTimeoutException"
   ]
  },
  "concurrent_50": {
   "p50_ms": 538.3,
   "max_ms": 549.3,
   "sources": [
    "db-fallback"
   ],
   "errors": [
    "QueryTimeoutException"
   ]
  },
  "catalog_api_still_ok": true,
  "recovery_ms_after_restore": 961,
  "recovery_polls": 2
 },
 "redis_paused": {
  "sequential_10": {
   "first_ms": 531.1,
   "median_ms": 508.7,
   "max_ms": 531.1,
   "sources": [
    "db-fallback"
   ],
   "errors": [
    "QueryTimeoutException"
   ]
  },
  "concurrent_50": {
   "p50_ms": 527.4,
   "max_ms": 534.2,
   "sources": [
    "db-fallback"
   ],
   "errors": [
    "QueryTimeoutException"
   ]
  },
  "catalog_api_still_ok": true,
  "recovery_ms_after_restore": 6,
  "recovery_polls": 1
 },
 "client": "Lettuce"
}
```

### v5-redis-jakarta

```json
{
 "consistency": {
  "db_value": "Product 42 v1795800750",
  "instance_b_before_invalidate": "Product 42",
  "stale_read": true,
  "instance_b_after_invalidate": "Product 42 v1795800750",
  "fresh_after_invalidate": true,
  "ttl_s": 30
 },
 "redis_stopped": {
  "sequential_10": {
   "first_ms": 2768.4,
   "median_ms": 4.4,
   "max_ms": 2768.4,
   "sources": [
    "db-fallback"
   ],
   "errors": [
    "JedisConnectionException"
   ]
  },
  "concurrent_50": {
   "p50_ms": 34.8,
   "max_ms": 45.7,
   "sources": [
    "db-fallback"
   ],
   "errors": [
    "JedisConnectionException"
   ]
  },
  "catalog_api_still_ok": true,
  "recovery_ms_after_restore": 9532,
  "recovery_polls": 148
 },
 "redis_paused": {
  "sequential_10": {
   "first_ms": 1012.5,
   "median_ms": 508.2,
   "max_ms": 1012.5,
   "sources": [
    "db-fallback"
   ],
   "errors": [
    "JedisConnectionException"
   ]
  },
  "concurrent_50": {
   "p50_ms": 526.4,
   "max_ms": 1015.8,
   "sources": [
    "db-fallback"
   ],
   "errors": [
    "JedisConnectionException",
    "JedisException"
   ]
  },
  "catalog_api_still_ok": true,
  "recovery_ms_after_restore": 23,
  "recovery_polls": 1
 },
 "client": "Jedis"
}
```

### v5-redis-dotnet10

```json
{
 "consistency": {
  "db_value": "Product 42 v1795801144",
  "instance_b_before_invalidate": "Product 42",
  "stale_read": true,
  "instance_b_after_invalidate": "Product 42 v1795801144",
  "fresh_after_invalidate": true,
  "ttl_s": 30
 },
 "redis_stopped": {
  "sequential_10": {
   "first_ms": 611.6,
   "median_ms": 999.8,
   "max_ms": 1004.3,
   "sources": [
    "db-fallback"
   ],
   "errors": [
    "RedisConnectionException"
   ]
  },
  "concurrent_50": {
   "p50_ms": 984.1,
   "max_ms": 1009.2,
   "sources": [
    "db-fallback"
   ],
   "errors": [
    "RedisConnectionException"
   ]
  },
  "catalog_api_still_ok": true,
  "recovery_ms_after_restore": 726,
  "recovery_polls": 2
 },
 "redis_paused": {
  "sequential_10": {
   "first_ms": 728.6,
   "median_ms": 999.4,
   "max_ms": 1002.7,
   "sources": [
    "db-fallback"
   ],
   "errors": [
    "RedisTimeoutException"
   ]
  },
  "concurrent_50": {
   "p50_ms": 1000.5,
   "max_ms": 1007.8,
   "sources": [
    "db-fallback"
   ],
   "errors": [
    "RedisTimeoutException"
   ]
  },
  "catalog_api_still_ok": true,
  "recovery_ms_after_restore": 945,
  "recovery_polls": 2
 },
 "client": "StackExchange.Redis"
}
```


Raw k6 summaries (`*.json`), `probes.json` and `environment.json` are stored next to this report.
