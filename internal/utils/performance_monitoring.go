package utils

import (
	"fmt"
	"log"
	"runtime"
	"strings"
	"sync"
	"time"
)

// PerformanceMetrics holds performance measurement data
type PerformanceMetrics struct {
	Operation    string        `json:"operation"`
	Duration     time.Duration `json:"duration"`
	MemoryUsage  int64         `json:"memory_usage"`
	Goroutines   int           `json:"goroutines"`
	Timestamp    time.Time     `json:"timestamp"`
	Success      bool          `json:"success"`
	ErrorMessage string        `json:"error_message,omitempty"`
}

// PerformanceMonitor tracks performance metrics and alerts
type PerformanceMonitor struct {
	Thresholds map[string]time.Duration
	Metrics    []PerformanceMetrics
	MaxMetrics int
	AlertFunc  func(alert PerformanceAlert)
	mutex      sync.RWMutex
	Enabled    bool
}

// PerformanceAlert represents a performance alert
type PerformanceAlert struct {
	Level      string             `json:"level"`
	Operation  string             `json:"operation"`
	Message    string             `json:"message"`
	Metrics    PerformanceMetrics `json:"metrics"`
	Threshold  time.Duration      `json:"threshold"`
	ExceededBy time.Duration      `json:"exceeded_by"`
	Timestamp  time.Time          `json:"timestamp"`
}

// NewPerformanceMonitor creates a new performance monitor
func NewPerformanceMonitor() *PerformanceMonitor {
	pm := &PerformanceMonitor{
		Thresholds: make(map[string]time.Duration),
		Metrics:    make([]PerformanceMetrics, 0),
		MaxMetrics: 1000,
		Enabled:    true,
		AlertFunc: func(alert PerformanceAlert) {
			log.Printf("PERFORMANCE ALERT [%s]: %s", alert.Level, alert.Message)
		},
	}

	// Set default thresholds
	pm.SetThreshold("wasm_execution", 500*time.Millisecond)
	pm.SetThreshold("api_request", 2*time.Second)
	pm.SetThreshold("database_query", 1*time.Second)
	pm.SetThreshold("file_operation", 500*time.Millisecond)

	return pm
}

// SetThreshold sets a performance threshold for an operation
func (pm *PerformanceMonitor) SetThreshold(operation string, threshold time.Duration) {
	pm.mutex.Lock()
	defer pm.mutex.Unlock()
	pm.Thresholds[operation] = threshold
}

// Enable enables performance monitoring
func (pm *PerformanceMonitor) Enable() {
	pm.mutex.Lock()
	defer pm.mutex.Unlock()
	pm.Enabled = true
}

// Disable disables performance monitoring
func (pm *PerformanceMonitor) Disable() {
	pm.mutex.Lock()
	defer pm.mutex.Unlock()
	pm.Enabled = false
}

// MonitorOperation monitors the execution time of an operation
func (pm *PerformanceMonitor) MonitorOperation(operation string, fn func() error) error {
	if !pm.Enabled {
		return fn()
	}

	start := time.Now()
	var memStatsBefore runtime.MemStats
	runtime.ReadMemStats(&memStatsBefore)

	err := fn()

	duration := time.Since(start)
	var memStatsAfter runtime.MemStats
	runtime.ReadMemStats(&memStatsAfter)

	// Record metrics
	metrics := PerformanceMetrics{
		Operation:   operation,
		Duration:    duration,
		MemoryUsage: int64(memStatsAfter.Alloc - memStatsBefore.Alloc),
		Goroutines:  runtime.NumGoroutine(),
		Timestamp:   start,
		Success:     err == nil,
	}

	if err != nil {
		metrics.ErrorMessage = err.Error()
	}

	pm.recordMetrics(metrics)

	// Check thresholds and alert if necessary
	pm.checkThresholds(metrics)

	return err
}

