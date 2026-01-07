#!/usr/bin/env python3
"""
Comprehensive Security & Health Audit Tool
Performs deep analysis of security vulnerabilities and health check issues
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

class SecurityHealthAuditor:
    """Comprehensive security and health auditing"""
    
    def __init__(self):
        self.security_issues = []
        self.health_issues = []
        self.logging_issues = []
        self.integration_issues = []
        self.critical_count = 0
        self.high_count = 0
        self.medium_count = 0
        self.low_count = 0
    
    def print_header(self, text):
        print("\n" + "=" * 80)
        print(f" {text}")
        print("=" * 80)
    
    def print_issue(self, severity, category, issue, file=None, line=None):
        icons = {"CRITICAL": "🚨", "HIGH": "❌", "MEDIUM": "⚠️", "LOW": "ℹ️"}
        icon = icons.get(severity, "•")
        
        print(f"\n{icon} [{severity}] {category}: {issue}")
        if file:
            location = f"   📁 File: {file}"
            if line:
                location += f" (line {line})"
            print(location)
        
        # Track counts
        if severity == "CRITICAL":
            self.critical_count += 1
        elif severity == "HIGH":
            self.high_count += 1
        elif severity == "MEDIUM":
            self.medium_count += 1
        else:
            self.low_count += 1
    
    def audit_security_logging(self):
        """Audit for insecure logging practices"""
        self.print_header("🔐 SECURITY LOGGING AUDIT")
        
        go_files = list(Path('.').rglob('*.go'))
        
        # Patterns that indicate security issues in logging
        insecure_patterns = [
            (r'log\.Print.*JWT.*Secret', "JWT secret in logs", "CRITICAL"),
            (r'log\.Print.*password', "Password in logs", "CRITICAL"),
            (r'log\.Print.*token', "Token in logs", "HIGH"),
            (r'log\.Print.*API.*[Kk]ey', "API key in logs", "HIGH"),
            (r'log\.Print.*DEBUG.*', "Debug logs in production", "MEDIUM"),
            (r'fmt\.Printf.*%v.*err', "Error details exposed", "MEDIUM"),
            (r'log\.Fatal', "Abrupt termination", "LOW"),
        ]
        
        for go_file in go_files[:50]:  # Limit to first 50 for performance
            try:
                content = go_file.read_text()
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    for pattern, issue, severity in insecure_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            self.print_issue(
                                severity,
                                "Insecure Logging",
                                issue,
                                str(go_file),
                                i
                            )
                            self.logging_issues.append({
                                "file": str(go_file),
                                "line": i,
                                "issue": issue,
                                "severity": severity,
                                "code": line.strip()
                            })
            except:
                pass
    
    def audit_sql_injection(self):
        """Audit for SQL injection vulnerabilities"""
        self.print_header("💉 SQL INJECTION AUDIT")
        
        go_files = list(Path('.').rglob('*.go'))
        
        # Patterns indicating potential SQL injection
        sql_patterns = [
            (r'fmt\.Sprintf.*SELECT', "String concatenation in SQL", "HIGH"),
            (r'fmt\.Sprintf.*INSERT', "String concatenation in SQL", "HIGH"),
            (r'fmt\.Sprintf.*UPDATE', "String concatenation in SQL", "HIGH"),
            (r'fmt\.Sprintf.*DELETE', "String concatenation in SQL", "HIGH"),
            (r'\+\s*".*SELECT', "SQL concatenation", "HIGH"),
            (r'Query\([^?]*\)', "Non-parameterized query", "MEDIUM"),
        ]
        
        for go_file in go_files[:50]:
            try:
                content = go_file.read_text()
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    for pattern, issue, severity in sql_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            # Check if it's actually using prepared statements
                            if '?' in line or '$1' in line:
                                continue  # This is okay, using parameters
                            
                            self.print_issue(
                                severity,
                                "SQL Injection Risk",
                                issue,
                                str(go_file),
                                i
                            )
                            self.security_issues.append({
                                "file": str(go_file),
                                "line": i,
                                "issue": issue,
                                "severity": severity,
                                "type": "sql_injection"
                            })
            except:
                pass
    
    def audit_health_endpoints(self):
        """Audit health check implementations"""
        self.print_header("🏥 HEALTH ENDPOINT AUDIT")
        
        # Check main.go for health endpoint
        main_go = Path('main.go')
        if main_go.exists():
            content = main_go.read_text()
            
            # Check for basic health endpoint
            if '/health' in content:
                print("✅ Health endpoint exists: /health")
            else:
                self.print_issue("HIGH", "Missing Endpoint", "No /health endpoint found", "main.go")
                self.health_issues.append({
                    "issue": "No /health endpoint",
                    "severity": "HIGH"
                })
            
            # Check for readiness endpoint
            if '/ready' in content:
                print("✅ Readiness endpoint exists: /ready")
            else:
                self.print_issue("MEDIUM", "Missing Endpoint", "No /ready endpoint found", "main.go")
                self.health_issues.append({
                    "issue": "No /ready endpoint",
                    "severity": "MEDIUM"
                })
            
            # Check for comprehensive health checks
            checks_found = []
            if 'db.Ping()' in content or 'database' in content.lower():
                checks_found.append("Database")
            if 'filesystem' in content.lower() or 'os.Stat' in content:
                checks_found.append("Filesystem")
            
            if checks_found:
                print(f"✅ Health checks implemented: {', '.join(checks_found)}")
            else:
                self.print_issue("MEDIUM", "Incomplete Checks", "Health checks don't verify dependencies", "main.go")
                self.health_issues.append({
                    "issue": "Incomplete health checks",
                    "severity": "MEDIUM"
                })
    
    def audit_integration_health(self):
        """Audit integration service health"""
        self.print_header("🔌 INTEGRATION HEALTH AUDIT")
        
        # Check for VIP service
        vip_service = Path('internal/services/vip_integration_service.go')
        if vip_service.exists():
            content = vip_service.read_text()
            if 'health' in content.lower() or 'Health' in content:
                print("✅ VIP Integration Service has health checks")
            else:
                self.print_issue("MEDIUM", "No Health Check", "VIP service lacks health monitoring", str(vip_service))
                self.integration_issues.append({
                    "service": "VIP Integration",
                    "issue": "No health check method",
                    "severity": "MEDIUM"
                })
        
        # Check for Enhanced Health Service
        enhanced_service = Path('internal/services/enhanced_health_service.go')
        if enhanced_service.exists():
            print("✅ Enhanced Health Service exists")
        else:
            self.print_issue("LOW", "Missing Service", "Enhanced Health Service not found", "internal/services/")
    
    def audit_xss_protection(self):
        """Audit XSS protection"""
        self.print_header("🛡️ XSS PROTECTION AUDIT")
        
        # Check for HTML escaping
        utils_security = Path('internal/utils/security.go')
        if utils_security.exists():
            content = utils_security.read_text()
            if 'html.EscapeString' in content:
                print("✅ HTML escaping implemented")
            else:
                self.print_issue("HIGH", "Missing XSS Protection", "No HTML escaping found", str(utils_security))
                self.security_issues.append({
                    "file": str(utils_security),
                    "issue": "Missing HTML escaping",
                    "severity": "HIGH",
                    "type": "xss"
                })
            
            # Check for JSON sanitization
            if 'SanitizeForJSON' in content:
                print("✅ JSON sanitization implemented")
            else:
                self.print_issue("MEDIUM", "Missing Sanitization", "No JSON sanitization", str(utils_security))
                self.security_issues.append({
                    "file": str(utils_security),
                    "issue": "Missing JSON sanitization",
                    "severity": "MEDIUM",
                    "type": "xss"
                })
    
    def audit_rate_limiting(self):
        """Audit rate limiting implementation"""
        self.print_header("🚦 RATE LIMITING AUDIT")
        
        rate_limit = Path('internal/middleware/rate_limit.go')
        if rate_limit.exists():
            content = rate_limit.read_text()
            if 'RateLimit' in content:
                print("✅ Rate limiting middleware exists")
            
            # Check for per-user limits
            if 'user' in content.lower() and 'quota' in content.lower():
                print("✅ Per-user quota implemented")
            else:
                self.print_issue("MEDIUM", "Missing Feature", "No per-user rate limiting", str(rate_limit))
                self.security_issues.append({
                    "file": str(rate_limit),
                    "issue": "Missing per-user rate limiting",
                    "severity": "MEDIUM",
                    "type": "rate_limiting"
                })
        else:
            self.print_issue("HIGH", "Missing Middleware", "No rate limiting middleware", "internal/middleware/")
            self.security_issues.append({
                "issue": "Missing rate limiting",
                "severity": "HIGH",
                "type": "rate_limiting"
            })
    
    def audit_error_handling(self):
        """Audit error handling practices"""
        self.print_header("🔧 ERROR HANDLING AUDIT")
        
        go_files = list(Path('.').rglob('*.go'))
        panic_count = 0
        unhandled_errors = 0
        
        for go_file in go_files[:30]:
            try:
                content = go_file.read_text()
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    # Check for panic()
                    if 'panic(' in line and 'recover' not in content:
                        panic_count += 1
                        if panic_count <= 3:  # Only report first 3
                            self.print_issue("MEDIUM", "Panic Usage", "Using panic() can crash server", str(go_file), i)
                    
                    # Check for ignored errors
                    if re.search(r'_,\s*err\s*:=', line) and i < len(lines) - 1:
                        next_line = lines[i]
                        if 'if err' not in next_line:
                            unhandled_errors += 1
            except:
                pass
        
        if panic_count > 0:
            print(f"\n⚠️  Found {panic_count} panic() calls - consider graceful error handling")
    
    def generate_report(self):
        """Generate comprehensive audit report"""
        self.print_header("📊 AUDIT SUMMARY")
        
        total_issues = self.critical_count + self.high_count + self.medium_count + self.low_count
        
        print(f"\n🚨 Critical: {self.critical_count}")
        print(f"❌ High:     {self.high_count}")
        print(f"⚠️  Medium:   {self.medium_count}")
        print(f"ℹ️  Low:      {self.low_count}")
        print(f"━━━━━━━━━━━━━━━━━━")
        print(f"📊 Total:    {total_issues}")
        
        # Generate detailed report
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
                "total": total_issues
            },
            "security_issues": self.security_issues,
            "health_issues": self.health_issues,
            "logging_issues": self.logging_issues,
            "integration_issues": self.integration_issues
        }
        
        report_dir = Path("orchestration/reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = report_dir / f"security-health-audit-{int(datetime.now().timestamp())}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Detailed report saved: {report_file}")
        
        # Priority recommendations
        print("\n" + "=" * 80)
        print(" 🎯 PRIORITY RECOMMENDATIONS")
        print("=" * 80)
        
        if self.critical_count > 0:
            print("\n🚨 CRITICAL - Fix Immediately:")
            print("   1. Remove sensitive data from logs (JWT secrets, passwords)")
            print("   2. Implement proper secret management")
            print("   3. Add log sanitization for all user inputs")
        
        if self.high_count > 0:
            print("\n❌ HIGH - Fix This Week:")
            print("   1. Review SQL injection risks - use prepared statements")
            print("   2. Implement comprehensive XSS protection")
            print("   3. Add missing health check endpoints")
            print("   4. Remove debug logging from production")
        
        if self.medium_count > 0:
            print("\n⚠️  MEDIUM - Fix This Month:")
            print("   1. Implement per-user rate limiting")
            print("   2. Add integration health monitoring")
            print("   3. Improve error handling (reduce panic usage)")
            print("   4. Add JSON sanitization")
        
        print("\n" + "=" * 80)
        
        return total_issues == 0
    
    def run_full_audit(self):
        """Run complete security and health audit"""
        print("=" * 80)
        print(" 🔒 COMPREHENSIVE SECURITY & HEALTH AUDIT")
        print("=" * 80)
        print(f" Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Run all audits
        self.audit_security_logging()
        self.audit_sql_injection()
        self.audit_xss_protection()
        self.audit_rate_limiting()
        self.audit_health_endpoints()
        self.audit_integration_health()
        self.audit_error_handling()
        
        # Generate report
        return self.generate_report()

def main():
    auditor = SecurityHealthAuditor()
    success = auditor.run_full_audit()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
