package tests
//go:build testutils



import (
	"bytes"
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	_ "github.com/lib/pq"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"api-key-generator/internal/config"
	"api-key-generator/internal/controllers"
	"api-key-generator/internal/middleware"
	"api-key-generator/internal/models"
	"api-key-generator/internal/repositories"
	"api-key-generator/internal/services"
)

// TestDB holds the test database connection
var TestDB *sql.DB

// setupTestDatabase creates a test database connection
func setupTestDatabase(t *testing.T) *sql.DB {
	if TestDB != nil {
		return TestDB
	}

	// Use test database connection string
	testDBURL := os.Getenv("TEST_DATABASE_URL")
	if testDBURL == "" {
		testDBURL = "postgres://test:test@localhost:5432/nutrition_test?sslmode=disable"
	}

	db, err := sql.Open("postgres", testDBURL)
	require.NoError(t, err, "Failed to connect to test database")

	// Test the connection
	err = db.Ping()
	require.NoError(t, err, "Failed to ping test database")

	TestDB = db
	return db
}

// cleanupTestDatabase cleans up the test database
func cleanupTestDatabase(t *testing.T) {
	if TestDB == nil {
		return
	}

	// Clean up test data
	tables := []string{"meal_plans", "user_profiles", "users"}
	for _, table := range tables {
		_, err := TestDB.Exec(fmt.Sprintf("DELETE FROM %s WHERE email LIKE '%%test%%'", table))
		if err != nil {
			t.Logf("Warning: Failed to clean table %s: %v", table, err)
		}
	}
}

// setupTestRouter creates a test router with all middleware and routes
func setupTestRouter() *gin.Engine {
	gin.SetMode(gin.TestMode)
	router := gin.New()

	// Add test configuration
	cfg := &config.Config{
		ServerPort:  "8080",
		Environment: "test",
		JWTSecret:   "test-jwt-secret-key-for-testing-only",
		DatabaseURL: "postgres://test:test@localhost:5432/nutrition_test?sslmode=disable",
		AllowedOrigins: []string{
			"https://nutrifit.com",
			"https://app.nutrifit.com",
			"https://admin.nutrifit.com",
		},
		EnableCORS:      true,
		EnableRateLimit: true,
	}

	// Add middleware
	router.Use(middleware.Logger())
	router.Use(middleware.Recovery())
	router.Use(middleware.SecurityHeaders())

	if cfg.EnableCORS {
		router.Use(middleware.CORS(cfg.AllowedOrigins))
	}

	if cfg.EnableRateLimit {
		router.Use(middleware.RateLimit(10, time.Minute))
	}

	// Setup database
	db := setupTestDatabase(nil)
	defer db.Close()

	// Initialize repositories
	userRepo := repositories.NewUserRepository(db)
	mealPlanRepo := repositories.NewMealPlanRepository(db)

	// Initialize services
	userService := services.NewUserService(userRepo)
	mealPlanService := services.NewMealPlanService(mealPlanRepo)
	authService := services.NewAuthService(userService, cfg.JWTSecret)

	// Initialize controllers
	authController := controllers.NewAuthController(authService)
	userController := controllers.NewUserController(userService)
	mealPlanController := controllers.NewMealPlanController(mealPlanService)

	// Setup routes
	api := router.Group("/api")
	{
		// Health check
		api.GET("/health", func(c *gin.Context) {
			c.JSON(http.StatusOK, gin.H{"status": "healthy"})
		})

		// Auth routes
		auth := api.Group("/auth")
		{
			auth.POST("/register", authController.Register)
			auth.POST("/login", authController.Login)
			auth.GET("/validate", middleware.JWTAuth(cfg.JWTSecret), authController.ValidateToken)
		}

		// User routes
		users := api.Group("/users")
		users.Use(middleware.JWTAuth(cfg.JWTSecret))
		{
			users.GET("/profile", userController.GetProfile)
			users.PUT("/profile", userController.UpdateProfile)
		}

		// Meal plan routes
		mealPlans := api.Group("/meal-plans")
		mealPlans.Use(middleware.JWTAuth(cfg.JWTSecret))
		{
			mealPlans.GET("/", mealPlanController.GetMealPlans)
			mealPlans.POST("/", mealPlanController.CreateMealPlan)
			mealPlans.PUT("/:id", mealPlanController.UpdateMealPlan)
			mealPlans.DELETE("/:id", mealPlanController.DeleteMealPlan)
		}
	}

	return router
}

