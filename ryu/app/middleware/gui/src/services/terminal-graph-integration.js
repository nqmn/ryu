/**
 * Terminal-Graph Integration Service
 * 
 * Provides integration between terminal events and topology graph
 * for enhanced visualization and interaction.
 */

class TerminalGraphIntegration {
    constructor(terminal, graph, store) {
        this.terminal = terminal;
        this.graph = graph;
        this.store = store;
        
        // Integration state
        this.highlightedElements = new Set();
        this.eventNodeMap = new Map();
        this.highlightTimeout = null;
        
        this.initialize();
    }

    /**
     * Initialize integration
     */
    initialize() {
        this.setupTerminalEventHandlers();
        this.setupGraphEventHandlers();
        
        console.log('Terminal-Graph integration initialized');
    }

    /**
     * Setup terminal event handlers
     */
    setupTerminalEventHandlers() {
        const terminalStore = this.terminal.getStore();
        
        // Handle event selection in terminal
        terminalStore.on('eventSelected', (event) => {
            this.highlightEventInGraph(event);
        });
        
        // Handle event hover in terminal (if implemented)
        terminalStore.on('eventHovered', (event) => {
            this.previewEventInGraph(event);
        });
        
        // Handle new events for auto-highlighting
        terminalStore.on('eventAdded', (event) => {
            this.handleNewEvent(event);
        });
    }

    /**
     * Setup graph event handlers
     */
    setupGraphEventHandlers() {
        // Handle node selection in graph
        this.store.subscribe('nodeSelected', (data) => {
            if (data && data.node) {
                this.highlightRelatedEvents(data.node);
            }
        });

        // Handle link selection in graph
        this.store.subscribe('linkSelected', (data) => {
            if (data && data.link) {
                this.highlightRelatedEvents(data.link);
            }
        });

        // Clear highlights when selection is cleared
        this.store.subscribe('selectionCleared', () => {
            this.clearHighlights();
        });
    }

    /**
     * Highlight event-related elements in graph
     */
    highlightEventInGraph(event) {
        if (!event || !this.graph.cy) return;
        
        this.clearHighlights();
        
        const elementsToHighlight = this.getGraphElementsForEvent(event);
        
        if (elementsToHighlight.length > 0) {
            // Highlight elements
            elementsToHighlight.forEach(element => {
                element.addClass('terminal-highlighted');
                this.highlightedElements.add(element.id());
            });
            
            // Fit view to highlighted elements
            this.graph.cy.fit(elementsToHighlight, 50);
            
            // Auto-clear highlight after delay
            this.scheduleHighlightClear();
        }
    }

    /**
     * Preview event in graph (lighter highlight)
     */
    previewEventInGraph(event) {
        if (!event || !this.graph.cy) return;
        
        const elementsToHighlight = this.getGraphElementsForEvent(event);
        
        if (elementsToHighlight.length > 0) {
            // Add preview class
            elementsToHighlight.forEach(element => {
                element.addClass('terminal-preview');
            });
            
            // Clear preview after short delay
            setTimeout(() => {
                elementsToHighlight.forEach(element => {
                    element.removeClass('terminal-preview');
                });
            }, 1000);
        }
    }

    /**
     * Handle new events for auto-highlighting
     */
    handleNewEvent(event) {
        // Auto-highlight important events
        if (this.shouldAutoHighlight(event)) {
            setTimeout(() => {
                this.highlightEventInGraph(event);
            }, 100);
        }
    }

    /**
     * Highlight events related to graph element
     */
    highlightRelatedEvents(graphElement) {
        const terminalStore = this.terminal.getStore();
        const relatedEvents = this.getEventsForGraphElement(graphElement);
        
        if (relatedEvents.length > 0) {
            // Highlight events in terminal
            const eventIds = relatedEvents.map(event => event.id);
            terminalStore.highlightEvents(eventIds);
            
            // Show summary toast
            this.showEventSummary(graphElement, relatedEvents);
        }
    }

