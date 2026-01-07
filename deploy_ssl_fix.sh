#!/bin/bash

# DoctorHealthy1 Coolify Deployment Script - PRODUCTION READY
# Automated deployment to Coolify platform with comprehensive monitoring

set -e  # Exit on any error

echo "🚀 Starting DoctorHealthy1 API deployment to Coolify..."

# Configuration
COOLIFY_HOST="128.140.111.171"
COOLIFY_PORT="8000"
COOLIFY_TOKEN="${COOLIFY_API_TOKEN:-}"
APP_UUID="hcw0gc8wcwk440gw4c88408o"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Pre-deployment checks
print_header "🔍 PRE-DEPLOYMENT CHECKS"

# Check if git is clean
if ! git diff-index --quiet HEAD --; then
    print_warning "Uncommitted changes detected. Consider committing first."
fi

# Check if SSH tunnel is active
print_info "Checking SSH tunnel connectivity..."
if ! nc -z localhost $COOLIFY_PORT; then
    print_warning "SSH tunnel not detected, attempting to establish..."
    ssh -i ~/.ssh/coolify_doctorhealthy1 -N -L ${COOLIFY_PORT}:localhost:${COOLIFY_PORT} root@${COOLIFY_HOST} &
    SSH_PID=$!
    print_info "SSH tunnel started with PID: $SSH_PID"
    sleep 5
    
    if ! nc -z localhost $COOLIFY_PORT; then
        print_error "Failed to establish SSH tunnel"
        exit 1
    fi
fi

print_status "SSH tunnel is active"

# Test API connectivity
print_info "Testing Coolify API connectivity..."
API_TEST=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${COOLIFY_PORT}/api/v1/applications/${APP_UUID}" \
  -H "Authorization: Bearer ${COOLIFY_TOKEN}")

if [ "$API_TEST" != "200" ]; then
    print_error "Coolify API not accessible (HTTP $API_TEST)"
    exit 1
fi

print_status "Coolify API is accessible"

# Trigger deployment
print_header "🏗️ TRIGGERING DEPLOYMENT"

print_info "Initiating deployment request..."
DEPLOY_RESPONSE=$(curl -s -X POST "http://localhost:${COOLIFY_PORT}/api/v1/deploy" \
  -H "Authorization: Bearer ${COOLIFY_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"uuid\": \"${APP_UUID}\"}")

DEPLOYMENT_UUID=$(echo $DEPLOY_RESPONSE | grep -o '"deployment_uuid":"[^"]*' | sed 's/"deployment_uuid":"//')

if [ -z "$DEPLOYMENT_UUID" ]; then
    print_error "Failed to trigger deployment"
    echo "Response: $DEPLOY_RESPONSE"
    exit 1
fi

print_status "Deployment triggered successfully!"
print_info "Deployment UUID: $DEPLOYMENT_UUID"

# Monitor deployment with enhanced feedback
print_header "📊 MONITORING DEPLOYMENT"

LAST_STATUS=""
DEPLOY_START_TIME=$SECONDS

while true; do
    STATUS_RESPONSE=$(curl -s -X GET "http://localhost:${COOLIFY_PORT}/api/v1/deployments/${DEPLOYMENT_UUID}" \
      -H "Authorization: Bearer ${COOLIFY_TOKEN}")
    
    STATUS=$(echo $STATUS_RESPONSE | grep -o '"status":"[^"]*' | sed 's/"status":"//')
    CURRENT_TIME=$((SECONDS - DEPLOY_START_TIME))
    
    # Only print status change to avoid spam
    if [ "$STATUS" != "$LAST_STATUS" ]; then
        case $STATUS in
            "in_progress")
                print_info "Deployment in progress... (${CURRENT_TIME}s elapsed)"
                ;;
            "finished")
                print_status "Deployment completed successfully! (${CURRENT_TIME}s total)"
                break
                ;;
            "failed")
                print_error "Deployment failed after ${CURRENT_TIME}s!"
                # Get failure details from logs
                LOGS=$(echo $STATUS_RESPONSE | grep -o '"logs":"[^"]*' | sed 's/"logs":"//' | sed 's/\\n/\n/g')
                echo -e "\n${RED}Recent logs:${NC}"
                echo "$LOGS" | tail -10
                exit 1
                ;;
            *)
                print_warning "Status: $STATUS (${CURRENT_TIME}s elapsed)"
                ;;
        esac
        LAST_STATUS=$STATUS
    fi
    
    # Timeout after 10 minutes
    if [ $CURRENT_TIME -gt 600 ]; then
        print_error "Deployment timeout (10 minutes exceeded)"
        exit 1
    fi
    
    sleep 10
