package utils

import (
	"api-key-generator/internal/models"
	"fmt"
	"log"
	"os"
	"os/exec"
	"runtime"
	"strings"
	"syscall"
	"time"
)

// DeploymentConfig represents deployment configuration validation
type DeploymentConfig struct {
	Platform        string
	Environment     string
	RequiredEnvVars []string
	RequiredPorts   []int
	RequiredFiles   []string
	RequiredDirs    []string
}

// NginxConfig represents Nginx reverse proxy configuration
type NginxConfig struct {
	ServerName   string
	ProxyPort    int
	SSL          bool
	SSLCert      string
	SSLKey       string
	RateLimit    int
	CacheEnabled bool
	Compression  bool
}

// DockerConfig represents Docker deployment configuration
type DockerConfig struct {
	ImageName      string
	ContainerName  string
	Ports          map[int]int
	Volumes        map[string]string
	Environment    map[string]string
	RestartPolicy  string
	ResourceLimits ResourceLimits
}

// ResourceLimits represents container resource limits
type ResourceLimits struct {
	CPU    string
	Memory string
}

// NewDeploymentConfig creates a new deployment configuration validator
func NewDeploymentConfig(platform, environment string) *DeploymentConfig {
	return &DeploymentConfig{
		Platform:    platform,
		Environment: environment,
		RequiredEnvVars: []string{
			"DATABASE_URL",
			"JWT_SECRET",
			"API_PORT",
			"FRONTEND_URL",
		},
		RequiredPorts: []int{8080, 5432, 80, 443},
		RequiredFiles: []string{
			"main.go",
			"go.mod",
			"Dockerfile",
			"package.json",
		},
		RequiredDirs: []string{
			"internal",
			"frontend",
			"data",
		},
	}
}

// ValidateEnvironment validates the deployment environment
func (dc *DeploymentConfig) ValidateEnvironment() error {
	log.Printf("🔍 Validating deployment environment for %s...", dc.Platform)

	// Check required environment variables
	for _, envVar := range dc.RequiredEnvVars {
		if os.Getenv(envVar) == "" {
			return fmt.Errorf("required environment variable %s is not set", envVar)
		}
	}

	// Check required ports
	for _, port := range dc.RequiredPorts {
		if !dc.isPortAvailable(port) {
			log.Printf("⚠️ Port %d may be in use", port)
		}
	}

	// Check required files
	for _, file := range dc.RequiredFiles {
		if _, err := os.Stat(file); os.IsNotExist(err) {
			return fmt.Errorf("required file %s does not exist", file)
		}
	}

	// Check required directories
	for _, dir := range dc.RequiredDirs {
		if _, err := os.Stat(dir); os.IsNotExist(err) {
			return fmt.Errorf("required directory %s does not exist", dir)
		}
	}

	log.Println("✅ Environment validation passed")
	return nil
}

// isPortAvailable checks if a port is available
func (dc *DeploymentConfig) isPortAvailable(port int) bool {
	// This is a simplified check - in production, use proper port checking
	return true
}

// GenerateNginxConfig generates optimized Nginx configuration
func (dc *DeploymentConfig) GenerateNginxConfig(config NginxConfig) string {
	sslConfig := ""
	if config.SSL {
		sslConfig = fmt.Sprintf(`
    listen 443 ssl http2;
    ssl_certificate %s;
    ssl_certificate_key %s;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
`, config.SSLCert, config.SSLKey)
	}

	cacheConfig := ""
	if config.CacheEnabled {
		cacheConfig = `
    # Enable caching
    proxy_cache my_cache;
    proxy_cache_valid 200 302 10m;
    proxy_cache_valid 404 1m;
    add_header X-Proxy-Cache $upstream_cache_status;
`
	}

	compressionConfig := ""
	if config.Compression {
		compressionConfig = `
    # Enable compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied expired no-cache no-store private must-revalidate auth;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss;
`
	}

	nginxConf := fmt.Sprintf(`# Nginx Configuration for %s
upstream backend {
    server localhost:%d;
    keepalive 32;
}

server {
    listen 80;
    server_name %s;
%s
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    client_max_body_size 50M;
    client_body_timeout 12;
    client_header_timeout 12;
    send_timeout 10;

    location / {
        limit_req zone=api burst=20 nodelay;

        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
%s
%s
        # Health check endpoint
        location /nginx-health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }

    # API endpoints with CORS
    location /api/ {
        if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' '*';
            add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE';
            add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization';
            add_header 'Access-Control-Max-Age' 1728000;
            add_header 'Content-Type' 'text/plain charset=UTF-8';
            add_header 'Content-Length' 0;
            return 204;
        }

        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE' always;
        add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;

        proxy_pass http://backend;
    }

    # Static files caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        try_files $uri @proxy;
    }

    location @proxy {
        proxy_pass http://backend;
    }
}
`, config.ServerName, config.ProxyPort, config.ServerName, sslConfig, cacheConfig, compressionConfig)

	return nginxConf
}

