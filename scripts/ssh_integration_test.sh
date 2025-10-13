#!/bin/bash
# Real-time SSH Integration Testing Script
# Tests deployment, connectivity, and live API endpoints

set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

SSH_KEY="$HOME/.ssh/coolify_doctorhealthy1"
SERVER="128.140.111.171"
DOMAIN="my.doctorhealthy1.com"

echo -e "${BOLD}${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║     REAL-TIME SSH & INTEGRATION TESTING SYSTEM             ║${NC}"
echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════╝${NC}\n"

# Test 1: SSH Connectivity
echo -e "${CYAN}[1/8] Testing SSH connectivity...${NC}"
if ssh -i "$SSH_KEY" -o ConnectTimeout=10 root@$SERVER 'echo "SSH OK"' > /dev/null 2>&1; then
    echo -e "${GREEN}✅ SSH connection successful${NC}"
else
    echo -e "${RED}❌ SSH connection failed${NC}"
    exit 1
fi

# Test 2: Docker Status
echo -e "\n${CYAN}[2/8] Checking Docker containers...${NC}"
CONTAINERS=$(ssh -i "$SSH_KEY" root@$SERVER "docker ps --filter 'name=doctorhealthy' --format '{{.Names}}\t{{.Status}}'")
if [ -n "$CONTAINERS" ]; then
    echo -e "${GREEN}✅ Containers found:${NC}"
    echo "$CONTAINERS"
else
    echo -e "${YELLOW}⚠️  No DoctorHealthy containers running${NC}"
fi

# Test 3: Server Health
echo -e "\n${CYAN}[3/8] Testing internal server health...${NC}"
HEALTH=$(ssh -i "$SSH_KEY" root@$SERVER "curl -s http://localhost:8081/health 2>/dev/null || echo 'FAIL'")
if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✅ Internal health check passed${NC}"
    echo "$HEALTH" | head -5
else
    echo -e "${YELLOW}⚠️  Internal health check unclear${NC}"
fi

# Test 4: DNS Resolution
echo -e "\n${CYAN}[4/8] Verifying DNS resolution...${NC}"
DNS_IP=$(dig +short $DOMAIN | head -1)
if [ "$DNS_IP" = "$SERVER" ]; then
    echo -e "${GREEN}✅ DNS resolves correctly: $DOMAIN → $SERVER${NC}"
else
    echo -e "${RED}❌ DNS mismatch: $DOMAIN → $DNS_IP (expected $SERVER)${NC}"
fi

# Test 5: Domain HTTP Response
echo -e "\n${CYAN}[5/8] Testing domain HTTP response...${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 http://$DOMAIN 2>/dev/null || echo "000")
echo -e "HTTP Status: ${YELLOW}$HTTP_CODE${NC}"
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ]; then
    echo -e "${GREEN}✅ Domain responding${NC}"
elif [ "$HTTP_CODE" = "404" ]; then
    echo -e "${RED}❌ Domain returns 404 - Not configured in Coolify${NC}"
else
    echo -e "${YELLOW}⚠️  Unexpected response code${NC}"
fi

# Test 6: HTTPS/SSL Status
echo -e "\n${CYAN}[6/8] Checking HTTPS/SSL...${NC}"
if timeout 10 curl -s -k -I https://$DOMAIN 2>/dev/null | head -1 | grep -q "HTTP"; then
    SSL_STATUS=$(timeout 10 curl -s -k -I https://$DOMAIN 2>/dev/null | head -1)
    echo -e "${GREEN}✅ HTTPS responding: $SSL_STATUS${NC}"
else
    echo -e "${YELLOW}⚠️  HTTPS not yet available (SSL may be provisioning)${NC}"
fi

# Test 7: Coolify API Check
echo -e "\n${CYAN}[7/8] Testing Coolify API accessibility...${NC}"
ssh -i "$SSH_KEY" -N -L 8001:localhost:8000 root@$SERVER &
SSH_PID=$!
sleep 3

COOLIFY_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001 2>/dev/null || echo "000")
if [ "$COOLIFY_STATUS" = "200" ] || [ "$COOLIFY_STATUS" = "302" ]; then
    echo -e "${GREEN}✅ Coolify dashboard accessible${NC}"
    echo -e "   Access: http://localhost:8001"
else
    echo -e "${YELLOW}⚠️  Coolify dashboard not accessible${NC}"
fi

kill $SSH_PID 2>/dev/null || true

# Test 8: Application Logs
echo -e "\n${CYAN}[8/8] Fetching recent application logs...${NC}"
LOGS=$(ssh -i "$SSH_KEY" root@$SERVER "docker logs --tail=20 \$(docker ps -q --filter 'name=doctorhealthy' | head -1) 2>&1 || echo 'No logs available'")
if echo "$LOGS" | grep -qi "error"; then
    echo -e "${RED}⚠️  Errors found in logs:${NC}"
    echo "$LOGS" | grep -i "error" | head -5
else
    echo -e "${GREEN}✅ No critical errors in recent logs${NC}"
    echo "$LOGS" | tail -5
fi

# Summary
echo -e "\n${BOLD}${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║                    TEST SUMMARY                            ║${NC}"
echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"

echo -e "\n${BOLD}Quick Action Items:${NC}"
if [ "$HTTP_CODE" = "404" ]; then
    echo -e "${YELLOW}1. Configure domain in Coolify:${NC}"
    echo -e "   - Access: http://localhost:8001"
    echo -e "   - Go to: Applications → doctorhealthy1-api → Domains"
    echo -e "   - Add: $DOMAIN"
    echo -e "   - Enable: Generate Automatic HTTPS"
fi

echo -e "\n${GREEN}✅ Integration testing complete!${NC}"
echo -e "${CYAN}Timestamp: $(date)${NC}\n"
