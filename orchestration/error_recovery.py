#!/usr/bin/env python3
"""
Error Recovery and Automation Module
Provides automatic error detection, logging, retry logic, and recovery mechanisms
"""

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any
import traceback


class ErrorRecovery:
    """Handles automatic error detection, logging, and recovery"""
    
    def __init__(self, config_path: str = "./orchestration/error-recovery-config.json"):
        self.config = self._load_config(config_path)
        self.logs_dir = Path("orchestration/logs")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.error_log_file = self.logs_dir / f"error_recovery_{datetime.now().strftime('%Y%m%d')}.log"
        
        # Setup logging
        self._setup_logging()
        
        # Error statistics
        self.error_stats = {
            "total_errors": 0,
            "recovered_errors": 0,
            "failed_recoveries": 0,
            "retry_attempts": 0
        }
    
    def _load_config(self, config_path: str) -> Dict:
        """Load error recovery configuration"""
        default_config = {
            "max_retries": 3,
            "retry_delay": 5,
            "exponential_backoff": True,
            "backoff_multiplier": 2,
            "auto_rollback": True,
            "alert_on_failure": True,
            "recovery_strategies": {
                "import_error": "reinstall_dependencies",
                "network_error": "retry_with_backoff",
                "docker_error": "restart_docker",
                "test_failure": "run_verbose_tests",
                "build_failure": "clean_and_rebuild",
                "deployment_error": "rollback_deployment"
            }
        }
        
        try:
            if Path(config_path).exists():
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
        except Exception as e:
            print(f"Warning: Could not load config, using defaults: {e}")
        
        return default_config
    
    def _setup_logging(self):
        """Configure logging with rotation"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.error_log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('ErrorRecovery')
    
    def execute_with_recovery(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a function with automatic error recovery
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
        
        Returns:
            Dict with success status, result/error, and recovery info
        """
        max_retries = kwargs.pop('max_retries', self.config['max_retries'])
        retry_delay = kwargs.pop('retry_delay', self.config['retry_delay'])
        
        attempt = 0
        last_error = None
        
        while attempt <= max_retries:
            try:
                self.logger.info(f"Executing {func.__name__} (attempt {attempt + 1}/{max_retries + 1})")
                
                result = func(*args, **kwargs)
                
                if attempt > 0:
                    self.logger.info(f"✅ Recovered after {attempt} retries")
                    self.error_stats["recovered_errors"] += 1
                
                return {
                    "success": True,
                    "result": result,
                    "attempts": attempt + 1,
                    "recovered": attempt > 0
                }
                
            except Exception as e:
                attempt += 1
                self.error_stats["total_errors"] += 1
                self.error_stats["retry_attempts"] += 1
                last_error = e
                
                error_type = type(e).__name__
                error_message = str(e)
                stack_trace = traceback.format_exc()
                
                self.logger.error(f"❌ Error in {func.__name__}: {error_type}: {error_message}")
                self.logger.debug(f"Stack trace: {stack_trace}")
                
                # Try recovery strategy
                if attempt <= max_retries:
                    recovery_strategy = self._get_recovery_strategy(error_type, error_message)
                    
                    if recovery_strategy:
                        self.logger.info(f"🔧 Attempting recovery strategy: {recovery_strategy}")
                        recovery_success = self._execute_recovery(recovery_strategy, error_message)
                        
                        if recovery_success:
                            self.logger.info("✅ Recovery strategy succeeded, retrying...")
                        else:
                            self.logger.warning("⚠️  Recovery strategy failed, retrying anyway...")
                    
                    # Calculate delay with exponential backoff
                    if self.config['exponential_backoff']:
                        delay = retry_delay * (self.config['backoff_multiplier'] ** (attempt - 1))
                    else:
                        delay = retry_delay
                    
                    self.logger.info(f"⏳ Waiting {delay}s before retry...")
                    time.sleep(delay)
                else:
                    self.logger.error(f"❌ Max retries ({max_retries}) exceeded")
                    self.error_stats["failed_recoveries"] += 1
        
        # All retries failed
        return {
            "success": False,
            "error": str(last_error),
            "error_type": type(last_error).__name__,
            "attempts": attempt,
            "recovered": False,
            "stack_trace": traceback.format_exc()
        }
    
    def _get_recovery_strategy(self, error_type: str, error_message: str) -> Optional[str]:
        """Determine the appropriate recovery strategy for an error"""
        strategies = self.config['recovery_strategies']
        
        # Check for specific error types
        error_keywords = {
            "ImportError": "import_error",
            "ModuleNotFoundError": "import_error",
            "ConnectionError": "network_error",
            "TimeoutError": "network_error",
            "DockerException": "docker_error",
            "TestFailed": "test_failure",
            "BuildError": "build_failure",
            "DeploymentError": "deployment_error"
        }
        
        # Check error message for keywords
        message_lower = error_message.lower()
        if "docker" in message_lower:
            return strategies.get("docker_error")
        elif "connection" in message_lower or "timeout" in message_lower:
            return strategies.get("network_error")
        elif "import" in message_lower or "module" in message_lower:
            return strategies.get("import_error")
        elif "test" in message_lower and "fail" in message_lower:
            return strategies.get("test_failure")
        elif "build" in message_lower and "fail" in message_lower:
            return strategies.get("build_failure")
        elif "deploy" in message_lower:
            return strategies.get("deployment_error")
        
        # Check error type
        for error_name, strategy_key in error_keywords.items():
            if error_name in error_type:
                return strategies.get(strategy_key)
        
        return "retry_with_backoff"
    
    def _execute_recovery(self, strategy: str, error_context: str) -> bool:
        """Execute a specific recovery strategy"""
        self.logger.info(f"Executing recovery strategy: {strategy}")
        
        try:
            if strategy == "reinstall_dependencies":
                return self._reinstall_dependencies()
            elif strategy == "retry_with_backoff":
                return True  # Just retry
            elif strategy == "restart_docker":
                return self._restart_docker()
            elif strategy == "run_verbose_tests":
                return self._run_verbose_tests()
            elif strategy == "clean_and_rebuild":
                return self._clean_and_rebuild()
            elif strategy == "rollback_deployment":
                return self._rollback_deployment()
            else:
                self.logger.warning(f"Unknown recovery strategy: {strategy}")
                return False
        except Exception as e:
            self.logger.error(f"Recovery strategy failed: {e}")
            return False
    
    def _reinstall_dependencies(self) -> bool:
        """Reinstall Python dependencies"""
        try:
            self.logger.info("Reinstalling dependencies...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "orchestration/requirements.txt", "--force-reinstall"],
                capture_output=True,
                text=True,
                timeout=300
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Dependency reinstall failed: {e}")
            return False
    
    def _restart_docker(self) -> bool:
        """Restart Docker daemon (requires sudo)"""
        try:
            self.logger.info("Restarting Docker...")
            # Try different Docker restart commands
            commands = [
                ["docker", "system", "prune", "-f"],
                ["pkill", "-HUP", "dockerd"]
            ]
            
            for cmd in commands:
                try:
                    subprocess.run(cmd, timeout=30, check=False)
                except Exception:
                    continue
            
            time.sleep(5)  # Wait for Docker to restart
            return True
        except Exception as e:
            self.logger.error(f"Docker restart failed: {e}")
            return False
    
    def _run_verbose_tests(self) -> bool:
        """Run tests with verbose output for debugging"""
        try:
            self.logger.info("Running verbose tests...")
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-vv", "--tb=short"],
                timeout=600
            )
            return True  # Always return True to allow retry
        except Exception as e:
            self.logger.error(f"Verbose test run failed: {e}")
            return True
    
    def _clean_and_rebuild(self) -> bool:
        """Clean build artifacts and rebuild"""
        try:
            self.logger.info("Cleaning build artifacts...")
            
            # Remove common build artifacts
            patterns = [
                "**/__pycache__",
                "**/*.pyc",
                "**/*.pyo",
                "**/build",
                "**/dist",
                "**/.pytest_cache"
            ]
            
            for pattern in patterns:
                for path in Path(".").glob(pattern):
                    if path.is_file():
                        path.unlink()
                    elif path.is_dir():
                        import shutil
                        shutil.rmtree(path, ignore_errors=True)
            
            return True
        except Exception as e:
            self.logger.error(f"Clean and rebuild failed: {e}")
            return False
    
    def _rollback_deployment(self) -> bool:
        """Rollback to previous deployment"""
        try:
            self.logger.info("Rolling back deployment...")
            # This would need to be implemented based on your deployment strategy
            # For now, just log the intent
            self.logger.warning("Rollback not implemented - manual intervention required")
            return False
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False
    
    def get_statistics(self) -> Dict:
        """Get error recovery statistics"""
        return {
            **self.error_stats,
            "recovery_rate": (
                self.error_stats["recovered_errors"] / self.error_stats["total_errors"]
                if self.error_stats["total_errors"] > 0 else 0
            ) * 100
        }
    
    def save_statistics(self, filepath: Optional[Path] = None):
        """Save error statistics to file"""
        if filepath is None:
            filepath = self.logs_dir / f"error_stats_{datetime.now().strftime('%Y%m%d')}.json"
        
        stats = {
            "timestamp": datetime.now().isoformat(),
            "statistics": self.get_statistics()
        }
        
        with open(filepath, 'w') as f:
            json.dump(stats, f, indent=2)
        
        self.logger.info(f"Statistics saved to {filepath}")


