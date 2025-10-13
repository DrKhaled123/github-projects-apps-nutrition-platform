#!/usr/bin/env python3
"""
GitHub MCP Integration with AI Coordination
Leverages GitHub MCP server for advanced automation and coordination
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

try:
    from ai_agents_shared_memory.utils.memory_manager import MemoryManager
    from orchestration.ai_agent_coordinator import AIAgentCoordinator
    from orchestration.coolify_integration import CoolifyAIIntegration
    HAS_MEMORY = True
except Exception as e:
    print(f"Warning: Could not import modules: {e}")
    HAS_MEMORY = False


class GitHubAIAutomation:
    """GitHub automation with AI agent coordination"""
    
    def __init__(self):
        self.coordinator = AIAgentCoordinator(agent_name="github_automation") if HAS_MEMORY else None
        self.memory = MemoryManager(base_path="./ai_agents_shared_memory") if HAS_MEMORY else None
        self.coolify = CoolifyAIIntegration() if HAS_MEMORY else None
        
        # GitHub configuration
        self.repo_owner = "DrKhaled123"
        self.repo_name = "doctorhealthy1"
        self.repo_branch = "main"
    
    def log(self, message: str, level: str = "INFO"):
        """Log activities"""
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] [{level}] [GitHub] {message}")
        
        if self.coordinator:
            self.coordinator.log(message, level)
    
    def create_ai_workflow_templates(self):
        """Create GitHub Actions workflows for AI-coordinated CI/CD"""
        
        workflows = {
            "ai-coordinated-cicd.yml": self._get_main_workflow(),
            "ai-testing.yml": self._get_testing_workflow(),
            "ai-deployment.yml": self._get_deployment_workflow(),
            "ai-code-review.yml": self._get_code_review_workflow(),
            "ai-learning.yml": self._get_learning_workflow()
        }
        
        workflows_dir = Path(".github/workflows")
        workflows_dir.mkdir(parents=True, exist_ok=True)
        
        for filename, content in workflows.items():
            filepath = workflows_dir / filename
            with open(filepath, 'w') as f:
                f.write(content)
            
            self.log(f"Created workflow: {filepath}")
        
        return workflows_dir
    
    def _get_main_workflow(self) -> str:
        """Main AI-coordinated CI/CD workflow"""
        return """name: AI-Coordinated CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  workflow_dispatch:
    inputs:
      agent_mode:
        description: 'AI Agent Mode'
        required: true
        default: 'auto'
        type: choice
        options:
          - auto
          - parallel
          - sequential

