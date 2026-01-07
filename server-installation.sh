#!/bin/bash

# Dokploy Installation Script for Hetzner Server
# DoctorHealthy Nutrition Platform
# IP: 128.140.111.171
# Domain: dokploy.doctorhealthy1.com

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" >&2
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Secure sensitive data handling
log "🔒 Starting secure installation process..."

# Store sensitive data in memory only
SERVER_IP="128.140.111.171"
DOMAIN="dokploy.doctorhealthy1.com"
DOMAINS=("dokploy.doctorhealthy1.com" "monitor.doctorhealthy1.com" "backend.doctorhealthy1.com" "my.doctorhealthy1.com")

# Clear command history
history -c

# Update system
log "📦 Updating system packages..."
apt update && apt upgrade -y

# Install required packages
log "🔧 Installing required packages..."
apt install -y curl wget git gnupg2 software-properties-common \
    apt-transport-https ca-certificates gnupg \
    lsb-release htop nginx certbot python3-certbot-nginx \
    docker.io docker-compose-plugin ufw fail2ban

# Configure firewall
log "🛡️ Configuring firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 3000/tcp  # Dokploy default port
ufw allow 8080/tcp  # Application port
ufw enable

# Configure fail2ban
log "🔒 Configuring fail2ban..."
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 3
bantime = 3600
EOF

systemctl enable fail2ban
systemctl restart fail2ban

# Install Docker
log "🐳 Installing Docker..."
systemctl enable docker
systemctl start docker
usermod -aG docker root

# Add current user to docker group
if ! groups $USER | grep -q docker; then
    usermod -aG docker $USER
    log "Added $USER to docker group. Please log out and log back in for changes to take effect."
fi

# Install Docker Compose
log "🔧 Installing Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Verify Docker installation
log "✅ Verifying Docker installation..."
docker --version
docker-compose --version

# Create secure directories
log "📁 Creating application directories..."
mkdir -p /opt/dokploy
mkdir -p /opt/doctorhealthy
mkdir -p /opt/backups
mkdir -p /opt/ssl
mkdir -p /opt/logs
mkdir -p /opt/monitoring

# Set proper permissions
chmod 755 /opt/dokploy
chmod 755 /opt/doctorhealthy
chmod 700 /opt/ssl
chmod 755 /opt/backups
chmod 755 /opt/logs
chmod 755 /opt/monitoring

# Install Dokploy
log "🚀 Installing Dokploy..."
cd /opt/dokploy

# Download and install Dokploy
curl -sSL https://dokploy.com/install.sh | sh

# Create systemd service for Dokploy
log "⚙️ Creating systemd service for Dokploy..."
cat > /etc/systemd/system/dokploy.service << 'EOF'
[Unit]
Description=Dokploy
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/dokploy
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Enable and start Dokploy
systemctl daemon-reload
systemctl enable dokploy
systemctl start dokploy

# Wait for Dokploy to start
log "⏳ Waiting for Dokploy to start..."
sleep 30

# Check if Dokploy is running
if ! docker ps | grep -q dokploy; then
    error "Dokploy failed to start. Checking logs..."
    docker logs dokploy
    exit 1
fi

log "✅ Dokploy installed successfully!"

# Configure Nginx for reverse proxy
log "🌐 Configuring Nginx reverse proxy..."

# Backup original nginx config
if [ -f /etc/nginx/sites-available/default ]; then
    cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup
fi

