#!/usr/bin/env python3
"""
GUI Dashboard Demo Script

This script demonstrates the SDN Middleware GUI dashboard by creating
a simple test topology using Mininet (if available) or by simulating
switch connections directly.
"""

import time
import requests
import json
import subprocess
import sys
import os

def check_middleware_running():
    """Check if the middleware is running"""
    try:
        response = requests.get('http://localhost:8080/v2.0/health', timeout=5)
        if response.status_code == 200:
            print("✅ Middleware is running")
            return True
        else:
            print(f"❌ Middleware returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Middleware is not running: {e}")
        return False

def test_api_endpoints():
    """Test the middleware API endpoints"""
    print("\n🧪 Testing API Endpoints...")
    
    endpoints = [
        '/v2.0/health',
        '/v2.0/topology/view',
        '/v2.0/stats/topology'
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f'http://localhost:8080{endpoint}', timeout=5)
            if response.status_code == 200:
                print(f"✅ {endpoint} - OK")
            else:
                print(f"❌ {endpoint} - Status {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint} - Error: {e}")

def test_gui_access():
    """Test GUI access"""
    print("\n🌐 Testing GUI Access...")
    
    try:
        response = requests.get('http://localhost:8080/', timeout=5)
        if response.status_code == 200 and 'SDN Middleware' in response.text:
            print("✅ GUI is accessible")
            return True
        else:
            print(f"❌ GUI returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ GUI is not accessible: {e}")
        return False

def check_mininet_available():
    """Check if Mininet is available"""
    try:
        result = subprocess.run(['mn', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Mininet is available")
            return True
        else:
            print("❌ Mininet is not available")
            return False
    except Exception:
        print("❌ Mininet is not available")
        return False

def create_mininet_topology():
    """Create a simple Mininet topology"""
    print("\n🏗️ Creating Mininet topology...")
    
    try:
        # Create a simple linear topology with 3 switches and 3 hosts
        cmd = [
            'mn', 
            '--controller=remote,ip=127.0.0.1,port=6653',
            '--topo=linear,3',
            '--switch=ovsk',
            '--link=tc'
        ]
        
        print("Starting Mininet with linear topology (3 switches, 3 hosts)...")
        print("Command:", ' '.join(cmd))
        print("Note: This will run in the background. Use 'sudo mn -c' to clean up later.")
        
        # Start Mininet in background
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a bit for topology to be created
        time.sleep(5)
        
        if process.poll() is None:
            print("✅ Mininet topology started")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Mininet failed to start: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"❌ Failed to create Mininet topology: {e}")
        return None

def wait_for_topology():
    """Wait for topology to appear in the middleware"""
    print("\n⏳ Waiting for topology to be discovered...")
    
    for i in range(30):  # Wait up to 30 seconds
        try:
            response = requests.get('http://localhost:8080/v2.0/topology/view', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('data'):
                    switches = data['data'].get('switches', [])
                    hosts = data['data'].get('hosts', [])
                    links = data['data'].get('links', [])
                    
                    if switches or hosts or links:
                        print(f"✅ Topology discovered: {len(switches)} switches, {len(hosts)} hosts, {len(links)} links")
                        return True
                        
        except Exception as e:
            pass
            
        print(f"⏳ Waiting... ({i+1}/30)")
        time.sleep(1)
    
    print("❌ No topology discovered within 30 seconds")
    return False

def display_topology_info():
    """Display current topology information"""
    print("\n📊 Current Topology Information:")
    
    try:
        response = requests.get('http://localhost:8080/v2.0/topology/view', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('data'):
                topology = data['data']
                switches = topology.get('switches', [])
                hosts = topology.get('hosts', [])
                links = topology.get('links', [])
                
                print(f"Switches: {len(switches)}")
                for switch in switches:
                    print(f"  - DPID: {switch.get('dpid', 'N/A')}")
                
                print(f"Hosts: {len(hosts)}")
                for host in hosts:
                    print(f"  - MAC: {host.get('mac', 'N/A')}, IP: {host.get('ipv4', ['N/A'])[0] if host.get('ipv4') else 'N/A'}")
                
                print(f"Links: {len(links)}")
                for link in links:
                    src = link.get('src', {})
                    dst = link.get('dst', {})
                    print(f"  - {src.get('dpid', 'N/A')}:{src.get('port_no', 'N/A')} -> {dst.get('dpid', 'N/A')}:{dst.get('port_no', 'N/A')}")
                    
            else:
                print("No topology data available")
                
    except Exception as e:
        print(f"❌ Failed to get topology info: {e}")

def main():
    """Main demo function"""
    print("🌐 SDN Middleware GUI Dashboard Demo")
    print("=" * 50)
    
    # Check if middleware is running
    if not check_middleware_running():
        print("\n❌ Please start the middleware first:")
        print("   python -m ryu.cmd.manager ryu.app.middleware.core")
        return False
    
    # Test API endpoints
    test_api_endpoints()
    
    # Test GUI access
    if not test_gui_access():
        return False
    
    print("\n🎉 Basic tests passed!")
    print("\n📋 Dashboard Features to Test:")
    print("1. Open http://localhost:8080/ in your browser")
    print("2. Check connection status (should show 'Connected')")
    print("3. Try the theme toggle (dark/light mode)")
    print("4. Test sidebar collapse/expand")
    print("5. Use search and filter controls")
    print("6. Try different layout options")
    
    # Check for Mininet
    if check_mininet_available():
        print("\n🤔 Would you like to create a test topology with Mininet?")
        print("This will help demonstrate the real-time visualization features.")
        
        response = input("Create Mininet topology? (y/n): ").lower().strip()
        if response == 'y':
            process = create_mininet_topology()
            if process:
                if wait_for_topology():
                    display_topology_info()
                    
                    print("\n🎉 Demo topology created successfully!")
                    print("\n📋 Additional Features to Test:")
                    print("1. Click on switches/hosts to see details")
                    print("2. Watch real-time updates in the dashboard")
                    print("3. Try the export functions")
                    print("4. Test the ping functionality")
                    
                    print(f"\n⚠️  Remember to clean up when done:")
                    print("   sudo mn -c")
                    
                    return True
    else:
        print("\n💡 To test with a real topology:")
        print("1. Install Mininet: sudo apt-get install mininet")
        print("2. Or connect physical OpenFlow switches")
        print("3. Or use other SDN emulators")
    
    print("\n✅ Demo completed successfully!")
    print("The dashboard is ready to use at: http://localhost:8080/")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        sys.exit(1)
