# Optional observability

The baseline lab does not depend on monitoring. Start only the selected backend and optional services. Spring includes Actuator and a Prometheus registry. The provisioned Grafana dashboard uses Spring's request rate, p95 histogram, heap and live thread metrics; validate the exported names after startup.

```powershell
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d app mock-api otel-collector prometheus tempo grafana
```

Grafana: http://localhost:3000 (local admin / `local-grafana-password`), Prometheus: http://localhost:9090, Tempo: http://localhost:3200. These are loopback-only lab endpoints. Prometheus may show no data until the application starts and receives requests.

For Java tracing download the official OpenTelemetry Java agent JAR from https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases, select and record a compatible release and verify its published checksum. Save it as `observability/agent.jar` (not included). Then apply the optional overlay:

```powershell
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml -f docker-compose.otel-java.yml up -d --force-recreate app mock-api otel-collector prometheus tempo grafana
```

For Jakarta select `--profile jakarta` and `jakarta` instead of `app`. For .NET use `docker-compose.otel-dotnet.yml` and `--profile dotnet`. The SDK is configured conditionally using OTLP environment variables. Collector exports metrics to a scrape endpoint and traces to Tempo. No Loki/log shipping is configured. Dashboard data for Jakarta and .NET requires querying their actual emitted metric names; the Spring dashboard is not a universal cross-framework dashboard.

Check traces by making requests, then querying Tempo in Grafana Explore. Verify ingestion before making claims. No telemetry stack was run in the authoring environment.

For profiling use JFR (`jcmd <pid> JFR.start name=lab settings=profile duration=60s filename=lab.jfr`) on a JDK-equipped local runtime, `dotnet-counters monitor --process-id <pid>` or `dotnet-trace collect --process-id <pid>` on a local .NET process with the diagnostic tools installed. The runtime-only Docker images may not contain these tools. Record profiles separately from uninstrumented benchmark measurements.
