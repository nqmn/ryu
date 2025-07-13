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
Middleware Utilities

This module provides common utilities, configuration management, and helper
functions for the middleware API.
"""

import os
import time
import json
import yaml
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from pathlib import Path

LOG = logging.getLogger(__name__)


@dataclass
class MiddlewareConfig:
    """Configuration class for middleware settings"""
    
    # Mininet configuration
    mininet_enabled: bool = True
    mininet_python_path: str = "/usr/bin/python3"
    mininet_cleanup_on_exit: bool = True
    mininet_timeout: int = 30
    
    # Traffic generation configuration
    traffic_tools: List[str] = field(default_factory=lambda: ["hping3", "iperf3", "scapy"])
    traffic_max_concurrent: int = 10
    traffic_timeout: int = 60
    
    # ML integration configuration
    ml_providers: List[Dict[str, Any]] = field(default_factory=list)
    ml_timeout: int = 30
    ml_enabled: bool = False
    
    # WebSocket configuration
    websocket_max_connections: int = 100
    websocket_heartbeat_interval: int = 30
    
    # API configuration
    api_rate_limit: int = 100  # requests per minute
    api_timeout: int = 30
    
    # Monitoring configuration
    monitoring_enabled: bool = True
    monitoring_interval: int = 5  # seconds
    stats_retention_time: int = 3600  # seconds

    # SDN Backend configuration
    sdn_backends: Dict[str, Any] = field(default_factory=lambda: {
        'openflow': {
            'enabled': True,
            'controller_host': 'localhost',
            'controller_port': 6653
        },
        'p4runtime': {
            'enabled': False,
            'switches': []
        }
    })

    # P4Runtime specific configuration
    p4runtime_enabled: bool = False
    p4runtime_switches: List[Dict[str, Any]] = field(default_factory=list)
    p4runtime_pipeline_directory: str = "./pipelines"
    p4runtime_connection_timeout: int = 30

    # Event stream configuration
    event_stream: Dict[str, Any] = field(default_factory=lambda: {
        'max_queue_size': 10000,
        'max_history_size': 1000,
        'auto_deactivate_failed_subscribers': True
    })

    # Controller manager configuration
    controller_manager: Dict[str, Any] = field(default_factory=lambda: {
        'health_check_interval': 30,
        'health_check_timeout': 5,
        'max_health_failures': 3
    })
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration values"""
        if self.mininet_timeout <= 0:
            raise ValueError("mininet_timeout must be positive")

        if self.traffic_max_concurrent <= 0:
            raise ValueError("traffic_max_concurrent must be positive")

        if self.websocket_max_connections <= 0:
            raise ValueError("websocket_max_connections must be positive")

        # Validate P4Runtime configuration
        if self.p4runtime_enabled:
            if not self.p4runtime_switches and not self.sdn_backends.get('p4runtime', {}).get('switches'):
                raise ValueError("P4Runtime enabled but no switches configured")

        # Validate SDN backend configuration
        if not any(backend.get('enabled', False) for backend in self.sdn_backends.values()):
            raise ValueError("At least one SDN backend must be enabled")
    
    @classmethod
    def from_file(cls, config_path: str) -> 'MiddlewareConfig':
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Extract middleware section if it exists
            middleware_config = config_data.get('middleware', {})

            # Handle legacy P4Runtime configuration
            if 'p4runtime' in config_data:
                p4_config = config_data['p4runtime']
                middleware_config['p4runtime_enabled'] = p4_config.get('enabled', False)
                middleware_config['p4runtime_switches'] = p4_config.get('switches', [])
                middleware_config['p4runtime_pipeline_directory'] = p4_config.get('pipeline_directory', './pipelines')

                # Update sdn_backends configuration
                if 'sdn_backends' not in middleware_config:
                    middleware_config['sdn_backends'] = {}
                middleware_config['sdn_backends']['p4runtime'] = p4_config

            return cls(**middleware_config)
            
        except FileNotFoundError:
            LOG.warning(f"Config file {config_path} not found, using defaults")
            return cls()
        except Exception as e:
            LOG.error(f"Failed to load config from {config_path}: {e}")
            return cls()


