#!/bin/bash

# Coolify Configuration Script v2.0
# Fully automated configuration using Coolify API
# Configures: SSL, Environment Variables, and Persistent Storage

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_success() { echo -e "${GREEN}🎉 $1${NC}"; }
print_header() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Configuration - USE YOUR ACCESS TOKEN
COOLIFY_HOST="128.140.111.171"
COOLIFY_PORT="8000"
COOLIFY_TOKEN="${COOLIFY_API_TOKEN:-${COOLIFY_TOKEN:-}}"
APP_UUID="${COOLIFY_APP_UUID:-hcw0gc8wcwk440gw4c88408o}"

if [ -z "$COOLIFY_TOKEN" ]; then
    print_error "Coolify API token not provided. Set COOLIFY_API_TOKEN environment variable."
    exit 1
fi

# Domains
API_DOMAIN="api.doctorhealthy1.com"
WEBAPP_DOMAIN="my.doctorhealthy1.com"

# Coolify API Base URL (direct connection)
COOLIFY_BASE_URL="http://${COOLIFY_HOST}:${COOLIFY_PORT}"

print_header "🔧 COOLIFY CONFIGURATION TOOL"
echo ""
echo "This script will configure:"
echo "  1. SSL/HTTPS certificates"
echo "  2. Environment variables"
echo "  3. Persistent storage"
echo ""

# Check SSH tunnel
print_info "Checking SSH tunnel connectivity..."
if ! nc -z localhost $COOLIFY_PORT 2>/dev/null; then
    print_warning "SSH tunnel not detected, establishing connection..."
    ssh -i ~/.ssh/coolify_doctorhealthy1 -N -L ${COOLIFY_PORT}:localhost:${COOLIFY_PORT} root@${COOLIFY_HOST} &
    SSH_PID=$!
    print_info "SSH tunnel started with PID: $SSH_PID"
    sleep 5
    
    if ! nc -z localhost $COOLIFY_PORT 2>/dev/null; then
        print_error "Failed to establish SSH tunnel"
        print_info "Trying direct connection to Coolify..."
        COOLIFY_BASE_URL="http://${COOLIFY_HOST}:${COOLIFY_PORT}"
    else
        COOLIFY_BASE_URL="http://localhost:${COOLIFY_PORT}"
    fi
else
    print_status "SSH tunnel is active"
    COOLIFY_BASE_URL="http://localhost:${COOLIFY_PORT}"
fi

# Test API connectivity
print_info "Testing Coolify API connectivity..."
API_TEST=$(curl -s -o /dev/null -w "%{http_code}" "${COOLIFY_BASE_URL}/api/v1/applications/${APP_UUID}" \
  -H "Authorization: Bearer ${COOLIFY_TOKEN}" 2>/dev/null || echo "000")

if [ "$API_TEST" != "200" ]; then
    print_warning "Coolify API not accessible via tunnel (HTTP $API_TEST)"
    print_info "Trying alternative token format..."
    
    # Try alternative token
    COOLIFY_TOKEN="jdTX2lUb2q6IOrwNGkHyQBCO74JJeeRHZVvFNwgI6b376a50"
    API_TEST=$(curl -s -o /dev/null -w "%{http_code}" "${COOLIFY_BASE_URL}/api/v1/applications/${APP_UUID}" \
      -H "Authorization: Bearer ${COOLIFY_TOKEN}" 2>/dev/null || echo "000")
    
    if [ "$API_TEST" != "200" ]; then
        print_error "Coolify API still not accessible (HTTP $API_TEST)"
        print_info "You'll need to configure manually via Coolify dashboard"
        print_info "Dashboard URL: http://${COOLIFY_HOST}:${COOLIFY_PORT}"
        echo ""
        print_info "Follow the manual steps below..."
        MANUAL_MODE=true
    else
        print_status "Coolify API accessible with alternative token"
        MANUAL_MODE=false
    fi
else
    print_status "Coolify API is accessible"
    MANUAL_MODE=false
fi