// MonitorWasmOperation is a specialized monitor for WASM operations
func (pm *PerformanceMonitor) MonitorWasmOperation(operation string, fn func() (interface{}, error)) (interface{}, error) {
	if !pm.Enabled {
		return fn()
	}

	start := time.Now()
	var memStatsBefore runtime.MemStats
	runtime.ReadMemStats(&memStatsBefore)

	result, err := fn()

	duration := time.Since(start)
	var memStatsAfter runtime.MemStats
	runtime.ReadMemStats(&memStatsAfter)

	// Record metrics
	metrics := PerformanceMetrics{
		Operation:   operation,
		Duration:    duration,
		MemoryUsage: int64(memStatsAfter.Alloc - memStatsBefore.Alloc),
		Goroutines:  runtime.NumGoroutine(),
		Timestamp:   start,
		Success:     err == nil,
	}

	if err != nil {
		metrics.ErrorMessage = fmt.Sprintf("%v", err)
	}

	pm.recordMetrics(metrics)

	// Check thresholds and alert if necessary
	pm.checkThresholds(metrics)

	return result, err
}

// recordMetrics stores performance metrics
func (pm *PerformanceMonitor) recordMetrics(metrics PerformanceMetrics) {
	pm.mutex.Lock()
	defer pm.mutex.Unlock()

	pm.Metrics = append(pm.Metrics, metrics)

	// Keep only the most recent metrics
	if len(pm.Metrics) > pm.MaxMetrics {
		pm.Metrics = pm.Metrics[len(pm.Metrics)-pm.MaxMetrics:]
	}
}

// checkThresholds checks if metrics exceed thresholds
func (pm *PerformanceMonitor) checkThresholds(metrics PerformanceMetrics) {
	pm.mutex.RLock()
	threshold, exists := pm.Thresholds[metrics.Operation]
	pm.mutex.RUnlock()

	if !exists {
		return
	}

	if metrics.Duration > threshold {
		alert := PerformanceAlert{
			Level:      "warning",
			Operation:  metrics.Operation,
			Message:    fmt.Sprintf("Operation %s took %v, exceeding threshold %v", metrics.Operation, metrics.Duration, threshold),
			Metrics:    metrics,
			Threshold:  threshold,
			ExceededBy: metrics.Duration - threshold,
			Timestamp:  time.Now(),
		}

		// Escalate to error if significantly exceeded
		if metrics.Duration > threshold*2 {
			alert.Level = "error"
		}

		if pm.AlertFunc != nil {
			pm.AlertFunc(alert)
		}
	}
}

// GetMetrics returns recent performance metrics
func (pm *PerformanceMonitor) GetMetrics() []PerformanceMetrics {
	pm.mutex.RLock()
	defer pm.mutex.RUnlock()

	// Return a copy to prevent external modification
	result := make([]PerformanceMetrics, len(pm.Metrics))
	copy(result, pm.Metrics)
	return result
}

// GetMetricsForOperation returns metrics for a specific operation
func (pm *PerformanceMonitor) GetMetricsForOperation(operation string) []PerformanceMetrics {
	pm.mutex.RLock()
	defer pm.mutex.RUnlock()

	var result []PerformanceMetrics
	for _, metric := range pm.Metrics {
		if metric.Operation == operation {
			result = append(result, metric)
		}
	}
	return result
}

// GetAverageDuration returns the average duration for an operation
func (pm *PerformanceMonitor) GetAverageDuration(operation string) time.Duration {
	metrics := pm.GetMetricsForOperation(operation)

	if len(metrics) == 0 {
		return 0
	}

	var total time.Duration
	for _, metric := range metrics {
		total += metric.Duration
	}

	return total / time.Duration(len(metrics))
}

// GetSlowOperations returns operations that consistently exceed thresholds
func (pm *PerformanceMonitor) GetSlowOperations() []SlowOperationReport {
	pm.mutex.RLock()
	defer pm.mutex.RUnlock()

	operationStats := make(map[string]struct {
		Count     int
		TotalTime time.Duration
		MaxTime   time.Duration
		Threshold time.Duration
	})

	for _, metric := range pm.Metrics {
		threshold, exists := pm.Thresholds[metric.Operation]
		if !exists {
			continue
		}

		if metric.Duration > threshold {
			stats := operationStats[metric.Operation]
			stats.Count++
			stats.TotalTime += metric.Duration
			if metric.Duration > stats.MaxTime {
				stats.MaxTime = metric.Duration
			}
			stats.Threshold = threshold
			operationStats[metric.Operation] = stats
		}
	}

	var result []SlowOperationReport
	for operation, stats := range operationStats {
		if stats.Count > 0 {
			result = append(result, SlowOperationReport{
				Operation:       operation,
				SlowOccurrences: stats.Count,
				AverageTime:     stats.TotalTime / time.Duration(stats.Count),
				MaxTime:         stats.MaxTime,
				Threshold:       stats.Threshold,
			})
		}
	}

	return result
}

