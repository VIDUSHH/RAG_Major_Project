/**
 * RAG Postmortem Intelligence System - Frontend Application
 */
class RAGApp {
    constructor() {
        this.apiBase = '/api/v1';
        this.currentFiles = [];
        this.uploadedFiles = new Map();
        this.init();
    }

    async init() {
        this.bindEvents();
        await this.checkConnection();
        await this.loadDashboardStats();
        this.loadExampleQueries();
    }

    bindEvents() {
        // Tab navigation
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => this.switchTab(btn.dataset.tab));
        });

        // Upload zone
        const uploadZone = document.getElementById('uploadZone');
        const fileInput = document.getElementById('fileInput');

        uploadZone.addEventListener('click', () => fileInput.click());
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('drag-over');
        });
        uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('drag-over');
            this.handleFiles(e.dataTransfer.files);
        });
        fileInput.addEventListener('change', (e) => this.handleFiles(e.target.files));

        // Ingest button
        document.getElementById('ingestBtn').addEventListener('click', () => this.startIngestion());

        // Query analysis
        document.getElementById('analyzeBtn').addEventListener('click', () => this.analyzeIncident());

        // Example query chips
        document.getElementById('exampleChips').addEventListener('click', (e) => {
            if (e.target.classList.contains('example-chip')) {
                document.getElementById('queryInput').value = e.target.textContent;
            }
        });

        // Response tabs
        document.querySelectorAll('.response-tab-btn').forEach(btn => {
            btn.addEventListener('click', () => this.switchResponseTab(btn.dataset.responseTab));
        });

        // Vector DB search
        document.getElementById('vectorSearchBtn').addEventListener('click', () => this.searchVectors());
        document.getElementById('vectorSearchQuery').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.searchVectors();
        });
        document.getElementById('vectorFilterService').addEventListener('change', () => this.searchVectors());
        document.getElementById('vectorFilterLevel').addEventListener('change', () => this.searchVectors());

        // Graph DB
        document.getElementById('graphLoadBtn').addEventListener('click', () => this.loadGraphNodes());
        document.getElementById('graphNodeType').addEventListener('change', () => this.loadGraphNodes());
        document.getElementById('serviceGraphBtn').addEventListener('click', () => this.loadServiceGraph());

        // System status
        document.getElementById('refreshStatusBtn').addEventListener('click', () => this.checkConnection());
    }

    getApiKey() {
        return (window.RAG_CONFIG && window.RAG_CONFIG.apiKey) || '';
    }

    async api(path, options = {}) {
        const url = `${this.apiBase}${path}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-Internal-API-Key': this.getApiKey(),
                'X-Organization-ID': '00000000-0000-0000-0000-000000000001',
                'X-User-ID': '00000000-0000-0000-0000-000000000001',
                'X-User-Email': 'admin@example.com',
                'X-User-Roles': 'ENGINEER',
            },
        };

        const response = await fetch(url, { ...defaultOptions, ...options });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return response.json();
    }

    async checkConnection() {
        this.updateConnectionStatus('connecting');
        try {
            const status = await this.api('/database/system/status');
            this.updateConnectionStatus('connected');
            this.updateSystemStatus(status);
        } catch (e) {
            console.error('Connection check failed:', e);
            this.updateConnectionStatus('disconnected');
        }
    }

    updateConnectionStatus(status) {
        const dot = document.querySelector('.status-dot');
        const text = document.querySelector('.status-text');
        dot.className = `status-dot ${status}`;
        text.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    }

    async loadDashboardStats() {
        try {
            const [vectorStats, graphStats] = await Promise.all([
                this.api('/database/vectors/stats'),
                this.api('/database/graph/stats'),
            ]);

            document.getElementById('statDocuments').textContent = this.formatNumber(vectorStats.points_count);
            document.getElementById('statChunks').textContent = this.formatNumber(vectorStats.points_count);
            document.getElementById('statVectors').textContent = this.formatNumber(vectorStats.vectors_count);
            document.getElementById('statNodes').textContent = this.formatNumber(
                (graphStats.services || 0) + (graphStats.incidents || 0) +
                (graphStats.log_entries || 0) + (graphStats.errors || 0) +
                (graphStats.fixes || 0) + (graphStats.lessons || 0)
            );
            document.getElementById('statRelationships').textContent = this.formatNumber(graphStats.relationships || 0);
            document.getElementById('statIncidents').textContent = this.formatNumber(graphStats.incidents || 0);

            // Populate service filter
            this.loadServicesForFilter();
        } catch (e) {
            console.error('Failed to load dashboard stats:', e);
        }
    }

    async loadServicesForFilter() {
        try {
            const result = await this.api('/database/graph/nodes?node_type=Service&limit=100');
            const select = document.getElementById('vectorFilterService');
            select.innerHTML = '<option value="">All Services</option>';
            result.nodes.forEach(node => {
                const option = document.createElement('option');
                option.value = node.properties.name || node.id;
                option.textContent = node.properties.name || node.id;
                select.appendChild(option);
            });
        } catch (e) {
            console.error('Failed to load services:', e);
        }
    }

    handleFiles(files) {
        for (const file of files) {
            if (this.uploadedFiles.has(file.name)) continue;

            const ext = file.name.split('.').pop().toLowerCase();
            const allowed = ['log', 'txt', 'json', 'csv', 'md', 'markdown', 'yaml', 'yml'];
            if (!allowed.includes(ext)) {
                this.showToast(`Unsupported file type: ${ext}`, 'error');
                continue;
            }

            if (file.size > 100 * 1024 * 1024) {
                this.showToast(`File too large: ${file.name}`, 'error');
                continue;
            }

            this.uploadedFiles.set(file.name, file);
        }
        this.renderFileList();
    }

    renderFileList() {
        const list = document.getElementById('fileList');
        const ingestBtn = document.getElementById('ingestBtn');

        if (this.uploadedFiles.size === 0) {
            list.innerHTML = '';
            ingestBtn.disabled = true;
            return;
        }

        ingestBtn.disabled = false;
        list.innerHTML = Array.from(this.uploadedFiles.values()).map(file => `
            <div class="file-item" data-name="${file.name}">
                <div class="file-icon">${this.getFileIcon(file.name)}</div>
                <div class="file-info">
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${this.formatBytes(file.size)}</div>
                </div>
                <button class="file-remove" onclick="app.removeFile('${file.name}')">✕</button>
            </div>
        `).join('');
    }

    removeFile(name) {
        this.uploadedFiles.delete(name);
        this.renderFileList();
    }

    getFileIcon(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const icons = { log: '📋', txt: '📄', json: '📋', csv: '📊', md: '📝', yaml: '⚙️', yml: '⚙️' };
        return icons[ext] || '📄';
    }

    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    }

    async startIngestion() {
        const files = Array.from(this.uploadedFiles.values());
        if (files.length === 0) return;

        const chunkingStrategy = document.getElementById('chunkingStrategy').value;
        const progressSection = document.getElementById('progressSection');
        const progressBar = document.getElementById('progressBar');
        const progressDetails = document.getElementById('progressDetails');
        const resultsSection = document.getElementById('resultsSection');
        const resultsBody = document.getElementById('resultsBody');
        const ingestBtn = document.getElementById('ingestBtn');

        progressSection.hidden = false;
        resultsSection.hidden = true;
        ingestBtn.disabled = true;
        progressBar.style.width = '0%';
        progressDetails.textContent = 'Preparing...';

        const formData = new FormData();
        files.forEach(f => formData.append('files', f));
        formData.append('chunking_strategy', chunkingStrategy);

        try {
            const response = await fetch(`${this.apiBase}/ingest/batch`, {
                method: 'POST',
                headers: {
                    'X-Internal-API-Key': this.getApiKey(),
                    'X-Organization-ID': '00000000-0000-0000-0000-000000000001',
                    'X-User-ID': '00000000-0000-0000-0000-000000000001',
                    'X-User-Email': 'admin@example.com',
                    'X-User-Roles': 'ENGINEER',
                },
                body: formData,
            });

            if (!response.ok) throw new Error('Ingestion failed');

            const result = await response.json();
            const failures = result.results.filter(r => r.status === 'failed').length;
            progressBar.style.width = '100%';
            progressDetails.textContent = failures > 0
                ? `Completed with ${failures} failure(s)`
                : 'Completed!';

            resultsSection.hidden = false;
            resultsBody.innerHTML = result.results.map(r => `
                <tr>
                    <td>${r.filename}</td>
                    <td><span class="status-badge ${r.status}">${r.status}</span></td>
                    <td>${r.entries_parsed || 0}</td>
                    <td>${r.chunks_created || 0}</td>
                    <td>${r.error ? this.escapeHtml(r.error).substring(0, 120) : '-'}</td>
                </tr>
            `).join('');

            this.uploadedFiles.clear();
            this.renderFileList();
            await this.loadDashboardStats();

            this.showToast(`Ingested ${files.length} file(s) successfully`, 'success');
        } catch (e) {
            console.error('Ingestion failed:', e);
            progressDetails.textContent = `Failed: ${e.message}`;
            this.showToast('Ingestion failed: ' + e.message, 'error');
        } finally {
            ingestBtn.disabled = false;
        }
    }

    loadExampleQueries() {
        const examples = {
            "root_cause_analysis": [
                "Why did the payment service fail last night?",
                "What caused the authentication service to return 500 errors?",
                "Root cause of the database connection pool exhaustion"
            ],
            "historical_incident_search": [
                "Show previous incidents related to authentication service",
                "Find similar incidents to the current Redis timeout issue",
                "What happened during the last payment service outage?"
            ],
            "component_investigation": [
                "Which components should I investigate first for the checkout failure?",
                "What services are affected by the API gateway issue?"
            ],
            "dependency_investigation": [
                "What services depend on the failing payment service?",
                "Show upstream dependencies of the authentication service"
            ],
            "previous_fix_search": [
                "What fixes worked previously for database timeouts?",
                "How was the Redis connection issue resolved last time?"
            ],
            "lesson_learned_search": [
                "What lessons were learned from the last major outage?",
                "What preventive measures were recommended after the payment failure?"
            ],
            "impact_analysis": [
                "What is the blast radius of the auth service failure?",
                "Which services will be impacted if the database goes down?"
            ],
            "error_diagnosis": [
                "Diagnose: NullPointerException in payment adapter v2.3.1",
                "Intermittent 500 errors from checkout service after deployment"
            ]
        };

        const container = document.getElementById('exampleChips');
        container.innerHTML = Object.values(examples).flat().map(q => `
            <button class="example-chip" title="${q}">${q}</button>
        `).join('');
    }

    async analyzeIncident() {
        const query = document.getElementById('queryInput').value.trim();
        const topK = parseInt(document.getElementById('topK').value) || 10;

        if (!query) {
            this.showToast('Please enter a query', 'error');
            return;
        }

        this.showLoading(true);
        this.updateLoadingSteps([
            { text: 'Understanding query...', active: true },
            { text: 'Searching vector database...' },
            { text: 'Searching graph database...' },
            { text: 'Ranking evidence...' },
            { text: 'Generating incident analysis...' },
        ]);

        try {
            const response = await this.api('/query/analyze', {
                method: 'POST',
                body: JSON.stringify({ query, top_k: topK }),
            });

            this.showLoading(false);
            this.displayResponse(response);
            document.getElementById('responseSection').hidden = false;
            document.getElementById('responseSection').scrollIntoView({ behavior: 'smooth' });
        } catch (e) {
            this.showLoading(false);
            console.error('Analysis failed:', e);
            this.showToast('Analysis failed: ' + e.message, 'error');
        }
    }

    showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        overlay.hidden = !show;
    }

    updateLoadingSteps(steps) {
        const container = document.getElementById('loadingSteps');
        container.innerHTML = steps.map((step, i) => `
            <div class="loading-step ${step.active ? 'active' : ''} ${step.completed ? 'completed' : ''}" data-step="${i}">
                <div class="loading-step-icon">
                    ${step.active ? '<div class="spinner" style="width:16px;height:16px;border-width:2px;"></div>' :
                      step.completed ? '✓' : (i + 1)}
                </div>
                <span>${step.text}</span>
            </div>
        `).join('');
    }

    displayResponse(response) {
        // Update meta
        document.getElementById('confidenceBadge').textContent = `Confidence: ${response.confidence}`;
        document.getElementById('confidenceBadge').className = `confidence-badge ${response.confidence.toLowerCase().replace(' ', '-')}`;
        document.getElementById('responseTime').textContent = `Generated: ${new Date().toLocaleTimeString()}`;

        // Incident details
        const details = document.getElementById('incidentDetails');
        details.innerHTML = `
            <dt>Incident ID</dt><dd>${response.incident_id}</dd>
            <dt>Title</dt><dd>${response.title}</dd>
            <dt>Source</dt><dd>${response.source}${response.source_url ? ` (<a href="${response.source_url}" target="_blank">link</a>)` : ''}</dd>
            <dt>Severity</dt><dd><span class="status-badge ${response.severity.toLowerCase()}">${response.severity}</span></dd>
            <dt>Status</dt><dd><span class="status-badge ${response.status}">${response.status}</span></dd>
            <dt>Service</dt><dd>${response.service}</dd>
            <dt>Team</dt><dd>${response.team}</dd>
            <dt>Created</dt><dd>${response.created_at}</dd>
            <dt>Resolved</dt><dd>${response.resolved_at || 'Not resolved'}</dd>
        `;

        // Root cause
        document.getElementById('potentialRootCause').textContent = response.potential_root_cause || 'Not determined';
        document.getElementById('rootCause').textContent = response.root_cause || 'Not determined';

        // Impact & Resolution
        const impactRes = document.getElementById('impactResolution');
        impactRes.innerHTML = `
            <dt>Impact</dt><dd>${response.impact}</dd>
            <dt>Resolution</dt><dd>${response.resolution}</dd>
            <dt>Risk Severity</dt><dd><span class="status-badge ${response.risk_severity.toLowerCase()}">${response.risk_severity}</span></dd>
        `;

        // Timeline
        const timeline = document.getElementById('timeline');
        timeline.innerHTML = response.timeline.map((event, i) => `
            <div class="timeline-item">
                <div class="timeline-time">${this.formatDateTime(event.timestamp)}</div>
                <div class="timeline-content">
                    <div class="timeline-event">${event.event}</div>
                    <div class="timeline-actor">${event.actor}</div>
                </div>
            </div>
        `).join('');

        // Lessons learned
        const lessons = document.getElementById('lessonsLearned');
        lessons.innerHTML = response.lessons_learned.map(l => `<li>${l}</li>`).join('') ||
            '<li style="color: var(--text-muted);">No lessons recorded</li>';

        // Log snippets
        const snippets = document.getElementById('logSnippets');
        snippets.innerHTML = response.log_snippets.map(s => `
            <div class="log-snippet">${this.escapeHtml(s)}</div>
        `).join('') || '<p style="color: var(--text-muted);">No log snippets available</p>';

        // Tags
        const tags = document.getElementById('tags');
        tags.innerHTML = response.tags.map(t => `<span class="tag">${t}</span>`).join('') ||
            '<span class="tag" style="color: var(--text-muted);">No tags</span>';

        // Evidence
        const evidence = document.getElementById('evidenceList');
        evidence.innerHTML = response.evidence.map((ev, i) => `
            <div class="evidence-item">
                <div class="evidence-header">
                    <span class="evidence-source">[Source ${i + 1}] ${ev.type.toUpperCase()}: ${ev.source}</span>
                    <div class="evidence-meta">
                        <span>Score: ${ev.score?.toFixed(3) || 'N/A'}</span>
                        <span>Service: ${ev.metadata?.service || 'unknown'}</span>
                        <span>Time: ${ev.metadata?.timestamp || 'unknown'}</span>
                    </div>
                </div>
                <div class="evidence-content">${this.escapeHtml(ev.content || '')}</div>
            </div>
        `).join('') || '<p style="color: var(--text-muted); padding: 20px; text-align: center;">No evidence retrieved</p>';

        // Graph relationships
        const graphRel = document.getElementById('graphRelationships');
        if (response.graph_relationships && response.graph_relationships.length > 0) {
            graphRel.innerHTML = `
                <h4>Graph Relationships</h4>
                <div class="results-table-container">
                    <table class="results-table">
                        <thead>
                            <tr><th>Source</th><th>Relationship</th><th>Target</th></tr>
                        </thead>
                        <tbody>
                            ${response.graph_relationships.map(r => `
                                <tr>
                                    <td>${r.source}</td>
                                    <td>${r.type}</td>
                                    <td>${r.target}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        } else {
            graphRel.innerHTML = '<p style="color: var(--text-muted); padding: 20px; text-align: center;">No graph relationships found</p>';
        }

        // Recommendations
        const recs = document.getElementById('recommendationsList');
        recs.innerHTML = response.recommended_investigation.map((r, i) => `
            <div class="recommendation-item">
                <div class="recommendation-number">${i + 1}</div>
                <div class="recommendation-content">
                    <div class="recommendation-title">Investigation Step ${i + 1}</div>
                    <div class="recommendation-description">${r}</div>
                </div>
            </div>
        `).join('') || '<p style="color: var(--text-muted); padding: 20px; text-align: center;">No recommendations available</p>';

        // Raw JSON
        document.getElementById('jsonViewer').textContent = JSON.stringify(response, null, 2);

        // Graph visualization
        this.renderGraphViz(response.graph_relationships);
    }

    renderGraphViz(relationships) {
        const container = document.getElementById('graphViz');
        if (!relationships || relationships.length === 0) {
            container.innerHTML = '<p style="color: var(--text-muted); text-align: center; padding: 40px;">No graph data to visualize</p>';
            return;
        }

        // Build nodes from relationships
        const nodes = new Map();
        relationships.forEach(r => {
            if (!nodes.has(r.source)) nodes.set(r.source, { id: r.source, type: 'Service' });
            if (!nodes.has(r.target)) nodes.set(r.target, { id: r.target, type: 'Service' });
        });

        const nodeArray = Array.from(nodes.values());
        const width = container.clientWidth || 800;
        const height = 400;
        const centerX = width / 2;
        const centerY = height / 2;
        const radius = Math.min(width, height) / 2.5;

        // Simple force-directed layout simulation
        const positions = new Map();
        nodeArray.forEach((node, i) => {
            const angle = (i / nodeArray.length) * Math.PI * 2;
            positions.set(node.id, {
                x: centerX + radius * Math.cos(angle),
                y: centerY + radius * Math.sin(angle)
            });
        });

        let svg = `
            <svg class="graph-svg" viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                        <polygon points="0 0, 10 3.5, 0 7" fill="var(--border-hover)" />
                    </marker>
                </defs>
        `;

        // Links
        relationships.forEach(r => {
            const sourcePos = positions.get(r.source);
            const targetPos = positions.get(r.target);
            if (sourcePos && targetPos) {
                svg += `<line class="graph-link" x1="${sourcePos.x}" y1="${sourcePos.y}" x2="${targetPos.x}" y2="${targetPos.y}" />`;
            }
        });

        // Nodes
        nodeArray.forEach(node => {
            const pos = positions.get(node.id);
            if (pos) {
                const typeClass = node.type ? `graph-node-type-${node.type.toLowerCase()}` : '';
                svg += `
                    <g class="graph-node ${typeClass}" data-id="${node.id}">
                        <circle cx="${pos.x}" cy="${pos.y}" r="16" fill="var(--accent-blue)" />
                        <text class="graph-label" x="${pos.x}" y="${pos.y + 28}" text-anchor="middle">${this.escapeHtml(node.id.substring(0, 20))}</text>
                    </g>
                `;
            }
        });

        svg += '</svg>';
        container.innerHTML = svg;
    }

    formatDateTime(isoString) {
        if (!isoString) return 'Unknown';
        try {
            return new Date(isoString).toLocaleString();
        } catch {
            return isoString;
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed; bottom: 24px; right: 24px; z-index: 2000;
            padding: 12px 20px; border-radius: var(--radius-md);
            background: var(--bg-secondary); border: 1px solid var(--border-color);
            color: var(--text-primary); box-shadow: var(--shadow-lg);
            animation: slideIn 300ms ease;
        `;
        if (type === 'success') toast.style.borderLeft = '4px solid var(--accent-green)';
        if (type === 'error') toast.style.borderLeft = '4px solid var(--accent-red)';
        if (type === 'warning') toast.style.borderLeft = '4px solid var(--accent-yellow)';

        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.animation = 'slideOut 300ms ease';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    switchTab(tabName) {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
            btn.setAttribute('aria-selected', btn.dataset.tab === tabName);
        });
        document.querySelectorAll('.tab-panel').forEach(panel => {
            panel.classList.toggle('active', panel.id === tabName);
        });

        // Load tab-specific data
        if (tabName === 'vector-db') this.searchVectors();
        if (tabName === 'graph-db') this.loadGraphNodes();
        if (tabName === 'system') this.checkConnection();
    }

    switchResponseTab(tabName) {
        document.querySelectorAll('.response-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.responseTab === tabName);
            btn.setAttribute('aria-selected', btn.dataset.responseTab === tabName);
        });
        document.querySelectorAll('.response-tab-panel').forEach(panel => {
            panel.classList.toggle('active', panel.id === tabName);
        });
    }

    async searchVectors() {
        const query = document.getElementById('vectorSearchQuery').value.trim();
        const service = document.getElementById('vectorFilterService').value;
        const level = document.getElementById('vectorFilterLevel').value;

        if (!query) {
            this.showToast('Enter a search query', 'error');
            return;
        }

        try {
            let url = `/database/vectors/search?query=${encodeURIComponent(query)}&limit=20`;
            if (service) url += `&service=${encodeURIComponent(service)}`;
            if (level) url += `&level=${encodeURIComponent(level)}`;

            const result = await this.api(url);
            this.renderVectorResults(result.results);
        } catch (e) {
            console.error('Vector search failed:', e);
            this.showToast('Search failed: ' + e.message, 'error');
        }
    }

    renderVectorResults(results) {
        const tbody = document.getElementById('vectorResultsBody');
        tbody.innerHTML = results.map(r => `
            <tr>
                <td><code>${r.id.substring(0, 12)}...</code></td>
                <td>${r.score.toFixed(3)}</td>
                <td>${r.source}</td>
                <td>${r.service}</td>
                <td>${this.formatDateTime(r.timestamp)}</td>
                <td style="max-width: 300px;">${this.escapeHtml(r.text.substring(0, 100))}...</td>
            </tr>
        `).join('') || '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:40px;">No results</td></tr>';
    }

    async loadGraphNodes() {
        const nodeType = document.getElementById('graphNodeType').value;

        try {
            let url = '/database/graph/nodes?limit=100';
            if (nodeType) url += `&node_type=${encodeURIComponent(nodeType)}`;

            const result = await this.api(url);
            this.renderGraphNodes(result.nodes);
            this.updateGraphStats(result);
        } catch (e) {
            console.error('Failed to load graph nodes:', e);
            this.showToast('Failed to load nodes: ' + e.message, 'error');
        }
    }

    renderGraphNodes(nodes) {
        const tbody = document.getElementById('graphNodesBody');
        tbody.innerHTML = nodes.map(n => `
            <tr>
                <td><code>${n.id.substring(0, 12)}...</code></td>
                <td>${n.type}</td>
                <td style="max-width: 400px;">${this.escapeHtml(JSON.stringify(n.properties, null, 2).substring(0, 200))}...</td>
            </tr>
        `).join('') || '<tr><td colspan="3" style="text-align:center;color:var(--text-muted);padding:40px;">No nodes</td></tr>';
    }

    updateGraphStats(result) {
        document.getElementById('graphStats').innerHTML = `
            <div class="db-stat"><span class="db-stat-label">Total Nodes</span><span class="db-stat-value">${this.formatNumber(result.count)}</span></div>
        `;
    }

    async loadServiceGraph() {
        const serviceName = document.getElementById('serviceGraphInput').value.trim();
        if (!serviceName) {
            this.showToast('Enter a service name', 'error');
            return;
        }

        try {
            const result = await this.api(`/database/graph/service/${encodeURIComponent(serviceName)}?depth=2`);
            this.renderGraphViz(
                result.nodes.flatMap(n =>
                    n.properties.dependencies?.map(d => ({ source: serviceName, target: d, type: 'DEPENDS_ON' })) || []
                )
            );
        } catch (e) {
            console.error('Failed to load service graph:', e);
            this.showToast('Failed to load service graph: ' + e.message, 'error');
        }
    }

    updateSystemStatus(status) {
        const qdrant = status.qdrant || {};
        const neo4j = status.neo4j || {};

        document.getElementById('qdrantStatus').innerHTML = `
            <span class="status-dot ${qdrant.healthy ? 'connected' : 'disconnected'}"></span>
            <span>${qdrant.healthy ? 'Healthy' : 'Unhealthy'}</span>
        `;
        document.getElementById('qdrantDetails').textContent = qdrant.stats ?
            `Vectors: ${this.formatNumber(qdrant.stats.vectors_count)} | Points: ${this.formatNumber(qdrant.stats.points_count)}` :
            'No stats available';

        document.getElementById('neo4jStatus').innerHTML = `
            <span class="status-dot ${neo4j.healthy ? 'connected' : 'disconnected'}"></span>
            <span>${neo4j.healthy ? 'Healthy' : 'Unhealthy'}</span>
        `;
        document.getElementById('neo4jDetails').textContent = neo4j.stats ?
            `Services: ${neo4j.stats.services || 0} | Incidents: ${neo4j.stats.incidents || 0} | Relationships: ${neo4j.stats.relationships || 0}` :
            'No stats available';

        document.getElementById('llmStatus').innerHTML = `
            <span class="status-dot ${status.overall_healthy ? 'connected' : 'disconnected'}"></span>
            <span>${status.overall_healthy ? 'Available' : 'Unavailable'}</span>
        `;
    }
}

// Initialize app
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new RAGApp();
});

// Add toast animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn { from { opacity: 0; transform: translateX(100px); } to { opacity: 1; transform: translateX(0); } }
    @keyframes slideOut { from { opacity: 1; transform: translateX(0); } to { opacity: 0; transform: translateX(100px); } }
`;
document.head.appendChild(style);