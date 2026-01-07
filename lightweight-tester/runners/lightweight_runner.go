package main

import (
	"context"
	"fmt"
	"log"
	"os/exec"
	"runtime"
	"strings"
	"sync"
	"time"
)

type LightweightRunner struct {
	maxMemoryMB   int64
	maxConcurrent int
	running       int32
	mu            sync.Mutex
}

type TestResult struct {
	Name       string
	Status     string
	Duration   time.Duration
	MemoryPeak int64
	Error      string
	Output     string
}

func NewLightweightRunner(maxMemoryMB int64, maxConcurrent int) *LightweightRunner {
	return &LightweightRunner{
		maxMemoryMB:   maxMemoryMB,
		maxConcurrent: maxConcurrent,
	}
}

func (lr *LightweightRunner) getMemoryUsage() int64 {
	var m runtime.MemStats
	runtime.GC()
	runtime.ReadMemStats(&m)
	return int64(m.Alloc / 1024 / 1024)
}

func (lr *LightweightRunner) checkMemoryLimit() error {
	current := lr.getMemoryUsage()
	if current > lr.maxMemoryMB {
		return fmt.Errorf("memory limit exceeded: %dMB > %dMB", current, lr.maxMemoryMB)
	}
	return nil
}

func (lr *LightweightRunner) RunSimpleTest(ctx context.Context, testName string) (*TestResult, error) {
	start := time.Now()
	result := &TestResult{Name: testName}

	// Check memory before starting
	if err := lr.checkMemoryLimit(); err != nil {
		result.Status = "failed"
		result.Error = err.Error()
		return result, err
	}

	// Simulate lightweight test execution
	select {
	case <-ctx.Done():
		result.Status = "cancelled"
		return result, ctx.Err()
	case <-time.After(50 * time.Millisecond):
		// Simple test logic
		if strings.Contains(testName, "fail") {
			result.Status = "failed"
			result.Error = "Simulated test failure"
		} else {
			result.Status = "passed"
		}
	}

	result.Duration = time.Since(start)
	result.MemoryPeak = lr.getMemoryUsage()

	return result, nil
}

func (lr *LightweightRunner) RunCommandTest(ctx context.Context, command string, args ...string) (*TestResult, error) {
	start := time.Now()
	result := &TestResult{Name: fmt.Sprintf("Command: %s", command)}

	// Check memory before starting
	if err := lr.checkMemoryLimit(); err != nil {
		result.Status = "failed"
		result.Error = err.Error()
		return result, err
	}

	cmd := exec.CommandContext(ctx, command, args...)
	output, err := cmd.CombinedOutput()

	result.Output = string(output)
	result.Duration = time.Since(start)
	result.MemoryPeak = lr.getMemoryUsage()

	if err != nil {
		result.Status = "failed"
		result.Error = err.Error()
	} else {
		result.Status = "passed"
	}

	return result, nil
}

func (lr *LightweightRunner) RunHTTPTest(ctx context.Context, url string) (*TestResult, error) {
	return lr.RunCommandTest(ctx, "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url)
}

func (lr *LightweightRunner) RunBatchTests(ctx context.Context, tests []string) ([]*TestResult, error) {
	results := make([]*TestResult, len(tests))
	semaphore := make(chan struct{}, lr.maxConcurrent)

	var wg sync.WaitGroup
	var mu sync.Mutex

	for i, test := range tests {
		wg.Add(1)
		go func(index int, testName string) {
			defer wg.Done()

			// Acquire semaphore
			semaphore <- struct{}{}
			defer func() { <-semaphore }()

			result, err := lr.RunSimpleTest(ctx, testName)
			if err != nil {
				log.Printf("Test %s failed: %v", testName, err)
			}

			mu.Lock()
			results[index] = result
			mu.Unlock()
		}(i, test)
	}

	wg.Wait()
	return results, nil
}

func (lr *LightweightRunner) Cleanup() {
	runtime.GC()
}

func main() {
	runner := NewLightweightRunner(50, 3) // 50MB limit, 3 concurrent tests

	// Example usage
	ctx := context.Background()

	// Run single test
	result, err := runner.RunSimpleTest(ctx, "basic-connectivity-test")
	if err != nil {
		log.Printf("Test failed: %v", err)
	}
	fmt.Printf("Test: %s, Status: %s, Duration: %v, Memory: %dMB\n",
		result.Name, result.Status, result.Duration, result.MemoryPeak)

	// Run HTTP test
	httpResult, err := runner.RunHTTPTest(ctx, "https://httpbin.org/status/200")
	if err != nil {
		log.Printf("HTTP test failed: %v", err)
	}
	fmt.Printf("HTTP Test: %s, Status: %s, Duration: %v\n",
		httpResult.Name, httpResult.Status, httpResult.Duration)

	// Run batch tests
	tests := []string{
		"auth-test",
		"database-test",
		"api-test",
		"ui-test",
		"performance-test",
	}

	batchResults, err := runner.RunBatchTests(ctx, tests)
	if err != nil {
		log.Printf("Batch test failed: %v", err)
	}

	fmt.Println("\nBatch Test Results:")
	for _, result := range batchResults {
		fmt.Printf("- %s: %s (%v)\n", result.Name, result.Status, result.Duration)
	}

	runner.Cleanup()
}
