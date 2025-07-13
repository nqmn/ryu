# Multi-Controller SDN Middleware

## 🎯 Overview

This enhanced SDN middleware extends the existing Ryu-based middleware to support multiple SDN controllers of different types (OpenFlow/Ryu, P4Runtime) with unified management, health monitoring, and automatic failover capabilities.

## 🚀 Key Features

### ✅ Multi-Controller Support
- **Heterogeneous Controllers**: Support for OpenFlow (Ryu) and P4Runtime controllers
- **Unified API**: Single REST API for managing all controller types
- **Dynamic Registration**: Runtime controller registration and deregistration
- **Controller Abstraction**: Protocol-agnostic interface for different SDN technologies

### ✅ Advanced Management
- **Switch Mapping**: Flexible switch-to-controller assignment with backup support
- **Health Monitoring**: Continuous health checks with configurable intervals
- **Automatic Failover**: Seamless failover to backup controllers on failure
- **Manual Failover**: On-demand failover for maintenance or testing

### ✅ Real-time Event System
- **Centralized Events**: Unified event stream from all controllers
- **WebSocket Streaming**: Real-time event broadcasting to clients
- **Event Filtering**: Client-side filtering by event type, controller, or priority
- **Performance Optimized**: Efficient event aggregation and distribution

### ✅ Enhanced Monitoring
- **Controller Metrics**: Uptime, response time, error counts, and activity tracking
- **Switch Statistics**: Per-controller switch counts and connection status
- **Event Analytics**: Event frequency and type distribution
- **Health Dashboards**: Comprehensive health status reporting

## 📁 Architecture

```
ryu/app/middleware/
├── core.py                     # Enhanced main middleware app
├── sdn_backends/
│   ├── base.py                # Enhanced base controller with health monitoring
│   ├── openflow_controller.py # Enhanced OpenFlow controller
│   ├── p4runtime_controller.py# Enhanced P4Runtime controller
│   ├── switch_manager.py      # Existing switch manager
│   └── controller_manager.py  # NEW: Multi-controller manager
├── events/
│   └── event_stream.py        # NEW: Centralized event system
├── models/
│   └── controller_schemas.py  # NEW: Data models and schemas
├── rest_api.py               # Enhanced with controller management endpoints
├── websocket_api.py          # Enhanced with filtering and multi-controller events
└── utils/                    # Existing utilities
```

## 🔧 Installation & Setup

### Prerequisites
- Python 3.10+
- Ryu SDN Framework
- FastAPI dependencies
- WebSocket support

### Quick Start

1. **Start the Enhanced Middleware**:
   ```bash
   python start_middleware.py --verbose
   ```

2. **Run the Demo**:
   ```bash
   python demo_multi_controller.py
   ```

3. **Run Tests**:
   ```bash
   python test_multi_controller.py --verbose
   ```

## 📚 API Reference

### Controller Management

#### Register Controller
```http
POST /v2.0/controllers/register
Content-Type: application/json

{
  "config": {
    "controller_id": "my_controller",
    "controller_type": "ryu_openflow",
    "name": "My OpenFlow Controller",
    "host": "localhost",
    "port": 6653,
    "health_check_interval": 30,
    "priority": 100,
    "backup_controllers": ["backup_controller_id"]
  },
  "auto_start": true
}
```

#### List Controllers
```http
GET /v2.0/controllers/list
```

#### Health Check
```http
GET /v2.0/controllers/health/{controller_id}
```

#### Deregister Controller
```http
DELETE /v2.0/controllers/deregister/{controller_id}
```

### Switch Mapping

#### Map Switch to Controller
```http
POST /v2.0/switches/map
Content-Type: application/json

{
  "switch_id": "switch_1",
  "primary_controller": "controller_1",
  "backup_controllers": ["controller_2", "controller_3"]
}
```

#### Get Switch Mappings
```http
GET /v2.0/switches/mappings
```

#### Manual Failover
```http
POST /v2.0/switches/failover
Content-Type: application/json

{
  "switch_id": "switch_1",
  "target_controller": "backup_controller"
}
```

### Real-time Events

#### WebSocket Connection
```javascript
const ws = new WebSocket('ws://localhost:8080/v2.0/events/ws');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Event:', data.event_type, data.data);
};
```

