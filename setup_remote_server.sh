#!/bin/bash
# Setup script for Ryu Enhanced SDN Middleware on remote Linux server
# This script prepares the environment and installs all dependencies

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] ✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ✗${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should NOT be run as root for the initial setup"
        error "Run without sudo first, then use sudo only for the test script"
        exit 1
    fi
}

# Detect OS
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        error "Cannot detect OS version"
        exit 1
    fi
    
    log "Detected OS: $OS $VER"
}

# Install system dependencies
install_system_deps() {
    log "Installing system dependencies..."
    
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        sudo apt update
        sudo apt install -y \
            python3 python3-pip python3-dev python3-venv \
            git curl wget \
            build-essential \
            mininet \
            openvswitch-switch openvswitch-common \
            net-tools \
            iproute2 \
            iperf3 \
            tcpdump
        success "Ubuntu/Debian dependencies installed"
        
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]] || [[ "$OS" == *"Rocky"* ]]; then
        sudo yum update -y
        sudo yum install -y \
            python3 python3-pip python3-devel \
            git curl wget \
            gcc gcc-c++ make \
            openvswitch \
            net-tools \
            iproute \
            iperf3 \
            tcpdump
        
        # Install Mininet from source on RHEL-based systems
        if ! command -v mn &> /dev/null; then
            warning "Installing Mininet from source..."
            cd /tmp
            git clone https://github.com/mininet/mininet.git
            cd mininet
            sudo ./util/install.sh -a
            cd ~
        fi
        success "RHEL-based dependencies installed"
        
    else
        error "Unsupported OS: $OS"
        exit 1
    fi
}

# Setup Python environment
setup_python_env() {
    log "Setting up Python environment..."
    
    # Create virtual environment
    if [[ ! -d "venv" ]]; then
        python3 -m venv venv
        success "Virtual environment created"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install Python dependencies
    pip install wheel setuptools
    
    success "Python environment ready"
}

# Clone and setup Ryu Enhanced
setup_ryu_enhanced() {
    log "Setting up Ryu Enhanced..."
    
    # Clone repository if not exists
    if [[ ! -d "ryu" ]]; then
        log "Cloning Ryu Enhanced repository..."
        git clone https://github.com/nqmn/ryu.git
        success "Repository cloned"
    else
        log "Repository already exists, updating..."
        cd ryu
        git pull
        cd ..
        success "Repository updated"
    fi
    
    # Install Ryu Enhanced
    cd ryu
    source ../venv/bin/activate
    
    # Install with all features
    pip install -e .[all]
    
    # Install additional middleware dependencies
    pip install pydantic pyyaml requests scapy psutil websockets
    
    success "Ryu Enhanced installed with all dependencies"
    cd ..
}

# Verify installation
verify_installation() {
    log "Verifying installation..."
    
    source venv/bin/activate
    
    # Check Python modules
    python3 -c "import ryu; print('✓ Ryu imported successfully')"
    python3 -c "import pydantic; print('✓ Pydantic available')"
    python3 -c "import mininet; print('✓ Mininet available')" 2>/dev/null || warning "Mininet Python module not available"
    
    # Check commands
    if command -v ryu-manager &> /dev/null; then
        success "ryu-manager command available"
        ryu-manager --version
    else
        error "ryu-manager command not found"
        exit 1
    fi
    
    if command -v mn &> /dev/null; then
        success "Mininet command available"
        mn --version
    else
        error "Mininet command not found"
        exit 1
    fi
    
    if command -v ovs-vsctl &> /dev/null; then
        success "Open vSwitch available"
        ovs-vsctl --version | head -1
    else
        error "Open vSwitch not found"
        exit 1
    fi
    
    success "All components verified successfully"
}

# Setup firewall rules
setup_firewall() {
    log "Configuring firewall rules..."
    
    # Check if ufw is available (Ubuntu/Debian)
    if command -v ufw &> /dev/null; then
        sudo ufw allow 8080/tcp comment "Ryu Middleware API"
        sudo ufw allow 6653/tcp comment "OpenFlow Controller"
        success "UFW rules added"
    # Check if firewall-cmd is available (RHEL/CentOS)
    elif command -v firewall-cmd &> /dev/null; then
        sudo firewall-cmd --permanent --add-port=8080/tcp
        sudo firewall-cmd --permanent --add-port=6653/tcp
        sudo firewall-cmd --reload
        success "Firewalld rules added"
    else
        warning "No firewall management tool found, please manually open ports 8080 and 6653"
    fi
}

# Create test script launcher
create_launcher() {
    log "Creating test launcher script..."
    
    cat > run_tests.sh << 'EOF'
#!/bin/bash
# Test launcher script

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Ryu Enhanced SDN Middleware Test Launcher ===${NC}"
echo

# Check if virtual environment exists
if [[ ! -d "venv" ]]; then
    echo "Error: Virtual environment not found. Run setup_remote_server.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Change to ryu directory
cd ryu

# Run the test script
echo -e "${GREEN}Starting comprehensive test suite...${NC}"
echo "Note: This will run as root for Mininet access"
echo

sudo -E env PATH=$PATH python3 ../test_full_deployment.py "$@"
EOF

    chmod +x run_tests.sh
    success "Test launcher created: run_tests.sh"
}

# Display usage instructions
show_usage() {
    echo
    echo -e "${GREEN}=== Setup Complete! ===${NC}"
    echo
    echo "Next steps:"
    echo "1. Run the test suite:"
    echo -e "   ${BLUE}./run_tests.sh${NC}"
    echo
    echo "2. Run with specific topology:"
    echo -e "   ${BLUE}./run_tests.sh --topology linear --hosts 6${NC}"
    echo
    echo "3. Manual testing:"
    echo -e "   ${BLUE}source venv/bin/activate${NC}"
    echo -e "   ${BLUE}cd ryu${NC}"
    echo -e "   ${BLUE}ryu-manager ryu.app.middleware.core${NC}"
    echo
    echo "4. Access GUI (after starting middleware):"
    echo -e "   ${BLUE}http://YOUR_SERVER_IP:8080/gui${NC}"
    echo
    echo "Available test options:"
    echo "  --topology simple|linear|tree"
    echo "  --hosts N (number of hosts)"
    echo "  --controller-port PORT"
    echo "  --api-port PORT"
    echo
}

# Main execution
main() {
    echo -e "${BLUE}=== Ryu Enhanced Remote Server Setup ===${NC}"
    echo
    
    check_root
    detect_os
    install_system_deps
    setup_python_env
    setup_ryu_enhanced
    verify_installation
    setup_firewall
    create_launcher
    show_usage
    
    success "Setup completed successfully!"
}

# Run main function
main "$@"
