/**
 * Terminal Store for State Management
 * 
 * Manages terminal state including event buffering, filtering,
 * pause/resume functionality, and scrollback limits.
 */

import EventFormatter from '../services/event-formatter.js';

class TerminalStore {
    constructor() {
        this.formatter = new EventFormatter();
        
        // Terminal state
        this.state = {
            // Event buffer
            events: [],
            filteredEvents: [],
            
            // Display settings
            maxBufferSize: 1000,
            autoScroll: true,
            isPaused: false,
            showTimestamps: true,
            showIcons: true,
            
            // Filtering
            filters: {
                eventTypes: new Set(), // Empty = show all
                categories: new Set(), // Empty = show all
                searchQuery: '',
                ipFilter: '',
                protocolFilter: '',
                switchFilter: '',
                timeRange: null // { start, end }
            },
            
            // Statistics
            stats: {
                totalEvents: 0,
                eventsByType: {},
                eventsByCategory: {},
                filteredCount: 0,
                pausedEvents: 0
            },
            
            // UI state
            selectedEvent: null,
            highlightedEvents: new Set(),
            
            // Export state
            exportFormat: 'json',
            exportFilename: ''
        };
        
        // Paused events buffer (events received while paused)
        this.pausedBuffer = [];
        
        // Event listeners
        this.listeners = new Map();
        
        // Performance optimization
        this.filterDebounceTimeout = null;
        this.updateDebounceTimeout = null;
    }

    /**
     * Add new event to the terminal
     */
    addEvent(rawEvent) {
        const formattedEvent = this.formatter.formatEvent(rawEvent);
        
        // Update statistics
        this.updateStats(formattedEvent);
        
        if (this.state.isPaused) {
            // Store in paused buffer
            this.pausedBuffer.push(formattedEvent);
            this.state.stats.pausedEvents++;
            this.emit('pausedEventAdded', formattedEvent);
        } else {
            // Add to main buffer
            this.addToBuffer(formattedEvent);
        }
    }

    /**
     * Add event to main buffer
     */
    addToBuffer(event) {
        // Add to events array
        this.state.events.push(event);
        
        // Maintain buffer size limit
        if (this.state.events.length > this.state.maxBufferSize) {
            const removed = this.state.events.shift();
            this.emit('eventRemoved', removed);
        }
        
        // Update filtered events
        this.updateFilteredEvents();
        
        // Emit events
        this.emit('eventAdded', event);
        this.emit('eventsUpdated', this.state.filteredEvents);
    }

    /**
     * Update statistics
     */
    updateStats(event) {
        this.state.stats.totalEvents++;
        
        // Count by event type
        const eventType = event.eventType;
        if (!this.state.stats.eventsByType[eventType]) {
            this.state.stats.eventsByType[eventType] = 0;
        }
        this.state.stats.eventsByType[eventType]++;
        
        // Count by category
        const category = event.category;
        if (!this.state.stats.eventsByCategory[category]) {
            this.state.stats.eventsByCategory[category] = 0;
        }
        this.state.stats.eventsByCategory[category]++;
        
        this.emit('statsUpdated', this.state.stats);
    }

    /**
     * Update filtered events based on current filters
     */
    updateFilteredEvents() {
        // Debounce filter updates for performance
        if (this.filterDebounceTimeout) {
            clearTimeout(this.filterDebounceTimeout);
        }
        
        this.filterDebounceTimeout = setTimeout(() => {
            this.applyFilters();
        }, 100);
    }

    /**
     * Apply filters to events
     */
    applyFilters() {
        const { filters } = this.state;
        
        this.state.filteredEvents = this.state.events.filter(event => {
            // Event type filter
            if (filters.eventTypes.size > 0 && !filters.eventTypes.has(event.eventType)) {
                return false;
            }
            
            // Category filter
            if (filters.categories.size > 0 && !filters.categories.has(event.category)) {
                return false;
            }
            
            // Search query filter
            if (filters.searchQuery && !event.searchText.includes(filters.searchQuery.toLowerCase())) {
                return false;
            }
            
            // IP filter
            if (filters.ipFilter) {
                const ipFilter = filters.ipFilter.toLowerCase();
                const hasIP = event.details.src_ip?.toLowerCase().includes(ipFilter) ||
                             event.details.dst_ip?.toLowerCase().includes(ipFilter);
                if (!hasIP) return false;
            }
            
            // Protocol filter
            if (filters.protocolFilter) {
                const protocolFilter = filters.protocolFilter.toLowerCase();
                const hasProtocol = event.details.protocol?.toLowerCase().includes(protocolFilter);
                if (!hasProtocol) return false;
            }
            
            // Switch filter
            if (filters.switchFilter) {
                const switchFilter = filters.switchFilter.toLowerCase();
                const hasSwitch = event.details.switch_id?.toLowerCase().includes(switchFilter);
                if (!hasSwitch) return false;
            }
            
            // Time range filter
            if (filters.timeRange) {
                const eventTime = new Date(event.timestampRaw);
                if (eventTime < filters.timeRange.start || eventTime > filters.timeRange.end) {
                    return false;
                }
            }
            
            return true;
        });
        
        this.state.stats.filteredCount = this.state.filteredEvents.length;
        
        this.emit('filtersApplied', {
            total: this.state.events.length,
            filtered: this.state.filteredEvents.length
        });
        
        this.emit('eventsUpdated', this.state.filteredEvents);
    }

