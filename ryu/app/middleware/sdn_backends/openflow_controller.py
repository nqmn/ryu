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
OpenFlow Controller Backend

This module provides the RyuController class that wraps existing OpenFlow
functionality into the unified SDN backend interface, maintaining full
backward compatibility with existing middleware functionality.
"""

import logging
import asyncio
import time
from typing import Dict, Any, Optional, List, Callable

from ryu.controller import dpset
from ryu.ofproto import ofproto_v1_3
from ryu.lib import ofctl_v1_3
from ryu.lib import dpid as dpid_lib

from .base import SDNControllerBase, SwitchType, FlowData, PacketData, SwitchInfo
from ..utils import ResponseFormatter, NetworkUtils

LOG = logging.getLogger(__name__)


class RyuController(SDNControllerBase):
    """
    OpenFlow controller backend using Ryu
    
    This class wraps the existing Ryu OpenFlow functionality into the unified
    SDN backend interface, providing seamless backward compatibility while
    enabling integration with other SDN protocols.
    """
    
    def __init__(self, config: Dict[str, Any], dpset_instance: Optional[dpset.DPSet] = None):
        super().__init__(config)
        self.dpset = dpset_instance
        self.switch_type = SwitchType.OPENFLOW

        # Enhanced event handling
        self.event_stream = None  # Will be set by controller manager
        
    async def initialize(self) -> bool:
        """Initialize the OpenFlow controller"""
        try:
            # OpenFlow controller is already initialized via Ryu app
            self.connected = True
            self.reset_error_count()

            # Update switch information
            await self._update_switch_info()

            LOG.info(f"OpenFlow controller {self.controller_id} initialized")
            return True
        except Exception as e:
            LOG.error(f"Failed to initialize OpenFlow controller {self.controller_id}: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the OpenFlow controller"""
        try:
            self.connected = False
            LOG.info("OpenFlow controller backend shutdown")
        except Exception as e:
            LOG.error(f"Failed to shutdown OpenFlow controller: {e}")
    
    def get_switch_type(self) -> SwitchType:
        """Get the switch type supported by this controller"""
        return SwitchType.OPENFLOW
    
    async def install_flow(self, flow_data: FlowData) -> Dict[str, Any]:
        """Install a flow rule on the specified OpenFlow switch"""
        try:
            # Convert switch_id to DPID
            dpid = self._parse_dpid(flow_data.switch_id)
            
            # Get datapath
            if dpid not in self.dpset.dps:
                return ResponseFormatter.error(
                    f"Switch {flow_data.switch_id} not connected",
                    "SWITCH_NOT_CONNECTED"
                )
            
            datapath = self.dpset.dps[dpid]
            
            # Convert FlowData to OpenFlow flow specification
            flow_spec = self._convert_to_openflow_spec(flow_data)
            
            # Install flow using ofctl
            result = ofctl_v1_3.mod_flow_entry(datapath, flow_spec, ofproto_v1_3.OFPFC_ADD)

            # Update activity tracking
            self.increment_flow_count()

            # Publish event if event stream is available
            if self.event_stream:
                asyncio.create_task(self.event_stream.publish_event(
                    'flow_installed',
                    self.controller_id,
                    'openflow',
                    {
                        'switch_id': flow_data.switch_id,
                        'table_id': flow_data.table_id,
                        'priority': flow_data.priority,
                        'match_fields': flow_data.match_fields,
                        'actions': flow_data.actions
                    }
                ))

            return ResponseFormatter.success({
                'dpid': NetworkUtils.format_dpid(dpid),
                'action': 'installed',
                'flow_spec': flow_spec
            }, "Flow rule installed successfully")
            
        except Exception as e:
            LOG.error(f"Failed to install OpenFlow flow: {e}")
            return ResponseFormatter.error(str(e), "OPENFLOW_INSTALL_ERROR")
    
    async def delete_flow(self, flow_data: FlowData) -> Dict[str, Any]:
        """Delete a flow rule from the specified OpenFlow switch"""
        try:
            # Convert switch_id to DPID
            dpid = self._parse_dpid(flow_data.switch_id)
            
            # Get datapath
            if dpid not in self.dpset.dps:
                return ResponseFormatter.error(
                    f"Switch {flow_data.switch_id} not connected",
                    "SWITCH_NOT_CONNECTED"
                )
            
            datapath = self.dpset.dps[dpid]
            
            # Convert FlowData to OpenFlow flow specification
            flow_spec = self._convert_to_openflow_spec(flow_data)
            
            # Delete flow using ofctl
            result = ofctl_v1_3.mod_flow_entry(datapath, flow_spec, ofproto_v1_3.OFPFC_DELETE)
            
            return ResponseFormatter.success({
                'dpid': NetworkUtils.format_dpid(dpid),
                'action': 'deleted',
                'flow_spec': flow_spec
            }, "Flow rule deleted successfully")
            
        except Exception as e:
            LOG.error(f"Failed to delete OpenFlow flow: {e}")
            return ResponseFormatter.error(str(e), "OPENFLOW_DELETE_ERROR")
    
    async def modify_flow(self, flow_data: FlowData) -> Dict[str, Any]:
        """Modify an existing flow rule"""
        try:
            # Convert switch_id to DPID
            dpid = self._parse_dpid(flow_data.switch_id)
            
            # Get datapath
            if dpid not in self.dpset.dps:
                return ResponseFormatter.error(
                    f"Switch {flow_data.switch_id} not connected",
                    "SWITCH_NOT_CONNECTED"
                )
            
            datapath = self.dpset.dps[dpid]
            
            # Convert FlowData to OpenFlow flow specification
            flow_spec = self._convert_to_openflow_spec(flow_data)
            
            # Modify flow using ofctl
            result = ofctl_v1_3.mod_flow_entry(datapath, flow_spec, ofproto_v1_3.OFPFC_MODIFY)
            
            return ResponseFormatter.success({
                'dpid': NetworkUtils.format_dpid(dpid),
                'action': 'modified',
                'flow_spec': flow_spec
            }, "Flow rule modified successfully")
            
        except Exception as e:
            LOG.error(f"Failed to modify OpenFlow flow: {e}")
            return ResponseFormatter.error(str(e), "OPENFLOW_MODIFY_ERROR")
    
    async def get_flow_stats(self, switch_id: str, table_id: Optional[int] = None) -> Dict[str, Any]:
        """Get flow statistics for the specified OpenFlow switch"""
        try:
            # Convert switch_id to DPID
            dpid = self._parse_dpid(switch_id)
            
            # Get datapath
            if dpid not in self.dpset.dps:
                return ResponseFormatter.error(
                    f"Switch {switch_id} not connected",
                    "SWITCH_NOT_CONNECTED"
                )
            
            datapath = self.dpset.dps[dpid]
            
            # Build flow stats request
            match = {}
            if table_id is not None:
                match['table_id'] = table_id
            
            # Get flow stats using ofctl
            flows = ofctl_v1_3.get_flow_stats(datapath, match)
            
            return ResponseFormatter.success({
                'dpid': NetworkUtils.format_dpid(dpid),
                'flows': flows,
                'flow_count': len(flows)
            })
            
        except Exception as e:
            LOG.error(f"Failed to get OpenFlow flow stats: {e}")
            return ResponseFormatter.error(str(e), "OPENFLOW_STATS_ERROR")
    
    async def get_port_stats(self, switch_id: str, port_id: Optional[str] = None) -> Dict[str, Any]:
        """Get port statistics for the specified OpenFlow switch"""
        try:
            # Convert switch_id to DPID
            dpid = self._parse_dpid(switch_id)
            
            # Get datapath
            if dpid not in self.dpset.dps:
                return ResponseFormatter.error(
                    f"Switch {switch_id} not connected",
                    "SWITCH_NOT_CONNECTED"
                )
            
            datapath = self.dpset.dps[dpid]
            
            # Get port stats using ofctl
            ports = ofctl_v1_3.get_port_stats(datapath, port_id)
            
            return ResponseFormatter.success({
                'dpid': NetworkUtils.format_dpid(dpid),
                'ports': ports,
                'port_count': len(ports)
            })
            
        except Exception as e:
            LOG.error(f"Failed to get OpenFlow port stats: {e}")
            return ResponseFormatter.error(str(e), "OPENFLOW_PORT_STATS_ERROR")
    
    async def send_packet_out(self, packet_data: PacketData) -> Dict[str, Any]:
        """Send a packet out through the specified OpenFlow switch"""
        try:
            # Convert switch_id to DPID
            dpid = self._parse_dpid(packet_data.switch_id)
            
            # Get datapath
            if dpid not in self.dpset.dps:
                return ResponseFormatter.error(
                    f"Switch {packet_data.switch_id} not connected",
                    "SWITCH_NOT_CONNECTED"
                )
            
            datapath = self.dpset.dps[dpid]
            
            # Build packet-out message
            actions = []
            if packet_data.in_port is not None:
                actions.append(datapath.ofproto_parser.OFPActionOutput(packet_data.in_port))
            
            out = datapath.ofproto_parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=packet_data.buffer_id or datapath.ofproto.OFP_NO_BUFFER,
                in_port=packet_data.in_port or datapath.ofproto.OFPP_CONTROLLER,
                actions=actions,
                data=packet_data.packet
            )
            
            datapath.send_msg(out)
            
            return ResponseFormatter.success({
                'dpid': NetworkUtils.format_dpid(dpid),
                'action': 'packet_sent'
            }, "Packet sent successfully")
            
        except Exception as e:
            LOG.error(f"Failed to send OpenFlow packet: {e}")
            return ResponseFormatter.error(str(e), "OPENFLOW_PACKET_OUT_ERROR")
    
    def subscribe_packet_in(self, callback: Callable[[PacketData], None]) -> None:
        """Subscribe to packet-in events"""
        self.add_packet_in_callback(callback)
    
    def unsubscribe_packet_in(self, callback: Callable[[PacketData], None]) -> None:
        """Unsubscribe from packet-in events"""
        self.remove_packet_in_callback(callback)
    
    async def get_switch_info(self, switch_id: str) -> Optional[SwitchInfo]:
        """Get information about a specific OpenFlow switch"""
        try:
            dpid = self._parse_dpid(switch_id)
            
            if dpid in self.dpset.dps:
                datapath = self.dpset.dps[dpid]
                return SwitchInfo(
                    switch_id=switch_id,
                    switch_type=SwitchType.OPENFLOW,
                    address=datapath.address[0],
                    port=datapath.address[1],
                    connected=datapath.is_active,
                    capabilities={
                        'ofp_version': datapath.ofproto.OFP_VERSION,
                        'n_buffers': datapath.ofproto.OFP_NO_BUFFER,
                        'n_tables': 255  # Standard OpenFlow
                    }
                )
            return None
            
        except Exception as e:
            LOG.error(f"Failed to get OpenFlow switch info: {e}")
            return None
    
    async def list_switches(self) -> List[SwitchInfo]:
        """List all connected OpenFlow switches"""
        switches = []
        try:
            for dpid, datapath in self.dpset.dps.items():
                switch_info = await self.get_switch_info(NetworkUtils.format_dpid(dpid))
                if switch_info:
                    switches.append(switch_info)
        except Exception as e:
            LOG.error(f"Failed to list OpenFlow switches: {e}")
        
        return switches
    
    def _parse_dpid(self, switch_id: str) -> int:
        """Parse switch ID to DPID"""
        try:
            if isinstance(switch_id, int):
                return switch_id
            return dpid_lib.str_to_dpid(switch_id)
        except Exception as e:
            raise ValueError(f"Invalid DPID format: {switch_id}")
    
    def _convert_to_openflow_spec(self, flow_data: FlowData) -> Dict[str, Any]:
        """Convert FlowData to OpenFlow flow specification"""
        flow_spec = {
            'priority': flow_data.priority,
            'match': flow_data.match_fields.copy(),
            'actions': flow_data.actions.copy()
        }
        
        if flow_data.table_id is not None:
            flow_spec['table_id'] = flow_data.table_id
        
        if flow_data.cookie is not None:
            flow_spec['cookie'] = flow_data.cookie
        
        if flow_data.idle_timeout:
            flow_spec['idle_timeout'] = flow_data.idle_timeout
        
        if flow_data.hard_timeout:
            flow_spec['hard_timeout'] = flow_data.hard_timeout
        
        return flow_spec
    
    async def ping(self) -> bool:
        """Ping the OpenFlow controller to check if it's responsive"""
        try:
            if not self.dpset:
                return False

            # Check if we have any connected switches
            connected_switches = len(self.dpset.dps)

            # Try to get switch information for a quick health check
            if connected_switches > 0:
                # Pick the first available switch and try to get its features
                dpid = next(iter(self.dpset.dps.keys()))
                datapath = self.dpset.dps[dpid]

                # Simple check - if we can access the datapath, controller is responsive
                if datapath and datapath.is_active:
                    return True

            # If no switches connected, controller might still be healthy
            # Check if dpset is accessible
            return self.dpset is not None and self.connected

        except Exception as e:
            LOG.error(f"Ping failed for OpenFlow controller {self.controller_id}: {e}")
            return False

    def set_event_stream(self, event_stream):
        """Set the event stream for publishing events"""
        self.event_stream = event_stream

    async def _update_switch_info(self):
        """Update switch information from connected datapaths"""
        try:
            if not self.dpset:
                return

            self.switches.clear()

            for dpid, datapath in self.dpset.dps.items():
                switch_id = NetworkUtils.format_dpid(dpid)

                switch_info = SwitchInfo(
                    switch_id=switch_id,
                    switch_type=SwitchType.OPENFLOW,
                    address=datapath.address[0] if datapath.address else "unknown",
                    port=datapath.address[1] if datapath.address else 6653,
                    connected=datapath.is_active,
                    capabilities={
                        'n_buffers': datapath.ofproto.OFP_NO_BUFFER,
                        'n_tables': 255,  # Standard OpenFlow
                        'auxiliary_id': datapath.auxiliary_id,
                        'datapath_id': dpid
                    },
                    metadata={
                        'ofproto_version': datapath.ofproto.OFP_VERSION,
                        'last_seen': time.time()
                    }
                )

                self.switches[switch_id] = switch_info

            LOG.debug(f"Updated switch info for {len(self.switches)} switches")

        except Exception as e:
            LOG.error(f"Failed to update switch info: {e}")

    def handle_packet_in(self, ev):
        """Handle OpenFlow packet-in events"""
        try:
            msg = ev.msg
            datapath = msg.datapath

            packet_data = PacketData(
                switch_id=NetworkUtils.format_dpid(datapath.id),
                switch_type=SwitchType.OPENFLOW,
                packet=msg.data,
                in_port=msg.match['in_port'],
                buffer_id=msg.buffer_id,
                metadata={'reason': msg.reason}
            )

            self._notify_packet_in(packet_data)

            # Publish to event stream if available
            if self.event_stream:
                asyncio.create_task(self.event_stream.publish_event(
                    'packet_in',
                    self.controller_id,
                    'openflow',
                    {
                        'switch_id': packet_data.switch_id,
                        'packet_size': len(packet_data.packet),
                        'in_port': packet_data.in_port,
                        'buffer_id': packet_data.buffer_id,
                        'reason': packet_data.metadata.get('reason')
                    }
                ))

        except Exception as e:
            LOG.error(f"Error handling OpenFlow packet-in: {e}")

    def handle_switch_enter(self, ev):
        """Handle switch connection events"""
        try:
            datapath = ev.datapath
            switch_id = NetworkUtils.format_dpid(datapath.id)

            # Update switch info
            switch_info = SwitchInfo(
                switch_id=switch_id,
                switch_type=SwitchType.OPENFLOW,
                address=datapath.address[0] if datapath.address else "unknown",
                port=datapath.address[1] if datapath.address else 6653,
                connected=True,
                capabilities={
                    'n_buffers': datapath.ofproto.OFP_NO_BUFFER,
                    'n_tables': 255,
                    'auxiliary_id': datapath.auxiliary_id,
                    'datapath_id': datapath.id
                }
            )

            self.switches[switch_id] = switch_info
            self.update_activity()

            # Publish event
            if self.event_stream:
                asyncio.create_task(self.event_stream.publish_event(
                    'switch_enter',
                    self.controller_id,
                    'openflow',
                    {
                        'switch_id': switch_id,
                        'datapath_id': datapath.id,
                        'address': switch_info.address,
                        'port': switch_info.port
                    }
                ))

            LOG.info(f"Switch {switch_id} connected to OpenFlow controller {self.controller_id}")

        except Exception as e:
            LOG.error(f"Error handling switch enter: {e}")

    def handle_switch_leave(self, ev):
        """Handle switch disconnection events"""
        try:
            datapath = ev.datapath
            switch_id = NetworkUtils.format_dpid(datapath.id)

            # Update switch info
            if switch_id in self.switches:
                self.switches[switch_id].connected = False
                self.update_activity()

            # Publish event
            if self.event_stream:
                asyncio.create_task(self.event_stream.publish_event(
                    'switch_leave',
                    self.controller_id,
                    'openflow',
                    {
                        'switch_id': switch_id,
                        'datapath_id': datapath.id
                    }
                ))

            LOG.info(f"Switch {switch_id} disconnected from OpenFlow controller {self.controller_id}")

        except Exception as e:
            LOG.error(f"Error handling switch leave: {e}")
