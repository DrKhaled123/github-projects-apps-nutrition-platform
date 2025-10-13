package rate

import (
	"fmt"
	"sort"
	"sync"
	"time"

	"golang.org/x/time/rate"
)

// Unified rate limiter interface
type Limiter interface {
	Allow(key string) bool
	ResetTime(key string) time.Time
	Remaining(key string) int
	Burst() int
	Tokens() float64
}

// Unified in-memory rate limiter with enhanced cleanup
type MemoryLimiter struct {
	mu           sync.RWMutex
	limiters     map[string]*rate.Limiter
	rps          int
	burst        int
	lastSeenMap  sync.Map // key -> time.Time for atomic updates
	cleanupMutex sync.Mutex
}

// NewMemoryLimiter creates a new unified memory limiter
func NewMemoryLimiter(rps, burst int) *MemoryLimiter {
	ml := &MemoryLimiter{
		limiters: make(map[string]*rate.Limiter),
		rps:      rps,
		burst:    burst,
	}
	go ml.StartCleanup()
	return ml
}

// GetLimiter gets or creates a limiter for the given key with atomic last seen tracking
func (ml *MemoryLimiter) GetLimiter(key string) *rate.Limiter {
	ml.mu.RLock()
	limiter, exists := ml.limiters[key]
	ml.mu.RUnlock()

	if !exists {
		ml.mu.Lock()
		// Double-check after acquiring lock
		limiter, exists = ml.limiters[key]
		if !exists {
			limiter = rate.NewLimiter(rate.Limit(ml.rps), ml.burst)
			ml.limiters[key] = limiter
		}
		ml.mu.Unlock()
	}

	// Track last seen time atomically
	ml.lastSeenMap.Store(key, time.Now())
	return limiter
}

// Allow checks if the request is allowed for the given key
func (ml *MemoryLimiter) Allow(key string) bool {
	return ml.GetLimiter(key).Allow()
}

// ResetTime returns the reset time for the given key (simplified)
func (ml *MemoryLimiter) ResetTime(key string) time.Time {
	limiter := ml.GetLimiter(key)
	// Calculate reset time based on token regeneration
	// This is an approximation - in production you might want to track exact reset times
	return time.Now().Add(time.Minute)
}

// Remaining returns the remaining requests for the given key
func (ml *MemoryLimiter) Remaining(key string) int {
	limiter := ml.GetLimiter(key)

	// Calculate remaining based on actual token count
	tokens := limiter.Tokens()
	burst := float64(limiter.Burst())

	remaining := int(tokens)
	if tokens > burst {
		remaining = int(burst)
	}

	// Ensure non-negative
	if remaining < 0 {
		remaining = 0
	}

	return remaining
}

// Burst returns the burst capacity
func (ml *MemoryLimiter) Burst() int {
	return ml.burst
}

// Tokens returns the current token count for a key
func (ml *MemoryLimiter) Tokens(key string) float64 {
	limiter := ml.GetLimiter(key)
	return limiter.Tokens()
}

// StartCleanup starts the background cleanup process
func (ml *MemoryLimiter) StartCleanup() {
	go func() {
		ticker := time.NewTicker(30 * time.Second)
		defer ticker.Stop()

		for range ticker.C {
			ml.cleanupOnce()
		}
	}()
}

// cleanupOnce performs a single cleanup cycle with lock-free operations where possible
func (ml *MemoryLimiter) cleanupOnce() {
	// Prevent concurrent cleanup runs
	if !ml.cleanupMutex.TryLock() {
		return
	}
	defer ml.cleanupMutex.Unlock()

	ml.mu.Lock()
	defer ml.mu.Unlock()

	now := time.Now()
	var keysToDelete []string
	entryCount := 0

	// Collect keys to delete
	for key := range ml.limiters {
		lastSeen, exists := ml.lastSeenMap.Load(key)
		if !exists {
			// No last seen time, mark for deletion
			keysToDelete = append(keysToDelete, key)
			continue
		}

		lastSeenTime, ok := lastSeen.(time.Time)
		if !ok || lastSeenTime.Add(5*time.Minute).Before(now) {
			keysToDelete = append(keysToDelete, key)
		}

		entryCount++
	}

	// Always clean up old entries
	for _, key := range keysToDelete {
		delete(ml.limiters, key)
		ml.lastSeenMap.Delete(key)
	}

	// If over 50% capacity, clean more aggressively
	if entryCount > 5000 {
		ml.aggressiveCleanup(now)
	}
}

// aggressiveCleanup performs aggressive cleanup when memory usage is high
func (ml *MemoryLimiter) aggressiveCleanup(now time.Time) {
	// Sort entries by last seen time for efficient cleanup
	var entries []struct {
		key      string
		lastSeen time.Time
	}

	ml.lastSeenMap.Range(func(key, value interface{}) bool {
		lastSeen, ok := value.(time.Time)
		if ok {
			entries = append(entries, struct {
				key      string
				lastSeen time.Time
			}{key: key.(string), lastSeen: lastSeen})
		}
		return true
	})

	// Sort by oldest first
	sort.Slice(entries, func(i, j int) bool {
		return entries[i].lastSeen.Before(entries[j].lastSeen)
	})

	// Delete oldest 10% of entries
	deleteCount := len(entries) / 10
	for i := 0; i < deleteCount && i < len(entries); i++ {
		key := entries[i].key
		delete(ml.limiters, key)
		ml.lastSeenMap.Delete(key)
	}
}

// GetStats returns current statistics for monitoring
func (ml *MemoryLimiter) GetStats() map[string]interface{} {
	ml.mu.RLock()
	defer ml.mu.RUnlock()

	return map[string]interface{}{
		"total_limiters": len(ml.limiters),
		"rps":            ml.rps,
		"burst":          ml.burst,
	}
}

// ClearAll clears all limiters (useful for testing)
func (ml *MemoryLimiter) ClearAll() {
	ml.mu.Lock()
	defer ml.mu.Unlock()

	ml.limiters = make(map[string]*rate.Limiter)
	ml.lastSeenMap = sync.Map{}
}