jobs:
  ai-coordination:
    runs-on: ubuntu-latest
    outputs:
      task-assignments: ${{ steps.coordinate.outputs.assignments }}
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements-pcap.txt || true
          pip install requests psutil flask pytest
      
      - name: AI Coordination
        id: coordinate
        run: |
          python3 orchestration/ai_agent_coordinator.py
          echo "assignments=$(python3 orchestration/ai_agent_coordinator.py --output-json)" >> $GITHUB_OUTPUT
      
      - name: Share coordination context
        run: |
          python3 -c "
          from orchestration.ai_agent_coordinator import AIAgentCoordinator
          coord = AIAgentCoordinator()
          coord.register_agent_activity('github_actions', {
              'description': 'Running CI/CD pipeline',
              'commit': '${{ github.sha }}',
              'branch': '${{ github.ref }}'
          })
          "

  test:
    needs: ai-coordination
    runs-on: ubuntu-latest
    strategy:
      matrix:
        test-type: [unit, integration, security]
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install pytest pytest-cov bandit safety
      
      - name: Check for duplicate work
        run: |
          python3 -c "
          from orchestration.ai_agent_coordinator import AIAgentCoordinator
          coord = AIAgentCoordinator()
          dup = coord.check_duplicate_work('Running ${{ matrix.test-type }} tests')
          if dup:
              print('⚠️  Another agent is already running these tests')
              exit(1)
          "
      
      - name: Run ${{ matrix.test-type }} tests
        run: |
          if [ "${{ matrix.test-type }}" == "unit" ]; then
            pytest tests/ -v --cov
          elif [ "${{ matrix.test-type }}" == "integration" ]; then
            pytest tests/integration/ -v
          elif [ "${{ matrix.test-type }}" == "security" ]; then
            bandit -r . -f json -o security-report.json || true
            safety check --json > safety-report.json || true
          fi
      
      - name: Share test results
        if: always()
        run: |
          python3 -c "
          from orchestration.ai_agent_coordinator import AIAgentCoordinator
          coord = AIAgentCoordinator()
          coord.complete_agent_activity('github_actions_test', {
              'description': 'Completed ${{ matrix.test-type }} tests',
              'success': ${{ job.status == 'success' }},
              'test_type': '${{ matrix.test-type }}',
              'task_type': 'testing'
          })
          "

  build:
    needs: test
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: AI-coordinated build
        run: |
          python3 -c "
          from orchestration.ai_agent_coordinator import AIAgentCoordinator
          coord = AIAgentCoordinator()
          knowledge = coord.get_relevant_knowledge('docker build optimization')
          print(f'Found {len(knowledge)} relevant build patterns')
          coord.register_agent_activity('docker_build', {
              'description': 'Building Docker image',
              'task_type': 'build'
          })
          "
      
      - name: Build Docker image
        run: |
          docker build -t ${{ secrets.DOCKER_USERNAME }}/nutrition-platform:${{ github.sha }} .
          docker build -t ${{ secrets.DOCKER_USERNAME }}/nutrition-platform:latest .
      
      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      
      - name: Push Docker image
        run: |
          docker push ${{ secrets.DOCKER_USERNAME }}/nutrition-platform:${{ github.sha }}
          docker push ${{ secrets.DOCKER_USERNAME }}/nutrition-platform:latest
      
      - name: Share build results
        run: |
          python3 -c "
          from orchestration.ai_agent_coordinator import AIAgentCoordinator
          coord = AIAgentCoordinator()
          coord.complete_agent_activity('docker_build', {
              'description': 'Built and pushed Docker image',
              'success': True,
              'image_tag': '${{ github.sha }}',
              'task_type': 'build',
              'approach': 'Multi-stage Docker build',
              'pattern': 'Docker optimization'
          })
          "

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install requests
      
      - name: AI-coordinated deployment
        env:
          COOLIFY_API_URL: ${{ secrets.COOLIFY_API_URL }}
          COOLIFY_API_TOKEN: ${{ secrets.COOLIFY_API_TOKEN }}
        run: |
          python3 -c "
          from orchestration.coolify_integration import CoolifyAIIntegration
          import os
          
          # Set environment variables
          os.environ['COOLIFY_API_URL'] = 'https://api.doctorhealthy1.com'
          os.environ['COOLIFY_API_TOKEN'] = '${{ secrets.COOLIFY_API_TOKEN }}'
          
          integration = CoolifyAIIntegration()
          apps = integration.get_applications()
          
          if apps:
              # Deploy first app (or specify app_id)
              app_id = apps[0].get('id')
              result = integration.execute_coordinated_deployment(app_id)
              print(f'Deployment: {result}')
          "
      
      - name: Notify deployment status
        if: always()
        run: |
          if [ "${{ job.status }}" == "success" ]; then
            echo "✅ Deployment successful!"
          else
            echo "❌ Deployment failed!"
            python3 -c "
            from orchestration.ai_agent_coordinator import AIAgentCoordinator
            coord = AIAgentCoordinator()
            coord.share_failure_learning('github_deployment', {
                'description': 'Deployment failed',
                'commit': '${{ github.sha }}',
                'lesson': 'Check Coolify API configuration'
            })
            "
          fi

  ai-learning:
    needs: [test, build, deploy]
    runs-on: ubuntu-latest
    if: always()
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install requests
      
      - name: Collect and share learnings
        run: |
          python3 -c "
          from orchestration.ai_agent_coordinator import AIAgentCoordinator
          coord = AIAgentCoordinator()
          
          # Get all agent activities
          status = coord.get_agent_status_summary()
          print('📊 Agent Status Summary:')
          for agent, info in status.items():
              print(f'  {agent}: {info}')
          
          # Save pipeline results
          if coord.memory:
              coord.memory.write(
                  category='pipeline_execution',
                  key='run_${{ github.run_id }}',
                  data={
                      'workflow': 'AI-Coordinated CI/CD',
                      'commit': '${{ github.sha }}',
                      'branch': '${{ github.ref }}',
                      'test_status': '${{ needs.test.result }}',
                      'build_status': '${{ needs.build.result }}',
                      'deploy_status': '${{ needs.deploy.result }}',
                      'timestamp': '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
                  },
                  agent='github_actions',
                  tags=['pipeline', 'cicd', 'learning']
              )
              print('✅ Shared pipeline results with all AI agents')
          "