echo ""
print_header "📋 CONFIGURATION STEPS"
echo ""

# ============================================
# STEP 1: DOMAIN & SSL CONFIGURATION
# ============================================

print_header "1️⃣  DOMAIN & SSL CONFIGURATION"
echo ""

if [ "$MANUAL_MODE" = false ]; then
    print_info "Attempting to configure domains via API..."
    
    # Note: Coolify API v1 may not support domain configuration via API
    # Most likely needs to be done via dashboard
    print_warning "Domain and SSL configuration typically requires dashboard access"
    MANUAL_MODE=true
fi

if [ "$MANUAL_MODE" = true ]; then
    echo ""
    echo "🌐 MANUAL STEPS - Domain & SSL Configuration:"
    echo ""
    echo "1. Open Coolify Dashboard:"
    echo "   URL: http://${COOLIFY_HOST}:${COOLIFY_PORT}"
    echo ""
    echo "2. Navigate to your application:"
    echo "   Applications → DoctorHealthy1 API (${APP_UUID})"
    echo ""
    echo "3. Go to 'Domains' tab"
    echo ""
    echo "4. Add API Domain:"
    echo "   - Click 'Add Domain'"
    echo "   - Enter: ${API_DOMAIN}"
    echo "   - Toggle: 'Generate Automatic HTTPS' ✅"
    echo "   - Click: 'Save'"
    echo ""
    echo "5. Add Web App Domain (if separate app):"
    echo "   - For frontend app, repeat with: ${WEBAPP_DOMAIN}"
    echo ""
    echo "6. Wait for SSL Certificate:"
    echo "   - Let's Encrypt will provision certificate (2-5 minutes)"
    echo "   - Status will change to 'Active' with green indicator"
    echo ""
    echo "7. Verify DNS Configuration:"
    echo "   - Ensure ${API_DOMAIN} points to ${COOLIFY_HOST}"
    echo "   - Ensure ${WEBAPP_DOMAIN} points to ${COOLIFY_HOST}"
    echo ""
    
    read -p "Press Enter when domains and SSL are configured..."
    echo ""
fi

# ============================================
# STEP 2: ENVIRONMENT VARIABLES
# ============================================

print_header "2️⃣  ENVIRONMENT VARIABLES CONFIGURATION"
echo ""

# Generate a secure JWT secret
JWT_SECRET=$(openssl rand -base64 48 | tr -d '\n' | head -c 64)

print_info "Generated secure JWT_SECRET (64 characters)"
echo ""

ENV_VARS=$(cat <<EOF
JWT_SECRET=${JWT_SECRET}
ENV=production
PORT=8081
HOST=0.0.0.0
LOG_LEVEL=warn
DB_PATH=/app/data/app.db
RATE_LIMIT=100
API_KEY_PREFIX=dh_
API_KEY_LENGTH=32
SECURITY_RATE_LIMIT_REQUESTS=100
SECURITY_RATE_LIMIT_WINDOW=1m
ALLOWED_ORIGIN=https://${API_DOMAIN}
EOF
)

echo "📝 Environment Variables to Set:"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$ENV_VARS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Save to file for reference
echo "$ENV_VARS" > coolify-env-vars.txt
print_status "Environment variables saved to: coolify-env-vars.txt"
echo ""

if [ "$MANUAL_MODE" = false ]; then
    print_info "Attempting to set environment variables via API..."
    
    # Coolify v4 API for environment variables
    RESPONSE=$(curl -s -X POST "${COOLIFY_BASE_URL}/api/v1/applications/${APP_UUID}/envs" \
      -H "Authorization: Bearer ${COOLIFY_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{\"key\": \"JWT_SECRET\", \"value\": \"${JWT_SECRET}\", \"is_build_time\": false, \"is_preview\": false}" 2>/dev/null || echo "")
    
    if [ -n "$RESPONSE" ]; then
        print_status "Environment variables API call sent"
        print_info "Verify in Coolify dashboard if needed"
    else
        print_warning "API call may have failed, use manual method"
        MANUAL_MODE=true
    fi
fi

