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
Middleware REST API Controller

This module provides the REST API endpoints for the middleware functionality
including topology management, traffic generation, flow control, monitoring,
and AI/ML integration.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from ryu.app.wsgi import ControllerBase, Response, route
from ryu.lib import dpid as dpid_lib

from .utils import ResponseFormatter, TopologyValidator, NetworkUtils

LOG = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class MiddlewareRestController(ControllerBase):
    """
    REST API Controller for Middleware
    
    Provides v2.0 API endpoints for:
    - Topology management (/v2.0/topology/*)
    - Host operations (/v2.0/host/*)
    - Traffic generation (/v2.0/traffic/*)
    - Flow management (/v2.0/flow/*)
    - Statistics (/v2.0/stats/*)
    - ML integration (/v2.0/ml/*)
    """
    
    def __init__(self, req, link, data, **config):
        super(MiddlewareRestController, self).__init__(req, link, data, **config)
        
        # Get middleware components from data
        self.middleware_app = data['middleware_app']
        self.mininet_bridge = data['mininet_bridge']
        self.traffic_generator = data['traffic_generator']
        self.monitoring = data['monitoring']
        self.ml_integration = data['ml_integration']
        self.switch_manager = data['switch_manager']
        self.config = data['config']
    
    def _create_response(self, data: Any, status: int = 200) -> Response:
        """Create JSON response"""
        if isinstance(data, dict) and 'status' in data:
            # Already formatted response
            body = json.dumps(data, cls=DateTimeEncoder)
        else:
            # Wrap in success response
            body = json.dumps(ResponseFormatter.success(data), cls=DateTimeEncoder)

        return Response(
            content_type='application/json',
            body=body,
            status=status
        )
    
    def _create_error_response(self, message: str, status: int = 400,
                              error_code: str = "BAD_REQUEST") -> Response:
        """Create error response"""
        body = json.dumps(ResponseFormatter.error(message, error_code), cls=DateTimeEncoder)
        return Response(
            content_type='application/json',
            body=body,
            status=status
        )
    
    def _parse_json_body(self, req) -> Optional[Dict[str, Any]]:
        """Parse JSON request body"""
        try:
            if hasattr(req, 'body') and req.body:
                body_str = req.body.decode('utf-8')
                LOG.debug(f"Parsing JSON body: {body_str}")
                return json.loads(body_str)
            LOG.debug("No body found in request")
            return {}
        except json.JSONDecodeError as e:
            LOG.error(f"Failed to parse JSON body: {e}")
            return None
        except Exception as e:
            LOG.error(f"Unexpected error parsing JSON body: {e}")
            return None
    
    # ========================================================================
    # Topology Management Endpoints
    # ========================================================================
    
    @route('middleware', '/v2.0/topology/view', methods=['GET'])
    @route('middleware', '/topology/view', methods=['GET'])  # Backward compatibility
    def get_topology(self, req, **kwargs):
        """Get current topology information"""
        try:
            topology_info = self.middleware_app.get_topology_info()
            return self._create_response(topology_info)
        except Exception as e:
            LOG.error(f"Failed to get topology: {e}")
            return self._create_error_response(str(e), 500, "TOPOLOGY_ERROR")
    
    @route('middleware', '/v2.0/topology/create', methods=['POST'])
    def create_topology(self, req, **kwargs):
        """Create new topology using Mininet"""
        try:
            topology_def = self._parse_json_body(req)
            if topology_def is None:
                return self._create_error_response("Invalid JSON body", 400)
            
            # Validate topology definition
            is_valid, error_msg = TopologyValidator.validate_topology_definition(topology_def)
            if not is_valid:
                return self._create_error_response(error_msg, 400, "VALIDATION_ERROR")
            
            # Create topology via Mininet bridge
            result = self.mininet_bridge.create_topology(topology_def)
            
            if result.get('success'):
                return self._create_response(result, 201)
            else:
                return self._create_error_response(
                    result.get('error', 'Failed to create topology'),
                    500, "TOPOLOGY_CREATION_ERROR"
                )
                
        except Exception as e:
            LOG.error(f"Failed to create topology: {e}")
            return self._create_error_response(str(e), 500, "TOPOLOGY_ERROR")
    
    @route('middleware', '/v2.0/topology/delete', methods=['DELETE'])
    def delete_topology(self, req, **kwargs):
        """Delete current topology"""
        try:
            result = self.mininet_bridge.delete_topology()
            
            if result.get('success'):
                return self._create_response(result)
            else:
                return self._create_error_response(
                    result.get('error', 'Failed to delete topology'),
                    500, "TOPOLOGY_DELETION_ERROR"
                )
                
        except Exception as e:
            LOG.error(f"Failed to delete topology: {e}")
            return self._create_error_response(str(e), 500, "TOPOLOGY_ERROR")
    
    @route('middleware', '/v2.0/topology/status', methods=['GET'])
    def get_topology_status(self, req, **kwargs):
        """Get topology status"""
        try:
            status = self.mininet_bridge.get_status()
            return self._create_response(status)
        except Exception as e:
            LOG.error(f"Failed to get topology status: {e}")
            return self._create_error_response(str(e), 500, "TOPOLOGY_ERROR")
    
    # ========================================================================
    # Host Management Endpoints
    # ========================================================================
    
    @route('middleware', '/v2.0/host/list', methods=['GET'])
    @route('middleware', '/host/list', methods=['GET'])  # Also handle non-versioned path
    def list_hosts(self, req, **kwargs):
        """List all hosts in the topology"""
        try:
            LOG.info("Host list endpoint called")
            result = self.mininet_bridge.list_hosts()
            LOG.info(f"Mininet bridge returned: {result} (type: {type(result)})")
            
            # Simple approach - if it's already formatted, use it directly
            if isinstance(result, dict) and 'status' in result:
                LOG.info("Returning ResponseFormatter result as JSON")
                body = json.dumps(result, cls=DateTimeEncoder)
                return Response(content_type='application/json', body=body, status=200)
            else:
                # Fallback
                LOG.info("Using fallback response creation")
                return self._create_response(result)
                
        except Exception as e:
            LOG.error(f"Failed to list hosts: {e}")
            import traceback
            LOG.error(f"Traceback: {traceback.format_exc()}")
            return self._create_error_response(str(e), 500, "HOST_ERROR")
    
    @route('middleware', '/v2.0/host/ping', methods=['POST'])
    def ping_hosts(self, req, **kwargs):
        """Perform ping test between hosts"""
        try:
            ping_spec = self._parse_json_body(req)
            if ping_spec is None:
                return self._create_error_response("Invalid JSON body", 400)
            
            # Validate ping specification
            if 'src' not in ping_spec or 'dst' not in ping_spec:
                return self._create_error_response(
                    "Missing src or dst in ping specification", 400, "VALIDATION_ERROR"
                )
            
            result = self.mininet_bridge.ping_hosts(
                ping_spec['src'], 
                ping_spec['dst'],
                ping_spec.get('count', 3)
            )
            
            return self._create_response(result)
            
        except Exception as e:
            LOG.error(f"Failed to ping hosts: {e}")
            return self._create_error_response(str(e), 500, "PING_ERROR")
    
    # ========================================================================
    # Traffic Generation Endpoints
    # ========================================================================
    
    @route('middleware', '/v2.0/traffic/generate', methods=['POST'])
    def generate_traffic(self, req, **kwargs):
        """Generate network traffic"""
        try:
            traffic_spec = self._parse_json_body(req)
            if traffic_spec is None:
                return self._create_error_response("Invalid JSON body", 400)
            
            result = self.traffic_generator.generate_traffic(traffic_spec)
            
            # Handle ResponseFormatter results properly
            if isinstance(result, dict) and 'status' in result:
                if result['status'] == 'success':
                    return self._create_response(result, 201)
                else:
                    # Return error response with appropriate HTTP status code
                    return self._create_response(result, 400)
            else:
                # Fallback for legacy result format
                if isinstance(result, dict) and result.get('success'):
                    return self._create_response(result, 201)
                else:
                    return self._create_error_response(
                        result.get('error', 'Failed to generate traffic') if isinstance(result, dict) else str(result),
                        400, "TRAFFIC_ERROR"
                    )
                
        except Exception as e:
            LOG.error(f"Failed to generate traffic: {e}")
            import traceback
            LOG.error(f"Traceback: {traceback.format_exc()}")
            return self._create_error_response(str(e), 500, "TRAFFIC_ERROR")
    
    @route('middleware', '/v2.0/traffic/status', methods=['GET'])
    def get_traffic_status(self, req, **kwargs):
        """Get active traffic sessions"""
        try:
            status = self.traffic_generator.get_status()
            return self._create_response(status)
        except Exception as e:
            LOG.error(f"Failed to get traffic status: {e}")
            return self._create_error_response(str(e), 500, "TRAFFIC_ERROR")
    
    # ========================================================================
    # Statistics Endpoints
    # ========================================================================
    
    @route('middleware', '/v2.0/stats/flow', methods=['GET'])
    @route('middleware', '/v2.0/stats/flow/{dpid}', methods=['GET'],
           requirements={'dpid': dpid_lib.DPID_PATTERN})
    def get_flow_stats(self, req, **kwargs):
        """Get flow statistics"""
        try:
            dpid = kwargs.get('dpid')
            if dpid:
                dpid = dpid_lib.str_to_dpid(dpid)
            
            stats = self.monitoring.get_flow_stats(dpid)
            return self._create_response(stats)
            
        except Exception as e:
            LOG.error(f"Failed to get flow stats: {e}")
            return self._create_error_response(str(e), 500, "STATS_ERROR")
    
    @route('middleware', '/v2.0/stats/port', methods=['GET'])
    @route('middleware', '/v2.0/stats/port/{dpid}', methods=['GET'],
           requirements={'dpid': dpid_lib.DPID_PATTERN})
    def get_port_stats(self, req, **kwargs):
        """Get port statistics"""
        try:
            dpid = kwargs.get('dpid')
            if dpid:
                dpid = dpid_lib.str_to_dpid(dpid)
            
            stats = self.monitoring.get_port_stats(dpid)
            return self._create_response(stats)
            
        except Exception as e:
            LOG.error(f"Failed to get port stats: {e}")
            return self._create_error_response(str(e), 500, "STATS_ERROR")

    @route('middleware', '/v2.0/stats/packet', methods=['GET'])
    @route('middleware', '/stats/packet', methods=['GET'])  # Backward compatibility
    def get_packet_stats(self, req, **kwargs):
        """Get packet-in statistics"""
        try:
            stats = self.monitoring.get_packet_stats()
            return self._create_response(stats)
        except Exception as e:
            LOG.error(f"Failed to get packet stats: {e}")
            return self._create_error_response(str(e), 500, "STATS_ERROR")

    @route('middleware', '/v2.0/stats/topology', methods=['GET'])
    @route('middleware', '/stats/topology', methods=['GET'])  # Backward compatibility
    def get_topology_stats(self, req, **kwargs):
        """Get topology metrics"""
        try:
            stats = self.monitoring.get_topology_stats()
            return self._create_response(stats)
        except Exception as e:
            LOG.error(f"Failed to get topology stats: {e}")
            return self._create_error_response(str(e), 500, "STATS_ERROR")

    # ========================================================================
    # Flow Management Endpoints
    # ========================================================================

    @route('middleware', '/v2.0/flow/view/{dpid}', methods=['GET'],
           requirements={'dpid': dpid_lib.DPID_PATTERN})
    def view_flows(self, req, **kwargs):
        """View flow tables for a switch"""
        try:
            dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
            flows = self.monitoring.get_flow_table(dpid)
            return self._create_response(flows)
        except Exception as e:
            LOG.error(f"Failed to view flows: {e}")
            return self._create_error_response(str(e), 500, "FLOW_ERROR")

    @route('middleware', '/v2.0/flow/install', methods=['POST'])
    def install_flow(self, req, **kwargs):
        """Install flow rule (supports both OpenFlow and P4Runtime)"""
        try:
            flow_spec = self._parse_json_body(req)
            if flow_spec is None:
                return self._create_error_response("Invalid JSON body", 400)

            # Validate flow specification - support both dpid (OpenFlow) and switch_id (unified)
            switch_id = flow_spec.get('switch_id') or flow_spec.get('dpid')
            if not switch_id:
                return self._create_error_response(
                    "Missing switch_id or dpid in flow specification", 400, "VALIDATION_ERROR"
                )

            # Convert to unified FlowData format
            from .sdn_backends.base import FlowData

            flow_data = FlowData(
                switch_id=str(switch_id),
                switch_type=None,  # Will be detected by switch manager
                priority=flow_spec.get('priority', 1000),
                table_id=flow_spec.get('table_id'),
                match_fields=flow_spec.get('match', {}),
                actions=flow_spec.get('actions', []),
                metadata=flow_spec.get('metadata', {}),
                # OpenFlow specific
                cookie=flow_spec.get('cookie'),
                idle_timeout=flow_spec.get('idle_timeout', 0),
                hard_timeout=flow_spec.get('hard_timeout', 0),
                # P4Runtime specific
                table_name=flow_spec.get('table_name'),
                action_name=flow_spec.get('action_name'),
                action_params=flow_spec.get('action_params', {})
            )

            # Use switch manager for unified flow installation
            import asyncio
            result = asyncio.run(self.switch_manager.install_flow(flow_data))

            if result.get('status') == 'success':
                return self._create_response(result, 201)
            else:
                return self._create_error_response(
                    result.get('message', 'Failed to install flow'),
                    500, result.get('error_code', 'FLOW_ERROR')
                )

        except Exception as e:
            LOG.error(f"Failed to install flow: {e}")
            return self._create_error_response(str(e), 500, "FLOW_ERROR")

    @route('middleware', '/v2.0/flow/delete', methods=['DELETE'])
    def delete_flow(self, req, **kwargs):
        """Delete flow rule (supports both OpenFlow and P4Runtime)"""
        try:
            flow_spec = self._parse_json_body(req)
            if flow_spec is None:
                return self._create_error_response("Invalid JSON body", 400)

            # Validate flow specification
            switch_id = flow_spec.get('switch_id') or flow_spec.get('dpid')
            if not switch_id:
                return self._create_error_response(
                    "Missing switch_id or dpid in flow specification", 400, "VALIDATION_ERROR"
                )

            # Convert to unified FlowData format
            from .sdn_backends.base import FlowData

            flow_data = FlowData(
                switch_id=str(switch_id),
                switch_type=None,  # Will be detected by switch manager
                priority=flow_spec.get('priority', 1000),
                table_id=flow_spec.get('table_id'),
                match_fields=flow_spec.get('match', {}),
                actions=flow_spec.get('actions', []),
                metadata=flow_spec.get('metadata', {}),
                # P4Runtime specific
                table_name=flow_spec.get('table_name'),
                action_name=flow_spec.get('action_name'),
                action_params=flow_spec.get('action_params', {})
            )

            # Use switch manager for unified flow deletion
            import asyncio
            result = asyncio.run(self.switch_manager.delete_flow(flow_data))

            if result.get('status') == 'success':
                return self._create_response(result)
            else:
                return self._create_error_response(
                    result.get('message', 'Failed to delete flow'),
                    500, result.get('error_code', 'FLOW_ERROR')
                )

        except Exception as e:
            LOG.error(f"Failed to delete flow: {e}")
            return self._create_error_response(str(e), 500, "FLOW_ERROR")

    # ========================================================================
    # ML Integration Endpoints
    # ========================================================================

    @route('middleware', '/v2.0/ml/infer', methods=['POST'])
    def ml_infer(self, req, **kwargs):
        """Send data for ML inference"""
        try:
            if not self.config.ml_enabled:
                return self._create_error_response(
                    "ML integration is disabled", 503, "SERVICE_UNAVAILABLE"
                )

            inference_data = self._parse_json_body(req)
            if inference_data is None:
                return self._create_error_response("Invalid JSON body", 400)

            result = self.ml_integration.infer(inference_data)
            return self._create_response(result)

        except Exception as e:
            LOG.error(f"Failed ML inference: {e}")
            return self._create_error_response(str(e), 500, "ML_ERROR")

    @route('middleware', '/v2.0/ml/models', methods=['GET'])
    def list_ml_models(self, req, **kwargs):
        """List available ML models"""
        try:
            if not self.config.ml_enabled:
                return self._create_error_response(
                    "ML integration is disabled", 503, "SERVICE_UNAVAILABLE"
                )

            models = self.ml_integration.list_models()
            return self._create_response(models)

        except Exception as e:
            LOG.error(f"Failed to list ML models: {e}")
            return self._create_error_response(str(e), 500, "ML_ERROR")

    @route('middleware', '/v2.0/ml/alert', methods=['POST'])
    def configure_ml_alert(self, req, **kwargs):
        """Configure ML-based alerts"""
        try:
            if not self.config.ml_enabled:
                return self._create_error_response(
                    "ML integration is disabled", 503, "SERVICE_UNAVAILABLE"
                )

            alert_config = self._parse_json_body(req)
            if alert_config is None:
                return self._create_error_response("Invalid JSON body", 400)

            result = self.ml_integration.configure_alert(alert_config)

            if result.get('success'):
                return self._create_response(result, 201)
            else:
                return self._create_error_response(
                    result.get('error', 'Failed to configure alert'),
                    500, "ML_ERROR"
                )

        except Exception as e:
            LOG.error(f"Failed to configure ML alert: {e}")
            return self._create_error_response(str(e), 500, "ML_ERROR")

    # ========================================================================
    # Health Check Endpoint
    # ========================================================================

    @route('middleware', '/v2.0/health', methods=['GET'])
    @route('middleware', '/health', methods=['GET'])  # Backward compatibility
    def health_check(self, req, **kwargs):
        """Health check endpoint"""
        try:
            health_status = {
                'middleware': 'healthy',
                'mininet': self.mininet_bridge.is_healthy(),
                'traffic_generator': self.traffic_generator.is_healthy(),
                'monitoring': self.monitoring.is_healthy(),
                'ml_integration': self.ml_integration.is_healthy() if self.config.ml_enabled else 'disabled',
                'sdn_backends': self.middleware_app.get_backend_status(),
                'timestamp': self.monitoring.get_current_timestamp()
            }

            return self._create_response(health_status)

        except Exception as e:
            LOG.error(f"Health check failed: {e}")
            return self._create_error_response(str(e), 500, "HEALTH_CHECK_ERROR")

    # ========================================================================
    # P4Runtime Specific Endpoints
    # ========================================================================

    @route('middleware', '/v2.0/p4/switches', methods=['GET'])
    @route('middleware', '/p4/switches', methods=['GET'])  # Backward compatibility
    def list_p4_switches(self, req, **kwargs):
        """List all P4Runtime switches"""
        try:
            import asyncio
            result = asyncio.run(self.switch_manager.list_all_switches())

            # Filter for P4Runtime switches only
            if result.get('status') == 'success':
                all_switches = result.get('data', {}).get('switches', [])
                p4_switches = [s for s in all_switches if s.get('switch_type') == 'p4runtime']

                return self._create_response({
                    'switches': p4_switches,
                    'total_count': len(p4_switches)
                })
            else:
                return self._create_error_response(
                    result.get('message', 'Failed to list switches'),
                    500, result.get('error_code', 'P4_ERROR')
                )

        except Exception as e:
            LOG.error(f"Failed to list P4Runtime switches: {e}")
            return self._create_error_response(str(e), 500, "P4_ERROR")

    @route('middleware', '/v2.0/p4/pipeline/install', methods=['POST'])
    def install_p4_pipeline(self, req, **kwargs):
        """Install P4 pipeline on a switch"""
        try:
            pipeline_spec = self._parse_json_body(req)
            if pipeline_spec is None:
                return self._create_error_response("Invalid JSON body", 400)

            # Validate required fields
            required_fields = ['switch_id', 'pipeline_name', 'p4info_path', 'config_path']
            for field in required_fields:
                if field not in pipeline_spec:
                    return self._create_error_response(
                        f"Missing {field} in pipeline specification", 400, "VALIDATION_ERROR"
                    )

            # Get P4Runtime backend
            from .sdn_backends.base import SwitchType
            p4_backend = self.switch_manager.get_backend(SwitchType.P4RUNTIME)
            if not p4_backend:
                return self._create_error_response(
                    "P4Runtime backend not available", 500, "BACKEND_NOT_AVAILABLE"
                )

            # Install pipeline
            import asyncio
            result = asyncio.run(p4_backend.install_pipeline(
                pipeline_spec['switch_id'],
                pipeline_spec['pipeline_name'],
                pipeline_spec['p4info_path'],
                pipeline_spec['config_path']
            ))

            if result.get('status') == 'success':
                return self._create_response(result, 201)
            else:
                return self._create_error_response(
                    result.get('message', 'Failed to install pipeline'),
                    500, result.get('error_code', 'P4_PIPELINE_ERROR')
                )

        except Exception as e:
            LOG.error(f"Failed to install P4 pipeline: {e}")
            return self._create_error_response(str(e), 500, "P4_PIPELINE_ERROR")

    @route('middleware', '/v2.0/p4/pipeline/status', methods=['GET'])
    def get_p4_pipeline_status(self, req, **kwargs):
        """Get P4 pipeline status for all switches"""
        try:
            # Get P4Runtime backend
            from .sdn_backends.base import SwitchType
            p4_backend = self.switch_manager.get_backend(SwitchType.P4RUNTIME)
            if not p4_backend:
                return self._create_error_response(
                    "P4Runtime backend not available", 500, "BACKEND_NOT_AVAILABLE"
                )

            # Get pipeline manager and status
            pipeline_manager = p4_backend.get_pipeline_manager()
            summary = pipeline_manager.get_pipeline_summary()

            return self._create_response(summary)

        except Exception as e:
            LOG.error(f"Failed to get P4 pipeline status: {e}")
            return self._create_error_response(str(e), 500, "P4_PIPELINE_ERROR")

    @route('middleware', '/v2.0/p4/table/write', methods=['POST'])
    def write_p4_table_entry(self, req, **kwargs):
        """Write P4 table entry (alias for unified flow install with P4 fields)"""
        try:
            table_spec = self._parse_json_body(req)
            if table_spec is None:
                return self._create_error_response("Invalid JSON body", 400)

            # Ensure P4-specific fields are present
            if 'table_name' not in table_spec or 'action_name' not in table_spec:
                return self._create_error_response(
                    "P4 table entries require table_name and action_name", 400, "VALIDATION_ERROR"
                )

            # Use the unified flow install endpoint
            return self.install_flow(req, **kwargs)

        except Exception as e:
            LOG.error(f"Failed to write P4 table entry: {e}")
            return self._create_error_response(str(e), 500, "P4_TABLE_ERROR")

    @route('middleware', '/v2.0/p4/table/read/{switch_id}', methods=['GET'])
    def read_p4_table_entries(self, req, **kwargs):
        """Read P4 table entries from a switch"""
        try:
            switch_id = kwargs.get('switch_id')
            if not switch_id:
                return self._create_error_response("Missing switch_id", 400, "VALIDATION_ERROR")

            # Use switch manager to get flow stats (which includes table entries for P4)
            import asyncio
            result = asyncio.run(self.switch_manager.get_flow_stats(switch_id))

            if result.get('status') == 'success':
                return self._create_response(result)
            else:
                return self._create_error_response(
                    result.get('message', 'Failed to read table entries'),
                    500, result.get('error_code', 'P4_TABLE_ERROR')
                )

        except Exception as e:
            LOG.error(f"Failed to read P4 table entries: {e}")
            return self._create_error_response(str(e), 500, "P4_TABLE_ERROR")

    # ========================================================================
    # Controller Management Endpoints
    # ========================================================================

    @route('middleware', '/v2.0/controllers/register', methods=['POST'])
    def register_controller(self, req, **kwargs):
        """Register a new SDN controller"""
        try:
            controller_data = self._parse_json_body(req)
            if controller_data is None:
                return self._create_error_response("Invalid JSON body", 400)

            # Validate required fields
            if 'config' not in controller_data:
                return self._create_error_response(
                    "Missing controller config", 400, "VALIDATION_ERROR"
                )

            config = controller_data['config']
            required_fields = ['controller_id', 'controller_type', 'name']
            for field in required_fields:
                if field not in config:
                    return self._create_error_response(
                        f"Missing required field: {field}", 400, "VALIDATION_ERROR"
                    )

            # Get controller manager
            controller_manager = getattr(self.middleware_app, 'controller_manager', None)
            if not controller_manager:
                return self._create_error_response(
                    "Controller manager not available", 503, "SERVICE_UNAVAILABLE"
                )

            # Register controller
            import asyncio
            from .models.controller_schemas import ControllerConfig

            try:
                controller_config = ControllerConfig(**config)
            except Exception as e:
                return self._create_error_response(
                    f"Invalid controller configuration: {e}", 400, "VALIDATION_ERROR"
                )

            auto_start = controller_data.get('auto_start', True)
            result = asyncio.run(controller_manager.register_controller(controller_config, auto_start))

            if result.get('status') == 'success':
                return self._create_response(result, 201)
            else:
                return self._create_error_response(
                    result.get('message', 'Failed to register controller'),
                    400, result.get('error_code', 'REGISTRATION_FAILED')
                )

        except Exception as e:
            LOG.error(f"Failed to register controller: {e}")
            return self._create_error_response(str(e), 500, "REGISTRATION_ERROR")

    @route('middleware', '/v2.0/controllers/deregister/{controller_id}', methods=['DELETE'])
    def deregister_controller(self, req, **kwargs):
        """Deregister an SDN controller"""
        try:
            controller_id = kwargs.get('controller_id')
            if not controller_id:
                return self._create_error_response("Missing controller_id", 400, "VALIDATION_ERROR")

            # Get controller manager
            controller_manager = getattr(self.middleware_app, 'controller_manager', None)
            if not controller_manager:
                return self._create_error_response(
                    "Controller manager not available", 503, "SERVICE_UNAVAILABLE"
                )

            # Deregister controller
            import asyncio
            result = asyncio.run(controller_manager.deregister_controller(controller_id))

            if result.get('status') == 'success':
                return self._create_response(result)
            else:
                return self._create_error_response(
                    result.get('message', 'Failed to deregister controller'),
                    400, result.get('error_code', 'DEREGISTRATION_FAILED')
                )

        except Exception as e:
            LOG.error(f"Failed to deregister controller: {e}")
            return self._create_error_response(str(e), 500, "DEREGISTRATION_ERROR")

    @route('middleware', '/v2.0/controllers/list', methods=['GET'])
    @route('middleware', '/controllers/list', methods=['GET'])  # Backward compatibility
    def list_controllers(self, req, **kwargs):
        """List all registered controllers"""
        try:
            # Get controller manager
            controller_manager = getattr(self.middleware_app, 'controller_manager', None)
            if not controller_manager:
                return self._create_error_response(
                    "Controller manager not available", 503, "SERVICE_UNAVAILABLE"
                )

            # List controllers
            result = controller_manager.list_controllers()

            if result.get('status') == 'success':
                return self._create_response(result)
            else:
                return self._create_error_response(
                    result.get('message', 'Failed to list controllers'),
                    500, result.get('error_code', 'LIST_FAILED')
                )

        except Exception as e:
            LOG.error(f"Failed to list controllers: {e}")
            return self._create_error_response(str(e), 500, "LIST_ERROR")

    @route('middleware', '/v2.0/controllers/health/{controller_id}', methods=['GET'])
    def get_controller_health(self, req, **kwargs):
        """Get health status of a specific controller"""
        try:
            controller_id = kwargs.get('controller_id')
            if not controller_id:
                return self._create_error_response("Missing controller_id", 400, "VALIDATION_ERROR")

            # Get controller manager
            controller_manager = getattr(self.middleware_app, 'controller_manager', None)
            if not controller_manager:
                return self._create_error_response(
                    "Controller manager not available", 503, "SERVICE_UNAVAILABLE"
                )

            # Get controller
            with controller_manager.controller_lock:
                controller = controller_manager.controllers.get(controller_id)
                controller_info = controller_manager.controller_info.get(controller_id)

            if not controller or not controller_info:
                return self._create_error_response(
                    f"Controller {controller_id} not found", 404, "CONTROLLER_NOT_FOUND"
                )

            # Get health status
            import asyncio
            health = asyncio.run(controller.health_check())

            health_data = {
                'controller_id': controller_id,
                'overall_health': 'healthy' if health.is_healthy else 'unhealthy',
                'checks': [{
                    'controller_id': controller_id,
                    'status': 'healthy' if health.is_healthy else 'unhealthy',
                    'response_time_ms': health.response_time_ms,
                    'timestamp': health.last_check.isoformat() if health.last_check else None,
                    'details': health.details,
                    'error_message': health.last_error
                }],
                'summary': {
                    'uptime_seconds': health.uptime_seconds,
                    'error_count': health.error_count,
                    'last_error': health.last_error,
                    'connected': controller.is_connected()
                }
            }

            return self._create_response(health_data)

        except Exception as e:
            LOG.error(f"Failed to get controller health: {e}")
            return self._create_error_response(str(e), 500, "HEALTH_CHECK_ERROR")

    @route('middleware', '/v2.0/switches/map', methods=['POST'])
    def map_switch_to_controller(self, req, **kwargs):
        """Map a switch to a controller with optional backups"""
        try:
            mapping_data = self._parse_json_body(req)
            if mapping_data is None:
                return self._create_error_response("Invalid JSON body", 400)

            # Validate required fields
            required_fields = ['switch_id', 'primary_controller']
            for field in required_fields:
                if field not in mapping_data:
                    return self._create_error_response(
                        f"Missing required field: {field}", 400, "VALIDATION_ERROR"
                    )

            # Get controller manager
            controller_manager = getattr(self.middleware_app, 'controller_manager', None)
            if not controller_manager:
                return self._create_error_response(
                    "Controller manager not available", 503, "SERVICE_UNAVAILABLE"
                )

            # Map switch
            import asyncio
            result = asyncio.run(controller_manager.map_switch_to_controller(
                mapping_data['switch_id'],
                mapping_data['primary_controller'],
                mapping_data.get('backup_controllers', [])
            ))

            if result.get('status') == 'success':
                return self._create_response(result, 201)
            else:
                return self._create_error_response(
                    result.get('message', 'Failed to map switch'),
                    400, result.get('error_code', 'MAPPING_FAILED')
                )

        except Exception as e:
            LOG.error(f"Failed to map switch: {e}")
            return self._create_error_response(str(e), 500, "MAPPING_ERROR")

    @route('middleware', '/v2.0/switches/mappings', methods=['GET'])
    def get_switch_mappings(self, req, **kwargs):
        """Get all switch-to-controller mappings"""
        try:
            # Get controller manager
            controller_manager = getattr(self.middleware_app, 'controller_manager', None)
            if not controller_manager:
                return self._create_error_response(
                    "Controller manager not available", 503, "SERVICE_UNAVAILABLE"
                )

            # Get mappings
            result = controller_manager.get_switch_mappings()

            if result.get('status') == 'success':
                return self._create_response(result)
            else:
                return self._create_error_response(
                    result.get('message', 'Failed to get switch mappings'),
                    500, result.get('error_code', 'MAPPING_LIST_FAILED')
                )

        except Exception as e:
            LOG.error(f"Failed to get switch mappings: {e}")
            return self._create_error_response(str(e), 500, "MAPPING_LIST_ERROR")

    @route('middleware', '/v2.0/switches/failover', methods=['POST'])
    def perform_switch_failover(self, req, **kwargs):
        """Perform manual failover for a switch"""
        try:
            failover_data = self._parse_json_body(req)
            if failover_data is None:
                return self._create_error_response("Invalid JSON body", 400)

            # Validate required fields
            if 'switch_id' not in failover_data:
                return self._create_error_response(
                    "Missing required field: switch_id", 400, "VALIDATION_ERROR"
                )

            switch_id = failover_data['switch_id']
            target_controller = failover_data.get('target_controller')

            # Get controller manager
            controller_manager = getattr(self.middleware_app, 'controller_manager', None)
            if not controller_manager:
                return self._create_error_response(
                    "Controller manager not available", 503, "SERVICE_UNAVAILABLE"
                )

            # Get current mapping
            with controller_manager.mapping_lock:
                mapping = controller_manager.switch_mappings.get(switch_id)

            if not mapping:
                return self._create_error_response(
                    f"Switch {switch_id} not mapped to any controller", 404, "MAPPING_NOT_FOUND"
                )

            # Determine target controller
            if target_controller:
                # Validate target controller exists and is available
                with controller_manager.controller_lock:
                    if target_controller not in controller_manager.controllers:
                        return self._create_error_response(
                            f"Target controller {target_controller} not found", 404, "CONTROLLER_NOT_FOUND"
                        )

                    controller_info = controller_manager.controller_info.get(target_controller)
                    if not controller_info or controller_info.health_status != 'healthy':
                        return self._create_error_response(
                            f"Target controller {target_controller} is not healthy", 400, "CONTROLLER_UNHEALTHY"
                        )
            else:
                # Find next available backup
                target_controller = None
                for backup_id in mapping.backup_controllers:
                    with controller_manager.controller_lock:
                        if (backup_id in controller_manager.controller_info and
                            controller_manager.controller_info[backup_id].health_status == 'healthy'):
                            target_controller = backup_id
                            break

                if not target_controller:
                    return self._create_error_response(
                        f"No healthy backup controller available for switch {switch_id}",
                        400, "NO_BACKUP_AVAILABLE"
                    )

            # Perform failover
            import asyncio
            old_controller = mapping.current_controller

            # Update mapping
            with controller_manager.mapping_lock:
                mapping.current_controller = target_controller
                mapping.failover_count += 1
                mapping.last_updated = datetime.utcnow()

            # Publish failover event
            asyncio.run(controller_manager.event_stream.publish_event(
                'manual_failover',
                'controller_manager',
                'system',
                {
                    'switch_id': switch_id,
                    'old_controller': old_controller,
                    'new_controller': target_controller,
                    'failover_count': mapping.failover_count,
                    'manual': True
                },
                priority=3
            ))

            controller_manager.stats['failover_count'] += 1

            return self._create_response({
                'success': True,
                'message': f'Switch {switch_id} failed over successfully',
                'old_controller': old_controller,
                'new_controller': target_controller,
                'switch_id': switch_id,
                'failover_count': mapping.failover_count
            })

        except Exception as e:
            LOG.error(f"Failed to perform switch failover: {e}")
            return self._create_error_response(str(e), 500, "FAILOVER_ERROR")
