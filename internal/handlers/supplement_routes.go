package handlers

import (
	"api-key-generator/internal/middleware"
	"api-key-generator/internal/services"

	"github.com/labstack/echo/v4"
)

// SetupSupplementRoutes configures supplement-related routes with security middleware
func SetupSupplementRoutes(e *echo.Echo, supplementService *services.SupplementService, apiKeyService *services.APIKeyService) {
	// Create supplement handler with security integration
	supplementHandler := NewSupplementHandler(supplementService, apiKeyService)

	// Supplement API group with comprehensive middleware stack
	api := e.Group("/api/v1")
	api.Use(middleware.RecipeSecurity())
	api.Use(middleware.RecipeLogging())
	api.Use(middleware.RecipeRateLimit(apiKeyService))
	api.Use(middleware.RecipeValidation())
	api.Use(middleware.RecipeMetrics())

	// Supplement protocol endpoints - all protected by middleware stack
	api.POST("/supplements/protocols", supplementHandler.GenerateSupplementProtocol)
	api.GET("/supplements/protocols/:id", supplementHandler.GetSupplementProtocol)
	api.GET("/supplements/categories", supplementHandler.GetSupplementCategories)
	api.GET("/supplements/safety/:name", supplementHandler.GetSupplementSafetyInfo)
}
