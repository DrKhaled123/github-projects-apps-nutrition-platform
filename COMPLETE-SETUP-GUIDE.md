# Complete Setup Guide

## Part 1: AI Agents Shared Memory System

### Purpose
Lightweight, file-based memory sharing between AI coding agents (Kilocode, Roo Code, Cline) with **minimal RAM overhead** (<1MB).

### Quick Setup

1. **Initialize shared memory:**
```bash
cd ai-agents-shared-memory
python utils/memory_manager.py
```

2. **Test memory operations:**
```bash
# Write to shared memory
python -c "
from utils.memory_manager import MemoryManager
m = MemoryManager()
m.write('context', 'test_key', {'data': 'hello'}, agent='test')
"

# Read from shared memory
python -c "
from utils.memory_manager import MemoryManager
m = MemoryManager()
print(m.read('context', 'test_key'))
"
```

3. **Configure AI Agents:**

**For Kilocode:** Add to `.kilocode/config.json`:
```json
{
  "shared_memory_path": "./ai-agents-shared-memory",
  "memory_check_interval": 30
}
```

**For Roo Code:** Add to `.roocode/settings.json`:
```json
{
  "memory": {
    "type": "file-based",
    "path": "./ai-agents-shared-memory"
  }
}
```

**For Cline:** Add to `.cline/mcp.json`:
```json
{
  "shared_memory": "./ai-agents-shared-memory",
  "sync_enabled": true
}
```

### Memory Categories

- **context**: Current work state (24h TTL)
- **knowledge**: Persistent learnings (no expiry)
- **tasks**: Task queue (48h TTL)
- **history**: Action logs (7 days TTL)

### Performance Metrics

- Memory footprint: < 1MB
- Read latency: < 10ms
- Write latency: < 20ms
- Concurrent access: 100+ simultaneous reads

---

## Part 2: CI/CD Orchestration Pipeline

### Purpose
Automated pipeline: Testing → Code Review → Docker Build → Coolify Deployment

### Architecture

```
┌─────────────────────────────────────────────────────┐
│           Main Orchestrator                         │
└─────────────────┬───────────────────────────────────┘
                  │
    ┌─────────────┼─────────────┬──────────────┐
    ▼             ▼             ▼              ▼
┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
│ Testing │  │ Review  │  │  Build  │  │ Deploy  │
└─────────┘  └─────────┘  └─────────┘  └─────────┘
```

### Quick Setup

1. **Install dependencies:**
```bash
pip install -r orchestration/requirements.txt
```

2. **Configure environment variables:**
```bash
# Docker Registry
export DOCKER_USERNAME="your-username"
export DOCKER_PASSWORD="your-password"

# Coolify API
export COOLIFY_API_URL="https://your-coolify.com/api"
export COOLIFY_API_TOKEN="your-api-token"
export COOLIFY_PROJECT_ID="your-project-id"
export COOLIFY_APP_ID="your-app-id"
```

3. **Update configuration:**
Edit `orchestration/orchestration-config.json`:
- Set your Docker repository
- Configure Coolify settings
- Adjust test/review/build settings

### Usage

#### Run Full Pipeline
```bash
cd orchestration
python main_orchestrator.py --mode full
```

#### Run Individual Stages
```bash
# Testing only
python testing_orchestrator.py --type all

# Code review only
python review_orchestrator.py

# Docker build only
python build_orchestrator.py

# Deploy only
python deploy_orchestrator.py --image myapp --tag latest
```

#### Run Specific Stages
```bash
# Run test + review only
python main_orchestrator.py --stages test review

# Run build + deploy only
python main_orchestrator.py --stages build deploy
```

### Integration with AI Agents

#### Trigger Pipeline from AI Agent
```bash
# Write task to shared memory
./ai-agents-shared-memory/utils/write_memory.sh tasks "trigger_pipeline" '{"mode": "full"}'

# Or trigger specific stage
./ai-agents-shared-memory/utils/write_memory.sh tasks "trigger_pipeline" '{"stage": "test"}'
```