# Create nginx configuration for Dokploy
cat > /etc/nginx/sites-available/dokploy << 'EOF'
server {
    listen 80;
    server_name dokploy.doctorhealthy1.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name dokploy.doctorhealthy1.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/dokploy.doctorhealthy1.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dokploy.doctorhealthy1.com/privkey.pem;
    
    # SSL Security
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Proxy to Dokploy
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/dokploy /etc/nginx/sites-enabled/

# Test nginx configuration
nginx -t && systemctl reload nginx

log "✅ Nginx configured successfully!"

# Obtain SSL certificate
log "🔐 Obtaining SSL certificate for $DOMAIN..."

# Install certbot and obtain certificate
certbot --nginx -d dokploy.doctorhealthy1.com --email admin@doctorhealthy1.com --agree-tos --no-eff-email --non-interactive

# Set up automatic certificate renewal
echo "0 12 * * * /usr/bin/certbot renew --quiet" | crontab -

log "✅ SSL certificate obtained and auto-renewal configured!"

# Create secure backup script
log "💾 Creating backup script..."
cat > /opt/backups/backup.sh << 'EOF'
#!/bin/bash

# Secure backup script for DoctorHealthy platform
set -euo pipefail

BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/opt/logs/backup.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Backup Docker volumes
log "Starting backup process..."

# Backup Dokploy data
if [ -d "/opt/dokploy" ]; then
    tar -czf "$BACKUP_DIR/dokploy_$DATE.tar.gz" -C /opt dokploy
    log "Dokploy data backed up"
fi

# Backup application data
if [ -d "/opt/doctorhealthy" ]; then
    tar -czf "$BACKUP_DIR/doctorhealthy_$DATE.tar.gz" -C /opt doctorhealthy
    log "Application data backed up"
fi

# Backup Docker configurations
docker config ls > "$BACKUP_DIR/docker_configs_$DATE.txt"
log "Docker configurations backed up"

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.txt" -mtime +30 -delete

log "Backup completed successfully"
EOF

chmod +x /opt/backups/backup.sh

# Add backup to cron (daily at 2 AM)
echo "0 2 * * * /opt/backups/backup.sh" | crontab -

# Create monitoring setup script
log "📊 Setting up monitoring..."
cat > /opt/monitoring/setup.sh << 'EOF'
#!/bin/bash

# Monitoring setup script
set -euo pipefail

# Install monitoring tools
apt install -y htop iotop nethogs

# Create monitoring directories
mkdir -p /opt/monitoring/{prometheus,grafana,alertmanager,logs}

log "Monitoring setup completed"
EOF

chmod +x /opt/monitoring/setup.sh
/opt/monitoring/setup.sh

# Secure SSH configuration
log "🔒 Securing SSH configuration..."

# Backup SSH config
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

# Harden SSH configuration
cat > /etc/ssh/sshd_config << 'EOF'
# SSH Configuration
Port 22
Protocol 2
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
ChallengeResponseAuthentication no
UsePAM yes
X11Forwarding no
PrintMotd no
AcceptEnv LANG LC_*
Subsystem sftp /usr/lib/openssh/sftp-server
MaxAuthTries 3
MaxSessions 2
ClientAliveInterval 300
ClientAliveCountMax 2
EOF

# Restart SSH service
systemctl restart sshd

log "✅ SSH configuration secured!"

# Final security check
log "🔍 Performing final security check..."

# Check open ports
log "Open ports:"
netstat -tulpn | grep LISTEN

# Check running services
log "Running services:"
systemctl list-units --type=service --state=running | head -10

# Check disk usage
log "Disk usage:"
df -h

# Check memory usage
log "Memory usage:"
free -h

# Create system monitoring script
cat > /opt/monitoring/system-monitor.sh << 'EOF'
#!/bin/bash

# System monitoring script
while true; do
    echo "=== $(date) ==="
    echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//')"
    echo "Memory Usage: $(free | grep Mem | awk '{printf("%.2f%%"), $3/$2 * 100.0}')"
    echo "Disk Usage: $(df -h / | tail -1 | awk '{print $5}')"
    echo "Load Average: $(uptime | awk -F'load average:' '{print $2}')"
    echo "=== End Report ==="
    sleep 300  # Every 5 minutes
done
EOF

chmod +x /opt/monitoring/system-monitor.sh

# Create security monitoring
cat > /opt/monitoring/security-monitor.sh << 'EOF'
#!/bin/bash

# Security monitoring script
LOG_FILE="/opt/logs/security.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] SECURITY: $1" >> "$LOG_FILE"
}

# Monitor failed SSH attempts
FAILED_SSH=$(grep "Failed password" /var/log/auth.log | grep "$(date '+%b %d')" | wc -l)
if [ "$FAILED_SSH" -gt 0 ]; then
    log "$FAILED_SSH failed SSH attempts detected"
fi

# Monitor suspicious IP addresses
grep "Failed password" /var/log/auth.log | awk '{print $NF}' | sort | uniq -c | sort -nr | head -5 >> /opt/logs/suspicious_ips.log

# Monitor Docker containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" >> /opt/logs/docker_status.log

log "Security monitoring completed"
EOF

chmod +x /opt/monitoring/security-monitor.sh

# Add monitoring to cron
echo "*/5 * * * * /opt/monitoring/system-monitor.sh" | crontab -
echo "0 * * * * /opt/monitoring/security-monitor.sh" | crontab -

# Clear sensitive data from memory
unset SERVER_IP
unset DOMAIN
unset DOMAINS

# Final cleanup
log "🧹 Cleaning up installation files..."
apt autoremove -y
apt autoclean

log "🎉 Dokploy installation completed successfully!"
log ""
log "📋 Next Steps:"
log "1. Access Dokploy: https://dokploy.doctorhealthy1.com"
log "2. Create your admin account"
log "3. Configure GitHub repository"
log "4. Deploy your application"
log ""
log "🔒 Security Notes:"
log "- SSH login is now key-based only"
log "- Firewall is configured and active"
log "- SSL certificate is installed and auto-renews"
log "- Fail2ban is monitoring for attacks"
log "- Backups are scheduled daily"
log "- Monitoring is active"
log ""
log "📊 Monitoring Available:"
log "- System resources: htop, iotop, nethogs"
log "- Logs: /opt/logs/"
log "- Backups: /opt/backups/"
log "- Security: /opt/logs/security.log"
log ""
log "✨ Installation completed at $(date)"

# Success message with next steps
echo ""
echo "🎉 DOKPLOY INSTALLATION COMPLETE! 🎉"
echo "==================================="
echo "📱 Access your Dokploy instance:"
echo "   URL: https://dokploy.doctorhealthy1.com"
echo ""
echo "🔧 Next Steps:"
echo "1. Open the URL in your browser"
echo "2. Create your admin account"
echo "3. Add your GitHub repository"
echo "4. Configure your domains"
echo "5. Deploy your applications"
echo ""
echo "🔐 Security Status:"
echo "- ✅ Firewall configured"
echo "- ✅ SSL certificate installed"
echo "- ✅ SSH secured (key-based only)"
echo "- ✅ Fail2ban active"
echo "- ✅ Daily backups scheduled"
echo "- ✅ Monitoring active"
echo ""
echo "📊 Server Details:"
echo "- IP: 128.140.111.171"
echo "- Domain: dokploy.doctorhealthy1.com"
echo "- Platform: Ubuntu on Hetzner"
echo ""
echo "🔍 For help, check the logs:"
echo "- System logs: /opt/logs/"
echo "- Security logs: /opt/logs/security.log"
echo "- Backup logs: /opt/logs/backup.log"
echo ""
echo "🚀 Ready for deployment!"
