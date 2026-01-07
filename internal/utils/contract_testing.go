package utils

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"reflect"
	"strings"
	"time"

	"api-key-generator/internal/models"
)

// ContractTest represents a contract test between client and server
type ContractTest struct {
	Name           string
	Description    string
	Request        ContractRequest
	Response       ContractResponse
	ExpectedStatus int
	Tags           []string
}

// ContractRequest represents the expected request structure
type ContractRequest struct {
	Method      string            `json:"method"`
	Path        string            `json:"path"`
	Headers     map[string]string `json:"headers"`
	Body        interface{}       `json:"body,omitempty"`
	QueryParams map[string]string `json:"query_params,omitempty"`
}

// ContractResponse represents the expected response structure
type ContractResponse struct {
	StatusCode int               `json:"status_code"`
	Headers    map[string]string `json:"headers"`
	Body       interface{}       `json:"body"`
}

// ContractTestSuite manages a collection of contract tests
type ContractTestSuite struct {
	BaseURL string
	Tests   []ContractTest
	Client  *http.Client
}

// ContractTestResult represents the result of a contract test
type ContractTestResult struct {
	TestName         string
	Passed           bool
	Actual           *http.Response
	Expected         ContractResponse
	Error            error
	Duration         time.Duration
	ValidationErrors []string
}

// NewContractTestSuite creates a new contract test suite
func NewContractTestSuite(baseURL string) *ContractTestSuite {
	return &ContractTestSuite{
		BaseURL: baseURL,
		Tests:   make([]ContractTest, 0),
		Client: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// AddTest adds a contract test to the suite
func (cts *ContractTestSuite) AddTest(test ContractTest) {
	cts.Tests = append(cts.Tests, test)
}

// RunAllTests executes all contract tests
func (cts *ContractTestSuite) RunAllTests() []ContractTestResult {
	results := make([]ContractTestResult, 0, len(cts.Tests))

	for _, test := range cts.Tests {
		result := cts.RunTest(test)
		results = append(results, result)
	}

	return results
}

// RunTest executes a single contract test
func (cts *ContractTestSuite) RunTest(test ContractTest) ContractTestResult {
	start := time.Now()
	result := ContractTestResult{
		TestName: test.Name,
		Passed:   false,
	}

	// Build the request
	req, err := cts.buildRequest(test.Request)
	if err != nil {
		result.Error = fmt.Errorf("failed to build request: %w", err)
		result.Duration = time.Since(start)
		return result
	}

	// Execute the request
	resp, err := cts.Client.Do(req)
	result.Duration = time.Since(start)

	if err != nil {
		result.Error = fmt.Errorf("request failed: %w", err)
		return result
	}

	result.Actual = resp
	result.Expected = test.Response

	// Validate the response
	if err := cts.validateResponse(resp, test.Response); err != nil {
		result.Error = err
		result.ValidationErrors = cts.extractValidationErrors(err)
		return result
	}

	result.Passed = true
	return result
}

// buildRequest constructs an HTTP request from contract specification
func (cts *ContractTestSuite) buildRequest(req ContractRequest) (*http.Request, error) {
	// Build URL
	url := cts.BaseURL + req.Path

	// Add query parameters
	if len(req.QueryParams) > 0 {
		url += "?"
		params := make([]string, 0, len(req.QueryParams))
		for key, value := range req.QueryParams {
			params = append(params, fmt.Sprintf("%s=%s", key, value))
		}
		url += strings.Join(params, "&")
	}

	// Create request
	var body io.Reader
	if req.Body != nil {
		bodyBytes, err := json.Marshal(req.Body)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal request body: %w", err)
		}
		body = bytes.NewBuffer(bodyBytes)
	}

	httpReq, err := http.NewRequest(req.Method, url, body)
	if err != nil {
		return nil, fmt.Errorf("failed to create HTTP request: %w", err)
	}

	// Add headers
	for key, value := range req.Headers {
		httpReq.Header.Set(key, value)
	}

	// Set Content-Type if body is provided
	if req.Body != nil {
		httpReq.Header.Set("Content-Type", "application/json")
	}

	return httpReq, nil
}

// validateResponse validates the actual response against expected response
func (cts *ContractTestSuite) validateResponse(actual *http.Response, expected ContractResponse) error {
	// Check status code
	if actual.StatusCode != expected.StatusCode {
		return fmt.Errorf("status code mismatch: expected %d, got %d", expected.StatusCode, actual.StatusCode)
	}

	// Check headers if specified
	for key, expectedValue := range expected.Headers {
		actualValue := actual.Header.Get(key)
		if actualValue != expectedValue {
			return fmt.Errorf("header %s mismatch: expected %s, got %s", key, expectedValue, actualValue)
		}
	}

	// Validate response body if specified
	if expected.Body != nil {
		if err := cts.validateResponseBody(actual, expected.Body); err != nil {
			return fmt.Errorf("response body validation failed: %w", err)
		}
	}

	return nil
}

// validateResponseBody validates the response body structure
func (cts *ContractTestSuite) validateResponseBody(resp *http.Response, expectedBody interface{}) error {
	// Read response body
	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("failed to read response body: %w", err)
	}

	// Parse actual body
	var actualBody interface{}
	if err := json.Unmarshal(bodyBytes, &actualBody); err != nil {
		return fmt.Errorf("failed to parse response body as JSON: %w", err)
	}

	// Compare structures
	return cts.compareJSONStructures(actualBody, expectedBody)
}

