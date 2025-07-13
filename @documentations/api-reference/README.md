# API Reference

Complete API documentation for Ryu Enhanced SDN Framework, covering REST APIs, WebSocket events, and Python APIs.

## 🎯 API Overview

Ryu Enhanced provides multiple API interfaces for different use cases:

| API Type | Purpose | Base URL | Protocol |
|----------|---------|----------|----------|
| **REST API** | Network management and control | `http://localhost:8080/v2.0/` | HTTP/HTTPS |
| **WebSocket API** | Real-time event streaming | `ws://localhost:8080/v2.0/events` | WebSocket |
| **Python API** | Direct library integration | N/A | Python imports |
| **gRPC API** | P4Runtime communication | `localhost:9559` | gRPC |

## 🌐 REST API Reference

### Base Configuration

```
Base URL: http://localhost:8080/v2.0/
Content-Type: application/json
Accept: application/json
```

### Authentication

```bash
# API Key authentication (if enabled)
curl -H "X-API-Key: your-api-key" http://localhost:8080/v2.0/health

# Bearer token authentication (if enabled)
curl -H "Authorization: Bearer your-token" http://localhost:8080/v2.0/health
```

### Core Endpoints

#### Health and Status

```http
GET /v2.0/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "uptime": 3600,
  "controllers": {
    "active": 2,
    "total": 3
  },
  "middleware": {
    "enabled": true,
    "features": ["api", "websocket", "gui"]
  }
}
```

#### System Information

```http
GET /v2.0/info
```

**Response:**
```json
{
  "version": "2.0.0",
  "python_version": "3.10.0",
  "ryu_version": "4.34",
  "features": {
    "middleware": true,
    "p4runtime": true,
    "ml_integration": true,
    "gui": true
  },
  "configuration": {
    "api_port": 8080,
    "controller_port": 6653,
    "websocket_enabled": true
  }
}
```

### Topology Management

#### Get Topology

```http
GET /v2.0/topology
```

**Response:**
```json
{
  "topology_id": "topo_001",
  "name": "default",
  "switches": [
    {
      "dpid": "0000000000000001",
      "ports": [1, 2, 3, 4],
      "controller": "openflow_controller"
    }
  ],
  "hosts": [
    {
      "mac": "00:00:00:00:00:01",
      "ip": "10.0.0.1",
      "connected_to": "0000000000000001",
      "port": 1
    }
  ],
  "links": [
    {
      "src": {"dpid": "0000000000000001", "port": 2},
      "dst": {"dpid": "0000000000000002", "port": 1}
    }
  ]
}
```

#### Create Topology

```http
POST /v2.0/topology
Content-Type: application/json

{
  "name": "test_topology",
  "switches": 3,
  "hosts": 6,
  "links": "linear",
  "controller_type": "openflow"
}
```

**Response:**
```json
{
  "topology_id": "topo_002",
  "status": "created",
  "switches_created": 3,
  "hosts_created": 6,
  "links_created": 2
}
```

#### Delete Topology

```http
DELETE /v2.0/topology/{topology_id}
```

### Flow Management

#### Get Flows

```http
GET /v2.0/flows
GET /v2.0/flows?dpid=0000000000000001
GET /v2.0/flows?table_id=0
```

**Response:**
```json
{
  "flows": [
    {
      "dpid": "0000000000000001",
      "table_id": 0,
      "priority": 100,
      "match": {
        "in_port": 1,
        "eth_dst": "00:00:00:00:00:01"
      },
      "actions": [
        {"type": "OUTPUT", "port": 2}
      ],
      "stats": {
        "packet_count": 1500,
        "byte_count": 150000,
        "duration": 300
      }
    }
  ]
}
```

#### Install Flow

```http
POST /v2.0/flows
Content-Type: application/json

{
  "dpid": "0000000000000001",
  "table_id": 0,
  "priority": 100,
  "match": {
    "in_port": 1,
    "eth_type": 2048,
    "ipv4_dst": "10.0.0.2"
  },
  "actions": [
    {"type": "OUTPUT", "port": 2}
  ],
  "idle_timeout": 300,
  "hard_timeout": 600
}
```

#### Delete Flow

```http
DELETE /v2.0/flows/{flow_id}
DELETE /v2.0/flows?dpid=0000000000000001&table_id=0
```

