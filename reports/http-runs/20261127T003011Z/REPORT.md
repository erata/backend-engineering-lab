# HTTP benchmark report — measured local results

Indicative measurements of these lab implementations on one workstation. Not universal framework rankings.

- Run: `20261127T003011Z`  
- Host: 13th Gen Intel(R) Core(TM) i7-13700H, 20 logical CPUs, Windows-11-10.0.26300-SP0  
- Backend container quota: `cpus` per phase (default 4), `mem_limit` 2g. k6 grafana/k6:1.3.0 in a container on the Compose network.  
- Each k6 row: constant-arrival-rate, 10 s unreported warm-up, then the measured duration. Latency in ms. Container CPU/memory sampled once mid-run.

## Runtime identification

| Phase | /lab/threads/info |
|---|---|
| v2-rep5-spring-j25-platform | `{"virtual": false, "runtime": "25.0.5.1", "thread": "http-nio-0.0.0.0-8080-exec-3"}` |
| v2-rep5-spring-j25-virtual | `{"virtual": true, "runtime": "25.0.5.1", "thread": "tomcat-handler-2"}` |
| v2-rep5-spring-j17-platform | `{"thread": "http-nio-0.0.0.0-8080-exec-2", "virtual": false, "runtime": "17.0.21.1"}` |

## k6 results