// compareJSONStructures recursively compares JSON structures
func (cts *ContractTestSuite) compareJSONStructures(actual, expected interface{}) error {
	actualValue := reflect.ValueOf(actual)
	expectedValue := reflect.ValueOf(expected)

	// Handle nil cases
	if actualValue.IsZero() && expectedValue.IsZero() {
		return nil
	}
	if actualValue.IsZero() || expectedValue.IsZero() {
		return fmt.Errorf("structure mismatch: one value is nil")
	}

	// Dereference pointers
	for actualValue.Kind() == reflect.Ptr {
		actualValue = actualValue.Elem()
	}
	for expectedValue.Kind() == reflect.Ptr {
		expectedValue = expectedValue.Elem()
	}

	switch expectedValue.Kind() {
	case reflect.Map:
		return cts.compareMaps(actualValue, expectedValue)
	case reflect.Slice, reflect.Array:
		return cts.compareSlices(actualValue, expectedValue)
	case reflect.String, reflect.Int, reflect.Float64, reflect.Bool:
		return cts.compareValues(actualValue, expectedValue)
	default:
		return fmt.Errorf("unsupported type: %v", expectedValue.Kind())
	}
}

// compareMaps compares map structures
func (cts *ContractTestSuite) compareMaps(actual, expected reflect.Value) error {
	if actual.Kind() != reflect.Map {
		return fmt.Errorf("expected map, got %v", actual.Kind())
	}

	actualMap := actual.Interface().(map[string]interface{})
	expectedMap := expected.Interface().(map[string]interface{})

	// Check if all expected keys exist
	for key := range expectedMap {
		if _, exists := actualMap[key]; !exists {
			return fmt.Errorf("missing expected key: %s", key)
		}
	}

	// Compare each expected key
	for key, expectedValue := range expectedMap {
		actualValue := actualMap[key]
		if err := cts.compareJSONStructures(actualValue, expectedValue); err != nil {
			return fmt.Errorf("key %s: %w", key, err)
		}
	}

	return nil
}

