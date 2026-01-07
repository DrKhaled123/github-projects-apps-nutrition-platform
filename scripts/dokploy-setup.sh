#!/bin/bash

# Dokploy Application Setup Script
# This script sets up a comprehensive Dokploy environment with databases, monitoring, and backups

set -euo pipefail

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

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root for security reasons."
        exit 1
    fi
}

# Check if Docker and Docker Compose are installed
check_docker() {
    log_info "Checking Docker installation..."
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    log_success "Docker and Docker Compose are installed"
}

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."
    
    directories=(
        "database/postgres/init"
        "database/mysql/init"
        "database/mongodb/init"
        "database/mariadb/init"
        "database/redis"
        "monitoring/traefik/dynamic"
        "monitoring/grafana/provisioning/datasources"
        "monitoring/grafana/provisioning/dashboards"
        "monitoring/grafana/dashboards"
        "monitoring/prometheus/rules"
        "monitoring/alertmanager"
        "backups"
        "logs"
        "ssl"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        log_info "Created directory: $dir"
    done
    
    log_success "All directories created"
}

# Generate secure passwords
generate_passwords() {
    log_info "Generating secure passwords..."
    
    # Function to generate secure password
    generate_password() {
        openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
    }
    
    # Generate passwords if not already set
    if ! grep -q "DOKPLOY_DB_PASSWORD=" .env.dokploy 2>/dev/null || [[ "${DOKPLOY_DB_PASSWORD}" == "your-secure-postgres-password" ]]; then
        POSTGRES_PASSWORD=$(generate_password)
        sed -i "s/DOKPLOY_DB_PASSWORD=.*/DOKPLOY_DB_PASSWORD=${POSTGRES_PASSWORD}/" .env.dokploy
    fi
    
    if ! grep -q "DOKPLOY_MYSQL_ROOT_PASSWORD=" .env.dokploy 2>/dev/null || [[ "${DOKPLOY_MYSQL_ROOT_PASSWORD}" == "your-secure-mysql-root-password" ]]; then
        MYSQL_ROOT_PASSWORD=$(generate_password)
        sed -i "s/DOKPLOY_MYSQL_ROOT_PASSWORD=.*/DOKPLOY_MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}/" .env.dokploy
    fi
    
    if ! grep -q "DOKPLOY_MONGO_ROOT_PASSWORD=" .env.dokploy 2>/dev/null || [[ "${DOKPLOY_MONGO_ROOT_PASSWORD}" == "your-secure-mongo-password" ]]; then
        MONGO_PASSWORD=$(generate_password)
        sed -i "s/DOKPLOY_MONGO_ROOT_PASSWORD=.*/DOKPLOY_MONGO_ROOT_PASSWORD=${MONGO_PASSWORD}/" .env.dokploy
    fi
    
    if ! grep -q "DOKPLOY_GRAFANA_PASSWORD=" .env.dokploy 2>/dev/null || [[ "${DOKPLOY_GRAFANA_PASSWORD}" == "your-secure-grafana-password" ]]; then
        GRAFANA_PASSWORD=$(generate_password)
        sed -i "s/DOKPLOY_GRAFANA_PASSWORD=.*/DOKPLOY_GRAFANA_PASSWORD=${GRAFANA_PASSWORD}/" .env.dokploy
    fi
    
    if ! grep -q "NEXTAUTH_SECRET=" .env.dokploy 2>/dev/null || [[ "${NEXTAUTH_SECRET}" == "your-super-secret-nextauth-key-here" ]]; then
        NEXTAUTH_SECRET=$(generate_password)
        sed -i "s/NEXTAUTH_SECRET=.*/NEXTAUTH_SECRET=${NEXTAUTH_SECRET}/" .env.dokploy
    fi
    
    log_success "Secure passwords generated"
}

