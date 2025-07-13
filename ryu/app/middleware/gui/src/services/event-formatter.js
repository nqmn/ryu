/**
 * Event Formatter for Terminal Display
 * 
 * Formats JSON events into styled, color-coded terminal lines
 * with proper timestamp formatting and event categorization.
 */

class EventFormatter {
    constructor() {
        // Event type configurations
        this.eventTypes = {
            // Flow events (Green)
            'flow_mod': { 
                color: 'success', 
                icon: '⚡', 
                category: 'flow',
                description: 'Flow modification'
            },
            'flow_removed': { 
                color: 'success', 
                icon: '🗑️', 
                category: 'flow',
                description: 'Flow removed'
            },
            'event_flow_removed': { 
                color: 'success', 
                icon: '🗑️', 
                category: 'flow',
                description: 'Flow removed'
            },
            
            // Packet events (Yellow/Warning)
            'packet_in': { 
                color: 'warning', 
                icon: '📦', 
                category: 'packet',
                description: 'Packet received'
            },
            'packet_out': { 
                color: 'warning', 
                icon: '📤', 
                category: 'packet',
                description: 'Packet sent'
            },
            
            // Switch events (Blue/Info)
            'switch_enter': { 
                color: 'info', 
                icon: '🔌', 
                category: 'topology',
                description: 'Switch connected'
            },
            'switch_leave': { 
                color: 'info', 
                icon: '🔌', 
                category: 'topology',
                description: 'Switch disconnected'
            },
            'event_switch_enter': { 
                color: 'info', 
                icon: '🔌', 
                category: 'topology',
                description: 'Switch connected'
            },
            'event_switch_leave': { 
                color: 'info', 
                icon: '🔌', 
                category: 'topology',
                description: 'Switch disconnected'
            },
            
            // Link events (Blue/Info)
            'link_add': { 
                color: 'info', 
                icon: '🔗', 
                category: 'topology',
                description: 'Link added'
            },
            'link_delete': { 
                color: 'info', 
                icon: '🔗', 
                category: 'topology',
                description: 'Link removed'
            },
            'event_link_add': { 
                color: 'info', 
                icon: '🔗', 
                category: 'topology',
                description: 'Link added'
            },
            'event_link_delete': { 
                color: 'info', 
                icon: '🔗', 
                category: 'topology',
                description: 'Link removed'
            },
            
            // Host events (Blue/Info)
            'host_add': { 
                color: 'info', 
                icon: '💻', 
                category: 'topology',
                description: 'Host discovered'
            },
            
            // Port events (Blue/Info)
            'port_status': { 
                color: 'info', 
                icon: '🔌', 
                category: 'topology',
                description: 'Port status change'
            },
            
            // Alert events (Red/Danger)
            'alert': { 
                color: 'danger', 
                icon: '⚠️', 
                category: 'alert',
                description: 'System alert'
            },
            'traffic_alert': { 
                color: 'danger', 
                icon: '⚠️', 
                category: 'alert',
                description: 'Traffic alert'
            },
            
            // Error events (Red/Danger)
            'error': { 
                color: 'danger', 
                icon: '❌', 
                category: 'error',
                description: 'System error'
            },
            
            // ML events (Purple/Secondary)
            'ml_prediction': { 
                color: 'secondary', 
                icon: '🤖', 
                category: 'ml',
                description: 'ML prediction'
            },
            
            // Default for unknown events
            'unknown': { 
                color: 'muted', 
                icon: '❓', 
                category: 'unknown',
                description: 'Unknown event'
            }
        };
        
        // Protocol mappings
        this.protocols = {
            1: 'ICMP',
            6: 'TCP',
            17: 'UDP',
            2: 'IGMP',
            89: 'OSPF'
        };
    }

    /**
     * Format event into terminal line
     */
    formatEvent(event) {
        const eventConfig = this.getEventConfig(event.event);
        const timestamp = this.formatTimestamp(event.timestamp);
        const eventType = event.event || 'unknown';
        
        return {
            id: this.generateEventId(event),
            timestamp: timestamp,
            timestampRaw: event.timestamp,
            eventType: eventType,
            category: eventConfig.category,
            color: eventConfig.color,
            icon: eventConfig.icon,
            description: eventConfig.description,
            message: this.formatMessage(event),
            details: this.formatDetails(event),
            searchText: this.generateSearchText(event),
            raw: event
        };
    }

