#!/usr/bin/env python3
"""
Real-time Monitoring Dashboard
Flask-based web dashboard showing live pipeline status, errors, and metrics
"""

import json
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, jsonify, render_template_string, request
import psutil

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

try:
    from ai_agents_shared_memory.utils.memory_manager import MemoryManager
    HAS_MEMORY = True
except Exception as e:
    print(f"Warning: Memory manager not available: {e}")
    HAS_MEMORY = False


app = Flask(__name__)

# Global state
dashboard_state = {
    "pipeline_status": "idle",
    "current_stage": None,
    "test_results": [],
    "build_results": [],
    "deploy_results": [],
    "errors": [],
    "metrics": {
        "cpu_usage": 0,
        "memory_usage": 0,
        "disk_usage": 0,
    },
    "last_update": datetime.now().isoformat(),
}


class DashboardMonitor:
    """Monitors system and pipeline state"""
    
    def __init__(self):
        self.memory = MemoryManager() if HAS_MEMORY else None
        self.logs_dir = Path("orchestration/logs")
        self.reports_dir = Path("orchestration/reports")
        self.running = False
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start the background monitoring thread"""
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("✅ Monitoring started")
    
    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        print("🛑 Monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self._update_system_metrics()
                self._check_pipeline_status()
                self._scan_for_errors()
                self._load_recent_reports()
                dashboard_state["last_update"] = datetime.now().isoformat()
                time.sleep(2)  # Update every 2 seconds
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(5)
    
    def _update_system_metrics(self):
        """Update system resource metrics"""
        try:
            dashboard_state["metrics"]["cpu_usage"] = psutil.cpu_percent(interval=0.1)
            dashboard_state["metrics"]["memory_usage"] = psutil.virtual_memory().percent
            dashboard_state["metrics"]["disk_usage"] = psutil.disk_usage('/').percent
        except Exception as e:
            print(f"Metrics error: {e}")
    
    def _check_pipeline_status(self):
        """Check current pipeline status from memory"""
        if not self.memory:
            return
        
        try:
            # Query memory for recent orchestration events
            results = self.memory.query(
                category="context",
                tags=["orchestration"],
                limit=10
            )
            
            if results:
                latest = results[0]
                data = latest.get("data", {})
                dashboard_state["pipeline_status"] = data.get("status", "idle")
                dashboard_state["current_stage"] = data.get("stage", None)
        except Exception as e:
            print(f"Status check error: {e}")
    
    def _scan_for_errors(self):
        """Scan log files for recent errors"""
        try:
            errors = []
            if self.logs_dir.exists():
                for log_file in self.logs_dir.glob("*.log"):
                    if log_file.stat().st_mtime > (time.time() - 3600):  # Last hour
                        with open(log_file, 'r') as f:
                            lines = f.readlines()[-50:]  # Last 50 lines
                            for line in lines:
                                if any(kw in line.lower() for kw in ['error', 'failed', 'exception']):
                                    errors.append({
                                        "timestamp": datetime.now().isoformat(),
                                        "file": log_file.name,
                                        "message": line.strip()[:200]
                                    })
            
            dashboard_state["errors"] = errors[-20:]  # Keep last 20 errors
        except Exception as e:
            print(f"Error scan error: {e}")
    
    def _load_recent_reports(self):
        """Load recent test/build/deploy reports"""
        try:
            if not self.reports_dir.exists():
                return
            
            # Load test reports
            test_reports = sorted(
                self.reports_dir.glob("test_*.json"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )[:5]
            
            dashboard_state["test_results"] = [
                self._load_json_report(r) for r in test_reports
            ]
            
            # Load build reports
            build_reports = sorted(
                self.reports_dir.glob("build_*.json"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )[:5]
            
            dashboard_state["build_results"] = [
                self._load_json_report(r) for r in build_reports
            ]
            
            # Load deploy reports
            deploy_reports = sorted(
                self.reports_dir.glob("deploy_*.json"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )[:5]
            
            dashboard_state["deploy_results"] = [
                self._load_json_report(r) for r in deploy_reports
            ]
            
        except Exception as e:
            print(f"Report loading error: {e}")
    
    def _load_json_report(self, file_path: Path) -> Dict:
        """Load and parse a JSON report file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                data["report_file"] = file_path.name
                return data
        except Exception:
            return {"error": f"Failed to load {file_path.name}"}


