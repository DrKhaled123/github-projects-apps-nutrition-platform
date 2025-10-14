package handlers

import (
	"context"
	"database/sql"
	"fmt"
	"net/http"
	"os"
	"runtime"
	"time"

	"github.com/labstack/echo/v4"
)

type HealthResponse struct {
	Status    string            `json:"status"`
	Timestamp time.Time         `json:"timestamp"`
	Checks    map[string]string `json:"checks"`
	Uptime    string            `json:"uptime,omitempty"`
}

var startTime = time.Now()

func HealthCheckHandler(db *sql.DB) echo.HandlerFunc {
	return func(c echo.Context) error {
		checks := make(map[string]string)
		overallStatus := "healthy"

		// Check database connection with retry
		ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		defer cancel()

		dbHealthy := false
		for retries := 0; retries < 3 && !dbHealthy; retries++ {
			if err := db.PingContext(ctx); err != nil {
				time.Sleep(time.Duration(retries+1) * 100 * time.Millisecond)
				continue
			}
			dbHealthy = true
		}

		if !dbHealthy {
			checks["database"] = "unhealthy: connection failed after retries"
			overallStatus = "unhealthy"
		} else {
			checks["database"] = "healthy"
		}

		// Check file system permissions with absolute path
		testFile := "/app/data/health_check.tmp"
		if err := os.WriteFile(testFile, []byte("health_check"), 0644); err != nil {
			checks["filesystem"] = "unhealthy: " + err.Error()
			overallStatus = "unhealthy"
		} else {
			os.Remove(testFile)
			checks["filesystem"] = "healthy"
		}

		// Check memory usage
		var memStats runtime.MemStats
		runtime.ReadMemStats(&memStats)
		memoryMB := memStats.Alloc / 1024 / 1024
		checks["memory"] = fmt.Sprintf("healthy: %d MB used", memoryMB)

		// Check uptime
		uptime := time.Since(startTime).Round(time.Second).String()
		checks["uptime"] = fmt.Sprintf("healthy: %s", uptime)

		response := HealthResponse{
			Status:    overallStatus,
			Timestamp: time.Now(),
			Checks:    checks,
			Uptime:    uptime,
		}

		if overallStatus != "healthy" {
			return c.JSON(http.StatusServiceUnavailable, response)
		}
		return c.JSON(http.StatusOK, response)
	}
}

// DetailedHealthCheckHandler performs comprehensive health check with integration monitoring
func DetailedHealthCheckHandler(db *sql.DB) echo.HandlerFunc {
	return func(c echo.Context) error {
		checks := make(map[string]string)
		overallStatus := "healthy"

		// Check database
		ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		defer cancel()

		dbHealthy := false
		for retries := 0; retries < 3 && !dbHealthy; retries++ {
			if err := db.PingContext(ctx); err != nil {
				time.Sleep(time.Duration(retries+1) * 100 * time.Millisecond)
				continue
			}
			dbHealthy = true
		}

		if !dbHealthy {
			checks["database"] = "unhealthy: connection failed"
			overallStatus = "unhealthy"
		} else {
			checks["database"] = "healthy"
		}

		// Check filesystem
		testFile := "/app/data/health_check.tmp"
		if err := os.WriteFile(testFile, []byte("test"), 0644); err != nil {
			checks["filesystem"] = "degraded: " + err.Error()
			if overallStatus == "healthy" {
				overallStatus = "degraded"
			}
		} else {
			os.Remove(testFile)
			checks["filesystem"] = "healthy"
		}

		// Check VIP data files
		vipFiles := []string{"vip-drugs-nutrition.js", "data/vip-drugs-nutrition.js"}
		vipFound := false
		for _, file := range vipFiles {
			if _, err := os.Stat(file); err == nil {
				vipFound = true
				break
			}
		}
		if vipFound {
			checks["vip_integration"] = "healthy"
		} else {
			checks["vip_integration"] = "degraded: data files not found"
			if overallStatus == "healthy" {
				overallStatus = "degraded"
			}
		}

		// Check enhanced health data files
		enhancedFiles := []string{"enhanced-health-data.json", "data/enhanced-health-data.json"}
		enhancedFound := false
		for _, file := range enhancedFiles {
			if _, err := os.Stat(file); err == nil {
				enhancedFound = true
				break
			}
		}
		if enhancedFound {
			checks["enhanced_health"] = "healthy"
		} else {
			checks["enhanced_health"] = "degraded: data files not found"
			if overallStatus == "healthy" {
				overallStatus = "degraded"
			}
		}

		// Check comprehensive data
		comprehensiveFiles := []string{"comprehensive-health-data.json", "data/comprehensive-health-data.json"}
		comprehensiveFound := false
		for _, file := range comprehensiveFiles {
			if _, err := os.Stat(file); err == nil {
				comprehensiveFound = true
				break
			}
		}
		if comprehensiveFound {
			checks["comprehensive_data"] = "healthy"
		} else {
			checks["comprehensive_data"] = "degraded: data files not found"
			if overallStatus == "healthy" {
				overallStatus = "degraded"
			}
		}

		// Check data directory
		dataDir := "./data"
		if stat, err := os.Stat(dataDir); err != nil {
			checks["data_directory"] = "degraded: " + err.Error()
			if overallStatus == "healthy" {
				overallStatus = "degraded"
			}
		} else if !stat.IsDir() {
			checks["data_directory"] = "unhealthy: not a directory"
			overallStatus = "unhealthy"
		} else {
			checks["data_directory"] = "healthy"
		}

		// Check memory
		var memStats runtime.MemStats
		runtime.ReadMemStats(&memStats)
		memoryMB := memStats.Alloc / 1024 / 1024
		checks["memory"] = fmt.Sprintf("healthy: %d MB used", memoryMB)

		// Uptime
		uptime := time.Since(startTime).Round(time.Second).String()

		response := HealthResponse{
			Status:    overallStatus,
			Timestamp: time.Now(),
			Checks:    checks,
			Uptime:    uptime,
		}

		statusCode := http.StatusOK
		if overallStatus == "unhealthy" {
			statusCode = http.StatusServiceUnavailable
		}

		return c.JSON(statusCode, response)
	}
}

// ReadinessCheckHandler checks if the service is ready to accept traffic
func ReadinessCheckHandler(db *sql.DB) echo.HandlerFunc {
	return func(c echo.Context) error {
		// Check database connectivity
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()

		if err := db.PingContext(ctx); err != nil {
			return c.JSON(http.StatusServiceUnavailable, map[string]interface{}{
				"status":  "not_ready",
				"message": "Database not available",
			})
		}

		return c.JSON(http.StatusOK, map[string]interface{}{
			"status":  "ready",
			"message": "Service is ready to accept traffic",
		})
	}
}
