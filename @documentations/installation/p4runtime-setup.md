# P4Runtime Support Setup Guide

This guide explains how to set up and use the P4Runtime support in the Ryu Middleware API.

## 🎯 Overview

The enhanced middleware now supports dual SDN backends:
- **OpenFlow** (via Ryu controller) - Traditional SDN switches
- **P4Runtime** (via gRPC) - P4-programmable switches (BMv2, Tofino, etc.)

The middleware provides a unified API that automatically routes operations to the appropriate backend based on switch type and configuration.

## 📋 Prerequisites

### 1. Install P4Runtime Dependencies

```bash
# Install P4Runtime support
pip install -e .[p4runtime]

# Or install individual dependencies
pip install grpcio>=1.59.0 grpcio-tools>=1.59.0 protobuf>=4.25.0
```

### 2. P4 Development Environment

For testing with BMv2:

```bash
# Install P4 tools (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y p4lang-bmv2 p4lang-p4c

# Or build from source
git clone https://github.com/p4lang/behavioral-model.git
cd behavioral-model
./install_deps.sh
./autogen.sh
./configure --enable-debugger
make -j4
sudo make install
```

## 🚀 Quick Start

### 1. Basic Configuration

Create a configuration file `p4runtime_config.yaml`:

```yaml
middleware:
  sdn_backends:
    openflow:
      enabled: true
    p4runtime:
      enabled: true
      switches:
        - device_id: 1
          address: "localhost:50051"
          pipeline: "./examples/p4/basic_forwarding.json"
          p4info: "./examples/p4/basic_forwarding.p4info"
```

### 2. Start BMv2 Switch

```bash
# Start simple_switch_grpc
simple_switch_grpc \
  --device-id 1 \
  --thrift-port 9090 \
  --grpc-server-addr 0.0.0.0:50051 \
  --log-console \
  examples/p4/basic_forwarding.json
```

### 3. Start Middleware

```bash
# Start with P4Runtime support
ryu-manager ryu.app.middleware.core --config-file p4runtime_config.yaml
```

## 🔧 Configuration Options

### SDN Backend Configuration

```yaml
middleware:
  sdn_backends:
    openflow:
      enabled: true
      controller_host: "localhost"
      controller_port: 6653
      
    p4runtime:
      enabled: true
      connection_timeout: 30
      switches:
        - device_id: 1
          address: "localhost:50051"
          pipeline: "./path/to/program.json"
          p4info: "./path/to/program.p4info"
          description: "BMv2 switch description"
```

### Pipeline Management

```yaml
p4runtime:
  pipeline_directory: "./pipelines"
  pipelines:
    - name: "basic_forwarding"
      version: "1.0.0"
      p4info_path: "./basic_forwarding.p4info"
      config_path: "./basic_forwarding.json"
```

## 📡 API Usage

### Unified Flow Management

The middleware provides unified endpoints that work with both OpenFlow and P4Runtime:

```bash
# Install flow (automatically routed to correct backend)
curl -X POST http://localhost:8080/v2.0/flow/install \
  -H "Content-Type: application/json" \
  -d '{
    "switch_id": "1",
    "table_name": "ipv4_lpm",
    "action_name": "ipv4_forward",
    "match": {
      "hdr.ipv4.dstAddr": "10.0.0.1/24"
    },
    "action_params": {
      "dstAddr": "00:00:00:00:00:01",
      "port": "1"
    },
    "priority": 1000
  }'
```

### P4-Specific Endpoints

```bash
# List P4Runtime switches
curl http://localhost:8080/v2.0/p4/switches

# Install P4 pipeline
curl -X POST http://localhost:8080/v2.0/p4/pipeline/install \
  -H "Content-Type: application/json" \
  -d '{
    "switch_id": "1",
    "pipeline_name": "basic_forwarding",
    "p4info_path": "./basic_forwarding.p4info",
    "config_path": "./basic_forwarding.json"
  }'

# Get pipeline status
curl http://localhost:8080/v2.0/p4/pipeline/status

# Read table entries
curl http://localhost:8080/v2.0/p4/table/read/1
```

### WebSocket Events

Connect to WebSocket for real-time events:

```javascript
const ws = new WebSocket('ws://localhost:8080/v2.0/events/ws');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  
  switch(data.method) {
    case 'p4_packet_in':
      console.log('P4 Packet-in:', data.params);
      break;
    case 'p4_pipeline_installed':
      console.log('Pipeline installed:', data.params);
      break;
    case 'p4_table_updated':
      console.log('Table updated:', data.params);
      break;
  }
};
```

## 🧪 Testing

### Unit Tests

```bash
# Run P4Runtime tests
python -m pytest tests/test_p4runtime_integration.py -v

# Run all middleware tests
python -m pytest tests/ -v
```

### Integration Testing

```bash
# Start test environment
./examples/start_test_topology.sh

# Run integration tests
python tests/integration/test_mixed_topology.py
```

## 🔍 Troubleshooting

### Common Issues

1. **P4Runtime connection failed**
   ```
   ERROR: Failed to connect to P4Runtime switch 1: [Errno 111] Connection refused
   ```
   - Ensure BMv2 switch is running with gRPC enabled
   - Check address and port configuration

2. **Pipeline installation failed**
   ```
   ERROR: Failed to install pipeline: P4Info file not found
   ```
   - Verify P4Info and JSON file paths
   - Ensure files are accessible by the middleware

3. **Import errors**
   ```
   ImportError: No module named 'p4.v1.p4runtime_pb2'
   ```
   - Install P4Runtime dependencies: `pip install p4runtime`
   - Generate protobuf files if needed

### Debug Mode

Enable debug logging:

```yaml
logging:
  loggers:
    ryu.app.middleware.p4runtime:
      level: DEBUG
```

### Health Check

```bash
# Check backend status
curl http://localhost:8080/v2.0/health
```

## 📚 Examples

See the `examples/` directory for:
- Basic P4 programs
- Mixed topology configurations
- Integration scripts
- Performance testing tools

## 🔄 Migration from OpenFlow-only

### Backward Compatibility

All existing OpenFlow functionality continues to work unchanged:

```bash
# Existing OpenFlow API calls work as before
curl -X POST http://localhost:8080/v2.0/flow/install \
  -H "Content-Type: application/json" \
  -d '{
    "dpid": "123456789",
    "match": {"in_port": 1},
    "actions": [{"type": "OUTPUT", "port": 2}]
  }'
```

### Gradual Migration

1. **Phase 1**: Enable P4Runtime alongside OpenFlow
2. **Phase 2**: Add P4Runtime switches to configuration
3. **Phase 3**: Migrate applications to use unified APIs
4. **Phase 4**: Leverage P4-specific features

## 🆘 Support

- **Documentation**: See `MIDDLEWARE_README.md` for general middleware usage
- **Issues**: Report bugs on GitHub
- **Examples**: Check `examples/` directory for sample configurations
- **Tests**: Run test suite for validation
