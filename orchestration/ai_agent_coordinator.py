#!/usr/bin/env python3
"""
AI Agent Coordination System
Enables all AI agents to work together, share results, and learn from each other
"""

import json
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

try:
    from ai_agents_shared_memory.utils.memory_manager import MemoryManager
    HAS_MEMORY = True
except Exception as e:
    print(f"Warning: Memory manager not available: {e}")
    HAS_MEMORY = False


class AIAgentCoordinator:
    """Coordinates multiple AI agents to work together and share knowledge"""
    
    AGENTS = ["kilocode", "roo_code", "cline", "copilot"]
    
    def __init__(self, agent_name: str = "coordinator"):
        self.agent_name = agent_name
        self.memory = MemoryManager(base_path="./ai_agents_shared_memory") if HAS_MEMORY else None
        self.logs_dir = Path("orchestration/logs")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.coordination_log = self.logs_dir / "ai_coordination.log"
        
        # Agent activity tracking
        self.agent_activities = {}
        self.task_assignments = {}
        self.learning_database = {}
        
        # Coordination rules
        self.coordination_rules = {
            "avoid_duplicate_work": True,
            "share_results_immediately": True,
            "learn_from_failures": True,
            "parallel_when_possible": True,
            "coordinate_on_conflicts": True
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Log coordination activities"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{level}] [{self.agent_name}] {message}\n"
        
        with open(self.coordination_log, 'a') as f:
            f.write(log_entry)
        
        print(log_entry.strip())
    
    def register_agent_activity(self, agent_name: str, activity: Dict):
        """Register what an agent is currently doing"""
        if not self.memory:
            return
        
        activity_data = {
            "agent": agent_name,
            "activity": activity,
            "timestamp": datetime.now().isoformat(),
            "status": "active"
        }
        
        # Store in memory
        self.memory.write(
            category="agent_activity",
            key=f"{agent_name}_current",
            data=activity_data,
            agent=agent_name,
            tags=["coordination", "activity"]
        )
        
        self.agent_activities[agent_name] = activity_data
        self.log(f"Agent {agent_name} started: {activity.get('description', 'Unknown task')}")
    
    def complete_agent_activity(self, agent_name: str, result: Dict):
        """Mark agent activity as complete and share results"""
        if not self.memory:
            return
        
        result_data = {
            "agent": agent_name,
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "success": result.get("success", False)
        }
        
        # Store result in memory for other agents
        self.memory.write(
            category="agent_results",
            key=f"{agent_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            data=result_data,
            agent=agent_name,
            tags=["coordination", "result", "shared_learning"]
        )
        
        # Learn from this execution
        if result.get("success"):
            self._add_to_learning_database(agent_name, result)
        
        self.log(f"Agent {agent_name} completed: {result.get('description', 'Task')}")
        self.log(f"Result: {'SUCCESS' if result.get('success') else 'FAILED'}")
    
    def _add_to_learning_database(self, agent_name: str, result: Dict):
        """Add successful patterns to learning database"""
        pattern_key = self._generate_pattern_key(result)
        
        if pattern_key not in self.learning_database:
            self.learning_database[pattern_key] = {
                "pattern": result.get("pattern", ""),
                "success_count": 0,
                "agents_used": [],
                "best_practices": []
            }
        
        self.learning_database[pattern_key]["success_count"] += 1
        if agent_name not in self.learning_database[pattern_key]["agents_used"]:
            self.learning_database[pattern_key]["agents_used"].append(agent_name)
        
        # Store in memory
        if self.memory:
            self.memory.write(
                category="learning",
                key=pattern_key,
                data=self.learning_database[pattern_key],
                agent="coordinator",
                tags=["learning", "best_practices"]
            )
    
    def _generate_pattern_key(self, result: Dict) -> str:
        """Generate unique key for a pattern"""
        pattern_str = json.dumps({
            "task_type": result.get("task_type", "unknown"),
            "approach": result.get("approach", "unknown")
        }, sort_keys=True)
        
        return hashlib.md5(pattern_str.encode()).hexdigest()[:12]
    
    def check_duplicate_work(self, task_description: str) -> Optional[Dict]:
        """Check if another agent is already working on this task"""
        if not self.memory:
            return None
        
        # Query recent activities
        recent_activities = self.memory.query(
            category="agent_activity",
            tags=["coordination", "activity"],
            limit=20
        )
        
        for activity in recent_activities:
            data = activity.get("data", {})
            if data.get("status") == "active":
                other_desc = data.get("activity", {}).get("description", "")
                
                # Simple similarity check (can be improved with NLP)
                if self._is_similar_task(task_description, other_desc):
                    self.log(f"DUPLICATE WORK DETECTED: {data.get('agent')} is already working on similar task", "WARNING")
                    return data
        
        return None
    
    def _is_similar_task(self, task1: str, task2: str) -> bool:
        """Check if two task descriptions are similar"""
        # Simple word overlap check
        words1 = set(task1.lower().split())
        words2 = set(task2.lower().split())
        
        overlap = len(words1 & words2)
        min_length = min(len(words1), len(words2))
        
        return overlap > 0 and overlap / min_length > 0.5
    
    def get_relevant_knowledge(self, task_description: str) -> List[Dict]:
        """Get relevant knowledge from other agents' past work"""
        if not self.memory:
            return []
        
        # Query learning database
        results = self.memory.query(
            category="learning",
            tags=["learning", "best_practices"],
            limit=10
        )
        
        relevant = []
        for result in results:
            data = result.get("data", {})
            if data.get("success_count", 0) > 0:
                relevant.append(data)
        
        self.log(f"Found {len(relevant)} relevant knowledge items for task")
        return relevant
    
    def assign_task_to_best_agent(self, task: Dict) -> str:
        """Determine which agent is best suited for a task"""
        task_type = task.get("type", "general")
        
        # Agent specializations
        agent_specialties = {
            "kilocode": ["python", "backend", "api", "database"],
            "roo_code": ["frontend", "react", "ui", "css"],
            "cline": ["devops", "deployment", "docker", "automation"],
            "copilot": ["documentation", "testing", "code_review"]
        }
        
        # Score each agent
        scores = {}
        for agent, specialties in agent_specialties.items():
            score = 0
            for specialty in specialties:
                if specialty in task_type.lower():
                    score += 1
            scores[agent] = score
        
        # Get agent with highest score
        best_agent = max(scores.items(), key=lambda x: x[1])[0]
        
        self.log(f"Assigned task '{task.get('description')}' to {best_agent}")
        return best_agent
    
    def coordinate_parallel_tasks(self, tasks: List[Dict]) -> Dict[str, List[Dict]]:
        """Coordinate multiple tasks to run in parallel without conflicts"""
        all_agents = self.AGENTS + ["coordinator"]
        task_assignments = {agent: [] for agent in all_agents}
        
        # Group tasks by dependency
        for task in tasks:
            # Check for dependencies
            dependencies = task.get("dependencies", [])
            
            if not dependencies:
                # Can run in parallel
                best_agent = self.assign_task_to_best_agent(task)
                task_assignments[best_agent].append(task)
            else:
                # Must wait for dependencies
                task["status"] = "waiting"
                # Assign to coordinator for sequencing
                task_assignments["coordinator"].append(task)
        
        self.log(f"Coordinated {len(tasks)} tasks across {len(self.AGENTS)} agents")
        return task_assignments
    
    def share_failure_learning(self, agent_name: str, failure: Dict):
        """Share failure information so other agents can avoid it"""
        if not self.memory:
            return
        
        failure_data = {
            "agent": agent_name,
            "failure": failure,
            "timestamp": datetime.now().isoformat(),
            "lesson_learned": failure.get("lesson", "Unknown")
        }
        
        self.memory.write(
            category="failures",
            key=f"failure_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            data=failure_data,
            agent=agent_name,
            tags=["learning", "failure", "avoid"]
        )
        
        self.log(f"Agent {agent_name} shared failure learning: {failure.get('description')}", "WARNING")
    
    def get_agent_status_summary(self) -> Dict:
        """Get summary of all agents' current status"""
        if not self.memory:
            return {}
        
        summary = {}
        
        for agent in self.AGENTS:
            # Get latest activity
            results = self.memory.query(
                category="agent_activity",
                tags=["coordination", "activity"],
                limit=1
            )
            
            if results:
                data = results[0].get("data", {})
                if data.get("agent") == agent:
                    summary[agent] = {
                        "status": data.get("status", "idle"),
                        "current_task": data.get("activity", {}).get("description", "None"),
                        "last_update": data.get("timestamp", "Unknown")
                    }
                else:
                    summary[agent] = {"status": "idle", "current_task": "None"}
            else:
                summary[agent] = {"status": "idle", "current_task": "None"}
        
        return summary
    
    def create_collaboration_session(self, session_name: str, agents: List[str], goal: str) -> Dict:
        """Create a collaboration session where multiple agents work together"""
        session = {
            "session_id": hashlib.md5(session_name.encode()).hexdigest()[:8],
            "name": session_name,
            "agents": agents,
            "goal": goal,
            "start_time": datetime.now().isoformat(),
            "status": "active",
            "shared_context": {},
            "results": []
        }
        
        if self.memory:
            self.memory.write(
                category="collaboration",
                key=session["session_id"],
                data=session,
                agent="coordinator",
                tags=["collaboration", "session"]
            )
        
        self.log(f"Created collaboration session '{session_name}' with agents: {', '.join(agents)}")
        return session
    
    def update_collaboration_context(self, session_id: str, agent_name: str, update: Dict):
        """Update shared context in a collaboration session"""
        if not self.memory:
            return
        
        # Read current session
        results = self.memory.query(
            category="collaboration",
            tags=["collaboration", "session"],
            limit=50
        )
        
        for result in results:
            data = result.get("data", {})
            if data.get("session_id") == session_id:
                # Update shared context
                if "shared_context" not in data:
                    data["shared_context"] = {}
                
                data["shared_context"][agent_name] = {
                    "update": update,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Write back
                self.memory.write(
                    category="collaboration",
                    key=session_id,
                    data=data,
                    agent=agent_name,
                    tags=["collaboration", "session", "updated"]
                )
                
                self.log(f"Agent {agent_name} updated collaboration context in session {session_id}")
                break


def main():
    """Demo and testing"""
    print("="*60)
    print("AI Agent Coordination System")
    print("="*60)
    print()
    
    coordinator = AIAgentCoordinator()
    
    # Demo: Register agent activity
    coordinator.register_agent_activity("kilocode", {
        "description": "Building new API endpoint",
        "file": "api/endpoints.py",
        "task_type": "backend"
    })
    
    # Demo: Check for duplicate work
    duplicate = coordinator.check_duplicate_work("Creating API endpoint")
    if duplicate:
        print(f"\n⚠️  Duplicate work detected!")
    
    # Demo: Complete activity
    coordinator.complete_agent_activity("kilocode", {
        "description": "Built API endpoint",
        "success": True,
        "task_type": "backend",
        "approach": "FastAPI with Pydantic validation",
        "pattern": "REST API"
    })
    
    # Demo: Get agent status
    print("\n📊 Agent Status Summary:")
    status = coordinator.get_agent_status_summary()
    for agent, info in status.items():
        print(f"  {agent}: {info['status']} - {info['current_task']}")
    
    # Demo: Create collaboration session
    session = coordinator.create_collaboration_session(
        session_name="Build Nutrition API",
        agents=["kilocode", "roo_code", "copilot"],
        goal="Build complete nutrition tracking API with frontend"
    )
    print(f"\n🤝 Created collaboration session: {session['session_id']}")
    
    # Demo: Coordinate parallel tasks
    tasks = [
        {"description": "Build database models", "type": "backend", "dependencies": []},
        {"description": "Create React components", "type": "frontend", "dependencies": []},
        {"description": "Write API tests", "type": "testing", "dependencies": ["Build database models"]},
    ]
    
    assignments = coordinator.coordinate_parallel_tasks(tasks)
    print(f"\n📋 Task Assignments:")
    for agent, agent_tasks in assignments.items():
        if agent_tasks:
            print(f"  {agent}: {len(agent_tasks)} tasks")


if __name__ == "__main__":
    main()
