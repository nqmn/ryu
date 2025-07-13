/**
 * Network Graph Component
 * 
 * Interactive network topology visualization using Cytoscape.js
 */

class NetworkGraph {
    constructor(container, store) {
        this.container = container;
        this.store = store;
        this.cy = null;
        this.navigator = null;
        this.currentLayout = null;
        this.layoutOptions = {
            'cose-bilkent': {
                name: 'cose-bilkent',
                quality: 'default',
                nodeDimensionsIncludeLabels: true,
                refresh: 30,
                fit: true,
                padding: 30,
                randomize: false,
                nodeRepulsion: 4500,
                idealEdgeLength: 50,
                edgeElasticity: 0.45,
                nestingFactor: 0.1,
                gravity: 0.25,
                numIter: 2500,
                tile: true,
                animate: 'end',
                animationDuration: 1000
            },
            'grid': {
                name: 'grid',
                fit: true,
                padding: 30,
                avoidOverlap: true,
                avoidOverlapPadding: 10,
                nodeDimensionsIncludeLabels: true,
                spacingFactor: 1.5,
                animate: true,
                animationDuration: 500
            },
            'circle': {
                name: 'circle',
                fit: true,
                padding: 30,
                avoidOverlap: true,
                nodeDimensionsIncludeLabels: true,
                spacingFactor: 1.5,
                animate: true,
                animationDuration: 500
            },
            'breadthfirst': {
                name: 'breadthfirst',
                fit: true,
                padding: 30,
                avoidOverlap: true,
                nodeDimensionsIncludeLabels: true,
                spacingFactor: 1.5,
                directed: false,
                animate: true,
                animationDuration: 500
            }
        };
        
        this.initialize();
    }

    /**
     * Get available layout (with fallback)
     */
    getAvailableLayout() {
        // Use grid layout as default (reliable and works well for network topology)
        return this.layoutOptions['grid'];
    }

    /**
     * Check if a layout is available
     */
    isLayoutAvailable(layoutName) {
        try {
            // For cose-bilkent, check if the extension is registered
            if (layoutName === 'cose-bilkent') {
                return cytoscape.layout && cytoscape.layout.coseBilkent !== undefined;
            }

            // For other layouts, create a temporary cytoscape instance to test
            const testCy = cytoscape({
                elements: [],
                layout: { name: layoutName }
            });
            testCy.destroy();
            return true;
        } catch (error) {
            console.warn(`Layout ${layoutName} is not available:`, error.message);
            return false;
        }
    }

    /**
     * Initialize the graph
     */
    initialize() {
        // Check available layouts and set default
        const defaultLayout = this.getAvailableLayout();

        // Create Cytoscape instance
        this.cy = cytoscape({
            container: this.container,

            style: this.getGraphStyle(),

            layout: defaultLayout,

            // Interaction options
            minZoom: 0.1,
            maxZoom: 3,

            // Performance options
            textureOnViewport: true,
            motionBlur: true,
            pixelRatio: 'auto'
        });

        // Set up event handlers
        this.setupEventHandlers();

        // Initialize navigator (minimap)
        this.initializeNavigator();

        // Subscribe to store changes
        this.subscribeToStore();

        console.log('Network graph initialized with layout:', defaultLayout.name);
    }

