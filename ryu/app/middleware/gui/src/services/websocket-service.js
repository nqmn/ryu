/**
 * WebSocket Service for Real-time Events
 * 
 * Handles WebSocket connections to the middleware events endpoint
 * with automatic reconnection, event filtering, and error handling.
 */

class WebSocketService {
    constructor(url = null) {
        this.url = url || this.getDefaultWebSocketUrl();
        this.ws = null;
        this.eventHandlers = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 30000;
        this.isConnected = false;
        this.isConnecting = false;
        this.shouldReconnect = true;
        this.heartbeatInterval = null;
        this.heartbeatTimeout = null;
        this.lastHeartbeat = null;
        
        // Event statistics
        this.stats = {
            totalEvents: 0,
            eventsByType: {},
            connectionTime: null,
            lastEventTime: null,
            reconnectCount: 0
        };
        
        // Bind methods
        this.handleOpen = this.handleOpen.bind(this);
        this.handleMessage = this.handleMessage.bind(this);
        this.handleClose = this.handleClose.bind(this);
        this.handleError = this.handleError.bind(this);
        this.sendHeartbeat = this.sendHeartbeat.bind(this);
        this.checkHeartbeat = this.checkHeartbeat.bind(this);
    }

    /**
     * Get default WebSocket URL based on current location
     */
    getDefaultWebSocketUrl() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        return `${protocol}//${host}/v2.0/events/ws`;
    }

    /**
     * Connect to WebSocket
     */
    connect() {
        if (this.isConnected || this.isConnecting) {
            console.log('WebSocket already connected or connecting');
            return;
        }

        this.isConnecting = true;
        this.shouldReconnect = true;

        try {
            console.log(`Connecting to WebSocket: ${this.url}`);
            this.ws = new WebSocket(this.url);
            
            this.ws.onopen = this.handleOpen;
            this.ws.onmessage = this.handleMessage;
            this.ws.onclose = this.handleClose;
            this.ws.onerror = this.handleError;
            
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.isConnecting = false;
            this.scheduleReconnect();
        }
    }

    /**
     * Disconnect from WebSocket
     */
    disconnect() {
        this.shouldReconnect = false;
        this.clearHeartbeat();
        
        if (this.ws) {
            this.ws.close(1000, 'Client disconnect');
            this.ws = null;
        }
        
        this.isConnected = false;
        this.isConnecting = false;
        this.emit('connection', { status: 'disconnected', reason: 'manual' });
    }

    /**
     * Handle WebSocket open event
     */
    handleOpen(event) {
        console.log('WebSocket connected successfully');
        this.isConnected = true;
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.stats.connectionTime = new Date();
        
        // Start heartbeat
        this.startHeartbeat();
        
        this.emit('connection', { 
            status: 'connected', 
            connectionTime: this.stats.connectionTime 
        });
    }

    /**
     * Handle WebSocket message event
     */
    handleMessage(event) {
        try {
            let messageData = event.data;

            // Handle byte string format (remove b' prefix and ' suffix)
            if (typeof messageData === 'string' && messageData.startsWith("b'") && messageData.endsWith("'")) {
                messageData = messageData.slice(2, -1);
                // Unescape any escaped quotes
                messageData = messageData.replace(/\\"/g, '"');
            }

            const data = JSON.parse(messageData);
            this.processMessage(data);
        } catch (error) {
            console.error('Failed to parse WebSocket message:', error, event.data);
            this.emit('error', {
                type: 'parse_error',
                message: 'Failed to parse message',
                data: event.data
            });
        }
    }

    /**
     * Process incoming message
     */
    processMessage(data) {
        // Handle heartbeat responses
        if (data.type === 'pong' || data.event === 'pong') {
            this.lastHeartbeat = Date.now();
            return;
        }

        // Handle RPC-style messages (existing middleware format)
        if (data.method && data.params) {
            const event = {
                timestamp: new Date().toISOString(),
                event: data.method,
                data: data.params,
                raw: data
            };
            this.handleEvent(event);
            
            // Send RPC acknowledgment
            if (data.id) {
                this.sendMessage({
                    id: data.id,
                    jsonrpc: "2.0",
                    result: "ok"
                });
            }
            return;
        }

        // Handle direct event messages (new format)
        if (data.event || data.type) {
            const event = {
                timestamp: data.timestamp || new Date().toISOString(),
                event: data.event || data.type,
                switch_id: data.switch_id,
                src_ip: data.src_ip,
                dst_ip: data.dst_ip,
                protocol: data.protocol,
                data: data,
                raw: data
            };
            this.handleEvent(event);
            return;
        }

        // Handle other message types
        console.log('Received unhandled WebSocket message:', data);
        this.emit('message', data);
    }

    /**
     * Handle processed event
     */
    handleEvent(event) {
        // Update statistics
        this.stats.totalEvents++;
        this.stats.lastEventTime = new Date();
        
        const eventType = event.event;
        if (!this.stats.eventsByType[eventType]) {
            this.stats.eventsByType[eventType] = 0;
        }
        this.stats.eventsByType[eventType]++;

        // Emit event to handlers
        this.emit('event', event);
        this.emit(eventType, event);
    }

    /**
     * Handle WebSocket close event
     */
    handleClose(event) {
        console.log('WebSocket disconnected:', event.code, event.reason);
        this.isConnected = false;
        this.isConnecting = false;
        this.clearHeartbeat();
        
        this.emit('connection', { 
            status: 'disconnected', 
            code: event.code, 
            reason: event.reason 
        });

        // Attempt to reconnect unless it was a clean close
        if (this.shouldReconnect && event.code !== 1000) {
            this.scheduleReconnect();
        }
    }

    /**
     * Handle WebSocket error event
     */
    handleError(error) {
        console.error('WebSocket error:', error);
        this.emit('connection', { status: 'error', error });
        this.emit('error', { type: 'websocket_error', error });
    }

    /**
     * Schedule reconnection attempt
     */
    scheduleReconnect() {
        if (!this.shouldReconnect) {
            return;
        }

        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this.emit('connection', { status: 'failed', reason: 'max_attempts' });
            return;
        }

        this.reconnectAttempts++;
        this.stats.reconnectCount++;
        
        // Exponential backoff with jitter
        const delay = Math.min(
            this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
            this.maxReconnectDelay
        );
        const jitter = Math.random() * 1000;
        const totalDelay = delay + jitter;

        console.log(`Scheduling reconnection attempt ${this.reconnectAttempts} in ${Math.round(totalDelay)}ms`);
        
        this.emit('connection', { 
            status: 'reconnecting', 
            attempt: this.reconnectAttempts, 
            delay: totalDelay 
        });

        setTimeout(() => {
            if (this.shouldReconnect) {
                this.connect();
            }
        }, totalDelay);
    }

    /**
     * Start heartbeat mechanism
     */
    startHeartbeat() {
        this.clearHeartbeat();
        
        // Send ping every 30 seconds
        this.heartbeatInterval = setInterval(this.sendHeartbeat, 30000);
        
        // Check for response every 45 seconds
        this.heartbeatTimeout = setInterval(this.checkHeartbeat, 45000);
        
        this.lastHeartbeat = Date.now();
    }

    /**
     * Send heartbeat ping
     */
    sendHeartbeat() {
        if (this.isConnected) {
            this.sendMessage({ type: 'ping', timestamp: Date.now() });
        }
    }

    /**
     * Check heartbeat response
     */
    checkHeartbeat() {
        if (this.isConnected && this.lastHeartbeat) {
            const timeSinceLastHeartbeat = Date.now() - this.lastHeartbeat;
            
            // If no heartbeat response in 60 seconds, consider connection dead
            if (timeSinceLastHeartbeat > 60000) {
                console.warn('Heartbeat timeout, closing connection');
                this.ws.close(1006, 'Heartbeat timeout');
            }
        }
    }

    /**
     * Clear heartbeat timers
     */
    clearHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
        
        if (this.heartbeatTimeout) {
            clearInterval(this.heartbeatTimeout);
            this.heartbeatTimeout = null;
        }
    }

    /**
     * Send message to WebSocket
     */
    sendMessage(message) {
        if (this.isConnected && this.ws) {
            try {
                this.ws.send(JSON.stringify(message));
            } catch (error) {
                console.error('Failed to send WebSocket message:', error);
                this.emit('error', { type: 'send_error', error, message });
            }
        } else {
            console.warn('Cannot send message: WebSocket not connected');
        }
    }

    /**
     * Subscribe to events
     */
    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, []);
        }
        this.eventHandlers.get(event).push(handler);
        
        // Return unsubscribe function
        return () => this.off(event, handler);
    }

    /**
     * Unsubscribe from events
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
     * Emit event to handlers
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
     * Get connection status
     */
    getStatus() {
        return {
            connected: this.isConnected,
            connecting: this.isConnecting,
            reconnectAttempts: this.reconnectAttempts,
            stats: { ...this.stats }
        };
    }

    /**
     * Reset statistics
     */
    resetStats() {
        this.stats = {
            totalEvents: 0,
            eventsByType: {},
            connectionTime: this.stats.connectionTime,
            lastEventTime: null,
            reconnectCount: 0
        };
    }
}

export default WebSocketService;
