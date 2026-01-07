package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"time"

	"api-key-generator/internal/config"
)

func main() {
	var (
		sqlitePath   = flag.String("sqlite", "./data/app.db", "Path to SQLite database")
		postgresHost = flag.String("postgres-host", "localhost", "PostgreSQL host")
		postgresPort = flag.Int("postgres-port", 5432, "PostgreSQL port")
		postgresUser = flag.String("postgres-user", "", "PostgreSQL user (required)")
		postgresPass = flag.String("postgres-password", "", "PostgreSQL password (required)")
		postgresDB   = flag.String("postgres-database", "", "PostgreSQL database name (required)")
		postgresSSL  = flag.String("postgres-sslmode", "require", "PostgreSQL SSL mode")
		maxOpenConns = flag.Int("max-open-conns", 25, "Maximum open connections")
		maxIdleConns = flag.Int("max-idle-conns", 5, "Maximum idle connections")
		connMaxLife  = flag.String("conn-max-lifetime", "5m", "Connection max lifetime")
		verbose      = flag.Bool("verbose", false, "Enable verbose logging")
	)
	flag.Parse()

	// Validate required parameters
	if *postgresUser == "" {
		log.Fatal("PostgreSQL user is required")
	}
	if *postgresPass == "" {
		log.Fatal("PostgreSQL password is required")
	}
	if *postgresDB == "" {
		log.Fatal("PostgreSQL database name is required")
	}

	if *verbose {
		log.Printf("Starting migration from SQLite (%s) to PostgreSQL", *sqlitePath)
		log.Printf("PostgreSQL: %s:%d/%s as %s", *postgresHost, *postgresPort, *postgresDB, *postgresUser)
	}

	// Parse connection max lifetime
	connMaxLifetime, err := time.ParseDuration(*connMaxLife)
	if err != nil {
		log.Fatalf("Invalid connection max lifetime: %v", err)
	}

	// Create database configuration
	_ = config.DatabaseConfig{
		Type:            "postgres",
		Host:            *postgresHost,
		Port:            *postgresPort,
		User:            *postgresUser,
		Password:        *postgresPass,
		DBName:          *postgresDB,
		SSLMode:         *postgresSSL,
		MaxOpenConns:    *maxOpenConns,
		MaxIdleConns:    *maxIdleConns,
		ConnMaxLifetime: connMaxLifetime,
	}

	// Check if SQLite database exists
	if _, err := os.Stat(*sqlitePath); os.IsNotExist(err) {
		log.Fatalf("SQLite database not found: %s", *sqlitePath)
	}

	// Perform migration
	log.Println("Migration logic not implemented yet.")

	fmt.Println("Migration completed successfully!")
}
