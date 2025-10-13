package services

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strings"
	"sync"
	"time"
)

// UltimateDataService handles all comprehensive health data
type UltimateDataService struct {
	data     map[string]interface{}
	mutex    sync.RWMutex
	lastLoad time.Time
	dataPath string
}

// UltimateHealthDatabase represents the complete integrated database structure
type UltimateHealthDatabase struct {
	Medications             map[string]interface{} `json:"medications"`
	VitaminsMinerals        map[string]interface{} `json:"vitamins_minerals"`
	ComprehensiveDiseases   map[string]interface{} `json:"comprehensive_diseases"`
	ComprehensiveComplaints map[string]interface{} `json:"comprehensive_complaints"`
	Injuries                []interface{}          `json:"injuries"`
	Diseases                []interface{}          `json:"diseases"`
	Complaints              []interface{}          `json:"complaints"`
	TypePlans               []interface{}          `json:"type_plans"`
	Workouts                map[string]interface{} `json:"workouts"`
	Recipes                 map[string]interface{} `json:"recipes"`
	Metadata                map[string]interface{} `json:"metadata"`
}

// NewUltimateDataService creates a new ultimate data service
func NewUltimateDataService() *UltimateDataService {
	return &UltimateDataService{
		dataPath: "vip-complaints.js", // Using VIP complaints database
	}
}

// Note: Fallback database loaders are currently unused but kept for potential future use
// If needed, they can be re-enabled by uncommenting the functions below

/*
// loadFallbackDatabases loads individual complete databases as fallback
func (s *UltimateDataService) loadFallbackDatabases() {
	log.Println("🔄 Loading fallback databases...")

	// Load complete health database
	if err := s.loadHealthDatabase(); err != nil {
		log.Printf("Warning: Failed to load health database: %v", err)
	}

	// Load complete diseases database
	if err := s.loadDiseasesDatabase(); err != nil {
		log.Printf("Warning: Failed to load diseases database: %v", err)
	}

	// Load vitamins/minerals database
	if err := s.loadVitaminsMineralsDatabase(); err != nil {
		log.Printf("Warning: Failed to load vitamins/minerals database: %v", err)
	}
}

// loadHealthDatabase loads the complete health database from VIP files
func (s *UltimateDataService) loadHealthDatabase() error {
	log.Printf("DEBUG: Attempting to read vip-drugs-nutrition.js")
	content, err := os.ReadFile("vip-drugs-nutrition.js")
	if err != nil {
		log.Printf("DEBUG: Failed to read file: %v", err)
		return err
	}
	log.Printf("DEBUG: File read successfully, size: %d bytes", len(content))

	jsonData, err := s.convertJSToJSON(string(content))
	if err != nil {
		log.Printf("DEBUG: convertJSToJSON failed: %v", err)
		return err
	}
	log.Printf("DEBUG: Converted JSON length: %d characters", len(jsonData))
	if len(jsonData) > 500 {
		log.Printf("DEBUG: First 500 chars of converted JSON: %s", jsonData[:500])
	} else {
		log.Printf("DEBUG: Converted JSON: %s", jsonData)
	}

	var healthData map[string]interface{}
	if err := json.Unmarshal([]byte(jsonData), &healthData); err != nil {
		log.Printf("DEBUG: JSON unmarshal failed: %v", err)
		if len(jsonData) > 500 {
			log.Printf("DEBUG: Last 500 chars of JSON: %s", jsonData[len(jsonData)-500:])
		} else {
			log.Printf("DEBUG: Full JSON content: %s", jsonData)
		}
		return err
	}
	log.Printf("DEBUG: Successfully unmarshaled health data with %d keys", len(healthData))

	s.data["medications"] = healthData["medications"]
	s.data["vitamins"] = healthData["vitamins"]
	s.data["minerals"] = healthData["minerals"]
	s.data["workout_exercises"] = healthData["workout_exercises"]
	s.data["diet_plans"] = healthData["diet_plans"]

	log.Println("✅ Complete health database loaded")
	return nil
}

// loadDiseasesDatabase loads the complete diseases database from VIP injuries
func (s *UltimateDataService) loadDiseasesDatabase() error {
	content, err := os.ReadFile("vip-injuries.js")
	if err != nil {
		return err
	}

	jsonData, err := s.convertJSToJSON(string(content))
	if err != nil {
		return err
	}

	var diseasesData map[string]interface{}
	if err := json.Unmarshal([]byte(jsonData), &diseasesData); err != nil {
		return err
	}

	s.data["diseases"] = diseasesData["diseases"]
	s.data["treatment_protocols"] = diseasesData["treatment_protocols"]
	s.data["emergency_protocols"] = diseasesData["emergency_protocols"]

	log.Println("✅ Complete diseases database loaded")
	return nil
}

// loadVitaminsMineralsDatabase loads the vitamins/minerals database from VIP drugs-nutrition
func (s *UltimateDataService) loadVitaminsMineralsDatabase() error {
	content, err := os.ReadFile("vip-drugs-nutrition.js")
	if err != nil {
		return err
	}

	jsonData, err := s.convertJSToJSON(string(content))
	if err != nil {
		return err
	}

	var vitaminsData map[string]interface{}
	if err := json.Unmarshal([]byte(jsonData), &vitaminsData); err != nil {
		return err
	}

	s.data["water_soluble_vitamins"] = vitaminsData["water_soluble_vitamins"]
	s.data["fat_soluble_vitamins"] = vitaminsData["fat_soluble_vitamins"]
	s.data["minerals"] = vitaminsData["minerals"]
	s.data["supplement_interactions"] = vitaminsData["supplement_interactions"]
	s.data["special_populations"] = vitaminsData["special_populations"]

	log.Println("✅ Complete vitamins/minerals database loaded")
	return nil
}
*/

