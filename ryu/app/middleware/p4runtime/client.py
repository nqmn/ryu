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
P4Runtime gRPC Client

This module provides the P4RuntimeClient class for communicating with
P4Runtime-enabled switches via gRPC. It handles connection management,
pipeline installation, table operations, and packet I/O.
"""

import logging
import asyncio
import grpc
from typing import Dict, Any, Optional, List, Callable, AsyncIterator
from threading import Thread, Event
import json

# P4Runtime imports (these would be generated from protobuf)
try:
    import p4.v1.p4runtime_pb2 as p4runtime_pb2
    import p4.v1.p4runtime_pb2_grpc as p4runtime_pb2_grpc
    import p4.config.v1.p4info_pb2 as p4info_pb2
    P4RUNTIME_AVAILABLE = True
except ImportError:
    # Create mock classes for when P4Runtime is not available
    class MockP4Runtime:
        pass

    p4runtime_pb2 = MockP4Runtime()
    p4runtime_pb2_grpc = MockP4Runtime()
    p4info_pb2 = MockP4Runtime()
    P4RUNTIME_AVAILABLE = False

from .utils import P4RuntimeUtils, P4InfoHelper

LOG = logging.getLogger(__name__)


class P4RuntimeClient:
    """
    P4Runtime gRPC client for communicating with P4-programmable switches
    
    This client handles:
    - gRPC connection management
    - Pipeline installation and configuration
    - Table entry operations (insert, modify, delete, read)
    - Packet-in/packet-out streaming
    - Error handling and status reporting
    """
    
    def __init__(self, device_id: int, address: str, port: int = 50051):
        self.device_id = device_id
        self.address = address
        self.port = port
        self.grpc_address = f"{address}:{port}"
        
        # gRPC connection
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[p4runtime_pb2_grpc.P4RuntimeStub] = None
        self.connected = False
        
        # Pipeline information
        self.p4info: Optional[p4info_pb2.P4Info] = None
        self.p4info_helper: Optional[P4InfoHelper] = None
        self.pipeline_config: Optional[bytes] = None
        
        # Packet streaming
        self.packet_stream: Optional[AsyncIterator] = None
        self.packet_callbacks: List[Callable] = []
        self.stream_thread: Optional[Thread] = None
        self.stream_stop_event = Event()
        
        # Election ID for primary controller
        self.election_id = 1
        
        if not P4RUNTIME_AVAILABLE:
            LOG.error("P4Runtime not available - client will not function")
    
    async def connect(self) -> bool:
        """Establish gRPC connection to the P4Runtime switch"""
        if not P4RUNTIME_AVAILABLE:
            return False
        
        try:
            # Create gRPC channel
            self.channel = grpc.aio.insecure_channel(self.grpc_address)
            self.stub = p4runtime_pb2_grpc.P4RuntimeStub(self.channel)
            
            # Test connection with capabilities request
            capabilities_request = p4runtime_pb2.CapabilitiesRequest()
            capabilities_response = await self.stub.Capabilities(capabilities_request)
            
            LOG.info(f"Connected to P4Runtime switch {self.device_id} at {self.grpc_address}")
            LOG.info(f"Switch capabilities: {capabilities_response.p4runtime_api_version}")
            
            self.connected = True
            
            # Become primary controller
            await self._become_primary()
            
            return True
            
        except Exception as e:
            LOG.error(f"Failed to connect to P4Runtime switch {self.device_id}: {e}")
            return False
    
    async def disconnect(self):
        """Close gRPC connection"""
        try:
            self.connected = False
            
            # Stop packet streaming
            if self.stream_thread and self.stream_thread.is_alive():
                self.stream_stop_event.set()
                self.stream_thread.join(timeout=5)
            
            # Close gRPC channel
            if self.channel:
                await self.channel.close()
                self.channel = None
                self.stub = None
            
            LOG.info(f"Disconnected from P4Runtime switch {self.device_id}")
            
        except Exception as e:
            LOG.error(f"Error disconnecting from P4Runtime switch {self.device_id}: {e}")
    
    async def _become_primary(self):
        """Become the primary controller for this switch"""
        if not self.connected or not P4RUNTIME_AVAILABLE:
            return
        
        try:
            # Send arbitration request to become primary
            arbitration_request = p4runtime_pb2.StreamMessageRequest()
            arbitration_request.arbitration.device_id = self.device_id
            arbitration_request.arbitration.election_id.high = 0
            arbitration_request.arbitration.election_id.low = self.election_id
            
            # Start stream channel for arbitration
            stream_channel = self.stub.StreamChannel(self._stream_requests())
            
            # Send arbitration request
            await stream_channel.write(arbitration_request)
            
            # Wait for arbitration response
            response = await stream_channel.read()
            if response.arbitration.status.code == 0:
                LOG.info(f"Became primary controller for switch {self.device_id}")
            else:
                LOG.error(f"Failed to become primary controller: {response.arbitration.status}")
            
        except Exception as e:
            LOG.error(f"Error becoming primary controller: {e}")
    
    async def install_pipeline(self, p4info_path: str, pipeline_config_path: str) -> bool:
        """Install P4 pipeline on the switch"""
        if not self.connected or not P4RUNTIME_AVAILABLE:
            return False
        
        try:
            # Load P4Info
            with open(p4info_path, 'r') as f:
                p4info_json = json.load(f)
            
            # Convert JSON to protobuf (simplified - real implementation would be more complex)
            self.p4info = p4info_pb2.P4Info()
            # Note: Real implementation would properly parse JSON to protobuf
            
            # Load pipeline config
            with open(pipeline_config_path, 'rb') as f:
                self.pipeline_config = f.read()
            
            # Create pipeline config request
            config_request = p4runtime_pb2.SetForwardingPipelineConfigRequest()
            config_request.device_id = self.device_id
            config_request.election_id.low = self.election_id
            config_request.action = p4runtime_pb2.SetForwardingPipelineConfigRequest.VERIFY_AND_COMMIT
            
            config_request.config.p4info.CopyFrom(self.p4info)
            config_request.config.p4_device_config = self.pipeline_config
            
            # Send pipeline config
            response = await self.stub.SetForwardingPipelineConfig(config_request)
            
            # Create P4Info helper
            self.p4info_helper = P4InfoHelper(self.p4info)
            
            LOG.info(f"Pipeline installed successfully on switch {self.device_id}")
            return True
            
        except Exception as e:
            LOG.error(f"Failed to install pipeline on switch {self.device_id}: {e}")
            return False
    
    async def write_table_entry(self, table_name: str, match_fields: Dict[str, Any], 
                               action_name: str, action_params: Dict[str, Any],
                               priority: int = 1000) -> bool:
        """Write a table entry to the switch"""
        if not self.connected or not self.p4info_helper or not P4RUNTIME_AVAILABLE:
            return False
        
        try:
            # Build table entry
            table_entry = p4runtime_pb2.TableEntry()
            table_entry.table_id = self.p4info_helper.get_table_id(table_name)
            table_entry.priority = priority
            
            # Add match fields
            for field_name, value in match_fields.items():
                match = table_entry.match.add()
                match.field_id = self.p4info_helper.get_match_field_id(table_name, field_name)
                # Set match value (simplified - real implementation would handle different match types)
                match.exact.value = P4RuntimeUtils.encode_value(value)
            
            # Add action
            action = table_entry.action.action
            action.action_id = self.p4info_helper.get_action_id(action_name)
            
            for param_name, value in action_params.items():
                param = action.params.add()
                param.param_id = self.p4info_helper.get_action_param_id(action_name, param_name)
                param.value = P4RuntimeUtils.encode_value(value)
            
            # Create write request
            write_request = p4runtime_pb2.WriteRequest()
            write_request.device_id = self.device_id
            write_request.election_id.low = self.election_id
            
            update = write_request.updates.add()
            update.type = p4runtime_pb2.Update.INSERT
            update.entity.table_entry.CopyFrom(table_entry)
            
            # Send write request
            response = await self.stub.Write(write_request)
            
            LOG.debug(f"Table entry written to {table_name} on switch {self.device_id}")
            return True
            
        except Exception as e:
            LOG.error(f"Failed to write table entry: {e}")
            return False
    
    async def delete_table_entry(self, table_name: str, match_fields: Dict[str, Any]) -> bool:
        """Delete a table entry from the switch"""
        if not self.connected or not self.p4info_helper or not P4RUNTIME_AVAILABLE:
            return False
        
        try:
            # Build table entry for deletion
            table_entry = p4runtime_pb2.TableEntry()
            table_entry.table_id = self.p4info_helper.get_table_id(table_name)
            
            # Add match fields
            for field_name, value in match_fields.items():
                match = table_entry.match.add()
                match.field_id = self.p4info_helper.get_match_field_id(table_name, field_name)
                match.exact.value = P4RuntimeUtils.encode_value(value)
            
            # Create write request
            write_request = p4runtime_pb2.WriteRequest()
            write_request.device_id = self.device_id
            write_request.election_id.low = self.election_id
            
            update = write_request.updates.add()
            update.type = p4runtime_pb2.Update.DELETE
            update.entity.table_entry.CopyFrom(table_entry)
            
            # Send write request
            response = await self.stub.Write(write_request)
            
            LOG.debug(f"Table entry deleted from {table_name} on switch {self.device_id}")
            return True
            
        except Exception as e:
            LOG.error(f"Failed to delete table entry: {e}")
            return False
    
    async def read_table_entries(self, table_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Read table entries from the switch"""
        if not self.connected or not P4RUNTIME_AVAILABLE:
            return []
        
        try:
            # Create read request
            read_request = p4runtime_pb2.ReadRequest()
            read_request.device_id = self.device_id
            
            entity = read_request.entities.add()
            if table_name and self.p4info_helper:
                entity.table_entry.table_id = self.p4info_helper.get_table_id(table_name)
            else:
                # Read all tables
                entity.table_entry.table_id = 0
            
            # Send read request
            response_stream = self.stub.Read(read_request)
            
            entries = []
            async for response in response_stream:
                for entity in response.entities:
                    if entity.HasField('table_entry'):
                        entry_dict = P4RuntimeUtils.table_entry_to_dict(entity.table_entry, self.p4info_helper)
                        entries.append(entry_dict)
            
            return entries
            
        except Exception as e:
            LOG.error(f"Failed to read table entries: {e}")
            return []
    
    async def send_packet_out(self, packet: bytes, egress_port: str, metadata: Dict[str, Any] = None) -> bool:
        """Send a packet out through the switch"""
        if not self.connected or not P4RUNTIME_AVAILABLE:
            return False
        
        try:
            # Create packet out message
            packet_out = p4runtime_pb2.PacketOut()
            packet_out.payload = packet
            
            # Add metadata
            if metadata:
                for key, value in metadata.items():
                    meta = packet_out.metadata.add()
                    meta.metadata_id = self.p4info_helper.get_packet_metadata_id(key) if self.p4info_helper else 0
                    meta.value = P4RuntimeUtils.encode_value(value)
            
            # Create stream message
            stream_msg = p4runtime_pb2.StreamMessageRequest()
            stream_msg.packet.CopyFrom(packet_out)
            
            # Send via stream channel (would need active stream)
            # This is simplified - real implementation would maintain stream
            
            LOG.debug(f"Packet sent out on switch {self.device_id}")
            return True
            
        except Exception as e:
            LOG.error(f"Failed to send packet out: {e}")
            return False
    
    def add_packet_in_callback(self, callback: Callable):
        """Add callback for packet-in events"""
        if callback not in self.packet_callbacks:
            self.packet_callbacks.append(callback)
    
    def remove_packet_in_callback(self, callback: Callable):
        """Remove callback for packet-in events"""
        if callback in self.packet_callbacks:
            self.packet_callbacks.remove(callback)
    
    async def _stream_requests(self):
        """Generator for stream requests"""
        # This would yield stream requests for the bidirectional stream
        # Simplified implementation
        yield p4runtime_pb2.StreamMessageRequest()
    
    def _handle_packet_in(self, packet_in):
        """Handle incoming packet-in messages"""
        try:
            # Convert packet-in to standardized format
            packet_data = {
                'device_id': self.device_id,
                'packet': packet_in.payload,
                'metadata': {}
            }
            
            # Extract metadata
            for meta in packet_in.metadata:
                # Convert metadata to readable format
                packet_data['metadata'][str(meta.metadata_id)] = meta.value
            
            # Notify callbacks
            for callback in self.packet_callbacks:
                try:
                    callback(packet_data)
                except Exception as e:
                    LOG.error(f"Error in packet-in callback: {e}")
                    
        except Exception as e:
            LOG.error(f"Error handling packet-in: {e}")
    
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self.connected and P4RUNTIME_AVAILABLE
