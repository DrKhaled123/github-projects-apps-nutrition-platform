#!/usr/bin/env python3
"""
Container Health Diagnostic Tool
Provides detailed analysis and fix recommendations
"""

import os
import sys
import requests
from pathlib import Path
from datetime import datetime

# Load environment
env_file = Path(".env.local")
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip('"').strip("'")

API_URL = os.environ.get("COOLIFY_API_URL", "")
API_TOKEN = os.environ.get("COOLIFY_API_TOKEN", "")
APP_ID = os.environ.get("COOLIFY_APP_ID", "")

print("=" * 70)
print("🏥 CONTAINER HEALTH DIAGNOSTICS")
print("=" * 70)
print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

try:
    # Get application details
    response = requests.get(
        f"{API_URL}/api/v1/applications",
        headers={"Authorization": f"Bearer {API_TOKEN}"},
        timeout=10
    )
    
    if response.status_code != 200:
        print(f"❌ API error: {response.status_code}")
        sys.exit(1)
    
    apps = response.json()
    app = next((a for a in apps if a['uuid'] == APP_ID), None)
    
    if not app:
        print(f"❌ Application {APP_ID} not found")
        sys.exit(1)
    
    # Parse status
    status = app.get('status', 'unknown')
    print(f"📊 Current Status: {status}\n")
    
    # Detailed analysis
    issues = []
    fixes = []
    
    if 'unhealthy' in status.lower():
        print("🔍 HEALTH CHECK ANALYSIS")
        print("-" * 70)
        
        # Check 1: Health endpoint
        print("\n1️⃣ Health Endpoint Check")
        issues.append("Health checks are failing (HTTP 503)")
        
        health_endpoint_exists = False
        # Try to check if health endpoint exists in code
        go_files = list(Path('.').rglob('*.go'))
        for go_file in go_files[:10]:  # Check first 10 Go files
            try:
                content = go_file.read_text()
                if '/health' in content:
                    health_endpoint_exists = True
                    print(f"   ✅ Found health endpoint in {go_file}")
                    break
            except:
                pass
        
        if not health_endpoint_exists:
            print("   ❌ No health endpoint found in Go files")
            issues.append("Missing /health endpoint in application")
            fixes.append("""
Add health endpoint to your Go application (main.go or routes):
```go
router.GET("/health", func(c *gin.Context) {
    c.JSON(200, gin.H{
        "status": "healthy",
        "timestamp": time.Now().Format(time.RFC3339),
    })
})
```""")
        
        # Check 2: Port configuration
        print("\n2️⃣ Port Configuration Check")
        app_port = app.get('ports_exposes', '')
        print(f"   📋 Configured port: {app_port}")
        
        if app_port:
            # Check if PORT env var exists in Dockerfile
            dockerfile = Path('Dockerfile')
            if dockerfile.exists():
                content = dockerfile.read_text()
                if 'EXPOSE' in content and app_port in content:
                    print(f"   ✅ Dockerfile exposes port {app_port}")
                else:
                    print(f"   ⚠️  Dockerfile may not expose port {app_port}")
                    issues.append(f"Port {app_port} may not be properly exposed")
                    fixes.append(f"""
Add to Dockerfile:
```dockerfile
EXPOSE {app_port}
```""")
        
        # Check 3: Environment variables
        print("\n3️⃣ Environment Variables Check")
        env_vars = app.get('environment_variables', [])
        
        required_vars = ['DATABASE_URL', 'PORT', 'JWT_SECRET']
        missing_vars = []
        
        for var in required_vars:
            found = any(ev.get('key') == var for ev in env_vars)
            if found:
                print(f"   ✅ {var} configured")
            else:
                print(f"   ❌ {var} missing")
                missing_vars.append(var)
        
        if missing_vars:
            issues.append(f"Missing environment variables: {', '.join(missing_vars)}")
            fixes.append(f"""
Add missing environment variables in Coolify:
1. Go to Coolify dashboard
2. Navigate to doctorhealthy1-api → Environment Variables
3. Add:
   {chr(10).join(f'   - {var}=<value>' for var in missing_vars)}
4. Redeploy application
""")
        
        # Check 4: Build status
        print("\n4️⃣ Build Status Check")
        if 'running' in status:
            print("   ✅ Container is running")
        else:
            print(f"   ⚠️  Container status: {status}")
            issues.append(f"Container not running properly: {status}")
        
        # Check 5: Database connectivity
        print("\n5️⃣ Database Configuration Check")
        db_configured = any(
            'database' in ev.get('key', '').lower() or 
            'postgres' in ev.get('key', '').lower() or
            'db_' in ev.get('key', '').lower()
            for ev in env_vars
        )
        
        if db_configured:
            print("   ✅ Database environment variables found")
        else:
            print("   ❌ No database configuration found")
            issues.append("Database configuration missing")
            fixes.append("""
Configure database connection in Coolify environment variables:
- DATABASE_URL=postgresql://user:pass@host:port/dbname
  OR
- DB_HOST=your-db-host
- DB_PORT=5432
- DB_NAME=your-database
- DB_USER=your-user
- DB_PASSWORD=your-password
""")
    
    else:
        print("✅ Application appears healthy!")
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 DIAGNOSTIC SUMMARY")
    print("=" * 70)
    
    if issues:
        print(f"\n🚨 Issues Found: {len(issues)}")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
    
    if fixes:
        print(f"\n🔧 RECOMMENDED FIXES")
        print("=" * 70)
        for i, fix in enumerate(fixes, 1):
            print(f"\nFix #{i}:")
            print(fix)
    
    if not issues:
        print("\n✅ No issues detected!")
    
    # Action items
    print("\n" + "=" * 70)
    print("📌 IMMEDIATE ACTION ITEMS")
    print("=" * 70)
    print("""
1. Check container logs in Coolify:
   → Dashboard → doctorhealthy1-api → Logs
   
2. Verify application is starting:
   → Look for "Server started" or similar messages
   
3. Check for error messages:
   → Database connection errors
   → Missing environment variables
   → Port binding errors
   
4. Test locally:
   → docker build -t test .
   → docker run -p 8080:8080 test
   → curl localhost:8080/health
   
5. After fixes, redeploy:
   → python3 scripts/simple-deploy.py
""")

except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