    /**
     * Get Cytoscape style configuration
     */
    getGraphStyle() {
        // Get current theme colors
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const textColor = isDark ? '#ffffff' : '#212529';
        const bgColor = isDark ? '#1a1a1a' : '#ffffff';

        return [
            // Node styles
            {
                selector: 'node',
                style: {
                    'width': 40,
                    'height': 40,
                    'label': 'data(label)',
                    'text-valign': 'bottom',
                    'text-halign': 'center',
                    'text-margin-y': 5,
                    'font-size': '12px',
                    'font-weight': 'bold',
                    'color': textColor,
                    'text-outline-width': 2,
                    'text-outline-color': bgColor,
                    'overlay-padding': 6,
                    'z-index': 10
                }
            },
            
            // Switch nodes (OpenFlow)
            {
                selector: 'node[type="switch"][subtype="openflow"]',
                style: {
                    'shape': 'rectangle',
                    'background-color': '#007bff',
                    'border-width': 2,
                    'border-color': '#0056b3',
                    'width': 50,
                    'height': 35
                }
            },
            
            // Switch nodes (P4Runtime)
            {
                selector: 'node[type="switch"][subtype="p4runtime"]',
                style: {
                    'shape': 'rectangle',
                    'background-color': '#28a745',
                    'border-width': 2,
                    'border-color': '#1e7e34',
                    'width': 50,
                    'height': 35
                }
            },
            
            // Host nodes
            {
                selector: 'node[type="host"]',
                style: {
                    'shape': 'ellipse',
                    'background-color': '#ffc107',
                    'border-width': 2,
                    'border-color': '#e0a800',
                    'width': 35,
                    'height': 35
                }
            },
            
            // Selected nodes
            {
                selector: 'node:selected',
                style: {
                    'border-width': 4,
                    'border-color': '#dc3545',
                    'z-index': 20
                }
            },
            
            // Hovered nodes
            {
                selector: 'node:active',
                style: {
                    'overlay-opacity': 0.2,
                    'overlay-color': '#007bff'
                }
            },
            
            // Edge styles
            {
                selector: 'edge',
                style: {
                    'width': 3,
                    'line-color': '#6c757d',
                    'target-arrow-color': '#6c757d',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier',
                    'arrow-scale': 1.2,
                    'z-index': 5
                }
            },
            
            // Selected edges
            {
                selector: 'edge:selected',
                style: {
                    'width': 5,
                    'line-color': '#007bff',
                    'target-arrow-color': '#007bff',
                    'z-index': 15
                }
            },
            
            // Hovered edges
            {
                selector: 'edge:active',
                style: {
                    'overlay-opacity': 0.2,
                    'overlay-color': '#007bff'
                }
            },
            
            // Hidden elements
            {
                selector: '.hidden',
                style: {
                    'display': 'none'
                }
            },
            
            // Highlighted elements
            {
                selector: '.highlighted',
                style: {
                    'border-width': 4,
                    'border-color': '#ffc107',
                    'line-color': '#ffc107',
                    'target-arrow-color': '#ffc107'
                }
            }
        ];
    }

    /**
     * Set up event handlers
     */
    setupEventHandlers() {
        // Node click events
        this.cy.on('tap', 'node', (event) => {
            const node = event.target;
            const nodeData = node.data();
            this.store.setSelectedNode(nodeData.id);
            this.store.emit('nodeSelected', { node: nodeData, element: node });
        });

        // Edge click events
        this.cy.on('tap', 'edge', (event) => {
            const edge = event.target;
            const edgeData = edge.data();
            this.store.setSelectedLink(edgeData.id);
            this.store.emit('linkSelected', { link: edgeData, element: edge });
        });

        // Background click (deselect)
        this.cy.on('tap', (event) => {
            if (event.target === this.cy) {
                this.cy.$(':selected').unselect();
                this.store.setSelectedNode(null);
                this.store.setSelectedLink(null);
                this.store.emit('selectionCleared');
            }
        });

        // Double click to fit
        this.cy.on('dblclick', (event) => {
            if (event.target === this.cy) {
                this.cy.fit(null, 50);
            }
        });

        // Context menu (right click)
        this.cy.on('cxttap', 'node', (event) => {
            const node = event.target;
            const nodeData = node.data();
            this.store.emit('nodeContextMenu', { 
                node: nodeData, 
                element: node,
                position: event.position || event.cyPosition
            });
        });
    }

    /**
     * Initialize navigator (minimap)
     */
    initializeNavigator() {
        const minimapContainer = document.getElementById('minimap');
        if (minimapContainer && this.cy.navigator) {
            this.navigator = this.cy.navigator({
                container: minimapContainer,
                viewLiveFramerate: 0,
                thumbnailEventFramerate: 30,
                thumbnailLiveFramerate: false,
                dblClickDelay: 200,
                removeCustomContainer: false,
                rerenderDelay: 100
            });
        }
    }

