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
Monitoring Service Module

This module provides comprehensive monitoring and telemetry capabilities
including flow statistics, port statistics, packet monitoring, and
flow management.
"""

import time
import logging
import threading
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
from threading import Lock

from ryu.controller import dpset
from ryu.controller import ofp_event
from ryu.ofproto import ofproto_v1_3
from ryu.lib import ofctl_v1_3

from .utils import MiddlewareConfig, ResponseFormatter, NetworkUtils

LOG = logging.getLogger(__name__)


class MonitoringService:
    """
    Monitoring and telemetry service
    
    Provides functionality for:
    - Flow statistics collection and management
    - Port statistics monitoring
    - Packet-in event tracking
    - Flow rule installation and deletion
    - Topology metrics
    """
    
    def __init__(self, config: MiddlewareConfig, dpset_instance: dpset.DPSet, switch_manager=None):
        self.config = config
        self.dpset = dpset_instance
        self.switch_manager = switch_manager
        
        # Statistics storage
        self.flow_stats = defaultdict(dict)
        self.port_stats = defaultdict(dict)
        self.packet_stats = defaultdict(lambda: defaultdict(int))
        self.topology_stats = {}
        
        # Event tracking
        self.packet_events = deque(maxlen=1000)  # Keep last 1000 packet events
        self.flow_events = deque(maxlen=1000)    # Keep last 1000 flow events
        
        # Thread safety
        self.stats_lock = Lock()
        
        # Monitoring thread
        self.monitoring_enabled = config.monitoring_enabled
        self.monitoring_thread = None
        
        if self.monitoring_enabled:
            self._start_monitoring_thread()
        
        LOG.info("Monitoring service initialized")
    
    def _start_monitoring_thread(self):
        """Start background monitoring thread"""
        def monitoring_loop():
            while self.monitoring_enabled:
                try:
                    self._collect_statistics()
                    time.sleep(self.config.monitoring_interval)
                except Exception as e:
                    LOG.error(f"Error in monitoring loop: {e}")
                    time.sleep(5)  # Wait before retrying
        
        self.monitoring_thread = threading.Thread(target=monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        LOG.info("Monitoring thread started")
    
    def _collect_statistics(self):
        """Collect statistics from all connected switches"""
        try:
            with self.stats_lock:
                current_time = time.time()
                
                # Get all connected datapaths
                for dpid, datapath in self.dpset.dps.items():
                    if datapath.is_active:
                        # Request flow stats
                        self._request_flow_stats(datapath)
                        
                        # Request port stats
                        self._request_port_stats(datapath)
                
                # Update topology stats
                self.topology_stats = {
                    'last_update': current_time,
                    'connected_switches': len(self.dpset.dps),
                    'active_switches': sum(1 for dp in self.dpset.dps.values() if dp.is_active)
                }
                
        except Exception as e:
            LOG.error(f"Failed to collect statistics: {e}")
    
    def _request_flow_stats(self, datapath):
        """Request flow statistics from a datapath"""
        try:
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            
            req = parser.OFPFlowStatsRequest(datapath)
            datapath.send_msg(req)
            
        except Exception as e:
            LOG.error(f"Failed to request flow stats from {datapath.id}: {e}")
    
    def _request_port_stats(self, datapath):
        """Request port statistics from a datapath"""
        try:
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            
            req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
            datapath.send_msg(req)
            
        except Exception as e:
            LOG.error(f"Failed to request port stats from {datapath.id}: {e}")
    
    def on_switch_connected(self, datapath):
        """Handle switch connection event"""
        try:
            dpid = datapath.id
            LOG.info(f"Switch {dpid} connected")
            
            with self.stats_lock:
                # Initialize stats for this switch
                self.flow_stats[dpid] = {}
                self.port_stats[dpid] = {}
                self.packet_stats[dpid] = defaultdict(int)
            
        except Exception as e:
            LOG.error(f"Error handling switch connection: {e}")
    
    def on_packet_in(self, ev):
        """Handle packet-in events"""
        try:
            msg = ev.msg
            datapath = msg.datapath
            dpid = datapath.id
            
            with self.stats_lock:
                # Update packet statistics
                self.packet_stats[dpid]['total_packets'] += 1
                self.packet_stats[dpid]['last_packet_time'] = time.time()
                
                # Store packet event (limited history)
                packet_event = {
                    'dpid': dpid,
                    'timestamp': time.time(),
                    'buffer_id': msg.buffer_id,
                    'total_len': msg.total_len,
                    'reason': msg.reason,
                    'table_id': msg.table_id,
                    'cookie': msg.cookie
                }
                
                self.packet_events.append(packet_event)
            
        except Exception as e:
            LOG.error(f"Error handling packet-in event: {e}")
    
    def get_flow_stats(self, dpid: Optional[int] = None) -> Dict[str, Any]:
        """Get flow statistics"""
        try:
            with self.stats_lock:
                if dpid:
                    # Get stats for specific switch
                    if dpid in self.flow_stats:
                        return ResponseFormatter.success({
                            'dpid': NetworkUtils.format_dpid(dpid),
                            'flows': self.flow_stats[dpid],
                            'timestamp': time.time()
                        })
                    else:
                        return ResponseFormatter.error(
                            f"No flow stats for switch {dpid}",
                            "SWITCH_NOT_FOUND"
                        )
                else:
                    # Get stats for all switches
                    all_stats = {}
                    for switch_dpid, flows in self.flow_stats.items():
                        all_stats[NetworkUtils.format_dpid(switch_dpid)] = flows
                    
                    return ResponseFormatter.success({
                        'switches': all_stats,
                        'timestamp': time.time()
                    })
                    
        except Exception as e:
            LOG.error(f"Failed to get flow stats: {e}")
            return ResponseFormatter.error(str(e), "FLOW_STATS_ERROR")
    
    def get_port_stats(self, dpid: Optional[int] = None) -> Dict[str, Any]:
        """Get port statistics"""
        try:
            with self.stats_lock:
                if dpid:
                    # Get stats for specific switch
                    if dpid in self.port_stats:
                        return ResponseFormatter.success({
                            'dpid': NetworkUtils.format_dpid(dpid),
                            'ports': self.port_stats[dpid],
                            'timestamp': time.time()
                        })
                    else:
                        return ResponseFormatter.error(
                            f"No port stats for switch {dpid}",
                            "SWITCH_NOT_FOUND"
                        )
                else:
                    # Get stats for all switches
                    all_stats = {}
                    for switch_dpid, ports in self.port_stats.items():
                        all_stats[NetworkUtils.format_dpid(switch_dpid)] = ports
                    
                    return ResponseFormatter.success({
                        'switches': all_stats,
                        'timestamp': time.time()
                    })
                    
        except Exception as e:
            LOG.error(f"Failed to get port stats: {e}")
            return ResponseFormatter.error(str(e), "PORT_STATS_ERROR")
    
    def get_packet_stats(self) -> Dict[str, Any]:
        """Get packet-in statistics"""
        try:
            with self.stats_lock:
                stats = {}
                for dpid, packet_data in self.packet_stats.items():
                    stats[NetworkUtils.format_dpid(dpid)] = dict(packet_data)
                
                return ResponseFormatter.success({
                    'switches': stats,
                    'recent_events': list(self.packet_events)[-10:],  # Last 10 events
                    'total_events': len(self.packet_events),
                    'timestamp': time.time()
                })
                
        except Exception as e:
            LOG.error(f"Failed to get packet stats: {e}")
            return ResponseFormatter.error(str(e), "PACKET_STATS_ERROR")
    
    def get_topology_stats(self) -> Dict[str, Any]:
        """Get topology metrics"""
        try:
            with self.stats_lock:
                return ResponseFormatter.success(self.topology_stats)
                
        except Exception as e:
            LOG.error(f"Failed to get topology stats: {e}")
            return ResponseFormatter.error(str(e), "TOPOLOGY_STATS_ERROR")
    
    def get_flow_table(self, dpid: int) -> Dict[str, Any]:
        """Get flow table for a specific switch"""
        try:
            # Get datapath
            if dpid not in self.dpset.dps:
                return ResponseFormatter.error(
                    f"Switch {dpid} not connected",
                    "SWITCH_NOT_CONNECTED"
                )
            
            datapath = self.dpset.dps[dpid]
            
            # Use ofctl to get flow table
            flows = ofctl_v1_3.get_flow_stats(datapath, {})
            
            return ResponseFormatter.success({
                'dpid': NetworkUtils.format_dpid(dpid),
                'flows': flows,
                'flow_count': len(flows),
                'timestamp': time.time()
            })
            
        except Exception as e:
            LOG.error(f"Failed to get flow table: {e}")
            return ResponseFormatter.error(str(e), "FLOW_TABLE_ERROR")
    
    def install_flow(self, flow_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Install flow rule"""
        try:
            dpid = flow_spec['dpid']
            
            # Get datapath
            if dpid not in self.dpset.dps:
                return ResponseFormatter.error(
                    f"Switch {dpid} not connected",
                    "SWITCH_NOT_CONNECTED"
                )
            
            datapath = self.dpset.dps[dpid]
            
            # Use ofctl to install flow
            result = ofctl_v1_3.mod_flow_entry(datapath, flow_spec, ofproto_v1_3.OFPFC_ADD)
            
            # Log flow installation
            with self.stats_lock:
                flow_event = {
                    'dpid': dpid,
                    'action': 'install',
                    'flow_spec': flow_spec,
                    'timestamp': time.time()
                }
                self.flow_events.append(flow_event)
            
            return ResponseFormatter.success({
                'dpid': NetworkUtils.format_dpid(dpid),
                'action': 'installed',
                'flow_spec': flow_spec
            }, "Flow rule installed successfully")
            
        except Exception as e:
            LOG.error(f"Failed to install flow: {e}")
            return ResponseFormatter.error(str(e), "FLOW_INSTALL_ERROR")
    
    def delete_flow(self, flow_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Delete flow rule"""
        try:
            dpid = flow_spec['dpid']
            
            # Get datapath
            if dpid not in self.dpset.dps:
                return ResponseFormatter.error(
                    f"Switch {dpid} not connected",
                    "SWITCH_NOT_CONNECTED"
                )
            
            datapath = self.dpset.dps[dpid]
            
            # Use ofctl to delete flow
            result = ofctl_v1_3.mod_flow_entry(datapath, flow_spec, ofproto_v1_3.OFPFC_DELETE)
            
            # Log flow deletion
            with self.stats_lock:
                flow_event = {
                    'dpid': dpid,
                    'action': 'delete',
                    'flow_spec': flow_spec,
                    'timestamp': time.time()
                }
                self.flow_events.append(flow_event)
            
            return ResponseFormatter.success({
                'dpid': NetworkUtils.format_dpid(dpid),
                'action': 'deleted',
                'flow_spec': flow_spec
            }, "Flow rule deleted successfully")
            
        except Exception as e:
            LOG.error(f"Failed to delete flow: {e}")
            return ResponseFormatter.error(str(e), "FLOW_DELETE_ERROR")
    
    def get_stats_info(self, dpid: Optional[int] = None) -> Dict[str, Any]:
        """Get comprehensive statistics information"""
        try:
            with self.stats_lock:
                info = {
                    'monitoring_enabled': self.monitoring_enabled,
                    'monitoring_interval': self.config.monitoring_interval,
                    'stats_retention_time': self.config.stats_retention_time,
                    'topology_stats': self.topology_stats,
                    'timestamp': time.time()
                }
                
                if dpid:
                    # Stats for specific switch
                    if dpid in self.flow_stats:
                        info['switch'] = {
                            'dpid': NetworkUtils.format_dpid(dpid),
                            'flow_stats': self.flow_stats[dpid],
                            'port_stats': self.port_stats.get(dpid, {}),
                            'packet_stats': dict(self.packet_stats.get(dpid, {}))
                        }
                    else:
                        return ResponseFormatter.error(
                            f"No stats for switch {dpid}",
                            "SWITCH_NOT_FOUND"
                        )
                else:
                    # Stats for all switches
                    switches = {}
                    for switch_dpid in self.flow_stats.keys():
                        switches[NetworkUtils.format_dpid(switch_dpid)] = {
                            'flow_count': len(self.flow_stats[switch_dpid]),
                            'port_count': len(self.port_stats.get(switch_dpid, {})),
                            'packet_count': self.packet_stats.get(switch_dpid, {}).get('total_packets', 0)
                        }
                    info['switches'] = switches
                
                return ResponseFormatter.success(info)
                
        except Exception as e:
            LOG.error(f"Failed to get stats info: {e}")
            return ResponseFormatter.error(str(e), "STATS_INFO_ERROR")
    
    def get_current_timestamp(self) -> float:
        """Get current timestamp"""
        return time.time()
    
    def is_healthy(self) -> str:
        """Check if monitoring service is healthy"""
        try:
            if not self.monitoring_enabled:
                return "disabled"
            
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                return "healthy"
            else:
                return "unhealthy"
                
        except Exception:
            return "error"
    
    def cleanup(self):
        """Cleanup monitoring service"""
        try:
            self.monitoring_enabled = False
            
            if self.monitoring_thread:
                self.monitoring_thread.join(timeout=5)
            
            with self.stats_lock:
                self.flow_stats.clear()
                self.port_stats.clear()
                self.packet_stats.clear()
                self.packet_events.clear()
                self.flow_events.clear()
            
            LOG.info("Monitoring service cleanup completed")
            
        except Exception as e:
            LOG.error(f"Error during monitoring cleanup: {e}")

    def on_unified_packet_in(self, packet_data):
        """Handle unified packet-in events from any backend"""
        try:
            with self.stats_lock:
                switch_id = packet_data.switch_id

                # Update packet statistics
                self.packet_stats[switch_id]['total_packets'] += 1
                self.packet_stats[switch_id]['total_bytes'] += len(packet_data.packet)

                # Create packet event
                packet_event = {
                    'switch_id': switch_id,
                    'switch_type': packet_data.switch_type.value,
                    'packet_size': len(packet_data.packet),
                    'timestamp': time.time(),
                    'metadata': packet_data.metadata
                }

                self.packet_events.append(packet_event)

                LOG.debug(f"Processed unified packet-in from {switch_id} ({packet_data.switch_type.value})")

        except Exception as e:
            LOG.error(f"Error processing unified packet-in: {e}")