    /**
     * Set filter value
     */
    setFilter(filterType, value) {
        switch (filterType) {
            case 'eventTypes':
                this.state.filters.eventTypes = new Set(value);
                break;
            case 'categories':
                this.state.filters.categories = new Set(value);
                break;
            case 'searchQuery':
                this.state.filters.searchQuery = value;
                break;
            case 'ipFilter':
                this.state.filters.ipFilter = value;
                break;
            case 'protocolFilter':
                this.state.filters.protocolFilter = value;
                break;
            case 'switchFilter':
                this.state.filters.switchFilter = value;
                break;
            case 'timeRange':
                this.state.filters.timeRange = value;
                break;
        }
        
        this.updateFilteredEvents();
        this.emit('filterChanged', { type: filterType, value });
    }

    /**
     * Clear all filters
     */
    clearFilters() {
        this.state.filters = {
            eventTypes: new Set(),
            categories: new Set(),
            searchQuery: '',
            ipFilter: '',
            protocolFilter: '',
            switchFilter: '',
            timeRange: null
        };
        
        this.updateFilteredEvents();
        this.emit('filtersCleared');
    }

    /**
     * Pause event streaming
     */
    pause() {
        this.state.isPaused = true;
        this.emit('paused', true);
    }

    /**
     * Resume event streaming
     */
    resume() {
        this.state.isPaused = false;
        
        // Process paused events
        if (this.pausedBuffer.length > 0) {
            const pausedEvents = [...this.pausedBuffer];
            this.pausedBuffer = [];
            this.state.stats.pausedEvents = 0;
            
            // Add paused events to buffer
            pausedEvents.forEach(event => {
                this.addToBuffer(event);
            });
            
            this.emit('pausedEventsProcessed', pausedEvents.length);
        }
        
        this.emit('paused', false);
    }

    /**
     * Toggle pause state
     */
    togglePause() {
        if (this.state.isPaused) {
            this.resume();
        } else {
            this.pause();
        }
    }

    /**
     * Clear all events
     */
    clearEvents() {
        this.state.events = [];
        this.state.filteredEvents = [];
        this.pausedBuffer = [];
        this.state.selectedEvent = null;
        this.state.highlightedEvents.clear();
        
        // Reset stats but keep totals
        this.state.stats.filteredCount = 0;
        this.state.stats.pausedEvents = 0;
        
        this.emit('eventsCleared');
        this.emit('eventsUpdated', []);
    }

    /**
     * Set buffer size limit
     */
    setBufferSize(size) {
        this.state.maxBufferSize = Math.max(100, Math.min(10000, size));
        
        // Trim current buffer if needed
        if (this.state.events.length > this.state.maxBufferSize) {
            const removed = this.state.events.splice(0, this.state.events.length - this.state.maxBufferSize);
            removed.forEach(event => this.emit('eventRemoved', event));
            this.updateFilteredEvents();
        }
        
        this.emit('bufferSizeChanged', this.state.maxBufferSize);
    }

    /**
     * Set auto-scroll
     */
    setAutoScroll(enabled) {
        this.state.autoScroll = enabled;
        this.emit('autoScrollChanged', enabled);
    }

    /**
     * Select event
     */
    selectEvent(eventId) {
        const event = this.state.events.find(e => e.id === eventId) ||
                     this.state.filteredEvents.find(e => e.id === eventId);
        
        this.state.selectedEvent = event;
        this.emit('eventSelected', event);
    }

    /**
     * Highlight events
     */
    highlightEvents(eventIds) {
        this.state.highlightedEvents = new Set(eventIds);
        this.emit('eventsHighlighted', eventIds);
    }

    /**
     * Get events for export
     */
    getEventsForExport(useFiltered = true) {
        const events = useFiltered ? this.state.filteredEvents : this.state.events;
        return events.map(event => this.formatter.formatForExport(event, this.state.exportFormat));
    }

    /**
     * Export events
     */
    exportEvents(format = 'json', filename = null, useFiltered = true) {
        this.state.exportFormat = format;
        
        const events = useFiltered ? this.state.filteredEvents : this.state.events;
        const timestamp = new Date().toISOString().split('T')[0];
        
        if (!filename) {
            filename = `terminal-events-${timestamp}.${format}`;
        }
        
        let content = '';
        
        switch (format) {
            case 'json':
                content = JSON.stringify(events.map(e => e.raw), null, 2);
                break;
            case 'csv':
                const header = this.formatter.getCSVHeader();
                const rows = events.map(e => this.formatter.formatForCSV(e));
                content = [header, ...rows].join('\n');
                break;
            case 'log':
                content = events.map(e => this.formatter.formatForLog(e)).join('\n');
                break;
        }
        
        // Create and download file
        const blob = new Blob([content], { 
            type: format === 'json' ? 'application/json' : 'text/plain' 
        });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        
        URL.revokeObjectURL(url);
        
        this.emit('eventsExported', { format, filename, count: events.length });
    }

    /**
     * Get available event types
     */
    getAvailableEventTypes() {
        const types = new Set();
        this.state.events.forEach(event => types.add(event.eventType));
        return Array.from(types).sort();
    }

    /**
     * Get available categories
     */
    getAvailableCategories() {
        const categories = new Set();
        this.state.events.forEach(event => categories.add(event.category));
        return Array.from(categories).sort();
    }

    /**
     * Subscribe to events
     */
    on(event, handler) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(handler);
        
        // Return unsubscribe function
        return () => this.off(event, handler);
    }

    /**
     * Unsubscribe from events
     */
    off(event, handler) {
        if (this.listeners.has(event)) {
            const handlers = this.listeners.get(event);
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
            }
        }
    }

    /**
     * Emit event
     */
    emit(event, data) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in terminal store event handler for ${event}:`, error);
                }
            });
        }
    }

    /**
     * Get current state
     */
    getState() {
        return {
            ...this.state,
            availableEventTypes: this.getAvailableEventTypes(),
            availableCategories: this.getAvailableCategories()
        };
    }
}

export default TerminalStore;
