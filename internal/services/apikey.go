package services

import (
	"context"
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"time"

	"api-key-generator/internal/config"
	"api-key-generator/internal/models"
	"api-key-generator/internal/utils"

	"github.com/google/uuid"
)

// APIKeyService handles API key operations
type APIKeyService struct {
	db  *sql.DB
	cfg *config.Config
	// Prepared statements for frequently used queries
	getByKeyStmt    *sql.Stmt
	hasAnyKeysStmt  *sql.Stmt
	validateKeyStmt *sql.Stmt
}

// ensureAPIKeyTables creates required tables if they do not exist (useful for tests and first run on SQLite)
func ensureAPIKeyTables(db *sql.DB) error {
	queries := []string{
		`CREATE TABLE IF NOT EXISTS api_keys (
			id TEXT PRIMARY KEY,
			key TEXT UNIQUE NOT NULL,
			name TEXT NOT NULL,
			description TEXT,
			permissions TEXT NOT NULL,
			is_active BOOLEAN NOT NULL DEFAULT 1,
			expires_at DATETIME,
			last_used_at DATETIME,
			created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			usage_count INTEGER NOT NULL DEFAULT 0,
			rate_limit INTEGER,
			rate_limit_used INTEGER NOT NULL DEFAULT 0
		);`,
		`CREATE TABLE IF NOT EXISTS api_key_usage (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			api_key_id TEXT NOT NULL,
			endpoint TEXT NOT NULL,
			method TEXT NOT NULL,
			status INTEGER NOT NULL,
			timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			ip_address TEXT,
			user_agent TEXT,
			FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE CASCADE
		);`,
		`CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys(key);`,
		`CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON api_keys(is_active);`,
		`CREATE INDEX IF NOT EXISTS idx_usage_api_key_id ON api_key_usage(api_key_id);`,
	}
	for _, q := range queries {
		if _, err := db.Exec(q); err != nil {
			return fmt.Errorf("failed to ensure api key tables: %w", err)
		}
	}
	return nil
}


// NewAPIKeyService creates a new API key service with prepared statements
func NewAPIKeyService(db *sql.DB, cfg *config.Config) (*APIKeyService, error) {
	// Ensure tables exist (especially in tests or fresh SQLite)
	if err := ensureAPIKeyTables(db); err != nil {
		return nil, err
	}

	s := &APIKeyService{
		db:  db,
		cfg: cfg,
	}

	// Prepare frequently used statements
	var err error

	// Prepare GetAPIKeyByKey statement
	s.getByKeyStmt, err = db.Prepare(`
		SELECT id, key, name, description, permissions, is_active, 
			   expires_at, last_used_at, created_at, updated_at, 
			   usage_count, rate_limit, rate_limit_used
		FROM api_keys 
		WHERE key = ? AND is_active = 1
	`)
	if err != nil {
		return nil, fmt.Errorf("failed to prepare getByKey statement: %w", err)
	}

	// Prepare HasAnyKeys statement
	s.hasAnyKeysStmt, err = db.Prepare("SELECT COUNT(1) FROM api_keys")
	if err != nil {
		s.Close() // Clean up already prepared statements
		return nil, fmt.Errorf("failed to prepare hasAnyKeys statement: %w", err)
	}

	// Prepare ValidateKey statement
	s.validateKeyStmt, err = db.Prepare(`
		SELECT id, is_active, expires_at 
		FROM api_keys 
		WHERE key = ?
	`)
	if err != nil {
		s.Close()
		return nil, fmt.Errorf("failed to prepare validateKey statement: %w", err)
	}

	return s, nil
}

// Close closes all prepared statements
func (s *APIKeyService) Close() error {
	var errs []error

	if s.getByKeyStmt != nil {
		if err := s.getByKeyStmt.Close(); err != nil {
			errs = append(errs, fmt.Errorf("getByKeyStmt: %w", err))
		}
	}

	if s.hasAnyKeysStmt != nil {
		if err := s.hasAnyKeysStmt.Close(); err != nil {
			errs = append(errs, fmt.Errorf("hasAnyKeysStmt: %w", err))
		}
	}

	if s.validateKeyStmt != nil {
		if err := s.validateKeyStmt.Close(); err != nil {
			errs = append(errs, fmt.Errorf("validateKeyStmt: %w", err))
		}
	}

	if len(errs) > 0 {
		return fmt.Errorf("errors closing prepared statements: %v", errs)
	}

	return nil
}