// compareSlices compares slice structures
func (cts *ContractTestSuite) compareSlices(actual, expected reflect.Value) error {
	if actual.Kind() != reflect.Slice && actual.Kind() != reflect.Array {
		return fmt.Errorf("expected slice/array, got %v", actual.Kind())
	}

	actualSlice := actual.Interface().([]interface{})
	expectedSlice := expected.Interface().([]interface{})

	if len(actualSlice) != len(expectedSlice) {
		return fmt.Errorf("slice length mismatch: expected %d, got %d", len(expectedSlice), len(actualSlice))
	}

	// Compare each element
	for i, expectedValue := range expectedSlice {
		if err := cts.compareJSONStructures(actualSlice[i], expectedValue); err != nil {
			return fmt.Errorf("index %d: %w", i, err)
		}
	}

	return nil
}

// compareValues compares primitive values by type
func (cts *ContractTestSuite) compareValues(actual, expected reflect.Value) error {
	actualType := reflect.TypeOf(actual.Interface())
	expectedType := reflect.TypeOf(expected.Interface())
	if actualType != expectedType {
		return fmt.Errorf("type mismatch: expected %v, got %v", expectedType, actualType)
	}
	return nil
}

// extractValidationErrors extracts detailed validation errors
func (cts *ContractTestSuite) extractValidationErrors(err error) []string {
	var errors []string

	// This is a simplified implementation
	// In practice, you might use a more sophisticated error parsing
	errors = append(errors, err.Error())

	return errors
}

// ReportContractTestResults generates a summary report of contract test results
func ReportContractTestResults(results []ContractTestResult) string {
	report := "Contract Test Results:\n"
	report += fmt.Sprintf("Total Tests: %d\n", len(results))

	passed := 0
	failed := 0
	totalDuration := time.Duration(0)

	for _, result := range results {
		totalDuration += result.Duration

		if result.Passed {
			passed++
			report += fmt.Sprintf("✅ %s: PASSED (%v)\n", result.TestName, result.Duration)
		} else {
			failed++
			report += fmt.Sprintf("❌ %s: FAILED (%v)\n", result.TestName, result.Duration)
			if result.Error != nil {
				report += fmt.Sprintf("   Error: %v\n", result.Error)
			}
			for _, validationError := range result.ValidationErrors {
				report += fmt.Sprintf("   Validation: %s\n", validationError)
			}
		}
	}

	report += fmt.Sprintf("\nSummary: %d passed, %d failed\n", passed, failed)
	report += fmt.Sprintf("Total Duration: %v\n", totalDuration)
	report += fmt.Sprintf("Average Duration: %v\n", totalDuration/time.Duration(len(results)))

	return report
}

// Predefined Contract Tests

// CreateAPIKeyContractTest creates a contract test for API key creation
func CreateAPIKeyContractTest() ContractTest {
	return ContractTest{
		Name:        "Create API Key Contract",
		Description: "Tests the contract for creating API keys",
		Request: ContractRequest{
			Method: "POST",
			Path:   "/api/v1/apikeys",
			Headers: map[string]string{
				"Content-Type": "application/json",
			},
			Body: map[string]interface{}{
				"name":        "test-key",
				"permissions": []string{"read", "write"},
				"expiry_days": 30,
			},
		},
		Response: ContractResponse{
			StatusCode: 201,
			Headers: map[string]string{
				"Content-Type": "application/json",
			},
			Body: map[string]interface{}{
				"id":          "string",
				"key":         "string",
				"name":        "test-key",
				"permissions": []string{"read", "write"},
				"is_active":   true,
				"created_at":  "string",
				"updated_at":  "string",
			},
		},
		ExpectedStatus: 201,
		Tags:           []string{"api", "keys", "create"},
	}
}

