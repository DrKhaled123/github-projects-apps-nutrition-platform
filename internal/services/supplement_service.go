package services

import (
	"context"
	"database/sql"
	"fmt"
	"time"

	"api-key-generator/internal/models"
	"api-key-generator/internal/utils"

	"github.com/google/uuid"
)

// SupplementService handles supplement protocol generation and management
type SupplementService struct {
	db          *sql.DB
	userService *UserService
}

// NewSupplementService creates a new supplement service
func NewSupplementService(db *sql.DB, userService *UserService) *SupplementService {
	return &SupplementService{
		db:          db,
		userService: userService,
	}
}

// GenerateSupplementProtocol generates personalized supplement recommendations
func (s *SupplementService) GenerateSupplementProtocol(ctx context.Context, req *models.SupplementRequest) (*models.SupplementProtocol, error) {
	// Get user data for personalization
	user, err := s.userService.GetUser(ctx, req.UserID)
	if err != nil {
		return nil, fmt.Errorf("failed to get user: %w", err)
	}

	// Calculate dosages based on user weight
	weightKg := user.Weight

	protocol := &models.SupplementProtocol{
		ID:        uuid.New().String(),
		UserID:    req.UserID,
		Name:      fmt.Sprintf("Personalized Protocol - %s", req.WorkoutGoal),
		Category:  req.WorkoutGoal,
		Purpose:   s.getPurposeDescription(req.WorkoutGoal),
		CreatedAt: time.Now().UTC(),
		UpdatedAt: time.Now().UTC(),
	}

	// Generate pre-workout supplements
	protocol.PreWorkout = s.generatePreWorkoutSupplements(req, weightKg)

	// Generate during-workout supplements
	protocol.DuringWorkout = s.generateDuringWorkoutSupplements(req, weightKg)

	// Generate post-workout supplements
	protocol.PostWorkout = s.generatePostWorkoutSupplements(req, weightKg)

	// Generate daily supplements
	protocol.Daily = s.generateDailySupplements(req, weightKg)

	// Add safety information
	protocol.SafetyNotes = s.generateSafetyNotes(req)
	protocol.Contraindications = s.generateContraindications(req)
	protocol.Interactions = s.checkDrugInteractions(req.ExistingMeds)

	// Save protocol
	if err := s.saveProtocol(ctx, protocol); err != nil {
		return nil, fmt.Errorf("failed to save protocol: %w", err)
	}

	return protocol, nil
}

// generatePreWorkoutSupplements creates pre-workout supplement recommendations
func (s *SupplementService) generatePreWorkoutSupplements(req *models.SupplementRequest, weightKg float64) []models.SupplementTiming {
	supplements := []models.SupplementTiming{}

	// Caffeine for energy
	if req.Intensity != "low" {
		caffeineDose := s.calculateCaffeineDose(weightKg)
		supplements = append(supplements, models.SupplementTiming{
			SupplementName: "Caffeine",
			Dosage:         fmt.Sprintf("%.0f", caffeineDose),
			Unit:           "mg",
			TimingMinutes:  -30,
			Instructions:   "Take 30 minutes before workout",
			Benefits:       []string{"Increased energy", "Enhanced focus", "Improved performance"},
			SideEffects:    []string{"Jitters", "Insomnia if taken late"},
			MaxDailyDose:   "400mg",
		})
	}

	// Creatine for power
	if req.WorkoutGoal == "build_muscle" || req.WorkoutGoal == "increase_strength" {
		supplements = append(supplements, models.SupplementTiming{
			SupplementName: "Creatine Monohydrate",
			Dosage:         "5",
			Unit:           "g",
			TimingMinutes:  -15,
			Instructions:   "Take 15 minutes before workout with water",
			Benefits:       []string{"Increased power output", "Enhanced muscle building"},
			MaxDailyDose:   "10g",
		})
	}

	return supplements
}

// generateDuringWorkoutSupplements creates during-workout supplement recommendations
func (s *SupplementService) generateDuringWorkoutSupplements(req *models.SupplementRequest, weightKg float64) []models.SupplementTiming {
	supplements := []models.SupplementTiming{}

	// Electrolytes for longer workouts
	if req.Duration > 60 {
		supplements = append(supplements, models.SupplementTiming{
			SupplementName: "Electrolyte Mix",
			Dosage:         "1",
			Unit:           "scoop",
			TimingMinutes:  0,
			Instructions:   "Mix with 500ml water, sip throughout workout",
			Benefits:       []string{"Maintains hydration", "Prevents cramping"},
		})
	}

	return supplements
}

// generatePostWorkoutSupplements creates post-workout supplement recommendations
func (s *SupplementService) generatePostWorkoutSupplements(req *models.SupplementRequest, weightKg float64) []models.SupplementTiming {
	supplements := []models.SupplementTiming{}

	// Protein for recovery
	proteinDose := s.calculateProteinDose(weightKg, req.WorkoutGoal)
	supplements = append(supplements, models.SupplementTiming{
		SupplementName: "Whey Protein",
		Dosage:         fmt.Sprintf("%.0f", proteinDose),
		Unit:           "g",
		TimingMinutes:  30,
		Instructions:   "Take within 30 minutes post-workout",
		Benefits:       []string{"Muscle recovery", "Protein synthesis"},
	})

	return supplements
}

