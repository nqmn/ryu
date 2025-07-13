/**
 * Topology State Management
 * 
 * Reactive state store for managing topology data and real-time updates.
 */

class TopologyStore {
    constructor() {
        this.state = {
            // Topology data
            switches: new Map(),
            hosts: new Map(),
            links: new Map(),
            
            // Statistics
            stats: {
                openflow_switches: 0,
                p4runtime_switches: 0,
                total_hosts: 0,
                active_links: 0
            },
            
            // UI state
            loading: false,
            error: null,
            lastUpdate: null,
            
            // Connection state
            connected: false,
            connectionStatus: 'disconnected',
            
            // Filters and search
            filters: {
                showSwitches: true,
                showHosts: true,
                showLinks: true,
                searchQuery: ''
            },
            
            // Selected elements
            selectedNode: null,
            selectedLink: null
        };
        
        this.listeners = new Map();
        this.eventQueue = [];
        this.processingEvents = false;
    }

    /**
     * Subscribe to state changes
     */
    subscribe(key, callback) {
        if (!this.listeners.has(key)) {
            this.listeners.set(key, []);
        }
        this.listeners.get(key).push(callback);
        
        // Return unsubscribe function
        return () => {
            const callbacks = this.listeners.get(key);
            if (callbacks) {
                const index = callbacks.indexOf(callback);
                if (index > -1) {
                    callbacks.splice(index, 1);
                }
            }
        };
    }

