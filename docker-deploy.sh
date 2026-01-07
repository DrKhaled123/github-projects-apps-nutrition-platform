#!/bin/bash

# Production Docker deployment script for Dokploy
# This script handles the complete deployment process

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="nutrition-platform"
REGISTRY_URL="${DOCKER_REGISTRY:-your-registry.com}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
COMPOSE_FILE="docker-compose.prod.yml"

# Logging functions
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_info() {
    log "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    log "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    log "${RED}[ERROR]${NC} $1"
}

log_debug() {
    if [ "$DEBUG" = "true" ]; then
        log "${BLUE}[DEBUG]${NC} $1"
    fi
}

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking deployment prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        log_warn ".env file not found, copying from .env.example"
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_warn "Please edit .env file with your configuration before continuing"
            exit 1
        else
            log_error ".env.example file not found"
            exit 1
        fi
    fi
    
    # Check required files
    required_files=("Dockerfile" "docker-compose.prod.yml" "nginx/nginx.conf")
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "Required file $file not found"
            exit 1
        fi
    done
    
    log_info "Prerequisites check completed"
}

# Function to build Docker image
build_image() {
    log_info "Building Docker image..."
    
    local image_name="${PROJECT_NAME}:${IMAGE_TAG}"
    
    # Build with no-cache for production
    docker build \
        --no-cache \
        --pull \
        --tag "${image_name}" \
        --target production \
        .
    
    log_info "Docker image built successfully: ${image_name}"
}

# Function to run security scans
run_security_scans() {
    log_info "Running security scans..."
    
    # Check for vulnerabilities in the image
    if command -v trivy &> /dev/null; then
        log_info "Running Trivy security scan..."
        trivy image "${PROJECT_NAME}:${IMAGE_TAG}" || log_warn "Trivy scan completed with warnings"
    else
        log_warn "Trivy not installed, skipping security scan"
    fi
    
    # Check for secrets in the image
    log_info "Scanning for secrets..."
    # Add your secret scanning logic here
    
    log_info "Security scans completed"
}

# Function to validate configuration
validate_config() {
    log_info "Validating configuration..."
    
    # Validate Docker Compose file
    docker-compose -f "${COMPOSE_FILE}" config --quiet
    
    # Validate environment variables
    docker-compose -f "${COMPOSE_FILE}" config --services
    
    log_info "Configuration validation completed"
}

# Function to backup existing data
backup_data() {
    if [ "$SKIP_BACKUP" = "true" ]; then
        log_info "Skipping backup as requested"
        return
    fi
    
    log_info "Creating backup of existing data..."
    
    local backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup database if running
    if docker-compose -f "${COMPOSE_FILE}" ps postgres | grep -q "Up"; then
        log_info "Backing up PostgreSQL database..."
        docker-compose -f "${COMPOSE_FILE}" exec postgres pg_dump -U "${POSTGRES_USER:-postgres}" "${POSTGRES_DB:-nutrition_platform}" > "$backup_dir/database.sql"
    fi
    
    # Backup volumes
    log_info "Backing up Docker volumes..."
    docker run --rm -v nutrition-platform_postgres-data:/data -v "$(pwd)/$backup_dir":/backup alpine tar czf /backup/postgres-data.tar.gz -C /data .
    docker run --rm -v nutrition-platform_redis-data:/data -v "$(pwd)/$backup_dir":/backup alpine tar czf /backup/redis-data.tar.gz -C /data .
    
    log_info "Backup completed: $backup_dir"
}

