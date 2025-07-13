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
Mininet Bridge Module

This module provides integration with Mininet for topology creation,
management, and host operations.
"""

import os
import subprocess
import logging
import time
import json
from typing import Dict, Any, List, Optional, Tuple
from threading import Lock

from .utils import MiddlewareConfig, ResponseFormatter

LOG = logging.getLogger(__name__)


class MininetBridge:
    """
    Bridge class for Mininet integration
    
    Provides functionality for:
    - Creating topologies from JSON/YAML definitions
    - Managing Mininet network instances
    - Host discovery and connectivity testing
    - Topology status monitoring
    """
    
    def __init__(self, config: MiddlewareConfig):
        self.config = config
        self.current_topology = None
        self.mininet_process = None
        self.topology_lock = Lock()
        
        # Check if Mininet is available
        self._check_mininet_availability()
        
        LOG.info("Mininet bridge initialized")
    
    def _check_mininet_availability(self):
        """Check if Mininet is available on the system"""
        if not self.config.mininet_enabled:
            LOG.info("Mininet integration is disabled")
            return
        
        try:
            # Try to import Mininet modules
            result = subprocess.run(
                [self.config.mininet_python_path, '-c', 'import mininet.net; print("OK")'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and "OK" in result.stdout:
                LOG.info("Mininet is available")
            else:
                LOG.warning("Mininet not available, some features will be disabled")
                self.config.mininet_enabled = False
                
        except Exception as e:
            LOG.warning(f"Failed to check Mininet availability: {e}")
            self.config.mininet_enabled = False
    
    def create_topology(self, topology_def: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create topology from definition
        
        Args:
            topology_def: Topology definition dictionary
            
        Returns:
            Result dictionary with success status and details
        """
        if not self.config.mininet_enabled:
            return ResponseFormatter.error(
                "Mininet integration is disabled",
                "MININET_DISABLED"
            )
        
        with self.topology_lock:
            try:
                # Clean up existing topology if any
                if self.current_topology:
                    self._cleanup_topology()
                
                # Create new topology
                result = self._create_mininet_topology(topology_def)
                
                if result['success']:
                    self.current_topology = topology_def
                    LOG.info(f"Created topology: {topology_def.get('name', 'unnamed')}")
                
                return result
                
            except Exception as e:
                LOG.error(f"Failed to create topology: {e}")
                return ResponseFormatter.error(str(e), "TOPOLOGY_CREATION_ERROR")
    
    def _create_mininet_topology(self, topology_def: Dict[str, Any]) -> Dict[str, Any]:
        """Create Mininet topology using Python API"""
        try:
            # Generate Mininet Python script
            script_content = self._generate_mininet_script(topology_def)
            
            # Write script to temporary file
            script_path = f"/tmp/mininet_topology_{int(time.time())}.py"
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            # Execute Mininet script
            process = subprocess.Popen(
                [self.config.mininet_python_path, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.mininet_process = process
            
            # Wait a bit for topology to initialize
            time.sleep(2)
            
            # Check if process is still running
            if process.poll() is None:
                return ResponseFormatter.success({
                    'topology_name': topology_def.get('name', 'unnamed'),
                    'switches': len(topology_def.get('switches', [])),
                    'hosts': len(topology_def.get('hosts', [])),
                    'links': len(topology_def.get('links', [])),
                    'status': 'running'
                }, "Topology created successfully")
            else:
                stdout, stderr = process.communicate()
                return ResponseFormatter.error(
                    f"Mininet process failed: {stderr}",
                    "MININET_PROCESS_ERROR"
                )
                
        except Exception as e:
            return ResponseFormatter.error(str(e), "SCRIPT_GENERATION_ERROR")
    
    def _generate_mininet_script(self, topology_def: Dict[str, Any]) -> str:
        """Generate Mininet Python script from topology definition"""
        script_lines = [
            "#!/usr/bin/env python3",
            "from mininet.net import Mininet",
            "from mininet.node import Controller, RemoteController",
            "from mininet.cli import CLI",
            "from mininet.log import setLogLevel",
            "from mininet.link import TCLink",
            "",
            "def create_topology():",
            "    net = Mininet(controller=RemoteController, link=TCLink)",
            "",
            "    # Add controller",
            "    c0 = net.addController('c0', controller=RemoteController,",
            "                          ip='127.0.0.1', port=6633)",
            "",
        ]
        
        # Add switches
        for switch in topology_def.get('switches', []):
            switch_name = switch['name']
            script_lines.append(f"    {switch_name} = net.addSwitch('{switch_name}')")
        
        script_lines.append("")
        
        # Add hosts
        for host in topology_def.get('hosts', []):
            host_name = host['name']
            host_ip = host.get('ip', None)
            if host_ip:
                script_lines.append(f"    {host_name} = net.addHost('{host_name}', ip='{host_ip}')")
            else:
                script_lines.append(f"    {host_name} = net.addHost('{host_name}')")
        
        script_lines.append("")
        
        # Add links
        for link in topology_def.get('links', []):
            src = link['src']
            dst = link['dst']
            bw = link.get('bandwidth', None)
            delay = link.get('delay', None)
            
            if bw or delay:
                link_params = []
                if bw:
                    link_params.append(f"bw={bw}")
                if delay:
                    link_params.append(f"delay='{delay}'")
                params_str = ", " + ", ".join(link_params)
            else:
                params_str = ""
            
            script_lines.append(f"    net.addLink({src}, {dst}{params_str})")
        
        script_lines.extend([
            "",
            "    net.start()",
            "    print('Topology started successfully')",
            "",
            "    # Keep the network running",
            "    try:",
            "        CLI(net)",
            "    except KeyboardInterrupt:",
            "        pass",
            "    finally:",
            "        net.stop()",
            "",
            "if __name__ == '__main__':",
            "    setLogLevel('info')",
            "    create_topology()",
        ])
        
        return "\n".join(script_lines)
    
    def delete_topology(self) -> Dict[str, Any]:
        """Delete current topology"""
        if not self.config.mininet_enabled:
            return ResponseFormatter.error(
                "Mininet integration is disabled",
                "MININET_DISABLED"
            )
        
        with self.topology_lock:
            try:
                if not self.current_topology:
                    return ResponseFormatter.error(
                        "No topology to delete",
                        "NO_TOPOLOGY"
                    )
                
                self._cleanup_topology()
                
                return ResponseFormatter.success(
                    {'status': 'deleted'},
                    "Topology deleted successfully"
                )
                
            except Exception as e:
                LOG.error(f"Failed to delete topology: {e}")
                return ResponseFormatter.error(str(e), "TOPOLOGY_DELETION_ERROR")
    
    def _cleanup_topology(self):
        """Clean up current topology"""
        try:
            # Terminate Mininet process
            if self.mininet_process and self.mininet_process.poll() is None:
                self.mininet_process.terminate()
                self.mininet_process.wait(timeout=10)
            
            # Clean up Mininet state
            subprocess.run(['sudo', 'mn', '-c'], capture_output=True, timeout=10)
            
            self.current_topology = None
            self.mininet_process = None
            
            LOG.info("Topology cleanup completed")
            
        except Exception as e:
            LOG.error(f"Error during topology cleanup: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current topology status"""
        with self.topology_lock:
            if not self.current_topology:
                return ResponseFormatter.success({
                    'status': 'no_topology',
                    'mininet_enabled': self.config.mininet_enabled
                })
            
            # Check if Mininet process is still running
            is_running = (self.mininet_process and 
                         self.mininet_process.poll() is None)
            
            return ResponseFormatter.success({
                'status': 'running' if is_running else 'stopped',
                'topology_name': self.current_topology.get('name', 'unnamed'),
                'switches': len(self.current_topology.get('switches', [])),
                'hosts': len(self.current_topology.get('hosts', [])),
                'links': len(self.current_topology.get('links', [])),
                'mininet_enabled': self.config.mininet_enabled
            })
    
    def list_hosts(self) -> Dict[str, Any]:
        """List all hosts in the current topology"""
        if not self.current_topology:
            return ResponseFormatter.error(
                "No active topology",
                "NO_TOPOLOGY"
            )
        
        try:
            hosts = []
            for host in self.current_topology.get('hosts', []):
                hosts.append({
                    'name': host['name'],
                    'ip': host.get('ip', 'auto'),
                    'mac': host.get('mac', 'auto'),
                    'switch': host.get('switch', 'unknown')
                })
            
            return ResponseFormatter.success(hosts)
            
        except Exception as e:
            LOG.error(f"Failed to list hosts: {e}")
            return ResponseFormatter.error(str(e), "HOST_LIST_ERROR")
    
    def ping_hosts(self, src: str, dst: str, count: int = 3) -> Dict[str, Any]:
        """Perform ping test between hosts"""
        if not self.current_topology:
            return ResponseFormatter.error(
                "No active topology",
                "NO_TOPOLOGY"
            )
        
        try:
            # For now, return simulated ping results
            # In a full implementation, this would execute actual ping via Mininet
            result = {
                'src': src,
                'dst': dst,
                'count': count,
                'success': True,
                'packets_sent': count,
                'packets_received': count,
                'packet_loss': 0.0,
                'avg_rtt': 1.5,  # milliseconds
                'note': 'Simulated ping result - full implementation pending'
            }
            
            return ResponseFormatter.success(result)
            
        except Exception as e:
            LOG.error(f"Failed to ping hosts: {e}")
            return ResponseFormatter.error(str(e), "PING_ERROR")
    
    def is_healthy(self) -> str:
        """Check if Mininet bridge is healthy"""
        if not self.config.mininet_enabled:
            return "disabled"
        
        try:
            # Basic health check
            if self.current_topology and self.mininet_process:
                if self.mininet_process.poll() is None:
                    return "healthy"
                else:
                    return "unhealthy"
            else:
                return "idle"
                
        except Exception:
            return "error"
    
    def cleanup(self):
        """Cleanup resources"""
        if self.config.mininet_cleanup_on_exit:
            self._cleanup_topology()
        LOG.info("Mininet bridge cleanup completed")