// LoadData loads the ultimate comprehensive database
func (s *UltimateDataService) LoadData() error {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	// Read the JavaScript module file
	content, err := os.ReadFile(s.dataPath)
	if err != nil {
		return fmt.Errorf("failed to read ultimate database file: %w", err)
	}

	// Convert JavaScript module to JSON
	jsonData, err := s.convertJSToJSON(string(content))
	if err != nil {
		return fmt.Errorf("failed to convert JS to JSON: %w", err)
	}

	// Parse JSON
	var database UltimateHealthDatabase
	if err := json.Unmarshal([]byte(jsonData), &database); err != nil {
		return fmt.Errorf("failed to parse ultimate database JSON: %w", err)
	}

	// Store in service
	s.data["medications"] = database.Medications
	s.data["vitamins_minerals"] = database.VitaminsMinerals
	s.data["comprehensive_diseases"] = database.ComprehensiveDiseases
	s.data["comprehensive_complaints"] = database.ComprehensiveComplaints
	s.data["injuries"] = database.Injuries
	s.data["diseases"] = database.Diseases
	s.data["complaints"] = database.Complaints
	s.data["type_plans"] = database.TypePlans
	s.data["workouts"] = database.Workouts
	s.data["recipes"] = database.Recipes
	s.data["metadata"] = database.Metadata

	s.lastLoad = time.Now()
	log.Printf("✅ Ultimate comprehensive database loaded successfully")
	log.Printf("📊 Total data categories: %d", len(s.data))

	if metadata, ok := database.Metadata["total_items"].(map[string]interface{}); ok {
		totalItems := 0
		for category, count := range metadata {
			if countFloat, ok := count.(float64); ok {
				totalItems += int(countFloat)
				log.Printf("   %s: %.0f items", category, countFloat)
			}
		}
		log.Printf("🎯 Grand total items: %d", totalItems)
	}

	return nil
}

// convertJSToJSON converts JavaScript module export to JSON
func (s *UltimateDataService) convertJSToJSON(jsContent string) (string, error) {
	log.Printf("DEBUG: convertJSToJSON input length: %d", len(jsContent))
	if len(jsContent) > 200 {
		log.Printf("DEBUG: First 200 chars: %s", jsContent[:200])
	} else {
		log.Printf("DEBUG: Full input: %s", jsContent)
	}

	// Remove JavaScript module syntax and comments
	lines := strings.Split(jsContent, "\n")
	var jsonLines []string
	inObject := false

	log.Printf("DEBUG: Processing %d lines", len(lines))

	for i, line := range lines {
		trimmed := strings.TrimSpace(line)

		// Skip comments and require statements
		if strings.HasPrefix(trimmed, "//") ||
			strings.HasPrefix(trimmed, "const") ||
			strings.HasPrefix(trimmed, "module.exports") ||
			strings.Contains(trimmed, "require(") {
			continue
		}

		// Start of object
		if strings.Contains(trimmed, "= {") {
			log.Printf("DEBUG: Found object start at line %d: %s", i, trimmed)
			inObject = true
			jsonLines = append(jsonLines, "{")
			continue
		}

		// End of object
		if trimmed == "};" && inObject {
			log.Printf("DEBUG: Found object end at line %d", i)
			jsonLines = append(jsonLines, "}")
			break
		}

		if inObject && trimmed != "" {
			jsonLines = append(jsonLines, line)
		}
	}

	result := strings.Join(jsonLines, "\n")
	log.Printf("DEBUG: Final result length: %d", len(result))
	return result, nil
}

// GetAllData returns all data (requires authentication)
func (s *UltimateDataService) GetAllData() map[string]interface{} {
	s.mutex.RLock()
	defer s.mutex.RUnlock()

	result := make(map[string]interface{})
	for k, v := range s.data {
		result[k] = v
	}
	return result
}

