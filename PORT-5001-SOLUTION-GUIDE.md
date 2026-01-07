# 🔧 PORT 5001 "ADDRESS ALREADY IN USE" - SOLUTION GUIDE

## ❌ Problem
```
Address already in use
Port 5001 is in use by another program
```

## ✅ Quick Solutions

### Solution 1: Use Dashboard Manager (Recommended) ⭐

We've created a helper script that automatically manages the dashboard:

```bash
# Check status
./dashboard-manager.sh status

# Stop dashboard
./dashboard-manager.sh stop

# Start dashboard
./dashboard-manager.sh start

# Restart dashboard (stop + start)
./dashboard-manager.sh restart

# Open in browser
./dashboard-manager.sh open

# View logs
./dashboard-manager.sh logs
```

**This is the easiest way!** Just run:
```bash
./dashboard-manager.sh restart
```

---

### Solution 2: Manual Port Management

#### Step 1: Find what's using port 5001
```bash
lsof -ti:5001
# Output: PID number (e.g., 3299)
```

#### Step 2: Kill the process
```bash
kill -9 <PID>
# Example: kill -9 3299
```

#### Step 3: Verify port is free
```bash
lsof -ti:5001
# Should return nothing (empty)
```

#### Step 4: Start dashboard
```bash
python3 scripts/simple-dashboard.py > dashboard.log 2>&1 &
```

---

### Solution 3: One-Line Fix

Kill and restart in one command:
```bash
lsof -ti:5001 | xargs kill -9 2>/dev/null; sleep 2; python3 scripts/simple-dashboard.py > dashboard.log 2>&1 &
```

---

### Solution 4: Use Different Port

If you want to use a different port, edit `scripts/simple-dashboard.py`:

```python
# Change this line:
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=False)  # Changed to 5002
```

Then access at: `http://localhost:5002`

---

## 🔍 Troubleshooting

### Check if dashboard is running
```bash
ps aux | grep simple-dashboard | grep -v grep
```

### Check what's on port 5001
```bash
lsof -ti:5001
ps aux | grep $(lsof -ti:5001)
```

### Test dashboard connectivity
```bash
curl http://localhost:5001/api/status
```

### View dashboard logs
```bash
tail -f dashboard.log
```

---

## 🎯 Common Scenarios

### Scenario 1: Dashboard already running
**Symptom:** "Address already in use"
**Solution:** 
```bash
./dashboard-manager.sh restart
```

### Scenario 2: Dashboard crashed but port still held
**Symptom:** Port shows in use but dashboard not responding
**Solution:**
```bash
lsof -ti:5001 | xargs kill -9
sleep 2
./dashboard-manager.sh start
```

### Scenario 3: Multiple Python processes
**Symptom:** Several Python processes holding the port
**Solution:**
```bash
# Kill all Python dashboard processes
pkill -f simple-dashboard
sleep 2
./dashboard-manager.sh start
```

### Scenario 4: Permission denied
**Symptom:** Cannot kill process
**Solution:**
```bash
sudo kill -9 $(lsof -ti:5001)
./dashboard-manager.sh start
```

---

## 📊 Dashboard Manager Commands Reference

| Command | Description | Example |
|---------|-------------|---------|
| `status` | Check if running | `./dashboard-manager.sh status` |
| `start` | Start dashboard | `./dashboard-manager.sh start` |
| `stop` | Stop dashboard | `./dashboard-manager.sh stop` |
| `restart` | Restart dashboard | `./dashboard-manager.sh restart` |
| `logs` | View logs | `./dashboard-manager.sh logs` |
| `open` | Open in browser | `./dashboard-manager.sh open` |
| `help` | Show help | `./dashboard-manager.sh help` |

---

## ✅ Verification Steps

After fixing, verify everything works:

### 1. Check port is free
```bash
lsof -ti:5001
# Should return nothing
```

### 2. Start dashboard
```bash
./dashboard-manager.sh start
```

### 3. Verify it's running
```bash
./dashboard-manager.sh status
# Should show: ✅ Dashboard is running
```

### 4. Test API
```bash
curl http://localhost:5001/api/status | jq .
```

### 5. Open in browser
```bash
./dashboard-manager.sh open
# Or manually: open http://localhost:5001
```

---

## 🚀 Best Practices

1. **Always use dashboard-manager.sh** for starting/stopping
2. **Don't start multiple instances** - use restart instead
3. **Check logs if issues** - `./dashboard-manager.sh logs`
4. **Clean shutdown** - Use `./dashboard-manager.sh stop` before closing terminal
5. **Monitor process** - Use `./dashboard-manager.sh status` to check health

---

## 🆘 Emergency Commands

If nothing works, nuclear option:

```bash
# Kill everything on port 5001
sudo lsof -ti:5001 | xargs kill -9

# Kill all dashboard processes
pkill -9 -f simple-dashboard

# Kill all Python processes (careful!)
# pkill -9 python3  # Commented - only use if desperate!

# Clear port and restart
sleep 3
./dashboard-manager.sh start
```

---

## 📱 Quick Access

Once running:
- **Dashboard:** http://localhost:5001
- **API Status:** http://localhost:5001/api/status
- **Logs:** `tail -f dashboard.log`

---

## ✅ Your Issue - SOLVED!

**What happened:**
- Old dashboard process (PID 3299) was still running
- Port 5001 was held by that process
- New dashboard couldn't start

**What we did:**
1. ✅ Identified process: `lsof -ti:5001` → PID 3299
2. ✅ Killed process: `kill -9 3299`
3. ✅ Verified port free: `lsof -ti:5001` → empty
4. ✅ Started new dashboard: `python3 scripts/simple-dashboard.py &`
5. ✅ Verified working: Dashboard responding at port 5001

**Current Status:**
```
✅ Dashboard is running (PID: 14205)
✅ Port: 5001
✅ Status: running:healthy
✅ Access: http://localhost:5001
```

---

**🎉 Problem SOLVED! Dashboard is now running smoothly!**

Use `./dashboard-manager.sh` for easy management going forward!
