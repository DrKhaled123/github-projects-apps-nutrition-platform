#!/usr/bin/env python3
"""
Testing Orchestrator Module
Runs unit, integration, and e2e tests with coverage reporting
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import os


class TestingOrchestrator:
    """Orchestrates all testing activities"""
    
    def __init__(self, config_path: str = "./orchestration/orchestration-config.json"):
        self.config = self._load_config(config_path)
        self.test_config = self.config["testing"]
        self.reports_dir = Path("orchestration/reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
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
                    agent="testing_orchestrator",
                    tags=["testing", "orchestration"]
                )
            except Exception as e:
                print(f"Warning: Could not write to shared memory: {e}")
    
    def _run_command(self, command: List[str], timeout: int = 300) -> Dict:
        """Run a command and capture output"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.getcwd()
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }
    
    def detect_test_framework(self) -> Optional[str]:
        """Auto-detect test framework"""
        if Path("pytest.ini").exists() or Path("setup.cfg").exists():
            return "pytest"
        if Path("package.json").exists():
            try:
                with open("package.json", 'r') as f:
                    pkg = json.load(f)
                    if "jest" in pkg.get("devDependencies", {}):
                        return "jest"
                    if "mocha" in pkg.get("devDependencies", {}):
                        return "mocha"
            except Exception:
                pass
        if Path("go.mod").exists():
            return "go"
        return None
    
    def run_pytest(self, test_type: str, config: Dict) -> Dict:
        """Run pytest tests"""
        test_path = config.get("path", "tests")
        timeout = config.get("timeout_seconds", 300)
        
        # Build pytest command
        cmd = ["python", "-m", "pytest"]
        
        if Path(test_path).exists():
            cmd.append(test_path)
        
        # Add coverage if enabled
        if self.test_config.get("coverage", {}).get("enabled"):
            cmd.extend([
                "--cov=.",
                f"--cov-report=term",
                f"--cov-report=html:orchestration/reports/coverage-{test_type}",
                f"--cov-report=json:orchestration/reports/coverage-{test_type}.json"
            ])
            threshold = self.test_config["coverage"].get("threshold", 80)
            if self.test_config["coverage"].get("fail_under_threshold"):
                cmd.append(f"--cov-fail-under={threshold}")
        
        # Add verbose output
        cmd.extend(["-v", "--tb=short"])
        
        # Add JSON report
        cmd.append(f"--json-report")
        cmd.append(f"--json-report-file=orchestration/reports/test-{test_type}.json")
        
        print(f"Running pytest for {test_type} tests...")
        print(f"Command: {' '.join(cmd)}")
        
        result = self._run_command(cmd, timeout)
        
        # Parse results
        test_report = {
            "framework": "pytest",
            "test_type": test_type,
            "success": result["success"],
            "output": result["stdout"],
            "errors": result["stderr"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Try to read JSON report
        json_report_path = Path(f"orchestration/reports/test-{test_type}.json")
        if json_report_path.exists():
            try:
                with open(json_report_path, 'r') as f:
                    json_report = json.load(f)
                    test_report["summary"] = json_report.get("summary", {})
            except Exception:
                pass
        
        return test_report
    
    def run_jest(self, test_type: str, config: Dict) -> Dict:
        """Run Jest tests"""
        test_path = config.get("path", "tests")
        timeout = config.get("timeout_seconds", 300)
        
        cmd = ["npm", "test", "--", "--ci"]
        
        if self.test_config.get("coverage", {}).get("enabled"):
            cmd.append("--coverage")
        
        cmd.extend([
            "--json",
            f"--outputFile=orchestration/reports/test-{test_type}.json"
        ])
        
        print(f"Running Jest for {test_type} tests...")
        result = self._run_command(cmd, timeout)
        
        return {
            "framework": "jest",
            "test_type": test_type,
            "success": result["success"],
            "output": result["stdout"],
            "errors": result["stderr"],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def run_go_test(self, test_type: str, config: Dict) -> Dict:
        """Run Go tests"""
        test_path = config.get("path", "./...")
        timeout = config.get("timeout_seconds", 300)
        
        cmd = ["go", "test", test_path, "-v"]
        
        if self.test_config.get("coverage", {}).get("enabled"):
            cmd.extend(["-coverprofile=orchestration/reports/coverage.out"])
        
        print(f"Running Go tests for {test_type}...")
        result = self._run_command(cmd, timeout)
        
        return {
            "framework": "go",
            "test_type": test_type,
            "success": result["success"],
            "output": result["stdout"],
            "errors": result["stderr"],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def run_test_suite(self, test_type: str) -> Dict:
        """Run a specific test suite (unit, integration, e2e)"""
        if test_type not in self.test_config["test_types"]:
            return {
                "success": False,
                "error": f"Unknown test type: {test_type}"
            }
        
        test_config = self.test_config["test_types"][test_type]
        
        if not test_config.get("enabled", True):
            return {
                "success": True,
                "skipped": True,
                "message": f"{test_type} tests are disabled"
            }
        
        # Update shared memory
        self._write_to_memory(
            "pipeline_status",
            {
                "stage": "testing",
                "test_type": test_type,
                "status": "running",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Detect and run appropriate framework
        framework = self.detect_test_framework()
        
        if framework == "pytest":
            result = self.run_pytest(test_type, test_config)
        elif framework == "jest":
            result = self.run_jest(test_type, test_config)
        elif framework == "go":
            result = self.run_go_test(test_type, test_config)
        else:
            result = {
                "success": False,
                "error": "No test framework detected"
            }
        
        # Save report
        report_path = self.reports_dir / f"test-{test_type}-{int(time.time())}.json"
        with open(report_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        # Update shared memory
        self._write_to_memory(
            "pipeline_status",
            {
                "stage": "testing",
                "test_type": test_type,
                "status": "completed" if result["success"] else "failed",
                "timestamp": datetime.utcnow().isoformat(),
                "report_path": str(report_path)
            }
        )
        
        return result
    
    def run_all_tests(self) -> Dict:
        """Run all enabled test suites"""
        print("=" * 70)
        print("TESTING ORCHESTRATOR - Running All Tests")
        print("=" * 70)
        
        start_time = time.time()
        results = {
            "overall_success": True,
            "test_suites": {},
            "start_time": datetime.utcnow().isoformat(),
            "end_time": None,
            "duration_seconds": 0
        }
        
        # Run each test type
        for test_type, config in self.test_config["test_types"].items():
            if not config.get("enabled", True):
                continue
            
            print(f"\n--- Running {test_type.upper()} tests ---")
            result = self.run_test_suite(test_type)
            results["test_suites"][test_type] = result
            
            if not result.get("success", False):
                results["overall_success"] = False
                if self.config["pipeline"].get("fail_fast"):
                    print(f"\n❌ {test_type} tests failed. Stopping (fail_fast enabled).")
                    break
            else:
                print(f"✓ {test_type} tests passed")
        
        end_time = time.time()
        results["end_time"] = datetime.utcnow().isoformat()
        results["duration_seconds"] = round(end_time - start_time, 2)
        
        # Save overall report
        report_path = self.reports_dir / f"test-report-{int(time.time())}.json"
        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Write to shared memory
        self._write_to_memory(
            "test_results",
            {
                "success": results["overall_success"],
                "duration_seconds": results["duration_seconds"],
                "report_path": str(report_path),
                "timestamp": results["end_time"]
            }
        )
        
        print("\n" + "=" * 70)
        if results["overall_success"]:
            print("✓ ALL TESTS PASSED")
        else:
            print("❌ SOME TESTS FAILED")
        print(f"Duration: {results['duration_seconds']}s")
        print(f"Report: {report_path}")
        print("=" * 70)
        
        return results


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Testing Orchestrator")
    parser.add_argument(
        "--type",
        choices=["unit", "integration", "e2e", "all"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--config",
        default="./orchestration/orchestration-config.json",
        help="Path to configuration file"
    )
    
    args = parser.parse_args()
    
    orchestrator = TestingOrchestrator(args.config)
    
    if args.type == "all":
        results = orchestrator.run_all_tests()
    else:
        results = orchestrator.run_test_suite(args.type)
    
    sys.exit(0 if results.get("overall_success", results.get("success", False)) else 1)


if __name__ == "__main__":
    main()
