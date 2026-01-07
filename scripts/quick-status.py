#!/usr/bin/env python3
"""Quick deployment status checker"""

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
print("📊 DEPLOYMENT STATUS CHECK")
print("=" * 70)
print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

try:
    # Get application status
    response = requests.get(
        f"{API_URL}/api/v1/applications",
        headers={"Authorization": f"Bearer {API_TOKEN}"},
        timeout=10
    )
    
    if response.status_code == 200:
        apps = response.json()
        app = next((a for a in apps if a['uuid'] == APP_ID), None)
        
        if app:
            print(f"📱 Application: {app['name']}")
            print(f"🆔 UUID: {app['uuid']}")
            print(f"📊 Status: {app.get('status', 'unknown')}")
            print(f"🌐 Domain: {app.get('fqdn', 'N/A')}")
            
            # Get custom labels
            labels = app.get('custom_labels', [])
            if labels:
                for label in labels:
                    if 'traefik' in label and 'rule' in label:
                        print(f"🔗 Traefik Rule: {label['value']}")
            
            # Check build pack
            print(f"🐳 Build Pack: {app.get('build_pack', 'unknown')}")
            
            # Check ports
            ports = app.get('ports_exposes', '')
            if ports:
                print(f"🚪 Ports: {ports}")
            
            # Check last deployment
            if 'last_deployment_at' in app and app['last_deployment_at']:
                print(f"📅 Last Deployment: {app['last_deployment_at']}")
            
            print("\n" + "=" * 70)
            print("✅ STATUS CHECK COMPLETE")
            print("=" * 70)
        else:
            print(f"❌ Application {APP_ID} not found")
    else:
        print(f"❌ API error: {response.status_code}")

except Exception as e:
    print(f"❌ Error: {str(e)}")
    sys.exit(1)
