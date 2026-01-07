#!/bin/bash

# Dokploy Installation Script
echo "🚀 Setting up Dokploy..."

# Start Docker daemon (requires sudo)
echo "📦 Starting Docker daemon..."
sudo systemctl start docker || sudo service docker start

# Wait for Docker to be ready
sleep 5

# Create necessary directories for monitoring
echo "📁 Creating monitoring directories..."
mkdir -p monitoring/traefik
mkdir -p monitoring/grafana/provisioning/datasources
mkdir -p monitoring/grafana/provisioning/dashboards
mkdir -p monitoring/grafana/dashboards
mkdir -p monitoring/prometheus/rules
mkdir -p monitoring/alertmanager
mkdir -p database/postgres/init
mkdir -p database/mysql/init
mkdir -p database/mongodb/init
mkdir -p database/mariadb/init
mkdir -p database/redis

# Start Dokploy stack
echo "🔥 Starting Dokploy stack..."
docker-compose -f docker-compose.dokploy.yml --env-file .env.dokploy up -d

# Wait for services to start
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check if Dokploy is running
if curl -f http://localhost:3000/api/health > /dev/null 2>&1; then
    echo "✅ Dokploy is running successfully!"
    echo ""
    echo "🌐 Access Dokploy at: http://localhost:3000"
    echo "📊 Grafana at: http://localhost:3002 (admin / your-grafana-password)"
    echo "📈 Prometheus at: http://localhost:9090"
    echo "🚦 Traefik Dashboard at: http://localhost:8080"
    echo ""
    echo "🔑 Default credentials:"
    echo "   Dokploy: Check the logs for initial setup"
    echo "   Grafana: admin / $(grep DOKPLOY_GRAFANA_PASSWORD .env.dokploy | cut -d'=' -f2)"
else
    echo "❌ Dokploy health check failed. Checking logs..."
    docker-compose -f docker-compose.dokploy.yml logs dokploy
fi