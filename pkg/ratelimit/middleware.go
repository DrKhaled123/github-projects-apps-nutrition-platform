// pkg/ratelimit/middleware.go
package ratelimit

import (
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/labstack/echo/v4"
)

// Middleware returns Echo middleware for rate limiting
func (rl *UnifiedRateLimiter) Middleware() echo.MiddlewareFunc {
	return func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			// Extract user ID (multiple strategies)
			userID := rl.extractUserID(c)

			// Check rate limit
			allowed, remaining, retryAfter := rl.Allow(userID)

			// Set standard rate limit headers (RFC 6585)
			c.Response().Header().Set("X-RateLimit-Limit",
				fmt.Sprintf("%d", rl.config.RequestsPerMinute))
			c.Response().Header().Set("X-RateLimit-Remaining",
				fmt.Sprintf("%d", remaining))

			if !allowed {
				// Set Retry-After header (correct format - seconds as integer)
				c.Response().Header().Set("Retry-After",
					fmt.Sprintf("%d", int(retryAfter.Seconds())))

				// Alternative: HTTP date format
				// retryTime := time.Now().Add(retryAfter)
				// c.Response().Header().Set("Retry-After",
				//     retryTime.Format(http.TimeFormat))

				// Set reset time as Unix timestamp
				resetTime := time.Now().Add(retryAfter)
				c.Response().Header().Set("X-RateLimit-Reset",
					fmt.Sprintf("%d", resetTime.Unix()))

				return echo.NewHTTPError(http.StatusTooManyRequests,
					"Rate limit exceeded. Please try again later.")
			}

			return next(c)
		}
	}
}

// extractUserID implements multiple strategies for user identification
func (rl *UnifiedRateLimiter) extractUserID(c echo.Context) string {
	// Strategy 1: Authenticated user ID
	if userID, ok := c.Get("user_id").(string); ok && userID != "" {
		return "user:" + userID
	}

	// Strategy 2: API key
	if apiKey := c.Request().Header.Get("X-API-Key"); apiKey != "" {
		return "api:" + apiKey
	}

	// Strategy 3: Anonymous cookie
	if cookie, err := c.Cookie("anon_id"); err == nil {
		return "anon:" + cookie.Value
	}

	// Strategy 4: IP address (with proper proxy handling)
	ip := rl.extractIP(c)
	return "ip:" + ip
}

// extractIP safely extracts client IP with proxy support
func (rl *UnifiedRateLimiter) extractIP(c echo.Context) string {
	// Check X-Forwarded-For header (if trusted proxy)
	if xff := c.Request().Header.Get("X-Forwarded-For"); xff != "" {
		ips := strings.Split(xff, ",")
		if len(ips) > 0 {
			clientIP := strings.TrimSpace(ips[0])
			if rl.isTrustedProxy(c.RealIP()) {
				return clientIP
			}
		}
	}

	// Check X-Real-IP header
	if xri := c.Request().Header.Get("X-Real-IP"); xri != "" {
		if rl.isTrustedProxy(c.RealIP()) {
			return xri
		}
	}

	// Fallback to Echo's RealIP
	return c.RealIP()
}

// isTrustedProxy checks if IP is in trusted proxy list
func (rl *UnifiedRateLimiter) isTrustedProxy(ip string) bool {
	if len(rl.config.TrustedProxies) == 0 {
		return false
	}

	for _, trusted := range rl.config.TrustedProxies {
		if ip == trusted {
			return true
		}
	}

	return false
}
