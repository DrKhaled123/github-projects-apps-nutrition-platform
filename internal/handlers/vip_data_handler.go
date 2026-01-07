package handlers

import (
	"net/http"
	"strconv"

	"api-key-generator/internal/services"

	"github.com/labstack/echo/v4"
)

// VIPDataHandler handles VIP data integration endpoints
type VIPDataHandler struct {
	vipService *services.VIPIntegrationService
}

// NewVIPDataHandler creates a new VIP data handler
func NewVIPDataHandler(vipService *services.VIPIntegrationService) *VIPDataHandler {
	return &VIPDataHandler{
		vipService: vipService,
	}
}

// GetVIPDataSummary returns a comprehensive summary of all integrated VIP data
func (h *VIPDataHandler) GetVIPDataSummary(c echo.Context) error {
	summary, err := h.vipService.GetVIPDataSummary()
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Failed to get VIP data summary")
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"message": "VIP data summary retrieved successfully",
		"summary": summary,
	})
}

// GetAllMedications returns all medications from VIP data
func (h *VIPDataHandler) GetAllMedications(c echo.Context) error {
	medications, err := h.vipService.GetAllMedications()
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Failed to get medications")
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"message":     "Medications retrieved successfully",
		"medications": medications,
		"count":       len(medications),
	})
}

// GetMedicationsByCategory returns medications filtered by category
func (h *VIPDataHandler) GetMedicationsByCategory(c echo.Context) error {
	category := c.Param("category")
	if category == "" {
		return echo.NewHTTPError(http.StatusBadRequest, "Category parameter is required")
	}

	medications, err := h.vipService.GetMedicationsByCategory(category)
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, err.Error())
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"message":     "Medications retrieved successfully",
		"category":    category,
		"medications": medications,
		"count":       len(medications),
	})
}

// GetAllComplaintCases returns all complaint cases from VIP data
func (h *VIPDataHandler) GetAllComplaintCases(c echo.Context) error {
	cases, err := h.vipService.GetAllComplaintCases()
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Failed to get complaint cases")
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"message": "Complaint cases retrieved successfully",
		"cases":   cases,
		"count":   len(cases),
	})
}

// GetComplaintCaseByID returns a specific complaint case by ID
func (h *VIPDataHandler) GetComplaintCaseByID(c echo.Context) error {
	idStr := c.Param("id")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "Invalid case ID")
	}

	case_, err := h.vipService.GetComplaintCaseByID(id)
	if err != nil {
		return echo.NewHTTPError(http.StatusNotFound, err.Error())
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"message": "Complaint case retrieved successfully",
		"case":    case_,
	})
}

// GetAllVitaminsAndMinerals returns all vitamins and minerals from VIP data
func (h *VIPDataHandler) GetAllVitaminsAndMinerals(c echo.Context) error {
	nutrients, err := h.vipService.GetAllVitaminsAndMinerals()
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Failed to get vitamins and minerals")
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"message":           "Vitamins and minerals retrieved successfully",
		"vitamins_minerals": nutrients,
		"count":             len(nutrients),
	})
}

// GetDiseaseInformation returns comprehensive disease information
func (h *VIPDataHandler) GetDiseaseInformation(c echo.Context) error {
	diseaseID := c.Param("disease_id")
	if diseaseID == "" {
		return echo.NewHTTPError(http.StatusBadRequest, "Disease ID parameter is required")
	}

	disease, err := h.vipService.GetDiseaseInformation(diseaseID)
	if err != nil {
		return echo.NewHTTPError(http.StatusNotFound, err.Error())
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"message":    "Disease information retrieved successfully",
		"disease_id": diseaseID,
		"disease":    disease,
	})
}

// GetHalalHaramInformation returns halal/haram food information
func (h *VIPDataHandler) GetHalalHaramInformation(c echo.Context) error {
	info, err := h.vipService.GetHalalHaramInformation()
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Failed to get halal/haram information")
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"message":           "Halal/Haram information retrieved successfully",
		"halal_haram_foods": info,
	})
}

// GetWorkoutTechniques returns all workout techniques from VIP data
func (h *VIPDataHandler) GetWorkoutTechniques(c echo.Context) error {
	techniques, err := h.vipService.GetWorkoutTechniques()
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Failed to get workout techniques")
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"message":            "Workout techniques retrieved successfully",
		"workout_techniques": techniques,
		"count":              len(techniques),
	})
}

