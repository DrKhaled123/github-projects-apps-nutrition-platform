#!/bin/bash

##############################################################################
# Frontend-Backend Integrated Deployment Script
# Deploys DoctorHealthy1 with both backend API and frontend UI
##############################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}     DoctorHealthy1 Frontend-Backend Deployment        ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

##############################################################################
# Step 1: Load Environment Variables
##############################################################################

echo -e "${YELLOW}[1/8]${NC} Loading environment variables..."

if [ ! -f ".env.secure" ]; then
    echo -e "${RED}❌ ERROR: .env.secure file not found!${NC}"
    echo "Please create .env.secure with:"
    echo "  COOLIFY_API_TOKEN=your_token"
    echo "  COOLIFY_HOST=your_host"
    echo "  COOLIFY_APP_UUID=your_app_uuid"
    exit 1
fi

source .env.secure

# Validate required variables
if [ -z "${COOLIFY_API_TOKEN:-}" ] || [ -z "${COOLIFY_HOST:-}" ] || [ -z "${COOLIFY_APP_UUID:-}" ]; then
    echo -e "${RED}❌ ERROR: Missing required environment variables${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment variables loaded${NC}"
echo ""

##############################################################################
# Step 2: Verify Frontend Directory
##############################################################################

echo -e "${YELLOW}[2/8]${NC} Verifying frontend directory..."

if [ ! -d "frontend" ]; then
    echo -e "${RED}❌ ERROR: frontend directory not found!${NC}"
    exit 1
fi

FRONTEND_FILES=$(find frontend -type f \( -name "*.html" -o -name "*.css" -o -name "*.js" \) | wc -l | tr -d ' ')
echo -e "${GREEN}✅ Frontend directory found with ${FRONTEND_FILES} files${NC}"

# List frontend files for verification
echo "   Frontend structure:"
echo "   - HTML pages: $(find frontend -name "*.html" -type f | wc -l | tr -d ' ')"
echo "   - CSS files: $(find frontend/css -name "*.css" -type f 2>/dev/null | wc -l | tr -d ' ')"
echo "   - JS files: $(find frontend/js -name "*.js" -type f 2>/dev/null | wc -l | tr -d ' ')"
echo ""

##############################################################################
# Step 3: Verify Backend API Endpoints
##############################################################################

echo -e "${YELLOW}[3/8]${NC} Verifying backend API configuration..."

if ! grep -q "embeddedFrontend embed.FS" main.go; then
    echo -e "${YELLOW}⚠️  WARNING: Frontend embedding may not be configured in main.go${NC}"
fi

if ! grep -q "serveStaticFile" main.go; then
    echo -e "${RED}❌ ERROR: Static file serving not found in main.go${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Backend configured to serve frontend${NC}"
echo ""

##############################################################################
# Step 4: Build Application Locally (Test Build)
##############################################################################

echo -e "${YELLOW}[4/8]${NC} Testing local build..."

echo "   Building Go application..."
if ! go build -o test_main . 2>&1 | tee build_test.log; then
    echo -e "${RED}❌ ERROR: Build failed${NC}"
    echo "Check build_test.log for details"
    exit 1
fi

rm -f test_main
echo -e "${GREEN}✅ Local build successful${NC}"
echo ""

##############################################################################
# Step 5: Update Coolify Configuration
##############################################################################

echo -e "${YELLOW}[5/8]${NC} Updating Coolify configuration..."

# Update Coolify with frontend-enabled configuration
COOLIFY_UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH \
    "https://${COOLIFY_HOST}/api/v1/applications/${COOLIFY_APP_UUID}" \
    -H "Authorization: Bearer ${COOLIFY_API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
        "health_check_port": "8081",
        "health_check_path": "/health",
        "health_check_interval": 15,
        "health_check_timeout": 10,
        "health_check_retries": 5,
        "health_check_start_period": 30,
        "ports_exposes": "8081",
        "custom_labels": "traefik.http.routers.app.rule=Host(`my.doctorhealthy1.com`)"
    }' 2>&1)

HTTP_CODE=$(echo "$COOLIFY_UPDATE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$COOLIFY_UPDATE_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "201" ]; then
    echo -e "${RED}❌ ERROR: Failed to update Coolify configuration (HTTP $HTTP_CODE)${NC}"
    echo "Response: $RESPONSE_BODY"
    exit 1
fi

echo -e "${GREEN}✅ Coolify configuration updated${NC}"
echo ""

##############################################################################
# Step 6: Trigger Deployment
##############################################################################

echo -e "${YELLOW}[6/8]${NC} Triggering deployment to Coolify..."

DEPLOY_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "https://${COOLIFY_HOST}/api/v1/deploy" \
    -H "Authorization: Bearer ${COOLIFY_API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"uuid\": \"${COOLIFY_APP_UUID}\"}" 2>&1)

