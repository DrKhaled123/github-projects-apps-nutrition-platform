#!/bin/bash

# ==================================================
# DoctorHealthy - Final E2E Verification
# Complete testing before production deployment
# ==================================================

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
API_BASE_URL="https://backend.doctorhealthy1.com"
FRONTEND_URL="https://my.doctorhealthy1.com"
MONITOR_URL="https://monitor.doctorhealthy1.com"
COOLIFY_API_URL="http://128.140.111.171:8000"
COOLIFY_API_TOKEN="7|Pc76Go9w1ELoKy0GBYb2RpMxWWujefpjEKM30R3Obef9679a"

# Logging
LOG_FILE="/tmp/e2e-test-$(date +%Y%m%d-%H%M%S).log"
TEST_RESULTS_FILE="/tmp/e2e-results-$(date +%Y%m%d-%H%M%S).json"

echo "${BLUE}🚀 DoctorHealthy - Final E2E Verification${NC}"
echo "================================================"
echo "API Base URL: $API_BASE_URL"
echo "Frontend URL: $FRONTEND_URL"
echo "Monitor URL: $MONITOR_URL"
echo "Coolify API: $COOLIFY_API_URL"
echo "Log File: $LOG_FILE"
echo "Results File: $TEST_RESULTS_FILE"
echo ""

# Initialize results
cat > "$TEST_RESULTS_FILE" << 'EOFILE'
{
  "test_run": {
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "phase": "final_verification",
    "total_tests": 0,
    "passed": 0,
    "failed": 0,
    "skipped": 0
  },
  "test_suites": []
}
EOFILE

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

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "Required command '$1' is not installed"
        return 1
    fi
    return 0
}

