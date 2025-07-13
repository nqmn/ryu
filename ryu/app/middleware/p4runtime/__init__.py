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
P4Runtime Package

This package provides P4Runtime gRPC client implementation for controlling
P4-programmable switches including BMv2, Tofino, and other P4Runtime-compatible
devices.

Key Features:
- P4Runtime gRPC client with connection management
- Pipeline installation and management
- Table entry operations (insert, modify, delete, read)
- Packet-in/packet-out streaming
- Error handling and status reporting
"""

from .client import P4RuntimeClient
from .utils import P4RuntimeUtils, P4InfoHelper
from .pipeline import PipelineManager

__all__ = [
    'P4RuntimeClient',
    'P4RuntimeUtils',
    'P4InfoHelper', 
    'PipelineManager',
]
