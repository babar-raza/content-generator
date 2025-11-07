// Job Detail JavaScript

let ws;
let refreshInterval;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadJobDetails();
    connectWebSocket();
    connectLogStream();
    startAutoRefresh();
    loadAvailableAgents();
});

// Connect to SSE log stream
function connectLogStream() {
    const eventSource = new EventSource(`/api/jobs/${JOB_ID}/logs/stream`);
    
    eventSource.onmessage = (event) => {
        const logLine = event.data;
        if (logLine === '[LOG_STREAM_CLOSED]') {
            appendOutput('Log stream closed', 'info');
            eventSource.close();
        } else {
            appendOutput(logLine, 'log');
        }
    };
    
    eventSource.onerror = (error) => {
        console.error('SSE error:', error);
        eventSource.close();
        // Try to reconnect after 5 seconds
        setTimeout(connectLogStream, 5000);
    };
}

// Load available agents for the add dialog
async function loadAvailableAgents() {
    try {
        const response = await fetch('/api/agents');
        const agents = await response.json();
        
        const select = document.getElementById('agent-type');
        select.innerHTML = '<option value="">Select agent...</option>';
        
        agents.forEach(agent => {
            const option = document.createElement('option');
            option.value = agent.id;
            option.textContent = `${agent.name} (${agent.category})`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load agents:', error);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadJobDetails();
    connectWebSocket();
    startAutoRefresh();
});

// Load job details
async function loadJobDetails() {
    try {
        const response = await fetch(`/api/jobs/${JOB_ID}`);
        const job = await response.json();
        
        document.getElementById('job-status').textContent = job.status.toUpperCase();
        document.getElementById('job-status').className = `badge ${job.status}`;
        document.getElementById('job-topic').textContent = job.topic || 'Unknown';
        document.getElementById('job-started').textContent = formatTime(job.started_at);
        document.getElementById('job-progress').textContent = `${job.progress || 0}%`;
        document.getElementById('progress-fill').style.width = `${job.progress || 0}%`;
        
        updateControls(job.status);
        loadPipeline(job.pipeline);
        loadAgentDetails(job.agents);
    } catch (error) {
        console.error('Failed to load job:', error);
    }
}

// Update control buttons based on status
function updateControls(status) {
    const pauseBtn = document.getElementById('pause-btn');
    const resumeBtn = document.getElementById('resume-btn');
    
    if (status === 'paused') {
        pauseBtn.disabled = true;
        resumeBtn.disabled = false;
    } else if (status === 'running') {
        pauseBtn.disabled = false;
        resumeBtn.disabled = true;
    } else {
        pauseBtn.disabled = true;
        resumeBtn.disabled = true;
    }
}

// Load pipeline
function loadPipeline(pipeline) {
    if (!pipeline || pipeline.length === 0) {
        document.getElementById('agent-pipeline').innerHTML = 
            '<p class="no-data">No pipeline configured</p>';
        return;
    }
    
    const html = pipeline.map(agent => `
        <div class="pipeline-agent ${agent.status}">
            <h4>${agent.name}</h4>
            <div class="status">${agent.status}</div>
            <div class="actions">
                <button class="btn btn-sm btn-remove" onclick="removeAgent('${agent.id}')">✕</button>
            </div>
        </div>
    `).join('');
    
    document.getElementById('agent-pipeline').innerHTML = html;
    
    // Populate "insert after" dropdown
    const select = document.getElementById('insert-after');
    select.innerHTML = pipeline.map(agent => 
        `<option value="${agent.id}">${agent.name}</option>`
    ).join('');
}

// Load agent details
function loadAgentDetails(agents) {
    if (!agents || agents.length === 0) {
        document.getElementById('agents-details').innerHTML = 
            '<tr><td colspan="6" class="no-data">No agents executed yet</td></tr>';
        return;
    }
    
    const html = agents.map(agent => `
        <tr>
            <td>${agent.name}</td>
            <td><span class="badge ${agent.status}">${agent.status}</span></td>
            <td>${formatTime(agent.started_at)}</td>
            <td>${agent.duration || '-'}</td>
            <td>${agent.last_output || agent.output_size || '-'}</td>
            <td>
                <button class="btn btn-sm" onclick="viewAgentLogs('${agent.id}')">Logs</button>
            </td>
        </tr>
    `).join('');
    
    document.getElementById('agents-details').innerHTML = html;
    
    // Also load artifacts
    loadArtifacts();
}

// Load artifacts
async function loadArtifacts() {
    try {
        const response = await fetch(`/api/jobs/${JOB_ID}/artifacts`);
        const data = await response.json();
        
        if (data.artifacts && data.artifacts.length > 0) {
            let artifactsHtml = '<div class="artifacts-list"><h3>📦 Artifacts:</h3><ul>';
            data.artifacts.forEach(artifact => {
                const size = (artifact.size / 1024).toFixed(1);
                artifactsHtml += `<li><a href="${artifact.download_url}" download>${artifact.name}</a> (${size} KB)</li>`;
            });
            artifactsHtml += '</ul></div>';
            
            // Append to agents table or insert after it
            const agentsSection = document.querySelector('.agents-table').parentElement;
            let artifactsDiv = document.getElementById('artifacts-section');
            if (!artifactsDiv) {
                artifactsDiv = document.createElement('div');
                artifactsDiv.id = 'artifacts-section';
                agentsSection.appendChild(artifactsDiv);
            }
            artifactsDiv.innerHTML = artifactsHtml;
        }
    } catch (error) {
        console.error('Failed to load artifacts:', error);
    }
}

// WebSocket connection
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/mesh?job=${JOB_ID}`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
        appendOutput('Connected to job stream', 'info');
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        appendOutput('WebSocket error occurred', 'error');
    };
    
    ws.onclose = () => {
        console.log('WebSocket closed');
        appendOutput('Disconnected from job stream', 'info');
        // Reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
    };
}

// Handle WebSocket messages
function handleWebSocketMessage(data) {
    const { type, timestamp, data: eventData } = data;
    
    switch (type) {
        case 'NODE.START':
            appendOutput(`[${timestamp}] Agent started: ${eventData.node_id}`, 'info');
            break;
        case 'NODE.STDOUT':
            appendOutput(`[${timestamp}] ${eventData.message}`, 'log');
            break;
        case 'NODE.CHECKPOINT':
            appendOutput(`[${timestamp}] Checkpoint: ${eventData.checkpoint}`, 'info');
            break;
        case 'NODE.OUTPUT':
            appendOutput(`[${timestamp}] Output ready`, 'success');
            break;
        case 'NODE.ERROR':
            appendOutput(`[${timestamp}] ERROR: ${eventData.error}`, 'error');
            break;
        case 'RUN.PAUSED':
            appendOutput(`[${timestamp}] Job paused`, 'info');
            updateControls('paused');
            break;
        case 'RUN.RESUMED':
            appendOutput(`[${timestamp}] Job resumed`, 'info');
            updateControls('running');
            break;
    }
}

// Append output to console
function appendOutput(message, type = 'log') {
    const console = document.getElementById('output-console');
    const line = document.createElement('div');
    line.className = `output-line ${type}`;
    line.textContent = message;
    console.appendChild(line);
    console.scrollTop = console.scrollHeight;
    
    // Keep only last 100 lines
    while (console.children.length > 100) {
        console.removeChild(console.firstChild);
    }
}

// Job control functions
async function pauseJob() {
    try {
        const response = await fetch(`/api/jobs/${JOB_ID}/pause`, {
            method: 'POST'
        });
        const result = await response.json();
        appendOutput('Pause requested', 'info');
    } catch (error) {
        alert('Failed to pause job: ' + error.message);
    }
}

async function resumeJob() {
    try {
        const response = await fetch(`/api/jobs/${JOB_ID}/resume`, {
            method: 'POST'
        });
        const result = await response.json();
        appendOutput('Resume requested', 'info');
    } catch (error) {
        alert('Failed to resume job: ' + error.message);
    }
}

async function stepJob() {
    try {
        const response = await fetch(`/api/jobs/${JOB_ID}/step`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({mode: 'into'})
        });
        const result = await response.json();
        appendOutput('Step requested', 'info');
    } catch (error) {
        alert('Failed to step job: ' + error.message);
    }
}

async function cancelJob() {
    if (!confirm('Are you sure you want to cancel this job?')) return;
    
    try {
        const response = await fetch(`/api/jobs/${JOB_ID}/cancel`, {
            method: 'POST'
        });
        const result = await response.json();
        appendOutput('Job cancelled', 'info');
        setTimeout(() => window.location = '/', 2000);
    } catch (error) {
        alert('Failed to cancel job: ' + error.message);
    }
}

// Pipeline editing
function showAddAgent() {
    document.getElementById('add-agent-modal').classList.add('show');
}

function closeAddAgent() {
    document.getElementById('add-agent-modal').classList.remove('show');
}

document.getElementById('add-agent-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const agentSelect = document.getElementById('agent-type');
    const agentId = agentSelect.value;
    const agentName = agentSelect.options[agentSelect.selectedIndex].text;
    
    const data = {
        agent_id: agentId,
        agent_name: agentName,
        insert_after: document.getElementById('insert-after').value,
        params: JSON.parse(document.getElementById('agent-params').value || '{}')
    };
    
    try {
        const response = await fetch(`/api/jobs/${JOB_ID}/pipeline/add`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        closeAddAgent();
        appendOutput(`Agent ${agentName} added to pipeline`, 'success');
        loadJobDetails();
    } catch (error) {
        alert('Failed to add agent: ' + error.message);
    }
});

async function removeAgent(agentId) {
    if (!confirm('Remove this agent from pipeline?')) return;
    
    try {
        const response = await fetch(`/api/jobs/${JOB_ID}/pipeline/remove`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({agent_id: agentId})
        });
        
        const result = await response.json();
        appendOutput(`Agent removed`, 'info');
        loadJobDetails();
    } catch (error) {
        alert('Failed to remove agent: ' + error.message);
    }
}

// View agent output
function viewAgentOutput(agentId) {
    // Open agent output in new tab showing JSON data
    window.open(`/api/jobs/${JOB_ID}/agents/${agentId}/output`, '_blank');
}

// View agent logs
function viewAgentLogs(agentId) {
    // Fetch agent I/O data
    fetch(`/api/agents/${agentId}/logs`)
        .then(res => {
            if (!res.ok) throw new Error('Failed to load logs');
            return res.json();
        })
        .then(data => showLogModal(data))
        .catch(err => {
            appendOutput(`Error loading logs: ${err.message}`, 'error');
        });
}

function showLogModal(agentData) {
    // Remove any existing modal
    const existingModal = document.querySelector('.log-modal');
    if (existingModal) {
        existingModal.closest('.modal').remove();
    }
    
    const modal = document.createElement('div');
    modal.className = 'modal active';
    modal.style.display = 'flex';
    modal.innerHTML = `
        <div class="modal-content log-modal" style="max-width: 900px; max-height: 80vh; overflow-y: auto;">
            <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #ddd; padding-bottom: 12px;">
                <h2>Agent: ${agentData.agent_name}</h2>
                <button onclick="closeLogModal()" class="close-btn" style="background: none; border: none; font-size: 24px; cursor: pointer;">&times;</button>
            </div>
            
            <div class="log-section" style="margin-top: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3>Input</h3>
                    <button onclick="downloadJSON('input-${agentData.agent_name}', ${JSON.stringify(JSON.stringify(agentData.input))})" class="btn btn-sm">
                        📥 Download Input
                    </button>
                </div>
                <pre class="json-output" style="background: #f5f5f5; padding: 12px; border-radius: 4px; overflow-x: auto; max-height: 300px;">${JSON.stringify(agentData.input, null, 2)}</pre>
            </div>
            
            <div class="log-section" style="margin-top: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3>Output</h3>
                    <button onclick="downloadJSON('output-${agentData.agent_name}', ${JSON.stringify(JSON.stringify(agentData.output))})" class="btn btn-sm">
                        📥 Download Output
                    </button>
                </div>
                <pre class="json-output" style="background: #f5f5f5; padding: 12px; border-radius: 4px; overflow-x: auto; max-height: 300px;">${JSON.stringify(agentData.output, null, 2)}</pre>
            </div>
            
            ${agentData.status ? `
            <div class="log-section" style="margin-top: 20px;">
                <p><strong>Status:</strong> <span class="badge ${agentData.status}">${agentData.status}</span></p>
                ${agentData.duration ? `<p><strong>Duration:</strong> ${agentData.duration}</p>` : ''}
            </div>
            ` : ''}
        </div>
    `;
    document.body.appendChild(modal);
    
    // Close on background click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeLogModal();
        }
    });
}

function closeLogModal() {
    const modal = document.querySelector('.log-modal');
    if (modal) {
        modal.closest('.modal').remove();
    }
}

function downloadJSON(filename, dataStr) {
    const data = JSON.parse(dataStr);
    const blob = new Blob([JSON.stringify(data, null, 2)], 
                          {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${filename}-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

// Auto refresh
function startAutoRefresh() {
    refreshInterval = setInterval(() => {
        loadJobDetails();
    }, 5000);
}

// Utility functions
function formatTime(timestamp) {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
}

// Cleanup
window.addEventListener('beforeunload', () => {
    if (ws) ws.close();
    if (refreshInterval) clearInterval(refreshInterval);
});
