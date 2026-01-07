package handlers

import (
	"api-key-generator/internal/services"

	"github.com/labstack/echo/v4"
)

// RegisterComprehensiveWorkoutRoutes registers all comprehensive workout routes with API key authentication
func RegisterComprehensiveWorkoutRoutes(e *echo.Echo, handler *ComprehensiveWorkoutHandler, apiKeyService *services.APIKeyService) {
	// Create workout group with API key middleware
	workoutGroup := e.Group("/api/v1/workouts")
	workoutGroup.Use(func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			// API Key validation
			apiKey := c.Request().Header.Get("X-API-Key")
			if apiKey == "" {
				return echo.NewHTTPError(401, "API key required")
			}

			// Validate API key
			valid, err := apiKeyService.ValidateKey(c.Request().Context(), apiKey)
			if err != nil || !valid {
				return echo.NewHTTPError(401, "Invalid API key")
			}

			return next(c)
		}
	})

	// Core workout program endpoints
	workoutGroup.GET("/programs", handler.GetAllPrograms)
	workoutGroup.POST("/programs", handler.CreateCustomProgram)
	workoutGroup.GET("/programs/level/:level", handler.GetProgramsByLevel)
	workoutGroup.GET("/programs/goal/:goal", handler.GetProgramsByGoal)

	// VIP data integration endpoints
	workoutGroup.GET("/vip-programs", handler.GetVIPPrograms)

	// Nutrition endpoints
	workoutGroup.GET("/nutrition", handler.GetNutritionRecommendations)
	workoutGroup.POST("/nutrition/timing", handler.GetWorkoutNutrition)

	// Supplement endpoints
	workoutGroup.GET("/supplements", handler.GetSupplementRecommendations)

	// Technique guidance endpoints
	workoutGroup.GET("/techniques", handler.GetWorkoutTechniques)
}
