#!/bin/bash

# Automated Backup Script for Dokploy
# This script handles automated backups based on the backup configuration

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Configuration
BACKUP_CONFIG_FILE="${BACKUP_CONFIG_FILE:-./scripts/backup-config.yml}"
BACKUP_DIR="/var/lib/dokploy/backups"
LOG_FILE="/var/log/dokploy-backups.log"
TEMP_DIR="/tmp/dokploy-backup-$$"

# Load environment variables
if [ -f .env.dokploy ]; then
    export $(cat .env.dokploy | grep -v '^#' | xargs)
fi

# Function to parse YAML (simple parser)
parse_yaml() {
    local file="$1"
    local prefix="$2"
    local s='[[:space:]]*'
    local w='[a-zA-Z0-9_]*'
    
    grep -E "^\s*#|^\s*$" "$file" >/dev/null || true
    sed -ne "s|^\($s\)\($w\)$s:${s}\(.*\)\$|\1$prefix\2 \3|p" "$file" | \
    sed -e "s|^\($s\)-$s\(.*\)\$|\1$prefix\- \2|p" | \
    while read -r key value; do
        echo "$key $value"
    done
}

# Function to create backup directory
create_backup_dir() {
    local backup_path="$1"
    local date_suffix=$(date '+%Y%m%d_%H%M%S')
    local full_path="${backup_path}/${date_suffix}"
    
    mkdir -p "$full_path"
    echo "$full_path"
}

# Function to compress backup
compress_backup() {
    local source_dir="$1"
    local destination_file="$2"
    
    log_info "Compressing backup: $source_dir -> $destination_file"
    
    if tar -czf "$destination_file" -C "$(dirname "$source_dir")" "$(basename "$source_dir")"; then
        log_success "Backup compressed successfully"
        rm -rf "$source_dir"  # Remove uncompressed backup
        echo "$destination_file"
    else
        log_error "Failed to compress backup"
        return 1
    fi
}

# Function to upload to S3
upload_to_s3() {
    local file="$1"
    local bucket="$2"
    local s3_path="$3"
    
    if ! command -v aws &> /dev/null; then
        log_warning "AWS CLI not found, skipping S3 upload"
        return 0
    fi
    
    log_info "Uploading to S3: $bucket/$s3_path"
    
    if aws s3 cp "$file" "s3://$bucket/$s3_path" --region "${AWS_REGION:-us-east-1}"; then
        log_success "Successfully uploaded to S3"
        return 0
    else
        log_error "Failed to upload to S3"
        return 1
    fi
}

# Function to backup PostgreSQL
backup_postgres() {
    log_info "Starting PostgreSQL backup"
    
    local backup_dir=$(create_backup_dir "$BACKUP_DIR/postgres")
    local date_suffix=$(date '+%Y%m%d_%H%M%S')
    local backup_file="$backup_dir/postgres_backup_$date_suffix.sql"
    
    # Create backup
    if docker exec dokploy-postgres pg_dump -U postgres dokploy > "$backup_file"; then
        log_success "PostgreSQL backup created successfully"
        
        # Compress backup
        local compressed_file=$(compress_backup "$backup_dir" "${backup_dir}.tar.gz")
        
        # Upload to destinations
        if [[ "${BACKUP_DESTINATION_S3:-true}" == "true" ]]; then
            upload_to_s3 "$compressed_file" "${AWS_BACKUP_BUCKET}" "dokploy/postgres/$(basename "$compressed_file")"
        fi
        
        # Cleanup old backups
        find "$BACKUP_DIR/postgres" -name "*.tar.gz" -mtime +30 -delete
        
        log_success "PostgreSQL backup completed"
    else
        log_error "PostgreSQL backup failed"
        return 1
    fi
}

# Function to backup MySQL
backup_mysql() {
    log_info "Starting MySQL backup"
    
    local backup_dir=$(create_backup_dir "$BACKUP_DIR/mysql")
    local date_suffix=$(date '+%Y%m%d_%H%M%S')
    local backup_file="$backup_dir/mysql_backup_$date_suffix.sql"
    
    # Create backup
    if docker exec dokploy-mysql mysqldump -u root -p"${DOKPLOY_MYSQL_ROOT_PASSWORD}" --all-databases > "$backup_file"; then
        log_success "MySQL backup created successfully"
        
        # Compress backup
        local compressed_file=$(compress_backup "$backup_dir" "${backup_dir}.tar.gz")
        
        # Upload to destinations
        if [[ "${BACKUP_DESTINATION_S3:-true}" == "true" ]]; then
            upload_to_s3 "$compressed_file" "${AWS_BACKUP_BUCKET}" "dokploy/mysql/$(basename "$compressed_file")"
        fi
        
        # Cleanup old backups
        find "$BACKUP_DIR/mysql" -name "*.tar.gz" -mtime +30 -delete
        
        log_success "MySQL backup completed"
    else
        log_error "MySQL backup failed"
        return 1
    fi
}

