# HTTP benchmark report — measured local results

Indicative measurements of these lab implementations on one workstation. Not universal framework rankings.

- Run: `20261127T063929Z`  
- Host: 13th Gen Intel(R) Core(TM) i7-13700H, 20 logical CPUs, Windows-11-10.0.26300-SP0  
- Backend container quota: `cpus` per phase (default 4), `mem_limit` 2g. k6 grafana/k6:1.3.0 in a container on the Compose network.  
- Each k6 row: constant-arrival-rate, 10 s unreported warm-up, then the measured duration. Latency in ms. Container CPU/memory sampled once mid-run.

## Runtime identification

| Phase | /lab/threads/info |
|---|---|
| v4-rep5-spring-j17-platform | `{"thread": "http-nio-0.0.0.0-8080-exec-2", "runtime": "17.0.21.1", "virtual": false, "image": "backend-engineering-lab-full-app sha256:0de81ad9074c79154fef300706a7c7a45d52fb7e687fe7288e1632c228f9ac02", "db_image": "mysql:8.4"}` |
| v4-rep5-jakarta | `{"virtual": false, "runtime": "25.0.4.1", "thread": "default task-3", "image": "backend-engineering-lab-full-jakarta sha256:09d844d1ae0e71794f9645d83a999f58e0e1f12da53827094a139c098aa8e029", "db_image": "mysql:8.4"}` |
| v4-rep3-jakarta-saturation | `{"thread": "default task-2", "runtime": "25.0.4.1", "virtual": false, "image": "backend-engineering-lab-full-jakarta sha256:09d844d1ae0e71794f9645d83a999f58e0e1f12da53827094a139c098aa8e029", "db_image": "mysql:8.4"}` |
| v4-rep5-dotnet10 | `{"runtime": "10.0.15", "processors": 4, "threadPool": 5, "image": "backend-engineering-lab-full-dotnet sha256:d15d83080c1accd1481a78a6c2c9f6d8ccc82d5d212296ec62885f0be0302d4a", "db_image": "mysql:8.4"}` |
| v4-rep3-dotnet-saturation | `{"runtime": "10.0.15", "processors": 4, "threadPool": 5, "image": "backend-engineering-lab-full-dotnet sha256:d15d83080c1accd1481a78a6c2c9f6d8ccc82d5d212296ec62885f0be0302d4a", "db_image": "mysql:8.4"}` |
| v4-dotnet11-saturation | `{"runtime": "11.0.0", "processors": 4, "threadPool": 5, "image": "backend-engineering-lab-full-dotnet sha256:2d0a580643fecb8caf7237736f8f233e037ce5f5a1981cafdba7b9ba108ba887", "db_image": "mysql:8.4"}` |

## k6 results

