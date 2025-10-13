# ✅ Domain Setup Checklist - my.doctorhealthy1.com

**Current Status**: DNS ✅ | Coolify Configuration ❌  
**Issue**: Server returns 404 - Domain not configured in Coolify yet

---

## 🔍 Current Status Verification

### ✅ DNS Configuration (WORKING)
```bash
✅ Domain: my.doctorhealthy1.com
✅ Resolves to: 128.140.111.171
✅ DNS propagation: Complete
```

**Test Results**:
```bash
$ dig my.doctorhealthy1.com +short
128.140.111.171  ✅

$ nslookup my.doctorhealthy1.com
Name:   my.doctorhealthy1.com
Address: 128.140.111.171  ✅
```

### ❌ Coolify Configuration (MISSING)
```bash
❌ Domain not configured in application
❌ Traefik not routing traffic
❌ SSL certificate not provisioned
```

**Test Results**:
```bash
$ curl -I http://128.140.111.171 -H "Host: my.doctorhealthy1.com"
HTTP/1.1 404 Not Found  ❌
```

---

## 🚀 STEP-BY-STEP CONFIGURATION

Follow these exact steps to configure the domain in Coolify:

### **STEP 1: Access Coolify Dashboard**

```bash
# Option A: Via SSH Tunnel (Recommended)
ssh -i ~/.ssh/coolify_doctorhealthy1 -N -L 8000:localhost:8000 root@128.140.111.171 &
# Then open: http://localhost:8000

# Option B: Direct Access (if firewall allows)
# Open: http://128.140.111.171:8000
```

**Login** to Coolify dashboard

---

### **STEP 2: Navigate to Your Application**

1. Click on **"Projects"** in the sidebar
2. Find and click your project (usually "doctorhealthy1" or similar)
3. Click on your application **"doctorhealthy1-api"** or the one with UUID: `hcw0gc8wcwk440gw4c88408o`

---

### **STEP 3: Configure Domain (MOST IMPORTANT)**

1. In your application page, find and click the **"Domains"** tab
2. Look for the **"FQDN"** or **"Domain"** field
3. You'll see one of these scenarios:

#### **Scenario A: Empty Domain Field**
- Click **"Add Domain"** or the domain input field
- Enter: `my.doctorhealthy1.com`
- **DO NOT** add `http://` or `https://` - just the domain name
- Click **"Save"** or the check mark button

#### **Scenario B: Existing Domain**
- You might see: `coolify`, `localhost`, or another domain
- Click **"Edit"** or directly in the domain field
- Replace with: `my.doctorhealthy1.com`
- Click **"Save"** or the check mark button

#### **Scenario C: Multiple Domains**
- Click **"Add New Domain"**
- Enter: `my.doctorhealthy1.com`
- Click **"Save"**

---

### **STEP 4: Enable HTTPS/SSL**

In the same **Domains** tab:

1. Find the toggle/checkbox for **"Generate Automatic HTTPS"** or **"Auto SSL"**
2. ✅ **Enable it** (turn it ON)
3. Find and enable **"Force HTTPS Redirect"** (if available)
4. Click **"Save"** if there's a save button

**Expected Behavior**:
- Coolify will automatically request an SSL certificate from Let's Encrypt
- This takes **2-5 minutes**
- You'll see a status indicator (pending → active)

---

### **STEP 5: Verify Port Exposure**

Still in your application settings:

