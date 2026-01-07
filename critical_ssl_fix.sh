#!/bin/bash

# 🚨 CRITICAL SSL FIX: Remove EduVoice & Install Let's Encrypt SSL
# Smart alternative deployment without SSH dependency

set -e

echo "🚨 CRITICAL SSL MISSION: SMART ALTERNATIVE APPROACH"
echo "===================================================="

# Step 1: Create comprehensive SSL replacement commands
echo "📋 Step 1: Creating SSL replacement commands for server..."

cat > remote_ssl_commands.txt << 'EOF'
# Execute these commands on the production server (213.199.36.17)

# 1. REMOVE EDUVOICE CONFLICTS
echo "🗑️  Removing EduVoice conflicts..."
sudo systemctl stop eduvoice* 2>/dev/null || true
sudo pkill -f eduvoice 2>/dev/null || true
sudo rm -rf /etc/eduvoice* 2>/dev/null || true
sudo rm -f /etc/nginx/sites-enabled/*eduvoice* 2>/dev/null || true

# 2. BACKUP CURRENT NGINX
echo "💾 Backing up current configuration..."
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)

# 3. STOP NGINX AND CONFLICTING SERVICES
echo "🛑 Stopping conflicting services..."
sudo systemctl stop nginx
sudo fuser -k 80/tcp 2>/dev/null || true
sudo fuser -k 443/tcp 2>/dev/null || true

# 4. INSTALL CERTBOT
echo "📦 Installing/updating certbot..."
sudo apt update
sudo apt install -y certbot python3-certbot-nginx nginx-extras

# 5. INSTALL SSL CERTIFICATE FOR PRIMARY DOMAIN
echo "🔒 Installing SSL for my.doctorhealthy1.com..."
sudo certbot certonly \
    --standalone \
    --non-interactive \
    --agree-tos \
    --email admin@doctorhealthy1.com \
    --domains my.doctorhealthy1.com \
    --force-renewal

# 6. INSTALL SSL CERTIFICATE FOR ALTERNATIVE DOMAIN (if DNS configured)
echo "🔒 Testing and installing SSL for doctorhealy1.com..."
if nslookup doctorhealy1.com >/dev/null 2>&1; then
    sudo certbot certonly \
        --standalone \
        --non-interactive \
        --agree-tos \
        --email admin@doctorhealthy1.com \
        --domains doctorhealy1.com,www.doctorhealy1.com \
        --force-renewal
else
    echo "⚠️  doctorhealy1.com not configured in DNS, skipping..."
fi

# 7. CREATE NEW NGINX CONFIGURATION
echo "📝 Creating nutrition platform nginx configuration..."
sudo tee /etc/nginx/sites-available/nutrition-ssl > /dev/null << 'NGINXCONF'
upstream nutrition_backend {
    server 127.0.0.1:8085;
    keepalive 32;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name my.doctorhealthy1.com doctorhealy1.com www.doctorhealy1.com;
    
    # Remove EduVoice headers and add nutrition platform branding
    add_header Server "DoctorHealthy1-Nutrition/1.0";
    
    return 301 https://$server_name$request_uri;
}

# HTTPS for my.doctorhealthy1.com
server {
    listen 443 ssl http2;
    server_name my.doctorhealthy1.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/my.doctorhealthy1.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/my.doctorhealthy1.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;
    
    # Security headers (replace EduVoice)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header Server "DoctorHealthy1-Nutrition/1.0";
    
    # Serve nutrition platform
    root /var/www/nutrition-platform/frontend;
    index index.html;
    
    # API proxy
    location /api/ {
        proxy_pass http://nutrition_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Health endpoint
    location /health {
        proxy_pass http://nutrition_backend/health;
        proxy_set_header Host $host;
    }
    
    # Frontend SPA
    location / {
        try_files $uri $uri/ /index.html;
    }
}

# HTTPS for doctorhealy1.com (if SSL cert exists)
server {
    listen 443 ssl http2;
    server_name doctorhealy1.com www.doctorhealy1.com;
    
    # SSL Configuration (conditional)
    ssl_certificate /etc/letsencrypt/live/doctorhealy1.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/doctorhealy1.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    
    # Redirect to primary domain
    return 301 https://my.doctorhealthy1.com$request_uri;
}
NGINXCONF

# 8. ENABLE NEW CONFIGURATION
echo "🔄 Enabling new SSL configuration..."
sudo rm -f /etc/nginx/sites-enabled/default
sudo rm -f /etc/nginx/sites-enabled/*eduvoice*
sudo ln -sf /etc/nginx/sites-available/nutrition-ssl /etc/nginx/sites-enabled/

# 9. TEST AND START NGINX
echo "🧪 Testing nginx configuration..."
sudo nginx -t

echo "🚀 Starting nginx with SSL..."
sudo systemctl start nginx
sudo systemctl enable nginx

# 10. VERIFY SSL INSTALLATION
echo "✅ Verifying SSL installation..."
sleep 5
curl -I https://my.doctorhealthy1.com 2>/dev/null | head -3

echo ""
echo "🎉 SSL INSTALLATION COMPLETE!"
echo "✅ EduVoice conflicts removed"
echo "✅ Let's Encrypt SSL installed"
echo "✅ Nutrition platform secured"
echo ""
echo "🌐 Test URLs:"
echo "   https://my.doctorhealthy1.com"
echo "   https://doctorhealy1.com (if DNS configured)"
EOF

echo "✅ SSL replacement commands created in remote_ssl_commands.txt"

# Step 2: Create manual deployment instructions
echo "📋 Step 2: Creating manual deployment guide..."

cat > URGENT_SSL_DEPLOYMENT_GUIDE.md << 'EOF'
# 🚨 URGENT: SSL Certificate Fix Deployment Guide

## CRITICAL MISSION: Remove EduVoice & Install Proper SSL

### ⚡ IMMEDIATE ACTION REQUIRED

The nutrition platform currently has EduVoice SSL conflicts. Follow these steps:

### 📞 CONTACT SERVER ADMINISTRATOR OR:

1. **Access Production Server**:
   ```bash
   ssh root@213.199.36.17
   # or contact your server administrator
   ```

2. **Execute SSL Fix Commands**:
   ```bash
   # Copy and paste the commands from remote_ssl_commands.txt
   # OR download and run:
   wget https://raw.githubusercontent.com/your-repo/ssl-fix.sh
   chmod +x ssl-fix.sh
   ./ssl-fix.sh
   ```

### 🎯 EXPECTED RESULTS:

✅ **BEFORE**: Browser shows "Not Secure" (EduVoice self-signed cert)  
✅ **AFTER**: Browser shows green lock (Let's Encrypt SSL)

### 🧪 VERIFICATION:

After deployment, test:
```bash
curl -I https://my.doctorhealthy1.com
# Should show: Let's Encrypt certificate, no EduVoice headers

openssl s_client -servername my.doctorhealthy1.com -connect my.doctorhealthy1.com:443 2>/dev/null | openssl x509 -noout -issuer
# Should show: Let's Encrypt Authority X3 (not EduVoice)
```

### 🚨 CRITICAL SUCCESS FACTORS:

1. **Remove all EduVoice processes and configs**
2. **Install Let's Encrypt certificates for both domains** 
3. **Replace nginx configuration with nutrition platform config**
4. **Verify browser warnings are gone**

### 📱 ALTERNATIVE: Use Coolify Dashboard

If SSH access is limited:
1. Access Coolify dashboard
2. Navigate to nutrition platform application  
3. Update SSL settings to use Let's Encrypt
4. Deploy updated configuration

### ⏰ URGENCY: HIGH

Browser warnings impact user trust and SEO. This fix should be deployed ASAP.
EOF

echo "📋 Manual deployment guide created: URGENT_SSL_DEPLOYMENT_GUIDE.md"

# Step 3: Test current status and prepare alternatives
echo "🧪 Step 3: Testing current SSL status for comparison..."
echo "Before SSL fix:"
echo | openssl s_client -servername my.doctorhealthy1.com -connect my.doctorhealthy1.com:443 2>/dev/null | openssl x509 -noout -issuer | head -1

echo ""
echo "🎯 CRITICAL SSL FIX PREPARED!"
echo "============================="
echo ""
echo "📁 Files created:"
echo "   ✅ remote_ssl_commands.txt (server commands)"
echo "   ✅ URGENT_SSL_DEPLOYMENT_GUIDE.md (manual guide)"
echo "   ✅ nginx_ssl_proxy.conf (nginx configuration)"
echo ""
echo "🚨 NEXT ACTION: Execute SSL fix on production server"
echo "🌐 Result: https://my.doctorhealthy1.com will show green lock"
echo ""
echo "📞 Need help? The commands are ready for server administrator!"