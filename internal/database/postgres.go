package database

import (
	"context"
	"database/sql"
	"fmt"
	"log"
	"os"
	"strconv"
	"time"

	_ "github.com/lib/pq"
)

// PostgresDB wraps a PostgreSQL connection pool with production-ready configuration
type PostgresDB struct {
	db     *sql.DB
	config *Config
}

// Config holds PostgreSQL connection configuration
type Config struct {
	Host            string
	Port            int
	User            string
	Password        string
	Database        string
	SSLMode         string
	MaxOpenConns    int
	MaxIdleConns    int
	ConnMaxLifetime time.Duration
	ConnMaxIdleTime time.Duration
}

// NewPostgresDB creates a new PostgreSQL connection with production optimizations
func NewPostgresDB(cfg Config) (*PostgresDB, error) {
	connStr := fmt.Sprintf(
		"host=%s port=%d user=%s password=%s dbname=%s sslmode=%s",
		cfg.Host, cfg.Port, cfg.User, cfg.Password, cfg.Database, cfg.SSLMode,
	)

	db, err := sql.Open("postgres", connStr)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	// Configure connection pool for production
	db.SetMaxOpenConns(cfg.MaxOpenConns)
	db.SetMaxIdleConns(cfg.MaxIdleConns)
	db.SetConnMaxLifetime(cfg.ConnMaxLifetime)
	db.SetConnMaxIdleTime(cfg.ConnMaxIdleTime)

	// Test connection with retries
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	for i := 0; i < 5; i++ {
		if err := db.PingContext(ctx); err == nil {
			break
		}
		if i == 4 {
			return nil, fmt.Errorf("failed to ping database after 5 attempts: %w", err)
		}
		log.Printf("Database ping attempt %d failed, retrying...", i+1)
		time.Sleep(time.Duration(i+1) * time.Second)
	}

	log.Printf("✅ PostgreSQL connection established to %s:%d/%s", cfg.Host, cfg.Port, cfg.Database)

	return &PostgresDB{
		db:     db,
		config: &cfg,
	}, nil
}

// GetDB returns the underlying database connection
func (p *PostgresDB) GetDB() *sql.DB {
	return p.db
}

// GetConnectionPoolStats returns detailed connection pool statistics
func (p *PostgresDB) GetConnectionPoolStats() map[string]interface{} {
	stats := p.db.Stats()
	return map[string]interface{}{
		"open_connections":     stats.OpenConnections,
		"in_use":               stats.InUse,
		"idle":                 stats.Idle,
		"wait_count":           stats.WaitCount,
		"wait_duration":        stats.WaitDuration,
		"max_idle_closed":      stats.MaxIdleClosed,
		"max_idle_time_closed": stats.MaxIdleTimeClosed,
		"max_lifetime_closed":  stats.MaxLifetimeClosed,
		"max_open_connections": stats.MaxOpenConnections,
		"max_idle_connections": p.config.MaxIdleConns,
	}
}

// HealthCheck performs a comprehensive database health check
func (p *PostgresDB) HealthCheck(ctx context.Context) error {
	// Basic connectivity check
	if err := p.db.PingContext(ctx); err != nil {
		return fmt.Errorf("database ping failed: %w", err)
	}

	// Check if we can query
	var version string
	if err := p.db.QueryRowContext(ctx, "SELECT version()").Scan(&version); err != nil {
		return fmt.Errorf("failed to query database version: %w", err)
	}

	// Check table access
	var tableCount int
	if err := p.db.QueryRowContext(ctx,
		"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'").Scan(&tableCount); err != nil {
		return fmt.Errorf("failed to count tables: %w", err)
	}

	log.Printf("✅ Database health check passed - Version: %s, Tables: %d", version, tableCount)
	return nil
}

// Close closes the database connection gracefully
func (p *PostgresDB) Close() error {
	if p.db != nil {
		log.Printf("🔌 Closing PostgreSQL connection...")
		return p.db.Close()
	}
	return nil
}