## 🎮 Usage Examples

### Example 1: Register Multiple Controllers

```python
import requests

# Register OpenFlow controller
openflow_config = {
    "config": {
        "controller_id": "openflow_main",
        "controller_type": "ryu_openflow",
        "name": "Main OpenFlow Controller",
        "host": "10.0.0.1",
        "port": 6653,
        "priority": 100
    },
    "auto_start": True
}

response = requests.post(
    "http://localhost:8080/v2.0/controllers/register",
    json=openflow_config
)

# Register P4Runtime controller
p4_config = {
    "config": {
        "controller_id": "p4_edge",
        "controller_type": "p4runtime",
        "name": "Edge P4 Controller",
        "host": "10.0.0.2",
        "port": 50051,
        "priority": 90,
        "backup_controllers": ["openflow_main"]
    },
    "auto_start": True
}

response = requests.post(
    "http://localhost:8080/v2.0/controllers/register",
    json=p4_config
)
```

### Example 2: Switch Mapping with Failover

```python
# Map core switches to OpenFlow
core_mapping = {
    "switch_id": "core_switch_1",
    "primary_controller": "openflow_main",
    "backup_controllers": ["p4_edge"]
}

requests.post(
    "http://localhost:8080/v2.0/switches/map",
    json=core_mapping
)

# Map edge switches to P4Runtime
edge_mapping = {
    "switch_id": "edge_switch_1", 
    "primary_controller": "p4_edge",
    "backup_controllers": ["openflow_main"]
}

requests.post(
    "http://localhost:8080/v2.0/switches/map",
    json=edge_mapping
)
```

### Example 3: Health Monitoring

```python
# Check health of all controllers
controllers = requests.get("http://localhost:8080/v2.0/controllers/list").json()

for controller in controllers["data"]["controllers"]:
    controller_id = controller["config"]["controller_id"]
    health = requests.get(f"http://localhost:8080/v2.0/controllers/health/{controller_id}")
    
    health_data = health.json()["data"]
    print(f"Controller {controller_id}: {health_data['overall_health']}")
    print(f"  Uptime: {health_data['summary']['uptime_seconds']}s")
    print(f"  Response time: {health_data['checks'][0]['response_time_ms']}ms")
```

## 🔍 Monitoring & Debugging

### Event Types
- `controller_registered` - New controller registered
- `controller_deregistered` - Controller removed
- `switch_mapped` - Switch mapped to controller
- `switch_failover` - Automatic failover occurred
- `manual_failover` - Manual failover performed
- `flow_installed` - Flow rule installed
- `packet_in` - Packet-in event from any controller
- `health_check_failed` - Controller health check failed

### Health Status Levels
- `healthy` - Controller responding normally
- `degraded` - Controller responding but with issues
- `unhealthy` - Controller not responding
- `unknown` - Health status not yet determined

### Logging
The middleware provides structured logging for:
- Controller lifecycle events
- Health monitoring results
- Failover operations
- Event stream statistics
- API request/response details

## 🧪 Testing

### Unit Tests
```bash
python -m pytest tests/test_controller_manager.py
python -m pytest tests/test_event_stream.py
```

### Integration Tests
```bash
python test_multi_controller.py --verbose
```

### Demo
```bash
python demo_multi_controller.py --url http://localhost:8080
```

## 🔧 Configuration

### Controller Manager Configuration
```python
controller_manager = {
    'health_check_interval': 30,      # Health check interval in seconds
    'health_check_timeout': 5,        # Health check timeout in seconds
    'max_health_failures': 3,         # Max failures before failover
}
```

### Event Stream Configuration
```python
event_stream = {
    'max_queue_size': 10000,          # Maximum event queue size
    'max_history_size': 1000,         # Maximum event history
    'cleanup_interval': 300,          # Cleanup interval in seconds
}
```

## 🤝 Contributing

1. Follow existing code patterns and conventions
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Ensure backward compatibility with existing middleware
5. Test with both OpenFlow and P4Runtime scenarios

## 📄 License

Licensed under the Apache License, Version 2.0. See the existing Ryu framework license for details.

## 🆘 Support

For issues and questions:
1. Check the existing middleware documentation
2. Review the test files for usage examples
3. Examine the demo script for complete workflows
4. Check logs for detailed error information
