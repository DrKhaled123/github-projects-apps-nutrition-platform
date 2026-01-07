package config

import (
	"fmt"
	"os"
	"strconv"
	"time"
)

type Config struct {
	Server    ServerConfig
	Database  DatabaseConfig
	JWT       JWTConfig
	CORS      CORSConfig
	RateLimit RateLimitConfig
	APIKey    APIKeyConfig
	Security  SecurityConfig
	Logging   LoggingConfig
	Cache     CacheConfig
}

type ServerConfig struct {
	Port string
	Host string
}

type DatabaseConfig struct {
	Type            string // "sqlite" or "postgres"
	Path            string // For SQLite
	Host            string // For PostgreSQL
	Port            int    // For PostgreSQL
	User            string // For PostgreSQL
	Password        string // For PostgreSQL
	DBName          string // For PostgreSQL
	SSLMode         string // For PostgreSQL
	MaxOpenConns    int
	MaxIdleConns    int
	ConnMaxLifetime time.Duration
}

type JWTConfig struct {
	Secret string
}

type CORSConfig struct {
	AllowedOrigins []string
}

type RateLimitConfig struct {
	RequestsPerMinute int
}

type APIKeyConfig struct {
	Prefix         string
	Length         int
	ExpiryDuration time.Duration
}

type SecurityConfig struct {
	RateLimitRequests int
	RateLimitWindow   time.Duration
}

type LoggingConfig struct {
	Level       string // debug, info, warn, error
	EnableDebug bool
}

type CacheConfig struct {
	Type   string // "redis" or "memory"
	Redis  RedisConfig
	Memory MemoryConfig
}

type RedisConfig struct {
	Host         string
	Port         int
	Password     string
	DB           int
	PoolSize     int
	MinIdleConns int
	DialTimeout  time.Duration
	ReadTimeout  time.Duration
	WriteTimeout time.Duration
	PoolTimeout  time.Duration
	IdleTimeout  time.Duration
	MaxRetries   int
}

type MemoryConfig struct {
	MaxSize int
	TTL     time.Duration
}

