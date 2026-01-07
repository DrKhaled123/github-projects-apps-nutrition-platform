# DoctorHealthy Platform - Coolify Deployment Verification & API Setup

## Overview

This comprehensive deployment verification and Coolify API setup script is designed specifically for the DoctorHealthy platform deployment on Hetzner servers. The script provides end-to-end testing, automated deployment capabilities, and MCP server integration for seamless Goose AI platform management.

## Features

### 🔍 **Server Connectivity Testing**
- Ping connectivity verification to Hetzner server (128.140.111.171)
- SSH port accessibility testing
- HTTP/HTTPS connectivity validation
- Network diagnostics and troubleshooting

### 🚀 **Coolify Installation Verification**
- Automatic detection of Coolify installation
- Service status monitoring
- Version information retrieval
- Installation guidance if Coolify is not found

### 🔌 **API Connectivity Testing**
- Coolify API authentication validation
- Endpoint accessibility testing
- User authentication verification
- Comprehensive API health checks

### ⚙️ **Configuration Generation**
- Automatic generation of DoctorHealthy platform configurations
- Backend, frontend, and monitoring application settings
- Environment variable configuration
- Domain and SSL configuration templates

### 🔗 **MCP Server Integration**
- Model Context Protocol (MCP) server setup for Goose AI
- Seamless integration with existing workflows
- Real-time deployment management capabilities
- Automated monitoring and alerting

### 🧪 **End-to-End Testing**
- Comprehensive E2E test suite
- Automated deployment verification
- Health monitoring and diagnostics
- Performance validation

## Installation & Setup

### Prerequisites

The script automatically installs required dependencies:
- `curl` - For API testing and HTTP requests
- `jq` - For JSON parsing and manipulation
- `netcat` - For network connectivity testing

### Quick Start

```bash
# Download and make executable
chmod +x coolify-deploy-verification.sh

# Run full verification (Recommended)
./coolify-deploy-verification.sh --verify

# Or run interactive mode
./coolify-deploy-verification.sh
```

## Usage Options

### Command Line Options

```bash
./coolify-deploy-verification.sh [OPTION]

Options:
  -h, --help              Show help message
  -v, --verify           Run full deployment verification
  -c, --connectivity     Test server connectivity only
  -i, --install         Check Coolify installation only
  -a, --api             Test Coolify API only
  -g, --generate        Generate configuration files only
  -m, --mcp             Setup MCP server only
  -t, --test            Run E2E tests only
  -d, --deploy          Deploy DoctorHealthy platform
  -H, --health          Run health check
  --auto                Run automated verification (no interaction)
```

### Interactive Mode

Run the script without arguments to access the interactive menu:

```bash
./coolify-deploy-verification.sh
```

Available options:
1. Run Full Deployment Verification (Recommended)
2. Test Server Connectivity Only
3. Check Coolify Installation Only
4. Test Coolify API Only
5. Generate Configuration Files Only
6. Setup MCP Server Only
7. Run E2E Tests Only
8. Deploy DoctorHealthy Platform
9. Run Health Check
10. Show Help

## Configuration Files

The script generates several configuration files:

### 1. `coolify-config.json`
Complete DoctorHealthy platform configuration including:
- Backend application settings (Node.js, PostgreSQL, Redis)
- Frontend application settings (Next.js, static hosting)
- Monitoring stack (Grafana, Prometheus)
- Environment variables and secrets
- Domain configurations and SSL settings

### 2. `mcp-coolify-config.json`
MCP server configuration for Goose AI integration:
- Server connection settings
- API authentication configuration
- Tool definitions and parameters
- Environment variables

### 3. `coolify-mcp-server.js`
Node.js MCP server implementation:
- API request handling
- Error management
- Tool execution logic
- Response formatting

### 4. `deployment-verification.log`
Comprehensive execution log with:
- Timestamped events
- Success/failure indicators
- Error messages and diagnostics
- Test results and validation

## DoctorHealthy Platform Architecture

### Backend Application
- **Technology**: Node.js with Express
- **Database**: PostgreSQL
- **Cache**: Redis
- **Port**: 3000
- **Domain**: api.doctorhealthy.com