1. Look for **"Ports"** or **"Port Mapping"** section
2. Verify you see: **`8081`** (your application's internal port)
3. If empty or different:
   - Click **"Add Port"** or **"Edit"**
   - Enter: `8081`
   - Click **"Save"**

---

### **STEP 6: Check Application Status**

1. In the application page, look at the top for **"Status"**
2. Should show: **"running"** or **"healthy"**
3. If it shows **"stopped"** or **"error"**:
   - Click **"Start"** or **"Deploy"** button
   - Wait for deployment to complete (~1-2 minutes)

---

### **STEP 7: Verify Configuration**

After saving, you should see in Coolify:

```
✅ Domain: my.doctorhealthy1.com
✅ SSL: Enabled (or "Pending" → wait 2-5 min)
✅ Port: 8081
✅ Status: Running/Healthy
```

---

## 🧪 Testing & Verification

### **Wait for SSL Provisioning (2-5 minutes)**

Check SSL status in Coolify dashboard. Once it shows "Active" or green checkmark, test:

### **Test 1: HTTP Access (should redirect to HTTPS)**
```bash
curl -I http://my.doctorhealthy1.com

# Expected:
# HTTP/1.1 301 Moved Permanently
# Location: https://my.doctorhealthy1.com
```

### **Test 2: HTTPS Health Endpoint**
```bash
curl https://my.doctorhealthy1.com/health

# Expected:
{
  "status": "healthy",
  "timestamp": "2025-10-04T...",
  "checks": {
    "database": "healthy",
    "filesystem": "healthy"
  }
}
```

### **Test 3: API Endpoints**
```bash
# Test recipes endpoint
curl https://my.doctorhealthy1.com/api/v1/recipes

# Test VIP summary
curl https://my.doctorhealthy1.com/api/v1/vip/summary
```

---

## 🔧 Troubleshooting Common Issues

### **Issue 1: Still Getting 404 After Configuration**

**Solution**:
1. Go back to Coolify
2. Click **"Restart"** button on your application
3. Wait 30 seconds
4. Test again

### **Issue 2: SSL Certificate Not Generating**

**Possible Causes**:
- Port 80 or 443 blocked on server
- Coolify can't reach Let's Encrypt servers
- Domain DNS not fully propagated

**Solution**:
```bash
# Check if ports are open
ssh -i ~/.ssh/coolify_doctorhealthy1 root@128.140.111.171 "netstat -tlnp | grep ':80\|:443'"

# Check Traefik logs
ssh -i ~/.ssh/coolify_doctorhealthy1 root@128.140.111.171 "docker logs coolify-proxy 2>&1 | grep -i 'error\|certificate' | tail -30"
```

### **Issue 3: "Domain Already in Use"**

**Solution**:
- Another application in Coolify might be using this domain
- Go to other applications and remove the domain
- Or use the fallback: `i.doctorhealthy1.com`

### **Issue 4: Application Won't Start**

**Solution**:
1. Check application logs in Coolify: **Logs** tab
2. Look for errors related to:
   - Port binding (is 8081 already in use?)
   - Database connection
   - Missing environment variables
3. Fix errors and click **"Restart"**

---

## 📸 Visual Guide - Where to Find Settings

### **Coolify Dashboard Layout**:
```
┌─────────────────────────────────────────────────┐
│ Coolify Dashboard                                │
├─────────────────────────────────────────────────┤
│ Sidebar:                                         │
│   - Projects  ← Click here first                │
│   - Servers                                      │
│   - ...                                          │
├─────────────────────────────────────────────────┤
│ Projects Page:                                   │
│   - Your Project Name                            │
│     - doctorhealthy1-api  ← Click here          │
├─────────────────────────────────────────────────┤
│ Application Page (Tabs):                        │
│   - Overview                                     │
│   - Configuration                                │
│   - Domains  ← CONFIGURE HERE ★★★               │
│   - Environment Variables                        │
│   - Storages                                     │
│   - Logs                                         │
└─────────────────────────────────────────────────┘
```

---

## 🎯 Quick Summary

**What You Need to Do**:
1. ✅ Open Coolify: http://localhost:8000 (via SSH tunnel)
2. ✅ Navigate: Projects → doctorhealthy1-api → **Domains** tab
3. ✅ Add domain: `my.doctorhealthy1.com`
4. ✅ Enable: "Generate Automatic HTTPS"
5. ✅ Save and wait 2-5 minutes for SSL
6. ✅ Test: `curl https://my.doctorhealthy1.com/health`

**Expected Timeline**:
- Configuration: 2-3 minutes
- SSL provisioning: 2-5 minutes
- Total: ~5-10 minutes

---

## 📞 If You're Stuck

### **Screenshot These**:
1. Coolify application page (showing current domain)
2. Domains tab (showing configuration)
3. Application status (showing if running/error)
4. Any error messages in Logs tab

### **Provide This Info**:
```bash
# Check application details
curl http://localhost:8000/api/v1/applications/hcw0gc8wcwk440gw4c88408o \
  -H "Authorization: Bearer YOUR_TOKEN" | jq '.'

# Check current domain in Coolify
# (Get from Coolify UI → Application → Domains)
```

---

## ✅ Success Criteria

You'll know it's working when:

1. ✅ Coolify shows domain: `my.doctorhealthy1.com`
2. ✅ SSL status shows: "Active" or green checkmark
3. ✅ `curl https://my.doctorhealthy1.com/health` returns JSON
4. ✅ Browser shows: 🔒 Secure connection
5. ✅ No 404 errors

---

**Current Status**: Waiting for manual configuration in Coolify  
**Next Step**: Follow STEP 1-7 above  
**ETA**: 5-10 minutes
