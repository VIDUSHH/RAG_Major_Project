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
class RAGApp {
    constructor() {
        this.apiBase = '/api/v1';
        this.uploadedFiles = new Map();
        this.lastServiceGraph = null;
        this._activityTimer = null;
        this._loadingTimer = null;
        this._ingestTimer = null;
        this._ingestCompleted = false;

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

    displayResponse(response) {
        document.getElementById('confidenceBadge').textContent = `Confidence: ${response.confidence}`;
        document.getElementById('confidenceBadge').className =
            `confidence-badge ${(response.confidence || '').toLowerCase().replace(/ /g, '-')}`;
        document.getElementById('responseTime').textContent =
            `Generated: ${new Date().toLocaleTimeString()} · took ${((Date.now() - this._analyzeStart) / 1000).toFixed(1)}s`;

        document.getElementById('incidentDetails').innerHTML = `
            <dt>Incident ID</dt><dd>${this.escapeHtml(response.incident_id)}</dd>
            <dt>Title</dt><dd>${this.escapeHtml(response.title)}</dd>
            <dt>Source</dt><dd>${this.escapeHtml(response.source)}${response.source_url ? ` (<a href="${this.escapeHtml(response.source_url)}" target="_blank" rel="noopener">link</a>)` : ''}</dd>
            <dt>Severity</dt><dd><span class="status-pill ${this.escapeHtml((response.severity || '').toLowerCase())}">${this.escapeHtml(response.severity)}</span></dd>
            <dt>Status</dt><dd>${this.escapeHtml(response.status)}</dd>
            <dt>Service</dt><dd>${this.escapeHtml(response.service)}</dd>
            <dt>Team</dt><dd>${this.escapeHtml(response.team)}</dd>
            <dt>Created</dt><dd>${this.escapeHtml(response.created_at)}</dd>
            <dt>Resolved</dt><dd>${this.escapeHtml(response.resolved_at || 'Not resolved')}</dd>`;

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
            '<p class="muted-center">No log snippets available</p>';

        document.getElementById('tags').innerHTML =
            (response.tags || []).map((t) => `<span class="tag">${this.escapeHtml(t)}</span>`).join('') ||
            '<span class="tag muted">No tags</span>';

        document.getElementById('evidenceList').innerHTML =
            (response.evidence || []).map((ev, i) => `
            <div class="evidence-item">
                <div class="evidence-header">
                    <span class="evidence-source">[Source ${i + 1}] ${this.escapeHtml((ev.type || '').toUpperCase())}: ${this.escapeHtml(ev.source)}</span>
                    <div class="evidence-meta">
                        <span>Score: ${ev.score != null ? Number(ev.score).toFixed(3) : 'N/A'}</span>
                        <span>Service: ${this.escapeHtml(ev.metadata?.service || 'unknown')}</span>
                        <span>Time: ${this.escapeHtml(ev.metadata?.timestamp || 'unknown')}</span>
                    </div>
                </div>
                <div class="evidence-content">${this.escapeHtml(ev.content || '')}</div>
            </div>`).join('') || '<p class="muted-center">No evidence retrieved</p>';

        const graphRel = document.getElementById('graphRelationships');
        if (response.graph_relationships && response.graph_relationships.length > 0) {
            graphRel.innerHTML = `
                <div class="table-scroll">
                    <table class="data-table">
                        <thead><tr><th>Source</th><th>Relationship</th><th>Target</th></tr></thead>
                        <tbody>
                            ${response.graph_relationships.map((r) => `
                                <tr><td>${this.escapeHtml(r.source)}</td>
                                <td><span class="rel-type-badge">${this.escapeHtml(r.type)}</span></td>
                                <td>${this.escapeHtml(r.target)}</td></tr>`).join('')}
                        </tbody>
                    </table>
                </div>`;
        } else {
            graphRel.innerHTML = '<p class="muted-center">No graph relationships found</p>';
        }

        document.getElementById('recommendationsList').innerHTML =
            (response.recommended_investigation || []).map((r, i) => `
            <div class="recommendation-item">
                <div class="recommendation-number">${i + 1}</div>
                <div class="recommendation-content">
                    <div class="recommendation-title">Investigation Step ${i + 1}</div>
                    <div class="recommendation-description">${this.escapeHtml(r)}</div>
                </div>
            </div>`).join('') || '<p class="muted-center">No recommendations available</p>';

        document.getElementById('jsonViewer').textContent = JSON.stringify(response, null, 2);
        document.getElementById('jsonViewer').hidden = false;

        this.renderGraphViz(response.graph_relationships || [], 'graphViz', { interactive: false });
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

        const nodes = new Map();
        relationships.forEach((r) => {
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
                    <polygon points="0 0, 10 3.5, 0 7" fill="var(--muted)" />
                </marker>
            </defs>`;

        relationships.forEach((r) => {
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
            const r = isLog ? 7 : 15;
            const fill = isLog ? 'var(--accent-green)' : node.type === 'Service' ? 'var(--accent-blue)' : 'var(--accent-purple)';
            const clickAttr = opts.interactive === false ? '' : ` onclick="app.showServiceNode('${node.id.replace(/'/g, '')}')" style="cursor:pointer"`;
            svg += `
                <g class="graph-node" data-id="${node.id}"${clickAttr}>
                    <circle cx="${pos.x}" cy="${pos.y}" r="${r}" fill="${fill}" stroke="rgba(255,255,255,0.85)" stroke-width="1.5" />
                    <text class="graph-label" x="${pos.x}" y="${pos.y + (isLog ? 18 : 30)}" text-anchor="middle">${this.escapeHtml(String(node.id).substring(0, isLog ? 10 : 22))}</text>
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
        return `<div class="chat-results">
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
            const nodeById = {};
            nodes.forEach((n) => { nodeById[n.id] = n; });

            const edges = (result.relationships || []).map((r) => ({
                source: r.source,
                target: r.target,
                type: r.type,
            }));
            if (edges.length === 0) {
                nodes.forEach((n) => {
                    (n.properties?.dependencies || []).forEach((d) =>
                        edges.push({ source: result.service, target: d, type: 'DEPENDS_ON' }));
                });
            }

            this.lastServiceGraph = { nodes, edges, service: result.service || serviceName };
            this.renderServiceGraph(nodes, edges);
        } catch (e) {
            console.error('Failed to load service graph:', e);
            container.innerHTML = `<p class="muted-center text-error">Failed to load service graph: ${this.escapeHtml(e.message)}</p>`;
            this.showToast('Failed to load service graph: ' + e.message, 'error');
        }
    }

    renderServiceGraph(nodes, edges) {
        if (!edges.length) {
            document.getElementById('serviceGraphViz').innerHTML =
                `<p class="muted-center">No relationships found for this service.</p>`;
            return;
        }
        this.renderGraphViz(edges, 'serviceGraphViz', {
            interactive: true,
            nodeTypeOf: (id) => {
                const n = (this.lastServiceGraph?.nodes || []).find((x) => x.id === id);
                return n ? n.type : 'Service';
            },
        });
        document.getElementById('serviceGraphViz').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
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
        document.getElementById('embedStatus').innerHTML =
            `${dot(emb.provider === 'sentence-transformers')} ${emb.provider === 'sentence-transformers' ? 'Local · offline' : 'API'}`;
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
    app = new RAGApp();
});
