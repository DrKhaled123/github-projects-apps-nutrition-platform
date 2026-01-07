// pkg/ratelimit/ratelimit_test.go
package ratelimit

import (
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestUnifiedRateLimiter(t *testing.T) {
	tests := []struct {
		name          string
		config        *Config
		requests      int
		userID        string
		expectBlocked int
		expectHeaders bool
	}{
		{
			name: "Allow within limit",
			config: &Config{
				RequestsPerMinute: 60,
				BurstSize:         5,
			},
			requests:      3,
			userID:        "user1",
			expectBlocked: 0,
			expectHeaders: true,
		},
		{
			name: "Block over limit",
			config: &Config{
				RequestsPerMinute: 60,
				BurstSize:         2,
			},
			requests:      5,
			userID:        "user2",
			expectBlocked: 3,
			expectHeaders: true,
		},
		{
			name: "Different users independent",
			config: &Config{
				RequestsPerMinute: 60,
				BurstSize:         2,
			},
			requests:      2,
			userID:        "user3",
			expectBlocked: 0,
			expectHeaders: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Create rate limiter ONCE (fixes test issue #8)
			rl := NewUnifiedRateLimiter(tt.config)
			defer rl.Shutdown()

			// Create Echo instance
			e := echo.New()

			// Create middleware ONCE
			middleware := rl.Middleware()

			// Handler that always succeeds
			handler := func(c echo.Context) error {
				return c.String(http.StatusOK, "OK")
			}

			// Wrap handler with middleware
			wrappedHandler := middleware(handler)

			blocked := 0
			allowed := 0

			// Make multiple requests with SAME middleware instance
			for i := 0; i < tt.requests; i++ {
				// Create new request/response for each iteration
				req := httptest.NewRequest(http.MethodGet, "/", nil)
				rec := httptest.NewRecorder()
				c := e.NewContext(req, rec)

				// Set user ID
				c.Set("user_id", tt.userID)

				// Call wrapped handler
				err := wrappedHandler(c)

				if err != nil {
					if httpErr, ok := err.(*echo.HTTPError); ok {
						if httpErr.Code == http.StatusTooManyRequests {
							blocked++

							// Verify headers on blocked requests
							if tt.expectHeaders {
								assert.NotEmpty(t, rec.Header().Get("Retry-After"))
								assert.NotEmpty(t, rec.Header().Get("X-RateLimit-Reset"))
							}
						}
					}
				} else {
					allowed++

					// Verify headers on allowed requests
					if tt.expectHeaders {
						assert.NotEmpty(t, rec.Header().Get("X-RateLimit-Limit"))
						assert.NotEmpty(t, rec.Header().Get("X-RateLimit-Remaining"))
					}
				}

				// Small delay between requests to avoid race conditions
				time.Sleep(10 * time.Millisecond)
			}

			// Verify expectations
			assert.Equal(t, tt.expectBlocked, blocked, "Unexpected number of blocked requests")
			assert.Equal(t, tt.requests-tt.expectBlocked, allowed, "Unexpected number of allowed requests")
		})
	}
}

func TestRateLimiterCleanup(t *testing.T) {
	config := &Config{
		RequestsPerMinute: 60,
		BurstSize:         10,
		CleanupInterval:   100 * time.Millisecond,
		MaxIdleTime:       200 * time.Millisecond,
	}

	rl := NewUnifiedRateLimiter(config)
	defer rl.Shutdown()

	// Create some limiters
	rl.Allow("user1")
	rl.Allow("user2")
	rl.Allow("user3")

	// Verify they exist
	stats := rl.Stats()
	assert.Equal(t, int64(3), stats["active_users"])

	// Wait for cleanup
	time.Sleep(400 * time.Millisecond)

	// Verify cleanup occurred
	stats = rl.Stats()
	assert.Equal(t, int64(0), stats["active_users"])
}

func TestRetryAfterHeader(t *testing.T) {
	config := &Config{
		RequestsPerMinute: 60,
		BurstSize:         1,
	}

	rl := NewUnifiedRateLimiter(config)
	defer rl.Shutdown()

	e := echo.New()
	middleware := rl.Middleware()
	handler := middleware(func(c echo.Context) error {
		return c.String(http.StatusOK, "OK")
	})

	// First request - should pass
	req1 := httptest.NewRequest(http.MethodGet, "/", nil)
	rec1 := httptest.NewRecorder()
	c1 := e.NewContext(req1, rec1)
	c1.Set("user_id", "test_user")

	err := handler(c1)
	require.NoError(t, err)

	// Second request - should be blocked
	req2 := httptest.NewRequest(http.MethodGet, "/", nil)
	rec2 := httptest.NewRecorder()
	c2 := e.NewContext(req2, rec2)
	c2.Set("user_id", "test_user")

	err = handler(c2)
	require.Error(t, err)

	// Verify Retry-After header format
	retryAfter := rec2.Header().Get("Retry-After")
	assert.NotEmpty(t, retryAfter, "Retry-After header should be set")

	// Should be parseable as integer (seconds)
	var seconds int
	_, err = fmt.Sscanf(retryAfter, "%d", &seconds)
	assert.NoError(t, err, "Retry-After should be integer seconds")
	assert.Greater(t, seconds, 0, "Retry-After should be positive")
}

func TestConcurrentAccess(t *testing.T) {
	config := &Config{
		RequestsPerMinute: 60,
		BurstSize:         10,
	}

	rl := NewUnifiedRateLimiter(config)
	defer rl.Shutdown()

	// Launch multiple goroutines
	const goroutines = 100
	const requestsPerGoroutine = 10

	done := make(chan bool, goroutines)

	for i := 0; i < goroutines; i++ {
		go func(id int) {
			userID := fmt.Sprintf("user%d", id)
			for j := 0; j < requestsPerGoroutine; j++ {
				rl.Allow(userID)
			}
			done <- true
		}(i)
	}

	// Wait for all goroutines
	for i := 0; i < goroutines; i++ {
		<-done
	}

	// Verify no panics or race conditions occurred
	stats := rl.Stats()
	assert.Greater(t, stats["total_requests"], int64(0))
}

func TestMetricsCallback(t *testing.T) {
	var metrics []MetricEvent
	config := &Config{
		RequestsPerMinute: 60,
		BurstSize:         1,
		EnableMetrics:     true,
		MetricsCallback: func(event MetricEvent) {
			metrics = append(metrics, event)
		},
	}

	rl := NewUnifiedRateLimiter(config)
	defer rl.Shutdown()

	// Make some requests
	allowed, _, _ := rl.Allow("test_user")
	assert.True(t, allowed)

	// Wait a bit for cleanup
	time.Sleep(50 * time.Millisecond)

	// Make blocked request
	_, _, _ = rl.Allow("test_user")

	// Wait for metrics to be recorded
	time.Sleep(50 * time.Millisecond)

	// Verify metrics were recorded
	assert.GreaterOrEqual(t, len(metrics), 1, "Metrics should be recorded")

	// Check last metric (blocked request)
	if len(metrics) > 0 {
		lastMetric := metrics[len(metrics)-1]
		assert.False(t, lastMetric.Allowed, "Last request should be blocked")
		assert.Greater(t, lastMetric.RetryAfter, time.Duration(0), "RetryAfter should be set")
	}
}

func TestUserIdentification(t *testing.T) {
	config := &Config{
		RequestsPerMinute: 60,
		BurstSize:         1,
	}

	rl := NewUnifiedRateLimiter(config)
	defer rl.Shutdown()

	e := echo.New()
	middleware := rl.Middleware()
	handler := middleware(func(c echo.Context) error {
		return c.String(http.StatusOK, "OK")
	})

	// Test authenticated user
	req1 := httptest.NewRequest(http.MethodGet, "/", nil)
	rec1 := httptest.NewRecorder()
	c1 := e.NewContext(req1, rec1)
	c1.Set("user_id", "authenticated_user")

	err := handler(c1)
	require.NoError(t, err)

	// Test API key
	req2 := httptest.NewRequest(http.MethodGet, "/", nil)
	req2.Header.Set("X-API-Key", "test-api-key")
	rec2 := httptest.NewRecorder()
	c2 := e.NewContext(req2, rec2)

	err = handler(c2)
	require.Error(t, err) // Should be blocked due to different user

	// Test IP-based limiting
	req3 := httptest.NewRequest(http.MethodGet, "/", nil)
	rec3 := httptest.NewRecorder()
	c3 := e.NewContext(req3, rec3)
	c3.Request().RemoteAddr = "192.168.1.100:12345"

	err = handler(c3)
	require.Error(t, err) // Should be blocked due to different user
}

func TestRateLimiterStats(t *testing.T) {
	config := &Config{
		RequestsPerMinute: 60,
		BurstSize:         10,
	}

	rl := NewUnifiedRateLimiter(config)
	defer rl.Shutdown()

	// Initial stats should be zero
	stats := rl.Stats()
	assert.Equal(t, int64(0), stats["total_requests"])
	assert.Equal(t, int64(0), stats["total_blocked"])
	assert.Equal(t, int64(0), stats["active_users"])

	// Make some requests
	rl.Allow("user1")
	rl.Allow("user2")

	stats = rl.Stats()
	assert.Equal(t, int64(2), stats["total_requests"])
	assert.Equal(t, int64(0), stats["total_blocked"])
	assert.Equal(t, int64(2), stats["active_users"])

	// Make blocked requests
	rl.Allow("user1") // This should be blocked due to burst limit

	stats = rl.Stats()
	assert.Equal(t, int64(3), stats["total_requests"])
	assert.Equal(t, int64(1), stats["total_blocked"])
	assert.Equal(t, int64(2), stats["active_users"])
}

func TestRateLimiterShutdown(t *testing.T) {
	config := &Config{
		RequestsPerMinute: 60,
		BurstSize:         10,
		CleanupInterval:   time.Minute, // Long interval
	}

	rl := NewUnifiedRateLimiter(config)

	// Should not panic
	rl.Shutdown()

	// Multiple shutdowns should not panic
	rl.Shutdown()
}