// GetSportsNutrition returns sports nutrition information
func (h *VIPDataHandler) GetSportsNutrition(c echo.Context) error {
	nutrition, err := h.vipService.GetSportsNutrition()
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Failed to get sports nutrition")
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"message":          "Sports nutrition retrieved successfully",
		"sports_nutrition": nutrition,
	})
}

// GetInjuryManagement returns injury management protocols
func (h *VIPDataHandler) GetInjuryManagement(c echo.Context) error {
	management, err := h.vipService.GetInjuryManagement()
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Failed to get injury management")
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"message":           "Injury management retrieved successfully",
		"injury_management": management,
	})
}

// GetDietPlans returns all diet plans from VIP data
func (h *VIPDataHandler) GetDietPlans(c echo.Context) error {
	plans, err := h.vipService.GetDietPlans()
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Failed to get diet plans")
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"message":    "Diet plans retrieved successfully",
		"diet_plans": plans,
	})
}

// GetNutritionGuidelines returns nutrition guidelines
func (h *VIPDataHandler) GetNutritionGuidelines(c echo.Context) error {
	guidelines, err := h.vipService.GetNutritionGuidelines()
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Failed to get nutrition guidelines")
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"message":              "Nutrition guidelines retrieved successfully",
		"nutrition_guidelines": guidelines,
	})
}

// GetDataIntegrityReport returns a detailed report of data integrity
func (h *VIPDataHandler) GetDataIntegrityReport(c echo.Context) error {
	report, err := h.vipService.GetDataIntegrityReport()
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Failed to generate integrity report")
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"message": "Data integrity report generated successfully",
		"report":  report,
	})
}

// ValidateDataIntegrity performs comprehensive validation of all VIP data
func (h *VIPDataHandler) ValidateDataIntegrity(c echo.Context) error {
	err := h.vipService.ValidateDataIntegrity()
	if err != nil {
		return c.JSON(http.StatusOK, map[string]interface{}{
			"message":           "Data validation completed with issues",
			"validation_status": "FAILED",
			"error":             err.Error(),
		})
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"message":           "Data validation completed successfully",
		"validation_status": "PASSED",
		"result":            "All VIP data successfully integrated and validated",
	})
}

// GetAvailableMedicationCategories returns available medication categories
func (h *VIPDataHandler) GetAvailableMedicationCategories(c echo.Context) error {
	categories := []map[string]string{
		{"id": "weight_loss", "name": "Weight Loss Drugs", "description": "Medications for weight management"},
		{"id": "diabetes", "name": "Diabetes Medications", "description": "Medications for diabetes management"},
		{"id": "appetite_suppressants", "name": "Appetite Suppressants", "description": "Medications that suppress appetite"},
		{"id": "investigational", "name": "Investigational Drugs", "description": "Experimental medications under research"},
		{"id": "hormonal", "name": "Hormonal Medications", "description": "Hormone-related medications"},
		{"id": "performance", "name": "Performance Enhancers", "description": "Performance enhancement medications"},
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"message":    "Medication categories retrieved successfully",
		"categories": categories,
		"count":      len(categories),
	})
}