// GetAPIKeyContractTest creates a contract test for retrieving API keys
func GetAPIKeyContractTest() ContractTest {
	return ContractTest{
		Name:        "Get API Key Contract",
		Description: "Tests the contract for retrieving API keys",
		Request: ContractRequest{
			Method: "GET",
			Path:   "/api/v1/apikeys",
			Headers: map[string]string{
				"Authorization": "Bearer test-token",
			},
		},
		Response: ContractResponse{
			StatusCode: 200,
			Headers: map[string]string{
				"Content-Type": "application/json",
			},
			Body: map[string]interface{}{
				"api_keys": []interface{}{
					map[string]interface{}{
						"id":          "string",
						"name":        "string",
						"permissions": []string{},
						"is_active":   true,
						"created_at":  "string",
						"updated_at":  "string",
					},
				},
				"pagination": map[string]interface{}{
					"page":        1,
					"limit":       10,
					"total":       1,
					"total_pages": 1,
				},
			},
		},
		ExpectedStatus: 200,
		Tags:           []string{"api", "keys", "read"},
	}
}

// HealthCheckContractTest creates a contract test for health check endpoint
func HealthCheckContractTest() ContractTest {
	return ContractTest{
		Name:        "Health Check Contract",
		Description: "Tests the contract for health check endpoint",
		Request: ContractRequest{
			Method: "GET",
			Path:   "/health",
		},
		Response: ContractResponse{
			StatusCode: 200,
			Headers: map[string]string{
				"Content-Type": "application/json",
			},
			Body: map[string]interface{}{
				"status":    "healthy",
				"timestamp": "string",
				"version":   "string",
				"features":  []string{},
			},
		},
		ExpectedStatus: 200,
		Tags:           []string{"health", "monitoring"},
	}
}

// RunContractTests executes all predefined contract tests
func RunContractTests(baseURL string) []ContractTestResult {
	suite := NewContractTestSuite(baseURL)

	// Add predefined tests
	suite.AddTest(CreateAPIKeyContractTest())
	suite.AddTest(GetAPIKeyContractTest())
	suite.AddTest(HealthCheckContractTest())

	// Run all tests
	return suite.RunAllTests()
}

// APIContractValidator validates API contracts at runtime
type APIContractValidator struct {
	Contracts map[string]ContractTest
}

// compareJSONStructures recursively compares JSON structures
func (acv *APIContractValidator) compareJSONStructures(actual, expected interface{}) error {
	actualValue := reflect.ValueOf(actual)
	expectedValue := reflect.ValueOf(expected)

	// Handle nil cases
	if actualValue.IsZero() && expectedValue.IsZero() {
		return nil
	}
	if actualValue.IsZero() || expectedValue.IsZero() {
		return fmt.Errorf("structure mismatch: one value is nil")
	}

	// Dereference pointers
	for actualValue.Kind() == reflect.Ptr {
		actualValue = actualValue.Elem()
	}
	for expectedValue.Kind() == reflect.Ptr {
		expectedValue = expectedValue.Elem()
	}

	switch expectedValue.Kind() {
	case reflect.Map:
		return acv.compareMaps(actualValue, expectedValue)
	case reflect.Slice, reflect.Array:
		return acv.compareSlices(actualValue, expectedValue)
	case reflect.String, reflect.Int, reflect.Float64, reflect.Bool:
		return acv.compareValues(actualValue, expectedValue)
	default:
		return fmt.Errorf("unsupported type: %v", expectedValue.Kind())
	}
}

// compareMaps compares map structures
func (acv *APIContractValidator) compareMaps(actual, expected reflect.Value) error {
	if actual.Kind() != reflect.Map {
		return fmt.Errorf("expected map, got %v", actual.Kind())
	}

	actualMap := actual.Interface().(map[string]interface{})
	expectedMap := expected.Interface().(map[string]interface{})

	// Check if all expected keys exist
	for key := range expectedMap {
		if _, exists := actualMap[key]; !exists {
			return fmt.Errorf("missing expected key: %s", key)
		}
	}

	// Compare each expected key
	for key, expectedValue := range expectedMap {
		actualValue := actualMap[key]
		if err := acv.compareJSONStructures(actualValue, expectedValue); err != nil {
			return fmt.Errorf("key %s: %w", key, err)
		}
	}

	return nil
}

