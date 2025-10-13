#!/usr/bin/env python3
"""
Review Orchestrator Module
Performs static analysis, security scanning, and quality checks
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import os


class ReviewOrchestrator:
    """Orchestrates code review activities"""
    
    def __init__(self, config_path: str = "./orchestration/orchestration-config.json"):
        self.config = self._load_config(config_path)
        self.review_config = self.config["review"]
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
                    agent="review_orchestrator",
                    tags=["review", "orchestration"]
                )
            except Exception as e:
                print(f"Warning: Could not write to shared memory: {e}")
    
    def _run_command(self, command: List[str]) -> Dict:
        """Run a command and capture output"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }
    
    def detect_language(self) -> str:
        """Auto-detect primary language"""
        if Path("requirements.txt").exists() or Path("setup.py").exists():
            return "python"
        if Path("package.json").exists():
            return "javascript"
        if Path("go.mod").exists():
            return "go"
        return "unknown"
    
    def run_pylint(self) -> Dict:
        """Run pylint for Python code"""
        print("Running pylint...")
        
        # Find Python files
        python_files = list(Path(".").rglob("*.py"))
        if not python_files:
            return {"skipped": True, "reason": "No Python files found"}
        
        cmd = ["python", "-m", "pylint"]
        cmd.extend([str(f) for f in python_files[:50]])  # Limit to first 50 files
        cmd.extend([
            "--output-format=json",
            f"--rcfile={self.review_config['static_analysis']['python']['config_files'].get('pylint', '.pylintrc')}"
        ])
        
        result = self._run_command(cmd)
        
        # Parse pylint output
        score = 0.0
        issues = []
        try:
            if result["stdout"]:
                pylint_output = json.loads(result["stdout"])
                issues = pylint_output
                # Extract score from stderr (pylint puts it there)
                if "Your code has been rated at" in result["stderr"]:
                    score_str = result["stderr"].split("rated at ")[1].split("/")[0]
                    score = float(score_str)
        except Exception:
            pass
        
        return {
            "tool": "pylint",
            "score": score,
            "issues": issues,
            "success": result["success"] or score >= 7.0,
            "raw_output": result["stdout"]
        }
    
    def run_flake8(self) -> Dict:
        """Run flake8 for Python code"""
        print("Running flake8...")
        
        cmd = ["python", "-m", "flake8", ".", "--format=json"]
        config_file = self.review_config['static_analysis']['python']['config_files'].get('flake8')
        if config_file and Path(config_file).exists():
            cmd.append(f"--config={config_file}")
        
        result = self._run_command(cmd)
        
        issues = []
        try:
            if result["stdout"]:
                issues = json.loads(result["stdout"])
        except Exception:
            pass
        
        return {
            "tool": "flake8",
            "issues_count": len(issues),
            "issues": issues,
            "success": len(issues) == 0,
            "raw_output": result["stdout"]
        }
    
    def run_bandit(self) -> Dict:
        """Run bandit for Python security"""
        print("Running bandit (security scan)...")
        
        cmd = ["python", "-m", "bandit", "-r", ".", "-f", "json"]
        severity = self.review_config['security']['python'].get('severity_threshold', 'medium')
        cmd.extend(["-ll"])  # Low severity
        
        result = self._run_command(cmd)
        
        vulnerabilities = []
        try:
            if result["stdout"]:
                bandit_output = json.loads(result["stdout"])
                vulnerabilities = bandit_output.get("results", [])
        except Exception:
            pass
        
        # Filter by severity
        critical_vulns = [v for v in vulnerabilities if v.get("issue_severity") in ["HIGH", "CRITICAL"]]
        
        return {
            "tool": "bandit",
            "vulnerabilities_count": len(vulnerabilities),
            "critical_count": len(critical_vulns),
            "vulnerabilities": vulnerabilities,
            "success": len(critical_vulns) == 0,
            "raw_output": result["stdout"]
        }
    
    def run_safety(self) -> Dict:
        """Run safety for Python dependency vulnerabilities"""
        print("Running safety (dependency check)...")
        
        cmd = ["python", "-m", "safety", "check", "--json"]
        result = self._run_command(cmd)
        
        vulnerabilities = []
        try:
            if result["stdout"]:
                vulnerabilities = json.loads(result["stdout"])
        except Exception:
            pass
        
        return {
            "tool": "safety",
            "vulnerabilities_count": len(vulnerabilities),
            "vulnerabilities": vulnerabilities,
            "success": len(vulnerabilities) == 0,
            "raw_output": result["stdout"]
        }
    
    def run_eslint(self) -> Dict:
        """Run ESLint for JavaScript code"""
        print("Running ESLint...")
        
        cmd = ["npx", "eslint", ".", "--format=json"]
        config_file = self.review_config['static_analysis'].get('javascript', {}).get('config_files', {}).get('eslint')
        if config_file and Path(config_file).exists():
            cmd.append(f"--config={config_file}")
        
        result = self._run_command(cmd)
        
        issues = []
        try:
            if result["stdout"]:
                issues = json.loads(result["stdout"])
        except Exception:
            pass
        
        return {
            "tool": "eslint",
            "files_with_issues": len(issues),
            "issues": issues,
            "success": len(issues) == 0,
            "raw_output": result["stdout"]
        }
    
    def run_npm_audit(self) -> Dict:
        """Run npm audit for JavaScript dependencies"""
        print("Running npm audit...")
        
        cmd = ["npm", "audit", "--json"]
        result = self._run_command(cmd)
        
        vulnerabilities = {}
        try:
            if result["stdout"]:
                audit_output = json.loads(result["stdout"])
                vulnerabilities = audit_output.get("vulnerabilities", {})
        except Exception:
            pass
        
        return {
            "tool": "npm_audit",
            "vulnerabilities_count": len(vulnerabilities),
            "vulnerabilities": vulnerabilities,
            "success": len(vulnerabilities) == 0,
            "raw_output": result["stdout"]
        }
    
    def run_static_analysis(self, language: str) -> Dict:
        """Run static analysis for detected language"""
        results = {
            "language": language,
            "tools": {},
            "overall_success": True
        }
        
        if language == "python":
            tools = self.review_config['static_analysis']['python']['tools']
            if "pylint" in tools:
                results["tools"]["pylint"] = self.run_pylint()
                if not results["tools"]["pylint"].get("success"):
                    results["overall_success"] = False
            
            if "flake8" in tools:
                results["tools"]["flake8"] = self.run_flake8()
                if not results["tools"]["flake8"].get("success"):
                    results["overall_success"] = False
        
        elif language == "javascript":
            tools = self.review_config['static_analysis'].get('javascript', {}).get('tools', [])
            if "eslint" in tools:
                results["tools"]["eslint"] = self.run_eslint()
                if not results["tools"]["eslint"].get("success"):
                    results["overall_success"] = False
        
        return results
    
    def run_security_scan(self, language: str) -> Dict:
        """Run security scanning for detected language"""
        results = {
            "language": language,
            "tools": {},
            "overall_success": True
        }
        
        if language == "python":
            tools = self.review_config['security']['python']['tools']
            if "bandit" in tools:
                results["tools"]["bandit"] = self.run_bandit()
                if not results["tools"]["bandit"].get("success"):
                    results["overall_success"] = False
            
            if "safety" in tools:
                results["tools"]["safety"] = self.run_safety()
                if not results["tools"]["safety"].get("success"):
                    results["overall_success"] = False
        
        elif language == "javascript":
            tools = self.review_config['security'].get('javascript', {}).get('tools', [])
            if "npm audit" in tools:
                results["tools"]["npm_audit"] = self.run_npm_audit()
                if not results["tools"]["npm_audit"].get("success"):
                    results["overall_success"] = False
        
        return results
    
    def check_quality_gate(self, static_results: Dict, security_results: Dict) -> Dict:
        """Check if code meets quality gate requirements"""
        gate_config = self.review_config.get("quality_gate", {})
        
        if not gate_config.get("enabled"):
            return {"passed": True, "skipped": True}
        
        rules = gate_config.get("rules", {})
        violations = []
        
        # Check code score
        min_score = rules.get("min_code_score", 7.0)
        for tool_name, tool_result in static_results.get("tools", {}).items():
            score = tool_result.get("score", 10.0)
            if score < min_score:
                violations.append(f"{tool_name} score {score} < {min_score}")
        
        # Check critical vulnerabilities
        if rules.get("no_critical_vulnerabilities"):
            for tool_name, tool_result in security_results.get("tools", {}).items():
                critical = tool_result.get("critical_count", 0)
                if critical > 0:
                    violations.append(f"{tool_name} found {critical} critical vulnerabilities")
        
        passed = len(violations) == 0
        
        return {
            "passed": passed,
            "violations": violations,
            "block_pipeline": not passed and gate_config.get("block_on_failure", False)
        }
    
    def run_full_review(self) -> Dict:
        """Run complete code review"""
        print("=" * 70)
        print("REVIEW ORCHESTRATOR - Running Code Review")
        print("=" * 70)
        
        start_time = time.time()
        
        # Update shared memory
        self._write_to_memory(
            "pipeline_status",
            {
                "stage": "review",
                "status": "running",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Detect language
        language = self.detect_language()
        print(f"\nDetected language: {language}")
        
        results = {
            "language": language,
            "start_time": datetime.utcnow().isoformat(),
            "end_time": None,
            "duration_seconds": 0,
            "overall_success": True
        }
        
        # Run static analysis
        print("\n--- Static Analysis ---")
        static_results = self.run_static_analysis(language)
        results["static_analysis"] = static_results
        
        if not static_results.get("overall_success"):
            results["overall_success"] = False
        
        # Run security scan
        print("\n--- Security Scan ---")
        security_results = self.run_security_scan(language)
        results["security"] = security_results
        
        if not security_results.get("overall_success"):
            results["overall_success"] = False
        
        # Check quality gate
        print("\n--- Quality Gate ---")
        quality_gate = self.check_quality_gate(static_results, security_results)
        results["quality_gate"] = quality_gate
        
        if quality_gate.get("block_pipeline"):
            results["overall_success"] = False
        
        end_time = time.time()
        results["end_time"] = datetime.utcnow().isoformat()
        results["duration_seconds"] = round(end_time - start_time, 2)
        
        # Save report
        report_path = self.reports_dir / f"review-report-{int(time.time())}.json"
        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Update shared memory
        self._write_to_memory(
            "review_results",
            {
                "success": results["overall_success"],
                "duration_seconds": results["duration_seconds"],
                "report_path": str(report_path),
                "timestamp": results["end_time"]
            }
        )
        
        print("\n" + "=" * 70)
        if results["overall_success"]:
            print("✓ CODE REVIEW PASSED")
        else:
            print("❌ CODE REVIEW FAILED")
        print(f"Duration: {results['duration_seconds']}s")
        print(f"Report: {report_path}")
        print("=" * 70)
        
        return results


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Review Orchestrator")
    parser.add_argument(
        "--config",
        default="./orchestration/orchestration-config.json",
        help="Path to configuration file"
    )
    
    args = parser.parse_args()
    
    orchestrator = ReviewOrchestrator(args.config)
    results = orchestrator.run_full_review()
    
    sys.exit(0 if results.get("overall_success") else 1)


if __name__ == "__main__":
    main()
