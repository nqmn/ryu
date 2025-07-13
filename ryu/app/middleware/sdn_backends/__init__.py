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
SDN Backends Package

This package provides backend abstraction for different SDN protocols
including OpenFlow (via Ryu) and P4Runtime (via gRPC).

The backend system allows the middleware to support multiple SDN protocols
simultaneously while providing a unified API interface.
"""

from .base import SDNControllerBase, SwitchType, FlowData, PacketData
from .switch_manager import SwitchManager

__all__ = [
    'SDNControllerBase',
    'SwitchType', 
    'FlowData',
    'PacketData',
    'SwitchManager',
]
