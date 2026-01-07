#!/bin/bash

# ==================================================
# DoctorHealthy - Coolify API Test Script
# Test Coolify API connectivity and functionality
# ==================================================

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
COOLIFY_API_URL="http://128.140.111.171:8000"
COOLIFY_API_TOKEN="7|Pc76Go9w1ELoKy0GBYb2RpMxWWujefpjEKM30R3Obef9679a"
SERVER_IP="128.140.111.171"

echo "${BLUE}🚀 DoctorHealthy - Coolify API Test${NC}"
echo "================================================"
echo "Coolify API URL: $COOLIFY_API_URL"
echo "Server IP: $SERVER_IP"
echo ""

# Logging
LOG_FILE="/tmp/coolify-test-$(date +%Y%m%d-%H%M%S).log"

# Utility functions
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}" | tee -a "$LOG_FILE"
}

check_coolify_connection() {
    log_info "Checking Coolify API connection..."
    
    local response=$(curl -s -w "%{http_code}" \
        -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
        -H "Content-Type: application/json" \
        "$COOLIFY_API_URL/api/user" 2>/dev/null)
    
    local http_code="${response: -3}"
    local body="${response%???}"
    
    if [ "$http_code" -eq 200 ]; then
        log_success "Coolify API is accessible"
        log_info "User info: $(echo "$body" | jq -r '.email // "Unknown" 2>/dev/null || echo "Unknown")"
        return 0
    else
        log_error "Coolify API connection failed (HTTP $http_code)"
        log_error "Response: $body"
        return 1
    fi
}

test_api_endpoints() {
    log_info "Testing API endpoints..."
    
    local endpoints=(
        "/api/user"
        "/api/servers"
        "/api/applications"
        "/api/deployments"
        "/api/v1/user"
        "/api/v1/servers"
        "/api/v1/applications"
    )
    
    for endpoint in "${endpoints[@]}"; do
        log_info "Testing: $endpoint"
        local response=$(curl -s -w "%{http_code}" \
            -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
            "$COOLIFY_API_URL$endpoint" 2>/dev/null)
        
        local http_code="${response: -3}"
        
        if [ "$http_code" -eq 200 ]; then
            log_success "✅ $endpoint"
        elif [ "$http_code" -eq 401 ]; then
            log_warning "⚠️  $endpoint - Unauthorized"
        elif [ "$http_code" -eq 404 ]; then
            log_warning "⚠️  $endpoint - Not Found"
        else
            log_error "❌ $endpoint - HTTP $http_code"
        fi
    done
}

run_tests() {
    log_info "Starting Coolify API tests..."
    log_info "Log file: $LOG_FILE"
    
    # Check dependencies
    if ! command -v curl &> /dev/null; then
        log_error "curl is required but not installed"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        log_error "jq is required but not installed"
        exit 1
    fi
    
    # Test Coolify connection
    if check_coolify_connection; then
        test_api_endpoints
        log_success "All tests completed"
    else
        log_error "Cannot connect to Coolify API"
        exit 1
    fi
}

# Run tests
run_tests
