# HTTP benchmark report — measured local results

Indicative measurements of these lab implementations on one workstation. Not universal framework rankings.

- Run: `20261127T203811Z`  
- Host: v6b JVM DNS cache A/B via security properties, 20 logical CPUs, Windows-11-10.0.26300-SP0  
- Backend container quota: `cpus` per phase (default 4), `mem_limit` 2g. k6 grafana/k6:1.3.0 in a container on the Compose network.  
- Each k6 row: constant-arrival-rate, 10 s unreported warm-up, then the measured duration. Latency in ms. Container CPU/memory sampled once mid-run.

## Runtime identification

| Phase | /lab/threads/info |
|---|---|
| v6b-outage-jakarta-neg0 | `{"runtime": "25.0.4.1", "thread": "default task-3", "virtual": false, "image": "backend-engineering-lab-full-jakarta sha256:0fe9c71b36e2d542748b49477f95b8ffd3b7eadf07d69ba69e39a9459a855367", "db_image": "mysql:8.4"}` |
| v6b-outage-jakarta-nocache | `{"virtual": false, "runtime": "25.0.4.1", "thread": "default task-3", "image": "backend-engineering-lab-full-jakarta sha256:0fe9c71b36e2d542748b49477f95b8ffd3b7eadf07d69ba69e39a9459a855367", "db_image": "mysql:8.4"}` |

## k6 results

| Phase | Experiment | Lab | Target rps | Achieved rps | p50 | p95 | p99 | max | Failed | Dropped | Max VUs | CPU | Memory |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|

Raw k6 summaries (`*.json`), `probes.json` and `environment.json` are stored next to this report.
