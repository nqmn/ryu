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
Centralized Event Stream System

This module provides a unified event streaming system that aggregates events
from multiple SDN controllers and distributes them to subscribers through
various channels (WebSocket, callbacks, etc.).
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, List, Callable, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from collections import deque, defaultdict

LOG = logging.getLogger(__name__)


@dataclass
class Event:
    """Unified event representation"""
    event_type: str
    source_controller: str
    source_type: str  # 'openflow', 'p4runtime', etc.
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    sequence_number: int = 0
    priority: int = 1  # 1=low, 2=medium, 3=high
    metadata: Dict[str, Any] = field(default_factory=dict)


class EventFilter:
    """Event filtering configuration"""
    
    def __init__(self):
        self.event_types: Set[str] = set()
        self.controller_ids: Set[str] = set()
        self.source_types: Set[str] = set()
        self.min_priority: int = 1
        self.custom_filter: Optional[Callable[[Event], bool]] = None
    
    def matches(self, event: Event) -> bool:
        """Check if event matches filter criteria"""
        # Check event type filter
        if self.event_types and event.event_type not in self.event_types:
            return False
        
        # Check controller filter
        if self.controller_ids and event.source_controller not in self.controller_ids:
            return False
        
        # Check source type filter
        if self.source_types and event.source_type not in self.source_types:
            return False
        
        # Check priority filter
        if event.priority < self.min_priority:
            return False
        
        # Check custom filter
        if self.custom_filter and not self.custom_filter(event):
            return False
        
        return True


class EventSubscriber:
    """Event subscriber with filtering and callback"""
    
    def __init__(self, subscriber_id: str, callback: Callable[[Event], None], 
                 event_filter: Optional[EventFilter] = None):
        self.subscriber_id = subscriber_id
        self.callback = callback
        self.filter = event_filter or EventFilter()
        self.created_at = datetime.utcnow()
        self.event_count = 0
        self.last_event = None
        self.active = True