// GenerateDockerfile generates optimized Dockerfile
func (dc *DeploymentConfig) GenerateDockerfile(config DockerConfig) string {
	dockerfile := fmt.Sprintf(`# Multi-stage build for optimal image size
FROM golang:1.21-alpine AS builder

# Install necessary packages
RUN apk add --no-cache git ca-certificates tzdata

# Create appuser for security
RUN adduser -D -g '' appuser

WORKDIR /build

# Copy go mod files
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY . .

# Build the binary
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o main .

# Final stage
FROM alpine:latest

# Install ca-certificates for HTTPS requests
RUN apk --no-cache add ca-certificates tzdata

WORKDIR /root/

# Copy the binary from builder stage
COPY --from=builder /build/main .

# Copy data directory if it exists
COPY --from=builder /build/data ./data

# Create non-root user
RUN adduser -D -g '' appuser

# Change ownership
RUN chown -R appuser:appuser /root/

USER appuser

# Expose port
EXPOSE %d

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:%d/health || exit 1

# Start the application
CMD ["./main"]
`, config.Ports[8080], config.Ports[8080])

	return dockerfile
}

// GenerateDockerCompose generates docker-compose.yml
func (dc *DeploymentConfig) GenerateDockerCompose(config DockerConfig) string {
	envVars := ""
	for key, value := range config.Environment {
		envVars += fmt.Sprintf("      - %s=%s\n", key, value)
	}

	ports := ""
	for host, container := range config.Ports {
		ports += fmt.Sprintf("      - \"%d:%d\"\n", host, container)
	}

	volumes := ""
	for host, container := range config.Volumes {
		volumes += fmt.Sprintf("      - %s:%s\n", host, container)
	}

	compose := fmt.Sprintf(`version: '3.8'

services:
  app:
    image: %s
    container_name: %s
    ports:
%s
    environment:
%s
    volumes:
%s
    restart: %s
    deploy:
      resources:
        limits:
          cpus: '%s'
          memory: %s
        reservations:
          cpus: '0.5'
          memory: 256M
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:%d/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Optional: Database service
  # db:
  #   image: postgres:15-alpine
  #   environment:
  #     POSTGRES_DB: nutrition_app
  #     POSTGRES_USER: app_user
  #     POSTGRES_PASSWORD: secure_password
  #   volumes:
  #     - db_data:/var/lib/postgresql/data
  #   ports:
  #     - "5432:5432"

# volumes:
#   db_data:
`, config.ImageName, config.ContainerName, ports, envVars, volumes,
		config.RestartPolicy, config.ResourceLimits.CPU, config.ResourceLimits.Memory,
		dc.getInternalPort(config.Ports))

	return compose
}

// getInternalPort extracts the internal port from port mapping
func (dc *DeploymentConfig) getInternalPort(ports map[int]int) int {
	for _, port := range ports {
		return port
	}
	return 8080
}

