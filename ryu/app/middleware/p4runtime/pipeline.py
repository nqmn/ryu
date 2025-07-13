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
P4 Pipeline Manager

This module provides the PipelineManager class for managing P4 pipeline
installation, validation, and status monitoring across P4Runtime switches.
"""

import logging
import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field

from .utils import P4InfoHelper

LOG = logging.getLogger(__name__)


@dataclass
class PipelineInfo:
    """Information about a P4 pipeline"""
    name: str
    p4info_path: str
    config_path: str
    version: str = "1.0.0"
    description: str = ""
    tables: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_valid(self) -> bool:
        """Check if pipeline files exist and are valid"""
        return (
            os.path.exists(self.p4info_path) and
            os.path.exists(self.config_path)
        )


@dataclass
class PipelineStatus:
    """Status of a pipeline on a switch"""
    switch_id: str
    pipeline_name: str
    installed: bool = False
    version: str = ""
    install_time: Optional[float] = None
    error_message: str = ""
    table_count: int = 0
    action_count: int = 0


class PipelineManager:
    """
    Manager for P4 pipeline operations
    
    This class handles:
    - Pipeline registration and validation
    - Installation status tracking
    - Pipeline metadata management
    - Multi-switch pipeline coordination
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pipelines: Dict[str, PipelineInfo] = {}
        self.switch_status: Dict[str, PipelineStatus] = {}
        self.pipeline_directory = config.get('pipeline_directory', './pipelines')
        
        # Ensure pipeline directory exists
        Path(self.pipeline_directory).mkdir(parents=True, exist_ok=True)
        
        # Load registered pipelines
        self._load_registered_pipelines()
    
    def _load_registered_pipelines(self):
        """Load pipelines from configuration and directory"""
        try:
            # Load from configuration
            pipeline_configs = self.config.get('pipelines', [])
            for pipeline_config in pipeline_configs:
                pipeline_info = PipelineInfo(**pipeline_config)
                if pipeline_info.is_valid():
                    self.pipelines[pipeline_info.name] = pipeline_info
                    LOG.info(f"Loaded pipeline: {pipeline_info.name}")
                else:
                    LOG.warning(f"Invalid pipeline configuration: {pipeline_info.name}")
            
            # Auto-discover pipelines in directory
            self._discover_pipelines()
            
            LOG.info(f"Loaded {len(self.pipelines)} pipelines")
            
        except Exception as e:
            LOG.error(f"Failed to load pipelines: {e}")
    
    def _discover_pipelines(self):
        """Auto-discover pipelines in the pipeline directory"""
        try:
            pipeline_dir = Path(self.pipeline_directory)
            if not pipeline_dir.exists():
                return
            
            # Look for pipeline.json files
            for pipeline_file in pipeline_dir.glob('**/pipeline.json'):
                try:
                    with open(pipeline_file, 'r') as f:
                        pipeline_data = json.load(f)
                    
                    # Resolve relative paths
                    pipeline_dir_path = pipeline_file.parent
                    pipeline_data['p4info_path'] = str(pipeline_dir_path / pipeline_data['p4info_path'])
                    pipeline_data['config_path'] = str(pipeline_dir_path / pipeline_data['config_path'])
                    
                    pipeline_info = PipelineInfo(**pipeline_data)
                    if pipeline_info.is_valid():
                        self.pipelines[pipeline_info.name] = pipeline_info
                        LOG.info(f"Discovered pipeline: {pipeline_info.name}")
                    
                except Exception as e:
                    LOG.error(f"Failed to load pipeline from {pipeline_file}: {e}")
                    
        except Exception as e:
            LOG.error(f"Failed to discover pipelines: {e}")
    
    def register_pipeline(self, pipeline_info: PipelineInfo) -> bool:
        """Register a new pipeline"""
        try:
            if not pipeline_info.is_valid():
                LOG.error(f"Invalid pipeline: {pipeline_info.name}")
                return False
            
            # Parse P4Info to extract table and action information
            self._extract_pipeline_metadata(pipeline_info)
            
            self.pipelines[pipeline_info.name] = pipeline_info
            LOG.info(f"Registered pipeline: {pipeline_info.name}")
            return True
            
        except Exception as e:
            LOG.error(f"Failed to register pipeline {pipeline_info.name}: {e}")
            return False
    
    def _extract_pipeline_metadata(self, pipeline_info: PipelineInfo):
        """Extract metadata from P4Info file"""
        try:
            with open(pipeline_info.p4info_path, 'r') as f:
                p4info_data = json.load(f)
            
            # Extract table names
            tables = p4info_data.get('tables', [])
            pipeline_info.tables = [table.get('preamble', {}).get('name', '') for table in tables]
            
            # Extract action names
            actions = p4info_data.get('actions', [])
            pipeline_info.actions = [action.get('preamble', {}).get('name', '') for action in actions]
            
            LOG.debug(f"Extracted metadata for {pipeline_info.name}: "
                     f"{len(pipeline_info.tables)} tables, {len(pipeline_info.actions)} actions")
            
        except Exception as e:
            LOG.error(f"Failed to extract metadata for {pipeline_info.name}: {e}")
    
    def unregister_pipeline(self, pipeline_name: str) -> bool:
        """Unregister a pipeline"""
        try:
            if pipeline_name in self.pipelines:
                del self.pipelines[pipeline_name]
                LOG.info(f"Unregistered pipeline: {pipeline_name}")
                return True
            else:
                LOG.warning(f"Pipeline not found: {pipeline_name}")
                return False
                
        except Exception as e:
            LOG.error(f"Failed to unregister pipeline {pipeline_name}: {e}")
            return False
    
    def get_pipeline(self, pipeline_name: str) -> Optional[PipelineInfo]:
        """Get pipeline information by name"""
        return self.pipelines.get(pipeline_name)
    
    def list_pipelines(self) -> List[PipelineInfo]:
        """List all registered pipelines"""
        return list(self.pipelines.values())
    
    def update_switch_status(self, switch_id: str, pipeline_name: str, 
                           installed: bool, error_message: str = "") -> None:
        """Update pipeline status for a switch"""
        try:
            import time
            
            status = PipelineStatus(
                switch_id=switch_id,
                pipeline_name=pipeline_name,
                installed=installed,
                error_message=error_message
            )
            
            if installed:
                status.install_time = time.time()
                pipeline_info = self.get_pipeline(pipeline_name)
                if pipeline_info:
                    status.version = pipeline_info.version
                    status.table_count = len(pipeline_info.tables)
                    status.action_count = len(pipeline_info.actions)
            
            self.switch_status[switch_id] = status
            LOG.info(f"Updated pipeline status for switch {switch_id}: {pipeline_name} - {'installed' if installed else 'failed'}")
            
        except Exception as e:
            LOG.error(f"Failed to update switch status: {e}")
    
    def get_switch_status(self, switch_id: str) -> Optional[PipelineStatus]:
        """Get pipeline status for a switch"""
        return self.switch_status.get(switch_id)
    
    def list_switch_status(self) -> List[PipelineStatus]:
        """List pipeline status for all switches"""
        return list(self.switch_status.values())
    
    def validate_pipeline(self, pipeline_name: str) -> Dict[str, Any]:
        """Validate a pipeline configuration"""
        try:
            pipeline_info = self.get_pipeline(pipeline_name)
            if not pipeline_info:
                return {
                    'valid': False,
                    'error': f"Pipeline {pipeline_name} not found"
                }
            
            validation_result = {
                'valid': True,
                'pipeline_name': pipeline_name,
                'files_exist': pipeline_info.is_valid(),
                'tables': len(pipeline_info.tables),
                'actions': len(pipeline_info.actions),
                'errors': [],
                'warnings': []
            }
            
            # Check file existence
            if not os.path.exists(pipeline_info.p4info_path):
                validation_result['errors'].append(f"P4Info file not found: {pipeline_info.p4info_path}")
                validation_result['valid'] = False
            
            if not os.path.exists(pipeline_info.config_path):
                validation_result['errors'].append(f"Config file not found: {pipeline_info.config_path}")
                validation_result['valid'] = False
            
            # Validate P4Info format
            if os.path.exists(pipeline_info.p4info_path):
                try:
                    with open(pipeline_info.p4info_path, 'r') as f:
                        p4info_data = json.load(f)
                    
                    if 'tables' not in p4info_data:
                        validation_result['warnings'].append("No tables found in P4Info")
                    
                    if 'actions' not in p4info_data:
                        validation_result['warnings'].append("No actions found in P4Info")
                        
                except json.JSONDecodeError as e:
                    validation_result['errors'].append(f"Invalid JSON in P4Info file: {e}")
                    validation_result['valid'] = False
                except Exception as e:
                    validation_result['errors'].append(f"Error reading P4Info file: {e}")
                    validation_result['valid'] = False
            
            return validation_result
            
        except Exception as e:
            LOG.error(f"Failed to validate pipeline {pipeline_name}: {e}")
            return {
                'valid': False,
                'error': str(e)
            }
    
    def get_pipeline_summary(self) -> Dict[str, Any]:
        """Get summary of all pipelines and their status"""
        try:
            summary = {
                'total_pipelines': len(self.pipelines),
                'total_switches': len(self.switch_status),
                'installed_switches': sum(1 for status in self.switch_status.values() if status.installed),
                'pipelines': [],
                'switches': []
            }
            
            # Pipeline information
            for pipeline_info in self.pipelines.values():
                pipeline_summary = {
                    'name': pipeline_info.name,
                    'version': pipeline_info.version,
                    'description': pipeline_info.description,
                    'tables': len(pipeline_info.tables),
                    'actions': len(pipeline_info.actions),
                    'installed_on': [
                        status.switch_id for status in self.switch_status.values()
                        if status.pipeline_name == pipeline_info.name and status.installed
                    ]
                }
                summary['pipelines'].append(pipeline_summary)
            
            # Switch status
            for status in self.switch_status.values():
                switch_summary = {
                    'switch_id': status.switch_id,
                    'pipeline': status.pipeline_name,
                    'installed': status.installed,
                    'version': status.version,
                    'install_time': status.install_time,
                    'error': status.error_message
                }
                summary['switches'].append(switch_summary)
            
            return summary
            
        except Exception as e:
            LOG.error(f"Failed to get pipeline summary: {e}")
            return {'error': str(e)}
    
    def cleanup_switch_status(self, switch_id: str):
        """Remove status information for a disconnected switch"""
        if switch_id in self.switch_status:
            del self.switch_status[switch_id]
            LOG.info(f"Cleaned up status for switch {switch_id}")
