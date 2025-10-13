# Q30S Implementation Guide: Practical Examples

## Overview

This guide provides practical implementation examples of the Q30S hybrid approach, demonstrating how to apply these principles in real-world scenarios.

## 1. Simple Automation Strategy

### Makefile-Based Approach (Preferred)

```bash
# Makefile.simple - Q30S Automation Strategy
.PHONY: build test deploy health logs

# Build application
build:
	go mod tidy
	go build -o bin/app main.go

# Run tests
test:
	go test ./...

# Deploy with health check
deploy: build
	@echo "Deploying application..."
	-pkill -f app || true
	nohup ./bin/app > app.log 2>&1 &
	@sleep 3
	@make health

# Health check
health:
	@curl -f http://localhost:8080/health || exit 1

# View logs
logs:
	tail -f app.log
```

### Usage Examples

```bash
# Build and test
make build
make test

# Deploy with verification
make deploy

# Monitor in production
make logs
make health
```

## 2. Configuration Management

### Simple Configuration Pattern

```json
// config.simple.json
{
  "app": {
    "name": "nutrition-api",
    "port": 8080,
    "environment": "development"
  },
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "nutrition_db",
    "ssl_mode": "disable"
  },
  "security": {
    "jwt_secret": "${JWT_SECRET}",
    "rate_limit": 100
  }
}
```

### Configuration Loader

```go
// internal/config/simple_loader.go
package config

import (
    "encoding/json"
    "os"
    "strconv"
)

type SimpleConfig struct {
    App      AppConfig      `json:"app"`
    Database DatabaseConfig `json:"database"`
    Security SecurityConfig `json:"security"`
}

type AppConfig struct {
    Name        string `json:"name"`
    Port        int    `json:"port"`
    Environment string `json:"environment"`
}

type DatabaseConfig struct {
    Host     string `json:"host"`
    Port     int    `json:"port"`
    Name     string `json:"name"`
    Username string `json:"username"`
    SSLMode  string `json:"ssl_mode"`
}

type SecurityConfig struct {
    JWTSecret  string `json:"jwt_secret"`
    RateLimit  int    `json:"rate_limit"`
}

func LoadSimpleConfig() (*SimpleConfig, error) {
    file, err := os.Open("config.simple.json")
    if err != nil {
        return nil, err
    }
    defer file.Close()

    var config SimpleConfig
    if err := json.NewDecoder(file).Decode(&config); err != nil {
        return nil, err
    }

    // Override with environment variables
    if port := os.Getenv("PORT"); port != "" {
        if p, err := strconv.Atoi(port); err == nil {
            config.App.Port = p
        }
    }

    if secret := os.Getenv("JWT_SECRET"); secret != "" {
        config.Security.JWTSecret = secret
    }

    return &config, nil
}
```

## 3. Monitoring Strategy

### Simple Monitoring Implementation

```go
// internal/monitoring/simple_monitor.go
package monitoring

import (
    "fmt"
    "log"
    "net/http"
    "runtime"
    "time"
)

type SimpleMonitor struct {
    logger    *log.Logger
    startTime time.Time
}

func NewSimpleMonitor() *SimpleMonitor {
    return &SimpleMonitor{
        logger:    log.New(os.Stdout, "[MONITOR] ", log.LstdFlags),
        startTime: time.Now(),
    }
}

func (m *SimpleMonitor) Middleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()

        // Create response writer wrapper
        rw := &responseWriter{ResponseWriter: w, statusCode: 200}

        next.ServeHTTP(rw, r)

        duration := time.Since(start)
        m.logger.Printf("REQUEST: %s %s | %v | %d",
            r.Method, r.URL.Path, duration, rw.statusCode)
    })
}

func (m *SimpleMonitor) HealthCheck(w http.ResponseWriter, r *http.Request) {
    var mem runtime.MemStats
    runtime.ReadMemStats(&mem)

    uptime := time.Since(m.startTime)

    w.Header().Set("Content-Type", "application/json")
    fmt.Fprintf(w, `{
        "status": "healthy",
        "uptime": "%s",
        "goroutines": %d,
        "memory_usage": "%d KB"
    }`, uptime.String(), runtime.NumGoroutine(), mem.Alloc/1024)
}

type responseWriter struct {
    http.ResponseWriter
    statusCode int
}

func (rw *responseWriter) WriteHeader(code int) {
    rw.statusCode = code
    rw.ResponseWriter.WriteHeader(code)
}
```

