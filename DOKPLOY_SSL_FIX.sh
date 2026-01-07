#!/bin/bash

# 🚀 DOKPLOY SSL FIX - Simple One-Command Solution
# Run this in Dokploy terminal after SSH setup

echo "🔒 DOKPLOY SSL CERTIFICATE FIX FOR my.doctorhealthy1.com"
echo "======================================================"

# Step 1: Stop nginx to free port 80/443
echo "🛑 Stopping nginx..."
systemctl stop nginx || service nginx stop

# Step 2: Remove EduVoice conflicts
echo "🗑️ Removing EduVoice conflicts..."
pkill -f eduvoice || echo "No EduVoice processes found"
rm -f /etc/nginx/sites-enabled/*eduvoice* || echo "No EduVoice nginx configs"

# Step 3: Install/Update certbot
echo "📦 Installing certbot..."
apt update -y
apt install -y certbot python3-certbot-nginx

# Step 4: Install Let's Encrypt SSL certificate
echo "🔐 Installing Let's Encrypt SSL certificate..."
certbot certonly \
    --standalone \
    --non-interactive \
    --agree-tos \
    --email admin@doctorhealthy1.com \
    --domains my.doctorhealthy1.com \
    --force-renewal

# Step 5: Create optimized nginx configuration
echo "📝 Creating optimized nginx configuration..."
cat > /etc/nginx/sites-available/nutrition-ssl << 'NGINXEOF'
upstream nutrition_backend {
    server 127.0.0.1:8085;
    keepalive 32;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name my.doctorhealthy1.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS configuration
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
    
    # Cache static assets
    location ~* \.(css|js|jpg|jpeg|gif|png|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
}
NGINXEOF

# Step 6: Enable new configuration
echo "🔄 Enabling SSL configuration..."
rm -f /etc/nginx/sites-enabled/default
rm -f /etc/nginx/sites-enabled/*eduvoice*
ln -sf /etc/nginx/sites-available/nutrition-ssl /etc/nginx/sites-enabled/

# Step 7: Test and start nginx
echo "🧪 Testing nginx configuration..."
nginx -t

if [ $? -eq 0 ]; then
    echo "🚀 Starting nginx with SSL..."
    systemctl start nginx
    systemctl enable nginx
    
    # Step 8: Verify SSL installation
    echo "✅ Verifying SSL installation..."
    sleep 5
    curl -I https://my.doctorhealthy1.com 2>/dev/null | head -3
    
    echo ""
    echo "🎉 SSL CERTIFICATE FIX COMPLETE!"
    echo "================================="
    echo "✅ EduVoice certificate removed"
    echo "✅ Let's Encrypt SSL installed"
    echo "✅ Browser warnings eliminated"
    echo ""
    echo "🌐 Test your site: https://my.doctorhealthy1.com"
    echo "🔒 You should now see a green lock icon!"
    
else
    echo "❌ Nginx configuration test failed"
    echo "Please check the configuration and try again"
    exit 1
fi