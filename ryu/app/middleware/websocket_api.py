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
Middleware WebSocket API Controller

This module provides WebSocket endpoints for real-time event streaming
including topology changes, packet events, flow events, and ML predictions.
"""

import json
import logging
import time
import asyncio
from socket import error as SocketError
from typing import Dict, Any, List, Optional, Set
try:
    import eventlet
    from eventlet import semaphore
    Lock = semaphore.Semaphore
except ImportError:
    from threading import Lock

from tinyrpc.exc import InvalidReplyError

from ryu.app.wsgi import ControllerBase, websocket, WebSocketRPCClient
from ryu.controller.handler import set_ev_cls
from ryu.topology import event as topo_event
from ryu.controller import ofp_event

from .events.event_stream import Event, EventFilter

LOG = logging.getLogger(__name__)


class MiddlewareWebSocketController(ControllerBase):
    """
    WebSocket API Controller for Middleware
    
    Provides real-time event streaming for:
    - Topology events (switch/link/host changes)
    - Packet-in events
    - Flow events (installation/removal)
    - Port status events
    - ML prediction events
    - Traffic alerts
    """
    
    def __init__(self, req, link, data, **config):
        super(MiddlewareWebSocketController, self).__init__(req, link, data, **config)
        
        # Get middleware components from data
        self.middleware_app = data['middleware_app']
        self.mininet_bridge = data['mininet_bridge']
        self.traffic_generator = data['traffic_generator']
        self.monitoring = data['monitoring']
        self.ml_integration = data['ml_integration']
        self.switch_manager = data['switch_manager']
        self.config = data['config']
        
        # WebSocket client management with enhanced filtering
        self.rpc_clients: List[WebSocketRPCClient] = []
        self.client_filters: Dict[WebSocketRPCClient, EventFilter] = {}
        self.client_subscriptions: Dict[WebSocketRPCClient, Set[str]] = {}
        self.clients_lock = Lock()

        # Event counters for statistics (enhanced)
        self.event_counters = {
            'switch_enter': 0,
            'switch_leave': 0,
            'link_add': 0,
            'link_delete': 0,
            'host_add': 0,
            'packet_in': 0,
            'flow_removed': 0,
            'port_status': 0,
            'ml_prediction': 0,
            'traffic_alert': 0,
            'p4_packet_in': 0,
            'p4_pipeline_installed': 0,
            'p4_table_updated': 0,
            'flow_installed': 0,
            'flow_deleted': 0,
            'controller_registered': 0,
            'controller_deregistered': 0,
            'switch_mapped': 0,
            'switch_failover': 0,
            'manual_failover': 0,
        }

        # Event stream integration
        self.event_stream = None
        self.event_stream_subscriber_id = f"websocket_controller_{id(self)}"

        LOG.info("Enhanced WebSocket controller initialized")

    def set_event_stream(self, event_stream):
        """Set the event stream for centralized event handling"""
        self.event_stream = event_stream

        # Subscribe to all events from the event stream
        if event_stream:
            event_stream.subscribe(
                self.event_stream_subscriber_id,
                self._handle_event_stream_event
            )
            LOG.info("WebSocket controller subscribed to event stream")

    def _handle_event_stream_event(self, event: Event):
        """Handle events from the centralized event stream"""
        try:
            # Convert event stream event to WebSocket format
            event_data = {
                'event_type': event.event_type,
                'source_controller': event.source_controller,
                'source_type': event.source_type,
                'data': event.data,
                'timestamp': event.timestamp.timestamp(),
                'sequence_number': event.sequence_number,
                'priority': event.priority,
                'metadata': event.metadata
            }

            # Broadcast to WebSocket clients with filtering
            self._broadcast_filtered_event(event_data, event)

        except Exception as e:
            LOG.error(f"Error handling event stream event: {e}")

    def _broadcast_filtered_event(self, event_data: Dict[str, Any], original_event: Event):
        """Broadcast event to WebSocket clients with filtering"""
        if not self.rpc_clients:
            return

        # Update event counter
        event_type = event_data['event_type']
        if event_type in self.event_counters:
            self.event_counters[event_type] += 1

        # Prepare event message
        event_message = {
            'event_type': event_type,
            'data': event_data,
            'timestamp': time.time(),
            'sequence_number': self.event_counters.get(event_type, 0)
        }

        # Broadcast to filtered clients
        disconnected_clients = []

        with self.clients_lock:
            for rpc_client in self.rpc_clients:
                try:
                    # Check if client has filters
                    client_filter = self.client_filters.get(rpc_client)
                    if client_filter and not client_filter.matches(original_event):
                        continue

                    # Check subscriptions
                    subscriptions = self.client_subscriptions.get(rpc_client)
                    if subscriptions and event_type not in subscriptions:
                        continue

                    # Send event
                    rpc_server = rpc_client.get_proxy()
                    rpc_server.event_notification(event_message)

                except SocketError:
                    LOG.debug(f'WebSocket disconnected: {rpc_client.ws}')
                    disconnected_clients.append(rpc_client)

                except InvalidReplyError as e:
                    LOG.error(f'Invalid reply error: {e}')

                except Exception as e:
                    LOG.error(f'Error broadcasting to client: {e}')
                    disconnected_clients.append(rpc_client)

            # Remove disconnected clients
            for client in disconnected_clients:
                self._cleanup_client(client)

        if disconnected_clients:
            LOG.info(f"Removed {len(disconnected_clients)} disconnected clients")

    def _cleanup_client(self, client: WebSocketRPCClient):
        """Clean up client data"""
        if client in self.rpc_clients:
            self.rpc_clients.remove(client)
        if client in self.client_filters:
            del self.client_filters[client]
        if client in self.client_subscriptions:
            del self.client_subscriptions[client]

    @websocket('middleware', '/v2.0/events/ws')
    def websocket_handler(self, ws):
        """Handle WebSocket connections for event streaming"""
        try:
            LOG.info(f"WebSocket client connected: {ws}")
            
            # Check connection limit
            with self.clients_lock:
                if len(self.rpc_clients) >= self.config.websocket_max_connections:
                    LOG.warning("WebSocket connection limit reached")
                    ws.close()
                    return
                
                # Create RPC client and add to list
                rpc_client = WebSocketRPCClient(ws)
                self.rpc_clients.append(rpc_client)

                # Initialize client data
                self.client_filters[rpc_client] = EventFilter()  # Default: no filtering
                self.client_subscriptions[rpc_client] = set()    # Default: all events

            # Send welcome message
            self._send_welcome_message(rpc_client)
            
            # Start serving RPC requests
            rpc_client.serve_forever()
            
        except Exception as e:
            LOG.error(f"WebSocket error: {e}")
        finally:
            # Clean up on disconnect
            with self.clients_lock:
                self._cleanup_client(rpc_client)
            LOG.info(f"WebSocket client disconnected: {ws}")
    
    def _send_welcome_message(self, rpc_client: WebSocketRPCClient):
        """Send enhanced welcome message to new client"""
        try:
            # Get event stream stats if available
            event_stream_stats = {}
            if self.event_stream:
                event_stream_stats = self.event_stream.get_stats()

            welcome_msg = {
                'event_type': 'welcome',
                'message': 'Connected to Enhanced Ryu Middleware WebSocket API v2.0',
                'timestamp': time.time(),
                'available_events': list(self.event_counters.keys()),
                'event_counters': self.event_counters.copy(),
                'event_stream_stats': event_stream_stats,
                'features': {
                    'filtering': True,
                    'subscriptions': True,
                    'multi_controller': True,
                    'centralized_events': self.event_stream is not None
                },
                'api_version': '2.0',
                'client_id': id(rpc_client)
            }

            rpc_server = rpc_client.get_proxy()
            rpc_server.event_notification(welcome_msg)

        except Exception as e:
            LOG.error(f"Failed to send welcome message: {e}")

    def set_client_filter(self, client_id: int, event_types: List[str] = None,
                         controller_ids: List[str] = None, source_types: List[str] = None,
                         min_priority: int = 1):
        """Set event filter for a specific client"""
        try:
            # Find client by ID
            target_client = None
            with self.clients_lock:
                for client in self.rpc_clients:
                    if id(client) == client_id:
                        target_client = client
                        break

            if not target_client:
                LOG.warning(f"Client {client_id} not found for filter update")
                return False

            # Create new filter
            event_filter = EventFilter()
            if event_types:
                event_filter.event_types = set(event_types)
            if controller_ids:
                event_filter.controller_ids = set(controller_ids)
            if source_types:
                event_filter.source_types = set(source_types)
            event_filter.min_priority = min_priority

            # Update client filter
            with self.clients_lock:
                self.client_filters[target_client] = event_filter

            LOG.info(f"Updated filter for client {client_id}")
            return True

        except Exception as e:
            LOG.error(f"Failed to set client filter: {e}")
            return False

    def set_client_subscriptions(self, client_id: int, event_types: List[str]):
        """Set event subscriptions for a specific client"""
        try:
            # Find client by ID
            target_client = None
            with self.clients_lock:
                for client in self.rpc_clients:
                    if id(client) == client_id:
                        target_client = client
                        break

            if not target_client:
                LOG.warning(f"Client {client_id} not found for subscription update")
                return False

            # Update subscriptions
            with self.clients_lock:
                self.client_subscriptions[target_client] = set(event_types)

            LOG.info(f"Updated subscriptions for client {client_id}: {event_types}")
            return True

        except Exception as e:
            LOG.error(f"Failed to set client subscriptions: {e}")
            return False
    
    def broadcast_event(self, event_type: str, event_data: Dict[str, Any]):
        """Broadcast event to all connected WebSocket clients"""
        if not self.rpc_clients:
            return
        
        # Increment event counter
        if event_type in self.event_counters:
            self.event_counters[event_type] += 1
        
        # Prepare event message
        event_message = {
            'event_type': event_type,
            'data': event_data,
            'timestamp': time.time(),
            'sequence_number': self.event_counters.get(event_type, 0)
        }
        
        # Broadcast to all clients
        disconnected_clients = []
        
        with self.clients_lock:
            for rpc_client in self.rpc_clients:
                try:
                    rpc_server = rpc_client.get_proxy()
                    rpc_server.event_notification(event_message)
                    
                except SocketError:
                    LOG.debug(f'WebSocket disconnected: {rpc_client.ws}')
                    disconnected_clients.append(rpc_client)
                    
                except InvalidReplyError as e:
                    LOG.error(f'Invalid reply error: {e}')
                    
                except Exception as e:
                    LOG.error(f'Error broadcasting to client: {e}')
                    disconnected_clients.append(rpc_client)
            
            # Remove disconnected clients
            for client in disconnected_clients:
                if client in self.rpc_clients:
                    self.rpc_clients.remove(client)
        
        if disconnected_clients:
            LOG.info(f"Removed {len(disconnected_clients)} disconnected clients")
    
    # ========================================================================
    # Topology Event Handlers
    # ========================================================================
    
    def on_switch_enter(self, switch_data: Dict[str, Any]):
        """Handle switch enter event"""
        self.broadcast_event('switch_enter', switch_data)
    
    def on_switch_leave(self, switch_data: Dict[str, Any]):
        """Handle switch leave event"""
        self.broadcast_event('switch_leave', switch_data)
    
    def on_link_add(self, link_data: Dict[str, Any]):
        """Handle link add event"""
        self.broadcast_event('link_add', link_data)
    
    def on_link_delete(self, link_data: Dict[str, Any]):
        """Handle link delete event"""
        self.broadcast_event('link_delete', link_data)
    
    def on_host_add(self, host_data: Dict[str, Any]):
        """Handle host add event"""
        self.broadcast_event('host_add', host_data)
    
    # ========================================================================
    # OpenFlow Event Handlers
    # ========================================================================
    
    def on_packet_in(self, packet_data: Dict[str, Any]):
        """Handle packet-in event"""
        # Filter packet events to avoid spam
        if self._should_broadcast_packet_event(packet_data):
            self.broadcast_event('packet_in', packet_data)
    
    def on_flow_removed(self, flow_data: Dict[str, Any]):
        """Handle flow removed event"""
        self.broadcast_event('flow_removed', flow_data)
    
    def on_port_status(self, port_data: Dict[str, Any]):
        """Handle port status change event"""
        self.broadcast_event('port_status', port_data)
    
    # ========================================================================
    # ML and Traffic Event Handlers
    # ========================================================================
    
    def on_ml_prediction(self, prediction_data: Dict[str, Any]):
        """Handle ML prediction event"""
        self.broadcast_event('ml_prediction', prediction_data)
    
    def on_traffic_alert(self, alert_data: Dict[str, Any]):
        """Handle traffic alert event"""
        self.broadcast_event('traffic_alert', alert_data)
    
    def on_topology_change(self, change_data: Dict[str, Any]):
        """Handle comprehensive topology change event"""
        self.broadcast_event('topology_change', change_data)
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def _should_broadcast_packet_event(self, packet_data: Dict[str, Any]) -> bool:
        """
        Determine if packet event should be broadcasted
        
        This helps prevent spam from high-frequency packet events
        """
        # For now, broadcast all packet events
        # In the future, we could add filtering based on:
        # - Packet type
        # - Rate limiting
        # - Client subscriptions
        return True
    
    def get_client_count(self) -> int:
        """Get number of connected WebSocket clients"""
        with self.clients_lock:
            return len(self.rpc_clients)
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """Get event broadcasting statistics"""
        return {
            'connected_clients': self.get_client_count(),
            'event_counters': self.event_counters.copy(),
            'max_connections': self.config.websocket_max_connections,
            'heartbeat_interval': self.config.websocket_heartbeat_interval
        }
    
    def send_custom_event(self, event_type: str, event_data: Dict[str, Any]):
        """Send custom event (for testing or special purposes)"""
        self.broadcast_event(event_type, event_data)

    # ========================================================================
    # P4Runtime Event Handlers
    # ========================================================================

    def broadcast_packet_event(self, packet_data):
        """Broadcast unified packet-in events from any backend"""
        try:
            event_data = {
                'switch_id': packet_data.switch_id,
                'switch_type': packet_data.switch_type.value,
                'packet_size': len(packet_data.packet),
                'metadata': packet_data.metadata,
                'timestamp': time.time()
            }

            # Determine event type based on switch type
            if packet_data.switch_type.value == 'p4runtime':
                event_type = 'p4_packet_in'
                self.event_counters['p4_packet_in'] += 1
            else:
                event_type = 'packet_in'
                self.event_counters['packet_in'] += 1

            self.broadcast_event(event_type, event_data)

        except Exception as e:
            LOG.error(f"Error broadcasting packet event: {e}")

    def broadcast_p4_pipeline_event(self, switch_id: str, pipeline_name: str,
                                   status: str, error_message: str = ""):
        """Broadcast P4 pipeline installation events"""
        try:
            event_data = {
                'switch_id': switch_id,
                'pipeline_name': pipeline_name,
                'status': status,
                'error_message': error_message,
                'timestamp': time.time()
            }

            self.event_counters['p4_pipeline_installed'] += 1
            self.broadcast_event('p4_pipeline_installed', event_data)

        except Exception as e:
            LOG.error(f"Error broadcasting P4 pipeline event: {e}")

    def broadcast_p4_table_event(self, switch_id: str, table_name: str,
                                operation: str, match_fields: Dict[str, Any]):
        """Broadcast P4 table update events"""
        try:
            event_data = {
                'switch_id': switch_id,
                'table_name': table_name,
                'operation': operation,  # 'insert', 'modify', 'delete'
                'match_fields': match_fields,
                'timestamp': time.time()
            }

            self.event_counters['p4_table_updated'] += 1
            self.broadcast_event('p4_table_updated', event_data)

        except Exception as e:
            LOG.error(f"Error broadcasting P4 table event: {e}")

    def broadcast_backend_status_event(self, backend_type: str, status: str,
                                     switch_count: int = 0):
        """Broadcast SDN backend status changes"""
        try:
            event_data = {
                'backend_type': backend_type,
                'status': status,  # 'connected', 'disconnected', 'error'
                'switch_count': switch_count,
                'timestamp': time.time()
            }

            self.broadcast_event('backend_status_change', event_data)

        except Exception as e:
            LOG.error(f"Error broadcasting backend status event: {e}")

    def get_event_statistics(self) -> Dict[str, Any]:
        """Get WebSocket event statistics including P4 events"""
        try:
            return {
                'event_counters': self.event_counters.copy(),
                'active_connections': len(self.rpc_clients),
                'total_events': sum(self.event_counters.values()),
                'timestamp': time.time()
            }
        except Exception as e:
            LOG.error(f"Error getting event statistics: {e}")
            return {'error': str(e)}

    def cleanup(self):
        """Cleanup WebSocket connections"""
        with self.clients_lock:
            for rpc_client in self.rpc_clients:
                try:
                    rpc_client.ws.close()
                except Exception as e:
                    LOG.error(f"Error closing WebSocket: {e}")

            self.rpc_clients.clear()

        LOG.info("WebSocket controller cleanup completed")
