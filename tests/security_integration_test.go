package tests

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// TestSecurityHeaders validates that all security headers are properly set
func TestSecurityHeaders(t *testing.T) {
	router := setupTestRouter()

	req := httptest.NewRequest("GET", "/api/health", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	// Validate security headers
	assert.Equal(t, "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
		w.Header().Get("Content-Security-Policy"))
	assert.Equal(t, "max-age=31536000; includeSubDomains", w.Header().Get("Strict-Transport-Security"))
	assert.Equal(t, "nosniff", w.Header().Get("X-Content-Type-Options"))
	assert.Equal(t, "DENY", w.Header().Get("X-Frame-Options"))
	assert.Equal(t, "1; mode=block", w.Header().Get("X-XSS-Protection"))
	assert.Equal(t, "no-referrer-when-downgrade", w.Header().Get("Referrer-Policy"))
	assert.Contains(t, w.Header().Get("Permissions-Policy"), "geolocation=()")
}

// TestCORSConfiguration validates CORS settings
func TestCORSConfiguration(t *testing.T) {
	router := setupTestRouter()

	tests := []struct {
		origin      string
		allowed     bool
		description string
	}{
		{"https://nutrifit.com", true, "Allowed origin should work"},
		{"https://app.nutrifit.com", true, "Subdomain should work"},
		{"https://admin.nutrifit.com", true, "Admin subdomain should work"},
		{"https://evil.com", false, "Unknown origin should be blocked"},
		{"http://nutrifit.com", false, "HTTP should be blocked"},
	}

	for _, test := range tests {
		t.Run(test.description, func(t *testing.T) {
			req := httptest.NewRequest("OPTIONS", "/api/auth/register", nil)
			req.Header.Set("Origin", test.origin)
			req.Header.Set("Access-Control-Request-Method", "POST")

			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			if test.allowed {
				assert.Contains(t, w.Header().Get("Access-Control-Allow-Origin"), test.origin)
			} else {
				assert.Empty(t, w.Header().Get("Access-Control-Allow-Origin"))
			}
		})
	}
}

// TestAuthenticationSecurity validates JWT security
func TestAuthenticationSecurity(t *testing.T) {
	router := setupTestRouter()

	// Test 1: Login with valid credentials
	loginReq := LoginRequest{
		Email:    "test@example.com",
		Password: "testpassword123",
	}

	reqBody, _ := json.Marshal(loginReq)
	req := httptest.NewRequest("POST", "/api/auth/login", bytes.NewBuffer(reqBody))
	req.Header.Set("Content-Type", "application/json")

	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var loginResp struct {
		Token string `json:"token"`
	}
	err := json.Unmarshal(w.Body.Bytes(), &loginResp)
	require.NoError(t, err)
	require.NotEmpty(t, loginResp.Token)

	// Test 2: Validate JWT token structure
	// JWT should have 3 parts separated by dots
	parts := bytes.Split([]byte(loginResp.Token), []byte("."))
	assert.Len(t, parts, 3, "JWT should have 3 parts")

	// Test 3: Access protected endpoint with valid token
	protectedReq := httptest.NewRequest("GET", "/api/auth/validate", nil)
	protectedReq.Header.Set("Authorization", "Bearer "+loginResp.Token)

	w2 := httptest.NewRecorder()
	router.ServeHTTP(w2, protectedReq)

	assert.Equal(t, http.StatusOK, w2.Code)

	// Test 4: Access protected endpoint with invalid token
	invalidReq := httptest.NewRequest("GET", "/api/auth/validate", nil)
	invalidReq.Header.Set("Authorization", "Bearer invalid.token.here")

	w3 := httptest.NewRecorder()
	router.ServeHTTP(w3, invalidReq)

	assert.Equal(t, http.StatusUnauthorized, w3.Code)

	// Test 5: Access protected endpoint without token
	noTokenReq := httptest.NewRequest("GET", "/api/auth/validate", nil)

	w4 := httptest.NewRecorder()
	router.ServeHTTP(w4, noTokenReq)

	assert.Equal(t, http.StatusUnauthorized, w4.Code)
}

// TestInputValidation validates input sanitization
func TestInputValidation(t *testing.T) {
	router := setupTestRouter()

	tests := []struct {
		name           string
		email          string
		password       string
		expectedStatus int
		description    string
	}{
		{
			name:           "Valid registration",
			email:          "valid@example.com",
			password:       "ValidPass123!",
			expectedStatus: http.StatusCreated,
			description:    "Valid input should work",
		},
		{
			name:           "Invalid email format",
			email:          "invalid-email",
			password:       "ValidPass123!",
			expectedStatus: http.StatusBadRequest,
			description:    "Invalid email should be rejected",
		},
		{
			name:           "Short password",
			email:          "test@example.com",
			password:       "123",
			expectedStatus: http.StatusBadRequest,
			description:    "Short password should be rejected",
		},
		{
			name:           "SQL injection attempt in email",
			email:          "'; DROP TABLE users; --",
			password:       "ValidPass123!",
			expectedStatus: http.StatusBadRequest,
			description:    "SQL injection should be rejected",
		},
		{
			name:           "XSS attempt in email",
			email:          "<script>alert('xss')</script>@example.com",
			password:       "ValidPass123!",
			expectedStatus: http.StatusBadRequest,
			description:    "XSS attempt should be rejected",
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			regReq := RegisterRequest{
				Email:    test.email,
				Password: test.password,
			}

			reqBody, _ := json.Marshal(regReq)
			req := httptest.NewRequest("POST", "/api/auth/register", bytes.NewBuffer(reqBody))
			req.Header.Set("Content-Type", "application/json")

			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			assert.Equal(t, test.expectedStatus, w.Code, test.description)
		})
	}
}

// TestRateLimiting validates API rate limiting
func TestRateLimiting(t *testing.T) {
	router := setupTestRouter()

	// Make multiple rapid requests
	for i := 0; i < 15; i++ {
		req := httptest.NewRequest("POST", "/api/auth/login", bytes.NewBuffer([]byte(`{"email":"test@example.com","password":"wrong"}`)))
		req.Header.Set("Content-Type", "application/json")
		req.RemoteAddr = "127.0.0.1:8080"

		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		// After 10 requests, should be rate limited
		if i >= 10 {
			assert.Equal(t, http.StatusTooManyRequests, w.Code, "Should be rate limited after 10 requests")
		}
	}
}

// TestHTTPSRedirect validates HTTPS enforcement
func TestHTTPSRedirect(t *testing.T) {
	router := setupTestRouter()

	req := httptest.NewRequest("GET", "/api/health", nil)
	req.Header.Set("X-Forwarded-Proto", "http")

	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	// Should redirect to HTTPS
	assert.Equal(t, http.StatusMovedPermanently, w.Code)
	assert.Contains(t, w.Header().Get("Location"), "https://")
}

// BenchmarkSecurityHeaders ensures security headers don't impact performance
func BenchmarkSecurityHeaders(b *testing.B) {
	router := setupTestRouter()

	for i := 0; i < b.N; i++ {
		req := httptest.NewRequest("GET", "/api/health", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)
	}
}
