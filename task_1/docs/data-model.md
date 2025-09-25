# Data Models and Schemas

## Overview

This document defines the comprehensive data models, Prometheus metrics, and schemas used in the Kubernetes proxy monitoring solution. It covers metric definitions, data attribution, storage schemas, and query patterns.

## Prometheus Metrics Schema

### Core Proxy Metrics

#### Request Metrics
```prometheus
# Total HTTP requests by proxy vendor
istio_requests_total{
    source_app="crawler|load-generator",
    proxy_vendor="vendor-a|vendor-b|vendor-c",
    destination_service_name="external|httpbin-org|github-api|...",
    destination_host="httpbin.org|api.github.com|...",
    response_code="200|201|400|404|500|...",
    request_protocol="http|grpc",
    protocol_version="HTTP/1.1|HTTP/2.0",
    method="GET|POST|PUT|DELETE"
}

# Request duration histogram
istio_request_duration_milliseconds{
    source_app="crawler|load-generator",
    proxy_vendor="vendor-a|vendor-b|vendor-c", 
    destination_service_name="external|httpbin-org|...",
    method="GET|POST|PUT|DELETE",
    le="0.5|1|2.5|5|10|25|50|100|250|500|1000|2500|5000|10000|+Inf"
}

# Request size histogram 
istio_request_bytes{
    source_app="crawler|load-generator",
    proxy_vendor="vendor-a|vendor-b|vendor-c",
    destination_service_name="external|...",
    le="100|500|1000|5000|10000|50000|100000|500000|1000000|+Inf"
}

# Response size histogram
istio_response_bytes{
    source_app="crawler|load-generator", 
    proxy_vendor="vendor-a|vendor-b|vendor-c",
    destination_service_name="external|...",
    le="100|500|1000|5000|10000|50000|100000|500000|1000000|+Inf"
}
```

#### Bandwidth Metrics
```prometheus
# Total bytes sent (request payloads)
istio_request_bytes_sum{
    source_app="crawler|load-generator",
    proxy_vendor="vendor-a|vendor-b|vendor-c",
    destination_service_name="external|...",
    destination_host="httpbin.org|..."
}

# Total bytes received (response payloads)
istio_response_bytes_sum{
    source_app="crawler|load-generator",
    proxy_vendor="vendor-a|vendor-b|vendor-c", 
    destination_service_name="external|...",
    destination_host="httpbin.org|..."
}
```

#### TCP Connection Metrics
```prometheus
# TCP connections opened
istio_tcp_opened_total{
    source_app="crawler|load-generator",
    proxy_vendor="vendor-a|vendor-b|vendor-c",
    destination_service_name="external|...",
    connection_security_policy="mutual_tls|tls|plaintext"
}

# TCP connections closed
istio_tcp_closed_total{
    source_app="crawler|load-generator", 
    proxy_vendor="vendor-a|vendor-b|vendor-c",
    destination_service_name="external|..."
}
```

### Custom Load Generator Metrics

#### Application-Level Metrics
```prometheus
# Load generator specific request counter
load_generator_requests_total{
    vendor="vendor-a|vendor-b|vendor-c",
    method="GET|POST|PUT|DELETE",
    status_code="200|201|400|404|500|error",
    destination_host="httpbin.org|api.github.com|..."
}

# Request duration from application perspective
load_generator_request_duration_seconds{
    vendor="vendor-a|vendor-b|vendor-c",
    method="GET|POST|PUT|DELETE", 
    destination_host="httpbin.org|..."
}

# Bandwidth tracking from application
load_generator_bytes_sent_total{
    vendor="vendor-a|vendor-b|vendor-c",
    destination_host="httpbin.org|..."
}

load_generator_bytes_received_total{
    vendor="vendor-a|vendor-b|vendor-c",
    destination_host="httpbin.org|..."  
}
```

#### Connection Pool Metrics
```prometheus
# Active connections per vendor
load_generator_active_connections{
    vendor="vendor-a|vendor-b|vendor-c"
}

# Error rate by vendor (percentage)
load_generator_error_rate{
    vendor="vendor-a|vendor-b|vendor-c"
}

# Proxy pool health status
proxy_pool_health{
    vendor="vendor-a|vendor-b|vendor-c",
    pool="datacenter-us-east|residential-us|mobile-us|..."
}
```