| Phase | Experiment | Lab | Target rps | Achieved rps | p50 | p95 | p99 | max | Failed | Dropped | Max VUs | CPU | Memory |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| v4-rep5-spring-j17-platform | io-blocking-400rps | 04 | 400 | 324.3 | 2452.95 | 3895.57 | 4026.83 | 4112.3 | 0.00% | 955 | 1349 | 96.08% | 578.3MiB / 2GiB |
| v4-rep5-spring-j17-platform | io-blocking-400rps | 04 | 400 | 324.6 | 2420.91 | 3875.11 | 4016.11 | 4100.9 | 0.00% | 943 | 1339 | 65.75% | 569.6MiB / 2GiB |
| v4-rep5-spring-j17-platform | io-blocking-400rps | 04 | 400 | 322.8 | 2479.25 | 3906.09 | 4036.20 | 4099.4 | 0.00% | 998 | 1352 | 133.04% | 569.6MiB / 2GiB |
| v4-rep5-spring-j17-platform | io-blocking-400rps | 04 | 400 | 324.2 | 2434.41 | 3883.68 | 4018.58 | 4107.2 | 0.00% | 948 | 1345 | 58.27% | 569.9MiB / 2GiB |
| v4-rep5-spring-j17-platform | io-blocking-400rps | 04 | 400 | 319.5 | 2410.64 | 3902.64 | 3981.93 | 4019.6 | 0.00% | 1135 | 1293 | 84.99% | 569.6MiB / 2GiB |
| v4-rep5-jakarta | io-blocking | 03 | 50 | 49.0 | 607.62 | 612.41 | 614.88 | 619.7 | 0.00% | 0 | 100 | 29.77% | 520.6MiB / 2GiB |
| v4-rep5-jakarta | io-blocking | 03 | 50 | 49.0 | 606.26 | 608.02 | 609.11 | 614.1 | 0.00% | 0 | 100 | 55.27% | 524.8MiB / 2GiB |
| v4-rep5-jakarta | io-blocking | 03 | 50 | 49.0 | 605.79 | 607.60 | 608.99 | 615.0 | 0.00% | 0 | 100 | 18.95% | 525.4MiB / 2GiB |
| v4-rep5-jakarta | io-blocking | 03 | 50 | 49.0 | 607.09 | 610.94 | 612.91 | 623.0 | 0.00% | 0 | 100 | 19.60% | 524.9MiB / 2GiB |
| v4-rep5-jakarta | io-blocking | 03 | 50 | 49.0 | 606.76 | 609.65 | 611.00 | 619.3 | 0.00% | 0 | 100 | 21.33% | 526MiB / 2GiB |
| v4-rep5-jakarta | io-sequential-async | 03 | 50 | 49.0 | 607.12 | 609.91 | 611.05 | 618.2 | 0.00% | 0 | 100 | 42.98% | 526.4MiB / 2GiB |
| v4-rep5-jakarta | io-sequential-async | 03 | 50 | 49.0 | 607.11 | 615.25 | 734.56 | 1223.5 | 0.00% | 0 | 100 | 42.87% | 524.1MiB / 2GiB |
| v4-rep5-jakarta | io-sequential-async | 03 | 50 | 49.0 | 605.82 | 608.15 | 609.55 | 620.7 | 0.00% | 0 | 100 | 17.12% | 523.8MiB / 2GiB |
| v4-rep5-jakarta | io-sequential-async | 03 | 50 | 49.0 | 605.69 | 607.54 | 608.55 | 613.5 | 0.00% | 0 | 100 | 23.67% | 523.9MiB / 2GiB |
| v4-rep5-jakarta | io-sequential-async | 03 | 50 | 49.0 | 605.34 | 607.10 | 608.28 | 625.1 | 0.00% | 0 | 100 | 15.09% | 523.8MiB / 2GiB |
| v4-rep5-jakarta | io-concurrent | 03 | 50 | 49.5 | 303.03 | 304.23 | 305.28 | 320.8 | 0.00% | 0 | 100 | 15.45% | 524.1MiB / 2GiB |
| v4-rep5-jakarta | io-concurrent | 03 | 50 | 49.5 | 303.03 | 304.11 | 304.92 | 308.7 | 0.00% | 0 | 100 | 16.42% | 524.3MiB / 2GiB |
| v4-rep5-jakarta | io-concurrent | 03 | 50 | 49.5 | 303.02 | 303.91 | 304.57 | 311.7 | 0.00% | 0 | 100 | 16.73% | 524.5MiB / 2GiB |
| v4-rep5-jakarta | io-concurrent | 03 | 50 | 49.5 | 303.01 | 304.01 | 304.42 | 307.9 | 0.00% | 0 | 100 | 16.93% | 524.4MiB / 2GiB |
| v4-rep5-jakarta | io-concurrent | 03 | 50 | 49.5 | 303.04 | 304.16 | 304.99 | 306.4 | 0.00% | 0 | 100 | 18.51% | 524MiB / 2GiB |
| v4-rep3-jakarta-saturation | io-blocking-400rps | 04 | 400 | 209.3 | 10000.19 | 10000.92 | 10001.17 | 10010.4 | 89.35% | 3626 | 3000 | 40.31% | 512.9MiB / 2GiB |
| v4-rep3-jakarta-saturation | io-blocking-400rps | 04 | 400 | 213.2 | 9999.94 | 10000.87 | 10001.07 | 10002.1 | 81.24% | 3474 | 3000 | 26.94% | 572.9MiB / 2GiB |
| v4-rep3-jakarta-saturation | io-blocking-400rps | 04 | 400 | 213.4 | 10000.01 | 10000.91 | 10001.14 | 10008.4 | 81.25% | 3465 | 3000 | 49.14% | 596MiB / 2GiB |
| v4-rep3-jakarta-saturation | io-blocking-async-virtual-400rps | 04 | 400 | 204.8 | 9999.90 | 10000.81 | 10001.03 | 10009.4 | 100.00% | 3808 | 3000 | 29.51% | 661.6MiB / 2GiB |
| v4-rep3-jakarta-saturation | io-blocking-async-virtual-400rps | 04 | 400 | 204.7 | 9990.38 | 10000.70 | 10000.94 | 10007.6 | 100.00% | 3813 | 3000 | 28.64% | 745.5MiB / 2GiB |
| v4-rep3-jakarta-saturation | io-blocking-async-virtual-400rps | 04 | 400 | 204.6 | 9989.15 | 10000.45 | 10000.87 | 10012.9 | 100.00% | 3816 | 3000 | 35.97% | 929.5MiB / 2GiB |
| v4-rep3-jakarta-saturation | io-blocking-async-default-400rps | 04 | 400 | 200.6 | 9988.91 | 10001.05 | 10381.35 | 10821.9 | 100.00% | 3977 | 3000 | 29.40% | 1.011GiB / 2GiB |
| v4-rep3-jakarta-saturation | io-blocking-async-default-400rps | 04 | 400 | 204.6 | 9988.64 | 9994.26 | 10000.60 | 10005.3 | 100.00% | 3815 | 3000 | 35.12% | 1.067GiB / 2GiB |
| v4-rep3-jakarta-saturation | io-blocking-async-default-400rps | 04 | 400 | 201.9 | 9988.49 | 9992.23 | 10000.44 | 10016.1 | 100.00% | 3926 | 3000 | 368.38% | 1.122GiB / 2GiB |
| v4-rep5-dotnet10 | io-blocking | 03 | 50 | 32.0 | 9999.94 | 10000.71 | 10000.97 | 10001.4 | 84.61% | 351 | 451 | 0.91% | 141.8MiB / 2GiB |
| v4-rep5-dotnet10 | io-blocking | 03 | 50 | 49.0 | 604.41 | 605.91 | 606.70 | 623.6 | 0.00% | 0 | 100 | 13.63% | 167.9MiB / 2GiB |
| v4-rep5-dotnet10 | io-blocking | 03 | 50 | 49.0 | 604.51 | 606.20 | 606.95 | 615.7 | 0.00% | 0 | 100 | 14.40% | 167.9MiB / 2GiB |
| v4-rep5-dotnet10 | io-blocking | 03 | 50 | 49.0 | 604.49 | 606.12 | 607.04 | 652.4 | 0.00% | 0 | 100 | 12.97% | 174.1MiB / 2GiB |
| v4-rep5-dotnet10 | io-blocking | 03 | 50 | 49.0 | 604.39 | 605.82 | 606.42 | 607.4 | 0.00% | 0 | 100 | 12.23% | 173.8MiB / 2GiB |
| v4-rep5-dotnet10 | io-sequential-async | 03 | 50 | 49.0 | 604.16 | 606.00 | 607.48 | 617.1 | 0.00% | 0 | 100 | 15.13% | 171MiB / 2GiB |
| v4-rep5-dotnet10 | io-sequential-async | 03 | 50 | 49.0 | 604.17 | 606.00 | 607.48 | 610.6 | 0.00% | 0 | 100 | 11.63% | 169MiB / 2GiB |
| v4-rep5-dotnet10 | io-sequential-async | 03 | 50 | 49.0 | 604.12 | 605.66 | 606.34 | 608.2 | 0.00% | 0 | 100 | 9.39% | 171.9MiB / 2GiB |
| v4-rep5-dotnet10 | io-sequential-async | 03 | 50 | 49.0 | 604.05 | 605.53 | 606.52 | 613.4 | 0.00% | 0 | 100 | 10.29% | 171.6MiB / 2GiB |
| v4-rep5-dotnet10 | io-sequential-async | 03 | 50 | 49.0 | 604.14 | 605.54 | 606.07 | 607.5 | 0.00% | 0 | 100 | 12.52% | 173.3MiB / 2GiB |
| v4-rep5-dotnet10 | io-concurrent | 03 | 50 | 49.5 | 302.00 | 302.92 | 303.68 | 306.6 | 0.00% | 0 | 100 | 10.84% | 174.1MiB / 2GiB |
| v4-rep5-dotnet10 | io-concurrent | 03 | 50 | 49.5 | 302.10 | 303.08 | 303.81 | 304.5 | 0.00% | 0 | 100 | 8.99% | 174MiB / 2GiB |
| v4-rep5-dotnet10 | io-concurrent | 03 | 50 | 49.5 | 302.13 | 303.13 | 303.71 | 307.8 | 0.00% | 0 | 100 | 12.88% | 173.4MiB / 2GiB |
| v4-rep5-dotnet10 | io-concurrent | 03 | 50 | 49.5 | 302.01 | 302.86 | 303.25 | 307.4 | 0.00% | 0 | 100 | 8.63% | 174.7MiB / 2GiB |
| v4-rep5-dotnet10 | io-concurrent | 03 | 50 | 49.5 | 302.05 | 302.93 | 303.55 | 305.3 | 0.00% | 0 | 100 | 9.00% | 174.7MiB / 2GiB |
| v4-rep3-dotnet-saturation | io-blocking-400rps | 04 | 400 | 204.8 | 0.00 | 0.00 | 0.00 | 0.0 | 100.00% | 3809 | 3000 | 1.94% | 142.7MiB / 2GiB |
| v4-rep3-dotnet-saturation | io-blocking-400rps | 04 | 400 | 216.0 | 0.00 | 10000.47 | 10000.97 | 10012.8 | 83.79% | 3358 | 3000 | 2.80% | 232.6MiB / 2GiB |
| v4-rep3-dotnet-saturation | io-blocking-400rps | 04 | 400 | 392.1 | 604.56 | 606.61 | 619.19 | 655.7 | 0.00% | 0 | 400 | 139.12% | 278.3MiB / 2GiB |
| v4-dotnet11-saturation | io-sequential-async | 03 | 50 | 49.0 | 604.05 | 605.55 | 606.83 | 656.4 | 0.00% | 0 | 100 | 12.13% | 110.4MiB / 2GiB |
| v4-dotnet11-saturation | io-sequential-async | 03 | 50 | 49.0 | 603.84 | 605.29 | 605.97 | 607.8 | 0.00% | 0 | 100 | 10.81% | 131.4MiB / 2GiB |
| v4-dotnet11-saturation | io-sequential-async | 03 | 50 | 49.0 | 604.06 | 605.54 | 606.27 | 611.2 | 0.00% | 0 | 100 | 10.44% | 142MiB / 2GiB |
| v4-dotnet11-saturation | io-concurrent | 03 | 50 | 49.5 | 301.98 | 302.78 | 303.43 | 316.5 | 0.00% | 0 | 100 | 9.18% | 143.2MiB / 2GiB |
| v4-dotnet11-saturation | io-concurrent | 03 | 50 | 49.5 | 301.96 | 302.82 | 303.39 | 304.8 | 0.00% | 0 | 100 | 8.77% | 146.6MiB / 2GiB |
| v4-dotnet11-saturation | io-concurrent | 03 | 50 | 49.5 | 302.03 | 302.93 | 303.83 | 311.9 | 0.00% | 0 | 100 | 9.01% | 146.5MiB / 2GiB |
| v4-dotnet11-saturation | io-blocking-400rps | 04 | 400 | 204.8 | 0.00 | 10000.33 | 10000.74 | 10001.4 | 100.00% | 3810 | 3000 | 3.20% | 203.4MiB / 2GiB |
| v4-dotnet11-saturation | io-blocking-400rps | 04 | 400 | 263.1 | 605.41 | 10000.56 | 10001.09 | 10002.0 | 17.76% | 1478 | 1870 | 153.52% | 346.4MiB / 2GiB |
| v4-dotnet11-saturation | io-blocking-400rps | 04 | 400 | 392.1 | 604.50 | 609.60 | 625.81 | 650.7 | 0.00% | 0 | 400 | 95.62% | 401.2MiB / 2GiB |

