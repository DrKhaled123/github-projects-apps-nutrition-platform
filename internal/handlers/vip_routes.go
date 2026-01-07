package handlers

import (
	"api-key-generator/internal/services"

	"github.com/labstack/echo/v4"
)

// RegisterVIPDataRoutes registers all VIP data integration routes
func RegisterVIPDataRoutes(api *echo.Group, vipService *services.VIPIntegrationService) {
	vipHandler := NewVIPDataHandler(vipService)

	// VIP data group
	vip := api.Group("/vip")

	// Summary and validation endpoints
	vip.GET("/summary", vipHandler.GetVIPDataSummary)
	vip.GET("/validate", vipHandler.ValidateDataIntegrity)
	vip.GET("/integrity-report", vipHandler.GetDataIntegrityReport)

	// Medications endpoints
	medications := vip.Group("/medications")
	medications.GET("", vipHandler.GetAllMedications)
	medications.GET("/categories", vipHandler.GetAvailableMedicationCategories)
	medications.GET("/category/:category", vipHandler.GetMedicationsByCategory)

	// Complaint cases endpoints
	complaints := vip.Group("/complaints")
	complaints.GET("", vipHandler.GetAllComplaintCases)
	complaints.GET("/:id", vipHandler.GetComplaintCaseByID)

	// Vitamins and minerals endpoints
	nutrients := vip.Group("/nutrients")
	nutrients.GET("", vipHandler.GetAllVitaminsAndMinerals)

	// Diseases endpoints
	diseases := vip.Group("/diseases")
	diseases.GET("", vipHandler.GetAvailableDiseases)
	diseases.GET("/:disease_id", vipHandler.GetDiseaseInformation)

	// Specialized data endpoints
	vip.GET("/halal-haram", vipHandler.GetHalalHaramInformation)
	vip.GET("/workout-techniques", vipHandler.GetWorkoutTechniques)
	vip.GET("/sports-nutrition", vipHandler.GetSportsNutrition)
	vip.GET("/injury-management", vipHandler.GetInjuryManagement)
	vip.GET("/diet-plans", vipHandler.GetDietPlans)
	vip.GET("/nutrition-guidelines", vipHandler.GetNutritionGuidelines)
}
