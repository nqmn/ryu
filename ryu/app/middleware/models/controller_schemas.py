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
Controller Management Data Models

This module defines Pydantic schemas and data models for multi-controller
management including controller registration, health monitoring, switch
mapping, and API request/response models.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field, validator
from dataclasses import dataclass


class ControllerType(str, Enum):
    """Enumeration of supported controller types"""
    RYU_OPENFLOW = "ryu_openflow"
    P4RUNTIME = "p4runtime"
    CUSTOM = "custom"


class ControllerStatus(str, Enum):
    """Enumeration of controller status states"""
    INITIALIZING = "initializing"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class HealthStatus(str, Enum):
    """Enumeration of health check status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ControllerMetrics:
    """Controller performance and operational metrics"""
    uptime_seconds: float = 0.0
    total_switches: int = 0
    active_flows: int = 0
    packets_processed: int = 0
    events_generated: int = 0
    last_activity: Optional[datetime] = None
    response_time_ms: float = 0.0
    error_count: int = 0


class ControllerConfig(BaseModel):
    """Controller configuration model"""
    controller_id: str = Field(..., description="Unique controller identifier")
    controller_type: ControllerType = Field(..., description="Type of controller")
    name: str = Field(..., description="Human-readable controller name")
    description: Optional[str] = Field(None, description="Controller description")
    
    # Connection configuration
    host: str = Field("localhost", description="Controller host address")
    port: int = Field(..., description="Controller port")
    protocol: str = Field("http", description="Communication protocol")
    
    # Authentication (if required)
    username: Optional[str] = Field(None, description="Authentication username")
    password: Optional[str] = Field(None, description="Authentication password")
    api_key: Optional[str] = Field(None, description="API key for authentication")
    
    # Health monitoring configuration
    health_check_interval: int = Field(30, description="Health check interval in seconds")
    health_check_timeout: int = Field(5, description="Health check timeout in seconds")
    max_retries: int = Field(3, description="Maximum retry attempts")
    
    # Failover configuration
    backup_controllers: List[str] = Field(default_factory=list, description="List of backup controller IDs")
    priority: int = Field(100, description="Controller priority (higher = preferred)")
    
    # Additional configuration
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('controller_id')
    def validate_controller_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Controller ID cannot be empty')
        return v.strip()
    
    @validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v


class ControllerInfo(BaseModel):
    """Complete controller information including status and metrics"""
    config: ControllerConfig
    status: ControllerStatus = ControllerStatus.INITIALIZING
    health_status: HealthStatus = HealthStatus.UNKNOWN
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    
    # Metrics
    metrics: ControllerMetrics = Field(default_factory=ControllerMetrics)
    
    # Switch assignments
    assigned_switches: List[str] = Field(default_factory=list, description="List of assigned switch IDs")
    
    # Error information
    last_error: Optional[str] = None
    error_count: int = 0


class SwitchMapping(BaseModel):
    """Switch to controller mapping"""
    switch_id: str = Field(..., description="Switch identifier")
    primary_controller: str = Field(..., description="Primary controller ID")
    backup_controllers: List[str] = Field(default_factory=list, description="Backup controller IDs")
    current_controller: str = Field(..., description="Currently active controller ID")
    
    # Mapping metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    failover_count: int = Field(0, description="Number of failovers")
    
    @validator('current_controller')
    def validate_current_controller(cls, v, values):
        primary = values.get('primary_controller')
        backups = values.get('backup_controllers', [])
        
        if v != primary and v not in backups:
            raise ValueError('Current controller must be either primary or backup')
        return v


class HealthCheckResult(BaseModel):
    """Health check result"""
    controller_id: str
    status: HealthStatus
    response_time_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class ControllerEvent(BaseModel):
    """Controller lifecycle event"""
    event_type: str = Field(..., description="Event type (registered, connected, disconnected, etc.)")
    controller_id: str = Field(..., description="Controller ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict)
    severity: str = Field("info", description="Event severity (info, warning, error)")


# API Request/Response Models

class RegisterControllerRequest(BaseModel):
    """Request model for controller registration"""
    config: ControllerConfig
    auto_start: bool = Field(True, description="Automatically start the controller after registration")


class RegisterControllerResponse(BaseModel):
    """Response model for controller registration"""
    success: bool
    controller_id: str
    message: str
    controller_info: Optional[ControllerInfo] = None


class SwitchMappingRequest(BaseModel):
    """Request model for switch mapping"""
    switch_id: str
    primary_controller: str
    backup_controllers: List[str] = Field(default_factory=list)


class SwitchMappingResponse(BaseModel):
    """Response model for switch mapping"""
    success: bool
    message: str
    mapping: Optional[SwitchMapping] = None


class ControllerListResponse(BaseModel):
    """Response model for listing controllers"""
    controllers: List[ControllerInfo]
    total_count: int
    healthy_count: int
    connected_count: int


class HealthCheckResponse(BaseModel):
    """Response model for health check status"""
    controller_id: str
    overall_health: HealthStatus
    checks: List[HealthCheckResult]
    summary: Dict[str, Any]


class FailoverRequest(BaseModel):
    """Request model for manual failover"""
    switch_id: str
    target_controller: Optional[str] = None  # If None, use next available backup


class FailoverResponse(BaseModel):
    """Response model for failover operation"""
    success: bool
    message: str
    old_controller: str
    new_controller: str
    switch_id: str
