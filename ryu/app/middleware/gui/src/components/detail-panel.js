/**
 * Detail Panel Component
 * 
 * Shows detailed information about selected nodes and links
 */

class DetailPanel {
    constructor(store, api) {
        this.store = store;
        this.api = api;
        this.panel = document.getElementById('detailPanel');
        this.title = document.getElementById('detailTitle');
        this.content = document.getElementById('detailContent');
        this.closeButton = document.getElementById('detailClose');
        
        this.currentNode = null;
        this.currentLink = null;
        
        this.initialize();
    }

    /**
     * Initialize the detail panel
     */
    initialize() {
        // Set up event handlers
        this.closeButton.addEventListener('click', () => this.close());
        
        // Close on escape key
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && this.panel.classList.contains('open')) {
                this.close();
            }
        });
        
        // Subscribe to store events using the correct method
        this.store.subscribe('nodeSelected', (data) => {
            if (data && data.node) {
                this.showNodeDetails(data.node);
            }
        });
        this.store.subscribe('linkSelected', (data) => {
            if (data && data.link) {
                this.showLinkDetails(data.link);
            }
        });
        this.store.subscribe('selectionCleared', () => this.close());
        
        console.log('Detail panel initialized');
    }

    /**
     * Show node details
     */
    async showNodeDetails(nodeData) {
        this.currentNode = nodeData;
        this.currentLink = null;
        
        this.title.textContent = this.getNodeTitle(nodeData);
        this.content.innerHTML = this.createLoadingContent();
        this.open();
        
        try {
            // Get additional data based on node type
            let additionalData = {};
            
            if (nodeData.type === 'switch') {
                additionalData = await this.getSwitchDetails(nodeData);
            } else if (nodeData.type === 'host') {
                additionalData = await this.getHostDetails(nodeData);
            }
            
            this.content.innerHTML = this.createNodeContent(nodeData, additionalData);
            this.setupNodeActions(nodeData);
            
        } catch (error) {
            console.error('Failed to load node details:', error);
            this.content.innerHTML = this.createErrorContent(error.message);
        }
    }

    /**
     * Show link details
     */
    showLinkDetails(linkData) {
        this.currentLink = linkData;
        this.currentNode = null;
        
        this.title.textContent = 'Link Details';
        this.content.innerHTML = this.createLinkContent(linkData);
        this.open();
    }

    /**
     * Get switch details from API
     */
    async getSwitchDetails(nodeData) {
        const switchId = nodeData.id;
        const details = {};
        
        try {
            // Get flow statistics
            details.flows = await this.api.getFlowStats(switchId);
        } catch (error) {
            console.warn('Failed to get flow stats:', error);
            details.flows = null;
        }
        
        try {
            // Get port statistics
            details.ports = await this.api.getPortStats(switchId);
        } catch (error) {
            console.warn('Failed to get port stats:', error);
            details.ports = null;
        }
        
        return details;
    }

    /**
     * Get host details
     */
    async getHostDetails(nodeData) {
        // For now, just return the basic data
        // Could be extended to get connectivity info, etc.
        return {};
    }

    /**
     * Create node content HTML
     */
    createNodeContent(nodeData, additionalData = {}) {
        const data = nodeData.nodeData || nodeData.data || {};
        
        if (nodeData.type === 'switch') {
            return this.createSwitchContent(nodeData, data, additionalData);
        } else if (nodeData.type === 'host') {
            return this.createHostContent(nodeData, data, additionalData);
        }
        
        return this.createGenericContent(nodeData, data);
    }

    /**
     * Create switch content
     */
    createSwitchContent(nodeData, data, additionalData) {
        const subtype = nodeData.subtype || 'openflow';
        const subtypeClass = `switch-${subtype}`;
        
        return `
            <div class="detail-section">
                <div class="detail-section-title">Switch Information</div>
                <div class="node-type-indicator ${subtypeClass}">
                    <span>${subtype.toUpperCase()} Switch</span>
                </div>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">DPID</span>
                        <span class="detail-value code">${data.dpid || nodeData.id}</span>
                    </div>
                    ${data.address ? `
                    <div class="detail-item">
                        <span class="detail-label">Address</span>
                        <span class="detail-value">${data.address}:${data.port || 'N/A'}</span>
                    </div>
                    ` : ''}
                    <div class="detail-item">
                        <span class="detail-label">Status</span>
                        <span class="detail-value">
                            <span class="connection-indicator ${data.connected ? 'connected' : 'disconnected'}"></span>
                            ${data.connected ? 'Connected' : 'Disconnected'}
                        </span>
                    </div>
                    ${data.capabilities ? `
                    <div class="detail-item">
                        <span class="detail-label">OpenFlow Version</span>
                        <span class="detail-value">${data.capabilities.ofp_version || 'N/A'}</span>
                    </div>
                    ` : ''}
                </div>
            </div>
            
            ${this.createPortsSection(data)}
            ${this.createFlowsSection(additionalData.flows)}
            ${this.createActionsSection(nodeData)}
        `;
    }

    /**
     * Create host content
     */
    createHostContent(nodeData, data, additionalData) {
        return `
            <div class="detail-section">
                <div class="detail-section-title">Host Information</div>
                <div class="node-type-indicator host">
                    <span>Host</span>
                </div>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">MAC Address</span>
                        <span class="detail-value code">${data.mac || nodeData.id}</span>
                    </div>
                    ${data.ipv4 && data.ipv4.length > 0 ? `
                    <div class="detail-item">
                        <span class="detail-label">IPv4 Address</span>
                        <span class="detail-value">${data.ipv4.join(', ')}</span>
                    </div>
                    ` : ''}
                    ${data.ipv6 && data.ipv6.length > 0 ? `
                    <div class="detail-item">
                        <span class="detail-label">IPv6 Address</span>
                        <span class="detail-value">${data.ipv6.join(', ')}</span>
                    </div>
                    ` : ''}
                    ${data.port ? `
                    <div class="detail-item">
                        <span class="detail-label">Connected Port</span>
                        <span class="detail-value">${data.port.dpid}:${data.port.port_no}</span>
                    </div>
                    ` : ''}
                </div>
            </div>
            
            ${this.createHostActionsSection(nodeData)}
        `;
    }

    /**
     * Create generic content for unknown node types
     */
    createGenericContent(nodeData, data) {
        return `
            <div class="detail-section">
                <div class="detail-section-title">Node Information</div>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">ID</span>
                        <span class="detail-value code">${nodeData.id}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Type</span>
                        <span class="detail-value">${nodeData.type}</span>
                    </div>
                </div>
            </div>
            
            <div class="detail-section">
                <div class="detail-section-title">Raw Data</div>
                <pre class="detail-value code">${JSON.stringify(data, null, 2)}</pre>
            </div>
        `;
    }

    /**
     * Create ports section
     */
    createPortsSection(data) {
        if (!data.ports || data.ports.length === 0) {
            return '';
        }
        
        const portsHtml = data.ports.map(port => `
            <div class="port-item">
                <div class="port-info">
                    <div class="port-name">${port.name || `Port ${port.port_no}`}</div>
                    <div class="port-details">${port.hw_addr || 'N/A'}</div>
                </div>
                <div class="port-status ${port.is_live ? 'up' : 'down'}">
                    ${port.is_live ? 'UP' : 'DOWN'}
                </div>
            </div>
        `).join('');
        
        return `
            <div class="detail-section">
                <div class="detail-section-title">Ports (${data.ports.length})</div>
                <div class="port-list">
                    ${portsHtml}
                </div>
            </div>
        `;
    }

    /**
     * Create flows section
     */
    createFlowsSection(flowsData) {
        if (!flowsData || !flowsData.flows) {
            return '';
        }
        
        const flowCount = Array.isArray(flowsData.flows) ? flowsData.flows.length : 0;
        
        return `
            <div class="detail-section">
                <div class="detail-section-title">Flow Rules</div>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">Total Flows</span>
                        <span class="detail-value">${flowCount}</span>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Create actions section for switches
     */
    createActionsSection(nodeData) {
        return `
            <div class="detail-section">
                <div class="detail-section-title">Actions</div>
                <div class="detail-actions">
                    <button class="btn btn-secondary" data-action="refresh">Refresh Data</button>
                    <button class="btn btn-secondary" data-action="flows">View Flows</button>
                </div>
            </div>
        `;
    }

    /**
     * Create actions section for hosts
     */
    createHostActionsSection(nodeData) {
        return `
            <div class="detail-section">
                <div class="detail-section-title">Actions</div>
                <div class="detail-actions">
                    <button class="btn btn-primary" data-action="ping">Ping Host</button>
                    <button class="btn btn-secondary" data-action="refresh">Refresh Data</button>
                </div>
            </div>
        `;
    }

    /**
     * Create link content
     */
    createLinkContent(linkData) {
        const data = linkData.linkData || linkData.data || {};
        
        return `
            <div class="detail-section">
                <div class="detail-section-title">Link Information</div>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">Source</span>
                        <span class="detail-value">${data.src?.dpid || linkData.source}:${data.src?.port_no || ''}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Destination</span>
                        <span class="detail-value">${data.dst?.dpid || linkData.target}:${data.dst?.port_no || ''}</span>
                    </div>
                    ${data.bandwidth ? `
                    <div class="detail-item">
                        <span class="detail-label">Bandwidth</span>
                        <span class="detail-value">${data.bandwidth} Mbps</span>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Create loading content
     */
    createLoadingContent() {
        return `
            <div class="loading-spinner">
                <div class="spinner"></div>
                <span>Loading details...</span>
            </div>
        `;
    }

    /**
     * Create error content
     */
    createErrorContent(message) {
        return `
            <div class="detail-section">
                <div class="detail-section-title">Error</div>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">Message</span>
                        <span class="detail-value">${message}</span>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Setup action button handlers
     */
    setupNodeActions(nodeData) {
        const actionButtons = this.content.querySelectorAll('[data-action]');
        
        actionButtons.forEach(button => {
            button.addEventListener('click', async (event) => {
                const action = event.target.getAttribute('data-action');
                await this.handleAction(action, nodeData);
            });
        });
    }

    /**
     * Handle action button clicks
     */
    async handleAction(action, nodeData) {
        try {
            switch (action) {
                case 'refresh':
                    await this.showNodeDetails(nodeData);
                    break;
                    
                case 'ping':
                    await this.pingHost(nodeData);
                    break;
                    
                case 'flows':
                    this.showFlows(nodeData);
                    break;
                    
                default:
                    console.warn('Unknown action:', action);
            }
        } catch (error) {
            console.error(`Action ${action} failed:`, error);
            this.showToast('error', 'Action Failed', error.message);
        }
    }

    /**
     * Ping host
     */
    async pingHost(nodeData) {
        const hostData = {
            mac: nodeData.data?.mac || nodeData.id,
            ip: nodeData.data?.ipv4?.[0] || null
        };
        
        if (!hostData.ip) {
            this.showToast('warning', 'Ping Failed', 'No IP address available for this host');
            return;
        }
        
        this.showToast('info', 'Ping Started', `Pinging ${hostData.ip}...`);
        
        const result = await this.api.pingHost(hostData);
        
        if (result.success) {
            this.showToast('success', 'Ping Successful', `Host ${hostData.ip} is reachable`);
        } else {
            this.showToast('error', 'Ping Failed', result.error || 'Host is not reachable');
        }
    }

    /**
     * Show flows (placeholder)
     */
    showFlows(nodeData) {
        this.showToast('info', 'Flow Viewer', 'Flow viewer feature coming soon');
    }

    /**
     * Show toast notification
     */
    showToast(type, title, message) {
        // This would integrate with a toast notification system
        console.log(`Toast [${type}]: ${title} - ${message}`);
    }

    /**
     * Get node title
     */
    getNodeTitle(nodeData) {
        if (nodeData.type === 'switch') {
            const subtype = nodeData.subtype || 'openflow';
            return `${subtype.toUpperCase()} Switch`;
        } else if (nodeData.type === 'host') {
            return 'Host';
        }
        return 'Node Details';
    }

    /**
     * Open the panel
     */
    open() {
        this.panel.classList.add('open');
    }

    /**
     * Close the panel
     */
    close() {
        this.panel.classList.remove('open');
        this.currentNode = null;
        this.currentLink = null;
    }

    /**
     * Check if panel is open
     */
    isOpen() {
        return this.panel.classList.contains('open');
    }
}

export default DetailPanel;