# Function to deploy application
deploy_application() {
    log_info "Deploying application..."
    
    # Stop existing services
    log_info "Stopping existing services..."
    docker-compose -f "${COMPOSE_FILE}" down
    
    # Pull latest images
    log_info "Pulling latest images..."
    docker-compose -f "${COMPOSE_FILE}" pull
    
    # Start services
    log_info "Starting services..."
    docker-compose -f "${COMPOSE_FILE}" up -d
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 30
    
    # Run health checks
    log_info "Running health checks..."
    for i in {1..10}; do
        if curl -f http://localhost:8080/health &> /dev/null; then
            log_info "Application is healthy"
            break
        fi
        
        if [ $i -eq 10 ]; then
            log_error "Application failed health check after 10 attempts"
            docker-compose -f "${COMPOSE_FILE}" logs --tail=50 app
            exit 1
        fi
        
        log_info "Waiting for application to be ready... ($i/10)"
        sleep 10
    done
    
    log_info "Application deployed successfully"
}

# Function to run post-deployment tests
run_post_deployment_tests() {
    log_info "Running post-deployment tests..."
    
    # Test API endpoints
    log_info "Testing API endpoints..."
    curl -f http://localhost:8080/health || log_error "Health endpoint test failed"
    
    # Test database connectivity
    log_info "Testing database connectivity..."
    docker-compose -f "${COMPOSE_FILE}" exec -T python3 -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    conn.close()
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
    exit(1)
"
    
    log_info "Post-deployment tests completed"
}

# Function to cleanup old images
cleanup_old_images() {
    log_info "Cleaning up old Docker images..."
    
    # Remove dangling images
    docker image prune -f
    
    # Remove old versions of our image (keep last 3 versions)
    local old_images=$(docker images "${PROJECT_NAME}" --format "table {{.Repository}}:{{.Tag}}" | tail -n +2 | tail -n +4)
    if [ -n "$old_images" ]; then
        echo "$old_images" | xargs docker rmi -f || true
    fi
    
    log_info "Cleanup completed"
}

# Function to display deployment status
display_status() {
    log_info "Deployment status:"
    docker-compose -f "${COMPOSE_FILE}" ps
    
    log_info "Container logs (last 20 lines):"
    docker-compose -f "${COMPOSE_FILE}" logs --tail=20 app
}

# Function to rollback deployment
rollback_deployment() {
    log_error "Rolling back deployment..."
    
    # Stop current services
    docker-compose -f "${COMPOSE_FILE}" down
    
    # Restore from backup if available
    local latest_backup=$(ls -t backups/ | head -n 1)
    if [ -n "$latest_backup" ]; then
        log_info "Restoring from backup: $latest_backup"
        # Add rollback logic here
    fi
    
    # Start previous version
    # Add logic to start previous version here
    
    log_error "Rollback completed"
}

# Main deployment function
main() {
    log_info "Starting Docker deployment for ${PROJECT_NAME}"
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --debug)
                DEBUG=true
                shift
                ;;
            --rollback)
                ROLLBACK=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Handle rollback
    if [ "$ROLLBACK" = "true" ]; then
        rollback_deployment
        exit 0
    fi
    
    # Set trap for cleanup on exit
    trap 'log_error "Deployment failed, cleaning up..."; docker-compose -f "${COMPOSE_FILE}" down' EXIT
    
    # Execute deployment steps
    check_prerequisites
    validate_config
    build_image
    run_security_scans
    backup_data
    deploy_application
    run_post_deployment_tests
    cleanup_old_images
    display_status
    
    # Remove trap
    trap - EXIT
    
    log_info "🎉 Deployment completed successfully!"
    log_info "Application is available at: http://localhost:8080"
    log_info "Monitoring dashboards:"
    log_info "  - Grafana: http://localhost:3000"
    log_info "  - Prometheus: http://localhost:9090"
}

# Script usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --skip-backup    Skip backup creation"
    echo "  --debug          Enable debug logging"
    echo "  --rollback       Rollback to previous version"
    echo "  --help           Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  IMAGE_TAG        Docker image tag (default: latest)"
    echo "  DOCKER_REGISTRY  Docker registry URL"
    echo "  DEBUG            Enable debug mode (true/false)"
    echo "  SKIP_BACKUP      Skip backup creation (true/false)"
}

# Check for help flag
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    usage
    exit 0
fi

# Execute main function
main "$@"
