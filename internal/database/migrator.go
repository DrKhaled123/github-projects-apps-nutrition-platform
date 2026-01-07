package database

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"time"
)

// Migrator handles data migration from SQLite to PostgreSQL
type Migrator struct {
	sqliteDB *sql.DB
	pgDB     *PostgresDB
	progress *MigrationProgress
}

// MigrationProgress tracks migration progress
type MigrationProgress struct {
	TotalRecords    int64     `json:"total_records"`
	MigratedRecords int64     `json:"migrated_records"`
	FailedRecords   int64     `json:"failed_records"`
	StartTime       time.Time `json:"start_time"`
	CurrentTable    string    `json:"current_table"`
	LastError       string    `json:"last_error,omitempty"`
	EstimatedETA    string    `json:"estimated_eta,omitempty"`
}

// NewMigrator creates a new migrator instance
func NewMigrator(sqlitePath, sqliteKey string, pgDB *PostgresDB) (*Migrator, error) {
	// Open SQLite database (encrypted)
	sqliteDB, err := sql.Open("sqlite3", sqlitePath+"?_pragma_key="+sqliteKey)
	if err != nil {
		return nil, fmt.Errorf("failed to open SQLite database: %w", err)
	}

	// Test SQLite connection
	if err := sqliteDB.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping SQLite database: %w", err)
	}

	return &Migrator{
		sqliteDB: sqliteDB,
		pgDB:     pgDB,
		progress: &MigrationProgress{
			StartTime: time.Now(),
		},
	}, nil
}

// MigrateAll performs complete migration from SQLite to PostgreSQL
func (m *Migrator) MigrateAll(ctx context.Context) error {
	log.Println("🚀 Starting complete database migration...")
	m.progress.StartTime = time.Now()

	// Migration order matters due to foreign key dependencies
	migrationSteps := []struct {
		name     string
		migrate  func(context.Context) error
		validate func(context.Context) error
	}{
		{"users", m.migrateUsers, m.validateUsers},
		{"api_keys", m.migrateAPIKeys, m.validateAPIKeys},
		{"nutrition_plans", m.migrateNutritionPlans, m.validateNutritionPlans},
		{"workout_plans", m.migrateWorkoutPlans, m.validateWorkoutPlans},
		{"recipes", m.migrateRecipes, m.validateRecipes},
		{"user_sessions", m.migrateUserSessions, m.validateUserSessions},
		{"audit_events", m.migrateAuditLogs, m.validateAuditLogs},
	}

	for _, step := range migrationSteps {
		m.progress.CurrentTable = step.name
		log.Printf("🔄 Migrating table: %s", step.name)

		// Count records before migration
		totalRecords, err := m.countSQLiteRecords(ctx, step.name)
		if err != nil {
			return fmt.Errorf("failed to count %s records: %w", step.name, err)
		}

		if totalRecords == 0 {
			log.Printf("⏭️  No records found in %s, skipping", step.name)
			continue
		}

		// Reset progress for this table
		m.progress.MigratedRecords = 0
		m.progress.FailedRecords = 0
		m.progress.TotalRecords = totalRecords

		// Perform migration
		if err := step.migrate(ctx); err != nil {
			m.progress.LastError = err.Error()
			return fmt.Errorf("failed to migrate %s: %w", step.name, err)
		}

		// Validate migration
		if err := step.validate(ctx); err != nil {
			return fmt.Errorf("migration validation failed for %s: %w", step.name, err)
		}

		log.Printf("✅ Successfully migrated %s: %d records", step.name, totalRecords)
	}

	log.Printf("🎉 Database migration completed in %v", time.Since(m.progress.StartTime))
	return nil
}