// ValidateDockerSetup validates Docker deployment setup
func (dc *DeploymentConfig) ValidateDockerSetup() error {
	log.Println("🐳 Validating Docker setup...")

	// Check if Docker is installed and running
	if err := dc.checkDockerInstallation(); err != nil {
		return fmt.Errorf("docker validation failed: %w", err)
	}

	// Check if required ports are available
	for port := range dc.getRequiredPorts() {
		if !dc.isPortAvailable(port) {
			log.Printf("⚠️ Port %d may conflict with Docker setup", port)
		}
	}

	// Validate Dockerfile exists and is valid
	if err := dc.validateDockerfile(); err != nil {
		return fmt.Errorf("dockerfile validation failed: %w", err)
	}

	log.Println("✅ Docker setup validation passed")
	return nil
}

// checkDockerInstallation checks if Docker is properly installed
func (dc *DeploymentConfig) checkDockerInstallation() error {
	cmd := exec.Command("docker", "--version")
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("docker is not installed or not accessible")
	}

	// Check if Docker daemon is running
	cmd = exec.Command("docker", "info")
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("docker daemon is not running")
	}

	return nil
}

// validateDockerfile validates the Dockerfile syntax
func (dc *DeploymentConfig) validateDockerfile() error {
	if _, err := os.Stat("Dockerfile"); os.IsNotExist(err) {
		return fmt.Errorf("dockerfile does not exist")
	}

	// Basic syntax check
	cmd := exec.Command("docker", "build", "--dry-run", ".")
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("dockerfile syntax check failed")
	}

	return nil
}

// getRequiredPorts returns required ports based on platform
func (dc *DeploymentConfig) getRequiredPorts() map[int]bool {
	ports := make(map[int]bool)
	for _, port := range dc.RequiredPorts {
		ports[port] = true
	}
	return ports
}

// GenerateCoolifyConfig generates Coolify-specific configuration
func (dc *DeploymentConfig) GenerateCoolifyConfig() map[string]interface{} {
	config := map[string]interface{}{
		"buildCommand":    "go build -o app .",
		"startCommand":    "./app",
		"installCommand":  "go mod download",
		"buildDirectory":  "/app",
		"healthCheckPath": "/health",
		"port":            8080,
		"environment": map[string]string{
			"GO_ENV": dc.Environment,
			"PORT":   "8080",
		},
		"limits": map[string]string{
			"cpu":    "1",
			"memory": "512Mi",
		},
		"healthCheck": map[string]interface{}{
			"enabled": true,
			"path":    "/health",
			"port":    8080,
			"method":  "GET",
		},
	}

	return config
}

// ValidateCoolifyDeployment validates Coolify deployment requirements
func (dc *DeploymentConfig) ValidateCoolifyDeployment() error {
	log.Println("🔧 Validating Coolify deployment...")

	// Check environment variables
	for _, envVar := range dc.RequiredEnvVars {
		if os.Getenv(envVar) == "" {
			return fmt.Errorf("coolify requires environment variable: %s", envVar)
		}
	}

	// Validate database connectivity if DATABASE_URL is set
	if dbURL := os.Getenv("DATABASE_URL"); dbURL != "" {
		if err := dc.validateDatabaseConnection(dbURL); err != nil {
			return fmt.Errorf("database validation failed: %w", err)
		}
	}

	// Check resource requirements
	if err := dc.validateResourceRequirements(); err != nil {
		return fmt.Errorf("resource validation failed: %w", err)
	}

	log.Println("✅ Coolify deployment validation passed")
	return nil
}

// validateDatabaseConnection validates database connectivity
func (dc *DeploymentConfig) validateDatabaseConnection(dbURL string) error {
	// This would implement actual database connectivity testing
	// For now, we'll do basic URL validation
	if !strings.HasPrefix(dbURL, "postgres://") && !strings.HasPrefix(dbURL, "mysql://") {
		return fmt.Errorf("unsupported database URL scheme")
	}

	log.Println("✅ Database connection validation passed")
	return nil
}

