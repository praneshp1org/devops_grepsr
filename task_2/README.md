# Microservices Application

A production-ready microservices application with Docker containerization, Kubernetes deployment, and automated CI/CD pipeline.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Frontend       │    │  API Service    │    │  Worker Service │
│  (React/Nginx)  │────│  (Node.js)      │────│  (Python)       │
│  Port: 8080     │    │  Port: 3000     │    │  Background     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                └──────────┬─────────────┘
                                          │
                                ┌─────────────────┐
                                │  PostgreSQL     │
                                │  Port: 5432     │
                                └─────────────────┘
```

## Services Overview

- **Frontend Service**: React application served via Nginx
- **API Service**: REST API built with Node.js and Express
- **Worker Service**: Python background job processor
- **Database**: PostgreSQL with persistent storage

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)
- kubectl (for Kubernetes deployment)
- minikube/kind/Docker Desktop (for local Kubernetes)

### Local Development with Docker Compose

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd microservices-app
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start all services**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Frontend: http://localhost:8080
   - API: http://localhost:3000
   - Database: localhost:5432

5. **View logs**
   ```bash
   docker-compose logs -f [service-name]
   ```

6. **Stop services**
   ```bash
   docker-compose down
   ```

### Kubernetes Deployment

#### Using Local Kubernetes (minikube/kind)

1. **Start your local Kubernetes cluster**
   ```bash
   # For minikube
   minikube start

   # For kind
   kind create cluster --name microservices
   ```

2. **Build Docker images**
   ```bash
   # Build all images
   ./k8s/deploy.sh
   
   # Or build individually
   cd api-service && docker build -t api-service:v1.0.0 .
   cd ../worker-service && docker build -t worker-service:v1.0.0 .
   cd ../frontend-service && docker build -t frontend-service:v1.0.0 .
   ```

3. **Load images to cluster (for minikube/kind)**
   ```bash
   # For minikube
   minikube image load api-service:v1.0.0
   minikube image load worker-service:v1.0.0
   minikube image load frontend-service:v1.0.0
   
   # For kind
   kind load docker-image api-service:v1.0.0 --name microservices
   kind load docker-image worker-service:v1.0.0 --name microservices
   kind load docker-image frontend-service:v1.0.0 --name microservices
   ```

4. **Deploy to Kubernetes**
   ```bash
   # Apply all manifests
   kubectl apply -f k8s/namespace.yaml
   kubectl apply -f k8s/configmap.yaml
   kubectl apply -f k8s/secret.yaml
   kubectl apply -f k8s/db-init-configmap.yaml
   kubectl apply -f k8s/postgres-pvc.yaml
   kubectl apply -f k8s/postgres-deployment.yaml
   
   # Wait for database
   kubectl wait --for=condition=ready pod -l app=postgres -n microservices --timeout=300s
   
   # Deploy services
   kubectl apply -f k8s/api-deployment.yaml
   kubectl apply -f k8s/worker-deployment.yaml
   kubectl apply -f k8s/frontend-deployment.yaml
   ```

5. **Access the application**
   ```bash
   # Get service URL (for minikube)
   minikube service frontend-service -n microservices --url
   
   # Or port-forward
   kubectl port-forward service/frontend-service 8080:8080 -n microservices
   ```

## Database Strategy

### Persistence

- **Development**: Docker volume (`postgres_data`)
- **Kubernetes**: PersistentVolumeClaim with 5Gi storage
- **Production**: Cloud-managed database recommended (AWS RDS, GCP Cloud SQL, etc.)

### Schema Management

Database schema is automatically initialized using:
- Docker Compose: `./database/init.sql` mounted as volume
- Kubernetes: ConfigMap `db-init-script` with init.sql

### Backup Strategy

For production environments:

1. **Automated Backups**
   ```bash
   # Example backup script
   kubectl exec deployment/postgres-deployment -n microservices -- pg_dump -U postgres microservices_db > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Scheduled Backups**
   ```yaml
   # Add to Kubernetes CronJob
   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: postgres-backup
   spec:
     schedule: "0 2 * * *"  # Daily at 2 AM
     jobTemplate:
       spec:
         template:
           spec:
             containers:
             - name: backup
               image: postgres:15-alpine
               command: ["/bin/bash"]
               args: ["-c", "pg_dump -h postgres-service -U postgres microservices_db | gzip > /backup/backup_$(date +%Y%m%d_%H%M%S).sql.gz"]
   ```

## CI/CD Pipeline

### GitHub Actions Workflow

The pipeline includes three main jobs:

1. **Test**: Runs unit tests for all services
2. **Build**: Creates Docker images and pushes to registry
3. **Deploy**: Deploys to Kubernetes cluster
4. **Rollback**: Automatic rollback on deployment failure

### Required Secrets

Configure these in GitHub repository settings:

```bash
# Kubernetes config (base64 encoded)
KUBECONFIG: <base64-encoded-kubeconfig>

# Container registry credentials
GITHUB_TOKEN: <github-token>

# Optional: Slack notifications
SLACK_WEBHOOK_URL: <slack-webhook-url>
```

### Manual Rollback

Use the manual rollback workflow:

1. Go to Actions → Manual Rollback
2. Select deployment to rollback
3. Choose number of revisions
4. Run workflow

## Scaling and Performance

### Horizontal Pod Autoscaler (HPA)

API service includes HPA configuration:
- Min replicas: 2
- Max replicas: 10
- Target CPU: 70%