# Function to backup MongoDB
backup_mongodb() {
    log_info "Starting MongoDB backup"
    
    local backup_dir=$(create_backup_dir "$BACKUP_DIR/mongodb")
    local date_suffix=$(date '+%Y%m%d_%H%M%S')
    local temp_backup="/tmp/mongodb_backup_$date_suffix"
    
    # Create backup
    if docker exec dokploy-mongodb mongodump --uri="mongodb://${DOKPLOY_MONGO_ROOT_USERNAME}:${DOKPLOY_MONGO_ROOT_PASSWORD}@localhost:27017" --out="$temp_backup"; then
        # Copy backup from container
        docker cp "dokploy-mongodb:$temp_backup" "$backup_dir/"
        
        log_success "MongoDB backup created successfully"
        
        # Compress backup
        local compressed_file=$(compress_backup "$backup_dir" "${backup_dir}.tar.gz")
        
        # Upload to destinations
        if [[ "${BACKUP_DESTINATION_S3:-true}" == "true" ]]; then
            upload_to_s3 "$compressed_file" "${AWS_BACKUP_BUCKET}" "dokploy/mongodb/$(basename "$compressed_file")"
        fi
        
        # Cleanup old backups
        find "$BACKUP_DIR/mongodb" -name "*.tar.gz" -mtime +30 -delete
        
        log_success "MongoDB backup completed"
    else
        log_error "MongoDB backup failed"
        return 1
    fi
}

# Function to backup Redis
backup_redis() {
    log_info "Starting Redis backup"
    
    local backup_dir=$(create_backup_dir "$BACKUP_DIR/redis")
    local date_suffix=$(date '+%Y%m%d_%H%M%S')
    local backup_file="$backup_dir/redis_backup_$date_suffix.rdb"
    
    # Trigger background save
    if docker exec dokploy-redis redis-cli BGSAVE; then
        # Wait for backup to complete
        sleep 5
        
        # Copy backup from container
        if docker cp "dokploy-redis:/data/dump.rdb" "$backup_file"; then
            log_success "Redis backup created successfully"
            
            # Compress backup
            local compressed_file=$(compress_backup "$backup_dir" "${backup_dir}.tar.gz")
            
            # Upload to destinations
            if [[ "${BACKUP_DESTINATION_S3:-true}" == "true" ]]; then
                upload_to_s3 "$compressed_file" "${AWS_BACKUP_BUCKET}" "dokploy/redis/$(basename "$compressed_file")"
            fi
            
            # Cleanup old backups
            find "$BACKUP_DIR/redis" -name "*.tar.gz" -mtime +7 -delete
            
            log_success "Redis backup completed"
        else
            log_error "Failed to copy Redis backup"
            return 1
        fi
    else
        log_error "Failed to trigger Redis backup"
        return 1
    fi
}

# Function to backup application data
backup_application_data() {
    log_info "Starting application data backup"
    
    local backup_dir=$(create_backup_dir "$BACKUP_DIR/application")
    local date_suffix=$(date '+%Y%m%d_%H%M%S')
    
    # Backup Dokploy data
    if docker run --rm -v dokploy_data:/source -v "$backup_dir":/backup alpine tar -czf "/backup/dokploy_data_$date_suffix.tar.gz" -C /source .; then
        log_success "Dokploy data backup created successfully"
        
        # Upload to destinations
        if [[ "${BACKUP_DESTINATION_S3:-true}" == "true" ]]; then
            upload_to_s3 "$backup_dir/dokploy_data_$date_suffix.tar.gz" "${AWS_BACKUP_BUCKET}" "dokploy/application/dokploy_data_$date_suffix.tar.gz"
        fi
        
        # Cleanup old backups
        find "$BACKUP_DIR/application" -name "dokploy_data_*.tar.gz" -mtime +30 -delete
    else
        log_error "Failed to backup Dokploy data"
        return 1
    fi
    
    log_success "Application data backup completed"
}

