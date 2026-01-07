// pkg/ratelimit/unified_limiter.go
package ratelimit

import (
	"context"
	"fmt"
	"sync"
	"sync/atomic"
	"time"

	"golang.org/x/time/rate"
)

// Config holds unified rate limiter configuration
type Config struct {
	// Rate limiting
	RequestsPerMinute int
	BurstSize         int

	// Storage
	CleanupInterval time.Duration
	MaxIdleTime     time.Duration
	MaxUsers        int

	// Security
	EnableHTTPSOnly bool
	TrustedProxies  []string

	// Monitoring
	EnableMetrics   bool
	MetricsCallback func(event MetricEvent)
}

// DefaultConfig returns secure defaults
func DefaultConfig() *Config {
	return &Config{
		RequestsPerMinute: 60,
		BurstSize:         10,
		CleanupInterval:   time.Minute,
		MaxIdleTime:       5 * time.Minute,
		MaxUsers:          10000,
		EnableHTTPSOnly:   true,
		EnableMetrics:     true,
	}
}

// MetricEvent represents a rate limit event
type MetricEvent struct {
	UserID     string
	Timestamp  time.Time
	Allowed    bool
	Remaining  int
	RetryAfter time.Duration
}

// UserLimiter holds rate limiter for a single user
type UserLimiter struct {
	limiter  *rate.Limiter
	lastSeen time.Time
	count    int64 // Total requests
	blocked  int64 // Blocked requests
}

// UnifiedRateLimiter implements thread-safe, efficient rate limiting
type UnifiedRateLimiter struct {
	config   *Config
	limiters sync.Map // map[string]*UserLimiter (lock-free)

	// Metrics
	totalRequests int64
	totalBlocked  int64
	activeUsers   int64

	// Lifecycle
	ctx    context.Context
	cancel context.CancelFunc
	wg     sync.WaitGroup
}

// NewUnifiedRateLimiter creates a new rate limiter with best practices
func NewUnifiedRateLimiter(config *Config) *UnifiedRateLimiter {
	if config == nil {
		config = DefaultConfig()
	}

	ctx, cancel := context.WithCancel(context.Background())

	rl := &UnifiedRateLimiter{
		config: config,
		ctx:    ctx,
		cancel: cancel,
	}

	// Start background cleanup
	rl.startCleanup()

	return rl
}

// GetLimiter returns or creates a limiter for a user
func (rl *UnifiedRateLimiter) GetLimiter(userID string) *UserLimiter {
	// Try to load existing
	if limiter, ok := rl.limiters.Load(userID); ok {
		ul := limiter.(*UserLimiter)
		ul.lastSeen = time.Now()
		return ul
	}

	// Create new limiter
	rateLimit := rate.Limit(float64(rl.config.RequestsPerMinute) / 60.0)
	newLimiter := &UserLimiter{
		limiter:  rate.NewLimiter(rateLimit, rl.config.BurstSize),
		lastSeen: time.Now(),
	}

	// Store atomically
	actual, loaded := rl.limiters.LoadOrStore(userID, newLimiter)

	if !loaded {
		// We created a new limiter
		atomic.AddInt64(&rl.activeUsers, 1)
	}

	return actual.(*UserLimiter)
}

// Allow checks if request is allowed (thread-safe)
func (rl *UnifiedRateLimiter) Allow(userID string) (allowed bool, remaining int, retryAfter time.Duration) {
	limiter := rl.GetLimiter(userID)

	// Check if allowed
	reservation := limiter.limiter.Reserve()
	if !reservation.OK() {
		// Should never happen with our configuration
		atomic.AddInt64(&rl.totalBlocked, 1)
		atomic.AddInt64(&limiter.blocked, 1)
		return false, 0, time.Minute
	}

	delay := reservation.Delay()

	if delay > 0 {
		// Rate limit exceeded
		reservation.Cancel()
		atomic.AddInt64(&rl.totalBlocked, 1)
		atomic.AddInt64(&limiter.blocked, 1)

		// Calculate retry after (proper format)
		retryAfter = delay

		// Emit metric
		if rl.config.EnableMetrics && rl.config.MetricsCallback != nil {
			rl.config.MetricsCallback(MetricEvent{
				UserID:     userID,
				Timestamp:  time.Now(),
				Allowed:    false,
				RetryAfter: retryAfter,
			})
		}

		return false, 0, retryAfter
	}

	// Request allowed
	atomic.AddInt64(&rl.totalRequests, 1)
	atomic.AddInt64(&limiter.count, 1)

	// Calculate remaining tokens
	// This is approximate due to token bucket algorithm
	remaining = int(limiter.limiter.Tokens())

	// Emit metric
	if rl.config.EnableMetrics && rl.config.MetricsCallback != nil {
		rl.config.MetricsCallback(MetricEvent{
			UserID:    userID,
			Timestamp: time.Now(),
			Allowed:   true,
			Remaining: remaining,
		})
	}

	return true, remaining, 0
}

// startCleanup runs periodic cleanup (fixes memory leak)
func (rl *UnifiedRateLimiter) startCleanup() {
	rl.wg.Add(1)

	go func() {
		defer rl.wg.Done()

		// Ensure cleanup interval is positive to avoid ticker panic
		if rl.config.CleanupInterval <= 0 {
			rl.config.CleanupInterval = time.Minute
		}
		ticker := time.NewTicker(rl.config.CleanupInterval)
		defer ticker.Stop()

		for {
			select {
			case <-rl.ctx.Done():
				return

			case <-ticker.C:
				rl.cleanup()
			}
		}
	}()
}

// cleanup removes idle limiters (fixes memory leak and race condition)
func (rl *UnifiedRateLimiter) cleanup() {
	now := time.Now()
	toDelete := []string{}

	// First pass: collect keys to delete (no locks held)
	rl.limiters.Range(func(key, value interface{}) bool {
		userID := key.(string)
		limiter := value.(*UserLimiter)

		if now.Sub(limiter.lastSeen) > rl.config.MaxIdleTime {
			toDelete = append(toDelete, userID)
		}

		return true
	})

	// Second pass: delete collected keys
	for _, userID := range toDelete {
		if _, loaded := rl.limiters.LoadAndDelete(userID); loaded {
			atomic.AddInt64(&rl.activeUsers, -1)
		}
	}

	// Log cleanup if metrics enabled
	if rl.config.EnableMetrics && len(toDelete) > 0 {
		fmt.Printf("[RateLimit] Cleaned up %d idle limiters\n", len(toDelete))
	}
}

// Shutdown gracefully stops the rate limiter
func (rl *UnifiedRateLimiter) Shutdown() {
	rl.cancel()
	rl.wg.Wait()
}

// Stats returns current statistics
func (rl *UnifiedRateLimiter) Stats() map[string]interface{} {
	return map[string]interface{}{
		"total_requests": atomic.LoadInt64(&rl.totalRequests),
		"total_blocked":  atomic.LoadInt64(&rl.totalBlocked),
		"active_users":   atomic.LoadInt64(&rl.activeUsers),
	}
}
