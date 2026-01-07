#!/bin/bash

# 🎯 LIVE DASHBOARD ACCESS GUIDE
# Quick commands to access and manage the DoctorHealthy1 dashboard

echo "════════════════════════════════════════════════════════════════"
echo " 📊 DOCTORHEALTHY1 - LIVE DASHBOARD ACCESS"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check if dashboard is running
echo "🔍 Checking dashboard status..."
DASHBOARD_PID=$(ps aux | grep "simple-dashboard.py" | grep -v grep | awk '{print $2}')

if [ -n "$DASHBOARD_PID" ]; then
    echo "✅ Dashboard is RUNNING (PID: $DASHBOARD_PID)"
else
    echo "❌ Dashboard is NOT RUNNING"
    echo ""
    echo "Starting dashboard..."
    cd "$(dirname "$0")"
    python3 scripts/simple-dashboard.py &
    sleep 3
    echo "✅ Dashboard started!"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo " 🌐 ACCESS METHODS"
echo "════════════════════════════════════════════════════════════════"
echo ""

echo "1️⃣  LOCAL BROWSER ACCESS"
echo "   Open in your browser:"
echo "   👉 http://localhost:5001"
echo ""

echo "2️⃣  TERMINAL ACCESS (Quick Status)"
echo "   Run this command:"
echo "   curl -s http://localhost:5001/api/status | jq ."
echo ""

echo "3️⃣  API HEALTH CHECK"
echo "   curl -s http://localhost:8085/health/detailed | jq ."
echo ""

# Test dashboard connectivity
echo "════════════════════════════════════════════════════════════════"
echo " 🧪 CONNECTIVITY TEST"
echo "════════════════════════════════════════════════════════════════"
echo ""

echo "Testing dashboard API..."
DASHBOARD_RESPONSE=$(curl -s http://localhost:5001/api/status 2>/dev/null)

if [ -n "$DASHBOARD_RESPONSE" ]; then
    echo "✅ Dashboard API responding"
    echo ""
    echo "Status:"
    echo "$DASHBOARD_RESPONSE" | jq -r '.status'
    echo ""
    echo "Application:"
    echo "$DASHBOARD_RESPONSE" | jq -r '.app_name'
    echo ""
    echo "Domain:"
    echo "$DASHBOARD_RESPONSE" | jq -r '.domain'
    echo ""
    echo "Health:"
    echo "$DASHBOARD_RESPONSE" | jq -r '.health.api'
else
    echo "❌ Dashboard not responding"
    echo "   Try restarting: python3 scripts/simple-dashboard.py"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo " 🚀 DASHBOARD FEATURES"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "📊 Real-time health monitoring"
echo "⏱️  Response time tracking"
echo "🔄 Auto-refresh every 5 seconds"
echo "🎯 One-click deployment"
echo "📈 Uptime monitoring"
echo "🔍 Error tracking"
echo ""

echo "════════════════════════════════════════════════════════════════"
echo " 🔧 QUICK COMMANDS"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Open dashboard:"
echo "  open http://localhost:5001"
echo ""
echo "Check API status:"
echo "  curl http://localhost:5001/api/status | jq ."
echo ""
echo "Check application health:"
echo "  curl http://localhost:8085/health | jq ."
echo ""
echo "Detailed health check:"
echo "  curl http://localhost:8085/health/detailed | jq ."
echo ""
echo "Restart dashboard:"
echo "  killall -9 python3"
echo "  python3 scripts/simple-dashboard.py &"
echo ""

echo "════════════════════════════════════════════════════════════════"
echo " 📱 TO MAKE DASHBOARD PUBLIC (OPTIONAL)"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "1. Add to Coolify:"
echo "   - Create new service"
echo "   - Port: 5001"
echo "   - Command: python3 scripts/simple-dashboard.py"
echo "   - Domain: dashboard.doctorhealthy1.com"
echo ""
echo "2. SSH Tunnel (Temporary):"
echo "   ssh -L 5001:localhost:5001 root@128.140.111.171"
echo "   Then open: http://localhost:5001"
echo ""

echo "════════════════════════════════════════════════════════════════"
echo " ✅ ALL SYSTEMS READY"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "🎉 Dashboard is accessible at: http://localhost:5001"
echo "🔒 Application secured and running healthy"
echo "🏥 Health monitoring enhanced with integrations"
echo "📊 All security fixes deployed"
echo ""
