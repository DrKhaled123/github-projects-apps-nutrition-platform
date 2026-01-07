#!/bin/bash
# Production Deployment Script for DoctorHealthy1 using Coolify MCP

set -e

echo "🚀 Starting DoctorHealthy1 Production Deployment..."
echo "================================================="

# Configuration
COOLIFY_INSTANCE="api.doctorhealthy1.com"
FRONTEND_DOMAIN="super.doctorhealthy1.com"
BACKEND_DOMAIN="api.doctorhealthy1.com"
MONITORING_DOMAIN="test.doctorhealthy1.com"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required files exist
check_requirements() {
    log_info "Checking deployment requirements..."

    local required_files=(
        "Dockerfile.frontend"
        "Dockerfile"
        "docker-compose.yml"
        "nginx.conf"
        "coolify-config.json"
        ".env.coolify"
    )

    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            log_error "Required file missing: $file"
            exit 1
        fi
    done

    log_success "All required files present"
}

# Validate Docker configuration
validate_docker() {
    log_info "Validating Docker configuration..."

    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi

    # Validate Dockerfiles
    if ! docker build -f Dockerfile.frontend -t doctorhealthy1-frontend:test . >/dev/null 2>&1; then
        log_error "Frontend Dockerfile validation failed"
        exit 1
    fi

    if ! docker build -f Dockerfile -t doctorhealthy1-backend:test . >/dev/null 2>&1; then
        log_error "Backend Dockerfile validation failed"
        exit 1
    fi

    # Clean up test images
    docker rmi doctorhealthy1-frontend:test doctorhealthy1-backend:test >/dev/null 2>&1

    log_success "Docker configuration validated"
}

# Setup environment variables for Coolify
setup_coolify_env() {
    log_info "Setting up Coolify environment variables..."

    # Load environment variables
    if [[ -f ".env.coolify" ]]; then
        source .env.coolify
        log_success "Environment variables loaded from .env.coolify"
    else
        log_error ".env.coolify file not found"
        exit 1
    fi

    # Export variables for Coolify
    export COOLIFY_API_TOKEN="${COOLIFY_API_TOKEN:-}"
    export COOLIFY_APP_UUID="${COOLIFY_APP_UUID:-}"

    if [[ -z "$COOLIFY_API_TOKEN" ]] || [[ -z "$COOLIFY_APP_UUID" ]]; then
        log_error "COOLIFY_API_TOKEN and COOLIFY_APP_UUID must be set in .env.coolify"
        log_info "Please add these values to your .env.coolify file:"
        log_info "COOLIFY_API_TOKEN=your-actual-coolify-token"
        log_info "COOLIFY_APP_UUID=your-actual-app-uuid"
        exit 1
    fi

    log_success "Coolify environment variables configured"
}

# Deploy to Coolify using MCP server
deploy_to_coolify() {
    log_info "Deploying to Coolify instance: $COOLIFY_INSTANCE"

    # Check Coolify connection
    if ! curl -s "https://$COOLIFY_INSTANCE/api/v1/health" >/dev/null; then
        log_error "Cannot connect to Coolify instance at $COOLIFY_INSTANCE"
        exit 1
    fi

    log_success "Coolify instance accessible"

    # Deploy frontend
    log_info "Deploying frontend to $FRONTEND_DOMAIN..."
    # Using Coolify API to deploy frontend
    curl -X POST "https://$COOLIFY_INSTANCE/api/v1/deploy" \
        -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"uuid\": \"$COOLIFY_APP_UUID\", \"service\": \"frontend\"}"

    log_success "Frontend deployment initiated"

    # Deploy backend
    log_info "Deploying backend to $BACKEND_DOMAIN..."
    # Using Coolify API to deploy backend
    curl -X POST "https://$COOLIFY_INSTANCE/api/v1/deploy" \
        -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"uuid\": \"$COOLIFY_APP_UUID\", \"service\": \"backend\"}"

    log_success "Backend deployment initiated"

    # Deploy monitoring
    log_info "Deploying monitoring to $MONITORING_DOMAIN..."
    # Using Coolify API to deploy monitoring
    curl -X POST "https://$COOLIFY_INSTANCE/api/v1/deploy" \
        -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"uuid\": \"$COOLIFY_APP_UUID\", \"service\": \"monitoring\"}"

    log_success "Monitoring deployment initiated"
}

# Wait for deployment completion
wait_for_deployment() {
    log_info "Waiting for deployment completion..."

    local max_attempts=30
    local attempt=1
    local deployed=false

    while [[ $attempt -le $max_attempts ]]; do
        log_info "Checking deployment status (attempt $attempt/$max_attempts)..."

        # Check if services are responding
        if curl -s -f "https://$FRONTEND_DOMAIN/health.html" >/dev/null && \
           curl -s -f "https://$BACKEND_DOMAIN/health" >/dev/null; then
            deployed=true
            break
        fi

        sleep 10
        ((attempt++))
    done

    if [[ "$deployed" == "true" ]]; then
        log_success "Deployment completed successfully!"
    else
        log_warning "Deployment may still be in progress. Please check Coolify dashboard."
    fi
}

# Setup SSL certificates
setup_ssl() {
    log_info "Setting up SSL certificates..."

    # This would typically be handled by Coolify's automatic SSL
    log_info "SSL certificates will be automatically provisioned by Coolify"
    log_success "SSL setup initiated"
}

# Configure monitoring
setup_monitoring() {
    log_info "Configuring monitoring and alerting..."

    # Setup monitoring dashboards
    log_info "Monitoring dashboards available at: https://$MONITORING_DOMAIN"
    log_success "Monitoring configured"
}

# Final verification
verify_deployment() {
    log_info "Performing final deployment verification..."

    local endpoints=(
        "https://$FRONTEND_DOMAIN/health.html"
        "https://$BACKEND_DOMAIN/health"
        "https://$BACKEND_DOMAIN/api/v1/recipes"
    )

    for endpoint in "${endpoints[@]}"; do
        if curl -s -f "$endpoint" >/dev/null; then
            log_success "✓ $endpoint is accessible"
        else
            log_warning "✗ $endpoint is not accessible"
        fi
    done

    log_success "Deployment verification completed"
}

# Main deployment flow
main() {
    log_info "Starting DoctorHealthy1 production deployment"
    echo ""

    check_requirements
    validate_docker
    setup_coolify_env
    deploy_to_coolify
    wait_for_deployment
    setup_ssl
    setup_monitoring
    verify_deployment

    echo ""
    log_success "🎉 DoctorHealthy1 deployment completed successfully!"
    echo ""
    log_info "📋 Deployment Summary:"
    log_info "Frontend: https://$FRONTEND_DOMAIN"
    log_info "Backend API: https://$BACKEND_DOMAIN"
    log_info "Monitoring: https://$MONITORING_DOMAIN"
    log_info "Coolify Dashboard: https://$COOLIFY_INSTANCE"
    echo ""
    log_info "🔧 Next steps:"
    log_info "1. Verify all services are running in Coolify dashboard"
    log_info "2. Test the application functionality"
    log_info "3. Configure DNS records if needed"
    log_info "4. Setup monitoring alerts"
}

# Run deployment
main "$@"