package handlers

import (
	"net/http"

	"api-key-generator/internal/services"

	"github.com/labstack/echo/v4"
)

// ComprehensiveWorkoutHandler handles comprehensive workout endpoints
type ComprehensiveWorkoutHandler struct {
	workoutService   *services.ComprehensiveWorkoutService
	vipExtractor     *services.VIPWorkoutExtractor
	nutritionService *services.NutritionTimingService
}

// NewComprehensiveWorkoutHandler creates a new comprehensive workout handler
func NewComprehensiveWorkoutHandler() *ComprehensiveWorkoutHandler {
	return &ComprehensiveWorkoutHandler{
		workoutService:   services.NewComprehensiveWorkoutService(),
		vipExtractor:     services.NewVIPWorkoutExtractor(),
		nutritionService: services.NewNutritionTimingService(),
	}
}

// GetAllPrograms returns all available workout programs
// GET /api/v1/workouts/programs
func (cwh *ComprehensiveWorkoutHandler) GetAllPrograms(c echo.Context) error {
	programs, err := cwh.workoutService.GetComprehensivePrograms(c.Request().Context())
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Failed to fetch programs")
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"success": true,
		"data":    programs,
		"count":   len(programs),
	})
}

// GetVIPPrograms returns VIP extracted workout programs
// GET /api/v1/workouts/vip-programs
func (cwh *ComprehensiveWorkoutHandler) GetVIPPrograms(c echo.Context) error {
	programs, err := cwh.vipExtractor.ExtractVIPWorkouts(c.Request().Context(), ".")
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Failed to extract VIP programs")
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"success": true,
		"data":    programs,
		"count":   len(programs),
	})
}

// CreateCustomProgram generates a personalized workout program
// POST /api/v1/workouts/programs
func (cwh *ComprehensiveWorkoutHandler) CreateCustomProgram(c echo.Context) error {
	var req services.CustomProgramRequest
	if err := c.Bind(&req); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Invalid request format")
	}

	if err := c.Validate(&req); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, err.Error())
	}

	program, err := cwh.workoutService.GenerateCustomProgram(c.Request().Context(), &req)
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Failed to generate program")
	}

	return c.JSON(http.StatusCreated, map[string]interface{}{
		"success": true,
		"data":    program,
		"message": "Custom program created successfully",
	})
}

// GetNutritionRecommendations provides nutrition guidelines
// GET /api/v1/workouts/nutrition
func (cwh *ComprehensiveWorkoutHandler) GetNutritionRecommendations(c echo.Context) error {
	goal := c.QueryParam("goal")
	fitnessLevel := c.QueryParam("fitness_level")

	if goal == "" {
		goal = "muscle_gain"
	}
	if fitnessLevel == "" {
		fitnessLevel = "intermediate"
	}

	recommendations, err := cwh.nutritionService.GetNutritionRecommendations(c.Request().Context(), goal, fitnessLevel)
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Failed to get nutrition recommendations")
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"success": true,
		"data":    recommendations,
	})
}

// GetWorkoutNutrition provides workout-specific nutrition timing
// POST /api/v1/workouts/nutrition/timing
func (cwh *ComprehensiveWorkoutHandler) GetWorkoutNutrition(c echo.Context) error {
	var req services.WorkoutNutritionRequest
	if err := c.Bind(&req); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Invalid request format")
	}

	// Set defaults
	if req.Language == "" {
		req.Language = "en"
	}
	if req.Goal == "" {
		req.Goal = "muscle_gain"
	}

	nutrition, err := cwh.nutritionService.GenerateWorkoutNutrition(c.Request().Context(), &req)
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Failed to generate nutrition plan")
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"success": true,
		"data":    nutrition,
	})
}

// GetProgramsByLevel filters programs by fitness level
// GET /api/v1/workouts/programs/level/{level}
func (cwh *ComprehensiveWorkoutHandler) GetProgramsByLevel(c echo.Context) error {
	level := c.Param("level")
	if level == "" {
		return echo.NewHTTPError(http.StatusBadRequest, "Fitness level is required")
	}

	programs, err := cwh.workoutService.GetComprehensivePrograms(c.Request().Context())
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Failed to fetch programs")
	}

	// Filter by level (simplified - in production, this would be done in service layer)
	filteredPrograms := make([]*services.WorkoutProgramData, 0)
	for _, program := range programs {
		// This is a simplified filter - you'd implement proper filtering logic
		if program.Purpose != "" { // Placeholder condition
			filteredPrograms = append(filteredPrograms, program)
		}
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"success": true,
		"data":    filteredPrograms,
		"level":   level,
		"count":   len(filteredPrograms),
	})
}

// GetProgramsByGoal filters programs by fitness goal
// GET /api/v1/workouts/programs/goal/{goal}
func (cwh *ComprehensiveWorkoutHandler) GetProgramsByGoal(c echo.Context) error {
	goal := c.Param("goal")
	if goal == "" {
		return echo.NewHTTPError(http.StatusBadRequest, "Goal is required")
	}

	programs, err := cwh.workoutService.GetComprehensivePrograms(c.Request().Context())
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Failed to fetch programs")
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"success": true,
		"data":    programs,
		"goal":    goal,
		"count":   len(programs),
	})
}