## Repeatability — median [min – max] over repetitions

| Phase | Experiment | Lab | Target rps | n | Achieved rps | p50 ms | p99 ms | Dropped | Failed % |
|---|---|---|---:|---:|---|---|---|---|---|
| v4-rep5-spring-j17-platform | io-blocking-400rps | 04 | 400 | 5 | 324.2 [319.5 – 324.6] | 2434.41 [2410.64 – 2479.25] | 4018.58 [3981.93 – 4036.20] | 955 [943 – 1135] | 0.00 [0.00 – 0.00] |
| v4-rep5-jakarta | io-blocking | 03 | 50 | 5 | 49.0 [49.0 – 49.0] | 606.76 [605.79 – 607.62] | 611.00 [608.99 – 614.88] | 0 [0 – 0] | 0.00 [0.00 – 0.00] |
| v4-rep5-jakarta | io-sequential-async | 03 | 50 | 5 | 49.0 [49.0 – 49.0] | 605.82 [605.34 – 607.12] | 609.55 [608.28 – 734.56] | 0 [0 – 0] | 0.00 [0.00 – 0.00] |
| v4-rep5-jakarta | io-concurrent | 03 | 50 | 5 | 49.5 [49.5 – 49.5] | 303.03 [303.01 – 303.04] | 304.92 [304.42 – 305.28] | 0 [0 – 0] | 0.00 [0.00 – 0.00] |
| v4-rep3-jakarta-saturation | io-blocking-400rps | 04 | 400 | 3 | 213.2 [209.3 – 213.4] | 10000.01 [9999.94 – 10000.19] | 10001.14 [10001.07 – 10001.17] | 3474 [3465 – 3626] | 81.25 [81.24 – 89.35] |
| v4-rep3-jakarta-saturation | io-blocking-async-virtual-400rps | 04 | 400 | 3 | 204.7 [204.6 – 204.8] | 9990.38 [9989.15 – 9999.90] | 10000.94 [10000.87 – 10001.03] | 3813 [3808 – 3816] | 100.00 [100.00 – 100.00] |
| v4-rep3-jakarta-saturation | io-blocking-async-default-400rps | 04 | 400 | 3 | 201.9 [200.6 – 204.6] | 9988.64 [9988.49 – 9988.91] | 10000.60 [10000.44 – 10381.35] | 3926 [3815 – 3977] | 100.00 [100.00 – 100.00] |
| v4-rep5-dotnet10 | io-blocking | 03 | 50 | 5 | 49.0 [32.0 – 49.0] | 604.49 [604.39 – 9999.94] | 606.95 [606.42 – 10000.97] | 0 [0 – 351] | 0.00 [0.00 – 84.61] |
| v4-rep5-dotnet10 | io-sequential-async | 03 | 50 | 5 | 49.0 [49.0 – 49.0] | 604.14 [604.05 – 604.17] | 606.52 [606.07 – 607.48] | 0 [0 – 0] | 0.00 [0.00 – 0.00] |
| v4-rep5-dotnet10 | io-concurrent | 03 | 50 | 5 | 49.5 [49.5 – 49.5] | 302.05 [302.00 – 302.13] | 303.68 [303.25 – 303.81] | 0 [0 – 0] | 0.00 [0.00 – 0.00] |
| v4-rep3-dotnet-saturation | io-blocking-400rps | 04 | 400 | 3 | 216.0 [204.8 – 392.1] | 0.00 [0.00 – 604.56] | 619.19 [0.00 – 10000.97] | 3358 [0 – 3809] | 83.79 [0.00 – 100.00] |
| v4-dotnet11-saturation | io-sequential-async | 03 | 50 | 3 | 49.0 [49.0 – 49.0] | 604.05 [603.84 – 604.06] | 606.27 [605.97 – 606.83] | 0 [0 – 0] | 0.00 [0.00 – 0.00] |
| v4-dotnet11-saturation | io-concurrent | 03 | 50 | 3 | 49.5 [49.5 – 49.5] | 301.98 [301.96 – 302.03] | 303.43 [303.39 – 303.83] | 0 [0 – 0] | 0.00 [0.00 – 0.00] |
| v4-dotnet11-saturation | io-blocking-400rps | 04 | 400 | 3 | 263.1 [204.8 – 392.1] | 604.50 [0.00 – 605.41] | 10000.74 [625.81 – 10001.09] | 1478 [0 – 3810] | 17.76 [0.00 – 100.00] |

Raw k6 summaries (`*.json`), `probes.json` and `environment.json` are stored next to this report.
