package handlers

import (
	"net/http"
	"strings"

	"api-key-generator/internal/services"
	"api-key-generator/internal/utils"

	"github.com/labstack/echo/v4"
)

// URLSlugHandler handles URL slug generation requests
type URLSlugHandler struct {
	apiKeyService *services.APIKeyService
}

// NewURLSlugHandler creates a new URL slug handler
func NewURLSlugHandler(apiKeyService *services.APIKeyService) *URLSlugHandler {
	return &URLSlugHandler{
		apiKeyService: apiKeyService,
	}
}

// GenerateEnterpriseTrialURL generates an enterprise trial URL slug
func (h *URLSlugHandler) GenerateEnterpriseTrialURL(c echo.Context) error {
	// Bind request
	var req struct {
		Domain   string `json:"domain" validate:"required"`
		Company  string `json:"company" validate:"required"`
		PlanType string `json:"plan_type"`
		APIKey   string `json:"api_key"`
	}

	if err := c.Bind(&req); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid request format")
	}

	// Validate request
	if err := c.Validate(&req); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, err.Error())
	}

	// Validate API key if provided
	if req.APIKey != "" {
		valid, err := h.apiKeyService.ValidateAPIKey(req.APIKey)
		if err != nil {
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to validate API key")
		}
		if !valid {
			return echo.NewHTTPError(http.StatusUnauthorized, "invalid API key")
		}
	}

	// Generate URL slug
	url, err := utils.GenerateEnterpriseTrialURLSlug(req.Domain, req.Company, req.PlanType)
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, err.Error())
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"url":          url,
		"domain":       req.Domain,
		"company":      req.Company,
		"plan_type":    req.PlanType,
		"slug":         extractSlugFromURL(url),
		"api_key_used": req.APIKey != "",
	})
}

// GenerateCustomTrialURL generates a custom trial URL with parameters
func (h *URLSlugHandler) GenerateCustomTrialURL(c echo.Context) error {
	// Bind request
	var req struct {
		Domain string            `json:"domain" validate:"required"`
		Params map[string]string `json:"params" validate:"required"`
		APIKey string            `json:"api_key"`
	}

	if err := c.Bind(&req); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid request format")
	}

	// Validate request
	if err := c.Validate(&req); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, err.Error())
	}

	// Validate API key if provided
	if req.APIKey != "" {
		valid, err := h.apiKeyService.ValidateAPIKey(req.APIKey)
		if err != nil {
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to validate API key")
		}
		if !valid {
			return echo.NewHTTPError(http.StatusUnauthorized, "invalid API key")
		}
	}

	// Generate URL
	url, err := utils.GenerateCustomTrialURL(req.Domain, req.Params)
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, err.Error())
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"url":          url,
		"domain":       req.Domain,
		"params":       req.Params,
		"api_key_used": req.APIKey != "",
	})
}

// extractSlugFromURL extracts the slug portion from a URL
func extractSlugFromURL(url string) string {
	// This is a simplified implementation
	// In a real application, you would use proper URL parsing
	parts := strings.Split(url, "/")
	if len(parts) > 0 {
		return parts[len(parts)-1]
	}
	return ""
}

// RegisterURLSlugRoutes registers URL slug generation routes
func RegisterURLSlugRoutes(e *echo.Group, apiKeyService *services.APIKeyService) {
	handler := NewURLSlugHandler(apiKeyService)

	// Enterprise trial URL generation
	e.POST("/url-slug/enterprise-trial", handler.GenerateEnterpriseTrialURL)

	// Custom trial URL generation
	e.POST("/url-slug/custom-trial", handler.GenerateCustomTrialURL)
}