    /**
     * Get graph elements related to an event
     */
    getGraphElementsForEvent(event) {
        if (!this.graph.cy) return [];
        
        const elements = [];
        const eventType = event.eventType;
        const details = event.details;
        
        // Switch-related events
        if (details.switch_id || details.dpid) {
            const switchId = details.switch_id || details.dpid;
            const switchElement = this.graph.cy.getElementById(switchId);
            if (switchElement.length > 0) {
                elements.push(switchElement);
            }
        }
        
        // Host-related events
        if (details.mac || (eventType === 'packet_in' && (details.src_ip || details.dst_ip))) {
            // Find host by MAC
            if (details.mac) {
                const hostElement = this.graph.cy.getElementById(details.mac);
                if (hostElement.length > 0) {
                    elements.push(hostElement);
                }
            }
            
            // Find hosts by IP
            if (details.src_ip) {
                const srcHost = this.findHostByIP(details.src_ip);
                if (srcHost) elements.push(srcHost);
            }
            
            if (details.dst_ip) {
                const dstHost = this.findHostByIP(details.dst_ip);
                if (dstHost) elements.push(dstHost);
            }
        }
        
        // Link-related events
        if (eventType.includes('link') && details.src && details.dst) {
            const srcId = details.src.dpid || details.src.id;
            const dstId = details.dst.dpid || details.dst.id;
            
            if (srcId && dstId) {
                // Find link between switches
                const link = this.graph.cy.edges().filter(edge => {
                    const source = edge.source().id();
                    const target = edge.target().id();
                    return (source === srcId && target === dstId) ||
                           (source === dstId && target === srcId);
                });
                
                if (link.length > 0) {
                    elements.push(link);
                }
                
                // Also highlight the switches
                const srcSwitch = this.graph.cy.getElementById(srcId);
                const dstSwitch = this.graph.cy.getElementById(dstId);
                if (srcSwitch.length > 0) elements.push(srcSwitch);
                if (dstSwitch.length > 0) elements.push(dstSwitch);
            }
        }
        
        return elements;
    }

    /**
     * Get events related to a graph element
     */
    getEventsForGraphElement(graphElement) {
        const terminalStore = this.terminal.getStore();
        const allEvents = terminalStore.state.events;
        const elementId = graphElement.id;
        const elementType = graphElement.type;
        
        return allEvents.filter(event => {
            const details = event.details;
            
            // Match by switch ID
            if (elementType === 'switch') {
                return details.switch_id === elementId || 
                       details.dpid === elementId;
            }
            
            // Match by host MAC
            if (elementType === 'host') {
                return details.mac === elementId ||
                       details.src_ip === this.getHostIP(elementId) ||
                       details.dst_ip === this.getHostIP(elementId);
            }
            
            // Match by link endpoints
            if (elementType === 'link') {
                const linkData = graphElement.data;
                return (details.src?.dpid === linkData.source && details.dst?.dpid === linkData.target) ||
                       (details.src?.dpid === linkData.target && details.dst?.dpid === linkData.source);
            }
            
            return false;
        });
    }

    /**
     * Find host element by IP address
     */
    findHostByIP(ip) {
        if (!this.graph.cy) return null;
        
        // Search through host nodes to find matching IP
        const hosts = this.graph.cy.nodes('[type="host"]');
        
        for (let i = 0; i < hosts.length; i++) {
            const host = hosts[i];
            const hostData = host.data('nodeData');
            
            if (hostData && hostData.ipv4 && hostData.ipv4.includes(ip)) {
                return host;
            }
        }
        
        return null;
    }

    /**
     * Get IP address for host element
     */
    getHostIP(hostId) {
        if (!this.graph.cy) return null;
        
        const hostElement = this.graph.cy.getElementById(hostId);
        if (hostElement.length > 0) {
            const hostData = hostElement.data('nodeData');
            if (hostData && hostData.ipv4 && hostData.ipv4.length > 0) {
                return hostData.ipv4[0];
            }
        }
        
        return null;
    }

    /**
     * Check if event should be auto-highlighted
     */
    shouldAutoHighlight(event) {
        const importantEvents = [
            'switch_enter',
            'switch_leave',
            'event_switch_enter',
            'event_switch_leave',
            'link_add',
            'link_delete',
            'event_link_add',
            'event_link_delete',
            'alert',
            'error'
        ];
        
        return importantEvents.includes(event.eventType);
    }

