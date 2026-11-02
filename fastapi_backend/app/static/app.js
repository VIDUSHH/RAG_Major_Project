'use strict';

// ============================================================
// Icons
// ============================================================
const ICON_PATHS = {
    grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    inbox: '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
    search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    chip: '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
    network: '<circle cx="5" cy="6" r="3"/><circle cx="19" cy="6" r="3"/><circle cx="12" cy="18" r="3"/><path d="M7.5 7.5 10 15M16.5 7.5 14 15M6 8v1a4 4 0 0 0 4 4h4a4 4 0 0 0 4-4V8"/>',
    monitor: '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>',
    doc: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/>',
    layers: '<path d="m12 2 10 6-10 6L2 8z"/><path d="m2 13 10 6 10-6"/><path d="m2 18 10 6 10-6"/>',
    node: '<circle cx="12" cy="5" r="3"/><circle cx="5" cy="19" r="3"/><circle cx="19" cy="19" r="3"/><path d="M12 8v5a4 4 0 0 1-3.5 4M12 13a4 4 0 0 1 3.5 4"/>',
    link: '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
    alert: '<path d="m21.7 18-8-14a2 2 0 0 0-3.5 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3z"/><path d="M12 9v4M12 17h.01"/>',
    upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5M12 3v12"/>',
    send: '<path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/>',
    spark: '<path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1"/>',
    brain: '<path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44A2.5 2.5 0 0 1 4 17.5V6.5A2.5 2.5 0 0 1 7.04 4.06 2.5 2.5 0 0 1 9.5 2z"/><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44A2.5 2.5 0 0 0 20 17.5V6.5a2.5 2.5 0 0 0-3.04-2.44A2.5 2.5 0 0 0 14.5 2z"/>',
    close: '<path d="M18 6 6 18M6 6l12 12"/>',
    refresh: '<path d="M21 12a9 9 0 1 1-2.64-6.36L21 8"/><path d="M21 3v5h-5"/>',
};

function icon(name, cls) {
    const inner = ICON_PATHS[name] || ICON_PATHS.doc;
    return `<svg class="icon-svg ${cls || ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${inner}</svg>`;
}

// Fill any <span data-icon="name"> placeholders in the DOM.
function hydrateIcons() {
    document.querySelectorAll('[data-icon]').forEach((el) => {
        el.innerHTML = icon(el.getAttribute('data-icon'), el.getAttribute('data-icon-class') || '');
    });
}

const ORG_ID = '00000000-0000-0000-0000-000000000001';
const USER_ID = '00000000-0000-0000-0000-000000000001';
const USER_EMAIL = 'admin@example.com';
const USER_ROLES = 'ENGINEER';

const STRATEGY_INFO = {
    hierarchical: { label: 'Hierarchical', color: 'strategy-hierarchical' },
    semantic: { label: 'Semantic', color: 'strategy-semantic' },
    fixed: { label: 'Fixed Size', color: 'strategy-fixed' },
};

const FILE_EXT_COLORS = {
    log: '#f0a35e', txt: '#9db4d0', json: '#e0c46a', csv: '#7bc86c',
    md: '#6aa7e8', markdown: '#6aa7e8', yaml: '#c39be8', yml: '#c39be8',
};

// ============================================================
// App
// ============================================================
class GraphRCAApp {
    constructor() {
        this.apiBase = '/api/v1';
        this.uploadedFiles = new Map();
        this.lastServiceGraph = null;
        this._serviceGraphSim = null;
        this._serviceGraphReset = null;
        this._activityTimer = null;
        this._loadingTimer = null;
        this._ingestTimer = null;
        this._ingestCompleted = false;
        this._lastAnalysis = null;

        this.bindEvents();
        hydrateIcons();
        this.switchTab('dashboard');
        this.loadExampleQueries();
    }

    getApiKey() {
        return typeof INTERNAL_API_KEY === 'string' ? INTERNAL_API_KEY : '';
    }

    async api(path, options = {}) {
        const headers = Object.assign({
            'Content-Type': 'application/json',
            'X-Internal-API-Key': this.getApiKey(),
            'X-Organization-ID': ORG_ID,
            'X-User-ID': USER_ID,
            'X-User-Email': USER_EMAIL,
            'X-User-Roles': USER_ROLES,
        }, options.headers || {});
        if (options.body && !(options.body instanceof FormData)) {
            options.body = JSON.stringify(options.body);
        }
        if (options.body instanceof FormData) {
            delete headers['Content-Type'];
        }
        const response = await fetch(this.apiBase + path, Object.assign({}, options, { headers }));
        if (!response.ok) {
            let detail = `Request failed (${response.status})`;
            try {
                const data = await response.json();
                if (data && data.detail) detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
            } catch (_) { /* ignore */ }
            const err = new Error(detail);
            err.status = response.status;
            throw err;
        }
        return response.json();
    }

    // ---------------------------------------------------------
    // Navigation
    // ---------------------------------------------------------
    switchTab(tabName) {
        const titles = {
            dashboard: ['Dashboard', 'System overview & knowledge base state'],
            ingest: ['Ingest', 'Add logs and documents to the knowledge base'],
            analyze: ['Analyze Incident', 'Grounded incident analysis via hybrid RAG'],
            'vector-db': ['Vector DB', 'Semantic search over indexed chunks'],
            'graph-db': ['Graph DB', 'Knowledge graph & service dependencies'],
            system: ['System Status', 'Infrastructure health'],
        };
        document.querySelectorAll('.nav-btn').forEach((btn) => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });
        document.querySelectorAll('.tab-panel').forEach((panel) => {
            panel.classList.toggle('active', panel.id === tabName);
        });
        const [title, sub] = titles[tabName] || ['', ''];
        document.getElementById('pageTitle').textContent = title;
        document.getElementById('pageSubtitle').textContent = sub;