#### System Resource Metrics
```prometheus
# CPU usage of load generator
load_generator_cpu_usage_percent

# Memory usage of load generator  
load_generator_memory_usage_bytes

# Network I/O rates
load_generator_network_bytes_received_per_second
load_generator_network_bytes_sent_per_second
```

### Infrastructure Metrics

#### Kubernetes Pod Metrics
```prometheus
# Container CPU usage
container_cpu_usage_seconds_total{
    pod=~"prometheus-.*|grafana-.*|load-generator-.*",
    namespace="proxy-monitoring",
    container="prometheus|grafana|load-generator"
}

# Container memory usage
container_memory_working_set_bytes{
    pod=~"prometheus-.*|grafana-.*|load-generator-.*",
    namespace="proxy-monitoring",
    container="prometheus|grafana|load-generator"
}

# Container network I/O
container_network_receive_bytes_total{
    pod=~"prometheus-.*|grafana-.*|load-generator-.*",
    namespace="proxy-monitoring"
}

container_network_transmit_bytes_total{
    pod=~"prometheus-.*|grafana-.*|load-generator-.*", 
    namespace="proxy-monitoring"
}
```

#### Kubernetes API Metrics
```prometheus
# API server request rate
apiserver_request_total{
    verb="GET|POST|PUT|DELETE|PATCH",
    resource="pods|services|endpoints|configmaps|secrets"
}

# API server request duration
apiserver_request_duration_seconds{
    verb="GET|POST|PUT|DELETE|PATCH",
    resource="pods|services|endpoints|..."
}
```

## Recording Rules

### Aggregated Metrics for Performance

#### Request Rate Rules
```yaml
# 5-minute request rate by vendor
- record: proxy:request_rate_5m
  expr: sum(rate(istio_requests_total{source_app=~"crawler|load-generator"}[5m])) by (proxy_vendor, destination_service_name, source_app)

# 1-hour request rate by vendor
- record: proxy:request_rate_1h  
  expr: sum(rate(istio_requests_total{source_app=~"crawler|load-generator"}[1h])) by (proxy_vendor, destination_service_name, source_app)

# Daily request rate by vendor
- record: proxy:request_rate_24h
  expr: sum(rate(istio_requests_total{source_app=~"crawler|load-generator"}[24h])) by (proxy_vendor, destination_service_name, source_app)
```

#### Error Rate Rules
```yaml
# 5-minute error rate by vendor (4xx + 5xx errors)
- record: proxy:error_rate_5m
  expr: |
    sum(rate(istio_requests_total{source_app=~"crawler|load-generator", response_code=~"[45].."}[5m])) by (proxy_vendor, source_app) /
    sum(rate(istio_requests_total{source_app=~"crawler|load-generator"}[5m])) by (proxy_vendor, source_app)

# 5-minute client error rate (4xx only)  
- record: proxy:client_error_rate_5m
  expr: |
    sum(rate(istio_requests_total{source_app=~"crawler|load-generator", response_code=~"4.."}[5m])) by (proxy_vendor, source_app) /
    sum(rate(istio_requests_total{source_app=~"crawler|load-generator"}[5m])) by (proxy_vendor, source_app)

# 5-minute server error rate (5xx only)
- record: proxy:server_error_rate_5m  
  expr: |
    sum(rate(istio_requests_total{source_app=~"crawler|load-generator", response_code=~"5.."}[5m])) by (proxy_vendor, source_app) /
    sum(rate(istio_requests_total{source_app=~"crawler|load-generator"}[5m])) by (proxy_vendor, source_app)
```

#### Latency Rules
```yaml
# P50, P95, P99 latency by vendor
- record: proxy:p50_latency_5m
  expr: |
    histogram_quantile(0.50, 
      sum(rate(istio_request_duration_milliseconds_bucket{source_app=~"crawler|load-generator"}[5m])) by (proxy_vendor, source_app, le)
    )

- record: proxy:p95_latency_5m
  expr: |
    histogram_quantile(0.95, 
      sum(rate(istio_request_duration_milliseconds_bucket{source_app=~"crawler|load-generator"}[5m])) by (proxy_vendor, source_app, le)
    )

- record: proxy:p99_latency_5m
  expr: |
    histogram_quantile(0.99, 
      sum(rate(istio_request_duration_milliseconds_bucket{source_app=~"crawler|load-generator"}[5m])) by (proxy_vendor, source_app, le)
    )
```

