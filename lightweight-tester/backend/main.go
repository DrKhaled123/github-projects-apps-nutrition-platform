package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"runtime"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

type TestResult struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	Status      string    `json:"status"` // "running", "passed", "failed"
	Duration    int64     `json:"duration"`
	Error       string    `json:"error,omitempty"`
	Timestamp   time.Time `json:"timestamp"`
	MemoryUsage int64     `json:"memory_usage"`
}

type TestRunner struct {
	mu          sync.RWMutex
	results     []TestResult
	connections map[*websocket.Conn]bool
	running     bool
	maxMemory   int64 // MB
}

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool { return true },
}

func NewTestRunner() *TestRunner {
	return &TestRunner{
		results:     make([]TestResult, 0),
		connections: make(map[*websocket.Conn]bool),
		maxMemory:   50, // 50MB limit
	}
}

func (tr *TestRunner) getMemoryUsage() int64 {
	var m runtime.MemStats
	runtime.GC()
	runtime.ReadMemStats(&m)
	return int64(m.Alloc / 1024 / 1024) // MB
}

func (tr *TestRunner) broadcastUpdate(result TestResult) {
	tr.mu.Lock()
	defer tr.mu.Unlock()

	data, _ := json.Marshal(result)
	for conn := range tr.connections {
		if err := conn.WriteMessage(websocket.TextMessage, data); err != nil {
			delete(tr.connections, conn)
		}
	}
}

func (tr *TestRunner) runLightweightTest(testName string) TestResult {
	start := time.Now()
	result := TestResult{
		ID:        fmt.Sprintf("%d", time.Now().UnixNano()),
		Name:      testName,
		Status:    "running",
		Timestamp: start,
	}

	tr.broadcastUpdate(result)

	// Simulate lightweight test execution
	time.Sleep(100 * time.Millisecond)

	// Check memory usage
	memUsage := tr.getMemoryUsage()
	if memUsage > tr.maxMemory {
		result.Status = "failed"
		result.Error = fmt.Sprintf("Memory limit exceeded: %dMB > %dMB", memUsage, tr.maxMemory)
	} else {
		result.Status = "passed"
	}

	result.Duration = time.Since(start).Milliseconds()
	result.MemoryUsage = memUsage

	tr.mu.Lock()
	tr.results = append(tr.results, result)
	// Keep only last 100 results to save memory
	if len(tr.results) > 100 {
		tr.results = tr.results[1:]
	}
	tr.mu.Unlock()

	tr.broadcastUpdate(result)
	return result
}

func (tr *TestRunner) handleWebSocket(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Println("WebSocket upgrade failed:", err)
		return
	}
	defer conn.Close()

	tr.mu.Lock()
	tr.connections[conn] = true
	tr.mu.Unlock()

	defer func() {
		tr.mu.Lock()
		delete(tr.connections, conn)
		tr.mu.Unlock()
	}()

	for {
		_, message, err := conn.ReadMessage()
		if err != nil {
			break
		}

		var msg map[string]string
		if err := json.Unmarshal(message, &msg); err != nil {
			continue
		}

		if msg["action"] == "run_test" && msg["name"] != "" {
			go tr.runLightweightTest(msg["name"])
		}
	}
}

func (tr *TestRunner) handleResults(w http.ResponseWriter, r *http.Request) {
	tr.mu.RLock()
	results := make([]TestResult, len(tr.results))
	copy(results, tr.results)
	tr.mu.RUnlock()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(results)
}

func (tr *TestRunner) handleHealth(w http.ResponseWriter, r *http.Request) {
	memUsage := tr.getMemoryUsage()
	status := map[string]interface{}{
		"status":      "healthy",
		"memory_mb":   memUsage,
		"connections": len(tr.connections),
		"total_tests": len(tr.results),
		"max_memory":  tr.maxMemory,
	}

	if memUsage > tr.maxMemory {
		status["status"] = "warning"
		status["message"] = "Memory usage high"
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(status)
}

func main() {
	runner := NewTestRunner()

	// Static file server for dashboard
	fs := http.FileServer(http.Dir("../dashboard"))
	http.Handle("/", fs)

	// API endpoints
	http.HandleFunc("/ws", runner.handleWebSocket)
	http.HandleFunc("/api/results", runner.handleResults)
	http.HandleFunc("/api/health", runner.handleHealth)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	fmt.Printf("Lightweight Test Runner starting on :%s\n", port)
	fmt.Printf("Dashboard: http://localhost:%s\n", port)
	fmt.Printf("WebSocket: ws://localhost:%s/ws\n", port)

	log.Fatal(http.ListenAndServe(":"+port, nil))
}
