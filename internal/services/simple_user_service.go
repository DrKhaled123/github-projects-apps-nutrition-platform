package services

import (
	"context"
	"database/sql"
	"fmt"
	"log"
	"time"
)

// SimpleUserServiceExample demonstrates Q30S dependency injection approach
// This is an example implementation showing simple patterns instead of complex frameworks

// SimpleDatabase interface for loose coupling (Q30S Approach)
// Simple interface instead of complex ORM
type SimpleDatabase interface {
	QueryContext(ctx context.Context, query string, args ...interface{}) (*sql.Rows, error)
	ExecContext(ctx context.Context, query string, args ...interface{}) (sql.Result, error)
	Close() error
}

// SimpleUser represents a user in the system
type SimpleUser struct {
	ID        int       `json:"id"`
	Name      string    `json:"name"`
	Email     string    `json:"email"`
	CreatedAt time.Time `json:"created_at"`
}

// SimpleUserService with constructor injection (Q30S Approach)
// Simple struct with injected dependencies instead of complex DI framework
type SimpleUserService struct {
	db     SimpleDatabase
	logger *log.Logger
}

// NewSimpleUserService creates a new SimpleUserService with dependency injection
// Constructor injection is simple and doesn't require framework magic
func NewSimpleUserService(db SimpleDatabase, logger *log.Logger) *SimpleUserService {
	return &SimpleUserService{
		db:     db,
		logger: logger,
	}
}

// GetUserByID retrieves a user by ID
func (s *SimpleUserService) GetUserByID(ctx context.Context, id int) (*SimpleUser, error) {
	query := "SELECT id, name, email, created_at FROM users WHERE id = $1"

	rows, err := s.db.QueryContext(ctx, query, id)
	if err != nil {
		s.logger.Printf("Error querying user %d: %v", id, err)
		return nil, fmt.Errorf("failed to query user: %w", err)
	}
	defer rows.Close()

	if !rows.Next() {
		return nil, fmt.Errorf("user not found")
	}

	var user SimpleUser
	err = rows.Scan(&user.ID, &user.Name, &user.Email, &user.CreatedAt)
	if err != nil {
		s.logger.Printf("Error scanning user %d: %v", id, err)
		return nil, fmt.Errorf("failed to scan user: %w", err)
	}

	return &user, nil
}

// CreateUser creates a new user
func (s *SimpleUserService) CreateUser(ctx context.Context, name, email string) (*SimpleUser, error) {
	query := "INSERT INTO users (name, email, created_at) VALUES ($1, $2, $3) RETURNING id"

	now := time.Now()
	var userID int

	_, err := s.db.ExecContext(ctx, query, name, email, now)
	if err != nil {
		s.logger.Printf("Error creating user %s: %v", name, err)
		return nil, fmt.Errorf("failed to create user: %w", err)
	}

	// Get the inserted ID (this is a simplified approach)
	// In real implementation, you'd use RETURNING clause or LastInsertId()
	userID = 1 // Placeholder

	user := &SimpleUser{
		ID:        userID,
		Name:      name,
		Email:     email,
		CreatedAt: now,
	}

	s.logger.Printf("Created user: %s (ID: %d)", name, userID)
	return user, nil
}

// ListUsers retrieves all users with pagination
func (s *SimpleUserService) ListUsers(ctx context.Context, limit, offset int) ([]SimpleUser, error) {
	query := "SELECT id, name, email, created_at FROM users ORDER BY created_at DESC LIMIT $1 OFFSET $2"

	rows, err := s.db.QueryContext(ctx, query, limit, offset)
	if err != nil {
		s.logger.Printf("Error querying users: %v", err)
		return nil, fmt.Errorf("failed to query users: %w", err)
	}
	defer rows.Close()

	var users []SimpleUser
	for rows.Next() {
		var user SimpleUser
		err := rows.Scan(&user.ID, &user.Name, &user.Email, &user.CreatedAt)
		if err != nil {
			s.logger.Printf("Error scanning user row: %v", err)
			continue
		}
		users = append(users, user)
	}

	if err = rows.Err(); err != nil {
		s.logger.Printf("Error iterating user rows: %v", err)
		return nil, fmt.Errorf("error iterating users: %w", err)
	}

	return users, nil
}

// SimpleMockDatabase provides a mock implementation for testing
// Simple mock instead of complex mocking framework
type SimpleMockDatabase struct {
	users map[int]*SimpleUser
	nextID int
}

func NewSimpleMockDatabase() *SimpleMockDatabase {
	return &SimpleMockDatabase{
		users:  make(map[int]*SimpleUser),
		nextID: 1,
	}
}

func (m *SimpleMockDatabase) QueryContext(ctx context.Context, query string, args ...interface{}) (*sql.Rows, error) {
	// Simplified mock implementation
	// In a real scenario, you'd parse the SQL and return appropriate mock data
	return nil, fmt.Errorf("mock query not implemented")
}

func (m *SimpleMockDatabase) ExecContext(ctx context.Context, query string, args ...interface{}) (sql.Result, error) {
	// Simplified mock implementation
	return nil, fmt.Errorf("mock exec not implemented")
}

func (m *SimpleMockDatabase) Close() error {
	return nil
}