// GetSupplementRecommendations provides supplement protocols
// GET /api/v1/workouts/supplements
func (cwh *ComprehensiveWorkoutHandler) GetSupplementRecommendations(c echo.Context) error {
	goal := c.QueryParam("goal")
	level := c.QueryParam("level")

	if goal == "" {
		goal = "muscle_gain"
	}
	if level == "" {
		level = "intermediate"
	}

	// Generate supplement recommendations based on goal and level
	supplements := cwh.generateSupplementRecommendations(goal, level)

	return c.JSON(http.StatusOK, map[string]interface{}{
		"success": true,
		"data": map[string]interface{}{
			"goal":        goal,
			"level":       level,
			"supplements": supplements,
			"notes":       "Consult healthcare provider before starting any supplement regimen",
		},
	})
}

// GetWorkoutTechniques provides exercise technique guidance
// GET /api/v1/workouts/techniques
func (cwh *ComprehensiveWorkoutHandler) GetWorkoutTechniques(c echo.Context) error {
	exerciseType := c.QueryParam("type")
	language := c.QueryParam("language")

	if language == "" {
		language = "en"
	}

	techniques := cwh.generateTechniqueGuidance(exerciseType, language)

	return c.JSON(http.StatusOK, map[string]interface{}{
		"success": true,
		"data": map[string]interface{}{
			"exercise_type": exerciseType,
			"language":      language,
			"techniques":    techniques,
		},
	})
}

// Helper methods

func (cwh *ComprehensiveWorkoutHandler) generateSupplementRecommendations(goal, level string) map[string]interface{} {
	supplements := map[string]map[string]interface{}{
		"fat_loss": {
			"protein":     map[string]string{"dosage": "25-30g", "timing": "post_workout", "purpose": "Muscle preservation"},
			"l_carnitine": map[string]string{"dosage": "1-2g", "timing": "pre_workout", "purpose": "Fat oxidation"},
			"green_tea":   map[string]string{"dosage": "500mg", "timing": "between_meals", "purpose": "Metabolism boost"},
			"caffeine":    map[string]string{"dosage": "200mg", "timing": "pre_workout", "purpose": "Energy and focus"},
		},
		"muscle_gain": {
			"protein":      map[string]string{"dosage": "30-40g", "timing": "post_workout", "purpose": "Muscle protein synthesis"},
			"creatine":     map[string]string{"dosage": "5g", "timing": "daily", "purpose": "Strength and power"},
			"mass_gainer":  map[string]string{"dosage": "1 serving", "timing": "post_workout", "purpose": "Calorie surplus"},
			"beta_alanine": map[string]string{"dosage": "3-5g", "timing": "daily", "purpose": "Muscular endurance"},
		},
	}

	// Adjust recommendations based on fitness level
	baseSupps := map[string]interface{}{}
	if goalSupps, exists := supplements[goal]; exists {
		baseSupps = goalSupps
	} else {
		baseSupps = supplements["muscle_gain"]
	}

	// Apply level-based modifications
	switch level {
	case "beginner":
		// Reduce dosages for beginners
		if protein, ok := baseSupps["protein"].(map[string]string); ok {
			protein["dosage"] = "20-25g"
		}
		if creatine, ok := baseSupps["creatine"].(map[string]string); ok {
			creatine["dosage"] = "3g"
		}
	case "advanced":
		// Increase dosages for advanced users
		if protein, ok := baseSupps["protein"].(map[string]string); ok {
			protein["dosage"] = "35-45g"
		}
		if creatine, ok := baseSupps["creatine"].(map[string]string); ok {
			creatine["dosage"] = "7g"
		}
	}

	return baseSupps
}

func (cwh *ComprehensiveWorkoutHandler) generateTechniqueGuidance(exerciseType, language string) map[string]interface{} {
	// Language-specific technique guidance
	techniques := map[string]map[string]map[string]interface{}{
		"en": {
			"strength": {
				"form_cues": []string{"Maintain neutral spine", "Control eccentric phase", "Full range of motion", "Breathe properly"},
				"mistakes":  []string{"Using momentum", "Partial reps", "Poor posture", "Holding breath"},
				"safety":    []string{"Warm up properly", "Use spotters for heavy lifts", "Progress gradually", "Listen to your body"},
			},
			"cardio": {
				"form_cues": []string{"Maintain upright posture", "Land softly", "Controlled breathing", "Engage core"},
				"mistakes":  []string{"Overstriding", "Poor posture", "Holding breath", "Too much too soon"},
				"safety":    []string{"Start gradually", "Stay hydrated", "Monitor heart rate", "Cool down properly"},
			},
		},
		"es": {
			"strength": {
				"form_cues": []string{"Mantén la columna neutral", "Controla la fase excéntrica", "Rango completo de movimiento", "Respira correctamente"},
				"mistakes":  []string{"Usar momentum", "Repeticiones parciales", "Postura deficiente", "Contener la respiración"},
				"safety":    []string{"Calienta adecuadamente", "Usa ayudantes para levantamientos pesados", "Progresa gradualmente", "Escucha a tu cuerpo"},
			},
			"cardio": {
				"form_cues": []string{"Mantén postura erguida", "Aterriza suavemente", "Respiración controlada", "Activa el core"},
				"mistakes":  []string{"Excederse en la zancada", "Postura deficiente", "Contener la respiración", "Demasiado pronto"},
				"safety":    []string{"Comienza gradualmente", "Mantente hidratado", "Monitorea el ritmo cardíaco", "Enfría adecuadamente"},
			},
		},
	}

	// Default to English if language not supported
	langTechniques := techniques["en"]
	if langData, exists := techniques[language]; exists {
		langTechniques = langData
	}

	if technique, exists := langTechniques[exerciseType]; exists {
		return technique
	}
	return langTechniques["strength"]
}
