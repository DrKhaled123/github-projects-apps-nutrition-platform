#!/bin/bash

# 🔒 Production Secrets Setup Script
# This script helps generate and configure secure production secrets

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if openssl is available
check_dependencies() {
    print_status "Checking dependencies..."
    
    if ! command -v openssl &> /dev/null; then
        print_error "OpenSSL is required but not installed. Please install OpenSSL."
        exit 1
    fi
    
    if ! command -v tr &> /dev/null; then
        print_error "tr command is required but not found."
        exit 1
    fi
    
    print_success "Dependencies check passed"
}

# Generate secure random string
generate_secret() {
    local length=${1:-32}
    openssl rand -hex "$length"
}

# Generate JWT secret
generate_jwt_secret() {
    print_status "Generating secure JWT secret..."
    local jwt_secret=$(generate_secret 32)
    echo "$jwt_secret"
}

# Generate API key
generate_api_key() {
    print_status "Generating API key..."
    local api_key="ak_$(generate_secret 24)"
    echo "$api_key"
}

# Setup environment files
setup_environment_files() {
    print_status "Setting up environment files..."
    
    # Check if production env file exists
    if [[ -f ".env.production" ]]; then
        print_warning ".env.production already exists. Creating backup..."
        cp .env.production .env.production.backup.$(date +%Y%m%d_%H%M%S)
    fi
    
    # Copy template to production file
    if [[ -f ".env.production.template" ]]; then
        cp .env.production.template .env.production
        print_success "Created .env.production from template"
    else
        print_error ".env.production.template not found"
        exit 1
    fi
    
    # Setup development environment
    if [[ ! -f ".env.local" ]]; then
        cp .env.development.template .env.local
        print_success "Created .env.local from template"
    fi
}

# Generate and update secrets
update_secrets() {
    print_status "Generating and updating secrets..."
    
    # Generate JWT secret
    local jwt_secret=$(generate_jwt_secret | tr -d '\n' | tr -d '\r')
    print_status "Generated JWT secret (64 characters)"
    
    # Update production env file
    if [[ -f ".env.production" ]]; then
        sed -i.bak "s|JWT_SECRET=CHANGE_ME.*|JWT_SECRET=$jwt_secret|" .env.production
        print_success "Updated JWT secret in .env.production"
    fi
    
    # Generate and display API key for manual configuration
    local api_key=$(generate_api_key)
    print_status "Generated API key: $api_key"
    print_warning "Please configure this API key in your deployment system"
    
    # Save API key to a temporary file for reference
    echo "$api_key" > .generated_api_key
    chmod 600 .generated_api_key
    print_success "API key saved to .generated_api_key (secure permissions)"
}

# Validate configuration
validate_configuration() {
    print_status "Validating configuration..."
    
    if [[ -f ".env.production" ]]; then
        # Check if JWT secret was updated
        if grep -q "CHANGE_ME" .env.production; then
            print_error "Some configuration values still need to be updated:"
            grep "CHANGE_ME" .env.production
            print_warning "Please update these values manually"
        else
            print_success "Configuration validation passed"
        fi
    fi
}

# Generate SSL certificate (self-signed for development)
generate_ssl_cert() {
    print_status "Generating self-signed SSL certificate for testing..."
    
    local cert_dir="./certs"
    mkdir -p "$cert_dir"
    
    # Generate private key
    openssl genrsa -out "$cert_dir/server.key" 2048
    
    # Generate certificate signing request
    openssl req -new -key "$cert_dir/server.key" -out "$cert_dir/server.csr" -subj "/C=US/ST=State/L=City/O=DoctorHealthy/OU=IT/CN=doctorhealthy1.com"
    
    # Generate self-signed certificate
    openssl x509 -req -days 365 -in "$cert_dir/server.csr" -signkey "$cert_dir/server.key" -out "$cert_dir/server.crt"
    
    # Set secure permissions
    chmod 600 "$cert_dir/server.key"
    chmod 644 "$cert_dir/server.crt"
    
    print_success "SSL certificate generated in $cert_dir/"
    print_warning "This is a self-signed certificate for testing only"
}

# Show security checklist
show_security_checklist() {
    print_status "Security Setup Checklist:"
    echo ""
    echo "✅ Environment files created"
    echo "✅ JWT secret generated"
    echo "✅ API key generated"
    echo "✅ SSL certificate generated (testing only)"
    echo ""
    echo "📋 Remaining Tasks:"
    echo "   1. Update remaining CHANGE_ME values in .env.production"
    echo "   2. Add real API keys from service providers"
    echo "   3. Configure proper SSL certificates for production"
    echo "   4. Set up monitoring and alerting"
    echo "   5. Test security configuration"
    echo ""
    echo "🔐 Security Files Created:"
    echo "   - .env.production (production configuration)"
    echo "   - .env.local (development configuration)"
    echo "   - .generated_api_key (API key for configuration)"
    echo "   - certs/ (SSL certificates for testing)"
    echo ""
    echo "⚠️  Important Security Notes:"
    echo "   - Never commit .env.production with real values"
    echo "   - Store secrets securely (AWS Secrets Manager, Azure Key Vault, etc.)"
    echo "   - Rotate secrets regularly"
    echo "   - Use proper SSL certificates in production"
    echo "   - Monitor for security events"
}

# Main execution
main() {
    echo "🔒 DoctorHealthy1 Production Secrets Setup"
    echo "========================================"
    echo ""
    
    check_dependencies
    setup_environment_files
    update_secrets
    validate_configuration
    generate_ssl_cert
    show_security_checklist
    
    print_success "Production secrets setup completed!"
    echo ""
    print_status "Next steps:"
    echo "1. Review and update remaining configuration in .env.production"
    echo "2. Test the application with new configuration"
    echo "3. Deploy to production environment"
    echo ""
}

# Run main function
main "$@"
