// Package database provides DB initialization and migrations
package database

import (
	"database/sql"
	"fmt"
	"log"
	"os"
	"strings"

	appconfig "api-key-generator/internal/config"
	_ "github.com/lib/pq"
	_ "github.com/mattn/go-sqlite3"
)

// Initialize opens a SQLite database at the given path (default ./data/apikeys.db)
func Initialize(dbPath string) (*sql.DB, error) {
	if dbPath == "" {
		dbPath = "./data/apikeys.db"
	}

	log.Printf("Initializing SQLite database at %s", dbPath)
	dsn := dbPath + "?_foreign_keys=on&_journal_mode=WAL"
	db, err := sql.Open("sqlite3", dsn)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}
	if err := db.Ping(); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}
	return db, nil
}

// InitializePostgresDSN opens a PostgreSQL connection using lib/pq DSN
// Deprecated: prefer using the typed Config in postgres.go for production use.
func InitializePostgresDSN(connString string) (*sql.DB, error) {
	log.Printf("Initializing PostgreSQL connection")
	db, err := sql.Open("postgres", connString)
	if err != nil {
		return nil, fmt.Errorf("failed to open postgres: %w", err)
	}
	if err := db.Ping(); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("failed to ping postgres: %w", err)
	}
	return db, nil
}

// InitializeConfig selects and initializes DB by app config
func InitializeConfig(cfg appconfig.DatabaseConfig) (*sql.DB, error) {
	if strings.ToLower(cfg.Type) == "postgres" {
		conn := fmt.Sprintf(
			"host=%s port=%d user=%s password=%s dbname=%s sslmode=%s",
			cfg.Host, cfg.Port, cfg.User, cfg.Password, cfg.DBName, cfg.SSLMode,
		)
		db, err := sql.Open("postgres", conn)
		if err != nil {
			return nil, err
		}
		if err := db.Ping(); err != nil {
			_ = db.Close()
			return nil, err
		}
		// Pool tuning
		if cfg.MaxOpenConns > 0 {
			db.SetMaxOpenConns(cfg.MaxOpenConns)
		}
		if cfg.MaxIdleConns > 0 {
			db.SetMaxIdleConns(cfg.MaxIdleConns)
		}
		if cfg.ConnMaxLifetime > 0 {
			db.SetConnMaxLifetime(cfg.ConnMaxLifetime)
		}
		return db, nil
	}
	// default sqlite
	return Initialize(cfg.Path)
}

// Migrate applies minimal schema required by the application (SQLite)
func Migrate(db *sql.DB) error {
	log.Println("Running database migrations...")
	queries := []string{
		`CREATE TABLE IF NOT EXISTS users (
			id TEXT PRIMARY KEY,
			email TEXT UNIQUE NOT NULL,
			name TEXT,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP
		);`,
		`CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);`,
	}
	for _, q := range queries {
		if _, err := db.Exec(q); err != nil {
			return fmt.Errorf("migration failed: %w", err)
		}
	}
	return nil
}

// Close closes the DB if non-nil
func Close(db *sql.DB) error {
	if db != nil {
		return db.Close()
	}
	return nil
}

// GetConnectionType returns postgres if DATABASE_URL contains postgres, otherwise sqlite
func GetConnectionType() string {
	if strings.Contains(os.Getenv("DATABASE_URL"), "postgres") {
		return "postgres"
	}
	return "sqlite"
}