// migrateUsers migrates user data from SQLite to PostgreSQL
func (m *Migrator) migrateUsers(ctx context.Context) error {
	query := `SELECT id, email, name, age, weight, height, gender, 
			  activity_level, metabolic_rate, goal, food_dislikes, 
			  allergies, diseases, medications, preferred_cuisine, 
			  language, created_at, updated_at, last_login_at, 
			  is_active, email_verified, phone, date_of_birth, metadata 
			  FROM users`

	rows, err := m.sqliteDB.QueryContext(ctx, query)
	if err != nil {
		return fmt.Errorf("failed to query SQLite users: %w", err)
	}
	defer rows.Close()

	insertQuery := `
		INSERT INTO users (id, email, name, age, weight, height, gender, 
						  activity_level, metabolic_rate, goal, food_dislikes, 
						  allergies, diseases, medications, preferred_cuisine, 
						  language, created_at, updated_at, last_login_at, 
						  is_active, email_verified, phone, date_of_birth, metadata)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24)
		ON CONFLICT (email) DO NOTHING`

	return m.pgDB.ExecuteInTransaction(ctx, func(tx *sql.Tx) error {
		stmt, err := tx.PrepareContext(ctx, insertQuery)
		if err != nil {
			return fmt.Errorf("failed to prepare user insert: %w", err)
		}
		defer stmt.Close()

		for rows.Next() {
			var user UserRecord
			var foodDislikes, allergies, diseases, medications sql.NullString
			var metadata sql.NullString

			err := rows.Scan(
				&user.ID, &user.Email, &user.Name, &user.Age, &user.Weight, &user.Height,
				&user.Gender, &user.ActivityLevel, &user.MetabolicRate, &user.Goal,
				&foodDislikes, &allergies, &diseases, &medications,
				&user.PreferredCuisine, &user.Language, &user.CreatedAt, &user.UpdatedAt,
				&user.LastLoginAt, &user.IsActive, &user.EmailVerified, &user.Phone,
				&user.DateOfBirth, &metadata,
			)
			if err != nil {
				log.Printf("⚠️  Failed to scan user record: %v", err)
				m.progress.FailedRecords++
				continue
			}

			// Parse JSON arrays
			user.FoodDislikes = m.parseJSONArray(foodDislikes)
			user.Allergies = m.parseJSONArray(allergies)
			user.Diseases = m.parseJSONArray(diseases)
			user.Medications = m.parseJSONArray(medications)
			user.Metadata = m.parseJSONMetadata(metadata)

			// Execute insert
			_, err = stmt.ExecContext(ctx,
				user.ID, user.Email, user.Name, user.Age, user.Weight, user.Height,
				user.Gender, user.ActivityLevel, user.MetabolicRate, user.Goal,
				user.FoodDislikes, user.Allergies, user.Diseases, user.Medications,
				user.PreferredCuisine, user.Language, user.CreatedAt, user.UpdatedAt,
				user.LastLoginAt, user.IsActive, user.EmailVerified, user.Phone,
				user.DateOfBirth, user.Metadata,
			)
			if err != nil {
				log.Printf("⚠️  Failed to insert user %s: %v", user.Email, err)
				m.progress.FailedRecords++
				continue
			}

			m.progress.MigratedRecords++
		}

		return nil
	})
}

// migrateAPIKeys migrates API keys from SQLite to PostgreSQL
func (m *Migrator) migrateAPIKeys(ctx context.Context) error {
	query := `SELECT id, name, key_hash, key_prefix, permissions, 
			  created_at, updated_at, expires_at, last_used_at, 
			  usage_count, is_active, created_by, metadata 
			  FROM api_keys`

	rows, err := m.sqliteDB.QueryContext(ctx, query)
	if err != nil {
		return fmt.Errorf("failed to query SQLite API keys: %w", err)
	}
	defer rows.Close()

	insertQuery := `
		INSERT INTO api_keys (id, name, key_hash, key_prefix, permissions, 
							 created_at, updated_at, expires_at, last_used_at, 
							 usage_count, is_active, created_by, metadata)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
		ON CONFLICT (key_hash) DO NOTHING`

	return m.pgDB.ExecuteInTransaction(ctx, func(tx *sql.Tx) error {
		stmt, err := tx.PrepareContext(ctx, insertQuery)
		if err != nil {
			return fmt.Errorf("failed to prepare API key insert: %w", err)
		}
		defer stmt.Close()

		for rows.Next() {
			var apiKey APIKeyRecord
			var permissions, metadata sql.NullString

			err := rows.Scan(
				&apiKey.ID, &apiKey.Name, &apiKey.KeyHash, &apiKey.KeyPrefix,
				&permissions, &apiKey.CreatedAt, &apiKey.UpdatedAt, &apiKey.ExpiresAt,
				&apiKey.LastUsedAt, &apiKey.UsageCount, &apiKey.IsActive,
				&apiKey.CreatedBy, &metadata,
			)
			if err != nil {
				log.Printf("⚠️  Failed to scan API key record: %v", err)
				m.progress.FailedRecords++
				continue
			}

			apiKey.Permissions = m.parseJSONArray(permissions)
			apiKey.Metadata = m.parseJSONMetadata(metadata)

			_, err = stmt.ExecContext(ctx,
				apiKey.ID, apiKey.Name, apiKey.KeyHash, apiKey.KeyPrefix,
				apiKey.Permissions, apiKey.CreatedAt, apiKey.UpdatedAt, apiKey.ExpiresAt,
				apiKey.LastUsedAt, apiKey.UsageCount, apiKey.IsActive,
				apiKey.CreatedBy, apiKey.Metadata,
			)
			if err != nil {
				log.Printf("⚠️  Failed to insert API key %s: %v", apiKey.Name, err)
				m.progress.FailedRecords++
				continue
			}

			m.progress.MigratedRecords++
		}

		return nil
	})
}