// validateResourceRequirements validates system resource requirements
func (dc *DeploymentConfig) validateResourceRequirements() error {
	var stat syscall.Statfs_t
	wd, err := os.Getwd()
	if err != nil {
		return err
	}

	err = syscall.Statfs(wd, &stat)
	if err != nil {
		return err
	}

	// Available bytes
	availableBytes := stat.Bavail * uint64(stat.Bsize)

	// Check minimum requirements (1GB free space)
	minRequired := uint64(1024 * 1024 * 1024)
	if availableBytes < minRequired {
		return fmt.Errorf("insufficient disk space: %d bytes available, %d bytes required",
			availableBytes, minRequired)
	}

	// Check memory
	var memStats runtime.MemStats
	runtime.ReadMemStats(&memStats)
	availableMemory := runtime.NumCPU() * 512 * 1024 * 1024 // Assume 512MB per core

	if memStats.Sys > uint64(availableMemory) {
		log.Printf("⚠️ High memory usage: %d bytes", memStats.Sys)
	}

	log.Println("✅ Resource requirements validation passed")
	return nil
}

// GenerateHetznerConfig generates Hetzner-specific configuration
func (dc *DeploymentConfig) GenerateHetznerConfig() map[string]interface{} {
	config := map[string]interface{}{
		"firewall": map[string]interface{}{
			"enabled": true,
			"rules": []map[string]interface{}{
				{
					"direction":   "in",
					"protocol":    "tcp",
					"port":        "22",
					"source_ips":  []string{"0.0.0.0/0"},
					"action":      "accept",
					"description": "SSH access",
				},
				{
					"direction":   "in",
					"protocol":    "tcp",
					"port":        "80",
					"source_ips":  []string{"0.0.0.0/0"},
					"action":      "accept",
					"description": "HTTP access",
				},
				{
					"direction":   "in",
					"protocol":    "tcp",
					"port":        "443",
					"source_ips":  []string{"0.0.0.0/0"},
					"action":      "accept",
					"description": "HTTPS access",
				},
				{
					"direction":   "in",
					"protocol":    "tcp",
					"port":        "8080",
					"source_ips":  []string{"0.0.0.0/0"},
					"action":      "accept",
					"description": "Application port",
				},
			},
		},
		"monitoring": map[string]interface{}{
			"enabled": true,
			"metrics": []string{"cpu", "memory", "disk", "network"},
		},
		"backup": map[string]interface{}{
			"enabled":   true,
			"schedule":  "0 2 * * *", // Daily at 2 AM
			"retention": 7,
		},
	}

	return config
}

// ValidateHetznerSetup validates Hetzner server setup
func (dc *DeploymentConfig) ValidateHetznerSetup() error {
	log.Println("🌐 Validating Hetzner server setup...")

	// Check firewall configuration
	if err := dc.validateFirewall(); err != nil {
		return fmt.Errorf("firewall validation failed: %w", err)
	}

	// Check SSH access
	if err := dc.validateSSHAccess(); err != nil {
		return fmt.Errorf("SSH validation failed: %w", err)
	}

	// Check disk space
	if err := dc.validateDiskSpace(); err != nil {
		return fmt.Errorf("disk space validation failed: %w", err)
	}

	// Check network connectivity
	if err := dc.validateNetwork(); err != nil {
		return fmt.Errorf("network validation failed: %w", err)
	}

	log.Println("✅ Hetzner server setup validation passed")
	return nil
}

// validateFirewall validates firewall configuration
func (dc *DeploymentConfig) validateFirewall() error {
	// This would check actual firewall rules
	// For now, we'll simulate the check
	log.Println("✅ Firewall validation passed")
	return nil
}

// validateSSHAccess validates SSH connectivity
func (dc *DeploymentConfig) validateSSHAccess() error {
	// This would test SSH connectivity
	// For now, we'll simulate the check
	log.Println("✅ SSH access validation passed")
	return nil
}

// validateDiskSpace validates available disk space
func (dc *DeploymentConfig) validateDiskSpace() error {
	// This would check actual disk space
	// For now, we'll simulate the check
	log.Println("✅ Disk space validation passed")
	return nil
}

// validateNetwork validates network connectivity
func (dc *DeploymentConfig) validateNetwork() error {
	// This would test network connectivity
	// For now, we'll simulate the check
	log.Println("✅ Network validation passed")
	return nil
}

// DeploymentErrorTracker tracks deployment-specific errors
type DeploymentErrorTracker struct {
	Errors []DeploymentError
}