// GetAvailableDiseases returns available diseases in the database
func (h *VIPDataHandler) GetAvailableDiseases(c echo.Context) error {
	diseases := []map[string]string{
		// Cardiovascular Diseases
		{"id": "hypertension", "name": "Essential Hypertension", "category": "cardiovascular"},
		{"id": "coronary_artery_disease", "name": "Coronary Artery Disease", "category": "cardiovascular"},
		{"id": "heart_failure", "name": "Congestive Heart Failure", "category": "cardiovascular"},
		{"id": "atrial_fibrillation", "name": "Atrial Fibrillation", "category": "cardiovascular"},
		{"id": "stroke", "name": "Cerebrovascular Accident", "category": "cardiovascular"},

		// Endocrine Diseases
		{"id": "type_1_diabetes", "name": "Type 1 Diabetes Mellitus", "category": "endocrine"},
		{"id": "type_2_diabetes", "name": "Type 2 Diabetes Mellitus", "category": "endocrine"},
		{"id": "hypothyroidism", "name": "Primary Hypothyroidism", "category": "endocrine"},
		{"id": "hyperthyroidism", "name": "Hyperthyroidism", "category": "endocrine"},
		{"id": "cushings_syndrome", "name": "Cushing's Syndrome", "category": "endocrine"},
		{"id": "addisons_disease", "name": "Addison's Disease", "category": "endocrine"},

		// Respiratory Diseases
		{"id": "asthma", "name": "Bronchial Asthma", "category": "respiratory"},
		{"id": "copd", "name": "Chronic Obstructive Pulmonary Disease", "category": "respiratory"},
		{"id": "pneumonia", "name": "Community-Acquired Pneumonia", "category": "respiratory"},

		// Gastrointestinal Diseases
		{"id": "gastroesophageal_reflux", "name": "Gastroesophageal Reflux Disease", "category": "gastrointestinal"},
		{"id": "peptic_ulcer", "name": "Peptic Ulcer Disease", "category": "gastrointestinal"},
		{"id": "inflammatory_bowel_disease", "name": "Inflammatory Bowel Disease", "category": "gastrointestinal"},
		{"id": "irritable_bowel_syndrome", "name": "Irritable Bowel Syndrome", "category": "gastrointestinal"},

		// Neurological Diseases
		{"id": "alzheimers_disease", "name": "Alzheimer's Disease", "category": "neurological"},
		{"id": "parkinsons_disease", "name": "Parkinson's Disease", "category": "neurological"},
		{"id": "multiple_sclerosis", "name": "Multiple Sclerosis", "category": "neurological"},
		{"id": "epilepsy", "name": "Epilepsy", "category": "neurological"},
		{"id": "migraine", "name": "Migraine Headache", "category": "neurological"},

		// Musculoskeletal Diseases
		{"id": "osteoarthritis", "name": "Osteoarthritis", "category": "musculoskeletal"},
		{"id": "rheumatoid_arthritis", "name": "Rheumatoid Arthritis", "category": "musculoskeletal"},
		{"id": "osteoporosis", "name": "Osteoporosis", "category": "musculoskeletal"},
		{"id": "fibromyalgia", "name": "Fibromyalgia", "category": "musculoskeletal"},

		// Mental Health Disorders
		{"id": "major_depression", "name": "Major Depressive Disorder", "category": "mental_health"},
		{"id": "anxiety_disorders", "name": "Generalized Anxiety Disorder", "category": "mental_health"},
		{"id": "bipolar_disorder", "name": "Bipolar Disorder", "category": "mental_health"},
		{"id": "schizophrenia", "name": "Schizophrenia", "category": "mental_health"},

		// Infectious Diseases
		{"id": "tuberculosis", "name": "Tuberculosis", "category": "infectious"},
		{"id": "hepatitis_b", "name": "Hepatitis B", "category": "infectious"},
		{"id": "hiv_aids", "name": "HIV/AIDS", "category": "infectious"},
		{"id": "malaria", "name": "Malaria", "category": "infectious"},

		// Renal Diseases
		{"id": "chronic_kidney_disease", "name": "Chronic Kidney Disease", "category": "renal"},
		{"id": "acute_kidney_injury", "name": "Acute Kidney Injury", "category": "renal"},
		{"id": "nephrotic_syndrome", "name": "Nephrotic Syndrome", "category": "renal"},

		// Hematological Diseases
		{"id": "iron_deficiency_anemia", "name": "Iron Deficiency Anemia", "category": "hematological"},
		{"id": "sickle_cell_disease", "name": "Sickle Cell Disease", "category": "hematological"},
		{"id": "leukemia", "name": "Leukemia", "category": "hematological"},

		// Dermatological Diseases
		{"id": "psoriasis", "name": "Psoriasis", "category": "dermatological"},
		{"id": "eczema", "name": "Atopic Dermatitis", "category": "dermatological"},
		{"id": "acne", "name": "Acne Vulgaris", "category": "dermatological"},

		// Ophthalmological Diseases
		{"id": "glaucoma", "name": "Primary Open-Angle Glaucoma", "category": "ophthalmological"},
		{"id": "cataracts", "name": "Cataracts", "category": "ophthalmological"},
		{"id": "macular_degeneration", "name": "Age-Related Macular Degeneration", "category": "ophthalmological"},
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"message":  "Available diseases retrieved successfully",
		"diseases": diseases,
		"count":    len(diseases),
	})
}