class EventStream:
    """
    Centralized event streaming system
    
    This class manages event aggregation from multiple controllers,
    filtering, and distribution to subscribers.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.running = False
        
        # Event storage and processing
        self.event_queue = asyncio.Queue(maxsize=config.get('max_queue_size', 10000))
        self.event_history = deque(maxlen=config.get('max_history_size', 1000))
        self.sequence_counter = 0
        
        # Subscribers management
        self.subscribers: Dict[str, EventSubscriber] = {}
        self.subscribers_lock = Lock()
        
        # Statistics
        self.stats = {
            'total_events': 0,
            'events_by_type': defaultdict(int),
            'events_by_controller': defaultdict(int),
            'events_by_source_type': defaultdict(int),
            'dropped_events': 0,
            'subscriber_count': 0,
            'start_time': datetime.utcnow()
        }
        
        # Processing tasks
        self.processor_task = None
        self.cleanup_task = None
    
    async def start(self):
        """Start the event stream processing"""
        if self.running:
            LOG.warning("Event stream already running")
            return
        
        self.running = True
        LOG.info("Starting event stream processor")
        
        # Start event processor
        self.processor_task = asyncio.create_task(self._process_events())
        
        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self._cleanup_task())
        
        LOG.info("Event stream started successfully")
    
    async def stop(self):
        """Stop the event stream processing"""
        if not self.running:
            return
        
        self.running = False
        LOG.info("Stopping event stream processor")
        
        # Cancel tasks
        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        LOG.info("Event stream stopped")
    
    async def publish_event(self, event_type: str, source_controller: str, 
                          source_type: str, data: Dict[str, Any], 
                          priority: int = 1, metadata: Optional[Dict[str, Any]] = None):
        """Publish an event to the stream"""
        try:
            # Create event
            event = Event(
                event_type=event_type,
                source_controller=source_controller,
                source_type=source_type,
                data=data,
                sequence_number=self._get_next_sequence(),
                priority=priority,
                metadata=metadata or {}
            )
            
            # Add to queue
            if self.event_queue.full():
                # Drop oldest event if queue is full
                try:
                    self.event_queue.get_nowait()
                    self.stats['dropped_events'] += 1
                except asyncio.QueueEmpty:
                    pass
            
            await self.event_queue.put(event)
            
        except Exception as e:
            LOG.error(f"Failed to publish event: {e}")
    
    def subscribe(self, subscriber_id: str, callback: Callable[[Event], None], 
                  event_filter: Optional[EventFilter] = None) -> bool:
        """Subscribe to events with optional filtering"""
        try:
            with self.subscribers_lock:
                if subscriber_id in self.subscribers:
                    LOG.warning(f"Subscriber {subscriber_id} already exists")
                    return False
                
                subscriber = EventSubscriber(subscriber_id, callback, event_filter)
                self.subscribers[subscriber_id] = subscriber
                self.stats['subscriber_count'] = len(self.subscribers)
                
                LOG.info(f"Added subscriber: {subscriber_id}")
                return True
                
        except Exception as e:
            LOG.error(f"Failed to add subscriber {subscriber_id}: {e}")
            return False
    
    def unsubscribe(self, subscriber_id: str) -> bool:
        """Unsubscribe from events"""
        try:
            with self.subscribers_lock:
                if subscriber_id not in self.subscribers:
                    LOG.warning(f"Subscriber {subscriber_id} not found")
                    return False
                
                del self.subscribers[subscriber_id]
                self.stats['subscriber_count'] = len(self.subscribers)
                
                LOG.info(f"Removed subscriber: {subscriber_id}")
                return True
                
        except Exception as e:
            LOG.error(f"Failed to remove subscriber {subscriber_id}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event stream statistics"""
        uptime = (datetime.utcnow() - self.stats['start_time']).total_seconds()
        
        return {
            'running': self.running,
            'uptime_seconds': uptime,
            'queue_size': self.event_queue.qsize(),
            'history_size': len(self.event_history),
            'total_events': self.stats['total_events'],
            'events_by_type': dict(self.stats['events_by_type']),
            'events_by_controller': dict(self.stats['events_by_controller']),
            'events_by_source_type': dict(self.stats['events_by_source_type']),
            'dropped_events': self.stats['dropped_events'],
            'subscriber_count': self.stats['subscriber_count'],
            'events_per_second': self.stats['total_events'] / max(uptime, 1)
        }
    
    def get_recent_events(self, count: int = 100, 
                         event_filter: Optional[EventFilter] = None) -> List[Event]:
        """Get recent events with optional filtering"""
        events = list(self.event_history)
        
        if event_filter:
            events = [event for event in events if event_filter.matches(event)]
        
        return events[-count:] if count > 0 else events
    
    async def _process_events(self):
        """Main event processing loop"""
        LOG.info("Event processor started")
        
        while self.running:
            try:
                # Get event from queue with timeout
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                
                # Update statistics
                self._update_stats(event)
                
                # Add to history
                self.event_history.append(event)
                
                # Distribute to subscribers
                await self._distribute_event(event)
                
            except asyncio.TimeoutError:
                # No events to process, continue
                continue
            except Exception as e:
                LOG.error(f"Error processing event: {e}")
    
    async def _distribute_event(self, event: Event):
        """Distribute event to all matching subscribers"""
        with self.subscribers_lock:
            subscribers = list(self.subscribers.values())
        
        for subscriber in subscribers:
            if not subscriber.active:
                continue
            
            try:
                # Check if event matches subscriber's filter
                if subscriber.filter.matches(event):
                    # Call subscriber callback
                    if asyncio.iscoroutinefunction(subscriber.callback):
                        await subscriber.callback(event)
                    else:
                        subscriber.callback(event)
                    
                    # Update subscriber stats
                    subscriber.event_count += 1
                    subscriber.last_event = event
                    
            except Exception as e:
                LOG.error(f"Error calling subscriber {subscriber.subscriber_id}: {e}")
                # Optionally deactivate problematic subscribers
                if self.config.get('auto_deactivate_failed_subscribers', True):
                    subscriber.active = False
    
    async def _cleanup_task(self):
        """Periodic cleanup task"""
        cleanup_interval = self.config.get('cleanup_interval', 300)  # 5 minutes
        
        while self.running:
            try:
                await asyncio.sleep(cleanup_interval)
                
                # Remove inactive subscribers
                with self.subscribers_lock:
                    inactive_subscribers = [
                        sub_id for sub_id, sub in self.subscribers.items()
                        if not sub.active
                    ]
                    
                    for sub_id in inactive_subscribers:
                        del self.subscribers[sub_id]
                        LOG.info(f"Removed inactive subscriber: {sub_id}")
                    
                    self.stats['subscriber_count'] = len(self.subscribers)
                
            except Exception as e:
                LOG.error(f"Error in cleanup task: {e}")
    
    def _get_next_sequence(self) -> int:
        """Get next sequence number"""
        self.sequence_counter += 1
        return self.sequence_counter
    
    def _update_stats(self, event: Event):
        """Update event statistics"""
        self.stats['total_events'] += 1
        self.stats['events_by_type'][event.event_type] += 1
        self.stats['events_by_controller'][event.source_controller] += 1
        self.stats['events_by_source_type'][event.source_type] += 1