// SlowOperationReport reports on slow operations
type SlowOperationReport struct {
	Operation       string        `json:"operation"`
	SlowOccurrences int           `json:"slow_occurrences"`
	AverageTime     time.Duration `json:"average_time"`
	MaxTime         time.Duration `json:"max_time"`
	Threshold       time.Duration `json:"threshold"`
}

// WasmPerformanceTracker provides specialized tracking for WASM operations
type WasmPerformanceTracker struct {
	Monitor           *PerformanceMonitor
	WasmThresholds    map[string]time.Duration
	MemoryThreshold   int64
	AlertOnMemoryLeak bool
}

// NewWasmPerformanceTracker creates a new WASM performance tracker
func NewWasmPerformanceTracker() *WasmPerformanceTracker {
	baseMonitor := NewPerformanceMonitor()

	wpt := &WasmPerformanceTracker{
		Monitor:           baseMonitor,
		WasmThresholds:    make(map[string]time.Duration),
		MemoryThreshold:   100 * 1024 * 1024, // 100MB
		AlertOnMemoryLeak: true,
	}

	// Set WASM-specific thresholds
	wpt.WasmThresholds["wasm_init"] = 2 * time.Second
	wpt.WasmThresholds["wasm_call"] = 500 * time.Millisecond
	wpt.WasmThresholds["wasm_memory_alloc"] = 100 * time.Millisecond

	return wpt
}

// TrackWasmOperation tracks a WASM operation with specialized monitoring
func (wpt *WasmPerformanceTracker) TrackWasmOperation(operation string, fn func() (interface{}, error)) (interface{}, error) {
	// Set up custom alert function for WASM-specific alerts
	originalAlertFunc := wpt.Monitor.AlertFunc
	wpt.Monitor.AlertFunc = func(alert PerformanceAlert) {
		if strings.Contains(alert.Operation, "wasm") {
			wpt.handleWasmAlert(alert)
		}
		if originalAlertFunc != nil {
			originalAlertFunc(alert)
		}
	}

	// Use the base monitor
	result, err := wpt.Monitor.MonitorWasmOperation(operation, fn)

	// Restore original alert function
	wpt.Monitor.AlertFunc = originalAlertFunc

	return result, err
}

// handleWasmAlert handles WASM-specific performance alerts
func (wpt *WasmPerformanceTracker) handleWasmAlert(alert PerformanceAlert) {
	// Check for memory leaks
	if wpt.AlertOnMemoryLeak && alert.Metrics.MemoryUsage > wpt.MemoryThreshold {
		wasmAlert := PerformanceAlert{
			Level:     "error",
			Operation: alert.Operation,
			Message:   fmt.Sprintf("WASM memory usage %d bytes exceeds threshold %d bytes", alert.Metrics.MemoryUsage, wpt.MemoryThreshold),
			Metrics:   alert.Metrics,
			Timestamp: time.Now(),
		}

		if wpt.Monitor.AlertFunc != nil {
			wpt.Monitor.AlertFunc(wasmAlert)
		}
	}

	// Check for excessive goroutine creation
	if alert.Metrics.Goroutines > 100 {
		goroutineAlert := PerformanceAlert{
			Level:     "warning",
			Operation: alert.Operation,
			Message:   fmt.Sprintf("High goroutine count: %d", alert.Metrics.Goroutines),
			Metrics:   alert.Metrics,
			Timestamp: time.Now(),
		}

		if wpt.Monitor.AlertFunc != nil {
			wpt.Monitor.AlertFunc(goroutineAlert)
		}
	}
}

// GetWasmMetrics returns WASM-specific metrics
func (wpt *WasmPerformanceTracker) GetWasmMetrics() []PerformanceMetrics {
	var wasmMetrics []PerformanceMetrics
	allMetrics := wpt.Monitor.GetMetrics()

	for _, metric := range allMetrics {
		if strings.Contains(metric.Operation, "wasm") {
			wasmMetrics = append(wasmMetrics, metric)
		}
	}

	return wasmMetrics
}