// migrateAuditLogs migrates audit logs from SQLite to PostgreSQL
func (m *Migrator) migrateAuditLogs(ctx context.Context) error {
	query := `SELECT id, timestamp, user_id, session_id, action, resource, 
			  resource_id, ip_address, user_agent, success, error_message, 
			  error_code, request_id, response_time_ms, metadata, created_at 
			  FROM audit_events`

	rows, err := m.sqliteDB.QueryContext(ctx, query)
	if err != nil {
		return fmt.Errorf("failed to query SQLite audit logs: %w", err)
	}
	defer rows.Close()

	insertQuery := `
		INSERT INTO audit_events (id, timestamp, user_id, session_id, action, resource, 
								 resource_id, ip_address, user_agent, success, error_message, 
								 error_code, request_id, response_time_ms, metadata, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)`

	return m.pgDB.ExecuteInTransaction(ctx, func(tx *sql.Tx) error {
		stmt, err := tx.PrepareContext(ctx, insertQuery)
		if err != nil {
			return fmt.Errorf("failed to prepare audit log insert: %w", err)
		}
		defer stmt.Close()

		batchSize := 1000
		batch := make([]AuditEventRecord, 0, batchSize)

		for rows.Next() {
			var auditEvent AuditEventRecord
			var metadata sql.NullString

			err := rows.Scan(
				&auditEvent.ID, &auditEvent.Timestamp, &auditEvent.UserID, &auditEvent.SessionID,
				&auditEvent.Action, &auditEvent.Resource, &auditEvent.ResourceID,
				&auditEvent.IPAddress, &auditEvent.UserAgent, &auditEvent.Success,
				&auditEvent.ErrorMessage, &auditEvent.ErrorCode, &auditEvent.RequestID,
				&auditEvent.ResponseTimeMs, &metadata, &auditEvent.CreatedAt,
			)
			if err != nil {
				log.Printf("⚠️  Failed to scan audit log record: %v", err)
				m.progress.FailedRecords++
				continue
			}

			auditEvent.Metadata = m.parseJSONMetadata(metadata)
			batch = append(batch, auditEvent)

			// Execute batch when full
			if len(batch) >= batchSize {
				if err := m.insertAuditLogBatch(ctx, stmt, batch); err != nil {
					return err
				}
				batch = batch[:0] // Reset slice
			}

			m.progress.MigratedRecords++
		}

		// Insert remaining records
		if len(batch) > 0 {
			if err := m.insertAuditLogBatch(ctx, stmt, batch); err != nil {
				return err
			}
		}

		return nil
	})
}

