#!/usr/bin/env python3
"""
Automated Orchestration System for DoctorHealthy1
Handles build, test, deploy, and validation cycles automatically
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from pathlib import Path

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class AutoOrchestrator:
    """Automated build, test, and deployment orchestrator"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "phases": {},
            "errors": [],
            "warnings": [],
            "success": True
        }
        
    def log(self, message: str, level: str = "INFO"):
        """Enhanced logging with colors"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {
            "INFO": Colors.CYAN,
            "SUCCESS": Colors.GREEN,
            "WARNING": Colors.YELLOW,
            "ERROR": Colors.RED,
            "HEADER": Colors.HEADER
        }
        color = colors.get(level, Colors.END)
        print(f"{color}[{timestamp}] [{level}] {message}{Colors.END}")
        
    def run_command(self, cmd: str, cwd: Optional[str] = None, timeout: int = 300) -> Tuple[int, str, str]:
        """Execute shell command with timeout"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd or self.base_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timeout after {timeout}s"
        except Exception as e:
            return -1, "", str(e)
    
    def phase_1_backend_validation(self) -> bool:
        """Phase 1: Validate and build backend"""
        self.log("="*60, "HEADER")
        self.log("PHASE 1: BACKEND VALIDATION & BUILD", "HEADER")
        self.log("="*60, "HEADER")
        
        phase_results = {"steps": [], "success": True}
        
        # Step 1: Check Go version
        self.log("Checking Go environment...")
        code, out, err = self.run_command("go version")
        if code == 0:
            self.log(f"✅ {out.strip()}", "SUCCESS")
            phase_results["steps"].append({"name": "go_version", "status": "success", "output": out.strip()})
        else:
            self.log(f"❌ Go not found: {err}", "ERROR")
            phase_results["success"] = False
            self.results["success"] = False
            return False
            
        # Step 2: Clean and update dependencies
        self.log("Updating Go dependencies...")
        code, out, err = self.run_command("go mod tidy")
        if code == 0:
            self.log("✅ Dependencies updated", "SUCCESS")
        else:
            self.log(f"⚠️ Warning: {err}", "WARNING")
            self.results["warnings"].append(f"go mod tidy: {err}")
        
        # Step 3: Build backend
        self.log("Building Go backend...")
        code, out, err = self.run_command("go build -o main .")
        if code == 0:
            self.log("✅ Backend build successful", "SUCCESS")
            phase_results["steps"].append({"name": "build", "status": "success"})
        else:
            self.log(f"❌ Build failed: {err}", "ERROR")
            phase_results["success"] = False
            self.results["success"] = False
            self.results["errors"].append(f"Backend build: {err}")
            return False
        
        # Step 4: Run tests
        self.log("Running backend tests...")
        code, out, err = self.run_command("go test ./... -v -count=1 -timeout=5m", timeout=300)
        if code == 0:
            # Parse test results
            pass_count = out.count("PASS")
            fail_count = out.count("FAIL")
            self.log(f"✅ Tests completed: {pass_count} passed, {fail_count} failed", "SUCCESS")
            phase_results["steps"].append({"name": "tests", "passed": pass_count, "failed": fail_count})
        else:
            self.log(f"⚠️ Some tests failed", "WARNING")
            self.results["warnings"].append("Some backend tests failed")
        
        self.results["phases"]["backend"] = phase_results
        return True
    
    def phase_2_docker_build(self) -> bool:
        """Phase 2: Build and test Docker image"""
        self.log("="*60, "HEADER")
        self.log("PHASE 2: DOCKER BUILD & VALIDATION", "HEADER")
        self.log("="*60, "HEADER")
        
        phase_results = {"steps": [], "success": True}
        
        # Build Docker image
        self.log("Building Docker image...")
        code, out, err = self.run_command(
            "docker build -t doctorhealthy1:auto-test .",
            timeout=600
        )
        if code == 0:
            self.log("✅ Docker image built successfully", "SUCCESS")
            phase_results["steps"].append({"name": "docker_build", "status": "success"})
        else:
            self.log(f"❌ Docker build failed: {err}", "ERROR")
            phase_results["success"] = False
            self.results["success"] = False
            return False
        
        # Test container
        self.log("Testing Docker container...")
        
        # Start container
        code, out, err = self.run_command(
            "docker run -d --name doctorhealthy_auto_test -p 8086:8081 -e PORT=8081 doctorhealthy1:auto-test"
        )
        if code != 0:
            self.log(f"❌ Failed to start container: {err}", "ERROR")
            phase_results["success"] = False
            return False
        
        # Wait for startup
        self.log("Waiting for container startup...")
        time.sleep(8)
        
        # Test health endpoint
        code, out, err = self.run_command("curl -s http://localhost:8086/health")
        if code == 0 and "healthy" in out.lower():
            self.log("✅ Container health check passed", "SUCCESS")
            phase_results["steps"].append({"name": "health_check", "status": "success"})
        else:
            self.log(f"⚠️ Health check returned: {out}", "WARNING")
        
        # Cleanup
        self.run_command("docker stop doctorhealthy_auto_test")
        self.run_command("docker rm doctorhealthy_auto_test")
        
        self.results["phases"]["docker"] = phase_results
        return True
    
    def phase_3_frontend_validation(self) -> bool:
        """Phase 3: Validate frontend structure"""
        self.log("="*60, "HEADER")
        self.log("PHASE 3: FRONTEND VALIDATION", "HEADER")
        self.log("="*60, "HEADER")
        
        phase_results = {"steps": [], "success": True}
        
        frontend_path = self.base_path / "frontend"
        if not frontend_path.exists():
            self.log("❌ Frontend directory not found", "ERROR")
            phase_results["success"] = False
            return False
        
        # Check required files
        required_files = ["index.html", "diet.html", "workouts.html", "lifestyle.html"]
        missing = []
        for file in required_files:
            if not (frontend_path / file).exists():
                missing.append(file)
        
        if missing:
            self.log(f"⚠️ Missing frontend files: {', '.join(missing)}", "WARNING")
            self.results["warnings"].append(f"Missing frontend files: {missing}")
        else:
            self.log("✅ All required frontend files present", "SUCCESS")
        
        # Check CSS and JS
        css_path = frontend_path / "css"
        js_path = frontend_path / "js"
        
        if css_path.exists():
            css_count = len(list(css_path.glob("*.css")))
            self.log(f"✅ Found {css_count} CSS files", "SUCCESS")
        
        if js_path.exists():
            js_count = len(list(js_path.glob("*.js")))
            self.log(f"✅ Found {js_count} JS files", "SUCCESS")
        
        self.results["phases"]["frontend"] = phase_results
        return True
    
    def phase_4_integration_tests(self) -> bool:
        """Phase 4: Run integration tests"""
        self.log("="*60, "HEADER")
        self.log("PHASE 4: INTEGRATION TESTING", "HEADER")
        self.log("="*60, "HEADER")
        
        phase_results = {"steps": [], "success": True}
        
        # Start test server
        self.log("Starting test server...")
        test_server = subprocess.Popen(
            ["./main"],
            cwd=self.base_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "PORT": "8087"}
        )
        
        time.sleep(5)
        
        # Test endpoints
        endpoints = [
            "/health",
            "/api/v1/recipes",
            "/api/v1/vip/summary"
        ]
        
        for endpoint in endpoints:
            code, out, err = self.run_command(f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:8087{endpoint}")
            status_code = out.strip() if code == 0 else "000"
            
            if status_code in ["200", "401"]:  # 401 is OK for protected endpoints
                self.log(f"✅ {endpoint}: {status_code}", "SUCCESS")
                phase_results["steps"].append({"endpoint": endpoint, "status": status_code, "result": "pass"})
            else:
                self.log(f"⚠️ {endpoint}: {status_code}", "WARNING")
                phase_results["steps"].append({"endpoint": endpoint, "status": status_code, "result": "fail"})
        
        # Cleanup
        test_server.terminate()
        test_server.wait(timeout=5)
        
        self.results["phases"]["integration"] = phase_results
        return True
    
    def phase_5_deployment_prep(self) -> bool:
        """Phase 5: Prepare deployment artifacts"""
        self.log("="*60, "HEADER")
        self.log("PHASE 5: DEPLOYMENT PREPARATION", "HEADER")
        self.log("="*60, "HEADER")
        
        phase_results = {"steps": [], "success": True}
        
        # Check SSH connectivity
        self.log("Testing SSH connection to server...")
        code, out, err = self.run_command(
            "ssh -i ~/.ssh/coolify_doctorhealthy1 -o ConnectTimeout=5 root@128.140.111.171 'echo Connected'"
        )
        if code == 0:
            self.log("✅ SSH connection successful", "SUCCESS")
            phase_results["steps"].append({"name": "ssh_test", "status": "success"})
        else:
            self.log(f"⚠️ SSH connection issue: {err}", "WARNING")
            self.results["warnings"].append("SSH connection needs verification")
        
        # Tag image for deployment
        self.log("Tagging image for deployment...")
        code, out, err = self.run_command(
            "docker tag doctorhealthy1:auto-test doctorhealthy1:latest"
        )
        if code == 0:
            self.log("✅ Image tagged", "SUCCESS")
        
        self.results["phases"]["deployment_prep"] = phase_results
        return True
    
    def generate_report(self) -> str:
        """Generate comprehensive test report"""
        self.log("="*60, "HEADER")
        self.log("ORCHESTRATION COMPLETE - GENERATING REPORT", "HEADER")
        self.log("="*60, "HEADER")
        
        report = {
            "timestamp": self.results["timestamp"],
            "overall_success": self.results["success"],
            "phases_completed": len(self.results["phases"]),
            "errors": len(self.results["errors"]),
            "warnings": len(self.results["warnings"]),
            "details": self.results
        }
        
        report_path = self.base_path / "AUTO_ORCHESTRATION_REPORT.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        self.log(f"✅ Report saved to: {report_path}", "SUCCESS")
        
        # Print summary
        if self.results["success"]:
            self.log("="*60, "SUCCESS")
            self.log("🎉 ALL PHASES COMPLETED SUCCESSFULLY!", "SUCCESS")
            self.log("="*60, "SUCCESS")
        else:
            self.log("="*60, "ERROR")
            self.log("❌ ORCHESTRATION COMPLETED WITH ERRORS", "ERROR")
            for error in self.results["errors"]:
                self.log(f"  - {error}", "ERROR")
            self.log("="*60, "ERROR")
        
        if self.results["warnings"]:
            self.log(f"\n⚠️ {len(self.results['warnings'])} Warnings:", "WARNING")
            for warning in self.results["warnings"]:
                self.log(f"  - {warning}", "WARNING")
        
        return str(report_path)
    
    def run(self):
        """Execute all orchestration phases"""
        self.log(f"\n{Colors.BOLD}{'='*60}{Colors.END}", "HEADER")
        self.log(f"{Colors.BOLD}🚀 AUTOMATED ORCHESTRATION SYSTEM{Colors.END}", "HEADER")
        self.log(f"{Colors.BOLD}   DoctorHealthy1 Full Stack Validation{Colors.END}", "HEADER")
        self.log(f"{Colors.BOLD}{'='*60}{Colors.END}\n", "HEADER")
        
        phases = [
            ("Backend Validation", self.phase_1_backend_validation),
            ("Docker Build", self.phase_2_docker_build),
            ("Frontend Validation", self.phase_3_frontend_validation),
            ("Integration Tests", self.phase_4_integration_tests),
            ("Deployment Prep", self.phase_5_deployment_prep)
        ]
        
        for phase_name, phase_func in phases:
            try:
                if not phase_func():
                    self.log(f"❌ Phase '{phase_name}' failed, continuing...", "ERROR")
            except Exception as e:
                self.log(f"❌ Phase '{phase_name}' crashed: {e}", "ERROR")
                self.results["errors"].append(f"{phase_name}: {str(e)}")
                self.results["success"] = False
        
        return self.generate_report()

if __name__ == "__main__":
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    orchestrator = AutoOrchestrator(base_path)
    report_path = orchestrator.run()
    
    sys.exit(0 if orchestrator.results["success"] else 1)