class ResponseFormatter:
    """Utility class for formatting API responses"""
    
    @staticmethod
    def success(data: Any, message: str = "Success") -> Dict[str, Any]:
        """Format successful response"""
        return {
            'status': 'success',
            'message': message,
            'data': data,
            'timestamp': time.time()
        }
    
    @staticmethod
    def error(message: str, error_code: str = "UNKNOWN_ERROR", 
              details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Format error response"""
        response = {
            'status': 'error',
            'message': message,
            'error_code': error_code,
            'timestamp': time.time()
        }
        
        if details:
            response['details'] = details
        
        return response
    
    @staticmethod
    def validation_error(field: str, message: str) -> Dict[str, Any]:
        """Format validation error response"""
        return ResponseFormatter.error(
            message=f"Validation error: {message}",
            error_code="VALIDATION_ERROR",
            details={'field': field}
        )


class TopologyValidator:
    """Utility class for validating topology definitions"""
    
    @staticmethod
    def validate_topology_definition(topology: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate topology definition
        
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            # Check required fields
            required_fields = ['name', 'switches', 'hosts', 'links']
            for field in required_fields:
                if field not in topology:
                    return False, f"Missing required field: {field}"
            
            # Validate switches
            if not isinstance(topology['switches'], list):
                return False, "switches must be a list"
            
            # Validate hosts
            if not isinstance(topology['hosts'], list):
                return False, "hosts must be a list"
            
            # Validate links
            if not isinstance(topology['links'], list):
                return False, "links must be a list"
            
            # Validate switch definitions
            for i, switch in enumerate(topology['switches']):
                if not isinstance(switch, dict):
                    return False, f"Switch {i} must be a dictionary"
                
                if 'name' not in switch:
                    return False, f"Switch {i} missing name field"
            
            # Validate host definitions
            for i, host in enumerate(topology['hosts']):
                if not isinstance(host, dict):
                    return False, f"Host {i} must be a dictionary"
                
                if 'name' not in host:
                    return False, f"Host {i} missing name field"
            
            # Validate link definitions
            for i, link in enumerate(topology['links']):
                if not isinstance(link, dict):
                    return False, f"Link {i} must be a dictionary"
                
                required_link_fields = ['src', 'dst']
                for field in required_link_fields:
                    if field not in link:
                        return False, f"Link {i} missing {field} field"
            
            return True, None
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"


class NetworkUtils:
    """Network utility functions"""
    
    @staticmethod
    def is_valid_ip(ip: str) -> bool:
        """Check if IP address is valid"""
        try:
            import ipaddress
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def is_valid_mac(mac: str) -> bool:
        """Check if MAC address is valid"""
        try:
            # Remove common separators and check length
            clean_mac = mac.replace(':', '').replace('-', '').replace('.', '')
            return len(clean_mac) == 12 and all(c in '0123456789abcdefABCDEF' for c in clean_mac)
        except:
            return False
    
    @staticmethod
    def format_dpid(dpid: Union[int, str]) -> str:
        """Format datapath ID consistently"""
        if isinstance(dpid, int):
            return f"{dpid:016x}"
        elif isinstance(dpid, str):
            # Remove any existing formatting
            clean_dpid = dpid.replace(':', '').replace('-', '')
            try:
                dpid_int = int(clean_dpid, 16)
                return f"{dpid_int:016x}"
            except ValueError:
                return dpid
        else:
            return str(dpid)


class FileUtils:
    """File utility functions"""
    
    @staticmethod
    def ensure_directory(path: str) -> bool:
        """Ensure directory exists, create if necessary"""
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            LOG.error(f"Failed to create directory {path}: {e}")
            return False
    
    @staticmethod
    def load_yaml_file(file_path: str) -> Optional[Dict[str, Any]]:
        """Load YAML file safely"""
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            LOG.error(f"Failed to load YAML file {file_path}: {e}")
            return None
    
    @staticmethod
    def save_yaml_file(data: Dict[str, Any], file_path: str) -> bool:
        """Save data to YAML file"""
        try:
            with open(file_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)
            return True
        except Exception as e:
            LOG.error(f"Failed to save YAML file {file_path}: {e}")
            return False
