// Dashboard JavaScript

let refreshInterval;
const uploadedFiles = {
    kb: [],
    docs: [],
    blog: [],
    api: [],
    tutorial: []
};

// File upload handlers
function setupFileUploads() {
    const fileInputs = [
        { input: 'job-kb-files', list: 'kb-files-list', key: 'kb' },
        { input: 'job-docs-files', list: 'docs-files-list', key: 'docs' },
        { input: 'job-blog-files', list: 'blog-files-list', key: 'blog' },
        { input: 'job-api-files', list: 'api-files-list', key: 'api' },
        { input: 'job-tutorial-files', list: 'tutorial-files-list', key: 'tutorial' }
    ];

    fileInputs.forEach(({ input, list, key }) => {
        const fileInput = document.getElementById(input);
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                const files = Array.from(e.target.files);
                uploadedFiles[key] = uploadedFiles[key].concat(files);
                renderFileChips(list, uploadedFiles[key], key);
                e.target.value = ''; // Reset input
            });
        }
    });
}

function renderFileChips(listId, files, key) {
    const container = document.getElementById(listId);
    if (!container) return;
    
    container.innerHTML = '';
    files.forEach((file, index) => {
        const chip = document.createElement('div');
        chip.className = 'file-chip';
        chip.innerHTML = `
            <span class="file-chip-name" title="${file.name}">${file.name}</span>
            <button type="button" class="file-chip-remove" onclick="removeFile('${key}', ${index}, '${listId}')">&times;</button>
        `;
        container.appendChild(chip);
    });
}

function removeFile(key, index, listId) {
    uploadedFiles[key].splice(index, 1);
    renderFileChips(listId, uploadedFiles[key], key);
}

// Make removeFile globally available
window.removeFile = removeFile;

// Browse path function - defined FIRST before anything else
function browsePath(inputId) {
    console.log('=== browsePath START ===');
    console.log('Input ID:', inputId);
    
    try {
        const input = document.getElementById(inputId);
        console.log('Found input:', input);
        
        if (!input) {
            alert('Error: Could not find input field with ID: ' + inputId);
            return;
        }
        
        const currentPath = input.value || './';
        console.log('Current path:', currentPath);
        
        const newPath = prompt('Enter path:', currentPath);
        console.log('New path entered:', newPath);
        
        if (newPath !== null && newPath.trim() !== '') {
            input.value = newPath.trim();
            console.log('SUCCESS: Path updated to:', newPath.trim());
            alert('Path updated to: ' + newPath.trim());
        } else {
            console.log('Cancelled or empty');
        }
    } catch (error) {
        console.error('ERROR in browsePath:', error);
        alert('Error: ' + error.message);
    }
    
    console.log('=== browsePath END ===');
}

// Make it globally available
window.browsePath = browsePath;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, browsePath type:', typeof browsePath);
    console.log('window.browsePath type:', typeof window.browsePath);
    
    initTabs();
    loadJobs();
    loadAgents();
    startAutoRefresh();
    setupFileUploads();
    
    // Setup browse button handlers with event delegation
    document.body.addEventListener('click', function(e) {
        if (e.target && e.target.classList.contains('browse-btn')) {
            e.preventDefault();
            e.stopPropagation();
            const targetId = e.target.getAttribute('data-target');
            console.log('Browse button clicked via delegation, target:', targetId);
            browsePath(targetId);
        }
    });
    
    console.log('Event delegation setup complete');
});

// Tab switching
function initTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            switchTab(tabName);
        });
    });
}

function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`.tab[data-tab="${tabName}"]`).classList.add('active');
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById(`${tabName}-tab`).classList.add('active');
}

