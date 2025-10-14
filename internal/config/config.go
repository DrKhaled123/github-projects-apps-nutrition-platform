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
}

type ServerConfig struct {
	Port string
	Host string
}

type DatabaseConfig struct {
	Path string
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

func Load() (*Config, error) {
	cfg := &Config{
		Server: ServerConfig{
			Port: getEnv("PORT", "8081"),
			Host: getEnv("HOST", "0.0.0.0"),
		},
		Database: DatabaseConfig{
			Path: getEnv("DB_PATH", "./data/app.db"),
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
	}

	// Validate required fields
	if cfg.JWT.Secret == "" {
		return nil, fmt.Errorf("JWT_SECRET environment variable is required")
	}

	if len(cfg.JWT.Secret) < 32 {
		return nil, fmt.Errorf("JWT_SECRET must be at least 32 characters, got %d", len(cfg.JWT.Secret))
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
