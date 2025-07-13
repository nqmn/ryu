/**
 * Terminal Panel Component
 * 
 * Interactive terminal component that displays real-time network events
 * with filtering, search, and export capabilities.
 */

import WebSocketService from '../services/websocket-service.js';
import TerminalStore from '../state/terminal-store.js';

class TerminalPanel {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            autoConnect: true,
            showHeader: true,
            showFilters: true,
            showStats: true,
            maxHeight: '400px',
            ...options
        };
        
        // Services
        this.wsService = new WebSocketService();
        this.store = new TerminalStore();
        
        // DOM elements
        this.elements = {};
        
        // State
        this.isVisible = true;
        this.isResizing = false;
        this.lastScrollTop = 0;
        
        // Initialize
        this.initialize();
    }

    /**
     * Initialize the terminal panel
     */
    initialize() {
        this.createHTML();
        this.bindElements();
        this.setupEventHandlers();
        this.setupStoreSubscriptions();
        this.setupWebSocketSubscriptions();
        
        if (this.options.autoConnect) {
            this.connect();
        }
        
        console.log('Terminal panel initialized');
    }

    /**
     * Create HTML structure
     */
    createHTML() {
        this.container.innerHTML = `
            <div class="terminal-panel" id="terminalPanel">
                ${this.options.showHeader ? this.createHeaderHTML() : ''}
                ${this.options.showFilters ? this.createFiltersHTML() : ''}
                <div class="terminal-content">
                    <div class="terminal-output" id="terminalOutput">
                        <div class="terminal-welcome">
                            <div class="terminal-welcome-icon">🖥️</div>
                            <div class="terminal-welcome-text">
                                <h3>SDN Network Events Terminal</h3>
                                <p>Real-time network events will appear here</p>
                                <div class="terminal-status" id="terminalStatus">
                                    <span class="status-indicator" id="terminalStatusIndicator"></span>
                                    <span class="status-text" id="terminalStatusText">Disconnected</span>
                                </div>
                            </div>
                        </div>
                        <div class="terminal-events" id="terminalEvents"></div>
                    </div>
                </div>
                ${this.options.showStats ? this.createStatsHTML() : ''}
                <div class="terminal-resize-handle" id="terminalResizeHandle"></div>
            </div>
        `;
    }

    /**
     * Create header HTML
     */
    createHeaderHTML() {
        return `
            <div class="terminal-header">
                <div class="terminal-title">
                    <span class="terminal-icon">🖥️</span>
                    <span>Network Events</span>
                </div>
                <div class="terminal-controls">
                    <button class="terminal-btn" id="terminalPauseBtn" title="Pause/Resume">
                        <span class="btn-icon">⏸️</span>
                    </button>
                    <button class="terminal-btn" id="terminalClearBtn" title="Clear">
                        <span class="btn-icon">🗑️</span>
                    </button>
                    <button class="terminal-btn" id="terminalExportBtn" title="Export">
                        <span class="btn-icon">💾</span>
                    </button>
                    <button class="terminal-btn" id="terminalSettingsBtn" title="Settings">
                        <span class="btn-icon">⚙️</span>
                    </button>
                    <button class="terminal-btn" id="terminalToggleBtn" title="Toggle">
                        <span class="btn-icon">📐</span>
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Create filters HTML
     */
    createFiltersHTML() {
        return `
            <div class="terminal-filters" id="terminalFilters">
                <div class="filter-group">
                    <input type="text" class="filter-input" id="terminalSearchInput" 
                           placeholder="Search events..." />
                    <button class="filter-clear" id="terminalSearchClear">×</button>
                </div>
                <div class="filter-group">
                    <select class="filter-select" id="terminalEventTypeFilter">
                        <option value="">All Event Types</option>
                    </select>
                </div>
                <div class="filter-group">
                    <select class="filter-select" id="terminalCategoryFilter">
                        <option value="">All Categories</option>
                    </select>
                </div>
                <div class="filter-group">
                    <input type="text" class="filter-input" id="terminalIpFilter" 
                           placeholder="Filter by IP..." />
                </div>
                <div class="filter-group">
                    <input type="text" class="filter-input" id="terminalProtocolFilter" 
                           placeholder="Protocol..." />
                </div>
                <button class="filter-clear-all" id="terminalClearFilters">Clear All</button>
            </div>
        `;
    }

    /**
     * Create stats HTML
     */
    createStatsHTML() {
        return `
            <div class="terminal-stats" id="terminalStats">
                <div class="stat-item">
                    <span class="stat-label">Total:</span>
                    <span class="stat-value" id="terminalTotalEvents">0</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Filtered:</span>
                    <span class="stat-value" id="terminalFilteredEvents">0</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Paused:</span>
                    <span class="stat-value" id="terminalPausedEvents">0</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Rate:</span>
                    <span class="stat-value" id="terminalEventRate">0/s</span>
                </div>
            </div>
        `;
    }

    /**
     * Bind DOM elements
     */
    bindElements() {
        this.elements = {
            panel: this.container.querySelector('#terminalPanel'),
            output: this.container.querySelector('#terminalOutput'),
            events: this.container.querySelector('#terminalEvents'),
            status: this.container.querySelector('#terminalStatus'),
            statusIndicator: this.container.querySelector('#terminalStatusIndicator'),
            statusText: this.container.querySelector('#terminalStatusText'),
            
            // Controls
            pauseBtn: this.container.querySelector('#terminalPauseBtn'),
            clearBtn: this.container.querySelector('#terminalClearBtn'),
            exportBtn: this.container.querySelector('#terminalExportBtn'),
            settingsBtn: this.container.querySelector('#terminalSettingsBtn'),
            toggleBtn: this.container.querySelector('#terminalToggleBtn'),
            
            // Filters
            filters: this.container.querySelector('#terminalFilters'),
            searchInput: this.container.querySelector('#terminalSearchInput'),
            searchClear: this.container.querySelector('#terminalSearchClear'),
            eventTypeFilter: this.container.querySelector('#terminalEventTypeFilter'),
            categoryFilter: this.container.querySelector('#terminalCategoryFilter'),
            ipFilter: this.container.querySelector('#terminalIpFilter'),
            protocolFilter: this.container.querySelector('#terminalProtocolFilter'),
            clearFilters: this.container.querySelector('#terminalClearFilters'),
            
            // Stats
            stats: this.container.querySelector('#terminalStats'),
            totalEvents: this.container.querySelector('#terminalTotalEvents'),
            filteredEvents: this.container.querySelector('#terminalFilteredEvents'),
            pausedEvents: this.container.querySelector('#terminalPausedEvents'),
            eventRate: this.container.querySelector('#terminalEventRate'),
            
            // Resize
            resizeHandle: this.container.querySelector('#terminalResizeHandle')
        };
    }

    /**
     * Setup event handlers
     */
    setupEventHandlers() {
        // Control buttons
        if (this.elements.pauseBtn) {
            this.elements.pauseBtn.addEventListener('click', () => this.togglePause());
        }
        
        if (this.elements.clearBtn) {
            this.elements.clearBtn.addEventListener('click', () => this.clearEvents());
        }
        
        if (this.elements.exportBtn) {
            this.elements.exportBtn.addEventListener('click', () => this.showExportDialog());
        }
        
        if (this.elements.settingsBtn) {
            this.elements.settingsBtn.addEventListener('click', () => this.showSettingsDialog());
        }
        
        if (this.elements.toggleBtn) {
            this.elements.toggleBtn.addEventListener('click', () => this.toggleVisibility());
        }
        
        // Filter inputs
        if (this.elements.searchInput) {
            this.elements.searchInput.addEventListener('input', (e) => {
                this.store.setFilter('searchQuery', e.target.value);
            });
        }
        
        if (this.elements.searchClear) {
            this.elements.searchClear.addEventListener('click', () => {
                this.elements.searchInput.value = '';
                this.store.setFilter('searchQuery', '');
            });
        }
        
        if (this.elements.eventTypeFilter) {
            this.elements.eventTypeFilter.addEventListener('change', (e) => {
                const value = e.target.value;
                this.store.setFilter('eventTypes', value ? [value] : []);
            });
        }
        
        if (this.elements.categoryFilter) {
            this.elements.categoryFilter.addEventListener('change', (e) => {
                const value = e.target.value;
                this.store.setFilter('categories', value ? [value] : []);
            });
        }
        
        if (this.elements.ipFilter) {
            this.elements.ipFilter.addEventListener('input', (e) => {
                this.store.setFilter('ipFilter', e.target.value);
            });
        }
        
        if (this.elements.protocolFilter) {
            this.elements.protocolFilter.addEventListener('input', (e) => {
                this.store.setFilter('protocolFilter', e.target.value);
            });
        }
        
        if (this.elements.clearFilters) {
            this.elements.clearFilters.addEventListener('click', () => {
                this.clearAllFilters();
            });
        }
        
        // Resize handling
        if (this.elements.resizeHandle) {
            this.setupResizeHandling();
        }
        
        // Auto-scroll detection
        if (this.elements.output) {
            this.elements.output.addEventListener('scroll', () => {
                this.handleScroll();
            });
        }
    }

    /**
     * Setup store subscriptions
     */
    setupStoreSubscriptions() {
        this.store.on('eventsUpdated', (events) => {
            this.renderEvents(events);
        });
        
        this.store.on('statsUpdated', (stats) => {
            this.updateStats(stats);
        });
        
        this.store.on('paused', (isPaused) => {
            this.updatePauseButton(isPaused);
        });
        
        this.store.on('eventSelected', (event) => {
            this.showEventDetails(event);
        });
        
        this.store.on('filtersApplied', (result) => {
            this.updateFilterStats(result);
        });
    }

    /**
     * Setup WebSocket subscriptions
     */
    setupWebSocketSubscriptions() {
        this.wsService.on('connection', (data) => {
            this.updateConnectionStatus(data.status);
        });
        
        this.wsService.on('event', (event) => {
            this.store.addEvent(event);
        });
        
        // Handle specific event types for better UX
        this.wsService.on('packet_in', (event) => {
            this.store.addEvent({ ...event, event: 'packet_in' });
        });
        
        this.wsService.on('flow_mod', (event) => {
            this.store.addEvent({ ...event, event: 'flow_mod' });
        });
        
        this.wsService.on('alert', (event) => {
            this.store.addEvent({ ...event, event: 'alert' });
        });
        
        this.wsService.on('error', (event) => {
            this.store.addEvent({ ...event, event: 'error' });
        });
    }

    /**
     * Connect to WebSocket
     */
    connect() {
        this.wsService.connect();
    }

    /**
     * Disconnect from WebSocket
     */
    disconnect() {
        this.wsService.disconnect();
    }

    /**
     * Render events in terminal
     */
    renderEvents(events) {
        if (!this.elements.events) return;
        
        // Clear existing events
        this.elements.events.innerHTML = '';
        
        // Render each event
        events.forEach(event => {
            const eventElement = this.createEventElement(event);
            this.elements.events.appendChild(eventElement);
        });
        
        // Auto-scroll if enabled
        if (this.store.state.autoScroll) {
            this.scrollToBottom();
        }
        
        // Update filter dropdowns
        this.updateFilterDropdowns();
    }

    /**
     * Create event element
     */
    createEventElement(event) {
        const div = document.createElement('div');
        div.className = `terminal-event event-${event.color}`;
        div.dataset.eventId = event.id;
        div.dataset.eventType = event.eventType;
        div.dataset.category = event.category;
        
        div.innerHTML = `
            <div class="event-line">
                <span class="event-timestamp">${event.timestamp.time}</span>
                <span class="event-icon">${event.icon}</span>
                <span class="event-type">${event.eventType}</span>
                <span class="event-message">${event.message}</span>
            </div>
        `;
        
        // Add click handler for details
        div.addEventListener('click', () => {
            this.store.selectEvent(event.id);
        });
        
        return div;
    }

    /**
     * Update connection status
     */
    updateConnectionStatus(status) {
        if (!this.elements.statusIndicator || !this.elements.statusText) return;
        
        this.elements.statusIndicator.className = `status-indicator ${status}`;
        
        const statusTexts = {
            connected: 'Connected',
            disconnected: 'Disconnected',
            connecting: 'Connecting...',
            reconnecting: 'Reconnecting...',
            error: 'Connection Error',
            failed: 'Connection Failed'
        };
        
        this.elements.statusText.textContent = statusTexts[status] || status;
    }

    /**
     * Update statistics display
     */
    updateStats(stats) {
        if (this.elements.totalEvents) {
            this.elements.totalEvents.textContent = stats.totalEvents;
        }
        
        if (this.elements.pausedEvents) {
            this.elements.pausedEvents.textContent = stats.pausedEvents;
        }
        
        // Calculate event rate (events per second)
        this.updateEventRate();
    }

    /**
     * Update event rate calculation
     */
    updateEventRate() {
        // Simple rate calculation based on recent events
        const now = Date.now();
        const recentEvents = this.store.state.events.filter(event => {
            const eventTime = new Date(event.timestampRaw).getTime();
            return now - eventTime < 10000; // Last 10 seconds
        });
        
        const rate = Math.round(recentEvents.length / 10);
        
        if (this.elements.eventRate) {
            this.elements.eventRate.textContent = `${rate}/s`;
        }
    }

    /**
     * Update filter statistics
     */
    updateFilterStats(result) {
        if (this.elements.filteredEvents) {
            this.elements.filteredEvents.textContent = result.filtered;
        }
    }

    /**
     * Update filter dropdowns
     */
    updateFilterDropdowns() {
        // Update event type filter
        if (this.elements.eventTypeFilter) {
            const currentValue = this.elements.eventTypeFilter.value;
            const eventTypes = this.store.getAvailableEventTypes();

            this.elements.eventTypeFilter.innerHTML = '<option value="">All Event Types</option>';
            eventTypes.forEach(type => {
                const option = document.createElement('option');
                option.value = type;
                option.textContent = type;
                if (type === currentValue) option.selected = true;
                this.elements.eventTypeFilter.appendChild(option);
            });
        }

        // Update category filter
        if (this.elements.categoryFilter) {
            const currentValue = this.elements.categoryFilter.value;
            const categories = this.store.getAvailableCategories();

            this.elements.categoryFilter.innerHTML = '<option value="">All Categories</option>';
            categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category;
                option.textContent = category.charAt(0).toUpperCase() + category.slice(1);
                if (category === currentValue) option.selected = true;
                this.elements.categoryFilter.appendChild(option);
            });
        }
    }

    /**
     * Get terminal panel element
     */
    getElement() {
        return this.elements.panel;
    }

    /**
     * Get WebSocket service
     */
    getWebSocketService() {
        return this.wsService;
    }

    /**
     * Get terminal store
     */
    getStore() {
        return this.store;
    }

    /**
     * Toggle pause state
     */
    togglePause() {
        this.store.togglePause();
    }

    /**
     * Update pause button
     */
    updatePauseButton(isPaused) {
        if (this.elements.pauseBtn) {
            const icon = this.elements.pauseBtn.querySelector('.btn-icon');
            if (icon) {
                icon.textContent = isPaused ? '▶️' : '⏸️';
            }
            this.elements.pauseBtn.title = isPaused ? 'Resume' : 'Pause';
        }
    }

    /**
     * Clear all events
     */
    clearEvents() {
        if (confirm('Clear all events from the terminal?')) {
            this.store.clearEvents();
        }
    }

    /**
     * Clear all filters
     */
    clearAllFilters() {
        this.store.clearFilters();
        
        // Reset filter inputs
        if (this.elements.searchInput) this.elements.searchInput.value = '';
        if (this.elements.eventTypeFilter) this.elements.eventTypeFilter.value = '';
        if (this.elements.categoryFilter) this.elements.categoryFilter.value = '';
        if (this.elements.ipFilter) this.elements.ipFilter.value = '';
        if (this.elements.protocolFilter) this.elements.protocolFilter.value = '';
    }

    /**
     * Show export dialog
     */
    showExportDialog() {
        const format = prompt('Export format (json, csv, log):', 'json');
        if (format && ['json', 'csv', 'log'].includes(format)) {
            this.store.exportEvents(format);
        }
    }

    /**
     * Show settings dialog
     */
    showSettingsDialog() {
        const bufferSize = prompt('Buffer size (100-10000):', this.store.state.maxBufferSize);
        if (bufferSize) {
            const size = parseInt(bufferSize);
            if (!isNaN(size)) {
                this.store.setBufferSize(size);
            }
        }
    }

    /**
     * Toggle visibility
     */
    toggleVisibility() {
        this.isVisible = !this.isVisible;
        this.elements.panel.style.display = this.isVisible ? 'flex' : 'none';
    }

    /**
     * Setup resize handling
     */
    setupResizeHandling() {
        let startY, startHeight;
        
        this.elements.resizeHandle.addEventListener('mousedown', (e) => {
            startY = e.clientY;
            startHeight = parseInt(document.defaultView.getComputedStyle(this.elements.panel).height, 10);
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
            this.isResizing = true;
        });
        
        const handleMouseMove = (e) => {
            const newHeight = startHeight + (startY - e.clientY);
            this.elements.panel.style.height = Math.max(200, Math.min(800, newHeight)) + 'px';
        };
        
        const handleMouseUp = () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
            this.isResizing = false;
        };
    }

    /**
     * Handle scroll events
     */
    handleScroll() {
        if (this.isResizing) return;
        
        const { scrollTop, scrollHeight, clientHeight } = this.elements.output;
        const isAtBottom = scrollTop + clientHeight >= scrollHeight - 10;
        
        // Update auto-scroll based on user scroll position
        this.store.setAutoScroll(isAtBottom);
        this.lastScrollTop = scrollTop;
    }

    /**
     * Scroll to bottom
     */
    scrollToBottom() {
        if (this.elements.output) {
            this.elements.output.scrollTop = this.elements.output.scrollHeight;
        }
    }

    /**
     * Show event details
     */
    showEventDetails(event) {
        if (!event) return;
        
        // Create or update detail popup
        this.showEventDetailPopup(event);
    }

    /**
     * Show event detail popup
     */
    showEventDetailPopup(event) {
        // Remove existing popup
        const existingPopup = document.querySelector('.terminal-event-popup');
        if (existingPopup) {
            existingPopup.remove();
        }
        
        // Create popup
        const popup = document.createElement('div');
        popup.className = 'terminal-event-popup';
        popup.innerHTML = `
            <div class="popup-header">
                <h3>${event.eventType} Details</h3>
                <button class="popup-close">×</button>
            </div>
            <div class="popup-content">
                <div class="detail-section">
                    <strong>Timestamp:</strong> ${event.timestamp.full}
                </div>
                <div class="detail-section">
                    <strong>Message:</strong> ${event.message}
                </div>
                <div class="detail-section">
                    <strong>Details:</strong>
                    <pre>${JSON.stringify(event.details, null, 2)}</pre>
                </div>
            </div>
        `;
        
        // Add to document
        document.body.appendChild(popup);
        
        // Add close handler
        popup.querySelector('.popup-close').addEventListener('click', () => {
            popup.remove();
        });
        
        // Close on outside click
        popup.addEventListener('click', (e) => {
            if (e.target === popup) {
                popup.remove();
            }
        });
    }

    /**
     * Destroy the terminal panel
     */
    destroy() {
        this.disconnect();
        this.container.innerHTML = '';
    }
}

export default TerminalPanel;
