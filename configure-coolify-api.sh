#!/bin/bash

# Coolify API Configuration Script v2.0
# Fully automated configuration using Coolify API v1
# Token: 4|jdTX2lUb2q6IOrwNGkHyQBCO74JJeeRHZVvFNwgI6b376a50

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_success() { echo -e "${GREEN}🎉 $1${NC}"; }
print_step() { echo -e "${MAGENTA}▶ $1${NC}"; }
print_header() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Configuration
COOLIFY_HOST="128.140.111.171"
COOLIFY_PORT="8000"
COOLIFY_TOKEN="${COOLIFY_API_TOKEN:-${COOLIFY_TOKEN:-}}"
APP_UUID="${COOLIFY_APP_UUID:-hcw0gc8wcwk440gw4c88408o}"

if [ -z "$COOLIFY_TOKEN" ]; then
    print_error "Coolify API token not provided. Set COOLIFY_API_TOKEN environment variable."
    exit 1
fi

# Domains
API_DOMAIN="my.doctorhealthy1.com"
WEBAPP_DOMAIN="my.doctorhealthy1.com"

# Coolify API Base URL
COOLIFY_BASE_URL="http://${COOLIFY_HOST}:${COOLIFY_PORT}/api/v1"

# Headers
AUTH_HEADER="Authorization: Bearer ${COOLIFY_TOKEN}"
CONTENT_TYPE="Content-Type: application/json"

print_header "🚀 COOLIFY AUTOMATED CONFIGURATION"
echo ""
echo "Configuration:"
echo "  Host: ${COOLIFY_HOST}:${COOLIFY_PORT}"
echo "  Application: ${APP_UUID}"
echo "  API Domain: ${API_DOMAIN}"
echo "  Web Domain: ${WEBAPP_DOMAIN}"
echo ""

# ============================================
# Test API Connection
# ============================================
print_header "🔌 TESTING API CONNECTION"
echo ""
print_step "Testing Coolify API v1..."

API_RESPONSE=$(curl -s -w "\n%{http_code}" "${COOLIFY_BASE_URL}/applications/${APP_UUID}" \
  -H "${AUTH_HEADER}" 2>/dev/null || echo -e "\n000")

HTTP_CODE=$(echo "$API_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$API_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    print_status "API connection successful!"
    echo "Application found: $(echo $RESPONSE_BODY | grep -o '"name":"[^"]*"' | cut -d'"' -f4)"
else
    print_error "API connection failed (HTTP $HTTP_CODE)"
    echo "Response: $RESPONSE_BODY"
    echo ""
    print_warning "Possible issues:"
    echo "  - Token might be invalid or expired"
    echo "  - Application UUID might be incorrect"
    echo "  - Coolify API might not be accessible"
    echo ""
    echo "Please configure manually via dashboard:"
    echo "  http://${COOLIFY_HOST}:${COOLIFY_PORT}"
    exit 1
fi

echo ""

# ============================================
# Generate JWT Secret
# ============================================
print_header "🔐 GENERATING SECURE JWT SECRET"
echo ""

JWT_SECRET=$(openssl rand -base64 48 | tr -d '\n' | head -c 64)
print_status "Generated 64-character JWT_SECRET"
echo ""

# ============================================
# Configure Environment Variables
# ============================================
print_header "🔧 CONFIGURING ENVIRONMENT VARIABLES"
echo ""

# Create environment variables array
ENV_VARS=(
    "JWT_SECRET=${JWT_SECRET}"
    "ENV=production"
    "PORT=8081"
    "HOST=0.0.0.0"
    "LOG_LEVEL=warn"
    "DB_PATH=/app/data/app.db"
    "RATE_LIMIT=100"
    "API_KEY_PREFIX=dh_"
    "API_KEY_LENGTH=32"
    "SECURITY_RATE_LIMIT_REQUESTS=100"
    "SECURITY_RATE_LIMIT_WINDOW=1m"
    "ALLOWED_ORIGIN=https://${API_DOMAIN}"
)

# Save to file
ENV_FILE="coolify-env-vars.txt"
echo "# Coolify Environment Variables" > $ENV_FILE
echo "# Generated: $(date)" >> $ENV_FILE
echo "# Application: ${APP_UUID}" >> $ENV_FILE
echo "" >> $ENV_FILE

for env_var in "${ENV_VARS[@]}"; do
    echo "$env_var" >> $ENV_FILE
done

print_status "Environment variables saved to: $ENV_FILE"
echo ""

# Try to set environment variables via API
print_step "Setting environment variables via API..."
echo ""

ENV_SUCCESS=0
ENV_FAILED=0

for env_var in "${ENV_VARS[@]}"; do
    VAR_NAME=$(echo "$env_var" | cut -d'=' -f1)
    VAR_VALUE=$(echo "$env_var" | cut -d'=' -f2-)
    
    print_info "Setting: $VAR_NAME"
    
    # Coolify API v1 endpoint for environment variables
    # POST /api/v1/applications/{uuid}/envs
    ENV_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
        "${COOLIFY_BASE_URL}/applications/${APP_UUID}/envs" \
        -H "${AUTH_HEADER}" \
        -H "${CONTENT_TYPE}" \
        -d "{\"key\":\"${VAR_NAME}\",\"value\":\"${VAR_VALUE}\",\"is_build_time\":false,\"is_preview\":false}" \
        2>/dev/null || echo -e "\n000")
    
    ENV_HTTP_CODE=$(echo "$ENV_RESPONSE" | tail -n1)
    
    if [ "$ENV_HTTP_CODE" = "200" ] || [ "$ENV_HTTP_CODE" = "201" ]; then
        echo -e "  ${GREEN}✓ Set successfully${NC}"
        ((ENV_SUCCESS++))
    else
        echo -e "  ${YELLOW}⚠ API method not available (HTTP $ENV_HTTP_CODE)${NC}"
        ((ENV_FAILED++))
    fi
done

echo ""
if [ $ENV_SUCCESS -gt 0 ]; then
    print_status "Successfully set $ENV_SUCCESS environment variable(s) via API"
fi

if [ $ENV_FAILED -gt 0 ]; then
    print_warning "$ENV_FAILED environment variable(s) need manual configuration"
    echo ""
    echo "Manual configuration:"
    echo "  1. Open: http://${COOLIFY_HOST}:${COOLIFY_PORT}"
    echo "  2. Go to: Applications → Your App → Environment Variables"
    echo "  3. Click: 'Bulk Add' or 'Add Variable'"
    echo "  4. Copy from: $ENV_FILE"
fi

echo ""

# ============================================
# Configure Domain and SSL
# ============================================
print_header "🌐 CONFIGURING DOMAIN & SSL"
echo ""

print_step "Configuring domain: ${API_DOMAIN}"

# Coolify API v1 endpoint for domains
# PATCH /api/v1/applications/{uuid}
DOMAIN_PAYLOAD=$(cat <<EOF
{
  "fqdn": "${API_DOMAIN}",
  "is_static": false,
  "ports_exposes": "8081"
}
EOF
)

DOMAIN_RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH \
    "${COOLIFY_BASE_URL}/applications/${APP_UUID}" \
    -H "${AUTH_HEADER}" \
    -H "${CONTENT_TYPE}" \
    -d "${DOMAIN_PAYLOAD}" \
    2>/dev/null || echo -e "\n000")

