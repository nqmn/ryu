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
Core Middleware API Application

This module provides the main MiddlewareAPI Ryu application that coordinates
all middleware functionality including topology management, traffic generation,
flow control, monitoring, and AI/ML integration.
"""

import logging
import asyncio
from typing import Dict, Any, Optional

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller import dpset
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.topology import switches
from ryu.app.wsgi import WSGIApplication

from .rest_api import MiddlewareRestController
from .websocket_api import MiddlewareWebSocketController
from .gui_controller import MiddlewareGUIController
from .mininet_bridge import MininetBridge
from .traffic_gen import TrafficGenerator
from .monitoring import MonitoringService
from .ml_integration import MLIntegrationService
from .utils import MiddlewareConfig
from .sdn_backends import SwitchManager, SwitchType
from .sdn_backends.openflow_controller import RyuController
from .sdn_backends.p4runtime_controller import P4RuntimeController
from .sdn_backends.controller_manager import ControllerManager
from .events.event_stream import EventStream

LOG = logging.getLogger(__name__)


class MiddlewareAPI(app_manager.RyuApp):
    """
    Main Middleware API Application
    
    This application provides a comprehensive middleware that bridges
    communication between Ryu SDN controller, Mininet emulator, and
    external AI/ML modules or dashboards.
    
    Features:
    - Topology management via Mininet integration
    - Traffic generation and flow management
    - Real-time event streaming via WebSocket
    - AI/ML integration framework
    - Comprehensive monitoring and telemetry
    """
    
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    
    _CONTEXTS = {
        'wsgi': WSGIApplication,
        'dpset': dpset.DPSet,
        'switches': switches.Switches,
    }
    
    def __init__(self, *args, **kwargs):
        super(MiddlewareAPI, self).__init__(*args, **kwargs)

        # Initialize configuration
        self.config = MiddlewareConfig()

        # Get context objects
        self.wsgi = kwargs['wsgi']
        self.dpset = kwargs['dpset']
        self.switches_context = kwargs['switches']

        # Initialize event stream (before other components)
        self._init_event_stream()

        # Initialize SDN backend manager
        self._init_sdn_backends()

        # Initialize controller manager
        self._init_controller_manager()

        # Initialize core services
        self._init_services()

        # Register REST and WebSocket controllers
        self._register_controllers()

        # Initialize event handlers
        self._init_event_handlers()

        # Start async initialization
        self._start_async_init()

        LOG.info("Enhanced Middleware API initialized successfully")

    def _init_event_stream(self):
        """Initialize centralized event stream"""
        try:
            event_stream_config = self.config.get('event_stream', {})
            self.event_stream = EventStream(event_stream_config)
            LOG.info("Event stream initialized")
        except Exception as e:
            LOG.error(f"Failed to initialize event stream: {e}")
            raise

    def _init_controller_manager(self):
        """Initialize multi-controller manager"""
        try:
            controller_manager_config = self.config.get('controller_manager', {})
            self.controller_manager = ControllerManager(controller_manager_config, self.event_stream)
            LOG.info("Controller manager initialized")
        except Exception as e:
            LOG.error(f"Failed to initialize controller manager: {e}")
            raise

    def _init_sdn_backends(self):
        """Initialize SDN backend manager and controllers"""
        try:
            # Initialize switch manager
            self.switch_manager = SwitchManager(self.config.sdn_backends)

            # Initialize OpenFlow controller backend
            openflow_config = self.config.sdn_backends.get('openflow', {})
            if openflow_config.get('enabled', True):
                self.openflow_controller = RyuController(openflow_config, self.dpset)
                self.openflow_controller.set_event_stream(self.event_stream)
                self.switch_manager.register_backend(SwitchType.OPENFLOW, self.openflow_controller)
                LOG.info("OpenFlow backend registered with event stream")

            # Initialize P4Runtime controller backend
            p4runtime_config = self.config.sdn_backends.get('p4runtime', {})
            if p4runtime_config.get('enabled', False):
                self.p4runtime_controller = P4RuntimeController(p4runtime_config)
                self.p4runtime_controller.set_event_stream(self.event_stream)
                self.switch_manager.register_backend(SwitchType.P4RUNTIME, self.p4runtime_controller)
                LOG.info("P4Runtime backend registered with event stream")

            LOG.info("SDN backends initialized")

        except Exception as e:
            LOG.error(f"Failed to initialize SDN backends: {e}")
            raise

    def _init_services(self):
        """Initialize core middleware services"""
        try:
            # Initialize Mininet bridge
            self.mininet_bridge = MininetBridge(self.config)

            # Initialize traffic generator
            self.traffic_generator = TrafficGenerator(self.config)

            # Initialize monitoring service (now with switch manager)
            self.monitoring = MonitoringService(self.config, self.dpset, self.switch_manager)

            # Initialize ML integration service
            self.ml_integration = MLIntegrationService(self.config)

            LOG.info("All middleware services initialized")

        except Exception as e:
            LOG.error(f"Failed to initialize services: {e}")
            raise
    
    def _register_controllers(self):
        """Register REST and WebSocket controllers"""
        try:
            # Prepare data for controllers
            controller_data = {
                'middleware_app': self,
                'mininet_bridge': self.mininet_bridge,
                'traffic_generator': self.traffic_generator,
                'monitoring': self.monitoring,
                'ml_integration': self.ml_integration,
                'switch_manager': self.switch_manager,
                'controller_manager': self.controller_manager,
                'event_stream': self.event_stream,
                'config': self.config,
            }

            # Register REST controller
            self.wsgi.register(MiddlewareRestController, controller_data)

            # Register WebSocket controller
            websocket_controller = MiddlewareWebSocketController
            self.wsgi.register(websocket_controller, controller_data)

            # Set event stream for WebSocket controller
            # Note: This is a bit of a hack since we can't easily get the instance
            # In a real implementation, we'd need a better way to connect these

            # Register GUI controller
            self.wsgi.register(MiddlewareGUIController, controller_data)

            LOG.info("Controllers registered successfully")

        except Exception as e:
            LOG.error(f"Failed to register controllers: {e}")
            raise
    
    def _init_event_handlers(self):
        """Initialize event handlers for real-time monitoring"""
        # Set up packet-in callbacks for OpenFlow backend
        if hasattr(self, 'openflow_controller'):
            self.openflow_controller.subscribe_packet_in(self._handle_unified_packet_in)

        LOG.info("Event handlers initialized")

    def _start_async_init(self):
        """Start asynchronous initialization of backends"""
        try:
            # Create event loop for async operations
            import threading

            def async_init():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    # Start event stream
                    loop.run_until_complete(self.event_stream.start())
                    LOG.info("Event stream started")

                    # Start controller manager
                    loop.run_until_complete(self.controller_manager.start())
                    LOG.info("Controller manager started")

                    # Initialize switch manager (backward compatibility)
                    loop.run_until_complete(self.switch_manager.initialize())
                    LOG.info("Switch manager initialized")

                    LOG.info("Enhanced async initialization completed")
                except Exception as e:
                    LOG.error(f"Failed to initialize enhanced components asynchronously: {e}")
                finally:
                    # Keep the loop running for async operations
                    # Don't close it immediately
                    pass

            # Start in separate thread to avoid blocking Ryu
            init_thread = threading.Thread(target=async_init, daemon=True)
            init_thread.start()

        except Exception as e:
            LOG.error(f"Failed to start async initialization: {e}")

    def _handle_unified_packet_in(self, packet_data):
        """Handle packet-in events from any backend"""
        try:
            # Forward to monitoring service
            self.monitoring.on_unified_packet_in(packet_data)

            # Forward to WebSocket clients if available
            if hasattr(self, 'websocket_controller'):
                self.websocket_controller.broadcast_packet_event(packet_data)

        except Exception as e:
            LOG.error(f"Error handling unified packet-in: {e}")
    
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Handle switch features event"""
        datapath = ev.msg.datapath
        LOG.info(f"Switch connected: {datapath.id}")
        
        # Notify monitoring service
        self.monitoring.on_switch_connected(datapath)
    
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """Handle packet-in events for monitoring"""
        # Forward to OpenFlow controller backend
        if hasattr(self, 'openflow_controller'):
            self.openflow_controller.handle_packet_in(ev)

        # Also forward to monitoring service for backward compatibility
        self.monitoring.on_packet_in(ev)

    def get_topology_info(self):
        """Get comprehensive topology information from all backends"""
        try:
            topology_info = {
                'openflow_switches': [],
                'p4runtime_switches': [],
                'total_switches': 0,
                'backend_status': {}
            }

            # Get OpenFlow switches
            if hasattr(self, 'openflow_controller') and self.openflow_controller.is_connected():
                of_switches = asyncio.run(self.openflow_controller.list_switches())
                topology_info['openflow_switches'] = [switch.__dict__ for switch in of_switches]
                topology_info['backend_status']['openflow'] = 'connected'
            else:
                topology_info['backend_status']['openflow'] = 'disconnected'

            # Get P4Runtime switches
            if hasattr(self, 'p4runtime_controller') and self.p4runtime_controller.is_connected():
                p4_switches = asyncio.run(self.p4runtime_controller.list_switches())
                topology_info['p4runtime_switches'] = [switch.__dict__ for switch in p4_switches]
                topology_info['backend_status']['p4runtime'] = 'connected'
            else:
                topology_info['backend_status']['p4runtime'] = 'disconnected'

            topology_info['total_switches'] = (
                len(topology_info['openflow_switches']) +
                len(topology_info['p4runtime_switches'])
            )

            return topology_info

        except Exception as e:
            LOG.error(f"Failed to get topology info: {e}")
            return {'error': str(e)}

    def get_switch_manager(self):
        """Get the switch manager instance"""
        return self.switch_manager

    def get_backend_status(self):
        """Get status of all SDN backends"""
        try:
            status = {
                'switch_manager_initialized': self.switch_manager.is_initialized(),
                'backends': {}
            }

            if hasattr(self, 'openflow_controller'):
                status['backends']['openflow'] = {
                    'enabled': True,
                    'connected': self.openflow_controller.is_connected(),
                    'switch_count': len(self.openflow_controller.switches)
                }

            if hasattr(self, 'p4runtime_controller'):
                status['backends']['p4runtime'] = {
                    'enabled': True,
                    'connected': self.p4runtime_controller.is_connected(),
                    'switch_count': len(self.p4runtime_controller.switches)
                }

            return status

        except Exception as e:
            LOG.error(f"Failed to get backend status: {e}")
            return {'error': str(e)}
    
    def get_topology_info(self) -> Dict[str, Any]:
        """Get current topology information"""
        try:
            from ryu.topology import api as topo_api

            # Get topology data using the topology API
            switches = topo_api.get_switch(self)
            links = topo_api.get_link(self)
            hosts = topo_api.get_host(self)

            return {
                'switches': [switch.to_dict() for switch in switches],
                'links': [link.to_dict() for link in links],
                'hosts': [host.to_dict() for host in hosts],
                'timestamp': self.monitoring.get_current_timestamp(),
            }
        except Exception as e:
            LOG.error(f"Failed to get topology info: {e}")
            return {'error': str(e)}
    
    def get_stats_info(self, dpid: Optional[int] = None) -> Dict[str, Any]:
        """Get statistics information"""
        return self.monitoring.get_stats_info(dpid)

    async def shutdown(self):
        """Shutdown the middleware and all components"""
        try:
            LOG.info("Shutting down enhanced middleware...")

            # Stop controller manager
            if hasattr(self, 'controller_manager'):
                await self.controller_manager.stop()
                LOG.info("Controller manager stopped")

            # Stop event stream
            if hasattr(self, 'event_stream'):
                await self.event_stream.stop()
                LOG.info("Event stream stopped")

            # Stop switch manager
            if hasattr(self, 'switch_manager'):
                await self.switch_manager.shutdown()
                LOG.info("Switch manager stopped")

            LOG.info("Enhanced middleware shutdown completed")

        except Exception as e:
            LOG.error(f"Error during shutdown: {e}")

    def get_controller_manager(self):
        """Get the controller manager instance"""
        return getattr(self, 'controller_manager', None)

    def get_event_stream(self):
        """Get the event stream instance"""
        return getattr(self, 'event_stream', None)
    
    def shutdown(self):
        """Cleanup resources on shutdown"""
        try:
            if hasattr(self, 'mininet_bridge'):
                self.mininet_bridge.cleanup()
            
            if hasattr(self, 'traffic_generator'):
                self.traffic_generator.cleanup()
            
            LOG.info("Middleware API shutdown completed")
            
        except Exception as e:
            LOG.error(f"Error during shutdown: {e}")
