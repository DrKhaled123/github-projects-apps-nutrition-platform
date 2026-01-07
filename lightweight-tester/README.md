# Lightweight Test Runner

A resource-efficient testing automation system with real-time updates and minimal memory/disk usage.

## Features

- **Low Resource Usage**: ~50MB RAM, minimal disk footprint
- **Real-time Updates**: WebSocket-based live test monitoring
- **Memory Monitoring**: Automatic memory limit enforcement
- **Concurrent Testing**: Configurable concurrent test execution
- **Web Dashboard**: Static HTML interface, no heavy frameworks
- **Go Backend**: Minimal dependencies, fast compilation

## Architecture

```
lightweight-tester/
├── backend/          # Go HTTP/WebSocket server
├── dashboard/        # Static HTML dashboard
├── runners/          # Lightweight test execution engine
└── tests/           # Example test configurations
```

## Quick Start

1. **Install Go** (1.21+)
2. **Clone and build**:
   ```bash
   cd lightweight-tester/backend
   go mod tidy
   go build -o test-runner main.go
   ```

3. **Start the server**:
   ```bash
   ./test-runner
   ```

4. **Open dashboard**:
   ```
   http://localhost:8080
   ```

## API Endpoints

- `GET /` - Dashboard interface
- `GET /api/health` - System health status
- `GET /api/results` - Test results history
- `WS /ws` - Real-time test updates

## Test Runner Features

### Memory Management
- Automatic memory monitoring
- Configurable memory limits (default: 50MB)
- Garbage collection optimization

### Concurrent Execution
- Configurable concurrent test limit
- Semaphore-based resource control
- Context-based cancellation

### Test Types
- **Simple Tests**: Lightweight unit-style tests
- **Command Tests**: External command execution
- **HTTP Tests**: REST API endpoint testing
- **Batch Tests**: Parallel test execution

## Configuration

```go
runner := NewLightweightRunner(50, 3) // 50MB limit, 3 concurrent tests
```

## Resource Usage

- **Memory**: < 50MB during normal operation
- **Disk**: < 10MB for application + results
- **CPU**: Minimal background processing
- **Network**: WebSocket connections only

## Browser Testing (Optional)

For browser automation with minimal footprint:

```bash
# Install lightweight browser testing
npm install puppeteer-core --save-dev
```

The system can integrate with headless Chrome/Chromium for UI testing while maintaining low resource usage through:

- Browser instance reuse
- Minimal viewport sizes
- Automatic cleanup
- Memory monitoring

## Development

### Adding New Test Types

```go
func (lr *LightweightRunner) RunCustomTest(ctx context.Context, config TestConfig) (*TestResult, error) {
    // Check memory limits
    if err := lr.checkMemoryLimit(); err != nil {
        return &TestResult{Status: "failed", Error: err.Error()}, err
    }

    // Your test logic here
    // ...

    return result, nil
}
```

### Extending the Dashboard

The dashboard is pure HTML/CSS/JS. Add new features by:

1. Adding HTML elements
2. Implementing JavaScript functions
3. Using the WebSocket API for real-time updates

## Monitoring

The system provides built-in monitoring:

- Memory usage tracking
- Connection count monitoring
- Test execution statistics
- Health status indicators

## Cleanup

Automatic cleanup features:

- Old test result pruning (keeps last 100)
- Memory garbage collection
- WebSocket connection cleanup
- Temporary file removal

## Security

- Minimal attack surface (single binary)
- No database dependencies
- In-memory result storage
- Configurable resource limits

## Performance

- Sub-millisecond test execution for simple tests
- WebSocket-based real-time updates (no polling)
- Efficient memory usage with Go's GC
- Concurrent test execution with resource limits