    /**
     * Show event summary for graph element
     */
    showEventSummary(graphElement, events) {
        const eventCounts = {};
        events.forEach(event => {
            eventCounts[event.eventType] = (eventCounts[event.eventType] || 0) + 1;
        });
        
        const summary = Object.entries(eventCounts)
            .map(([type, count]) => `${count} ${type}`)
            .join(', ');
        
        const elementName = graphElement.id || 'element';
        const message = `${elementName}: ${summary}`;
        
        // Show toast with summary
        if (window.topologyDashboard) {
            window.topologyDashboard.showToast('info', 'Related Events', message, 3000);
        }
    }

    /**
     * Clear all highlights
     */
    clearHighlights() {
        if (this.graph.cy) {
            this.graph.cy.elements().removeClass('terminal-highlighted terminal-preview');
        }
        
        this.highlightedElements.clear();
        
        if (this.highlightTimeout) {
            clearTimeout(this.highlightTimeout);
            this.highlightTimeout = null;
        }
    }

    /**
     * Schedule highlight clearing
     */
    scheduleHighlightClear() {
        if (this.highlightTimeout) {
            clearTimeout(this.highlightTimeout);
        }
        
        this.highlightTimeout = setTimeout(() => {
            this.clearHighlights();
        }, 5000); // Clear after 5 seconds
    }

    /**
     * Add custom styles for terminal highlighting
     */
    addCustomStyles() {
        if (!this.graph.cy) return;
        
        // Add custom styles for terminal integration
        this.graph.cy.style()
            .selector('.terminal-highlighted')
            .style({
                'border-width': 4,
                'border-color': '#ff6b35',
                'line-color': '#ff6b35',
                'target-arrow-color': '#ff6b35',
                'z-index': 100
            })
            .selector('.terminal-preview')
            .style({
                'border-width': 3,
                'border-color': '#ffa500',
                'line-color': '#ffa500',
                'target-arrow-color': '#ffa500',
                'opacity': 0.8
            })
            .update();
    }

    /**
     * Create event correlation visualization
     */
    createEventCorrelation(events) {
        // Group events by time windows
        const timeWindows = this.groupEventsByTime(events, 5000); // 5 second windows
        
        // Find correlated events
        const correlations = this.findEventCorrelations(timeWindows);
        
        return correlations;
    }

    /**
     * Group events by time windows
     */
    groupEventsByTime(events, windowMs) {
        const windows = [];
        let currentWindow = [];
        let windowStart = null;
        
        events.forEach(event => {
            const eventTime = new Date(event.timestampRaw).getTime();
            
            if (!windowStart || eventTime - windowStart > windowMs) {
                if (currentWindow.length > 0) {
                    windows.push(currentWindow);
                }
                currentWindow = [event];
                windowStart = eventTime;
            } else {
                currentWindow.push(event);
            }
        });
        
        if (currentWindow.length > 0) {
            windows.push(currentWindow);
        }
        
        return windows;
    }

    /**
     * Find event correlations
     */
    findEventCorrelations(timeWindows) {
        const correlations = [];
        
        timeWindows.forEach(window => {
            if (window.length > 1) {
                // Find patterns in the window
                const patterns = this.identifyPatterns(window);
                if (patterns.length > 0) {
                    correlations.push({
                        timeWindow: window,
                        patterns: patterns
                    });
                }
            }
        });
        
        return correlations;
    }

    /**
     * Identify patterns in event window
     */
    identifyPatterns(events) {
        const patterns = [];
        
        // Pattern: packet_in followed by flow_mod
        const packetInEvents = events.filter(e => e.eventType === 'packet_in');
        const flowModEvents = events.filter(e => e.eventType === 'flow_mod');
        
        if (packetInEvents.length > 0 && flowModEvents.length > 0) {
            patterns.push({
                type: 'packet_to_flow',
                description: 'Packet-in triggered flow installation',
                events: [...packetInEvents, ...flowModEvents]
            });
        }
        
        // Pattern: switch events
        const switchEvents = events.filter(e => 
            e.eventType.includes('switch_enter') || e.eventType.includes('switch_leave')
        );
        
        if (switchEvents.length > 0) {
            patterns.push({
                type: 'topology_change',
                description: 'Network topology change',
                events: switchEvents
            });
        }
        
        return patterns;
    }

    /**
     * Destroy integration
     */
    destroy() {
        this.clearHighlights();
        
        if (this.highlightTimeout) {
            clearTimeout(this.highlightTimeout);
        }
    }
}

export default TerminalGraphIntegration;