# Create Redis configuration
create_redis_config() {
    log_info "Creating Redis configuration..."
    
    cat > database/redis/redis.conf << 'EOF'
# Redis configuration for Dokploy

# Network
bind 0.0.0.0
port 6379
timeout 0
tcp-keepalive 300

# General
daemonize no
supervised no
pidfile /var/run/redis_6379.pid
loglevel notice
logfile ""

# Snapshotting
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /data

# Security
# requirepass your-redis-password-here

# Memory
maxmemory 256mb
maxmemory-policy allkeys-lru

# Append only file
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# Slow log
slowlog-log-slower-than 10000
slowlog-max-len 128
EOF

    log_success "Redis configuration created"
}

# Create Traefik configuration
create_traefik_config() {
    log_info "Creating Traefik configuration..."
    
    cat > monitoring/traefik/traefik.yml << 'EOF'
# Traefik Static Configuration

api:
  dashboard: true
  insecure: true

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
    network: dokploy_dokploy-network
  
  file:
    directory: /etc/traefik/dynamic
    watch: true

entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
          permanent: true
  
  websecure:
    address: ":443"
    http:
      middlewares:
        - secureHeaders@file
      tls:
        options: modern@file

certificatesResolvers:
  letsencrypt:
    acme:
      email: "your-email@your-domain.com"
      storage: "/letsencrypt/acme.json"
      httpChallenge:
        entryPoint: web

log:
  level: INFO
  filePath: "/var/log/traefik/traefik.log"

accessLog:
  filePath: "/var/log/traefik/access.log"
  buffering:
    size: 100
    memLimit: 50MB
EOF

    cat > monitoring/traefik/dynamic/middlewares.yml << 'EOF'
# Traefik Dynamic Middlewares

http:
  middlewares:
    secureHeaders:
      headers:
        customRequestHeaders:
          X-Forwarded-Proto: https
        customResponseHeaders:
          X-Content-Type-Options: nosniff
          X-Frame-Options: DENY
          X-XSS-Protection: "1; mode=block"
          Referrer-Policy: strict-origin-when-cross-origin
          Strict-Transport-Security: "max-age=31536000; includeSubDomains"
        contentTypeNosniff: true
        browserXssFilter: true
        forceSTSHeader: true
        stsIncludeSubdomains: true
        stsPreload: true
        stsSeconds: 31536000
    
    compress:
      compress:
        enabled: true
        excludedContentTypes:
          - text/event-stream
    
    rateLimit:
      rateLimit:
        average: 100
        period: 1m
        
    auth:
      basicAuth:
        users:
          - "admin:$apr1$d9hrkHmz$B5L.zqG6Q2V8J9U0J7p5M/"
EOF

    log_success "Traefik configuration created"
}