make_http_request() {
    local url="$1"
    local method="${2:-GET}"
    local data="${3:-}"
    local headers="${4:-}"
    
    if [ -n "$data" ]; then
        response=$(curl -s -w "%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            ${headers:+-H "$headers"} \
            -d "$data" \
            "$url" 2>/dev/null)
    else
        response=$(curl -s -w "%{http_code}" -X "$method" \
            ${headers:+-H "$headers"} \
            "$url" 2>/dev/null)
    fi
    
    http_code="${response: -3}"
    body="${response%???}"
    
    echo "$body"
    return "$http_code"
}

check_health_endpoint() {
    local url="$1"
    local service_name="$2"
    local expected_status="${3:-200}"
    
    log_info "Checking $service_name health endpoint: $url"
    
    body=$(make_http_request "$url")
    status_code=$?
    
    if [ "$status_code" -eq "$expected_status" ]; then
        log_success "$service_name is healthy (Status: $status_code)"
        return 0
    else
        log_error "$service_name health check failed (Status: $status_code)"
        log_error "Response: $body"
        return 1
    fi
}

check_ssl_certificate() {
    local domain="$1"
    local port="${2:-443}"
    
    log_info "Checking SSL certificate for $domain:$port"
    
    if echo | timeout 10 openssl s_client -connect "$domain:$port" -servername "$domain" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null; then
        log_success "SSL certificate is valid for $domain"
        return 0
    else
        log_error "SSL certificate check failed for $domain"
        return 1
    fi
}

# Test Suite 1: Infrastructure Health Check
test_infrastructure_health() {
    log_info "🏗️  Running Infrastructure Health Checks..."
    
    local suite_passed=0
    local suite_total=0
    
    # Test 1: SSL Certificates
    suite_total=$((suite_total + 1))
    if check_ssl_certificate "doctorhealthy1.com"; then
        suite_passed=$((suite_passed + 1))
    fi
    
    # Test 2: API Domain SSL
    suite_total=$((suite_total + 1))
    if check_ssl_certificate "backend.doctorhealthy1.com"; then
        suite_passed=$((suite_passed + 1))
    fi
    
    # Test 3: Frontend Domain SSL
    suite_total=$((suite_total + 1))
    if check_ssl_certificate "my.doctorhealthy1.com"; then
        suite_passed=$((suite_passed + 1))
    fi
    
    # Test 4: Monitor Domain SSL
    suite_total=$((suite_total + 1))
    if check_ssl_certificate "monitor.doctorhealthy1.com"; then
        suite_passed=$((suite_passed + 1))
    fi
    
    # Test 5: API Health Endpoint
    suite_total=$((suite_total + 1))
    if check_health_endpoint "$API_BASE_URL/api/health" "API"; then
        suite_passed=$((suite_passed + 1))
    fi
    
    # Test 6: Frontend Accessibility
    suite_total=$((suite_total + 1))
    if make_http_request "$FRONTEND_URL" > /dev/null; then
        log_success "Frontend is accessible"
        suite_passed=$((suite_passed + 1))
    else
        log_error "Frontend is not accessible"
    fi
    
    # Test 7: Monitor Accessibility
    suite_total=$((suite_total + 1))
    if make_http_request "$MONITOR_URL" > /dev/null; then
        log_success "Monitoring dashboard is accessible"
        suite_passed=$((suite_passed + 1))
    else
        log_error "Monitoring dashboard is not accessible"
    fi
    
    # Test 8: Database Connectivity (via API)
    suite_total=$((suite_total + 1))
    body=$(make_http_request "$API_BASE_URL/api/health/db")
    if [ $? -eq 200 ] && echo "$body" | grep -q "database.*connected"; then
        log_success "Database is connected and accessible"
        suite_passed=$((suite_passed + 1))
    else
        log_error "Database connectivity check failed"
    fi
    
    # Test 9: Redis Connectivity (via API)
    suite_total=$((suite_total + 1))
    body=$(make_http_request "$API_BASE_URL/api/health/redis")
    if [ $? -eq 200 ] && echo "$body" | grep -q "redis.*connected"; then
        log_success "Redis is connected and accessible"
        suite_passed=$((suite_passed + 1))
    else
        log_error "Redis connectivity check failed"
    fi
    
    # Test 10: Container Health
    suite_total=$((suite_total + 1))
    if curl -s "http://128.140.111.171:2375/containers/json" 2>/dev/null | jq -r '.[].Status' 2>/dev/null | grep -q "Up"; then
        log_success "Docker containers are running"
        suite_passed=$((suite_passed + 1))
    else
        log_warning "Docker containers health check inconclusive"
    fi
    
    log_info "Infrastructure Health: $suite_passed/$suite_total tests passed"
    return $((suite_total - suite_passed))
}

# Test Suite 2: Coolify Deployment Test
test_coolify_deployment() {
    log_info "🚀 Testing Coolify API Deployment..."
    
    local suite_passed=0
    local suite_total=0
    
    # Test 1: Coolify API Connectivity
    suite_total=$((suite_total + 1))
    if make_http_request "$COOLIFY_API_URL/api/health" "GET" "" "Authorization: Bearer $COOLIFY_API_TOKEN" > /dev/null 2>&1; then
        log_success "Coolify API is accessible"
        suite_passed=$((suite_passed + 1))
    else
        log_warning "Coolify API is not accessible (may not be configured yet)"
    fi
    
    # Test 2: Coolify Service Availability
    suite_total=$((suite_total + 1))
    if make_http_request "$COOLIFY_API_URL" > /dev/null 2>&1; then
        log_success "Coolify service is running"
        suite_passed=$((suite_passed + 1))
    else
        log_warning "Coolify service is not accessible"
    fi
    
    # Test 3: Coolify Application Listing
    suite_total=$((suite_total + 1))
    body=$(make_http_request "$COOLIFY_API_URL/api/applications" "GET" "" "Authorization: Bearer $COOLIFY_API_TOKEN" 2>/dev/null)
    if [ $? -eq 200 ]; then
        log_success "Can list applications from Coolify"
        suite_passed=$((suite_passed + 1))
        app_count=$(echo "$body" | jq '. | length' 2>/dev/null || echo "0")
        log_info "Found $app_count applications in Coolify"
    else
        log_warning "Cannot list applications from Coolify (may need authentication)"
    fi
    
    log_info "Coolify Deployment: $suite_passed/$suite_total tests passed"
    return $((suite_total - suite_passed))
}

# Generate Test Report
generate_test_report() {
    local total_failed=$1
    local total_passed=$2
    local total_tests=$3
    
    log_info "📋 Generating Test Report..."
    
    local report_file="/tmp/e2e-report-$(date +%Y%m%d-%H%M%S).html"
    
    cat > "$report_file" << 'EOHTML'
<!DOCTYPE html>
<html>
<head>
    <title>DoctorHealthy - E2E Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
        .success { color: #27ae60; }
        .error { color: #e74c3c; }
        .warning { color: #f39c12; }
        .info { color: #3498db; }
        .summary { background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .test-suite { margin: 20px 0; padding: 15px; border: 1px solid #bdc3c7; border-radius: 5px; }
        .status-pass { border-left: 5px solid #27ae60; }
        .status-fail { border-left: 5px solid #e74c3c; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏥 DoctorHealthy - End-to-End Test Report</h1>
        <p>Generated on: $(date)</p>
        <p>Environment: Production</p>
    </div>
    
    <div class="summary">
        <h2>📊 Test Summary</h2>
        <p class="success">✅ Passed: PASSED_COUNT</p>
        <p class="error">❌ Failed: FAILED_COUNT</p>
        <p class="info">📈 Total: TOTAL_COUNT</p>
        <p><strong>Success Rate: SUCCESS_RATE%</strong></p>
    </div>
    
    <div class="test-suite status-pass">
        <h3>🏗️ Infrastructure Health</h3>
        <p>Tests SSL certificates, domain accessibility, and service health endpoints.</p>
    </div>
    
    <div class="test-suite status-pass">
        <h3>🚀 Coolify Deployment</h3>
        <p>Tests Coolify API integration and deployment functionality.</p>
    </div>
    
    <div class="summary">
        <h2>🎯 Next Steps</h2>
        <ul>
            <li>Review any failed tests and address issues</li>
            <li>Monitor production performance</li>
            <li>Set up automated alerts</li>
            <li>Schedule regular E2E tests</li>
            <li>Configure Coolify if not already done</li>
        </ul>
    </div>
</body>
</html>
EOHTML
    
    # Replace placeholders
    sed -i '' "s/PASSED_COUNT/$total_passed/g" "$report_file"
    sed -i '' "s/FAILED_COUNT/$total_failed/g" "$report_file"
    sed -i '' "s/TOTAL_COUNT/$total_tests/g" "$report_file"
    sed -i '' "s/SUCCESS_RATE/$(( total_passed * 100 / total_tests ))/g" "$report_file"
    
    log_success "Test report generated: $report_file"
    echo "📊 Report available at: file://$report_file"
}

# Execute tests
run_tests() {
    log_info "Starting Final E2E Verification for DoctorHealthy"
    
    # Check dependencies
    log_info "Checking dependencies..."
    for cmd in curl jq openssl date; do
        if ! check_command "$cmd"; then
            log_error "Missing dependency: $cmd"
            exit 1
        fi
    done
    
    # Run test suites
    local total_failed=0
    local total_passed=0
    local total_tests=0
    
    # Infrastructure Health
    test_infrastructure_health
    local failed=$?
    total_failed=$((total_failed + failed))
    total_passed=$((total_passed + 10 - failed))
    total_tests=$((total_tests + 10))
    
    # Coolify Deployment
    test_coolify_deployment
    failed=$?
    total_failed=$((total_failed + failed))
    total_passed=$((total_passed + 3 - failed))
    total_tests=$((total_tests + 3))
    
    # Generate report
    generate_test_report $total_failed $total_passed $total_tests
    
    # Final summary
    echo ""
    echo "================================================"
    echo "🏥 DoctorHealthy - E2E Test Results"
    echo "================================================"
    echo -e "${GREEN}✅ Passed: $total_passed${NC}"
    echo -e "${RED}❌ Failed: $total_failed${NC}"
    echo -e "${BLUE}📈 Total: $total_tests${NC}"
    echo -e "${YELLOW}📊 Success Rate: $(( total_passed * 100 / total_tests ))%${NC}"
    echo ""
    
    if [ $total_failed -eq 0 ]; then
        echo -e "${GREEN}🎉 All tests passed! System is ready for production.${NC}"
        echo ""
        echo "🚀 Next Steps:"
        echo "1. Configure Coolify if not already done"
        echo "2. Deploy applications using Coolify API"
        echo "3. Monitor production performance"
        echo "4. Set up automated alerts"
        exit 0
    else
        echo -e "${RED}⚠️  Some tests failed. Please review and fix issues before production deployment.${NC}"
        echo ""
        echo "🔧 Recommended Actions:"
        echo "1. Review failed tests in the log file: $LOG_FILE"
        echo "2. Fix identified issues"
        echo "3. Re-run tests to verify fixes"
        echo "4. Ensure all infrastructure components are properly configured"
        exit 1
    fi
}

# Run the tests
run_tests "$@"
