"""Simple Web Monitor - Lightweight alternative to full ops console.

This provides basic real-time monitoring without complex dependencies.
"""

import asyncio
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from collections import deque
import webbrowser

logger = logging.getLogger(__name__)

# Simple in-memory storage
class MonitorState:
    def __init__(self):
        self.agents = {}
        self.events = deque(maxlen=100)
        self.jobs = {}
        self.start_time = datetime.now()
        
    def add_event(self, event):
        self.events.append({
            'timestamp': datetime.now().isoformat(),
            'event': event
        })
    
    def update_agent(self, agent_name, status):
        self.agents[agent_name] = {
            'name': agent_name,
            'status': status,
            'last_update': datetime.now().isoformat()
        }
    
    def add_job(self, job_id, job_info):
        self.jobs[job_id] = job_info

state = MonitorState()


class SimpleWebMonitor:
    """Simple HTTP server for monitoring."""
    
    def __init__(self, host='0.0.0.0', port=8080):
        self.host = host
        self.port = port
        self.running = False
        self.server_thread = None
        
    def start(self):
        """Start the monitoring web server."""
        try:
            from http.server import HTTPServer, BaseHTTPRequestHandler
            
            monitor_state = state
            
            class MonitorHandler(BaseHTTPRequestHandler):
                def log_message(self, format, *args):
                    pass  # Suppress default logging
                
                def do_GET(self):
                    if self.path == '/':
                        self.send_html()
                    elif self.path == '/api/status':
                        self.send_status()
                    else:
                        self.send_response(404)
                        self.end_headers()
                
                def send_html(self):
                    html = """<!DOCTYPE html>
<html>
<head>
    <title>Blog Generator Monitor</title>
    <meta charset="UTF-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f1419;
            color: #e8eaed;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        header {
            background: linear-gradient(135deg, #1a1f2e 0%, #2d3748 100%);
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        h1 { font-size: 2rem; margin-bottom: 10px; }
        .status-bar {
            display: flex;
            gap: 20px;
            margin-top: 15px;
            flex-wrap: wrap;
        }
        .status-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: rgba(255,255,255,0.05);
            border-radius: 4px;
        }
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #10b981;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .section {
            background: #1a1f2e;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .section h2 {
            margin-bottom: 15px;
            color: #60a5fa;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
        }
        .card {
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 6px;
            border-left: 3px solid #10b981;
        }
        .card.warning { border-left-color: #f59e0b; }
        .card.error { border-left-color: #ef4444; }
        .card h3 {
            font-size: 0.9rem;
            color: #9ca3af;
            margin-bottom: 5px;
        }
        .card .value {
            font-size: 1.5rem;
            font-weight: bold;
        }
        .events {
            max-height: 400px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.85rem;
        }
        .event {
            padding: 8px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .event .time {
            color: #60a5fa;
            margin-right: 10px;
        }
        .refresh-indicator {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #10b981;
            color: white;
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="refresh-indicator">🔄 Auto-refreshing...</div>
    <div class="container">
        <header>
            <h1>🎯 Blog Generator Monitor</h1>
            <div class="status-bar">
                <div class="status-item">
                    <div class="status-dot"></div>
                    <span>System Running</span>
                </div>
                <div class="status-item">
                    <span id="agent-count">Loading...</span>
                </div>
                <div class="status-item">
                    <span id="event-count">Loading...</span>
                </div>
                <div class="status-item">
                    <span id="uptime">Loading...</span>
                </div>
            </div>
        </header>
        
        <div class="section">
            <h2>📊 Overview</h2>
            <div class="grid">
                <div class="card">
                    <h3>Active Agents</h3>
                    <div class="value" id="agents-active">-</div>
                </div>
                <div class="card">
                    <h3>Total Events</h3>
                    <div class="value" id="total-events">-</div>
                </div>
                <div class="card">
                    <h3>Active Jobs</h3>
                    <div class="value" id="active-jobs">-</div>
                </div>
                <div class="card">
                    <h3>System Status</h3>
                    <div class="value">✅ OK</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>🤖 Agents</h2>
            <div class="grid" id="agents-grid">
                <div class="card">
                    <h3>Loading agents...</h3>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>📝 Recent Events</h2>
            <div class="events" id="events-list">
                <div class="event">Loading events...</div>
            </div>
        </div>
    </div>
    
    <script>
        function updateStatus() {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    // Update header stats
                    document.getElementById('agent-count').textContent = 
                        `Agents: ${Object.keys(data.agents).length}`;
                    document.getElementById('event-count').textContent = 
                        `Events: ${data.events.length}`;
                    document.getElementById('uptime').textContent = 
                        `Uptime: ${data.uptime}`;
                    
                    // Update overview cards
                    document.getElementById('agents-active').textContent = 
                        Object.keys(data.agents).length;
                    document.getElementById('total-events').textContent = 
                        data.events.length;
                    document.getElementById('active-jobs').textContent = 
                        Object.keys(data.jobs).length;
                    
                    // Update agents grid
                    const agentsGrid = document.getElementById('agents-grid');
                    agentsGrid.innerHTML = '';
                    Object.values(data.agents).forEach(agent => {
                        const card = document.createElement('div');
                        card.className = 'card';
                        card.innerHTML = `
                            <h3>${agent.name}</h3>
                            <div class="value" style="font-size: 0.9rem;">
                                ${agent.status}
                            </div>
                            <div style="font-size: 0.75rem; color: #9ca3af; margin-top: 5px;">
                                ${new Date(agent.last_update).toLocaleTimeString()}
                            </div>
                        `;
                        agentsGrid.appendChild(card);
                    });
                    
                    // Update events list
                    const eventsList = document.getElementById('events-list');
                    eventsList.innerHTML = '';
                    data.events.slice().reverse().slice(0, 20).forEach(evt => {
                        const div = document.createElement('div');
                        div.className = 'event';
                        const time = new Date(evt.timestamp).toLocaleTimeString();
                        div.innerHTML = `
                            <span class="time">${time}</span>
                            <span>${JSON.stringify(evt.event)}</span>
                        `;
                        eventsList.appendChild(div);
                    });
                })
                .catch(err => console.error('Error:', err));
        }
        
        // Update every 2 seconds
        updateStatus();
        setInterval(updateStatus, 2000);
    </script>
</body>
</html>"""
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(html.encode())
                
                def send_status(self):
                    uptime = datetime.now() - monitor_state.start_time
                    uptime_str = str(uptime).split('.')[0]  # Remove microseconds
                    
                    data = {
                        'agents': monitor_state.agents,
                        'events': list(monitor_state.events),
                        'jobs': monitor_state.jobs,
                        'uptime': uptime_str
                    }
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(data).encode())
            
            def run_server():
                try:
                    server = HTTPServer((self.host, self.port), MonitorHandler)
                    logger.info(f"Simple web monitor started at http://{self.host}:{self.port}")
                    self.running = True
                    
                    # Auto-open browser
                    try:
                        webbrowser.open(f'http://localhost:{self.port}')
                    except:
                        pass
                    
                    server.serve_forever()
                except Exception as e:
                    logger.error(f"Failed to start web monitor: {e}")
                    self.running = False
            
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            
            # Give it a moment to start
            time.sleep(0.5)
            
            if self.running:
                return True
            return False
            
        except ImportError as e:
            logger.error(f"Failed to import HTTP server: {e}")
            return False
    
    def stop(self):
        """Stop the monitoring server."""
        self.running = False


# Global monitor instance
_monitor = None

def get_monitor(host='0.0.0.0', port=8080):
    """Get or create the global monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = SimpleWebMonitor(host, port)
    return _monitor


# Event tracking functions
def track_event(event):
    """Track an event for monitoring."""
    state.add_event(event)

def track_agent(agent_name, status='active'):
    """Track an agent status."""
    state.update_agent(agent_name, status)

def track_job(job_id, job_info):
    """Track a job."""
    state.add_job(job_id, job_info)
