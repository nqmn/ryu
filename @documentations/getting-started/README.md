# Getting Started with Ryu Enhanced

Welcome to the Ryu Enhanced SDN Framework! This guide will help you get up and running quickly with our modernized and feature-rich SDN platform.

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

### System Requirements
- **Operating System**: Linux (Ubuntu 18.04+), macOS, or Windows 10/11
- **Python**: 3.8 or later (3.10+ recommended)
- **Memory**: At least 4GB RAM (8GB+ recommended for complex topologies)
- **Storage**: 2GB free space

### Required Software
- **Python 3.8+** with pip
- **Git** for cloning the repository
- **Mininet** (optional but recommended for network emulation)
- **Open vSwitch** (optional, for advanced features)

## 🚀 Quick Installation

### Option 1: Standard Installation

```bash
# Clone the repository
git clone https://github.com/your-repo/ryu-enhanced.git
cd ryu-enhanced

# Install with basic features
pip install -e .

# Verify installation
ryu-manager --version
```

### Option 2: Full Installation with All Features

```bash
# Install with all optional features
pip install -e .[all]

# This includes:
# - middleware: REST API and WebSocket support
# - gui: Web-based GUI interface
# - p4runtime: P4Runtime controller support
# - ml: AI/ML integration capabilities
# - dev: Development and testing tools
```

### Option 3: Custom Installation

```bash
# Install specific feature sets
pip install -e .[middleware,gui]        # API + GUI
pip install -e .[p4runtime,ml]          # P4 + ML support
pip install -e .[dev]                   # Development tools
```

## 🎯 Your First Ryu Application

### 1. Basic Controller

Create a simple learning switch:

```python
# my_switch.py
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet

class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Install table-miss flow entry
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # Packet processing logic here
        pass
```

### 2. Run Your Application

```bash
# Start your application
ryu-manager my_switch.py

# With verbose logging
ryu-manager --verbose my_switch.py

# With multiple applications
ryu-manager my_switch.py ryu.app.simple_switch_13
```

## 🌐 Using the Middleware API

### 1. Start with Middleware

```bash
# Start Ryu with middleware support
ryu-manager ryu.app.middleware.core

# The API will be available at http://localhost:8080
```

### 2. Test the API

```bash
# Check health
curl http://localhost:8080/v2.0/health

# Get topology
curl http://localhost:8080/v2.0/topology

# Create a simple topology
curl -X POST http://localhost:8080/v2.0/topology \
  -H "Content-Type: application/json" \
  -d '{"name": "simple", "switches": 2, "hosts": 2}'
```

### 3. WebSocket Events

```javascript
// Connect to WebSocket for real-time events
const ws = new WebSocket('ws://localhost:8080/v2.0/events');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Network event:', data);
};
```

## 🖥️ Web GUI Interface

### 1. Enable GUI

```bash
# Start with GUI support
ryu-manager ryu.app.middleware.core ryu.app.gui.topology

# Access GUI at http://localhost:8080/gui
```

### 2. GUI Features

- **Interactive Topology**: Drag and drop network visualization
- **Live Monitoring**: Real-time network status and metrics
- **Flow Management**: Visual flow rule management
- **Event Terminal**: Live network event stream

## 🧪 Testing Your Setup

### 1. Run Basic Tests

```bash
# Test middleware functionality
python test_middleware.py

# Test multi-controller features
python test_multi_controller.py

# Test GUI components
python test_gui_demo.py
```

### 2. Create Test Topology

```bash
# Start a test topology with Mininet
sudo python examples/start_mixed_topology.py

# Or use the middleware API
python examples/middleware_usage.py
```

## 🔧 Development Setup

### 1. Development Installation

```bash
# Install in development mode with all tools
pip install -e .[dev]

# This includes:
# - pytest: Testing framework
# - mypy: Type checking
# - black: Code formatting
# - flake8: Linting
```

### 2. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ryu

# Run specific test file
pytest ryu/tests/unit/test_utils.py -v
```

### 3. Code Quality

```bash
# Format code
black ryu/

# Type checking
mypy ryu/

# Linting
flake8 ryu/
```

## 📚 Next Steps

Now that you have Ryu Enhanced running, explore these areas:

1. **[Architecture Overview](../architecture/)** - Understand the system design
2. **[API Reference](../api-reference/)** - Detailed API documentation
3. **[Examples](../examples/)** - More complex examples and tutorials
4. **[Installation Guide](../installation/)** - Advanced installation options

## 🆘 Troubleshooting

### Common Issues

**Import Errors**
```bash
# Ensure all dependencies are installed
pip install -e .[all]
```

**Port Already in Use**
```bash
# Change the default port
ryu-manager --wsapi-port 8081 ryu.app.middleware.core
```

**Permission Errors with Mininet**
```bash
# Run with sudo for Mininet operations
sudo python examples/start_mixed_topology.py
```

### Getting Help

- Check the [troubleshooting guide](troubleshooting.md)
- Review [common issues](common-issues.md)
- Ask questions in [GitHub Discussions](https://github.com/your-repo/ryu-enhanced/discussions)

---

**Ready to dive deeper?** Check out our [Architecture Guide](../architecture/) to understand how everything works together! 🚀