// BeginTransaction starts a new database transaction
func (p *PostgresDB) BeginTransaction(ctx context.Context) (*sql.Tx, error) {
	tx, err := p.db.BeginTx(ctx, &sql.TxOptions{
		Isolation: sql.LevelReadCommitted,
		ReadOnly:  false,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to begin transaction: %w", err)
	}
	return tx, nil
}

// BeginReadOnlyTransaction starts a read-only transaction
func (p *PostgresDB) BeginReadOnlyTransaction(ctx context.Context) (*sql.Tx, error) {
	tx, err := p.db.BeginTx(ctx, &sql.TxOptions{
		Isolation: sql.LevelReadCommitted,
		ReadOnly:  true,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to begin read-only transaction: %w", err)
	}
	return tx, nil
}

// ExecuteInTransaction executes a function within a database transaction
func (p *PostgresDB) ExecuteInTransaction(ctx context.Context, fn func(*sql.Tx) error) error {
	tx, err := p.BeginTransaction(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback()

	if err := fn(tx); err != nil {
		return fmt.Errorf("transaction function failed: %w", err)
	}

	if err := tx.Commit(); err != nil {
		return fmt.Errorf("failed to commit transaction: %w", err)
	}

	return nil
}

// GetProductionConfig returns a production-optimized configuration
func GetProductionConfig() Config {
	return Config{
		Host:            getEnv("DB_HOST", "localhost"),
		Port:            getEnvInt("DB_PORT", 5432),
		User:            getEnv("DB_USER", "doctorhealthy"),
		Password:        getEnv("DB_PASSWORD", ""),
		Database:        getEnv("DB_NAME", "doctorhealthy"),
		SSLMode:         "require",
		MaxOpenConns:    25,              // Conservative for health data
		MaxIdleConns:    10,              // Keep some connections ready
		ConnMaxLifetime: 5 * time.Minute, // Recreate connections periodically
		ConnMaxIdleTime: 1 * time.Minute, // Don't keep idle connections too long
	}
}

// GetDevelopmentConfig returns a development-friendly configuration
func GetDevelopmentConfig() Config {
	return Config{
		Host:            getEnv("DB_HOST", "localhost"),
		Port:            getEnvInt("DB_PORT", 5432),
		User:            getEnv("DB_USER", "doctorhealthy"),
		Password:        getEnv("DB_PASSWORD", ""),
		Database:        getEnv("DB_NAME", "doctorhealthy_dev"),
		SSLMode:         "disable",
		MaxOpenConns:    10,
		MaxIdleConns:    5,
		ConnMaxLifetime: 1 * time.Hour,
		ConnMaxIdleTime: 30 * time.Minute,
	}
}

// RunMigrations executes database migrations from SQL files
func (p *PostgresDB) RunMigrations(ctx context.Context, migrationSQL string) error {
	log.Printf("🔄 Running database migrations...")

	if _, err := p.db.ExecContext(ctx, migrationSQL); err != nil {
		return fmt.Errorf("migration execution failed: %w", err)
	}

	log.Printf("✅ Database migrations completed successfully")
	return nil
}

// CreatePartitions creates monthly partitions for audit logs
func (p *PostgresDB) CreatePartitions(ctx context.Context) error {
	log.Printf("🔄 Creating audit log partitions...")

	query := `SELECT create_monthly_audit_partition()`
	if _, err := p.db.ExecContext(ctx, query); err != nil {
		return fmt.Errorf("failed to create partitions: %w", err)
	}

	log.Printf("✅ Audit log partitions created successfully")
	return nil
}

// CleanupOldAuditLogs removes audit logs older than retention period
func (p *PostgresDB) CleanupOldAuditLogs(ctx context.Context) error {
	log.Printf("🧹 Cleaning up old audit logs...")

	query := `SELECT cleanup_old_audit_logs()`
	result, err := p.db.ExecContext(ctx, query)
	if err != nil {
		return fmt.Errorf("failed to cleanup old audit logs: %w", err)
	}

	rowsAffected, _ := result.RowsAffected()
	log.Printf("✅ Cleaned up %d old audit log entries", rowsAffected)
	return nil
}

// GetDatabaseStatistics returns comprehensive database statistics
func (p *PostgresDB) GetDatabaseStatistics(ctx context.Context) (map[string]interface{}, error) {
	stats := make(map[string]interface{})

	// Connection pool stats
	stats["connection_pool"] = p.GetConnectionPoolStats()

	// Database size stats
	var dbSize string
	err := p.db.QueryRowContext(ctx,
		"SELECT pg_size_pretty(pg_database_size(current_database()))").Scan(&dbSize)
	if err == nil {
		stats["database_size"] = dbSize
	}

	// Table row counts
	tables := []string{"users", "api_keys", "audit_events", "nutrition_plans", "workout_plans", "recipes"}
	tableStats := make(map[string]int64)

	for _, table := range tables {
		var count int64
		err := p.db.QueryRowContext(ctx,
			fmt.Sprintf("SELECT COUNT(*) FROM %s", table)).Scan(&count)
		if err == nil {
			tableStats[table] = count
		}
	}
	stats["table_row_counts"] = tableStats

	// Recent activity
	var recentActivity int64
	err = p.db.QueryRowContext(ctx,
		"SELECT COUNT(*) FROM audit_events WHERE timestamp > NOW() - INTERVAL '24 hours'").Scan(&recentActivity)
	if err == nil {
		stats["recent_activity_24h"] = recentActivity
	}

	return stats, nil
}

// InitializePostgres initializes a PostgreSQL database connection using our Config
func InitializePostgres(cfg Config) (*sql.DB, error) {
	pgDB, err := NewPostgresDB(cfg)
	if err != nil {
		return nil, fmt.Errorf("failed to create PostgreSQL connection: %w", err)
	}
	return pgDB.GetDB(), nil
}

// runMigrations executes database migrations (placeholder implementation)
func runMigrations(db *sql.DB) error {
	// Basic migration check - create a simple migration tracking table
	query := `
		CREATE TABLE IF NOT EXISTS migration_version (
			version INTEGER PRIMARY KEY,
			applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		);`

	_, err := db.Exec(query)
	if err != nil {
		return fmt.Errorf("failed to create migration table: %w", err)
	}

	// Check current migration version
	var currentVersion int
	err = db.QueryRow("SELECT COALESCE(MAX(version), 0) FROM migration_version").Scan(&currentVersion)
	if err != nil {
		return fmt.Errorf("failed to check migration version: %w", err)
	}

	// Apply migrations if needed (simplified implementation)
	if currentVersion == 0 {
		// Apply initial migration
		if err := applyInitialMigration(db); err != nil {
			return fmt.Errorf("failed to apply initial migration: %w", err)
		}

		// Record migration
		_, err = db.Exec("INSERT INTO migration_version (version) VALUES (1)")
		if err != nil {
			return fmt.Errorf("failed to record migration: %w", err)
		}
	}

	return nil
}

// applyInitialMigration applies the initial database schema
func applyInitialMigration(db *sql.DB) error {
	// This is a simplified version - in production you'd load from migration files
	log.Printf("🔄 Applying initial database migration...")

	// Create basic tables that match the SQLite schema
	tables := []string{
		`CREATE TABLE IF NOT EXISTS api_keys (
			id TEXT PRIMARY KEY,
			key TEXT UNIQUE NOT NULL,
			name TEXT NOT NULL,
			description TEXT,
			user_id TEXT,
			permissions TEXT NOT NULL,
			is_active BOOLEAN NOT NULL DEFAULT true,
			expires_at TIMESTAMP,
			last_used_at TIMESTAMP,
			created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
			updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
			usage_count INTEGER NOT NULL DEFAULT 0,
			rate_limit INTEGER,
			rate_limit_used INTEGER NOT NULL DEFAULT 0
		)`,
		`CREATE TABLE IF NOT EXISTS api_key_usage (
			id SERIAL PRIMARY KEY,
			api_key_id TEXT NOT NULL,
			endpoint TEXT NOT NULL,
			method TEXT NOT NULL,
			status INTEGER NOT NULL,
			timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
			ip_address TEXT,
			user_agent TEXT,
			FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE CASCADE
		)`,
		`CREATE TABLE IF NOT EXISTS users (
			id TEXT PRIMARY KEY,
			name TEXT NOT NULL,
			email TEXT UNIQUE NOT NULL,
			age INTEGER NOT NULL,
			weight DECIMAL NOT NULL,
			height DECIMAL NOT NULL,
			gender TEXT NOT NULL,
			activity_level TEXT NOT NULL,
			metabolic_rate TEXT NOT NULL,
			goal TEXT NOT NULL,
			food_dislikes TEXT,
			allergies TEXT,
			diseases TEXT,
			medications TEXT,
			preferred_cuisine TEXT,
			language TEXT DEFAULT 'en',
			created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
			updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
		)`,
		`CREATE TABLE IF NOT EXISTS nutrition_plans (
			id TEXT PRIMARY KEY,
			user_id TEXT NOT NULL,
			calories_per_day INTEGER NOT NULL,
			protein_grams DECIMAL NOT NULL,
			carbs_grams DECIMAL NOT NULL,
			fats_grams DECIMAL NOT NULL,
			plan_type TEXT NOT NULL,
			calculation_method TEXT,
			disclaimer TEXT,
			created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
		)`,
		`CREATE TABLE IF NOT EXISTS workout_plans (
			id TEXT PRIMARY KEY,
			user_id TEXT NOT NULL,
			goal TEXT NOT NULL,
			workout_type TEXT NOT NULL,
			created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
		)`,
		`CREATE TABLE IF NOT EXISTS recipes (
			id TEXT PRIMARY KEY,
			name TEXT NOT NULL,
			cuisine TEXT NOT NULL,
			prep_time INTEGER,
			cook_time INTEGER,
			servings INTEGER,
			calories INTEGER,
			difficulty TEXT,
			created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
		)`,
	}

	for _, query := range tables {
		if _, err := db.Exec(query); err != nil {
			return fmt.Errorf("failed to create table: %w", err)
		}
	}

	log.Printf("✅ Initial database migration completed successfully")
	return nil
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
