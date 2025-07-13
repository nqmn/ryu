# Examples and Tutorials

Comprehensive collection of examples, tutorials, and practical implementations for Ryu Enhanced SDN Framework.

## 🎯 Quick Navigation

| Category | Description | Difficulty |
|----------|-------------|------------|
| [Basic SDN](#-basic-sdn-examples) | Fundamental SDN concepts | Beginner |
| [Middleware API](#-middleware-api-examples) | REST API and WebSocket usage | Intermediate |
| [Multi-Controller](#-multi-controller-examples) | Advanced controller management | Advanced |
| [AI/ML Integration](#-aiml-integration) | Machine learning examples | Advanced |
| [GUI Applications](#-gui-applications) | Web interface examples | Intermediate |
| [P4Runtime](#-p4runtime-examples) | P4 programming examples | Advanced |

## 🚀 Basic SDN Examples

### Simple Learning Switch

**File**: `examples/basic/simple_switch.py`

A basic learning switch that demonstrates fundamental OpenFlow concepts:

```python
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3

class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    # Implementation details...
```

**Run**: `ryu-manager examples/basic/simple_switch.py`

### Traffic Monitor

**File**: `examples/basic/traffic_monitor.py`

Monitor network traffic and collect statistics:

```python
class TrafficMonitor(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(TrafficMonitor, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.monitor_thread = hub.spawn(self._monitor)

    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                self._request_stats(dp)
            hub.sleep(10)
```

**Run**: `ryu-manager examples/basic/traffic_monitor.py`

### Load Balancer

**File**: `examples/basic/load_balancer.py`

Simple round-robin load balancer implementation:

```python
class LoadBalancer(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(LoadBalancer, self).__init__(*args, **kwargs)
        self.servers = ['10.0.0.2', '10.0.0.3', '10.0.0.4']
        self.current_server = 0
```

**Run**: `ryu-manager examples/basic/load_balancer.py`

## 🔌 Middleware API Examples

### REST API Usage

**File**: `examples/middleware/api_client.py`

Comprehensive example of using the REST API:

```python
import requests
import json

class RyuAPIClient:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url

    def get_topology(self):
        response = requests.get(f"{self.base_url}/v2.0/topology")
        return response.json()

    def create_topology(self, name, switches, hosts):
        data = {
            "name": name,
            "switches": switches,
            "hosts": hosts
        }
        response = requests.post(
            f"{self.base_url}/v2.0/topology",
            json=data
        )
        return response.json()

# Usage example
client = RyuAPIClient()
topology = client.create_topology("test", 3, 6)
print(f"Created topology: {topology}")
```

**Run**: `python examples/middleware/api_client.py`

### WebSocket Event Streaming

**File**: `examples/middleware/websocket_client.py`

Real-time event monitoring using WebSocket:

```python
import asyncio
import websockets
import json

async def event_monitor():
    uri = "ws://localhost:8080/v2.0/events"
    
    async with websockets.connect(uri) as websocket:
        print("Connected to Ryu event stream")
        
        async for message in websocket:
            event = json.loads(message)
            print(f"Event: {event['type']} - {event['data']}")

# Run the event monitor
asyncio.run(event_monitor())
```

**Run**: `python examples/middleware/websocket_client.py`

### Traffic Generation

**File**: `examples/middleware/traffic_generator.py`

Generate various types of network traffic for testing:

```python
class TrafficGenerator:
    def __init__(self, api_client):
        self.client = api_client

    def generate_icmp_traffic(self, src, dst, count=10):
        data = {
            "type": "icmp",
            "source": src,
            "destination": dst,
            "count": count
        }
        return self.client.post("/v2.0/traffic/generate", json=data)

    def generate_tcp_traffic(self, src, dst, port, duration=30):
        data = {
            "type": "tcp",
            "source": src,
            "destination": dst,
            "port": port,
            "duration": duration
        }
        return self.client.post("/v2.0/traffic/generate", json=data)
```

**Run**: `python examples/middleware/traffic_generator.py`

## 🎛️ Multi-Controller Examples

### Controller Registration

**File**: `examples/multi_controller/register_controllers.py`

Register multiple controllers dynamically:

```python
from ryu.app.middleware.multi_controller import MultiControllerManager

# Register OpenFlow controller
openflow_config = {
    "type": "openflow",
    "host": "localhost",
    "port": 6653,
    "version": "1.3"
}

# Register P4Runtime controller
p4runtime_config = {
    "type": "p4runtime",
    "host": "localhost", 
    "port": 9559,
    "device_id": 1
}

manager = MultiControllerManager()
manager.register_controller("of_controller", openflow_config)
manager.register_controller("p4_controller", p4runtime_config)
```

**Run**: `python examples/multi_controller/register_controllers.py`

### Failover Testing

**File**: `examples/multi_controller/failover_test.py`

Test automatic failover capabilities:

```python
class FailoverTest:
    def __init__(self):
        self.manager = MultiControllerManager()

    def test_controller_failover(self):
        # Simulate controller failure
        self.manager.simulate_failure("primary_controller")
        
        # Verify failover to backup
        active_controller = self.manager.get_active_controller("switch_1")
        assert active_controller == "backup_controller"
        
        # Test recovery
        self.manager.recover_controller("primary_controller")
        time.sleep(5)  # Wait for recovery
        
        active_controller = self.manager.get_active_controller("switch_1")
        assert active_controller == "primary_controller"
```

**Run**: `python examples/multi_controller/failover_test.py`

## 🧠 AI/ML Integration

### Anomaly Detection

**File**: `examples/ml/anomaly_detection.py`

Machine learning-based network anomaly detection:

```python
import numpy as np
from sklearn.ensemble import IsolationForest
from ryu.app.middleware.ml import MLPlugin

class AnomalyDetector(MLPlugin):
    def __init__(self):
        super().__init__()
        self.model = IsolationForest(contamination=0.1)
        self.feature_buffer = []

    def process_flow_stats(self, stats):
        features = self.extract_features(stats)
        self.feature_buffer.append(features)
        
        if len(self.feature_buffer) >= 100:
            # Train model
            X = np.array(self.feature_buffer)
            self.model.fit(X)
            
            # Detect anomalies
            predictions = self.model.predict(X)
            anomalies = X[predictions == -1]
            
            if len(anomalies) > 0:
                self.alert_anomaly(anomalies)

    def extract_features(self, stats):
        return [
            stats['packet_count'],
            stats['byte_count'],
            stats['duration'],
            stats['packets_per_second']
        ]
```

**Run**: `ryu-manager examples/ml/anomaly_detection.py`

### Traffic Prediction

**File**: `examples/ml/traffic_prediction.py`

Predict network traffic patterns using time series analysis:

```python
import tensorflow as tf
from ryu.app.middleware.ml import MLPlugin

class TrafficPredictor(MLPlugin):
    def __init__(self):
        super().__init__()
        self.model = self.build_lstm_model()
        self.traffic_history = []

    def build_lstm_model(self):
        model = tf.keras.Sequential([
            tf.keras.layers.LSTM(50, return_sequences=True),
            tf.keras.layers.LSTM(50),
            tf.keras.layers.Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse')
        return model

    def predict_traffic(self, current_stats):
        # Prepare input data
        input_data = self.prepare_input(current_stats)
        
        # Make prediction
        prediction = self.model.predict(input_data)
        
        # Take proactive actions if needed
        if prediction > self.threshold:
            self.trigger_load_balancing()
```

**Run**: `ryu-manager examples/ml/traffic_prediction.py`

## 🖥️ GUI Applications

### Interactive Topology Viewer

**File**: `examples/gui/topology_viewer.html`

Web-based interactive topology visualization:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Ryu Topology Viewer</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
</head>
<body>
    <div id="topology"></div>
    <script>
        // WebSocket connection for real-time updates
        const ws = new WebSocket('ws://localhost:8080/v2.0/events');
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            if (data.type === 'topology_change') {
                updateTopology(data.topology);
            }
        };

        function updateTopology(topology) {
            // D3.js visualization code
            const svg = d3.select("#topology")
                .append("svg")
                .attr("width", 800)
                .attr("height", 600);
            
            // Render nodes and links
            // ... D3.js implementation
        }
    </script>
</body>
</html>
```

**Access**: `http://localhost:8080/gui/topology_viewer.html`

### Network Dashboard

**File**: `examples/gui/dashboard.html`

Comprehensive network monitoring dashboard:

```javascript
class NetworkDashboard {
    constructor() {
        this.ws = new WebSocket('ws://localhost:8080/v2.0/events');
        this.setupEventHandlers();
        this.initializeCharts();
    }

    setupEventHandlers() {
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.updateDashboard(data);
        };
    }

    updateDashboard(data) {
        switch(data.type) {
            case 'flow_stats':
                this.updateFlowChart(data.stats);
                break;
            case 'port_stats':
                this.updatePortChart(data.stats);
                break;
            case 'topology_change':
                this.updateTopology(data.topology);
                break;
        }
    }
}
```

**Access**: `http://localhost:8080/gui/dashboard.html`

## 🔧 P4Runtime Examples

### Basic P4 Program

**File**: `examples/p4/basic_forwarding.p4`

Simple P4 program for basic forwarding:

```p4
#include <core.p4>
#include <v1model.p4>

header ethernet_t {
    bit<48> dstAddr;
    bit<48> srcAddr;
    bit<16> etherType;
}

struct headers {
    ethernet_t ethernet;
}

struct metadata {
    /* empty */
}

parser MyParser(packet_in packet,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {
    state start {
        packet.extract(hdr.ethernet);
        transition accept;
    }
}

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {
    
    action forward(bit<9> port) {
        standard_metadata.egress_spec = port;
    }
    
    action drop() {
        mark_to_drop(standard_metadata);
    }
    
    table forwarding {
        key = {
            hdr.ethernet.dstAddr: exact;
        }
        actions = {
            forward;
            drop;
        }
        default_action = drop();
    }
    
    apply {
        forwarding.apply();
    }
}

// ... rest of P4 program
```

### P4Runtime Controller

**File**: `examples/p4/p4runtime_controller.py`

Python controller for P4Runtime:

```python
from ryu.app.middleware.p4runtime import P4RuntimeController

class BasicP4Controller(P4RuntimeController):
    def __init__(self):
        super().__init__()
        self.p4_program = "examples/p4/basic_forwarding.p4"

    def install_forwarding_rules(self):
        # Install table entries
        table_entry = {
            "table_name": "forwarding",
            "match_fields": {
                "hdr.ethernet.dstAddr": "00:00:00:00:00:01"
            },
            "action": {
                "name": "forward",
                "params": {"port": 1}
            }
        }
        self.insert_table_entry(table_entry)
```

**Run**: `ryu-manager examples/p4/p4runtime_controller.py`

## 🧪 Testing Examples

### Unit Tests

**File**: `examples/testing/test_middleware.py`

Comprehensive middleware testing:

```python
import pytest
import requests
from ryu.app.middleware.core import MiddlewareApp

class TestMiddleware:
    def setup_method(self):
        self.app = MiddlewareApp()
        self.base_url = "http://localhost:8080"

    def test_health_endpoint(self):
        response = requests.get(f"{self.base_url}/v2.0/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_topology_creation(self):
        data = {"name": "test", "switches": 2, "hosts": 4}
        response = requests.post(
            f"{self.base_url}/v2.0/topology",
            json=data
        )
        assert response.status_code == 201
        assert "topology_id" in response.json()
```

**Run**: `pytest examples/testing/test_middleware.py`

### Integration Tests

**File**: `examples/testing/test_integration.py`

End-to-end integration testing:

```python
class TestIntegration:
    def test_full_workflow(self):
        # Create topology
        topology = self.create_test_topology()
        
        # Generate traffic
        self.generate_test_traffic(topology)
        
        # Verify flow installation
        flows = self.get_flow_stats()
        assert len(flows) > 0
        
        # Test failover
        self.simulate_controller_failure()
        
        # Verify backup controller takes over
        assert self.verify_backup_active()
```

**Run**: `pytest examples/testing/test_integration.py`

## 📚 Tutorial Series

### Tutorial 1: Building Your First SDN App

**File**: `examples/tutorials/tutorial_01_first_app.md`

Step-by-step guide to building a basic SDN application.

### Tutorial 2: REST API Integration

**File**: `examples/tutorials/tutorial_02_api_integration.md`

Learn to integrate with the Ryu Enhanced REST API.

### Tutorial 3: Real-time Monitoring

**File**: `examples/tutorials/tutorial_03_monitoring.md`

Implement real-time network monitoring and alerting.

### Tutorial 4: Multi-Controller Setup

**File**: `examples/tutorials/tutorial_04_multi_controller.md`

Advanced tutorial on multi-controller deployment.

## 🚀 Running Examples

### Prerequisites

```bash
# Ensure Ryu Enhanced is installed
pip install -e .[all]

# Start Mininet (for network examples)
sudo mn --topo single,3 --controller remote
```

### Basic Examples

```bash
# Run simple switch
ryu-manager examples/basic/simple_switch.py

# Run with middleware
ryu-manager examples/basic/simple_switch.py ryu.app.middleware.core

# Run multiple apps
ryu-manager examples/basic/simple_switch.py examples/basic/traffic_monitor.py
```

### Advanced Examples

```bash
# Multi-controller demo
python examples/multi_controller/demo.py

# ML integration
ryu-manager examples/ml/anomaly_detection.py ryu.app.middleware.core

# P4Runtime example
python examples/p4/p4runtime_demo.py
```

## 📋 Example Categories

### By Difficulty Level

- **Beginner**: Basic SDN concepts, simple applications
- **Intermediate**: API integration, GUI development, monitoring
- **Advanced**: Multi-controller, ML integration, P4Runtime

### By Use Case

- **Learning**: Educational examples for understanding SDN
- **Development**: Templates and patterns for building applications
- **Production**: Real-world deployment examples
- **Testing**: Testing frameworks and methodologies

## 🔗 Additional Resources

- **[API Reference](../api-reference/)** - Complete API documentation
- **[Architecture Guide](../architecture/)** - System design details
- **[Installation Guide](../installation/)** - Setup instructions
- **[Getting Started](../getting-started/)** - Basic usage guide

---

**Ready to start coding?** 🚀 Pick an example that matches your skill level and dive in! Each example includes detailed comments and explanations to help you understand the concepts.
