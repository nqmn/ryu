# Copyright (C) 2024 Ryu SDN Framework Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
P4Runtime Integration Tests

This module provides comprehensive tests for P4Runtime functionality
including backend integration, API endpoints, and mixed topology scenarios.
"""

import unittest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add the ryu directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ryu.app.middleware.sdn_backends.base import SDNControllerBase, SwitchType, FlowData, PacketData
from ryu.app.middleware.sdn_backends.switch_manager import SwitchManager
from ryu.app.middleware.sdn_backends.p4runtime_controller import P4RuntimeController
from ryu.app.middleware.p4runtime.client import P4RuntimeClient
from ryu.app.middleware.p4runtime.utils import P4RuntimeUtils, P4InfoHelper
from ryu.app.middleware.p4runtime.pipeline import PipelineManager


class TestP4RuntimeBackend(unittest.TestCase):
    """Test P4Runtime backend functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = {
            'p4runtime': {
                'enabled': True,
                'switches': [
                    {
                        'device_id': 1,
                        'address': 'localhost:50051',
                        'pipeline': '/tmp/test.json',
                        'p4info': '/tmp/test.p4info'
                    }
                ]
            }
        }
        
    def test_p4runtime_controller_initialization(self):
        """Test P4Runtime controller initialization"""
        controller = P4RuntimeController(self.config['p4runtime'])
        
        self.assertEqual(controller.get_switch_type(), SwitchType.P4RUNTIME)
        self.assertIn('1', controller.clients)
        self.assertIn('1', controller.switches)
        
    def test_flow_data_conversion(self):
        """Test FlowData creation for P4Runtime"""
        flow_data = FlowData(
            switch_id='1',
            switch_type=SwitchType.P4RUNTIME,
            table_name='ipv4_lpm',
            action_name='ipv4_forward',
            match_fields={'hdr.ipv4.dstAddr': '10.0.0.1/24'},
            action_params={'dstAddr': '00:00:00:00:00:01', 'port': '1'}
        )
        
        self.assertEqual(flow_data.switch_id, '1')
        self.assertEqual(flow_data.switch_type, SwitchType.P4RUNTIME)
        self.assertEqual(flow_data.table_name, 'ipv4_lpm')
        self.assertEqual(flow_data.action_name, 'ipv4_forward')
        
    @patch('ryu.app.middleware.p4runtime.client.P4RuntimeClient.connect')
    async def test_p4runtime_client_connection(self, mock_connect):
        """Test P4Runtime client connection"""
        mock_connect.return_value = True
        
        client = P4RuntimeClient(1, 'localhost', 50051)
        connected = await client.connect()
        
        self.assertTrue(connected)
        mock_connect.assert_called_once()


class TestSwitchManager(unittest.TestCase):
    """Test switch manager functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = {
            'openflow': {
                'enabled': True
            },
            'p4runtime': {
                'enabled': True,
                'switches': [
                    {'device_id': 1, 'address': 'localhost:50051'}
                ]
            }
        }
        
    def test_switch_manager_initialization(self):
        """Test switch manager initialization"""
        manager = SwitchManager(self.config)
        
        self.assertIsNotNone(manager)
        self.assertEqual(len(manager.switch_registry), 1)
        self.assertEqual(manager.switch_registry['1'], SwitchType.P4RUNTIME)
        
    def test_switch_type_detection(self):
        """Test switch type detection logic"""
        manager = SwitchManager(self.config)
        
        # Test P4Runtime switch detection
        self.assertEqual(manager.detect_switch_type('1'), SwitchType.P4RUNTIME)
        
        # Test OpenFlow switch detection
        self.assertEqual(manager.detect_switch_type('123456789'), SwitchType.OPENFLOW)
        self.assertEqual(manager.detect_switch_type('0x123'), SwitchType.OPENFLOW)
        
        # Test with P4-specific flow data
        flow_data = FlowData(
            switch_id='unknown',
            switch_type=None,
            table_name='test_table',
            action_name='test_action'
        )
        self.assertEqual(manager.detect_switch_type('unknown', flow_data), SwitchType.P4RUNTIME)


class TestP4RuntimeUtils(unittest.TestCase):
    """Test P4Runtime utility functions"""
    
    def test_value_encoding(self):
        """Test value encoding for P4Runtime"""
        # Test integer encoding
        encoded = P4RuntimeUtils.encode_value(42, 32)
        self.assertEqual(len(encoded), 4)
        
        # Test IP address encoding
        encoded = P4RuntimeUtils.encode_value('192.168.1.1')
        self.assertEqual(len(encoded), 4)
        
        # Test hex string encoding
        encoded = P4RuntimeUtils.encode_value('0x1234')
        self.assertEqual(encoded, b'\x12\x34')
        
    def test_value_decoding(self):
        """Test value decoding from P4Runtime"""
        # Test integer decoding
        data = b'\x00\x00\x00\x2a'  # 42 in big-endian
        decoded = P4RuntimeUtils.decode_value(data, 'int')
        self.assertEqual(decoded, 42)
        
        # Test IPv4 decoding
        data = b'\xc0\xa8\x01\x01'  # 192.168.1.1
        decoded = P4RuntimeUtils.decode_value(data, 'ipv4')
        self.assertEqual(decoded, '192.168.1.1')
        
        # Test MAC decoding
        data = b'\x00\x11\x22\x33\x44\x55'
        decoded = P4RuntimeUtils.decode_value(data, 'mac')
        self.assertEqual(decoded, '00:11:22:33:44:55')


class TestPipelineManager(unittest.TestCase):
    """Test P4 pipeline manager functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = {
            'pipeline_directory': '/tmp/pipelines',
            'pipelines': []
        }
        
    def test_pipeline_manager_initialization(self):
        """Test pipeline manager initialization"""
        manager = PipelineManager(self.config)
        
        self.assertIsNotNone(manager)
        self.assertEqual(manager.pipeline_directory, '/tmp/pipelines')
        
    def test_pipeline_validation(self):
        """Test pipeline validation"""
        manager = PipelineManager(self.config)
        
        # Test validation of non-existent pipeline
        result = manager.validate_pipeline('non_existent')
        self.assertFalse(result['valid'])
        self.assertIn('not found', result['error'])