// HasAnyKeys returns true if any API key exists
func (s *APIKeyService) HasAnyKeys(ctx context.Context) (bool, error) {
	var count int
	err := s.hasAnyKeysStmt.QueryRowContext(ctx).Scan(&count)
	if err != nil {
		return false, err
	}
	return count > 0, nil
}

// ValidateKey checks whether a raw API key string is valid and active
func (s *APIKeyService) ValidateKey(ctx context.Context, rawKey string) (bool, error) {
	if rawKey == "" {
		return false, fmt.Errorf("API key is empty")
	}
	key, err := s.GetAPIKeyByKey(ctx, rawKey)
	if err != nil {
		return false, err
	}
	return key != nil, nil
}

// CreateAPIKey creates a new API key
func (s *APIKeyService) CreateAPIKey(ctx context.Context, req *models.CreateAPIKeyRequest) (*models.APIKey, error) {
	// Input validation
	if err := s.validateCreateRequest(req); err != nil {
		return nil, fmt.Errorf("validation failed: %w", err)
	}

	// Generate secure API key
	key, err := s.generateAPIKey()
	if err != nil {
		return nil, fmt.Errorf("failed to generate API key: %w", err)
	}

	// Calculate expiry date
	var expiresAt *time.Time
	if req.ExpiryDays != nil {
		expiry := time.Now().UTC().AddDate(0, 0, *req.ExpiryDays)
		expiresAt = &expiry
	} else {
		expiry := time.Now().UTC().Add(s.cfg.APIKey.ExpiryDuration)
		expiresAt = &expiry
	}

	// Create API key model
	apiKey := &models.APIKey{
		ID:          uuid.New().String(),
		Key:         key,
		Name:        req.Name,
		Description: req.Description,
		Permissions: req.Permissions,
		IsActive:    true,
		ExpiresAt:   expiresAt,
		CreatedAt:   time.Now().UTC(),
		UpdatedAt:   time.Now().UTC(),
		UsageCount:  0,
		RateLimit:   req.RateLimit,
	}

	// Serialize permissions
	permissionsJSON, err := json.Marshal(apiKey.Permissions)
	if err != nil {
		return nil, fmt.Errorf("failed to serialize permissions: %w", err)
	}

	// Insert into database
	query := `
		INSERT INTO api_keys (
			id, key, name, description, permissions, is_active, 
			expires_at, created_at, updated_at, usage_count, rate_limit
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`

	_, err = s.db.ExecContext(ctx, query,
		apiKey.ID,
		apiKey.Key,
		apiKey.Name,
		apiKey.Description,
		string(permissionsJSON),
		apiKey.IsActive,
		apiKey.ExpiresAt,
		apiKey.CreatedAt,
		apiKey.UpdatedAt,
		apiKey.UsageCount,
		apiKey.RateLimit,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create API key: %w", err)
	}

	return apiKey, nil
}

// GetAPIKey retrieves an API key by ID
func (s *APIKeyService) GetAPIKey(ctx context.Context, id string) (*models.APIKey, error) {
	if id == "" {
		return nil, fmt.Errorf("API key ID cannot be empty")
	}

	query := `
		SELECT id, key, name, description, permissions, is_active, 
			   expires_at, last_used_at, created_at, updated_at, 
			   usage_count, rate_limit, rate_limit_used
		FROM api_keys 
		WHERE id = ?
	`

	var apiKey models.APIKey
	var permissionsJSON string

	err := s.db.QueryRowContext(ctx, query, id).Scan(
		&apiKey.ID,
		&apiKey.Key,
		&apiKey.Name,
		&apiKey.Description,
		&permissionsJSON,
		&apiKey.IsActive,
		&apiKey.ExpiresAt,
		&apiKey.LastUsedAt,
		&apiKey.CreatedAt,
		&apiKey.UpdatedAt,
		&apiKey.UsageCount,
		&apiKey.RateLimit,
		&apiKey.RateLimitUsed,
	)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("API key not found")
		}
		return nil, fmt.Errorf("failed to get API key: %w", err)
	}

	// Deserialize permissions
	if err := json.Unmarshal([]byte(permissionsJSON), &apiKey.Permissions); err != nil {
		return nil, fmt.Errorf("failed to deserialize permissions: %w", err)
	}

	return &apiKey, nil
}

