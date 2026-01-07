# Quick Reference: AI Agents + CI/CD Orchestration

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                   AI Agents (Kilocode, Roo, Cline)              │
│                                                                   │
│  Write: context, tasks, knowledge  →  Shared Memory  ← Read      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│              Shared Memory System (File-Based)                    │
│  - context/     (24h)   : Current work state                     │
│  - knowledge/   (∞)     : Persistent learnings                   │
│  - tasks/       (48h)   : Task queue                             │
│  - history/     (7d)    : Action logs                            │
│  - index.db             : SQLite for fast queries                │
│                                                                   │
│  Performance: <1MB RAM, <10ms read, <20ms write                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                  CI/CD Orchestration Pipeline                     │
│                                                                   │
│  1. Testing    → pytest/jest/go test + coverage                  │
│  2. Review     → pylint/bandit/eslint + security                 │
│  3. Build      → Docker multi-stage + Trivy scan                 │
│  4. Deploy     → Coolify API + health check + rollback           │
│                                                                   │
│  Each stage writes progress to Shared Memory                     │
└──────────────────────────────────────────────────────────────────┘
```

## Quick Commands

### Shared Memory Operations

```bash
# Write to shared memory
python -c "
from ai-agents-shared-memory.utils.memory_manager import MemoryManager
m = MemoryManager()
m.write('context', 'task_1', {'status': 'in_progress'}, agent='kilocode')
"

# Read from shared memory
python -c "
from ai-agents-shared-memory.utils.memory_manager import MemoryManager
m = MemoryManager()
print(m.read('context', 'task_1'))
"

# Query by tags
python -c "
from ai-agents-shared-memory.utils.memory_manager import MemoryManager
m = MemoryManager()
results = m.query(category='knowledge', tags=['bug_fix'])
for r in results: print(r['key'], r['data'])
"

# Cleanup old entries
python -c "
from ai-agents-shared-memory.utils.memory_manager import MemoryManager
m = MemoryManager()
m.cleanup()
"
```

### Pipeline Operations

```bash
# Run full pipeline
python orchestration/main_orchestrator.py --mode full

# Run specific stage
python orchestration/main_orchestrator.py --stage test
python orchestration/main_orchestrator.py --stage review
python orchestration/main_orchestrator.py --stage build
python orchestration/main_orchestrator.py --stage deploy

# Run multiple stages
python orchestration/main_orchestrator.py --stages test review build

# Individual orchestrators
python orchestration/testing_orchestrator.py --type all
python orchestration/review_orchestrator.py
python orchestration/build_orchestrator.py
python orchestration/deploy_orchestrator.py --image myapp --tag v1.0.0
```

### Integration Commands

```bash
# Trigger pipeline from AI agent
./ai-agents-shared-memory/utils/write_memory.sh tasks "pipeline_trigger" '{"mode": "full"}'

# Check pipeline status
./ai-agents-shared-memory/utils/read_memory.sh context pipeline_status

# Get test results
./ai-agents-shared-memory/utils/read_memory.sh context test_results

# Get deployment status
./ai-agents-shared-memory/utils/read_memory.sh context deploy_results
```

## Environment Variables

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

## Configuration Files

```
Project Root/
├── ai-agents-shared-memory/
│   ├── .memory-config.json          # Memory system config
│   └── utils/
│       ├── memory_manager.py        # Core memory manager
│       ├── write_memory.sh          # CLI write utility
│       └── read_memory.sh           # CLI read utility
│
├── orchestration/
│   ├── orchestration-config.json    # Pipeline config
│   ├── main_orchestrator.py         # Main coordinator
│   ├── testing_orchestrator.py      # Test runner
│   ├── review_orchestrator.py       # Code reviewer
│   ├── build_orchestrator.py        # Docker builder
│   ├── deploy_orchestrator.py       # Coolify deployer
│   ├── requirements.txt             # Python deps
│   ├── reports/                     # Generated reports
│   └── logs/                        # Logs
│
├── COMPLETE-SETUP-GUIDE.md          # Full documentation
└── quick-start.sh                   # Setup script
```

## AI Agent Integration Examples

### Python API (Direct)

```python
from ai-agents-shared-memory.utils.memory_manager import MemoryManager

# Initialize
memory = MemoryManager()

