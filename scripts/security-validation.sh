#!/bin/bash

# 🔒 Security Validation Script
# This script performs comprehensive security validation of the application

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_BASE_URL="http://localhost:8081"
SECURITY_HEADERS_URL="$API_BASE_URL/health"
JWT_SECRET_CHECK=true
CORS_CHECK=true
SSL_CHECK=true

# Results counter
PASSED=0
FAILED=0
WARNINGS=0

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓ PASS]${NC} $1"
    ((PASSED++))
}

print_warning() {
    echo -e "${YELLOW}[⚠ WARN]${NC} $1"
    ((WARNINGS++))
}

print_error() {
    echo -e "${RED}[✗ FAIL]${NC} $1"
    ((FAILED++))
}

print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

# Check if URL is accessible
check_url() {
    local url=$1
    local description=$2
    
    print_status "Checking $description..."
    
    if command -v curl &> /dev/null; then
        if curl -s -f --max-time 10 "$url" > /dev/null 2>&1; then
            print_success "$description is accessible"
            return 0
        else
            print_error "$description is not accessible"
            return 1
        fi
    else
        print_warning "curl not available, skipping URL check"
        return 2
    fi
}

# Validate security headers
validate_security_headers() {
    print_header "Security Headers Validation"
    
    if ! command -v curl &> /dev/null; then
        print_warning "curl not available, skipping security headers check"
        return
    fi
    
    print_status "Checking security headers on $SECURITY_HEADERS_URL..."
    
    # Get headers from the server
    local headers=$(curl -s -I "$SECURITY_HEADERS_URL" 2>/dev/null || echo "")
    
    if [[ -z "$headers" ]]; then
        print_error "Could not retrieve headers from server"
        return
    fi
    
    # Check required security headers
    local required_headers=(
        "x-content-type-options:nosniff"
        "x-frame-options:DENY"
        "x-xss-protection:1; mode=block"
        "strict-transport-security:max-age=31536000"
        "content-security-policy:default-src 'self'"
        "referrer-policy:strict-origin-when-cross-origin"
    )
    
    for header_config in "${required_headers[@]}"; do
        local header_name="${header_config%%:*}"
        local expected_value="${header_config##*:}"
        
        if echo "$headers" | grep -i "$header_name" | grep -qi "$expected_value"; then
            print_success "$header_name header present"
        else
            print_error "$header_name header missing or incorrect"
        fi
    done
}