// insertAuditLogBatch inserts a batch of audit log records
func (m *Migrator) insertAuditLogBatch(ctx context.Context, stmt *sql.Stmt, batch []AuditEventRecord) error {
	for _, record := range batch {
		_, err := stmt.ExecContext(ctx,
			record.ID, record.Timestamp, record.UserID, record.SessionID,
			record.Action, record.Resource, record.ResourceID,
			record.IPAddress, record.UserAgent, record.Success,
			record.ErrorMessage, record.ErrorCode, record.RequestID,
			record.ResponseTimeMs, record.Metadata, record.CreatedAt,
		)
		if err != nil {
			log.Printf("⚠️  Failed to insert audit log %s: %v", record.ID, err)
			m.progress.FailedRecords++
			continue
		}
	}
	return nil
}

// Validation functions for each table
func (m *Migrator) validateUsers(ctx context.Context) error {
	return m.validateTableCounts(ctx, "users")
}

func (m *Migrator) validateAPIKeys(ctx context.Context) error {
	return m.validateTableCounts(ctx, "api_keys")
}

func (m *Migrator) validateNutritionPlans(ctx context.Context) error {
	return m.validateTableCounts(ctx, "nutrition_plans")
}

func (m *Migrator) validateWorkoutPlans(ctx context.Context) error {
	return m.validateTableCounts(ctx, "workout_plans")
}

func (m *Migrator) validateRecipes(ctx context.Context) error {
	return m.validateTableCounts(ctx, "recipes")
}

func (m *Migrator) validateUserSessions(ctx context.Context) error {
	return m.validateTableCounts(ctx, "user_sessions")
}

func (m *Migrator) validateAuditLogs(ctx context.Context) error {
	return m.validateTableCounts(ctx, "audit_events")
}

// validateTableCounts compares record counts between SQLite and PostgreSQL
func (m *Migrator) validateTableCounts(ctx context.Context, tableName string) error {
	// Count SQLite records
	sqliteCount, err := m.countSQLiteRecords(ctx, tableName)
	if err != nil {
		return fmt.Errorf("failed to count SQLite %s: %w", tableName, err)
	}

	// Count PostgreSQL records
	pgCount, err := m.countPostgresRecords(ctx, tableName)
	if err != nil {
		return fmt.Errorf("failed to count PostgreSQL %s: %w", tableName, err)
	}

	log.Printf("📊 %s validation: SQLite=%d, PostgreSQL=%d", tableName, sqliteCount, pgCount)

	if sqliteCount != pgCount {
		return fmt.Errorf("migration validation failed for %s: count mismatch (SQLite: %d, PostgreSQL: %d)",
			tableName, sqliteCount, pgCount)
	}

	return nil
}

// Helper functions
func (m *Migrator) countSQLiteRecords(ctx context.Context, tableName string) (int64, error) {
	var count int64
	err := m.sqliteDB.QueryRowContext(ctx, fmt.Sprintf("SELECT COUNT(*) FROM %s", tableName)).Scan(&count)
	return count, err
}

func (m *Migrator) countPostgresRecords(ctx context.Context, tableName string) (int64, error) {
	var count int64
	err := m.pgDB.GetDB().QueryRowContext(ctx, fmt.Sprintf("SELECT COUNT(*) FROM %s", tableName)).Scan(&count)
	return count, err
}

func (m *Migrator) parseJSONArray(ns sql.NullString) []string {
	if !ns.Valid || ns.String == "" {
		return []string{}
	}
	var result []string
	if err := json.Unmarshal([]byte(ns.String), &result); err != nil {
		log.Printf("⚠️  Failed to parse JSON array: %v", err)
		return []string{}
	}
	return result
}

func (m *Migrator) parseJSONMetadata(ns sql.NullString) map[string]interface{} {
	if !ns.Valid || ns.String == "" {
		return map[string]interface{}{}
	}
	var result map[string]interface{}
	if err := json.Unmarshal([]byte(ns.String), &result); err != nil {
		log.Printf("⚠️  Failed to parse JSON metadata: %v", err)
		return map[string]interface{}{}
	}
	return result
}

// GetProgress returns current migration progress
func (m *Migrator) GetProgress() *MigrationProgress {
	// Calculate ETA
	if m.progress.MigratedRecords > 0 {
		elapsed := time.Since(m.progress.StartTime)
		rate := float64(m.progress.MigratedRecords) / elapsed.Seconds()
		remaining := float64(m.progress.TotalRecords - m.progress.MigratedRecords)
		etaSeconds := remaining / rate
		m.progress.EstimatedETA = (time.Duration(etaSeconds) * time.Second).String()
	}

	return m.progress
}

