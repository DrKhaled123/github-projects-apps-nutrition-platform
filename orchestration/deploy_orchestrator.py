#!/usr/bin/env python3
"""
Deploy Orchestrator Module
Deploys Docker images to Coolify with health checks and rollback
"""

import json
import subprocess
import sys
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import os


class CoolifyDeployOrchestrator:
    """Orchestrates deployment to Coolify"""
    
    def __init__(self, config_path: str = "./orchestration/orchestration-config.json"):
        self.config = self._load_config(config_path)
        self.deploy_config = self.config["deploy"]
        self.coolify_config = self.deploy_config.get("coolify", {})
        self.reports_dir = Path("orchestration/reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Get Coolify credentials
        self.api_url = os.getenv(
            self.coolify_config.get("api_url", "").replace("${", "").replace("}", ""),
            self.coolify_config.get("api_url", "")
        )
        self.api_token = os.getenv(
            self.coolify_config.get("api_token", "").replace("${", "").replace("}", ""),
            self.coolify_config.get("api_token", "")
        )
        
        # Initialize shared memory integration
        try:
            # Add parent directory to Python path for imports
            parent_dir = Path(__file__).parent.parent
            sys.path.insert(0, str(parent_dir))
            
            from ai_agents_shared_memory.utils.memory_manager import MemoryManager
            self.memory = MemoryManager()
        except Exception as e:
            print(f"Warning: Could not initialize shared memory: {e}")
            self.memory = None
    
    def _load_config(self, config_path: str) -> Dict:
        """Load orchestration configuration"""
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def _write_to_memory(self, key: str, data: Dict):
        """Write progress to shared memory"""
        if self.memory:
            try:
                self.memory.write(
                    category="context",
                    key=key,
                    data=data,
                    agent="deploy_orchestrator",
                    tags=["deploy", "orchestration", "coolify"]
                )
            except Exception as e:
                print(f"Warning: Could not write to shared memory: {e}")
    
    def _coolify_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make request to Coolify API"""
        if not self.api_url or not self.api_token:
            return {
                "success": False,
                "error": "Coolify API credentials not configured"
            }
        
        url = f"{self.api_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                return {"success": False, "error": f"Unsupported method: {method}"}
            
            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "data": response.json() if response.text else {},
                "error": None if response.status_code < 400 else response.text
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_application_info(self) -> Dict:
        """Get current application information from Coolify"""
        app_id = self.coolify_config.get("application_id")
        if not app_id:
            return {"success": False, "error": "No application_id configured"}
        
        print(f"Getting application info for {app_id}...")
        return self._coolify_request("GET", f"/applications/{app_id}")
    
    def get_current_deployment(self) -> Optional[Dict]:
        """Get current deployment information"""
        app_info = self.get_application_info()
        if not app_info.get("success"):
            return None
        
        return app_info.get("data", {}).get("current_deployment")
    
    def trigger_deployment(self, image: str, tag: str = "latest") -> Dict:
        """Trigger a new deployment on Coolify"""
        print(f"Triggering deployment for {image}:{tag}...")
        
        app_id = self.coolify_config.get("application_id")
        if not app_id:
            return {"success": False, "error": "No application_id configured"}
        
        # Update shared memory
        self._write_to_memory(
            "pipeline_status",
            {
                "stage": "deploy",
                "status": "deploying",
                "image": f"{image}:{tag}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Trigger deployment via Coolify API
        deployment_data = {
            "image": f"{image}:{tag}",
            "environment": self.coolify_config.get("environment", "production")
        }
        
        result = self._coolify_request(
            "POST",
            f"/applications/{app_id}/deploy",
            deployment_data
        )
        
        if result.get("success"):
            deployment_id = result.get("data", {}).get("deployment_id")
            print(f"✓ Deployment triggered: {deployment_id}")
            return {
                "success": True,
                "deployment_id": deployment_id,
                "data": result.get("data")
            }
        else:
            print(f"❌ Deployment failed: {result.get('error')}")
            return result
    
    def wait_for_deployment(self, deployment_id: str, timeout: int = 600) -> Dict:
        """Wait for deployment to complete"""
        print(f"Waiting for deployment {deployment_id} to complete...")
        
        start_time = time.time()
        app_id = self.coolify_config.get("application_id")
        
        while time.time() - start_time < timeout:
            # Check deployment status
            result = self._coolify_request(
                "GET",
                f"/applications/{app_id}/deployments/{deployment_id}"
            )
            
            if not result.get("success"):
                return {
                    "success": False,
                    "error": "Failed to check deployment status",
                    "details": result.get("error")
                }
            
            status = result.get("data", {}).get("status")
            print(f"  Status: {status}")
            
            if status in ["success", "completed", "running"]:
                return {
                    "success": True,
                    "status": status,
                    "deployment_data": result.get("data")
                }
            elif status in ["failed", "error", "cancelled"]:
                return {
                    "success": False,
                    "status": status,
                    "deployment_data": result.get("data")
                }
            
            # Wait before next check
            time.sleep(10)
        
        return {
            "success": False,
            "error": f"Deployment timed out after {timeout} seconds"
        }
    
    def health_check(self, retries: int = 5, interval: int = 10) -> Dict:
        """Perform health check on deployed application"""
        print("Performing health check...")
        
        health_config = self.deploy_config.get("health_check", {})
        if not health_config.get("enabled", True):
            return {"skipped": True}
        
        # Get application info to find URL
        app_info = self.get_application_info()
        if not app_info.get("success"):
            return {
                "success": False,
                "error": "Could not get application info for health check"
            }
        
        app_data = app_info.get("data", {})
        base_url = app_data.get("fqdn") or app_data.get("url")
        
        if not base_url:
            return {
                "success": False,
                "error": "No URL found for health check"
            }
        
        endpoint = health_config.get("endpoint", "/health")
        health_url = f"{base_url.rstrip('/')}{endpoint}"
        expected_status = health_config.get("expected_status", 200)
        timeout = health_config.get("timeout_seconds", 10)
        
        for attempt in range(1, retries + 1):
            print(f"  Health check attempt {attempt}/{retries}...")
            
            try:
                response = requests.get(health_url, timeout=timeout)
                
                if response.status_code == expected_status:
                    print(f"✓ Health check passed (status: {response.status_code})")
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "attempts": attempt,
                        "response": response.text[:500]  # First 500 chars
                    }
                else:
                    print(f"  Health check returned {response.status_code}, expected {expected_status}")
            
            except Exception as e:
                print(f"  Health check failed: {e}")
            
            if attempt < retries:
                time.sleep(interval)
        
        return {
            "success": False,
            "error": f"Health check failed after {retries} attempts"
        }
    
    def rollback(self) -> Dict:
        """Rollback to previous deployment"""
        print("Rolling back to previous deployment...")
        
        if not self.deploy_config.get("rollback", {}).get("enabled", True):
            return {"skipped": True, "reason": "Rollback disabled"}
        
        app_id = self.coolify_config.get("application_id")
        if not app_id:
            return {"success": False, "error": "No application_id configured"}
        
        # Trigger rollback
        result = self._coolify_request(
            "POST",
            f"/applications/{app_id}/rollback"
        )
        
        if result.get("success"):
            print("✓ Rollback successful")
        else:
            print(f"❌ Rollback failed: {result.get('error')}")
        
        return result
    
    def run_full_deployment(self, image: str, tag: str = "latest") -> Dict:
        """Run complete deployment process"""
        print("=" * 70)
        print("DEPLOY ORCHESTRATOR - Deploying to Coolify")
        print("=" * 70)
        
        start_time = time.time()
        
        # Update shared memory
        self._write_to_memory(
            "pipeline_status",
            {
                "stage": "deploy",
                "status": "running",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        results = {
            "image": f"{image}:{tag}",
            "start_time": datetime.utcnow().isoformat(),
            "end_time": None,
            "duration_seconds": 0,
            "overall_success": True
        }
        
        # Trigger deployment
        print("\n--- Triggering Deployment ---")
        deploy_result = self.trigger_deployment(image, tag)
        results["deployment"] = deploy_result
        
        if not deploy_result.get("success"):
            results["overall_success"] = False
            print("❌ Deployment trigger failed")
        else:
            deployment_id = deploy_result.get("deployment_id")
            
            # Wait for deployment
            print("\n--- Waiting for Deployment ---")
            wait_result = self.wait_for_deployment(deployment_id)
            results["deployment_wait"] = wait_result
            
            if not wait_result.get("success"):
                results["overall_success"] = False
                print("❌ Deployment failed")
                
                # Attempt rollback
                if self.deploy_config.get("rollback", {}).get("auto_rollback_on_failure", True):
                    print("\n--- Attempting Rollback ---")
                    rollback_result = self.rollback()
                    results["rollback"] = rollback_result
            else:
                print("✓ Deployment completed")
                
                # Health check
                print("\n--- Health Check ---")
                health_result = self.health_check()
                results["health_check"] = health_result
                
                if not health_result.get("success") and not health_result.get("skipped"):
                    results["overall_success"] = False
                    print("❌ Health check failed")
                    
                    # Attempt rollback
                    if self.deploy_config.get("rollback", {}).get("auto_rollback_on_failure", True):
                        print("\n--- Attempting Rollback ---")
                        rollback_result = self.rollback()
                        results["rollback"] = rollback_result
                else:
                    print("✓ Health check passed")
        
        end_time = time.time()
        results["end_time"] = datetime.utcnow().isoformat()
        results["duration_seconds"] = round(end_time - start_time, 2)
        
        # Save report
        report_path = self.reports_dir / f"deploy-report-{int(time.time())}.json"
        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Update shared memory
        self._write_to_memory(
            "deploy_results",
            {
                "success": results["overall_success"],
                "duration_seconds": results["duration_seconds"],
                "report_path": str(report_path),
                "timestamp": results["end_time"]
            }
        )
        
        print("\n" + "=" * 70)
        if results["overall_success"]:
            print("✓ DEPLOYMENT SUCCESSFUL")
        else:
            print("❌ DEPLOYMENT FAILED")
        print(f"Duration: {results['duration_seconds']}s")
        print(f"Report: {report_path}")
        print("=" * 70)
        
        return results


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy Orchestrator")
    parser.add_argument(
        "--image",
        required=True,
        help="Docker image name"
    )
    parser.add_argument(
        "--tag",
        default="latest",
        help="Docker image tag"
    )
    parser.add_argument(
        "--config",
        default="./orchestration/orchestration-config.json",
        help="Path to configuration file"
    )
    
    args = parser.parse_args()
    
    orchestrator = CoolifyDeployOrchestrator(args.config)
    results = orchestrator.run_full_deployment(args.image, args.tag)
    
    sys.exit(0 if results.get("overall_success") else 1)


if __name__ == "__main__":
    main()
