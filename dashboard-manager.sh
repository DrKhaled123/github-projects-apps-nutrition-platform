#!/bin/bash

# 🎯 Dashboard Manager Script
# Easily start, stop, restart, or check the dashboard status

set -e

DASHBOARD_PORT=5001
DASHBOARD_SCRIPT="scripts/simple-dashboard.py"
LOG_FILE="dashboard.log"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo " 📊 DASHBOARD MANAGER"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
}

check_port() {
    PID=$(lsof -ti:$DASHBOARD_PORT 2>/dev/null || echo "")
    if [ -n "$PID" ]; then
        echo -e "${GREEN}✅ Dashboard is running${NC} (PID: $PID, Port: $DASHBOARD_PORT)"
        
        # Check if it's responding
        if curl -s http://localhost:$DASHBOARD_PORT/api/status > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Dashboard is responding${NC}"
            STATUS=$(curl -s http://localhost:$DASHBOARD_PORT/api/status | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "unknown")
            echo -e "${BLUE}📊 Status: ${STATUS}${NC}"
        else
            echo -e "${YELLOW}⚠️  Dashboard not responding (may be starting up)${NC}"
        fi
        return 0
    else
        echo -e "${RED}❌ Dashboard is not running${NC}"
        return 1
    fi
}

stop_dashboard() {
    echo "🛑 Stopping dashboard..."
    PID=$(lsof -ti:$DASHBOARD_PORT 2>/dev/null || echo "")
    
    if [ -n "$PID" ]; then
        kill -9 $PID 2>/dev/null || true
        sleep 1
        
        # Verify it stopped
        if ! lsof -ti:$DASHBOARD_PORT > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Dashboard stopped successfully${NC}"
        else
            echo -e "${RED}❌ Failed to stop dashboard${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  Dashboard was not running${NC}"
    fi
}

start_dashboard() {
    echo "🚀 Starting dashboard..."
    
    # Check if port is in use
    if lsof -ti:$DASHBOARD_PORT > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Port $DASHBOARD_PORT is already in use${NC}"
        echo "   Use './dashboard-manager.sh restart' to restart the dashboard"
        return 1
    fi
    
    # Start dashboard
    python3 $DASHBOARD_SCRIPT > $LOG_FILE 2>&1 &
    sleep 3
    
    # Check if it started
    if lsof -ti:$DASHBOARD_PORT > /dev/null 2>&1; then
        PID=$(lsof -ti:$DASHBOARD_PORT)
        echo -e "${GREEN}✅ Dashboard started successfully${NC} (PID: $PID)"
        echo -e "${BLUE}📊 Access at: http://localhost:$DASHBOARD_PORT${NC}"
        
        # Test connectivity
        if curl -s http://localhost:$DASHBOARD_PORT/api/status > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Dashboard is responding${NC}"
        else
            echo -e "${YELLOW}⚠️  Dashboard started but not responding yet (check logs)${NC}"
        fi
    else
        echo -e "${RED}❌ Failed to start dashboard${NC}"
        echo "Check logs: tail -f $LOG_FILE"
        return 1
    fi
}

restart_dashboard() {
    echo "🔄 Restarting dashboard..."
    stop_dashboard
    sleep 2
    start_dashboard
}

show_logs() {
    if [ -f "$LOG_FILE" ]; then
        echo "📋 Dashboard logs (last 50 lines):"
        echo "════════════════════════════════════════════════════════════════"
        tail -50 $LOG_FILE
    else
        echo -e "${YELLOW}⚠️  No log file found${NC}"
    fi
}

open_browser() {
    echo "🌐 Opening dashboard in browser..."
    if command -v open > /dev/null 2>&1; then
        open http://localhost:$DASHBOARD_PORT
        echo -e "${GREEN}✅ Browser opened${NC}"
    elif command -v xdg-open > /dev/null 2>&1; then
        xdg-open http://localhost:$DASHBOARD_PORT
        echo -e "${GREEN}✅ Browser opened${NC}"
    else
        echo -e "${YELLOW}⚠️  Could not detect browser command${NC}"
        echo -e "${BLUE}📊 Access at: http://localhost:$DASHBOARD_PORT${NC}"
    fi
}

show_help() {
    cat << EOF
Usage: ./dashboard-manager.sh [COMMAND]

Commands:
  status      Check if dashboard is running
  start       Start the dashboard
  stop        Stop the dashboard
  restart     Restart the dashboard
  logs        Show dashboard logs
  open        Open dashboard in browser
  help        Show this help message

Examples:
  ./dashboard-manager.sh start
  ./dashboard-manager.sh status
  ./dashboard-manager.sh restart
  ./dashboard-manager.sh logs

Quick Access:
  Dashboard URL: http://localhost:$DASHBOARD_PORT
  API Status:    http://localhost:$DASHBOARD_PORT/api/status

EOF
}

# Main script
print_header

COMMAND=${1:-status}

case "$COMMAND" in
    status)
        check_port
        ;;
    start)
        start_dashboard
        ;;
    stop)
        stop_dashboard
        ;;
    restart)
        restart_dashboard
        ;;
    logs)
        show_logs
        ;;
    open)
        if check_port; then
            open_browser
        else
            echo "Dashboard is not running. Start it first with: ./dashboard-manager.sh start"
        fi
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}❌ Unknown command: $COMMAND${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac

echo ""
