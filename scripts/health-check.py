#!/usr/bin/env python3
"""
Production-ready health check script for Docker containers
Supports multiple service checks and comprehensive health monitoring
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

import requests
from requests.exceptions import RequestException


class HealthChecker:
    """Comprehensive health checking utility"""
    
    def __init__(self):
        self.results = {}
        self.start_time = time.time()
        
    def check_database(self) -> bool:
        """Check database connectivity"""
        try:
            db_url = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
            if not db_url:
                self.results['database'] = {
                    'status': 'warning',
                    'message': 'No database URL configured'
                }
                return True  # Not critical for basic health
                
            # Simple connectivity check (you can enhance this)
            if 'postgresql://' in db_url:
                import psycopg2
                conn = psycopg2.connect(db_url)
                conn.close()
                
            self.results['database'] = {
                'status': 'healthy',
                'message': 'Database connection successful'
            }
            return True
            
        except Exception as e:
            self.results['database'] = {
                'status': 'unhealthy',
                'message': f'Database connection failed: {str(e)}'
            }
            return False
    
    def check_redis(self) -> bool:
        """Check Redis connectivity"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            if 'redis://' in redis_url:
                import redis
                r = redis.from_url(redis_url)
                r.ping()
                
            self.results['redis'] = {
                'status': 'healthy',
                'message': 'Redis connection successful'
            }
            return True
            
        except Exception as e:
            self.results['redis'] = {
                'status': 'warning',
                'message': f'Redis connection failed: {str(e)}'
            }
            return True  # Redis is often not critical
    
    def check_http_endpoint(self, url: str, timeout: int = 5) -> bool:
        """Check HTTP endpoint health"""
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code < 400:
                return True
            return False
            
        except RequestException:
            return False
    
    def check_main_application(self) -> bool:
        """Check main application health"""
        try:
            port = os.getenv('PORT', '8080')
            url = f'http://localhost:{port}/health'
            
            if self.check_http_endpoint(url):
                self.results['application'] = {
                    'status': 'healthy',
                    'message': f'Application responding on port {port}'
                }
                return True
            else:
                self.results['application'] = {
                    'status': 'unhealthy',
                    'message': f'Application not responding on port {port}'
                }
                return False
                
        except Exception as e:
            self.results['application'] = {
                'status': 'unhealthy',
                'message': f'Application health check failed: {str(e)}'
            }
            return False
    
    def check_disk_space(self, threshold: float = 90.0) -> bool:
        """Check available disk space"""
        try:
            import shutil
            
            total, used, free = shutil.disk_usage('/')
            percent_used = (used / total) * 100
            
            if percent_used < threshold:
                self.results['disk_space'] = {
                    'status': 'healthy',
                    'message': f'Disk usage: {percent_used:.1f}%'
                }
                return True
            else:
                self.results['disk_space'] = {
                    'status': 'warning',
                    'message': f'Disk usage critical: {percent_used:.1f}%'
                }
                return False
                
        except Exception as e:
            self.results['disk_space'] = {
                'status': 'warning',
                'message': f'Disk space check failed: {str(e)}'
            }
            return True
    
    def check_memory(self) -> Dict:
        """Check memory usage"""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            self.results['memory'] = {
                'status': 'healthy' if memory.percent < 90 else 'warning',
                'message': f'Memory usage: {memory.percent:.1f}%',
                'details': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent
                }
            }
            return self.results['memory']
            
        except Exception as e:
            self.results['memory'] = {
                'status': 'warning',
                'message': f'Memory check failed: {str(e)}'
            }
            return self.results['memory']
    
    def check_dependencies(self) -> bool:
        """Check critical dependencies"""
        try:
            # Check Python modules
            required_modules = ['flask', 'requests', 'psutil']
            missing_modules = []
            
            for module in required_modules:
                try:
                    __import__(module)
                except ImportError:
                    missing_modules.append(module)
            
            if missing_modules:
                self.results['dependencies'] = {
                    'status': 'unhealthy',
                    'message': f'Missing modules: {", ".join(missing_modules)}'
                }
                return False
            
            self.results['dependencies'] = {
                'status': 'healthy',
                'message': 'All required dependencies available'
            }
            return True
            
        except Exception as e:
            self.results['dependencies'] = {
                'status': 'warning',
                'message': f'Dependency check failed: {str(e)}'
            }
            return True
    
    def run_comprehensive_check(self) -> bool:
        """Run all health checks"""
        checks = [
            ('application', self.check_main_application),
            ('database', self.check_database),
            ('redis', self.check_redis),
            ('disk_space', self.check_disk_space),
            ('memory', self.check_memory),
            ('dependencies', self.check_dependencies),
        ]
        
        overall_healthy = True
        
        for check_name, check_func in checks:
            if check_name == 'memory':
                check_func()  # Memory check returns details
            else:
                if not check_func():
                    overall_healthy = False
        
        return overall_healthy
    
    def get_service_status(self, service: str) -> bool:
        """Get status of a specific service"""
        check_map = {
            'database': self.check_database,
            'redis': self.check_redis,
            'application': self.check_main_application,
            'disk': self.check_disk_space,
            'memory': self.check_memory,
            'dependencies': self.check_dependencies,
        }
        
        if service in check_map:
            return check_map[service]()
        else:
            print(f"Unknown service: {service}", file=sys.stderr)
            return False
    
    def output_results(self, format_type: str = 'json') -> str:
        """Output health check results"""
        end_time = time.time()
        duration = end_time - self.start_time
        
        output_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'duration_seconds': round(duration, 2),
            'overall_status': 'healthy' if all(
                result.get('status') == 'healthy' 
                for result in self.results.values()
            ) else 'unhealthy',
            'checks': self.results
        }
        
        if format_type == 'json':
            return json.dumps(output_data, indent=2)
        else:
            # Plain text format
            lines = [
                f"Health Check Results - {output_data['timestamp']}",
                f"Duration: {output_data['duration_seconds']}s",
                f"Overall Status: {output_data['overall_status'].upper()}",
                "",
                "Individual Checks:"
            ]
            
            for check_name, result in self.results.items():
                status = result['status'].upper()
                message = result['message']
                lines.append(f"  {check_name}: {status} - {message}")
            
            return "\n".join(lines)


def main():
    """Main health check execution"""
    parser = argparse.ArgumentParser(description='Health check script')
    parser.add_argument('--service', help='Check specific service only')
    parser.add_argument('--format', choices=['json', 'text'], default='json',
                       help='Output format')
    parser.add_argument('--timeout', type=int, default=10,
                       help='Health check timeout in seconds')
    parser.add_argument('--verbose', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    checker = HealthChecker()
    
    try:
        if args.service:
            # Check specific service
            healthy = checker.get_service_status(args.service)
            if not healthy:
                print(f"Service {args.service} is unhealthy", file=sys.stderr)
                sys.exit(1)
            else:
                print(f"Service {args.service} is healthy")
        else:
            # Run comprehensive check
            healthy = checker.run_comprehensive_check()
            
            output = checker.output_results(args.format)
            print(output)
            
            if not healthy:
                sys.exit(1)
                
    except KeyboardInterrupt:
        print("Health check interrupted", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Health check failed: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
