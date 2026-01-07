// pkg/quota/quota_manager.go
package quota

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/redis/go-redis/v9"
)

// QuotaConfig holds quota configuration
type QuotaConfig struct {
	MonthlyLimit    int
	StorageBackend  StorageBackend
	CleanupInterval time.Duration
	EnableMetrics   bool
}

// StorageBackend defines interface for quota storage
type StorageBackend interface {
	Get(ctx context.Context, userID, monthKey string) (int, error)
	Increment(ctx context.Context, userID, monthKey string) error
	Set(ctx context.Context, userID, monthKey string, value int) error
	Delete(ctx context.Context, userID, monthKey string) error
	GetAll(ctx context.Context, userID string) (map[string]int, error)
	Close() error
}

// MemoryStorage implements in-memory storage (for development)
type MemoryStorage struct {
	mu   sync.RWMutex
	data map[string]map[string]int // userID -> monthKey -> count
}

func NewMemoryStorage() *MemoryStorage {
	return &MemoryStorage{
		data: make(map[string]map[string]int),
	}
}

func (m *MemoryStorage) Get(ctx context.Context, userID, monthKey string) (int, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	if months, ok := m.data[userID]; ok {
		return months[monthKey], nil
	}
	return 0, nil
}

func (m *MemoryStorage) Increment(ctx context.Context, userID, monthKey string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if _, ok := m.data[userID]; !ok {
		m.data[userID] = make(map[string]int)
	}

	m.data[userID][monthKey]++
	return nil
}

func (m *MemoryStorage) Set(ctx context.Context, userID, monthKey string, value int) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if _, ok := m.data[userID]; !ok {
		m.data[userID] = make(map[string]int)
	}

	m.data[userID][monthKey] = value
	return nil
}

func (m *MemoryStorage) Delete(ctx context.Context, userID, monthKey string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if months, ok := m.data[userID]; ok {
		delete(months, monthKey)
	}
	return nil
}

func (m *MemoryStorage) GetAll(ctx context.Context, userID string) (map[string]int, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	if months, ok := m.data[userID]; ok {
		// Return copy to prevent external modification
		result := make(map[string]int, len(months))
		for k, v := range months {
			result[k] = v
		}
		return result, nil
	}
	return make(map[string]int), nil
}

func (m *MemoryStorage) Close() error {
	return nil
}

// RedisStorage implements Redis storage (for production)
type RedisStorage struct {
	client *redis.Client
}

func NewRedisStorage(addr string, password string, db int) *RedisStorage {
	return &RedisStorage{
		client: redis.NewClient(&redis.Options{
			Addr:     addr,
			Password: password,
			DB:       db,
		}),
	}
}

func (r *RedisStorage) Get(ctx context.Context, userID, monthKey string) (int, error) {
	key := fmt.Sprintf("quota:%s:%s", userID, monthKey)
	val, err := r.client.Get(ctx, key).Int()
	if err == redis.Nil {
		return 0, nil
	}
	return val, err
}

func (r *RedisStorage) Increment(ctx context.Context, userID, monthKey string) error {
	key := fmt.Sprintf("quota:%s:%s", userID, monthKey)

	// Increment and set expiry
	pipe := r.client.Pipeline()
	pipe.Incr(ctx, key)

	// Set expiry to end of next month
	nextMonth := getNextMonthEnd()
	pipe.ExpireAt(ctx, key, nextMonth)

	_, err := pipe.Exec(ctx)
	return err
}

func (r *RedisStorage) Set(ctx context.Context, userID, monthKey string, value int) error {
	key := fmt.Sprintf("quota:%s:%s", userID, monthKey)
	return r.client.Set(ctx, key, value, time.Until(getNextMonthEnd())).Err()
}

func (r *RedisStorage) Delete(ctx context.Context, userID, monthKey string) error {
	key := fmt.Sprintf("quota:%s:%s", userID, monthKey)
	return r.client.Del(ctx, key).Err()
}