// GetAPIKeyByKey retrieves an API key by its key value (uses prepared statement)
func (s *APIKeyService) GetAPIKeyByKey(ctx context.Context, key string) (*models.APIKey, error) {
	if key == "" {
		return nil, fmt.Errorf("API key cannot be empty")
	}

	var apiKey models.APIKey
	var permissionsJSON string

	err := s.getByKeyStmt.QueryRowContext(ctx, key).Scan(
		&apiKey.ID,
		&apiKey.Key,
		&apiKey.Name,
		&apiKey.Description,
		&permissionsJSON,
		&apiKey.IsActive,
		&apiKey.ExpiresAt,
		&apiKey.LastUsedAt,
		&apiKey.CreatedAt,
		&apiKey.UpdatedAt,
		&apiKey.UsageCount,
		&apiKey.RateLimit,
		&apiKey.RateLimitUsed,
	)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("API key not found or inactive")
		}
		return nil, fmt.Errorf("failed to get API key: %w", err)
	}

	// Check if expired
	if apiKey.ExpiresAt != nil && apiKey.ExpiresAt.Before(time.Now().UTC()) {
		return nil, fmt.Errorf("API key has expired")
	}

	// Deserialize permissions
	if err := json.Unmarshal([]byte(permissionsJSON), &apiKey.Permissions); err != nil {
		return nil, fmt.Errorf("failed to deserialize permissions: %w", err)
	}

	return &apiKey, nil
}

// ListAPIKeys lists API keys with pagination and filters
func (s *APIKeyService) ListAPIKeys(ctx context.Context, params *models.ListAPIKeysParams) (*models.ListAPIKeysResponse, error) {
	// Set defaults
	if params.Page <= 0 {
		params.Page = 1
	}
	if params.Limit <= 0 || params.Limit > 100 {
		params.Limit = 20
	}

	// Build query with filters
	query := `
		SELECT id, key, name, description, permissions, is_active, 
			   expires_at, last_used_at, created_at, updated_at, 
			   usage_count, rate_limit, rate_limit_used
		FROM api_keys 
		WHERE 1=1
	`
	args := []interface{}{}

	if params.Search != "" {
		query += " AND (name LIKE ? OR description LIKE ?)"
		searchTerm := "%" + params.Search + "%"
		args = append(args, searchTerm, searchTerm)
	}

	if params.IsActive != nil {
		query += " AND is_active = ?"
		args = append(args, *params.IsActive)
	}

	if params.UserID != "" {
		query += " AND user_id = ?"
		args = append(args, params.UserID)
	}

	// Add ordering and pagination
	query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
	args = append(args, params.Limit, (params.Page-1)*params.Limit)

	// Execute query
	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to list API keys: %w", err)
	}
	defer func() {
		_ = rows.Close()
	}()

	// Scan results
	var apiKeys []models.APIKey
	for rows.Next() {
		var apiKey models.APIKey
		var permissionsJSON string

		err := rows.Scan(
			&apiKey.ID,
			&apiKey.Key,
			&apiKey.Name,
			&apiKey.Description,
			&permissionsJSON,
			&apiKey.IsActive,
			&apiKey.ExpiresAt,
			&apiKey.LastUsedAt,
			&apiKey.CreatedAt,
			&apiKey.UpdatedAt,
			&apiKey.UsageCount,
			&apiKey.RateLimit,
			&apiKey.RateLimitUsed,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan API key: %w", err)
		}

		// Deserialize permissions
		if err := json.Unmarshal([]byte(permissionsJSON), &apiKey.Permissions); err != nil {
			return nil, fmt.Errorf("failed to deserialize permissions: %w", err)
		}

		// Mask the key for security (show only first 8 and last 4 characters)
		if len(apiKey.Key) > 12 {
			apiKey.Key = apiKey.Key[:8] + "..." + apiKey.Key[len(apiKey.Key)-4:]
		}

		apiKeys = append(apiKeys, apiKey)
	}

	// Check for iteration errors
	if err = rows.Err(); err != nil {
		return nil, fmt.Errorf("error during row iteration: %w", err)
	}

	// Get total count
	countQuery := "SELECT COUNT(*) FROM api_keys WHERE 1=1"
	countArgs := []interface{}{}

	if params.Search != "" {
		countQuery += " AND (name LIKE ? OR description LIKE ?)"
		searchTerm := "%" + params.Search + "%"
		countArgs = append(countArgs, searchTerm, searchTerm)
	}

	if params.IsActive != nil {
		countQuery += " AND is_active = ?"
		countArgs = append(countArgs, *params.IsActive)
	}

	if params.UserID != "" {
		countQuery += " AND user_id = ?"
		countArgs = append(countArgs, params.UserID)
	}

	var total int
	err = s.db.QueryRowContext(ctx, countQuery, countArgs...).Scan(&total)
	if err != nil {
		return nil, fmt.Errorf("failed to count API keys: %w", err)
	}

	// Build response
	response := &models.ListAPIKeysResponse{
		APIKeys: apiKeys,
		Pagination: models.PaginationResponse{
			Page:       params.Page,
			Limit:      params.Limit,
			Total:      total,
			TotalPages: (total + params.Limit - 1) / params.Limit,
		},
	}

	return response, nil
}

