# Examples Directory

This directory contains practical examples and demonstration scripts for the Ryu Enhanced SDN Framework.

## 📁 Contents

### 🚀 Demo Scripts
- **`demo_multi_controller.py`** - Demonstrates multi-controller setup and management
- **`start_middleware.py`** - Basic middleware startup and configuration example

### 🌐 Middleware Examples
- **`middleware_usage.py`** - Comprehensive middleware API usage examples
- **`start_mixed_topology.py`** - Mixed topology creation with OpenFlow and P4Runtime

### 🔧 P4Runtime Examples
- **`p4runtime_config.yaml`** - P4Runtime configuration template
- **`p4/`** - P4 program examples
  - **`basic_forwarding.p4`** - Simple P4 forwarding program

## 🚀 Running Examples

### Prerequisites
```bash
# Ensure Ryu Enhanced is installed
pip install -e .[all]

# For network examples, start Mininet
sudo mn --topo single,3 --controller remote
```

### Basic Usage
```bash
# Run middleware demo
python examples/start_middleware.py

# Run multi-controller demo
python examples/demo_multi_controller.py

# Run topology example
python examples/start_mixed_topology.py

# Test middleware API
python examples/middleware_usage.py
```

### P4Runtime Examples
```bash
# Compile P4 program (if P4 compiler is installed)
p4c examples/p4/basic_forwarding.p4

# Run with P4Runtime configuration
python examples/start_mixed_topology.py --config examples/p4runtime_config.yaml
```

## 📚 Documentation

For more detailed examples and tutorials, see the main documentation:
- [Examples Documentation](@documentations/examples/)
- [Getting Started Guide](@documentations/getting-started/)
- [API Reference](@documentations/api-reference/)

## 🤝 Contributing

To add new examples:
1. Create descriptive filenames
2. Include comprehensive comments
3. Add usage instructions
4. Test with different configurations
5. Update this README

---

**Need help?** Check the [main documentation](@documentations/) or [create an issue](https://github.com/nqmn/ryu/issues).
