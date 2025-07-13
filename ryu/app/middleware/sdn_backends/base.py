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
SDN Backend Base Classes

This module defines the abstract base classes and data models for SDN backend
controllers. It provides a unified interface for different SDN protocols
(OpenFlow, P4Runtime) while maintaining protocol-specific capabilities.
"""

import logging
import time
import asyncio
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime

LOG = logging.getLogger(__name__)


class SwitchType(Enum):
    """Enumeration of supported switch types"""
    OPENFLOW = "openflow"
    P4RUNTIME = "p4runtime"
    UNKNOWN = "unknown"


@dataclass
class FlowData:
    """Unified flow data representation"""
    switch_id: str
    switch_type: SwitchType
    priority: int = 1000
    table_id: Optional[int] = None
    match_fields: Dict[str, Any] = field(default_factory=dict)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # OpenFlow specific fields
    cookie: Optional[int] = None
    idle_timeout: int = 0
    hard_timeout: int = 0
    
    # P4Runtime specific fields
    table_name: Optional[str] = None
    action_name: Optional[str] = None
    action_params: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class PacketData:
    """Unified packet data representation"""
    switch_id: str
    switch_type: SwitchType
    packet: bytes
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # OpenFlow specific fields
    in_port: Optional[int] = None
    buffer_id: Optional[int] = None
    
    # P4Runtime specific fields
    ingress_port: Optional[str] = None
    egress_port: Optional[str] = None
    packet_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SwitchInfo:
    """Switch information and capabilities"""
    switch_id: str
    switch_type: SwitchType
    address: str
    port: int
    connected: bool = False
    capabilities: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ControllerHealth:
    """Controller health status information"""
    is_healthy: bool = True
    last_check: Optional[datetime] = None
    response_time_ms: float = 0.0
    error_count: int = 0
    last_error: Optional[str] = None
    uptime_seconds: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


class SDNControllerBase(ABC):
    """
    Abstract base class for SDN backend controllers
    
    This class defines the unified interface that all SDN backend controllers
    must implement. It provides protocol-agnostic methods for flow management,
    statistics collection, and packet handling.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.switches: Dict[str, SwitchInfo] = {}
        self.packet_in_callbacks: List[Callable[[PacketData], None]] = []
        self.connected = False

        # Health monitoring
        self.health = ControllerHealth()
        self.start_time = time.time()
        self.last_activity = datetime.utcnow()

        # Controller metadata
        self.controller_id = config.get('controller_id', f"{self.get_switch_type().value}_{id(self)}")
        self.name = config.get('name', self.controller_id)
        self.description = config.get('description', f"{self.get_switch_type().value} controller")

        # Event tracking
        self.event_count = 0
        self.packet_count = 0
        self.flow_count = 0
        
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the controller and establish connections"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the controller and cleanup resources"""
        pass
    
    @abstractmethod
    async def install_flow(self, flow_data: FlowData) -> Dict[str, Any]:
        """Install a flow rule on the specified switch"""
        pass
    
    @abstractmethod
    async def delete_flow(self, flow_data: FlowData) -> Dict[str, Any]:
        """Delete a flow rule from the specified switch"""
        pass
    
    @abstractmethod
    async def modify_flow(self, flow_data: FlowData) -> Dict[str, Any]:
        """Modify an existing flow rule"""
        pass
    
    @abstractmethod
    async def get_flow_stats(self, switch_id: str, table_id: Optional[int] = None) -> Dict[str, Any]:
        """Get flow statistics for the specified switch"""
        pass
    
    @abstractmethod
    async def get_port_stats(self, switch_id: str, port_id: Optional[str] = None) -> Dict[str, Any]:
        """Get port statistics for the specified switch"""
        pass
    
    @abstractmethod
    async def send_packet_out(self, packet_data: PacketData) -> Dict[str, Any]:
        """Send a packet out through the specified switch"""
        pass
    
    @abstractmethod
    def subscribe_packet_in(self, callback: Callable[[PacketData], None]) -> None:
        """Subscribe to packet-in events"""
        pass
    
    @abstractmethod
    def unsubscribe_packet_in(self, callback: Callable[[PacketData], None]) -> None:
        """Unsubscribe from packet-in events"""
        pass
    
    @abstractmethod
    async def get_switch_info(self, switch_id: str) -> Optional[SwitchInfo]:
        """Get information about a specific switch"""
        pass
    
    @abstractmethod
    async def list_switches(self) -> List[SwitchInfo]:
        """List all connected switches"""
        pass

    @abstractmethod
    async def ping(self) -> bool:
        """Ping the controller to check if it's responsive"""
        pass

    def get_switch_type(self) -> SwitchType:
        """Get the switch type supported by this controller"""
        return SwitchType.UNKNOWN

    def is_connected(self) -> bool:
        """Check if the controller is connected"""
        return self.connected
    
    def add_packet_in_callback(self, callback: Callable[[PacketData], None]) -> None:
        """Add a packet-in callback"""
        if callback not in self.packet_in_callbacks:
            self.packet_in_callbacks.append(callback)
    
    def remove_packet_in_callback(self, callback: Callable[[PacketData], None]) -> None:
        """Remove a packet-in callback"""
        if callback in self.packet_in_callbacks:
            self.packet_in_callbacks.remove(callback)
    
    def _notify_packet_in(self, packet_data: PacketData) -> None:
        """Notify all registered callbacks of a packet-in event"""
        self.packet_count += 1
        self.last_activity = datetime.utcnow()

        for callback in self.packet_in_callbacks:
            try:
                callback(packet_data)
            except Exception as e:
                LOG.error(f"Error in packet-in callback: {e}")

    # ========================================================================
    # Health Monitoring Methods
    # ========================================================================

    async def health_check(self) -> ControllerHealth:
        """Perform comprehensive health check"""
        start_time = time.time()

        try:
            # Ping the controller
            ping_success = await self.ping()
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            # Update health status
            self.health.last_check = datetime.utcnow()
            self.health.response_time_ms = response_time
            self.health.uptime_seconds = time.time() - self.start_time

            if ping_success and self.connected:
                self.health.is_healthy = True
                self.health.last_error = None
            else:
                self.health.is_healthy = False
                self.health.error_count += 1
                self.health.last_error = "Ping failed or not connected"

            # Add detailed health information
            self.health.details = {
                'connected': self.connected,
                'switch_count': len(self.switches),
                'packet_count': self.packet_count,
                'flow_count': self.flow_count,
                'event_count': self.event_count,
                'last_activity': self.last_activity.isoformat() if self.last_activity else None,
                'controller_id': self.controller_id,
                'controller_type': self.get_switch_type().value
            }

        except Exception as e:
            self.health.is_healthy = False
            self.health.error_count += 1
            self.health.last_error = str(e)
            self.health.response_time_ms = (time.time() - start_time) * 1000
            LOG.error(f"Health check failed for controller {self.controller_id}: {e}")

        return self.health

    def get_health_status(self) -> ControllerHealth:
        """Get current health status without performing new check"""
        return self.health

    def get_controller_info(self) -> Dict[str, Any]:
        """Get comprehensive controller information"""
        return {
            'controller_id': self.controller_id,
            'name': self.name,
            'description': self.description,
            'type': self.get_switch_type().value,
            'connected': self.connected,
            'health': {
                'is_healthy': self.health.is_healthy,
                'last_check': self.health.last_check.isoformat() if self.health.last_check else None,
                'response_time_ms': self.health.response_time_ms,
                'error_count': self.health.error_count,
                'last_error': self.health.last_error,
                'uptime_seconds': self.health.uptime_seconds
            },
            'metrics': {
                'switch_count': len(self.switches),
                'packet_count': self.packet_count,
                'flow_count': self.flow_count,
                'event_count': self.event_count,
                'last_activity': self.last_activity.isoformat() if self.last_activity else None
            },
            'switches': [switch.switch_id for switch in self.switches.values()],
            'config': self.config
        }

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
        self.event_count += 1

    def increment_flow_count(self):
        """Increment flow count for metrics"""
        self.flow_count += 1
        self.update_activity()

    def reset_error_count(self):
        """Reset error count when controller recovers"""
        self.health.error_count = 0
        self.health.last_error = None
