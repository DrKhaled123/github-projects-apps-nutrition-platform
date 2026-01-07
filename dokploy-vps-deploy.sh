#!/bin/bash

# Dokploy VPS Deployment Script (Password Authentication)
# Usage: ./dokploy-vps-deploy.sh <vps-ip> <ssh-user> <password>

VPS_IP=$1
SSH_USER=$2
SSH_PASSWORD=$3

if [ -z "$VPS_IP" ] || [ -z "$SSH_USER" ] || [ -z "$SSH_PASSWORD" ]; then
    echo "Usage: $0 <vps-ip> <ssh-user> <password>"
    echo "Example: $0 149.102.150.185 root Khaled55400214"
    exit 1
fi

echo "🚀 Deploying Dokploy to VPS: $VPS_IP"

# Install sshpass if not available
if ! command -v sshpass &> /dev/null; then
    echo "📦 Installing sshpass..."
    brew install hudochenkov/sshpass/sshpass || apt-get install -y sshpass || yum install -y sshpass
fi

# Copy project files to VPS
echo "📁 Copying project files to VPS..."
sshpass -p "$SSH_PASSWORD" rsync -avz --exclude 'node_modules' --exclude '.git' --exclude '__pycache__' \
      -e "ssh -o StrictHostKeyChecking=no" \
      ./ $SSH_USER@$VPS_IP:~/nutrition-platform/

# Install Dokploy on VPS
echo "🔥 Installing Dokploy on VPS..."
sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_USER@$VPS_IP << 'EOF'
    cd ~/nutrition-platform

    # Update system
    sudo apt update && sudo apt upgrade -y

    # Install Docker and Docker Compose
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER

    # Install Docker Compose
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose

    # Start Docker service
    sudo systemctl start docker
    sudo systemctl enable docker

    # Create necessary directories
    mkdir -p monitoring/traefik monitoring/grafana/provisioning/datasources
    mkdir -p monitoring/grafana/provisioning/dashboards monitoring/grafana/dashboards
    mkdir -p monitoring/prometheus/rules monitoring/alertmanager
    mkdir -p database/postgres/init database/mysql/init database/mongodb/init
    mkdir -p database/mariadb/init database/redis

    # Generate secure passwords if .env.dokploy doesn't exist
    if [ ! -f .env.dokploy ]; then
        cat > .env.dokploy << 'EOL'
# Dokploy Configuration
DOKPLOY_DOMAIN=your-domain.com
DOKPLOY_NEXTAUTH_URL=https://your-domain.com
DOKPLOY_NEXTAUTH_SECRET=d3f5d829775f0a4946b86187213c12052fdae9b41d13739d773fc3f3fbf1fd32

# Database Passwords
DOKPLOY_DB_PASSWORD=47d2d96166970c30ffc0434b0a7ffdec
DOKPLOY_MYSQL_ROOT_PASSWORD=7a0eb16fa3f5b0e147b1c53291f17145
DOKPLOY_MYSQL_PASSWORD=08f282dba99f16cc99883fa5d8847792
DOKPLOY_MONGO_ROOT_USERNAME=admin
DOKPLOY_MONGO_ROOT_PASSWORD=c31c53beb28abfef359df23ef9fa5c3b
DOKPLOY_MARIADB_ROOT_PASSWORD=404480403bcb192a2aeb045d3f9d21e3
DOKPLOY_MARIADB_PASSWORD=9028a93247e3a04f3a16544090551ed5

# Monitoring Configuration
DOKPLOY_METRICS_CONFIG='{
  "server": {
    "refreshRate": 25,
    "port": 3001,
    "type": "Dokploy",
    "token": "dokploy-metrics-ad62cfcc94a1426bd8dcdb8de71d3f87",
    "urlCallback": "http://dokploy-main:3000/api/trpc/notification.receiveNotification",
    "retentionDays": 7,
    "cronJob": "0 0 * * *",
    "thresholds": {
      "cpu": 80,
      "memory": 85
    }
  },
  "containers": {
    "refreshRate": 25,
    "services": {
      "include": ["*"],
      "exclude": []
    }
  }
}'

# Grafana Configuration
DOKPLOY_GRAFANA_USER=admin
DOKPLOY_GRAFANA_PASSWORD=2fcb7849df8bd95dfcc33cf58f235484

# SSL/TLS Configuration
DOKPLOY_LETSENCRYPT_EMAIL=your-email@your-domain.com

# Security
JWT_SECRET=64c0126cae66f509b56c38ed9913c7203b6bb856feef4ef3a83ce162e97e2464
ENCRYPTION_KEY=5f2af5f97ede69866f22b67f600c82412b770145e8bcbd40192393d3f1d22c7c

# Application Settings
NODE_ENV=production
LOG_LEVEL=info
MAX_BACKUP_RETENTION_DAYS=30
BACKUP_SCHEDULE=0 2 * * *
HEALTH_CHECK_INTERVAL=30
EOL
    fi

    # Start Dokploy
    docker-compose -f docker-compose.dokploy.yml --env-file .env.dokploy up -d

    # Wait for startup
    sleep 60

    # Show status
    echo "📊 Dokploy Status:"
    docker-compose -f docker-compose.dokploy.yml ps

    echo "✅ Dokploy deployment completed!"
    echo "🌐 Dokploy Dashboard: http://$VPS_IP:3000"
    echo "📊 Grafana: http://$VPS_IP:3002"
    echo "🔍 Traefik: http://$VPS_IP:8080"
EOF

echo "✅ Dokploy deployment to VPS completed!"
echo ""
echo "🌐 Access your Dokploy instance at: http://$VPS_IP:3000"
echo "📊 Grafana at: http://$VPS_IP:3002"
echo "🔍 Traefik Dashboard at: http://$VPS_IP:8080"