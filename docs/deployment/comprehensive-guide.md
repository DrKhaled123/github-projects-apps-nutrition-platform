# 🚀 Comprehensive Deployment Guide

**Complete guide for deploying DoctorHealthy1 to production environments**

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Deployment Methods](#deployment-methods)
4. [Coolify Deployment](#coolify-deployment)
5. [Dokploy Deployment](#dokploy-deployment)
6. [Manual Deployment](#manual-deployment)
7. [Environment Configuration](#environment-configuration)
8. [Monitoring & Health Checks](#monitoring--health-checks)
9. [Rollback Procedures](#rollback-procedures)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

This guide consolidates all deployment procedures for the DoctorHealthy1 nutrition platform. It covers multiple deployment methods, automation scripts, and best practices for production deployments.

### Supported Deployment Methods

- **Coolify** - Recommended for automated deployments
- **Dokploy** - Alternative self-hosted solution
- **Manual Docker** - Full control deployment
- **Direct Server** - Traditional server deployment

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Production Architecture                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Frontend  │    │   Backend   │    │  Database   │     │
│  │   (React)   │◄──►│   (Go)      │◄──►│ PostgreSQL  │     │
│  │   PWA Ready │    │   REST API  │    │   Primary   │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Coolify   │    │  Monitoring │    │  Security   │     │
│  │ Deployment  │    │   Dashboard │    │   Layer     │     │
│  │ Automation  │    │ Prometheus  │    │   SSL/TLS   │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ Prerequisites

### System Requirements

- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 20GB minimum, 50GB recommended
- **OS**: Ubuntu 20.04+ / Debian 10+ / CentOS 8+
- **Network**: Public IP with domain configured

### Software Dependencies

```bash
# Required packages
sudo apt update
sudo apt install -y docker docker-compose nginx certbot git

# Optional for development
sudo apt install -y nodejs npm go postgresql-client
```

### Domain Configuration

- **Primary Domain**: `doctorhealthy1.com`
- **API Domain**: `api.doctorhealthy1.com`
- **Monitoring Domain**: `monitor.doctorhealthy1.com`

### SSL Certificates

```bash
# Generate SSL certificates
sudo certbot certonly --standalone \
  -d doctorhealthy1.com \
  -d api.doctorhealthy1.com \
  -d monitor.doctorhealthy1.com
```

---

## 🚀 Deployment Methods

### Quick Start

```bash
# Automated deployment (recommended)
./scripts/deploy-to-coolify.sh

# Alternative methods
./scripts/deploy-manual.sh          # Manual Docker deployment
./scripts/deploy-dokploy.sh         # Dokploy deployment
./scripts/deploy-direct.sh          # Direct server deployment
```

### Method Selection Guide

| Method | Use Case | Complexity | Automation |
|--------|----------|------------|------------|
| **Coolify** | Production, CI/CD | Medium | ✅ Full |
| **Dokploy** | Self-hosted | Medium | ✅ Partial |
| **Manual** | Development | High | ❌ Manual |
| **Direct** | Legacy systems | Low | ❌ Manual |

---

## 🔄 Coolify Deployment (Recommended)

### Setup Configuration

1. **Install Coolify**
   ```bash
   curl -fsSL https://coolify.io/install.sh | bash
   ```

2. **Configure Application**
   ```bash
   cp coolify-config.json.example coolify-config.json
   # Edit configuration with your domain and settings
   ```

3. **Deploy Application**
   ```bash
   ./scripts/deploy-to-coolify.sh
   ```

### Coolify Configuration

```json
{
  "application": {
    "name": "DoctorHealthy1",
    "domain": "doctorhealthy1.com",
    "repository": "https://github.com/yourusername/doctorhealthy1",
    "branch": "main",
    "build_command": "docker-compose -f docker-compose.prod.yml build",
    "start_command": "docker-compose -f docker-compose.prod.yml up -d"
  },
  "services": {
    "frontend": {
      "domain": "doctorhealthy1.com",
      "port": 3000,
      "ssl": true
    },
    "backend": {
      "domain": "api.doctorhealthy1.com",
      "port": 8080,
      "ssl": true
    },
    "monitoring": {
      "domain": "monitor.doctorhealthy1.com",
      "port": 9090,
      "ssl": true
    }
  },
  "environment": {
    "NODE_ENV": "production",
    "DATABASE_URL": "postgresql://user:pass@localhost:5432/doctorhealthy1",
    "JWT_SECRET": "${JWT_SECRET}",
    "REDIS_URL": "redis://localhost:6379"
  }
}
```

### Deployment Script

```bash
#!/bin/bash
# scripts/deploy-to-coolify.sh

set -e

echo "🚀 Starting Coolify deployment..."

# Pre-deployment checks
./scripts/pre-deploy-check.sh

# Update environment variables
./scripts/setup-production-secrets.sh

# Trigger Coolify deployment
curl -X POST "https://api.coolify.io/v1/deploy" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d @coolify-config.json

# Monitor deployment
./scripts/monitor-deployment.sh

echo "✅ Deployment completed successfully!"
```

---

## 🔧 Dokploy Deployment

### Setup Instructions

1. **Install Dokploy**
   ```bash
   curl -sSL https://dokploy.com/install.sh | bash
   ```

2. **Configure Application**
   ```bash
   ./scripts/dokploy-setup.sh
   ```

3. **Deploy**
   ```bash
   ./scripts/deploy-dokploy.sh
   ```

### Dokploy Configuration

```yaml
# dokploy-config.yml
application:
  name: doctorhealthy1
  repository: https://github.com/yourusername/doctorhealthy1
  branch: main

build:
  dockerfile: Dockerfile
  context: .

deploy:
  port: 8080
  domains:
    - doctorhealthy1.com
    - api.doctorhealthy1.com
  
environment:
  - NODE_ENV=production
  - DATABASE_URL=${DATABASE_URL}
  - JWT_SECRET=${JWT_SECRET}
```

---

## 🐳 Manual Docker Deployment

### Production Dockerfile

```dockerfile
# Dockerfile
FROM golang:1.21-alpine AS backend-builder

WORKDIR /app
COPY backend/ .
RUN CGO_ENABLED=0 GOOS=linux go build -o main .

FROM node:18-alpine AS frontend-builder

WORKDIR /app
COPY frontend/ .
RUN npm install && npm run build

FROM alpine:latest

RUN apk --no-cache add ca-certificates
WORKDIR /root/

COPY --from=backend-builder /app/main .
COPY --from=frontend-builder /app/dist ./static

EXPOSE 8080
CMD ["./main"]
```

### Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:80"
    environment:
      - NODE_ENV=production
    restart: unless-stopped

  backend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - JWT_SECRET=${JWT_SECRET}
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=doctorhealthy1
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - /etc/letsencrypt:/etc/letsencrypt
    depends_on:
      - frontend
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
```

### Manual Deployment Steps

```bash
# 1. Clone repository
git clone https://github.com/yourusername/doctorhealthy1.git
cd doctorhealthy1

# 2. Configure environment
cp .env.example .env.production
# Edit .env.production with your values

# 3. Build and deploy
docker-compose -f docker-compose.prod.yml up -d

# 4. Setup SSL
./scripts/setup-ssl.sh

# 5. Verify deployment
./scripts/verify-deployment.sh
```

---

## ⚙️ Environment Configuration

### Required Environment Variables

```bash
# Application
NODE_ENV=production
PORT=8080
HOST=0.0.0.0

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/doctorhealthy1
DB_HOST=localhost
DB_PORT=5432
DB_NAME=doctorhealthy1
DB_USER=doctorhealthy1
DB_PASSWORD=your_secure_password

# Security
JWT_SECRET=your_jwt_secret_key_at_least_32_characters
JWT_EXPIRES_IN=24h
CORS_ORIGIN=https://doctorhealthy1.com

# Redis
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your_redis_password

# External Services
API_SECRET_KEY=your_api_secret_key
WEBHOOK_SECRET=your_webhook_secret

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001

# Email (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

### Secrets Management

```bash
# Generate secure secrets
./scripts/generate-secrets.sh

# Setup production secrets
./scripts/setup-production-secrets.sh
```

---

## 📊 Monitoring & Health Checks

### Health Check Endpoints

```bash
# Application health
curl https://api.doctorhealthy1.com/health

# Database health
curl https://api.doctorhealthy1.com/health/db

# Redis health
curl https://api.doctorhealthy1.com/health/redis

# System metrics
curl https://api.doctorhealthy1.com/metrics
```

### Monitoring Setup

```yaml
# monitoring/docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
    restart: unless-stopped

  alertmanager:
    image: prom/alertmanager:latest
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml
    restart: unless-stopped

volumes:
  grafana_data:
```

### Health Check Script

```bash
#!/bin/bash
# scripts/health-check.sh

echo "🔍 Running health checks..."

# Check frontend
if curl -f https://doctorhealthy1.com > /dev/null 2>&1; then
    echo "✅ Frontend is healthy"
else
    echo "❌ Frontend is down"
fi

# Check backend API
if curl -f https://api.doctorhealthy1.com/health > /dev/null 2>&1; then
    echo "✅ Backend API is healthy"
else
    echo "❌ Backend API is down"
fi

# Check database
if curl -f https://api.doctorhealthy1.com/health/db > /dev/null 2>&1; then
    echo "✅ Database is healthy"
else
    echo "❌ Database is down"
fi

# Check SSL certificates
if openssl s_client -connect doctorhealthy1.com:443 -servername doctorhealthy1.com </dev/null 2>/dev/null | openssl x509 -noout -dates | grep -q "notAfter"; then
    echo "✅ SSL certificates are valid"
else
    echo "❌ SSL certificates are invalid"
fi
```

---

## 🔄 Rollback Procedures

### Quick Rollback

```bash
# Coolify rollback
./scripts/rollback-coolify.sh

# Manual rollback
./scripts/rollback-manual.sh

# Database rollback
./scripts/rollback-database.sh
```

### Rollback Script

```bash
#!/bin/bash
# scripts/rollback.sh

set -e

BACKUP_VERSION=$1
if [ -z "$BACKUP_VERSION" ]; then
    echo "Usage: $0 <backup-version>"
    exit 1
}

echo "🔄 Starting rollback to version $BACKUP_VERSION..."

# Stop current services
docker-compose -f docker-compose.prod.yml down

# Restore database
./scripts/restore-database.sh $BACKUP_VERSION

# Deploy previous version
git checkout $BACKUP_VERSION
docker-compose -f docker-compose.prod.yml up -d

# Verify rollback
./scripts/verify-deployment.sh

echo "✅ Rollback to version $BACKUP_VERSION completed successfully!"
```

### Backup and Restore

```bash
# Create backup
./scripts/create-backup.sh

# List available backups
./scripts/list-backups.sh

# Restore from backup
./scripts/restore-backup.sh <backup-id>
```

---

## 🚨 Troubleshooting

### Common Issues

#### 1. SSL Certificate Issues

```bash
# Check certificate expiration
openssl s_client -connect doctorhealthy1.com:443 -servername doctorhealthy1.com 2>/dev/null | openssl x509 -noout -dates

# Renew certificates
sudo certbot renew --dry-run
sudo certbot renew
```

#### 2. Database Connection Issues

```bash
# Check database status
docker-compose -f docker-compose.prod.yml exec postgres pg_isready

# Check database logs
docker-compose -f docker-compose.prod.yml logs postgres

# Test database connection
psql $DATABASE_URL -c "SELECT 1;"
```

#### 3. Application Won't Start

```bash
# Check application logs
docker-compose -f docker-compose.prod.yml logs backend

# Check resource usage
docker stats

# Restart services
docker-compose -f docker-compose.prod.yml restart
```

#### 4. Performance Issues

```bash
# Check system resources
top
htop
df -h

# Check application metrics
curl https://api.doctorhealthy1.com/metrics

# Monitor in real-time
./scripts/live-monitor.py
```

### Debug Commands

```bash
# Full system diagnosis
./scripts/diagnose-system.sh

# Check all services
./scripts/check-all-services.sh

# Run performance tests
./scripts/performance-test.sh

# Security audit
./scripts/security-audit.sh
```

### Emergency Procedures

```bash
# Emergency stop
docker-compose -f docker-compose.prod.yml down

# Emergency restart
./scripts/emergency-restart.sh

# Data recovery
./scripts/emergency-recovery.sh
```

---

## 📞 Support

### Getting Help

- **Documentation**: Check this guide first
- **Issues**: Open an issue on GitHub
- **Emergency**: Contact the DevOps team

### Monitoring Alerts

Configure alerts in `monitoring/alertmanager.yml`:

```yaml
route:
  receiver: 'web.hook'
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h

receivers:
  - name: 'web.hook'
    email_configs:
      - to: 'admin@doctorhealthy1.com'
        subject: '[Alert] DoctorHealthy1 Production Alert'
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          {{ end }}
```

---

## 📚 Additional Resources

### Documentation Links

- [Security Guide](../security/comprehensive-security-guide.md)
- [API Documentation](../api/README.md)
- [Development Setup](../development/README.md)

### Scripts Reference

- [`scripts/deploy-to-coolify.sh`](../../scripts/deploy-to-coolify.sh) - Coolify deployment
- [`scripts/deploy-manual.sh`](../../scripts/deploy-manual.sh) - Manual deployment
- [`scripts/health-check.sh`](../../scripts/health-check.sh) - Health monitoring
- [`scripts/rollback.sh`](../../scripts/rollback.sh) - Rollback procedures

---

**Last Updated**: November 3, 2025
**Version**: 1.0.0

---

*This guide consolidates information from 10+ deployment guides into a single comprehensive resource.*