// compareSlices compares slice structures
func (acv *APIContractValidator) compareSlices(actual, expected reflect.Value) error {
	if actual.Kind() != reflect.Slice && actual.Kind() != reflect.Array {
		return fmt.Errorf("expected slice/array, got %v", actual.Kind())
	}

	actualSlice := actual.Interface().([]interface{})
	expectedSlice := expected.Interface().([]interface{})

	if len(actualSlice) != len(expectedSlice) {
		return fmt.Errorf("slice length mismatch: expected %d, got %d", len(expectedSlice), len(actualSlice))
	}

	// Compare each element
	for i, expectedValue := range expectedSlice {
		if err := acv.compareJSONStructures(actualSlice[i], expectedValue); err != nil {
			return fmt.Errorf("index %d: %w", i, err)
		}
	}

	return nil
}

// compareValues compares primitive values by type
func (acv *APIContractValidator) compareValues(actual, expected reflect.Value) error {
	actualType := reflect.TypeOf(actual.Interface())
	expectedType := reflect.TypeOf(expected.Interface())
	if actualType != expectedType {
		return fmt.Errorf("type mismatch: expected %v, got %v", expectedType, actualType)
	}
	return nil
}

// NewAPIContractValidator creates a new API contract validator
func NewAPIContractValidator() *APIContractValidator {
	return &APIContractValidator{
		Contracts: make(map[string]ContractTest),
	}
}

// RegisterContract registers a contract for validation
func (acv *APIContractValidator) RegisterContract(test ContractTest) {
	key := fmt.Sprintf("%s %s", test.Request.Method, test.Request.Path)
	acv.Contracts[key] = test
}

// ValidateRequest validates an incoming request against its contract
func (acv *APIContractValidator) ValidateRequest(method, path string, body interface{}) []models.ValidationError {
	key := fmt.Sprintf("%s %s", method, path)
	contract, exists := acv.Contracts[key]

	var errors []models.ValidationError

	if !exists {
		errors = append(errors, models.ValidationError{
			Field:   "contract",
			Message: fmt.Sprintf("No contract found for %s", key),
		})
		return errors
	}

	// Validate request body structure
	if contract.Request.Body != nil {
		if err := acv.validateRequestBody(body, contract.Request.Body); err != nil {
			errors = append(errors, models.ValidationError{
				Field:   "body",
				Message: err.Error(),
			})
		}
	}

	return errors
}

// validateRequestBody validates request body structure
func (acv *APIContractValidator) validateRequestBody(actual, expected interface{}) error {
	if actual == nil && expected == nil {
		return nil
	}
	if actual == nil || expected == nil {
		return fmt.Errorf("body structure mismatch: one is nil")
	}
	return acv.compareJSONStructures(actual, expected)
}

// ValidateResponse validates an outgoing response against its contract
func (acv *APIContractValidator) ValidateResponse(method, path string, statusCode int, body interface{}) []models.ValidationError {
	key := fmt.Sprintf("%s %s", method, path)
	contract, exists := acv.Contracts[key]

	var errors []models.ValidationError

	if !exists {
		return errors // No contract to validate against
	}

	// Check status code
	if contract.ExpectedStatus != statusCode {
		errors = append(errors, models.ValidationError{
			Field:   "status_code",
			Value:   statusCode,
			Message: fmt.Sprintf("Expected status %d, got %d", contract.ExpectedStatus, statusCode),
		})
	}

	// Validate response body structure
	if contract.Response.Body != nil {
		if err := acv.validateResponseBodyStructure(body, contract.Response.Body); err != nil {
			errors = append(errors, models.ValidationError{
				Field:   "body",
				Message: err.Error(),
			})
		}
	}

	return errors
}

// validateResponseBodyStructure validates response body structure
func (acv *APIContractValidator) validateResponseBodyStructure(actual, expected interface{}) error {
	if actual == nil && expected == nil {
		return nil
	}
	if actual == nil || expected == nil {
		return fmt.Errorf("response body structure mismatch: one is nil")
	}
	return acv.compareJSONStructures(actual, expected)
}
