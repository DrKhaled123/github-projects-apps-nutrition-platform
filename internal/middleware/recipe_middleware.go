package middleware

import (
	"net/http"
	"strconv"
	"time"

	"api-key-generator/internal/services"
	"api-key-generator/internal/utils"

	"github.com/labstack/echo/v4"
)

// RecipeRateLimit implements rate limiting specifically for recipe endpoints
func RecipeRateLimit(apiKeyService *services.APIKeyService) echo.MiddlewareFunc {
	return func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			// Extract API key
			apiKeyValue := c.Request().Header.Get("X-API-Key")
			if apiKeyValue == "" {
				return echo.NewHTTPError(http.StatusUnauthorized, "API key required")
			}

			// Get API key details
			apiKey, err := apiKeyService.GetAPIKeyByKey(c.Request().Context(), apiKeyValue)
			if err != nil {
				return echo.NewHTTPError(http.StatusUnauthorized, "invalid API key")
			}

			// Check rate limit
			if apiKey.RateLimit != nil && *apiKey.RateLimit > 0 && apiKey.RateLimitUsed >= *apiKey.RateLimit {
				return echo.NewHTTPError(http.StatusTooManyRequests, "rate limit exceeded")
			}

			// Store API key in context for handlers
			c.Set("api_key", apiKey)

			return next(c)
		}
	}
}

// RecipeValidation validates common recipe request parameters
func RecipeValidation() echo.MiddlewareFunc {
	return func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			// Validate pagination parameters
			if limit := c.QueryParam("limit"); limit != "" {
				if l, err := strconv.Atoi(limit); err != nil || l < 1 || l > 100 {
					return echo.NewHTTPError(http.StatusBadRequest, "invalid limit parameter (1-100)")
				}
			}

			if offset := c.QueryParam("offset"); offset != "" {
				if o, err := strconv.Atoi(offset); err != nil || o < 0 {
					return echo.NewHTTPError(http.StatusBadRequest, "invalid offset parameter (>=0)")
				}
			}

			// Validate cuisine parameter
			if cuisine := c.QueryParam("cuisine"); cuisine != "" {
				validCuisines := []string{"arabian_gulf", "shami", "egyptian", "moroccan"}
				valid := false
				for _, v := range validCuisines {
					if cuisine == v {
						valid = true
						break
					}
				}
				if !valid {
					return echo.NewHTTPError(http.StatusBadRequest, "invalid cuisine parameter")
				}
			}

			// Validate category parameter
			if category := c.QueryParam("category"); category != "" {
				validCategories := []string{"appetizer", "main_course", "dessert", "breakfast"}
				valid := false
				for _, v := range validCategories {
					if category == v {
						valid = true
						break
					}
				}
				if !valid {
					return echo.NewHTTPError(http.StatusBadRequest, "invalid category parameter")
				}
			}

			return next(c)
		}
	}
}

// RecipeSecurity adds security headers and input sanitization
func RecipeSecurity() echo.MiddlewareFunc {
	return func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			// Add security headers
			c.Response().Header().Set("X-Content-Type-Options", "nosniff")
			c.Response().Header().Set("X-Frame-Options", "DENY")
			c.Response().Header().Set("X-XSS-Protection", "1; mode=block")
			c.Response().Header().Set("Cache-Control", "no-cache, no-store, must-revalidate")

			// Sanitize query parameters
			for _, values := range c.QueryParams() {
				for i, value := range values {
					values[i] = utils.SanitizeInput(value)
				}
			}

			return next(c)
		}
	}
}

// RecipeLogging logs recipe API requests with sanitization
func RecipeLogging() echo.MiddlewareFunc {
	return func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			start := time.Now()

			// Execute request
			err := next(c)

			// Log request details
			duration := time.Since(start)
			status := c.Response().Status

			// Sanitize logging data
			path := utils.SanitizeForLog(c.Request().URL.Path)
			method := utils.SanitizeForLog(c.Request().Method)
			ip := utils.SanitizeForLog(c.RealIP())
			userAgent := utils.SanitizeForLog(c.Request().UserAgent())

			c.Logger().Infof("Recipe API: %s %s - %d - %v - IP: %s - UA: %s",
				method, path, status, duration, ip, userAgent)

			return err
		}
	}
}

// RecipeMetrics collects metrics for recipe API usage
func RecipeMetrics() echo.MiddlewareFunc {
	return func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			start := time.Now()

			// Execute request
			err := next(c)

			// Collect metrics
			duration := time.Since(start)
			status := c.Response().Status
			endpoint := c.Path()

			// Store metrics in context for potential collection
			c.Set("metrics", map[string]interface{}{
				"endpoint":  endpoint,
				"method":    c.Request().Method,
				"status":    status,
				"duration":  duration,
				"timestamp": start,
			})

			return err
		}
	}
}
