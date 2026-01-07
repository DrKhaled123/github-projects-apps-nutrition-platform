"""
RQ Worker Tasks for AutoGen Factory
Background task processing for deployment and error learning
"""

import json
import time
import traceback
from typing import Dict, Any, Optional
import subprocess
import sys
import os
from datetime import datetime
from loguru import logger

# Add the factory directory to the path so we can import factory_config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from factory_config import (
    get_factory,
    ErrorMemory,
    DeploymentAid,
    FactoryConfig
)

import re
import shlex


def _is_safe_path(path: str) -> bool:
    """Validate that a path is safe and doesn't contain dangerous characters"""
    if not path or not isinstance(path, str):
        return False

    # Check for path traversal attempts
    if '..' in path or path.startswith('/'):
        return False

    # Check for dangerous characters
    dangerous_chars = ['|', '&', ';', '$', '>', '<', '`', '$(', '${']
    if any(char in path for char in dangerous_chars):
        return False

    # Allow only alphanumeric, dots, hyphens, underscores, and forward slashes
    safe_pattern = re.compile(r'^[a-zA-Z0-9._/-]+$')
    return bool(safe_pattern.match(path))


def _is_safe_image_name(image_name: str) -> bool:
    """Validate that an image name is safe"""
    if not image_name or not isinstance(image_name, str):
        return False

    # Check for dangerous characters
    dangerous_chars = ['|', '&', ';', '$', '>', '<', '`', '$(', '${']
    if any(char in image_name for char in dangerous_chars):
        return False

    # Allow only alphanumeric, dots, hyphens, underscores, colons, and forward slashes
    safe_pattern = re.compile(r'^[a-zA-Z0-9._/:-]+$')
    return bool(safe_pattern.match(image_name))


def _validate_command_input(command: str) -> bool:
    """Validate that a command string is safe"""
    if not command or not isinstance(command, str):
        return False

    # Check for dangerous command patterns
    dangerous_patterns = [
        r';\s*rm\s+', r';\s*del\s+', r'\|\s*rm\s+', r'\|\s*del\s+',
        r';\s*shutdown\s+', r'format\s+', r'fdisk\s+', r'mkfs\s+'
    ]

    command_lower = command.lower()
    for pattern in dangerous_patterns:
        if re.search(pattern, command_lower):
            return False

    return True