// UpdateAPIKey updates an API key
func (s *APIKeyService) UpdateAPIKey(ctx context.Context, id string, req *models.UpdateAPIKeyRequest) (*models.APIKey, error) {
	if id == "" {
		return nil, fmt.Errorf("API key ID cannot be empty")
	}

	// Get existing API key
	existing, err := s.GetAPIKey(ctx, id)
	if err != nil {
		return nil, fmt.Errorf("failed to get existing API key: %w", err)
	}

	// Build update query dynamically
	setParts := []string{}
	args := []interface{}{}

	if req.Name != nil {
		setParts = append(setParts, "name = ?")
		args = append(args, *req.Name)
	}
	if req.Description != nil {
		setParts = append(setParts, "description = ?")
		args = append(args, *req.Description)
	}
	if req.Permissions != nil {
		permissionsJSON, err := json.Marshal(req.Permissions)
		if err != nil {
			return nil, fmt.Errorf("failed to serialize permissions: %w", err)
		}
		setParts = append(setParts, "permissions = ?")
		args = append(args, string(permissionsJSON))
	}
	if req.IsActive != nil {
		setParts = append(setParts, "is_active = ?")
		args = append(args, *req.IsActive)
	}
	if req.RateLimit != nil {
		setParts = append(setParts, "rate_limit = ?")
		args = append(args, *req.RateLimit)
	}

	if len(setParts) == 0 {
		return existing, nil // No updates needed
	}

	setParts = append(setParts, "updated_at = ?")
	args = append(args, time.Now().UTC())
	args = append(args, id)

	// Build parameterized query safely
	if len(setParts) == 0 {
		return existing, nil
	}
	query := fmt.Sprintf("UPDATE api_keys SET %s WHERE id = ?", strings.Join(setParts, ", ")) // #nosec G201 - Validated dynamic query

	// Execute update
	_, err = s.db.ExecContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to update API key: %w", err)
	}

	// Get updated API key
	updated, err := s.GetAPIKey(ctx, id)
	if err != nil {
		return nil, fmt.Errorf("failed to get updated API key: %w", err)
	}

	return updated, nil
}