## 4. Dependency Injection Pattern

### Constructor Injection Example

```go
// internal/services/simple_service.go
package services

import (
    "context"
    "database/sql"
    "log"
)

// Database interface (simple abstraction)
type Database interface {
    QueryContext(ctx context.Context, query string, args ...interface{}) (*sql.Rows, error)
    ExecContext(ctx context.Context, query string, args ...interface{}) (sql.Result, error)
    Close() error
}

// Logger interface (simple abstraction)
type Logger interface {
    Printf(format string, v ...interface{})
    Println(v ...interface{})
}

// SimpleService demonstrates constructor injection
type SimpleService struct {
    db     Database
    logger Logger
}

// NewSimpleService creates service with injected dependencies
func NewSimpleService(db Database, logger Logger) *SimpleService {
    return &SimpleService{
        db:     db,
        logger: logger,
    }
}

func (s *SimpleService) DoWork(ctx context.Context) error {
    s.logger.Printf("Starting work...")

    // Use database through interface
    rows, err := s.db.QueryContext(ctx, "SELECT 1")
    if err != nil {
        s.logger.Printf("Database error: %v", err)
        return err
    }
    defer rows.Close()

    s.logger.Printf("Work completed successfully")
    return nil
}
```

### Usage Example

```go
// In main.go or wherever you wire up dependencies
db := sql.Open("postgres", connectionString)
logger := log.New(os.Stdout, "[APP] ", log.LstdFlags)

service := NewSimpleService(db, logger)

// Easy to test with mocks
mockDB := &MockDatabase{}
mockLogger := &MockLogger{}
testService := NewSimpleService(mockDB, mockLogger)
```

## 5. Testing Strategy

### Simple Unit Tests

```go
// internal/services/simple_service_test.go
package services

import (
    "context"
    "testing"
)

// MockDatabase for testing
type MockDatabase struct {
    queryResult *sql.Rows
    queryError  error
}

func (m *MockDatabase) QueryContext(ctx context.Context, query string, args ...interface{}) (*sql.Rows, error) {
    return m.queryResult, m.queryError
}

func (m *MockDatabase) ExecContext(ctx context.Context, query string, args ...interface{}) (sql.Result, error) {
    return nil, nil
}

func (m *MockDatabase) Close() error {
    return nil
}

// Test constructor injection
func TestSimpleService_DoWork_Success(t *testing.T) {
    mockDB := &MockDatabase{
        queryError: nil,
    }

    mockLogger := &MockLogger{
        messages: []string{},
    }

    service := NewSimpleService(mockDB, mockLogger)

    err := service.DoWork(context.Background())
    if err != nil {
        t.Fatalf("Expected no error, got %v", err)
    }

    if len(mockLogger.messages) == 0 {
        t.Error("Expected log messages to be written")
    }
}

func TestSimpleService_DoWork_DatabaseError(t *testing.T) {
    mockDB := &MockDatabase{
        queryError: fmt.Errorf("database connection failed"),
    }

    mockLogger := &MockLogger{}
    service := NewSimpleService(mockDB, mockLogger)

    err := service.DoWork(context.Background())
    if err == nil {
        t.Error("Expected error, got nil")
    }
}
```

## 6. Benchmarking Strategy

### Simple Performance Tests

```go
// internal/services/simple_benchmark_test.go
package services

import (
    "context"
    "testing"
)

func BenchmarkSimpleService_DoWork(b *testing.B) {
    service := NewSimpleService(&MockDatabase{}, &MockLogger{})

    b.ResetTimer()
    b.ReportAllocs()

    for i := 0; i < b.N; i++ {
        service.DoWork(context.Background())
    }
}

// Benchmark with different scenarios
func BenchmarkSimpleService_DoWork_WithDatabaseCall(b *testing.B) {
    // Setup more realistic mock
    mockDB := &MockDatabase{
        queryError: nil,
    }

    service := NewSimpleService(mockDB, &MockLogger{})

    b.ResetTimer()
    b.ReportAllocs()

    for i := 0; i < b.N; i++ {
        service.DoWork(context.Background())
    }
}

// Memory usage benchmark
func TestSimpleService_MemoryUsage(t *testing.T) {
    service := NewSimpleService(&MockDatabase{}, &MockLogger{})

    // This is a simplified example
    // In practice, you'd use more sophisticated memory tracking
    for i := 0; i < 1000; i++ {
        service.DoWork(context.Background())
    }

    t.Log("Memory test completed")
}
```

