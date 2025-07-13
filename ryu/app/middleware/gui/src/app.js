/**
 * Main Application
 * 
 * SDN Middleware Network Topology Dashboard
 */

import TopologyAPI from './api/topology.js';
import TopologyStore from './state/topology-store.js';
import NetworkGraph from './components/network-graph.js';
import DetailPanel from './components/detail-panel.js';
import TerminalPanel from './components/terminal-panel.js';
import TerminalGraphIntegration from './services/terminal-graph-integration.js';

class TopologyDashboard {
    constructor() {
        this.api = null;
        this.store = null;
        this.graph = null;
        this.detailPanel = null;
        this.terminal = null;
        this.terminalIntegration = null;
        this.toastContainer = null;
        
        // UI elements
        this.elements = {
            connectionStatus: document.getElementById('connectionStatus'),
            statusIndicator: document.getElementById('statusIndicator'),
            statusText: document.getElementById('statusText'),
            themeToggle: document.getElementById('themeToggle'),
            sidebarToggle: document.getElementById('sidebarToggle'),
            sidebar: document.getElementById('sidebar'),
            searchInput: document.getElementById('searchInput'),
            searchClear: document.getElementById('searchClear'),
            showSwitches: document.getElementById('showSwitches'),
            showHosts: document.getElementById('showHosts'),
            showLinks: document.getElementById('showLinks'),
            layoutSelect: document.getElementById('layoutSelect'),
            resetLayout: document.getElementById('resetLayout'),
            refreshTopology: document.getElementById('refreshTopology'),
            exportTopology: document.getElementById('exportTopology'),
            exportImage: document.getElementById('exportImage'),
            loadingSpinner: document.getElementById('loadingSpinner'),
            minimapToggle: document.getElementById('minimapToggle'),
            minimapContainer: document.getElementById('minimapContainer'),
            terminalContainer: document.getElementById('terminalContainer'),
            toastContainer: document.getElementById('toastContainer'),
            // Statistics elements
            switchCount: document.getElementById('switchCount'),
            hostCount: document.getElementById('hostCount'),
            linkCount: document.getElementById('linkCount'),
            ofSwitchCount: document.getElementById('ofSwitchCount'),
            p4SwitchCount: document.getElementById('p4SwitchCount'),
            totalHostCount: document.getElementById('totalHostCount'),
            activeLinkCount: document.getElementById('activeLinkCount')
        };
        
        this.initialize();
    }

    /**
     * Initialize the application
     */
    async initialize() {
        try {
            console.log('Initializing SDN Topology Dashboard...');
            
            // Initialize components
            this.api = new TopologyAPI();
            this.store = new TopologyStore();
            
            // Initialize graph
            const graphContainer = document.getElementById('cy');
            this.graph = new NetworkGraph(graphContainer, this.store);
            
            // Initialize detail panel
            this.detailPanel = new DetailPanel(this.store, this.api);

            // Initialize terminal panel
            this.terminal = new TerminalPanel(this.elements.terminalContainer, {
                autoConnect: false, // We'll connect manually after API is ready
                showHeader: true,
                showFilters: true,
                showStats: true
            });

            // Set up UI event handlers
            this.setupUIHandlers();
            
            // Set up store subscriptions
            this.setupStoreSubscriptions();
            
            // Initialize API and load data
            await this.initializeAPI();
            
            // Apply initial theme
            this.applyTheme();

            // Update layout dropdown with available layouts
            this.updateLayoutDropdown();

            console.log('Dashboard initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize dashboard:', error);
            this.showToast('error', 'Initialization Failed', error.message);
        }
    }

    /**
     * Initialize API and load initial data
     */
    async initializeAPI() {
        try {
            this.showLoading(true);
            
            // Initialize API connection
            await this.api.initialize();
            
            // Set up API event handlers
            this.setupAPIHandlers();
            
            // Load initial topology
            await this.loadTopology();

            // Connect terminal to WebSocket
            this.terminal.connect();

            // Initialize terminal-graph integration
            this.terminalIntegration = new TerminalGraphIntegration(
                this.terminal,
                this.graph,
                this.store
            );

            // Add custom styles for terminal integration
            this.terminalIntegration.addCustomStyles();

            // Show terminal container
            this.showTerminal(true);

            this.showLoading(false);
            
        } catch (error) {
            this.showLoading(false);
            throw error;
        }
    }

