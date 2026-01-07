# CI/CD Pipeline Setup Guide

This guide explains how to set up and configure the complete CI/CD pipeline with GitHub Actions and Dokploy integration for the nutrition platform application.

## Overview

The CI/CD pipeline includes:
- **Automated testing** (unit, integration, performance, smoke tests)
- **Security scanning** (vulnerability detection, secret scanning)
- **Code quality checks** (linting, formatting, type checking)
- **Docker image building** and multi-platform support
- **Automated deployment** to staging and production environments
- **Health checks** and rollback capabilities
- **Monitoring** and alerting

## Prerequisites

### 1. GitHub Repository Setup
- Repository must be hosted on GitHub
- GitHub Actions must be enabled
- Container registry access (GitHub Container Registry)

### 2. Dokploy Setup
- Dokploy instance installed and configured
- Staging and production environments set up
- Applications created in Dokploy with corresponding IDs
- API keys generated for both environments

### 3. Required Secrets
Add the following secrets to your GitHub repository:

#### Dokploy Configuration
```
DOKPLOY_HOST_STAGING=https://staging.dokploy.com
DOKPLOY_API_KEY_STAGING=your_staging_api_key
DOKPLOY_APP_ID_STAGING=your_staging_app_id

DOKPLOY_HOST_PRODUCTION=https://dokploy.com
DOKPLOY_API_KEY_PRODUCTION=your_production_api_key
DOKPLOY_APP_ID_PRODUCTION=your_production_app_id
```

#### Database Configuration
```
DB_HOST_STAGING=staging-db.example.com
DB_PORT_STAGING=5432
DB_USER_STAGING=staging_user
DB_PASSWORD_STAGING=staging_password
DB_NAME_STAGING=staging_db

DB_HOST_PRODUCTION=prod-db.example.com
DB_PORT_PRODUCTION=5432
DB_USER_PRODUCTION=prod_user
DB_PASSWORD_PRODUCTION=prod_password
DB_NAME_PRODUCTION=prod_db
```

#### Security Configuration
```
JWT_SECRET_STAGING=your_staging_jwt_secret
JWT_SECRET_PRODUCTION=your_production_jwt_secret
```

#### Notification Configuration
```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
```

## Pipeline Structure

### Main CI/CD Workflow (`.github/workflows/ci-cd.yml`)

#### Triggers
- **Push** to `main`, `develop`, `staging` branches
- **Pull requests** to `main` branch
- **Releases** when published

#### Jobs

1. **Security Scan**
   - Trivy vulnerability scanning
   - Gosec security scanning for Go
   - Secret detection with TruffleHog
   - Results uploaded to GitHub Security tab

2. **Code Quality**
   - Go formatting and linting with golangci-lint
   - Frontend linting
   - Type checking
   - Secret scanning

3. **Testing**
   - Unit tests with coverage
   - Integration tests with PostgreSQL and Redis
   - Frontend tests
   - Property-based tests
   - Contract tests
   - Coverage reporting to Codecov

4. **Build and Push**
   - Multi-platform Docker builds (amd64, arm64)
   - Container registry pushing
   - SBOM generation
   - Docker layer caching

5. **Performance Testing**
   - Load testing with k6
   - Performance audits
   - Synthetic monitoring

6. **Deployment**
   - Staging deployment for develop/staging branches
   - Production deployment for main branch
   - Health checks and smoke tests
   - Slack notifications

7. **Post-Deployment**
   - Comprehensive health checks
   - Metrics monitoring
   - Synthetic monitoring
   - Deployment status tracking

8. **Rollback**
   - Automatic rollback on health check failures
   - Previous deployment detection
   - Rollback notifications

### Dokploy Deployment Workflow (`.github/workflows/dokploy-deploy.yml`)

#### Triggers
- **Manual workflow dispatch** with environment selection
- **Tag pushes** for releases

#### Features
- Environment selection (staging/production)
- Force deployment option (skip health checks)
- Comprehensive health checks
- Rollback capabilities
- Deployment artifacts and records

## Local Development Setup

### 1. Install Dependencies
```bash
# Go dependencies
go mod download

# Node.js dependencies
npm install
```

### 2. Testing Commands
```bash
# Run all tests
npm test

# Run unit tests only
go test ./... -v

# Run integration tests
npm run test:integration

# Run smoke tests
npm run test:smoke

# Run performance tests
npm run test:performance

# Run property-based tests
npm run test:property

# Run contract tests
npm run test:contract
```