// Load jobs
async function loadJobs() {
    try {
        const response = await fetch('/api/jobs');
        const jobs = await response.json();
        
        document.getElementById('job-count').textContent = `Jobs: ${jobs.length}`;
        
        const tbody = document.getElementById('jobs-list');
        if (jobs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="no-data">No jobs running</td></tr>';
            return;
        }
        
        tbody.innerHTML = jobs.map(job => `
            <tr onclick="window.location='/jobs/${job.id}'">
                <td><code>${job.id.substring(0, 8)}</code></td>
                <td>${job.topic || 'Unknown'}</td>
                <td><span class="badge ${job.status}">${job.status.toUpperCase()}</span></td>
                <td>${job.progress || 0}%</td>
                <td>${formatTime(job.started_at)}</td>
                <td>
                    <button class="btn btn-sm" onclick="viewJob('${job.id}'); event.stopPropagation();">View</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Failed to load jobs:', error);
    }
}

// Load agents
async function loadAgents() {
    try {
        const response = await fetch('/api/agents');
        const agents = await response.json();
        
        document.getElementById('agent-count').textContent = `Agents: ${agents.length}`;
        
        const grid = document.getElementById('agents-grid');
        grid.innerHTML = agents.map(agent => `
            <div class="agent-card">
                <h3>${agent.name}</h3>
                <div class="meta">
                    <p>Type: ${agent.type || 'Unknown'}</p>
                    <p>Status: ${agent.status || 'Idle'}</p>
                    <p>Checkpoints: ${agent.checkpoints?.length || 0}</p>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load agents:', error);
    }
}

// New job modal
function startNewJob() {
    document.getElementById('new-job-modal').classList.add('show');
    console.log('Modal opened, browsePath available:', typeof window.browsePath);
}

function closeModal() {
    document.getElementById('new-job-modal').classList.remove('show');
}

document.getElementById('new-job-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Use FormData for multipart uploads
    const formData = new FormData();
    
    // Add text fields
    formData.append('template_name', document.getElementById('job-template').value);
    formData.append('topic', document.getElementById('job-topic').value || '');
    formData.append('auto_topic', document.getElementById('job-auto-topic').checked);
    formData.append('workflow', document.getElementById('job-workflow').value);
    formData.append('output_dir', document.getElementById('job-output-dir').value || './output');
    
    // Add path fields
    const kbPath = document.getElementById('job-kb-path').value;
    const docsPath = document.getElementById('job-docs-path').value;
    const blogPath = document.getElementById('job-blog-path').value;
    const apiPath = document.getElementById('job-api-path').value;
    const tutorialPath = document.getElementById('job-tutorial-path').value;
    
    if (kbPath) formData.append('kb_path', kbPath);
    if (docsPath) formData.append('docs_path', docsPath);
    if (blogPath) formData.append('blog_path', blogPath);
    if (apiPath) formData.append('api_path', apiPath);
    if (tutorialPath) formData.append('tutorial_path', tutorialPath);
    
    // Add uploaded files
    uploadedFiles.kb.forEach(file => formData.append('kb_files', file));
    uploadedFiles.docs.forEach(file => formData.append('docs_files', file));
    uploadedFiles.blog.forEach(file => formData.append('blog_files', file));
    uploadedFiles.api.forEach(file => formData.append('api_files', file));
    uploadedFiles.tutorial.forEach(file => formData.append('tutorial_files', file));
    
    try {
        const response = await fetch('/api/jobs', {
            method: 'POST',
            body: formData  // Don't set Content-Type, browser will set it with boundary
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.detail || 'Failed to start job');
        }
        
        // Reset form and uploaded files
        uploadedFiles.kb = [];
        uploadedFiles.docs = [];
        uploadedFiles.blog = [];
        uploadedFiles.api = [];
        uploadedFiles.tutorial = [];
        
        closeModal();
        window.location = `/jobs/${result.job_id}`;
    } catch (error) {
        alert('Failed to start job: ' + error.message);
    }
});

// View job
function viewJob(jobId) {
    window.location = `/jobs/${jobId}`;
}

// Auto refresh
function startAutoRefresh() {
    refreshInterval = setInterval(() => {
        loadJobs();
        loadAgents();
    }, 3000);
}

// Utility functions
function formatTime(timestamp) {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
}

// Cleanup
window.addEventListener('beforeunload', () => {
    if (refreshInterval) clearInterval(refreshInterval);
});