# Create Prometheus configuration
create_prometheus_config() {
    log_info "Creating Prometheus configuration..."
    
    cat > monitoring/prometheus/prometheus.yml << 'EOF'
# Prometheus Configuration

global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    monitor: 'dokploy-monitor'

rule_files:
  - "rules/*.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
    scrape_interval: 10s

  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
    scrape_interval: 10s

  - job_name: 'traefik'
    static_configs:
      - targets: ['traefik:8080']
    metrics_path: /metrics
    scrape_interval: 10s

  - job_name: 'dokploy-monitoring'
    static_configs:
      - targets: ['dokploy-monitoring:3001']
    scrape_interval: 25s
    metrics_path: /metrics

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
    scrape_interval: 10s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
    scrape_interval: 10s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
EOF

    cat > monitoring/prometheus/rules/alerts.yml << 'EOF'
# Prometheus Alert Rules

groups:
  - name: dokploy.rules
    rules:
      - alert: HighCPUUsage
        expr: 100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is above 80% for more than 5 minutes on {{ $labels.instance }}"

      - alert: HighMemoryUsage
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is above 85% for more than 5 minutes on {{ $labels.instance }}"

      - alert: DiskSpaceLow
        expr: (1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100 > 90
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Low disk space"
          description: "Disk usage is above 90% on {{ $labels.instance }}"

      - alert: ContainerDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Container is down"
          description: "Container {{ $labels.instance }} has been down for more than 1 minute"

      - alert: PostgreSQLDown
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL is down"
          description: "PostgreSQL database has been down for more than 1 minute"

      - alert: RedisDown
        expr: up{job="redis"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis is down"
          description: "Redis cache has been down for more than 1 minute"
EOF

    log_success "Prometheus configuration created"
}

# Create AlertManager configuration
create_alertmanager_config() {
    log_info "Creating AlertManager configuration..."
    
    cat > monitoring/alertmanager/alertmanager.yml << 'EOF'
# AlertManager Configuration

global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@your-domain.com'
  smtp_require_tls: false

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
    - match:
        severity: warning
      receiver: 'warning-alerts'

receivers:
  - name: 'web.hook'
    webhook_configs:
      - url: 'http://dokploy-main:3000/api/trpc/notification.receiveNotification'
        send_resolved: true

  - name: 'critical-alerts'
    email_configs:
      - to: 'admin@your-domain.com'
        subject: '[CRITICAL] Dokploy Alert'
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          {{ end }}
    webhook_configs:
      - url: 'http://dokploy-main:3000/api/trpc/notification.receiveNotification'
        send_resolved: true

  - name: 'warning-alerts'
    email_configs:
      - to: 'alerts@your-domain.com'
        subject: '[WARNING] Dokploy Alert'
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          {{ end }}

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'dev', 'instance']
EOF

    log_success "AlertManager configuration created"
}

# Create Grafana provisioning
create_grafana_config() {
    log_info "Creating Grafana configuration..."
    
    cat > monitoring/grafana/provisioning/datasources/prometheus.yml << 'EOF'
# Grafana Prometheus Datasource

apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF

    cat > monitoring/grafana/provisioning/dashboards/dashboard.yml << 'EOF'
# Grafana Dashboard Provisioning

apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
EOF

    log_success "Grafana configuration created"
}

# Create backup scripts
create_backup_scripts() {
    log_info "Creating backup scripts..."
    
    cat > scripts/backup-databases.sh << 'EOF'
#!/bin/bash

# Database Backup Script
set -euo pipefail

BACKUP_DIR="/var/lib/dokploy/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup directory
mkdir -p "$BACKUP_DIR"

# PostgreSQL Backup
echo "Backing up PostgreSQL..."
docker exec dokploy-postgres pg_dump -U postgres dokploy > "$BACKUP_DIR/postgres_backup_$DATE.sql"

# MySQL Backup
echo "Backing up MySQL..."
docker exec dokploy-mysql mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" --all-databases > "$BACKUP_DIR/mysql_backup_$DATE.sql"

# MongoDB Backup
echo "Backing up MongoDB..."
docker exec dokploy-mongodb mongodump --uri="mongodb://$MONGO_ROOT_USERNAME:$MONGO_ROOT_PASSWORD@localhost:27017" --out="/tmp/mongodb_backup_$DATE"
docker cp dokploy-mongodb:/tmp/mongodb_backup_$DATE "$BACKUP_DIR/"

# Cleanup old backups
find "$BACKUP_DIR" -name "*.sql" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "mongodb_backup_*" -mtime +$RETENTION_DAYS -exec rm -rf {} \;

echo "Backup completed: $DATE"
EOF

    cat > scripts/backup-redis.sh << 'EOF'
#!/bin/bash

# Redis Backup Script
set -euo pipefail

BACKUP_DIR="/var/lib/dokploy/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Redis Backup
echo "Backing up Redis..."
docker exec dokploy-redis redis-cli BGSAVE
docker cp dokploy-redis:/data/dump.rdb "$BACKUP_DIR/redis_backup_$DATE.rdb"

echo "Redis backup completed: $DATE"
EOF

    chmod +x scripts/backup-databases.sh
    chmod +x scripts/backup-redis.sh
    
    log_success "Backup scripts created"
}

# Create startup script
create_startup_script() {
    log_info "Creating startup script..."
    
    cat > scripts/start-dokploy.sh << 'EOF'
#!/bin/bash

# Dokploy Startup Script
set -euo pipefail

echo "Starting Dokploy environment..."

# Load environment variables
if [ -f .env.dokploy ]; then
    export $(cat .env.dokploy | grep -v '^#' | xargs)
fi

# Start services
echo "Starting all services..."
docker-compose -f docker-compose.dokploy.yml up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 30

# Check service health
echo "Checking service health..."
docker-compose -f docker-compose.dokploy.yml ps

echo "Dokploy environment started successfully!"
echo "Access URLs:"
echo "- Dokploy: https://your-domain.com"
echo "- Grafana: https://grafana.your-domain.com"
echo "- Traefik: https://traefik.your-domain.com"
echo "- Prometheus: https://prometheus.your-domain.com"
EOF

    chmod +x scripts/start-dokploy.sh
    
    log_success "Startup script created"
}

# Create monitoring script
create_monitoring_script() {
    log_info "Creating monitoring script..."
    
    cat > scripts/monitor-dokploy.sh << 'EOF'
#!/bin/bash

# Dokploy Monitoring Script
set -euo pipefail

echo "Dokploy Environment Status"
echo "=========================="

# Check if services are running
services=("dokploy" "postgres" "redis" "mysql" "mongodb" "mariadb" "traefik" "grafana" "prometheus" "node-exporter" "cadvisor" "alertmanager")

for service in "${services[@]}"; do
    status=$(docker-compose -f docker-compose.dokploy.yml ps -q $service | xargs docker inspect --format='{{.State.Status}}' 2>/dev/null || echo "not_found")
    if [[ "$status" == "running" ]]; then
        echo "✅ $service: Running"
    else
        echo "❌ $service: $status"
    fi
done

echo ""
echo "Resource Usage:"
echo "=============="

# Docker system info
docker system df

echo ""
echo "Container Resource Usage:"
echo "========================"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

echo ""
echo "Recent Logs (last 20 lines):"
echo "============================"
docker-compose -f docker-compose.dokploy.yml logs --tail=20
EOF

    chmod +x scripts/monitor-dokploy.sh
    
    log_success "Monitoring script created"
}

# Function to display usage information
show_usage() {
    cat << EOF

🚀 Dokploy Setup Complete! 🚀

Next Steps:

1. Update the .env.dokploy file with your domain and email:
   nano .env.dokploy

2. Start the services:
   ./scripts/start-dokploy.sh

3. Monitor the services:
   ./scripts/monitor-dokploy.sh

4. Access your applications:
   - Dokploy: https://your-domain.com
   - Grafana: https://grafana.your-domain.com (admin:password)
   - Traefik Dashboard: https://traefik.your-domain.com
   - Prometheus: https://prometheus.your-domain.com

5. Configure backups in cron:
   0 2 * * * /path/to/scripts/backup-databases.sh
   0 3 * * * /path/to/scripts/backup-redis.sh

6. Set up monitoring alerts in Grafana and AlertManager

Important Notes:
- Make sure your domain points to this server's IP
- Replace all placeholder passwords and secrets in .env.dokploy
- Configure SSL certificates through Traefik
- Monitor disk space and resource usage regularly
- Test your backup and restore procedures

For more information, visit: https://docs.dokploy.com

EOF
}

# Main execution function
main() {
    log_info "Starting Dokploy setup..."
    
    check_root
    check_docker
    create_directories
    generate_passwords
    create_redis_config
    create_traefik_config
    create_prometheus_config
    create_alertmanager_config
    create_grafana_config
    create_backup_scripts
    create_startup_script
    create_monitoring_script
    
    log_success "Dokploy setup completed successfully!"
    show_usage
}

# Run the main function
main "$@"
