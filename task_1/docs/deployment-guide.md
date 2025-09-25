# Deployment Guide

This guide provides step-by-step instructions for deploying the proxy monitoring solution in a production Kubernetes environment.

## Prerequisites

### Infrastructure Requirements

- **Kubernetes Cluster**: Version 1.24 or higher
- **Helm**: Version 3.10 or higher
- **Istio Service Mesh**: Version 1.18 or higher
- **Storage Class**: Dynamic provisioning enabled
- **LoadBalancer**: External load balancer for ingress

### Resource Requirements

- **Minimum Cluster Size**: 3 nodes with 4 CPU cores and 8GB RAM each
- **Storage**: 100GB+ persistent storage for metrics retention
- **Network**: Cluster networking with support for NetworkPolicies

### Access Requirements

- Cluster admin privileges for initial setup
- Container registry access for custom images
- DNS management for external access

## Pre-Deployment Setup

### 1. Namespace Preparation

```bash
kubectl create namespace proxy-monitor
kubectl label namespace proxy-monitor istio-injection=enabled
```

### 2. Storage Configuration

```bash
# Verify storage class is available
kubectl get storageclass

# Create PVC for Prometheus if using standalone manifests
kubectl apply -f manifests/prometheus-pvc.yaml
```

### 3. Secret Management

```bash
# Create secrets for sensitive data
kubectl create secret generic monitoring-secrets \
  --from-literal=admin-password='secure-password' \
  --namespace proxy-monitor

# Create TLS certificates (if using custom certificates)
kubectl create secret tls monitoring-tls \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key \
  --namespace proxy-monitor
```

## Deployment Options

### Option 1: Helm Chart Deployment (Recommended)

#### Install from Local Chart

```bash
# Navigate to project directory
cd task_1/

# Install the monitoring stack
helm install proxy-monitor ./helm-chart/proxy-monitor \
  --namespace proxy-monitor \
  --create-namespace \
  --values helm-chart/proxy-monitor/values.yaml
```

#### Configuration Customization

Create a custom values file for your environment:

```yaml
# custom-values.yaml
prometheus:
  retention: "30d"
  storage:
    size: "200Gi"
  resources:
    requests:
      memory: "2Gi"
      cpu: "1000m"
    limits:
      memory: "4Gi"
      cpu: "2000m"

grafana:
  persistence:
    enabled: true
    size: "10Gi"
  ingress:
    enabled: true
    hosts:
      - grafana.yourcompany.com

istio:
  enabled: true
  gateway:
    hosts:
      - monitoring.yourcompany.com
```

Install with custom values:

```bash
helm install proxy-monitor ./helm-chart/proxy-monitor \
  --namespace proxy-monitor \
  --create-namespace \
  --values custom-values.yaml
```

#### Upgrade Deployment

```bash
# Upgrade with new configuration
helm upgrade proxy-monitor ./helm-chart/proxy-monitor \
  --namespace proxy-monitor \
  --values custom-values.yaml

# Check upgrade status
helm status proxy-monitor --namespace proxy-monitor
```

### Option 2: Standalone Manifests

#### Deploy Core Components

```bash
# Deploy in order
kubectl apply -f manifests/namespace.yaml
kubectl apply -f manifests/prometheus-config.yaml
kubectl apply -f manifests/grafana-config.yaml
kubectl apply -f manifests/istio-gateway.yaml
kubectl apply -f manifests/network-policy.yaml
```

#### Verify Deployment

```bash
# Check pod status
kubectl get pods -n proxy-monitor

# Check services
kubectl get svc -n proxy-monitor

# Check ingress
kubectl get gateway -n proxy-monitor
```

## Load Generator Deployment

### Deploy Load Generator

```bash
# Deploy load generator application
kubectl apply -f load-generator/k8s-manifests/

# Verify deployment
kubectl get deployment load-generator -n proxy-monitor
kubectl get hpa load-generator -n proxy-monitor
```

### Configure Load Patterns

Edit the ConfigMap to customize load patterns:

```bash
kubectl edit configmap load-generator-config -n proxy-monitor
```

## Post-Deployment Configuration

### 1. Grafana Setup

#### Access Grafana

```bash
# Get Grafana URL
kubectl get svc grafana -n proxy-monitor

# Port forward for local access
kubectl port-forward svc/grafana 3000:80 -n proxy-monitor
```

#### Import Dashboards

1. Access Grafana at `http://localhost:3000`
2. Login with admin credentials
3. Import dashboards from `grafana-dashboards/` directory:
   - Upload `proxy-overview.json`
   - Upload `vendor-analytics.json`
   - Upload `bandwidth-tracking.json`
   - Upload `infrastructure.json`

#### Configure Data Sources

Prometheus data source should be auto-configured. Verify:
- URL: `http://prometheus.proxy-monitor.svc.cluster.local:9090`
- Access: Server (default)

### 2. Prometheus Configuration

#### Verify Scrape Targets

```bash
# Port forward to Prometheus
kubectl port-forward svc/prometheus 9090:9090 -n proxy-monitor

# Check targets at http://localhost:9090/targets
```

#### Validate Recording Rules

Check that recording rules are loaded:
- Navigate to `http://localhost:9090/rules`
- Verify all rules are active

### 3. Istio Configuration

#### Verify Service Mesh

```bash
# Check Istio injection
kubectl get pods -n proxy-monitor -o jsonpath='{.items[*].spec.containers[*].name}' | tr ' ' '\n' | grep istio-proxy

# Check virtual services
kubectl get virtualservice -n proxy-monitor

# Check destination rules
kubectl get destinationrule -n proxy-monitor
```

