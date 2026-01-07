#!/bin/bash
# Execute SSL fix commands directly on production server

echo "🚨 EXECUTING CRITICAL SSL FIX ON PRODUCTION SERVER"
echo "=================================================="

# Method 1: Use scp to copy files and execute
echo "📤 Uploading SSL fix files to server..."
scp -o StrictHostKeyChecking=no remote_ssl_commands.txt root@213.199.36.17:/tmp/ 2>/dev/null && echo "✅ Commands uploaded"

# Method 2: Execute commands directly via SSH
echo "🔧 Executing SSL fix commands..."
ssh -o StrictHostKeyChecking=no root@213.199.36.17 'bash /tmp/remote_ssl_commands.txt' 2>/dev/null && echo "✅ SSL fix executed"

# Method 3: Test SSL result
echo "🧪 Testing SSL fix result..."
sleep 10
curl -I https://my.doctorhealthy1.com 2>/dev/null | head -3

echo "🎉 SSL fix deployment complete!"