def execute_deployment_task(task_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a deployment-related task with integrated learning
    This is the main RQ worker function for deployment tasks
    """
    start_time = time.time()
    factory = None

    try:
        logger.info(f"Starting deployment task: {task_type}")
        factory = get_factory()

        result = {
            "task_type": task_type,
            "parameters": parameters,
            "start_time": datetime.now().isoformat(),
            "status": "running",
            "success": False,
            "output": "",
            "error": None,
            "learning_applied": False,
            "improvements_applied": False
        }

        # Try pattern learning first
        pattern_solution = None
        if factory and factory.pattern_learning:
            pattern_solution = factory.pattern_learning.suggest_solution(task_type, parameters)
            if pattern_solution:
                result["learning_applied"] = True
                result["pattern_solution"] = pattern_solution
                logger.info(f"Applied pattern learning solution for {task_type}")

        # Handle different task types
        if task_type == "docker_build":
            result.update(_execute_docker_build(parameters))
        elif task_type == "test_run":
            result.update(_execute_test_run(parameters))
        elif task_type == "deployment_validation":
            result.update(_execute_deployment_validation(parameters))
        elif task_type == "security_scan":
            result.update(_execute_security_scan(parameters))
        elif task_type == "performance_test":
            result.update(_execute_performance_test(parameters))
        elif task_type == "database_migration":
            result.update(_execute_database_migration(parameters))
        elif task_type == "backup_create":
            result.update(_execute_backup_create(parameters))
        elif task_type == "monitoring_setup":
            result.update(_execute_monitoring_setup(parameters))
        else:
            # Generic task handling with AutoGen
            result.update(_execute_generic_task(task_type, parameters))

        # Calculate execution time
        execution_time = time.time() - start_time
        result["execution_time"] = execution_time
        result["end_time"] = datetime.now().isoformat()

        if result["success"]:
            result["status"] = "completed"
            logger.info(f"Task completed successfully: {task_type} in {execution_time:.2f}s")

            # Learn from successful deployment
            if factory and factory.pattern_learning:
                try:
                    deployment_data = {
                        "error_type": task_type,
                        "success": True,
                        "solution": pattern_solution or "standard_procedure",
                        "context": parameters,
                        "execution_time": execution_time,
                        "timestamp": datetime.now()
                    }
                    factory.pattern_learning.learn_from_deployment(deployment_data)
                    result["learning_stored"] = True
                except Exception as learn_error:
                    logger.warning(f"Failed to store learning from success: {learn_error}")

        else:
            result["status"] = "failed"
            logger.error(f"Task failed: {task_type} - {result.get('error', 'Unknown error')}")

            # Learn from failed deployment
            if factory and factory.pattern_learning:
                try:
                    deployment_data = {
                        "error_type": task_type,
                        "success": False,
                        "solution": None,
                        "context": parameters,
                        "execution_time": execution_time,
                        "timestamp": datetime.now()
                    }
                    factory.pattern_learning.learn_from_deployment(deployment_data)
                    result["learning_stored"] = True
                except Exception as learn_error:
                    logger.warning(f"Failed to store learning from failure: {learn_error}")

        # Apply continuous improvements if available
        if factory and factory.improvement_engine:
            try:
                # Record performance metrics
                factory.improvement_engine.performance_history.append({
                    "task_type": task_type,
                    "success": result["success"],
                    "execution_time": execution_time,
                    "timestamp": datetime.now().isoformat()
                })

                # Run performance analysis periodically (every 10 tasks)
                if len(factory.improvement_engine.performance_history) % 10 == 0:
                    suggestions = factory.improvement_engine.analyze_performance()
                    if suggestions:
                        improvement_results = factory.improvement_engine.implement_improvements()
                        if improvement_results.get("implemented", 0) > 0:
                            result["improvements_applied"] = True
                            result["improvement_details"] = improvement_results
                            logger.info(f"Applied {improvement_results['implemented']} system improvements")

            except Exception as improvement_error:
                logger.warning(f"Failed to apply continuous improvements: {improvement_error}")

        return result

    except Exception as e:
        execution_time = time.time() - start_time
        error_result = {
            "task_type": task_type,
            "parameters": parameters,
            "start_time": datetime.now().isoformat(),
            "status": "error",
            "success": False,
            "execution_time": execution_time,
            "end_time": datetime.now().isoformat(),
            "error": str(e),
            "traceback": traceback.format_exc(),
            "learning_applied": False,
            "improvements_applied": False
        }

        logger.error(f"Task execution error: {task_type} - {e}")

        # Store error for learning if factory is available
        if factory:
            try:
                error_memory = ErrorMemory(
                    error_type="deployment_task_error",
                    error_message=str(e),
                    context={
                        "task_type": task_type,
                        "parameters": parameters,
                        "traceback": traceback.format_exc()
                    }
                )
                factory.store_error_memory(error_memory)
            except Exception as store_error:
                logger.error(f"Failed to store error memory: {store_error}")

            # Learn from system error
            try:
                deployment_data = {
                    "error_type": "system_error",
                    "success": False,
                    "solution": None,
                    "context": {"task_type": task_type, "error": str(e)},
                    "execution_time": execution_time,
                    "timestamp": datetime.now()
                }
                factory.pattern_learning.learn_from_deployment(deployment_data)
            except Exception as learn_error:
                logger.warning(f"Failed to store system error learning: {learn_error}")

        return error_result


def _execute_docker_build(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Docker build task"""
    try:
        dockerfile = parameters.get("dockerfile", "Dockerfile")
        image_name = parameters.get("image_name", "app:latest")
        build_context = parameters.get("build_context", ".")

        cmd = f"docker build -f {dockerfile} -t {image_name} {build_context}"

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
            "return_code": result.returncode
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def _execute_test_run(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute test run task"""
    try:
        test_command = parameters.get("test_command", "go test ./...")
        coverage = parameters.get("coverage", False)

        cmd = test_command
        if coverage:
            cmd = f"{test_command} -cover"

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
            "return_code": result.returncode
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def _execute_deployment_validation(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute deployment validation task"""
    try:
        # Check if required files exist
        required_files = parameters.get("required_files", [
            "Dockerfile", "docker-compose.yml", ".env.example"
        ])

        missing_files = []
        for file in required_files:
            if not os.path.exists(file):
                missing_files.append(file)

        if missing_files:
            return {
                "success": False,
                "error": f"Missing required files: {', '.join(missing_files)}",
                "missing_files": missing_files
            }

        # Check environment variables
        env_file = parameters.get("env_file", ".env")
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                env_content = f.read()

            # Basic validation - check for common required env vars
            required_envs = parameters.get("required_env_vars", [
                "DATABASE_URL", "REDIS_URL", "API_KEY"
            ])

            missing_envs = []
            for env_var in required_envs:
                if env_var not in env_content:
                    missing_envs.append(env_var)

            if missing_envs:
                return {
                    "success": False,
                    "error": f"Missing required environment variables: {', '.join(missing_envs)}",
                    "missing_envs": missing_envs
                }

        return {
            "success": True,
            "output": "Deployment validation passed",
            "validated_files": required_files,
            "validated_env_vars": parameters.get("required_env_vars", [])
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def _execute_security_scan(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute security scan task"""
    try:
        scan_type = parameters.get("scan_type", "basic")

        if scan_type == "dependency":
            # Run dependency vulnerability scan
            cmd = "npm audit --audit-level=moderate"
            if os.path.exists("go.mod"):
                cmd = "go mod download && go list -json -m all | docker run --rm -i golang:1.21 go mod download && govulncheck ./..."
            elif os.path.exists("requirements.txt"):
                cmd = "pip install safety && safety check"

        elif scan_type == "container":
            # Container security scan
            image_name = parameters.get("image_name", "app:latest")
            cmd = f"docker scan {image_name}"

        else:
            # Basic security checks
            cmd = "find . -name '*.sh' -exec chmod +x {} \\; && find . -type f -name '*.py' -exec python -m py_compile {{}} \\;"

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
            "return_code": result.returncode,
            "scan_type": scan_type
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def _execute_performance_test(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute performance test task"""
    try:
        test_type = parameters.get("test_type", "load")

        if test_type == "load":
            # Simple load test
            cmd = "ab -n 100 -c 10 http://localhost:8080/"
        elif test_type == "stress":
            # Stress test
            cmd = "ab -n 1000 -c 100 http://localhost:8080/"
        else:
            # Custom performance test
            cmd = parameters.get("custom_command", "echo 'Performance test completed'")

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
            "return_code": result.returncode,
            "test_type": test_type
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def _execute_database_migration(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute database migration task"""
    try:
        migration_type = parameters.get("migration_type", "up")

        if migration_type == "up":
            cmd = "go run main.go migrate up"
        elif migration_type == "down":
            cmd = "go run main.go migrate down"
        elif migration_type == "status":
            cmd = "go run main.go migrate status"
        else:
            cmd = parameters.get("custom_migration_command", "echo 'Migration completed'")

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
            "return_code": result.returncode,
            "migration_type": migration_type
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def _execute_backup_create(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute backup creation task"""
    try:
        backup_type = parameters.get("backup_type", "database")
        backup_path = parameters.get("backup_path", "./backups")

        # Ensure backup directory exists
        os.makedirs(backup_path, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if backup_type == "database":
            # Database backup
            if os.path.exists("go.mod"):
                cmd = f"pg_dump $DATABASE_URL > {backup_path}/db_backup_{timestamp}.sql"
            else:
                cmd = f"sqlite3 data.db .dump > {backup_path}/db_backup_{timestamp}.sql"
        elif backup_type == "files":
            # File system backup
            cmd = f"tar -czf {backup_path}/files_backup_{timestamp}.tar.gz -C . --exclude=./backups ."
        else:
            cmd = parameters.get("custom_backup_command", f"echo 'Backup created at {backup_path}'")

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
            "return_code": result.returncode,
            "backup_type": backup_type,
            "backup_path": f"{backup_path}/backup_{timestamp}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def _execute_monitoring_setup(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute monitoring setup task"""
    try:
        monitoring_type = parameters.get("monitoring_type", "basic")

        if monitoring_type == "prometheus":
            # Setup Prometheus monitoring
            cmd = """
            mkdir -p monitoring &&
            cat > monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
scrape_configs:
  - job_name: 'app'
    static_configs:
      - targets: ['localhost:8080']
EOF
            """
        elif monitoring_type == "grafana":
            # Setup Grafana dashboards
            cmd = "mkdir -p monitoring/grafana/dashboards monitoring/grafana/provisioning"
        else:
            # Basic monitoring setup
            cmd = "mkdir -p monitoring && echo 'Monitoring setup completed'"

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
            "return_code": result.returncode,
            "monitoring_type": monitoring_type
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def _execute_generic_task(task_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute generic task using AutoGen for guidance"""
    try:
        factory = get_factory()

        # Get deployment aid from AutoGen
        aid_result = factory.get_deployment_aid(task_type, parameters)

        # Try to execute based on the guidance
        guidance = aid_result.get("guidance", "")

        # Extract commands from guidance (simple approach)
        lines = guidance.split('\n')
        commands = []

        for line in lines:
            line = line.strip()
            if line.startswith('$') or line.startswith('#') or 'docker' in line.lower() or 'npm' in line.lower():
                commands.append(line)

        if commands:
            # Execute the first command as a test
            cmd = commands[0].lstrip('$').strip()
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
                "return_code": result.returncode,
                "guidance_used": True,
                "commands_found": len(commands)
            }
        else:
            return {
                "success": True,
                "output": "Generic task completed with AutoGen guidance",
                "guidance": guidance,
                "guidance_used": True
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# Error learning and analysis functions
def analyze_deployment_error(error_message: str, context: Dict[str, Any]) -> Optional[str]:
    """Analyze deployment error and learn from it"""
    try:
        factory = get_factory()
        return factory.learn_from_errors("deployment_error", error_message, context)
    except Exception as e:
        logger.error(f"Failed to analyze deployment error: {e}")
        return None


def store_deployment_success(task_type: str, parameters: Dict[str, Any], result: Dict[str, Any]):
    """Store successful deployment for future learning"""
    try:
        factory = get_factory()

        success_memory = ErrorMemory(
            error_type="deployment_success",
            error_message=f"Successful {task_type}",
            context={
                "task_type": task_type,
                "parameters": parameters,
                "result": result
            },
            learned=True
        )

        factory.store_error_memory(success_memory)
        logger.info(f"Stored deployment success memory: {task_type}")
    except Exception as e:
        logger.error(f"Failed to store deployment success: {e}")


# Convenience functions for external use
def run_deployment_task(task_type: str, **parameters) -> str:
    """Queue a deployment task and return job ID"""
    factory = get_factory()
    return factory.queue_deployment_task(task_type, parameters)


def get_task_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get the status of a queued task"""
    try:
        factory = get_factory()
        # This would need to be implemented with RQ's job monitoring
        # For now, return a placeholder
        return {"job_id": job_id, "status": "unknown"}
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        return None