    /**
     * Subscribe to store changes
     */
    subscribeToStore() {
        // Listen for topology updates
        this.store.subscribe('switches', () => this.updateGraph());
        this.store.subscribe('hosts', () => this.updateGraph());
        this.store.subscribe('links', () => this.updateGraph());
        this.store.subscribe('filters', () => this.applyFilters());
        
        // Listen for real-time events
        this.store.subscribe('switchEnter', (data) => this.handleSwitchEnter(data));
        this.store.subscribe('switchLeave', (data) => this.handleSwitchLeave(data));
        this.store.subscribe('linkAdd', (data) => this.handleLinkAdd(data));
        this.store.subscribe('linkDelete', (data) => this.handleLinkDelete(data));
        this.store.subscribe('hostAdd', (data) => this.handleHostAdd(data));
    }

    /**
     * Update the entire graph
     */
    updateGraph() {
        const topology = this.store.getFilteredTopology();
        const elements = this.buildGraphElements(topology);
        
        // Update graph elements
        this.cy.elements().remove();
        this.cy.add(elements);
        
        // Apply layout (will fallback to grid if cose-bilkent not available)
        this.applyLayout();
        
        console.log('Graph updated:', {
            switches: topology.switches.length,
            hosts: topology.hosts.length,
            links: topology.links.length
        });
    }

    /**
     * Build Cytoscape elements from topology data
     */
    buildGraphElements(topology) {
        const elements = [];
        
        // Add switch nodes
        topology.switches.forEach(switchNode => {
            elements.push({
                group: 'nodes',
                data: {
                    id: switchNode.id,
                    label: this.formatNodeLabel(switchNode),
                    type: switchNode.type,
                    subtype: switchNode.subtype,
                    nodeData: switchNode.data
                }
            });
        });
        
        // Add host nodes
        topology.hosts.forEach(hostNode => {
            elements.push({
                group: 'nodes',
                data: {
                    id: hostNode.id,
                    label: this.formatNodeLabel(hostNode),
                    type: hostNode.type,
                    nodeData: hostNode.data
                }
            });
        });
        
        // Add links
        topology.links.forEach(link => {
            elements.push({
                group: 'edges',
                data: {
                    id: link.id,
                    source: link.source,
                    target: link.target,
                    linkData: link.data
                }
            });
        });
        
        return elements;
    }

    /**
     * Format node label for display
     */
    formatNodeLabel(node) {
        if (node.type === 'switch') {
            const dpid = node.data.dpid || node.id;
            return dpid.length > 8 ? dpid.slice(-4) : dpid;
        } else if (node.type === 'host') {
            const mac = node.data.mac || node.id;
            return mac.split(':').slice(-2).join(':');
        }
        return node.id;
    }

    /**
     * Apply layout to the graph
     */
    applyLayout(layoutName = 'grid', options = {}) {
        if (this.currentLayout) {
            this.currentLayout.stop();
        }

        // Use built-in layouts only
        const availableLayouts = ['grid', 'circle', 'breadthfirst', 'cose'];
        if (!availableLayouts.includes(layoutName)) {
            console.warn(`Layout ${layoutName} not available, using grid layout`);
            layoutName = 'grid';
        }

        const layoutOptions = {
            ...this.layoutOptions[layoutName],
            ...options
        };

        try {
            this.currentLayout = this.cy.layout(layoutOptions);
            this.currentLayout.run();
            console.log(`Applied layout: ${layoutName}`);
        } catch (error) {
            console.error(`Failed to apply layout ${layoutName}:`, error);
            // Fallback to basic grid layout
            this.currentLayout = this.cy.layout({ name: 'grid' });
            this.currentLayout.run();
        }

        return this.currentLayout;
    }