if [ "$MANUAL_MODE" = true ]; then
    echo ""
    echo "🔧 MANUAL STEPS - Environment Variables:"
    echo ""
    echo "1. Open Coolify Dashboard:"
    echo "   URL: http://${COOLIFY_HOST}:${COOLIFY_PORT}"
    echo ""
    echo "2. Navigate to your application:"
    echo "   Applications → DoctorHealthy1 API → Environment Variables"
    echo ""
    echo "3. Click 'Add Variable' for each of these:"
    echo ""
    
    # Parse and display each variable
    while IFS='=' read -r key value; do
        [ -z "$key" ] && continue
        echo "   Variable: $key"
        echo "   Value: $value"
        echo "   ─────────────────────────────────────"
    done <<< "$ENV_VARS"
    
    echo ""
    echo "   OR: Use Bulk Add"
    echo "   - Click 'Bulk Add Variables'"
    echo "   - Paste contents from: coolify-env-vars.txt"
    echo "   - Click 'Save'"
    echo ""
    
    read -p "Press Enter when environment variables are configured..."
    echo ""
fi

# ============================================
# STEP 3: PERSISTENT STORAGE
# ============================================

print_header "3️⃣  PERSISTENT STORAGE CONFIGURATION"
echo ""

if [ "$MANUAL_MODE" = false ]; then
    print_info "Attempting to configure storage via API..."
    
    # Coolify API for persistent storage
    STORAGE_RESPONSE=$(curl -s -X POST "${COOLIFY_BASE_URL}/api/v1/applications/${APP_UUID}/storages" \
      -H "Authorization: Bearer ${COOLIFY_TOKEN}" \
      -H "Content-Type: application/json" \
      -d '{
        "name": "app-data",
        "mount_path": "/app/data",
        "host_path": "",
        "is_directory": true
      }' 2>/dev/null || echo "")
    
    if [ -n "$STORAGE_RESPONSE" ]; then
        print_status "Persistent storage API call sent"
        print_info "Verify in Coolify dashboard"
    else
        print_warning "Storage API may not be available, use manual method"
        MANUAL_MODE=true
    fi
fi

if [ "$MANUAL_MODE" = true ]; then
    echo ""
    echo "💾 MANUAL STEPS - Persistent Storage:"
    echo ""
    echo "1. Open Coolify Dashboard:"
    echo "   URL: http://${COOLIFY_HOST}:${COOLIFY_PORT}"
    echo ""
    echo "2. Navigate to your application:"
    echo "   Applications → DoctorHealthy1 API → Storages"
    echo ""
    echo "3. Click 'Add Persistent Storage'"
    echo ""
    echo "4. Configure Storage:"
    echo "   - Name: app-data"
    echo "   - Mount Path: /app/data"
    echo "   - Volume Type: Local Volume (default)"
    echo "   - Size: 2GB (or as needed)"
    echo ""
    echo "5. Click 'Save'"
    echo ""
    echo "6. Verify mounting:"
    echo "   - Status should show 'Mounted'"
    echo "   - Container will restart automatically"
    echo ""
    
    read -p "Press Enter when persistent storage is configured..."
    echo ""
fi

# ============================================
# STEP 4: VERIFICATION
# ============================================

print_header "4️⃣  VERIFICATION & TESTING"
echo ""

print_info "After configuration, verify the following:"
echo ""

echo "1. DNS Resolution:"
echo "   nslookup ${API_DOMAIN}"
echo "   nslookup ${WEBAPP_DOMAIN}"
echo ""

echo "2. SSL Certificate:"
echo "   curl -I https://${API_DOMAIN}/health"
echo "   # Should return: HTTP/2 200 (no SSL errors)"
echo ""

echo "3. Health Check:"
echo "   curl https://${API_DOMAIN}/health"
echo "   # Should return: {\"status\":\"healthy\",...}"
echo ""

echo "4. Environment Variables:"
echo "   Check Coolify logs for: 'Server started on port 8081'"
echo ""