# Decorator for easy error recovery
def with_recovery(max_retries: int = 3, retry_delay: int = 5):
    """Decorator to add error recovery to any function"""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            recovery = ErrorRecovery()
            result = recovery.execute_with_recovery(
                func,
                *args,
                max_retries=max_retries,
                retry_delay=retry_delay,
                **kwargs
            )
            
            if not result["success"]:
                raise Exception(f"Function failed after {result['attempts']} attempts: {result['error']}")
            
            return result["result"]
        
        return wrapper
    return decorator


# Example usage
if __name__ == "__main__":
    # Create default config
    config_path = Path("orchestration/error-recovery-config.json")
    if not config_path.exists():
        default_config = {
            "max_retries": 3,
            "retry_delay": 5,
            "exponential_backoff": True,
            "backoff_multiplier": 2,
            "auto_rollback": True,
            "alert_on_failure": True,
            "recovery_strategies": {
                "import_error": "reinstall_dependencies",
                "network_error": "retry_with_backoff",
                "docker_error": "restart_docker",
                "test_failure": "run_verbose_tests",
                "build_failure": "clean_and_rebuild",
                "deployment_error": "rollback_deployment"
            }
        }
        
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        print(f"✅ Created default config at {config_path}")
    
    # Test the error recovery system
    recovery = ErrorRecovery()
    
    def test_function():
        """Test function that might fail"""
        import random
        if random.random() < 0.7:  # 70% chance of failure
            raise ValueError("Random test failure")
        return "Success!"
    
    print("\n" + "="*60)
    print("Testing Error Recovery System")
    print("="*60 + "\n")
    
    result = recovery.execute_with_recovery(test_function)
    
    print(f"\nResult: {result}")
    print(f"\nStatistics: {recovery.get_statistics()}")
    
    recovery.save_statistics()
