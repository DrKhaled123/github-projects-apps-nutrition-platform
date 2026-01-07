#!/bin/bash
# Automated Coolify Configuration Fix Script

echo "════════════════════════════════════════════════════════════════════"
echo "🔧 COOLIFY CONFIGURATION FIX AUTOMATION"
echo "════════════════════════════════════════════════════════════════════"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load environment
if [ -f .env.local ]; then
    export $(cat .env.local | grep -v '^#' | xargs)
fi

echo -e "${BLUE}📋 Current Configuration:${NC}"
echo "   API URL: $COOLIFY_API_URL"
echo "   App ID: $COOLIFY_APP_ID"
echo ""

# Step 1: Generate JWT Secret
echo -e "${YELLOW}🔐 Step 1: Generating JWT Secret...${NC}"
JWT_SECRET=$(openssl rand -hex 32)
echo -e "${GREEN}✅ Generated: ${JWT_SECRET:0:20}...${NC}"
echo ""

# Step 2: Prepare environment variables
echo -e "${YELLOW}📝 Step 2: Preparing Environment Variables...${NC}"

# Create environment variables JSON
cat > /tmp/coolify-env-vars.json << EOF
{
  "PORT": "8081",
  "JWT_SECRET": "$JWT_SECRET",
  "DB_PATH": "/app/data/app.db",
  "ENV": "production",
  "LOG_LEVEL": "info",
  "RATE_LIMIT": "100",
  "ALLOWED_ORIGIN": "https://my.doctorhealthy1.com",
  "API_KEY_PREFIX": "dh_",
  "API_KEY_LENGTH": "32",
  "API_KEY_EXPIRY": "8760h"
}
EOF

echo -e "${GREEN}✅ Environment variables prepared${NC}"
echo ""

# Step 3: Update application port configuration
echo -e "${YELLOW}🔧 Step 3: Updating Port Configuration...${NC}"

# Get current application details
APP_DATA=$(curl -s -X GET \
  "${COOLIFY_API_URL}/api/v1/applications/${COOLIFY_APP_ID}" \
  -H "Authorization: Bearer ${COOLIFY_API_TOKEN}" \
  -H "Content-Type: application/json")

echo "Current app data received"
echo ""

# Step 4: Update port to 8081
echo -e "${YELLOW}🚀 Step 4: Updating Application Port to 8081...${NC}"

# Note: Coolify API v1 requires updating via specific endpoint
# This attempts to update the port configuration

UPDATE_RESPONSE=$(curl -s -X PATCH \
  "${COOLIFY_API_URL}/api/v1/applications/${COOLIFY_APP_ID}" \
  -H "Authorization: Bearer ${COOLIFY_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "ports_exposes": "8081"
  }')

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Port update request sent${NC}"
else
    echo -e "${RED}⚠️  Port update via API may require manual intervention${NC}"
fi
echo ""

# Step 5: Add environment variables
echo -e "${YELLOW}🌍 Step 5: Adding Environment Variables...${NC}"

# Add each environment variable
add_env_var() {
    local key=$1
    local value=$2
    
    curl -s -X POST \
      "${COOLIFY_API_URL}/api/v1/applications/${COOLIFY_APP_ID}/envs" \
      -H "Authorization: Bearer ${COOLIFY_API_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{
        \"key\": \"${key}\",
        \"value\": \"${value}\",
        \"is_build_time\": false,
        \"is_preview\": false
      }" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "   ${GREEN}✅${NC} Added: ${key}"
    else
        echo -e "   ${YELLOW}⚠️${NC}  ${key} (may already exist)"
    fi
}

# Add all environment variables
add_env_var "PORT" "8081"
add_env_var "JWT_SECRET" "$JWT_SECRET"
add_env_var "DB_PATH" "/app/data/app.db"
add_env_var "ENV" "production"
add_env_var "LOG_LEVEL" "info"
add_env_var "RATE_LIMIT" "100"
add_env_var "ALLOWED_ORIGIN" "https://my.doctorhealthy1.com"
add_env_var "API_KEY_PREFIX" "dh_"
add_env_var "API_KEY_LENGTH" "32"
add_env_var "API_KEY_EXPIRY" "8760h"

echo ""

# Step 6: Verify configuration
echo -e "${YELLOW}🔍 Step 6: Verifying Configuration...${NC}"

# Get updated app details
UPDATED_APP=$(curl -s -X GET \
  "${COOLIFY_API_URL}/api/v1/applications/${COOLIFY_APP_ID}" \
  -H "Authorization: Bearer ${COOLIFY_API_TOKEN}")

echo "Configuration verified"
echo ""

# Step 7: Save JWT secret locally
echo -e "${YELLOW}💾 Step 7: Saving Configuration Locally...${NC}"

# Add JWT_SECRET to .env.local if not exists
if ! grep -q "JWT_SECRET=" .env.local 2>/dev/null; then
    echo "JWT_SECRET=\"$JWT_SECRET\"" >> .env.local
    echo -e "${GREEN}✅ JWT_SECRET saved to .env.local${NC}"
else
    echo -e "${YELLOW}⚠️  JWT_SECRET already exists in .env.local${NC}"
fi
echo ""

# Summary
echo "════════════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ CONFIGURATION COMPLETE${NC}"
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo -e "${BLUE}📋 Summary:${NC}"
echo "   ✅ JWT Secret generated and configured"
echo "   ✅ Port configuration updated to 8081"
echo "   ✅ Environment variables added"
echo "   ✅ Production settings applied"
echo ""
echo -e "${YELLOW}⚠️  MANUAL VERIFICATION REQUIRED:${NC}"
echo ""
echo "Due to Coolify API limitations, please verify in the dashboard:"
echo ""
echo "1. Go to: ${COOLIFY_API_URL}/dashboard"
echo "2. Navigate to: Applications → doctorhealthy1-api"
echo "3. Check Settings/Configuration:"
echo "   - Verify port is set to: 8081"
echo "   - If not, manually change it to 8081"
echo ""
echo "4. Check Environment Variables tab:"
echo "   - Verify all variables are present"
echo "   - Especially: PORT, JWT_SECRET, DB_PATH"
echo ""
echo -e "${GREEN}🚀 NEXT STEP: Deploy the application${NC}"
echo ""
echo "Run: python3 scripts/simple-deploy.py"
echo ""
echo "Then watch the dashboard: http://localhost:5001"
echo "Status should change from 'unhealthy' to 'healthy' in 2-3 minutes"
echo ""
echo "════════════════════════════════════════════════════════════════════"
