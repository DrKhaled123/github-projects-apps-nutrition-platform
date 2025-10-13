// pkg/session/cookie_manager.go
package session

import (
	"crypto/rand"
	"encoding/base64"
	"fmt"
	"net/http"
	"time"

	"github.com/labstack/echo/v4"
)

// CookieConfig holds cookie configuration
type CookieConfig struct {
	Name       string
	Domain     string
	Path       string
	MaxAge     int
	Secure     bool  // Only send over HTTPS
	HttpOnly   bool  // Prevent JS access
	SameSite   http.SameSite
	AutoDetect bool  // Auto-detect HTTPS
}

// DefaultCookieConfig returns secure defaults
func DefaultCookieConfig() *CookieConfig {
	return &CookieConfig{
		Name:       "session_id",
		Path:       "/",
		MaxAge:     86400 * 365, // 1 year
		HttpOnly:   true,
		SameSite:   http.SameSiteLaxMode,
		AutoDetect: true, // Auto-detect HTTPS
	}
}

// CookieManager handles secure cookie operations
type CookieManager struct {
	config *CookieConfig
}

func NewCookieManager(config *CookieConfig) *CookieManager {
	if config == nil {
		config = DefaultCookieConfig()
	}
	return &CookieManager{config: config}
}

// GetOrCreate gets existing cookie or creates new one
func (cm *CookieManager) GetOrCreate(c echo.Context) (string, error) {
	// Try to get existing cookie
	cookie, err := c.Cookie(cm.config.Name)
	if err == nil && cookie.Value != "" {
		return cookie.Value, nil
	}

	// Generate new value
	value, err := cm.generateSecureToken()
	if err != nil {
		return "", err
	}

	// Set cookie with proper error handling
	if err := cm.Set(c, value); err != nil {
		return "", err
	}

	return value, nil
}

// Set creates and sets a cookie
func (cm *CookieManager) Set(c echo.Context, value string) error {
	cookie := &http.Cookie{
		Name:     cm.config.Name,
		Value:    value,
		Path:     cm.config.Path,
		Domain:   cm.config.Domain,
		MaxAge:   cm.config.MaxAge,
		HttpOnly: cm.config.HttpOnly,
		SameSite: cm.config.SameSite,
	}

	// Auto-detect HTTPS if enabled
	if cm.config.AutoDetect {
		cookie.Secure = cm.isHTTPS(c)
	} else {
		cookie.Secure = cm.config.Secure
	}

	// Set cookie with error handling
	c.SetCookie(cookie)

	// Verify cookie was set
	if _, err := c.Cookie(cm.config.Name); err != nil {
		return fmt.Errorf("failed to set cookie: %w", err)
	}

	return nil
}

// Delete removes a cookie
func (cm *CookieManager) Delete(c echo.Context) error {
	cookie := &http.Cookie{
		Name:   cm.config.Name,
		Value:  "",
		Path:   cm.config.Path,
		MaxAge: -1,
	}

	c.SetCookie(cookie)
	return nil
}

// isHTTPS detects if connection is over HTTPS
func (cm *CookieManager) isHTTPS(c echo.Context) bool {
	// Check request scheme
	if c.Scheme() == "https" {
		return true
	}

	// Check X-Forwarded-Proto header (behind proxy)
	if proto := c.Request().Header.Get("X-Forwarded-Proto"); proto == "https" {
		return true
	}

	// Check X-Forwarded-SSL header
	if ssl := c.Request().Header.Get("X-Forwarded-SSL"); ssl == "on" {
		return true
	}

	return false
}

// generateSecureToken generates cryptographically secure token
func (cm *CookieManager) generateSecureToken() (string, error) {
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return base64.URLEncoding.EncodeToString(b), nil
}