// createTestUser creates a test user in the database
func createTestUser(t *testing.T, email, password string) *models.User {
	db := setupTestDatabase(t)
	userRepo := repositories.NewUserRepository(db)
	userService := services.NewUserService(userRepo)

	user, err := userService.CreateUser(email, password)
	require.NoError(t, err)
	require.NotEmpty(t, user.ID)

	return user
}

// getTestJWTToken generates a JWT token for testing
func getTestJWTToken(t *testing.T, email, password string) string {
	router := setupTestRouter()

	loginReq := map[string]string{
		"email":    email,
		"password": password,
	}

	// First create the user if it doesn't exist
	createTestUser(t, email, password)

	// Then login to get token
	req := httptest.NewRequest("POST", "/api/auth/login", nil)
	req.Header.Set("Content-Type", "application/json")

	// Use a JSON writer for the request body
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("Failed to login: %d - %s", w.Code, w.Body.String())
	}

	var response map[string]string
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)

	token, exists := response["token"]
	require.True(t, exists, "Token not found in response")
	require.NotEmpty(t, token)

	return token
}

// makeAuthenticatedRequest makes an HTTP request with JWT authentication
func makeAuthenticatedRequest(t *testing.T, method, url, token string, body interface{}) *httptest.ResponseRecorder {
	var reqBody *bytes.Buffer
	if body != nil {
		jsonBody, err := json.Marshal(body)
		require.NoError(t, err)
		reqBody = bytes.NewBuffer(jsonBody)
	} else {
		reqBody = bytes.NewBuffer(nil)
	}

	req := httptest.NewRequest(method, url, reqBody)
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	req.Header.Set("Content-Type", "application/json")

	w := httptest.NewRecorder()
	router := setupTestRouter()
	router.ServeHTTP(w, req)

	return w
}

// assertSecurityHeaders validates that all required security headers are present
func assertSecurityHeaders(t *testing.T, w *httptest.ResponseRecorder) {
	headers := w.Header()

	// Content Security Policy
	csp := headers.Get("Content-Security-Policy")
	assert.NotEmpty(t, csp, "Content-Security-Policy header should be present")
	assert.Contains(t, csp, "default-src 'self'", "CSP should restrict to same origin")

	// Strict Transport Security
	hsts := headers.Get("Strict-Transport-Security")
	assert.NotEmpty(t, hsts, "Strict-Transport-Security header should be present")
	assert.Contains(t, hsts, "max-age=31536000", "HSTS should have max-age of 1 year")

	// X-Content-Type-Options
	xcto := headers.Get("X-Content-Type-Options")
	assert.Equal(t, "nosniff", xcto, "X-Content-Type-Options should be nosniff")

	// X-Frame-Options
	xfo := headers.Get("X-Frame-Options")
	assert.Equal(t, "DENY", xfo, "X-Frame-Options should be DENY")

	// X-XSS-Protection
	xxsp := headers.Get("X-XSS-Protection")
	assert.Equal(t, "1; mode=block", xxsp, "X-XSS-Protection should be enabled")

	// Referrer Policy
	rp := headers.Get("Referrer-Policy")
	assert.NotEmpty(t, rp, "Referrer-Policy header should be present")

	// Permissions Policy
	pp := headers.Get("Permissions-Policy")
	assert.NotEmpty(t, pp, "Permissions-Policy header should be present")
}

// TestMain is the main entry point for tests
func TestMain(m *testing.M) {
	// Setup test environment
	gin.SetMode(gin.TestMode)

	// Run tests
	code := m.Run()

	// Cleanup
	if TestDB != nil {
		TestDB.Close()
	}

	os.Exit(code)
}

// MockRequest represents a mock HTTP request for testing
type MockRequest struct {
	Method  string
	Path    string
	Body    interface{}
	Headers map[string]string
	Token   string
}

// MockResponse represents a mock HTTP response for testing
type MockResponse struct {
	Status  int
	Body    interface{}
	Headers map[string]string
}

// SecurityTestResult represents the result of a security test
type SecurityTestResult struct {
	TestName    string
	Passed      bool
	Description string
	Error       string
}

// RunSecurityTests runs a suite of security tests
func RunSecurityTests(t *testing.T, tests []func(*testing.T) SecurityTestResult) []SecurityTestResult {
	results := make([]SecurityTestResult, 0, len(tests))

	for _, test := range tests {
		result := test(t)
		results = append(results, result)

		if !result.Passed {
			t.Logf("Security test failed: %s - %s", result.TestName, result.Error)
		}
	}

	return results
}
