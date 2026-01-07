#!/bin/bash

# PostgreSQL Migration Script for Nutrition Platform
# This script migrates data from SQLite to PostgreSQL

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Default values
SQLITE_DB_PATH="./data/app.db"
BACKUP_DIR="./backups"
MIGRATION_TOOL="./bin/migrate-to-postgres"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --sqlite-path)
            SQLITE_DB_PATH="$2"
            shift 2
            ;;
        --backup-dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --sqlite-path PATH    Path to SQLite database file (default: ./data/app.db)"
            echo "  --backup-dir PATH     Directory for backups (default: ./backups)"
            echo "  --dry-run            Show what would be done without executing"
            echo "  --help, -h           Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  DB_HOST              PostgreSQL host (default: localhost)"
            echo "  DB_PORT              PostgreSQL port (default: 5432)"
            echo "  DB_USER              PostgreSQL user (required)"
            echo "  DB_PASSWORD          PostgreSQL password (required)"
            echo "  DB_NAME              PostgreSQL database name (required)"
            echo "  DB_SSLMODE           SSL mode (default: require)"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate required environment variables
check_env() {
    local required_vars=("DB_USER" "DB_PASSWORD" "DB_NAME")
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        error "Missing required environment variables: ${missing_vars[*]}"
        error "Please set these variables and try again"
        exit 1
    fi
}

# Validate SQLite database exists
validate_sqlite() {
    if [[ ! -f "$SQLITE_DB_PATH" ]]; then
        error "SQLite database not found: $SQLITE_DB_PATH"
        exit 1
    fi
    
    # Check if SQLite database is readable
    if ! sqlite3 "$SQLITE_DB_PATH" "SELECT 1;" >/dev/null 2>&1; then
        error "SQLite database is not readable: $SQLITE_DB_PATH"
        exit 1
    fi
    
    log "SQLite database validation passed: $SQLITE_DB_PATH"
}

# Test PostgreSQL connection
test_postgres_connection() {
    info "Testing PostgreSQL connection..."
    
    local host="${DB_HOST:-localhost}"
    local port="${DB_PORT:-5432}"
    local user="$DB_USER"
    local dbname="$DB_NAME"
    
    PGPASSWORD="$DB_PASSWORD" psql -h "$host" -p "$port" -U "$user" -d "$dbname" -c "SELECT 1;" >/dev/null 2>&1
    
    if [[ $? -eq 0 ]]; then
        log "PostgreSQL connection test passed"
        return 0
    else
        error "Failed to connect to PostgreSQL"
        error "Please check your connection parameters and ensure the database exists"
        return 1
    fi
}

# Create backup directory
create_backup_dir() {
    mkdir -p "$BACKUP_DIR"
    log "Backup directory created/verified: $BACKUP_DIR"
}

# Backup SQLite database
backup_sqlite() {
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_file="$BACKUP_DIR/sqlite_backup_${timestamp}.db"
    
    info "Creating SQLite backup: $backup_file"
    
    cp "$SQLITE_DB_PATH" "$backup_file"
    
    if [[ $? -eq 0 ]]; then
        log "SQLite backup created successfully"
        echo "$backup_file"
    else
        error "Failed to create SQLite backup"
        exit 1
    fi
}

# Check database size and estimate migration time
estimate_migration() {
    local sqlite_size=$(du -h "$SQLITE_DB_PATH" | cut -f1)
    info "SQLite database size: $sqlite_size"
    
    # Count records in main tables
    local user_count=$(sqlite3 "$SQLITE_DB_PATH" "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")
    local api_key_count=$(sqlite3 "$SQLITE_DB_PATH" "SELECT COUNT(*) FROM api_keys;" 2>/dev/null || echo "0")
    local recipe_count=$(sqlite3 "$SQLITE_DB_PATH" "SELECT COUNT(*) FROM recipes;" 2>/dev/null || echo "0")
    
    info "Records to migrate:"
    info "  - Users: $user_count"
    info "  - API Keys: $api_key_count"
    info "  - Recipes: $recipe_count"
    
    # Estimate time (rough calculation: ~1000 records per second)
    local total_records=$((user_count + api_key_count + recipe_count))
    local estimated_seconds=$((total_records / 1000 + 30)) # Base 30 seconds overhead
    
    info "Estimated migration time: ${estimated_seconds} seconds"
}

# Build migration tool
build_migration_tool() {
    if [[ ! -f "$MIGRATION_TOOL" ]]; then
        info "Building migration tool..."
        
        mkdir -p "$(dirname "$MIGRATION_TOOL")"
        go build -o "$MIGRATION_TOOL" ./cmd/migrate-to-postgres
        
        if [[ $? -eq 0 ]]; then
            log "Migration tool built successfully"
        else
            error "Failed to build migration tool"
            exit 1
        fi
    fi
}

