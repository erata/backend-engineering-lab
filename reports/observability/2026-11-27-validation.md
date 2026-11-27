# Observability validation (2026-11-27)

Run after all performance benchmarks, so instrumentation could not influence them. Stack: `docker-compose.monitoring.yml` (OTel Collector contrib 0.133.0, Prometheus v3.5.0, Tempo 2.8.2, Grafana 12.1.1) plus `docker-compose.otel-java.yml` (OpenTelemetry Java agent **2.34.0**, SHA-256 `DA44154CEA128257779C8A782B9651FD7C0C6AA177CD3810F9A867AC8509555D`, downloaded from the official GitHub release, not committed) and `docker-compose.otel-dotnet.yml` (OpenTelemetry .NET SDK 1.12.0, OTLP/gRPC).

Load: 200 (Spring) / 100 (Jakarta, .NET) catalogue reads plus 10 / 5 `GET /lab/io/concurrent` calls (3 upstream HTTP calls each). Checks were made through the HTTP APIs (Prometheus `/api/v1`, Grafana `/api`, Tempo through the Grafana datasource proxy), not by looking at the UI.

## Metrics

| Check | Result |
|---|---|
| Prometheus targets `spring` (Actuator `/actuator/prometheus`) and `collector` (OTLP → Prometheus exporter :9464) | both `up`, no scrape errors |
| Micrometer `sum(http_server_requests_seconds_count{job="spring"})` | 216 |
| OTel `http_server_request_duration_seconds_count` via collector | spring 223, jakarta 108, dotnet 106 |
| OTel `http_client_request_duration_seconds_count` (upstream calls) | spring 30 (= 10 × 3), jakarta 15 (= 5 × 3), dotnet 17 |
| metric series per service in Prometheus | spring 184, dotnet 165, jakarta 106 |
| first collector metrics visible after start | ≈ 20–35 s (export interval 60 s by default; first export earlier) |

## Traces (Tempo)

| Service | Search result | Example trace |
|---|---|---|
| backendlab-spring | 50 traces (search limit), roots `GET /api/products/{id}`, `GET /lab/io/{mode}` | `/lab/io` trace with server span + client `GET` spans |
| backendlab-jakarta | 50 traces | `/lab/io/{mode}`: 4 spans (server + 3 client calls) |
| backendlab-dotnet | TraceQL `{ resource.service.name = "backendlab-dotnet" && span.http.route = "/lab/io/{mode}" }` → 5 traces | 4 spans: `GET /lab/io/{mode}`, `GET` × 3 |

## Grafana

- `/api/health`: database `ok`.
- Provisioned datasources: Prometheus (`uid=prometheus`), Tempo (`uid=tempo`).
- Provisioned dashboard "Backend Lab — Spring baseline" (`uid=backend-lab`): each of its 4 panel queries (request rate, p95 latency, JVM heap, live threads) returned 1 series from Prometheus.

## Limitations

- The provisioned dashboard covers Spring (Micrometer metric names) only. Jakarta and .NET data is in Prometheus/Tempo and visible in Grafana Explore, but has no dedicated dashboard.
- The .NET client count (17) is slightly above 5 × 3 = 15; the extra calls were not attributed.
- No log pipeline (Loki) is configured.
- Benchmarks in the report were run **without** instrumentation; the overhead of the agent was not measured.
