#!/usr/bin/env python3
"""
Security Manager
Centralized security utilities for credential management and validation
"""

import os
import re
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
import secrets
import string


class SecurityManager:
    """Manages security operations and credential validation"""
    
    # Sensitive patterns to detect
    SENSITIVE_PATTERNS = [
        r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?',
        r'(?i)(secret|password|passwd|pwd)\s*[:=]\s*["\']?([^"\'\s]{8,})["\']?',
        r'(?i)(token)\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{20,})["\']?',
        r'(?i)(bearer\s+)([a-zA-Z0-9_\-\.]{20,})',
        r'(?i)(authorization:\s*basic\s+)([a-zA-Z0-9+/=]{20,})',
        r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----',
        r'(?i)(aws_access_key_id|aws_secret_access_key)\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
        r'\d\|[a-zA-Z0-9]{40,}',  # Coolify token pattern
    ]
    
    # Required environment variables per service
    REQUIRED_ENV_VARS = {
        "coolify": ["COOLIFY_API_URL", "COOLIFY_API_TOKEN", "COOLIFY_APP_ID"],
        "docker": ["DOCKER_USERNAME", "DOCKER_PASSWORD"],
        "security": ["JWT_SECRET"],
        "openai": ["OPENAI_API_KEY"],
    }
    
    def __init__(self):
        self.env_cache = {}
        self._load_env_file()
    
    def _load_env_file(self):
        """Load environment variables from .env.local if it exists"""
        env_file = Path(".env.local")
        if env_file.exists():
            print("📄 Loading configuration from .env.local")
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        value = value.strip('"').strip("'")
                        os.environ[key] = value
                        self.env_cache[key] = value
    
    def validate_environment(self, service: str) -> Dict[str, Any]:
        """
        Validate required environment variables for a service
        
        Args:
            service: Service name (coolify, docker, security, openai)
            
        Returns:
            Dict with validation results
        """
        required_vars = self.REQUIRED_ENV_VARS.get(service, [])
        
        results = {
            "service": service,
            "valid": True,
            "missing": [],
            "present": [],
            "masked_values": {}
        }
        
        for var in required_vars:
            value = os.getenv(var)
            if value and value not in ["your-api-key-here", "your-token-here", "change-me"]:
                results["present"].append(var)
                results["masked_values"][var] = self.mask_value(value)
            else:
                results["missing"].append(var)
                results["valid"] = False
        
        return results
    
    def validate_all_services(self) -> Dict[str, Any]:
        """Validate environment for all services"""
        all_results = {}
        overall_valid = True
        
        for service in ["coolify", "docker", "security"]:
            result = self.validate_environment(service)
            all_results[service] = result
            if not result["valid"]:
                overall_valid = False
        
        return {
            "overall_valid": overall_valid,
            "services": all_results
        }
    
    def mask_value(self, value: str, show_chars: int = 4) -> str:
        """
        Mask sensitive value for logging
        
        Args:
            value: Value to mask
            show_chars: Number of characters to show at start/end
            
        Returns:
            Masked string
        """
        if not value or len(value) < show_chars * 2:
            return "***"
        
        return f"{value[:show_chars]}...{value[-show_chars:]}"
    
    def scan_file_for_secrets(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Scan a file for potential secrets
        
        Args:
            file_path: Path to file to scan
            
        Returns:
            List of findings
        """
        findings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            for i, pattern in enumerate(self.SENSITIVE_PATTERNS):
                matches = re.finditer(pattern, content, re.MULTILINE)
                for match in matches:
                    # Get line number
                    line_num = content[:match.start()].count('\n') + 1
                    
                    # Skip if in comment or example
                    line_content = content.split('\n')[line_num - 1]
                    if '#' in line_content and line_content.index('#') < line_content.index(match.group(0)):
                        continue
                    
                    findings.append({
                        "file": str(file_path.relative_to(Path.cwd())),
                        "line": line_num,
                        "pattern": i,
                        "match": match.group(0)[:50],
                        "severity": "HIGH"
                    })
        
        except Exception:
            pass
        
        return findings
    
    def scan_directory(self, directory: Path, exclude_dirs: List[str] = None) -> Dict[str, Any]:
        """
        Scan directory for secrets
        
        Args:
            directory: Directory to scan
            exclude_dirs: Directories to exclude
            
        Returns:
            Scan results
        """
        if exclude_dirs is None:
            exclude_dirs = ['.git', 'node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build', 'orchestration/reports']
        
        all_findings = []
        files_scanned = 0
        
        for file_path in directory.rglob('*'):
            # Skip excluded directories
            if any(excluded in file_path.parts for excluded in exclude_dirs):
                continue
            
            # Only scan text files
            if file_path.is_file() and file_path.suffix in ['.py', '.js', '.json', '.env', '.yaml', '.yml', '.sh', '.md', '.txt', '.go']:
                findings = self.scan_file_for_secrets(file_path)
                if findings:
                    all_findings.extend(findings)
                files_scanned += 1
        
        return {
            "files_scanned": files_scanned,
            "findings": all_findings,
            "total_issues": len(all_findings),
            "high_severity": len([f for f in all_findings if f["severity"] == "HIGH"])
        }
    
    def generate_secure_token(self, length: int = 64) -> str:
        """Generate a cryptographically secure random token"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def generate_jwt_secret(self) -> str:
        """Generate a secure JWT secret"""
        return secrets.token_urlsafe(64)
    
    def hash_value(self, value: str) -> str:
        """Create SHA-256 hash of a value"""
        return hashlib.sha256(value.encode()).hexdigest()
    
    def get_safe_config(self, config: Dict) -> Dict:
        """
        Sanitize configuration dictionary by masking sensitive values
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Safe configuration with masked sensitive values
        """
        import copy
        safe_config = copy.deepcopy(config)
        
        sensitive_keys = ['password', 'token', 'secret', 'key', 'credential', 'api_key', 'apikey']
        
        def mask_dict(obj):
            if isinstance(obj, dict):
                for key in list(obj.keys()):
                    if any(sensitive in key.lower() for sensitive in sensitive_keys):
                        if isinstance(obj[key], str):
                            obj[key] = self.mask_value(obj[key])
                    else:
                        mask_dict(obj[key])
            elif isinstance(obj, list):
                for item in obj:
                    mask_dict(item)
        
        mask_dict(safe_config)
        return safe_config
    
    def create_env_template(self, output_path: Path = Path(".env.example")):
        """Create environment template file"""
        template = """# Environment Configuration Template
# Copy this file to .env.local and fill in your values
# NEVER commit .env.local to version control!

# Coolify Configuration
COOLIFY_API_URL="https://api.doctorhealthy1.com"
COOLIFY_API_TOKEN="generate-new-token-in-coolify-dashboard"
COOLIFY_APP_ID="your-app-id-here"

# Docker Hub
DOCKER_USERNAME="your-dockerhub-username"
DOCKER_PASSWORD="your-dockerhub-password"

# Application Security
# Generate with: openssl rand -base64 64
JWT_SECRET="generate-with-openssl-rand-base64-64"

# OpenAI API (for AI features)
OPENAI_API_KEY="sk-your-openai-api-key-here"

# Optional: GitHub Token (for CI/CD)
# GITHUB_TOKEN="your-github-token-if-needed"

# Optional: Database
# DATABASE_URL="postgresql://user:password@localhost:5432/dbname"

# Optional: Redis
# REDIS_URL="redis://localhost:6379"
"""
        
        with open(output_path, 'w') as f:
            f.write(template)
        
        print(f"✅ Created environment template: {output_path}")
    
    def print_security_report(self):
        """Print comprehensive security report"""
        print("\n" + "=" * 70)
        print("🔒 SECURITY VALIDATION REPORT")
        print("=" * 70)
        
        # Validate environment
        validation = self.validate_all_services()
        
        print("\n📋 Environment Variables:")
        for service, results in validation["services"].items():
            status = "✅" if results["valid"] else "❌"
            print(f"\n{status} {service.upper()}:")
            
            if results["present"]:
                print("   Present:")
                for var in results["present"]:
                    masked = results["masked_values"][var]
                    print(f"      ✓ {var}: {masked}")
            
            if results["missing"]:
                print("   Missing:")
                for var in results["missing"]:
                    print(f"      ✗ {var}")
        
        print("\n" + "=" * 70)
        if validation["overall_valid"]:
            print("✅ ALL REQUIRED CREDENTIALS CONFIGURED")
        else:
            print("❌ MISSING REQUIRED CREDENTIALS")
            print("\nPlease set missing environment variables:")
            print("1. Copy .env.example to .env.local")
            print("2. Fill in your credentials")
            print("3. Run: source .env.local")
        print("=" * 70)
        
        return validation["overall_valid"]


def main():
    """Main entry point for security manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Security Manager")
    parser.add_argument("--validate", action="store_true", help="Validate environment")
    parser.add_argument("--scan", action="store_true", help="Scan for secrets")
    parser.add_argument("--create-template", action="store_true", help="Create .env.example")
    parser.add_argument("--generate-jwt-secret", action="store_true", help="Generate JWT secret")
    
    args = parser.parse_args()
    
    security = SecurityManager()
    
    if args.validate or not any([args.scan, args.create_template, args.generate_jwt_secret]):
        valid = security.print_security_report()
        exit(0 if valid else 1)
    
    if args.scan:
        print("\n🔍 Scanning for secrets...")
        results = security.scan_directory(Path("."))
        print(f"\n📊 Scan Results:")
        print(f"   Files scanned: {results['files_scanned']}")
        print(f"   Issues found: {results['total_issues']}")
        print(f"   High severity: {results['high_severity']}")
        
        if results['findings']:
            print("\n🚨 Findings:")
            for finding in results['findings'][:20]:
                print(f"   {finding['file']}:{finding['line']}")
                print(f"      {finding['match']}")
    
    if args.create_template:
        security.create_env_template()
    
    if args.generate_jwt_secret:
        secret = security.generate_jwt_secret()
        print(f"\n🔑 Generated JWT Secret:")
        print(f"   {secret}")
        print(f"\nAdd to .env.local:")
        print(f'JWT_SECRET="{secret}"')


if __name__ == "__main__":
    main()
