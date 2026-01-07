#!/bin/bash
# Quick Reference: AI Agent Coordination Commands

cat << 'EOF'
╔════════════════════════════════════════════════════════════════╗
║       AI AGENT COORDINATION - QUICK REFERENCE                  ║
╚════════════════════════════════════════════════════════════════╝

📋 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Test AI coordinator (activity, duplicate detection, learning)
python3 orchestration/ai_agent_coordinator.py

# Test Coolify integration (list apps, test API)
python3 orchestration/coolify_integration.py

# Setup GitHub automation (create workflows)
python3 orchestration/github_ai_automation.py


🚀 DEPLOYMENT COMMANDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Deploy to Coolify with AI coordination
python3 orchestration/coolify_integration.py deploy <app_id>

# Get application IDs
python3 orchestration/coolify_integration.py


📊 MONITORING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Watch coordination in real-time
tail -f orchestration/logs/ai_coordination.log

# Check agent status
python3 -c "
from orchestration.ai_agent_coordinator import AIAgentCoordinator
coord = AIAgentCoordinator()
status = coord.get_agent_status_summary()
for agent, info in status.items():
    print(f'{agent}: {info[\"status\"]} - {info[\"current_task\"]}')
"

# View learning patterns
python3 -c "
from orchestration.ai_agent_coordinator import AIAgentCoordinator
coord = AIAgentCoordinator()
if coord.memory:
    patterns = coord.memory.query(category='learning', limit=10)
    print(f'Learning patterns: {len(patterns)}')
"


🔧 GITHUB SETUP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 1. Add secrets to GitHub:
#    Settings → Secrets → Actions → New secret
#    - COOLIFY_API_TOKEN: 7|Pc76Go9w1ELoKy0GBYb2RpMxWWujefpjEKM30R3Obef9679a
#    - DOCKER_USERNAME: your_username
#    - DOCKER_PASSWORD: your_password

# 2. Commit and push workflows
git add .github/workflows/
git add orchestration/*.py
git add AI_*.md
git commit -m "🤖 Enable AI agent coordination"
git push origin main

# 3. View workflows
# https://github.com/DrKhaled123/doctorhealthy1/actions


💻 PYTHON API EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Example: Register activity
python3 << 'PYTHON'
from orchestration.ai_agent_coordinator import AIAgentCoordinator

coord = AIAgentCoordinator(agent_name="my_agent")

coord.register_agent_activity("kilocode", {
    "description": "Building authentication system",
    "task_type": "backend"
})
print("✅ Activity registered")
PYTHON

# Example: Check duplicate work
python3 << 'PYTHON'
from orchestration.ai_agent_coordinator import AIAgentCoordinator

coord = AIAgentCoordinator()
duplicate = coord.check_duplicate_work("authentication")

if duplicate:
    print(f"⚠️  Agent {duplicate['agent']} is already working on this")
else:
    print("✅ No duplicate work")
PYTHON

# Example: Get knowledge
python3 << 'PYTHON'
from orchestration.ai_agent_coordinator import AIAgentCoordinator

coord = AIAgentCoordinator()
knowledge = coord.get_relevant_knowledge("API development")

print(f"📚 Found {len(knowledge)} relevant patterns")
PYTHON

# Example: Deploy to Coolify
python3 << 'PYTHON'
from orchestration.coolify_integration import CoolifyAIIntegration

integration = CoolifyAIIntegration()
apps = integration.get_applications()

if apps:
    app_id = apps[0].get('id')
    result = integration.execute_coordinated_deployment(app_id)
    print(f"{'✅' if result['success'] else '❌'} Deployment: {result}")
PYTHON


📁 FILE LOCATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Core Systems:
  orchestration/ai_agent_coordinator.py    - Main coordinator
  orchestration/coolify_integration.py     - Coolify API
  orchestration/github_ai_automation.py    - GitHub automation

Workflows:
  .github/workflows/ai-coordinated-cicd.yml  - Main CI/CD
  .github/workflows/ai-testing.yml           - Testing
  .github/workflows/ai-deployment.yml        - Deployment
  .github/workflows/ai-code-review.yml       - Code review
  .github/workflows/ai-learning.yml          - Learning

Documentation:
  AI_COORDINATION_COMPLETE.md   - Complete guide
  AI_AUTOMATION_README.md       - Automation docs

Logs & Data:
  orchestration/logs/ai_coordination.log  - Activity log
  ai_agents_shared_memory/shared/         - Shared memory


🎯 COMMON TASKS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# See what agents are doing
python3 orchestration/ai_agent_coordinator.py

# List Coolify apps
python3 orchestration/coolify_integration.py

# Deploy specific app
python3 orchestration/coolify_integration.py deploy <app_id>

# Check coordination logs
cat orchestration/logs/ai_coordination.log

# Watch live activity
tail -f orchestration/logs/ai_coordination.log


🔍 TROUBLESHOOTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Problem: Memory system not working
ls -la ai_agents_shared_memory/shared/
# Should see: agent_activity, learning, failures, etc.

# Problem: Coolify not connecting
curl -H "Authorization: Bearer 7|Pc76Go9w1ELoKy0GBYb2RpMxWWujefpjEKM30R3Obef9679a" \
     https://api.doctorhealthy1.com/api/v1/applications

# Problem: Workflows not running
# Check: GitHub Settings → Actions → Enable workflows


📚 DOCUMENTATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Full guide:          AI_COORDINATION_COMPLETE.md
Automation setup:    AI_AUTOMATION_README.md
Production ready:    PRODUCTION_READY_SUMMARY.md
Deployment guide:    DEPLOYMENT_COMPLETE.md


🎓 AGENT SPECIALTIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Kilocode:  Python, Backend, API, Database
Roo Code:  Frontend, React, UI, CSS
Cline:     DevOps, Deployment, Docker, Automation
Copilot:   Documentation, Testing, Code Review


💡 TIPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Always register activities before starting work
✓ Check for duplicates to avoid wasted effort
✓ Complete activities to share results
✓ Share failures so others can learn
✓ Use collaboration sessions for multi-agent work
✓ Review learning patterns regularly


🆘 SUPPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Logs:     orchestration/logs/ai_coordination.log
Memory:   ai_agents_shared_memory/shared/
Actions:  https://github.com/DrKhaled123/doctorhealthy1/actions

EOF
