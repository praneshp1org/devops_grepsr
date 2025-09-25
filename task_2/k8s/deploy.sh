#!/bin/bash

# Build and deploy script for Kubernetes

echo "Building Docker images..."

# Build API service
echo "Building API service..."
cd api-service
docker build -t api-service:v1.0.0 .
cd ..

# Build worker service
echo "Building Worker service..."
cd worker-service
docker build -t worker-service:v1.0.0 .
cd ..

# Build frontend service
echo "Building Frontend service..."
cd frontend-service
docker build -t frontend-service:v1.0.0 .
cd ..

echo "Applying Kubernetes manifests..."

# Apply manifests in order
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/db-init-configmap.yaml
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/postgres-deployment.yaml

# Wait for database to be ready
echo "Waiting for database to be ready..."
kubectl wait --for=condition=ready pod -l app=postgres -n microservices --timeout=300s

# Deploy services
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/worker-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml

echo "Deployment complete!"
echo "Check status with: kubectl get pods -n microservices"