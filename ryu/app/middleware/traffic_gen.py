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
Traffic Generation Module

This module provides traffic generation capabilities using various tools
like hping3, iperf3, and Scapy for network testing and simulation.
"""

import subprocess
import logging
import time
import threading
import uuid
from typing import Dict, Any, List, Optional
from threading import Lock

from .utils import MiddlewareConfig, ResponseFormatter

LOG = logging.getLogger(__name__)


class TrafficSession:
    """Represents an active traffic generation session"""
    
    def __init__(self, session_id: str, traffic_spec: Dict[str, Any]):
        self.session_id = session_id
        self.traffic_spec = traffic_spec
        self.start_time = time.time()
        self.process = None
        self.status = "initializing"
        self.results = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            'session_id': self.session_id,
            'traffic_spec': self.traffic_spec,
            'start_time': self.start_time,
            'status': self.status,
            'duration': time.time() - self.start_time,
            'results': self.results
        }


class TrafficGenerator:
    """
    Traffic generation service
    
    Provides functionality for:
    - ICMP traffic generation using hping3
    - TCP/UDP traffic generation using iperf3
    - Custom packet generation using Scapy
    - Session management and monitoring
    """
    
    def __init__(self, config: MiddlewareConfig):
        self.config = config
        self.active_sessions: Dict[str, TrafficSession] = {}
        self.sessions_lock = Lock()
        
        # Check available tools
        self.available_tools = self._check_available_tools()
        
        LOG.info(f"Traffic generator initialized with tools: {self.available_tools}")
    
    def _check_available_tools(self) -> List[str]:
        """Check which traffic generation tools are available"""
        available = []
        
        for tool in self.config.traffic_tools:
            try:
                if tool == "hping3":
                    result = subprocess.run(['which', 'hping3'], 
                                          capture_output=True, timeout=5)
                    if result.returncode == 0:
                        available.append(tool)
                
                elif tool == "iperf3":
                    result = subprocess.run(['which', 'iperf3'], 
                                          capture_output=True, timeout=5)
                    if result.returncode == 0:
                        available.append(tool)
                
                elif tool == "scapy":
                    try:
                        import scapy
                        available.append(tool)
                    except ImportError:
                        pass
                        
            except Exception as e:
                LOG.warning(f"Failed to check tool {tool}: {e}")
        
        return available
    
    def generate_traffic(self, traffic_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate network traffic based on specification
        
        Args:
            traffic_spec: Traffic specification dictionary
            
        Returns:
            Result dictionary with session information
        """
        try:
            # Validate traffic specification
            validation_result = self._validate_traffic_spec(traffic_spec)
            if not validation_result['valid']:
                return ResponseFormatter.error(
                    validation_result['error'],
                    "VALIDATION_ERROR"
                )
            
            # Check session limit
            with self.sessions_lock:
                if len(self.active_sessions) >= self.config.traffic_max_concurrent:
                    return ResponseFormatter.error(
                        "Maximum concurrent sessions reached",
                        "SESSION_LIMIT_EXCEEDED"
                    )
            
            # Create new session
            session_id = str(uuid.uuid4())
            session = TrafficSession(session_id, traffic_spec)
            
            # Start traffic generation
            result = self._start_traffic_generation(session)
            
            if result['success']:
                with self.sessions_lock:
                    self.active_sessions[session_id] = session
                
                return ResponseFormatter.success({
                    'session_id': session_id,
                    'status': 'started',
                    'traffic_type': traffic_spec.get('type', 'unknown')
                }, "Traffic generation started")
            else:
                return result
                
        except Exception as e:
            LOG.error(f"Failed to generate traffic: {e}")
            return ResponseFormatter.error(str(e), "TRAFFIC_GENERATION_ERROR")
    
    def _validate_traffic_spec(self, traffic_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Validate traffic specification"""
        try:
            # Check required fields
            required_fields = ['type', 'src', 'dst']
            for field in required_fields:
                if field not in traffic_spec:
                    return {'valid': False, 'error': f"Missing required field: {field}"}
            
            # Validate traffic type
            traffic_type = traffic_spec['type'].lower()
            if traffic_type not in ['icmp', 'tcp', 'udp', 'scapy']:
                return {'valid': False, 'error': f"Unsupported traffic type: {traffic_type}"}
            
            # Check if required tool is available
            if traffic_type == 'icmp' and 'hping3' not in self.available_tools:
                return {'valid': False, 'error': "hping3 not available for ICMP traffic"}
            
            if traffic_type in ['tcp', 'udp'] and 'iperf3' not in self.available_tools:
                return {'valid': False, 'error': "iperf3 not available for TCP/UDP traffic"}
            
            if traffic_type == 'scapy' and 'scapy' not in self.available_tools:
                return {'valid': False, 'error': "Scapy not available for custom packets"}
            
            return {'valid': True}
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}
    
    def _start_traffic_generation(self, session: TrafficSession) -> Dict[str, Any]:
        """Start traffic generation for a session"""
        try:
            traffic_type = session.traffic_spec['type'].lower()
            
            if traffic_type == 'icmp':
                return self._start_icmp_traffic(session)
            elif traffic_type in ['tcp', 'udp']:
                return self._start_iperf_traffic(session)
            elif traffic_type == 'scapy':
                return self._start_scapy_traffic(session)
            else:
                return ResponseFormatter.error(
                    f"Unsupported traffic type: {traffic_type}",
                    "UNSUPPORTED_TRAFFIC_TYPE"
                )
                
        except Exception as e:
            LOG.error(f"Failed to start traffic generation: {e}")
            return ResponseFormatter.error(str(e), "TRAFFIC_START_ERROR")
    
    def _start_icmp_traffic(self, session: TrafficSession) -> Dict[str, Any]:
        """Start ICMP traffic using hping3"""
        try:
            spec = session.traffic_spec
            src = spec['src']
            dst = spec['dst']
            count = spec.get('count', 10)
            interval = spec.get('interval', 1)
            
            # Build hping3 command
            cmd = [
                'hping3',
                '-1',  # ICMP mode
                '-c', str(count),
                '-i', str(interval),
                dst
            ]
            
            # Start process in background
            def run_traffic():
                try:
                    session.status = "running"
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    session.process = process
                    
                    stdout, stderr = process.communicate(timeout=self.config.traffic_timeout)
                    
                    session.status = "completed"
                    session.results = {
                        'stdout': stdout,
                        'stderr': stderr,
                        'return_code': process.returncode
                    }
                    
                except subprocess.TimeoutExpired:
                    session.status = "timeout"
                    if session.process:
                        session.process.kill()
                except Exception as e:
                    session.status = "error"
                    session.results = {'error': str(e)}
            
            # Start traffic generation thread
            thread = threading.Thread(target=run_traffic)
            thread.daemon = True
            thread.start()
            
            return ResponseFormatter.success({'status': 'started'})
            
        except Exception as e:
            return ResponseFormatter.error(str(e), "ICMP_TRAFFIC_ERROR")
    
    def _start_iperf_traffic(self, session: TrafficSession) -> Dict[str, Any]:
        """Start TCP/UDP traffic using iperf3"""
        try:
            # For now, return simulated result
            # Full implementation would require iperf3 server setup
            session.status = "simulated"
            session.results = {
                'note': 'iperf3 traffic simulation - full implementation pending',
                'bandwidth': '100 Mbps',
                'duration': '10 seconds'
            }
            
            return ResponseFormatter.success({'status': 'simulated'})
            
        except Exception as e:
            return ResponseFormatter.error(str(e), "IPERF_TRAFFIC_ERROR")
    
    def _start_scapy_traffic(self, session: TrafficSession) -> Dict[str, Any]:
        """Start custom packet traffic using Scapy"""
        try:
            # For now, return simulated result
            # Full implementation would use Scapy to craft and send packets
            session.status = "simulated"
            session.results = {
                'note': 'Scapy traffic simulation - full implementation pending',
                'packets_sent': 100,
                'packet_type': 'custom'
            }
            
            return ResponseFormatter.success({'status': 'simulated'})
            
        except Exception as e:
            return ResponseFormatter.error(str(e), "SCAPY_TRAFFIC_ERROR")
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all traffic sessions"""
        try:
            with self.sessions_lock:
                sessions = []
                for session in self.active_sessions.values():
                    sessions.append(session.to_dict())
                
                # Clean up completed sessions older than 1 hour
                current_time = time.time()
                to_remove = []
                for session_id, session in self.active_sessions.items():
                    if (session.status in ['completed', 'error', 'timeout'] and
                        current_time - session.start_time > 3600):
                        to_remove.append(session_id)
                
                for session_id in to_remove:
                    del self.active_sessions[session_id]
                
                return ResponseFormatter.success({
                    'active_sessions': len(self.active_sessions),
                    'max_concurrent': self.config.traffic_max_concurrent,
                    'available_tools': self.available_tools,
                    'sessions': sessions
                })
                
        except Exception as e:
            LOG.error(f"Failed to get traffic status: {e}")
            return ResponseFormatter.error(str(e), "STATUS_ERROR")
    
    def stop_session(self, session_id: str) -> Dict[str, Any]:
        """Stop a traffic generation session"""
        try:
            with self.sessions_lock:
                if session_id not in self.active_sessions:
                    return ResponseFormatter.error(
                        "Session not found",
                        "SESSION_NOT_FOUND"
                    )
                
                session = self.active_sessions[session_id]
                
                if session.process and session.process.poll() is None:
                    session.process.terminate()
                    session.status = "stopped"
                
                return ResponseFormatter.success({
                    'session_id': session_id,
                    'status': session.status
                })
                
        except Exception as e:
            LOG.error(f"Failed to stop session: {e}")
            return ResponseFormatter.error(str(e), "STOP_SESSION_ERROR")
    
    def is_healthy(self) -> str:
        """Check if traffic generator is healthy"""
        try:
            if not self.available_tools:
                return "no_tools"
            
            with self.sessions_lock:
                active_count = len(self.active_sessions)
                if active_count < self.config.traffic_max_concurrent:
                    return "healthy"
                else:
                    return "at_capacity"
                    
        except Exception:
            return "error"
    
    def cleanup(self):
        """Cleanup active sessions"""
        try:
            with self.sessions_lock:
                for session in self.active_sessions.values():
                    if session.process and session.process.poll() is None:
                        session.process.terminate()
                
                self.active_sessions.clear()
            
            LOG.info("Traffic generator cleanup completed")
            
        except Exception as e:
            LOG.error(f"Error during traffic generator cleanup: {e}")
