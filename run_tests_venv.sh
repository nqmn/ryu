#!/bin/bash
# Wrapper script to run tests in the correct virtual environment
# This ensures all dependencies are available and paths are correct

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] ✓${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ✗${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root (use sudo)"
    echo "Example: sudo ./run_tests_venv.sh"
    exit 1
fi

# Get the original user (the one who ran sudo)
ORIGINAL_USER=${SUDO_USER:-$(whoami)}
ORIGINAL_HOME=$(eval echo ~$ORIGINAL_USER)

log "Running as root, original user: $ORIGINAL_USER"
log "Original home directory: $ORIGINAL_HOME"

# Find the virtual environment
VENV_PATHS=(
    "$ORIGINAL_HOME/ryu/venv"
    "$ORIGINAL_HOME/venv"
    "./venv"
    "../venv"
)

VENV_PATH=""
for path in "${VENV_PATHS[@]}"; do
    if [[ -d "$path" && -f "$path/bin/activate" ]]; then
        VENV_PATH="$path"
        success "Found virtual environment: $VENV_PATH"
        break
    fi
done

if [[ -z "$VENV_PATH" ]]; then
    error "Virtual environment not found in any of these locations:"
    for path in "${VENV_PATHS[@]}"; do
        echo "  - $path"
    done
    error "Please create a virtual environment first or run from the correct directory"
    exit 1
fi

# Find the test script
TEST_SCRIPT_PATHS=(
    "./test_full_deployment.py"
    "$ORIGINAL_HOME/test_full_deployment.py"
    "$ORIGINAL_HOME/ryu/test_full_deployment.py"
)

TEST_SCRIPT=""
for path in "${TEST_SCRIPT_PATHS[@]}"; do
    if [[ -f "$path" ]]; then
        TEST_SCRIPT="$path"
        success "Found test script: $TEST_SCRIPT"
        break
    fi
done

if [[ -z "$TEST_SCRIPT" ]]; then
    error "Test script not found in any of these locations:"
    for path in "${TEST_SCRIPT_PATHS[@]}"; do
        echo "  - $path"
    done
    exit 1
fi

# Verify virtual environment has required packages
log "Verifying virtual environment setup..."

# Activate virtual environment and check dependencies
source "$VENV_PATH/bin/activate"

# Check Python packages
REQUIRED_PACKAGES=("ryu" "pydantic" "requests" "yaml" "scapy" "psutil" "websockets")
MISSING_PACKAGES=()

for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! python3 -c "import $package" 2>/dev/null; then
        MISSING_PACKAGES+=("$package")
    fi
done

if [[ ${#MISSING_PACKAGES[@]} -gt 0 ]]; then
    warning "Missing packages: ${MISSING_PACKAGES[*]}"
    log "Installing missing packages..."
    
    # Map package names to pip names
    declare -A PIP_NAMES
    PIP_NAMES["yaml"]="pyyaml"
    
    for package in "${MISSING_PACKAGES[@]}"; do
        pip_name=${PIP_NAMES[$package]:-$package}
        log "Installing $pip_name..."
        pip install "$pip_name"
    done
    
    success "All packages installed"
fi

# Verify ryu-manager is available
if ! command -v ryu-manager &> /dev/null; then
    if [[ -f "$VENV_PATH/bin/ryu-manager" ]]; then
        success "ryu-manager found in virtual environment"
    else
        error "ryu-manager not found"
        exit 1
    fi
else
    success "ryu-manager found in PATH"
fi

# Set environment variables for the test script
export VIRTUAL_ENV="$VENV_PATH"
export PATH="$VENV_PATH/bin:$PATH"
export PYTHONPATH="$ORIGINAL_HOME/ryu:$PYTHONPATH"

# Fix protobuf and threading compatibility issues
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

# Additional fixes for RLock/green thread compatibility
export EVENTLET_HUB=poll                    # Use poll hub for better compatibility
export EVENTLET_NOPATCH=time                # Only prevent time module patching, allow thread patching
export PYTHONDONTWRITEBYTECODE=1            # Avoid .pyc file conflicts in concurrent environments

# Set RYU_HUB_TYPE explicitly (used by ryu.lib.hub)
export RYU_HUB_TYPE=eventlet

log "Applied compatibility fixes:"
log "  - PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python"
log "  - EVENTLET_HUB=poll" 
log "  - EVENTLET_NOPATCH=time"
log "  - RYU_HUB_TYPE=eventlet"

# Change to the directory containing the test script
cd "$(dirname "$TEST_SCRIPT")"

log "Starting comprehensive test suite..."
log "Virtual Environment: $VIRTUAL_ENV"
log "Python Path: $(which python3)"
log "Ryu Manager: $(which ryu-manager 2>/dev/null || echo 'Not in PATH')"

# Run the test script with all arguments passed through
python3 "$(basename "$TEST_SCRIPT")" "$@"

# Capture exit code
EXIT_CODE=$?

if [[ $EXIT_CODE -eq 0 ]]; then
    success "Test suite completed successfully!"
else
    error "Test suite failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE
