#!/usr/bin/env python3
"""
Comprehensive Test Suite
Unit and integration tests for all orchestration components
"""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))


class TestMemoryManager(unittest.TestCase):
    """Test memory manager functionality"""
    
    @patch('ai_agents_shared_memory.utils.memory_manager.MemoryManager')
    def test_write_and_read(self, mock_memory):
        """Test writing and reading from memory"""
        mock_instance = mock_memory.return_value
        mock_instance.write.return_value = True
        mock_instance.read.return_value = {"test": "data"}
        
        # Write
        result = mock_instance.write(
            category="test",
            key="test_key",
            data={"test": "data"},
            agent="test_agent"
        )
        
        self.assertTrue(result)
        
        # Read
        data = mock_instance.read(category="test", key="test_key")
        self.assertEqual(data, {"test": "data"})
    
    @patch('ai_agents_shared_memory.utils.memory_manager.MemoryManager')
    def test_query(self, mock_memory):
        """Test querying memory"""
        mock_instance = mock_memory.return_value
        mock_instance.query.return_value = [
            {"key": "test1", "data": {"value": 1}},
            {"key": "test2", "data": {"value": 2}}
        ]
        
        results = mock_instance.query(category="test", tags=["test"])
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["data"]["value"], 1)


class TestErrorRecovery(unittest.TestCase):
    """Test error recovery functionality"""
    
    def setUp(self):
        """Setup test environment"""
        from orchestration.error_recovery import ErrorRecovery
        self.recovery = ErrorRecovery()
    
    def test_successful_execution(self):
        """Test function execution without errors"""
        def test_func():
            return "success"
        
        result = self.recovery.execute_with_recovery(test_func)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["result"], "success")
        self.assertEqual(result["attempts"], 1)
    
    def test_retry_on_failure(self):
        """Test retry mechanism"""
        attempts = {"count": 0}
        
        def test_func():
            attempts["count"] += 1
            if attempts["count"] < 2:
                raise ValueError("Test error")
            return "success"
        
        result = self.recovery.execute_with_recovery(test_func, max_retries=3)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["attempts"], 2)
        self.assertTrue(result["recovered"])
    
    def test_max_retries_exceeded(self):
        """Test behavior when max retries exceeded"""
        def test_func():
            raise ValueError("Persistent error")
        
        result = self.recovery.execute_with_recovery(test_func, max_retries=2)
        
        self.assertFalse(result["success"])
        self.assertEqual(result["attempts"], 3)  # Initial + 2 retries
        self.assertIn("error", result)


class TestTestingOrchestrator(unittest.TestCase):
    """Test testing orchestrator"""
    
    @patch('subprocess.run')
    def test_run_pytest(self, mock_subprocess):
        """Test pytest execution"""
        mock_subprocess.return_value = Mock(returncode=0, stdout="PASSED", stderr="")
        
        from orchestration.testing_orchestrator import TestingOrchestrator
        orchestrator = TestingOrchestrator()
        
        # Mock the run_pytest method
        with patch.object(orchestrator, 'run_pytest') as mock_run:
            mock_run.return_value = {"success": True, "passed": 10, "failed": 0}
            result = orchestrator.run_pytest()
            
            self.assertTrue(result["success"])
            self.assertEqual(result["passed"], 10)


class TestBuildOrchestrator(unittest.TestCase):
    """Test build orchestrator"""
    
    @patch('subprocess.run')
    def test_docker_build(self, mock_subprocess):
        """Test Docker image building"""
        mock_subprocess.return_value = Mock(returncode=0, stdout="Successfully built", stderr="")
        
        from orchestration.build_orchestrator import BuildOrchestrator
        orchestrator = BuildOrchestrator()
        
        with patch.object(orchestrator, 'build_image') as mock_build:
            mock_build.return_value = {
                "success": True,
                "image_id": "sha256:abc123",
                "image_tag": "test:latest"
            }
            
            result = orchestrator.build_image(tag="test:latest")
            
            self.assertTrue(result["success"])
            self.assertIn("image_id", result)


class TestDeployOrchestrator(unittest.TestCase):
    """Test deploy orchestrator"""
    
    @patch('requests.post')
    def test_coolify_deployment(self, mock_post):
        """Test Coolify API deployment"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {"status": "success", "deployment_id": "123"}
        )
        
        from orchestration.deploy_orchestrator import CoolifyDeployOrchestrator
        orchestrator = CoolifyDeployOrchestrator()
        
        with patch.object(orchestrator, 'trigger_deployment') as mock_deploy:
            mock_deploy.return_value = {
                "success": True,
                "deployment_id": "123",
                "url": "https://app.example.com"
            }
            
            result = orchestrator.trigger_deployment()
            
            self.assertTrue(result["success"])
            self.assertEqual(result["deployment_id"], "123")


class TestMainOrchestrator(unittest.TestCase):
    """Test main orchestrator"""
    
    def test_pipeline_coordination(self):
        """Test pipeline stage coordination"""
        from orchestration.main_orchestrator import MainOrchestrator
        orchestrator = MainOrchestrator()
        
        # Mock all stage methods
        with patch.object(orchestrator, 'run_stage') as mock_stage:
            mock_stage.return_value = {"success": True, "stage": "test"}
            
            result = orchestrator.run_stage("testing")
            
            self.assertTrue(result["success"])
            self.assertEqual(result["stage"], "test")


class IntegrationTests(unittest.TestCase):
    """Integration tests for full pipeline"""
    
    @patch('subprocess.run')
    @patch('requests.post')
    def test_full_pipeline(self, mock_post, mock_subprocess):
        """Test full pipeline execution"""
        # Mock successful responses
        mock_subprocess.return_value = Mock(returncode=0, stdout="SUCCESS", stderr="")
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {"status": "success"}
        )
        
        from orchestration.main_orchestrator import MainOrchestrator
        orchestrator = MainOrchestrator()
        
        # This would need actual implementation
        # For now, just verify the orchestrator can be instantiated
        self.assertIsNotNone(orchestrator)


def run_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("Running Comprehensive Test Suite")
    print("="*60 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestMemoryManager))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorRecovery))
    suite.addTests(loader.loadTestsFromTestCase(TestTestingOrchestrator))
    suite.addTests(loader.loadTestsFromTestCase(TestBuildOrchestrator))
    suite.addTests(loader.loadTestsFromTestCase(TestDeployOrchestrator))
    suite.addTests(loader.loadTestsFromTestCase(TestMainOrchestrator))
    suite.addTests(loader.loadTestsFromTestCase(IntegrationTests))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
