# AI-Coordinated Automation System

## Overview
This system enables multiple AI agents to work together seamlessly, sharing knowledge and avoiding duplicate work.

## Components

### 1. AI Agent Coordinator
- **File**: `orchestration/ai_agent_coordinator.py`
- **Purpose**: Coordinates multiple AI agents
- **Features**:
  - Prevents duplicate work
  - Shares results immediately
  - Learns from failures
  - Assigns tasks to best-suited agents

### 2. Coolify Integration
- **File**: `orchestration/coolify_integration.py`
- **Purpose**: Integrates with Coolify API for deployment
- **Features**:
  - Automated deployments
  - Health monitoring
  - Rollback support

### 3. GitHub Actions Workflows
- **ai-coordinated-cicd.yml**: Main CI/CD pipeline
- **ai-testing.yml**: Comprehensive testing
- **ai-deployment.yml**: Deployment automation
- **ai-code-review.yml**: Automated code review
- **ai-learning.yml**: Pattern analysis and learning

## Quick Start

### 1. Set GitHub Secrets
```bash
# Required secrets
COOLIFY_API_TOKEN=7|Pc76Go9w1ELoKy0GBYb2RpMxWWujefpjEKM30R3Obef9679a
DOCKER_USERNAME=your_username
DOCKER_PASSWORD=your_password
```

### 2. Enable Workflows
```bash
git add .github/workflows/
git commit -m "Enable AI-coordinated automation"
git push origin main
```

### 3. Trigger Manual Deployment
```bash
# Via GitHub UI: Actions → AI Deployment → Run workflow
# Or via API:
curl -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.github.com/repos/DrKhaled123/doctorhealthy1/actions/workflows/ai-deployment.yml/dispatches" \
  -d '{"ref":"main","inputs":{"app_id":"your_app_id"}}'
```

## How It Works

### AI Coordination Flow
1. **Task Registration**: Each agent registers its current activity
2. **Duplicate Detection**: System checks if another agent is doing the same work
3. **Knowledge Sharing**: Successful patterns are shared immediately
4. **Learning**: Failures are logged and shared to avoid repetition
5. **Best Agent Selection**: Tasks are assigned based on agent specialties

### Automation Pipeline
1. **Code Push** → GitHub Actions triggered
2. **AI Coordination** → Tasks distributed to agents
3. **Parallel Testing** → Multiple test types run simultaneously
4. **Docker Build** → Image built with optimizations
5. **Coolify Deployment** → App deployed to production
6. **Health Monitoring** → Deployment verified
7. **Learning Update** → Results shared with all agents

## AI Agent Specialties
- **Kilocode**: Python, backend, API, database
- **Roo Code**: Frontend, React, UI, CSS
- **Cline**: DevOps, deployment, Docker, automation
- **Copilot**: Documentation, testing, code review

## Examples

### Check Agent Status
```python
from orchestration.ai_agent_coordinator import AIAgentCoordinator

coord = AIAgentCoordinator()
status = coord.get_agent_status_summary()
for agent, info in status.items():
    print(f"{agent}: {info['status']} - {info['current_task']}")
```

### Deploy with Coolify
```python
from orchestration.coolify_integration import CoolifyAIIntegration

integration = CoolifyAIIntegration()
result = integration.execute_coordinated_deployment("app_id")
print(result)
```

### Create Collaboration Session
```python
from orchestration.ai_agent_coordinator import AIAgentCoordinator

coord = AIAgentCoordinator()
session = coord.create_collaboration_session(
    session_name="Build Feature X",
    agents=["kilocode", "roo_code"],
    goal="Implement feature X with tests"
)
```

## Monitoring

### View Agent Activities
```bash
cat orchestration/logs/ai_coordination.log
```

### Check Learning Database
```python
from orchestration.ai_agent_coordinator import AIAgentCoordinator

coord = AIAgentCoordinator()
knowledge = coord.get_relevant_knowledge("your_task")
```

## Troubleshooting

### No agents responding
- Check memory system is initialized
- Verify file permissions in `.ai-memory/`

### Deployment failures
- Verify Coolify API token is correct
- Check application ID exists in Coolify
- Review logs in `orchestration/logs/`

### Duplicate work detected
- This is working as designed! Agents are coordinating properly
- Review coordination log to see which agent is handling the task

## Advanced Usage

### Custom Agent Coordination Rules
```python
coord.coordination_rules = {
    "avoid_duplicate_work": True,
    "share_results_immediately": True,
    "learn_from_failures": True,
    "parallel_when_possible": True,
    "coordinate_on_conflicts": True
}
```

### Manual Task Assignment
```python
tasks = [
    {"description": "Build API", "type": "backend"},
    {"description": "Create UI", "type": "frontend"}
]
assignments = coord.coordinate_parallel_tasks(tasks)
```

## Best Practices
1. Always register activities before starting work
2. Complete activities immediately after finishing
3. Share failures to help other agents learn
4. Check for duplicates before starting new work
5. Use collaboration sessions for multi-agent tasks

## Support
- Check logs in `orchestration/logs/`
- Review memory in `.ai-memory/`
- See GitHub Actions runs for pipeline details