#### Monitor Pipeline Status
```bash
# Check pipeline status
./ai-agents-shared-memory/utils/read_memory.sh context pipeline_status

# Check results
./ai-agents-shared-memory/utils/read_memory.sh context pipeline_results
```

#### Example: AI Agent Workflow

```python
from ai-agents-shared-memory.utils.memory_manager import MemoryManager

# Initialize
memory = MemoryManager()

# Check if tests passed
test_results = memory.read("context", "test_results")
if test_results and test_results["data"]["success"]:
    print("✓ Tests passed, proceeding to build...")
    
    # Trigger build
    memory.write(
        "tasks",
        "trigger_build",
        {"image": "myapp", "tag": "v1.0.0"},
        agent="kilocode"
    )
```

---

## Part 3: Pipeline Stages Details

### Stage 1: Testing

**What it does:**
- Runs unit, integration, and e2e tests
- Generates coverage reports
- Fails fast on critical errors

**Frameworks supported:**
- Python: pytest, unittest
- JavaScript: Jest, Mocha
- Go: go test

**Reports:**
- `orchestration/reports/test-report-*.json`
- `orchestration/reports/coverage-*/`

### Stage 2: Code Review

**What it does:**
- Static code analysis
- Security vulnerability scanning
- Quality gate checks

**Tools:**
- **Python**: pylint, flake8, bandit, safety
- **JavaScript**: ESLint, npm audit
- **Go**: golint, go vet

**Reports:**
- `orchestration/reports/review-report-*.json`

### Stage 3: Docker Build

**What it does:**
- Builds optimized Docker images
- Scans for vulnerabilities
- Tags and pushes to registry

**Features:**
- Multi-stage builds
- Layer caching
- Automatic tagging (semantic versioning)
- Trivy security scanning

**Reports:**
- `orchestration/reports/build-report-*.json`

### Stage 4: Coolify Deploy

**What it does:**
- Deploys to Coolify via API
- Performs health checks
- Auto-rollback on failure

**Features:**
- Zero-downtime deployment
- Health check with retries
- Automatic rollback
- Deployment status tracking

**Reports:**
- `orchestration/reports/deploy-report-*.json`

---

## Part 4: Advanced Configuration

### Custom Test Configuration

```json
{
  "testing": {
    "test_types": {
      "unit": {
        "enabled": true,
        "path": "tests/unit",
        "timeout_seconds": 120
      },
      "integration": {
        "enabled": true,
        "path": "tests/integration",
        "timeout_seconds": 300
      },
      "e2e": {
        "enabled": false,
        "path": "tests/e2e",
        "timeout_seconds": 600
      }
    },
    "coverage": {
      "enabled": true,
      "threshold": 80,
      "fail_under_threshold": false
    }
  }
}
```

### Custom Quality Gate

```json
{
  "review": {
    "quality_gate": {
      "enabled": true,
      "rules": {
        "min_code_score": 7.0,
        "max_complexity": 10,
        "no_critical_vulnerabilities": true
      },
      "block_on_failure": false
    }
  }
}
```

### Custom Docker Build

```json
{
  "build": {
    "docker": {
      "file": "Dockerfile",
      "platform": "linux/amd64",
      "multi_stage": true,
      "build_args": {
        "PYTHON_VERSION": "3.11",
        "NODE_VERSION": "18"
      }
    },
    "tagging": {
      "strategy": "semantic",
      "tags": [
        "latest",
        "{version}",
        "{git_commit}",
        "{timestamp}"
      ]
    }
  }
}
```

---

## Part 5: Troubleshooting

### Memory System Issues

**Problem:** "Could not write to shared memory"
**Solution:** Check file permissions:
```bash
chmod -R 755 ai-agents-shared-memory
```

**Problem:** "Index database locked"
**Solution:** Remove stale locks:
```bash
rm -f ai-agents-shared-memory/locks/*.lock
```