    /**
     * Emit state change to listeners
     */
    emit(key, data) {
        if (this.listeners.has(key)) {
            this.listeners.get(key).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in state listener for ${key}:`, error);
                }
            });
        }
    }

    /**
     * Update state and notify listeners
     */
    setState(updates) {
        const oldState = { ...this.state };
        this.state = { ...this.state, ...updates };
        
        // Emit specific change events
        Object.keys(updates).forEach(key => {
            if (oldState[key] !== this.state[key]) {
                this.emit(key, this.state[key]);
            }
        });
        
        // Emit general state change
        this.emit('stateChange', this.state);
    }

    /**
     * Load initial topology data
     */
    loadTopology(topologyData) {
        this.setState({ loading: true, error: null });
        
        try {
            const switches = new Map();
            const hosts = new Map();
            const links = new Map();
            
            // Process switches
            if (topologyData.switches) {
                topologyData.switches.forEach(switchData => {
                    const id = switchData.dpid || switchData.id || switchData.switch_id;
                    switches.set(id, {
                        id,
                        type: 'switch',
                        subtype: this.detectSwitchType(switchData),
                        data: switchData,
                        position: null
                    });
                });
            }
            
            // Process OpenFlow switches
            if (topologyData.openflow_switches) {
                topologyData.openflow_switches.forEach(switchData => {
                    const id = switchData.switch_id || switchData.dpid;
                    switches.set(id, {
                        id,
                        type: 'switch',
                        subtype: 'openflow',
                        data: switchData,
                        position: null
                    });
                });
            }
            
            // Process P4Runtime switches
            if (topologyData.p4runtime_switches) {
                topologyData.p4runtime_switches.forEach(switchData => {
                    const id = switchData.switch_id || switchData.dpid;
                    switches.set(id, {
                        id,
                        type: 'switch',
                        subtype: 'p4runtime',
                        data: switchData,
                        position: null
                    });
                });
            }
            
            // Process hosts
            if (topologyData.hosts) {
                topologyData.hosts.forEach(hostData => {
                    const id = hostData.mac || hostData.id;
                    hosts.set(id, {
                        id,
                        type: 'host',
                        data: hostData,
                        position: null
                    });
                });
            }
            
            // Process links
            if (topologyData.links) {
                topologyData.links.forEach(linkData => {
                    const id = this.generateLinkId(linkData);
                    links.set(id, {
                        id,
                        type: 'link',
                        data: linkData,
                        source: linkData.src?.dpid || linkData.src?.id || linkData.src,
                        target: linkData.dst?.dpid || linkData.dst?.id || linkData.dst
                    });
                });
            }
            
            // Update statistics
            const stats = {
                openflow_switches: Array.from(switches.values()).filter(s => s.subtype === 'openflow').length,
                p4runtime_switches: Array.from(switches.values()).filter(s => s.subtype === 'p4runtime').length,
                total_hosts: hosts.size,
                active_links: links.size
            };
            
            this.setState({
                switches,
                hosts,
                links,
                stats,
                loading: false,
                lastUpdate: new Date().toISOString()
            });
            
            console.log('Topology loaded:', { switches: switches.size, hosts: hosts.size, links: links.size });
            
        } catch (error) {
            console.error('Failed to load topology:', error);
            this.setState({ loading: false, error: error.message });
        }
    }

    /**
     * Handle real-time topology events
     */
    handleTopologyEvent(eventType, eventData) {
        // Queue events to process them in order
        this.eventQueue.push({ type: eventType, data: eventData });
        this.processEventQueue();
    }

    /**
     * Process queued events
     */
    async processEventQueue() {
        if (this.processingEvents || this.eventQueue.length === 0) {
            return;
        }
        
        this.processingEvents = true;
        
        while (this.eventQueue.length > 0) {
            const event = this.eventQueue.shift();
            await this.processEvent(event.type, event.data);
        }
        
        this.processingEvents = false;
    }

    /**
     * Process individual topology event
     */
    async processEvent(eventType, eventData) {
        try {
            switch (eventType) {
                case 'switch_enter':
                case 'event_switch_enter':
                    this.handleSwitchEnter(eventData);
                    break;
                    
                case 'switch_leave':
                case 'event_switch_leave':
                    this.handleSwitchLeave(eventData);
                    break;
                    
                case 'link_add':
                case 'event_link_add':
                    this.handleLinkAdd(eventData);
                    break;
                    
                case 'link_delete':
                case 'event_link_delete':
                    this.handleLinkDelete(eventData);
                    break;
                    
                case 'host_add':
                    this.handleHostAdd(eventData);
                    break;
                    
                case 'port_status':
                    this.handlePortStatus(eventData);
                    break;
                    
                default:
                    console.log('Unhandled topology event:', eventType, eventData);
            }
        } catch (error) {
            console.error(`Error processing event ${eventType}:`, error);
        }
    }

    /**
     * Handle switch enter event
     */
    handleSwitchEnter(switchData) {
        const switches = new Map(this.state.switches);
        const id = switchData.dpid || switchData.id || switchData.switch_id;
        
        switches.set(id, {
            id,
            type: 'switch',
            subtype: this.detectSwitchType(switchData),
            data: switchData,
            position: null
        });
        
        this.updateStats(switches, this.state.hosts, this.state.links);
        this.setState({ switches });
        this.emit('switchEnter', { id, data: switchData });
    }

    /**
     * Handle switch leave event
     */
    handleSwitchLeave(switchData) {
        const switches = new Map(this.state.switches);
        const id = switchData.dpid || switchData.id || switchData.switch_id;
        
        switches.delete(id);
        
        this.updateStats(switches, this.state.hosts, this.state.links);
        this.setState({ switches });
        this.emit('switchLeave', { id, data: switchData });
    }

    /**
     * Handle link add event
     */
    handleLinkAdd(linkData) {
        const links = new Map(this.state.links);
        const id = this.generateLinkId(linkData);
        
        links.set(id, {
            id,
            type: 'link',
            data: linkData,
            source: linkData.src?.dpid || linkData.src?.id || linkData.src,
            target: linkData.dst?.dpid || linkData.dst?.id || linkData.dst
        });
        
        this.updateStats(this.state.switches, this.state.hosts, links);
        this.setState({ links });
        this.emit('linkAdd', { id, data: linkData });
    }

    /**
     * Handle link delete event
     */
    handleLinkDelete(linkData) {
        const links = new Map(this.state.links);
        const id = this.generateLinkId(linkData);
        
        links.delete(id);
        
        this.updateStats(this.state.switches, this.state.hosts, links);
        this.setState({ links });
        this.emit('linkDelete', { id, data: linkData });
    }

    /**
     * Handle host add event
     */
    handleHostAdd(hostData) {
        const hosts = new Map(this.state.hosts);
        const id = hostData.mac || hostData.id;
        
        hosts.set(id, {
            id,
            type: 'host',
            data: hostData,
            position: null
        });
        
        this.updateStats(this.state.switches, hosts, this.state.links);
        this.setState({ hosts });
        this.emit('hostAdd', { id, data: hostData });
    }

    /**
     * Handle port status event
     */
    handlePortStatus(portData) {
        // Update switch data with new port status
        const switches = new Map(this.state.switches);
        // Implementation depends on port data structure
        this.emit('portStatus', portData);
    }

    /**
     * Update statistics
     */
    updateStats(switches, hosts, links) {
        const stats = {
            openflow_switches: Array.from(switches.values()).filter(s => s.subtype === 'openflow').length,
            p4runtime_switches: Array.from(switches.values()).filter(s => s.subtype === 'p4runtime').length,
            total_hosts: hosts.size,
            active_links: links.size
        };
        
        this.setState({ stats });
    }

    /**
     * Detect switch type from switch data
     */
    detectSwitchType(switchData) {
        if (switchData.switch_type) {
            return switchData.switch_type;
        }
        
        // Try to detect from other fields
        if (switchData.capabilities && switchData.capabilities.ofp_version) {
            return 'openflow';
        }
        
        if (switchData.p4_device_id || switchData.pipeline) {
            return 'p4runtime';
        }
        
        // Default to openflow for backward compatibility
        return 'openflow';
    }

    /**
     * Generate unique link ID
     */
    generateLinkId(linkData) {
        const src = linkData.src?.dpid || linkData.src?.id || linkData.src;
        const dst = linkData.dst?.dpid || linkData.dst?.id || linkData.dst;
        const srcPort = linkData.src?.port_no || linkData.src?.port || '';
        const dstPort = linkData.dst?.port_no || linkData.dst?.port || '';
        
        return `${src}:${srcPort}-${dst}:${dstPort}`;
    }

    /**
     * Set connection status
     */
    setConnectionStatus(status) {
        this.setState({ 
            connected: status === 'connected',
            connectionStatus: status 
        });
    }

    /**
     * Update filters
     */
    updateFilters(newFilters) {
        const filters = { ...this.state.filters, ...newFilters };
        this.setState({ filters });
    }

    /**
     * Set selected node
     */
    setSelectedNode(nodeId) {
        this.setState({ selectedNode: nodeId });
    }

    /**
     * Set selected link
     */
    setSelectedLink(linkId) {
        this.setState({ selectedLink: linkId });
    }

    /**
     * Get filtered topology data for visualization
     */
    getFilteredTopology() {
        const { switches, hosts, links, filters } = this.state;
        const { showSwitches, showHosts, showLinks, searchQuery } = filters;
        
        const filteredSwitches = showSwitches ? 
            Array.from(switches.values()).filter(node => 
                this.matchesSearch(node, searchQuery)
            ) : [];
            
        const filteredHosts = showHosts ? 
            Array.from(hosts.values()).filter(node => 
                this.matchesSearch(node, searchQuery)
            ) : [];
            
        const filteredLinks = showLinks ? Array.from(links.values()) : [];
        
        return {
            switches: filteredSwitches,
            hosts: filteredHosts,
            links: filteredLinks
        };
    }

    /**
     * Check if node matches search query
     */
    matchesSearch(node, query) {
        if (!query) return true;
        
        const searchText = query.toLowerCase();
        const nodeId = (node.id || '').toLowerCase();
        const nodeData = JSON.stringify(node.data || {}).toLowerCase();
        
        return nodeId.includes(searchText) || nodeData.includes(searchText);
    }

    /**
     * Get current state
     */
    getState() {
        return { ...this.state };
    }

    /**
     * Clear all data
     */
    clear() {
        this.setState({
            switches: new Map(),
            hosts: new Map(),
            links: new Map(),
            stats: {
                openflow_switches: 0,
                p4runtime_switches: 0,
                total_hosts: 0,
                active_links: 0
            },
            selectedNode: null,
            selectedLink: null,
            lastUpdate: null
        });
    }
}

export default TopologyStore;