## 7. Error Handling Strategy

### Simple Error Handling Pattern

```go
// internal/errors/simple_errors.go
package errors

import (
    "fmt"
    "log"
)

// AppError represents application errors
type AppError struct {
    Code    string `json:"code"`
    Message string `json:"message"`
    Cause   error  `json:"-"`
}

func (e *AppError) Error() string {
    if e.Cause != nil {
        return fmt.Sprintf("%s: %v", e.Message, e.Cause)
    }
    return e.Message
}

func (e *AppError) Unwrap() error {
    return e.Cause
}

// Error codes
const (
    ErrCodeValidation    = "VALIDATION_ERROR"
    ErrCodeDatabase      = "DATABASE_ERROR"
    ErrCodeNotFound      = "NOT_FOUND"
    ErrCodeUnauthorized  = "UNAUTHORIZED"
    ErrCodeInternal      = "INTERNAL_ERROR"
)

// Helper functions for creating errors
func NewValidationError(message string, cause error) *AppError {
    return &AppError{
        Code:    ErrCodeValidation,
        Message: message,
        Cause:   cause,
    }
}

func NewDatabaseError(message string, cause error) *AppError {
    return &AppError{
        Code:    ErrCodeDatabase,
        Message: message,
        Cause:   cause,
    }
}

func NewNotFoundError(resource string) *AppError {
    return &AppError{
        Code:    ErrCodeNotFound,
        Message: fmt.Sprintf("%s not found", resource),
    }
}

// Simple error handler middleware
func SimpleErrorHandler(logger *log.Logger) func(error) {
    return func(err error) {
        var appErr *AppError
        if errors.As(err, &appErr) {
            logger.Printf("ERROR [%s]: %s", appErr.Code, appErr.Message)
            if appErr.Cause != nil {
                logger.Printf("CAUSE: %v", appErr.Cause)
            }
        } else {
            logger.Printf("UNEXPECTED ERROR: %v", err)
        }
    }
}
```

## 8. Implementation Checklist

### Phase 1: Foundation ✅
- [x] Simple Makefile for automation
- [x] Basic configuration management
- [x] Constructor injection pattern
- [x] Simple logging setup
- [x] Basic error handling

### Phase 2: Enhancement (Next)
- [ ] Environment-based configuration
- [ ] Structured logging with levels
- [ ] Basic performance benchmarks
- [ ] Input validation helpers
- [ ] Simple health checks

### Phase 3: Production Ready (Future)
- [ ] Configuration validation
- [ ] Metrics collection
- [ ] Request tracing
- [ ] Circuit breaker pattern
- [ ] Graceful shutdown

## 9. Best Practices Summary

### What to Avoid (Initially)
- ❌ Complex multi-agent systems
- ❌ Over-engineered configuration management
- ❌ Heavy monitoring stacks
- ❌ Complex DI frameworks
- ❌ Extensive benchmarking suites

### What to Embrace
- ✅ Simple shell scripts and Makefiles
- ✅ Single configuration files
- ✅ Constructor injection
- ✅ Basic logging to stdout
- ✅ Go's built-in testing tools

### When to Add Complexity
Add complexity only when:
1. **Pain threshold reached**: Current solution causes real problems
2. **Clear benefit**: New complexity solves specific issues
3. **Simple first**: Try simple solutions before complex ones
4. **Incremental approach**: Add complexity gradually

## 10. Migration Strategy

### From Complex to Simple

```go
// Before: Complex DI framework
type Service struct {
    // Complex dependency injection with reflection
}

// After: Simple constructor injection
type Service struct {
    db     Database
    logger Logger
}

func NewService(db Database, logger Logger) *Service {
    return &Service{db: db, logger: logger}
}
```

### From Complex Monitoring

```go
// Before: Complex monitoring stack
// Prometheus, Grafana, Jaeger, etc.

// After: Simple logging
logger.Printf("REQUEST: %s %s | %v | %d",
    method, path, duration, statusCode)
```

## Conclusion

The Q30S approach is about **strategic simplicity**. Start simple, validate that it works, and only add complexity when you have clear evidence that it's needed. This approach reduces maintenance burden, speeds up development, and often results in more reliable systems.

**Key Principle:** "Make it work, make it right, make it fast" - but only add "right" and "fast" when "work" isn't sufficient anymore.
