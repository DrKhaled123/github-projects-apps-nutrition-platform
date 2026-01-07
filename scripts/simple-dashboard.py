#!/usr/bin/env python3
"""
Simple Real-Time Dashboard
Lightweight monitoring interface
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
import requests

# Load environment
env_file = Path(".env.local")
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip('"').strip("'")

app = Flask(__name__)
CORS(app)

API_URL = os.environ.get("COOLIFY_API_URL", "")
API_TOKEN = os.environ.get("COOLIFY_API_TOKEN", "")
APP_ID = os.environ.get("COOLIFY_APP_ID", "")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DoctorHealthy1 - Live Monitor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .refresh-info {
            color: rgba(255,255,255,0.9);
            font-size: 0.9em;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
        }
        
        .card h2 {
            font-size: 1.3em;
            margin-bottom: 15px;
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        
        .status-badge {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
            margin: 10px 0;
        }
        
        .status-healthy {
            background: #10b981;
            color: white;
        }
        
        .status-unhealthy {
            background: #ef4444;
            color: white;
        }
        
        .status-building {
            background: #f59e0b;
            color: white;
        }
        
        .status-unknown {
            background: #6b7280;
            color: white;
        }
        
        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #e5e7eb;
        }
        
        .info-row:last-child {
            border-bottom: none;
        }
        
        .info-label {
            font-weight: 600;
            color: #6b7280;
        }
        
        .info-value {
            color: #1f2937;
            font-family: monospace;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            margin: 5px;
            transition: transform 0.2s;
        }
        
        .btn:hover {
            transform: translateY(-2px);
        }
        
        .btn:active {
            transform: translateY(0);
        }
        
        .error {
            background: #fee2e2;
            border-left: 4px solid #ef4444;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            color: #991b1b;
        }
        
        .success {
            background: #d1fae5;
            border-left: 4px solid #10b981;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            color: #065f46;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            font-size: 1.2em;
            color: #6b7280;
        }
        
        .countdown {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(255,255,255,0.9);
            padding: 15px 20px;
            border-radius: 10px;
            font-weight: 600;
            color: #667eea;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .pulse {
            animation: pulse 2s infinite;
        }
    </style>
</head>
<body>
    <div class="countdown" id="countdown">Refreshing in <span id="timer">5</span>s</div>
    
    <div class="container">
        <div class="header">
            <h1>🏥 DoctorHealthy1 Live Monitor</h1>
            <p class="refresh-info">Auto-refresh every 5 seconds | <span id="timestamp"></span></p>
        </div>
        
        <div style="text-align: center; margin-bottom: 20px;">
            <button class="btn" onclick="refreshNow()">🔄 Refresh Now</button>
            <button class="btn" onclick="triggerDeploy()">🚀 Deploy Now</button>
        </div>
        
        <div id="content" class="loading pulse">
            Loading application status...
        </div>
    </div>
    
    <script>
        let countdown = 5;
        let timerInterval;
        let isFetching = false;
        let lastFetchTime = 0;
        const MIN_FETCH_INTERVAL = 4000; // Minimum 4 seconds between requests
        let requestCount = 0;
        let startTime = Date.now();
        
        // Page Visibility API - prevent background tabs from making requests
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                console.log('🔴 Tab hidden - pausing requests');
                clearInterval(timerInterval);
            } else {
                console.log('🟢 Tab visible - resuming requests');
                startCountdown();
                // Don't fetch immediately on visibility change if rate limit active
                const timeSinceLastFetch = Date.now() - lastFetchTime;
                if (timeSinceLastFetch >= MIN_FETCH_INTERVAL) {
                    fetchStatus();
                }
            }
        });
        
        function updateTimestamp() {
            document.getElementById('timestamp').textContent = new Date().toLocaleString();
        }
        
        function logRequestStats() {
            requestCount++;
            const elapsed = (Date.now() - startTime) / 1000;
            const rate = (requestCount / elapsed * 60).toFixed(1);
            console.log(`📊 Request #${requestCount} | Rate: ${rate} req/min | Expected: 12 req/min`);
        }
        
        function startCountdown() {
            countdown = 5;
            clearInterval(timerInterval);
            timerInterval = setInterval(() => {
                // Don't countdown or fetch if tab is hidden
                if (document.hidden) {
                    console.log('⏸️ Tab hidden - countdown paused');
                    return;
                }
                countdown--;
                document.getElementById('timer').textContent = countdown;
                if (countdown <= 0) {
                    fetchStatus();
                }
            }, 1000);
        }
        
        function fetchStatus() {
            // Prevent multiple simultaneous requests
            if (isFetching) {
                console.log('⏭️ Request already in progress, skipping...');
                startCountdown();
                return;
            }
            
            // Check if tab is visible - don't fetch if hidden
            if (document.hidden) {
                console.log('🔴 Tab hidden, skipping fetch');
                startCountdown();
                return;
            }
            
            // Rate limiting - prevent requests too close together
            const now = Date.now();
            if (now - lastFetchTime < MIN_FETCH_INTERVAL) {
                const waitTime = ((MIN_FETCH_INTERVAL - (now - lastFetchTime)) / 1000).toFixed(1);
                console.log(`⏳ Rate limit active: wait ${waitTime}s before next request`);
                startCountdown();
                return;
            }
            
            isFetching = true;
            lastFetchTime = now;
            logRequestStats();
            console.log('🌐 Fetching /api/status...');
            
            fetch('/api/status')
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('✅ Status fetched successfully');
                    updateUI(data);
                    isFetching = false;
                    startCountdown();
                })
                .catch(error => {
                    console.error('❌ Fetch error:', error);
                    document.getElementById('content').innerHTML = 
                        '<div class="error">❌ Failed to fetch status: ' + error.message + '</div>';
                    isFetching = false;
                    startCountdown();
                });
        }
        
        function updateUI(data) {
            const statusClass = data.status.includes('healthy') ? 'status-healthy' :
                               data.status.includes('unhealthy') ? 'status-unhealthy' :
                               data.status.includes('building') ? 'status-building' :
                               'status-unknown';
            
            let html = '<div class="grid">';
            
            // Application Status Card
            html += `
                <div class="card">
                    <h2>📱 Application Status</h2>
                    <div class="status-badge ${statusClass}">${data.status.toUpperCase()}</div>
                    <div class="info-row">
                        <span class="info-label">Name:</span>
                        <span class="info-value">${data.app_name}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Domain:</span>
                        <span class="info-value">${data.domain}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Last Update:</span>
                        <span class="info-value">${data.last_update}</span>
                    </div>
                </div>
            `;
            
            // Health Checks Card
            html += `
                <div class="card">
                    <h2>🏥 Health Checks</h2>
                    <div class="info-row">
                        <span class="info-label">API Status:</span>
                        <span class="info-value">${data.health.api || 'Unknown'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Database:</span>
                        <span class="info-value">${data.health.database || 'Unknown'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Response Time:</span>
                        <span class="info-value">${data.health.response_time || 'N/A'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Uptime:</span>
                        <span class="info-value">${data.health.uptime || 'N/A'}</span>
                    </div>
                </div>
            `;
            
            // Deployments Card
            html += `
                <div class="card">
                    <h2>🚀 Recent Deployments</h2>
                    ${data.deployments.length > 0 ? 
                        data.deployments.slice(0, 5).map(d => `
                            <div class="info-row">
                                <span class="info-label">${d.timestamp || 'Unknown'}</span>
                                <span class="info-value">${d.status || 'Unknown'}</span>
                            </div>
                        `).join('') :
                        '<p style="color: #6b7280;">No recent deployments</p>'
                    }
                </div>
            `;
            
            html += '</div>';
            
            // Errors section
            if (data.errors && data.errors.length > 0) {
                html += '<div class="card">';
                html += '<h2>⚠️ Errors & Warnings</h2>';
                data.errors.forEach(error => {
                    html += `<div class="error">${error}</div>`;
                });
                html += '</div>';
            }
            
            document.getElementById('content').innerHTML = html;
            updateTimestamp();
        }
        
        function refreshNow() {
            // Prevent multiple rapid clicks
            if (isFetching) {
                console.log('Already fetching, please wait...');
                return;
            }
            
            document.getElementById('content').innerHTML = 
                '<div class="loading pulse">Refreshing...</div>';
            
            // Reset rate limiting for manual refresh
            lastFetchTime = 0;
            fetchStatus();
        }
        
        function triggerDeploy() {
            if (!confirm('Deploy the application now?')) return;
            
            if (isFetching) {
                alert('Please wait for current operation to complete');
                return;
            }
            
            document.getElementById('content').innerHTML = 
                '<div class="loading pulse">Triggering deployment...</div>';
            
            fetch('/api/deploy', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('content').innerHTML = 
                            '<div class="success">✅ Deployment queued! UUID: ' + data.deployment_uuid + '</div>';
                        setTimeout(() => {
                            lastFetchTime = 0;
                            fetchStatus();
                        }, 3000);
                    } else {
                        document.getElementById('content').innerHTML = 
                            '<div class="error">❌ Deployment failed: ' + data.error + '</div>';
                        setTimeout(() => {
                            lastFetchTime = 0;
                            fetchStatus();
                        }, 3000);
                    }
                })
                .catch(error => {
                    document.getElementById('content').innerHTML = 
                        '<div class="error">❌ Error: ' + error.message + '</div>';
                    setTimeout(fetchStatus, 3000);
                });
        }
        
        // Initialize
        updateTimestamp();
        fetchStatus();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def get_status():
    try:
        response = requests.get(
            f"{API_URL}/api/v1/applications",
            headers={"Authorization": f"Bearer {API_TOKEN}"},
            timeout=10
        )
        
        if response.status_code == 200:
            apps = response.json()
            app = next((a for a in apps if a['uuid'] == APP_ID), None)
            
            if app:
                return jsonify({
                    "status": app.get('status', 'unknown'),
                    "app_name": app.get('name', 'Unknown'),
                    "domain": app.get('fqdn', 'my.doctorhealthy1.com'),
                    "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "deployments": [],
                    "health": {
                        "api": "✅ Connected",
                        "database": "Unknown",
                        "response_time": f"{int(response.elapsed.total_seconds() * 1000)}ms",
                        "uptime": "N/A"
                    },
                    "errors": [] if 'unhealthy' not in app.get('status', '') else [
                        "Application is unhealthy - Check CRITICAL-PORT-FIX.md",
                        "Port mismatch detected: App uses 8081, Coolify expects 8080"
                    ]
                })
        
        return jsonify({
            "status": "error",
            "app_name": "DoctorHealthy1 API",
            "domain": "my.doctorhealthy1.com",
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "deployments": [],
            "health": {},
            "errors": [f"API error: {response.status_code}"]
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "app_name": "DoctorHealthy1 API",
            "domain": "my.doctorhealthy1.com",
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "deployments": [],
            "health": {},
            "errors": [str(e)]
        })

@app.route('/api/deploy', methods=['POST'])
def deploy():
    try:
        response = requests.post(
            f"{API_URL}/api/v1/deploy?uuid={APP_ID}&force=false",
            headers={"Authorization": f"Bearer {API_TOKEN}"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                "success": True,
                "deployment_uuid": result['deployments'][0]['deployment_uuid']
            })
        else:
            return jsonify({
                "success": False,
                "error": f"API returned {response.status_code}"
            })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("🚀 SIMPLE LIVE DASHBOARD")
    print("=" * 70)
    print(f"\n🌐 Dashboard: http://localhost:5001")
    print(f"🔄 Auto-refresh: Every 5 seconds")
    print(f"📱 Monitoring: {APP_ID}")
    print(f"\n✅ Press Ctrl+C to stop\n")
    print("=" * 70 + "\n")
    
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
