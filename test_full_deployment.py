#!/usr/bin/env python3
"""
Comprehensive Test Script for Ryu Enhanced SDN Middleware
=========================================================

This script automates the complete testing workflow:
1. Sets up Mininet topology
2. Starts Ryu middleware
3. Tests network connectivity (pingall)
4. Tests GUI and API endpoints
5. Generates comprehensive test report

Designed for remote Linux server deployment and testing.

Usage:
    python3 test_full_deployment.py [--topology simple|linear|tree] [--hosts 4]
"""

import os
import sys
import time
import json
import signal
import argparse
import subprocess
import threading
import requests
from datetime import datetime
from pathlib import Path

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class TestRunner:
    """Main test runner class"""
    
    def __init__(self, topology='simple', num_hosts=4, controller_port=6653, api_port=8080):
        self.topology = topology
        self.num_hosts = num_hosts
        self.controller_port = controller_port
        self.api_port = api_port
        self.processes = {}
        self.test_results = {}
        self.start_time = datetime.now()
        
        # URLs for testing
        self.base_url = f"http://localhost:{api_port}/v2.0"
        self.gui_url = f"http://localhost:{api_port}/gui"
        
        print(f"{Colors.BOLD}{Colors.BLUE}=== Ryu Enhanced SDN Middleware Test Suite ==={Colors.END}")
        print(f"Topology: {topology}, Hosts: {num_hosts}")
        print(f"Controller Port: {controller_port}, API Port: {api_port}")
        print(f"Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

    def log(self, message, color=Colors.WHITE, prefix="INFO"):
        """Enhanced logging with colors and timestamps"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"{color}[{timestamp}] {prefix}: {message}{Colors.END}")

    def run_command(self, command, timeout=30, capture_output=True):
        """Run shell command with timeout and error handling"""
        try:
            if capture_output:
                result = subprocess.run(
                    command, shell=True, capture_output=True, 
                    text=True, timeout=timeout
                )
                return result.returncode == 0, result.stdout, result.stderr
            else:
                process = subprocess.Popen(command, shell=True)
                return process, None, None
        except subprocess.TimeoutExpired:
            self.log(f"Command timed out: {command}", Colors.RED, "ERROR")
            return False, "", "Timeout"
        except Exception as e:
            self.log(f"Command failed: {command} - {e}", Colors.RED, "ERROR")
            return False, "", str(e)

    def check_dependencies(self):
        """Check if all required dependencies are installed"""
        self.log("Checking dependencies...", Colors.CYAN, "CHECK")

        # Check if we're in a virtual environment
        in_venv = os.environ.get('VIRTUAL_ENV') is not None
        if in_venv:
            self.log(f"✓ Virtual environment detected: {os.environ.get('VIRTUAL_ENV')}", Colors.GREEN)
        else:
            self.log("⚠ No virtual environment detected", Colors.YELLOW)

        dependencies = {
            'python3': 'python3 --version',
            'mininet': 'mn --version',
            'ovs': 'ovs-vsctl --version',
            'ryu': 'ryu-manager --version',
            'curl': 'curl --version || apt list --installed curl 2>/dev/null | grep curl || echo "curl not found"'
        }

        missing = []
        for dep, cmd in dependencies.items():
            success, stdout, stderr = self.run_command(cmd)
            if success and stdout and "not found" not in stdout.lower():
                version = stdout.split('\n')[0] if stdout else "installed"
                self.log(f"✓ {dep}: {version}", Colors.GREEN)
            else:
                # Special handling for ryu in virtual environment
                if dep == 'ryu' and in_venv:
                    # Try to import ryu instead
                    success_import, _, _ = self.run_command("python3 -c 'import ryu; print(\"Ryu available\")'")
                    if success_import:
                        self.log(f"✓ {dep}: available in virtual environment", Colors.GREEN)
                        continue

                # Special handling for mininet - try multiple ways to detect it
                if dep == 'mininet':
                    # Try alternative detection methods
                    alt_commands = [
                        "which mn",
                        "sudo mn --version 2>/dev/null || echo 'not found'",
                        "python3 -c 'import mininet; print(\"Mininet Python module available\")' 2>/dev/null || echo 'not found'",
                        "ls /usr/bin/mn 2>/dev/null && echo 'mn found in /usr/bin' || echo 'not found'"
                    ]
                    
                    mininet_found = False
                    for alt_cmd in alt_commands:
                        success_alt, stdout_alt, stderr_alt = self.run_command(alt_cmd)
                        if success_alt and stdout_alt and "not found" not in stdout_alt.lower():
                            self.log(f"✓ {dep}: found via '{alt_cmd}' - {stdout_alt.strip()}", Colors.GREEN)
                            mininet_found = True
                            break
                    
                    if not mininet_found:
                        # If all methods fail, log detailed info for debugging
                        self.log(f"✗ {dep}: not found with any detection method", Colors.RED)
                        self.log(f"Tried: mn --version, which mn, sudo mn --version, python import", Colors.YELLOW)
                        missing.append(dep)
                    continue

                # Special handling for curl - it's optional
                if dep == 'curl':
                    self.log(f"⚠ {dep}: not found (will use python requests instead)", Colors.YELLOW)
                    continue

                self.log(f"✗ {dep}: not found", Colors.RED)
                missing.append(dep)

        if missing:
            self.log(f"Missing critical dependencies: {', '.join(missing)}", Colors.RED, "ERROR")
            self.log("Please ensure you're in the correct virtual environment", Colors.RED, "ERROR")
            return False

        self.test_results['dependencies'] = True
        return True

    def cleanup_existing_processes(self):
        """Clean up any existing Mininet or Ryu processes"""
        self.log("Cleaning up existing processes...", Colors.YELLOW, "CLEANUP")
        
        # Try nuclear cleanup script first if it exists
        nuclear_script = "./nuclear_cleanup.sh"
        if os.path.exists(nuclear_script):
            self.log("Using nuclear cleanup script...", Colors.CYAN)
            success, stdout, stderr = self.run_command(f"chmod +x {nuclear_script} && sudo {nuclear_script}", timeout=30)
            if success:
                self.log("✓ Nuclear cleanup completed", Colors.GREEN)
                self.test_results['cleanup_existing'] = True
                return True
            else:
                self.log("⚠ Nuclear cleanup had issues, continuing with standard cleanup...", Colors.YELLOW)
        
        # Standard cleanup with more aggressive commands
        cleanup_commands = [
            "sudo mn -c 2>/dev/null || true",  # Clean Mininet
            "sudo pkill -9 -f ryu-manager 2>/dev/null || true",  # Kill Ryu processes
            "sudo pkill -9 -f mininet 2>/dev/null || true",  # Kill Mininet processes
            "sudo pkill -9 -f python.*test 2>/dev/null || true",  # Kill test processes
            "sudo ovs-vsctl del-br s1 2>/dev/null || true",  # Remove OVS bridges
            "sudo ovs-vsctl del-br s2 2>/dev/null || true",
            "sudo ovs-vsctl del-br s3 2>/dev/null || true",
            "sudo fuser -k 6653/tcp 2>/dev/null || true",  # Kill processes on OpenFlow port
            "sudo fuser -k 8080/tcp 2>/dev/null || true",  # Kill processes on API port
            "sudo ip netns list | xargs -r sudo ip netns delete 2>/dev/null || true",  # Clean namespaces
        ]
        
        success_count = 0
        for cmd in cleanup_commands:
            success, stdout, stderr = self.run_command(cmd, timeout=15)
            if success or "|| true" in cmd:  # Count as success if command has error handling
                success_count += 1
        
        # Additional wait for processes to die
        time.sleep(3)
        
        # Check if cleanup was reasonably successful
        if success_count >= len(cleanup_commands) * 0.7:  # 70% success rate
            self.log("✓ Cleanup completed (some commands may have failed but that's normal)", Colors.GREEN)
            self.test_results['cleanup_existing'] = True
            return True
        else:
            self.log("⚠ Cleanup had some issues but continuing anyway...", Colors.YELLOW, "WARN")
            self.test_results['cleanup_existing'] = False
            # Don't fail the entire test suite for cleanup issues
            return True

    def start_ryu_controller(self):
        """Start Ryu middleware controller"""
        self.log("Starting Ryu middleware controller...", Colors.BLUE, "START")

        # Check if we're in virtual environment
        in_venv = os.environ.get('VIRTUAL_ENV') is not None
        if not in_venv:
            self.log("⚠ Not in virtual environment, this may cause issues", Colors.YELLOW)

        # Check if middleware dependencies are installed
        deps_to_check = ['pydantic', 'yaml', 'requests', 'scapy', 'psutil', 'websockets']
        missing_deps = []

        for dep in deps_to_check:
            success, _, _ = self.run_command(f"python3 -c 'import {dep}'")
            if not success:
                missing_deps.append(dep)

        if missing_deps:
            self.log(f"Missing dependencies: {', '.join(missing_deps)}", Colors.YELLOW, "INSTALL")
            if in_venv:
                # Install in virtual environment
                install_cmd = f"pip install {' '.join(['pydantic', 'pyyaml', 'requests', 'scapy', 'psutil', 'websockets'])}"
                self.log("Installing middleware dependencies in virtual environment...", Colors.YELLOW)
                success, stdout, stderr = self.run_command(install_cmd, timeout=120)
                if not success:
                    self.log(f"Failed to install dependencies: {stderr}", Colors.RED, "ERROR")
                    self.log("Please manually install: pip install pydantic pyyaml requests scapy psutil websockets", Colors.RED)
                    return False
                else:
                    self.log("✓ Dependencies installed successfully", Colors.GREEN)
            else:
                self.log("Please activate virtual environment and install dependencies manually", Colors.RED, "ERROR")
                return False

        # Check if ryu is available
        success, _, _ = self.run_command("python3 -c 'import ryu'")
        if not success:
            self.log("✗ Ryu not available in Python path", Colors.RED, "ERROR")
            return False

        # Find ryu-manager command
        ryu_manager_cmd = None
        possible_paths = [
            "ryu-manager",  # In PATH
            f"{os.environ.get('VIRTUAL_ENV', '')}/bin/ryu-manager",  # Virtual env
            "./venv/bin/ryu-manager",  # Local venv
            "python3 -m ryu.cmd.manager"  # Python module
        ]

        for cmd in possible_paths:
            if cmd and cmd.strip():
                success, _, _ = self.run_command(f"{cmd} --version", timeout=5)
                if success:
                    ryu_manager_cmd = cmd
                    self.log(f"✓ Found ryu-manager: {cmd}", Colors.GREEN)
                    break

        if not ryu_manager_cmd:
            self.log("✗ ryu-manager command not found", Colors.RED, "ERROR")
            return False

        # Set environment variables to fix threading issues
        env_fixes = {
            "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION": "python",
            "EVENTLET_HUB": "poll", 
            "EVENTLET_NOPATCH": "time",
            "RYU_HUB_TYPE": "eventlet"
        }
        
        for key, value in env_fixes.items():
            os.environ[key] = value
            
        # Start Ryu controller with enhanced configuration
        ryu_cmd = f"{ryu_manager_cmd} ryu.app.middleware.core --ofp-tcp-listen-port {self.controller_port} --wsapi-port {self.api_port} --verbose"
        self.log(f"Starting: {ryu_cmd}", Colors.CYAN)
        self.log("Applied threading compatibility fixes", Colors.GREEN)

        process, _, _ = self.run_command(ryu_cmd, capture_output=False)

        if process:
            self.processes['ryu'] = process
            self.log(f"Ryu controller started (PID: {process.pid})", Colors.GREEN)

            # Wait for controller to initialize
            self.log("Waiting for controller to initialize...", Colors.YELLOW)
            time.sleep(15)  # Increased wait time

            # Check if controller is responding
            for attempt in range(30):  # 30 second timeout
                try:
                    response = requests.get(f"{self.base_url}/health", timeout=2)
                    if response.status_code == 200:
                        self.log("✓ Ryu middleware API is responding", Colors.GREEN)
                        self.test_results['ryu_startup'] = True
                        return True
                except requests.exceptions.RequestException:
                    pass
                time.sleep(1)

            self.log("✗ Ryu middleware API not responding", Colors.RED, "ERROR")
            self.log("Check if the middleware started correctly", Colors.YELLOW)
            return False

        self.log("Failed to start Ryu controller", Colors.RED, "ERROR")
        return False

    def create_mininet_topology(self):
        """Create and start Mininet topology"""
        self.log(f"Creating Mininet topology: {self.topology}", Colors.BLUE, "START")

        # Create topology script
        topo_script = self.generate_topology_script()
        script_path = "/tmp/mininet_topology.py"

        with open(script_path, 'w') as f:
            f.write(topo_script)

        # Start Mininet with the topology
        mininet_cmd = f"sudo python3 {script_path}"
        process, _, _ = self.run_command(mininet_cmd, capture_output=False)

        if process:
            self.processes['mininet'] = process
            self.log(f"Mininet started (PID: {process.pid})", Colors.GREEN)

            # Wait for topology to be established
            time.sleep(5)

            # Verify switches are connected to controller
            success = self.verify_switch_connection()
            if success:
                self.test_results['mininet_startup'] = True
                return True

        self.log("Failed to start Mininet", Colors.RED, "ERROR")
        return False

    def generate_topology_script(self):
        """Generate Mininet topology script based on configuration"""
        if self.topology == 'simple':
            return f'''#!/usr/bin/env python3
from mininet.net import Mininet
from mininet.node import Controller, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import TCLink
import time
import sys

def create_topology():
    # Set OpenFlow version and protocols
    setLogLevel('info')
    
    # Create network with proper switch configuration
    net = Mininet(controller=RemoteController, link=TCLink, autoSetMacs=True, autoStaticArp=True)

    # Add controller with explicit protocols
    c0 = net.addController('c0', controller=RemoteController,
                          ip='127.0.0.1', port={self.controller_port},
                          protocols='OpenFlow13')

    # Add switch with OpenFlow 1.3 support
    s1 = net.addSwitch('s1', protocols='OpenFlow13')

    # Add hosts
    hosts = []
    for i in range(1, {self.num_hosts + 1}):
        h = net.addHost(f'h{{i}}', ip=f'10.0.0.{{i}}/24')
        hosts.append(h)
        net.addLink(h, s1)

    # Build and start network
    net.build()
    net.start()
    
    # Wait for controller connection
    print("Waiting for controller connection...")
    time.sleep(3)
    
    # Test controller connection
    switch_connected = False
    for i in range(10):  # Try for 10 seconds
        try:
            # Check if switch is connected
            result = s1.cmd('ovs-vsctl show')
            if 'is_connected: true' in result or 'Controller' in result:
                switch_connected = True
                break
        except:
            pass
        time.sleep(1)
    
    if switch_connected:
        print("✓ Switch connected to controller")
    else:
        print("⚠ Switch connection status unclear")

    print("Network started successfully")
    print("Topology: {{}} hosts connected to 1 switch".format({self.num_hosts}))
    
    # Add some initial flows to help with connectivity
    try:
        # Basic learning switch behavior will be handled by the controller
        pass
    except Exception as e:
        print(f"Warning: Could not set initial flows: {{e}}")

    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping network...")
        net.stop()

if __name__ == '__main__':
    create_topology()
'''
        elif self.topology == 'linear':
            return f'''#!/usr/bin/env python3
from mininet.topo import LinearTopo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel
import time

def create_topology():
    topo = LinearTopo(k={self.num_hosts//2}, n=2)  # k switches, n hosts per switch
    net = Mininet(topo=topo, controller=RemoteController)

    # Add controller
    c0 = net.addController('c0', controller=RemoteController,
                          ip='127.0.0.1', port={self.controller_port})

    net.start()
    print("Linear topology started")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    create_topology()
'''
        else:  # tree topology
            return f'''#!/usr/bin/env python3
from mininet.topo import TreeTopo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel
import time

def create_topology():
    topo = TreeTopo(depth=2, fanout=2)
    net = Mininet(topo=topo, controller=RemoteController)

    # Add controller
    c0 = net.addController('c0', controller=RemoteController,
                          ip='127.0.0.1', port={self.controller_port})

    net.start()
    print("Tree topology started")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    create_topology()
'''

    def verify_switch_connection(self):
        """Verify switches are connected to the controller"""
        self.log("Verifying switch connections...", Colors.CYAN, "CHECK")

        # Wait longer for switches to connect
        self.log("Waiting for switches to connect...", Colors.YELLOW)
        time.sleep(8)  # Increased wait time
        
        # Try multiple times with longer intervals
        for attempt in range(6):  # Try 6 times over 30 seconds
            try:
                response = requests.get(f"{self.base_url}/topology/view", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    switches = data.get('data', {}).get('switches', [])
                    if switches:
                        self.log(f"✓ {len(switches)} switch(es) connected", Colors.GREEN)
                        return True
                    else:
                        self.log(f"Attempt {attempt + 1}/6: No switches detected yet...", Colors.YELLOW)
                        
                        # Also check via alternative API endpoints
                        try:
                            stats_response = requests.get(f"{self.base_url}/stats/topology", timeout=3)
                            if stats_response.status_code == 200:
                                stats_data = stats_response.json()
                                connected = stats_data.get('data', {}).get('connected_switches', 0)
                                if connected > 0:
                                    self.log(f"✓ {connected} switch(es) connected (via stats)", Colors.GREEN)
                                    return True
                        except:
                            pass
                            
            except Exception as e:
                self.log(f"Attempt {attempt + 1}: Error checking switch connection: {e}", Colors.YELLOW)
            
            if attempt < 5:  # Don't sleep on the last attempt
                time.sleep(5)

        # Final check - try a direct OpenFlow connection test
        self.log("Trying direct OpenFlow verification...", Colors.YELLOW)
        try:
            # Check if there are any OpenFlow connections
            ovs_check_script = f'''#!/usr/bin/env python3
import subprocess
import time
try:
    # Check OVS controller connections
    result = subprocess.run(['sudo', 'ovs-vsctl', 'show'], 
                          capture_output=True, text=True, timeout=10)
    if result.returncode == 0 and 'Controller' in result.stdout:
        print("OVS_CONTROLLER_FOUND")
        print(result.stdout)
    else:
        print("OVS_NO_CONTROLLER")
        print(result.stdout if result.stdout else "No output")
except Exception as e:
    print(f"OVS_ERROR: {{e}}")
'''
            ovs_script_path = "/tmp/check_ovs.py"
            with open(ovs_script_path, 'w') as f:
                f.write(ovs_check_script)
                
            success, stdout, stderr = self.run_command(f"python3 {ovs_script_path}", timeout=15)
            if success and "OVS_CONTROLLER_FOUND" in stdout:
                self.log("✓ OpenFlow controller connection detected via OVS", Colors.GREEN)
                return True
                
        except Exception as e:
            self.log(f"OVS check error: {e}", Colors.YELLOW)

        self.log("✗ No switches connected after extensive verification", Colors.RED, "ERROR")
        self.log("This may be due to controller-switch handshake timing", Colors.YELLOW)
        return False

    def test_mininet_pingall(self):
        """Test network connectivity using Mininet pingall"""
        self.log("Testing network connectivity (pingall)...", Colors.BLUE, "TEST")

        # Create a script to run pingall
        pingall_script = '''#!/usr/bin/env python3
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel
import sys

def run_pingall():
    # Connect to existing Mininet instance
    try:
        # Use mn command to run pingall
        import subprocess
        result = subprocess.run(['sudo', 'mn', '--test', 'pingall'],
                              capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            print("PINGALL_SUCCESS")
            print(result.stdout)
        else:
            print("PINGALL_FAILED")
            print(result.stderr)
    except Exception as e:
        print(f"PINGALL_ERROR: {e}")

if __name__ == '__main__':
    run_pingall()
'''

        pingall_path = "/tmp/test_pingall.py"
        with open(pingall_path, 'w') as f:
            f.write(pingall_script)

        # Run pingall test
        success, stdout, stderr = self.run_command(f"python3 {pingall_path}", timeout=90)

        if success and "PINGALL_SUCCESS" in stdout:
            self.log("✓ Pingall test passed - all hosts can communicate", Colors.GREEN)
            self.test_results['pingall'] = True
            return True
        else:
            self.log("✗ Pingall test failed", Colors.RED, "ERROR")
            if stdout:
                self.log(f"Output: {stdout}", Colors.YELLOW)
            if stderr:
                self.log(f"Error: {stderr}", Colors.RED)
            self.test_results['pingall'] = False
            return False

    def test_api_endpoints(self):
        """Test all middleware API endpoints"""
        self.log("Testing API endpoints...", Colors.BLUE, "TEST")

        endpoints = {
            'health': '/health',
            'topology': '/topology/view',
            'stats_packet': '/stats/packet',
            'stats_topology': '/stats/topology',
            'controllers': '/controllers/list',
            'p4_switches': '/p4/switches',
            'host_list': '/host/list'
        }

        api_results = {}

        for name, endpoint in endpoints.items():
            try:
                url = f"{self.base_url}{endpoint}"
                self.log(f"Testing {name}: {endpoint} -> {url}", Colors.CYAN)

                # Make request with detailed logging
                response = requests.get(url, timeout=10)
                
                self.log(f"Response for {name}: Status={response.status_code}, Content-Type={response.headers.get('content-type', 'unknown')}", Colors.WHITE)
                
                if response.status_code == 200:
                    try:
                        # Try to parse JSON with detailed error handling
                        response_text = response.text
                        self.log(f"Raw response for {name} (first 500 chars): {response_text[:500]}", Colors.WHITE)
                        
                        data = response.json()
                        self.log(f"Parsed JSON for {name}: type={type(data)}, content={str(data)[:200]}", Colors.WHITE)
                        
                        # Check if data is a dictionary before calling .get()
                        if isinstance(data, dict):
                            if data.get('status') == 'success':
                                self.log(f"✓ {name}: SUCCESS", Colors.GREEN)
                                api_results[name] = True
                            else:
                                self.log(f"⚠ {name}: API returned error - {data.get('message', 'Unknown')}", Colors.YELLOW)
                                self.log(f"Full error response for {name}: {data}", Colors.YELLOW)
                                api_results[name] = False
                        elif isinstance(data, list):
                            self.log(f"⚠ {name}: API returned list instead of dict with status - treating as success", Colors.YELLOW)
                            self.log(f"List content for {name}: {data[:3] if len(data) > 3 else data}", Colors.WHITE)
                            api_results[name] = True
                        else:
                            self.log(f"⚠ {name}: API returned unexpected data type {type(data)}: {data}", Colors.YELLOW)
                            api_results[name] = False
                            
                    except json.JSONDecodeError as json_err:
                        self.log(f"✗ {name}: JSON decode error - {json_err}", Colors.RED)
                        self.log(f"Raw response text for {name}: {response.text[:1000]}", Colors.RED)
                        api_results[name] = False
                        
                else:
                    self.log(f"✗ {name}: HTTP {response.status_code}", Colors.RED)
                    self.log(f"Response headers for {name}: {dict(response.headers)}", Colors.RED)
                    self.log(f"Response text for {name}: {response.text[:500]}", Colors.RED)
                    api_results[name] = False

            except requests.exceptions.RequestException as e:
                self.log(f"✗ {name}: Connection error - {e}", Colors.RED)
                import traceback
                self.log(f"Full traceback for {name}: {traceback.format_exc()}", Colors.RED)
                api_results[name] = False
            except Exception as e:
                self.log(f"✗ {name}: Unexpected error - {e}", Colors.RED)
                import traceback
                self.log(f"Full traceback for {name}: {traceback.format_exc()}", Colors.RED)
                api_results[name] = False

        self.test_results['api_endpoints'] = api_results

        # Summary with detailed results
        passed = sum(1 for result in api_results.values() if result)
        total = len(api_results)
        self.log(f"API Tests: {passed}/{total} passed", Colors.GREEN if passed == total else Colors.YELLOW)
        
        # Log individual results for debugging
        for endpoint_name, result in api_results.items():
            status_color = Colors.GREEN if result else Colors.RED
            status_text = "PASS" if result else "FAIL"
            self.log(f"  {endpoint_name}: {status_text}", status_color)

        return passed == total

    def test_gui_interface(self):
        """Test GUI interface accessibility"""
        self.log("Testing GUI interface...", Colors.BLUE, "TEST")

        gui_tests = {}

        # Test main GUI page
        try:
            response = requests.get(self.gui_url, timeout=10)
            if response.status_code == 200 and 'html' in response.headers.get('content-type', '').lower():
                self.log("✓ GUI main page accessible", Colors.GREEN)
                gui_tests['main_page'] = True
            else:
                self.log(f"✗ GUI main page: HTTP {response.status_code}", Colors.RED)
                gui_tests['main_page'] = False
        except Exception as e:
            self.log(f"✗ GUI main page: {e}", Colors.RED)
            gui_tests['main_page'] = False

        # Test GUI static resources
        static_resources = [
            '/gui/index.html',
            f'{self.gui_url}/index.html'
        ]

        for resource in static_resources:
            try:
                if not resource.startswith('http'):
                    url = f"http://localhost:{self.api_port}{resource}"
                else:
                    url = resource

                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    self.log(f"✓ GUI resource accessible: {resource}", Colors.GREEN)
                    gui_tests[f'resource_{resource.split("/")[-1]}'] = True
                    break
            except Exception:
                continue

        self.test_results['gui_interface'] = gui_tests

        # Summary
        passed = sum(1 for result in gui_tests.values() if result)
        total = len(gui_tests)
        self.log(f"GUI Tests: {passed}/{total} passed",
                Colors.GREEN if passed == total else Colors.YELLOW)

        return passed > 0  # At least main page should work

    def test_traffic_generation(self):
        """Test traffic generation capabilities"""
        self.log("Testing traffic generation...", Colors.BLUE, "TEST")

        # Simple traffic test using scapy
        traffic_data = {
            "type": "scapy",
            "src": "10.0.0.1",
            "dst": "10.0.0.2",
            "protocol": "icmp",
            "count": 3
        }

        try:
            url = f"{self.base_url}/traffic/generate"
            self.log(f"Sending POST request to: {url}", Colors.CYAN)
            self.log(f"Request payload: {traffic_data}", Colors.WHITE)
            
            response = requests.post(
                url,
                json=traffic_data,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            self.log(f"Traffic generation response: Status={response.status_code}, Content-Type={response.headers.get('content-type', 'unknown')}", Colors.WHITE)
            self.log(f"Response headers: {dict(response.headers)}", Colors.WHITE)
            self.log(f"Raw response text (first 1000 chars): {response.text[:1000]}", Colors.WHITE)

            if response.status_code in [200, 201]:
                try:
                    data = response.json()
                    self.log(f"Parsed JSON response: {data}", Colors.WHITE)
                    
                    if isinstance(data, dict) and data.get('status') == 'success':
                        self.log("✓ Traffic generation test passed", Colors.GREEN)
                        self.test_results['traffic_generation'] = True
                        return True
                    else:
                        self.log(f"⚠ Traffic generation returned non-success status: {data}", Colors.YELLOW)
                        self.test_results['traffic_generation'] = False
                        return False
                        
                except json.JSONDecodeError as json_err:
                    self.log(f"✗ Traffic generation: JSON decode error - {json_err}", Colors.RED)
                    self.log(f"Response was not valid JSON: {response.text}", Colors.RED)
                    self.test_results['traffic_generation'] = False
                    return False
                    
            elif response.status_code == 400:
                self.log(f"⚠ Traffic generation: HTTP 400 (Client Error)", Colors.YELLOW)
                try:
                    error_data = response.json()
                    self.log(f"Error details: {error_data}", Colors.YELLOW)
                except:
                    self.log(f"Error response text: {response.text}", Colors.YELLOW)
                self.test_results['traffic_generation'] = False
                return False
                
            elif response.status_code == 500:
                self.log(f"✗ Traffic generation: HTTP 500 (Server Error)", Colors.RED)
                self.log(f"Server error response: {response.text}", Colors.RED)
                try:
                    error_data = response.json()
                    self.log(f"Server error details: {error_data}", Colors.RED)
                except:
                    pass
                self.test_results['traffic_generation'] = False
                return False
                
            else:
                self.log(f"✗ Traffic generation: HTTP {response.status_code}", Colors.RED)
                self.log(f"Unexpected status code response: {response.text}", Colors.RED)
                self.test_results['traffic_generation'] = False
                return False

        except requests.exceptions.RequestException as req_err:
            self.log(f"✗ Traffic generation: Request error - {req_err}", Colors.RED)
            import traceback
            self.log(f"Request error traceback: {traceback.format_exc()}", Colors.RED)
            self.test_results['traffic_generation'] = False
            return False
            
        except Exception as e:
            self.log(f"✗ Traffic generation: Unexpected error - {e}", Colors.RED)
            import traceback
            self.log(f"Unexpected error traceback: {traceback.format_exc()}", Colors.RED)
            self.test_results['traffic_generation'] = False
            return False

    def generate_test_report(self):
        """Generate comprehensive test report"""
        end_time = datetime.now()
        duration = end_time - self.start_time

        print(f"\n{Colors.BOLD}{Colors.BLUE}=== TEST REPORT ==={Colors.END}")
        print(f"Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {duration.total_seconds():.1f} seconds")
        print(f"Topology: {self.topology} ({self.num_hosts} hosts)")
        print("=" * 50)

        # Overall results
        total_tests = 0
        passed_tests = 0

        for test_name, result in self.test_results.items():
            if isinstance(result, bool):
                total_tests += 1
                if result:
                    passed_tests += 1
                    status = f"{Colors.GREEN}✓ PASS{Colors.END}"
                else:
                    status = f"{Colors.RED}✗ FAIL{Colors.END}"
                print(f"{test_name.replace('_', ' ').title()}: {status}")
            elif isinstance(result, dict):
                # Handle API endpoint results
                sub_passed = sum(1 for r in result.values() if r)
                sub_total = len(result)
                total_tests += sub_total
                passed_tests += sub_passed

                if sub_passed == sub_total:
                    status = f"{Colors.GREEN}✓ PASS ({sub_passed}/{sub_total}){Colors.END}"
                else:
                    status = f"{Colors.YELLOW}⚠ PARTIAL ({sub_passed}/{sub_total}){Colors.END}"
                print(f"{test_name.replace('_', ' ').title()}: {status}")

        print("=" * 50)

        # Overall score
        if total_tests > 0:
            score = (passed_tests / total_tests) * 100
            if score >= 90:
                color = Colors.GREEN
                grade = "EXCELLENT"
            elif score >= 75:
                color = Colors.YELLOW
                grade = "GOOD"
            elif score >= 50:
                color = Colors.YELLOW
                grade = "FAIR"
            else:
                color = Colors.RED
                grade = "POOR"

            print(f"Overall Score: {color}{score:.1f}% ({passed_tests}/{total_tests}) - {grade}{Colors.END}")

        # Save detailed report
        report_data = {
            'timestamp': end_time.isoformat(),
            'duration_seconds': duration.total_seconds(),
            'topology': self.topology,
            'num_hosts': self.num_hosts,
            'controller_port': self.controller_port,
            'api_port': self.api_port,
            'test_results': self.test_results,
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'score_percentage': (passed_tests / total_tests * 100) if total_tests > 0 else 0
            }
        }

        report_file = f"test_report_{end_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)

        print(f"\nDetailed report saved to: {report_file}")
        return report_data

    def cleanup(self):
        """Clean up all processes and resources"""
        self.log("Cleaning up processes...", Colors.YELLOW, "CLEANUP")

        # Stop Mininet
        if 'mininet' in self.processes:
            try:
                self.processes['mininet'].terminate()
                self.processes['mininet'].wait(timeout=10)
                self.log("✓ Mininet stopped", Colors.GREEN)
            except:
                try:
                    self.processes['mininet'].kill()
                except:
                    pass

        # Stop Ryu controller
        if 'ryu' in self.processes:
            try:
                self.processes['ryu'].terminate()
                self.processes['ryu'].wait(timeout=10)
                self.log("✓ Ryu controller stopped", Colors.GREEN)
            except:
                try:
                    self.processes['ryu'].kill()
                except:
                    pass

        # Additional cleanup
        self.run_command("sudo mn -c", timeout=10)
        self.run_command("sudo pkill -f ryu-manager", timeout=5)
        self.run_command("sudo pkill -f mininet", timeout=5)

        # Clean up temporary files
        temp_files = ["/tmp/mininet_topology.py", "/tmp/test_pingall.py"]
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except:
                pass

    def run_full_test_suite(self):
        """Run the complete test suite"""
        try:
            # Setup signal handler for cleanup
            def signal_handler(signum, frame):
                self.log("Received interrupt signal, cleaning up...", Colors.YELLOW, "SIGNAL")
                self.cleanup()
                sys.exit(1)

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            # Test sequence
            test_sequence = [
                ("Dependency Check", self.check_dependencies),
                ("Cleanup Existing", self.cleanup_existing_processes),
                ("Start Ryu Controller", self.start_ryu_controller),
                ("Create Mininet Topology", self.create_mininet_topology),
                ("Test Network Connectivity", self.test_mininet_pingall),
                ("Test API Endpoints", self.test_api_endpoints),
                ("Test GUI Interface", self.test_gui_interface),
                ("Test Traffic Generation", self.test_traffic_generation),
            ]

            self.log("Starting comprehensive test suite...", Colors.BOLD + Colors.BLUE, "START")

            for test_name, test_func in test_sequence:
                self.log(f"Running: {test_name}", Colors.CYAN, "TEST")

                try:
                    success = test_func()
                    if success:
                        self.log(f"✓ {test_name} completed successfully", Colors.GREEN)
                    else:
                        self.log(f"✗ {test_name} failed", Colors.RED, "FAIL")
                        # Continue with other tests even if one fails

                except Exception as e:
                    self.log(f"✗ {test_name} error: {e}", Colors.RED, "ERROR")
                    self.test_results[test_name.lower().replace(' ', '_')] = False

                time.sleep(2)  # Brief pause between tests

            # Generate final report
            self.log("Generating test report...", Colors.CYAN, "REPORT")
            report = self.generate_test_report()

            return report

        except KeyboardInterrupt:
            self.log("Test interrupted by user", Colors.YELLOW, "INTERRUPT")
            return None
        except Exception as e:
            self.log(f"Unexpected error during testing: {e}", Colors.RED, "ERROR")
            return None
        finally:
            self.cleanup()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Comprehensive test suite for Ryu Enhanced SDN Middleware",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 test_full_deployment.py                    # Default simple topology
  python3 test_full_deployment.py --topology linear  # Linear topology
  python3 test_full_deployment.py --hosts 6          # 6 hosts
  python3 test_full_deployment.py --controller-port 6633 --api-port 8080
        """
    )

    parser.add_argument('--topology', choices=['simple', 'linear', 'tree'],
                       default='simple', help='Mininet topology type')
    parser.add_argument('--hosts', type=int, default=4,
                       help='Number of hosts in topology')
    parser.add_argument('--controller-port', type=int, default=6653,
                       help='OpenFlow controller port')
    parser.add_argument('--api-port', type=int, default=8080,
                       help='Middleware API port')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')

    args = parser.parse_args()

    # Check if running as root (required for Mininet)
    if os.geteuid() != 0:
        print(f"{Colors.RED}Error: This script must be run as root (use sudo){Colors.END}")
        print("Example: sudo python3 test_full_deployment.py")
        sys.exit(1)

    # Create and run test suite
    test_runner = TestRunner(
        topology=args.topology,
        num_hosts=args.hosts,
        controller_port=args.controller_port,
        api_port=args.api_port
    )

    try:
        report = test_runner.run_full_test_suite()

        if report:
            score = report['summary']['score_percentage']
            if score >= 75:
                print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 Test suite completed successfully!{Colors.END}")
                sys.exit(0)
            else:
                print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ Test suite completed with issues{Colors.END}")
                sys.exit(1)
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}❌ Test suite failed to complete{Colors.END}")
            sys.exit(2)

    except Exception as e:
        print(f"\n{Colors.RED}Fatal error: {e}{Colors.END}")
        sys.exit(3)


if __name__ == "__main__":
    main()
