#!/usr/bin/env python3
"""
Multi-Controller SDN Middleware Test

This script tests the enhanced SDN middleware with multi-controller support,
including controller registration, switch mapping, health monitoring, and
failover functionality.
"""

import asyncio
import json
import time
import requests
import websocket
from typing import Dict, Any, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)

class MultiControllerTester:
    """Test suite for multi-controller SDN middleware"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.api_base = f"{base_url}/v2.0"
        self.ws_url = f"ws://localhost:8080/v2.0/events/ws"
        self.test_results = {}
        
    def run_all_tests(self):
        """Run comprehensive test suite"""
        LOG.info("Starting Multi-Controller SDN Middleware Test Suite")
        LOG.info("=" * 60)
        
        tests = [
            ("API Connectivity", self.test_api_connectivity),
            ("Controller Registration", self.test_controller_registration),
            ("Controller Health Monitoring", self.test_health_monitoring),
            ("Switch Mapping", self.test_switch_mapping),
            ("Event Stream", self.test_event_stream),
            ("Failover Functionality", self.test_failover),
            ("Controller Deregistration", self.test_controller_deregistration),
        ]
        
        for test_name, test_func in tests:
            LOG.info(f"\n🧪 Running Test: {test_name}")
            try:
                result = test_func()
                self.test_results[test_name] = {"status": "PASS", "result": result}
                LOG.info(f"✅ {test_name}: PASSED")
            except Exception as e:
                self.test_results[test_name] = {"status": "FAIL", "error": str(e)}
                LOG.error(f"❌ {test_name}: FAILED - {e}")
        
        self.print_test_summary()
    
    def test_api_connectivity(self) -> Dict[str, Any]:
        """Test basic API connectivity"""
        # Test topology endpoint (should exist from original middleware)
        response = requests.get(f"{self.api_base}/topology/view", timeout=10)
        response.raise_for_status()
        
        # Test new controller endpoints
        response = requests.get(f"{self.api_base}/controllers/list", timeout=10)
        response.raise_for_status()
        
        return {"topology_api": "OK", "controller_api": "OK"}
    
    def test_controller_registration(self) -> Dict[str, Any]:
        """Test controller registration functionality"""
        results = {}
        
        # Test OpenFlow controller registration
        openflow_config = {
            "config": {
                "controller_id": "test_openflow_1",
                "controller_type": "ryu_openflow",
                "name": "Test OpenFlow Controller 1",
                "description": "Test OpenFlow controller for multi-controller testing",
                "host": "localhost",
                "port": 6653,
                "health_check_interval": 30,
                "priority": 100
            },
            "auto_start": True
        }
        
        response = requests.post(
            f"{self.api_base}/controllers/register",
            json=openflow_config,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        results["openflow_registration"] = data
        
        # Test P4Runtime controller registration
        p4_config = {
            "config": {
                "controller_id": "test_p4_1",
                "controller_type": "p4runtime",
                "name": "Test P4Runtime Controller 1",
                "description": "Test P4Runtime controller for multi-controller testing",
                "host": "localhost",
                "port": 50051,
                "health_check_interval": 30,
                "priority": 90,
                "backup_controllers": ["test_openflow_1"]
            },
            "auto_start": True
        }
        
        response = requests.post(
            f"{self.api_base}/controllers/register",
            json=p4_config,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        results["p4_registration"] = data
        
        # Verify controllers are listed
        response = requests.get(f"{self.api_base}/controllers/list", timeout=10)
        response.raise_for_status()
        controllers_data = response.json()
        results["controller_list"] = controllers_data
        
        # Verify we have at least 2 controllers
        if controllers_data.get("data", {}).get("total_count", 0) < 2:
            raise Exception("Expected at least 2 registered controllers")
        
        return results
    
    def test_health_monitoring(self) -> Dict[str, Any]:
        """Test health monitoring functionality"""
        results = {}
        
        # Test health check for OpenFlow controller
        response = requests.get(
            f"{self.api_base}/controllers/health/test_openflow_1",
            timeout=10
        )
        response.raise_for_status()
        health_data = response.json()
        results["openflow_health"] = health_data
        
        # Test health check for P4Runtime controller
        response = requests.get(
            f"{self.api_base}/controllers/health/test_p4_1",
            timeout=10
        )
        response.raise_for_status()
        health_data = response.json()
        results["p4_health"] = health_data
        
        return results
    
    def test_switch_mapping(self) -> Dict[str, Any]:
        """Test switch-to-controller mapping"""
        results = {}
        
        # Map a test switch to OpenFlow controller
        mapping_config = {
            "switch_id": "test_switch_1",
            "primary_controller": "test_openflow_1",
            "backup_controllers": ["test_p4_1"]
        }
        
        response = requests.post(
            f"{self.api_base}/switches/map",
            json=mapping_config,
            timeout=10
        )
        response.raise_for_status()
        mapping_data = response.json()
        results["switch_mapping"] = mapping_data
        
        # Map another switch to P4Runtime controller
        mapping_config2 = {
            "switch_id": "test_switch_2",
            "primary_controller": "test_p4_1",
            "backup_controllers": ["test_openflow_1"]
        }
        
        response = requests.post(
            f"{self.api_base}/switches/map",
            json=mapping_config2,
            timeout=10
        )
        response.raise_for_status()
        mapping_data2 = response.json()
        results["switch_mapping_2"] = mapping_data2
        
        # Get all mappings
        response = requests.get(f"{self.api_base}/switches/mappings", timeout=10)
        response.raise_for_status()
        mappings_data = response.json()
        results["all_mappings"] = mappings_data
        
        # Verify we have at least 2 mappings
        if mappings_data.get("data", {}).get("total_count", 0) < 2:
            raise Exception("Expected at least 2 switch mappings")
        
        return results
    
    def test_event_stream(self) -> Dict[str, Any]:
        """Test WebSocket event streaming"""
        results = {}
        events_received = []
        
        def on_message(ws, message):
            try:
                event_data = json.loads(message)
                events_received.append(event_data)
                LOG.info(f"Received event: {event_data.get('event_type', 'unknown')}")
            except json.JSONDecodeError:
                LOG.warning(f"Failed to parse WebSocket message: {message}")
        
        def on_error(ws, error):
            LOG.error(f"WebSocket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            LOG.info("WebSocket connection closed")
        
        def on_open(ws):
            LOG.info("WebSocket connection opened")
        
        # Test WebSocket connection
        ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # Run WebSocket in a separate thread for a short time
        import threading
        ws_thread = threading.Thread(target=ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        
        # Wait for connection and some events
        time.sleep(3)
        
        # Close WebSocket
        ws.close()
        
        results["events_received"] = len(events_received)
        results["sample_events"] = events_received[:5]  # First 5 events
        
        # We should receive at least a welcome message
        if len(events_received) == 0:
            raise Exception("No events received from WebSocket")
        
        return results
    
    def test_failover(self) -> Dict[str, Any]:
        """Test manual failover functionality"""
        results = {}
        
        # Perform manual failover for test_switch_1
        failover_config = {
            "switch_id": "test_switch_1",
            "target_controller": "test_p4_1"
        }
        
        response = requests.post(
            f"{self.api_base}/switches/failover",
            json=failover_config,
            timeout=10
        )
        response.raise_for_status()
        failover_data = response.json()
        results["manual_failover"] = failover_data
        
        # Verify the mapping was updated
        response = requests.get(f"{self.api_base}/switches/mappings", timeout=10)
        response.raise_for_status()
        mappings_data = response.json()
        
        # Find the updated mapping
        updated_mapping = None
        for mapping in mappings_data.get("data", {}).get("mappings", []):
            if mapping["switch_id"] == "test_switch_1":
                updated_mapping = mapping
                break
        
        if not updated_mapping:
            raise Exception("Could not find updated mapping after failover")
        
        if updated_mapping["current_controller"] != "test_p4_1":
            raise Exception("Failover did not update current controller correctly")
        
        results["updated_mapping"] = updated_mapping
        
        return results
    
    def test_controller_deregistration(self) -> Dict[str, Any]:
        """Test controller deregistration"""
        results = {}
        
        # Deregister P4Runtime controller
        response = requests.delete(
            f"{self.api_base}/controllers/deregister/test_p4_1",
            timeout=10
        )
        response.raise_for_status()
        deregister_data = response.json()
        results["p4_deregistration"] = deregister_data
        
        # Deregister OpenFlow controller
        response = requests.delete(
            f"{self.api_base}/controllers/deregister/test_openflow_1",
            timeout=10
        )
        response.raise_for_status()
        deregister_data2 = response.json()
        results["openflow_deregistration"] = deregister_data2
        
        # Verify controllers are removed
        response = requests.get(f"{self.api_base}/controllers/list", timeout=10)
        response.raise_for_status()
        controllers_data = response.json()
        results["final_controller_list"] = controllers_data
        
        return results
    
    def print_test_summary(self):
        """Print test results summary"""
        LOG.info("\n" + "=" * 60)
        LOG.info("TEST SUMMARY")
        LOG.info("=" * 60)
        
        passed = sum(1 for result in self.test_results.values() if result["status"] == "PASS")
        total = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            LOG.info(f"{status_icon} {test_name}: {result['status']}")
            if result["status"] == "FAIL":
                LOG.info(f"   Error: {result['error']}")
        
        LOG.info(f"\nResults: {passed}/{total} tests passed")
        
        if passed == total:
            LOG.info("🎉 All tests passed! Multi-controller system is working correctly.")
        else:
            LOG.warning(f"⚠️  {total - passed} test(s) failed. Please check the implementation.")


def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Multi-Controller SDN Middleware")
    parser.add_argument('--url', default='http://localhost:8080', 
                       help='Base URL of the middleware API')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    tester = MultiControllerTester(args.url)
    tester.run_all_tests()


if __name__ == "__main__":
    main()
