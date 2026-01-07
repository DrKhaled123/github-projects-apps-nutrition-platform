package utils

import (
	"log"
	"os"
	"strings"
)

// SecureLogger provides secure logging functionality that prevents sensitive data exposure
type SecureLogger struct {
	enableDebug bool
}

// NewSecureLogger creates a new secure logger instance
func NewSecureLogger(enableDebug bool) *SecureLogger {
	return &SecureLogger{
		enableDebug: enableDebug,
	}
}

// SanitizeLogValue sanitizes values for logging by masking sensitive information
func (sl *SecureLogger) SanitizeLogValue(key, value string) string {
	key = strings.ToLower(key)

	// Mask sensitive keys
	sensitiveKeys := []string{
		"password", "pwd", "secret", "token", "key", "api", "jwt",
		"credential", "auth", "private", "pass",
	}

	for _, sensitiveKey := range sensitiveKeys {
		if strings.Contains(key, sensitiveKey) {
			if value == "" {
				return "[NOT_SET]"
			}
			// Show only first 4 chars
			if len(value) > 4 {
				return value[:4] + "****[REDACTED]"
			}
			return "****[REDACTED]"
		}
	}

	return value
}

// LogConfigSafely logs configuration values safely, masking sensitive data
func (sl *SecureLogger) LogConfigSafely(key, value string) {
	if !sl.enableDebug {
		return
	}

	sanitizedValue := sl.SanitizeLogValue(key, value)
	log.Printf("[DEBUG] %s: %s", key, sanitizedValue)
}

// LogBoolConfig logs boolean configuration values
func (sl *SecureLogger) LogBoolConfig(key string, value bool) {
	if !sl.enableDebug {
		return
	}

	log.Printf("[DEBUG] %s: %t", key, value)
}

// Info logs informational messages
func (sl *SecureLogger) Info(format string, args ...interface{}) {
	log.Printf("[INFO] "+format, args...)
}

// Debug logs debug messages only if debug is enabled
func (sl *SecureLogger) Debug(format string, args ...interface{}) {
	if sl.enableDebug {
		log.Printf("[DEBUG] "+format, args...)
	}
}

// Error logs error messages
func (sl *SecureLogger) Error(format string, args ...interface{}) {
	log.Printf("[ERROR] "+format, args...)
}

// Fatal logs fatal messages and exits
func (sl *SecureLogger) Fatal(format string, args ...interface{}) {
	log.Fatalf("[FATAL] "+format, args...)
}

// CheckSecretPresence checks if a secret environment variable is set without logging its value
func (sl *SecureLogger) CheckSecretPresence(secretName string) {
	if !sl.enableDebug {
		return
	}

	value := os.Getenv(secretName)
	status := "NOT_SET"
	if value != "" {
		length := len(value)
		status = "SET"
		if length < 32 {
			log.Printf("[WARN] %s is set but may be too short (length: %d, recommended: 32+)", secretName, length)
		} else {
			log.Printf("[DEBUG] %s: %s (length: %d chars)", secretName, status, length)
		}
	} else {
		log.Printf("[WARN] %s: %s - Using default/fallback", secretName, status)
	}
}

// LogStartup logs a startup message
func (sl *SecureLogger) LogStartup(port, features string) {
	log.Printf("🚀 Health Management System server started on port %s", port)
	log.Printf("📊 Available features: %s", features)
}

// LogFeature logs a feature message
func (sl *SecureLogger) LogFeature(icon, message string) {
	log.Printf("%s %s", icon, message)
}