func (r *RedisStorage) GetAll(ctx context.Context, userID string) (map[string]int, error) {
	pattern := fmt.Sprintf("quota:%s:*", userID)
	keys, err := r.client.Keys(ctx, pattern).Result()
	if err != nil {
		return nil, err
	}

	result := make(map[string]int)
	for _, key := range keys {
		val, err := r.client.Get(ctx, key).Int()
		if err != nil {
			continue
		}

		// Extract month key from Redis key
		parts := strings.Split(key, ":")
		if len(parts) >= 3 {
			monthKey := parts[2]
			result[monthKey] = val
		}
	}

	return result, nil
}

func (r *RedisStorage) Close() error {
	return r.client.Close()
}

// QuotaManager manages user quotas
type QuotaManager struct {
	config  *QuotaConfig
	storage StorageBackend

	ctx    context.Context
	cancel context.CancelFunc
	wg     sync.WaitGroup
}

func NewQuotaManager(config *QuotaConfig) *QuotaManager {
	ctx, cancel := context.WithCancel(context.Background())

	qm := &QuotaManager{
		config:  config,
		storage: config.StorageBackend,
		ctx:     ctx,
		cancel:  cancel,
	}

	// Start cleanup routine
	qm.startCleanup()

	return qm
}

// Check verifies if user is within quota
func (qm *QuotaManager) Check(ctx context.Context, userID string) (allowed bool, current int, limit int, resetAt time.Time, err error) {
	monthKey := getCurrentMonthKey()

	current, err = qm.storage.Get(ctx, userID, monthKey)
	if err != nil {
		return false, 0, 0, time.Time{}, err
	}

	limit = qm.config.MonthlyLimit
	resetAt = getNextMonthStart()
	allowed = current < limit

	return allowed, current, limit, resetAt, nil
}

// Consume increments user's quota usage
func (qm *QuotaManager) Consume(ctx context.Context, userID string) error {
	monthKey := getCurrentMonthKey()
	return qm.storage.Increment(ctx, userID, monthKey)
}

// Get returns current usage
func (qm *QuotaManager) Get(ctx context.Context, userID string) (int, error) {
	monthKey := getCurrentMonthKey()
	return qm.storage.Get(ctx, userID, monthKey)
}

// Reset resets user's quota
func (qm *QuotaManager) Reset(ctx context.Context, userID string) error {
	monthKey := getCurrentMonthKey()
	return qm.storage.Delete(ctx, userID, monthKey)
}

// startCleanup starts periodic cleanup
func (qm *QuotaManager) startCleanup() {
	if qm.config.CleanupInterval == 0 {
		return
	}

	qm.wg.Add(1)
	go func() {
		defer qm.wg.Done()

		ticker := time.NewTicker(qm.config.CleanupInterval)
		defer ticker.Stop()

		for {
			select {
			case <-qm.ctx.Done():
				return
			case <-ticker.C:
				// Cleanup old months (storage-specific)
				// For Redis, this is handled by TTL
				// For memory, we need manual cleanup
				if mem, ok := qm.storage.(*MemoryStorage); ok {
					qm.cleanupMemoryStorage(mem)
				}
			}
		}
	}()
}

func (qm *QuotaManager) cleanupMemoryStorage(mem *MemoryStorage) {
	// Keep only current and previous month
	currentMonth := getCurrentMonthKey()
	previousMonth := getPreviousMonthKey()

	mem.mu.Lock()
	defer mem.mu.Unlock()

	for userID, months := range mem.data {
		for monthKey := range months {
			if monthKey != currentMonth && monthKey != previousMonth {
				delete(months, monthKey)
			}
		}

		// Remove user if no data
		if len(months) == 0 {
			delete(mem.data, userID)
		}
	}
}

func (qm *QuotaManager) Shutdown() {
	qm.cancel()
	qm.wg.Wait()
	qm.storage.Close()
}

// Utility functions (all use UTC to fix timezone issues)
func getCurrentMonthKey() string {
	return time.Now().UTC().Format("2006-01")
}

func getPreviousMonthKey() string {
	return time.Now().UTC().AddDate(0, -1, 0).Format("2006-01")
}

func getNextMonthStart() time.Time {
	now := time.Now().UTC()
	return time.Date(now.Year(), now.Month()+1, 1, 0, 0, 0, 0, time.UTC)
}

func getNextMonthEnd() time.Time {
	return getNextMonthStart().AddDate(0, 1, 0).Add(-time.Second)
}
