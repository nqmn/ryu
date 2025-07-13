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
P4Runtime Utilities

This module provides utility functions and helper classes for P4Runtime
operations including P4Info parsing, value encoding/decoding, and data
format conversions.
"""

import logging
import struct
import ipaddress
from typing import Dict, Any, Optional, List, Union

try:
    import p4.config.v1.p4info_pb2 as p4info_pb2
    P4RUNTIME_AVAILABLE = True
except ImportError:
    class MockP4Info:
        pass
    p4info_pb2 = MockP4Info()
    P4RUNTIME_AVAILABLE = False

LOG = logging.getLogger(__name__)


class P4RuntimeUtils:
    """Utility functions for P4Runtime operations"""
    
    @staticmethod
    def encode_value(value: Any, bitwidth: int = 32) -> bytes:
        """Encode a value to bytes for P4Runtime"""
        try:
            if isinstance(value, int):
                # Encode integer value
                byte_len = (bitwidth + 7) // 8
                return value.to_bytes(byte_len, byteorder='big')
            
            elif isinstance(value, str):
                # Try to parse as IP address
                try:
                    ip = ipaddress.ip_address(value)
                    return ip.packed
                except ValueError:
                    # Try to parse as hex string
                    if value.startswith('0x'):
                        return bytes.fromhex(value[2:])
                    # Encode as UTF-8
                    return value.encode('utf-8')
            
            elif isinstance(value, bytes):
                return value
            
            elif isinstance(value, (list, tuple)):
                # Encode as concatenated bytes
                result = b''
                for item in value:
                    result += P4RuntimeUtils.encode_value(item, bitwidth)
                return result
            
            else:
                # Convert to string and encode
                return str(value).encode('utf-8')
                
        except Exception as e:
            LOG.error(f"Failed to encode value {value}: {e}")
            return b''
    
    @staticmethod
    def decode_value(data: bytes, value_type: str = 'int') -> Any:
        """Decode bytes to a value"""
        try:
            if value_type == 'int':
                return int.from_bytes(data, byteorder='big')
            
            elif value_type == 'ipv4':
                if len(data) == 4:
                    return str(ipaddress.IPv4Address(data))
                return data.hex()
            
            elif value_type == 'ipv6':
                if len(data) == 16:
                    return str(ipaddress.IPv6Address(data))
                return data.hex()
            
            elif value_type == 'mac':
                if len(data) == 6:
                    return ':'.join(f'{b:02x}' for b in data)
                return data.hex()
            
            elif value_type == 'hex':
                return '0x' + data.hex()
            
            elif value_type == 'string':
                return data.decode('utf-8', errors='ignore')
            
            else:
                # Default to hex representation
                return '0x' + data.hex()
                
        except Exception as e:
            LOG.error(f"Failed to decode value {data}: {e}")
            return data.hex()
    
    @staticmethod
    def table_entry_to_dict(table_entry, p4info_helper: Optional['P4InfoHelper'] = None) -> Dict[str, Any]:
        """Convert P4Runtime table entry to dictionary"""
        try:
            entry_dict = {
                'table_id': table_entry.table_id,
                'priority': table_entry.priority,
                'match_fields': {},
                'action': {},
                'metadata': {}
            }
            
            # Extract match fields
            for match in table_entry.match:
                field_name = f"field_{match.field_id}"
                if p4info_helper:
                    field_name = p4info_helper.get_match_field_name(table_entry.table_id, match.field_id)
                
                if match.HasField('exact'):
                    entry_dict['match_fields'][field_name] = P4RuntimeUtils.decode_value(match.exact.value)
                elif match.HasField('lpm'):
                    entry_dict['match_fields'][field_name] = {
                        'value': P4RuntimeUtils.decode_value(match.lpm.value),
                        'prefix_len': match.lpm.prefix_len
                    }
                elif match.HasField('ternary'):
                    entry_dict['match_fields'][field_name] = {
                        'value': P4RuntimeUtils.decode_value(match.ternary.value),
                        'mask': P4RuntimeUtils.decode_value(match.ternary.mask)
                    }
            
            # Extract action
            if table_entry.action.HasField('action'):
                action = table_entry.action.action
                action_name = f"action_{action.action_id}"
                if p4info_helper:
                    action_name = p4info_helper.get_action_name(action.action_id)
                
                entry_dict['action'] = {
                    'name': action_name,
                    'params': {}
                }
                
                for param in action.params:
                    param_name = f"param_{param.param_id}"
                    if p4info_helper:
                        param_name = p4info_helper.get_action_param_name(action.action_id, param.param_id)
                    
                    entry_dict['action']['params'][param_name] = P4RuntimeUtils.decode_value(param.value)
            
            return entry_dict
            
        except Exception as e:
            LOG.error(f"Failed to convert table entry to dict: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def format_match_key(match_fields: Dict[str, Any]) -> str:
        """Format match fields into a readable key"""
        try:
            key_parts = []
            for field, value in match_fields.items():
                if isinstance(value, dict):
                    if 'prefix_len' in value:
                        key_parts.append(f"{field}={value['value']}/{value['prefix_len']}")
                    elif 'mask' in value:
                        key_parts.append(f"{field}={value['value']}&{value['mask']}")
                    else:
                        key_parts.append(f"{field}={value}")
                else:
                    key_parts.append(f"{field}={value}")
            
            return ', '.join(key_parts)
            
        except Exception as e:
            LOG.error(f"Failed to format match key: {e}")
            return str(match_fields)


class P4InfoHelper:
    """Helper class for P4Info operations"""
    
    def __init__(self, p4info):
        self.p4info = p4info
        self._table_name_to_id = {}
        self._table_id_to_name = {}
        self._action_name_to_id = {}
        self._action_id_to_name = {}
        self._match_field_cache = {}
        self._action_param_cache = {}
        
        if P4RUNTIME_AVAILABLE:
            self._build_caches()
    
    def _build_caches(self):
        """Build lookup caches from P4Info"""
        try:
            # Build table caches
            for table in self.p4info.tables:
                self._table_name_to_id[table.preamble.name] = table.preamble.id
                self._table_id_to_name[table.preamble.id] = table.preamble.name
                
                # Cache match fields for this table
                self._match_field_cache[table.preamble.id] = {}
                for match_field in table.match_fields:
                    self._match_field_cache[table.preamble.id][match_field.id] = match_field.name
            
            # Build action caches
            for action in self.p4info.actions:
                self._action_name_to_id[action.preamble.name] = action.preamble.id
                self._action_id_to_name[action.preamble.id] = action.preamble.name
                
                # Cache action parameters
                self._action_param_cache[action.preamble.id] = {}
                for param in action.params:
                    self._action_param_cache[action.preamble.id][param.id] = param.name
            
            LOG.info(f"P4Info cache built: {len(self._table_name_to_id)} tables, {len(self._action_name_to_id)} actions")
            
        except Exception as e:
            LOG.error(f"Failed to build P4Info caches: {e}")
    
    def get_table_id(self, table_name: str) -> int:
        """Get table ID by name"""
        return self._table_name_to_id.get(table_name, 0)
    
    def get_table_name(self, table_id: int) -> str:
        """Get table name by ID"""
        return self._table_id_to_name.get(table_id, f"table_{table_id}")
    
    def get_action_id(self, action_name: str) -> int:
        """Get action ID by name"""
        return self._action_name_to_id.get(action_name, 0)
    
    def get_action_name(self, action_id: int) -> str:
        """Get action name by ID"""
        return self._action_id_to_name.get(action_id, f"action_{action_id}")
    
    def get_match_field_id(self, table_name: str, field_name: str) -> int:
        """Get match field ID by table and field name"""
        table_id = self.get_table_id(table_name)
        if table_id in self._match_field_cache:
            for field_id, name in self._match_field_cache[table_id].items():
                if name == field_name:
                    return field_id
        return 0
    
    def get_match_field_name(self, table_id: int, field_id: int) -> str:
        """Get match field name by table and field ID"""
        if table_id in self._match_field_cache:
            return self._match_field_cache[table_id].get(field_id, f"field_{field_id}")
        return f"field_{field_id}"
    
    def get_action_param_id(self, action_name: str, param_name: str) -> int:
        """Get action parameter ID by action and parameter name"""
        action_id = self.get_action_id(action_name)
        if action_id in self._action_param_cache:
            for param_id, name in self._action_param_cache[action_id].items():
                if name == param_name:
                    return param_id
        return 0
    
    def get_action_param_name(self, action_id: int, param_id: int) -> str:
        """Get action parameter name by action and parameter ID"""
        if action_id in self._action_param_cache:
            return self._action_param_cache[action_id].get(param_id, f"param_{param_id}")
        return f"param_{param_id}"
    
    def get_packet_metadata_id(self, metadata_name: str) -> int:
        """Get packet metadata ID by name"""
        # Simplified implementation - real version would parse packet metadata from P4Info
        return 0
    
    def list_tables(self) -> List[Dict[str, Any]]:
        """List all tables with their information"""
        tables = []
        for table_id, table_name in self._table_id_to_name.items():
            table_info = {
                'id': table_id,
                'name': table_name,
                'match_fields': list(self._match_field_cache.get(table_id, {}).values())
            }
            tables.append(table_info)
        return tables
    
    def list_actions(self) -> List[Dict[str, Any]]:
        """List all actions with their information"""
        actions = []
        for action_id, action_name in self._action_id_to_name.items():
            action_info = {
                'id': action_id,
                'name': action_name,
                'params': list(self._action_param_cache.get(action_id, {}).values())
            }
            actions.append(action_info)
        return actions