func Load() (*Config, error) {
	cfg := &Config{
		Server: ServerConfig{
			Port: getEnv("PORT", "8080"),
			Host: getEnv("HOST", "0.0.0.0"),
		},
		Database: DatabaseConfig{
			Type:            getEnv("DB_TYPE", "sqlite"),
			Path:            getEnv("DB_PATH", "./data/app.db"),
			Host:            getEnv("DB_HOST", "localhost"),
			Port:            getEnvInt("DB_PORT", 5432),
			User:            getEnv("DB_USER", "postgres"),
			Password:        getEnv("DB_PASSWORD", ""),
			DBName:          getEnv("DB_NAME", "nutrition_platform"),
			SSLMode:         getEnv("DB_SSLMODE", "require"),
			MaxOpenConns:    getEnvInt("DB_MAX_OPEN_CONNS", 25),
			MaxIdleConns:    getEnvInt("DB_MAX_IDLE_CONNS", 5),
			ConnMaxLifetime: getEnvDuration("DB_CONN_MAX_LIFETIME", 5*time.Minute),
		},
		JWT: JWTConfig{
			Secret: getEnv("JWT_SECRET", ""),
		},
		CORS: CORSConfig{
			AllowedOrigins: []string{
				getEnv("ALLOWED_ORIGIN", "https://api.doctorhealthy1.com"),
			},
		},
		RateLimit: RateLimitConfig{
			RequestsPerMinute: getEnvInt("RATE_LIMIT", 100),
		},
		APIKey: APIKeyConfig{
			Prefix:         getEnv("API_KEY_PREFIX", "dh_"),
			Length:         getEnvInt("API_KEY_LENGTH", 32),
			ExpiryDuration: getEnvDuration("API_KEY_EXPIRY", 365*24*time.Hour), // Default 1 year
		},
		Security: SecurityConfig{
			RateLimitRequests: getEnvInt("SECURITY_RATE_LIMIT_REQUESTS", 100),
			RateLimitWindow:   getEnvDuration("SECURITY_RATE_LIMIT_WINDOW", time.Minute),
		},
		Logging: LoggingConfig{
			Level:       getEnv("LOG_LEVEL", "info"),
			EnableDebug: getEnv("ENV", "production") == "development",
		},
		Cache: CacheConfig{
			Type: getEnv("CACHE_TYPE", "memory"),
			Redis: RedisConfig{
				Host:         getEnv("REDIS_HOST", "localhost"),
				Port:         getEnvInt("REDIS_PORT", 6379),
				Password:     getEnv("REDIS_PASSWORD", ""),
				DB:           getEnvInt("REDIS_DB", 0),
				PoolSize:     getEnvInt("REDIS_POOL_SIZE", 10),
				MinIdleConns: getEnvInt("REDIS_MIN_IDLE_CONNS", 5),
				DialTimeout:  getEnvDuration("REDIS_DIAL_TIMEOUT", 5*time.Second),
				ReadTimeout:  getEnvDuration("REDIS_READ_TIMEOUT", 3*time.Second),
				WriteTimeout: getEnvDuration("REDIS_WRITE_TIMEOUT", 3*time.Second),
				PoolTimeout:  getEnvDuration("REDIS_POOL_TIMEOUT", 4*time.Second),
				IdleTimeout:  getEnvDuration("REDIS_IDLE_TIMEOUT", 5*time.Minute),
				MaxRetries:   getEnvInt("REDIS_MAX_RETRIES", 3),
			},
			Memory: MemoryConfig{
				MaxSize: getEnvInt("MEMORY_CACHE_MAX_SIZE", 1000),
				TTL:     getEnvDuration("MEMORY_CACHE_TTL", 15*time.Minute),
			},
		},
	}

	// Validate required fields
	if cfg.JWT.Secret == "" {
		return nil, fmt.Errorf("JWT_SECRET environment variable is required")
	}

	if len(cfg.JWT.Secret) < 32 {
		return nil, fmt.Errorf("JWT_SECRET must be at least 32 characters, got %d", len(cfg.JWT.Secret))
	}

	// Validate database configuration
	if cfg.Database.Type == "postgres" {
		if cfg.Database.Host == "" {
			return nil, fmt.Errorf("DB_HOST is required for PostgreSQL")
		}
		if cfg.Database.User == "" {
			return nil, fmt.Errorf("DB_USER is required for PostgreSQL")
		}
		if cfg.Database.Password == "" {
			return nil, fmt.Errorf("DB_PASSWORD is required for PostgreSQL")
		}
		if cfg.Database.DBName == "" {
			return nil, fmt.Errorf("DB_NAME is required for PostgreSQL")
		}
	} else if cfg.Database.Type != "sqlite" {
		return nil, fmt.Errorf("DB_TYPE must be either 'sqlite' or 'postgres', got '%s'", cfg.Database.Type)
	}

	// Validate cache configuration
	if cfg.Cache.Type != "memory" && cfg.Cache.Type != "redis" {
		return nil, fmt.Errorf("CACHE_TYPE must be either 'memory' or 'redis', got '%s'", cfg.Cache.Type)
	}

	if cfg.Cache.Type == "redis" {
		if cfg.Cache.Redis.Host == "" {
			return nil, fmt.Errorf("REDIS_HOST is required when using Redis cache")
		}
	}

	return cfg, nil
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intVal, err := strconv.Atoi(value); err == nil {
			return intVal
		}
	}
	return defaultValue
}

func getEnvDuration(key string, defaultValue time.Duration) time.Duration {
	if value := os.Getenv(key); value != "" {
		if duration, err := time.ParseDuration(value); err == nil {
			return duration
		}
	}
	return defaultValue
}
