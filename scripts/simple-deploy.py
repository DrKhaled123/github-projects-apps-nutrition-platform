#!/usr/bin/env python3
"""
Simple Deployment Script
Deploys directly to Coolify without tests or complex orchestration
"""

import os
import sys
import requests
from datetime import datetime
from pathlib import Path


class SimpleDeployer:
    """Simple deployment to Coolify"""
    
    def __init__(self):
        # Load environment
        self._load_env()
        
        # Validate required variables
        self.api_url = os.environ.get("COOLIFY_API_URL")
        self.api_token = os.environ.get("COOLIFY_API_TOKEN")
        self.app_id = os.environ.get("COOLIFY_APP_ID")
        
        if not all([self.api_url, self.api_token, self.app_id]):
            print("❌ Missing required environment variables:")
            print("   COOLIFY_API_URL, COOLIFY_API_TOKEN, COOLIFY_APP_ID")
            print("\nPlease ensure .env.local is configured correctly")
            sys.exit(1)
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        print("✅ Environment validated")
    
    def _load_env(self):
        """Load .env.local if it exists"""
        env_file = Path(".env.local")
        if env_file.exists():
            print(f"📄 Loading {env_file}")
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        value = value.strip('"').strip("'")
                        os.environ[key.strip()] = value
    
    def deploy(self):
        """Trigger Coolify deployment"""
        print("\n" + "=" * 70)
        print("🚀 SIMPLE DEPLOYMENT TO COOLIFY")
        print("=" * 70)
        print(f"API URL: {self.api_url}")
        print(f"App ID: {self.app_id[:8]}...")
        print(f"Time: {datetime.now().isoformat()}")
        print("=" * 70)
        
        try:
            # Trigger deployment - Coolify uses /deploy endpoint with uuid parameter
            url = f"{self.api_url}/api/v1/deploy?uuid={self.app_id}&force=false"
            
            print(f"\n📤 Sending deployment request...")
            print(f"URL: {url}")
            
            response = requests.post(
                url,
                headers=self.headers,
                timeout=30
            )
            
            print(f"\n📊 Response Status: {response.status_code}")
            
            if response.status_code in [200, 201, 202]:
                print("✅ Deployment triggered successfully!")
                
                try:
                    result = response.json()
                    print(f"\n📋 Response:")
                    for key, value in result.items():
                        print(f"   {key}: {value}")
                except:
                    print(f"\n📋 Response: {response.text}")
                
                print("\n" + "=" * 70)
                print("✅ DEPLOYMENT STARTED")
                print("=" * 70)
                print("\n📝 Next steps:")
                print("1. Check Coolify dashboard for deployment progress")
                print("2. Monitor application logs")
                print("3. Verify health endpoint once deployed")
                print("\n🌐 Coolify Dashboard: " + self.api_url.replace("/api/v1", ""))
                
                return True
            
            else:
                print(f"❌ Deployment failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return False
        
        except requests.exceptions.Timeout:
            print("❌ Request timed out")
            print("The deployment may still be processing in Coolify")
            print("Check your Coolify dashboard")
            return False
        
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def check_health(self, app_url: str):
        """Check application health"""
        try:
            print(f"\n🏥 Checking health: {app_url}/health")
            response = requests.get(f"{app_url}/health", timeout=10)
            
            if response.status_code == 200:
                print("✅ Application is healthy!")
                return True
            else:
                print(f"⚠️  Health check returned {response.status_code}")
                return False
        
        except Exception as e:
            print(f"⚠️  Health check failed: {e}")
            return False


def main():
    """Main entry point"""
    print("\n" + "=" * 70)
    print("SIMPLE COOLIFY DEPLOYMENT")
    print("=" * 70)
    
    deployer = SimpleDeployer()
    success = deployer.deploy()
    
    if success:
        print("\n✅ Deployment request sent successfully!")
        sys.exit(0)
    else:
        print("\n❌ Deployment failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