### Statistics and Monitoring

#### Flow Statistics

```http
GET /v2.0/stats/flows
GET /v2.0/stats/flows/{dpid}
```

#### Port Statistics

```http
GET /v2.0/stats/ports
GET /v2.0/stats/ports/{dpid}
GET /v2.0/stats/ports/{dpid}/{port_no}
```

**Response:**
```json
{
  "port_stats": [
    {
      "dpid": "0000000000000001",
      "port_no": 1,
      "rx_packets": 1000,
      "tx_packets": 950,
      "rx_bytes": 100000,
      "tx_bytes": 95000,
      "rx_dropped": 5,
      "tx_dropped": 2,
      "rx_errors": 0,
      "tx_errors": 0
    }
  ]
}
```

#### Table Statistics

```http
GET /v2.0/stats/tables
GET /v2.0/stats/tables/{dpid}
```

### Traffic Generation

#### Generate Traffic

```http
POST /v2.0/traffic/generate
Content-Type: application/json

{
  "type": "icmp",
  "source": "10.0.0.1",
  "destination": "10.0.0.2",
  "count": 10,
  "interval": 1.0
}
```

```http
POST /v2.0/traffic/generate
Content-Type: application/json

{
  "type": "tcp",
  "source": "10.0.0.1",
  "destination": "10.0.0.2",
  "port": 80,
  "duration": 30,
  "bandwidth": "1Mbps"
}
```

### Controller Management

#### List Controllers

```http
GET /v2.0/controllers
```

**Response:**
```json
{
  "controllers": [
    {
      "id": "openflow_main",
      "type": "openflow",
      "status": "active",
      "host": "localhost",
      "port": 6653,
      "switches": ["0000000000000001", "0000000000000002"],
      "health": {
        "status": "healthy",
        "last_check": "2025-01-13T10:30:00Z",
        "response_time": 5.2
      }
    },
    {
      "id": "p4runtime_main",
      "type": "p4runtime",
      "status": "active",
      "host": "localhost",
      "port": 9559,
      "devices": [1, 2],
      "health": {
        "status": "healthy",
        "last_check": "2025-01-13T10:30:00Z",
        "response_time": 8.1
      }
    }
  ]
}
```

#### Register Controller

```http
POST /v2.0/controllers
Content-Type: application/json

{
  "id": "backup_controller",
  "type": "openflow",
  "host": "192.168.1.100",
  "port": 6653,
  "priority": 2,
  "health_check_interval": 30
}
```

#### Controller Failover

```http
POST /v2.0/controllers/{controller_id}/failover
Content-Type: application/json

{
  "target_controller": "backup_controller",
  "switches": ["0000000000000001"]
}
```

## ⚡ WebSocket API Reference

### Connection

```javascript
const ws = new WebSocket('ws://localhost:8080/v2.0/events');

ws.onopen = function(event) {
    console.log('Connected to Ryu event stream');
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    handleEvent(data);
};
```

### Event Types

#### Topology Events

```json
{
  "type": "topology_change",
  "timestamp": "2025-01-13T10:30:00Z",
  "data": {
    "change_type": "switch_added",
    "dpid": "0000000000000003",
    "controller": "openflow_main"
  }
}
```

#### Flow Events

```json
{
  "type": "flow_mod",
  "timestamp": "2025-01-13T10:30:00Z",
  "data": {
    "dpid": "0000000000000001",
    "table_id": 0,
    "command": "ADD",
    "match": {"in_port": 1},
    "actions": [{"type": "OUTPUT", "port": 2}]
  }
}
```

#### Packet Events

```json
{
  "type": "packet_in",
  "timestamp": "2025-01-13T10:30:00Z",
  "data": {
    "dpid": "0000000000000001",
    "in_port": 1,
    "reason": "NO_MATCH",
    "packet_data": "base64_encoded_packet"
  }
}
```

#### Statistics Events

```json
{
  "type": "stats_update",
  "timestamp": "2025-01-13T10:30:00Z",
  "data": {
    "stats_type": "flow",
    "dpid": "0000000000000001",
    "flows": [
      {
        "table_id": 0,
        "packet_count": 1500,
        "byte_count": 150000
      }
    ]
  }
}
```

### Event Filtering

