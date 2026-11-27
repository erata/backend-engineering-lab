# HTTP benchmark report — measured local results

Indicative measurements of these lab implementations on one workstation. Not universal framework rankings.

- Run: `20261127T201204Z`  
- Host: v6 Redis outage repetitions and client settings, 20 logical CPUs, Windows-11-10.0.26300-SP0  
- Backend container quota: `cpus` per phase (default 4), `mem_limit` 2g. k6 grafana/k6:1.3.0 in a container on the Compose network.  
- Each k6 row: constant-arrival-rate, 10 s unreported warm-up, then the measured duration. Latency in ms. Container CPU/memory sampled once mid-run.

## Runtime identification

| Phase | /lab/threads/info |
|---|---|
| v6-outage-spring-queue | `{"virtual": false, "runtime": "25.0.5.1", "thread": "http-nio-0.0.0.0-8080-exec-3", "image": "backend-engineering-lab-full-app sha256:502bee3469a5cb91143ac9ea2f8e61b57479a94c1e2ea831b4c558c915b34f8a", "db_image": "mysql:8.4"}` |
| v6-outage-spring-reject | `{"thread": "http-nio-0.0.0.0-8080-exec-3", "runtime": "25.0.5.1", "virtual": false, "image": "backend-engineering-lab-full-app sha256:502bee3469a5cb91143ac9ea2f8e61b57479a94c1e2ea831b4c558c915b34f8a", "db_image": "mysql:8.4"}` |
| v6-outage-jakarta | `{"virtual": false, "runtime": "25.0.4.1", "thread": "default task-3", "image": "backend-engineering-lab-full-jakarta sha256:d6b5dfd9952188f5202fa76cb7df585fbe421e4e9a5808424f432e81f988949c", "db_image": "mysql:8.4"}` |
| v6-outage-jakarta-dns0 | `{"thread": "default task-2", "runtime": "25.0.4.1", "virtual": false, "image": "backend-engineering-lab-full-jakarta sha256:d6b5dfd9952188f5202fa76cb7df585fbe421e4e9a5808424f432e81f988949c", "db_image": "mysql:8.4"}` |
| v6-outage-dotnet-hb1000 | `{"runtime": "10.0.15", "processors": 4, "threadPool": 5, "image": "backend-engineering-lab-full-dotnet sha256:ffc2ad705922360b8dcb2b0eff6ffd12446b62dded5cbd71d43d68a441c940fc", "db_image": "mysql:8.4"}` |
| v6-outage-dotnet-hb500 | `{"runtime": "10.0.15", "processors": 4, "threadPool": 5, "image": "backend-engineering-lab-full-dotnet sha256:ffc2ad705922360b8dcb2b0eff6ffd12446b62dded5cbd71d43d68a441c940fc", "db_image": "mysql:8.4"}` |
| v6-outage-dotnet-hb100 | `{"runtime": "10.0.15", "processors": 4, "threadPool": 5, "image": "backend-engineering-lab-full-dotnet sha256:ffc2ad705922360b8dcb2b0eff6ffd12446b62dded5cbd71d43d68a441c940fc", "db_image": "mysql:8.4"}` |

## k6 results

| Phase | Experiment | Lab | Target rps | Achieved rps | p50 | p95 | p99 | max | Failed | Dropped | Max VUs | CPU | Memory |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|

Raw k6 summaries (`*.json`), `probes.json` and `environment.json` are stored next to this report.
