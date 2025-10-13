package rate

import (
	"fmt"
	"net/http"
	"time"

	"github.com/labstack/echo/v4"
)

// SetRateLimitHeaders sets standardized rate limit headers on the response
func SetRateLimitHeaders(c echo.Context, limiter Limiter, key string, burst int) {
	resetTime := limiter.ResetTime(key)
	remaining := limiter.Remaining(key)

	// Set standard headers
	c.Response().Header().Set("X-RateLimit-Limit", fmt.Sprintf("%d", burst))
	c.Response().Header().Set("X-RateLimit-Remaining", fmt.Sprintf("%d", remaining))

	// Set Retry-After in both formats for compatibility
	c.Response().Header().Set("Retry-After", resetTime.Format(http.TimeFormat))

	// Also set in seconds for compatibility with older clients
	seconds := int(time.Until(resetTime).Seconds())
	if seconds < 1 {
		seconds = 1
	}
	c.Response().Header().Add("X-Retry-After-Seconds", fmt.Sprintf("%d", seconds))
}

// SetRateLimitHeadersForBlocked sets headers when a request is blocked
func SetRateLimitHeadersForBlocked(c echo.Context, limiter Limiter, key string, burst int) {
	resetTime := limiter.ResetTime(key)

	// Set standard headers for blocked requests
	c.Response().Header().Set("X-RateLimit-Limit", fmt.Sprintf("%d", burst))
	c.Response().Header().Set("X-RateLimit-Remaining", "0")

	// Set Retry-After in both formats for compatibility
	c.Response().Header().Set("Retry-After", resetTime.Format(http.TimeFormat))

	// Also set in seconds for compatibility with older clients
	seconds := int(time.Until(resetTime).Seconds())
	if seconds < 1 {
		seconds = 1
	}
	c.Response().Header().Add("X-Retry-After-Seconds", fmt.Sprintf("%d", seconds))
}

// GetRetryAfterSeconds returns the retry-after time in seconds
func GetRetryAfterSeconds(resetTime time.Time) int {
	seconds := int(time.Until(resetTime).Seconds())
	if seconds < 1 {
		seconds = 1
	}
	return seconds
}