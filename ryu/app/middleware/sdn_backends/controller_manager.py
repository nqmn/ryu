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
Controller Manager

This module provides the ControllerManager class that handles registration,
lifecycle management, health monitoring, and failover logic for multiple
SDN controllers of different types.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Set
from threading import Lock
from datetime import datetime, timedelta

from .base import SDNControllerBase, SwitchType, ControllerHealth
from .openflow_controller import RyuController
from .p4runtime_controller import P4RuntimeController
from ..models.controller_schemas import (
    ControllerConfig, ControllerInfo, ControllerStatus, HealthStatus,
    SwitchMapping, ControllerMetrics, ControllerType
)
from ..events.event_stream import EventStream
from ..utils import ResponseFormatter

LOG = logging.getLogger(__name__)


class ControllerManager:
    """
    Multi-Controller Management System
    
    This class manages multiple SDN controllers, handles registration,
    health monitoring, failover logic, and provides a unified interface
    for controller operations.
    """
    
    def __init__(self, config: Dict[str, Any], event_stream: EventStream):
        self.config = config
        self.event_stream = event_stream
        
        # Controller registry
        self.controllers: Dict[str, SDNControllerBase] = {}
        self.controller_info: Dict[str, ControllerInfo] = {}
        self.controller_lock = Lock()
        
        # Switch mapping
        self.switch_mappings: Dict[str, SwitchMapping] = {}
        self.mapping_lock = Lock()
        
        # Health monitoring
        self.health_check_interval = config.get('health_check_interval', 30)
        self.health_check_timeout = config.get('health_check_timeout', 5)
        self.max_health_failures = config.get('max_health_failures', 3)
        
        # Background tasks
        self.health_monitor_task = None
        self.running = False
        
        # Statistics
        self.stats = {
            'total_controllers': 0,
            'active_controllers': 0,
            'failed_controllers': 0,
            'total_switches': 0,
            'failover_count': 0,
            'health_checks_performed': 0,
            'start_time': datetime.utcnow()
        }
    
    async def start(self):
        """Start the controller manager"""
        if self.running:
            LOG.warning("Controller manager already running")
            return
        
        self.running = True
        LOG.info("Starting controller manager")
        
        # Start health monitoring
        self.health_monitor_task = asyncio.create_task(self._health_monitor_loop())
        
        # Subscribe to events
        self.event_stream.subscribe(
            'controller_manager',
            self._handle_controller_event
        )
        
        LOG.info("Controller manager started successfully")
    
    async def stop(self):
        """Stop the controller manager"""
        if not self.running:
            return
        
        self.running = False
        LOG.info("Stopping controller manager")
        
        # Stop health monitoring
        if self.health_monitor_task:
            self.health_monitor_task.cancel()
            try:
                await self.health_monitor_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown all controllers
        await self._shutdown_all_controllers()
        
        # Unsubscribe from events
        self.event_stream.unsubscribe('controller_manager')
        
        LOG.info("Controller manager stopped")
    
    async def register_controller(self, config: ControllerConfig, 
                                auto_start: bool = True) -> Dict[str, Any]:
        """Register a new controller"""
        try:
            controller_id = config.controller_id
            
            with self.controller_lock:
                if controller_id in self.controllers:
                    return ResponseFormatter.error(
                        f"Controller {controller_id} already registered",
                        "CONTROLLER_EXISTS"
                    )
            
            # Create controller instance
            controller = await self._create_controller_instance(config)
            if not controller:
                return ResponseFormatter.error(
                    f"Failed to create controller instance for type {config.controller_type}",
                    "CONTROLLER_CREATION_FAILED"
                )
            
            # Create controller info
            controller_info = ControllerInfo(
                config=config,
                status=ControllerStatus.INITIALIZING,
                health_status=HealthStatus.UNKNOWN,
                metrics=ControllerMetrics()
            )
            
            # Register controller
            with self.controller_lock:
                self.controllers[controller_id] = controller
                self.controller_info[controller_id] = controller_info
                self.stats['total_controllers'] += 1
            
            # Auto-start if requested
            if auto_start:
                await self._start_controller(controller_id)
            
            # Publish event
            await self.event_stream.publish_event(
                'controller_registered',
                'controller_manager',
                'system',
                {
                    'controller_id': controller_id,
                    'controller_type': config.controller_type.value,
                    'auto_start': auto_start
                }
            )
            
            LOG.info(f"Controller {controller_id} registered successfully")
            
            return ResponseFormatter.success({
                'controller_id': controller_id,
                'status': 'registered',
                'auto_start': auto_start,
                'controller_info': controller_info.dict()
            })
            
        except Exception as e:
            LOG.error(f"Failed to register controller: {e}")
            return ResponseFormatter.error(str(e), "REGISTRATION_FAILED")
    
    async def deregister_controller(self, controller_id: str) -> Dict[str, Any]:
        """Deregister a controller"""
        try:
            with self.controller_lock:
                if controller_id not in self.controllers:
                    return ResponseFormatter.error(
                        f"Controller {controller_id} not found",
                        "CONTROLLER_NOT_FOUND"
                    )
                
                controller = self.controllers[controller_id]
                controller_info = self.controller_info[controller_id]
            
            # Stop controller if running
            if controller_info.status == ControllerStatus.CONNECTED:
                await self._stop_controller(controller_id)
            
            # Remove switch mappings
            await self._remove_controller_mappings(controller_id)
            
            # Remove from registry
            with self.controller_lock:
                del self.controllers[controller_id]
                del self.controller_info[controller_id]
                self.stats['total_controllers'] -= 1
            
            # Publish event
            await self.event_stream.publish_event(
                'controller_deregistered',
                'controller_manager',
                'system',
                {'controller_id': controller_id}
            )
            
            LOG.info(f"Controller {controller_id} deregistered successfully")
            
            return ResponseFormatter.success({
                'controller_id': controller_id,
                'status': 'deregistered'
            })
            
        except Exception as e:
            LOG.error(f"Failed to deregister controller {controller_id}: {e}")
            return ResponseFormatter.error(str(e), "DEREGISTRATION_FAILED")
    
    async def map_switch_to_controller(self, switch_id: str, primary_controller: str,
                                     backup_controllers: List[str] = None) -> Dict[str, Any]:
        """Map a switch to a controller with optional backups"""
        try:
            backup_controllers = backup_controllers or []
            
            # Validate controllers exist
            with self.controller_lock:
                if primary_controller not in self.controllers:
                    return ResponseFormatter.error(
                        f"Primary controller {primary_controller} not found",
                        "CONTROLLER_NOT_FOUND"
                    )
                
                for backup_id in backup_controllers:
                    if backup_id not in self.controllers:
                        return ResponseFormatter.error(
                            f"Backup controller {backup_id} not found",
                            "CONTROLLER_NOT_FOUND"
                        )
            
            # Create mapping
            mapping = SwitchMapping(
                switch_id=switch_id,
                primary_controller=primary_controller,
                backup_controllers=backup_controllers,
                current_controller=primary_controller
            )
            
            # Store mapping
            with self.mapping_lock:
                self.switch_mappings[switch_id] = mapping
            
            # Update controller info
            with self.controller_lock:
                if primary_controller in self.controller_info:
                    self.controller_info[primary_controller].assigned_switches.append(switch_id)
            
            # Publish event
            await self.event_stream.publish_event(
                'switch_mapped',
                'controller_manager',
                'system',
                {
                    'switch_id': switch_id,
                    'primary_controller': primary_controller,
                    'backup_controllers': backup_controllers
                }
            )
            
            LOG.info(f"Switch {switch_id} mapped to controller {primary_controller}")
            
            return ResponseFormatter.success({
                'switch_id': switch_id,
                'mapping': mapping.dict()
            })
            
        except Exception as e:
            LOG.error(f"Failed to map switch {switch_id}: {e}")
            return ResponseFormatter.error(str(e), "MAPPING_FAILED")
    
    def get_controller_for_switch(self, switch_id: str) -> Optional[SDNControllerBase]:
        """Get the active controller for a switch"""
        with self.mapping_lock:
            mapping = self.switch_mappings.get(switch_id)
            if not mapping:
                return None
        
        with self.controller_lock:
            return self.controllers.get(mapping.current_controller)
    
    def list_controllers(self) -> Dict[str, Any]:
        """List all registered controllers"""
        try:
            with self.controller_lock:
                controllers_data = []
                for controller_id, info in self.controller_info.items():
                    controllers_data.append(info.dict())
            
            healthy_count = sum(1 for info in self.controller_info.values() 
                              if info.health_status == HealthStatus.HEALTHY)
            connected_count = sum(1 for info in self.controller_info.values() 
                                if info.status == ControllerStatus.CONNECTED)
            
            return ResponseFormatter.success({
                'controllers': controllers_data,
                'total_count': len(controllers_data),
                'healthy_count': healthy_count,
                'connected_count': connected_count,
                'stats': self.stats
            })
            
        except Exception as e:
            LOG.error(f"Failed to list controllers: {e}")
            return ResponseFormatter.error(str(e), "LIST_FAILED")
    
    def get_switch_mappings(self) -> Dict[str, Any]:
        """Get all switch mappings"""
        try:
            with self.mapping_lock:
                mappings_data = [mapping.dict() for mapping in self.switch_mappings.values()]
            
            return ResponseFormatter.success({
                'mappings': mappings_data,
                'total_count': len(mappings_data)
            })
            
        except Exception as e:
            LOG.error(f"Failed to get switch mappings: {e}")
            return ResponseFormatter.error(str(e), "MAPPING_LIST_FAILED")
    
    async def _create_controller_instance(self, config: ControllerConfig) -> Optional[SDNControllerBase]:
        """Create controller instance based on type"""
        try:
            controller_config = config.dict()
            
            if config.controller_type == ControllerType.RYU_OPENFLOW:
                return RyuController(controller_config)
            elif config.controller_type == ControllerType.P4RUNTIME:
                return P4RuntimeController(controller_config)
            else:
                LOG.error(f"Unsupported controller type: {config.controller_type}")
                return None
                
        except Exception as e:
            LOG.error(f"Failed to create controller instance: {e}")
            return None
    
    async def _start_controller(self, controller_id: str):
        """Start a controller"""
        try:
            with self.controller_lock:
                controller = self.controllers.get(controller_id)
                controller_info = self.controller_info.get(controller_id)
            
            if not controller or not controller_info:
                return
            
            # Update status
            controller_info.status = ControllerStatus.INITIALIZING
            
            # Initialize controller
            success = await controller.initialize()
            
            if success:
                controller_info.status = ControllerStatus.CONNECTED
                controller_info.last_seen = datetime.utcnow()
                self.stats['active_controllers'] += 1
                
                # Subscribe to controller events
                controller.subscribe_packet_in(self._handle_packet_in)
                
                LOG.info(f"Controller {controller_id} started successfully")
            else:
                controller_info.status = ControllerStatus.ERROR
                controller_info.last_error = "Failed to initialize"
                self.stats['failed_controllers'] += 1
                
                LOG.error(f"Failed to start controller {controller_id}")
            
        except Exception as e:
            LOG.error(f"Error starting controller {controller_id}: {e}")
            with self.controller_lock:
                if controller_id in self.controller_info:
                    self.controller_info[controller_id].status = ControllerStatus.ERROR
                    self.controller_info[controller_id].last_error = str(e)
    
    async def _stop_controller(self, controller_id: str):
        """Stop a controller"""
        try:
            with self.controller_lock:
                controller = self.controllers.get(controller_id)
                controller_info = self.controller_info.get(controller_id)
            
            if not controller or not controller_info:
                return
            
            # Shutdown controller
            await controller.shutdown()
            
            # Update status
            controller_info.status = ControllerStatus.DISCONNECTED
            if self.stats['active_controllers'] > 0:
                self.stats['active_controllers'] -= 1
            
            LOG.info(f"Controller {controller_id} stopped")
            
        except Exception as e:
            LOG.error(f"Error stopping controller {controller_id}: {e}")
    
    async def _shutdown_all_controllers(self):
        """Shutdown all controllers"""
        with self.controller_lock:
            controller_ids = list(self.controllers.keys())
        
        for controller_id in controller_ids:
            await self._stop_controller(controller_id)
    
    async def _remove_controller_mappings(self, controller_id: str):
        """Remove all switch mappings for a controller"""
        with self.mapping_lock:
            switches_to_remove = []
            for switch_id, mapping in self.switch_mappings.items():
                if (mapping.primary_controller == controller_id or 
                    mapping.current_controller == controller_id):
                    switches_to_remove.append(switch_id)
            
            for switch_id in switches_to_remove:
                del self.switch_mappings[switch_id]
                LOG.info(f"Removed mapping for switch {switch_id}")
    
    async def _health_monitor_loop(self):
        """Health monitoring loop"""
        LOG.info("Health monitor started")
        
        while self.running:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_checks()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                LOG.error(f"Error in health monitor: {e}")
    
    async def _perform_health_checks(self):
        """Perform health checks on all controllers"""
        with self.controller_lock:
            controllers_to_check = list(self.controllers.items())
        
        for controller_id, controller in controllers_to_check:
            try:
                # Perform health check
                health = await controller.health_check()
                
                # Update controller info
                with self.controller_lock:
                    if controller_id in self.controller_info:
                        info = self.controller_info[controller_id]
                        info.last_health_check = datetime.utcnow()
                        
                        if health.is_healthy:
                            info.health_status = HealthStatus.HEALTHY
                            info.last_seen = datetime.utcnow()
                            info.error_count = 0
                        else:
                            info.health_status = HealthStatus.UNHEALTHY
                            info.error_count += 1
                            info.last_error = health.last_error
                            
                            # Check if failover is needed
                            if info.error_count >= self.max_health_failures:
                                await self._handle_controller_failure(controller_id)
                
                self.stats['health_checks_performed'] += 1
                
            except Exception as e:
                LOG.error(f"Health check failed for controller {controller_id}: {e}")
    
    async def _handle_controller_failure(self, failed_controller_id: str):
        """Handle controller failure and perform failover if needed"""
        LOG.warning(f"Controller {failed_controller_id} has failed, initiating failover")
        
        # Find switches that need failover
        switches_to_failover = []
        with self.mapping_lock:
            for switch_id, mapping in self.switch_mappings.items():
                if mapping.current_controller == failed_controller_id:
                    switches_to_failover.append((switch_id, mapping))
        
        # Perform failover for each switch
        for switch_id, mapping in switches_to_failover:
            await self._perform_switch_failover(switch_id, mapping, failed_controller_id)
    
    async def _perform_switch_failover(self, switch_id: str, mapping: SwitchMapping, 
                                     failed_controller_id: str):
        """Perform failover for a specific switch"""
        try:
            # Find next available backup controller
            backup_controller_id = None
            for backup_id in mapping.backup_controllers:
                with self.controller_lock:
                    if (backup_id in self.controller_info and 
                        self.controller_info[backup_id].health_status == HealthStatus.HEALTHY):
                        backup_controller_id = backup_id
                        break
            
            if not backup_controller_id:
                LOG.error(f"No healthy backup controller available for switch {switch_id}")
                return
            
            # Update mapping
            with self.mapping_lock:
                mapping.current_controller = backup_controller_id
                mapping.failover_count += 1
                mapping.last_updated = datetime.utcnow()
            
            # Update statistics
            self.stats['failover_count'] += 1
            
            # Publish failover event
            await self.event_stream.publish_event(
                'switch_failover',
                'controller_manager',
                'system',
                {
                    'switch_id': switch_id,
                    'failed_controller': failed_controller_id,
                    'new_controller': backup_controller_id,
                    'failover_count': mapping.failover_count
                },
                priority=3  # High priority
            )
            
            LOG.info(f"Switch {switch_id} failed over from {failed_controller_id} to {backup_controller_id}")
            
        except Exception as e:
            LOG.error(f"Failover failed for switch {switch_id}: {e}")
    
    def _handle_packet_in(self, packet_data):
        """Handle packet-in events from controllers"""
        # Forward to event stream
        asyncio.create_task(self.event_stream.publish_event(
            'packet_in',
            packet_data.switch_id,
            packet_data.switch_type.value,
            {
                'switch_id': packet_data.switch_id,
                'packet_size': len(packet_data.packet),
                'metadata': packet_data.metadata
            }
        ))
    
    async def _handle_controller_event(self, event):
        """Handle events from the event stream"""
        # Process controller-related events
        if event.event_type in ['controller_connected', 'controller_disconnected']:
            # Update controller status based on events
            pass
