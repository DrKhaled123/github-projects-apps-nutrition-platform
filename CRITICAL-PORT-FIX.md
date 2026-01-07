# 🔧 Critical Fix Required - Port Mismatch

## Issue Identified ⚠️

**Port Configuration Mismatch Between Application and Coolify**

### Current Configuration:

| Component | Port | Status |
|-----------|------|--------|
| Application Code | 8081 | ✅ Correct (default in config.go) |
| Dockerfile | 8081 | ✅ Correct (EXPOSE 8081) |
| **Coolify** | **8080** | ❌ **WRONG** |

### Root Cause:
The application listens on port **8081** (see `internal/config/config.go` line 60), but Coolify is configured to connect to port **8080**. This causes health checks to fail because Coolify is checking the wrong port.

---

## Immediate Fix Required

### Option 1: Update Coolify Configuration (RECOMMENDED)
**Change Coolify port from 8080 to 8081**

1. Go to Coolify Dashboard: https://api.doctorhealthy1.com/dashboard
2. Navigate to: **Applications** → **doctorhealthy1-api**
3. Click: **Configuration** or **Settings**
4. Find: **Port** or **Ports Exposes** setting
5. Change: `8080` → `8081`
6. Click: **Save**
7. Redeploy:
   ```bash
   python3 scripts/simple-deploy.py
   ```

### Option 2: Change Application Port (Alternative)
**Set PORT environment variable to 8080**

1. Go to Coolify Dashboard
2. Navigate to: **doctorhealthy1-api** → **Environment Variables**
3. Add variable:
   ```
   PORT=8080
   ```
4. Redeploy:
   ```bash
   python3 scripts/simple-deploy.py
   ```

---

## Other Environment Variables Required

Based on diagnostic scan, these variables are **MISSING** in Coolify:

### 1. JWT_SECRET (REQUIRED)
```bash
JWT_SECRET=your-super-secret-key-at-least-32-characters-long
```

**Generate one**:
```bash
openssl rand -hex 32
```

### 2. DATABASE_URL or Database Components (REQUIRED)
Choose one option:

**Option A - Single Connection String**:
```bash
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

**Option B - Individual Components**:
```bash
DB_HOST=your-postgres-host
DB_PORT=5432
DB_NAME=doctorhealthy1_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password
```

**Note**: The application uses SQLite by default (`./data/app.db`), so if you want to use SQLite instead of PostgreSQL, you don't need DATABASE_URL. Just ensure the data directory is persistent.

### 3. Optional Environment Variables

```bash
# Application
PORT=8081
HOST=0.0.0.0
ENV=production

# Database (if using SQLite)
DB_PATH=/app/data/app.db

# Security
RATE_LIMIT=100
SECURITY_RATE_LIMIT_REQUESTS=100
SECURITY_RATE_LIMIT_WINDOW=60s

# API Keys
API_KEY_PREFIX=dh_
API_KEY_LENGTH=32
API_KEY_EXPIRY=8760h

# CORS
ALLOWED_ORIGIN=https://my.doctorhealthy1.com

# Logging
LOG_LEVEL=info
```

---

## Step-by-Step Fix Process

### Step 1: Access Coolify
```bash
# Open in browser
https://api.doctorhealthy1.com/dashboard
# Login with your credentials
```

### Step 2: Fix Port Configuration
1. Applications → **doctorhealthy1-api**
2. Settings/Configuration
3. Change port: `8080` → `8081`
4. Save

### Step 3: Add Environment Variables
1. Still in **doctorhealthy1-api**
2. Go to **Environment Variables** tab
3. Add each variable (click "+ Add Variable"):

```
JWT_SECRET = <generate-with-openssl-rand>
PORT = 8081
DB_PATH = /app/data/app.db
ENV = production
LOG_LEVEL = info
```

### Step 4: Save & Redeploy
```bash
python3 scripts/simple-deploy.py
```

### Step 5: Monitor Deployment
```bash
# Option 1: Live monitor
python3 scripts/live-monitor.py  # http://localhost:5001

# Option 2: Quick status
python3 scripts/quick-status.py

# Option 3: Wait 30 seconds, then check
sleep 30 && curl https://my.doctorhealthy1.com/health
```

---

## Expected Results After Fix

### Before Fix:
```bash
$ curl https://my.doctorhealthy1.com/health
→ HTTP 503 Service Unavailable
```

### After Fix:
```bash
$ curl https://my.doctorhealthy1.com/health
→ HTTP 200 OK
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2025-10-14T00:00:00Z"
}
```

### Application Status:
```bash
$ python3 scripts/quick-status.py
📊 Status: running:healthy ✅
```

---

## Verification Checklist

After applying fixes, verify:

- [ ] Coolify port changed to 8081
- [ ] JWT_SECRET added (minimum 32 characters)
- [ ] PORT=8081 environment variable added
- [ ] DB_PATH or DATABASE_URL configured
- [ ] Application redeployed successfully
- [ ] Health check returns 200 OK
- [ ] Application status is "running:healthy"
- [ ] Domain accessible: https://my.doctorhealthy1.com

---

## Quick Commands Reference

```bash
# 1. Check current status
python3 scripts/quick-status.py

# 2. Run diagnostics
python3 scripts/diagnose-health.py

# 3. Deploy after fixes
python3 scripts/simple-deploy.py

# 4. Test health endpoint
curl https://my.doctorhealthy1.com/health

# 5. Monitor live
python3 scripts/live-monitor.py  # http://localhost:5001

# 6. Run performance tests
python3 scripts/performance-test.py
```

---

## Troubleshooting

### If health checks still fail after fixes:

1. **Check container logs**:
   - Coolify Dashboard → doctorhealthy1-api → Logs
   - Look for:
     - "Server starting on :8081" ✅
     - Database connection errors ❌
     - Missing environment variable errors ❌

2. **Verify port binding**:
   ```bash
   # In Coolify container terminal
   netstat -tulpn | grep 8081
   # Should show: LISTEN on 0.0.0.0:8081
   ```

3. **Test health endpoint locally in container**:
   ```bash
   # In Coolify container terminal
   curl localhost:8081/health
   # Should return: {"status":"healthy"}
   ```

4. **Check Traefik routing**:
   - Ensure Traefik rule points to port 8081
   - Custom labels should have: `traefik.http.services.*.loadbalancer.server.port=8081`

---

## Summary

**CRITICAL**: Port mismatch is the root cause of health check failures.

**Solution**: Update Coolify port from 8080 → 8081

**Additional**: Add required environment variables (JWT_SECRET, PORT, etc.)

**Timeline**: 5-10 minutes to fix + 2-3 minutes deployment

**Impact**: Will resolve "running:unhealthy" status

---

**Generated**: 2025-10-14 00:10:00
**Priority**: 🚨 CRITICAL
**Estimated Fix Time**: 10 minutes
