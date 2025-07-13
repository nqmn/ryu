#!/usr/bin/env python3
"""
Multi-Controller SDN Middleware Demo

This script demonstrates the enhanced SDN middleware capabilities including:
- Multiple controller registration and management
- Switch-to-controller mapping
- Health monitoring and failover
- Real-time event streaming
- Unified API for heterogeneous SDN environments
"""

import asyncio
import json
import time
import requests
import websocket
import threading
from typing import Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
LOG = logging.getLogger(__name__)

class MultiControllerDemo:
    """Demo class for multi-controller SDN middleware"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.api_base = f"{base_url}/v2.0"
        self.ws_url = f"ws://localhost:8080/v2.0/events/ws"
        self.events_received = []
        self.ws = None
        
    def run_demo(self):
        """Run the complete demo"""
        print("\n" + "=" * 80)
        print("🚀 MULTI-CONTROLLER SDN MIDDLEWARE DEMO")
        print("=" * 80)
        
        try:
            self.demo_step_1_setup()
            self.demo_step_2_register_controllers()
            self.demo_step_3_health_monitoring()
            self.demo_step_4_switch_mapping()
            self.demo_step_5_event_streaming()
            self.demo_step_6_failover()
            self.demo_step_7_cleanup()
            
            print("\n🎉 Demo completed successfully!")
            print("The multi-controller SDN middleware is working correctly.")
            
        except Exception as e:
            print(f"\n❌ Demo failed: {e}")
            LOG.error(f"Demo error: {e}")
    
    def demo_step_1_setup(self):
        """Step 1: Verify middleware is running"""
        print("\n📋 Step 1: Verifying Middleware Setup")
        print("-" * 40)
        
        try:
            response = requests.get(f"{self.api_base}/topology/view", timeout=5)
            response.raise_for_status()
            print("✅ Middleware API is accessible")
            
            response = requests.get(f"{self.api_base}/controllers/list", timeout=5)
            response.raise_for_status()
            data = response.json()
            print(f"✅ Controller management API is working")
            print(f"   Current controllers: {data.get('data', {}).get('total_count', 0)}")
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Middleware not accessible: {e}")
    
    def demo_step_2_register_controllers(self):
        """Step 2: Register multiple controllers"""
        print("\n🎛️  Step 2: Registering Multiple Controllers")
        print("-" * 40)
        
        # Register OpenFlow controller
        openflow_config = {
            "config": {
                "controller_id": "demo_openflow",
                "controller_type": "ryu_openflow",
                "name": "Demo OpenFlow Controller",
                "description": "OpenFlow controller for demonstration",
                "host": "localhost",
                "port": 6653,
                "health_check_interval": 30,
                "priority": 100
            },
            "auto_start": True
        }
        
        print("📡 Registering OpenFlow controller...")
        response = requests.post(f"{self.api_base}/controllers/register", json=openflow_config)
        if response.status_code == 201:
            print("✅ OpenFlow controller registered successfully")
        else:
            print(f"⚠️  OpenFlow controller registration: {response.status_code}")
        
        # Register P4Runtime controller
        p4_config = {
            "config": {
                "controller_id": "demo_p4runtime",
                "controller_type": "p4runtime", 
                "name": "Demo P4Runtime Controller",
                "description": "P4Runtime controller for demonstration",
                "host": "localhost",
                "port": 50051,
                "health_check_interval": 30,
                "priority": 90,
                "backup_controllers": ["demo_openflow"]
            },
            "auto_start": True
        }
        
        print("📡 Registering P4Runtime controller...")
        response = requests.post(f"{self.api_base}/controllers/register", json=p4_config)
        if response.status_code == 201:
            print("✅ P4Runtime controller registered successfully")
        else:
            print(f"⚠️  P4Runtime controller registration: {response.status_code}")
        
        # List all controllers
        response = requests.get(f"{self.api_base}/controllers/list")
        if response.status_code == 200:
            data = response.json()
            controllers = data.get('data', {}).get('controllers', [])
            print(f"\n📊 Total registered controllers: {len(controllers)}")
            for controller in controllers:
                config = controller.get('config', {})
                print(f"   • {config.get('name', 'Unknown')} ({config.get('controller_type', 'Unknown')})")
    
    def demo_step_3_health_monitoring(self):
        """Step 3: Demonstrate health monitoring"""
        print("\n💓 Step 3: Health Monitoring")
        print("-" * 40)
        
        controllers = ["demo_openflow", "demo_p4runtime"]
        
        for controller_id in controllers:
            print(f"🔍 Checking health of {controller_id}...")
            try:
                response = requests.get(f"{self.api_base}/controllers/health/{controller_id}")
                if response.status_code == 200:
                    health_data = response.json()
                    overall_health = health_data.get('data', {}).get('overall_health', 'unknown')
                    print(f"   Status: {overall_health}")
                    
                    summary = health_data.get('data', {}).get('summary', {})
                    uptime = summary.get('uptime_seconds', 0)
                    print(f"   Uptime: {uptime:.1f} seconds")
                else:
                    print(f"   ⚠️  Health check failed: {response.status_code}")
            except Exception as e:
                print(f"   ❌ Health check error: {e}")
    
    def demo_step_4_switch_mapping(self):
        """Step 4: Demonstrate switch mapping"""
        print("\n🔗 Step 4: Switch-to-Controller Mapping")
        print("-" * 40)
        
        # Map switches to controllers
        mappings = [
            {
                "switch_id": "demo_switch_of_1",
                "primary_controller": "demo_openflow",
                "backup_controllers": ["demo_p4runtime"]
            },
            {
                "switch_id": "demo_switch_p4_1", 
                "primary_controller": "demo_p4runtime",
                "backup_controllers": ["demo_openflow"]
            },
            {
                "switch_id": "demo_switch_of_2",
                "primary_controller": "demo_openflow",
                "backup_controllers": []
            }
        ]
        
        for mapping in mappings:
            switch_id = mapping["switch_id"]
            primary = mapping["primary_controller"]
            print(f"🔗 Mapping {switch_id} to {primary}...")
            
            response = requests.post(f"{self.api_base}/switches/map", json=mapping)
            if response.status_code == 201:
                print(f"   ✅ Mapped successfully")
            else:
                print(f"   ⚠️  Mapping failed: {response.status_code}")
        
        # Show all mappings
        response = requests.get(f"{self.api_base}/switches/mappings")
        if response.status_code == 200:
            data = response.json()
            mappings = data.get('data', {}).get('mappings', [])
            print(f"\n📊 Total switch mappings: {len(mappings)}")
            for mapping in mappings:
                switch_id = mapping.get('switch_id', 'Unknown')
                current = mapping.get('current_controller', 'Unknown')
                primary = mapping.get('primary_controller', 'Unknown')
                print(f"   • {switch_id} → {current} (primary: {primary})")
    
    def demo_step_5_event_streaming(self):
        """Step 5: Demonstrate real-time event streaming"""
        print("\n📡 Step 5: Real-time Event Streaming")
        print("-" * 40)
        
        def on_message(ws, message):
            try:
                event_data = json.loads(message)
                event_type = event_data.get('event_type', 'unknown')
                self.events_received.append(event_data)
                
                if event_type == 'welcome':
                    print("   📨 Received welcome message")
                    features = event_data.get('features', {})
                    print(f"      Multi-controller support: {features.get('multi_controller', False)}")
                    print(f"      Event filtering: {features.get('filtering', False)}")
                else:
                    print(f"   📨 Event: {event_type}")
                    
            except json.JSONDecodeError:
                print(f"   ⚠️  Failed to parse message: {message}")
        
        def on_error(ws, error):
            print(f"   ❌ WebSocket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            print("   🔌 WebSocket connection closed")
        
        def on_open(ws):
            print("   🔌 WebSocket connection established")
        
        print("🔌 Connecting to WebSocket event stream...")
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # Run WebSocket in background
        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        
        # Wait for events
        time.sleep(3)
        print(f"   📊 Received {len(self.events_received)} events")
    
    def demo_step_6_failover(self):
        """Step 6: Demonstrate failover functionality"""
        print("\n🔄 Step 6: Failover Demonstration")
        print("-" * 40)
        
        # Perform manual failover
        failover_config = {
            "switch_id": "demo_switch_of_1",
            "target_controller": "demo_p4runtime"
        }
        
        print("🔄 Performing manual failover...")
        print(f"   Switch: {failover_config['switch_id']}")
        print(f"   Target: {failover_config['target_controller']}")
        
        response = requests.post(f"{self.api_base}/switches/failover", json=failover_config)
        if response.status_code == 200:
            data = response.json()
            result = data.get('data', {})
            print("   ✅ Failover completed successfully")
            print(f"      Old controller: {result.get('old_controller', 'Unknown')}")
            print(f"      New controller: {result.get('new_controller', 'Unknown')}")
        else:
            print(f"   ⚠️  Failover failed: {response.status_code}")
        
        # Verify mapping update
        time.sleep(1)
        response = requests.get(f"{self.api_base}/switches/mappings")
        if response.status_code == 200:
            data = response.json()
            mappings = data.get('data', {}).get('mappings', [])
            for mapping in mappings:
                if mapping.get('switch_id') == 'demo_switch_of_1':
                    current = mapping.get('current_controller', 'Unknown')
                    failover_count = mapping.get('failover_count', 0)
                    print(f"   📊 Current controller: {current}")
                    print(f"   📊 Failover count: {failover_count}")
                    break
    
    def demo_step_7_cleanup(self):
        """Step 7: Clean up demo resources"""
        print("\n🧹 Step 7: Cleanup")
        print("-" * 40)
        
        # Close WebSocket
        if self.ws:
            self.ws.close()
            print("✅ WebSocket connection closed")
        
        # Deregister controllers
        controllers = ["demo_p4runtime", "demo_openflow"]
        for controller_id in controllers:
            print(f"🗑️  Deregistering {controller_id}...")
            response = requests.delete(f"{self.api_base}/controllers/deregister/{controller_id}")
            if response.status_code == 200:
                print(f"   ✅ Deregistered successfully")
            else:
                print(f"   ⚠️  Deregistration failed: {response.status_code}")
        
        print("✅ Cleanup completed")


def main():
    """Main demo function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Multi-Controller SDN Middleware Demo")
    parser.add_argument('--url', default='http://localhost:8080',
                       help='Base URL of the middleware API')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    demo = MultiControllerDemo(args.url)
    demo.run_demo()


if __name__ == "__main__":
    main()
