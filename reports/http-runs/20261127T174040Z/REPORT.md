# HTTP benchmark report — measured local results

Indicative measurements of these lab implementations on one workstation. Not universal framework rankings.

- Run: `20261127T174040Z`  
- Host: v5b Redis Jedis repetitions and DNS check, 20 logical CPUs, Windows-11-10.0.26300-SP0  
- Backend container quota: `cpus` per phase (default 4), `mem_limit` 2g. k6 grafana/k6:1.3.0 in a container on the Compose network.  
- Each k6 row: constant-arrival-rate, 10 s unreported warm-up, then the measured duration. Latency in ms. Container CPU/memory sampled once mid-run.

## Runtime identification

| Phase | /lab/threads/info |
|---|---|
| v5b-redis-jakarta-rep5 | `{"virtual": false, "thread": "default task-3", "runtime": "25.0.4.1", "image": "backend-engineering-lab-full-jakarta sha256:088cd90f4372cb93f18912f1a36cdf630b488aa01864d1934584cd02c5e2e76f", "db_image": "mysql:8.4"}` |
| v5b-redis-jakarta-pool64-rep5 | `{"virtual": false, "runtime": "25.0.4.1", "thread": "default task-3", "image": "backend-engineering-lab-full-jakarta sha256:088cd90f4372cb93f18912f1a36cdf630b488aa01864d1934584cd02c5e2e76f", "db_image": "mysql:8.4"}` |
| v5b-redis-jakarta-dns0 | `{"thread": "default task-3", "runtime": "25.0.4.1", "virtual": false, "image": "backend-engineering-lab-full-jakarta sha256:088cd90f4372cb93f18912f1a36cdf630b488aa01864d1934584cd02c5e2e76f", "db_image": "mysql:8.4"}` |

## k6 results

| Phase | Experiment | Lab | Target rps | Achieved rps | p50 | p95 | p99 | max | Failed | Dropped | Max VUs | CPU | Memory |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| v5b-redis-jakarta-rep5 | redis-get | 08 | 2000 | 1806.0 | 104.26 | 746.59 | 896.95 | 1285.7 | 0.00% | 5737 | 1000 | 406.06% | 519.8MiB / 2GiB |
| v5b-redis-jakarta-rep5 | redis-get | 08 | 2000 | 1813.6 | 275.83 | 729.74 | 867.81 | 1337.2 | 0.00% | 5584 | 1000 | 395.15% | 590.9MiB / 2GiB |
| v5b-redis-jakarta-rep5 | redis-get | 08 | 2000 | 1989.6 | 1.96 | 98.66 | 184.68 | 541.9 | 0.00% | 289 | 344 | 362.91% | 588.9MiB / 2GiB |
| v5b-redis-jakarta-rep5 | redis-get | 08 | 2000 | 1944.2 | 4.04 | 238.13 | 366.55 | 800.1 | 0.00% | 1028 | 634 | 266.55% | 589.9MiB / 2GiB |
| v5b-redis-jakarta-rep5 | redis-get | 08 | 2000 | 1965.6 | 38.89 | 234.18 | 324.82 | 848.2 | 0.00% | 831 | 577 | 411.62% | 589.6MiB / 2GiB |
| v5b-redis-jakarta-pool64-rep5 | redis-get | 08 | 2000 | 1760.0 | 461.84 | 682.05 | 778.19 | 1103.1 | 0.00% | 6969 | 1000 | 429.03% | 512.9MiB / 2GiB |
| v5b-redis-jakarta-pool64-rep5 | redis-get | 08 | 2000 | 1925.9 | 211.80 | 532.90 | 637.68 | 1096.1 | 0.00% | 2190 | 1000 | 409.81% | 528.8MiB / 2GiB |
| v5b-redis-jakarta-pool64-rep5 | redis-get | 08 | 2000 | 1974.4 | 2.56 | 108.24 | 195.55 | 502.0 | 0.00% | 492 | 379 | 402.86% | 526.6MiB / 2GiB |
| v5b-redis-jakarta-pool64-rep5 | redis-get | 08 | 2000 | 1972.6 | 7.46 | 195.25 | 301.09 | 574.0 | 0.00% | 761 | 553 | 305.63% | 542.2MiB / 2GiB |
| v5b-redis-jakarta-pool64-rep5 | redis-get | 08 | 2000 | 1971.2 | 1.93 | 185.30 | 308.89 | 577.2 | 0.00% | 857 | 564 | 220.61% | 541.7MiB / 2GiB |

## Repeatability — median [min – max] over repetitions

| Phase | Experiment | Lab | Target rps | n | Achieved rps | p50 ms | p99 ms | Dropped | Failed % |
|---|---|---|---:|---:|---|---|---|---|---|
| v5b-redis-jakarta-rep5 | redis-get | 08 | 2000 | 5 | 1944.2 [1806.0 – 1989.6] | 38.89 [1.96 – 275.83] | 366.55 [184.68 – 896.95] | 1028 [289 – 5737] | 0.00 [0.00 – 0.00] |
| v5b-redis-jakarta-pool64-rep5 | redis-get | 08 | 2000 | 5 | 1971.2 [1760.0 – 1974.4] | 7.46 [1.93 – 461.84] | 308.89 [195.55 – 778.19] | 857 [492 – 6969] | 0.00 [0.00 – 0.00] |

## Probe: Redis consistency and outage (Lab 08)

### v5b-redis-jakarta-dns0

```json
{
 "consistency": {
  "db_value": "Product 42 v1795801798",
  "instance_b_before_invalidate": "Product 42",
  "stale_read": true,
  "instance_b_after_invalidate": "Product 42 v1795801798",
  "fresh_after_invalidate": true,
  "ttl_s": 30
 },
 "redis_stopped": {
  "sequential_10": {
   "first_ms": 511.8,
   "median_ms": 512.6,
   "max_ms": 541.7,
   "sources": [
    "db-fallback"
   ],
   "errors": [
    "JedisConnectionException"
   ]
  },
  "concurrent_50": {
   "p50_ms": 575.9,
   "max_ms": 1029.4,
   "sources": [
    "db-fallback"
   ],
   "errors": [
    "JedisConnectionException",
    "JedisException"
   ]
  },
  "catalog_api_still_ok": true,
  "recovery_ms_after_restore": 10,
  "recovery_polls": 1
 },
 "redis_paused": {
  "sequential_10": {
   "first_ms": 1031.9,
   "median_ms": 511.4,
   "max_ms": 1031.9,
   "sources": [
    "db-fallback"
   ],
   "errors": [
    "JedisConnectionException"
   ]
  },
  "concurrent_50": {
   "p50_ms": 532.1,
   "max_ms": 1021.4,
   "sources": [
    "db-fallback"
   ],
   "errors": [
    "JedisConnectionException",
    "JedisException"
   ]
  },
  "catalog_api_still_ok": true,
  "recovery_ms_after_restore": 10,
  "recovery_polls": 1
 },
 "client": "Jedis"
}
```


Raw k6 summaries (`*.json`), `probes.json` and `environment.json` are stored next to this report.