## Validation and Testing

### 1. Health Checks

```bash
# Check all pods are running
kubectl get pods -n proxy-monitor --field-selector=status.phase!=Running

# Check service endpoints
kubectl get endpoints -n proxy-monitor

# Verify persistent volumes
kubectl get pv | grep proxy-monitor
```

### 2. Metrics Validation

#### Verify Metric Collection

```bash
# Query Prometheus for proxy metrics
curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=istio_requests_total{source_app="crawler"}'

# Check metric cardinality
curl -G 'http://localhost:9090/api/v1/label/__name__/values' | jq '.data | length'
```

#### Test Dashboard Functionality

1. Open Grafana dashboards
2. Verify data is populated
3. Test time range selection
4. Validate alert functionality

### 3. Load Testing

#### Generate Synthetic Load

```bash
# Scale up load generator for testing
kubectl scale deployment load-generator --replicas=5 -n proxy-monitor

# Monitor load generation
kubectl logs -f deployment/load-generator -n proxy-monitor
```

#### Validate Metrics

Monitor the following metrics during load testing:
- Request rate increases
- Latency metrics populated
- Error rates within expected ranges
- Resource utilization normal

## Troubleshooting

### Common Issues

#### 1. Pods Not Starting

```bash
# Check pod events
kubectl describe pod <pod-name> -n proxy-monitor

# Check resource constraints
kubectl top pods -n proxy-monitor
kubectl get limitrange -n proxy-monitor
```

#### 2. Metrics Not Appearing

```bash
# Verify Prometheus targets
kubectl logs deployment/prometheus -n proxy-monitor

# Check service discovery
kubectl get servicemonitor -n proxy-monitor
kubectl describe servicemonitor prometheus-servicemonitor -n proxy-monitor
```

#### 3. Dashboard Not Loading

```bash
# Check Grafana logs
kubectl logs deployment/grafana -n proxy-monitor

# Verify data source connectivity
kubectl exec -it deployment/grafana -n proxy-monitor -- wget -qO- http://prometheus:9090/api/v1/query?query=up
```

#### 4. Istio Issues

```bash
# Check Istio proxy status
istioctl proxy-status

# Verify configuration
istioctl analyze -n proxy-monitor

# Check Envoy configuration
kubectl exec deployment/load-generator -c istio-proxy -n proxy-monitor -- curl localhost:15000/stats/prometheus
```

### Performance Issues

#### High Memory Usage

```bash
# Check memory consumption
kubectl top pods -n proxy-monitor

# Adjust resource limits
kubectl patch deployment prometheus -n proxy-monitor -p '{"spec":{"template":{"spec":{"containers":[{"name":"prometheus","resources":{"limits":{"memory":"4Gi"}}}]}}}}'
```

#### Slow Dashboard Loading

1. Check Prometheus query performance
2. Optimize dashboard queries using recording rules
3. Increase Grafana memory limits
4. Enable query caching in Grafana

### Recovery Procedures

#### Pod Recovery

```bash
# Restart failed pods
kubectl rollout restart deployment/prometheus -n proxy-monitor
kubectl rollout restart deployment/grafana -n proxy-monitor

# Check rollout status
kubectl rollout status deployment/prometheus -n proxy-monitor
```

#### Data Recovery

```bash
# Restore from backup (if available)
kubectl apply -f backup/prometheus-data-restore.yaml

# Verify data integrity
kubectl exec -it deployment/prometheus -n proxy-monitor -- promtool tsdb list /prometheus
```

## Maintenance

### Regular Updates

#### Update Container Images

```bash
# Update to latest stable versions
helm upgrade proxy-monitor ./helm-chart/proxy-monitor \
  --set prometheus.image.tag=v2.40.0 \
  --set grafana.image.tag=9.3.0 \
  --namespace proxy-monitor
```

#### Backup Configuration

```bash
# Export current configuration
helm get values proxy-monitor -n proxy-monitor > current-values.yaml

# Backup Grafana dashboards
kubectl get configmap grafana-dashboards -n proxy-monitor -o yaml > grafana-backup.yaml
```

### Monitoring Maintenance

#### Clean Old Data

```bash
# Prometheus data cleanup (if manual retention needed)
kubectl exec -it deployment/prometheus -n proxy-monitor -- \
  promtool tsdb list /prometheus --human-readable

# Remove old snapshots
kubectl exec -it deployment/prometheus -n proxy-monitor -- \
  find /prometheus -name "*.snap" -mtime +7 -delete
```

#### Update Alerting Rules

```bash
# Update alert rules
kubectl apply -f manifests/prometheus-config.yaml

# Reload Prometheus configuration
kubectl exec deployment/prometheus -n proxy-monitor -- \
  curl -X POST http://localhost:9090/-/reload
```

## Security Hardening

### Network Security

```bash
# Apply restrictive network policies
kubectl apply -f manifests/network-policy.yaml

# Verify policy enforcement
kubectl get networkpolicy -n proxy-monitor
```

### RBAC Validation

```bash
# Check service account permissions
kubectl auth can-i --list --as=system:serviceaccount:proxy-monitor:prometheus

# Validate minimal privileges
kubectl describe clusterrole prometheus-clusterrole
```

### Certificate Management

```bash
# Check certificate expiration
kubectl get secret monitoring-tls -n proxy-monitor -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -dates

# Renew certificates (automated with cert-manager)
kubectl annotate certificate monitoring-tls -n proxy-monitor cert-manager.io/force-renewal=true
```

This deployment guide provides comprehensive instructions for setting up and maintaining the proxy monitoring solution in production environments.