### Resource Limits

| Service    | Request CPU | Request Memory | Limit CPU | Limit Memory |
|------------|-------------|----------------|-----------|--------------|
| API        | 100m        | 128Mi          | 200m      | 256Mi        |
| Worker     | 100m        | 128Mi          | 200m      | 256Mi        |
| Frontend   | 50m         | 64Mi           | 100m      | 128Mi        |
| Database   | 250m        | 256Mi          | 500m      | 512Mi        |

### Performance Tuning

1. **API Service**
   - Enable connection pooling in PostgreSQL client
   - Add Redis for caching (future enhancement)
   - Monitor response times with APM tools

2. **Worker Service**
   - Adjust worker count based on job volume
   - Implement job queuing with Redis/RabbitMQ
   - Add job retry mechanisms

3. **Frontend**
   - Enable gzip compression (configured in nginx.conf)
   - Implement CDN for static assets
   - Add service worker for caching

## Monitoring and Observability

### Health Checks

All services include health check endpoints:
- API: `GET /health`
- Frontend: `GET /` (nginx status)
- Database: `pg_isready` command

### Recommended Monitoring Stack

```yaml
# Example Prometheus + Grafana setup
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    scrape_configs:
    - job_name: 'kubernetes-pods'
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
```

### Logging

Structured logging is implemented in all services:
- API: Express request logging with Morgan
- Worker: Python logging with structured format
- Frontend: Nginx access logs

## Troubleshooting

### Common Issues

#### 1. Database Connection Issues

**Symptoms**: API/Worker services failing to connect to database

**Solutions**:
```bash
# Check database pod status
kubectl get pods -l app=postgres -n microservices

# Check database logs
kubectl logs deployment/postgres-deployment -n microservices

# Test database connectivity
kubectl exec -it deployment/api-deployment -n microservices -- nc -zv postgres-service 5432
```

#### 2. Service Discovery Issues

**Symptoms**: Services can't communicate with each other

**Solutions**:
```bash
# Check service DNS resolution
kubectl exec -it deployment/api-deployment -n microservices -- nslookup postgres-service

# Verify service endpoints
kubectl get endpoints -n microservices

# Check network policies
kubectl get networkpolicies -n microservices
```

#### 3. Image Pull Issues

**Symptoms**: `ImagePullBackOff` errors in Kubernetes

**Solutions**:
```bash
# For local clusters, load images manually
docker save api-service:v1.0.0 | docker load

# For minikube
minikube image load api-service:v1.0.0

# Check image pull policies
kubectl describe pod <pod-name> -n microservices
```

#### 4. Persistent Volume Issues

**Symptoms**: Database pod stuck in `Pending` state

**Solutions**:
```bash
# Check PVC status
kubectl get pvc -n microservices

# Check storage class availability
kubectl get storageclass

# For minikube, enable default storage class
minikube addons enable default-storageclass
minikube addons enable storage-provisioner
```

### Performance Issues

#### 1. High Database CPU Usage

**Investigation**:
```bash
# Check database metrics
kubectl top pods -l app=postgres -n microservices

# Analyze slow queries
kubectl exec -it deployment/postgres-deployment -n microservices -- psql -U postgres -d microservices_db -c "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
```

**Solutions**:
- Add database indexes for frequently queried columns
- Implement connection pooling
- Scale database vertically or use read replicas

#### 2. API Service High Latency

**Investigation**:
```bash
# Check API service logs
kubectl logs deployment/api-deployment -n microservices

# Monitor response times
curl -w "@curl-format.txt" -s -o /dev/null http://api-service:3000/health
```

**Solutions**:
- Scale API service horizontally
- Add caching layer (Redis)
- Optimize database queries

### Debugging Commands

```bash
# Get all resources in namespace
kubectl get all -n microservices

# Describe problematic pods
kubectl describe pod <pod-name> -n microservices

# Check events
kubectl get events -n microservices --sort-by=.metadata.creationTimestamp

# Port forward for local debugging
kubectl port-forward service/api-service 3000:3000 -n microservices

# Execute commands in pods
kubectl exec -it deployment/api-deployment -n microservices -- /bin/bash

# View resource usage
kubectl top pods -n microservices
kubectl top nodes
```

## Security Considerations

### Container Security

- All containers run as non-root users
- Multi-stage builds to minimize attack surface
- Regular base image updates for security patches

### Kubernetes Security

- Services use dedicated namespace
- Resource limits prevent resource exhaustion
- Secrets used for sensitive configuration
- Network policies can be added for additional isolation

### Database Security

- Passwords stored in Kubernetes secrets
- Database access restricted to service network
- Connection encryption enabled by default

## Development Workflow

### Local Development

1. **API Service**
   ```bash
   cd api-service
   npm install
   npm run dev
   ```

2. **Worker Service**
   ```bash
   cd worker-service
   pip install -r requirements.txt
   python worker.py
   ```

3. **Frontend Service**
   ```bash
   cd frontend-service
   npm install
   npm start
   ```

### Testing

```bash
# Run all tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# Individual service tests
cd api-service && npm test
cd worker-service && python -m pytest
cd frontend-service && npm test
```

### Code Quality

Recommended tools:
- ESLint for JavaScript code quality
- Black for Python code formatting
- Prettier for consistent formatting
- SonarQube for code quality analysis

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License.

---

For additional support or questions, please open an issue in the GitHub repository.