class TestAPIIntegration(unittest.TestCase):
    """Test API integration with P4Runtime"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock the middleware components
        self.mock_switch_manager = Mock()
        self.mock_middleware_app = Mock()
        
    def test_flow_install_api_conversion(self):
        """Test flow install API with P4Runtime fields"""
        # Test data that would come from REST API
        api_request = {
            'switch_id': '1',
            'table_name': 'ipv4_lpm',
            'action_name': 'ipv4_forward',
            'match': {
                'hdr.ipv4.dstAddr': '10.0.0.1/24'
            },
            'action_params': {
                'dstAddr': '00:00:00:00:00:01',
                'port': '1'
            },
            'priority': 1000
        }
        
        # Convert to FlowData
        flow_data = FlowData(
            switch_id=str(api_request['switch_id']),
            switch_type=None,
            priority=api_request.get('priority', 1000),
            table_id=api_request.get('table_id'),
            match_fields=api_request.get('match', {}),
            actions=api_request.get('actions', []),
            metadata=api_request.get('metadata', {}),
            table_name=api_request.get('table_name'),
            action_name=api_request.get('action_name'),
            action_params=api_request.get('action_params', {})
        )
        
        self.assertEqual(flow_data.switch_id, '1')
        self.assertEqual(flow_data.table_name, 'ipv4_lpm')
        self.assertEqual(flow_data.action_name, 'ipv4_forward')
        self.assertEqual(flow_data.match_fields['hdr.ipv4.dstAddr'], '10.0.0.1/24')


class TestMixedTopology(unittest.TestCase):
    """Test mixed OpenFlow and P4Runtime topology scenarios"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = {
            'openflow': {
                'enabled': True
            },
            'p4runtime': {
                'enabled': True,
                'switches': [
                    {'device_id': 1, 'address': 'localhost:50051'},
                    {'device_id': 2, 'address': 'localhost:50052'}
                ]
            }
        }
        
    def test_mixed_topology_management(self):
        """Test managing mixed topology with both OpenFlow and P4Runtime switches"""
        manager = SwitchManager(self.config)
        
        # Verify P4Runtime switches are registered
        self.assertEqual(manager.detect_switch_type('1'), SwitchType.P4RUNTIME)
        self.assertEqual(manager.detect_switch_type('2'), SwitchType.P4RUNTIME)
        
        # Verify OpenFlow switches are detected by default
        self.assertEqual(manager.detect_switch_type('123456789'), SwitchType.OPENFLOW)
        
    def test_backend_routing(self):
        """Test that operations are routed to correct backends"""
        manager = SwitchManager(self.config)
        
        # Mock backends
        mock_of_backend = Mock()
        mock_p4_backend = Mock()
        
        manager.register_backend(SwitchType.OPENFLOW, mock_of_backend)
        manager.register_backend(SwitchType.P4RUNTIME, mock_p4_backend)
        
        # Test routing to P4Runtime backend
        backend = manager.get_backend_for_switch('1')
        self.assertEqual(backend, mock_p4_backend)
        
        # Test routing to OpenFlow backend
        backend = manager.get_backend_for_switch('123456789')
        self.assertEqual(backend, mock_of_backend)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