#### Bandwidth Rules
```yaml
# Total bandwidth (ingress + egress) by vendor
- record: proxy:bandwidth_total_rate_5m
  expr: |
    sum(rate(istio_request_bytes_sum{source_app=~"crawler|load-generator"}[5m])) by (proxy_vendor, source_app) +
    sum(rate(istio_response_bytes_sum{source_app=~"crawler|load-generator"}[5m])) by (proxy_vendor, source_app)

# Request bandwidth by vendor  
- record: proxy:request_bandwidth_rate_5m
  expr: sum(rate(istio_request_bytes_sum{source_app=~"crawler|load-generator"}[5m])) by (proxy_vendor, source_app)

# Response bandwidth by vendor
- record: proxy:response_bandwidth_rate_5m
  expr: sum(rate(istio_response_bytes_sum{source_app=~"crawler|load-generator"}[5m])) by (proxy_vendor, source_app)

# Bandwidth by destination
- record: proxy:bandwidth_by_destination_5m
  expr: |
    sum(rate(istio_request_bytes_sum{source_app=~"crawler|load-generator"}[5m]) +
        rate(istio_response_bytes_sum{source_app=~"crawler|load-generator"}[5m])) by (destination_service_name, proxy_vendor)
```

#### Success Rate Rules
```yaml
# Overall success rate by vendor (2xx responses)
- record: proxy:success_rate_5m
  expr: |
    sum(rate(istio_requests_total{source_app=~"crawler|load-generator", response_code=~"2.."}[5m])) by (proxy_vendor, source_app) /
    sum(rate(istio_requests_total{source_app=~"crawler|load-generator"}[5m])) by (proxy_vendor, source_app)

# Success rate by destination and vendor
- record: proxy:success_rate_by_destination_5m
  expr: |
    sum(rate(istio_requests_total{source_app=~"crawler|load-generator", response_code=~"2.."}[5m])) by (proxy_vendor, destination_service_name) /
    sum(rate(istio_requests_total{source_app=~"crawler|load-generator"}[5m])) by (proxy_vendor, destination_service_name)
```

## Vendor Attribution Model

### Header-Based Attribution
Proxy vendor identification is achieved through custom HTTP headers injected by the load generator:

```http
X-Proxy-Vendor: vendor-a|vendor-b|vendor-c
X-Proxy-Pool: datacenter-us-east|residential-us|mobile-us|...
X-Request-ID: unique-request-identifier
X-Client-ID: crawler-client-001
User-Agent: Crawler-vendor-a-1234
```

### Istio Telemetry Attribution
Istio's telemetry configuration extracts vendor information:

```yaml
# Telemetry configuration for vendor attribution
tagOverrides:
  proxy_vendor:
    value: |
      has(request.headers['x-proxy-vendor']) ? request.headers['x-proxy-vendor'] : (
        has(request.headers['user-agent']) && (request.headers['user-agent'] | contains('vendor-a')) ? 'vendor-a' :
        has(request.headers['user-agent']) && (request.headers['user-agent'] | contains('vendor-b')) ? 'vendor-b' :
        has(request.headers['user-agent']) && (request.headers['user-agent'] | contains('vendor-c')) ? 'vendor-c' :
        'unknown'
      )
```

## Data Storage Schema

### Prometheus Storage Configuration

#### Retention Policy
- **Short-term**: 7 days at 15-second resolution (raw metrics)
- **Medium-term**: 30 days at 1-minute resolution (aggregated)  
- **Long-term**: 365 days at 1-hour resolution (summary metrics)

#### Cardinality Management
```yaml
# Metric relabeling to control cardinality
metric_relabel_configs:
- source_labels: [__name__]
  action: keep
  regex: 'istio_requests_total|istio_request_duration_milliseconds.*|istio_request_bytes.*|istio_response_bytes.*|load_generator_.*'

# Limit high-cardinality labels
- source_labels: [destination_host]
  action: replace
  target_label: destination_host_simplified
  regex: '^([^.]+\.[^.]+).*'
  replacement: '${1}'
```

#### Storage Resources
```yaml
# Production storage configuration
storage:
  retention: "30d"
  retention.size: "100GB"
  tsdb.min-block-duration: "2h"
  tsdb.max-block-duration: "24h"
  tsdb.retention.time: "30d"
  tsdb.retention.size: "100GB"
  tsdb.wal-compression: true
```

## Query Patterns

### Common Queries for Dashboards