    /**
     * Set up API event handlers
     */
    setupAPIHandlers() {
        // Connection status events
        this.api.on('connection', (data) => {
            this.updateConnectionStatus(data.status);
            this.store.setConnectionStatus(data.status);
        });
        
        // Topology events
        this.api.on('switch_enter', (data) => {
            this.store.handleTopologyEvent('switch_enter', data);
            this.showToast('info', 'Switch Connected', `Switch ${data.dpid} connected`);
        });
        
        this.api.on('switch_leave', (data) => {
            this.store.handleTopologyEvent('switch_leave', data);
            this.showToast('warning', 'Switch Disconnected', `Switch ${data.dpid} disconnected`);
        });
        
        this.api.on('event_switch_enter', (data) => {
            this.store.handleTopologyEvent('switch_enter', data);
            this.showToast('info', 'Switch Connected', `Switch ${data.dpid} connected`);
        });
        
        this.api.on('event_switch_leave', (data) => {
            this.store.handleTopologyEvent('switch_leave', data);
            this.showToast('warning', 'Switch Disconnected', `Switch ${data.dpid} disconnected`);
        });
        
        this.api.on('link_add', (data) => {
            this.store.handleTopologyEvent('link_add', data);
            this.showToast('success', 'Link Added', 'New network link discovered');
        });
        
        this.api.on('link_delete', (data) => {
            this.store.handleTopologyEvent('link_delete', data);
            this.showToast('warning', 'Link Removed', 'Network link removed');
        });
        
        this.api.on('event_link_add', (data) => {
            this.store.handleTopologyEvent('link_add', data);
            this.showToast('success', 'Link Added', 'New network link discovered');
        });
        
        this.api.on('event_link_delete', (data) => {
            this.store.handleTopologyEvent('link_delete', data);
            this.showToast('warning', 'Link Removed', 'Network link removed');
        });
        
        this.api.on('host_add', (data) => {
            this.store.handleTopologyEvent('host_add', data);
            this.showToast('info', 'Host Discovered', `Host ${data.mac} discovered`);
        });
    }

    /**
     * Set up store subscriptions
     */
    setupStoreSubscriptions() {
        // Update statistics when topology changes
        this.store.subscribe('stats', (stats) => {
            this.updateStatistics(stats);
        });
        
        // Update filter counts
        this.store.subscribe('switches', () => {
            const topology = this.store.getFilteredTopology();
            this.elements.switchCount.textContent = topology.switches.length;
        });
        
        this.store.subscribe('hosts', () => {
            const topology = this.store.getFilteredTopology();
            this.elements.hostCount.textContent = topology.hosts.length;
        });
        
        this.store.subscribe('links', () => {
            const topology = this.store.getFilteredTopology();
            this.elements.linkCount.textContent = topology.links.length;
        });
    }

    /**
     * Set up UI event handlers
     */
    setupUIHandlers() {
        // Theme toggle
        this.elements.themeToggle.addEventListener('click', () => {
            this.toggleTheme();
        });
        
        // Sidebar toggle
        this.elements.sidebarToggle.addEventListener('click', () => {
            this.toggleSidebar();
        });
        
        // Search functionality
        this.elements.searchInput.addEventListener('input', (event) => {
            this.handleSearch(event.target.value);
        });
        
        this.elements.searchClear.addEventListener('click', () => {
            this.elements.searchInput.value = '';
            this.handleSearch('');
        });
        
        // Filter checkboxes
        this.elements.showSwitches.addEventListener('change', () => {
            this.updateFilters();
        });
        
        this.elements.showHosts.addEventListener('change', () => {
            this.updateFilters();
        });
        
        this.elements.showLinks.addEventListener('change', () => {
            this.updateFilters();
        });
        
        // Layout controls
        this.elements.layoutSelect.addEventListener('change', (event) => {
            this.graph.applyLayout(event.target.value);
        });
        
        this.elements.resetLayout.addEventListener('click', () => {
            this.graph.resetLayout();
        });
        
        // Action buttons
        this.elements.refreshTopology.addEventListener('click', () => {
            this.loadTopology();
        });
        
        this.elements.exportTopology.addEventListener('click', () => {
            this.exportTopology();
        });
        
        this.elements.exportImage.addEventListener('click', () => {
            this.exportImage();
        });
        
        // Minimap toggle
        this.elements.minimapToggle.addEventListener('click', () => {
            this.toggleMinimap();
        });

        // Add terminal toggle button to header
        this.addTerminalToggleButton();
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (event) => {
            this.handleKeyboardShortcuts(event);
        });
        
