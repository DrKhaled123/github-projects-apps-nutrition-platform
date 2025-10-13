# 🌐 Domain Configuration Guide - my.doctorhealthy1.com

**Date**: October 4, 2025  
**Application**: DoctorHealthy1 API  
**Primary Domain**: my.doctorhealthy1.com  
**Fallback Domain**: i.doctorhealthy1.com  

---

## ✅ Prerequisites Completed

- ✅ DNS Records configured for my.doctorhealthy1.com
- ✅ Application deployed on Coolify (UUID: hcw0gc8wcwk440gw4c88408o)
- ✅ SSH tunnel available to Coolify server (128.140.111.171)

---

## 📋 Step-by-Step Configuration

### **Step 1: Access Coolify Dashboard**

```bash
# Establish SSH tunnel (if not already active)
ssh -i ~/.ssh/coolify_doctorhealthy1 -N -L 8000:localhost:8000 root@128.140.111.171 &

# Open Coolify in browser
open http://localhost:8000
```

**OR** access directly via: http://128.140.111.171:8000

---

### **Step 2: Configure Domain**

1. Navigate to: **Applications** → **doctorhealthy1-api**
2. Go to the **Domains** tab
3. Click **"Add Domain"** or edit existing domain
4. Enter: `my.doctorhealthy1.com`
5. **Enable the following options**:
   - ✅ **"Generate Automatic HTTPS"** (Let's Encrypt SSL)
   - ✅ **"Force HTTPS Redirect"**
6. Click **"Save"**

**Expected Result**: Coolify will automatically provision SSL certificate (2-5 minutes)

---

### **Step 3: Verify DNS Configuration**

Check your DNS records are pointing correctly:

```bash
# Check A record
dig my.doctorhealthy1.com A +short
# Should return: 128.140.111.171

# Check DNS propagation
nslookup my.doctorhealthy1.com
```

**Required DNS Record**:
```
Type: A
Name: my (or @)
Value: 128.140.111.171
TTL: 300 (or automatic)
```

---

### **Step 4: Configure Environment Variables**

While in the application settings, update environment variables:

1. Go to **Environment Variables** tab
2. Update or verify these variables:

```env
# Domain Configuration
ALLOWED_ORIGIN=https://my.doctorhealthy1.com

# CORS Origins (if you have multiple domains)
CORS_ORIGINS=https://my.doctorhealthy1.com,https://www.doctorhealthy1.com

# API Configuration (already set)
PORT=8081
HOST=0.0.0.0
ENV=production
```

3. Click **"Save"** and **"Restart"** the application

---

### **Step 5: Configure Persistent Storage (Important!)**

Your SQLite database needs persistent storage:

1. Go to **Storages** tab
2. Click **"Add Persistent Storage"**
3. Configure:
   - **Name**: `app-data`
   - **Mount Path**: `/app/data`
   - **Size**: `2GB` (or as needed)
4. Click **"Save"**

**⚠️ Warning**: The container will restart to apply storage changes.

---

### **Step 6: Verify Application Health**

After domain configuration, test the endpoints:

```bash
# Test health endpoint (wait 2-5 min for SSL)
curl https://my.doctorhealthy1.com/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2025-10-04T...",
  "checks": {
    "database": "healthy",
    "filesystem": "healthy"
  }
}

# Test API endpoint
curl https://my.doctorhealthy1.com/api/v1/recipes

# Test with authentication
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  https://my.doctorhealthy1.com/api/v1/apikeys
```

---

## 🔧 Troubleshooting

### **Issue 1: SSL Certificate Not Generating**

**Symptoms**: "Certificate pending" or "Let's Encrypt error"

**Solutions**:
1. Verify DNS is propagated: `dig my.doctorhealthy1.com +short`
2. Check port 80/443 are accessible on the server
3. Ensure domain is not behind Cloudflare proxy (orange cloud = off)
4. Wait 5-10 minutes and check logs in Coolify

**Check Logs**:
```bash
# In Coolify dashboard
Applications → Your App → Logs → Filter by "ssl" or "certificate"
```

---

### **Issue 2: Domain Not Accessible**

**Symptoms**: "Connection refused" or "DNS not found"

**Solutions**:
1. **Check DNS propagation** (can take up to 24 hours):
   ```bash
   # Check from multiple locations
   dig @8.8.8.8 my.doctorhealthy1.com
   dig @1.1.1.1 my.doctorhealthy1.com
   ```

2. **Verify Firewall Rules**:
   ```bash
   ssh -i ~/.ssh/coolify_doctorhealthy1 root@128.140.111.171
   sudo ufw status
   # Should show: 80/tcp, 443/tcp ALLOW
   ```

3. **Check Traefik (Coolify's reverse proxy)**:
   ```bash
   docker logs coolify-proxy
   ```

---

### **Issue 3: CORS Errors**

**Symptoms**: Browser console shows "CORS policy blocked"

**Solution**: Update `ALLOWED_ORIGIN` in environment variables:
```env
ALLOWED_ORIGIN=https://my.doctorhealthy1.com
CORS_ORIGINS=https://my.doctorhealthy1.com,https://www.doctorhealthy1.com
```

Then restart the application in Coolify.

---

## 🔄 Fallback Domain Configuration

If `my.doctorhealthy1.com` fails, use fallback domain:

### **Option 1: Use i.doctorhealthy1.com**

Repeat the same steps but use `i.doctorhealthy1.com` instead.

**Why it might fail**:
- **"my" subdomain** might conflict with some DNS providers' reserved names
- **"i" subdomain** is typically less restrictive

### **Option 2: Use nip.io (Development)**

For immediate testing without DNS configuration:

```
Domain: api.128.140.111.171.nip.io
```

This automatically resolves to your server IP.

**Configure in Coolify**:
1. Domain: `api.128.140.111.171.nip.io`
2. No SSL required (or use self-signed)
3. Test immediately without waiting for DNS

---

## 📊 Domain Configuration Comparison

| Domain | Pros | Cons | SSL | DNS Required |
|--------|------|------|-----|--------------|
| **my.doctorhealthy1.com** | ✅ Clean URL<br>✅ Branded | ⚠️ May conflict with DNS<br>⚠️ SSL setup time | Auto | Yes (A record) |
| **i.doctorhealthy1.com** | ✅ Less restrictive<br>✅ Faster setup | - | Auto | Yes (A record) |
| **api.128.140.111.171.nip.io** | ✅ No DNS needed<br>✅ Instant | ❌ Ugly URL<br>⚠️ Development only | Optional | No |

---

## ✅ Final Verification Checklist

After configuration, verify:

- [ ] Domain resolves to correct IP: `dig my.doctorhealthy1.com +short`
- [ ] SSL certificate is active: `curl -I https://my.doctorhealthy1.com`
- [ ] Health endpoint responds: `curl https://my.doctorhealthy1.com/health`
- [ ] API endpoints are accessible
- [ ] CORS headers are correct
- [ ] Persistent storage is mounted
- [ ] Environment variables are set
- [ ] Application logs show no errors

---

## 🚀 Post-Configuration Tasks

Once domain is working:

1. **Update Frontend Configuration**:
   - Update API base URL to `https://my.doctorhealthy1.com`
   - Test all API calls from frontend

2. **Update Documentation**:
   - Update README with new domain
   - Update API documentation
   - Notify users of the production URL

3. **Monitor Performance**:
   - Check response times
   - Monitor error rates
   - Review access logs

4. **Set Up Monitoring**:
   - Configure uptime monitoring (UptimeRobot, Pingdom)
   - Set up alerts for downtime
   - Monitor SSL certificate expiration

---

## 📞 Need Help?

### Quick Commands

```bash
# Check application status
curl http://localhost:8000/api/v1/applications/hcw0gc8wcwk440gw4c88408o \
  -H "Authorization: Bearer YOUR_TOKEN"

# Deploy application
./deploy.sh

# Check DNS
dig my.doctorhealthy1.com

# Test HTTPS
curl -I https://my.doctorhealthy1.com
```

### Access Information

- **Server IP**: 128.140.111.171
- **Coolify Dashboard**: http://localhost:8000 (via SSH tunnel)
- **Application UUID**: hcw0gc8wcwk440gw4c88408o
- **SSH Key**: ~/.ssh/coolify_doctorhealthy1

---

**Status**: 📝 Manual configuration required  
**Next Step**: Access Coolify dashboard and configure domain  
**ETA**: 5-10 minutes (+ SSL provisioning time)
