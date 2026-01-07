#!/bin/sh

# Production-ready Docker entrypoint script
# Handles initialization, health checks, and graceful shutdown

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
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

# Function to check if a service is healthy
check_service_health() {
    local service=$1
    local max_attempts=30
    local attempt=1
    
    log_info "Checking $service health..."
    
    while [ $attempt -le $max_attempts ]; do
        if python3 /app/scripts/health-check.py --service=$service; then
            log_info "$service is healthy"
            return 0
        fi
        
        log_warn "$service health check attempt $attempt/$max_attempts failed"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_error "$service failed to become healthy after $max_attempts attempts"
    return 1
}

# Function to run database migrations
run_migrations() {
    if [ "$RUN_MIGRATIONS" = "true" ]; then
        log_info "Running database migrations..."
        if python3 /app/scripts/migrate-database.py; then
            log_info "Database migrations completed successfully"
        else
            log_error "Database migrations failed"
            exit 1
        fi
    fi
}

# Function to initialize application
initialize_app() {
    log_info "Initializing application..."
    
    # Create necessary directories
    mkdir -p logs tmp data
    
    # Set proper permissions
    chmod 755 logs tmp data
    
    # Generate app-specific secrets if not provided
    if [ -z "$APP_SECRET_KEY" ]; then
        export APP_SECRET_KEY=$(openssl rand -hex 32)
        log_info "Generated application secret key"
    fi
    
    # Validate required environment variables
    if [ -z "$DATABASE_URL" ] && [ -z "$POSTGRES_URL" ]; then
        log_warn "No database URL provided, running with in-memory storage"
    fi
    
    log_info "Application initialization completed"
}

# Function to start background services
start_background_services() {
    log_info "Starting background services..."
    
    # Start monitoring service if enabled
    if [ "$ENABLE_MONITORING" = "true" ]; then
        python3 /app/monitoring/monitor.py &
        log_info "Started monitoring service"
    fi
    
    # Start orchestration service if enabled
    if [ "$ENABLE_ORCHESTRATION" = "true" ]; then
        python3 /app/orchestration/main_orchestrator.py &
        log_info "Started orchestration service"
    fi
}

# Function to handle graceful shutdown
graceful_shutdown() {
    log_info "Received shutdown signal, gracefully shutting down..."
    
    # Send SIGTERM to background processes
    if [ -n "$BACKGROUND_PIDS" ]; then
        for pid in $BACKGROUND_PIDS; do
            kill -TERM $pid 2>/dev/null || true
        done
        
        # Wait for processes to shut down
        sleep 5
        
        # Force kill if still running
        for pid in $BACKGROUND_PIDS; do
            kill -KILL $pid 2>/dev/null || true
        done
    fi
    
    log_info "Graceful shutdown completed"
    exit 0
}

# Set up signal handlers
trap graceful_shutdown SIGTERM SIGINT

# Main execution
main() {
    log_info "Starting Docker container for Nutrition Platform AI Factory"
    
    # Initialize application
    initialize_app
    
    # Run database migrations if needed
    run_migrations
    
    # Start background services
    start_background_services
    
    # Collect background process PIDs
    BACKGROUND_PIDS=$(jobs -p)
    
    # Wait a moment for services to start
    sleep 3
    
    # Health check before starting main application
    if ! check_service_health "database"; then
        log_error "Database health check failed, but continuing..."
    fi
    
    log_info "Starting main application..."
    log_info "Environment: ${ENVIRONMENT:-production}"
    log_info "Port: ${PORT:-8080}"
    log_info "Process ID: $$"
    
    # Execute the main application
    exec "$@"
}

# Execute main function with all arguments
main "$@"
