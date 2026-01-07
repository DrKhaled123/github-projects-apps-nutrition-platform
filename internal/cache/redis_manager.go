package cache

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"strconv"
	"time"

	"github.com/go-redis/redis/v8"
)

// RedisCacheManager provides production-ready Redis caching
type RedisCacheManager struct {
	client *redis.Client
	config *RedisConfig
}

// RedisConfig holds Redis connection configuration
type RedisConfig struct {
	Addr         string
	Password     string
	DB           int
	PoolSize     int
	MinIdleConns int
	MaxRetries   int
	DialTimeout  time.Duration
	ReadTimeout  time.Duration
	WriteTimeout time.Duration
	PoolTimeout  time.Duration
	IdleTimeout  time.Duration
	MaxConnAge   time.Duration
}

// CacheItem represents a cached item with metadata
type CacheItem struct {
	Key         string                 `json:"key"`
	Value       interface{}            `json:"value"`
	ExpiresAt   time.Time              `json:"expires_at"`
	CreatedAt   time.Time              `json:"created_at"`
	AccessCount int64                  `json:"access_count"`
	LastAccess  time.Time              `json:"last_access"`
	Tags        []string               `json:"tags"`
	Metadata    map[string]interface{} `json:"metadata"`
}

// CacheResult represents a cache operation result
type CacheResult struct {
	Found     bool          `json:"found"`
	Value     interface{}   `json:"value,omitempty"`
	TTL       time.Duration `json:"ttl"`
	FromCache string        `json:"from_cache"`
}

// NewRedisCacheManager creates a new Redis cache manager
func NewRedisCacheManager(cfg RedisConfig) (*RedisCacheManager, error) {
	rdb := redis.NewClient(&redis.Options{
		Addr:         cfg.Addr,
		Password:     cfg.Password,
		DB:           cfg.DB,
		PoolSize:     cfg.PoolSize,
		MinIdleConns: cfg.MinIdleConns,
		MaxRetries:   cfg.MaxRetries,
		DialTimeout:  cfg.DialTimeout,
		ReadTimeout:  cfg.ReadTimeout,
		WriteTimeout: cfg.WriteTimeout,
		PoolTimeout:  cfg.PoolTimeout,
		IdleTimeout:  cfg.IdleTimeout,
		MaxConnAge:   cfg.MaxConnAge,
	})

	// Test connection
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := rdb.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("failed to connect to Redis: %w", err)
	}

	return &RedisCacheManager{
		client: rdb,
		config: &cfg,
	}, nil
}

// Set stores an item in the cache with TTL
func (r *RedisCacheManager) Set(ctx context.Context, key string, value interface{}, ttl time.Duration) error {

	// Create cache item
	item := &CacheItem{
		Key:         key,
		Value:       value,
		ExpiresAt:   time.Now().Add(ttl),
		CreatedAt:   time.Now(),
		AccessCount: 0,
		LastAccess:  time.Now(),
	}

	// Serialize item with metadata
	itemData, err := json.Marshal(item)
	if err != nil {
		return fmt.Errorf("failed to marshal cache item: %w", err)
	}

	// Store in Redis with TTL
	if err := r.client.Set(ctx, key, itemData, ttl).Err(); err != nil {
		return fmt.Errorf("failed to set cache item: %w", err)
	}

	// Update access statistics
	r.incrementAccessCount(ctx, key)

	return nil
}

// Get retrieves an item from the cache
func (r *RedisCacheManager) Get(ctx context.Context, key string) (*CacheResult, error) {
	data, err := r.client.Get(ctx, key).Result()
	if err != nil {
		if err == redis.Nil {
			return &CacheResult{Found: false, FromCache: "redis"}, nil
		}
		return nil, fmt.Errorf("failed to get cache item: %w", err)
	}

	var item CacheItem
	if err := json.Unmarshal([]byte(data), &item); err != nil {
		return nil, fmt.Errorf("failed to unmarshal cache item: %w", err)
	}

	// Update access statistics
	item.AccessCount++
	item.LastAccess = time.Now()
	r.updateAccessStats(ctx, key, item)

	// Calculate remaining TTL
	ttl, err := r.client.TTL(ctx, key).Result()
	if err != nil {
		ttl = -1 * time.Second // Unknown TTL
	}

	return &CacheResult{
		Found:     true,
		Value:     item.Value,
		TTL:       ttl,
		FromCache: "redis",
	}, nil
}

// Delete removes an item from the cache
func (r *RedisCacheManager) Delete(ctx context.Context, key string) error {
	if err := r.client.Del(ctx, key).Err(); err != nil {
		return fmt.Errorf("failed to delete cache item: %w", err)
	}

	// Remove access statistics
	r.client.Del(ctx, key+":stats")
	r.client.Del(ctx, key+":access_count")

	return nil
}

// DeleteByPattern removes items matching a pattern
func (r *RedisCacheManager) DeleteByPattern(ctx context.Context, pattern string) (int64, error) {
	keys, err := r.client.Keys(ctx, pattern).Result()
	if err != nil {
		return 0, fmt.Errorf("failed to get keys for pattern %s: %w", pattern, err)
	}

	if len(keys) == 0 {
		return 0, nil
	}

	// Delete keys and their statistics
	allKeys := make([]string, 0, len(keys)*2)
	for _, key := range keys {
		allKeys = append(allKeys, key, key+":stats", key+":access_count")
	}

	result, err := r.client.Del(ctx, allKeys...).Result()
	if err != nil {
		return 0, fmt.Errorf("failed to delete keys: %w", err)
	}

	return result, nil
}

