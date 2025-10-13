#!/usr/bin/env python3
"""
Coolify Integration with AI Agent Coordination
Connects Coolify API with AI agents for automated deployment
"""

import json
import os
import sys
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

try:
    from ai_agents_shared_memory.utils.memory_manager import MemoryManager
    from orchestration.ai_agent_coordinator import AIAgentCoordinator
    HAS_MEMORY = True
except Exception as e:
    print(f"Warning: Could not import modules: {e}")
    HAS_MEMORY = False


class CoolifyAIIntegration:
    """Integrates Coolify API with AI agent coordination"""
    
    def __init__(self):
        # Coolify configuration - SECURE: No hardcoded fallbacks
        self.api_url = os.environ.get("COOLIFY_API_URL")
        self.api_token = os.environ.get("COOLIFY_API_TOKEN")

        # Security validation
        if not self.api_url:
            raise ValueError("COOLIFY_API_URL environment variable is required")
        if not self.api_token:
            raise ValueError("COOLIFY_API_TOKEN environment variable is required")

        # Validate API token format (Coolify tokens start with version|...)
        if not self.api_token.startswith("7|") or len(self.api_token) < 50:
            raise ValueError("Invalid COOLIFY_API_TOKEN format")

        # Validate API URL format
        if not self.api_url.startswith("https://"):
            raise ValueError("COOLIFY_API_URL must use HTTPS")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        self.coordinator = AIAgentCoordinator(agent_name="coolify_integration") if HAS_MEMORY else None
        self.memory = MemoryManager(base_path="./ai_agents_shared_memory") if HAS_MEMORY else None
    
    def log(self, message: str, level: str = "INFO"):
        """Log integration activities"""
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] [{level}] [Coolify] {message}")
        
        if self.coordinator:
            self.coordinator.log(message, level)
    
    def get_applications(self) -> List[Dict]:
        """Get all applications from Coolify"""
        try:
            response = requests.get(
                f"{self.api_url}/api/v1/applications",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                apps = response.json()
                self.log(f"Retrieved {len(apps)} applications from Coolify")
                return apps
            else:
                self.log(f"Failed to get applications: {response.status_code}", "ERROR")
                return []
        
        except Exception as e:
            self.log(f"Error getting applications: {e}", "ERROR")
            return []
    
    def get_application_details(self, app_id: str) -> Optional[Dict]:
        """Get detailed information about an application"""
        try:
            response = requests.get(
                f"{self.api_url}/api/v1/applications/{app_id}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.log(f"Failed to get app details: {response.status_code}", "ERROR")
                return None
        
        except Exception as e:
            self.log(f"Error getting app details: {e}", "ERROR")
            return None
    
    def trigger_deployment(self, app_id: str, force_rebuild: bool = False) -> Dict:
        """Trigger deployment for an application"""
        if self.coordinator:
            # Register activity
            self.coordinator.register_agent_activity("coolify_deployment", {
                "description": f"Deploying application {app_id}",
                "task_type": "deployment",
                "app_id": app_id
            })
        
        try:
            payload = {
                "force_rebuild": force_rebuild
            }
            
            response = requests.post(
                f"{self.api_url}/api/v1/applications/{app_id}/deploy",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                self.log(f"✅ Deployment triggered for {app_id}")
                
                if self.coordinator:
                    self.coordinator.complete_agent_activity("coolify_deployment", {
                        "description": f"Deployed application {app_id}",
                        "success": True,
                        "deployment_id": result.get("deployment_id"),
                        "task_type": "deployment"
                    })
                
                return {
                    "success": True,
                    "deployment_id": result.get("deployment_id"),
                    "status": result.get("status", "pending")
                }
            else:
                self.log(f"❌ Deployment failed: {response.status_code}", "ERROR")
                
                if self.coordinator:
                    self.coordinator.share_failure_learning("coolify_deployment", {
                        "description": f"Deployment failed for {app_id}",
                        "error_code": response.status_code,
                        "lesson": "Check API permissions and app configuration"
                    })
                
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                }
        
        except Exception as e:
            self.log(f"❌ Deployment error: {e}", "ERROR")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_deployment_status(self, app_id: str, deployment_id: str) -> Dict:
        """Get status of a deployment"""
        try:
            response = requests.get(
                f"{self.api_url}/api/v1/applications/{app_id}/deployments/{deployment_id}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "unknown", "error": f"HTTP {response.status_code}"}
        
        except Exception as e:
            self.log(f"Error getting deployment status: {e}", "ERROR")
            return {"status": "error", "error": str(e)}
    
    def wait_for_deployment(self, app_id: str, deployment_id: str, timeout: int = 600) -> bool:
        """Wait for deployment to complete"""
        import time
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_deployment_status(app_id, deployment_id)
            
            current_status = status.get("status", "unknown")
            self.log(f"Deployment status: {current_status}")
            
            if current_status in ["success", "completed", "running"]:
                self.log("✅ Deployment completed successfully")
                return True
            elif current_status in ["failed", "error"]:
                self.log("❌ Deployment failed", "ERROR")
                return False
            
            time.sleep(10)  # Check every 10 seconds
        
        self.log("⏱️ Deployment timeout", "WARNING")
        return False
    
    def create_github_deployment_workflow(self, repo_owner: str, repo_name: str, app_id: str):
        """Create a workflow that deploys to Coolify on git push"""
        workflow_content = f"""name: Deploy to Coolify

on:
  push:
    branches:
      - main
      - master
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Trigger Coolify Deployment
        run: |
          curl -X POST \\
            -H "Authorization: Bearer ${{{{ secrets.COOLIFY_API_TOKEN }}}}" \\
            -H "Content-Type: application/json" \\
            "{self.api_url}/api/v1/applications/{app_id}/deploy" \\
            -d '{{"force_rebuild": false}}'
      
      - name: Notify Success
        if: success()
        run: echo "✅ Deployment triggered successfully!"
      
      - name: Notify Failure
        if: failure()
        run: echo "❌ Deployment trigger failed!"
"""
        
        workflow_path = Path(".github/workflows/coolify-deploy.yml")
        workflow_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(workflow_path, 'w') as f:
            f.write(workflow_content)
        
        self.log(f"Created GitHub workflow at {workflow_path}")
        
        return workflow_path
    
    def setup_ai_coordinated_deployment(self):
        """Setup deployment pipeline coordinated by AI agents"""
        if not self.coordinator:
            self.log("AI Coordinator not available", "WARNING")
            return
        
        # Create collaboration session
        session = self.coordinator.create_collaboration_session(
            session_name="Coolify Deployment Pipeline",
            agents=["kilocode", "cline", "copilot"],
            goal="Automate deployment to Coolify with AI coordination"
        )
        
        # Define tasks
        tasks = [
            {
                "description": "Run tests before deployment",
                "type": "testing",
                "dependencies": [],
                "assigned_to": "copilot"
            },
            {
                "description": "Build Docker image",
                "type": "build",
                "dependencies": ["Run tests before deployment"],
                "assigned_to": "cline"
            },
            {
                "description": "Trigger Coolify deployment",
                "type": "deployment",
                "dependencies": ["Build Docker image"],
                "assigned_to": "coolify_integration"
            },
            {
                "description": "Monitor deployment health",
                "type": "monitoring",
                "dependencies": ["Trigger Coolify deployment"],
                "assigned_to": "cline"
            }
        ]
        
        # Store tasks in memory
        if self.memory:
            self.memory.write(
                category="deployment_pipeline",
                key=session["session_id"],
                data={
                    "session": session,
                    "tasks": tasks,
                    "status": "ready"
                },
                agent="coolify_integration",
                tags=["deployment", "pipeline", "coolify"]
            )
        
        self.log(f"Setup AI-coordinated deployment pipeline: {session['session_id']}")
        return session
    
    def execute_coordinated_deployment(self, app_id: str):
        """Execute deployment with AI agent coordination"""
        if not self.coordinator:
            return self.trigger_deployment(app_id)
        
        # Check if any agent is already deploying
        duplicate = self.coordinator.check_duplicate_work(f"Deploying {app_id}")
        if duplicate:
            self.log("Another agent is already deploying this app", "WARNING")
            return {"success": False, "reason": "Duplicate deployment in progress"}
        
        # Get relevant knowledge from past deployments
        knowledge = self.coordinator.get_relevant_knowledge("deployment")
        if knowledge:
            self.log(f"Found {len(knowledge)} relevant deployment patterns")
        
        # Trigger deployment
        result = self.trigger_deployment(app_id)
        
        # Share results with other agents
        if result.get("success"):
            if self.memory:
                self.memory.write(
                    category="deployment_success",
                    key=f"deploy_{app_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    data={
                        "app_id": app_id,
                        "deployment_id": result.get("deployment_id"),
                        "timestamp": datetime.now().isoformat(),
                        "success": True
                    },
                    agent="coolify_integration",
                    tags=["deployment", "success", "coolify", "shared_learning"]
                )
        
        return result


def main():
    """Demo and testing"""
    print("="*60)
    print("Coolify AI Integration")
    print("="*60)
    print()
    
    integration = CoolifyAIIntegration()
    
    # Get applications
    print("📱 Fetching applications...")
    apps = integration.get_applications()
    
    if apps:
        print(f"\n✅ Found {len(apps)} applications")
        for app in apps[:5]:  # Show first 5
            print(f"  - {app.get('name', 'Unknown')}: {app.get('id', 'N/A')}")
    else:
        print("\n⚠️  No applications found or API error")
    
    # Setup AI-coordinated deployment
    print("\n🤖 Setting up AI-coordinated deployment...")
    session = integration.setup_ai_coordinated_deployment()
    if session:
        print(f"✅ Created session: {session.get('session_id')}")
    
    print("\n💡 To deploy, run:")
    print("  python3 orchestration/coolify_integration.py deploy <app_id>")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "deploy":
        if len(sys.argv) > 2:
            app_id = sys.argv[2]
            integration = CoolifyAIIntegration()
            result = integration.execute_coordinated_deployment(app_id)
            print(f"\n{'✅' if result.get('success') else '❌'} Deployment result: {json.dumps(result, indent=2)}")
        else:
            print("Usage: python3 coolify_integration.py deploy <app_id>")
    else:
        main()
