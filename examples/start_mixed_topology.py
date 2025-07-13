#!/usr/bin/env python3
"""
Mixed Topology Example

This script demonstrates how to set up and use a mixed topology with both
OpenFlow and P4Runtime switches using the Ryu Middleware API.
"""

import requests
import json
import time
import subprocess
import os
import signal
import sys
from threading import Thread

# Configuration
MIDDLEWARE_URL = "http://localhost:8080/v2.0"
BMV2_BINARY = "simple_switch_grpc"
P4_PROGRAM = "./examples/p4/basic_forwarding.json"
P4INFO_FILE = "./examples/p4/basic_forwarding.p4info"

class MixedTopologyDemo:
    def __init__(self):
        self.bmv2_processes = []
        self.middleware_process = None
        
    def compile_p4_program(self):
        """Compile P4 program to JSON"""
        print("🔨 Compiling P4 program...")
        
        p4_source = "./examples/p4/basic_forwarding.p4"
        
        if not os.path.exists(p4_source):
            print(f"❌ P4 source file not found: {p4_source}")
            return False
        
        try:
            # Compile P4 program
            cmd = [
                "p4c-bm2-ss",
                "--p4v", "16",
                "--p4runtime-files", P4INFO_FILE,
                "-o", P4_PROGRAM,
                p4_source
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ P4 program compiled successfully")
                print(f"   JSON: {P4_PROGRAM}")
                print(f"   P4Info: {P4INFO_FILE}")
                return True
            else:
                print(f"❌ P4 compilation failed:")
                print(result.stderr)
                return False
                
        except FileNotFoundError:
            print("❌ p4c-bm2-ss not found. Please install P4 compiler.")
            return False
    
    def start_bmv2_switches(self):
        """Start BMv2 switches"""
        print("🚀 Starting BMv2 switches...")
        
        switches = [
            {"device_id": 1, "grpc_port": 50051, "thrift_port": 9090},
            {"device_id": 2, "grpc_port": 50052, "thrift_port": 9091},
        ]
        
        for switch in switches:
            print(f"   Starting BMv2 switch {switch['device_id']}...")
            
            cmd = [
                BMV2_BINARY,
                "--device-id", str(switch["device_id"]),
                "--thrift-port", str(switch["thrift_port"]),
                "--grpc-server-addr", f"0.0.0.0:{switch['grpc_port']}",
                "--log-console",
                P4_PROGRAM
            ]
            
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setsid
                )
                
                self.bmv2_processes.append(process)
                print(f"   ✅ BMv2 switch {switch['device_id']} started (PID: {process.pid})")
                
                # Give switch time to start
                time.sleep(2)
                
            except FileNotFoundError:
                print(f"❌ {BMV2_BINARY} not found. Please install BMv2.")
                return False
        
        return True
    
    def start_middleware(self):
        """Start Ryu middleware with P4Runtime support"""
        print("🚀 Starting Ryu middleware...")
        
        config_file = "./examples/p4runtime_config.yaml"
        
        cmd = [
            "ryu-manager",
            "ryu.app.middleware.core",
            "--config-file", config_file
        ]
        
        try:
            self.middleware_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            print(f"✅ Middleware started (PID: {self.middleware_process.pid})")
            
            # Wait for middleware to start
            time.sleep(5)
            
            return True
            
        except FileNotFoundError:
            print("❌ ryu-manager not found. Please install Ryu.")
            return False
    
    def wait_for_middleware(self):
        """Wait for middleware to be ready"""
        print("⏳ Waiting for middleware to be ready...")
        
        for i in range(30):  # Wait up to 30 seconds
            try:
                response = requests.get(f"{MIDDLEWARE_URL}/health", timeout=2)
                if response.status_code == 200:
                    print("✅ Middleware is ready!")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(1)
            print(f"   Waiting... ({i+1}/30)")
        
        print("❌ Middleware failed to start")
        return False
    
    def install_p4_pipelines(self):
        """Install P4 pipelines on switches"""
        print("📦 Installing P4 pipelines...")
        
        switches = [1, 2]
        
        for switch_id in switches:
            print(f"   Installing pipeline on switch {switch_id}...")
            
            pipeline_data = {
                "switch_id": str(switch_id),
                "pipeline_name": "basic_forwarding",
                "p4info_path": P4INFO_FILE,
                "config_path": P4_PROGRAM
            }
            
            try:
                response = requests.post(
                    f"{MIDDLEWARE_URL}/p4/pipeline/install",
                    json=pipeline_data,
                    timeout=10
                )
                
                if response.status_code == 201:
                    print(f"   ✅ Pipeline installed on switch {switch_id}")
                else:
                    print(f"   ❌ Failed to install pipeline on switch {switch_id}: {response.text}")
                    
            except requests.exceptions.RequestException as e:
                print(f"   ❌ Error installing pipeline on switch {switch_id}: {e}")
    
    def install_sample_flows(self):
        """Install sample flows on both OpenFlow and P4Runtime switches"""
        print("🌊 Installing sample flows...")
        
        # P4Runtime flow (table entry)
        p4_flow = {
            "switch_id": "1",
            "table_name": "ipv4_lpm",
            "action_name": "ipv4_forward",
            "match": {
                "hdr.ipv4.dstAddr": "10.0.0.1/32"
            },
            "action_params": {
                "dstAddr": "00:00:00:00:00:01",
                "port": "1"
            },
            "priority": 1000
        }
        
        try:
            response = requests.post(
                f"{MIDDLEWARE_URL}/flow/install",
                json=p4_flow,
                timeout=5
            )
            
            if response.status_code == 201:
                print("   ✅ P4Runtime flow installed")
            else:
                print(f"   ❌ Failed to install P4Runtime flow: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Error installing P4Runtime flow: {e}")
        
        # OpenFlow flow (if OpenFlow switches are available)
        of_flow = {
            "dpid": "123456789",  # Example OpenFlow switch
            "match": {"in_port": 1},
            "actions": [{"type": "OUTPUT", "port": 2}],
            "priority": 1000
        }
        
        try:
            response = requests.post(
                f"{MIDDLEWARE_URL}/flow/install",
                json=of_flow,
                timeout=5
            )
            
            if response.status_code == 201:
                print("   ✅ OpenFlow flow installed")
            else:
                print(f"   ⚠️  OpenFlow flow not installed (no OpenFlow switches): {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ⚠️  OpenFlow flow not installed: {e}")
    
    def show_status(self):
        """Show current status of the mixed topology"""
        print("\n📊 Topology Status:")
        
        try:
            # Get health status
            response = requests.get(f"{MIDDLEWARE_URL}/health", timeout=5)
            if response.status_code == 200:
                health = response.json()
                print(f"   Middleware: {health.get('data', {}).get('middleware', 'unknown')}")
                
                backends = health.get('data', {}).get('sdn_backends', {})
                print(f"   SDN Backends: {backends}")
            
            # Get P4 switches
            response = requests.get(f"{MIDDLEWARE_URL}/p4/switches", timeout=5)
            if response.status_code == 200:
                switches = response.json()
                switch_count = switches.get('data', {}).get('total_count', 0)
                print(f"   P4Runtime switches: {switch_count}")
            
            # Get pipeline status
            response = requests.get(f"{MIDDLEWARE_URL}/p4/pipeline/status", timeout=5)
            if response.status_code == 200:
                pipeline_status = response.json()
                data = pipeline_status.get('data', {})
                print(f"   Installed switches: {data.get('installed_switches', 0)}")
                print(f"   Total pipelines: {data.get('total_pipelines', 0)}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Error getting status: {e}")
    
    def cleanup(self):
        """Clean up all processes"""
        print("\n🧹 Cleaning up...")
        
        # Stop middleware
        if self.middleware_process:
            print("   Stopping middleware...")
            self.middleware_process.terminate()
            self.middleware_process.wait()
        
        # Stop BMv2 switches
        for i, process in enumerate(self.bmv2_processes):
            print(f"   Stopping BMv2 switch {i+1}...")
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait()
        
        print("✅ Cleanup completed")
    
    def run_demo(self):
        """Run the complete mixed topology demo"""
        print("🎯 Mixed Topology Demo Starting...")
        print("=" * 50)
        
        try:
            # Step 1: Compile P4 program
            if not self.compile_p4_program():
                return False
            
            # Step 2: Start BMv2 switches
            if not self.start_bmv2_switches():
                return False
            
            # Step 3: Start middleware
            if not self.start_middleware():
                return False
            
            # Step 4: Wait for middleware
            if not self.wait_for_middleware():
                return False
            
            # Step 5: Install P4 pipelines
            self.install_p4_pipelines()
            
            # Step 6: Install sample flows
            self.install_sample_flows()
            
            # Step 7: Show status
            self.show_status()
            
            print("\n🎉 Demo setup completed!")
            print("\nYou can now:")
            print(f"   • Access REST API: {MIDDLEWARE_URL}")
            print(f"   • Connect WebSocket: ws://localhost:8080/v2.0/events/ws")
            print(f"   • View health: {MIDDLEWARE_URL}/health")
            print(f"   • Check P4 status: {MIDDLEWARE_URL}/p4/pipeline/status")
            print("\nPress Ctrl+C to stop the demo...")
            
            # Keep running until interrupted
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\n⏹️  Demo interrupted by user")
        except Exception as e:
            print(f"\n❌ Demo failed: {e}")
        finally:
            self.cleanup()


def main():
    """Main function"""
    demo = MixedTopologyDemo()
    
    # Set up signal handler for clean shutdown
    def signal_handler(sig, frame):
        print("\n🛑 Received shutdown signal")
        demo.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the demo
    demo.run_demo()


if __name__ == "__main__":
    main()