// SetWithTags stores an item with tags for easy invalidation
func (r *RedisCacheManager) SetWithTags(ctx context.Context, key string, value interface{}, ttl time.Duration, tags []string) error {
	// Set the main cache item
	if err := r.Set(ctx, key, value, ttl); err != nil {
		return err
	}

	// Add to tag sets for each tag
	for _, tag := range tags {
		tagKey := fmt.Sprintf("tag:%s", tag)
		if err := r.client.SAdd(ctx, tagKey, key).Err(); err != nil {
			return fmt.Errorf("failed to add key to tag %s: %w", tag, err)
		}
		// Set TTL for tag set
		r.client.Expire(ctx, tagKey, ttl+time.Hour) // Keep tags longer than items
	}

	return nil
}

// InvalidateByTag removes all items with a specific tag
func (r *RedisCacheManager) InvalidateByTag(ctx context.Context, tag string) (int64, error) {
	tagKey := fmt.Sprintf("tag:%s", tag)

	keys, err := r.client.SMembers(ctx, tagKey).Result()
	if err != nil {
		return 0, fmt.Errorf("failed to get keys for tag %s: %w", tag, err)
	}

	if len(keys) == 0 {
		return 0, nil
	}

	// Delete all keys with this tag
	result, err := r.client.Del(ctx, keys...).Result()
	if err != nil {
		return 0, fmt.Errorf("failed to delete keys for tag %s: %w", tag, err)
	}

	// Remove the tag set itself
	r.client.Del(ctx, tagKey)

	return result, nil
}

// Exists checks if a key exists in the cache
func (r *RedisCacheManager) Exists(ctx context.Context, key string) (bool, error) {
	result, err := r.client.Exists(ctx, key).Result()
	if err != nil {
		return false, fmt.Errorf("failed to check if key exists: %w", err)
	}
	return result > 0, nil
}

// TTL returns the remaining time to live for a key
func (r *RedisCacheManager) TTL(ctx context.Context, key string) (time.Duration, error) {
	ttl, err := r.client.TTL(ctx, key).Result()
	if err != nil {
		return 0, fmt.Errorf("failed to get TTL: %w", err)
	}
	return ttl, nil
}

// SetTTL updates the TTL for an existing key
func (r *RedisCacheManager) SetTTL(ctx context.Context, key string, ttl time.Duration) error {
	return r.client.Expire(ctx, key, ttl).Err()
}

// GetStats returns cache statistics
func (r *RedisCacheManager) GetStats(ctx context.Context) (map[string]interface{}, error) {
	info, err := r.client.Info(ctx, "memory", "keyspace", "stats").Result()
	if err != nil {
		return nil, fmt.Errorf("failed to get Redis info: %w", err)
	}

	stats := make(map[string]interface{})
	stats["info"] = info

	// Get connection pool stats
	poolStats := r.client.PoolStats()
	stats["connection_pool"] = map[string]interface{}{
		"hits":        poolStats.Hits,
		"misses":      poolStats.Misses,
		"timeouts":    poolStats.Timeouts,
		"total_conns": poolStats.TotalConns,
		"idle_conns":  poolStats.IdleConns,
		"stale_conns": poolStats.StaleConns,
	}

	return stats, nil
}

// Ping checks if Redis is responsive
func (r *RedisCacheManager) Ping(ctx context.Context) error {
	return r.client.Ping(ctx).Err()
}

// Close closes the Redis connection
func (r *RedisCacheManager) Close() error {
	return r.client.Close()
}

// Helper methods

func (r *RedisCacheManager) incrementAccessCount(ctx context.Context, key string) {
	countKey := key + ":access_count"
	r.client.Incr(ctx, countKey)
	r.client.Expire(ctx, countKey, 24*time.Hour)
}

func (r *RedisCacheManager) updateAccessStats(ctx context.Context, key string, item CacheItem) {
	statsKey := key + ":stats"
	statsData := map[string]interface{}{
		"access_count": item.AccessCount,
		"last_access":  item.LastAccess.Unix(),
	}

	if data, err := json.Marshal(statsData); err == nil {
		r.client.Set(ctx, statsKey, data, 24*time.Hour)
	}
}

// GetProductionConfig returns production-optimized Redis configuration
func GetProductionConfig() RedisConfig {
	return RedisConfig{
		Addr:         getEnv("REDIS_ADDR", "localhost:6379"),
		Password:     getEnv("REDIS_PASSWORD", ""),
		DB:           getEnvInt("REDIS_DB", 0),
		PoolSize:     20,
		MinIdleConns: 5,
		MaxRetries:   3,
		DialTimeout:  5 * time.Second,
		ReadTimeout:  3 * time.Second,
		WriteTimeout: 3 * time.Second,
		PoolTimeout:  4 * time.Second,
		IdleTimeout:  5 * time.Minute,
		MaxConnAge:   30 * time.Minute,
	}
}

// GetDevelopmentConfig returns development-friendly Redis configuration
func GetDevelopmentConfig() RedisConfig {
	return RedisConfig{
		Addr:         getEnv("REDIS_ADDR", "localhost:6379"),
		Password:     getEnv("REDIS_PASSWORD", ""),
		DB:           getEnvInt("REDIS_DB", 1),
		PoolSize:     10,
		MinIdleConns: 2,
		MaxRetries:   2,
		DialTimeout:  3 * time.Second,
		ReadTimeout:  2 * time.Second,
		WriteTimeout: 2 * time.Second,
		PoolTimeout:  3 * time.Second,
		IdleTimeout:  10 * time.Minute,
		MaxConnAge:   1 * time.Hour,
	}
}

// Helper functions for environment variable parsing
func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}