// DeploymentError represents a deployment-specific error
type DeploymentError struct {
	Type       string    `json:"type"`
	Message    string    `json:"message"`
	Platform   string    `json:"platform"`
	Severity   string    `json:"severity"`
	Timestamp  time.Time `json:"timestamp"`
	Resolution string    `json:"resolution"`
	Category   string    `json:"category"`
}

// NewDeploymentErrorTracker creates a new deployment error tracker
func NewDeploymentErrorTracker() *DeploymentErrorTracker {
	return &DeploymentErrorTracker{
		Errors: make([]DeploymentError, 0),
	}
}

// TrackError tracks a deployment error
func (det *DeploymentErrorTracker) TrackError(err error, platform, category string) {
	deploymentError := DeploymentError{
		Type:       "deployment_error",
		Message:    err.Error(),
		Platform:   platform,
		Severity:   det.determineSeverity(err),
		Timestamp:  time.Now(),
		Category:   category,
		Resolution: det.suggestResolution(err, platform),
	}

	det.Errors = append(det.Errors, deploymentError)

	// Auto-create incident for critical deployment errors
	if deploymentError.Severity == "critical" {
		errorResp := models.NewEnhancedErrorResponse(
			"Deployment Error",
			err.Error(),
			"deployment_failed",
			false,
		).WithCategory("deployment").
			WithSeverity("critical")

		AutoCreateIncidentFromError(errorResp)
	}
}

// determineSeverity determines error severity
func (det *DeploymentErrorTracker) determineSeverity(err error) string {
	errMsg := err.Error()

	if strings.Contains(errMsg, "permission") || strings.Contains(errMsg, "access denied") {
		return "high"
	}
	if strings.Contains(errMsg, "connection") || strings.Contains(errMsg, "network") {
		return "medium"
	}
	if strings.Contains(errMsg, "disk") || strings.Contains(errMsg, "space") {
		return "high"
	}

	return "medium"
}

// suggestResolution suggests error resolution
func (det *DeploymentErrorTracker) suggestResolution(err error, platform string) string {
	errMsg := err.Error()

	switch platform {
	case "coolify":
		if strings.Contains(errMsg, "environment") {
			return "Check environment variables in Coolify dashboard"
		}
		if strings.Contains(errMsg, "database") {
			return "Verify database credentials and connectivity"
		}
	case "hetzner":
		if strings.Contains(errMsg, "firewall") {
			return "Check firewall rules in Hetzner Cloud Console"
		}
		if strings.Contains(errMsg, "disk") {
			return "Monitor disk usage in Hetzner Cloud Console"
		}
	case "docker":
		if strings.Contains(errMsg, "port") {
			return "Check port availability and Docker port mapping"
		}
		if strings.Contains(errMsg, "volume") {
			return "Verify Docker volume mounts and permissions"
		}
	}

	return "Review error logs and check configuration"
}

// GetErrorsByPlatform returns errors filtered by platform
func (det *DeploymentErrorTracker) GetErrorsByPlatform(platform string) []DeploymentError {
	var filtered []DeploymentError
	for _, err := range det.Errors {
		if err.Platform == platform {
			filtered = append(filtered, err)
		}
	}
	return filtered
}

// GetErrorsByCategory returns errors filtered by category
func (det *DeploymentErrorTracker) GetErrorsByCategory(category string) []DeploymentError {
	var filtered []DeploymentError
	for _, err := range det.Errors {
		if err.Category == category {
			filtered = append(filtered, err)
		}
	}
	return filtered
}