    /**
     * Get event configuration
     */
    getEventConfig(eventType) {
        return this.eventTypes[eventType] || this.eventTypes.unknown;
    }

    /**
     * Format timestamp
     */
    formatTimestamp(timestamp) {
        try {
            const date = new Date(timestamp);
            return {
                full: date.toISOString(),
                time: date.toLocaleTimeString('en-US', { 
                    hour12: false, 
                    hour: '2-digit', 
                    minute: '2-digit', 
                    second: '2-digit',
                    fractionalSecondDigits: 3
                }),
                date: date.toLocaleDateString('en-US'),
                relative: this.getRelativeTime(date)
            };
        } catch (error) {
            return {
                full: timestamp,
                time: timestamp,
                date: '',
                relative: 'now'
            };
        }
    }

    /**
     * Get relative time string
     */
    getRelativeTime(date) {
        const now = new Date();
        const diffMs = now - date;
        const diffSecs = Math.floor(diffMs / 1000);
        const diffMins = Math.floor(diffSecs / 60);
        const diffHours = Math.floor(diffMins / 60);
        
        if (diffSecs < 60) {
            return `${diffSecs}s ago`;
        } else if (diffMins < 60) {
            return `${diffMins}m ago`;
        } else if (diffHours < 24) {
            return `${diffHours}h ago`;
        } else {
            return date.toLocaleDateString();
        }
    }

    /**
     * Format main message
     */
    formatMessage(event) {
        const eventType = event.event || 'unknown';
        
        switch (eventType) {
            case 'packet_in':
                return this.formatPacketInMessage(event);
            case 'flow_mod':
            case 'flow_removed':
            case 'event_flow_removed':
                return this.formatFlowMessage(event);
            case 'switch_enter':
            case 'event_switch_enter':
                return this.formatSwitchEnterMessage(event);
            case 'switch_leave':
            case 'event_switch_leave':
                return this.formatSwitchLeaveMessage(event);
            case 'link_add':
            case 'event_link_add':
                return this.formatLinkAddMessage(event);
            case 'link_delete':
            case 'event_link_delete':
                return this.formatLinkDeleteMessage(event);
            case 'host_add':
                return this.formatHostAddMessage(event);
            case 'alert':
            case 'traffic_alert':
                return this.formatAlertMessage(event);
            case 'error':
                return this.formatErrorMessage(event);
            case 'ml_prediction':
                return this.formatMLMessage(event);
            default:
                return this.formatGenericMessage(event);
        }
    }

    /**
     * Format packet_in message
     */
    formatPacketInMessage(event) {
        const src = event.src_ip || event.data?.src_ip || 'unknown';
        const dst = event.dst_ip || event.data?.dst_ip || 'unknown';
        const protocol = this.getProtocolName(event.protocol || event.data?.protocol);
        const switchId = event.switch_id || event.data?.switch_id || event.data?.dpid || 'unknown';
        
        return `${protocol} packet from ${src} to ${dst} on switch ${switchId}`;
    }

    /**
     * Format flow message
     */
    formatFlowMessage(event) {
        const switchId = event.switch_id || event.data?.switch_id || event.data?.dpid || 'unknown';
        const action = event.event.includes('removed') ? 'removed from' : 'installed on';
        
        return `Flow ${action} switch ${switchId}`;
    }

    /**
     * Format switch enter message
     */
    formatSwitchEnterMessage(event) {
        const switchId = event.switch_id || event.data?.dpid || 'unknown';
        return `Switch ${switchId} connected`;
    }

    /**
     * Format switch leave message
     */
    formatSwitchLeaveMessage(event) {
        const switchId = event.switch_id || event.data?.dpid || 'unknown';
        return `Switch ${switchId} disconnected`;
    }

    /**
     * Format link add message
     */
    formatLinkAddMessage(event) {
        const src = event.data?.src?.dpid || 'unknown';
        const dst = event.data?.dst?.dpid || 'unknown';
        return `Link added between ${src} and ${dst}`;
    }