// DeleteAPIKey deletes an API key
func (s *APIKeyService) DeleteAPIKey(ctx context.Context, id string) error {
	if id == "" {
		return fmt.Errorf("API key ID cannot be empty")
	}

	// Check if API key exists
	_, err := s.GetAPIKey(ctx, id)
	if err != nil {
		return fmt.Errorf("failed to get API key: %w", err)
	}

	// Delete from database
	query := "DELETE FROM api_keys WHERE id = ?"
	_, err = s.db.ExecContext(ctx, query, id)
	if err != nil {
		return fmt.Errorf("failed to delete API key: %w", err)
	}

	return nil
}

// RecordUsage records API key usage
func (s *APIKeyService) RecordUsage(ctx context.Context, apiKeyID, endpoint, method string, status int, ipAddress, userAgent string) error {
	// Use transaction for atomicity
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	// Insert usage record
	usageQuery := `
		INSERT INTO api_key_usage (api_key_id, endpoint, method, status, ip_address, user_agent)
		VALUES (?, ?, ?, ?, ?, ?)
	`
	_, err = tx.ExecContext(ctx, usageQuery, apiKeyID, endpoint, method, status, ipAddress, userAgent)
	if err != nil {
		return fmt.Errorf("failed to record usage: %w", err)
	}

	// Update usage_count, last_used_at and increment rate_limit_used (free-tier enforcement)
	updateQuery := `
        UPDATE api_keys 
        SET usage_count = usage_count + 1,
            rate_limit_used = rate_limit_used + 1,
            last_used_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    `
	_, err = tx.ExecContext(ctx, updateQuery, apiKeyID)
	if err != nil {
		return fmt.Errorf("failed to update usage count: %w", err)
	}

	return tx.Commit()
}

// GetAvailablePermissions returns available permissions
func (s *APIKeyService) GetAvailablePermissions() []models.Permission {
	return models.AvailablePermissions
}

// RenewAPIKey extends the expiry of an API key by the specified number of days.
// If extendDays <= 0, the configured ExpiryDuration is used relative to now.
// When extendDays > 0, the expiry is set to max(current_expiry, now) + extendDays.
func (s *APIKeyService) RenewAPIKey(ctx context.Context, id string, extendDays int) (*models.APIKey, error) {
	if id == "" {
		return nil, fmt.Errorf("API key ID cannot be empty")
	}

	existing, err := s.GetAPIKey(ctx, id)
	if err != nil {
		return nil, fmt.Errorf("failed to get API key: %w", err)
	}

	var newExpiry time.Time
	now := time.Now().UTC()
	if extendDays <= 0 {
		newExpiry = now.Add(s.cfg.APIKey.ExpiryDuration)
	} else {
		base := now
		if existing.ExpiresAt != nil && existing.ExpiresAt.After(now) {
			base = *existing.ExpiresAt
		}
		newExpiry = base.AddDate(0, 0, extendDays)
	}

	query := "UPDATE api_keys SET expires_at = ?, updated_at = ? WHERE id = ?"
	if _, err := s.db.ExecContext(ctx, query, newExpiry, now, id); err != nil {
		return nil, fmt.Errorf("failed to renew API key: %w", err)
	}

	updated, err := s.GetAPIKey(ctx, id)
	if err != nil {
		return nil, fmt.Errorf("failed to get updated API key: %w", err)
	}
	return updated, nil
}

// AuthorizeAny validates the API key and checks if it has at least one of the required permissions (scopes).
// It returns the resolved API key record to enable callers to record usage or perform additional checks.
func (s *APIKeyService) AuthorizeAny(ctx context.Context, rawKey string, requiredPermissions []string) (*models.APIKey, bool, error) {
	if len(requiredPermissions) == 0 {
		// No specific permission required; only validate key
		key, err := s.GetAPIKeyByKey(ctx, rawKey)
		if err != nil {
			return nil, false, err
		}
		return key, true, nil
	}

	key, err := s.GetAPIKeyByKey(ctx, rawKey)
	if err != nil {
		return nil, false, err
	}

	if hasAnyPermission(key.Permissions, requiredPermissions) {
		return key, true, nil
	}
	return key, false, nil
}