| Phase | Experiment | Lab | Target rps | Achieved rps | p50 | p95 | p99 | max | Failed | Dropped | Max VUs | CPU | Memory |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| v2-rep5-spring-j25-platform | catalog-get | 01 | 2000 | 1999.9 | 0.65 | 1.46 | 5.16 | 57.0 | 0.00% | 0 | 200 | 102.70% | 407MiB / 2GiB |
| v2-rep5-spring-j25-platform | catalog-get | 01 | 2000 | 1999.9 | 0.49 | 1.01 | 2.00 | 35.1 | 0.00% | 0 | 200 | 74.80% | 406.8MiB / 2GiB |
| v2-rep5-spring-j25-platform | catalog-get | 01 | 2000 | 1999.7 | 0.48 | 0.92 | 1.52 | 10.4 | 0.00% | 0 | 200 | 76.10% | 407.9MiB / 2GiB |
| v2-rep5-spring-j25-platform | catalog-get | 01 | 2000 | 1974.2 | 0.62 | 18.42 | 104.93 | 599.6 | 0.00% | 771 | 258 | 99.73% | 408.8MiB / 2GiB |
| v2-rep5-spring-j25-platform | catalog-get | 01 | 2000 | 1999.9 | 0.79 | 2.97 | 13.18 | 74.0 | 0.00% | 0 | 200 | 148.00% | 407.6MiB / 2GiB |
| v2-rep5-spring-j25-platform | io-blocking | 03 | 50 | 49.0 | 606.94 | 610.30 | 611.73 | 630.5 | 0.00% | 0 | 100 | 31.28% | 425.1MiB / 2GiB |
| v2-rep5-spring-j25-platform | io-blocking | 03 | 50 | 49.0 | 605.24 | 609.02 | 610.77 | 616.2 | 0.00% | 0 | 100 | 62.13% | 431.6MiB / 2GiB |
| v2-rep5-spring-j25-platform | io-blocking | 03 | 50 | 49.0 | 605.24 | 610.38 | 612.44 | 661.2 | 0.00% | 0 | 100 | 38.99% | 431.1MiB / 2GiB |
| v2-rep5-spring-j25-platform | io-blocking | 03 | 50 | 49.0 | 605.34 | 610.21 | 622.07 | 680.2 | 0.00% | 0 | 100 | 23.20% | 430.9MiB / 2GiB |
| v2-rep5-spring-j25-platform | io-blocking | 03 | 50 | 49.0 | 605.04 | 609.22 | 611.73 | 637.9 | 0.00% | 0 | 100 | 22.73% | 431.2MiB / 2GiB |
| v2-rep5-spring-j25-platform | io-concurrent | 03 | 50 | 49.5 | 302.96 | 304.97 | 306.12 | 315.4 | 0.00% | 0 | 100 | 14.12% | 432.5MiB / 2GiB |
| v2-rep5-spring-j25-platform | io-concurrent | 03 | 50 | 49.5 | 303.37 | 305.31 | 306.50 | 328.0 | 0.00% | 0 | 100 | 27.02% | 432.3MiB / 2GiB |
| v2-rep5-spring-j25-platform | io-concurrent | 03 | 50 | 49.5 | 303.24 | 305.30 | 306.84 | 308.2 | 0.00% | 0 | 100 | 16.69% | 432.3MiB / 2GiB |
| v2-rep5-spring-j25-platform | io-concurrent | 03 | 50 | 49.5 | 303.06 | 304.82 | 306.55 | 320.8 | 0.00% | 0 | 100 | 18.88% | 432.5MiB / 2GiB |
| v2-rep5-spring-j25-platform | io-concurrent | 03 | 50 | 49.5 | 303.25 | 304.69 | 305.66 | 319.3 | 0.00% | 0 | 100 | 17.22% | 432.5MiB / 2GiB |
| v2-rep5-spring-j25-platform | events-direct | 07 | 200 | 109.0 | 4580.75 | 10001.28 | 10001.72 | 10005.9 | 15.85% | 1641 | 1000 | 31.13% | 468.3MiB / 2GiB |
| v2-rep5-spring-j25-platform | events-direct | 07 | 200 | 93.2 | 8658.18 | 10001.22 | 10001.52 | 10010.3 | 24.83% | 2271 | 1000 | 21.41% | 474.8MiB / 2GiB |
| v2-rep5-spring-j25-platform | events-direct | 07 | 200 | 129.8 | 1564.28 | 8844.82 | 8962.89 | 8999.9 | 0.00% | 1003 | 1000 | 31.75% | 471.2MiB / 2GiB |
| v2-rep5-spring-j25-platform | events-direct | 07 | 200 | 134.5 | 5655.95 | 6815.22 | 7000.88 | 7024.7 | 0.00% | 1269 | 1000 | 25.26% | 475.1MiB / 2GiB |
| v2-rep5-spring-j25-platform | events-direct | 07 | 200 | 143.3 | 5172.15 | 6050.87 | 6154.45 | 6969.6 | 0.00% | 1022 | 1000 | 19.60% | 474.7MiB / 2GiB |
| v2-rep5-spring-j25-platform | events-event | 07 | 200 | 200.0 | 3.20 | 5.95 | 11.53 | 62.5 | 0.00% | 0 | 100 | 59.05% | 472.6MiB / 2GiB |
| v2-rep5-spring-j25-platform | events-event | 07 | 200 | 200.0 | 2.73 | 5.01 | 7.86 | 28.3 | 0.00% | 0 | 100 | 48.06% | 473.4MiB / 2GiB |
| v2-rep5-spring-j25-platform | events-event | 07 | 200 | 200.0 | 2.97 | 4.93 | 8.03 | 51.2 | 0.00% | 0 | 100 | 60.94% | 473.4MiB / 2GiB |
| v2-rep5-spring-j25-platform | events-event | 07 | 200 | 200.0 | 2.45 | 4.56 | 6.03 | 23.0 | 0.00% | 0 | 100 | 57.64% | 473MiB / 2GiB |
| v2-rep5-spring-j25-platform | events-event | 07 | 200 | 200.0 | 1.95 | 3.72 | 4.91 | 21.8 | 0.00% | 0 | 100 | 33.68% | 473.1MiB / 2GiB |
| v2-rep5-spring-j25-platform | io-blocking-400rps | 04 | 400 | 312.5 | 2564.62 | 4072.46 | 4168.99 | 4230.4 | 0.00% | 1320 | 1347 | 146.66% | 491.3MiB / 2GiB |
| v2-rep5-spring-j25-platform | io-blocking-400rps | 04 | 400 | 316.0 | 2598.65 | 4143.74 | 4215.03 | 4299.8 | 0.00% | 1214 | 1389 | 116.00% | 497.2MiB / 2GiB |
| v2-rep5-spring-j25-platform | io-blocking-400rps | 04 | 400 | 322.9 | 2495.27 | 3942.26 | 4063.54 | 4122.2 | 0.00% | 1012 | 1365 | 77.03% | 516.6MiB / 2GiB |
| v2-rep5-spring-j25-platform | io-blocking-400rps | 04 | 400 | 319.9 | 2606.93 | 4046.66 | 4156.80 | 4216.4 | 0.00% | 1061 | 1396 | 123.49% | 515.9MiB / 2GiB |
| v2-rep5-spring-j25-platform | io-blocking-400rps | 04 | 400 | 322.1 | 2504.59 | 4024.57 | 4164.18 | 4227.3 | 0.00% | 992 | 1368 | 108.16% | 516.5MiB / 2GiB |
| v2-rep5-spring-j25-virtual | catalog-get | 01 | 2000 | 1999.9 | 0.62 | 1.40 | 6.29 | 65.3 | 0.00% | 0 | 200 | 91.21% | 349.2MiB / 2GiB |
| v2-rep5-spring-j25-virtual | catalog-get | 01 | 2000 | 1999.9 | 0.56 | 1.14 | 2.47 | 22.3 | 0.00% | 0 | 200 | 84.31% | 349.2MiB / 2GiB |
| v2-rep5-spring-j25-virtual | catalog-get | 01 | 2000 | 1999.9 | 0.55 | 1.14 | 2.89 | 35.7 | 0.00% | 0 | 200 | 92.66% | 349.5MiB / 2GiB |
| v2-rep5-spring-j25-virtual | catalog-get | 01 | 2000 | 1999.9 | 0.57 | 1.20 | 3.45 | 25.9 | 0.00% | 0 | 200 | 73.88% | 350.1MiB / 2GiB |
| v2-rep5-spring-j25-virtual | catalog-get | 01 | 2000 | 1999.9 | 0.57 | 1.07 | 1.68 | 15.4 | 0.00% | 0 | 200 | 80.83% | 349.8MiB / 2GiB |
| v2-rep5-spring-j25-virtual | io-blocking-400rps | 04 | 400 | 237.0 | 5004.69 | 7615.11 | 9242.48 | 10009.9 | 31.18% | 3647 | 1755 | 437.79% | 778.5MiB / 2GiB |
| v2-rep5-spring-j25-virtual | io-blocking-400rps | 04 | 400 | 212.1 | 5024.61 | 8267.97 | 9998.38 | 10014.0 | 32.70% | 4566 | 1790 | 141.41% | 799.5MiB / 2GiB |
| v2-rep5-spring-j25-virtual | io-blocking-400rps | 04 | 400 | 259.6 | 4408.99 | 6366.53 | 7949.16 | 10012.0 | 28.00% | 2919 | 1703 | 294.53% | 801.5MiB / 2GiB |
| v2-rep5-spring-j25-virtual | io-blocking-400rps | 04 | 400 | 278.1 | 3842.47 | 5871.49 | 7460.04 | 10000.8 | 24.57% | 2269 | 1668 | 203.64% | 801.1MiB / 2GiB |
| v2-rep5-spring-j25-virtual | io-blocking-400rps | 04 | 400 | 281.9 | 3496.69 | 5495.21 | 7050.62 | 9690.5 | 20.55% | 2166 | 1578 | 201.02% | 800.9MiB / 2GiB |
| v2-rep5-spring-j17-platform | catalog-get | 01 | 2000 | 1999.3 | 0.64 | 1.40 | 4.48 | 105.2 | 0.00% | 0 | 200 | 108.35% | 533.8MiB / 2GiB |
| v2-rep5-spring-j17-platform | catalog-get | 01 | 2000 | 2000.0 | 0.70 | 1.48 | 4.09 | 28.4 | 0.00% | 0 | 200 | 97.79% | 533.9MiB / 2GiB |
| v2-rep5-spring-j17-platform | catalog-get | 01 | 2000 | 1999.9 | 0.68 | 1.85 | 7.86 | 64.4 | 0.00% | 0 | 200 | 90.71% | 534MiB / 2GiB |
| v2-rep5-spring-j17-platform | catalog-get | 01 | 2000 | 2000.0 | 0.55 | 1.18 | 4.12 | 82.5 | 0.00% | 0 | 200 | 66.73% | 534.6MiB / 2GiB |
| v2-rep5-spring-j17-platform | catalog-get | 01 | 2000 | 1999.9 | 0.51 | 0.94 | 1.37 | 5.7 | 0.00% | 0 | 200 | 61.29% | 533.4MiB / 2GiB |
| v2-rep5-spring-j17-platform | io-blocking-400rps | 04 | 400 | 314.7 | 2847.45 | 4271.95 | 4397.31 | 4471.4 | 0.00% | 1186 | 1472 | 170.50% | 641.8MiB / 2GiB |
| v2-rep5-spring-j17-platform | io-blocking-400rps | 04 | 400 | 324.2 | 2460.46 | 3875.16 | 4017.53 | 4075.4 | 0.00% | 955 | 1344 | 146.50% | 652MiB / 2GiB |
| v2-rep5-spring-j17-platform | io-blocking-400rps | 04 | 400 | 323.5 | 2483.05 | 3911.47 | 4039.76 | 4074.4 | 0.00% | 978 | 1352 | 117.41% | 694MiB / 2GiB |
| v2-rep5-spring-j17-platform | io-blocking-400rps | 04 | 400 | 323.1 | 2493.42 | 3938.82 | 4055.14 | 4102.1 | 0.00% | 985 | 1351 | 124.50% | 694MiB / 2GiB |
| v2-rep5-spring-j17-platform | io-blocking-400rps | 04 | 400 | 323.1 | 2456.16 | 3953.53 | 4088.42 | 4121.4 | 0.00% | 989 | 1365 | 135.29% | 693.8MiB / 2GiB |

