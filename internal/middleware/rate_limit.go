package middleware

import (
	"fmt"
	"net/http"

	"github.com/labstack/echo/v4"
	"api-key-generator/internal/rate"
)

// RateLimiter creates a middleware function that uses the unified rate limiter
func RateLimiter(limiter rate.Limiter, rps, burst int) echo.MiddlewareFunc {
	return func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			key := c.RealIP()
			if c.Get("user_id") != nil {
				key = c.Get("user_id").(string)
			}

			if !limiter.Allow(key) {
				// Set headers for blocked requests
				rate.SetRateLimitHeadersForBlocked(c, limiter, key, burst)
				return echo.NewHTTPError(http.StatusTooManyRequests, "Rate limit exceeded")
			}

			// Set headers for successful requests
			rate.SetRateLimitHeaders(c, limiter, key, burst)
			return next(c)
		}
	}
}

// IPRateLimiter creates middleware that limits by IP address only
func IPRateLimiter(limiter rate.Limiter, rps, burst int) echo.MiddlewareFunc {
	return func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			key := c.RealIP()

			if !limiter.Allow(key) {
				rate.SetRateLimitHeadersForBlocked(c, limiter, key, burst)
				return echo.NewHTTPError(http.StatusTooManyRequests, "Rate limit exceeded")
			}

			rate.SetRateLimitHeaders(c, limiter, key, burst)
			return next(c)
		}
	}
}

// UserRateLimiter creates middleware that limits by user ID only (skips if no user)
func UserRateLimiter(limiter rate.Limiter, rps, burst int) echo.MiddlewareFunc {
	return func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			userID, ok := c.Get("user_id").(string)
			if !ok || userID == "" {
				// No user ID, skip rate limiting
				return next(c)
			}

			if !limiter.Allow(userID) {
				rate.SetRateLimitHeadersForBlocked(c, limiter, userID, burst)
				return echo.NewHTTPError(http.StatusTooManyRequests, "Rate limit exceeded")
			}

			rate.SetRateLimitHeaders(c, limiter, userID, burst)
			return next(c)
		}
	}
}

// CombinedRateLimiter creates middleware that tries user ID first, falls back to IP
func CombinedRateLimiter(limiter rate.Limiter, rps, burst int) echo.MiddlewareFunc {
	return func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			key := c.RealIP()
			if c.Get("user_id") != nil {
				key = c.Get("user_id").(string)
			}

			if !limiter.Allow(key) {
				rate.SetRateLimitHeadersForBlocked(c, limiter, key, burst)
				return echo.NewHTTPError(http.StatusTooManyRequests, "Rate limit exceeded")
			}

			rate.SetRateLimitHeaders(c, limiter, key, burst)
			return next(c)
		}
	}
}