# Run migration
run_migration() {
    local sqlite_backup="$1"
    
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        info "DRY RUN: Would migrate from $sqlite_backup to PostgreSQL"
        info "DRY RUN: Migration command: $MIGRATION_TOOL --sqlite $sqlite_backup"
        return 0
    fi
    
    info "Starting migration from $sqlite_backup to PostgreSQL..."
    
    # Run the migration tool
    "$MIGRATION_TOOL" \
        --sqlite "$sqlite_backup" \
        --postgres-host "${DB_HOST:-localhost}" \
        --postgres-port "${DB_PORT:-5432}" \
        --postgres-user "$DB_USER" \
        --postgres-password "$DB_PASSWORD" \
        --postgres-database "$DB_NAME" \
        --postgres-sslmode "${DB_SSLMODE:-require}"
    
    if [[ $? -eq 0 ]]; then
        log "Migration completed successfully!"
    else
        error "Migration failed!"
        exit 1
    fi
}

# Verify migration
verify_migration() {
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        info "DRY RUN: Would verify migration results"
        return 0
    fi
    
    info "Verifying migration results..."
    
    # Compare record counts
    local sqlite_user_count=$(sqlite3 "$SQLITE_DB_PATH" "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")
    local sqlite_api_key_count=$(sqlite3 "$SQLITE_DB_PATH" "SELECT COUNT(*) FROM api_keys;" 2>/dev/null || echo "0")
    local sqlite_recipe_count=$(sqlite3 "$SQLITE_DB_PATH" "SELECT COUNT(*) FROM recipes;" 2>/dev/null || echo "0")
    
    local postgres_user_count=$(PGPASSWORD="$DB_PASSWORD" psql -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null | xargs || echo "0")
    local postgres_api_key_count=$(PGPASSWORD="$DB_PASSWORD" psql -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM api_keys;" 2>/dev/null | xargs || echo "0")
    local postgres_recipe_count=$(PGPASSWORD="$DB_PASSWORD" psql -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM recipes;" 2>/dev/null | xargs || echo "0")
    
    info "Migration verification:"
    info "  Users: SQLite ($sqlite_user_count) -> PostgreSQL ($postgres_user_count)"
    info "  API Keys: SQLite ($sqlite_api_key_count) -> PostgreSQL ($postgres_api_key_count)"
    info "  Recipes: SQLite ($sqlite_recipe_count) -> PostgreSQL ($postgres_recipe_count)"
    
    # Check if counts match
    if [[ "$sqlite_user_count" -eq "$postgres_user_count" ]] && \
       [[ "$sqlite_api_key_count" -eq "$postgres_api_key_count" ]] && \
       [[ "$sqlite_recipe_count" -eq "$postgres_recipe_count" ]]; then
        log "Migration verification passed - all records migrated successfully!"
        return 0
    else
        warn "Migration verification failed - record counts don't match"
        return 1
    fi
}

# Update configuration
update_config() {
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        info "DRY RUN: Would update configuration to use PostgreSQL"
        return 0
    fi
    
    info "Updating configuration to use PostgreSQL..."
    
    # Create .env.postgres file
    cat > .env.postgres << EOF
# PostgreSQL Configuration
DB_TYPE=postgres
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_NAME=$DB_NAME
DB_SSLMODE=${DB_SSLMODE:-require}
DB_MAX_OPEN_CONNS=25
DB_MAX_IDLE_CONNS=5
DB_CONN_MAX_LIFETIME=5m
EOF
    
    log "PostgreSQL configuration saved to .env.postgres"
    warn "Please update your main .env file or set these environment variables in production"
}

# Main migration function
main() {
    log "Starting PostgreSQL migration process..."
    
    # Validation
    check_env
    validate_sqlite
    test_postgres_connection
    
    # Preparation
    create_backup_dir
    estimate_migration
    
    # Backup
    local sqlite_backup
    sqlite_backup=$(backup_sqlite)
    
    # Build tool and migrate
    build_migration_tool
    run_migration "$sqlite_backup"
    
    # Verification
    verify_migration
    
    # Update configuration
    update_config
    
    log "PostgreSQL migration completed successfully!"
    info "Next steps:"
    info "1. Test your application with the new PostgreSQL database"
    info "2. Update your deployment configuration to use PostgreSQL"
    info "3. Monitor the application for any issues"
    info "4. Keep the SQLite backup as a fallback"
}

# Handle script interruption
trap 'error "Migration interrupted"; exit 1' INT TERM

# Run main function
main "$@"
