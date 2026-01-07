package utils

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"runtime"
	"time"
)

// SimpleMonitor provides basic monitoring capabilities
// Q30S Approach: Start with simple logging instead of complex monitoring stack
type SimpleMonitor struct {
	logger    *log.Logger
	startTime time.Time
}

// NewSimpleMonitor creates a new simple monitor
func NewSimpleMonitor() *SimpleMonitor {
	return &SimpleMonitor{
		logger:    log.New(os.Stdout, "[MONITOR] ", log.LstdFlags),
		startTime: time.Now(),
	}
}

// LogRequest logs HTTP request information
func (m *SimpleMonitor) LogRequest(r *http.Request, duration time.Duration, statusCode int) {
	m.logger.Printf("REQUEST: %s %s | %v | %d | %s",
		r.Method, r.URL.Path, duration, statusCode, r.UserAgent())
}

// LogError logs application errors
func (m *SimpleMonitor) LogError(err error, context string) {
	m.logger.Printf("ERROR in %s: %v", context, err)
}

// LogInfo logs general information
func (m *SimpleMonitor) LogInfo(message string) {
	m.logger.Printf("INFO: %s", message)
}

// GetSystemInfo returns basic system information
func (m *SimpleMonitor) GetSystemInfo() map[string]interface{} {
	var memStats runtime.MemStats
	runtime.ReadMemStats(&memStats)

	return map[string]interface{}{
		"uptime":        time.Since(m.startTime).String(),
		"goroutines":    runtime.NumGoroutine(),
		"memory_alloc":  fmt.Sprintf("%d KB", memStats.Alloc/1024),
		"memory_total":  fmt.Sprintf("%d KB", memStats.TotalAlloc/1024),
		"memory_system": fmt.Sprintf("%d KB", memStats.Sys/1024),
		"gc_count":      memStats.NumGC,
	}
}

// HealthCheck performs a basic health check
func (m *SimpleMonitor) HealthCheck(w http.ResponseWriter, r *http.Request) {
	info := m.GetSystemInfo()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)

	fmt.Fprintf(w, `{
		"status": "healthy",
		"timestamp": "%s",
		"uptime": "%s",
		"system_info": {
			"goroutines": %d,
			"memory_usage": "%s"
		}
	}`, time.Now().Format(time.RFC3339), info["uptime"], info["goroutines"], info["memory_alloc"])
}

// Middleware returns HTTP middleware for request monitoring
func (m *SimpleMonitor) Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()

		// Create a response writer that captures status code
		rw := &responseWriter{ResponseWriter: w, statusCode: http.StatusOK}

		next.ServeHTTP(rw, r)

		duration := time.Since(start)
		m.LogRequest(r, duration, rw.statusCode)
	})
}

// responseWriter wraps http.ResponseWriter to capture status code
type responseWriter struct {
	http.ResponseWriter
	statusCode int
}

func (rw *responseWriter) WriteHeader(code int) {
	rw.statusCode = code
	rw.ResponseWriter.WriteHeader(code)
}
