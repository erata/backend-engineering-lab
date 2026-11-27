# HTTP benchmark report — measured local results

Indicative measurements of these lab implementations on one workstation. Not universal framework rankings.

- Run: `20261127T231118Z`  
- Host: v7 Redis regression checks, 20 logical CPUs, Windows-11-10.0.26300-SP0  
- Backend container quota: `cpus` per phase (default 4), `mem_limit` 2g. k6 grafana/k6:1.3.0 in a container on the Compose network.  
- Each k6 row: constant-arrival-rate, 10 s unreported warm-up, then the measured duration. Latency in ms. Container CPU/memory sampled once mid-run.

## Runtime identification

| Phase | /lab/threads/info |
|---|---|
| v7-redis-regression-spring | `{"thread": "http-nio-0.0.0.0-8080-exec-2", "runtime": "25.0.5.1", "virtual": false, "image": "backend-engineering-lab-full-app sha256:b92134fc3b607915e5c0103aa2ecc3e485ebaccacf14250614ba8cf8da25361b", "db_image": "mysql:8.4"}` |
| v7-redis-regression-jakarta | `{"runtime": "25.0.5.1", "virtual": false, "thread": "default task-3", "image": "backend-engineering-lab-full-jakarta sha256:b5c46df933bac90407f4d488bcba1e35f9784e1f0e5767e3cbc3bc53a786562c", "db_image": "mysql:8.4"}` |
| v7-redis-regression-dotnet10 | `{"runtime": "10.0.15", "processors": 4, "threadPool": 5, "image": "backend-engineering-lab-full-dotnet sha256:ea8f01650d0cb5ac27c7af2b735d634c5e806e04acb9ac45224755a1d6c4f27a", "db_image": "mysql:8.4"}` |

## k6 results

| Phase | Experiment | Lab | Target rps | Achieved rps | p50 | p95 | p99 | max | Failed | Dropped | Max VUs | CPU | Memory |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|

Raw k6 summaries (`*.json`), `probes.json` and `environment.json` are stored next to this report.
