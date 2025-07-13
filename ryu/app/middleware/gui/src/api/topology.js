/**
 * Topology API Client
 * 
 * Handles communication with the middleware REST API and WebSocket
 * for topology data and real-time events.
 */

class TopologyAPI {
    constructor(baseUrl = '', wsUrl = '') {
        this.baseUrl = baseUrl || window.location.origin;
        this.wsUrl = wsUrl || `ws://${window.location.host}/v2.0/events/ws`;
        this.ws = null;
        this.eventHandlers = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.isConnected = false;
        
        // Bind methods
        this.handleWebSocketMessage = this.handleWebSocketMessage.bind(this);
        this.handleWebSocketOpen = this.handleWebSocketOpen.bind(this);
        this.handleWebSocketClose = this.handleWebSocketClose.bind(this);
        this.handleWebSocketError = this.handleWebSocketError.bind(this);
    }

    /**
     * Initialize the API client
     */
    async initialize() {
        try {
            // Test REST API connectivity
            await this.healthCheck();
            
            // Initialize WebSocket connection
            this.connectWebSocket();
            
            return true;
        } catch (error) {
            console.error('Failed to initialize topology API:', error);
            throw error;
        }
    }

    /**
     * Health check endpoint
     */
    async healthCheck() {
        const response = await this.makeRequest('/v2.0/health');
        return response;
    }

    /**
     * Get current topology data
     */
    async getTopology() {
        const response = await this.makeRequest('/v2.0/topology/view');
        return response;
    }

    /**
     * Get topology statistics
     */
    async getTopologyStats() {
        const response = await this.makeRequest('/v2.0/stats/topology');
        return response;
    }

    /**
     * Get flow statistics for a specific switch
     */
    async getFlowStats(dpid) {
        const response = await this.makeRequest(`/v2.0/stats/flow/${dpid}`);
        return response;
    }

    /**
     * Get port statistics for a specific switch
     */
    async getPortStats(dpid) {
        const response = await this.makeRequest(`/v2.0/stats/port/${dpid}`);
        return response;
    }

    /**
     * Ping a host
     */
    async pingHost(hostData) {
        const response = await this.makeRequest('/v2.0/host/ping', {
            method: 'POST',
            body: JSON.stringify(hostData)
        });
        return response;
    }

    /**
     * Install a flow rule
     */
    async installFlow(flowData) {
        const response = await this.makeRequest('/v2.0/flow/install', {
            method: 'POST',
            body: JSON.stringify(flowData)
        });
        return response;
    }

    /**
     * Make HTTP request to the middleware API
     */
    async makeRequest(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        };

        const requestOptions = { ...defaultOptions, ...options };

        try {
            const response = await fetch(url, requestOptions);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            // Check if the response has an error field
            if (data.error) {
                throw new Error(data.error);
            }

            return data;
        } catch (error) {
            console.error(`API request failed for ${endpoint}:`, error);
            throw error;
        }
    }

    /**
     * Connect to WebSocket for real-time events
     */
    connectWebSocket() {
        try {
            this.ws = new WebSocket(this.wsUrl);
            this.ws.onopen = this.handleWebSocketOpen;
            this.ws.onmessage = this.handleWebSocketMessage;
            this.ws.onclose = this.handleWebSocketClose;
            this.ws.onerror = this.handleWebSocketError;
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.scheduleReconnect();
        }
    }

    /**
     * Handle WebSocket connection open
     */
    handleWebSocketOpen(event) {
        console.log('WebSocket connected');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.emit('connection', { status: 'connected' });
    }

    /**
     * Handle WebSocket message
     */
    handleWebSocketMessage(event) {
        try {
            let messageData = event.data;

            // Handle byte string format (remove b' prefix and ' suffix)
            if (typeof messageData === 'string' && messageData.startsWith("b'") && messageData.endsWith("'")) {
                messageData = messageData.slice(2, -1);
                // Unescape any escaped quotes
                messageData = messageData.replace(/\\"/g, '"');
            }

            const data = JSON.parse(messageData);

            // Handle RPC-style messages
            if (data.method && data.params) {
                this.emit(data.method, data.params);

                // Send acknowledgment for RPC calls
                if (data.id) {
                    this.ws.send(JSON.stringify({
                        id: data.id,
                        jsonrpc: "2.0",
                        result: "ok"
                    }));
                }
            }
            // Handle direct event messages
            else if (data.event && data.data) {
                this.emit(data.event, data.data);
            }
            // Handle other message formats
            else {
                console.log('Received WebSocket message:', data);
            }
        } catch (error) {
            console.error('Failed to parse WebSocket message:', error, event.data);
        }
    }

    /**
     * Handle WebSocket connection close
     */
    handleWebSocketClose(event) {
        console.log('WebSocket disconnected:', event.code, event.reason);
        this.isConnected = false;
        this.emit('connection', { status: 'disconnected' });
        
        // Attempt to reconnect unless it was a clean close
        if (event.code !== 1000) {
            this.scheduleReconnect();
        }
    }

    /**
     * Handle WebSocket error
     */
    handleWebSocketError(error) {
        console.error('WebSocket error:', error);
        this.emit('connection', { status: 'error', error });
    }

    /**
     * Schedule WebSocket reconnection
     */
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this.emit('connection', { status: 'failed' });
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        
        console.log(`Scheduling reconnection attempt ${this.reconnectAttempts} in ${delay}ms`);
        
        setTimeout(() => {
            this.connectWebSocket();
        }, delay);
    }

    /**
     * Subscribe to WebSocket events
     */
    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, []);
        }
        this.eventHandlers.get(event).push(handler);
    }

    /**
     * Unsubscribe from WebSocket events
     */
    off(event, handler) {
        if (this.eventHandlers.has(event)) {
            const handlers = this.eventHandlers.get(event);
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
            }
        }
    }

    /**
     * Emit event to registered handlers
     */
    emit(event, data) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in event handler for ${event}:`, error);
                }
            });
        }
    }

    /**
     * Close WebSocket connection
     */
    disconnect() {
        if (this.ws) {
            this.ws.close(1000, 'Client disconnect');
            this.ws = null;
        }
        this.isConnected = false;
    }

    /**
     * Get connection status
     */
    getConnectionStatus() {
        return {
            connected: this.isConnected,
            reconnectAttempts: this.reconnectAttempts
        };
    }
}

export default TopologyAPI;
