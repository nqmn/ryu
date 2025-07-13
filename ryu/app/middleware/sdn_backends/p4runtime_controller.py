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
P4Runtime Controller Backend

This module provides the P4RuntimeController class that implements the unified
SDN backend interface for P4Runtime-enabled switches, providing seamless
integration with the middleware API.
"""

import logging
import asyncio
import time
from typing import Dict, Any, Optional, List, Callable

from .base import SDNControllerBase, SwitchType, FlowData, PacketData, SwitchInfo
from ..utils import ResponseFormatter
from ..p4runtime.client import P4RuntimeClient
from ..p4runtime.pipeline import PipelineManager

LOG = logging.getLogger(__name__)


class P4RuntimeController(SDNControllerBase):
    """
    P4Runtime controller backend
    
    This class implements the unified SDN backend interface for P4Runtime
    switches, providing table management, packet I/O, and statistics
    collection through gRPC communication.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.switch_type = SwitchType.P4RUNTIME
        self.clients: Dict[str, P4RuntimeClient] = {}
        self.pipeline_manager = PipelineManager(config.get('pipeline', {}))

        # Enhanced event handling
        self.event_stream = None  # Will be set by controller manager

        # Load switch configurations
        self._load_switch_configs()
    
    def _load_switch_configs(self):
        """Load P4Runtime switch configurations"""
        try:
            p4_config = self.config.get('p4runtime', {})
            switches = p4_config.get('switches', [])
            
            for switch_config in switches:
                device_id = switch_config.get('device_id')
                address = switch_config.get('address', 'localhost')
                port = switch_config.get('port', 50051)
                
                if ':' in address:
                    # Address includes port
                    addr_parts = address.split(':')
                    address = addr_parts[0]
                    port = int(addr_parts[1])
                
                switch_id = str(device_id)
                
                # Create P4Runtime client
                client = P4RuntimeClient(device_id, address, port)
                self.clients[switch_id] = client
                
                # Store switch info
                self.switches[switch_id] = SwitchInfo(
                    switch_id=switch_id,
                    switch_type=SwitchType.P4RUNTIME,
                    address=address,
                    port=port,
                    metadata=switch_config
                )
                
                LOG.info(f"Configured P4Runtime switch {switch_id} at {address}:{port}")
            
        except Exception as e:
            LOG.error(f"Failed to load P4Runtime switch configurations: {e}")
    
    async def initialize(self) -> bool:
        """Initialize the P4Runtime controller and connect to switches"""
        try:
            if not self.clients:
                LOG.warning("No P4Runtime switches configured")
                return True  # Not an error if no P4 switches
            
            # Connect to all switches
            connection_results = []
            for switch_id, client in self.clients.items():
                try:
                    # Add packet-in callback
                    client.add_packet_in_callback(self._handle_packet_in)
                    
                    # Connect to switch
                    connected = await client.connect()
                    connection_results.append(connected)
                    
                    if connected:
                        self.switches[switch_id].connected = True
                        
                        # Install pipeline if configured
                        switch_config = self.switches[switch_id].metadata
                        pipeline_path = switch_config.get('pipeline')
                        p4info_path = switch_config.get('p4info')
                        
                        if pipeline_path and p4info_path:
                            pipeline_installed = await client.install_pipeline(p4info_path, pipeline_path)
                            if pipeline_installed:
                                LOG.info(f"Pipeline installed on switch {switch_id}")
                                self.pipeline_manager.update_switch_status(switch_id, "default", True)
                            else:
                                LOG.error(f"Failed to install pipeline on switch {switch_id}")
                                self.pipeline_manager.update_switch_status(switch_id, "default", False, "Pipeline installation failed")
                        
                        LOG.info(f"P4Runtime switch {switch_id} connected successfully")
                    else:
                        LOG.error(f"Failed to connect to P4Runtime switch {switch_id}")
                        
                except Exception as e:
                    LOG.error(f"Failed to initialize P4Runtime switch {switch_id}: {e}")
                    connection_results.append(False)
            
            # Consider successful if at least one switch connected
            self.connected = any(connection_results)

            if self.connected:
                self.reset_error_count()
                LOG.info(f"P4Runtime controller {self.controller_id} initialized")
            else:
                LOG.warning(f"P4Runtime controller {self.controller_id} initialized but no switches connected")

            return True
            
        except Exception as e:
            LOG.error(f"Failed to initialize P4Runtime controller: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the P4Runtime controller and disconnect from switches"""
        try:
            # Disconnect from all switches
            for switch_id, client in self.clients.items():
                try:
                    await client.disconnect()
                    self.switches[switch_id].connected = False
                    LOG.info(f"Disconnected from P4Runtime switch {switch_id}")
                except Exception as e:
                    LOG.error(f"Error disconnecting from switch {switch_id}: {e}")
            
            self.connected = False
            LOG.info("P4Runtime controller backend shutdown")
            
        except Exception as e:
            LOG.error(f"Failed to shutdown P4Runtime controller: {e}")
    
    def get_switch_type(self) -> SwitchType:
        """Get the switch type supported by this controller"""
        return SwitchType.P4RUNTIME
    
    async def install_flow(self, flow_data: FlowData) -> Dict[str, Any]:
        """Install a table entry on the specified P4Runtime switch"""
        try:
            client = self.clients.get(flow_data.switch_id)
            if not client or not client.is_connected():
                return ResponseFormatter.error(
                    f"Switch {flow_data.switch_id} not connected",
                    "SWITCH_NOT_CONNECTED"
                )
            
            # Convert FlowData to P4Runtime table entry
            table_name = flow_data.table_name or "default_table"
            action_name = flow_data.action_name or "default_action"
            
            # Install table entry
            success = await client.write_table_entry(
                table_name=table_name,
                match_fields=flow_data.match_fields,
                action_name=action_name,
                action_params=flow_data.action_params,
                priority=flow_data.priority
            )
            
            if success:
                # Update activity tracking
                self.increment_flow_count()

                # Publish event
                await self._publish_flow_event('flow_installed', flow_data, {
                    'table_name': table_name,
                    'action_name': action_name
                })

                return ResponseFormatter.success({
                    'switch_id': flow_data.switch_id,
                    'action': 'installed',
                    'table_name': table_name,
                    'match_fields': flow_data.match_fields,
                    'action_name': action_name,
                    'action_params': flow_data.action_params
                }, "Table entry installed successfully")
            else:
                return ResponseFormatter.error(
                    "Failed to install table entry",
                    "P4RUNTIME_INSTALL_ERROR"
                )
            
        except Exception as e:
            LOG.error(f"Failed to install P4Runtime table entry: {e}")
            return ResponseFormatter.error(str(e), "P4RUNTIME_INSTALL_ERROR")
    
    async def delete_flow(self, flow_data: FlowData) -> Dict[str, Any]:
        """Delete a table entry from the specified P4Runtime switch"""
        try:
            client = self.clients.get(flow_data.switch_id)
            if not client or not client.is_connected():
                return ResponseFormatter.error(
                    f"Switch {flow_data.switch_id} not connected",
                    "SWITCH_NOT_CONNECTED"
                )
            
            # Convert FlowData to P4Runtime table entry
            table_name = flow_data.table_name or "default_table"
            
            # Delete table entry
            success = await client.delete_table_entry(
                table_name=table_name,
                match_fields=flow_data.match_fields
            )
            
            if success:
                return ResponseFormatter.success({
                    'switch_id': flow_data.switch_id,
                    'action': 'deleted',
                    'table_name': table_name,
                    'match_fields': flow_data.match_fields
                }, "Table entry deleted successfully")
            else:
                return ResponseFormatter.error(
                    "Failed to delete table entry",
                    "P4RUNTIME_DELETE_ERROR"
                )
            
        except Exception as e:
            LOG.error(f"Failed to delete P4Runtime table entry: {e}")
            return ResponseFormatter.error(str(e), "P4RUNTIME_DELETE_ERROR")
    
    async def modify_flow(self, flow_data: FlowData) -> Dict[str, Any]:
        """Modify an existing table entry (P4Runtime uses modify as insert/update)"""
        # P4Runtime doesn't have explicit modify - use install with modify semantics
        return await self.install_flow(flow_data)
    
    async def get_flow_stats(self, switch_id: str, table_id: Optional[int] = None) -> Dict[str, Any]:
        """Get table entries for the specified P4Runtime switch"""
        try:
            client = self.clients.get(switch_id)
            if not client or not client.is_connected():
                return ResponseFormatter.error(
                    f"Switch {switch_id} not connected",
                    "SWITCH_NOT_CONNECTED"
                )
            
            # Read table entries
            table_name = None
            if table_id is not None:
                # Convert table_id to table_name if needed
                table_name = f"table_{table_id}"
            
            entries = await client.read_table_entries(table_name)
            
            return ResponseFormatter.success({
                'switch_id': switch_id,
                'table_entries': entries,
                'entry_count': len(entries)
            })
            
        except Exception as e:
            LOG.error(f"Failed to get P4Runtime table entries: {e}")
            return ResponseFormatter.error(str(e), "P4RUNTIME_STATS_ERROR")
    
    async def get_port_stats(self, switch_id: str, port_id: Optional[str] = None) -> Dict[str, Any]:
        """Get port statistics for the specified P4Runtime switch"""
        try:
            # P4Runtime doesn't have built-in port stats - would need custom implementation
            # This is a placeholder that returns basic information
            
            client = self.clients.get(switch_id)
            if not client or not client.is_connected():
                return ResponseFormatter.error(
                    f"Switch {switch_id} not connected",
                    "SWITCH_NOT_CONNECTED"
                )
            
            # Return placeholder port stats
            port_stats = {
                'switch_id': switch_id,
                'ports': {},
                'note': 'P4Runtime port statistics require custom implementation'
            }
            
            return ResponseFormatter.success(port_stats)
            
        except Exception as e:
            LOG.error(f"Failed to get P4Runtime port stats: {e}")
            return ResponseFormatter.error(str(e), "P4RUNTIME_PORT_STATS_ERROR")
    
    async def send_packet_out(self, packet_data: PacketData) -> Dict[str, Any]:
        """Send a packet out through the specified P4Runtime switch"""
        try:
            client = self.clients.get(packet_data.switch_id)
            if not client or not client.is_connected():
                return ResponseFormatter.error(
                    f"Switch {packet_data.switch_id} not connected",
                    "SWITCH_NOT_CONNECTED"
                )
            
            # Send packet out
            success = await client.send_packet_out(
                packet=packet_data.packet,
                egress_port=packet_data.egress_port or "1",
                metadata=packet_data.packet_metadata
            )
            
            if success:
                return ResponseFormatter.success({
                    'switch_id': packet_data.switch_id,
                    'action': 'packet_sent'
                }, "Packet sent successfully")
            else:
                return ResponseFormatter.error(
                    "Failed to send packet",
                    "P4RUNTIME_PACKET_OUT_ERROR"
                )
            
        except Exception as e:
            LOG.error(f"Failed to send P4Runtime packet: {e}")
            return ResponseFormatter.error(str(e), "P4RUNTIME_PACKET_OUT_ERROR")
    
    def subscribe_packet_in(self, callback: Callable[[PacketData], None]) -> None:
        """Subscribe to packet-in events"""
        self.add_packet_in_callback(callback)
    
    def unsubscribe_packet_in(self, callback: Callable[[PacketData], None]) -> None:
        """Unsubscribe from packet-in events"""
        self.remove_packet_in_callback(callback)
    
    async def get_switch_info(self, switch_id: str) -> Optional[SwitchInfo]:
        """Get information about a specific P4Runtime switch"""
        return self.switches.get(switch_id)
    
    async def list_switches(self) -> List[SwitchInfo]:
        """List all P4Runtime switches"""
        return list(self.switches.values())
    
    def _handle_packet_in(self, packet_data: Dict[str, Any]):
        """Handle packet-in events from P4Runtime clients"""
        try:
            # Convert P4Runtime packet-in to unified PacketData format
            unified_packet = PacketData(
                switch_id=str(packet_data['device_id']),
                switch_type=SwitchType.P4RUNTIME,
                packet=packet_data['packet'],
                packet_metadata=packet_data.get('metadata', {})
            )
            
            # Notify callbacks
            self._notify_packet_in(unified_packet)
            
        except Exception as e:
            LOG.error(f"Error handling P4Runtime packet-in: {e}")
    
    async def install_pipeline(self, switch_id: str, pipeline_name: str, 
                              p4info_path: str, config_path: str) -> Dict[str, Any]:
        """Install P4 pipeline on a specific switch"""
        try:
            client = self.clients.get(switch_id)
            if not client or not client.is_connected():
                return ResponseFormatter.error(
                    f"Switch {switch_id} not connected",
                    "SWITCH_NOT_CONNECTED"
                )
            
            # Install pipeline
            success = await client.install_pipeline(p4info_path, config_path)
            
            # Update pipeline manager status
            self.pipeline_manager.update_switch_status(
                switch_id, pipeline_name, success,
                "" if success else "Pipeline installation failed"
            )
            
            if success:
                return ResponseFormatter.success({
                    'switch_id': switch_id,
                    'pipeline_name': pipeline_name,
                    'action': 'installed'
                }, "Pipeline installed successfully")
            else:
                return ResponseFormatter.error(
                    "Failed to install pipeline",
                    "P4RUNTIME_PIPELINE_ERROR"
                )
            
        except Exception as e:
            LOG.error(f"Failed to install P4 pipeline: {e}")
            return ResponseFormatter.error(str(e), "P4RUNTIME_PIPELINE_ERROR")
    
    async def ping(self) -> bool:
        """Ping the P4Runtime controller to check if it's responsive"""
        try:
            if not self.clients:
                return False

            # Check if any client is connected and responsive
            for switch_id, client in self.clients.items():
                try:
                    # Try to get switch info as a health check
                    if client.is_connected():
                        # Simple ping - if client is connected, controller is responsive
                        return True
                except Exception as e:
                    LOG.debug(f"Ping failed for switch {switch_id}: {e}")
                    continue

            return False

        except Exception as e:
            LOG.error(f"Ping failed for P4Runtime controller {self.controller_id}: {e}")
            return False

    def set_event_stream(self, event_stream):
        """Set the event stream for publishing events"""
        self.event_stream = event_stream

    def get_pipeline_manager(self) -> PipelineManager:
        """Get the pipeline manager instance"""
        return self.pipeline_manager

    def _handle_packet_in(self, switch_id: str, packet_data: bytes, metadata: Dict[str, Any]):
        """Handle P4Runtime packet-in events"""
        try:
            packet_data_obj = PacketData(
                switch_id=switch_id,
                switch_type=SwitchType.P4RUNTIME,
                packet=packet_data,
                metadata=metadata
            )

            self._notify_packet_in(packet_data_obj)

            # Publish to event stream if available
            if self.event_stream:
                asyncio.create_task(self.event_stream.publish_event(
                    'packet_in',
                    self.controller_id,
                    'p4runtime',
                    {
                        'switch_id': switch_id,
                        'packet_size': len(packet_data),
                        'metadata': metadata
                    }
                ))

        except Exception as e:
            LOG.error(f"Error handling P4Runtime packet-in: {e}")

    async def _publish_flow_event(self, event_type: str, flow_data: FlowData, additional_data: Dict[str, Any] = None):
        """Publish flow-related events"""
        if not self.event_stream:
            return

        event_data = {
            'switch_id': flow_data.switch_id,
            'table_name': flow_data.table_name,
            'action_name': flow_data.action_name,
            'match_fields': flow_data.match_fields,
            'action_params': flow_data.action_params,
            'priority': flow_data.priority
        }

        if additional_data:
            event_data.update(additional_data)

        await self.event_stream.publish_event(
            event_type,
            self.controller_id,
            'p4runtime',
            event_data
        )
