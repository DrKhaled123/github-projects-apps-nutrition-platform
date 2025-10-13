#!/usr/bin/env python3
"""
Build Orchestrator Module
Builds, optimizes, and pushes Docker images
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import os
import hashlib


class BuildOrchestrator:
    """Orchestrates Docker image building"""
    
    def __init__(self, config_path: str = "./orchestration/orchestration-config.json"):
        self.config = self._load_config(config_path)
        self.build_config = self.config["build"]
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
                    agent="build_orchestrator",
                    tags=["build", "orchestration", "docker"]
                )
            except Exception as e:
                print(f"Warning: Could not write to shared memory: {e}")
    
    def _run_command(self, command: List[str], timeout: int = 600) -> Dict:
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
    
    def get_git_commit(self) -> str:
        """Get current Git commit hash"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return "unknown"
    
    def get_version(self) -> str:
        """Get version from package file or default"""
        # Try package.json
        if Path("package.json").exists():
            try:
                with open("package.json", 'r') as f:
                    pkg = json.load(f)
                    return pkg.get("version", "1.0.0")
            except Exception:
                pass
        
        # Try setup.py or pyproject.toml
        # Default
        return "1.0.0"
    
    def generate_tags(self) -> List[str]:
        """Generate Docker image tags based on strategy"""
        tagging_config = self.build_config.get("tagging", {})
        tag_templates = tagging_config.get("tags", ["latest"])
        
        tags = []
        replacements = {
            "version": self.get_version(),
            "git_commit": self.get_git_commit(),
            "timestamp": datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        }
        
        for template in tag_templates:
            tag = template
            for key, value in replacements.items():
                tag = tag.replace(f"{{{key}}}", value)
            tags.append(tag)
        
        return tags
    
    def build_image(self) -> Dict:
        """Build Docker image"""
        print("Building Docker image...")
        
        docker_config = self.build_config.get("docker", {})
        dockerfile = docker_config.get("file", "Dockerfile")
        context = docker_config.get("context", ".")
        platform = docker_config.get("platform", "linux/amd64")
        
        # Generate tags
        tags = self.generate_tags()
        repository = self.build_config.get("registry", {}).get("repository", "myapp")
        
        # Build command
        cmd = ["docker", "build"]
        
        # Add platform
        cmd.extend(["--platform", platform])
        
        # Add dockerfile
        cmd.extend(["-f", dockerfile])
        
        # Add build args
        build_args = docker_config.get("build_args", {})
        for key, value in build_args.items():
            cmd.extend(["--build-arg", f"{key}={value}"])
        
        # Add cache options
        if docker_config.get("cache", True):
            cmd.append("--cache-from")
            cmd.append(f"{repository}:latest")
        
        # Add tags
        for tag in tags:
            cmd.extend(["-t", f"{repository}:{tag}"])
        
        # Add context
        cmd.append(context)
        
        print(f"Command: {' '.join(cmd)}")
        
        # Update shared memory
        self._write_to_memory(
            "pipeline_status",
            {
                "stage": "build",
                "status": "building",
                "tags": tags,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Execute build
        result = self._run_command(cmd, timeout=1800)  # 30 min timeout
        
        return {
            "success": result["success"],
            "tags": tags,
            "repository": repository,
            "output": result["stdout"],
            "errors": result["stderr"]
        }
    
    def scan_image(self, image_name: str) -> Dict:
        """Scan image for vulnerabilities using Trivy"""
        print(f"Scanning image {image_name} for vulnerabilities...")
        
        scan_config = self.build_config.get("scan", {})
        if not scan_config.get("enabled", True):
            return {"skipped": True}
        
        tool = scan_config.get("tool", "trivy")
        severity = scan_config.get("fail_on_severity", "high").upper()
        
        cmd = ["trivy", "image", "--format", "json", "--severity", severity, image_name]
        
        result = self._run_command(cmd, timeout=300)
        
        vulnerabilities = []
        try:
            if result["stdout"]:
                scan_output = json.loads(result["stdout"])
                vulnerabilities = scan_output.get("Results", [])
        except Exception:
            pass
        
        # Count by severity
        severity_counts = {}
        for vuln_result in vulnerabilities:
            for vuln in vuln_result.get("Vulnerabilities", []):
                sev = vuln.get("Severity", "UNKNOWN")
                severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        critical_count = severity_counts.get("CRITICAL", 0) + severity_counts.get("HIGH", 0)
        
        return {
            "tool": tool,
            "success": critical_count == 0,
            "severity_counts": severity_counts,
            "vulnerabilities": vulnerabilities,
            "fail_threshold": severity
        }
    
    def optimize_image(self, image_name: str) -> Dict:
        """Optimize Docker image (optional)"""
        optimization_config = self.build_config.get("optimization", {})
        if not optimization_config.get("enabled", True):
            return {"skipped": True}
        
        print(f"Optimizing image {image_name}...")
        
        # Get image size before
        size_before = self._get_image_size(image_name)
        
        # Currently, optimization is done at build time with multi-stage builds
        # This is a placeholder for additional optimization tools like dive, etc.
        
        size_after = self._get_image_size(image_name)
        
        return {
            "success": True,
            "size_before_mb": size_before,
            "size_after_mb": size_after,
            "savings_mb": size_before - size_after
        }
    
    def _get_image_size(self, image_name: str) -> float:
        """Get Docker image size in MB"""
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", image_name, "--format={{.Size}}"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                size_bytes = int(result.stdout.strip())
                return round(size_bytes / (1024 * 1024), 2)
        except Exception:
            pass
        return 0.0
    
    def push_image(self, repository: str, tags: List[str]) -> Dict:
        """Push Docker image to registry"""
        print("Pushing image to registry...")
        
        registry_config = self.build_config.get("registry", {})
        
        # Login to registry (if credentials provided)
        username = os.getenv(registry_config.get("username", "").replace("${", "").replace("}", ""))
        password = os.getenv(registry_config.get("password", "").replace("${", "").replace("}", ""))
        
        if username and password:
            registry_url = registry_config.get("url", "")
            login_cmd = ["docker", "login", registry_url, "-u", username, "--password-stdin"]
            login_result = subprocess.run(login_cmd, input=password, capture_output=True, text=True)
            
            if login_result.returncode != 0:
                return {
                    "success": False,
                    "error": "Failed to login to registry",
                    "output": login_result.stderr
                }
        
        # Push each tag
        push_results = {}
        for tag in tags:
            image_name = f"{repository}:{tag}"
            print(f"Pushing {image_name}...")
            
            cmd = ["docker", "push", image_name]
            result = self._run_command(cmd, timeout=600)
            
            push_results[tag] = {
                "success": result["success"],
                "output": result["stdout"],
                "errors": result["stderr"]
            }
        
        all_success = all(r["success"] for r in push_results.values())
        
        return {
            "success": all_success,
            "tags": list(push_results.keys()),
            "results": push_results
        }
    
    def run_full_build(self) -> Dict:
        """Run complete build process"""
        print("=" * 70)
        print("BUILD ORCHESTRATOR - Building Docker Image")
        print("=" * 70)
        
        start_time = time.time()
        
        # Update shared memory
        self._write_to_memory(
            "pipeline_status",
            {
                "stage": "build",
                "status": "running",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        results = {
            "start_time": datetime.utcnow().isoformat(),
            "end_time": None,
            "duration_seconds": 0,
            "overall_success": True
        }
        
        # Build image
        print("\n--- Building Image ---")
        build_result = self.build_image()
        results["build"] = build_result
        
        if not build_result["success"]:
            results["overall_success"] = False
            print("❌ Build failed")
        else:
            print("✓ Build successful")
            
            # Get first tag as primary image
            primary_image = f"{build_result['repository']}:{build_result['tags'][0]}"
            
            # Scan image
            print("\n--- Scanning Image ---")
            scan_result = self.scan_image(primary_image)
            results["scan"] = scan_result
            
            if not scan_result.get("skipped") and not scan_result.get("success"):
                print("⚠️  Security vulnerabilities found")
                if self.build_config.get("scan", {}).get("fail_on_severity"):
                    results["overall_success"] = False
            
            # Optimize image
            print("\n--- Optimizing Image ---")
            optimize_result = self.optimize_image(primary_image)
            results["optimize"] = optimize_result
            
            # Push image
            if results["overall_success"]:
                print("\n--- Pushing Image ---")
                push_result = self.push_image(build_result["repository"], build_result["tags"])
                results["push"] = push_result
                
                if not push_result["success"]:
                    results["overall_success"] = False
                    print("❌ Push failed")
                else:
                    print("✓ Push successful")
        
        end_time = time.time()
        results["end_time"] = datetime.utcnow().isoformat()
        results["duration_seconds"] = round(end_time - start_time, 2)
        
        # Save report
        report_path = self.reports_dir / f"build-report-{int(time.time())}.json"
        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Update shared memory
        self._write_to_memory(
            "build_results",
            {
                "success": results["overall_success"],
                "duration_seconds": results["duration_seconds"],
                "image": f"{build_result.get('repository', '')}:{build_result.get('tags', [''])[0]}",
                "report_path": str(report_path),
                "timestamp": results["end_time"]
            }
        )
        
        print("\n" + "=" * 70)
        if results["overall_success"]:
            print("✓ BUILD SUCCESSFUL")
        else:
            print("❌ BUILD FAILED")
        print(f"Duration: {results['duration_seconds']}s")
        print(f"Report: {report_path}")
        print("=" * 70)
        
        return results


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Build Orchestrator")
    parser.add_argument(
        "--config",
        default="./orchestration/orchestration-config.json",
        help="Path to configuration file"
    )
    
    args = parser.parse_args()
    
    orchestrator = BuildOrchestrator(args.config)
    results = orchestrator.run_full_build()
    
    sys.exit(0 if results.get("overall_success") else 1)


if __name__ == "__main__":
    main()