#### Request Rate Analysis
```promql
# Current request rate by vendor
sum(rate(istio_requests_total{source_app="crawler"}[5m])) by (proxy_vendor)

# Request rate comparison over time
sum(rate(istio_requests_total{source_app="crawler"}[5m])) by (proxy_vendor) / 
sum(rate(istio_requests_total{source_app="crawler"}[5m]))

# Top destinations by request volume
topk(10, 
  sum(rate(istio_requests_total{source_app="crawler"}[5m])) by (destination_service_name)
)
```

#### Error Analysis  
```promql
# Error rate by vendor and error type
sum(rate(istio_requests_total{source_app="crawler", response_code=~"[45].."}[5m])) by (proxy_vendor, response_code) /
sum(rate(istio_requests_total{source_app="crawler"}[5m])) by (proxy_vendor) * 100

# Error trend over time
increase(istio_requests_total{source_app="crawler", response_code=~"[45].."}[1h]) by (proxy_vendor, response_code)

# Most problematic destinations
topk(5,
  sum(rate(istio_requests_total{source_app="crawler", response_code=~"[45].."}[5m])) by (destination_service_name)
)
```

#### Performance Analysis
```promql  
# Latency comparison by vendor
histogram_quantile(0.95, 
  sum(rate(istio_request_duration_milliseconds_bucket{source_app="crawler"}[5m])) by (proxy_vendor, le)
)

# Latency heatmap over time
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{source_app="crawler"}[5m])) by (proxy_vendor, le)
) by (proxy_vendor)

# Slowest requests by destination
topk(5,
  histogram_quantile(0.95,
    sum(rate(istio_request_duration_milliseconds_bucket{source_app="crawler"}[5m])) by (destination_service_name, le)
  )
)
```

#### Bandwidth Analysis
```promql
# Bandwidth usage by vendor (bytes/sec)
sum(rate(istio_request_bytes_sum{source_app="crawler"}[5m]) + 
    rate(istio_response_bytes_sum{source_app="crawler"}[5m])) by (proxy_vendor)

# Bandwidth distribution by destination
sum(rate(istio_request_bytes_sum{source_app="crawler"}[5m]) + 
    rate(istio_response_bytes_sum{source_app="crawler"}[5m])) by (destination_service_name, proxy_vendor)

# Total bandwidth over time period
increase(istio_request_bytes_sum{source_app="crawler"}[1h] + 
         istio_response_bytes_sum{source_app="crawler"}[1h]) by (proxy_vendor)
```

## Data Export Formats

### JSON Schema for External Systems
```json
{
  "timestamp": "2023-12-01T12:00:00Z",
  "vendor": "vendor-a",
  "metrics": {
    "requests_per_second": 150.5,
    "error_rate_percent": 2.1,
    "p95_latency_ms": 450.2,
    "bandwidth_bytes_per_second": 1048576,
    "success_rate_percent": 97.9
  },
  "destinations": [
    {
      "host": "httpbin.org", 
      "requests_per_second": 45.2,
      "error_rate_percent": 1.8,
      "avg_latency_ms": 320.5
    }
  ],
  "pools": [
    {
      "name": "datacenter-us-east",
      "health_status": "healthy",
      "utilization_percent": 78.5,
      "active_connections": 42
    }
  ]
}
```

### CSV Export Format
```csv
timestamp,vendor,pool,destination_host,requests_total,errors_total,latency_p95_ms,bandwidth_bytes
2023-12-01T12:00:00Z,vendor-a,datacenter-us-east,httpbin.org,1500,30,450.2,10485760
2023-12-01T12:00:00Z,vendor-b,residential-us,httpbin.org,800,25,680.1,7340032
2023-12-01T12:00:00Z,vendor-c,mobile-us,httpbin.org,400,15,1200.5,4194304
```

## Security and Compliance

### Data Anonymization
- Remove or hash sensitive request parameters
- Anonymize IP addresses in logs
- Strip authentication tokens from metrics
- Redact personally identifiable information

### Access Control  
- Metrics accessible only to monitoring namespace service accounts
- RBAC restrictions on metric queries
- Audit logging for data access
- Encryption in transit and at rest

### Data Retention Compliance
- Automatic deletion after retention period
- Backup procedures for compliance requirements  
- Data export capabilities for auditing
- Privacy-compliant data handling procedures

This data model provides comprehensive coverage of proxy monitoring requirements while maintaining performance, security, and operational excellence standards.