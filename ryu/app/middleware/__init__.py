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
Ryu Middleware API Package

This package provides a comprehensive middleware API that bridges communication
between the Ryu SDN controller, Mininet emulator, and external AI/ML modules.

Key Features:
- Unified REST and WebSocket API
- Topology management via Mininet integration
- Traffic generation and flow management
- Real-time event streaming
- AI/ML integration framework
- Comprehensive monitoring and telemetry

Usage:
    To start the middleware API, run:
    $ ryu-manager ryu.app.middleware.core

API Endpoints:
    REST API: http://localhost:8080/v2.0/
    WebSocket: ws://localhost:8080/v2.0/events/ws
"""

__version__ = "2.0.0"
__author__ = "Ryu SDN Framework Project"

# Import main components for easy access
from .core import MiddlewareAPI
from .rest_api import MiddlewareRestController
from .websocket_api import MiddlewareWebSocketController

__all__ = [
    'MiddlewareAPI',
    'MiddlewareRestController', 
    'MiddlewareWebSocketController',
]