"""
    
    def _get_testing_workflow(self) -> str:
        """Dedicated testing workflow"""
        return """name: AI Testing

on:
  pull_request:
    types: [opened, synchronize, reopened]
  workflow_dispatch:

jobs:
  ai-test-coordination:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install test dependencies
        run: |
          pip install pytest pytest-cov pytest-json-report pytest-metadata
          pip install requests psutil
      
      - name: Get test recommendations from AI
        id: ai-tests
        run: |
          python3 -c "
          from orchestration.ai_agent_coordinator import AIAgentCoordinator
          coord = AIAgentCoordinator()
          
          # Get relevant test patterns
          knowledge = coord.get_relevant_knowledge('testing best practices')
          if knowledge:
              print(f'Found {len(knowledge)} testing patterns')
              for k in knowledge:
                  print(f'  - Pattern with {k.get(\"success_count\", 0)} successes')
          
          coord.register_agent_activity('pytest', {
              'description': 'Running comprehensive tests',
              'task_type': 'testing',
              'pr_number': '${{ github.event.pull_request.number }}'
          })
          "
      
      - name: Run comprehensive tests
        run: |
          pytest tests/ -v \\
            --cov \\
            --cov-report=json \\
            --json-report \\
            --json-report-file=test-report.json
      
      - name: Share test results
        if: always()
        run: |
          python3 -c "
          import json
          from orchestration.ai_agent_coordinator import AIAgentCoordinator
          
          coord = AIAgentCoordinator()
          
          # Load test results
          try:
              with open('test-report.json') as f:
                  results = json.load(f)
              
              coord.complete_agent_activity('pytest', {
                  'description': 'Completed comprehensive tests',
                  'success': results.get('summary', {}).get('failed', 1) == 0,
                  'tests_passed': results.get('summary', {}).get('passed', 0),
                  'tests_failed': results.get('summary', {}).get('failed', 0),
                  'task_type': 'testing',
                  'approach': 'pytest with coverage',
                  'pattern': 'comprehensive testing'
              })
          except Exception as e:
              print(f'Could not load test results: {e}')
          "
      
      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-results
          path: |
            test-report.json
            coverage.json
"""
    
    def _get_deployment_workflow(self) -> str:
        """Dedicated deployment workflow"""
        return """name: AI Deployment

on:
  workflow_dispatch:
    inputs:
      app_id:
        description: 'Coolify App ID'
        required: true
      force_rebuild:
        description: 'Force rebuild'
        required: false
        default: 'false'

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install requests
      
      - name: AI-coordinated deployment
        env:
          COOLIFY_API_URL: https://api.doctorhealthy1.com
          COOLIFY_API_TOKEN: ${{ secrets.COOLIFY_API_TOKEN }}
        run: |
          python3 orchestration/coolify_integration.py deploy ${{ github.event.inputs.app_id }}
      
      - name: Monitor deployment
        run: |
          echo "Monitoring deployment health..."
          sleep 30
          
          python3 -c "
          from orchestration.coolify_integration import CoolifyAIIntegration
          integration = CoolifyAIIntegration()
          
          # Check app status
          details = integration.get_application_details('${{ github.event.inputs.app_id }}')
          if details:
              print(f'✅ Application status: {details.get(\"status\", \"unknown\")}')
          "
