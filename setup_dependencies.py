#!/usr/bin/env python3
"""
Setup script to fix imports and install dependencies
Run this before using the orchestration system
"""

import os
import sys
import subprocess
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"⚙️  {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"⚠️  {description} - WARNING (may be expected)")
            if result.stderr:
                print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False


def main():
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║  CI/CD Orchestration System - Dependency Installer       ║
    ║  Fixes imports and installs all required packages        ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Get project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # 1. Upgrade pip
    run_command([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                "Upgrading pip")
    
    # 2. Install core dependencies
    core_deps = [
        "requests>=2.31.0",
        "psutil>=5.9.0",
        "pytest>=7.4.0",
        "pytest-cov>=4.1.0",
        "pytest-json-report>=1.5.0",
        "pytest-metadata>=3.0.0",
    ]
    
    print(f"\n{'='*60}")
    print("📦 Installing core dependencies")
    print(f"{'='*60}")
    for dep in core_deps:
        run_command([sys.executable, "-m", "pip", "install", dep],
                   f"Installing {dep}")
    
    # 3. Install orchestration requirements
    req_file = project_root / "orchestration" / "requirements.txt"
    if req_file.exists():
        run_command([sys.executable, "-m", "pip", "install", "-r", str(req_file)],
                   "Installing orchestration requirements")
    
    # 4. Install code quality tools
    quality_tools = [
        "pylint>=3.0.0",
        "flake8>=6.1.0",
        "mypy>=1.7.0",
        "bandit>=1.7.5",
        "safety>=2.3.5",
    ]
    
    print(f"\n{'='*60}")
    print("🔍 Installing code quality tools")
    print(f"{'='*60}")
    for tool in quality_tools:
        run_command([sys.executable, "-m", "pip", "install", tool],
                   f"Installing {tool}")
    
    # 5. Create __init__.py files to fix imports
    print(f"\n{'='*60}")
    print("📝 Creating __init__.py files")
    print(f"{'='*60}")
    
    init_dirs = [
        project_root / "ai-agents-shared-memory",
        project_root / "ai-agents-shared-memory" / "utils",
        project_root / "orchestration",
    ]
    
    for dir_path in init_dirs:
        if dir_path.exists():
            init_file = dir_path / "__init__.py"
            if not init_file.exists():
                init_file.touch()
                print(f"✅ Created {init_file}")
    
    # 6. Create setup.py for proper package installation
    setup_content = '''
from setuptools import setup, find_packages

setup(
    name="orchestration-system",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "psutil>=5.9.0",
        "pytest>=7.4.0",
        "pytest-cov>=4.1.0",
        "pytest-json-report>=1.5.0",
        "pytest-metadata>=3.0.0",
        "pylint>=3.0.0",
        "flake8>=6.1.0",
        "mypy>=1.7.0",
        "bandit>=1.7.5",
        "safety>=2.3.5",
    ],
)
'''
    
    setup_file = project_root / "setup.py"
    with open(setup_file, 'w') as f:
        f.write(setup_content)
    print(f"✅ Created {setup_file}")
    
    # 7. Install package in development mode
    run_command([sys.executable, "-m", "pip", "install", "-e", "."],
               "Installing package in development mode")
    
    # 8. Create logs directory
    logs_dir = project_root / "orchestration" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Created logs directory: {logs_dir}")
    
    # 9. Create reports directory
    reports_dir = project_root / "orchestration" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Created reports directory: {reports_dir}")
    
    # 10. Verify installation
    print(f"\n{'='*60}")
    print("🔬 Verifying installation")
    print(f"{'='*60}")
    
    test_imports = [
        "requests",
        "psutil",
        "pytest",
        "pylint",
        "bandit",
    ]
    
    all_good = True
    for module in test_imports:
        try:
            __import__(module)
            print(f"✅ {module} imported successfully")
        except ImportError as e:
            print(f"❌ Failed to import {module}: {e}")
            all_good = False
    
    # Final message
    print(f"\n{'='*60}")
    if all_good:
        print("✅✅✅ ALL DEPENDENCIES INSTALLED SUCCESSFULLY ✅✅✅")
    else:
        print("⚠️  Some dependencies failed to install")
        print("Try running: pip install -r orchestration/requirements.txt")
    print(f"{'='*60}")
    
    print("""
    
    Next steps:
    
    1. Set environment variables:
       export DOCKER_USERNAME="your-username"
       export DOCKER_PASSWORD="your-password"
       export COOLIFY_API_URL="https://your-coolify.com/api"
       export COOLIFY_API_TOKEN="your-token"
       export COOLIFY_APP_ID="your-app-id"
    
    2. Test the system:
       python orchestration/testing_orchestrator.py --type unit
    
    3. Run full pipeline:
       python orchestration/main_orchestrator.py --mode full
    
    4. Start monitoring dashboard:
       python orchestration/monitoring_dashboard.py
    
    """)


if __name__ == "__main__":
    main()