// PerformanceBenchmark provides benchmarking capabilities
type PerformanceBenchmark struct {
	Monitor *PerformanceMonitor
	Results map[string][]time.Duration
	mutex   sync.RWMutex
}

// NewPerformanceBenchmark creates a new performance benchmark
func NewPerformanceBenchmark() *PerformanceBenchmark {
	return &PerformanceBenchmark{
		Monitor: NewPerformanceMonitor(),
		Results: make(map[string][]time.Duration),
	}
}

// BenchmarkOperation benchmarks an operation multiple times
func (pb *PerformanceBenchmark) BenchmarkOperation(name string, iterations int, fn func() error) BenchmarkResult {
	start := time.Now()

	var durations []time.Duration
	var errors []error

	for i := 0; i < iterations; i++ {
		iterStart := time.Now()
		err := fn()
		iterDuration := time.Since(iterStart)

		durations = append(durations, iterDuration)

		if err != nil {
			errors = append(errors, err)
		}
	}

	totalDuration := time.Since(start)

	pb.mutex.Lock()
	pb.Results[name] = durations
	pb.mutex.Unlock()

	return BenchmarkResult{
		Name:        name,
		Iterations:  iterations,
		TotalTime:   totalDuration,
		AverageTime: totalDuration / time.Duration(iterations),
		MinTime:     minimum(durations),
		MaxTime:     maximum(durations),
		ErrorCount:  len(errors),
		Errors:      errors,
	}
}

// BenchmarkResult represents the result of a benchmark
type BenchmarkResult struct {
	Name        string        `json:"name"`
	Iterations  int           `json:"iterations"`
	TotalTime   time.Duration `json:"total_time"`
	AverageTime time.Duration `json:"average_time"`
	MinTime     time.Duration `json:"min_time"`
	MaxTime     time.Duration `json:"max_time"`
	ErrorCount  int           `json:"error_count"`
	Errors      []error       `json:"errors,omitempty"`
}

// GetBenchmarkResults returns all benchmark results
func (pb *PerformanceBenchmark) GetBenchmarkResults() map[string]BenchmarkResult {
	pb.mutex.RLock()
	defer pb.mutex.RUnlock()

	results := make(map[string]BenchmarkResult)

	for name, durations := range pb.Results {
		if len(durations) == 0 {
			continue
		}

		results[name] = BenchmarkResult{
			Name:        name,
			Iterations:  len(durations),
			TotalTime:   sum(durations),
			AverageTime: average(durations),
			MinTime:     minimum(durations),
			MaxTime:     maximum(durations),
		}
	}

	return results
}

// Helper functions for benchmark calculations
func sum(durations []time.Duration) time.Duration {
	var total time.Duration
	for _, d := range durations {
		total += d
	}
	return total
}

func average(durations []time.Duration) time.Duration {
	if len(durations) == 0 {
		return 0
	}
	return sum(durations) / time.Duration(len(durations))
}

func minimum(durations []time.Duration) time.Duration {
	if len(durations) == 0 {
		return 0
	}
	min := durations[0]
	for _, d := range durations[1:] {
		if d < min {
			min = d
		}
	}
	return min
}

func maximum(durations []time.Duration) time.Duration {
	if len(durations) == 0 {
		return 0
	}
	max := durations[0]
	for _, d := range durations[1:] {
		if d > max {
			max = d
		}
	}
	return max
}

// Global performance monitor instance
var GlobalPerformanceMonitor = NewPerformanceMonitor()
var GlobalWasmTracker = NewWasmPerformanceTracker()

// Monitor wraps the global monitor for convenience
func Monitor(operation string, fn func() error) error {
	return GlobalPerformanceMonitor.MonitorOperation(operation, fn)
}

// MonitorWasm wraps the global WASM tracker for convenience
func MonitorWasm(operation string, fn func() (interface{}, error)) (interface{}, error) {
	return GlobalWasmTracker.TrackWasmOperation(operation, fn)
}

// Benchmark wraps the global benchmark for convenience
func Benchmark(name string, iterations int, fn func() error) BenchmarkResult {
	benchmark := NewPerformanceBenchmark()
	return benchmark.BenchmarkOperation(name, iterations, fn)
}
