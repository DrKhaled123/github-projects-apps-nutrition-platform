#!/bin/bash
# Deploy Go backend + SPA frontend to Coolify with best practices
set -e

# Load environment variables
if [ -f .env.local ]; then
  source .env.local
else
  echo "❌ .env.local not found!"; exit 1
fi

if [ -z "$COOLIFY_API_TOKEN" ] || [ -z "$COOLIFY_APP_UUID" ]; then
  echo "❌ COOLIFY_API_TOKEN or COOLIFY_APP_UUID not set!"; exit 1
fi

# Resolve API base URL
API_BASE="${COOLIFY_API_URL:-http://128.140.111.171:8000}"
API_ENDPOINT="${API_BASE%/}/api/v1"

request() {
  local method="$1"
  local path="$2"
  local data="$3"

  if [ -n "$data" ]; then
    RESPONSE=$(curl -s -w "\n%{http_code}" -X "$method" "${API_ENDPOINT}${path}" \
      -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
      -H "Content-Type: application/json" \
      -d "$data")
  else
    RESPONSE=$(curl -s -w "\n%{http_code}" -X "$method" "${API_ENDPOINT}${path}" \
      -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
      -H "Content-Type: application/json")
  fi

  BODY=$(echo "$RESPONSE" | sed '$d')
  STATUS=$(echo "$RESPONSE" | tail -n1)

  if [ "$STATUS" -ge 400 ]; then
    echo "❌ API request failed (${method} ${path}) - HTTP $STATUS" >&2
    [ -n "$BODY" ] && echo "$BODY" >&2
    exit 1
  fi

  echo "$BODY"
}

# Update Coolify app config: health check, publish dir, nginx
request PATCH "/applications/$COOLIFY_APP_UUID" '{
  "health_check_path": "/health",
  "health_check_port": "8081",
  "publish_directory": "frontend",
  "nginx_config_path": "nginx.conf"
}' > /dev/null

# Trigger deployment
request POST "/deploy" '{"uuid": "'$COOLIFY_APP_UUID'"}' > /dev/null

echo "🚀 Deployment triggered. Monitor Coolify dashboard for progress."