    /**
     * Apply filters to hide/show elements
     */
    applyFilters() {
        const filters = this.store.getState().filters;
        
        // Show/hide switches
        this.cy.nodes('[type="switch"]').toggleClass('hidden', !filters.showSwitches);
        
        // Show/hide hosts
        this.cy.nodes('[type="host"]').toggleClass('hidden', !filters.showHosts);
        
        // Show/hide links
        this.cy.edges().toggleClass('hidden', !filters.showLinks);
        
        // Apply search filter
        if (filters.searchQuery) {
            this.applySearchFilter(filters.searchQuery);
        } else {
            this.cy.elements().removeClass('highlighted');
        }
    }

    /**
     * Apply search highlighting
     */
    applySearchFilter(query) {
        const searchText = query.toLowerCase();
        
        this.cy.elements().removeClass('highlighted');
        
        this.cy.nodes().forEach(node => {
            const nodeData = node.data();
            const label = (nodeData.label || '').toLowerCase();
            const id = (nodeData.id || '').toLowerCase();
            
            if (label.includes(searchText) || id.includes(searchText)) {
                node.addClass('highlighted');
            }
        });
    }

    /**
     * Handle real-time switch enter
     */
    handleSwitchEnter(data) {
        const element = {
            group: 'nodes',
            data: {
                id: data.id,
                label: this.formatSwitchLabel(data.data),
                type: 'switch',
                subtype: this.store.detectSwitchType(data.data),
                nodeData: data.data
            }
        };
        
        this.cy.add(element);
        this.animateElementAddition(data.id);
    }

    /**
     * Handle real-time switch leave
     */
    handleSwitchLeave(data) {
        const element = this.cy.getElementById(data.id);
        if (element.length > 0) {
            this.animateElementRemoval(element);
        }
    }

    /**
     * Handle real-time link add
     */
    handleLinkAdd(data) {
        const element = {
            group: 'edges',
            data: {
                id: data.id,
                source: data.data.src?.dpid || data.data.src,
                target: data.data.dst?.dpid || data.data.dst,
                linkData: data.data
            }
        };
        
        this.cy.add(element);
        this.animateElementAddition(data.id);
    }

    /**
     * Handle real-time link delete
     */
    handleLinkDelete(data) {
        const element = this.cy.getElementById(data.id);
        if (element.length > 0) {
            this.animateElementRemoval(element);
        }
    }

    /**
     * Handle real-time host add
     */
    handleHostAdd(data) {
        const element = {
            group: 'nodes',
            data: {
                id: data.id,
                label: this.formatHostLabel(data.data),
                type: 'host',
                nodeData: data.data
            }
        };
        
        this.cy.add(element);
        this.animateElementAddition(data.id);
    }

    /**
     * Animate element addition
     */
    animateElementAddition(elementId) {
        const element = this.cy.getElementById(elementId);
        if (element.length > 0) {
            element.style('opacity', 0);
            element.animate({
                style: { opacity: 1 }
            }, {
                duration: 500,
                easing: 'ease-out'
            });
        }
    }

    /**
     * Animate element removal
     */
    animateElementRemoval(element) {
        element.animate({
            style: { opacity: 0 }
        }, {
            duration: 300,
            easing: 'ease-in',
            complete: () => {
                element.remove();
            }
        });
    }

    /**
     * Fit graph to viewport
     */
    fit(padding = 50) {
        this.cy.fit(null, padding);
    }

    /**
     * Reset graph layout
     */
    resetLayout() {
        this.applyLayout(); // Will use default layout with fallback
    }

    /**
     * Export graph as image
     */
    exportImage(format = 'png') {
        return this.cy.png({
            output: 'blob',
            bg: 'white',
            full: true,
            scale: 2
        });
    }

    /**
     * Get graph statistics
     */
    getStats() {
        return {
            nodes: this.cy.nodes().length,
            edges: this.cy.edges().length,
            switches: this.cy.nodes('[type="switch"]').length,
            hosts: this.cy.nodes('[type="host"]').length
        };
    }

    /**
     * Destroy the graph
     */
    destroy() {
        if (this.navigator) {
            this.navigator.destroy();
        }
        if (this.cy) {
            this.cy.destroy();
        }
    }
}

export default NetworkGraph;
