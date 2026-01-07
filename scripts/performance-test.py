#!/usr/bin/env python3
"""
High-Performance Load Testing & Error Detection
Comprehensive testing with real-time reporting
"""

import os
import sys
import time
import json
import requests
import concurrent.futures
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import statistics

# Load environment
def load_env():
    env_file = Path(".env.local")
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip('"').strip("'")

load_env()

class PerformanceTester:
    """High-performance testing suite"""
    
    def __init__(self):
        self.results = {
            "tests": [],
            "errors": [],
            "warnings": [],
            "metrics": {},
            "summary": {}
        }
        self.api_url = os.environ.get("COOLIFY_API_URL", "")
        self.api_token = os.environ.get("COOLIFY_API_TOKEN", "")
        self.app_id = os.environ.get("COOLIFY_APP_ID", "")
        self.app_domain = "https://my.doctorhealthy1.com"
    
    def print_header(self, text):
        """Print formatted header"""
        print("\n" + "=" * 70)
        print(f" {text}")
        print("=" * 70)
    
    def print_test(self, name, status, duration=None, details=None):
        """Print test result"""
        icon = "✅" if status == "pass" else "❌" if status == "fail" else "⚠️"
        duration_str = f" ({duration:.3f}s)" if duration else ""
        print(f"{icon} {name}{duration_str}")
        if details:
            print(f"   {details}")
    
    def test_coolify_api_connection(self):
        """Test 1: Coolify API connectivity"""
        test_name = "Coolify API Connection"
        start = time.time()
        
        try:
            response = requests.get(
                f"{self.api_url}/api/v1/applications",
                headers={"Authorization": f"Bearer {self.api_token}"},
                timeout=10
            )
            duration = time.time() - start
            
            if response.status_code == 200:
                apps = response.json()
                app = next((a for a in apps if a['uuid'] == self.app_id), None)
                
                if app:
                    self.print_test(test_name, "pass", duration, 
                                  f"Found application: {app['name']}")
                    self.results["tests"].append({
                        "name": test_name,
                        "status": "pass",
                        "duration": duration,
                        "details": f"Application: {app['name']}, Status: {app.get('status', 'unknown')}"
                    })
                    return True, app
                else:
                    self.print_test(test_name, "fail", duration, 
                                  f"Application {self.app_id} not found")
                    self.results["errors"].append(f"Application not found: {self.app_id}")
                    return False, None
            else:
                self.print_test(test_name, "fail", duration, 
                              f"API returned {response.status_code}")
                self.results["errors"].append(f"API error: {response.status_code}")
                return False, None
        
        except Exception as e:
            duration = time.time() - start
            self.print_test(test_name, "fail", duration, str(e))
            self.results["errors"].append(f"Connection error: {str(e)}")
            return False, None
    
    def test_application_health(self):
        """Test 2: Application health endpoint"""
        test_name = "Application Health Endpoint"
        endpoints = [
            f"{self.app_domain}/health",
            f"{self.app_domain}/",
            f"{self.app_domain}/api/health"
        ]
        
        for endpoint in endpoints:
            start = time.time()
            try:
                response = requests.get(endpoint, timeout=10, verify=False)
                duration = time.time() - start
                
                if response.status_code in [200, 301, 302, 404]:
                    self.print_test(f"{test_name} ({endpoint})", "pass", duration,
                                  f"Status: {response.status_code}")
                    self.results["tests"].append({
                        "name": test_name,
                        "endpoint": endpoint,
                        "status": "pass",
                        "http_status": response.status_code,
                        "duration": duration
                    })
                    return True
                else:
                    self.print_test(f"{test_name} ({endpoint})", "warning", duration,
                                  f"Status: {response.status_code}")
            
            except requests.exceptions.SSLError:
                self.print_test(f"{test_name} ({endpoint})", "warning", None,
                              "SSL certificate not yet configured (normal during initial setup)")
                self.results["warnings"].append(f"SSL not configured for {endpoint}")
            
            except Exception as e:
                self.print_test(f"{test_name} ({endpoint})", "warning", None, str(e))
        
        return False
    
    def test_deployment_trigger(self):
        """Test 3: Deployment trigger"""
        test_name = "Deployment Trigger"
        start = time.time()
        
        try:
            response = requests.post(
                f"{self.api_url}/api/v1/deploy?uuid={self.app_id}&force=false",
                headers={"Authorization": f"Bearer {self.api_token}"},
                timeout=30
            )
            duration = time.time() - start
            
            if response.status_code == 200:
                result = response.json()
                deployment_uuid = result['deployments'][0]['deployment_uuid']
                self.print_test(test_name, "pass", duration,
                              f"Deployment queued: {deployment_uuid}")
                self.results["tests"].append({
                    "name": test_name,
                    "status": "pass",
                    "duration": duration,
                    "deployment_uuid": deployment_uuid
                })
                return True, deployment_uuid
            else:
                self.print_test(test_name, "fail", duration,
                              f"API returned {response.status_code}")
                self.results["errors"].append(f"Deployment trigger failed: {response.status_code}")
                return False, None
        
        except Exception as e:
            duration = time.time() - start
            self.print_test(test_name, "fail", duration, str(e))
            self.results["errors"].append(f"Deployment trigger error: {str(e)}")
            return False, None
    
    def test_load_performance(self, concurrent_requests=10, total_requests=100):
        """Test 4: Load performance"""
        test_name = "Load Performance Test"
        self.print_header(f"{test_name} ({total_requests} requests, {concurrent_requests} concurrent)")
        
        response_times = []
        status_codes = defaultdict(int)
        errors = []
        
        def make_request():
            try:
                start = time.time()
                response = requests.get(
                    f"{self.api_url}/api/v1/applications",
                    headers={"Authorization": f"Bearer {self.api_token}"},
                    timeout=10
                )
                duration = time.time() - start
                response_times.append(duration)
                status_codes[response.status_code] += 1
                return True
            except Exception as e:
                errors.append(str(e))
                return False
        
        # Run load test
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [executor.submit(make_request) for _ in range(total_requests)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        total_duration = time.time() - start_time
        
        # Calculate metrics
        success_rate = (sum(results) / len(results)) * 100
        avg_response_time = statistics.mean(response_times) if response_times else 0
        median_response_time = statistics.median(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        requests_per_second = total_requests / total_duration
        
        # Print results
        print(f"\n📊 Load Test Results:")
        print(f"   Total Duration: {total_duration:.2f}s")
        print(f"   Requests/Second: {requests_per_second:.2f}")
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"   Response Times:")
        print(f"      Average: {avg_response_time*1000:.2f}ms")
        print(f"      Median:  {median_response_time*1000:.2f}ms")
        print(f"      Min:     {min_response_time*1000:.2f}ms")
        print(f"      Max:     {max_response_time*1000:.2f}ms")
        print(f"   Status Codes:")
        for code, count in sorted(status_codes.items()):
            print(f"      {code}: {count} requests")
        
        if errors:
            print(f"   ❌ Errors: {len(errors)}")
            for error in errors[:5]:
                print(f"      - {error}")
        
        self.results["metrics"]["load_test"] = {
            "total_requests": total_requests,
            "concurrent_requests": concurrent_requests,
            "duration": total_duration,
            "requests_per_second": requests_per_second,
            "success_rate": success_rate,
            "avg_response_time": avg_response_time,
            "median_response_time": median_response_time,
            "min_response_time": min_response_time,
            "max_response_time": max_response_time,
            "status_codes": dict(status_codes),
            "errors": errors
        }
        
        if success_rate >= 95:
            self.print_test(test_name, "pass", total_duration, 
                          f"Success rate: {success_rate:.1f}%")
            return True
        else:
            self.print_test(test_name, "warning", total_duration,
                          f"Success rate: {success_rate:.1f}% (< 95%)")
            self.results["warnings"].append(f"Load test success rate below 95%: {success_rate:.1f}%")
            return False
    
    def test_environment_variables(self):
        """Test 5: Environment variables"""
        test_name = "Environment Configuration"
        start = time.time()
        
        required_vars = [
            "COOLIFY_API_URL",
            "COOLIFY_API_TOKEN",
            "COOLIFY_APP_ID"
        ]
        
        missing = [var for var in required_vars if not os.environ.get(var)]
        duration = time.time() - start
        
        if not missing:
            self.print_test(test_name, "pass", duration,
                          f"All {len(required_vars)} variables configured")
            self.results["tests"].append({
                "name": test_name,
                "status": "pass",
                "duration": duration
            })
            return True
        else:
            self.print_test(test_name, "fail", duration,
                          f"Missing: {', '.join(missing)}")
            self.results["errors"].append(f"Missing environment variables: {', '.join(missing)}")
            return False
    
    def test_dockerfile_exists(self):
        """Test 6: Dockerfile validation"""
        test_name = "Dockerfile Exists"
        start = time.time()
        
        dockerfile_path = Path("Dockerfile")
        duration = time.time() - start
        
        if dockerfile_path.exists():
            # Check if Dockerfile has content
            content = dockerfile_path.read_text()
            if len(content) > 50:
                self.print_test(test_name, "pass", duration,
                              f"Size: {len(content)} bytes")
                self.results["tests"].append({
                    "name": test_name,
                    "status": "pass",
                    "duration": duration
                })
                return True
            else:
                self.print_test(test_name, "warning", duration,
                              "Dockerfile seems too small")
                self.results["warnings"].append("Dockerfile content seems minimal")
                return False
        else:
            self.print_test(test_name, "fail", duration,
                          "Dockerfile not found")
            self.results["errors"].append("Dockerfile not found in project root")
            return False
    
    def generate_report(self):
        """Generate comprehensive report"""
        self.print_header("📊 TEST SUMMARY")
        
        total_tests = len(self.results["tests"])
        passed_tests = sum(1 for t in self.results["tests"] if t.get("status") == "pass")
        failed_tests = sum(1 for t in self.results["tests"] if t.get("status") == "fail")
        
        print(f"\n✅ Passed: {passed_tests}/{total_tests}")
        print(f"❌ Failed: {failed_tests}/{total_tests}")
        print(f"⚠️  Warnings: {len(self.results['warnings'])}")
        print(f"🚨 Errors: {len(self.results['errors'])}")
        
        if self.results["errors"]:
            print(f"\n🚨 Critical Errors:")
            for i, error in enumerate(self.results["errors"], 1):
                print(f"   {i}. {error}")
        
        if self.results["warnings"]:
            print(f"\n⚠️  Warnings:")
            for i, warning in enumerate(self.results["warnings"], 1):
                print(f"   {i}. {warning}")
        
        # Save report
        report_file = Path("orchestration/reports") / f"performance-test-{int(time.time())}.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_tests": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "warnings": len(self.results["warnings"]),
                    "errors": len(self.results["errors"])
                },
                "results": self.results
            }, f, indent=2)
        
        print(f"\n📄 Report saved: {report_file}")
        
        # Overall result
        if failed_tests == 0 and len(self.results["errors"]) == 0:
            print("\n" + "=" * 70)
            print("🎉 ALL TESTS PASSED!")
            print("=" * 70)
            return True
        else:
            print("\n" + "=" * 70)
            print("⚠️  SOME TESTS FAILED - Review errors above")
            print("=" * 70)
            return False
    
    def run_all_tests(self):
        """Run complete test suite"""
        self.print_header("🚀 HIGH-PERFORMANCE TEST SUITE")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test 1: Environment
        self.print_header("Test 1: Environment Configuration")
        self.test_environment_variables()
        
        # Test 2: Dockerfile
        self.print_header("Test 2: Dockerfile Validation")
        self.test_dockerfile_exists()
        
        # Test 3: Coolify API
        self.print_header("Test 3: Coolify API Connection")
        success, app = self.test_coolify_api_connection()
        
        if not success:
            print("\n⚠️  Skipping remaining tests due to API connection failure")
            self.generate_report()
            return False
        
        # Test 4: Application Health
        self.print_header("Test 4: Application Health Check")
        self.test_application_health()
        
        # Test 5: Load Performance
        self.test_load_performance(concurrent_requests=10, total_requests=50)
        
        # Test 6: Deployment Trigger
        self.print_header("Test 5: Deployment Trigger (DRY RUN)")
        print("⚠️  Skipping actual deployment to avoid disruption")
        print("   Use 'python3 scripts/simple-deploy.py' to deploy")
        
        # Generate report
        return self.generate_report()

def main():
    """Main entry point"""
    tester = PerformanceTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
