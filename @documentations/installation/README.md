# Installation Guide

Complete installation guide for Ryu Enhanced SDN Framework across different platforms and deployment scenarios.

## 🎯 Installation Options

Choose the installation method that best fits your needs:

| Installation Type | Use Case | Command | Status |
|------------------|----------|---------|---------|
| **Basic** | Core Ryu functionality | `pip install -e .` | ✅ **Tested** |
| **Middleware** | API and WebSocket support | `pip install -e .[middleware]` | ✅ **Tested** |
| **Full** | All features included | `pip install -e .[all]` | ✅ **Verified** |
| **Development** | Development and testing | `pip install -e .[dev]` | ✅ **Available** |

## ✅ **Required Dependencies (Verified)**

The following dependencies are **required** and have been tested:

```bash
# Core middleware dependencies (required)
pip install pydantic pyyaml requests scapy psutil websockets

# These are automatically installed with [middleware] but may need manual installation
```

## 🖥️ Platform-Specific Installation

### 🐧 Linux (Ubuntu/Debian)

#### Prerequisites
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python and development tools
sudo apt install -y python3.8 python3.8-dev python3-pip git

# Install system dependencies
sudo apt install -y gcc libffi-dev libssl-dev libxml2-dev libxslt1-dev zlib1g-dev

# Install Mininet (optional but recommended)
sudo apt install -y mininet

# Install Open vSwitch (optional)
sudo apt install -y openvswitch-switch openvswitch-common
```

#### ✅ **Verified Installation**
```bash
# Clone repository
git clone https://github.com/your-repo/ryu-enhanced.git
cd ryu-enhanced

# Install with all features
pip3 install -e .[all]

# Install required middleware dependencies (verified)
pip3 install pydantic pyyaml requests scapy psutil websockets

# Verify installation (tested)
ryu-manager --version

# Test middleware (verified working)
ryu-manager ryu.app.middleware.core

# Verify API endpoints (tested)
curl http://localhost:8080/v2.0/health
```

### 🍎 macOS

#### Prerequisites
```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.10

# Install development tools
brew install git gcc libffi openssl libxml2 libxslt

# Install Mininet (optional)
brew install mininet
```

#### Installation
```bash
# Clone repository
git clone https://github.com/your-repo/ryu-enhanced.git
cd ryu-enhanced

# Install with all features
pip3 install -e .[all]

# Verify installation
ryu-manager --version
```

### 🪟 Windows ✅ **Fully Tested & Verified**

#### Prerequisites
1. **Install Python 3.8+** from [python.org](https://python.org) ✅ **Tested with Python 3.12**
2. **Install Git** from [git-scm.com](https://git-scm.com) ✅ **Verified**
3. **Install Visual Studio Build Tools** (for compiling dependencies) ✅ **Optional**

#### ✅ **Verified Installation (Tested on Windows 10/11)**
```powershell
# Clone repository
git clone https://github.com/your-repo/ryu-enhanced.git
cd ryu-enhanced

# Install with all features
pip install -e .[all]

# Install required middleware dependencies (verified working)
pip install pydantic pyyaml requests scapy psutil websockets

# Verify installation (tested)
ryu-manager --version

# Start middleware (verified working)
ryu-manager ryu.app.middleware.core

# Test API endpoints (all verified working)
# PowerShell commands:
Invoke-WebRequest -Uri 'http://localhost:8080/v2.0/health' -UseBasicParsing
Invoke-WebRequest -Uri 'http://localhost:8080/gui' -UseBasicParsing
```

#### ✅ **Windows-Specific Notes (Tested)**
- **Mininet**: Not available on Windows (expected behavior)
- **Traffic Generation**: Scapy-based traffic generation works
- **GUI Interface**: Fully functional web dashboard
- **All API Endpoints**: Tested and working correctly

## 🐳 Docker Installation

### Quick Start with Docker

```bash
# Pull the image
docker pull ryu-enhanced:latest

# Run with basic setup
docker run -p 8080:8080 ryu-enhanced:latest

# Run with volume mounting for persistence
docker run -p 8080:8080 -v $(pwd)/config:/app/config ryu-enhanced:latest
```

### Build from Source

```bash
# Clone repository
git clone https://github.com/your-repo/ryu-enhanced.git
cd ryu-enhanced

# Build Docker image
docker build -t ryu-enhanced:local .

# Run the container
docker run -p 8080:8080 ryu-enhanced:local
```

### Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'
services:
  ryu-enhanced:
    build: .
    ports:
      - "8080:8080"
      - "6653:6653"
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    environment:
      - RYU_LOG_LEVEL=INFO
      - RYU_API_PORT=8080
```

```bash
# Start with Docker Compose
docker-compose up -d
```

## ⚙️ Feature-Specific Installation

### 🔌 Middleware Features

```bash
# Install middleware dependencies
pip install -e .[middleware]

# Additional dependencies for advanced features
pip install pyyaml requests scapy psutil websockets
```

### 🎮 GUI Components

```bash
# Install GUI dependencies
pip install -e .[gui]

# For development of GUI components
npm install  # If you plan to modify web components
```

### 🤖 P4Runtime Support

See detailed guide: [P4Runtime Setup](p4runtime-setup.md)

```bash
# Install P4Runtime dependencies
pip install -e .[p4runtime]

# Install P4 compiler (optional)
# Follow instructions in p4runtime-setup.md
```

### 🧠 AI/ML Integration

```bash
# Install ML dependencies
pip install -e .[ml]

# Additional ML libraries (optional)
pip install tensorflow torch scikit-learn pandas numpy
```

