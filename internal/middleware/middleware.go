package middleware

import (
	"net/http"
	"os"
	"strings"
	"time"

	"api-key-generator/internal/config"

	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
	"golang.org/x/time/rate"
)

// Security adds security headers
func Security() echo.MiddlewareFunc {
	return func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			// Security headers
			c.Response().Header().Set("X-Content-Type-Options", "nosniff")
			c.Response().Header().Set("X-Frame-Options", "DENY")
			c.Response().Header().Set("X-XSS-Protection", "1; mode=block")
			c.Response().Header().Set("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
			c.Response().Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")
			c.Response().Header().Set("Content-Security-Policy", "default-src 'self'")

			return next(c)
		}
	}
}

// RateLimit adds rate limiting
func RateLimit(cfg *config.Config) echo.MiddlewareFunc {
	return middleware.RateLimiter(middleware.NewRateLimiterMemoryStore(
		rate.Limit(float64(cfg.Security.RateLimitRequests) / cfg.Security.RateLimitWindow.Seconds()),
	))
}

// APIKeyAuth validates API keys
func APIKeyAuth() echo.MiddlewareFunc {
	return func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			// Extract API key from header
			apiKey := c.Request().Header.Get("X-API-Key")
			if apiKey == "" {
				return echo.NewHTTPError(http.StatusUnauthorized, "API key is required")
			}

			// Store API key in context for handler validation
			c.Set("api_key", apiKey)

			return next(c)
		}
	}
}

// CORS configures CORS with secure defaults
func CORS() echo.MiddlewareFunc {
	// Get allowed origins from environment or use secure defaults
	allowedOrigins := []string{
		"http://localhost:3000",
		"http://localhost:8080",
		"https://super.doctorhealthy1.com",
		"https://api.doctorhealthy1.com",
		"https://doctorhealthy1.com",
	}

	// Allow additional origins from environment if specified
	if envOrigins := os.Getenv("CORS_ORIGINS"); envOrigins != "" {
		envList := strings.Split(envOrigins, ",")
		for _, origin := range envList {
			origin = strings.TrimSpace(origin)
			if origin != "" {
				allowedOrigins = append(allowedOrigins, origin)
			}
		}
	}

	return middleware.CORSWithConfig(middleware.CORSConfig{
		AllowOrigins: allowedOrigins,
		AllowMethods: []string{http.MethodGet, http.MethodPost, http.MethodPut, http.MethodDelete, http.MethodOptions},
		AllowHeaders: []string{echo.HeaderOrigin, echo.HeaderContentType, echo.HeaderAccept, echo.HeaderAuthorization, "X-API-Key"},
		MaxAge:       int(12 * time.Hour / time.Second),
	})
}

// RequestID adds request ID to context
func RequestID() echo.MiddlewareFunc {
	return middleware.RequestID()
}

// Logger configures structured logging
func Logger() echo.MiddlewareFunc {
	return middleware.LoggerWithConfig(middleware.LoggerConfig{
		Format: `{"time":"${time_rfc3339}","id":"${id}","remote_ip":"${remote_ip}","host":"${host}","method":"${method}","uri":"${uri}","user_agent":"${user_agent}","status":${status},"error":"${error}","latency":${latency},"latency_human":"${latency_human}","bytes_in":${bytes_in},"bytes_out":${bytes_out}}` + "\n",
	})
}

// Recover recovers from panics
func Recover() echo.MiddlewareFunc {
	return middleware.Recover()
}