### Frontend Application
- **Technology**: Next.js (React)
- **Hosting**: Static site generation
- **Port**: 3001
- **Domains**: doctorhealthy.com, www.doctorhealthy.com

### Monitoring Stack
- **Technology**: Docker containers
- **Tools**: Grafana, Prometheus
- **Port**: 3002
- **Domain**: monitoring.doctorhealthy.com

## API Configuration

### Coolify API Settings
- **Server IP**: 128.140.111.171
- **Port**: 8000
- **API Version**: v1
- **Authentication**: Bearer token
- **Token**: `7|Pc76Go9w1ELoKy0GBYb2RpMxWWujefpjEKM30R3Obef9679a`

### API Endpoints
- `/api/v1/user` - User information
- `/api/v1/servers` - Server management
- `/api/v1/applications` - Application management
- `/api/v1/deployments` - Deployment control

## Deployment Automation

### Automated Deployment Process

1. **Configuration Validation**
   - Verify all required settings
   - Validate environment variables
   - Check domain configurations

2. **Server Health Check**
   - Test connectivity to all servers
   - Verify service statuses
   - Check resource availability

3. **Application Deployment**
   - Backend API deployment
   - Frontend application deployment
   - Monitoring stack deployment

4. **Post-Deployment Verification**
   - Health endpoint testing
   - SSL certificate validation
   - Performance monitoring setup

### Manual Deployment Commands

```bash
# Deploy individual components
./coolify-deploy-verification.sh --deploy

# Run health checks
./coolify-deploy-verification.sh --health

# Test specific components
./coolify-deploy-verification.sh --connectivity
./coolify-deploy-verification.sh --api
```

## MCP Integration with Goose AI

### Setup Instructions

1. **Install MCP Server Dependencies**
   ```bash
   npm install @modelcontextprotocol/sdk
   ```

2. **Configure Goose AI**
   Add the MCP configuration to your Goose AI settings:
   ```json
   {
     "mcpServers": {
       "coolify": {
         "command": "node",
         "args": ["coolify-mcp-server.js"],
         "env": {
           "COOLIFY_API_URL": "http://128.140.111.171:8000/api/v1",
           "COOLIFY_API_TOKEN": "7|Pc76Go9w1ELoKy0GBYb2RpMxWWujefpjEKM30R3Obef9679a"
         }
       }
     }
   }
   ```

### Available MCP Tools

- `list_servers` - List all Coolify servers
- `list_applications` - List all deployed applications
- `deploy_application` - Trigger application deployment
- `get_application_logs` - Retrieve application logs
- `create_application` - Create new applications

## Troubleshooting

### Common Issues

1. **SSH Connection Failed**
   - Verify SSH key configuration
   - Check firewall settings
   - Ensure server accessibility

2. **API Authentication Failed**
   - Validate API token
   - Check token expiration
   - Verify API endpoint URLs

3. **Dependency Installation Failed**
   - Check package manager availability
   - Verify internet connectivity
   - Run with appropriate permissions

### Debug Mode

Enable verbose logging by modifying the script:
```bash
# Add at the beginning of the script
set -x  # Enable debug mode
```

### Log Analysis

Review the generated log file for detailed information:
```bash
tail -f deployment-verification.log
```

## Security Considerations

### API Token Security
- Store API tokens securely
- Rotate tokens regularly
- Use environment variables for sensitive data
- Never commit tokens to version control

### SSH Security
- Use key-based authentication
- Disable password authentication
- Implement IP whitelisting
- Regular security updates

### Network Security
- Implement firewall rules
- Use SSL/TLS for all communications
- Monitor network access logs
- Regular security audits

## Maintenance

### Regular Tasks
- Weekly health checks
- Monthly dependency updates
- Quarterly security audits
- Annual architecture review

### Monitoring
- Application performance metrics
- Server resource utilization
- API response times
- Error rate tracking

## Support

For issues and support:
1. Check the log files for error messages
2. Review the troubleshooting section
3. Run the health check utility
4. Consult the API documentation

## License

This script is part of the DoctorHealthy platform deployment toolkit and follows the project's licensing terms.

---

**Last Updated**: 2025-10-19  
**Version**: 1.0.0  
**Compatibility**: Coolify v4.x, Node.js 18+, Bash 4.0+