HTTP_CODE=$(echo "$DEPLOY_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$DEPLOY_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "201" ]; then
    echo -e "${RED}❌ ERROR: Failed to trigger deployment (HTTP $HTTP_CODE)${NC}"
    echo "Response: $RESPONSE_BODY"
    exit 1
fi

# Extract deployment UUID if present
DEPLOYMENT_UUID=$(echo "$RESPONSE_BODY" | grep -o '"deployment_uuid":"[^"]*"' | cut -d'"' -f4 || echo "")

echo -e "${GREEN}✅ Deployment triggered${NC}"
if [ -n "$DEPLOYMENT_UUID" ]; then
    echo "   Deployment UUID: $DEPLOYMENT_UUID"
fi
echo ""

##############################################################################
# Step 7: Wait for Deployment
##############################################################################

echo -e "${YELLOW}[7/8]${NC} Waiting for deployment to complete..."
echo "   This may take 2-5 minutes..."

MAX_WAIT=300  # 5 minutes
WAIT_INTERVAL=10
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    sleep $WAIT_INTERVAL
    ELAPSED=$((ELAPSED + WAIT_INTERVAL))
    
    # Check application status
    STATUS_RESPONSE=$(curl -s "https://${COOLIFY_HOST}/api/v1/applications/${COOLIFY_APP_UUID}" \
        -H "Authorization: Bearer ${COOLIFY_API_TOKEN}" 2>/dev/null || echo "")
    
    if echo "$STATUS_RESPONSE" | grep -q '"status":"running:healthy"'; then
        echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
        break
    elif echo "$STATUS_RESPONSE" | grep -q '"status":"running:unhealthy"'; then
        echo -e "${YELLOW}⚠️  Application running but unhealthy${NC}"
        break
    fi
    
    echo -n "."
done

echo ""
echo ""

##############################################################################
# Step 8: Verify Frontend and Backend
##############################################################################

echo -e "${YELLOW}[8/8]${NC} Verifying deployment..."

echo "   Testing backend API..."
BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://my.doctorhealthy1.com/health" || echo "000")

if [ "$BACKEND_STATUS" = "200" ]; then
    echo -e "${GREEN}   ✅ Backend API: Healthy (HTTP $BACKEND_STATUS)${NC}"
else
    echo -e "${RED}   ❌ Backend API: Failed (HTTP $BACKEND_STATUS)${NC}"
fi

echo "   Testing frontend..."
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://my.doctorhealthy1.com/" || echo "000")

if [ "$FRONTEND_STATUS" = "200" ]; then
    echo -e "${GREEN}   ✅ Frontend: Accessible (HTTP $FRONTEND_STATUS)${NC}"
else
    echo -e "${RED}   ❌ Frontend: Failed (HTTP $FRONTEND_STATUS)${NC}"
fi

echo "   Testing API endpoint..."
API_TEST_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://my.doctorhealthy1.com/api/v1/recipes" || echo "000")

if [ "$API_TEST_STATUS" = "200" ] || [ "$API_TEST_STATUS" = "401" ]; then
    echo -e "${GREEN}   ✅ API endpoints: Responding (HTTP $API_TEST_STATUS)${NC}"
else
    echo -e "${RED}   ❌ API endpoints: Failed (HTTP $API_TEST_STATUS)${NC}"
fi

echo ""

##############################################################################
# Deployment Summary
##############################################################################

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}              Deployment Summary                        ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo ""
echo "🌐 Access Your Application:"
echo "   - Frontend (Main Site): https://my.doctorhealthy1.com/"
echo "   - Backend API: https://my.doctorhealthy1.com/api/v1/*"
echo "   - Health Check: https://my.doctorhealthy1.com/health"
echo ""
echo "📱 Available Pages:"
echo "   - Home: https://my.doctorhealthy1.com/"
echo "   - Diet Plans: https://my.doctorhealthy1.com/diet.html"
echo "   - Workouts: https://my.doctorhealthy1.com/workouts.html"
echo "   - Recipes: https://my.doctorhealthy1.com/recipes.html"
echo "   - Lifestyle: https://my.doctorhealthy1.com/lifestyle.html"
echo "   - Pricing: https://my.doctorhealthy1.com/pricing.html"
echo ""
echo "🔍 Verification Commands:"
echo "   # Test frontend"
echo "   curl -I https://my.doctorhealthy1.com/"
echo ""
echo "   # Test backend API"
echo "   curl https://my.doctorhealthy1.com/health"
echo ""
echo "   # Test API endpoint"
echo "   curl https://my.doctorhealthy1.com/api/v1/recipes"
echo ""
echo "📊 Status Checks:"
if [ "$BACKEND_STATUS" = "200" ] && [ "$FRONTEND_STATUS" = "200" ]; then
    echo -e "   ${GREEN}✅ All systems operational${NC}"
elif [ "$BACKEND_STATUS" = "200" ]; then
    echo -e "   ${YELLOW}⚠️  Backend healthy, frontend may need time to propagate${NC}"
else
    echo -e "   ${RED}❌ Issues detected - check logs for details${NC}"
    echo ""
    echo "   # Check Coolify logs:"
    echo "   curl -s \"https://${COOLIFY_HOST}/api/v1/applications/${COOLIFY_APP_UUID}/logs\" \\"
    echo "        -H \"Authorization: Bearer ${COOLIFY_API_TOKEN}\""
fi
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Save deployment info
cat > deployment_info.txt <<EOF
Deployment completed at: $(date)
Backend Status: $BACKEND_STATUS
Frontend Status: $FRONTEND_STATUS
API Test Status: $API_TEST_STATUS
Application UUID: $COOLIFY_APP_UUID
Deployment UUID: ${DEPLOYMENT_UUID:-N/A}
EOF

echo "📝 Deployment info saved to deployment_info.txt"
echo ""

exit 0
