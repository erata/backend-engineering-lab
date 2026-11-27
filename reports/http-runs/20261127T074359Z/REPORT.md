# HTTP benchmark report — measured local results

Indicative measurements of these lab implementations on one workstation. Not universal framework rankings.

- Run: `20261127T074359Z`  
- Host: 13th Gen Intel(R) Core(TM) i7-13700H, 20 logical CPUs, Windows-11-10.0.26300-SP0  
- Backend container quota: `cpus` per phase (default 4), `mem_limit` 2g. k6 grafana/k6:1.3.0 in a container on the Compose network.  
- Each k6 row: constant-arrival-rate, 10 s unreported warm-up, then the measured duration. Latency in ms. Container CPU/memory sampled once mid-run.

## Runtime identification

| Phase | /lab/threads/info |
|---|---|
| v4-rep3-jakarta-saturation | `{"virtual": false, "runtime": "25.0.4.1", "thread": "default task-2", "image": "backend-engineering-lab-full-jakarta sha256:d1f8d3d867c34bd8d0b4afa57847fe2a3f700a41c1e9be868cc9d98ad56a6c40", "db_image": "mysql:8.4"}` |

## k6 results

| Phase | Experiment | Lab | Target rps | Achieved rps | p50 | p95 | p99 | max | Failed | Dropped | Max VUs | CPU | Memory |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| v4-rep3-jakarta-saturation | io-blocking-400rps | 04 | 400 | 210.3 | 10000.21 | 10000.92 | 10001.12 | 10009.2 | 88.57% | 3588 | 3000 | 51.55% | 524.2MiB / 2GiB |
| v4-rep3-jakarta-saturation | io-blocking-400rps | 04 | 400 | 213.8 | 9999.97 | 10000.89 | 10001.10 | 10003.1 | 81.29% | 3449 | 3000 | 29.91% | 587.1MiB / 2GiB |
| v4-rep3-jakarta-saturation | io-blocking-400rps | 04 | 400 | 213.4 | 9999.98 | 10000.88 | 10001.11 | 10012.0 | 81.26% | 3464 | 3000 | 24.83% | 609.1MiB / 2GiB |
| v4-rep3-jakarta-saturation | io-blocking-async-virtual-400rps | 04 | 400 | 392.0 | 605.84 | 610.94 | 617.00 | 636.4 | 0.00% | 0 | 400 | 119.98% | 623.5MiB / 2GiB |
| v4-rep3-jakarta-saturation | io-blocking-async-virtual-400rps | 04 | 400 | 392.1 | 605.51 | 608.59 | 614.35 | 638.8 | 0.00% | 0 | 400 | 148.90% | 610.5MiB / 2GiB |
| v4-rep3-jakarta-saturation | io-blocking-async-virtual-400rps | 04 | 400 | 392.1 | 605.39 | 608.19 | 613.25 | 627.5 | 0.00% | 0 | 400 | 116.63% | 590.1MiB / 2GiB |
| v4-rep3-jakarta-saturation | io-blocking-async-default-400rps | 04 | 400 | 204.8 | 10000.16 | 10000.90 | 10001.06 | 10027.3 | 100.00% | 3808 | 3000 | 21.24% | 646.2MiB / 2GiB |
| v4-rep3-jakarta-saturation | io-blocking-async-default-400rps | 04 | 400 | 204.7 | 9990.63 | 10000.74 | 10000.96 | 10009.1 | 100.00% | 3813 | 3000 | 21.05% | 723.1MiB / 2GiB |
| v4-rep3-jakarta-saturation | io-blocking-async-default-400rps | 04 | 400 | 204.9 | 9989.14 | 10000.50 | 10000.89 | 10008.7 | 100.00% | 3803 | 3000 | 18.33% | 861.5MiB / 2GiB |

## Repeatability — median [min – max] over repetitions

| Phase | Experiment | Lab | Target rps | n | Achieved rps | p50 ms | p99 ms | Dropped | Failed % |
|---|---|---|---:|---:|---|---|---|---|---|
| v4-rep3-jakarta-saturation | io-blocking-400rps | 04 | 400 | 3 | 213.4 [210.3 – 213.8] | 9999.98 [9999.97 – 10000.21] | 10001.11 [10001.10 – 10001.12] | 3464 [3449 – 3588] | 81.29 [81.26 – 88.57] |
| v4-rep3-jakarta-saturation | io-blocking-async-virtual-400rps | 04 | 400 | 3 | 392.1 [392.0 – 392.1] | 605.51 [605.39 – 605.84] | 614.35 [613.25 – 617.00] | 0 [0 – 0] | 0.00 [0.00 – 0.00] |
| v4-rep3-jakarta-saturation | io-blocking-async-default-400rps | 04 | 400 | 3 | 204.8 [204.7 – 204.9] | 9990.63 [9989.14 – 10000.16] | 10000.96 [10000.89 – 10001.06] | 3808 [3803 – 3813] | 100.00 [100.00 – 100.00] |

Raw k6 summaries (`*.json`), `probes.json` and `environment.json` are stored next to this report.
