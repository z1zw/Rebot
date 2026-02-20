# Rebot Observability Stack

This stack provides:

- Prometheus scraping backend metrics from `GET /metrics`
- Grafana with pre-provisioned Prometheus datasource
- Preloaded dashboard: `Rebot Backend Observability`

## Start

```powershell
docker compose up -d backend prometheus grafana
```

## Endpoints

- Backend API: `http://localhost:8001`
- Backend Metrics: `http://localhost:8001/metrics`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3001` (admin/admin)

## What to watch first

- `HTTP RPS by Path`
- `HTTP P95 Latency (s)`
- `Operation Outcome Rate`
- `Operation P95 Duration (s)`

## Notes

- If `prometheus-client` is unavailable in the backend runtime, `/metrics` still responds, but metric families are limited.
- OpenTelemetry is optional; set `REBOT_OTEL_EXPORTER_OTLP_ENDPOINT` to enable OTLP export.
