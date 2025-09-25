# Ryu SDN Framework - 2025 Edition

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)]()

> **🚀 Enhanced Ryu SDN Framework** - A modernized, feature-rich Software Defined Networking framework with advanced middleware capabilities, multi-controller support, and AI/ML integration.

## 🎯 What's New in This Enhanced Edition

This is a **comprehensively modernized and enhanced version** of the Ryu SDN framework that includes:

### ✨ Core Enhancements
- **🐍 Modern Python Support**: Python 3.8+ with type hints and modern syntax
- **📦 Updated Dependencies**: Latest stable versions of all dependencies
- **🧪 Modern Testing**: Migrated from nose to pytest with comprehensive test coverage
- **🏗️ Modern Project Structure**: Uses pyproject.toml and modern packaging standards

## 🚀 Quick Start

### Prerequisites
- **Python 3.8 or later**
- **pip** (Python package manager)
- **Mininet** (for network emulation) - run `sudo apt install mininet`

### Core Dependencies
The following dependencies are automatically installed with Ryu:
- `eventlet` - Asynchronous networking
- `msgpack` - Binary serialization
- `netaddr` - Network address manipulation
- `oslo.config` - Configuration management
- `ovs` - Open vSwitch bindings
- `tinyrpc` - RPC library for WSGI functionality
- `webob` - WSGI request/response objects

### Basic Installation (Default)

```bash
# Clone the repository
git clone https://github.com/nqmn/ryu.git
cd ryu

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Upgrade pip and install the package
pip install --upgrade pip

# Install with Core Ryu only (default)
pip install -e .

```

### Basic Installation (Bypass Ubuntu Safety Checks )

```bash
# Clone the repository
git clone https://github.com/nqmn/ryu.git
cd ryu

# Upgrade pip and install the package
pip install --upgrade pip --break-system-package --ignore-installed

# Install with Core Ryu only (default)
pip install -e . --break-system-package --ignore-installed

# Add to PATH environment
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Start Ryu with with simple switch
ryu-manager ryu/app/simple_switch_13.py

```

### Contact

✉️ If you found any issues, do reach me!

---

## Additional Features (NEW!)

If you want to test the advanced middleware capabilities, multi-controller support, and AI/ML integration, here it is.

### 🚀 Advanced Middleware System (Optional)
- **🌐 RESTful API**: Comprehensive REST API for network management
- **⚡ WebSocket Streaming**: Real-time event streaming and monitoring
- **🔄 Multi-Controller Support**: OpenFlow (Ryu) and P4Runtime controller management
- **🤖 AI/ML Integration**: Plugin architecture for machine learning modules
- **📊 Advanced Monitoring**: Flow statistics, port metrics, and network analytics

### 🎮 Interactive Features (Optional)
- **🖥️ Web-based GUI**: Interactive topology visualization and management
- **📺 Live Terminal**: Real-time network event monitoring with color coding
- **🔧 Dynamic Configuration**: Runtime topology and flow management
- **📈 Performance Analytics**: Comprehensive network performance metrics

### Features Installation

```bash
# Install with all features
pip install -e .[all]

# Or install individual features  
  pip install -e .[middleware]    # Enhanced SDN middleware
  pip install -e .[gui]           # Web GUI
  pip install -e .[p4runtime]     # P4Runtime support
  pip install -e .[dev]           # Development tools

# Or install with specific features
pip install -e .[middleware,gui,p4runtime]

```

### Basic Usage

```bash
# Start Ryu with middleware
ryu-manager ryu.app.middleware.core

# Start with GUI and monitoring
ryu-manager ryu.app.middleware.core ryu.app.gui.topology

# Start multi-controller setup
python demo_multi_controller.py
```

### Test the Installation

```bash
# Run basic tests
python test_middleware.py

# Check API health
curl http://localhost:8080/v2.0/health

# View GUI (if enabled)
# Open browser to http://localhost:8080/gui
```

## 📚 Documentation

Our documentation is organized into clear sections for easy navigation:

### 🏁 [Getting Started](@documentations/getting-started/)
- [Installation Guide](@documentations/installation/)
- [Quick Start Tutorial](@documentations/getting-started/)
- [Basic Examples](@documentations/examples/)

### 🏗️ [Architecture](@documentations/architecture/)
- [Middleware Architecture](@documentations/architecture/middleware-architecture.md)
- [Multi-Controller System](@documentations/architecture/multi-controller.md)
- [P4Runtime Implementation](@documentations/architecture/p4runtime-implementation.md)

### 🔧 [Installation & Setup](@documentations/installation/)
- [P4Runtime Setup](@documentations/installation/p4runtime-setup.md)
- [Development Environment](@documentations/installation/)
- [Docker Deployment](@documentations/installation/)

### 📖 [API Reference](@documentations/api-reference/)
- [REST API Documentation](@documentations/api-reference/)
- [WebSocket Events](@documentations/api-reference/)
- [Python API Reference](@documentations/api-reference/)

### 📝 [Examples & Tutorials](@documentations/examples/)
- [Basic SDN Applications](@documentations/examples/)
- [Middleware Integration](@documentations/examples/)
- [AI/ML Integration Examples](@documentations/examples/)

### 📋 [Changelog](@documentations/changelog/)
- [Version History](@documentations/changelog/CHANGELOG.md)
- [Migration Guide](@documentations/changelog/)

## 🌟 Key Features

### 🔌 Middleware API
- **RESTful Interface**: Complete REST API for network management
- **Real-time Events**: WebSocket streaming for live network monitoring
- **Topology Management**: Dynamic network topology creation and modification
- **Flow Control**: Advanced OpenFlow rule management
- **Traffic Generation**: Built-in traffic generation and testing tools

### 🎛️ Multi-Controller Support
- **Heterogeneous Controllers**: Support for OpenFlow and P4Runtime
- **Unified Management**: Single API for multiple controller types
- **Health Monitoring**: Automatic health checks and failover
- **Dynamic Registration**: Runtime controller registration and management

### 🤖 AI/ML Integration
- **Plugin Architecture**: Easy integration of ML models
- **Real-time Inference**: Live network analysis and prediction
- **Event-driven Processing**: Automatic ML processing of network events
- **Performance Optimization**: ML-based network optimization

### 🖥️ Interactive GUI
- **Topology Visualization**: Interactive network topology graphs
- **Live Monitoring**: Real-time network status and metrics
- **Control Interface**: GUI-based network management
- **Export Capabilities**: Network data export and reporting

## 🛠️ Development

### Contributing

We welcome contributions! Please see our [Contributing Guide](@documentations/getting-started/CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🤝 Support & Community

- **Documentation**: [Full Documentation](@documentations/)
- **Issues**: [GitHub Issues](https://github.com/nqmn/ryu/issues)
- **Discussions**: [GitHub Discussions](https://github.com/nqmn/ryu/discussions)
- **Original Ryu Website**: [Ryu Official Site](https://ryu-sdn.org/)
- **Original Ryu GitHub**: [Ryu GitHub](https://github.com/faucetsdn/ryu)

## 🙏 Acknowledgments

This enhanced version builds upon the excellent foundation of the original Ryu SDN framework. We thank the original Ryu development team and the SDN community for their contributions.

---

**Ready to build the future of networking?** 🚀 [Get Started](@documentations/getting-started/) today!
