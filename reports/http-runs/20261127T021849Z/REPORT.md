# HTTP benchmark report — measured local results

Indicative measurements of these lab implementations on one workstation. Not universal framework rankings.

- Run: `20261127T021849Z`  
- Host: 13th Gen Intel(R) Core(TM) i7-13700H, 20 logical CPUs, Windows-11-10.0.26300-SP0  
- Backend container quota: `cpus` per phase (default 4), `mem_limit` 2g. k6 grafana/k6:1.3.0 in a container on the Compose network.  
- Each k6 row: constant-arrival-rate, 10 s unreported warm-up, then the measured duration. Latency in ms. Container CPU/memory sampled once mid-run.

## Runtime identification

| Phase | /lab/threads/info |
|---|---|
| v4-rep5-spring-j25-platform | `{"thread": "http-nio-0.0.0.0-8080-exec-3", "runtime": "25.0.5.1", "virtual": false, "image": "backend-engineering-lab-full-app sha256:df7139e7a20f3f43cc250474ecd7a6d30ead4f5d2f91158d18c8bf7bdb631626", "db_image": "mysql:8.4"}` |
| v4-rep5-spring-j25-virtual | `{"thread": "tomcat-handler-1", "virtual": true, "runtime": "25.0.5.1", "image": "backend-engineering-lab-full-app sha256:df7139e7a20f3f43cc250474ecd7a6d30ead4f5d2f91158d18c8bf7bdb631626", "db_image": "mysql:8.4"}` |

## k6 results

| Phase | Experiment | Lab | Target rps | Achieved rps | p50 | p95 | p99 | max | Failed | Dropped | Max VUs | CPU | Memory |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| v4-rep5-spring-j25-platform | io-blocking | 03 | 50 | 49.0 | 607.07 | 609.28 | 611.34 | 617.7 | 0.00% | 0 | 100 | 38.68% | 328.6MiB / 2GiB |
| v4-rep5-spring-j25-platform | io-blocking | 03 | 50 | 49.0 | 606.42 | 608.55 | 610.09 | 622.8 | 0.00% | 0 | 100 | 58.62% | 337.1MiB / 2GiB |
| v4-rep5-spring-j25-platform | io-blocking | 03 | 50 | 49.0 | 605.67 | 607.49 | 608.46 | 610.4 | 0.00% | 0 | 100 | 18.10% | 341.4MiB / 2GiB |
| v4-rep5-spring-j25-platform | io-blocking | 03 | 50 | 49.0 | 605.75 | 608.47 | 610.24 | 617.3 | 0.00% | 0 | 100 | 14.88% | 353.1MiB / 2GiB |
| v4-rep5-spring-j25-platform | io-blocking | 03 | 50 | 49.0 | 605.66 | 608.39 | 609.68 | 611.6 | 0.00% | 0 | 100 | 19.55% | 351.9MiB / 2GiB |
| v4-rep5-spring-j25-platform | io-sequential-async | 03 | 50 | 49.0 | 605.75 | 607.75 | 608.73 | 617.8 | 0.00% | 0 | 100 | 13.81% | 354.1MiB / 2GiB |
| v4-rep5-spring-j25-platform | io-sequential-async | 03 | 50 | 49.0 | 605.56 | 607.36 | 608.37 | 610.9 | 0.00% | 0 | 100 | 17.65% | 353.5MiB / 2GiB |
| v4-rep5-spring-j25-platform | io-sequential-async | 03 | 50 | 49.0 | 605.51 | 607.19 | 608.19 | 612.9 | 0.00% | 0 | 100 | 15.75% | 353.8MiB / 2GiB |
| v4-rep5-spring-j25-platform | io-sequential-async | 03 | 50 | 49.0 | 605.64 | 607.67 | 608.65 | 612.2 | 0.00% | 0 | 100 | 23.51% | 354.7MiB / 2GiB |
| v4-rep5-spring-j25-platform | io-sequential-async | 03 | 50 | 49.0 | 605.49 | 607.15 | 607.87 | 622.0 | 0.00% | 0 | 100 | 17.04% | 354.5MiB / 2GiB |
| v4-rep5-spring-j25-platform | io-concurrent | 03 | 50 | 49.5 | 303.37 | 304.93 | 305.75 | 309.1 | 0.00% | 0 | 100 | 23.21% | 357.7MiB / 2GiB |
| v4-rep5-spring-j25-platform | io-concurrent | 03 | 50 | 49.5 | 303.12 | 304.36 | 305.20 | 308.8 | 0.00% | 0 | 100 | 16.64% | 358.4MiB / 2GiB |
| v4-rep5-spring-j25-platform | io-concurrent | 03 | 50 | 49.5 | 303.35 | 304.66 | 305.66 | 316.2 | 0.00% | 0 | 100 | 18.26% | 357.5MiB / 2GiB |
| v4-rep5-spring-j25-platform | io-concurrent | 03 | 50 | 49.5 | 302.99 | 304.30 | 305.36 | 313.6 | 0.00% | 0 | 100 | 17.49% | 358.6MiB / 2GiB |
| v4-rep5-spring-j25-platform | io-concurrent | 03 | 50 | 49.5 | 302.69 | 303.68 | 304.44 | 308.1 | 0.00% | 0 | 100 | 12.46% | 357.8MiB / 2GiB |
| v4-rep5-spring-j25-platform | io-blocking-400rps | 04 | 400 | 324.3 | 2435.47 | 3875.82 | 4017.12 | 4086.0 | 0.00% | 953 | 1343 | 76.52% | 464.6MiB / 2GiB |
| v4-rep5-spring-j25-platform | io-blocking-400rps | 04 | 400 | 324.1 | 2426.31 | 3861.81 | 4001.05 | 4094.8 | 0.00% | 964 | 1340 | 91.16% | 482.4MiB / 2GiB |
| v4-rep5-spring-j25-platform | io-blocking-400rps | 04 | 400 | 324.3 | 2431.40 | 3879.73 | 4018.15 | 4089.7 | 0.00% | 951 | 1342 | 68.71% | 486.1MiB / 2GiB |
| v4-rep5-spring-j25-platform | io-blocking-400rps | 04 | 400 | 324.2 | 2435.80 | 3876.09 | 4014.76 | 4091.4 | 0.00% | 953 | 1339 | 83.65% | 493.9MiB / 2GiB |
| v4-rep5-spring-j25-platform | io-blocking-400rps | 04 | 400 | 323.9 | 2419.22 | 3878.32 | 4013.69 | 4107.4 | 0.00% | 957 | 1344 | 82.74% | 495.2MiB / 2GiB |
| v4-rep5-spring-j25-virtual | io-blocking | 03 | 50 | 49.0 | 607.19 | 610.57 | 613.58 | 659.5 | 0.00% | 0 | 100 | 35.28% | 347MiB / 2GiB |
| v4-rep5-spring-j25-virtual | io-blocking | 03 | 50 | 49.0 | 610.49 | 615.04 | 623.72 | 638.7 | 0.00% | 0 | 100 | 136.56% | 349.4MiB / 2GiB |
| v4-rep5-spring-j25-virtual | io-blocking | 03 | 50 | 49.0 | 606.93 | 609.88 | 611.18 | 614.0 | 0.00% | 0 | 100 | 30.72% | 365.9MiB / 2GiB |
| v4-rep5-spring-j25-virtual | io-blocking | 03 | 50 | 49.0 | 605.41 | 607.35 | 608.77 | 616.1 | 0.00% | 0 | 100 | 16.77% | 374.6MiB / 2GiB |
| v4-rep5-spring-j25-virtual | io-blocking | 03 | 50 | 49.0 | 605.65 | 607.48 | 608.49 | 613.1 | 0.00% | 0 | 100 | 18.73% | 374.7MiB / 2GiB |
| v4-rep5-spring-j25-virtual | io-blocking-400rps | 04 | 400 | 392.1 | 605.99 | 615.83 | 634.91 | 688.5 | 0.00% | 0 | 400 | 133.94% | 472.8MiB / 2GiB |
| v4-rep5-spring-j25-virtual | io-blocking-400rps | 04 | 400 | 392.1 | 605.78 | 609.28 | 617.60 | 637.0 | 0.00% | 0 | 400 | 140.07% | 488MiB / 2GiB |
| v4-rep5-spring-j25-virtual | io-blocking-400rps | 04 | 400 | 392.1 | 605.59 | 608.06 | 616.11 | 630.0 | 0.00% | 0 | 400 | 126.84% | 488.3MiB / 2GiB |
| v4-rep5-spring-j25-virtual | io-blocking-400rps | 04 | 400 | 391.8 | 607.19 | 664.66 | 714.49 | 784.8 | 0.00% | 0 | 400 | 221.51% | 488.6MiB / 2GiB |
| v4-rep5-spring-j25-virtual | io-blocking-400rps | 04 | 400 | 392.0 | 606.16 | 614.73 | 631.26 | 667.3 | 0.00% | 0 | 400 | 127.61% | 495.7MiB / 2GiB |

## Repeatability — median [min – max] over repetitions

| Phase | Experiment | Lab | Target rps | n | Achieved rps | p50 ms | p99 ms | Dropped | Failed % |
|---|---|---|---:|---:|---|---|---|---|---|
| v4-rep5-spring-j25-platform | io-blocking | 03 | 50 | 5 | 49.0 [49.0 – 49.0] | 605.75 [605.66 – 607.07] | 610.09 [608.46 – 611.34] | 0 [0 – 0] | 0.00 [0.00 – 0.00] |
| v4-rep5-spring-j25-platform | io-sequential-async | 03 | 50 | 5 | 49.0 [49.0 – 49.0] | 605.56 [605.49 – 605.75] | 608.37 [607.87 – 608.73] | 0 [0 – 0] | 0.00 [0.00 – 0.00] |
| v4-rep5-spring-j25-platform | io-concurrent | 03 | 50 | 5 | 49.5 [49.5 – 49.5] | 303.12 [302.69 – 303.37] | 305.36 [304.44 – 305.75] | 0 [0 – 0] | 0.00 [0.00 – 0.00] |
| v4-rep5-spring-j25-platform | io-blocking-400rps | 04 | 400 | 5 | 324.2 [323.9 – 324.3] | 2431.40 [2419.22 – 2435.80] | 4014.76 [4001.05 – 4018.15] | 953 [951 – 964] | 0.00 [0.00 – 0.00] |
| v4-rep5-spring-j25-virtual | io-blocking | 03 | 50 | 5 | 49.0 [49.0 – 49.0] | 606.93 [605.41 – 610.49] | 611.18 [608.49 – 623.72] | 0 [0 – 0] | 0.00 [0.00 – 0.00] |
| v4-rep5-spring-j25-virtual | io-blocking-400rps | 04 | 400 | 5 | 392.1 [391.8 – 392.1] | 605.99 [605.59 – 607.19] | 631.26 [616.11 – 714.49] | 0 [0 – 0] | 0.00 [0.00 – 0.00] |

Raw k6 summaries (`*.json`), `probes.json` and `environment.json` are stored next to this report.
