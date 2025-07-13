#!/usr/bin/env python3
"""
Ryu Middleware API Usage Examples

This script demonstrates how to use the Ryu Middleware API for various
network management tasks including topology creation, traffic generation,
and monitoring.
"""

import requests
import json
import time
import websocket
import threading

# API Configuration
API_BASE = "http://localhost:8080"
WS_URL = "ws://localhost:8080/v2.0/events/ws"

class MiddlewareClient:
    """Simple client for Ryu Middleware API"""
    
    def __init__(self, base_url=API_BASE):
        self.base_url = base_url
        self.session = requests.Session()
    
    def get(self, endpoint):
        """GET request"""
        response = self.session.get(f"{self.base_url}{endpoint}")
        return response.json() if response.headers.get('content-type') == 'application/json' else response.text
    
    def post(self, endpoint, data):
        """POST request"""
        response = self.session.post(f"{self.base_url}{endpoint}", json=data)
        return response.json() if response.headers.get('content-type') == 'application/json' else response.text
    
    def delete(self, endpoint):
        """DELETE request"""
        response = self.session.delete(f"{self.base_url}{endpoint}")
        return response.json() if response.headers.get('content-type') == 'application/json' else response.text

def example_health_check():
    """Example: Check middleware health"""
    print("=== Health Check Example ===")
    
    client = MiddlewareClient()
    
    try:
        health = client.get("/v2.0/health")
        print(f"Health Status: {json.dumps(health, indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

def example_topology_management():
    """Example: Create and manage topology"""
    print("\n=== Topology Management Example ===")
    
    client = MiddlewareClient()
    
    # Define a simple topology
    topology = {
        "name": "example_topology",
        "switches": [
            {"name": "s1"},
            {"name": "s2"}
        ],
        "hosts": [
            {"name": "h1", "ip": "10.0.0.1"},
            {"name": "h2", "ip": "10.0.0.2"},
            {"name": "h3", "ip": "10.0.0.3"},
            {"name": "h4", "ip": "10.0.0.4"}
        ],
        "links": [
            {"src": "h1", "dst": "s1"},
            {"src": "h2", "dst": "s1"},
            {"src": "h3", "dst": "s2"},
            {"src": "h4", "dst": "s2"},
            {"src": "s1", "dst": "s2", "bandwidth": 100}
        ]
    }
    
    try:
        # Create topology
        print("Creating topology...")
        result = client.post("/v2.0/topology/create", topology)
        print(f"Creation result: {json.dumps(result, indent=2)}")
        
        # Check topology status
        print("\nChecking topology status...")
        status = client.get("/v2.0/topology/status")
        print(f"Status: {json.dumps(status, indent=2)}")
        
        # List hosts
        print("\nListing hosts...")
        hosts = client.get("/v2.0/host/list")
        print(f"Hosts: {json.dumps(hosts, indent=2)}")
        
        # Wait a bit
        time.sleep(2)
        
        # Delete topology
        print("\nDeleting topology...")
        delete_result = client.delete("/v2.0/topology/delete")
        print(f"Deletion result: {json.dumps(delete_result, indent=2)}")
        
    except Exception as e:
        print(f"Error: {e}")

def example_traffic_generation():
    """Example: Generate network traffic"""
    print("\n=== Traffic Generation Example ===")
    
    client = MiddlewareClient()
    
    # ICMP traffic specification
    icmp_traffic = {
        "type": "icmp",
        "src": "h1",
        "dst": "h2",
        "count": 5,
        "interval": 1
    }
    
    try:
        # Generate ICMP traffic
        print("Generating ICMP traffic...")
        result = client.post("/v2.0/traffic/generate", icmp_traffic)
        print(f"Traffic generation result: {json.dumps(result, indent=2)}")
        
        # Check traffic status
        print("\nChecking traffic status...")
        status = client.get("/v2.0/traffic/status")
        print(f"Traffic status: {json.dumps(status, indent=2)}")
        
    except Exception as e:
        print(f"Error: {e}")

def example_monitoring():
    """Example: Monitor network statistics"""
    print("\n=== Monitoring Example ===")
    
    client = MiddlewareClient()
    
    try:
        # Get flow statistics
        print("Getting flow statistics...")
        flow_stats = client.get("/v2.0/stats/flow")
        print(f"Flow stats: {json.dumps(flow_stats, indent=2)}")
        
        # Get port statistics
        print("\nGetting port statistics...")
        port_stats = client.get("/v2.0/stats/port")
        print(f"Port stats: {json.dumps(port_stats, indent=2)}")
        
        # Get packet statistics
        print("\nGetting packet statistics...")
        packet_stats = client.get("/v2.0/stats/packet")
        print(f"Packet stats: {json.dumps(packet_stats, indent=2)}")
        
        # Get topology statistics
        print("\nGetting topology statistics...")
        topo_stats = client.get("/v2.0/stats/topology")
        print(f"Topology stats: {json.dumps(topo_stats, indent=2)}")
        
    except Exception as e:
        print(f"Error: {e}")

def example_ml_integration():
    """Example: ML integration"""
    print("\n=== ML Integration Example ===")
    
    client = MiddlewareClient()
    
    try:
        # List available models
        print("Listing available ML models...")
        models = client.get("/v2.0/ml/models")
        print(f"Available models: {json.dumps(models, indent=2)}")
        
        # Perform inference (if ML is enabled)
        if models.get('status') == 'success':
            print("\nPerforming ML inference...")
            inference_data = {
                "model_name": "anomaly_detector",
                "data": {
                    "packet_count": 1000,
                    "byte_count": 64000,
                    "duration": 10,
                    "src_ip": "10.0.0.1",
                    "dst_ip": "10.0.0.2"
                }
            }
            
            inference_result = client.post("/v2.0/ml/infer", inference_data)
            print(f"Inference result: {json.dumps(inference_result, indent=2)}")
        
    except Exception as e:
        print(f"Error: {e}")

def example_websocket_events():
    """Example: WebSocket event streaming"""
    print("\n=== WebSocket Events Example ===")
    
    def on_message(ws, message):
        try:
            data = json.loads(message)
            print(f"Event received: {data.get('event_type', 'unknown')}")
            print(f"  Data: {json.dumps(data, indent=2)}")
        except Exception as e:
            print(f"Error parsing message: {e}")
    
    def on_error(ws, error):
        print(f"WebSocket error: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        print("WebSocket connection closed")
    
    def on_open(ws):
        print("WebSocket connection opened")
        print("Listening for events... (will close after 10 seconds)")
        
        # Close after 10 seconds for demo
        def close_after_delay():
            time.sleep(10)
            ws.close()
        
        threading.Thread(target=close_after_delay).start()
    
    try:
        # Create WebSocket connection
        ws = websocket.WebSocketApp(
            WS_URL,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # Run WebSocket (this will block for 10 seconds)
        ws.run_forever()
        
    except Exception as e:
        print(f"WebSocket error: {e}")

def main():
    """Run all examples"""
    print("Ryu Middleware API Usage Examples")
    print("=" * 50)
    
    # Run examples
    example_health_check()
    example_topology_management()
    example_traffic_generation()
    example_monitoring()
    example_ml_integration()
    example_websocket_events()
    
    print("\n" + "=" * 50)
    print("Examples completed!")
    print("\nTo start the middleware, run:")
    print("  ryu-manager ryu.app.middleware.core")
    print("\nAPI Documentation:")
    print("  REST API: http://localhost:8080/v2.0/")
    print("  WebSocket: ws://localhost:8080/v2.0/events/ws")

if __name__ == "__main__":
    main()
