package utils

import (
	"errors"
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

// jwtSecret retrieves and validates the JWT secret from environment
func jwtSecret() ([]byte, error) {
	secret := os.Getenv("JWT_SECRET")
	if secret == "" {
		return nil, errors.New("JWT_SECRET environment variable is required")
	}

	// Validate secret length (minimum 32 characters for security)
	if len(secret) < 32 {
		return nil, fmt.Errorf("JWT_SECRET must be at least 32 characters long, current length: %d", len(secret))
	}

	return []byte(secret), nil
}

// GenerateJWT issues a JWT for a user ID with given ttl.
func GenerateJWT(userID string, ttl time.Duration) (string, error) {
	secret, err := jwtSecret()
	if err != nil {
		return "", fmt.Errorf("failed to get JWT secret: %w", err)
	}

	// Validate userID
	if userID == "" {
		return "", errors.New("user ID cannot be empty")
	}

	// Create claims with additional security fields
	claims := jwt.MapClaims{
		"sub": userID,
		"exp": time.Now().Add(ttl).Unix(),
		"iat": time.Now().Unix(),
		"iss": "doctorhealthy-api",                                 // Issuer
		"aud": "doctorhealthy-client",                              // Audience
		"jti": fmt.Sprintf("%d-%s", time.Now().UnixNano(), userID), // JWT ID for uniqueness
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	signedToken, err := token.SignedString(secret)
	if err != nil {
		return "", fmt.Errorf("failed to sign JWT: %w", err)
	}

	return signedToken, nil
}

// ParseJWT validates the token and returns user ID.
func ParseJWT(tokenStr string) (string, error) {
	secret, err := jwtSecret()
	if err != nil {
		return "", fmt.Errorf("failed to get JWT secret: %w", err)
	}

	// Validate token format
	if tokenStr == "" {
		return "", errors.New("token string is empty")
	}

	token, err := jwt.Parse(tokenStr, func(t *jwt.Token) (interface{}, error) {
		// Validate signing method
		if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", t.Header["alg"])
		}
		return secret, nil
	})

	if err != nil {
		log.Printf("JWT parsing error: %v", err)
		return "", fmt.Errorf("invalid token: %w", err)
	}

	if !token.Valid {
		return "", errors.New("token is invalid")
	}

	// Extract claims with validation
	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		return "", errors.New("invalid token claims")
	}

	// Validate required claims
	sub, ok := claims["sub"].(string)
	if !ok || sub == "" {
		return "", errors.New("missing or invalid subject claim")
	}

	// Validate issuer
	iss, issOk := claims["iss"].(string)
	if !issOk || iss != "doctorhealthy-api" {
		return "", errors.New("invalid issuer claim")
	}

	// Validate audience
	aud, audOk := claims["aud"].(string)
	if !audOk || aud != "doctorhealthy-client" {
		return "", errors.New("invalid audience claim")
	}

	return sub, nil
}

// ValidateJWTFormat checks if a token string has the correct JWT format
func ValidateJWTFormat(tokenStr string) error {
	if tokenStr == "" {
		return errors.New("token is empty")
	}

	parts := strings.Split(tokenStr, ".")
	if len(parts) != 3 {
		return errors.New("invalid JWT format: expected 3 parts separated by dots")
	}

	return nil
}