        if (tabName === 'dashboard') this.loadDashboard();
        if (tabName === 'ingest') this.loadServicesForFilter();
        if (tabName === 'vector-db') this.loadServicesForFilter();
        if (tabName === 'graph-db') { this.loadGraphNodes(); this.loadGraphRelationships(); this.loadServicesForFilter(); }
        if (tabName === 'system') this.checkConnection();
    }

    bindEvents() {
        document.querySelectorAll('.nav-btn').forEach((btn) => {
            btn.addEventListener('click', () => this.switchTab(btn.dataset.tab));
        });

        // Ingest
        const dropzone = document.getElementById('dropzone');
        const fileInput = document.getElementById('fileInput');
        dropzone.addEventListener('click', () => fileInput.click());
        dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
        dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            this.handleFiles(e.dataTransfer.files);
        });
        fileInput.addEventListener('change', (e) => this.handleFiles(e.target.files));
        document.getElementById('ingestBtn').addEventListener('click', () => this.startIngestion());

        document.querySelectorAll('.strategy-card input[type="radio"]').forEach((radio) => {
            radio.addEventListener('change', () => {
                document.querySelectorAll('.strategy-card').forEach((c) => c.classList.remove('active'));
                radio.closest('.strategy-card').classList.add('active');
            });
        });

        // Analyze
        document.getElementById('queryInput').addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') this.analyzeIncident();
        });
        document.getElementById('downloadPdfBtn').addEventListener('click', () => this.downloadPdf());

        // Vector chat
        document.getElementById('vectorSearchQuery').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this.searchVectors();
        });
        document.getElementById('vectorFilterService').addEventListener('change', () => this.searchVectors());
        document.getElementById('vectorFilterLevel').addEventListener('change', () => this.searchVectors());

        // Graph DB
        document.getElementById('serviceGraphInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this.loadServiceGraph();
        });
        const graphReset = document.getElementById('serviceGraphReset');
        if (graphReset) graphReset.addEventListener('click', () => { if (this._serviceGraphReset) this._serviceGraphReset(); });
        const graphFs = document.getElementById('serviceGraphFullscreen');
        if (graphFs) graphFs.addEventListener('click', () => { if (this._serviceGraphFullscreenToggle) this._serviceGraphFullscreenToggle(); });
        document.getElementById('graphNodeType').addEventListener('change', () => this.loadGraphNodes());
        document.getElementById('graphRelType').addEventListener('change', () => this.loadGraphRelationships());

        // Modal
        document.getElementById('modalBackdrop').addEventListener('click', (e) => {
            if (e.target.id === 'modalBackdrop') this.closeModal();
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') { this.closeModal(); }
        });

        // Refresh activity periodically
        this._activityTimer = setInterval(() => {
            if (document.getElementById('dashboard').classList.contains('active')) this.loadActivity();
        }, 30000);
    }

    // ---------------------------------------------------------
    // Toast & helpers
    // ---------------------------------------------------------
    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `<span class="toast-icon">${type === 'success' ? icon('spark') : type === 'error' ? icon('alert') : icon('doc')}</span><span>${this.escapeHtml(message)}</span>`;
        container.appendChild(toast);
        setTimeout(() => { toast.classList.add('out'); setTimeout(() => toast.remove(), 300); }, 4500);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text == null ? '' : String(text);
        return div.innerHTML;
    }

    formatNumber(num) {
        if (num == null) return '–';
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    }

    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    formatDateTime(isoString) {
        if (!isoString) return 'Unknown';
        try { return new Date(isoString).toLocaleString(); } catch { return isoString; }
    }

    relativeTime(isoString) {
        if (!isoString) return '—';
        const then = new Date(isoString).getTime();
        if (Number.isNaN(then)) return isoString;
        const seconds = Math.floor((Date.now() - then) / 1000);
        if (seconds < 10) return 'just now';
        if (seconds < 60) return `${seconds}s ago`;
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes}m ago`;
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours}h ago`;
        const days = Math.floor(hours / 24);
        return `${days}d ago`;
    }

    strategyBadge(strategy) {
        const info = STRATEGY_INFO[strategy] || { label: strategy, color: 'strategy-fixed' };
        return `<span class="strategy-badge ${info.color}">${this.escapeHtml(info.label)}</span>`;
    }

    // ---------------------------------------------------------
    // Dashboard
    // ---------------------------------------------------------
    async loadDashboard() {
        try {
            const [vectorStats, graphStats, summary, activity] = await Promise.all([
                this.api('/database/vectors/stats'),
                this.api('/database/graph/stats'),
                this.api('/database/vectors/summary?limit=200'),
                this.api('/database/activity/recent?limit=30'),
            ]);
            this._vectorStats = vectorStats;
            this._graphStats = graphStats;

            const docs = summary.documents_count || 0;
            const chunks = summary.total_chunks || vectorStats.points_count || 0;
            document.getElementById('statDocuments').textContent = this.formatNumber(docs);
            document.getElementById('statChunks').textContent = this.formatNumber(chunks);
            document.getElementById('statVectors').textContent = this.formatNumber(vectorStats.vectors_count);
            document.getElementById('statVectorsHint').textContent =
                `${vectorStats.dimension}d · ${vectorStats.status || 'unknown'}`;
            document.getElementById('statNodes').textContent = this.formatNumber(
                (graphStats.services || 0) + (graphStats.incidents || 0) +
                (graphStats.log_entries || 0) + (graphStats.errors || 0) +
                (graphStats.fixes || 0) + (graphStats.lessons || 0)
            );
            document.getElementById('statRelationships').textContent = this.formatNumber(graphStats.relationships || 0);
            document.getElementById('statIncidents').textContent = this.formatNumber(graphStats.incidents || 0);

            this.renderDocsCard(summary.documents || [], docs);
            this.renderActivity(activity.activities || []);
        } catch (e) {
            console.error('Failed to load dashboard:', e);
            document.getElementById('docsCardBody').innerHTML =
                `<p class="muted-center">Could not load dashboard: ${this.escapeHtml(e.message)}</p>`;
        }
    }

    renderDocsCard(documents, total) {
        document.getElementById('docsCardBadge').textContent = this.formatNumber(total);
        const body = document.getElementById('docsCardBody');
        if (!documents.length) {
            body.innerHTML = `<p class="muted-center">No documents indexed yet — go to <b>Ingest</b> to add files.</p>`;
            return;
        }
        body.innerHTML = documents.map((doc) => {
            const attrSafe = String(doc.source)
                .replace(/&/g, '&amp;').replace(/"/g, '&quot;')
                .replace(/</g, '&lt;').replace(/>/g, '&gt;')
                .replace(/'/g, "\\'");
            return `
            <button class="doc-row" onclick="app.openDocumentInfo('${attrSafe}')">
                <div class="doc-row-main">
                    <span class="doc-row-icon">${icon('doc')}</span>
                    <div class="doc-row-text">
                        <div class="doc-row-name">${this.escapeHtml(doc.source)}</div>
                        <div class="doc-row-sub">${this.formatNumber(doc.chunks)} chunks · ${this.escapeHtml(doc.service || 'unknown service')} · ${this.formatDateTime(doc.first_timestamp)}</div>
                    </div>
                </div>
                <div class="doc-row-badges">${Object.keys(doc.strategies).map((s) => this.strategyBadge(s)).join('')}</div>
                <span class="doc-row-arrow">${icon('link')}</span>
            </button>`;
        }).join('');
    }

    renderActivity(activities) {
        document.getElementById('activityBadge').textContent = activities.length;
        const body = document.getElementById('activityBody');
        if (!activities.length) {
            body.innerHTML = `<p class="muted-center">No activity yet — ingest files or run an analysis.</p>`;
            return;
        }
        body.innerHTML = activities.map((a) => {
            const typeIcon = a.type === 'analyze' ? 'search' : 'inbox';
            const cls = a.status === 'failed' ? 'activity-failed' : a.status === 'warning' ? 'activity-warning' : '';
            return `
            <div class="activity-item ${cls}">
                <span class="activity-icon">${icon(typeIcon)}</span>
                <div class="activity-body">
                    <div class="activity-title">${this.escapeHtml(a.title)}</div>
                    ${a.detail ? `<div class="activity-detail">${this.escapeHtml(a.detail)}</div>` : ''}
                    <div class="activity-time">${this.relativeTime(a.timestamp)}</div>
                </div>
            </div>`;
        }).join('');
    }

    async loadActivity() {
        try {
            const activity = await this.api('/database/activity/recent?limit=30');
            this.renderActivity(activity.activities || []);
        } catch (e) { console.error('Failed to load activity:', e); }
    }

    // ---------------------------------------------------------
    // Dashboard modals
    // ---------------------------------------------------------
    async showDocumentsModal() {
        let summary;
        try {
            summary = await this.api('/database/vectors/summary?limit=500');
        } catch (e) {
            this.showToast('Failed to load documents: ' + e.message, 'error');
            return;
        }
        const rows = summary.documents.map((doc) => `
            <tr>
                <td class="cell-source">${this.escapeHtml(doc.source)}</td>
                <td>${this.formatNumber(doc.chunks)}</td>
                <td>${Object.entries(doc.strategies).map(([s, n]) => `${this.strategyBadge(s)} ×${n}`).join(' ')}</td>
                <td>${this.escapeHtml(doc.service || '—')}</td>
                <td>${this.formatDateTime(doc.first_timestamp)}</td>
                <td><pre class="cell-snippet">${this.escapeHtml(doc.sample_text)}</pre></td>
            </tr>`).join('');
        this.openModal(
            `Documents &amp; Chunking Strategies (${summary.documents_count})`,
            `<div class="table-scroll">
                <table class="data-table">
                    <thead><tr><th>Document</th><th>Chunks</th><th>Strategies</th><th>Service</th><th>First seen</th><th>Sample</th></tr></thead>
                    <tbody>${rows || '<tr><td colspan="6" class="muted-center">No documents</td></tr>'}</tbody>
                </table>
            </div>
            <p class="modal-note">Total chunks in store: <b>${this.formatNumber(summary.total_chunks)}</b> · scanned ${this.formatNumber(summary.scanned_points)} points</p>`,
            'wide'
        );
    }

    showVectorsModal() {
        const s = this._vectorStats || {};
        const items = [
            ['Collection', s.collection], ['Points (chunks)', s.points_count], ['Vectors', s.vectors_count],
            ['Dimension', s.dimension], ['Distance', s.distance], ['Status', s.status],
            ['Segments', s.segments_count], ['Optimizer', s.optimizer_status],
        ];
        this.openModal('Vector Store Details',
            `<dl class="kv-grid">${items.map(([k, v]) => `<dt>${k}</dt><dd>${this.escapeHtml(v)}</dd>`).join('')}</dl>`);
    }

    async showNodesModal() {
        let nodes;
        try {
            nodes = (await this.api('/database/graph/nodes?limit=500')).nodes || [];
        } catch (e) {
            this.showToast('Failed to load nodes: ' + e.message, 'error');
            return;
        }
        const byType = {};
        nodes.forEach((n) => { byType[n.type] = (byType[n.type] || 0) + 1; });
        const summaryRow = Object.entries(byType).map(([t, c]) =>
            `<span class="type-pill">${this.escapeHtml(t)} ×${c}</span>`).join(' ');
        this._modalNodes = nodes;
        const rows = nodes.map((n, i) => `
            <tr class="clickable" onclick="app.showModalNodeByIndex(${i})">
                <td><code>${this.escapeHtml(String(n.id).substring(0, 16))}</code></td>
                <td><span class="node-type-badge">${this.escapeHtml(n.type)}</span></td>
                <td>${this.escapeHtml(Object.keys(n.properties || {}).join(', '))}</td>
            </tr>`).join('');
        this.openModal(
            `Graph Nodes (${nodes.length})`,
            `<div class="modal-summary">${summaryRow}</div>
            <div class="table-scroll">
                <table class="data-table">
                    <thead><tr><th>ID</th><th>Type</th><th>Keys</th></tr></thead>
                    <tbody>${rows || '<tr><td colspan="3" class="muted-center">No nodes</td></tr>'}</tbody>
                </table>
            </div>
            <p class="modal-note">Click a row for full properties.</p>`,
            'wide'
        );
    }

    async showRelationshipsModal() {
        let rels;
        try {
            rels = (await this.api('/database/graph/relationships?limit=500')).relationships || [];
        } catch (e) {
            this.showToast('Failed to load relationships: ' + e.message, 'error');
            return;
        }
        this._modalRelationships = rels;
        const rows = rels.map((r, i) => `
            <tr class="clickable" onclick="app.showModalRelationshipByIndex(${i})">
                <td>${this.escapeHtml(r.source)}</td>
                <td><span class="rel-type-badge">${this.escapeHtml(r.type)}</span></td>
                <td>${this.escapeHtml(r.target)}</td>
                <td>${this.escapeHtml(Object.keys(r.properties || {}).join(', ')) || '—'}</td>
            </tr>`).join('');
        this.openModal(
            `Graph Relationships (${rels.length})`,
            `<div class="table-scroll">
                <table class="data-table">
                    <thead><tr><th>Source</th><th>Type</th><th>Target</th><th>Props</th></tr></thead>
                    <tbody>${rows || '<tr><td colspan="4" class="muted-center">No relationships</td></tr>'}</tbody>
                </table>
            </div>
            <p class="modal-note">Click a row for full relationship details.</p>`,
            'wide'
        );
    }

    async showIncidentsModal() {
        let nodes;
        try {
            nodes = (await this.api('/database/graph/nodes?node_type=Incident&limit=200')).nodes || [];
        } catch (e) {
            this.showToast('Failed to load incidents: ' + e.message, 'error');
            return;
        }
        this._modalNodes = nodes;
        const rows = nodes.map((n, i) => {
            const p = n.properties || {};
            return `
            <tr class="clickable" onclick="app.showModalNodeByIndex(${i})">
                <td>${this.escapeHtml(p.title || p.name || n.id)}</td>
                <td>${this.escapeHtml(p.severity || '—')}</td>
                <td>${this.escapeHtml(p.service || '—')}</td>
                <td>${this.escapeHtml(p.status || '—')}</td>
                <td>${this.formatDateTime(p.created_at)}</td>
            </tr>`;
        }).join('');
        this.openModal(
            `Incidents in Knowledge Graph (${nodes.length})`,
            `<div class="table-scroll">
                <table class="data-table">
                    <thead><tr><th>Title</th><th>Severity</th><th>Service</th><th>Status</th><th>Created</th></tr></thead>
                    <tbody>${rows || '<tr><td colspan="5" class="muted-center">No incidents</td></tr>'}</tbody>
                </table>
            </div>
            <p class="modal-note">Click a row for full details.</p>`,
            'wide'
        );
    }

    showModalNodeByIndex(i) {
        const node = this._modalNodes && this._modalNodes[i];
        if (node) this.showNodeDetail(node);
    }

    showModalRelationshipByIndex(i) {
        const rel = this._modalRelationships && this._modalRelationships[i];
        if (rel) this.showRelationshipDetail(rel);
    }

    showNodeDetail(node) {
        const p = node.properties || {};
        const kv = Object.entries(p).map(([k, v]) =>
            `<dt>${this.escapeHtml(k)}</dt><dd>${this.escapeHtml(typeof v === 'object' ? JSON.stringify(v) : v)}</dd>`).join('');
        this.openModal(
            `<span class="node-type-badge">${this.escapeHtml(node.type)}</span> ${this.escapeHtml(node.id)}`,
            `<dl class="kv-grid">${kv || '<p class="muted-center">No properties</p>'}</dl>
            <p class="modal-note"><code>${this.escapeHtml(node.id)}</code></p>`,
            'wide'
        );
    }

    showRelationshipDetail(rel) {
        const props = rel.properties || {};
        const kv = Object.entries(props).map(([k, v]) =>
            `<dt>${this.escapeHtml(k)}</dt><dd>${this.escapeHtml(v)}</dd>`).join('');
        this.openModal(
            `<span class="rel-type-badge">${this.escapeHtml(rel.type)}</span>`,
            `<dl class="kv-grid">
                <dt>Source</dt><dd>${this.escapeHtml(rel.source)}</dd>
                <dt>Target</dt><dd>${this.escapeHtml(rel.target)}</dd>
                ${kv}
            </dl>`,
            'wide'
        );
    }

    async openDocumentInfo(source, strategies) {
        let summary;
        try {
            summary = await this.api('/database/vectors/summary?limit=500');
        } catch (e) { return; }
        const doc = (summary.documents || []).find((d) => d.source === source);
        if (!doc) return;
        const rows = Object.entries(doc.strategies).map(([s, n]) =>
            `<tr><td>${this.strategyBadge(s)}</td><td>${n}</td></tr>`).join('');
        this.openModal(
            `Document: ${this.escapeHtml(source)}`,
            `<dl class="kv-grid">
                <dt>Chunks</dt><dd>${doc.chunks}</dd>
                <dt>Service</dt><dd>${this.escapeHtml(doc.service || '—')}</dd>
                <dt>First seen</dt><dd>${this.formatDateTime(doc.first_timestamp)}</dd>
                <dt>Last seen</dt><dd>${this.formatDateTime(doc.last_timestamp)}</dd>
            </dl>
            <h3 class="subsection-title">Chunks by strategy</h3>
            <table class="data-table">
                <thead><tr><th>Strategy</th><th>Chunks</th></tr></thead>
                <tbody>${rows}</tbody>
            </table>
            <h3 class="subsection-title">Sample</h3>
            <pre class="cell-snippet">${this.escapeHtml(doc.sample_text)}</pre>`,
            'wide'
        );
    }

    // ---------------------------------------------------------
    // Modal
    // ---------------------------------------------------------
    openModal(title, contentHtml, size = '') {
        const box = document.getElementById('modalBox');
        box.className = `modal ${size}`.trim();
        box.innerHTML = `
            <div class="modal-header">
                <h2>${title}</h2>
                <button class="btn-icon" onclick="app.closeModal()" title="Close">${icon('close')}</button>
            </div>
            <div class="modal-body">${contentHtml}</div>
        `;
        document.getElementById('modalBackdrop').hidden = false;
        document.body.classList.add('modal-open');
    }

    closeModal() {
        document.getElementById('modalBackdrop').hidden = true;
        document.body.classList.remove('modal-open');
    }

    // ---------------------------------------------------------
    // Ingest
    // ---------------------------------------------------------
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
        const btn = document.getElementById('ingestBtn');
        if (this.uploadedFiles.size === 0) {
            list.innerHTML = '';
            btn.disabled = true;
            return;
        }
        btn.disabled = false;
        list.innerHTML = Array.from(this.uploadedFiles.values()).map((file) => {
            const ext = file.name.split('.').pop().toLowerCase();
            const color = FILE_EXT_COLORS[ext] || '#9db4d0';
            return `
            <div class="file-item">
                <span class="file-item-icon" style="color:${color}">${icon('doc')}</span>
                <div class="file-item-info">
                    <div class="file-item-name">${this.escapeHtml(file.name)}</div>
                    <div class="file-item-size">${this.formatBytes(file.size)}</div>
                </div>
                <button class="btn-icon btn-icon-sm" onclick="app.removeFile('${file.name.replace(/'/g, '\\\'')}')" title="Remove">${icon('close')}</button>
            </div>`;
        }).join('');
    }

    removeFile(name) {
        this.uploadedFiles.delete(name);
        this.renderFileList();
    }

    getSelectedStrategy() {
        const checked = document.querySelector('.strategy-card input[type="radio"]:checked');
        return checked ? checked.value : 'hierarchical';
    }

    async startIngestion() {
        const files = Array.from(this.uploadedFiles.values());
        if (files.length === 0) return;

        const strategy = this.getSelectedStrategy();
        document.getElementById('ingestBtn').disabled = true;
        this.showIngestOverlay(files, strategy);

        const formData = new FormData();
        files.forEach((f) => formData.append('files', f));
        formData.append('chunking_strategy', strategy);

        try {
            const response = await fetch(`${this.apiBase}/ingest/batch`, {
                method: 'POST',
                headers: {
                    'X-Internal-API-Key': this.getApiKey(),
                    'X-Organization-ID': ORG_ID,
                    'X-User-ID': USER_ID,
                    'X-User-Email': USER_EMAIL,
                    'X-User-Roles': USER_ROLES,
                },
                body: formData,
            });
            if (!response.ok) {
                let detail = 'Ingestion failed';
                try {
                    const data = await response.json();
                    if (data && data.detail) detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
                } catch (_) { /* ignore */ }
                throw new Error(detail);
            }
            const result = await response.json();
            this.finishIngestOverlay(true);
            this.renderIngestResults(result.results || []);
            this.uploadedFiles.clear();
            this.renderFileList();
            await this.loadDashboard();
            this.showToast(`Ingested ${files.length} file(s) successfully`, 'success');
        } catch (e) {
            this.finishIngestOverlay(false);
            console.error('Ingestion failed:', e);
            this.showToast('Ingestion failed: ' + e.message, 'error');
        } finally {
            document.getElementById('ingestBtn').disabled = false;
            this.loadServicesForFilter();
        }
    }

    renderIngestResults(results) {
        const card = document.getElementById('resultsCard');
        card.hidden = false;
        document.getElementById('resultsBody').innerHTML = results.map((r) => `
            <tr>
                <td>${this.escapeHtml(r.filename)}</td>
                <td><span class="status-pill ${r.status}">${r.status === 'completed' ? 'completed' : r.status === 'failed' ? 'failed' : 'no entries'}</span></td>
                <td>${r.entries_parsed || 0}</td>
                <td>${r.chunks_created || 0}</td>
                <td>${r.error ? this.escapeHtml(r.error).substring(0, 140) : r.truncated ? `<span class="text-warn">truncated at max chunks</span>` : '—'}</td>
            </tr>`).join('');
        card.scrollIntoView({ behavior: 'smooth' });
    }

    showIngestOverlay(files, strategy) {
        this._ingestCompleted = false;
        document.getElementById('ingestOverlay').hidden = false;
        document.getElementById('ingestOverlayTitle').textContent = `Ingesting ${files.length} file(s) with ${STRATEGY_INFO[strategy]?.label || strategy} strategy…`;
        document.getElementById('ingestOverlayFile').textContent = files.map((f) => f.name).join(', ').substring(0, 120);
        document.getElementById('ingestStatus').textContent = 'Starting…';
        document.getElementById('ingestProgressBar').style.width = '0%';

        const steps = [
            'Saving uploaded files',
            'Parsing log entries',
            'Chunking with strategy',
            'Generating embeddings',
            'Storing vectors in Qdrant',
            'Building knowledge graph',
        ];
        const stepsEl = document.getElementById('ingestSteps');
        stepsEl.innerHTML = steps.map((s, i) => `
            <div class="ingest-step" data-step="${i}">
                <span class="ingest-step-ind"></span><span>${s}</span>
            </div>`).join('');

        let activeIndex = 0;
        this._ingestTimer = setInterval(() => {
            if (this._ingestCompleted) return;
            activeIndex = Math.min(steps.length - 1, activeIndex + 1);
            this.updateIngestSteps(activeIndex);
            document.getElementById('ingestProgressBar').style.width =
                Math.min(90, Math.round((activeIndex / steps.length) * 90)) + '%';
            document.getElementById('ingestStatus').textContent =
                activeIndex >= steps.length - 1 ? 'Finishing up…' : steps[activeIndex] + '…';
        }, 900);
        this.updateIngestSteps(0);
    }

    updateIngestSteps(activeIndex) {
        document.querySelectorAll('#ingestSteps .ingest-step').forEach((el) => {
            const i = parseInt(el.dataset.step, 10);
            el.classList.toggle('active', i === activeIndex);
            el.classList.toggle('completed', i < activeIndex);
            el.querySelector('.ingest-step-ind').innerHTML = i < activeIndex ? icon('spark') : '';
        });
    }

    finishIngestOverlay(success) {
        this._ingestCompleted = true;
        if (this._ingestTimer) { clearInterval(this._ingestTimer); this._ingestTimer = null; }
        document.querySelectorAll('#ingestSteps .ingest-step').forEach((el) => {
            el.classList.add('completed');
            el.classList.remove('active');
            el.querySelector('.ingest-step-ind').innerHTML = icon('spark');
        });
        document.getElementById('ingestProgressBar').style.width = '100%';
        document.getElementById('ingestStatus').textContent = success ? 'Done!' : 'Failed';
        setTimeout(() => {
            document.getElementById('ingestOverlay').hidden = true;
        }, success ? 700 : 1600);
    }

    // ---------------------------------------------------------
    // Analyze
    // ---------------------------------------------------------
    async analyzeIncident() {
        const query = document.getElementById('queryInput').value.trim();
        const topK = parseInt(document.getElementById('topK').value, 10) || 10;
        if (!query) {
            this.showToast('Please enter a query', 'error');
            return;
        }

        const steps = [
            { text: 'Understanding query…' },
            { text: 'Searching vector database…' },
            { text: 'Searching graph database…' },
            { text: 'Ranking evidence…' },
            { text: 'Generating incident analysis…' },
        ];
        this.showLoading(true);
        this.updateLoadingSteps(steps);
        this.startLoadingProgress(steps);
        this._analyzeStart = Date.now();

        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 60000);

        try {
            const response = await this.api('/query/analyze', {
                method: 'POST',
                body: { query, top_k: topK },
                signal: controller.signal,
            });
            this.stopLoadingProgress();
            this.showLoading(false);
            this.displayResponse(response);
            document.getElementById('responseSection').hidden = false;
            document.getElementById('responseSection').scrollIntoView({ behavior: 'smooth' });
        } catch (e) {
            this.stopLoadingProgress();
            this.showLoading(false);
            console.error('Analysis failed:', e);
            const message = e && e.name === 'AbortError'
                ? 'Analysis timed out after 60s. The LLM provider may be rate-limited; try again shortly.'
                : (e && e.message) || 'Unknown error';
            this.showToast('Analysis failed: ' + message, 'error');
        } finally {
            clearTimeout(timeout);
        }
    }

    startLoadingProgress(steps) {
        this._loadingStart = Date.now();
        this._loadingTimer = setInterval(() => {
            const elapsed = Math.round((Date.now() - this._loadingStart) / 1000);
            const activeIndex = Math.min(steps.length - 1, Math.floor(elapsed / 4));
            this.updateLoadingSteps(steps.map((step, i) => ({
                text: step.text,
                active: i === activeIndex,
                completed: i < activeIndex,
            })));
            const hint = document.getElementById('loadingHint');
            if (hint) {
                hint.textContent = `Working… ${elapsed}s. Analysis can take up to a minute on the free tier.`;
            }
        }, 1000);
    }

    stopLoadingProgress() {
        if (this._loadingTimer) { clearInterval(this._loadingTimer); this._loadingTimer = null; }
    }

    showLoading(show) {
        document.getElementById('loadingOverlay').hidden = !show;
    }

    updateLoadingSteps(steps) {
        const container = document.getElementById('loadingSteps');
        container.innerHTML = steps.map((step, i) => `
            <div class="loading-step ${step.active ? 'active' : ''} ${step.completed ? 'completed' : ''}" data-step="${i}">
                <div class="loading-step-icon">
                    ${step.active ? '<div class="spinner" style="width:16px;height:16px;border-width:2px;"></div>' :
                      step.completed ? icon('spark') : (i + 1)}
                </div>
                <span>${step.text}</span>
            </div>`).join('');
    }

    async downloadPdf() {
        if (!this._lastAnalysis) {
            this.showToast('Run an analysis first, then download the PDF.', 'error');
            return;
        }
        const btn = document.getElementById('downloadPdfBtn');
        const originalLabel = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Generating PDF…';
        try {
            const headers = {
                'Content-Type': 'application/json',
                'X-Internal-API-Key': this.getApiKey(),
                'X-Organization-ID': ORG_ID,
                'X-User-ID': USER_ID,
                'X-User-Email': USER_EMAIL,
                'X-User-Roles': USER_ROLES,
            };
            const response = await fetch(`${this.apiBase}/query/report/pdf`, {
                method: 'POST',
                headers,
                body: JSON.stringify({ analysis: this._lastAnalysis }),
            });
            if (!response.ok) {
                let detail = `PDF request failed (${response.status})`;
                try {
                    const data = await response.json();
                    if (data && data.detail) detail = data.detail;
                } catch (_) { /* ignore */ }
                throw new Error(detail);
            }
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
            const link = document.createElement('a');
            link.href = url;
            link.download = `incident-analysis-${stamp}.pdf`;
            document.body.appendChild(link);
            link.click();
            link.remove();
            setTimeout(() => URL.revokeObjectURL(url), 3000);
            this.showToast('PDF report downloaded', 'success');
        } catch (e) {
            this.showToast('PDF export failed: ' + e.message, 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = originalLabel;
        }
    }

    displayResponse(response) {
        this._lastAnalysis = response;
        const confidenceClass = (response.confidence || '').toLowerCase().replace(/ /g, '-');
        document.getElementById('confidenceBadge').textContent = `Confidence: ${response.confidence}`;
        document.getElementById('confidenceBadge').className = `confidence-badge ${confidenceClass}`;
        document.getElementById('responseTime').textContent =
            `${((Date.now() - this._analyzeStart) / 1000).toFixed(1)}s · ${new Date().toLocaleTimeString()}`;

        const evidenceList = response.evidence || [];
        const sources = response.sources || [];
        const graphRels = response.graph_relationships || [];
        const logEvidence = evidenceList.filter((e) => e.type !== 'graph');
        const graphEvidence = evidenceList.filter((e) => e.type === 'graph');

        // Report header
        document.getElementById('reportTitle').textContent = response.title || 'Incident Analysis';
        document.getElementById('reportSubline').textContent =
            `${response.service || 'unknown service'} · ${response.team || 'unassigned'} · severity ${response.severity || '—'} · status ${response.status || '—'}`;

        // Verdict tiles
        document.getElementById('reportVerdict').innerHTML = [
            ['Risk Severity', response.risk_severity || '—'],
            ['Evidence Items', String(evidenceList.length)],
            ['Verified Sources', String(sources.length)],
            ['Graph Links', String(graphRels.length)],
        ].map(([label, value]) => `
            <div class="verdict-tile">
                <div class="verdict-label">${this.escapeHtml(label)}</div>
                <div class="verdict-value">${this.escapeHtml(value)}</div>
            </div>`).join('');

        document.getElementById('incidentDetails').innerHTML = `
            <dt>Incident ID</dt><dd>${this.escapeHtml(response.incident_id)}</dd>
            <dt>Source</dt><dd>${this.escapeHtml(response.source)}${response.source_url ? ` (<a href="${this.escapeHtml(response.source_url)}" target="_blank" rel="noopener">link</a>)` : ''}</dd>
            <dt>Severity</dt><dd><span class="status-pill ${this.escapeHtml((response.severity || '').toLowerCase())}">${this.escapeHtml(response.severity)}</span></dd>
            <dt>Status</dt><dd>${this.escapeHtml(response.status)}</dd>
            <dt>Service</dt><dd>${this.escapeHtml(response.service)}</dd>
            <dt>Team</dt><dd>${this.escapeHtml(response.team)}</dd>
            <dt>Created</dt><dd>${this.escapeHtml(this.formatDateTime(response.created_at))}</dd>
            <dt>Resolved</dt><dd>${this.escapeHtml(response.resolved_at ? this.formatDateTime(response.resolved_at) : 'Not resolved')}</dd>`;

        // Evidence summary
        const services = [...new Set(evidenceList.map((e) => e.metadata && e.metadata.service).filter(Boolean))];
        const levels = {};
        evidenceList.forEach((e) => {
            const lvl = (e.metadata && (e.metadata.level || e.metadata.severity)) || null;
            if (lvl) levels[lvl] = (levels[lvl] || 0) + 1;
        });
        const levelText = Object.entries(levels).map(([k, v]) => `${k} ${v}`).join(' · ') || '—';
        document.getElementById('evidenceSummary').innerHTML = `
            <div class="status-details">
                <div class="detail-line"><span>Total evidence</span><span>${evidenceList.length}</span></div>
                <div class="detail-line"><span>Log chunks</span><span>${logEvidence.length}</span></div>
                <div class="detail-line"><span>Graph nodes</span><span>${graphEvidence.length}</span></div>
                <div class="detail-line"><span>Services seen</span><span>${this.escapeHtml(services.join(', ') || '—')}</span></div>
                <div class="detail-line"><span>Levels</span><span>${this.escapeHtml(levelText)}</span></div>
            </div>`;

        document.getElementById('potentialRootCause').textContent = response.potential_root_cause || 'Not determined';
        document.getElementById('rootCause').textContent = response.root_cause || 'Not determined';

        document.getElementById('impactResolution').innerHTML = `
            <dt>Impact</dt><dd>${this.escapeHtml(response.impact)}</dd>
            <dt>Resolution</dt><dd>${this.escapeHtml(response.resolution)}</dd>
            <dt>Risk Severity</dt><dd><span class="status-pill ${this.escapeHtml((response.risk_severity || '').toLowerCase())}">${this.escapeHtml(response.risk_severity)}</span></dd>`;

        const timeline = document.getElementById('timeline');
        timeline.innerHTML = (response.timeline || []).map((event) => `
            <div class="timeline-item">
                <div class="timeline-time">${this.formatDateTime(event.timestamp)}</div>
                <div class="timeline-content">
                    <div class="timeline-event">${this.escapeHtml(event.event)}</div>
                    <div class="timeline-actor">${this.escapeHtml(event.actor)}</div>
                </div>
            </div>`).join('') || '<p class="muted-center">No timeline</p>';

        document.getElementById('lessonsLearned').innerHTML =
            (response.lessons_learned || []).map((l) => `<li>${this.escapeHtml(l)}</li>`).join('') ||
            '<li class="muted-center">No lessons recorded</li>';

        document.getElementById('logSnippets').innerHTML =
            (response.log_snippets || []).map((s) => `<div class="log-snippet">${this.escapeHtml(s)}</div>`).join('') ||
            '<div class="empty-note">No log snippets available</div>';

        document.getElementById('tags').innerHTML =
            (response.tags || []).map((t) => `<span class="tag">${this.escapeHtml(t)}</span>`).join('') ||
            '<span class="tag muted">No tags</span>';

        // Evidence toolbar + list
        document.getElementById('evidenceToolbar').innerHTML = `
            <span class="evidence-count-badge">${evidenceList.length} evidence items</span>
            <span class="evidence-count-badge">${logEvidence.length} log chunks</span>
            <span class="evidence-count-badge">${graphEvidence.length} graph nodes</span>
            <span class="evidence-cite">Each item below was retrieved from the vector store or knowledge graph — this is the proof behind the analysis.</span>`;

        document.getElementById('evidenceList').innerHTML = evidenceList.length ? `
            <div class="evidence-list">
            ${evidenceList.map((ev, i) => {
                const isGraph = ev.type === 'graph';
                const meta = ev.metadata || {};
                return `
                <div class="evidence-item ${isGraph ? 'evidence-graph' : ''}">
                    <div class="evidence-header">
                        <span class="evidence-source">
                            <span class="evidence-type-tag ${isGraph ? 'graph' : ''}">${this.escapeHtml((ev.type || 'evidence').toUpperCase())}</span>
                            [Source ${i + 1}] ${this.escapeHtml(ev.source || ev.node_type || 'unknown')}
                        </span>
                        <div class="evidence-meta">
                            ${ev.score != null ? `<span class="evidence-score-tag">score ${Number(ev.score).toFixed(3)}</span>` : ''}
                            ${meta.service ? `<span>Service: ${this.escapeHtml(meta.service)}</span>` : ''}
                            ${meta.level ? `<span>Level: ${this.escapeHtml(meta.level)}</span>` : ''}
                            ${meta.timestamp ? `<span>${this.escapeHtml(this.formatDateTime(meta.timestamp))}</span>` : ''}
                        </div>
                    </div>
                    <div class="evidence-content">${this.escapeHtml(ev.content || '')}</div>
                    ${(ev.chunk_id || meta.source_file) ? `<div class="evidence-cite">${meta.source_file ? `file: ${this.escapeHtml(meta.source_file)}` : ''}${ev.chunk_id ? ` · chunk ${this.escapeHtml(ev.chunk_id)}` : ''}${ev.retrieval_method ? ` · via ${this.escapeHtml(ev.retrieval_method)}` : ''}</div>` : ''}
                </div>`;
            }).join('')}
            </div>` : '<div class="empty-note">No evidence retrieved for this query. Try rephrasing or ingesting more data.</div>';

        // Verified sources
        document.getElementById('sourcesList').innerHTML = sources.length ? sources.map((s, i) => `
            <div class="source-row">
                <span class="cell-source">[Source ${i + 1}] ${this.escapeHtml(s.source_file || 'unknown')}</span>
                <span>service: ${this.escapeHtml(s.service || '—')}</span>
                <span>type: ${this.escapeHtml(s.source_type || '—')}</span>
                <span>score: ${s.retrieval_score != null ? Number(s.retrieval_score).toFixed(3) : '—'}</span>
                <span>${this.escapeHtml(s.timestamp && s.timestamp !== 'unknown' ? this.formatDateTime(s.timestamp) : '—')}</span>
            </div>`).join('') : '<div class="empty-note">No verified sources available.</div>';

        const graphRel = document.getElementById('graphRelationships');
        if (graphRels.length > 0) {
            graphRel.innerHTML = `
                <div class="table-scroll">
                    <table class="data-table">
                        <thead><tr><th>Source</th><th>Relationship</th><th>Target</th></tr></thead>
                        <tbody>
                            ${graphRels.map((r) => `
                                <tr><td>${this.escapeHtml(r.source)}</td>
                                <td><span class="rel-type-badge">${this.escapeHtml(r.type)}</span></td>
                                <td>${this.escapeHtml(r.target)}</td></tr>`).join('')}
                        </tbody>
                    </table>
                </div>`;
        } else {
            graphRel.innerHTML = '<div class="empty-note">No graph relationships found</div>';
        }

        document.getElementById('recommendationsList').innerHTML =
            (response.recommended_investigation || []).map((r, i) => `
            <div class="recommendation-item">
                <div class="recommendation-number">${i + 1}</div>
                <div class="recommendation-content">
                    <div class="recommendation-title">Investigation Step ${i + 1}</div>
                    <div class="recommendation-description">${this.escapeHtml(r)}</div>
                </div>
            </div>`).join('') || '<div class="empty-note">No recommendations available</div>';

        document.getElementById('jsonViewer').textContent = JSON.stringify(response, null, 2);
        document.getElementById('jsonViewer').hidden = false;

        this.renderGraphViz(graphRels, 'graphViz', { interactive: false });
    }

    toggleJson() {
        const el = document.getElementById('jsonViewer');
        el.hidden = !el.hidden;
    }

    // ---------------------------------------------------------
    // Graph visualization (SVG)
    // ---------------------------------------------------------
    renderGraphViz(relationships, containerId = 'graphViz', opts = {}) {
        const container = document.getElementById(containerId);
        if (!container) return;
        if (!relationships || relationships.length === 0) {
            container.innerHTML = '<p class="muted-center">No graph data to visualize</p>';
            return;
        }

        const rels = [];
        const seenRels = new Set();
        relationships.forEach((r) => {
            if (!r || r.source === r.target) return;
            const key = `${r.source}|${r.target}|${r.type}`;
            if (seenRels.has(key)) return;
            seenRels.add(key);
            rels.push(r);
        });

        const nodes = new Map();
        rels.forEach((r) => {
            if (!nodes.has(r.source)) nodes.set(r.source, { id: r.source, type: opts.nodeTypeOf ? opts.nodeTypeOf(r.source) : 'Service' });
            if (!nodes.has(r.target)) nodes.set(r.target, { id: r.target, type: opts.nodeTypeOf ? opts.nodeTypeOf(r.target) : 'Service' });
        });

        const nodeArray = Array.from(nodes.values());
        const width = container.clientWidth || 900;
        const height = 420;
        const centerX = width / 2;
        const centerY = height / 2;
        const radius = Math.min(width, height) / 2.6;

        const positions = new Map();
        nodeArray.forEach((node, i) => {
            const angle = (i / nodeArray.length) * Math.PI * 2 - Math.PI / 2;
            positions.set(node.id, { x: centerX + radius * Math.cos(angle), y: centerY + radius * Math.sin(angle) });
        });

        let svg = `<svg class="graph-svg" viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <marker id="arrowhead-${containerId}" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                    <polygon points="0 0, 10 3.5, 0 7" fill="var(--text-muted)" />
                </marker>
            </defs>`;

        rels.forEach((r) => {
            const s = positions.get(r.source);
            const t = positions.get(r.target);
            if (!s || !t) return;
            const cls = r.type === 'DEPENDS_ON' ? 'edge-depends' : r.type === 'PRODUCED_LOG' ? 'edge-prod' : 'edge-other';
            svg += `<line class="graph-link ${cls}" marker-end="url(#arrowhead-${containerId})" x1="${s.x}" y1="${s.y}" x2="${t.x}" y2="${t.y}" />`;
        });

        nodeArray.forEach((node) => {
            const pos = positions.get(node.id);
            if (!pos) return;
            const isLog = node.type === 'LogEntry';
            const r = isLog ? 6 : 15;
            const fill = isLog ? 'var(--accent-green)' : node.type === 'Service' ? 'var(--accent-blue)' : 'var(--accent-purple)';
            const label = node.type === 'Service'
                ? String(node.id).replace(/^service-/, '')
                : isLog ? '' : String(node.id).substring(0, 22);
            const clickAttr = opts.interactive === false ? '' : ` onclick="app.showServiceNode('${node.id.replace(/'/g, '')}')" style="cursor:pointer"`;
            svg += `
                <g class="graph-node" data-id="${node.id}"${clickAttr}>
                    <circle cx="${pos.x}" cy="${pos.y}" r="${r}" fill="${fill}" stroke="rgba(255,255,255,0.85)" stroke-width="1.5" />
                    ${label ? `<text class="graph-label" x="${pos.x}" y="${pos.y + (isLog ? 16 : 30)}" text-anchor="middle">${this.escapeHtml(label)}</text>` : ''}
                </g>`;
        });

        svg += '</svg>';
        container.innerHTML = svg;
    }

    // ---------------------------------------------------------
    // Vector DB (chat-style)
    // ---------------------------------------------------------
    appendChatMessage(role, html, cls = '') {
        const messages = document.getElementById('chatMessages');
        const el = document.createElement('div');
        el.className = `chat-message chat-${role} ${cls}`.trim();
        el.innerHTML = html;
        messages.appendChild(el);
        messages.scrollTop = messages.scrollHeight;
        return el;
    }

    async searchVectors() {
        const query = document.getElementById('vectorSearchQuery').value.trim();
        if (!query) {
            this.showToast('Enter a search query', 'error');
            return;
        }
        const service = document.getElementById('vectorFilterService').value;
        const level = document.getElementById('vectorFilterLevel').value;

        this.appendChatMessage('user', `<p>${this.escapeHtml(query)}</p>`);

        let loading = null;
        let loadingDots = 0;
        const start = Date.now();
        loading = this.appendChatMessage('assistant',
            `<div class="chat-typing"><div class="spinner"></div><span>Searching vectors…</span></div>`, 'typing');
        const typingTimer = setInterval(() => {
            loadingDots = (loadingDots + 1) % 4;
            const span = loading.querySelector('span');
            if (span) span.textContent = 'Searching vectors' + '.'.repeat(loadingDots) + ` (${Math.round((Date.now() - start) / 1000)}s)`;
        }, 400);

        try {
            let url = `/database/vectors/search?query=${encodeURIComponent(query)}&limit=20`;
            if (service) url += `&service=${encodeURIComponent(service)}`;
            if (level) url += `&level=${encodeURIComponent(level)}`;

            const result = await this.api(url);
            clearInterval(typingTimer);

            if (loading) {
                loading.className = 'chat-message chat-assistant';
                loading.innerHTML = this.renderVectorResultBubbles(result.results || []);
            }
        } catch (e) {
            clearInterval(typingTimer);
            if (loading) {
                loading.className = 'chat-message chat-assistant chat-error';
                loading.innerHTML = `<div class="chat-error-text">Search failed: ${this.escapeHtml(e.message)}</div>`;
            }
            console.error('Vector search failed:', e);
        }
    }

    renderVectorResultBubbles(results) {
        if (!results.length) {
            return `<div class="chat-empty">No matches found. Try different wording or relax filters.</div>`;
        }
        const levelCounts = {};
        results.forEach((r) => {
            const lvl = r.metadata && (r.metadata.level || r.metadata.severity);
            if (lvl) levelCounts[lvl] = (levelCounts[lvl] || 0) + 1;
        });
        const levelText = Object.entries(levelCounts).map(([k, v]) => `${k} ${v}`).join(' · ');
        return `<div class="chat-results">
            <div class="evidence-toolbar">
                <span class="evidence-count-badge">${results.length} matching chunks</span>
                ${levelText ? `<span class="evidence-cite">${this.escapeHtml(levelText)}</span>` : ''}
                <span class="evidence-cite">Retrieved log chunks ranked by semantic relevance — click any result to inspect the full evidence.</span>
            </div>
            ${results.map((r) => `
                <button class="chat-result" onclick="app.openChunkModal('${r.id}')">
                    <div class="chat-result-head">
                        <span class="chat-result-score">${Number(r.score).toFixed(3)}</span>
                        <span class="chat-result-source">${this.escapeHtml(r.source || 'unknown')}</span>
                        <span class="chat-result-meta">${this.escapeHtml(r.service || '')}${r.timestamp ? ' · ' + this.formatDateTime(r.timestamp) : ''}</span>
                    </div>
                    <div class="chat-result-text">${this.escapeHtml((r.text || '').substring(0, 220))}${(r.text || '').length > 220 ? '…' : ''}</div>
                </button>`).join('')}
        </div>`;
    }

    async openChunkModal(id) {
        try {
            const doc = await this.api(`/database/vectors/document/${encodeURIComponent(id)}`);
            const meta = doc.metadata || {};
            this.openModal(
                `Chunk details`,
                `
                <div class="modal-chunk-head">
                    ${doc.chunking_strategy ? this.strategyBadge(doc.chunking_strategy) : ''}
                    <span class="tag">${this.escapeHtml(doc.source_type || 'chunk')}</span>
                    <span class="tag">${this.escapeHtml(doc.service || 'unknown')}</span>
                    ${doc.chunk_index != null ? `<span class="tag">chunk ${doc.chunk_index}${doc.total_chunks ? '/' + doc.total_chunks : ''}</span>` : ''}
                </div>
                <dl class="kv-grid">
                    <dt>Source</dt><dd>${this.escapeHtml(doc.source || '—')}</dd>
                    <dt>Timestamp</dt><dd>${this.formatDateTime(doc.timestamp)}</dd>
                    <dt>Chunk type</dt><dd>${this.escapeHtml(meta.chunk_type || '—')}</dd>
                    <dt>Levels</dt><dd>${this.escapeHtml(Array.isArray(meta.levels) ? meta.levels.join(', ') : (meta.levels || '—'))}</dd>
                </dl>
                <h3 class="subsection-title">Content</h3>
                <pre class="modal-code">${this.escapeHtml(doc.text || '')}</pre>
                <h3 class="subsection-title">Metadata</h3>
                <pre class="modal-code">${this.escapeHtml(JSON.stringify(meta, null, 2))}</pre>
                <p class="modal-note"><code>${this.escapeHtml(doc.id)}</code></p>`,
                'wide'
            );
        } catch (e) {
            this.showToast('Failed to load chunk: ' + e.message, 'error');
        }
    }

    // ---------------------------------------------------------
    // Graph DB
    // ---------------------------------------------------------
    async loadServicesForFilter() {
        try {
            const result = await this.api('/database/graph/nodes?node_type=Service&limit=100');
            const services = (result.nodes || []).map((n) => n.properties.name || n.id)
                .filter((n, i, arr) => n && arr.indexOf(n) === i);
            const select = document.getElementById('vectorFilterService');
            select.innerHTML = '<option value="">All Services</option>' +
                services.map((s) => `<option value="${this.escapeHtml(s)}">${this.escapeHtml(s)}</option>`).join('');
            document.getElementById('serviceList').innerHTML =
                services.map((s) => `<option value="${this.escapeHtml(s)}"></option>`).join('');
        } catch (e) {
            console.error('Failed to load services:', e);
        }
    }

    async loadGraphNodes() {
        const nodeType = document.getElementById('graphNodeType').value;
        try {
            let url = '/database/graph/nodes?limit=200';
            if (nodeType) url += `&node_type=${encodeURIComponent(nodeType)}`;
            const result = await this.api(url);
            this.renderGraphNodes(result.nodes || []);
        } catch (e) {
            console.error('Failed to load graph nodes:', e);
            this.showToast('Failed to load nodes: ' + e.message, 'error');
        }
    }

    renderGraphNodes(nodes) {
        const tbody = document.getElementById('graphNodesBody');
        this._tableNodes = nodes;
        tbody.innerHTML = nodes.map((n, i) => `
            <tr class="clickable" onclick="app.showTableNodeByIndex(${i})">
                <td><code>${this.escapeHtml(String(n.id).substring(0, 14))}</code></td>
                <td><span class="node-type-badge">${this.escapeHtml(n.type)}</span></td>
                <td>${this.escapeHtml(JSON.stringify(n.properties || {}).substring(0, 160))}</td>
            </tr>`).join('') || '<tr><td colspan="3" class="muted-center">No nodes</td></tr>';
    }

    async loadGraphRelationships() {
        const relType = document.getElementById('graphRelType').value;
        try {
            let url = '/database/graph/relationships?limit=200';
            if (relType) url += `&rel_type=${encodeURIComponent(relType)}`;
            const result = await this.api(url);
            this.renderGraphRelationships(result.relationships || []);
        } catch (e) {
            console.error('Failed to load relationships:', e);
            this.showToast('Failed to load relationships: ' + e.message, 'error');
        }
    }

    renderGraphRelationships(rels) {
        const tbody = document.getElementById('graphRelationshipsBody');
        this._tableRels = rels;
        tbody.innerHTML = rels.map((r, i) => `
            <tr class="clickable" onclick="app.showTableRelByIndex(${i})">
                <td>${this.escapeHtml(String(r.source).substring(0, 22))}</td>
                <td><span class="rel-type-badge">${this.escapeHtml(r.type)}</span></td>
                <td>${this.escapeHtml(String(r.target).substring(0, 22))}</td>
            </tr>`).join('') || '<tr><td colspan="3" class="muted-center">No relationships</td></tr>';
    }

    showTableNodeByIndex(i) {
        const node = this._tableNodes && this._tableNodes[i];
        if (node) this.showNodeDetail(node);
    }

    showTableRelByIndex(i) {
        const rel = this._tableRels && this._tableRels[i];
        if (rel) this.showRelationshipDetail(rel);
    }

    async loadServiceGraph() {
        const serviceName = document.getElementById('serviceGraphInput').value.trim();
        if (!serviceName) {
            this.showToast('Enter a service name', 'error');
            return;
        }

        const container = document.getElementById('serviceGraphViz');
        container.innerHTML = '<p class="muted-center">Loading service graph…</p>';

        try {
            const result = await this.api(`/database/graph/service/${encodeURIComponent(serviceName)}?depth=2`);
            const nodes = result.nodes || [];
            const relationships = result.relationships || [];
            const byId = new Map(nodes.map((n) => [n.id, n]));
            const rootName = result.service || serviceName;
            const rootNode = nodes.find((n) => n.type === 'Service' && n.properties && n.properties.name === rootName)
                || nodes.find((n) => n.id === rootName || n.id === `service-${rootName}`)
                || nodes.find((n) => n.type === 'Service');
            const rootId = rootNode ? rootNode.id : rootName;

            this.lastServiceGraph = { nodes, edges: relationships, service: rootName };
            this.renderServiceGraph({ rootId, nodes, relationships, byId });
        } catch (e) {
            console.error('Failed to load service graph:', e);
            container.innerHTML = `<p class="muted-center text-error">Failed to load service graph: ${this.escapeHtml(e.message)}</p>`;
            this.showToast('Failed to load service graph: ' + e.message, 'error');
        }
    }

    destroyServiceGraph() {
        const sim = this._serviceGraphSim;
        if (sim) {
            if (sim.raf) cancelAnimationFrame(sim.raf);
            if (sim.wrap && document.fullscreenElement === sim.wrap && document.exitFullscreen) {
                const p = document.exitFullscreen();
                if (p && p.catch) p.catch(() => {});
            }
            if (sim.ac) sim.ac.abort();
            if (sim.tooltip && sim.tooltip.parentNode) sim.tooltip.parentNode.removeChild(sim.tooltip);
        }
        const fsBtn = document.getElementById('serviceGraphFullscreen');
        if (fsBtn) fsBtn.textContent = 'Fullscreen';
        this._serviceGraphSim = null;
        this._serviceGraphReset = null;
        this._serviceGraphFullscreenToggle = null;
    }

    renderServiceGraph({ rootId, nodes, relationships, byId }) {
        const container = document.getElementById('serviceGraphViz');
        if (!container) return;
        this.destroyServiceGraph();

        const cssVar = (name, fallback) => {
            const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
            return v || fallback;
        };
        const colors = {
            Service: cssVar('--accent-blue', '#4f8cff'),
            LogEntry: cssVar('--accent-green', '#3ddc97'),
            Error: '#ff5c7a',
        };
        const otherColor = cssVar('--accent-purple', '#9d7bff');
        const edgeColors = {
            DEPENDS_ON: cssVar('--accent-blue', '#4f8cff'),
            PRODUCED_LOG: cssVar('--accent-green', '#3ddc97'),
            RELATED_ERROR: '#ff5c7a',
        };
        const fontFamily = getComputedStyle(document.body).fontFamily || 'sans-serif';

        const index = new Map(nodes.map((n, i) => [n.id, i]));
        const gNodes = nodes.map((n) => {
            const type = n.type || 'Other';
            const rawName = (n.properties && (n.properties.name || n.properties.source)) || String(n.id);
            return {
                id: n.id,
                type,
                orig: n,
                label: String(rawName).replace(/^service-/, '').slice(0, 30),
                x: 0, y: 0, vx: 0, vy: 0, deg: 0,
                r: type === 'Service' ? 26 : type === 'LogEntry' ? 4.2 : 8,
                color: colors[type] || otherColor,
            };
        });

        // Neo4j's undirected MATCH returns each edge twice (both orientations).
        const seen = new Set();
        const gLinks = [];
        for (const rel of relationships || []) {
            if (!rel || rel.source === rel.target) continue;
            const s = index.get(rel.source);
            const t = index.get(rel.target);
            if (s == null || t == null) continue;
            const key = (s < t ? `${s}|${t}` : `${t}|${s}`) + '|' + rel.type;
            if (seen.has(key)) continue;
            seen.add(key);
            gLinks.push({ s, t, type: rel.type });
            gNodes[s].deg += 1;
            gNodes[t].deg += 1;
        }
        gNodes.forEach((n) => {
            n.rel = {};
            if (n.type === 'Service') n.r = 22 + Math.min(16, n.deg * 0.7);
            else if (n.type === 'LogEntry') n.r = 3.4 + Math.min(2.6, n.deg * 0.5);
        });
        gLinks.forEach((l) => {
            gNodes[l.s].rel[l.type] = (gNodes[l.s].rel[l.type] || 0) + 1;
            gNodes[l.t].rel[l.type] = (gNodes[l.t].rel[l.type] || 0) + 1;
        });

        const count = Math.max(gNodes.length, 1);
        const worldW = Math.max(1500, Math.min(4600, Math.sqrt(count) * 96));
        const worldH = Math.max(950, Math.min(3200, Math.sqrt(count) * 72));
        const cx = worldW / 2;
        const cy = worldH / 2;

        const serviceIdx = [];
        const anchor = new Array(gNodes.length).fill(-1);
        gNodes.forEach((n, i) => { if (n.type === 'Service') serviceIdx.push(i); });
        gLinks.forEach((l) => {
            const a = gNodes[l.s];
            const b = gNodes[l.t];
            if (a.type === 'Service' && b.type !== 'Service') anchor[l.t] = l.s;
            else if (b.type === 'Service' && a.type !== 'Service') anchor[l.s] = l.t;
        });

        const placeInitial = () => {
            const ringRadius = Math.min(worldW, worldH) * 0.26;
            serviceIdx.forEach((ni, k) => {
                const angle = (k / Math.max(serviceIdx.length, 1)) * Math.PI * 2 - Math.PI / 2;
                gNodes[ni].x = cx + Math.cos(angle) * ringRadius;
                gNodes[ni].y = cy + Math.sin(angle) * ringRadius;
            });
            gNodes.forEach((n, i) => {
                if (n.type === 'Service') return;
                const base = anchor[i] >= 0 ? gNodes[anchor[i]] : null;
                const bx = base ? base.x : cx;
                const by = base ? base.y : cy;
                const angle = Math.random() * Math.PI * 2;
                const dist = 30 + Math.random() * (base ? 210 : Math.min(worldW, worldH) * 0.3);
                n.x = bx + Math.cos(angle) * dist;
                n.y = by + Math.sin(angle) * dist;
            });
        };
        placeInitial();

        container.innerHTML = '';
        const wrap = document.createElement('div');
        wrap.className = 'graph-canvas-wrap';
        const canvas = document.createElement('canvas');
        canvas.className = 'graph-canvas';
        wrap.appendChild(canvas);
        container.appendChild(wrap);
        const tooltip = document.createElement('div');
        tooltip.className = 'graph-tooltip';
        wrap.appendChild(tooltip);
        const fsHint = document.createElement('div');
        fsHint.className = 'graph-fs-hint';
        fsHint.textContent = 'Esc to exit · drag bubbles · scroll to zoom · drag background to pan';
        wrap.appendChild(fsHint);

        const sim = {
            nodes: gNodes,
            links: gLinks,
            wrap,
            alpha: 1,
            dragging: -1,
            hovered: -1,
            panning: null,
            down: null,
            raf: 0,
            ac: new AbortController(),
            tooltip,
            camera: { scale: 1, ox: 0, oy: 0 },
            dpr: 1,
        };
        this._serviceGraphSim = sim;

        let cssW = 900;
        let cssH = 560;
        const resize = () => {
            const rect = wrap.getBoundingClientRect();
            cssW = Math.max(320, Math.round(rect.width || container.clientWidth || 900));
            cssH = Math.max(360, Math.round(rect.height || 560));
            sim.dpr = window.devicePixelRatio || 1;
            canvas.width = Math.round(cssW * sim.dpr);
            canvas.height = Math.round(cssH * sim.dpr);
            canvas.style.width = cssW + 'px';
            canvas.style.height = cssH + 'px';
        };
        const fitAll = () => {
            const scale = Math.min(cssW / worldW, cssH / worldH) * 0.94;
            sim.camera.scale = Math.max(0.05, Math.min(4, scale));
            sim.camera.ox = (cssW - worldW * sim.camera.scale) / 2;
            sim.camera.oy = (cssH - worldH * sim.camera.scale) / 2;
        };
        resize();
        fitAll();

        const draw = () => {
            const ctx = canvas.getContext('2d');
            if (!ctx) return;
            const cam = sim.camera;
            const dpr = sim.dpr;
            ctx.setTransform(1, 0, 0, 1, 0, 0);
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.setTransform(dpr * cam.scale, 0, 0, dpr * cam.scale, dpr * cam.ox, dpr * cam.oy);

            ctx.lineCap = 'round';
            for (const l of sim.links) {
                const a = gNodes[l.s];
                const b = gNodes[l.t];
                const isDepend = l.type === 'DEPENDS_ON';
                ctx.globalAlpha = isDepend ? 0.8 : 0.16;
                ctx.strokeStyle = edgeColors[l.type] || '#7b8bb0';
                ctx.lineWidth = (isDepend ? 1.8 : 1) / cam.scale;
                ctx.setLineDash(isDepend ? [7 / cam.scale, 5 / cam.scale] : []);
                ctx.beginPath();
                ctx.moveTo(a.x, a.y);
                ctx.lineTo(b.x, b.y);
                ctx.stroke();
            }
            ctx.setLineDash([]);
            ctx.globalAlpha = 1;

            const showLogLabels = gNodes.length <= 90;
            for (let i = 0; i < gNodes.length; i += 1) {
                const n = gNodes[i];
                const minR = n.type === 'Service' ? 9 : n.type === 'LogEntry' ? 1.5 : 3;
                const r = Math.max(n.r, minR / cam.scale);
                n.drawR = r;
                ctx.beginPath();
                ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
                ctx.fillStyle = n.color;
                ctx.globalAlpha = n.type === 'LogEntry' ? 0.8 : 0.95;
                ctx.fill();
                if (n.type !== 'LogEntry') {
                    ctx.globalAlpha = 1;
                    ctx.lineWidth = (n.id === rootId ? 2.6 : (n.type === 'Service' ? 1.6 : 1)) / cam.scale;
                    ctx.strokeStyle = n.id === rootId ? '#ffffff' : 'rgba(255,255,255,0.5)';
                    ctx.stroke();
                }
                if (i === sim.hovered) {
                    ctx.globalAlpha = 0.9;
                    ctx.lineWidth = 1.5 / cam.scale;
                    ctx.strokeStyle = '#ffffff';
                    ctx.beginPath();
                    ctx.arc(n.x, n.y, r + 4 / cam.scale, 0, Math.PI * 2);
                    ctx.stroke();
                }
            }
            ctx.globalAlpha = 1;

            // Labels live in screen space so they stay readable at any zoom.
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.lineJoin = 'round';
            gNodes.forEach((n, i) => {
                const isService = n.type === 'Service';
                if (!isService && !(showLogLabels && n.type === 'LogEntry') && i !== sim.hovered) return;
                const sx = n.x * cam.scale + cam.ox;
                const sy = n.y * cam.scale + cam.oy + n.drawR * cam.scale + (isService ? 13 : 9);
                if (sx < -80 || sx > cssW + 80 || sy < -30 || sy > cssH + 30) return;
                const text = isService ? n.label : String(n.label).slice(0, 14);
                ctx.font = `${isService ? '600 12px' : '11px'} ${fontFamily}`;
                ctx.lineWidth = 3;
                ctx.strokeStyle = 'rgba(6, 10, 20, 0.88)';
                ctx.strokeText(text, sx, sy);
                ctx.fillStyle = isService ? (n.id === rootId ? '#ffffff' : '#cfe0ff') : '#c9d8f0';
                ctx.fillText(text, sx, sy);
            });
        };

        const cell = Math.max(90, Math.min(180, Math.min(worldW, worldH) / 14));
        const cols = Math.ceil(worldW / cell);
        const rows = Math.ceil(worldH / cell);
        const tick = () => {
            const n = gNodes.length;
            const bins = new Array(cols * rows);
            for (let i = 0; i < n; i += 1) {
                const p = gNodes[i];
                const gx = Math.min(cols - 1, Math.max(0, Math.floor(p.x / cell)));
                const gy = Math.min(rows - 1, Math.max(0, Math.floor(p.y / cell)));
                const bi = gy * cols + gx;
                let bin = bins[bi];
                if (!bin) bin = bins[bi] = { count: 0, sx: 0, sy: 0, items: [] };
                bin.count += 1;
                bin.sx += p.x;
                bin.sy += p.y;
                bin.items.push(i);
                p.bin = bi;
            }

            for (let i = 0; i < n; i += 1) {
                const p = gNodes[i];
                if (p.pinned) continue;
                let ax = (cx - p.x) * 0.0007;
                let ay = (cy - p.y) * 0.0007;
                for (let bi = 0; bi < bins.length; bi += 1) {
                    const bin = bins[bi];
                    if (!bin) continue;
                    if (bi === p.bin) {
                        for (let k = 0; k < bin.items.length; k += 1) {
                            const j = bin.items[k];
                            if (j === i) continue;
                            const q = gNodes[j];
                            const dx = p.x - q.x;
                            const dy = p.y - q.y;
                            const d2 = dx * dx + dy * dy + 4;
                            const d = Math.sqrt(d2);
                            const f = Math.min(9, 1600 / d2);
                            ax += (dx / d) * f;
                            ay += (dy / d) * f;
                        }
                    } else {
                        // Approximate a whole cell as one charge at its centroid.
                        const dx = p.x - bin.sx / bin.count;
                        const dy = p.y - bin.sy / bin.count;
                        const d2 = dx * dx + dy * dy + 900;
                        const d = Math.sqrt(d2);
                        const f = Math.min(7, (1500 * bin.count) / d2);
                        ax += (dx / d) * f;
                        ay += (dy / d) * f;
                    }
                }
                p.ax = ax;
                p.ay = ay;
            }

            for (const l of gLinks) {
                const a = gNodes[l.s];
                const b = gNodes[l.t];
                const dx = b.x - a.x;
                const dy = b.y - a.y;
                const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
                const rest = l.type === 'DEPENDS_ON' ? 250 : 70;
                const f = Math.max(-2.5, Math.min(2.5, (d - rest) * 0.012));
                const fx = (dx / d) * f;
                const fy = (dy / d) * f;
                if (!a.pinned) { a.ax += fx; a.ay += fy; }
                if (!b.pinned) { b.ax -= fx; b.ay -= fy; }
            }

            // Keep service bubbles apart so their labels stay readable.
            for (let a = 0; a < serviceIdx.length; a += 1) {
                for (let b = a + 1; b < serviceIdx.length; b += 1) {
                    const na = gNodes[serviceIdx[a]];
                    const nb = gNodes[serviceIdx[b]];
                    const dx = nb.x - na.x;
                    const dy = nb.y - na.y;
                    const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
                    if (d >= 240) continue;
                    const f = (240 - d) * 0.06;
                    const fx = (dx / d) * f;
                    const fy = (dy / d) * f;
                    if (!na.pinned) { na.ax -= fx; na.ay -= fy; }
                    if (!nb.pinned) { nb.ax += fx; nb.ay += fy; }
                }
            }

            const margin = 40;
            for (let i = 0; i < n; i += 1) {
                const p = gNodes[i];
                if (p.pinned) { p.vx = 0; p.vy = 0; continue; }
                if (p.x < margin) p.ax += (margin - p.x) * 0.02;
                else if (p.x > worldW - margin) p.ax -= (p.x - (worldW - margin)) * 0.02;
                if (p.y < margin) p.ay += (margin - p.y) * 0.02;
                else if (p.y > worldH - margin) p.ay -= (p.y - (worldH - margin)) * 0.02;

                p.vx = (p.vx + p.ax) * 0.9;
                p.vy = (p.vy + p.ay) * 0.9;
                const speed = Math.hypot(p.vx, p.vy);
                if (speed > 22) {
                    p.vx = (p.vx / speed) * 22;
                    p.vy = (p.vy / speed) * 22;
                }
                p.x += p.vx;
                p.y += p.vy;
            }
        };

        const loop = () => {
            sim.raf = 0;
            if (sim.alpha > 0.04 || sim.dragging >= 0) {
                tick();
                sim.alpha *= 0.985;
                draw();
                sim.raf = requestAnimationFrame(loop);
            } else {
                draw();
            }
        };
        const kick = () => {
            if (!sim.raf) sim.raf = requestAnimationFrame(loop);
        };
        sim.tick = tick;
        sim.draw = draw;
        kick();

        const pointerPos = (ev) => {
            const rect = canvas.getBoundingClientRect();
            return { x: ev.clientX - rect.left, y: ev.clientY - rect.top };
        };
        const pick = (mx, my) => {
            const cam = sim.camera;
            const wx = (mx - cam.ox) / cam.scale;
            const wy = (my - cam.oy) / cam.scale;
            let best = -1;
            let bestD = Infinity;
            for (let i = 0; i < gNodes.length; i += 1) {
                const n = gNodes[i];
                const base = Math.max(n.drawR || n.r, (n.type === 'Service' ? 10 : n.type === 'LogEntry' ? 2 : 4) / cam.scale);
                const rr = base + 5 / cam.scale;
                const dx = wx - n.x;
                const dy = wy - n.y;
                const d2 = dx * dx + dy * dy;
                if (d2 <= rr * rr && d2 < bestD) {
                    bestD = d2;
                    best = i;
                }
            }
            return best;
        };
        const showTip = (i, mx, my) => {
            if (i < 0) {
                tooltip.style.display = 'none';
                return;
            }
            const n = gNodes[i];
            const relText = Object.entries(n.rel || {}).map(([k, v]) => `${k} ${v}`).join(' · ');
            tooltip.textContent = `${n.label} · ${n.type}${relText ? ' · ' + relText : ''}`;
            tooltip.style.left = mx + 'px';
            tooltip.style.top = my + 'px';
            tooltip.style.display = 'block';
        };

        const onDown = (ev) => {
            const p = pointerPos(ev);
            const i = pick(p.x, p.y);
            sim.down = { x: p.x, y: p.y, i, moved: false };
            tooltip.style.display = 'none';
            if (i >= 0) {
                sim.dragging = i;
                gNodes[i].pinned = true;
                gNodes[i].vx = 0;
                gNodes[i].vy = 0;
                kick();
            } else {
                sim.panning = { x: p.x, y: p.y, ox: sim.camera.ox, oy: sim.camera.oy };
            }
            if (canvas.setPointerCapture) canvas.setPointerCapture(ev.pointerId);
            ev.preventDefault();
        };
        const onMove = (ev) => {
            const p = pointerPos(ev);
            if (sim.dragging >= 0) {
                const n = gNodes[sim.dragging];
                const wx = (p.x - sim.camera.ox) / sim.camera.scale;
                const wy = (p.y - sim.camera.oy) / sim.camera.scale;
                n.vx = (wx - n.x) * 0.6;
                n.vy = (wy - n.y) * 0.6;
                n.x = wx;
                n.y = wy;
                sim.alpha = Math.max(sim.alpha, 0.5);
                if (sim.down && Math.hypot(p.x - sim.down.x, p.y - sim.down.y) > 4) sim.down.moved = true;
                draw();
                kick();
                return;
            }
            if (sim.panning) {
                sim.camera.ox = sim.panning.ox + (p.x - sim.panning.x);
                sim.camera.oy = sim.panning.oy + (p.y - sim.panning.y);
                if (sim.down && Math.hypot(p.x - sim.down.x, p.y - sim.down.y) > 4) sim.down.moved = true;
                draw();
                return;
            }
            const i = pick(p.x, p.y);
            if (i !== sim.hovered) {
                sim.hovered = i;
                draw();
            }
            canvas.style.cursor = i >= 0 ? 'grab' : 'grab';
            showTip(i, p.x, p.y);
        };
        const onUp = () => {
            if (sim.dragging >= 0) {
                const i = sim.dragging;
                const n = gNodes[i];
                n.pinned = false;
                const speed = Math.hypot(n.vx, n.vy);
                if (speed > 18) {
                    n.vx = (n.vx / speed) * 18;
                    n.vy = (n.vy / speed) * 18;
                }
                if (sim.down && !sim.down.moved && n.orig) {
                    this.showNodeDetail(n.orig);
                }
                sim.dragging = -1;
                if (sim.down && sim.down.moved) sim.alpha = Math.max(sim.alpha, 0.25);
                kick();
            }
            sim.panning = null;
            sim.down = null;
            canvas.style.cursor = 'grab';
            tooltip.style.display = 'none';
        };
        const onWheel = (ev) => {
            ev.preventDefault();
            const p = pointerPos(ev);
            const cam = sim.camera;
            const factor = Math.exp(-ev.deltaY * 0.0015);
            const next = Math.max(0.04, Math.min(6, cam.scale * factor));
            const k = next / cam.scale;
            cam.ox = p.x - (p.x - cam.ox) * k;
            cam.oy = p.y - (p.y - cam.oy) * k;
            cam.scale = next;
            draw();
        };
        const onDblClick = (ev) => {
            const p = pointerPos(ev);
            if (pick(p.x, p.y) < 0) {
                fitAll();
                sim.alpha = Math.max(sim.alpha, 0.25);
                draw();
                kick();
            }
        };
        const onResize = () => {
            resize();
            fitAll();
            draw();
        };

        const signal = sim.ac.signal;
        canvas.addEventListener('pointerdown', onDown, { signal });
        canvas.addEventListener('pointermove', onMove, { signal });
        canvas.addEventListener('pointerup', onUp, { signal });
        canvas.addEventListener('pointercancel', onUp, { signal });
        canvas.addEventListener('pointerleave', () => {
            sim.hovered = -1;
            tooltip.style.display = 'none';
            draw();
        }, { signal });
        canvas.addEventListener('wheel', onWheel, { signal, passive: false });
        canvas.addEventListener('dblclick', onDblClick, { signal });
        window.addEventListener('resize', onResize, { signal });

        this._serviceGraphReset = () => {
            placeInitial();
            gNodes.forEach((n) => {
                n.vx = 0;
                n.vy = 0;
                n.pinned = false;
            });
            sim.alpha = 1;
            fitAll();
            draw();
            kick();
        };

        const fsBtn = document.getElementById('serviceGraphFullscreen');
        const onFullscreenChange = () => {
            const active = document.fullscreenElement === wrap;
            if (fsBtn) fsBtn.textContent = active ? 'Exit fullscreen' : 'Fullscreen';
            requestAnimationFrame(() => {
                resize();
                fitAll();
                draw();
            });
            setTimeout(() => {
                resize();
                fitAll();
                draw();
            }, 140);
        };
        document.addEventListener('fullscreenchange', onFullscreenChange, { signal });
        this._serviceGraphFullscreenToggle = () => {
            if (document.fullscreenElement === wrap) {
                if (document.exitFullscreen) {
                    const p = document.exitFullscreen();
                    if (p && p.catch) p.catch(() => {});
                }
                return;
            }
            if (wrap.requestFullscreen) {
                const p = wrap.requestFullscreen();
                if (p && p.catch) p.catch((e) => this.showToast('Fullscreen unavailable: ' + e.message, 'error'));
            }
        };
    }

    showServiceNode(id) {
        const node = (this.lastServiceGraph?.nodes || []).find((n) => n.id === id);
        if (node) {
            this.showNodeDetail(node);
        } else {
            this.openModal('Node', `<p class="muted-center">Node details unavailable for <code>${this.escapeHtml(id)}</code></p>`);
        }
    }

    // ---------------------------------------------------------
    // System status
    // ---------------------------------------------------------
    async checkConnection() {
        try {
            const status = await this.api('/database/system/status');
            this.renderSystemStatus(status);
        } catch (e) {
            console.error('System status check failed:', e);
            this.showToast('Status check failed: ' + e.message, 'error');
        }
    }

    renderSystemStatus(status) {
        const qdrant = status.qdrant || {};
        const neo4j = status.neo4j || {};
        const healthy = !!status.overall_healthy;

        const dot = (ok) => `<span class="status-dot ${ok ? 'connected' : 'disconnected'}"></span>`;

        // Qdrant
        document.getElementById('qdrantStatus').innerHTML = `${dot(qdrant.healthy)} ${qdrant.healthy ? 'Healthy' : 'Unhealthy'}`;
        document.getElementById('qdrantDetails').innerHTML = qdrant.stats ? `
            <div class="detail-line"><span>Collection</span><span><code>postmortems_v1</code></span></div>
            <div class="detail-line"><span>Points (chunks)</span><span>${this.formatNumber(qdrant.stats.points_count)}</span></div>
            <div class="detail-line"><span>Vectors</span><span>${this.formatNumber(qdrant.stats.vectors_count)}</span></div>
            <div class="detail-line"><span>Dimension</span><span>${this._vectorStats?.dimension ?? '—'}d</span></div>` :
            'No stats available';

        // Neo4j
        document.getElementById('neo4jStatus').innerHTML = `${dot(neo4j.healthy)} ${neo4j.healthy ? 'Healthy' : 'Unhealthy'}`;
        document.getElementById('neo4jDetails').innerHTML = neo4j.stats ? `
            <div class="detail-line"><span>Services</span><span>${this.formatNumber(neo4j.stats.services || 0)}</span></div>
            <div class="detail-line"><span>Incidents</span><span>${this.formatNumber(neo4j.stats.incidents || 0)}</span></div>
            <div class="detail-line"><span>Log entries</span><span>${this.formatNumber(neo4j.stats.log_entries || 0)}</span></div>
            <div class="detail-line"><span>Relationships</span><span>${this.formatNumber(neo4j.stats.relationships || 0)}</span></div>` :
            'No stats available';

        // Embeddings
        const emb = status.embedding || {};
        const embConfigured = Boolean(emb.provider && emb.model);
        const embLabel = emb.provider === 'sentence-transformers'
            ? 'Local · on-device'
            : embConfigured ? 'API · hosted' : 'Not configured';
        document.getElementById('embedStatus').innerHTML =
            `${dot(embConfigured)} ${embLabel}`;
        document.getElementById('embedDetails').innerHTML = `
            <div class="detail-line"><span>Provider</span><span>${this.escapeHtml(emb.provider || '—')}</span></div>
            <div class="detail-line"><span>Model</span><span>${this.escapeHtml(emb.model || '—')}</span></div>
            <div class="detail-line"><span>Dimension</span><span>${this.escapeHtml(emb.dimension ?? '—')}d</span></div>`;

        // LLM
        const llm = status.llm || {};
        document.getElementById('llmStatus').innerHTML = `${dot(true)} ${this.escapeHtml(llm.provider || '—')}`;
        document.getElementById('llmDetails').innerHTML = `
            <div class="detail-line"><span>Provider</span><span>${this.escapeHtml(llm.provider || '—')}</span></div>
            <div class="detail-line"><span>Model</span><span>${this.escapeHtml(llm.model || '—')}</span></div>`;

        // Global health pill
        const pill = document.getElementById('globalHealth');
        pill.innerHTML = `${dot(healthy)} <span>${healthy ? 'All systems operational' : 'Degraded'}</span>`;

        // Topbar pills
        document.getElementById('embedPill').innerHTML = `<span class="pill-dot"></span>${this.escapeHtml((emb.model || '').split('/').pop() || 'embeddings')}`;
        document.getElementById('llmPill').innerHTML = `<span class="pill-dot"></span>${this.escapeHtml(llm.model || llm.provider || 'llm')}`;
    }

    // ---------------------------------------------------------
    // Examples
    // ---------------------------------------------------------
    loadExampleQueries() {
        const examples = [
            'Why did the payment service fail last night?',
            'What caused the authentication service to return 500 errors?',
            'Root cause of the database connection pool exhaustion',
            'Show previous incidents related to authentication service',
            'Which services depend on the failing payment service?',
            'What fixes worked previously for database timeouts?',
            'What is the blast radius of the auth service failure?',
            'Diagnose: NullPointerException in payment adapter v2.3.1',
        ];
        const container = document.getElementById('exampleChips');
        container.innerHTML = examples.map((q) =>
            `<button class="example-chip" onclick="app.useExample('${q.replace(/'/g, '\\\'')}')">${this.escapeHtml(q)}</button>`).join('');
    }

    useExample(q) {
        document.getElementById('queryInput').value = q;
        this.switchTab('analyze');
        document.getElementById('queryInput').focus();
    }
}

// ============================================================
// Boot
// ============================================================
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new GraphRCAApp();
});