# Function to backup monitoring data
backup_monitoring_data() {
    log_info "Starting monitoring data backup"
    
    local backup_dir=$(create_backup_dir "$BACKUP_DIR/monitoring")
    local date_suffix=$(date '+%Y%m%d_%H%M%S')
    
    # Backup Grafana data
    if docker run --rm -v grafana_data:/source -v "$backup_dir":/backup alpine tar -czf "/backup/grafana_data_$date_suffix.tar.gz" -C /source .; then
        log_success "Grafana data backup created successfully"
    fi
    
    # Backup Prometheus data
    if docker run --rm -v prometheus_data:/source -v "$backup_dir":/backup alpine tar -czf "/backup/prometheus_data_$date_suffix.tar.gz" -C /source .; then
        log_success "Prometheus data backup created successfully"
    fi
    
    # Backup AlertManager data
    if docker run --rm -v alertmanager_data:/source -v "$backup_dir":/backup alpine tar -czf "/backup/alertmanager_data_$date_suffix.tar.gz" -C /source .; then
        log_success "AlertManager data backup created successfully"
    fi
    
    # Compress and upload
    local compressed_file=$(compress_backup "$backup_dir" "${backup_dir}.tar.gz")
    
    # Upload to destinations
    if [[ "${BACKUP_DESTINATION_S3:-true}" == "true" ]]; then
        upload_to_s3 "$compressed_file" "${AWS_BACKUP_BUCKET}" "dokploy/monitoring/$(basename "$compressed_file")"
    fi
    
    # Cleanup old backups
    find "$BACKUP_DIR/monitoring" -name "*.tar.gz" -mtime +90 -delete
    
    log_success "Monitoring data backup completed"
}

# Function to send notification
send_notification() {
    local status="$1"
    local message="$2"
    
    if [[ "${BACKUP_NOTIFICATIONS_ENABLED:-true}" == "true" ]]; then
        log_info "Sending backup notification: $status"
        
        # Send webhook notification
        if command -v curl &> /dev/null && [[ -n "${BACKUP_WEBHOOK_URL:-}" ]]; then
            curl -X POST "$BACKUP_WEBHOOK_URL" \
                -H "Content-Type: application/json" \
                -d "{\"status\": \"$status\", \"message\": \"$message\", \"timestamp\": \"$(date -Iseconds)\"}" \
                2>/dev/null || log_warning "Failed to send webhook notification"
        fi
        
        # Send email notification (if configured)
        if [[ -n "${BACKUP_EMAIL_TO:-}" ]] && command -v mail &> /dev/null; then
            echo "$message" | mail -s "Dokploy Backup $status" "${BACKUP_EMAIL_TO}" 2>/dev/null || log_warning "Failed to send email notification"
        fi
    fi
}

# Function to cleanup on exit
cleanup() {
    if [[ -n "${TEMP_DIR:-}" ]] && [[ -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
    fi
}

# Set up cleanup trap
trap cleanup EXIT

# Main execution
main() {
    log_info "Starting automated backup process"
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    # Create log directory
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Redirect output to log file
    exec > >(tee -a "$LOG_FILE") 2>&1
    
    local backup_type="${1:-all}"
    local success=true
    
    case "$backup_type" in
        "postgres")
            backup_postgres || success=false
            ;;
        "mysql")
            backup_mysql || success=false
            ;;
        "mongodb")
            backup_mongodb || success=false
            ;;
        "redis")
            backup_redis || success=false
            ;;
        "application")
            backup_application_data || success=false
            ;;
        "monitoring")
            backup_monitoring_data || success=false
            ;;
        "all")
            backup_postgres || success=false
            backup_mysql || success=false
            backup_mongodb || success=false
            backup_redis || success=false
            backup_application_data || success=false
            backup_monitoring_data || success=false
            ;;
        *)
            log_error "Unknown backup type: $backup_type"
            echo "Usage: $0 [postgres|mysql|mongodb|redis|application|monitoring|all]"
            exit 1
            ;;
    esac
    
    if $success; then
        log_success "Backup process completed successfully"
        send_notification "SUCCESS" "Dokploy backup completed successfully for type: $backup_type"
    else
        log_error "Backup process completed with errors"
        send_notification "FAILURE" "Dokploy backup failed for type: $backup_type"
        exit 1
    fi
}

# Execute main function
main "$@"