## Repeatability — median [min – max] over repetitions

| Phase | Experiment | Lab | Target rps | n | Achieved rps | p50 ms | p99 ms | Dropped | Failed % |
|---|---|---|---:|---:|---|---|---|---|---|
| v2-rep5-spring-j25-platform | catalog-get | 01 | 2000 | 5 | 1999.9 [1974.2 – 1999.9] | 0.62 [0.48 – 0.79] | 5.16 [1.52 – 104.93] | 0 [0 – 771] | 0.00 [0.00 – 0.00] |
| v2-rep5-spring-j25-platform | io-blocking | 03 | 50 | 5 | 49.0 [49.0 – 49.0] | 605.24 [605.04 – 606.94] | 611.73 [610.77 – 622.07] | 0 [0 – 0] | 0.00 [0.00 – 0.00] |
| v2-rep5-spring-j25-platform | io-concurrent | 03 | 50 | 5 | 49.5 [49.5 – 49.5] | 303.24 [302.96 – 303.37] | 306.50 [305.66 – 306.84] | 0 [0 – 0] | 0.00 [0.00 – 0.00] |
| v2-rep5-spring-j25-platform | events-direct | 07 | 200 | 5 | 129.8 [93.2 – 143.3] | 5172.15 [1564.28 – 8658.18] | 8962.89 [6154.45 – 10001.72] | 1269 [1003 – 2271] | 0.00 [0.00 – 24.83] |
| v2-rep5-spring-j25-platform | events-event | 07 | 200 | 5 | 200.0 [200.0 – 200.0] | 2.73 [1.95 – 3.20] | 7.86 [4.91 – 11.53] | 0 [0 – 0] | 0.00 [0.00 – 0.00] |
| v2-rep5-spring-j25-platform | io-blocking-400rps | 04 | 400 | 5 | 319.9 [312.5 – 322.9] | 2564.62 [2495.27 – 2606.93] | 4164.18 [4063.54 – 4215.03] | 1061 [992 – 1320] | 0.00 [0.00 – 0.00] |
| v2-rep5-spring-j25-virtual | catalog-get | 01 | 2000 | 5 | 1999.9 [1999.9 – 1999.9] | 0.57 [0.55 – 0.62] | 2.89 [1.68 – 6.29] | 0 [0 – 0] | 0.00 [0.00 – 0.00] |
| v2-rep5-spring-j25-virtual | io-blocking-400rps | 04 | 400 | 5 | 259.6 [212.1 – 281.9] | 4408.99 [3496.69 – 5024.61] | 7949.16 [7050.62 – 9998.38] | 2919 [2166 – 4566] | 28.00 [20.55 – 32.70] |
| v2-rep5-spring-j17-platform | catalog-get | 01 | 2000 | 5 | 1999.9 [1999.3 – 2000.0] | 0.64 [0.51 – 0.70] | 4.12 [1.37 – 7.86] | 0 [0 – 0] | 0.00 [0.00 – 0.00] |
| v2-rep5-spring-j17-platform | io-blocking-400rps | 04 | 400 | 5 | 323.1 [314.7 – 324.2] | 2483.05 [2456.16 – 2847.45] | 4055.14 [4017.53 – 4397.31] | 985 [955 – 1186] | 0.00 [0.00 – 0.00] |

Raw k6 summaries (`*.json`), `probes.json` and `environment.json` are stored next to this report.
