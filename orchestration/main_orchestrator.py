#!/usr/bin/env python3
"""
Main Orchestrator - Coordinates full CI/CD pipeline
Testing → Review → Build → Deploy
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import argparse

# Import orchestrators
from testing_orchestrator import TestingOrchestrator
from review_orchestrator import ReviewOrchestrator
from build_orchestrator import BuildOrchestrator
from deploy_orchestrator import CoolifyDeployOrchestrator


class MainOrchestrator:
    """Main orchestrator coordinating all pipeline stages"""
    
    def __init__(self, config_path: str = "./orchestration/orchestration-config.json"):
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.pipeline_config = self.config.get("pipeline", {})
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
        
        # Initialize orchestrators
        self.testing = TestingOrchestrator(config_path)
        self.review = ReviewOrchestrator(config_path)
        self.build = BuildOrchestrator(config_path)
        self.deploy = CoolifyDeployOrchestrator(config_path)
    
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
                    agent="main_orchestrator",
                    tags=["pipeline", "orchestration", "cicd"]
                )
            except Exception as e:
                print(f"Warning: Could not write to shared memory: {e}")
    
    def run_stage(self, stage: str) -> Dict:
        """Run a single pipeline stage"""
        print(f"\n{'=' * 70}")
        print(f"STAGE: {stage.upper()}")
        print(f"{'=' * 70}\n")
        
        stage_start = time.time()
        result = {"stage": stage, "success": False}
        
        try:
            if stage == "test":
                result = self.testing.run_all_tests()
            elif stage == "review":
                result = self.review.run_full_review()
            elif stage == "build":
                result = self.build.run_full_build()
            elif stage == "deploy":
                # Get image from build results
                build_memory = self.memory.read("context", "build_results") if self.memory else None
                if build_memory:
                    image_info = build_memory.get("data", {}).get("image", "myapp:latest")
                    image, tag = image_info.split(":", 1) if ":" in image_info else (image_info, "latest")
                else:
                    image, tag = "myapp", "latest"
                
                result = self.deploy.run_full_deployment(image, tag)
            else:
                result = {
                    "success": False,
                    "error": f"Unknown stage: {stage}"
                }
            
            result["stage"] = stage
            result["duration_seconds"] = round(time.time() - stage_start, 2)
            
        except Exception as e:
            result = {
                "stage": stage,
                "success": False,
                "error": str(e),
                "duration_seconds": round(time.time() - stage_start, 2)
            }
        
        return result
    
    def run_full_pipeline(self) -> Dict:
        """Run the complete CI/CD pipeline"""
        print("=" * 70)
        print("MAIN ORCHESTRATOR - CI/CD Pipeline")
        print("=" * 70)
        print(f"Pipeline: {' → '.join([s.upper() for s in self.pipeline_config.get('stages', [])])}")
        print(f"Fail Fast: {self.pipeline_config.get('fail_fast', True)}")
        print("=" * 70)
        
        start_time = time.time()
        
        # Initialize results
        results = {
            "pipeline_name": self.pipeline_config.get("name", "CI/CD Pipeline"),
            "start_time": datetime.utcnow().isoformat(),
            "end_time": None,
            "duration_seconds": 0,
            "stages": {},
            "overall_success": True,
            "failed_stage": None
        }
        
        # Update shared memory
        self._write_to_memory(
            "pipeline_status",
            {
                "status": "running",
                "stages": self.pipeline_config.get("stages", []),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Run each stage
        stages = self.pipeline_config.get("stages", ["test", "review", "build", "deploy"])
        fail_fast = self.pipeline_config.get("fail_fast", True)
        
        for stage in stages:
            # Check if stage is enabled in config
            stage_config_key = stage.replace("deploy", "deploy").replace("test", "testing")
            if not self.config.get(stage_config_key, {}).get("enabled", True):
                print(f"\n⊘ Skipping {stage.upper()} (disabled in config)")
                results["stages"][stage] = {
                    "skipped": True,
                    "reason": "Disabled in configuration"
                }
                continue
            
            # Run stage
            stage_result = self.run_stage(stage)
            results["stages"][stage] = stage_result
            
            # Check if stage failed
            stage_success = stage_result.get("overall_success", stage_result.get("success", False))
            
            if not stage_success:
                results["overall_success"] = False
                results["failed_stage"] = stage
                
                print(f"\n❌ Stage {stage.upper()} FAILED")
                
                if fail_fast:
                    print(f"\n⚠️  Stopping pipeline (fail_fast enabled)")
                    break
            else:
                print(f"\n✓ Stage {stage.upper()} PASSED")
        
        # Calculate totals
        end_time = time.time()
        results["end_time"] = datetime.utcnow().isoformat()
        results["duration_seconds"] = round(end_time - start_time, 2)
        
        # Save overall report
        report_path = self.reports_dir / f"pipeline-report-{int(time.time())}.json"
        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Update shared memory
        self._write_to_memory(
            "pipeline_results",
            {
                "success": results["overall_success"],
                "failed_stage": results["failed_stage"],
                "duration_seconds": results["duration_seconds"],
                "report_path": str(report_path),
                "timestamp": results["end_time"]
            }
        )
        
        # Print summary
        print("\n" + "=" * 70)
        print("PIPELINE SUMMARY")
        print("=" * 70)
        
        for stage, stage_result in results["stages"].items():
            if stage_result.get("skipped"):
                status = "⊘ SKIPPED"
            elif stage_result.get("overall_success", stage_result.get("success", False)):
                status = "✓ PASSED"
            else:
                status = "❌ FAILED"
            
            duration = stage_result.get("duration_seconds", 0)
            print(f"{stage.upper():15} {status:15} ({duration}s)")
        
        print("=" * 70)
        print(f"Total Duration: {results['duration_seconds']}s")
        print(f"Report: {report_path}")
        print("=" * 70)
        
        if results["overall_success"]:
            print("✓✓✓ PIPELINE SUCCESSFUL ✓✓✓")
        else:
            print(f"❌❌❌ PIPELINE FAILED at {results['failed_stage'].upper()} ❌❌❌")
        
        print("=" * 70)
        
        return results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Main CI/CD Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline
  python main_orchestrator.py --mode full
  
  # Run specific stage
  python main_orchestrator.py --stage test
  python main_orchestrator.py --stage review
  python main_orchestrator.py --stage build
  python main_orchestrator.py --stage deploy
  
  # Run multiple stages
  python main_orchestrator.py --stages test review build
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["full", "stage"],
        default="full",
        help="Run mode: full pipeline or single stage"
    )
    parser.add_argument(
        "--stage",
        choices=["test", "review", "build", "deploy"],
        help="Single stage to run (requires --mode stage)"
    )
    parser.add_argument(
        "--stages",
        nargs="+",
        choices=["test", "review", "build", "deploy"],
        help="Multiple stages to run in sequence"
    )
    parser.add_argument(
        "--config",
        default="./orchestration/orchestration-config.json",
        help="Path to configuration file"
    )
    
    args = parser.parse_args()
    
    orchestrator = MainOrchestrator(args.config)
    
    if args.mode == "full":
        # Run full pipeline
        results = orchestrator.run_full_pipeline()
    elif args.stages:
        # Run multiple stages
        results = {
            "stages": {},
            "overall_success": True
        }
        for stage in args.stages:
            stage_result = orchestrator.run_stage(stage)
            results["stages"][stage] = stage_result
            if not stage_result.get("overall_success", stage_result.get("success", False)):
                results["overall_success"] = False
        
        results["timestamp"] = datetime.utcnow().isoformat()
    elif args.stage:
        # Run single stage
        stage_result = orchestrator.run_stage(args.stage)
        results = {
            "stages": {args.stage: stage_result},
            "overall_success": stage_result.get("overall_success", stage_result.get("success", False))
        }
    else:
        print("Error: Please specify --mode full, --stage, or --stages")
        sys.exit(1)
    
    # Exit with appropriate code
    sys.exit(0 if results.get("overall_success", False) else 1)


if __name__ == "__main__":
    main()
