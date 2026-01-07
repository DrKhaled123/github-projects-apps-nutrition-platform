#!/bin/bash
# Quick Start Script for Orchestration System

set -e

echo "======================================"
echo "Orchestration System - Quick Start"
echo "======================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check Python
echo -e "\n${YELLOW}[1/6] Checking Python installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✓ $PYTHON_VERSION found${NC}"

# Step 2: Install Python dependencies
echo -e "\n${YELLOW}[2/6] Installing Python dependencies...${NC}"
pip install -r orchestration/requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Step 3: Initialize shared memory
echo -e "\n${YELLOW}[3/6] Initializing shared memory system...${NC}"
mkdir -p ai-agents-shared-memory/shared/{context,knowledge,tasks,history}
mkdir -p ai-agents-shared-memory/locks
chmod +x ai-agents-shared-memory/utils/*.sh
echo -e "${GREEN}✓ Shared memory initialized${NC}"

# Step 4: Create directories
echo -e "\n${YELLOW}[4/6] Creating orchestration directories...${NC}"
mkdir -p orchestration/{reports,logs}
echo -e "${GREEN}✓ Directories created${NC}"

# Step 5: Check Docker
echo -e "\n${YELLOW}[5/6] Checking Docker installation...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Warning: Docker is not installed${NC}"
    echo "Install Docker from: https://docs.docker.com/get-docker/"
else
    DOCKER_VERSION=$(docker --version)
    echo -e "${GREEN}✓ $DOCKER_VERSION found${NC}"
fi

# Step 6: Configuration check
echo -e "\n${YELLOW}[6/6] Checking configuration...${NC}"
if [ -f "orchestration/orchestration-config.json" ]; then
    echo -e "${GREEN}✓ Configuration file found${NC}"
else
    echo -e "${RED}Warning: orchestration-config.json not found${NC}"
fi

# Summary
echo -e "\n======================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "======================================"
echo ""
echo "Next Steps:"
echo ""
echo "1. Configure environment variables:"
echo "   export DOCKER_USERNAME='your-username'"
echo "   export DOCKER_PASSWORD='your-password'"
echo "   export COOLIFY_API_URL='https://your-coolify.com/api'"
echo "   export COOLIFY_API_TOKEN='your-token'"
echo "   export COOLIFY_PROJECT_ID='your-project-id'"
echo "   export COOLIFY_APP_ID='your-app-id'"
echo ""
echo "2. Update orchestration/orchestration-config.json with your settings"
echo ""
echo "3. Test the setup:"
echo "   python orchestration/testing_orchestrator.py --type unit"
echo ""
echo "4. Run full pipeline:"
echo "   python orchestration/main_orchestrator.py --mode full"
echo ""
echo "Documentation:"
echo "  - Complete Guide: COMPLETE-SETUP-GUIDE.md"
echo "  - Memory System: ai-agents-shared-memory/README.md"
echo "  - Orchestration: orchestration/README.md"
echo ""
echo "======================================"