// generateDailySupplements creates daily supplement recommendations
func (s *SupplementService) generateDailySupplements(req *models.SupplementRequest, weightKg float64) []models.SupplementTiming {
	supplements := []models.SupplementTiming{
		{
			SupplementName: "Multivitamin",
			Dosage:         "1",
			Unit:           "tablet",
			TimingMinutes:  0,
			Instructions:   "Take with breakfast",
			Benefits:       []string{"Overall health", "Nutrient insurance"},
		},
		{
			SupplementName: "Omega-3",
			Dosage:         "1000",
			Unit:           "mg",
			TimingMinutes:  0,
			Instructions:   "Take with meals",
			Benefits:       []string{"Heart health", "Anti-inflammatory"},
		},
	}

	return supplements
}

// Helper methods for dosage calculations
func (s *SupplementService) calculateCaffeineDose(weightKg float64) float64 {
	// 3-6mg per kg body weight
	dose := weightKg * 4
	if dose > 400 {
		dose = 400 // Max safe dose
	}
	if dose < 100 {
		dose = 100 // Min effective dose
	}
	return dose
}

func (s *SupplementService) calculateProteinDose(weightKg float64, goal string) float64 {
	// 20-40g based on goal
	if goal == "build_muscle" {
		return 30
	}
	return 25
}

// Safety and interaction methods
func (s *SupplementService) generateSafetyNotes(req *models.SupplementRequest) []string {
	notes := []string{
		"Consult healthcare provider before starting any supplement regimen",
		"Start with lower doses to assess tolerance",
		"Stay hydrated when using supplements",
	}

	if len(req.ExistingMeds) > 0 {
		notes = append(notes, "Check for drug interactions with existing medications")
	}

	return notes
}

func (s *SupplementService) generateContraindications(req *models.SupplementRequest) []string {
	contraindications := []string{}

	for _, condition := range req.HealthConditions {
		switch condition {
		case "hypertension":
			contraindications = append(contraindications, "Avoid high-dose caffeine with hypertension")
		case "kidney_disease":
			contraindications = append(contraindications, "Limit creatine with kidney disease")
		}
	}

	return contraindications
}

func (s *SupplementService) checkDrugInteractions(medications []string) []models.DrugInteraction {
	interactions := []models.DrugInteraction{}

	for _, med := range medications {
		switch med {
		case "warfarin":
			interactions = append(interactions, models.DrugInteraction{
				DrugName:    "Warfarin",
				Interaction: "Omega-3 may increase bleeding risk",
				Severity:    "moderate",
				Management:  "Monitor INR closely",
			})
		}
	}

	return interactions
}

func (s *SupplementService) getPurposeDescription(goal string) string {
	switch goal {
	case "build_muscle":
		return "Optimize muscle building and recovery"
	case "lose_weight":
		return "Support fat loss and energy"
	case "increase_strength":
		return "Enhance power and strength gains"
	default:
		return "General fitness support"
	}
}

// saveProtocol saves the supplement protocol to database
func (s *SupplementService) saveProtocol(ctx context.Context, protocol *models.SupplementProtocol) error {
	query := `
		INSERT INTO supplement_protocols (
			id, user_id, workout_program_id, name, category, purpose, 
			safety_notes, contraindications, created_at, updated_at
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`

	safetyNotesJSON := utils.StringSliceToJSON(protocol.SafetyNotes)
	contraindicationsJSON := utils.StringSliceToJSON(protocol.Contraindications)

	_, err := s.db.ExecContext(ctx, query,
		protocol.ID,
		protocol.UserID,
		protocol.WorkoutProgramID,
		protocol.Name,
		protocol.Category,
		protocol.Purpose,
		safetyNotesJSON,
		contraindicationsJSON,
		protocol.CreatedAt,
		protocol.UpdatedAt,
	)

	return err
}

// GetSupplementProtocol retrieves a supplement protocol by ID
func (s *SupplementService) GetSupplementProtocol(ctx context.Context, id string) (*models.SupplementProtocol, error) {
	query := `
		SELECT id, user_id, workout_program_id, name, category, purpose,
			   safety_notes, contraindications, created_at, updated_at
		FROM supplement_protocols WHERE id = ?
	`

	var protocol models.SupplementProtocol
	var safetyNotesJSON, contraindicationsJSON string

	err := s.db.QueryRowContext(ctx, query, id).Scan(
		&protocol.ID,
		&protocol.UserID,
		&protocol.WorkoutProgramID,
		&protocol.Name,
		&protocol.Category,
		&protocol.Purpose,
		&safetyNotesJSON,
		&contraindicationsJSON,
		&protocol.CreatedAt,
		&protocol.UpdatedAt,
	)

	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("supplement protocol not found")
		}
		return nil, err
	}

	protocol.SafetyNotes = utils.JSONToStringSlice(safetyNotesJSON)
	protocol.Contraindications = utils.JSONToStringSlice(contraindicationsJSON)

	return &protocol, nil
}
