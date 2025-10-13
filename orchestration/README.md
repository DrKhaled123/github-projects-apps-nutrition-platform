# CI/CD Orchestration Pipeline

## Overview
Automated orchestration system for testing, code review, Docker image building, and Coolify deployment.

## Pipeline Flow

```
┌──────────────┐
│ Code Changes │
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│  1. Testing Phase    │
│  - Unit Tests        │
│  - Integration Tests │
│  - E2E Tests         │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  2. Review Phase     │
│  - Static Analysis   │
│  - Security Scan     │
│  - Quality Metrics   │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  3. Build Phase      │
│  - Docker Build      │
│  - Image Optimization│
│  - Tag & Push        │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  4. Deploy Phase     │
│  - Coolify Deploy    │
│  - Health Check      │
│  - Rollback on Fail  │
└──────────────────────┘
```

## Components

### 1. Testing Orchestrator (`orchestration/testing_orchestrator.py`)
- Runs all test suites
- Generates coverage reports
- Fails fast on critical errors

### 2. Review Orchestrator (`orchestration/review_orchestrator.py`)
- Static code analysis (pylint, flake8)
- Security scanning (bandit, safety)
- Quality metrics (complexity, maintainability)

### 3. Build Orchestrator (`orchestration/build_orchestrator.py`)
- Docker image building
- Multi-stage optimization
- Image tagging strategy
- Registry push

### 4. Deploy Orchestrator (`orchestration/deploy_orchestrator.py`)
- Coolify API integration
- Health checks
- Automatic rollback
- Notification system

### 5. Main Orchestrator (`orchestration/main_orchestrator.py`)
- Coordinates all phases
- Handles failures gracefully
- Provides real-time feedback
- Integrates with shared memory

## Configuration

### orchestration-config.json
```json
{
  "pipeline": {
    "stages": ["test", "review", "build", "deploy"],
    "fail_fast": true,
    "parallel_execution": false
  },
  "testing": {
    "frameworks": ["pytest", "unittest"],
    "coverage_threshold": 80,
    "timeout_seconds": 300
  },
  "review": {
    "tools": ["pylint", "bandit", "safety"],
    "quality_gate": {
      "min_score": 7.0,
      "max_complexity": 10
    }
  },
  "build": {
    "platform": "linux/amd64",
    "cache": true,
    "multi_stage": true
  },
  "deploy": {
    "coolify_api": "https://your-coolify-instance.com/api",
    "health_check_retries": 5,
    "rollback_enabled": true
  }
}
```

## Usage

### Full Pipeline
```bash
python orchestration/main_orchestrator.py --mode full
```

### Individual Stages
```bash
python orchestration/main_orchestrator.py --stage test
python orchestration/main_orchestrator.py --stage review
python orchestration/main_orchestrator.py --stage build
python orchestration/main_orchestrator.py --stage deploy
```

### With AI Agent Integration
```bash
# Trigger from any AI agent
./ai-agents-shared-memory/utils/write_memory.sh tasks "trigger_pipeline" "full"

# Monitor progress
./ai-agents-shared-memory/utils/read_memory.sh context "pipeline_status"
```

## Reports

All orchestration runs generate reports in:
- `orchestration/reports/test-report-{timestamp}.json`
- `orchestration/reports/review-report-{timestamp}.json`
- `orchestration/reports/build-report-{timestamp}.json`
- `orchestration/reports/deploy-report-{timestamp}.json`

## Integration with AI Agents

The orchestration system automatically:
1. Reads tasks from shared memory
2. Executes pipeline stages
3. Writes progress to shared memory
4. Notifies agents of completion/failures

## Error Handling

- **Test Failures**: Pipeline stops, reports errors
- **Review Failures**: Warning mode or stop based on severity
- **Build Failures**: Retries 3 times, then fails
- **Deploy Failures**: Automatic rollback to previous version

## Monitoring

Real-time monitoring dashboard available at:
```bash
python orchestration/monitoring_dashboard.py
# Access at http://localhost:8080
```