DOMAIN_HTTP_CODE=$(echo "$DOMAIN_RESPONSE" | tail -n1)

if [ "$DOMAIN_HTTP_CODE" = "200" ] || [ "$DOMAIN_HTTP_CODE" = "201" ]; then
    print_status "Domain configured successfully"
    print_info "SSL certificates will be provisioned automatically by Let's Encrypt"
    print_info "This may take 2-5 minutes..."
else
    print_warning "Domain configuration via API not available (HTTP $DOMAIN_HTTP_CODE)"
    echo ""
    echo "Manual configuration:"
    echo "  1. Open: http://${COOLIFY_HOST}:${COOLIFY_PORT}"
    echo "  2. Go to: Applications → Your App → Domains"
    echo "  3. Add domain: ${API_DOMAIN}"
    echo "  4. Enable: 'Generate Automatic HTTPS' ✅"
    echo "  5. Save and wait for SSL provisioning (2-5 minutes)"
fi

echo ""

# ============================================
# Configure Persistent Storage
# ============================================
print_header "💾 CONFIGURING PERSISTENT STORAGE"
echo ""

print_step "Creating persistent storage volume..."

# Coolify API v1 endpoint for storage
# POST /api/v1/applications/{uuid}/storages
STORAGE_PAYLOAD=$(cat <<EOF
{
  "name": "app-data",
  "mount_path": "/app/data",
  "host_path": ""
}
EOF
)

STORAGE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "${COOLIFY_BASE_URL}/applications/${APP_UUID}/storages" \
    -H "${AUTH_HEADER}" \
    -H "${CONTENT_TYPE}" \
    -d "${STORAGE_PAYLOAD}" \
    2>/dev/null || echo -e "\n000")

STORAGE_HTTP_CODE=$(echo "$STORAGE_RESPONSE" | tail -n1)

if [ "$STORAGE_HTTP_CODE" = "200" ] || [ "$STORAGE_HTTP_CODE" = "201" ]; then
    print_status "Persistent storage configured successfully"
    print_info "Mount path: /app/data"
    print_info "Database will persist across deployments"