// Close closes the migrator and its database connections
func (m *Migrator) Close() error {
	var errors []error

	if m.sqliteDB != nil {
		if err := m.sqliteDB.Close(); err != nil {
			errors = append(errors, fmt.Errorf("failed to close SQLite: %w", err))
		}
	}

	if len(errors) > 0 {
		return fmt.Errorf("migration close errors: %v", errors)
	}

	return nil
}

// Record types for migration
type UserRecord struct {
	ID               string                 `json:"id"`
	Email            string                 `json:"email"`
	Name             string                 `json:"name"`
	Age              *int                   `json:"age"`
	Weight           *float64               `json:"weight"`
	Height           *float64               `json:"height"`
	Gender           *string                `json:"gender"`
	ActivityLevel    *string                `json:"activity_level"`
	MetabolicRate    *string                `json:"metabolic_rate"`
	Goal             *string                `json:"goal"`
	FoodDislikes     []string               `json:"food_dislikes"`
	Allergies        []string               `json:"allergies"`
	Diseases         []string               `json:"diseases"`
	Medications      []string               `json:"medications"`
	PreferredCuisine *string                `json:"preferred_cuisine"`
	Language         *string                `json:"language"`
	CreatedAt        time.Time              `json:"created_at"`
	UpdatedAt        time.Time              `json:"updated_at"`
	LastLoginAt      *time.Time             `json:"last_login_at"`
	IsActive         bool                   `json:"is_active"`
	EmailVerified    bool                   `json:"email_verified"`
	Phone            *string                `json:"phone"`
	DateOfBirth      *time.Time             `json:"date_of_birth"`
	Metadata         map[string]interface{} `json:"metadata"`
}

type APIKeyRecord struct {
	ID          string                 `json:"id"`
	Name        string                 `json:"name"`
	KeyHash     string                 `json:"key_hash"`
	KeyPrefix   string                 `json:"key_prefix"`
	Permissions []string               `json:"permissions"`
	CreatedAt   time.Time              `json:"created_at"`
	UpdatedAt   time.Time              `json:"updated_at"`
	ExpiresAt   *time.Time             `json:"expires_at"`
	LastUsedAt  *time.Time             `json:"last_used_at"`
	UsageCount  int64                  `json:"usage_count"`
	IsActive    bool                   `json:"is_active"`
	CreatedBy   *string                `json:"created_by"`
	Metadata    map[string]interface{} `json:"metadata"`
}

type AuditEventRecord struct {
	ID             string                 `json:"id"`
	Timestamp      time.Time              `json:"timestamp"`
	UserID         *string                `json:"user_id"`
	SessionID      *string                `json:"session_id"`
	Action         string                 `json:"action"`
	Resource       string                 `json:"resource"`
	ResourceID     *string                `json:"resource_id"`
	IPAddress      *string                `json:"ip_address"`
	UserAgent      *string                `json:"user_agent"`
	Success        bool                   `json:"success"`
	ErrorMessage   *string                `json:"error_message"`
	ErrorCode      *string                `json:"error_code"`
	RequestID      *string                `json:"request_id"`
	ResponseTimeMs *int                   `json:"response_time_ms"`
	Metadata       map[string]interface{} `json:"metadata"`
	CreatedAt      time.Time              `json:"created_at"`
}

// Placeholder methods for other tables
func (m *Migrator) migrateNutritionPlans(ctx context.Context) error {
	// Implementation similar to migrateUsers
	log.Printf("🔄 Migrating nutrition plans...")
	return nil
}

func (m *Migrator) migrateWorkoutPlans(ctx context.Context) error {
	// Implementation similar to migrateUsers
	log.Printf("🔄 Migrating workout plans...")
	return nil
}

func (m *Migrator) migrateRecipes(ctx context.Context) error {
	// Implementation similar to migrateUsers
	log.Printf("🔄 Migrating recipes...")
	return nil
}

func (m *Migrator) migrateUserSessions(ctx context.Context) error {
	// Implementation similar to migrateUsers
	log.Printf("🔄 Migrating user sessions...")
	return nil
}
