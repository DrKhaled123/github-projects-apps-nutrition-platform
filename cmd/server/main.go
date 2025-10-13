// cmd/server/main.go
package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"time"

	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"

	"yourproject/pkg/quota"
	"yourproject/pkg/ratelimit"
	"yourproject/pkg/session"
)

func main() {
	// Create Echo instance
	e := echo.New()

	// Basic middleware
	e.Use(middleware.Logger())
	e.Use(middleware.Recover())

	// Initialize rate limiter
	rateLimiterConfig := &ratelimit.Config{
		RequestsPerMinute: 60,
		BurstSize:         10,
		CleanupInterval:   time.Minute,
		MaxIdleTime:       5 * time.Minute,
		EnableHTTPSOnly:   false, // Set true in production
		TrustedProxies:    []string{"127.0.0.1"},
		EnableMetrics:     true,
		MetricsCallback: func(event ratelimit.MetricEvent) {
			if !event.Allowed {
				log.Printf("[RateLimit] User %s blocked, retry in %v",
					event.UserID, event.RetryAfter)
			}
		},
	}

	rateLimiter := ratelimit.NewUnifiedRateLimiter(rateLimiterConfig)
	defer rateLimiter.Shutdown()

	// Apply rate limiting
	e.Use(rateLimiter.Middleware())

	// Initialize quota manager (Redis in production)
	quotaStorage := quota.NewMemoryStorage()
	// quotaStorage := quota.NewRedisStorage("localhost:6379", "", 0)

	quotaConfig := &quota.QuotaConfig{
		MonthlyLimit:    1000,
		StorageBackend:  quotaStorage,
		CleanupInterval: time.Hour,
	}

	quotaManager := quota.NewQuotaManager(quotaConfig)
	defer quotaManager.Shutdown()

	// Initialize cookie manager
	cookieConfig := &session.CookieConfig{
		Name:       "anon_id",
		Path:       "/",
		MaxAge:     86400 * 365,
		HttpOnly:   true,
		SameSite:   http.SameSiteLaxMode,
		AutoDetect: true,
	}

	cookieManager := session.NewCookieManager(cookieConfig)

	// Routes
	e.GET("/api/generate", func(c echo.Context) error {
		ctx := c.Request().Context()

		// Get or create anonymous ID
		anonID, err := cookieManager.GetOrCreate(c)
		if err != nil {
			return echo.NewHTTPError(http.StatusInternalServerError,
				"Failed to create session")
		}

		// Check quota
		allowed, current, limit, resetAt, err := quotaManager.Check(ctx, anonID)
		if err != nil {
			return echo.NewHTTPError(http.StatusInternalServerError,
				"Failed to check quota")
		}

		// Set quota headers
		c.Response().Header().Set("X-Quota-Limit", fmt.Sprintf("%d", limit))
		c.Response().Header().Set("X-Quota-Remaining", fmt.Sprintf("%d", limit-current))
		c.Response().Header().Set("X-Quota-Reset", resetAt.Format(time.RFC3339))

		if !allowed {
			return echo.NewHTTPError(http.StatusTooManyRequests,
				"Monthly quota exceeded")
		}

		// Consume quota
		if err := quotaManager.Consume(ctx, anonID); err != nil {
			return echo.NewHTTPError(http.StatusInternalServerError,
				"Failed to update quota")
		}

		// Your business logic here
		return c.JSON(http.StatusOK, map[string]interface{}{
			"result": "success",
			"quota": map[string]interface{}{
				"used":      current + 1,
				"limit":     limit,
				"remaining": limit - current - 1,
				"resetAt":   resetAt,
			},
		})
	})

	// Stats endpoint
	e.GET("/api/stats", func(c echo.Context) error {
		return c.JSON(http.StatusOK, rateLimiter.Stats())
	})

	// Graceful shutdown
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()

	go func() {
		if err := e.Start(":8080"); err != nil && err != http.ErrServerClosed {
			log.Fatal(err)
		}
	}()

	log.Println("Server starting on :8080")
	log.Println("Rate limiter initialized with 60 requests/minute limit")

	<-ctx.Done()
	log.Println("Shutting down gracefully...")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := e.Shutdown(shutdownCtx); err != nil {
		log.Fatal(err)
	}
}