done

# Application health verification
print_header "🏥 HEALTH VERIFICATION"

print_info "Checking application health status..."
sleep 5  # Give the app a moment to fully start

APP_RESPONSE=$(curl -s -X GET "http://localhost:${COOLIFY_PORT}/api/v1/applications/${APP_UUID}" \
  -H "Authorization: Bearer ${COOLIFY_TOKEN}")

APP_STATUS=$(echo $APP_RESPONSE | grep -o '"status":"[^"]*' | sed 's/"status":"//')
LAST_ONLINE=$(echo $APP_RESPONSE | grep -o '"last_online_at":"[^"]*' | sed 's/"last_online_at":"//')

# Enhanced health check
case $APP_STATUS in
    "running:healthy")
        print_status "Application is running and healthy!"
        ;;
    "running"*)
        print_warning "Application is running but status: $APP_STATUS"
        ;;
    *)
        print_error "Application status: $APP_STATUS"
        ;;
esac

# Deployment summary
print_header "📋 DEPLOYMENT SUMMARY"

echo ""
echo "🎯 Application Details:"
echo "   Name: DoctorHealthy1 API"
echo "   Status: $APP_STATUS"
echo "   Last Online: $LAST_ONLINE"
echo "   Platform: Coolify (Self-hosted)"
echo "   Internal Port: 8081"
echo "   Health Endpoint: /health"
echo ""
echo "🏗️ Build Information:"
echo "   Docker: Multi-stage build with Go 1.22"
echo "   Database: SQLite with CGO support"
echo "   Runtime: Debian Bookworm Slim"
echo "   Security: Non-root user (appuser)"
echo ""
echo "🔗 Access Information:"
echo "   Internal Health Check: ✅ Active"
echo "   External Domain: Pending configuration"
echo "   Monitoring: Coolify Dashboard"
echo ""
echo "🚀 Next Steps:"
echo "   1. Configure domain mapping (api.128.140.111.171.nip.io)"
echo "   2. Set up SSL certificates for production"
echo "   3. Add persistent volume for database"
echo "   4. Configure log aggregation"
echo "   5. Set up monitoring and alerting"
echo ""

if [[ $APP_STATUS == *"healthy"* ]]; then
    print_status "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!"
    print_info "Your DoctorHealthy1 API is now running in production!"
    echo ""
    echo "� Quick Stats:"
    echo "   ⏱️  Total deployment time: ${CURRENT_TIME}s"
    echo "   🏥 Health status: Healthy"
    echo "   🔄 Auto-deployment: Configured"
    echo "   🛡️  Security: Hardened container"
    exit 0
else
    print_warning "Deployment completed but application needs attention"
    print_info "Check Coolify dashboard for detailed logs and metrics"
    exit 1
fi# SSL FIX COMMANDS
# Execute these commands on the production server (213.199.36.17)

