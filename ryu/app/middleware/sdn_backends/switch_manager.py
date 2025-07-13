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
Switch Manager

This module provides the SwitchManager class that handles routing of operations
to appropriate SDN backend controllers based on switch type and configuration.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Union
from threading import Lock

from .base import SDNControllerBase, SwitchType, FlowData, PacketData, SwitchInfo
from ..utils import ResponseFormatter

LOG = logging.getLogger(__name__)


class SwitchManager:
    """
    Switch Manager for routing operations to appropriate SDN backends
    
    This class manages multiple SDN backend controllers and routes operations
    to the appropriate controller based on switch type, configuration, or
    runtime detection.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.backends: Dict[SwitchType, SDNControllerBase] = {}
        self.switch_registry: Dict[str, SwitchType] = {}
        self.switch_configs: Dict[str, Dict[str, Any]] = {}
        self.lock = Lock()
        self.initialized = False
        
        # Load switch configurations
        self._load_switch_configs()
        
    def _load_switch_configs(self):
        """Load switch configurations from config"""
        try:
            sdn_config = self.config.get('sdn_backends', {})
            
            # Load OpenFlow switch configurations
            of_config = sdn_config.get('openflow', {})
            if of_config.get('enabled', True):
                # Auto-detect OpenFlow switches (legacy behavior)
                pass
            
            # Load P4Runtime switch configurations
            p4_config = sdn_config.get('p4runtime', {})
            if p4_config.get('enabled', False):
                switches = p4_config.get('switches', [])
                for switch_config in switches:
                    switch_id = str(switch_config.get('device_id'))
                    self.switch_registry[switch_id] = SwitchType.P4RUNTIME
                    self.switch_configs[switch_id] = switch_config
                    
            LOG.info(f"Loaded configurations for {len(self.switch_configs)} switches")
            
        except Exception as e:
            LOG.error(f"Failed to load switch configurations: {e}")
    
    def register_backend(self, switch_type: SwitchType, backend: SDNControllerBase):
        """Register a backend controller for a specific switch type"""
        with self.lock:
            self.backends[switch_type] = backend
            LOG.info(f"Registered backend for {switch_type.value}")
    
    def unregister_backend(self, switch_type: SwitchType):
        """Unregister a backend controller"""
        with self.lock:
            if switch_type in self.backends:
                del self.backends[switch_type]
                LOG.info(f"Unregistered backend for {switch_type.value}")
    
    async def initialize(self) -> bool:
        """Initialize all registered backends"""
        try:
            with self.lock:
                backends_to_init = list(self.backends.values())
            
            # Initialize all backends
            init_results = []
            for backend in backends_to_init:
                try:
                    result = await backend.initialize()
                    init_results.append(result)
                    LOG.info(f"Backend {backend.get_switch_type().value} initialized: {result}")
                except Exception as e:
                    LOG.error(f"Failed to initialize backend {backend.get_switch_type().value}: {e}")
                    init_results.append(False)
            
            self.initialized = any(init_results)
            return self.initialized
            
        except Exception as e:
            LOG.error(f"Failed to initialize switch manager: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown all backends"""
        try:
            with self.lock:
                backends_to_shutdown = list(self.backends.values())
            
            for backend in backends_to_shutdown:
                try:
                    await backend.shutdown()
                    LOG.info(f"Backend {backend.get_switch_type().value} shutdown")
                except Exception as e:
                    LOG.error(f"Failed to shutdown backend {backend.get_switch_type().value}: {e}")
            
            self.initialized = False
            
        except Exception as e:
            LOG.error(f"Failed to shutdown switch manager: {e}")
    
    def detect_switch_type(self, switch_id: str, flow_data: Optional[FlowData] = None) -> SwitchType:
        """Detect switch type based on switch ID and context"""
        # Check explicit registry first
        if switch_id in self.switch_registry:
            return self.switch_registry[switch_id]
        
        # Try to detect from switch ID format
        try:
            # OpenFlow DPIDs are typically numeric or hex
            if switch_id.isdigit() or (switch_id.startswith('0x') and len(switch_id) <= 18):
                return SwitchType.OPENFLOW
        except:
            pass
        
        # Check if flow data contains P4-specific fields
        if flow_data:
            if flow_data.table_name or flow_data.action_name:
                return SwitchType.P4RUNTIME
        
        # Default to OpenFlow for backward compatibility
        return SwitchType.OPENFLOW
    
    def get_backend(self, switch_type: SwitchType) -> Optional[SDNControllerBase]:
        """Get backend controller for the specified switch type"""
        with self.lock:
            return self.backends.get(switch_type)
    
    def get_backend_for_switch(self, switch_id: str, flow_data: Optional[FlowData] = None) -> Optional[SDNControllerBase]:
        """Get backend controller for the specified switch"""
        switch_type = self.detect_switch_type(switch_id, flow_data)
        return self.get_backend(switch_type)
    
    async def install_flow(self, flow_data: FlowData) -> Dict[str, Any]:
        """Route flow installation to appropriate backend"""
        try:
            backend = self.get_backend_for_switch(flow_data.switch_id, flow_data)
            if not backend:
                return ResponseFormatter.error(
                    f"No backend available for switch {flow_data.switch_id}",
                    "BACKEND_NOT_AVAILABLE"
                )
            
            # Set switch type in flow data
            flow_data.switch_type = backend.get_switch_type()
            
            result = await backend.install_flow(flow_data)
            return result
            
        except Exception as e:
            LOG.error(f"Failed to install flow: {e}")
            return ResponseFormatter.error(str(e), "FLOW_INSTALL_ERROR")
    
    async def delete_flow(self, flow_data: FlowData) -> Dict[str, Any]:
        """Route flow deletion to appropriate backend"""
        try:
            backend = self.get_backend_for_switch(flow_data.switch_id, flow_data)
            if not backend:
                return ResponseFormatter.error(
                    f"No backend available for switch {flow_data.switch_id}",
                    "BACKEND_NOT_AVAILABLE"
                )
            
            # Set switch type in flow data
            flow_data.switch_type = backend.get_switch_type()
            
            result = await backend.delete_flow(flow_data)
            return result
            
        except Exception as e:
            LOG.error(f"Failed to delete flow: {e}")
            return ResponseFormatter.error(str(e), "FLOW_DELETE_ERROR")
    
    async def get_flow_stats(self, switch_id: str, table_id: Optional[int] = None) -> Dict[str, Any]:
        """Route flow stats request to appropriate backend"""
        try:
            backend = self.get_backend_for_switch(switch_id)
            if not backend:
                return ResponseFormatter.error(
                    f"No backend available for switch {switch_id}",
                    "BACKEND_NOT_AVAILABLE"
                )
            
            result = await backend.get_flow_stats(switch_id, table_id)
            return result
            
        except Exception as e:
            LOG.error(f"Failed to get flow stats: {e}")
            return ResponseFormatter.error(str(e), "FLOW_STATS_ERROR")
    
    async def get_port_stats(self, switch_id: str, port_id: Optional[str] = None) -> Dict[str, Any]:
        """Route port stats request to appropriate backend"""
        try:
            backend = self.get_backend_for_switch(switch_id)
            if not backend:
                return ResponseFormatter.error(
                    f"No backend available for switch {switch_id}",
                    "BACKEND_NOT_AVAILABLE"
                )
            
            result = await backend.get_port_stats(switch_id, port_id)
            return result
            
        except Exception as e:
            LOG.error(f"Failed to get port stats: {e}")
            return ResponseFormatter.error(str(e), "PORT_STATS_ERROR")
    
    async def list_all_switches(self) -> Dict[str, Any]:
        """List all switches from all backends"""
        try:
            all_switches = []
            
            with self.lock:
                backends = list(self.backends.values())
            
            for backend in backends:
                try:
                    switches = await backend.list_switches()
                    all_switches.extend(switches)
                except Exception as e:
                    LOG.error(f"Failed to list switches from {backend.get_switch_type().value}: {e}")
            
            return ResponseFormatter.success({
                'switches': [switch.__dict__ for switch in all_switches],
                'total_count': len(all_switches)
            })
            
        except Exception as e:
            LOG.error(f"Failed to list switches: {e}")
            return ResponseFormatter.error(str(e), "LIST_SWITCHES_ERROR")
    
    def get_switch_config(self, switch_id: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific switch"""
        return self.switch_configs.get(switch_id)
    
    def is_initialized(self) -> bool:
        """Check if the switch manager is initialized"""
        return self.initialized