else
    print_warning "Storage configuration via API not available (HTTP $STORAGE_HTTP_CODE)"
    echo ""
    echo "Manual configuration:"
    echo "  1. Open: http://${COOLIFY_HOST}:${COOLIFY_PORT}"
    echo "  2. Go to: Applications → Your App → Storages"
    echo "  3. Click: 'Add Persistent Storage'"
    echo "  4. Configure:"
    echo "     - Name: app-data"
    echo "     - Mount Path: /app/data"
    echo "     - Size: 2GB"
    echo "  5. Save (container will restart)"
fi

echo ""

# ============================================
# Deploy Application
# ============================================
print_header "🚀 DEPLOYING APPLICATION"
echo ""

read -p "Trigger deployment now? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_step "Triggering deployment..."
    
    # Coolify API v1 endpoint for deployment
    # POST /api/v1/applications/{uuid}/deploy
    DEPLOY_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
        "${COOLIFY_BASE_URL}/applications/${APP_UUID}/deploy" \
        -H "${AUTH_HEADER}" \
        2>/dev/null || echo -e "\n000")
    
    DEPLOY_HTTP_CODE=$(echo "$DEPLOY_RESPONSE" | tail -n1)
    
    if [ "$DEPLOY_HTTP_CODE" = "200" ] || [ "$DEPLOY_HTTP_CODE" = "201" ]; then
        print_status "Deployment triggered successfully!"
        print_info "Monitor progress in Coolify dashboard"
        echo ""
        echo "Watch logs:"
        echo "  http://${COOLIFY_HOST}:${COOLIFY_PORT}/application/${APP_UUID}/logs"
    else
        print_warning "Deployment trigger via API not available (HTTP $DEPLOY_HTTP_CODE)"
        echo ""
        echo "Manual deployment:"
        echo "  1. Open: http://${COOLIFY_HOST}:${COOLIFY_PORT}"
        echo "  2. Go to: Applications → Your App"
        echo "  3. Click: 'Deploy' button"
    fi
else
    print_info "Deployment skipped"
    echo ""
    echo "Deploy manually when ready:"
    echo "  http://${COOLIFY_HOST}:${COOLIFY_PORT}/application/${APP_UUID}"
fi

echo ""

# ============================================
# Verification Tests
# ============================================
print_header "✅ VERIFICATION TESTS"
echo ""

print_step "Test 1: DNS Resolution"
if nslookup ${API_DOMAIN} > /dev/null 2>&1; then
    print_status "${API_DOMAIN} DNS resolves"
    IP=$(nslookup ${API_DOMAIN} | grep "Address:" | tail -n1 | awk '{print $2}')
    echo "  Resolved to: $IP"
else
    print_warning "${API_DOMAIN} DNS not resolving yet"
    echo "  Add A record: ${API_DOMAIN} → ${COOLIFY_HOST}"
fi

echo ""

print_step "Test 2: SSL Certificate (after deployment)"
echo "  Run this after deployment completes (2-5 minutes):"
echo "  curl -I https://${API_DOMAIN}/health"
echo ""

print_step "Test 3: Health Check (after deployment)"
echo "  Run this to verify application is running:"
echo "  curl https://${API_DOMAIN}/health"
echo ""

# ============================================
# Summary
# ============================================
print_header "📋 CONFIGURATION SUMMARY"
echo ""

print_success "Configuration completed!"
echo ""

echo "🌐 Domain Configuration:"
echo "   API Domain: ${API_DOMAIN}"
echo "   SSL: Let's Encrypt (automatic)"
echo "   Status: Check dashboard for SSL provisioning"
echo ""

echo "🔧 Environment Variables:"
echo "   Count: ${#ENV_VARS[@]} variables"
echo "   File: $ENV_FILE"
echo "   JWT_SECRET: ✓ Generated (64 chars)"
if [ $ENV_SUCCESS -gt 0 ]; then
    echo "   API: ✓ $ENV_SUCCESS set successfully"
fi
if [ $ENV_FAILED -gt 0 ]; then
    echo "   Manual: ⚠ $ENV_FAILED need manual configuration"
fi
echo ""

echo "💾 Persistent Storage:"
echo "   Mount Path: /app/data"
echo "   Purpose: SQLite database persistence"
echo "   Status: Check dashboard for mount status"
echo ""

echo "📊 Next Steps:"
echo "   1. Verify DNS: nslookup ${API_DOMAIN}"
echo "   2. Wait for SSL (2-5 minutes)"
echo "   3. Monitor deployment logs"
echo "   4. Test health endpoint"
echo "   5. Verify application functionality"
echo ""

echo "📞 Resources:"
echo "   Dashboard: http://${COOLIFY_HOST}:${COOLIFY_PORT}"
echo "   App Logs: http://${COOLIFY_HOST}:${COOLIFY_PORT}/application/${APP_UUID}/logs"
echo "   Env Vars: $ENV_FILE"
echo "   Docs: COOLIFY-SETUP-GUIDE.md"
echo ""

print_success "🎉 All done! Monitor your deployment in the Coolify dashboard."
echo ""