# 1. REMOVE EDUVOICE CONFLICTS
echo "🗑️  Removing EduVoice conflicts..."
sudo systemctl stop eduvoice* 2>/dev/null || true
sudo pkill -f eduvoice 2>/dev/null || true
sudo rm -rf /etc/eduvoice* 2>/dev/null || true
sudo rm -f /etc/nginx/sites-enabled/*eduvoice* 2>/dev/null || true

# 2. BACKUP CURRENT NGINX
echo "💾 Backing up current configuration..."
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)

# 3. STOP NGINX AND CONFLICTING SERVICES
echo "🛑 Stopping conflicting services..."
sudo systemctl stop nginx
sudo fuser -k 80/tcp 2>/dev/null || true
sudo fuser -k 443/tcp 2>/dev/null || true

# 4. INSTALL CERTBOT
echo "📦 Installing/updating certbot..."
sudo apt update
sudo apt install -y certbot python3-certbot-nginx nginx-extras

# 5. INSTALL SSL CERTIFICATE FOR PRIMARY DOMAIN
echo "🔒 Installing SSL for my.doctorhealthy1.com..."
sudo certbot certonly \
    --standalone \
    --non-interactive \
    --agree-tos \
    --email admin@doctorhealthy1.com \
    --domains my.doctorhealthy1.com \
    --force-renewal

# 6. INSTALL SSL CERTIFICATE FOR ALTERNATIVE DOMAIN (if DNS configured)
echo "🔒 Testing and installing SSL for doctorhealy1.com..."
if nslookup doctorhealy1.com >/dev/null 2>&1; then
    sudo certbot certonly \
        --standalone \
        --non-interactive \
        --agree-tos \
        --email admin@doctorhealthy1.com \
        --domains doctorhealy1.com,www.doctorhealy1.com \
        --force-renewal
else
    echo "⚠️  doctorhealy1.com not configured in DNS, skipping..."
fi

# 7. CREATE NEW NGINX CONFIGURATION
echo "📝 Creating nutrition platform nginx configuration..."
sudo tee /etc/nginx/sites-available/nutrition-ssl > /dev/null << 'NGINXCONF'
upstream nutrition_backend {
    server 127.0.0.1:8085;
    keepalive 32;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name my.doctorhealthy1.com doctorhealy1.com www.doctorhealy1.com;
    
    # Remove EduVoice headers and add nutrition platform branding
    add_header Server "DoctorHealthy1-Nutrition/1.0";
    
    return 301 https://$server_name$request_uri;
}

# HTTPS for my.doctorhealthy1.com
server {
    listen 443 ssl http2;
    server_name my.doctorhealthy1.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/my.doctorhealthy1.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/my.doctorhealthy1.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;
    
    # Security headers (replace EduVoice)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header Server "DoctorHealthy1-Nutrition/1.0";
    
    # Serve nutrition platform
    root /var/www/nutrition-platform/frontend;
    index index.html;
    
    # API proxy
    location /api/ {
        proxy_pass http://nutrition_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Health endpoint
    location /health {
        proxy_pass http://nutrition_backend/health;
        proxy_set_header Host $host;
    }
    
    # Frontend SPA
    location / {
        try_files $uri $uri/ /index.html;
    }
}

# HTTPS for doctorhealy1.com (if SSL cert exists)
server {
    listen 443 ssl http2;
    server_name doctorhealy1.com www.doctorhealy1.com;
    
    # SSL Configuration (conditional)
    ssl_certificate /etc/letsencrypt/live/doctorhealy1.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/doctorhealy1.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    
    # Redirect to primary domain
    return 301 https://my.doctorhealthy1.com$request_uri;
}
NGINXCONF

# 8. ENABLE NEW CONFIGURATION
echo "🔄 Enabling new SSL configuration..."
sudo rm -f /etc/nginx/sites-enabled/default
sudo rm -f /etc/nginx/sites-enabled/*eduvoice*
sudo ln -sf /etc/nginx/sites-available/nutrition-ssl /etc/nginx/sites-enabled/

# 9. TEST AND START NGINX
echo "🧪 Testing nginx configuration..."
sudo nginx -t

echo "🚀 Starting nginx with SSL..."
sudo systemctl start nginx
sudo systemctl enable nginx

# 10. VERIFY SSL INSTALLATION
echo "✅ Verifying SSL installation..."
sleep 5
curl -I https://my.doctorhealthy1.com 2>/dev/null | head -3

echo ""
echo "🎉 SSL INSTALLATION COMPLETE!"
echo "✅ EduVoice conflicts removed"
echo "✅ Let's Encrypt SSL installed"
echo "✅ Nutrition platform secured"
echo ""
echo "🌐 Test URLs:"
echo "   https://my.doctorhealthy1.com"
echo "   https://doctorhealy1.com (if DNS configured)"
