#!/usr/bin/env python3
"""
Terminal GUI Demo Script

This script demonstrates the SDN Middleware Terminal GUI by generating
sample network events and testing the terminal functionality.
"""

import time
import requests
import json
import asyncio
import websockets
import threading
import random
from datetime import datetime, timedelta

class TerminalEventGenerator:
    def __init__(self, ws_url='ws://localhost:8080/v2.0/events/ws'):
        self.ws_url = ws_url
        self.running = False
        self.websocket = None
        
        # Sample data for generating events
        self.switch_ids = ['s1', 's2', 's3', 's4']
        self.host_macs = ['00:00:00:00:00:01', '00:00:00:00:00:02', '00:00:00:00:00:03', '00:00:00:00:00:04']
        self.host_ips = ['10.0.0.1', '10.0.0.2', '10.0.0.3', '10.0.0.4']
        self.protocols = ['TCP', 'UDP', 'ICMP', 'ARP']
        
    async def connect(self):
        """Connect to WebSocket"""
        try:
            self.websocket = await websockets.connect(self.ws_url)
            print(f"✅ Connected to WebSocket: {self.ws_url}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to WebSocket: {e}")
            return False
    
    async def send_event(self, event):
        """Send event to WebSocket"""
        if self.websocket:
            try:
                await self.websocket.send(json.dumps(event))
                print(f"📤 Sent event: {event['event']}")
            except Exception as e:
                print(f"❌ Failed to send event: {e}")
    
    def generate_packet_in_event(self):
        """Generate a packet_in event"""
        return {
            "timestamp": datetime.now().isoformat() + "Z",
            "event": "packet_in",
            "switch_id": random.choice(self.switch_ids),
            "src_ip": random.choice(self.host_ips),
            "dst_ip": random.choice(self.host_ips),
            "protocol": random.choice(self.protocols),
            "data": {
                "dpid": random.choice(self.switch_ids),
                "in_port": random.randint(1, 4),
                "packet_size": random.randint(64, 1500)
            }
        }
    
    def generate_flow_mod_event(self):
        """Generate a flow_mod event"""
        return {
            "timestamp": datetime.now().isoformat() + "Z",
            "event": "flow_mod",
            "switch_id": random.choice(self.switch_ids),
            "data": {
                "dpid": random.choice(self.switch_ids),
                "table_id": 0,
                "priority": random.randint(1, 100),
                "idle_timeout": random.randint(10, 300),
                "hard_timeout": random.randint(30, 600)
            }
        }
    
    def generate_switch_event(self, action='enter'):
        """Generate a switch enter/leave event"""
        switch_id = random.choice(self.switch_ids)
        return {
            "timestamp": datetime.now().isoformat() + "Z",
            "event": f"switch_{action}",
            "data": {
                "dpid": switch_id,
                "address": f"127.0.0.1:{random.randint(6653, 6660)}",
                "connected": action == 'enter'
            }
        }
    
    def generate_link_event(self, action='add'):
        """Generate a link add/delete event"""
        switches = random.sample(self.switch_ids, 2)
        return {
            "timestamp": datetime.now().isoformat() + "Z",
            "event": f"link_{action}",
            "data": {
                "src": {
                    "dpid": switches[0],
                    "port_no": random.randint(1, 4)
                },
                "dst": {
                    "dpid": switches[1],
                    "port_no": random.randint(1, 4)
                }
            }
        }
    
    def generate_host_event(self):
        """Generate a host_add event"""
        return {
            "timestamp": datetime.now().isoformat() + "Z",
            "event": "host_add",
            "data": {
                "mac": random.choice(self.host_macs),
                "ipv4": [random.choice(self.host_ips)],
                "port": {
                    "dpid": random.choice(self.switch_ids),
                    "port_no": random.randint(1, 4)
                }
            }
        }
    
    def generate_alert_event(self):
        """Generate an alert event"""
        alert_types = [
            "High traffic detected",
            "Suspicious packet pattern",
            "Flow table overflow",
            "Link congestion warning",
            "Anomalous behavior detected"
        ]
        
        return {
            "timestamp": datetime.now().isoformat() + "Z",
            "event": "alert",
            "data": {
                "message": random.choice(alert_types),
                "severity": random.choice(["low", "medium", "high"]),
                "switch_id": random.choice(self.switch_ids)
            }
        }
    
    def generate_error_event(self):
        """Generate an error event"""
        error_types = [
            "Flow installation failed",
            "Port down detected",
            "Controller connection lost",
            "Invalid packet format",
            "Table miss error"
        ]
        
        return {
            "timestamp": datetime.now().isoformat() + "Z",
            "event": "error",
            "data": {
                "message": random.choice(error_types),
                "error_code": random.randint(1000, 9999),
                "switch_id": random.choice(self.switch_ids)
            }
        }
    
    def generate_ml_event(self):
        """Generate an ML prediction event"""
        predictions = [
            "Normal traffic",
            "DDoS attack detected",
            "Port scan detected",
            "Anomalous flow pattern",
            "Bandwidth prediction"
        ]
        
        return {
            "timestamp": datetime.now().isoformat() + "Z",
            "event": "ml_prediction",
            "data": {
                "prediction": random.choice(predictions),
                "confidence": random.uniform(0.7, 0.99),
                "model": "traffic_classifier_v2"
            }
        }
    
    async def generate_event_sequence(self):
        """Generate a sequence of related events"""
        print("\n🎬 Generating event sequence...")
        
        # Sequence 1: Switch connection and topology discovery
        await self.send_event(self.generate_switch_event('enter'))
        await asyncio.sleep(0.5)
        
        await self.send_event(self.generate_link_event('add'))
        await asyncio.sleep(0.3)
        
        await self.send_event(self.generate_host_event())
        await asyncio.sleep(0.5)
        
        # Sequence 2: Traffic flow
        for _ in range(3):
            await self.send_event(self.generate_packet_in_event())
            await asyncio.sleep(0.2)
            await self.send_event(self.generate_flow_mod_event())
            await asyncio.sleep(0.3)
        
        # Sequence 3: Alert and response
        await self.send_event(self.generate_alert_event())
        await asyncio.sleep(0.5)
        await self.send_event(self.generate_flow_mod_event())  # Response to alert
        
        print("✅ Event sequence completed")
    
    async def run_continuous_demo(self, duration=60):
        """Run continuous event generation"""
        print(f"\n🔄 Starting continuous demo for {duration} seconds...")
        
        start_time = time.time()
        event_count = 0
        
        while time.time() - start_time < duration:
            # Generate random event
            event_type = random.choices(
                ['packet_in', 'flow_mod', 'switch', 'link', 'host', 'alert', 'error', 'ml'],
                weights=[40, 30, 5, 5, 5, 5, 5, 5]
            )[0]
            
            if event_type == 'packet_in':
                event = self.generate_packet_in_event()
            elif event_type == 'flow_mod':
                event = self.generate_flow_mod_event()
            elif event_type == 'switch':
                event = self.generate_switch_event(random.choice(['enter', 'leave']))
            elif event_type == 'link':
                event = self.generate_link_event(random.choice(['add', 'delete']))
            elif event_type == 'host':
                event = self.generate_host_event()
            elif event_type == 'alert':
                event = self.generate_alert_event()
            elif event_type == 'error':
                event = self.generate_error_event()
            elif event_type == 'ml':
                event = self.generate_ml_event()
            
            await self.send_event(event)
            event_count += 1
            
            # Variable delay between events
            delay = random.uniform(0.5, 3.0)
            await asyncio.sleep(delay)
        
        print(f"✅ Continuous demo completed. Generated {event_count} events")
    
    async def close(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            print("🔌 WebSocket connection closed")

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

def check_gui_accessible():
    """Check if the GUI is accessible"""
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

async def main():
    """Main demo function"""
    print("🖥️ SDN Middleware Terminal GUI Demo")
    print("=" * 50)
    
    # Check prerequisites
    if not check_middleware_running():
        print("\n❌ Please start the middleware first:")
        print("   python -m ryu.cmd.manager ryu.app.middleware.core")
        return False
    
    if not check_gui_accessible():
        print("\n❌ GUI is not accessible. Please check the middleware.")
        return False
    
    print("\n📋 Terminal Features to Test:")
    print("1. Open http://localhost:8080/ in your browser")
    print("2. Look for the terminal panel at the bottom")
    print("3. Check the terminal toggle button (🖥️) in the header")
    print("4. Use Ctrl+T to toggle terminal visibility")
    
    # Initialize event generator
    generator = TerminalEventGenerator()
    
    if not await generator.connect():
        print("\n❌ Could not connect to WebSocket. Terminal events will not work.")
        return False
    
    try:
        print("\n🎯 Demo Options:")
        print("1. Generate event sequence (recommended)")
        print("2. Run continuous demo (60 seconds)")
        print("3. Generate single events manually")
        
        choice = input("\nSelect option (1-3): ").strip()
        
        if choice == '1':
            await generator.generate_event_sequence()
            
        elif choice == '2':
            await generator.run_continuous_demo(60)
            
        elif choice == '3':
            print("\n📝 Manual event generation:")
            print("Available events: packet_in, flow_mod, switch_enter, link_add, host_add, alert, error, ml")
            
            while True:
                event_type = input("Enter event type (or 'quit'): ").strip()
                if event_type == 'quit':
                    break
                
                if event_type == 'packet_in':
                    await generator.send_event(generator.generate_packet_in_event())
                elif event_type == 'flow_mod':
                    await generator.send_event(generator.generate_flow_mod_event())
                elif event_type == 'switch_enter':
                    await generator.send_event(generator.generate_switch_event('enter'))
                elif event_type == 'link_add':
                    await generator.send_event(generator.generate_link_event('add'))
                elif event_type == 'host_add':
                    await generator.send_event(generator.generate_host_event())
                elif event_type == 'alert':
                    await generator.send_event(generator.generate_alert_event())
                elif event_type == 'error':
                    await generator.send_event(generator.generate_error_event())
                elif event_type == 'ml':
                    await generator.send_event(generator.generate_ml_event())
                else:
                    print("Unknown event type")
        
        print("\n🎉 Demo completed successfully!")
        print("\n📋 Terminal Features Demonstrated:")
        print("✅ Real-time event streaming")
        print("✅ Color-coded event types")
        print("✅ Event filtering and search")
        print("✅ Terminal controls (pause/resume/clear)")
        print("✅ Event details on click")
        print("✅ Integration with topology graph")
        
        print("\n💡 Try these features in the GUI:")
        print("• Click on events to see details")
        print("• Use the search and filter controls")
        print("• Pause/resume the event stream")
        print("• Export events to JSON/CSV/log")
        print("• Toggle terminal visibility with Ctrl+T")
        print("• Click on graph nodes to see related events")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
    finally:
        await generator.close()
    
    return True

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