```javascript
// Subscribe to specific event types
ws.send(JSON.stringify({
    "action": "subscribe",
    "filters": {
        "event_types": ["flow_mod", "packet_in"],
        "dpids": ["0000000000000001"],
        "priority": "high"
    }
}));

// Unsubscribe from events
ws.send(JSON.stringify({
    "action": "unsubscribe",
    "filters": {
        "event_types": ["stats_update"]
    }
}));
```

## 🐍 Python API Reference

### Core Classes

#### MiddlewareApp

```python
from ryu.app.middleware.core import MiddlewareApp

class MyApp(MiddlewareApp):
    def __init__(self, *args, **kwargs):
        super(MyApp, self).__init__(*args, **kwargs)
    
    def on_topology_change(self, event):
        # Handle topology changes
        pass
    
    def on_flow_stats(self, dpid, stats):
        # Handle flow statistics
        pass
```

#### MultiControllerManager

```python
from ryu.app.middleware.multi_controller import MultiControllerManager

manager = MultiControllerManager()

# Register controllers
manager.register_controller("of_ctrl", {
    "type": "openflow",
    "host": "localhost",
    "port": 6653
})

# Get active controller for switch
controller = manager.get_active_controller("0000000000000001")

# Trigger failover
manager.failover_switch("0000000000000001", "backup_ctrl")
```

#### P4RuntimeController

```python
from ryu.app.middleware.p4runtime import P4RuntimeController

controller = P4RuntimeController(
    device_id=1,
    grpc_addr="localhost:9559"
)

# Install table entry
controller.insert_table_entry(
    table_name="forwarding",
    match_fields={"hdr.ethernet.dstAddr": "00:00:00:00:00:01"},
    action_name="forward",
    action_params={"port": 1}
)
```

### Utility Functions

#### Topology Utilities

```python
from ryu.app.middleware.topology import TopologyManager

topo = TopologyManager()

# Create topology
topology_id = topo.create_topology(
    name="test",
    switches=3,
    hosts=6,
    topology_type="linear"
)

# Get topology info
info = topo.get_topology_info(topology_id)

# Generate traffic
topo.generate_traffic(
    src="10.0.0.1",
    dst="10.0.0.2",
    traffic_type="icmp",
    count=10
)
```

#### Statistics Collection

```python
from ryu.app.middleware.stats import StatsCollector

collector = StatsCollector()

# Get flow statistics
flow_stats = collector.get_flow_stats(dpid="0000000000000001")

# Get port statistics
port_stats = collector.get_port_stats(
    dpid="0000000000000001",
    port_no=1
)

# Subscribe to statistics updates
collector.subscribe_stats(
    callback=my_stats_handler,
    interval=10,
    stats_types=["flow", "port"]
)
```

## 🔧 Configuration API

### Runtime Configuration

```http
GET /v2.0/config
PUT /v2.0/config
```

**Configuration Structure:**
```json
{
  "api": {
    "port": 8080,
    "host": "0.0.0.0",
    "cors_enabled": true,
    "rate_limiting": {
      "enabled": true,
      "requests_per_minute": 1000
    }
  },
  "websocket": {
    "enabled": true,
    "max_connections": 100,
    "event_buffer_size": 1000
  },
  "controllers": {
    "health_check_interval": 30,
    "failover_timeout": 10,
    "max_retries": 3
  },
  "logging": {
    "level": "INFO",
    "format": "json",
    "file": "/var/log/ryu/middleware.log"
  }
}
```

## 📊 Error Handling

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource conflict |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily unavailable |

### Error Response Format

```json
{
  "error": {
    "code": "INVALID_TOPOLOGY",
    "message": "Topology configuration is invalid",
    "details": {
      "field": "switches",
      "value": -1,
      "constraint": "must be positive integer"
    },
    "timestamp": "2025-01-13T10:30:00Z",
    "request_id": "req_12345"
  }
}
```

## 🔗 Related Documentation

- **[Getting Started](../getting-started/)** - Basic usage guide
- **[Examples](../examples/)** - Practical implementation examples
- **[Architecture](../architecture/)** - System design details
- **[Installation](../installation/)** - Setup instructions

---

**Need help with the API?** 🚀 Check out our [examples section](../examples/) for practical usage patterns and code samples!