# Initialize monitor
monitor = DashboardMonitor()


# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CI/CD Monitoring Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            color: white;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 12px rgba(0,0,0,0.15);
        }
        .card h2 {
            color: #667eea;
            margin-bottom: 15px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .status {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9rem;
        }
        .status.idle { background: #e0e0e0; color: #666; }
        .status.running { background: #4caf50; color: white; animation: pulse 2s infinite; }
        .status.success { background: #4caf50; color: white; }
        .status.failed { background: #f44336; color: white; }
        .status.warning { background: #ff9800; color: white; }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        
        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 10px 0;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 6px;
        }
        .metric-label {
            font-weight: 600;
            color: #555;
        }
        .metric-value {
            font-size: 1.2rem;
            font-weight: bold;
            color: #667eea;
        }
        .progress-bar {
            width: 100%;
            height: 20px;
            background: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
            margin-top: 5px;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transition: width 0.5s;
        }
        .error-list {
            max-height: 400px;
            overflow-y: auto;
        }
        .error-item {
            background: #ffebee;
            border-left: 4px solid #f44336;
            padding: 10px;
            margin: 8px 0;
            border-radius: 4px;
            font-size: 0.9rem;
        }
        .error-item .timestamp {
            font-size: 0.8rem;
            color: #666;
            font-weight: bold;
        }
        .report-item {
            background: #f5f5f5;
            padding: 12px;
            margin: 8px 0;
            border-radius: 6px;
            border-left: 4px solid #667eea;
        }
        .report-item .report-name {
            font-weight: bold;
            color: #667eea;
        }
        .last-update {
            text-align: center;
            color: white;
            margin-top: 20px;
            font-size: 0.9rem;
        }
        .no-data {
            text-align: center;
            color: #999;
            padding: 20px;
            font-style: italic;
        }
    </style>
    <script>
        function updateDashboard() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    // Update pipeline status
                    const statusEl = document.getElementById('pipeline-status');
                    statusEl.textContent = data.pipeline_status;
                    statusEl.className = 'status ' + data.pipeline_status;
                    
                    // Update current stage
                    document.getElementById('current-stage').textContent = 
                        data.current_stage || 'None';
                    
                    // Update metrics
                    updateMetric('cpu', data.metrics.cpu_usage);
                    updateMetric('memory', data.metrics.memory_usage);
                    updateMetric('disk', data.metrics.disk_usage);
                    
                    // Update errors
                    updateErrors(data.errors);
                    
                    // Update reports
                    updateReports('test-reports', data.test_results);
                    updateReports('build-reports', data.build_results);
                    updateReports('deploy-reports', data.deploy_results);
                    
                    // Update timestamp
                    document.getElementById('last-update').textContent = 
                        'Last updated: ' + new Date(data.last_update).toLocaleString();
                })
                .catch(err => console.error('Update failed:', err));
        }
        
        function updateMetric(name, value) {
            document.getElementById(name + '-value').textContent = value.toFixed(1) + '%';
            document.getElementById(name + '-bar').style.width = value + '%';
            
            // Color code based on value
            const bar = document.getElementById(name + '-bar');
            if (value > 80) {
                bar.style.background = '#f44336';
            } else if (value > 60) {
                bar.style.background = '#ff9800';
            } else {
                bar.style.background = 'linear-gradient(90deg, #667eea, #764ba2)';
            }
        }
        
        function updateErrors(errors) {
            const container = document.getElementById('error-list');
            if (!errors || errors.length === 0) {
                container.innerHTML = '<div class="no-data">No recent errors</div>';
                return;
            }
            
            container.innerHTML = errors.slice(0, 10).map(err => `
                <div class="error-item">
                    <div class="timestamp">${new Date(err.timestamp).toLocaleTimeString()} - ${err.file}</div>
                    <div>${err.message}</div>
                </div>
            `).join('');
        }
        
        function updateReports(containerId, reports) {
            const container = document.getElementById(containerId);
            if (!reports || reports.length === 0) {
                container.innerHTML = '<div class="no-data">No recent reports</div>';
                return;
            }
            
            container.innerHTML = reports.map(report => {
                const status = report.success ? 'success' : 'failed';
                return `
                    <div class="report-item">
                        <div class="report-name">${report.report_file || 'Unknown'}</div>
                        <span class="status ${status}">${status.toUpperCase()}</span>
                        ${report.duration ? `<div>Duration: ${report.duration}s</div>` : ''}
                    </div>
                `;
            }).join('');
        }
        
        // Update every 2 seconds
        setInterval(updateDashboard, 2000);
        
        // Initial update
        window.onload = updateDashboard;
    </script>
</head>
<body>
    <div class="container">
        <h1>🚀 CI/CD Monitoring Dashboard</h1>
        
        <div class="grid">
            <div class="card">
                <h2>📊 Pipeline Status</h2>
                <div class="metric">
                    <span class="metric-label">Status:</span>
                    <span class="status" id="pipeline-status">Loading...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Current Stage:</span>
                    <span class="metric-value" id="current-stage">-</span>
                </div>
            </div>
            
            <div class="card">
                <h2>💻 System Metrics</h2>
                <div class="metric">
                    <span class="metric-label">CPU Usage</span>
                    <span class="metric-value" id="cpu-value">0%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="cpu-bar" style="width: 0%"></div>
                </div>
                
                <div class="metric">
                    <span class="metric-label">Memory Usage</span>
                    <span class="metric-value" id="memory-value">0%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="memory-bar" style="width: 0%"></div>
                </div>
                
                <div class="metric">
                    <span class="metric-label">Disk Usage</span>
                    <span class="metric-value" id="disk-value">0%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="disk-bar" style="width: 0%"></div>
                </div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h2>🧪 Recent Tests</h2>
                <div id="test-reports">
                    <div class="no-data">Loading...</div>
                </div>
            </div>
            
            <div class="card">
                <h2>🏗️ Recent Builds</h2>
                <div id="build-reports">
                    <div class="no-data">Loading...</div>
                </div>
            </div>
            
            <div class="card">
                <h2>🚀 Recent Deploys</h2>
                <div id="deploy-reports">
                    <div class="no-data">Loading...</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>❌ Recent Errors</h2>
            <div class="error-list" id="error-list">
                <div class="no-data">Loading...</div>
            </div>
        </div>
        
        <div class="last-update" id="last-update">Last updated: Never</div>
    </div>
</body>
</html>
"""


@app.route('/')
def index():
    """Serve the dashboard HTML"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/status')
def get_status():
    """API endpoint for dashboard data"""
    return jsonify(dashboard_state)


@app.route('/api/trigger/<stage>', methods=['POST'])
def trigger_stage(stage):
    """Trigger a specific pipeline stage"""
    valid_stages = ['test', 'review', 'build', 'deploy', 'full']
    
    if stage not in valid_stages:
        return jsonify({"error": "Invalid stage"}), 400
    
    # TODO: Implement stage triggering via main_orchestrator
    return jsonify({
        "message": f"Triggered {stage} pipeline",
        "status": "queued"
    })


def main():
    """Start the monitoring dashboard"""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║       🚀 CI/CD Real-time Monitoring Dashboard            ║
    ╚═══════════════════════════════════════════════════════════╝
    
    Starting dashboard server...
    """)
    
    # Start background monitoring
    monitor.start_monitoring()
    
    # Get port from environment or use default
    port = int(os.environ.get('DASHBOARD_PORT', 5000))
    host = os.environ.get('DASHBOARD_HOST', '0.0.0.0')
    
    print(f"""
    ✅ Dashboard running at: http://{host}:{port}
    
    Features:
    - Real-time pipeline status monitoring
    - System resource metrics (CPU, Memory, Disk)
    - Live error tracking
    - Test/Build/Deploy report viewing
    - Auto-refresh every 2 seconds
    
    Press Ctrl+C to stop
    """)
    
    try:
        app.run(host=host, port=port, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down dashboard...")
        monitor.stop_monitoring()
    except Exception as e:
        print(f"\n❌ Dashboard error: {e}")
        monitor.stop_monitoring()


if __name__ == "__main__":
    main()