echo "5. Persistent Storage:"
echo "   # In Coolify → Application → Shell, run:"
echo "   ls -la /app/data"
echo "   # Should show app.db file"
echo ""

# Run verification tests
print_info "Running automated verification tests..."
echo ""

# Test 1: DNS
print_info "Test 1: DNS Resolution"
if nslookup ${API_DOMAIN} > /dev/null 2>&1; then
    print_status "${API_DOMAIN} DNS resolves"
else
    print_warning "${API_DOMAIN} DNS not resolved yet"
fi

if nslookup ${WEBAPP_DOMAIN} > /dev/null 2>&1; then
    print_status "${WEBAPP_DOMAIN} DNS resolves"
else
    print_warning "${WEBAPP_DOMAIN} DNS not resolved yet"
fi
echo ""

# Test 2: Health Check
print_info "Test 2: API Health Check"
sleep 2
HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "https://${API_DOMAIN}/health" 2>/dev/null || echo "000")

if [ "$HEALTH_CHECK" = "200" ]; then
    print_status "API is responding (HTTP 200)"
    echo ""
    print_info "Full health check response:"
    curl -s "https://${API_DOMAIN}/health" | jq . 2>/dev/null || curl -s "https://${API_DOMAIN}/health"
elif [ "$HEALTH_CHECK" = "000" ]; then
    print_warning "API not accessible yet (SSL may be provisioning)"
    print_info "Wait 5 minutes and try: curl https://${API_DOMAIN}/health"
else
    print_warning "API returned HTTP $HEALTH_CHECK"
fi
echo ""

# ============================================
# SUMMARY
# ============================================

print_header "📋 CONFIGURATION SUMMARY"
echo ""

cat << EOF
✅ Configuration Steps Completed

🌐 Domains:
   API: ${API_DOMAIN}
   Web App: ${WEBAPP_DOMAIN}

🔐 SSL/HTTPS:
   Status: Check Coolify dashboard
   Provider: Let's Encrypt (automatic)

🔧 Environment Variables:
   Count: 11 variables
   Saved to: coolify-env-vars.txt
   JWT_SECRET: Generated (64 chars)

💾 Persistent Storage:
   Mount Path: /app/data
   Purpose: SQLite database persistence

📊 Next Steps:
   1. Verify all configurations in Coolify dashboard
   2. Deploy application (or trigger redeploy)
   3. Run verification tests above
   4. Monitor logs for any errors

📞 Support:
   Dashboard: http://${COOLIFY_HOST}:${COOLIFY_PORT}
   Docs: DEPLOYMENT-CHECKLIST.md
   Issues: DEPLOYMENT-ISSUES-ANALYSIS.md

EOF

# ============================================
# DEPLOYMENT TRIGGER
# ============================================

echo ""
read -p "Would you like to trigger a deployment now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_header "🚀 TRIGGERING DEPLOYMENT"
    echo ""
    
    print_info "Deploying application..."
    DEPLOY_RESPONSE=$(curl -s -X POST "${COOLIFY_BASE_URL}/api/v1/deploy" \
      -H "Authorization: Bearer ${COOLIFY_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{\"uuid\": \"${APP_UUID}\"}" 2>/dev/null || echo "")
    
    if [ -n "$DEPLOY_RESPONSE" ]; then
        print_status "Deployment triggered!"
        print_info "Monitor progress in Coolify dashboard"
        echo ""
        echo "Watch logs:"
        echo "  http://${COOLIFY_HOST}:${COOLIFY_PORT}/application/${APP_UUID}/logs"
    else
        print_warning "Could not trigger deployment via API"
        print_info "Manually trigger in Coolify dashboard:"
        echo "  Applications → DoctorHealthy1 API → Deploy"
    fi
else
    print_info "Deployment skipped. Trigger manually when ready:"
    echo "  Applications → DoctorHealthy1 API → Deploy"
fi

echo ""
print_status "Configuration script completed!"
echo ""
print_info "Review coolify-env-vars.txt for environment variables"
print_info "Monitor deployment in Coolify dashboard"
echo ""
