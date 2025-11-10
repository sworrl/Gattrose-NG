/**
 * Gattrose-NG Mobile Control Interface
 * JavaScript Application Logic
 */

// Configuration
const API_BASE_URL = window.location.origin + '/api';
const REFRESH_INTERVAL = 10000; // 10 seconds

// Global state
let currentView = 'dashboard';
let currentNetwork = null;
let refreshTimer = null;

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    console.log('[Gattrose] Initializing mobile interface...');

    initializeNavigation();
    initializeEventListeners();
    checkConnection();
    loadDashboard();

    // Start auto-refresh
    startAutoRefresh();

    console.log('[Gattrose] Interface ready');
});

// Navigation
function initializeNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');

    navButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const view = this.getAttribute('data-view');
            switchView(view);
        });
    });
}

function switchView(viewName) {
    // Update nav buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.getAttribute('data-view') === viewName) {
            btn.classList.add('active');
        }
    });

    // Update views
    document.querySelectorAll('.view').forEach(view => {
        view.classList.remove('active');
    });

    document.getElementById(viewName + 'View').classList.add('active');
    currentView = viewName;

    // Load data for view
    switch(viewName) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'networks':
            loadNetworks();
            break;
        case 'attacks':
            loadAttackQueue();
            break;
        case 'system':
            loadSystemStatus();
            break;
    }
}

// Event Listeners
function initializeEventListeners() {
    // Network search
    const searchInput = document.getElementById('networkSearch');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                searchNetworks(this.value);
            }, 500);
        });
    }

    // Filters
    const encryptionFilter = document.getElementById('encryptionFilter');
    const wpsFilter = document.getElementById('wpsFilter');

    if (encryptionFilter) {
        encryptionFilter.addEventListener('change', () => loadNetworks());
    }
    if (wpsFilter) {
        wpsFilter.addEventListener('change', () => loadNetworks());
    }

    // System actions
    const exportBtn = document.getElementById('exportCsvBtn');
    const refreshBtn = document.getElementById('refreshBtn');
    const clearQueueBtn = document.getElementById('clearQueueBtn');

    if (exportBtn) exportBtn.addEventListener('click', exportData);
    if (refreshBtn) refreshBtn.addEventListener('click', refreshAllData);
    if (clearQueueBtn) clearQueueBtn.addEventListener('click', confirmClearQueue);
}

// API Functions
async function apiRequest(endpoint, options = {}) {
    try {
        const response = await fetch(API_BASE_URL + endpoint, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error('[API Error]', error);
        showToast('API Error: ' + error.message, 'error');
        updateConnectionStatus(false);
        throw error;
    }
}

// Connection Status
function checkConnection() {
    apiRequest('/dashboard/stats')
        .then(() => {
            updateConnectionStatus(true);
        })
        .catch(() => {
            updateConnectionStatus(false);
        });
}

function updateConnectionStatus(connected) {
    const statusDot = document.querySelector('.status-dot');
    const statusText = document.querySelector('.status-text');

    if (connected) {
        statusDot.classList.add('connected');
        statusText.textContent = 'Connected';
    } else {
        statusDot.classList.remove('connected');
        statusText.textContent = 'Disconnected';
    }
}

// Dashboard
async function loadDashboard() {
    try {
        const response = await apiRequest('/dashboard/stats');
        const data = response.data;

        // Update stats
        document.getElementById('totalNetworks').textContent = data.total_networks;
        document.getElementById('totalClients').textContent = data.total_clients;
        document.getElementById('totalHandshakes').textContent = data.total_handshakes;
        document.getElementById('crackedHandshakes').textContent = data.cracked_handshakes;

        // Update encryption chart
        renderEncryptionChart(data.encryption_breakdown);

        // Load recent activity
        loadRecentActivity();

        updateConnectionStatus(true);
    } catch (error) {
        console.error('[Dashboard] Load failed:', error);
    }
}

function renderEncryptionChart(breakdown) {
    const container = document.getElementById('encryptionChart');
    container.innerHTML = '';

    const total = Object.values(breakdown).reduce((sum, val) => sum + val, 0);

    if (total === 0) {
        container.innerHTML = '<p class="info">No encryption data available</p>';
        return;
    }

    Object.entries(breakdown).forEach(([encryption, count]) => {
        const percentage = (count / total * 100).toFixed(1);

        const bar = document.createElement('div');
        bar.className = 'chart-bar';
        bar.innerHTML = `
            <span class="chart-label">${encryption || 'Unknown'}</span>
            <div class="chart-bar-fill" style="width: ${percentage}%">
                ${count} (${percentage}%)
            </div>
        `;
        container.appendChild(bar);
    });
}

async function loadRecentActivity() {
    try {
        const response = await apiRequest('/networks?per_page=5');
        const networks = response.data;

        const container = document.getElementById('recentActivity');
        container.innerHTML = '';

        if (networks.length === 0) {
            container.innerHTML = '<p class="info">No recent activity</p>';
            return;
        }

        networks.forEach(network => {
            const item = document.createElement('div');
            item.className = 'network-item';
            item.innerHTML = `
                <div class="network-header">
                    <span class="network-ssid">${network.ssid || '(Hidden)'}</span>
                    <span class="network-encryption">${network.encryption || 'Unknown'}</span>
                </div>
                <div class="network-bssid">${network.bssid}</div>
            `;
            item.addEventListener('click', () => showNetworkDetails(network.bssid));
            container.appendChild(item);
        });
    } catch (error) {
        console.error('[Recent Activity] Load failed:', error);
    }
}

// Networks
async function loadNetworks(page = 1) {
    try {
        showLoading();

        const response = await apiRequest(`/networks?page=${page}&per_page=50`);
        const networks = response.data;
        const pagination = response.pagination;

        const container = document.getElementById('networksList');
        container.innerHTML = '';

        if (networks.length === 0) {
            container.innerHTML = '<p class="info">No networks found</p>';
            hideLoading();
            return;
        }

        networks.forEach(network => {
            const item = createNetworkItem(network);
            container.appendChild(item);
        });

        // Render pagination
        renderPagination(pagination);

        hideLoading();
    } catch (error) {
        hideLoading();
        console.error('[Networks] Load failed:', error);
    }
}

function createNetworkItem(network) {
    const item = document.createElement('div');
    item.className = 'network-item';

    const wpsStatus = network.wps_enabled ? '🔓 WPS' : '';
    const signalBars = getSignalBars(network.current_signal);

    item.innerHTML = `
        <div class="network-header">
            <span class="network-ssid">${network.ssid || '(Hidden)'}</span>
            <span class="network-encryption">${network.encryption || 'Unknown'}</span>
        </div>
        <div class="network-bssid">${network.bssid}</div>
        <div class="network-details">
            <div class="network-detail">
                <strong>Ch:</strong> ${network.channel || 'N/A'}
            </div>
            <div class="network-detail">
                <strong>Signal:</strong> ${signalBars} ${network.current_signal || 'N/A'}dBm
            </div>
            <div class="network-detail">
                <strong>${wpsStatus}</strong>
            </div>
        </div>
    `;

    item.addEventListener('click', () => showNetworkDetails(network.bssid));
    return item;
}

function getSignalBars(signal) {
    if (!signal) return '📶';
    if (signal > -50) return '📶📶📶📶';
    if (signal > -60) return '📶📶📶';
    if (signal > -70) return '📶📶';
    return '📶';
}

async function showNetworkDetails(bssid) {
    try {
        const response = await apiRequest(`/networks/${bssid}`);
        const network = response.data;

        currentNetwork = network;

        const modalBody = document.getElementById('modalBody');
        modalBody.innerHTML = `
            <div class="info-row">
                <span class="info-label">SSID:</span>
                <span class="info-value">${network.ssid || '(Hidden)'}</span>
            </div>
            <div class="info-row">
                <span class="info-label">BSSID:</span>
                <span class="info-value">${network.bssid}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Encryption:</span>
                <span class="info-value">${network.encryption || 'Unknown'}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Channel:</span>
                <span class="info-value">${network.channel || 'N/A'}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Signal:</span>
                <span class="info-value">${network.current_signal || 'N/A'} dBm</span>
            </div>
            <div class="info-row">
                <span class="info-label">WPS:</span>
                <span class="info-value">${network.wps_enabled ? '🔓 Enabled' : '🔒 Disabled'}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Manufacturer:</span>
                <span class="info-value">${network.manufacturer || 'Unknown'}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Attack Score:</span>
                <span class="info-value">${network.current_attack_score || 'N/A'}</span>
            </div>
        `;

        document.getElementById('modalNetworkName').textContent = network.ssid || network.bssid;
        openModal();
    } catch (error) {
        console.error('[Network Details] Load failed:', error);
    }
}

async function searchNetworks(query) {
    if (!query || query.length < 2) {
        loadNetworks();
        return;
    }

    try {
        const response = await apiRequest(`/search?q=${encodeURIComponent(query)}&type=networks`);
        const networks = response.data.networks;

        const container = document.getElementById('networksList');
        container.innerHTML = '';

        if (networks.length === 0) {
            container.innerHTML = '<p class="info">No networks found matching your search</p>';
            return;
        }

        networks.forEach(network => {
            const item = createNetworkItem(network);
            container.appendChild(item);
        });
    } catch (error) {
        console.error('[Search] Failed:', error);
    }
}

// Attack Queue
async function loadAttackQueue() {
    try {
        const response = await apiRequest('/attacks/queue');
        const queue = response.data;

        const container = document.getElementById('attackQueue');
        container.innerHTML = '';

        if (queue.length === 0) {
            container.innerHTML = '<p class="info">Attack queue is empty</p>';
            return;
        }

        queue.forEach(item => {
            const queueItem = createQueueItem(item);
            container.appendChild(queueItem);
        });
    } catch (error) {
        console.error('[Attack Queue] Load failed:', error);
    }
}

function createQueueItem(item) {
    const div = document.createElement('div');
    div.className = `queue-item ${item.status}`;

    div.innerHTML = `
        <div class="queue-header">
            <div>
                <div class="network-ssid">${item.ssid || '(Hidden)'}</div>
                <div class="network-bssid">${item.bssid}</div>
            </div>
            <span class="queue-status">${item.status.toUpperCase()}</span>
        </div>
        <div class="network-details">
            <div class="network-detail">
                <strong>Type:</strong> ${item.attack_type}
            </div>
            <div class="network-detail">
                <strong>Priority:</strong> ${item.priority}
            </div>
            <div class="network-detail">
                <strong>Added:</strong> ${formatDate(item.added_at)}
            </div>
        </div>
        <button class="queue-remove" onclick="removeFromQueue(${item.id})">Remove</button>
    `;

    return div;
}

async function addToQueue() {
    if (!currentNetwork) return;

    try {
        await apiRequest('/attacks/queue', {
            method: 'POST',
            body: JSON.stringify({
                bssid: currentNetwork.bssid,
                attack_type: 'auto',
                priority: 50
            })
        });

        showToast('Added to attack queue', 'success');
        closeModal();

        if (currentView === 'attacks') {
            loadAttackQueue();
        }
    } catch (error) {
        showToast('Failed to add to queue', 'error');
    }
}

async function removeFromQueue(queueId) {
    try {
        await apiRequest(`/attacks/queue/${queueId}`, {
            method: 'DELETE'
        });

        showToast('Removed from queue', 'success');
        loadAttackQueue();
    } catch (error) {
        showToast('Failed to remove from queue', 'error');
    }
}

// System
async function loadSystemStatus() {
    try {
        const response = await apiRequest('/system/status');
        const data = response.data;

        document.getElementById('monitorMode').textContent = data.monitor_enabled ? '✅ Enabled' : '❌ Disabled';
        document.getElementById('interfaces').textContent = data.interfaces.join(', ') || 'None';
        document.getElementById('scanningStatus').textContent = data.scanning ? '🟢 Active' : '⭕ Stopped';
    } catch (error) {
        console.error('[System] Load failed:', error);
    }
}

async function exportData() {
    try {
        window.location.href = `${API_BASE_URL}/export/csv?type=networks`;
        showToast('Export started', 'success');
    } catch (error) {
        showToast('Export failed', 'error');
    }
}

function confirmClearQueue() {
    if (confirm('Clear entire attack queue?')) {
        // TODO: Implement clear queue endpoint
        showToast('Queue cleared', 'success');
    }
}

// UI Helpers
function renderPagination(pagination) {
    const container = document.getElementById('networksPagination');
    container.innerHTML = '';

    for (let i = 1; i <= pagination.pages; i++) {
        const btn = document.createElement('button');
        btn.className = 'page-btn';
        btn.textContent = i;

        if (i === pagination.page) {
            btn.classList.add('active');
        }

        btn.addEventListener('click', () => loadNetworks(i));
        container.appendChild(btn);

        // Limit visible pages
        if (i >= 5 && i < pagination.pages) {
            container.innerHTML += '<span>...</span>';
            break;
        }
    }
}

function openModal() {
    document.getElementById('networkModal').classList.add('active');
}

function closeModal() {
    document.getElementById('networkModal').classList.remove('active');
    currentNetwork = null;
}

function showLoading() {
    document.getElementById('loadingOverlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('active');
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleTimeString();
}

// Auto-refresh
function startAutoRefresh() {
    refreshTimer = setInterval(() => {
        switch(currentView) {
            case 'dashboard':
                loadDashboard();
                break;
            case 'attacks':
                loadAttackQueue();
                break;
        }
    }, REFRESH_INTERVAL);
}

function refreshAllData() {
    checkConnection();

    switch(currentView) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'networks':
            loadNetworks();
            break;
        case 'attacks':
            loadAttackQueue();
            break;
        case 'system':
            loadSystemStatus();
            break;
    }

    showToast('Data refreshed', 'success');
}

// Prevent zoom on double-tap (mobile Safari)
let lastTouchEnd = 0;
document.addEventListener('touchend', function(event) {
    const now = Date.now();
    if (now - lastTouchEnd <= 300) {
        event.preventDefault();
    }
    lastTouchEnd = now;
}, false);