## 🔧 Development Installation

### Complete Development Setup

```bash
# Clone repository
git clone https://github.com/your-repo/ryu-enhanced.git
cd ryu-enhanced

# Install in development mode with all tools
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install

# Verify development setup
pytest --version
mypy --version
black --version
```

### Core Dependencies

Ryu requires the following core dependencies that are automatically installed:

- **eventlet**: Asynchronous networking library
- **msgpack**: Efficient binary serialization format
- **netaddr**: Network address manipulation
- **oslo.config**: Configuration management
- **ovs**: Open vSwitch Python bindings
- **packaging**: Core packaging utilities
- **routes**: URL routing and generation
- **tinyrpc**: RPC library for WSGI and BGP speaker functionality
- **webob**: WSGI request and response objects

### Development Dependencies

The development installation includes:

- **pytest**: Testing framework
- **pytest-cov**: Coverage reporting
- **mypy**: Static type checking
- **black**: Code formatting
- **flake8**: Code linting
- **pre-commit**: Git hooks for code quality
- **sphinx**: Documentation generation

### IDE Setup

#### VS Code
```bash
# Install recommended extensions
code --install-extension ms-python.python
code --install-extension ms-python.mypy-type-checker
code --install-extension ms-python.black-formatter
```

#### PyCharm
1. Open project in PyCharm
2. Configure Python interpreter to use virtual environment
3. Enable type checking and code formatting

## 🌐 Network Environment Setup

### Mininet Integration

```bash
# Install Mininet
sudo apt install -y mininet

# Test Mininet installation
sudo mn --test pingall

# Create custom topology
sudo python examples/start_mixed_topology.py
```

### Open vSwitch Configuration

```bash
# Install Open vSwitch
sudo apt install -y openvswitch-switch

# Start OVS services
sudo systemctl start openvswitch-switch
sudo systemctl enable openvswitch-switch

# Verify OVS installation
sudo ovs-vsctl show
```

### Virtual Environment Setup

```bash
# Create virtual environment
python3 -m venv ryu-env

# Activate virtual environment
source ryu-env/bin/activate  # Linux/macOS
# or
ryu-env\Scripts\activate     # Windows

# Install in virtual environment
pip install -e .[all]
```

## 🧪 Verification and Testing

### Basic Verification

```bash
# Check Ryu installation
ryu-manager --version

# Test basic functionality
python -c "import ryu; print('Ryu imported successfully')"

# Check middleware
curl http://localhost:8080/v2.0/health
```

### Run Test Suite

```bash
# Run all tests
pytest

# Run specific test categories
pytest ryu/tests/unit/
pytest tests/test_middleware.py
pytest tests/test_p4runtime_integration.py

# Run with coverage
pytest --cov=ryu --cov-report=html
```

### Performance Testing

```bash
# Run performance tests
python test_middleware.py --performance

# Load testing (if available)
python tools/load_test.py
```

## 🔧 Configuration

### Basic Configuration

```bash
# Create configuration directory
mkdir -p ~/.ryu/

# Copy default configuration
cp config/ryu.conf ~/.ryu/

# Edit configuration
nano ~/.ryu/ryu.conf
```

### Environment Variables

```bash
# Set common environment variables
export RYU_LOG_LEVEL=INFO
export RYU_API_PORT=8080
export RYU_CONTROLLER_PORT=6653
```

### Configuration Files

Create `config/ryu.yaml`:

```yaml
# Basic Ryu configuration
controller:
  port: 6653
  protocols:
    - openflow13
    - p4runtime

api:
  port: 8080
  host: "0.0.0.0"
  cors_enabled: true

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

middleware:
  enabled: true
  websocket_port: 8080
  event_buffer_size: 1000
```

## 🆘 Troubleshooting

### Common Issues

#### Permission Errors
```bash
# Fix permission issues
sudo chown -R $USER:$USER ~/.ryu/
chmod 755 ~/.ryu/
```

#### Port Conflicts
```bash
# Check port usage
netstat -tulpn | grep :8080

# Kill conflicting processes
sudo fuser -k 8080/tcp
```

#### Dependency Issues
```bash
# Reinstall dependencies
pip install --force-reinstall -e .[all]

# Clear pip cache
pip cache purge
```

#### Missing tinyrpc Module
If you encounter `ModuleNotFoundError: No module named 'tinyrpc'`:

```bash
# Install tinyrpc explicitly
pip install tinyrpc>=1.1.0

# Or reinstall Ryu with all dependencies
pip install --force-reinstall -e .[all]

# Verify tinyrpc installation
python -c "import tinyrpc; print('tinyrpc imported successfully')"
```

**Note**: `tinyrpc` is a core dependency for Ryu's WSGI and RPC functionality. It should be automatically installed with Ryu, but in some environments it may need to be installed separately.

#### Python Version Issues
```bash
# Check Python version
python --version

# Use specific Python version
python3.10 -m pip install -e .[all]
```

### Getting Help

- **Documentation**: Check other sections in this documentation
- **Issues**: [GitHub Issues](https://github.com/your-repo/ryu-enhanced/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/ryu-enhanced/discussions)
- **Community**: Join our community channels

## 📋 Next Steps

After successful installation:

1. **[Getting Started](../getting-started/)** - Basic usage and first application
2. **[Architecture](../architecture/)** - Understand the system design
3. **[Examples](../examples/)** - Explore practical examples
4. **[API Reference](../api-reference/)** - Detailed API documentation

---

**Installation complete?** 🎉 Head over to the [Getting Started Guide](../getting-started/) to build your first SDN application!