    /**
     * Format link delete message
     */
    formatLinkDeleteMessage(event) {
        const src = event.data?.src?.dpid || 'unknown';
        const dst = event.data?.dst?.dpid || 'unknown';
        return `Link removed between ${src} and ${dst}`;
    }

    /**
     * Format host add message
     */
    formatHostAddMessage(event) {
        const mac = event.data?.mac || 'unknown';
        const switchId = event.data?.port?.dpid || 'unknown';
        return `Host ${mac} discovered on switch ${switchId}`;
    }

    /**
     * Format alert message
     */
    formatAlertMessage(event) {
        const message = event.data?.message || event.message || 'Alert triggered';
        return message;
    }

    /**
     * Format error message
     */
    formatErrorMessage(event) {
        const message = event.data?.message || event.message || 'Error occurred';
        return message;
    }

    /**
     * Format ML message
     */
    formatMLMessage(event) {
        const prediction = event.data?.prediction || 'prediction';
        const confidence = event.data?.confidence || '';
        return `ML ${prediction}${confidence ? ` (${Math.round(confidence * 100)}%)` : ''}`;
    }

    /**
     * Format generic message
     */
    formatGenericMessage(event) {
        const eventType = event.event || 'event';
        const switchId = event.switch_id || event.data?.switch_id || event.data?.dpid;
        
        if (switchId) {
            return `${eventType} on switch ${switchId}`;
        }
        
        return `${eventType} occurred`;
    }

    /**
     * Format detailed information
     */
    formatDetails(event) {
        const details = {};
        
        // Add common fields
        if (event.switch_id) details.switch_id = event.switch_id;
        if (event.src_ip) details.src_ip = event.src_ip;
        if (event.dst_ip) details.dst_ip = event.dst_ip;
        if (event.protocol) details.protocol = this.getProtocolName(event.protocol);
        
        // Add data fields
        if (event.data) {
            Object.keys(event.data).forEach(key => {
                if (!details[key] && event.data[key] !== null && event.data[key] !== undefined) {
                    details[key] = event.data[key];
                }
            });
        }
        
        return details;
    }

    /**
     * Get protocol name
     */
    getProtocolName(protocol) {
        if (typeof protocol === 'string') {
            return protocol.toUpperCase();
        }
        
        return this.protocols[protocol] || `Protocol ${protocol}`;
    }

    /**
     * Generate search text for filtering
     */
    generateSearchText(event) {
        const parts = [
            event.event,
            event.switch_id,
            event.src_ip,
            event.dst_ip,
            this.getProtocolName(event.protocol),
            JSON.stringify(event.data)
        ];
        
        return parts.filter(Boolean).join(' ').toLowerCase();
    }

    /**
     * Generate unique event ID
     */
    generateEventId(event) {
        const timestamp = new Date(event.timestamp).getTime();
        const eventType = event.event || 'unknown';
        const random = Math.random().toString(36).substr(2, 9);
        
        return `${eventType}_${timestamp}_${random}`;
    }

    /**
     * Format event for export
     */
    formatForExport(event, format = 'json') {
        switch (format) {
            case 'json':
                return JSON.stringify(event.raw, null, 2);
            case 'csv':
                return this.formatForCSV(event);
            case 'log':
                return this.formatForLog(event);
            default:
                return JSON.stringify(event.raw);
        }
    }

    /**
     * Format event for CSV export
     */
    formatForCSV(event) {
        const fields = [
            event.timestamp.full,
            event.eventType,
            event.message,
            event.details.switch_id || '',
            event.details.src_ip || '',
            event.details.dst_ip || '',
            event.details.protocol || ''
        ];
        
        return fields.map(field => `"${String(field).replace(/"/g, '""')}"`).join(',');
    }

    /**
     * Format event for log export
     */
    formatForLog(event) {
        return `[${event.timestamp.full}] ${event.eventType.toUpperCase()}: ${event.message}`;
    }

    /**
     * Get CSV header
     */
    getCSVHeader() {
        return 'Timestamp,Event Type,Message,Switch ID,Source IP,Destination IP,Protocol';
    }
}

export default EventFormatter;