### Pipeline Issues

**Problem:** Tests failing
**Solution:** Run tests locally first:
```bash
pytest tests/ -v
```

**Problem:** Docker build failing
**Solution:** Check Dockerfile syntax and build locally:
```bash
docker build -t test:latest .
```

**Problem:** Coolify deployment failing
**Solution:** Verify API credentials:
```bash
curl -H "Authorization: Bearer $COOLIFY_API_TOKEN" $COOLIFY_API_URL/applications
```

### Common Errors

1. **Import errors in Python**: Install dependencies:
```bash
pip install -r orchestration/requirements.txt
```

2. **Docker permission denied**: Add user to docker group:
```bash
sudo usermod -aG docker $USER
newgrp docker
```

3. **Coolify API timeout**: Increase timeout in config:
```json
{
  "deploy": {
    "health_check": {
      "timeout_seconds": 30
    }
  }
}
```

---

## Part 6: Best Practices

### For AI Agents

1. **Always check memory before starting work:**
```python
context = memory.read("context", "current_task")
knowledge = memory.query(category="knowledge", tags=["relevant_topic"])
```

2. **Write progress regularly:**
```python
memory.write("context", "current_progress", {
    "task": "implementing feature X",
    "status": "50% complete",
    "files_modified": ["file1.py", "file2.py"]
}, agent="your_agent_name")
```

3. **Store reusable knowledge:**
```python
memory.write("knowledge", "bug_fix_cors", {
    "problem": "CORS errors on API calls",
    "solution": "Added CORS headers to middleware",
    "code_snippet": "..."
}, agent="your_agent_name", tags=["bug_fix", "cors", "api"])
```

### For Pipeline

1. **Run tests locally before pushing:**
```bash
python orchestration/testing_orchestrator.py
```

2. **Review changes before deploying:**
```bash
python orchestration/review_orchestrator.py
```

3. **Test Docker build locally:**
```bash
docker build -t test:latest .
docker run -p 8080:8080 test:latest
```

4. **Monitor deployments:**
```bash
# Check shared memory for status
./ai-agents-shared-memory/utils/read_memory.sh context pipeline_status
```

---

## Part 7: Examples

### Example 1: AI Agent Collaboration

**Scenario:** Kilocode starts a feature, Roo Code continues it

```python
# Kilocode writes context
memory.write("context", "feature_auth", {
    "status": "in_progress",
    "files": ["auth.py", "middleware.py"],
    "next_steps": ["Add tests", "Update docs"]
}, agent="kilocode")

# Roo Code reads context
context = memory.read("context", "feature_auth")
print(f"Continuing work on: {context['data']['next_steps']}")
```

### Example 2: Automated Pipeline Trigger

**Scenario:** Git hook triggers pipeline on push

```bash
#!/bin/bash
# .git/hooks/post-commit

echo "Triggering CI/CD pipeline..."
python orchestration/main_orchestrator.py --mode full

# Or write to shared memory for async processing
./ai-agents-shared-memory/utils/write_memory.sh tasks "pipeline_trigger" '{"mode": "full", "commit": "'$(git rev-parse HEAD)'"}'
```

### Example 3: Conditional Deployment

**Scenario:** Deploy only if tests pass

```python
# Run tests
test_results = testing_orchestrator.run_all_tests()

if test_results["overall_success"]:
    # Run review
    review_results = review_orchestrator.run_full_review()
    
    if review_results["overall_success"]:
        # Build and deploy
        build_results = build_orchestrator.run_full_build()
        
        if build_results["overall_success"]:
            image_tag = build_results["build"]["tags"][0]
            deploy_orchestrator.run_full_deployment("myapp", image_tag)
```

---

## Support & Resources

- **Memory System**: `ai-agents-shared-memory/README.md`
- **Pipeline**: `orchestration/README.md`
- **Reports**: `orchestration/reports/`
- **Logs**: `orchestration/logs/`

## License

MIT License - Free to use and modify
