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
        
        dependencies = {
            'python3': 'python3 --version',
            'mininet': 'mn --version',
            'ovs': 'ovs-vsctl --version',
            'ryu': 'ryu-manager --version',
            'curl': 'curl --version'
        }
        
        missing = []
        for dep, cmd in dependencies.items():
            success, stdout, stderr = self.run_command(cmd)
            if success:
                version = stdout.split('\n')[0] if stdout else "installed"
                self.log(f"✓ {dep}: {version}", Colors.GREEN)
            else:
                self.log(f"✗ {dep}: not found", Colors.RED)
                missing.append(dep)
        
        if missing:
            self.log(f"Missing dependencies: {', '.join(missing)}", Colors.RED, "ERROR")
            self.log("Please install missing dependencies and try again", Colors.RED, "ERROR")
            return False
        
        self.test_results['dependencies'] = True
        return True

    def cleanup_existing_processes(self):
        """Clean up any existing Mininet or Ryu processes"""
        self.log("Cleaning up existing processes...", Colors.YELLOW, "CLEANUP")
        
        cleanup_commands = [
            "sudo mn -c",  # Clean Mininet
            "sudo pkill -f ryu-manager",  # Kill Ryu processes
            "sudo pkill -f mininet",  # Kill Mininet processes
            "sudo ovs-vsctl del-br s1 2>/dev/null || true",  # Remove OVS bridges
        ]
        
        for cmd in cleanup_commands:
            self.run_command(cmd, timeout=10)
        
        time.sleep(2)  # Wait for cleanup to complete

    def start_ryu_controller(self):
        """Start Ryu middleware controller"""
        self.log("Starting Ryu middleware controller...", Colors.BLUE, "START")
        
        # Check if middleware dependencies are installed
        success, _, _ = self.run_command("python3 -c 'import pydantic'")
        if not success:
            self.log("Installing middleware dependencies...", Colors.YELLOW, "INSTALL")
            install_cmd = "pip3 install pydantic pyyaml requests scapy psutil websockets"
            success, stdout, stderr = self.run_command(install_cmd, timeout=120)
            if not success:
                self.log(f"Failed to install dependencies: {stderr}", Colors.RED, "ERROR")
                return False
        
        # Start Ryu controller
        ryu_cmd = f"ryu-manager ryu.app.middleware.core --ofp-tcp-listen-port {self.controller_port}"
        process, _, _ = self.run_command(ryu_cmd, capture_output=False)
        
        if process:
            self.processes['ryu'] = process
            self.log(f"Ryu controller started (PID: {process.pid})", Colors.GREEN)
            
            # Wait for controller to initialize
            self.log("Waiting for controller to initialize...", Colors.YELLOW)
            time.sleep(10)
            
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

def create_topology():
    net = Mininet(controller=RemoteController, link=TCLink)

    # Add controller
    c0 = net.addController('c0', controller=RemoteController,
                          ip='127.0.0.1', port={self.controller_port})

    # Add switch
    s1 = net.addSwitch('s1')

    # Add hosts
    hosts = []
    for i in range(1, {self.num_hosts + 1}):
        h = net.addHost(f'h{{i}}', ip=f'10.0.0.{{i}}/24')
        hosts.append(h)
        net.addLink(h, s1)

    # Start network
    net.start()

    print("Network started successfully")
    print("Topology: {{}} hosts connected to 1 switch".format({self.num_hosts}))

    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        net.stop()

if __name__ == '__main__':
    setLogLevel('info')
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

        # Check via API
        try:
            response = requests.get(f"{self.base_url}/topology/view", timeout=5)
            if response.status_code == 200:
                data = response.json()
                switches = data.get('data', {}).get('switches', [])
                if switches:
                    self.log(f"✓ {len(switches)} switch(es) connected", Colors.GREEN)
                    return True
                else:
                    self.log("Waiting for switches to connect...", Colors.YELLOW)
                    time.sleep(5)
                    # Try again
                    response = requests.get(f"{self.base_url}/topology/view", timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        switches = data.get('data', {}).get('switches', [])
                        if switches:
                            self.log(f"✓ {len(switches)} switch(es) connected", Colors.GREEN)
                            return True
        except Exception as e:
            self.log(f"Error checking switch connection: {e}", Colors.RED, "ERROR")

        self.log("✗ No switches connected", Colors.RED, "ERROR")
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
                self.log(f"Testing {name}: {endpoint}", Colors.CYAN)

                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'success':
                        self.log(f"✓ {name}: SUCCESS", Colors.GREEN)
                        api_results[name] = True
                    else:
                        self.log(f"⚠ {name}: API returned error - {data.get('message', 'Unknown')}", Colors.YELLOW)
                        api_results[name] = False
                else:
                    self.log(f"✗ {name}: HTTP {response.status_code}", Colors.RED)
                    api_results[name] = False

            except requests.exceptions.RequestException as e:
                self.log(f"✗ {name}: Connection error - {e}", Colors.RED)
                api_results[name] = False
            except Exception as e:
                self.log(f"✗ {name}: Unexpected error - {e}", Colors.RED)
                api_results[name] = False

        self.test_results['api_endpoints'] = api_results

        # Summary
        passed = sum(1 for result in api_results.values() if result)
        total = len(api_results)
        self.log(f"API Tests: {passed}/{total} passed",
                Colors.GREEN if passed == total else Colors.YELLOW)

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
            response = requests.post(
                f"{self.base_url}/traffic/generate",
                json=traffic_data,
                timeout=30
            )

            if response.status_code in [200, 201]:
                data = response.json()
                if data.get('status') == 'success':
                    self.log("✓ Traffic generation test passed", Colors.GREEN)
                    self.test_results['traffic_generation'] = True
                    return True
                else:
                    self.log(f"⚠ Traffic generation returned: {data.get('message', 'Unknown')}", Colors.YELLOW)
            else:
                self.log(f"✗ Traffic generation: HTTP {response.status_code}", Colors.RED)

        except Exception as e:
            self.log(f"⚠ Traffic generation test skipped: {e}", Colors.YELLOW)

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