        // Window resize
        window.addEventListener('resize', () => {
            if (this.graph) {
                this.graph.cy.resize();
            }
        });
    }

    /**
     * Load topology data
     */
    async loadTopology() {
        try {
            this.showLoading(true);
            this.showToast('info', 'Loading Topology', 'Fetching network topology...');
            
            const topologyData = await this.api.getTopology();
            this.store.loadTopology(topologyData);
            
            this.showToast('success', 'Topology Loaded', 'Network topology updated successfully');
            
        } catch (error) {
            console.error('Failed to load topology:', error);
            this.showToast('error', 'Load Failed', error.message);
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * Handle search input
     */
    handleSearch(query) {
        this.store.updateFilters({ searchQuery: query });
    }

    /**
     * Update filters based on UI state
     */
    updateFilters() {
        const filters = {
            showSwitches: this.elements.showSwitches.checked,
            showHosts: this.elements.showHosts.checked,
            showLinks: this.elements.showLinks.checked
        };
        
        this.store.updateFilters(filters);
    }

    /**
     * Update connection status display
     */
    updateConnectionStatus(status) {
        this.elements.statusIndicator.className = `status-indicator ${status}`;
        
        const statusText = {
            'connected': 'Connected',
            'disconnected': 'Disconnected',
            'connecting': 'Connecting...',
            'error': 'Connection Error',
            'failed': 'Connection Failed'
        };
        
        this.elements.statusText.textContent = statusText[status] || status;
    }

    /**
     * Update statistics display
     */
    updateStatistics(stats) {
        this.elements.ofSwitchCount.textContent = stats.openflow_switches;
        this.elements.p4SwitchCount.textContent = stats.p4runtime_switches;
        this.elements.totalHostCount.textContent = stats.total_hosts;
        this.elements.activeLinkCount.textContent = stats.active_links;
    }

    /**
     * Toggle theme
     */
    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        // Update theme toggle icon
        const icon = this.elements.themeToggle.querySelector('.theme-icon');
        icon.textContent = newTheme === 'dark' ? '☀️' : '🌙';
    }

    /**
     * Apply theme from localStorage
     */
    applyTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        
        const icon = this.elements.themeToggle.querySelector('.theme-icon');
        icon.textContent = savedTheme === 'dark' ? '☀️' : '🌙';
    }

    /**
     * Toggle sidebar
     */
    toggleSidebar() {
        this.elements.sidebar.classList.toggle('collapsed');
        
        const toggleIcon = this.elements.sidebarToggle.querySelector('span');
        const isCollapsed = this.elements.sidebar.classList.contains('collapsed');
        toggleIcon.textContent = isCollapsed ? '→' : '←';
    }

    /**
     * Toggle minimap
     */
    toggleMinimap() {
        this.elements.minimapContainer.classList.toggle('hidden');
    }

    /**
     * Handle keyboard shortcuts
     */
    handleKeyboardShortcuts(event) {
        // Ctrl/Cmd + R: Refresh topology
        if ((event.ctrlKey || event.metaKey) && event.key === 'r') {
            event.preventDefault();
            this.loadTopology();
        }
        
        // Ctrl/Cmd + F: Focus search
        if ((event.ctrlKey || event.metaKey) && event.key === 'f') {
            event.preventDefault();
            this.elements.searchInput.focus();
        }
        
        // Ctrl/Cmd + D: Toggle theme
        if ((event.ctrlKey || event.metaKey) && event.key === 'd') {
            event.preventDefault();
            this.toggleTheme();
        }

        // Ctrl/Cmd + T: Toggle terminal
        if ((event.ctrlKey || event.metaKey) && event.key === 't') {
            event.preventDefault();
            this.toggleTerminal();
        }
    }

    /**
     * Export topology as JSON
     */
    exportTopology() {
        const topology = this.store.getState();
        const data = {
            switches: Array.from(topology.switches.values()),
            hosts: Array.from(topology.hosts.values()),
            links: Array.from(topology.links.values()),
            timestamp: new Date().toISOString()
        };
        
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `topology-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        
        URL.revokeObjectURL(url);
        this.showToast('success', 'Export Complete', 'Topology exported as JSON');
    }

    /**
     * Export graph as image
     */
    async exportImage() {
        try {
            const blob = await this.graph.exportImage();
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = `topology-${new Date().toISOString().split('T')[0]}.png`;
            a.click();
            
            URL.revokeObjectURL(url);
            this.showToast('success', 'Export Complete', 'Topology exported as PNG');
            
        } catch (error) {
            console.error('Failed to export image:', error);
            this.showToast('error', 'Export Failed', error.message);
        }
    }

    /**
     * Show/hide loading spinner
     */
    showLoading(show) {
        if (show) {
            this.elements.loadingSpinner.classList.remove('hidden');
        } else {
            this.elements.loadingSpinner.classList.add('hidden');
        }
    }

    /**
     * Show toast notification
     */
    showToast(type, title, message, duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        
        toast.innerHTML = `
            <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
            <div class="toast-content">
                <div class="toast-title">${title}</div>
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close">×</button>
        `;
        
        // Add close handler
        const closeButton = toast.querySelector('.toast-close');
        closeButton.addEventListener('click', () => {
            this.removeToast(toast);
        });
        
        // Add to container
        this.elements.toastContainer.appendChild(toast);
        
        // Auto-remove after duration
        setTimeout(() => {
            this.removeToast(toast);
        }, duration);
    }

    /**
     * Remove toast notification
     */
    removeToast(toast) {
        if (toast.parentNode) {
            toast.style.animation = 'slideOut 0.3s ease-in forwards';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }
    }

    /**
     * Add terminal toggle button to header
     */
    addTerminalToggleButton() {
        const headerRight = document.querySelector('.header-right');
        if (headerRight) {
            const terminalToggle = document.createElement('button');
            terminalToggle.className = 'theme-toggle';
            terminalToggle.id = 'terminalToggleBtn';
            terminalToggle.title = 'Toggle Terminal (Ctrl+T)';
            terminalToggle.innerHTML = '<span class="theme-icon">🖥️</span>';

            terminalToggle.addEventListener('click', () => {
                this.toggleTerminal();
            });

            // Insert before theme toggle
            const themeToggle = document.getElementById('themeToggle');
            headerRight.insertBefore(terminalToggle, themeToggle);
        }
    }

    /**
     * Show/hide terminal
     */
    showTerminal(show) {
        const contentArea = document.querySelector('.content-area');
        const terminalContainer = this.elements.terminalContainer;

        if (show) {
            terminalContainer.classList.remove('hidden');
            contentArea.classList.add('terminal-open');
        } else {
            terminalContainer.classList.add('hidden');
            contentArea.classList.remove('terminal-open');
        }

        // Resize graph after layout change
        if (this.graph && this.graph.cy) {
            setTimeout(() => {
                this.graph.cy.resize();
            }, 300);
        }
    }

    /**
     * Toggle terminal visibility
     */
    toggleTerminal() {
        const terminalContainer = this.elements.terminalContainer;
        const isHidden = terminalContainer.classList.contains('hidden');

        this.showTerminal(isHidden);

        // Update toggle button
        const toggleBtn = document.getElementById('terminalToggleBtn');
        if (toggleBtn) {
            const icon = toggleBtn.querySelector('.theme-icon');
            icon.textContent = isHidden ? '🖥️' : '📐';
            toggleBtn.title = isHidden ? 'Hide Terminal (Ctrl+T)' : 'Show Terminal (Ctrl+T)';
        }
    }

    /**
     * Update layout dropdown with available layouts
     */
    updateLayoutDropdown() {
        const layoutSelect = this.elements.layoutSelect;
        if (!layoutSelect || !this.graph) return;

        // Clear existing options
        layoutSelect.innerHTML = '';

        // Available built-in layouts
        const layouts = [
            { value: 'grid', label: 'Grid' },
            { value: 'circle', label: 'Circle' },
            { value: 'breadthfirst', label: 'Hierarchical' },
            { value: 'cose', label: 'Force-directed' }
        ];

        layouts.forEach(layout => {
            const option = document.createElement('option');
            option.value = layout.value;
            option.textContent = layout.label;
            layoutSelect.appendChild(option);
        });

        // Set default selection to grid
        layoutSelect.value = 'grid';
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize the dashboard directly
    window.topologyDashboard = new TopologyDashboard();
});

// Add slideOut animation to CSS
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