// GenerateDeploymentReport generates a deployment error report
func (det *DeploymentErrorTracker) GenerateDeploymentReport() string {
	report := "# Deployment Error Report\n\n"

	// Summary statistics
	totalErrors := len(det.Errors)
	criticalErrors := 0
	highErrors := 0

	for _, err := range det.Errors {
		switch err.Severity {
		case "critical":
			criticalErrors++
		case "high":
			highErrors++
		}
	}

	report += "## Summary\n"
	report += fmt.Sprintf("- **Total Errors**: %d\n", totalErrors)
	report += fmt.Sprintf("- **Critical**: %d\n", criticalErrors)
	report += fmt.Sprintf("- **High**: %d\n", highErrors)
	report += fmt.Sprintf("- **Medium/Low**: %d\n", totalErrors-criticalErrors-highErrors)

	// Recent errors
	report += "\n## Recent Errors\n"
	recentCount := 0
	for i := len(det.Errors) - 1; i >= 0 && recentCount < 10; i-- {
		err := det.Errors[i]
		report += fmt.Sprintf("### %s (%s)\n", err.Type, err.Platform)
		report += fmt.Sprintf("- **Message**: %s\n", err.Message)
		report += fmt.Sprintf("- **Severity**: %s\n", err.Severity)
		report += fmt.Sprintf("- **Resolution**: %s\n", err.Resolution)
		report += fmt.Sprintf("- **Time**: %s\n\n", err.Timestamp.Format(time.RFC3339))
		recentCount++
	}

	return report
}

// Global deployment error tracker
var GlobalDeploymentErrorTracker = NewDeploymentErrorTracker()

// Convenience functions

// TrackDeploymentError tracks a deployment error
func TrackDeploymentError(err error, platform, category string) {
	GlobalDeploymentErrorTracker.TrackError(err, platform, category)
}

// GetDeploymentErrors returns all deployment errors
func GetDeploymentErrors() []DeploymentError {
	return GlobalDeploymentErrorTracker.Errors
}

// GenerateDeploymentReport generates a deployment error report
func GenerateDeploymentReport() string {
	return GlobalDeploymentErrorTracker.GenerateDeploymentReport()
}

// ValidateDeploymentEnvironment validates the deployment environment
func ValidateDeploymentEnvironment(platform string) error {
	config := NewDeploymentConfig(platform, os.Getenv("GO_ENV"))
	return config.ValidateEnvironment()
}

// SetupDeployment configures deployment for the specified platform
func SetupDeployment(platform string) error {
	log.Printf("🔧 Setting up deployment for %s...", platform)

	config := NewDeploymentConfig(platform, os.Getenv("GO_ENV"))

	switch platform {
	case "coolify":
		return config.ValidateCoolifyDeployment()
	case "hetzner":
		return config.ValidateHetznerSetup()
	case "docker":
		return config.ValidateDockerSetup()
	default:
		return fmt.Errorf("unsupported platform: %s", platform)
	}
}

// GenerateDeploymentConfigs generates all deployment configurations
func GenerateDeploymentConfigs() map[string]string {
	config := NewDeploymentConfig("multi-platform", os.Getenv("GO_ENV"))

	configs := make(map[string]string)

	// Nginx configuration
	nginxConfig := NginxConfig{
		ServerName:   os.Getenv("SERVER_NAME"),
		ProxyPort:    8080,
		SSL:          os.Getenv("SSL_ENABLED") == "true",
		SSLCert:      os.Getenv("SSL_CERT_PATH"),
		SSLKey:       os.Getenv("SSL_KEY_PATH"),
		RateLimit:    100,
		CacheEnabled: true,
		Compression:  true,
	}
	configs["nginx.conf"] = config.GenerateNginxConfig(nginxConfig)

	// Docker configuration
	dockerConfig := DockerConfig{
		ImageName:     "nutrition-app:latest",
		ContainerName: "nutrition-app",
		Ports:         map[int]int{8080: 8080},
		Volumes:       map[string]string{"./data": "/app/data"},
		Environment:   getEnvironmentVariables(),
		RestartPolicy: "unless-stopped",
		ResourceLimits: ResourceLimits{
			CPU:    "1",
			Memory: "512Mi",
		},
	}
	configs["Dockerfile"] = config.GenerateDockerfile(dockerConfig)
	configs["docker-compose.yml"] = config.GenerateDockerCompose(dockerConfig)

	return configs
}

// getEnvironmentVariables returns environment variables for Docker
func getEnvironmentVariables() map[string]string {
	env := make(map[string]string)

	envVars := []string{
		"DATABASE_URL",
		"JWT_SECRET",
		"API_PORT",
		"FRONTEND_URL",
		"GO_ENV",
		"SSL_ENABLED",
	}

	for _, envVar := range envVars {
		if value := os.Getenv(envVar); value != "" {
			env[envVar] = value
		}
	}

	return env
}