// AuthorizeAll validates the API key and checks if it has all required permissions (scopes).
// It returns the resolved API key record to enable callers to record usage or perform additional checks.
func (s *APIKeyService) AuthorizeAll(ctx context.Context, rawKey string, requiredPermissions []string) (*models.APIKey, bool, error) {
	if len(requiredPermissions) == 0 {
		key, err := s.GetAPIKeyByKey(ctx, rawKey)
		if err != nil {
			return nil, false, err
		}
		return key, true, nil
	}

	key, err := s.GetAPIKeyByKey(ctx, rawKey)
	if err != nil {
		return nil, false, err
	}

	if hasAllPermissions(key.Permissions, requiredPermissions) {
		return key, true, nil
	}
	return key, false, nil
}

// hasAnyPermission returns true if the granted list contains at least one of the required permissions.
// Comparison is case-insensitive.
func hasAnyPermission(granted, required []string) bool {
	if len(required) == 0 {
		return true
	}
	grantedSet := make(map[string]struct{}, len(granted))
	for _, p := range granted {
		grantedSet[strings.ToLower(p)] = struct{}{}
	}
	for _, r := range required {
		if _, ok := grantedSet[strings.ToLower(r)]; ok {
			return true
		}
	}
	return false
}

// ValidateAPIKey validates if an API key exists and is active
func (s *APIKeyService) ValidateAPIKey(apiKey string) (bool, error) {
	// Create context with timeout to prevent hanging
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	_, err := s.GetAPIKeyByKey(ctx, apiKey)
	if err != nil {
		if strings.Contains(err.Error(), "not found") {
			return false, nil
		}
		return false, err
	}
	return true, nil
}

// hasAllPermissions returns true if the granted list contains all required permissions.
// Comparison is case-insensitive.
func hasAllPermissions(granted, required []string) bool {
	if len(required) == 0 {
		return true
	}
	if len(granted) == 0 {
		return false
	}
	grantedSet := make(map[string]struct{}, len(granted))
	for _, p := range granted {
		grantedSet[strings.ToLower(p)] = struct{}{}
	}
	for _, r := range required {
		if _, ok := grantedSet[strings.ToLower(r)]; !ok {
			return false
		}
	}
	return true
}

// Private helper methods

// generateAPIKey generates a cryptographically secure API key
func (s *APIKeyService) generateAPIKey() (string, error) {
	// Generate random bytes
	bytes := make([]byte, s.cfg.APIKey.Length)
	if _, err := rand.Read(bytes); err != nil {
		return "", fmt.Errorf("failed to generate random bytes: %w", err)
	}

	// Convert to hex and add prefix
	key := s.cfg.APIKey.Prefix + hex.EncodeToString(bytes)
	return key, nil
}

// validateCreateRequest validates the create API key request
func (s *APIKeyService) validateCreateRequest(req *models.CreateAPIKeyRequest) error {
	if req.Name == "" {
		return fmt.Errorf("name is required")
	}
	if len(req.Name) < 2 || len(req.Name) > 100 {
		return fmt.Errorf("name must be between 2 and 100 characters")
	}
	if len(req.Permissions) == 0 {
		return fmt.Errorf("at least one permission is required")
	}
	if req.ExpiryDays != nil && (*req.ExpiryDays < 1 || *req.ExpiryDays > 3650) {
		return fmt.Errorf("expiry days must be between 1 and 3650")
	}
	if req.RateLimit != nil && (*req.RateLimit < 1 || *req.RateLimit > 10000) {
		return fmt.Errorf("rate limit must be between 1 and 10000")
	}

	// Validate permissions
	validPermissions := make(map[string]bool)
	for _, perm := range models.AvailablePermissions {
		validPermissions[perm.Name] = true
	}

	for _, perm := range req.Permissions {
		if !validPermissions[perm] {
			log.Printf("Invalid permission attempted: %s", utils.SanitizeForLog(perm))
			return fmt.Errorf("invalid permission: %s", utils.SanitizeForLog(perm))
		}
	}

	return nil
}