# Validate JWT configuration
validate_jwt_config() {
    print_header "JWT Configuration Validation"
    
    # Check if JWT_SECRET is set
    if [[ -f ".env.production" ]]; then
        local jwt_secret=$(grep "^JWT_SECRET=" .env.production | cut -d'=' -f2)
        
        if [[ -z "$jwt_secret" ]]; then
            print_error "JWT_SECRET not found in .env.production"
        elif [[ "$jwt_secret" == "CHANGE_ME"* ]]; then
            print_error "JWT_SECRET is still using placeholder value"
        elif [[ ${#jwt_secret} -lt 32 ]]; then
            print_error "JWT_SECRET is too short (${#jwt_secret} characters, minimum 32 required)"
        else
            print_success "JWT_SECRET is properly configured (${#jwt_secret} characters)"
        fi
    else
        print_warning ".env.production file not found"
    fi
    
    # Check if JWT implementation uses secure library
    print_status "Checking JWT implementation..."
    
    if grep -q "github.com/golang-jwt/jwt/v5" go.mod; then
        print_success "Using secure JWT library (golang-jwt/jwt/v5)"
    elif grep -q "github.com/golang-jwt/jwt" go.mod; then
        print_warning "Using older JWT library, consider upgrading to v5"
    else
        print_error "JWT library not found in go.mod"
    fi
    
    # Check for custom JWT implementation
    if grep -r "hmacSHA256\|custom.*jwt\|XOR.*sign" internal/ --include="*.go" 2>/dev/null; then
        print_error "Custom JWT implementation detected - SECURITY RISK"
    else
        print_success "No insecure custom JWT implementation found"
    fi
}

# Validate CORS configuration
validate_cors_config() {
    print_header "CORS Configuration Validation"
    
    if [[ -f ".env.production" ]]; then
        local cors_origins=$(grep "^CORS_ORIGINS=" .env.production | cut -d'=' -f2)
        
        if [[ -z "$cors_origins" ]]; then
            print_error "CORS_ORIGINS not configured in .env.production"
        elif [[ "$cors_origins" == *"*" ]]; then
            print_error "CORS_ORIGINS contains wildcard (*) - SECURITY RISK"
        elif [[ "$cors_origins" == *"localhost"* ]]; then
            print_warning "CORS_ORIGINS contains localhost - ensure this is intentional"
        else
            print_success "CORS_ORIGINS properly configured: $cors_origins"
        fi
    fi
    
    # Check middleware implementation
    print_status "Checking CORS middleware implementation..."
    
    if grep -r "AllowOrigins.*\[\]string{\".*\*.*\"}" internal/ --include="*.go" 2>/dev/null; then
        print_error "CORS wildcard found in middleware code"
    else
        print_success "CORS middleware appears secure"
    fi
}

# Validate SSL/TLS configuration
validate_ssl_config() {
    print_header "SSL/TLS Configuration Validation"
    
    # Check if SSL certificates exist
    if [[ -d "./certs" ]]; then
        if [[ -f "./certs/server.crt" && -f "./certs/server.key" ]]; then
            print_success "SSL certificate files found"
            
            # Check certificate expiration
            if command -v openssl &> /dev/null; then
                local expiry_date=$(openssl x509 -in ./certs/server.crt -noout -enddate 2>/dev/null | cut -d'=' -f2 || echo "")
                if [[ -n "$expiry_date" ]]; then
                    print_success "SSL certificate expires: $expiry_date"
                fi
            fi
        else
            print_warning "SSL certificate directory exists but files missing"
        fi
    else
        print_warning "SSL certificates not found (development only)"
    fi
    
    # Check HSTS configuration
    if [[ -f ".env.production" ]]; then
        local hsts_enabled=$(grep "^HSTS_ENABLED=" .env.production | cut -d'=' -f2)
        
        if [[ "$hsts_enabled" == "true" ]]; then
            print_success "HSTS enabled in production configuration"
        else
            print_warning "HSTS not enabled - consider enabling for production"
        fi
    fi
}

# Validate database security
validate_database_security() {
    print_header "Database Security Validation"
    
    # Check database file permissions
    local db_file="./data/apikeys.db"
    if [[ -f "$db_file" ]]; then
        local perms=$(ls -la "$db_file" | cut -d' ' -f1)
        print_status "Database file permissions: $perms"
        
        # Check if database is readable by others
        if [[ "$perms" =~ .*r..r..r.* ]]; then
            print_warning "Database file is readable by others - security risk"
        else
            print_success "Database file permissions appear secure"
        fi
    else
        print_warning "Database file not found (will be created on first run)"
    fi
    
    # Check for database encryption
    print_status "Checking database security implementation..."
    
    if grep -r "encryption.*at.*rest\|encrypt.*database" internal/ --include="*.go" 2>/dev/null; then
        print_success "Database encryption implemented"
    else
        print_warning "Database encryption not implemented (consider for production)"
    fi
}

# Validate input validation
validate_input_validation() {
    print_header "Input Validation Security"
    
    # Check for input validation library
    if grep -q "github.com/go-playground/validator" go.mod; then
        print_success "Input validation library found (validator)"
    else
        print_warning "Input validation library not found in go.mod"
    fi
    
    # Check for SQL injection protection
    print_status "Checking for SQL injection protection..."
    
    if grep -r "fmt\.Sprintf.*SELECT\|strings\.Replace.*sql" internal/ --include="*.go" 2>/dev/null; then
        print_error "Potential SQL injection vulnerability detected"
    else
        print_success "No obvious SQL injection vulnerabilities found"
    fi
    
    # Check for XSS protection
    print_status "Checking for XSS protection..."
    
    if grep -r "sanitizeString\|html.*escape" internal/ --include="*.go" 2>/dev/null; then
        print_success "XSS protection implemented"
    else
        print_warning "XSS protection not clearly implemented"
    fi
}

# Validate container security
validate_container_security() {
    print_header "Container Security Validation"
    
    # Check Dockerfile for security best practices
    if [[ -f "Dockerfile" ]]; then
        print_status "Checking Dockerfile security..."
        
        # Check for non-root user
        if grep -q "USER.*[0-9]" Dockerfile || grep -q "USER.*node\|USER.*nginx" Dockerfile; then
            print_success "Dockerfile uses non-root user"
        else
            print_warning "Dockerfile may run as root user"
        fi
        
        # Check for minimal base image
        if grep -q "alpine\|distroless" Dockerfile; then
            print_success "Dockerfile uses minimal base image"
        else
            print_warning "Dockerfile could use minimal base image"
        fi
    fi
    
    # Check docker-compose for security
    if [[ -f "docker-compose.yml" ]]; then
        print_status "Checking docker-compose security..."
        
        # Check for security configurations
        if grep -q "security_opt\|cap_drop\|read_only" docker-compose.yml; then
            print_success "Docker Compose includes security configurations"
        else
            print_warning "Docker Compose lacks security hardening"
        fi
        
        # Check for exposed ports
        local exposed_ports=$(grep -E "^\s*[0-9]+:[0-9]+" docker-compose.yml | wc -l)
        if [[ $exposed_ports -gt 2 ]]; then
            print_warning "Many ports exposed ($exposed_ports) - review if necessary"
        else
            print_success "Limited port exposure"
        fi
    fi
}

# Validate monitoring and logging
validate_monitoring() {
    print_header "Monitoring and Logging Validation"
    
    # Check for structured logging
    if grep -r "json\.Marshal\|structured.*log" internal/ --include="*.go" 2>/dev/null; then
        print_success "Structured logging implemented"
    else
        print_warning "Structured logging not clearly implemented"
    fi
    
    # Check for monitoring configuration
    if [[ -f "docker-compose.yml" ]] && grep -q "prometheus\|monitoring" docker-compose.yml; then
        print_success "Monitoring stack configured (Prometheus)"
    else
        print_warning "Monitoring stack not configured"
    fi
    
    # Check for health endpoints
    if grep -r "/health\|/ping" internal/ --include="*.go" 2>/dev/null; then
        print_success "Health check endpoints implemented"
    else
        print_warning "Health check endpoints not found"
    fi
}

# Generate security report
generate_report() {
    print_header "Security Validation Report"
    
    echo "Total Checks: $((PASSED + FAILED + WARNINGS))"
    echo "Passed: $PASSED"
    echo "Failed: $FAILED"
    echo "Warnings: $WARNINGS"
    echo ""
    
    if [[ $FAILED -eq 0 ]]; then
        if [[ $WARNINGS -eq 0 ]]; then
            print_success "🎉 All security checks passed! Application is secure."
        else
            print_warning "⚠️  All critical checks passed, but there are warnings to review."
        fi
    else
        print_error "❌ $FAILED security check(s) failed. Please address these issues before production deployment."
        echo ""
        echo "Critical Issues:"
        echo "1. Review failed security checks"
        echo "2. Fix vulnerabilities before production deployment"
        echo "3. Re-run validation after fixes"
    fi
    
    echo ""
    echo "Security validation completed at: $(date)"
}

# Main validation function
main() {
    echo "🔒 DoctorHealthy1 Security Validation"
    echo "===================================="
    echo ""
    
    # Check if application is running
    print_status "Performing security validation..."
    
    # Run all security checks
    validate_jwt_config
    validate_cors_config
    validate_security_headers
    validate_ssl_config
    validate_database_security
    validate_input_validation
    validate_container_security
    validate_monitoring
    
    # Generate final report
    generate_report
    
    echo ""
    print_status "For detailed security guidelines, see SECURITY.md"
    
    # Exit with appropriate code
    if [[ $FAILED -gt 0 ]]; then
        exit 1
    elif [[ $WARNINGS -gt 0 ]]; then
        exit 2
    else
        exit 0
    fi
}

# Run validation
main "$@"