// GetMedications returns all medications data
func (s *UltimateDataService) GetMedications() interface{} {
	s.mutex.RLock()
	defer s.mutex.RUnlock()
	return s.data["medications"]
}

// GetVitaminsMinerals returns vitamins and minerals data
func (s *UltimateDataService) GetVitaminsMinerals() interface{} {
	s.mutex.RLock()
	defer s.mutex.RUnlock()
	return s.data["vitamins_minerals"]
}

// GetComprehensiveDiseases returns comprehensive diseases data
func (s *UltimateDataService) GetComprehensiveDiseases() interface{} {
	s.mutex.RLock()
	defer s.mutex.RUnlock()
	return s.data["comprehensive_diseases"]
}

// GetComprehensiveComplaints returns comprehensive complaints data
func (s *UltimateDataService) GetComprehensiveComplaints() interface{} {
	s.mutex.RLock()
	defer s.mutex.RUnlock()
	return s.data["comprehensive_complaints"]
}

// GetInjuries returns injuries data
func (s *UltimateDataService) GetInjuries() interface{} {
	s.mutex.RLock()
	defer s.mutex.RUnlock()
	return s.data["injuries"]
}

// GetDiseases returns diseases data
func (s *UltimateDataService) GetDiseases() interface{} {
	s.mutex.RLock()
	defer s.mutex.RUnlock()
	return s.data["diseases"]
}

// GetComplaints returns complaints data
func (s *UltimateDataService) GetComplaints() interface{} {
	s.mutex.RLock()
	defer s.mutex.RUnlock()
	return s.data["complaints"]
}

// GetTypePlans returns type plans data
func (s *UltimateDataService) GetTypePlans() interface{} {
	s.mutex.RLock()
	defer s.mutex.RUnlock()
	return s.data["type_plans"]
}

// GetWorkouts returns workouts data
func (s *UltimateDataService) GetWorkouts() interface{} {
	s.mutex.RLock()
	defer s.mutex.RUnlock()
	return s.data["workouts"]
}

// GetRecipes returns recipes data
func (s *UltimateDataService) GetRecipes() interface{} {
	s.mutex.RLock()
	defer s.mutex.RUnlock()
	return s.data["recipes"]
}

// GetMetadata returns metadata about the database
func (s *UltimateDataService) GetMetadata() interface{} {
	s.mutex.RLock()
	defer s.mutex.RUnlock()
	return s.data["metadata"]
}

// SearchData searches across all data categories
func (s *UltimateDataService) SearchData(query string) map[string]interface{} {
	s.mutex.RLock()
	defer s.mutex.RUnlock()

	results := make(map[string]interface{})
	query = strings.ToLower(query)

	// Search in each category
	for category, data := range s.data {
		if category == "metadata" {
			continue
		}

		// Convert to JSON for searching
		jsonData, err := json.Marshal(data)
		if err != nil {
			continue
		}

		jsonStr := strings.ToLower(string(jsonData))
		if strings.Contains(jsonStr, query) {
			results[category] = data
		}
	}

	return results
}

// GetDataStats returns statistics about the loaded data
func (s *UltimateDataService) GetDataStats() map[string]interface{} {
	s.mutex.RLock()
	defer s.mutex.RUnlock()

	stats := map[string]interface{}{
		"last_loaded": s.lastLoad,
		"categories":  len(s.data),
		"status":      "active",
	}

	if metadata, ok := s.data["metadata"]; ok {
		stats["metadata"] = metadata
	}

	return stats
}

// ReloadData reloads the database from file
func (s *UltimateDataService) ReloadData() error {
	log.Println("🔄 Reloading ultimate comprehensive database...")
	return s.LoadData()
}

// ValidateData performs basic validation on loaded data
func (s *UltimateDataService) ValidateData() map[string]interface{} {
	s.mutex.RLock()
	defer s.mutex.RUnlock()

	validation := map[string]interface{}{
		"timestamp":        time.Now(),
		"status":           "valid",
		"categories":       make(map[string]bool),
		"total_categories": len(s.data),
	}

	categories := validation["categories"].(map[string]bool)

	// Check each category
	expectedCategories := []string{
		"medications", "vitamins_minerals", "comprehensive_diseases",
		"comprehensive_complaints", "injuries", "diseases", "complaints",
		"type_plans", "workouts", "recipes", "metadata",
	}

	for _, category := range expectedCategories {
		categories[category] = s.data[category] != nil
	}

	return validation
}

// GetCategoryData returns data for a specific category with optional filtering
func (s *UltimateDataService) GetCategoryData(category string, filters map[string]string) interface{} {
	s.mutex.RLock()
	defer s.mutex.RUnlock()

	data, exists := s.data[category]
	if !exists {
		return nil
	}

	// If no filters, return all data
	if len(filters) == 0 {
		return data
	}

	// Apply filters (basic implementation)
	// This can be enhanced based on specific filtering needs
	return data
}