# Agent writes context
memory.write(
    category="context",
    key="current_feature",
    data={
        "feature": "user authentication",
        "status": "in_progress",
        "files": ["auth.py", "middleware.py"],
        "next_steps": ["Add tests", "Update docs"]
    },
    agent="kilocode",
    tags=["authentication", "feature"]
)

# Another agent reads context
context = memory.read("context", "current_feature")
print(f"Working on: {context['data']['feature']}")
print(f"Status: {context['data']['status']}")
print(f"Next: {context['data']['next_steps']}")

# Store knowledge for future reference
memory.write(
    category="knowledge",
    key="cors_fix_2025",
    data={
        "problem": "CORS errors blocking API calls",
        "solution": "Added CORS middleware with proper headers",
        "code": "app.use(cors({origin: '*', credentials: true}))"
    },
    agent="roocode",
    tags=["bug_fix", "cors", "api"]
)

# Query knowledge
bugs_fixed = memory.query(category="knowledge", tags=["bug_fix"])
for bug in bugs_fixed:
    print(f"Bug: {bug['data']['problem']}")
    print(f"Solution: {bug['data']['solution']}")
```

### Shell Scripts (Simple)

```bash
#!/bin/bash
# AI agent writes task

./ai-agents-shared-memory/utils/write_memory.sh \
  tasks \
  "deploy_v1.0.0" \
  '{"action": "deploy", "version": "1.0.0", "environment": "production"}'

# AI agent reads task
TASK=$(./ai-agents-shared-memory/utils/read_memory.sh tasks deploy_v1.0.0)
echo "Task details: $TASK"
```

## Pipeline Stage Details

### 1. Testing Stage
- **Auto-detects**: pytest, jest, go test
- **Runs**: unit, integration, e2e tests
- **Generates**: Coverage reports (<80% threshold configurable)
- **Output**: `orchestration/reports/test-report-*.json`

### 2. Review Stage
- **Python**: pylint (code quality), bandit (security), safety (dependencies)
- **JavaScript**: eslint (linting), npm audit (security)
- **Quality Gate**: Configurable thresholds (min score, max complexity)
- **Output**: `orchestration/reports/review-report-*.json`

### 3. Build Stage
- **Docker**: Multi-stage builds with caching
- **Tagging**: Semantic versioning (latest, v1.0.0, git-commit, timestamp)
- **Scanning**: Trivy for vulnerabilities
- **Registry**: Auto-push to Docker Hub or custom registry
- **Output**: `orchestration/reports/build-report-*.json`

### 4. Deploy Stage
- **Coolify API**: Triggers deployment via REST API
- **Health Check**: Configurable endpoint with retries
- **Rollback**: Automatic on failure
- **Monitoring**: Real-time status tracking
- **Output**: `orchestration/reports/deploy-report-*.json`

## Troubleshooting

### Memory System
```bash
# Check memory stats
python -c "
from ai-agents-shared-memory.utils.memory_manager import MemoryManager
print(MemoryManager().get_stats())
"

# Clear old locks
rm -f ai-agents-shared-memory/locks/*.lock

# Reset memory (careful!)
rm -rf ai-agents-shared-memory/shared/*
```

### Pipeline
```bash
# View latest test report
cat orchestration/reports/test-report-*.json | jq '.overall_success'

# View latest review report
cat orchestration/reports/review-report-*.json | jq '.quality_gate'

# View latest build report
cat orchestration/reports/build-report-*.json | jq '.build.tags'

# View latest deploy report
cat orchestration/reports/deploy-report-*.json | jq '.overall_success'

# Check logs
tail -f orchestration/logs/orchestrator.log
```

## Performance Metrics

### Shared Memory System
- **Memory Footprint**: <1MB
- **Read Latency**: <10ms
- **Write Latency**: <20ms
- **Concurrent Reads**: 100+
- **Storage**: Disk-based (no RAM overhead)

### Pipeline
- **Testing**: 2-5 minutes (depends on test suite)
- **Review**: 1-3 minutes
- **Build**: 3-10 minutes (depends on image size)
- **Deploy**: 2-5 minutes (includes health checks)
- **Total**: ~10-25 minutes for full pipeline

## Support

- **Full Guide**: `COMPLETE-SETUP-GUIDE.md`
- **Memory README**: `ai-agents-shared-memory/README.md`
- **Pipeline README**: `orchestration/README.md`
- **Setup Script**: `./quick-start.sh`
