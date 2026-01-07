#!/bin/bash

# DoctorHealthy1 Direct API Deployment Script - SECURE & PRODUCTION READY
# Uses direct HTTP API calls without SSH tunneling for better security

set -e  # Exit on any error

echo "🚀 Starting Direct API deployment to Coolify..."

# Load secure environment variables
if [ ! -f ".env.secure" ]; then
    echo "❌ .env.secure file not found"
    exit 1
fi

source .env.secure

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Test API connectivity directly
print_info "Testing Coolify API connectivity..."
API_TEST=$(curl -s -o /dev/null -w "%{http_code}" "https://api.doctorhealthy1.com/api/v1/applications/${COOLIFY_APP_UUID}" \
  -H "Authorization: Bearer ${COOLIFY_API_TOKEN}")

if [ "$API_TEST" != "200" ]; then
    print_error "Coolify API not accessible (HTTP $API_TEST)"
    echo "🔧 Troubleshooting steps:"
    echo "   1. Check if token is valid"
    echo "   2. Verify Coolify server is running"
    echo "   3. Confirm application UUID is correct"
    exit 1
fi

print_status "Coolify API is accessible"

# Trigger deployment via direct API call
print_header "🏗️ TRIGGERING DEPLOYMENT"

print_info "Initiating deployment request..."
DEPLOY_RESPONSE=$(curl -s -X POST "https://api.doctorhealthy1.com/api/v1/deploy" \
  -H "Authorization: Bearer ${COOLIFY_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"uuid\": \"${COOLIFY_APP_UUID}\"}")

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
    STATUS_RESPONSE=$(curl -s -X GET "https://api.doctorhealthy1.com/api/v1/deployments/${DEPLOYMENT_UUID}" \
      -H "Authorization: Bearer ${COOLIFY_API_TOKEN}")

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
sleep 5

APP_RESPONSE=$(curl -s -X GET "https://api.doctorhealthy1.com/api/v1/applications/${COOLIFY_APP_UUID}" \
  -H "Authorization: Bearer ${COOLIFY_API_TOKEN}")

APP_STATUS=$(echo $APP_RESPONSE | grep -o '"status":"[^"]*' | sed 's/"status":"//')
LAST_ONLINE=$(echo $APP_RESPONSE | grep -o '"last_online_at":"[^"]*' | sed 's/"last_online_at":"//')

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

# Test actual endpoints
print_header "🔗 ENDPOINT TESTING"

print_info "Testing application endpoints..."
ENDPOINT_STATUS=0

# Test health endpoint
if curl -f -s "https://my.doctorhealthy1.com/health" > /dev/null; then
    print_status "Health endpoint: ✅ Responding"
else
    print_warning "Health endpoint: ❌ Not responding"
    ENDPOINT_STATUS=1
fi

# Test main application
if curl -f -s -I "https://my.doctorhealthy1.com/" > /dev/null; then
    print_status "Main application: ✅ Responding"
else
    print_warning "Main application: ❌ Not responding"
    ENDPOINT_STATUS=1
fi

# Deployment summary
print_header "📋 DEPLOYMENT SUMMARY"

echo ""
echo "🎯 Application Details:"
echo "   Name: DoctorHealthy1 API"
echo "   Status: $APP_STATUS"
echo "   Last Online: $LAST_ONLINE"
echo "   Platform: Coolify (Direct API)"
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
echo "   Production URL: https://my.doctorhealthy1.com"
echo "   Health Check: https://my.doctorhealthy1.com/health"
echo "   API Endpoints: https://my.doctorhealthy1.com/api/v1/*"
echo ""

if [[ $APP_STATUS == *"healthy"* && $ENDPOINT_STATUS -eq 0 ]]; then
    print_status "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!"
    print_info "Your DoctorHealthy1 API is now running in production!"
    echo ""
    echo "📊 Quick Stats:"
    echo "   ⏱️  Total deployment time: ${CURRENT_TIME}s"
    echo "   🏥 Health status: Healthy"
    echo "   🌐 HTTPS: Configured"
    echo "   🔒 SSL: Active"
    exit 0
else
    print_warning "Deployment completed but application needs attention"
    print_info "Check endpoints and Coolify dashboard for detailed status"
    exit 1
fi