### 3. Code Quality Commands
```bash
# Run linting
npm run lint

# Run type checking
npm run type-check

# Run security scan
npm run security-scan

# Run performance audit
npm run performance-audit
```

### 4. Docker Commands
```bash
# Build Docker image
npm run build:docker

# Run test environment
npm run start:test

# Stop test environment
npm run stop:test

# Run database migrations
npm run migrate:test
```

## Environment Configuration

### Staging Environment
- **Base URL**: `https://staging.doctorhealthy1.com`
- **Rate Limit**: 500 requests/minute
- **CORS Origins**: `https://staging.doctorhealthy1.com`
- **Debug Mode**: Enabled

### Production Environment
- **Base URL**: `https://my.doctorhealthy1.com`
- **Rate Limit**: 1000 requests/minute
- **CORS Origins**: Multiple domains
- **Debug Mode**: Disabled

## Monitoring and Observability

### Health Endpoints
- `/health` - Basic health check
- `/health/detailed` - Detailed health information
- `/ready` - Readiness probe
- `/metrics` - Prometheus metrics

### Monitoring Stack
- **Prometheus**: Metrics collection
- **Grafana**: Visualization and dashboards
- **AlertManager**: Alerting and notifications
- **Node Exporter**: System metrics

### Logging
- Structured JSON logging
- Log levels (debug, info, warn, error)
- Request/response logging
- Error tracking and reporting

## Deployment Process

### Automatic Deployment
1. **Push to develop** → Deploy to staging
2. **Push to main** → Deploy to production
3. **Create release tag** → Deploy to production with full validation

### Manual Deployment
1. Go to GitHub Actions → Dokploy Deployment Workflow
2. Click "Run workflow"
3. Select environment (staging/production)
4. Choose force deployment if needed
5. Monitor deployment progress

### Deployment Verification
- Health checks automatically run
- Smoke tests validate functionality
- Performance metrics are collected
- Slack notifications sent on completion

## Rollback Process

### Automatic Rollback
- Triggered when health checks fail
- Automatically deploys previous successful version
- Sends rollback notifications

### Manual Rollback
1. Identify previous stable version
2. Use Dokploy dashboard or API to rollback
3. Verify rollback health
4. Monitor application stability

## Security Best Practices

### Container Security
- Multi-stage builds to reduce attack surface
- Non-root user execution
- Minimal base images
- Security scanning on each build

### Secrets Management
- Environment-specific secrets
- GitHub encrypted secrets
- No hardcoded credentials
- Regular secret rotation

### Network Security
- HTTPS-only communication
- CORS restrictions
- Rate limiting
- Request validation

## Performance Optimization

### Build Optimization
- Docker layer caching
- Parallel builds
- Multi-platform support
- SBOM generation

### Runtime Optimization
- Health checks with proper timeouts
- Graceful shutdown handling
- Resource limits and monitoring
- Load balancing configuration

## Troubleshooting

### Common Issues

#### Build Failures
- Check dependency versions
- Verify build arguments
- Review build logs
- Check resource limits

#### Test Failures
- Review test logs
- Check environment setup
- Verify test data
- Debug with local testing

#### Deployment Failures
- Check Dokploy connection
- Verify API keys
- Review deployment logs
- Check health endpoints

#### Performance Issues
- Monitor resource usage
- Check response times
- Review load test results
- Optimize bottlenecks

### Debug Commands
```bash
# Check container logs
docker logs <container_id>

# Check health status
curl https://my.doctorhealthy1.com/health

# Run diagnostics
docker-compose -f docker-compose.test.yml logs

# Monitor resources
docker stats
```

## Maintenance

### Regular Tasks
- Update dependencies
- Review and update security scans
- Monitor and optimize performance
- Backup configurations and data

### Monitoring
- Set up alerting rules
- Review dashboards regularly
- Monitor error rates
- Track performance metrics

### Documentation
- Keep documentation updated
- Document changes and decisions
- Maintain runbooks for incidents
- Share knowledge with team

## Support

For issues and questions:
1. Check GitHub Issues
2. Review pipeline logs
3. Consult documentation
4. Contact the development team

---

This setup provides a robust, automated CI/CD pipeline that ensures code quality, security, and reliable deployments to staging and production environments using Dokploy.
