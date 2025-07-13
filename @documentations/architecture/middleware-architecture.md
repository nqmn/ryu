# Ryu Middleware API

A comprehensive middleware API that bridges communication between the Ryu SDN controller, Mininet emulator, and external AI/ML modules or dashboards.

## 🎯 Overview

The Ryu Middleware API provides a unified RESTful and WebSocket interface for:

- **Topology Management**: Create, view, and manage network topologies via Mininet integration
- **Traffic Generation**: Generate ICMP, TCP, and UDP traffic for testing and simulation
- **Flow Management**: Install, view, and delete OpenFlow rules dynamically
- **Real-time Monitoring**: Collect and stream flow, port, and packet statistics
- **Event Streaming**: Real-time WebSocket events for topology changes and network events
- **AI/ML Integration**: Plugin architecture for external ML inference and alerting

## 🚀 Quick Start

### 1. Installation

The middleware is included with the modernized Ryu framework. Install dependencies:

```bash
# Install with middleware support
pip install -e .[middleware]

# Or install individual dependencies
pip install pyyaml requests scapy psutil
```

### 2. Start the Middleware

```bash
# Start Ryu with middleware
ryu-manager ryu.app.middleware.core

# Or with additional apps
ryu-manager ryu.app.middleware.core ryu.app.simple_switch_13
```

### 3. Test the API

```bash
# Run the test suite
python test_middleware.py

# Check health
curl http://localhost:8080/v2.0/health
```

## 📚 API Documentation

### REST API Endpoints

#### Topology Management
- `GET /v2.0/topology/view` - Get current topology
- `POST /v2.0/topology/create` - Create topology from JSON/YAML
- `DELETE /v2.0/topology/delete` - Delete current topology
- `GET /v2.0/topology/status` - Get topology status

#### Host Operations
- `GET /v2.0/host/list` - List all hosts
- `POST /v2.0/host/ping` - Perform connectivity tests

#### Traffic Generation
- `POST /v2.0/traffic/generate` - Generate network traffic
- `GET /v2.0/traffic/status` - Get active traffic sessions

#### Flow Management
- `GET /v2.0/flow/view/{dpid}` - View flow tables
- `POST /v2.0/flow/install` - Install flow rules
- `DELETE /v2.0/flow/delete` - Delete flow rules

#### Statistics & Monitoring
- `GET /v2.0/stats/flow[/{dpid}]` - Flow statistics
- `GET /v2.0/stats/port[/{dpid}]` - Port statistics
- `GET /v2.0/stats/packet` - Packet-in statistics
- `GET /v2.0/stats/topology` - Topology metrics

#### AI/ML Integration
- `POST /v2.0/ml/infer` - ML inference requests
- `GET /v2.0/ml/models` - List available models
- `POST /v2.0/ml/alert` - Configure ML alerts

#### Health & Status
- `GET /v2.0/health` - Health check

### WebSocket Events

Connect to `ws://localhost:8080/v2.0/events/ws` for real-time events:

- `switch_enter/leave` - Switch connection events
- `link_add/delete` - Link topology changes
- `host_add` - Host discovery events
- `packet_in` - Packet-in events (filtered)
- `flow_removed` - Flow expiration events
- `port_status` - Port status changes
- `ml_prediction` - ML inference results
- `traffic_alert` - Traffic anomaly alerts

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Ryu Middleware API                       │
├─────────────────────────────────────────────────────────────┤
│  REST API Controller  │  WebSocket Controller               │
├─────────────────────────────────────────────────────────────┤
│ Mininet │ Traffic │ Monitoring │ ML Integration │ Core      │
│ Bridge  │ Gen     │ Service    │ Service        │ App       │
├─────────────────────────────────────────────────────────────┤
│                    Ryu SDN Framework                        │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

- **Core App**: Main middleware coordinator
- **Mininet Bridge**: Topology creation and management
- **Traffic Generator**: Network traffic simulation
- **Monitoring Service**: Statistics collection and flow management
- **ML Integration**: AI/ML plugin framework
- **REST/WebSocket APIs**: Unified interface layer

## 📋 Usage Examples

### Create a Topology

```python
import requests

topology = {
    "name": "simple_topology",
    "switches": [{"name": "s1"}],
    "hosts": [
        {"name": "h1", "ip": "10.0.0.1"},
        {"name": "h2", "ip": "10.0.0.2"}
    ],
    "links": [
        {"src": "h1", "dst": "s1"},
        {"src": "h2", "dst": "s1"}
    ]
}

response = requests.post(
    "http://localhost:8080/v2.0/topology/create",
    json=topology
)
print(response.json())
```

### Generate Traffic

```python
traffic_spec = {
    "type": "icmp",
    "src": "h1",
    "dst": "h2",
    "count": 10,
    "interval": 1
}

response = requests.post(
    "http://localhost:8080/v2.0/traffic/generate",
    json=traffic_spec
)
print(response.json())
```

### Install Flow Rule

```python
flow_rule = {
    "dpid": 1,
    "match": {"in_port": 1},
    "actions": [{"type": "OUTPUT", "port": 2}],
    "priority": 100
}

response = requests.post(
    "http://localhost:8080/v2.0/flow/install",
    json=flow_rule
)
print(response.json())
```

### WebSocket Events

```python
import websocket
import json

def on_message(ws, message):
    event = json.loads(message)
    print(f"Event: {event['event_type']}")
    print(f"Data: {event['data']}")

ws = websocket.WebSocketApp(
    "ws://localhost:8080/v2.0/events/ws",
    on_message=on_message
)
ws.run_forever()
```

## ⚙️ Configuration

Create a configuration file `middleware_config.yaml`:

```yaml
middleware:
  mininet:
    enabled: true
    python_path: "/usr/bin/python3"
    cleanup_on_exit: true
    timeout: 30
  
  traffic:
    tools: ["hping3", "iperf3", "scapy"]
    max_concurrent: 10
    timeout: 60
  
  ml:
    enabled: false
    providers: []
    timeout: 30
  
  websocket:
    max_connections: 100
    heartbeat_interval: 30
  
  monitoring:
    enabled: true
    interval: 5
    stats_retention_time: 3600
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Basic functionality tests
python test_middleware.py

# Usage examples
python examples/middleware_usage.py

# Manual API testing
curl -X GET http://localhost:8080/v2.0/health
curl -X GET http://localhost:8080/v2.0/topology/view
curl -X GET http://localhost:8080/v2.0/stats/flow
```

## 🔧 Development

### Adding New Features

1. **REST Endpoints**: Add to `rest_api.py`
2. **WebSocket Events**: Add to `websocket_api.py`
3. **Services**: Create new modules in the middleware package
4. **ML Providers**: Implement the `MLProvider` interface

### Project Structure

```
ryu/app/middleware/
├── __init__.py           # Package initialization
├── core.py              # Main middleware app
├── rest_api.py          # REST API controller
├── websocket_api.py     # WebSocket controller
├── mininet_bridge.py    # Mininet integration
├── traffic_gen.py       # Traffic generation
├── monitoring.py        # Monitoring service
├── ml_integration.py    # ML integration
└── utils.py            # Common utilities
```

## 🤝 Contributing

1. Follow the existing code style and patterns
2. Add tests for new functionality
3. Update documentation
4. Ensure backward compatibility with v1.0 APIs

## 📄 License

Licensed under the Apache License 2.0 - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check the inline code documentation
- **Examples**: See the `examples/` directory
- **Issues**: Report bugs and feature requests on GitHub
- **Testing**: Use `test_middleware.py` to verify functionality