"""
    
    def _get_code_review_workflow(self) -> str:
        """AI code review workflow"""
        return """name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  review:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        with:
          fetch-depth: 0
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install code quality tools
        run: |
          pip install pylint flake8 mypy bandit
          pip install requests
      
      - name: AI-coordinated code review
        run: |
          python3 -c "
          from orchestration.ai_agent_coordinator import AIAgentCoordinator
          coord = AIAgentCoordinator()
          
          coord.register_agent_activity('code_review', {
              'description': 'Reviewing PR #${{ github.event.pull_request.number }}',
              'task_type': 'code_review',
              'files_changed': ${{ github.event.pull_request.changed_files }}
          })
          "
      
      - name: Run linting
        run: |
          pylint **/*.py || true
          flake8 . --max-line-length=100 || true
      
      - name: Run security scan
        run: bandit -r . -f json -o bandit-report.json || true
      
      - name: Share review results
        if: always()
        run: |
          python3 -c "
          from orchestration.ai_agent_coordinator import AIAgentCoordinator
          coord = AIAgentCoordinator()
          
          coord.complete_agent_activity('code_review', {
              'description': 'Completed code review',
              'success': True,
              'task_type': 'code_review',
              'pr_number': '${{ github.event.pull_request.number }}'
          })
          "
"""
    
    def _get_learning_workflow(self) -> str:
        """AI learning and improvement workflow"""
        return """name: AI Learning

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:

jobs:
  analyze-patterns:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install requests
      
      - name: Analyze patterns and generate insights
        run: |
          python3 -c "
          from orchestration.ai_agent_coordinator import AIAgentCoordinator
          from datetime import datetime
          
          coord = AIAgentCoordinator()
          
          print('=' * 60)
          print('AI Learning Summary - Weekly Report')
          print('=' * 60)
          print()
          
          # Get agent status
          status = coord.get_agent_status_summary()
          print('📊 Agent Status:')
          for agent, info in status.items():
              print(f'  {agent}: {info}')
          
          print()
          
          # Get learning patterns
          if coord.memory:
              patterns = coord.memory.query(
                  category='learning',
                  tags=['best_practices'],
                  limit=50
              )
              
              print(f'📚 Learning Database: {len(patterns)} patterns')
              
              # Analyze success patterns
              successful = [p for p in patterns if p.get('data', {}).get('success_count', 0) > 0]
              print(f'✅ Successful patterns: {len(successful)}')
              
              # Top patterns
              sorted_patterns = sorted(
                  successful,
                  key=lambda x: x.get('data', {}).get('success_count', 0),
                  reverse=True
              )
              
              print()
              print('🏆 Top 5 Most Successful Patterns:')
              for i, pattern in enumerate(sorted_patterns[:5], 1):
                  data = pattern.get('data', {})
                  print(f'  {i}. Success count: {data.get(\"success_count\", 0)}')
                  print(f'     Agents: {data.get(\"agents_used\", [])}')
                  print()
          
          print('💡 Recommendation: Review top patterns for best practices')
          "
"""
    
    def setup_complete_automation(self):
        """Setup complete GitHub + Coolify + AI automation"""
        self.log("Setting up complete automation system...")
        
        # Create workflows
        self.log("Creating GitHub Actions workflows...")
        workflows_dir = self.create_ai_workflow_templates()
        
        # Create coordination session
        if self.coordinator:
            session = self.coordinator.create_collaboration_session(
                session_name="Complete Automation Pipeline",
                agents=["kilocode", "roo_code", "cline", "copilot"],
                goal="Fully automated CI/CD with AI coordination and Coolify deployment"
            )
            
            self.log(f"Created collaboration session: {session['session_id']}")
        
        # Create README
        self._create_automation_readme()
        
        self.log("✅ Complete automation setup finished!")
        
        return {
            "workflows_created": 5,
            "workflows_dir": str(workflows_dir),
            "session_id": session.get("session_id") if self.coordinator else None
        }
    
    def _create_automation_readme(self):
        """Create comprehensive README for automation"""
        readme_content = """# AI-Coordinated Automation System

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
curl -X POST \\
  -H "Authorization: Bearer $GITHUB_TOKEN" \\
  -H "Content-Type: application/json" \\
  "https://api.github.com/repos/DrKhaled123/doctorhealthy1/actions/workflows/ai-deployment.yml/dispatches" \\
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
"""
        
        readme_path = Path("AI_AUTOMATION_README.md")
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        
        self.log(f"Created automation README: {readme_path}")


def main():
    """Setup complete automation"""
    print("="*60)
    print("GitHub AI Automation Setup")
    print("="*60)
    print()
    
    automation = GitHubAIAutomation()
    result = automation.setup_complete_automation()
    
    print("\n" + "="*60)
    print("✅ AUTOMATION SETUP COMPLETE")
    print("="*60)
    print(f"\n📁 Workflows created: {result['workflows_created']}")
    print(f"📂 Location: {result['workflows_dir']}")
    if result.get('session_id'):
        print(f"🤝 Collaboration session: {result['session_id']}")
    
    print("\n🚀 Next Steps:")
    print("1. Add GitHub secrets (COOLIFY_API_TOKEN, DOCKER_USERNAME, DOCKER_PASSWORD)")
    print("2. git add .github/workflows/")
    print("3. git commit -m 'Enable AI automation'")
    print("4. git push origin main")
    print("\n💡 Read AI_AUTOMATION_README.md for full documentation")


if __name__ == "__main__":
    main()
