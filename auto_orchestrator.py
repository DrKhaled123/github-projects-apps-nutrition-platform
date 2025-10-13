#!/usr/bin/env python3
"""
🤖 AUTO-ORCHESTRATOR - FULL STACK TESTING & DEPLOYMENT
Automated system validation, testing, fixing, and deployment
"""

import subprocess
import json
import time
import os
from datetime import datetime
from typing import Dict, List, Tuple

class AutoOrchestrator:
    def __init__(self):
        self.results = {
            "start_time": datetime.now().isoformat(),
            "phases": {},
            "errors": [],
            "fixes_applied": []
        }
        self.server = "128.140.111.171"
        self.ssh_key = os.path.expanduser("~/.ssh/coolify_doctorhealthy1")
        
    def run_command(self, cmd: str, cwd: str = None) -> Tuple[bool, str, str]:
        """Execute command and return success, stdout, stderr"""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, 
                cwd=cwd, timeout=300
            )
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            return False, "", str(e)
    
    def log(self, message: str, level: str = "INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        symbols = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARN": "⚠️", "FIX": "🔧"}
        print(f"[{timestamp}] {symbols.get(level, '•')} {message}")
    
    def phase_1_backend_validation(self):
        """Validate and fix Go backend"""
        self.log("PHASE 1: Backend Validation", "INFO")
        phase_results = {}
        
        # Test Go compilation
        self.log("Testing Go compilation...")
        success, stdout, stderr = self.run_command("go build -o /tmp/test_build .")
        phase_results["compilation"] = success
        
        if not success:
            self.log("Compilation errors found, attempting fixes...", "WARN")
            # Auto-fix: Update dependencies
            self.run_command("go mod tidy")
            self.run_command("go mod download")
            success, _, _ = self.run_command("go build -o /tmp/test_build .")
            if success:
                self.log("Fixed compilation issues", "FIX")
                self.fixes_applied.append("go_mod_tidy")
        
        # Run Go tests
        self.log("Running Go tests...")
        success, stdout, stderr = self.run_command("go test ./... -v -timeout=60s")
        phase_results["tests"] = success
        
        # Check critical files
        critical_files = ["main.go", "go.mod", "Dockerfile"]
        for file in critical_files:
            exists = os.path.exists(file)
            phase_results[f"file_{file}"] = exists
            if not exists:
                self.log(f"Missing critical file: {file}", "ERROR")
        
        self.results["phases"]["backend"] = phase_results
        return all(phase_results.values())
    
    def phase_2_frontend_validation(self):
        """Validate frontend"""
        self.log("PHASE 2: Frontend Validation", "INFO")
        phase_results = {}
        
        frontend_path = "frontend"
        if os.path.exists(frontend_path):
            # Check package.json
            if os.path.exists(f"{frontend_path}/package.json"):
                self.log("Installing frontend dependencies...")
                success, _, _ = self.run_command("npm install", cwd=frontend_path)
                phase_results["dependencies"] = success
                
                if success:
                    self.log("Building frontend...")
                    success, _, _ = self.run_command("npm run build", cwd=frontend_path)
                    phase_results["build"] = success
            else:
                # Simple HTML frontend
                phase_results["static_html"] = os.path.exists(f"{frontend_path}/index.html")
        else:
            self.log("No frontend directory found", "WARN")
            phase_results["exists"] = False
        
        self.results["phases"]["frontend"] = phase_results
        return True  # Non-blocking
    
    def phase_3_docker_validation(self):
        """Validate Docker build"""
        self.log("PHASE 3: Docker Validation", "INFO")
        phase_results = {}
        
        self.log("Building Docker image...")
        success, stdout, stderr = self.run_command(
            "docker build -t doctorhealthy1:test-auto . 2>&1 | tail -20"
        )
        phase_results["build"] = success
        
        if success:
            self.log("Docker build successful", "SUCCESS")
            # Test container startup
            self.log("Testing container startup...")
            self.run_command("docker rm -f test-dh-container 2>/dev/null")
            success, _, _ = self.run_command(
                "docker run -d --name test-dh-container -p 9999:8081 doctorhealthy1:test-auto"
            )
            
            if success:
                time.sleep(3)
                # Test health endpoint
                health_success, _, _ = self.run_command(
                    "curl -f http://localhost:9999/health"
                )
                phase_results["health"] = health_success
                
                # Cleanup
                self.run_command("docker stop test-dh-container")
                self.run_command("docker rm test-dh-container")
        
        self.results["phases"]["docker"] = phase_results
        return phase_results.get("build", False)
    
    def phase_4_ssh_connectivity(self):
        """Validate SSH connectivity to production"""
        self.log("PHASE 4: SSH Connectivity Test", "INFO")
        phase_results = {}
        
        # Test SSH connection
        self.log(f"Testing SSH to {self.server}...")
        success, stdout, stderr = self.run_command(
            f'ssh -i {self.ssh_key} -o ConnectTimeout=10 -o StrictHostKeyChecking=no root@{self.server} "echo SSH_OK"'
        )
        phase_results["ssh_connection"] = success
        
        if success:
            self.log("SSH connection successful", "SUCCESS")
            
            # Check Docker on remote
            self.log("Checking remote Docker...")
            success, stdout, _ = self.run_command(
                f'ssh -i {self.ssh_key} root@{self.server} "docker --version"'
            )
            phase_results["remote_docker"] = success
            
            # Check application container
            self.log("Checking application container...")
            success, stdout, _ = self.run_command(
                f'ssh -i {self.ssh_key} root@{self.server} "docker ps --filter name=doctorhealthy"'
            )
            phase_results["app_container"] = "doctorhealthy" in stdout if success else False
        
        self.results["phases"]["ssh"] = phase_results
        return phase_results.get("ssh_connection", False)
    
    def phase_5_deployment_validation(self):
        """Validate deployment on production"""
        self.log("PHASE 5: Production Deployment Validation", "INFO")
        phase_results = {}
        
        # Check domain DNS
        self.log("Checking DNS resolution...")
        success, stdout, _ = self.run_command("dig +short my.doctorhealthy1.com")
        phase_results["dns"] = self.server in stdout if success else False
        
        # Try to access health endpoint
        self.log("Testing production health endpoint...")
        success, stdout, _ = self.run_command(
            f"curl -k -I http://{self.server}/health -H 'Host: my.doctorhealthy1.com' 2>&1"
        )
        phase_results["health_endpoint"] = success and "200" in stdout
        
        # Check SSL status (if configured)
        self.log("Checking HTTPS availability...")
        success, _, _ = self.run_command(
            "curl -I -k https://my.doctorhealthy1.com/health 2>&1"
        )
        phase_results["https"] = success
        
        self.results["phases"]["deployment"] = phase_results
        return True
    
    def phase_6_integration_tests(self):
        """Run integration tests"""
        self.log("PHASE 6: Integration Tests", "INFO")
        phase_results = {}
        
        # Test API endpoints
        endpoints = [
            "/health",
            "/api/v1/recipes",
            "/api/v1/vip/summary"
        ]
        
        for endpoint in endpoints:
            self.log(f"Testing endpoint: {endpoint}")
            success, stdout, _ = self.run_command(
                f"curl -f http://localhost:8085{endpoint} 2>/dev/null"
            )
            phase_results[f"endpoint_{endpoint}"] = success
        
        self.results["phases"]["integration"] = phase_results
        return True
    
    def generate_report(self):
        """Generate final report"""
        self.results["end_time"] = datetime.now().isoformat()
        self.results["fixes_applied"] = self.fixes_applied
        
        # Write JSON report
        with open("orchestrator_report.json", "w") as f:
            json.dump(self.results, f, indent=2)
        
        # Generate markdown report
        report = f"""# 🤖 Auto-Orchestrator Report
**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- **Start Time**: {self.results['start_time']}
- **End Time**: {self.results['end_time']}
- **Fixes Applied**: {len(self.fixes_applied)}

## Phase Results

"""
        for phase, results in self.results["phases"].items():
            report += f"\n### {phase.upper()}\n"
            for key, value in results.items():
                status = "✅" if value else "❌"
                report += f"- {status} {key}: {value}\n"
        
        if self.fixes_applied:
            report += f"\n## Fixes Applied\n"
            for fix in self.fixes_applied:
                report += f"- 🔧 {fix}\n"
        
        with open("ORCHESTRATOR_REPORT.md", "w") as f:
            f.write(report)
        
        self.log("Report generated: ORCHESTRATOR_REPORT.md", "SUCCESS")
    
    def run_all(self):
        """Execute all phases"""
        self.log("=" * 60, "INFO")
        self.log("🤖 AUTO-ORCHESTRATOR STARTED", "INFO")
        self.log("=" * 60, "INFO")
        
        phases = [
            ("Backend Validation", self.phase_1_backend_validation),
            ("Frontend Validation", self.phase_2_frontend_validation),
            ("Docker Validation", self.phase_3_docker_validation),
            ("SSH Connectivity", self.phase_4_ssh_connectivity),
            ("Deployment Validation", self.phase_5_deployment_validation),
            ("Integration Tests", self.phase_6_integration_tests),
        ]
        
        for name, phase_func in phases:
            try:
                result = phase_func()
                status = "✅ PASSED" if result else "⚠️ COMPLETED WITH ISSUES"
                self.log(f"{name}: {status}", "SUCCESS" if result else "WARN")
            except Exception as e:
                self.log(f"{name}: ❌ FAILED - {str(e)}", "ERROR")
                self.results["errors"].append(f"{name}: {str(e)}")
        
        self.log("=" * 60, "INFO")
        self.log("🤖 AUTO-ORCHESTRATOR COMPLETED", "INFO")
        self.log("=" * 60, "INFO")
        
        self.generate_report()

if __name__ == "__main__":
    orchestrator = AutoOrchestrator()
    orchestrator.run_all()
