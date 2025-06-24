#!/usr/bin/env python3
"""
Adaptive synchronization scheduler for EdgeSync
Makes intelligent decisions about when to sync data
"""

import time
import threading
import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Callable
from queue import Queue, PriorityQueue
import hashlib

from network_monitor import NetworkMonitor, NetworkCondition

@dataclass
class SyncEvent:
    """Represents a data synchronization event"""
    data_id: str
    data_size: int
    priority: int  # 1-10, higher = more important
    timestamp: float
    source_node: str
    app_type: str = "generic"  # Type of application data
    consistency_level: str = "eventual"  # eventual, strong, causal
    
    def __lt__(self, other):
        """For priority queue ordering"""
        return self.priority > other.priority  # Higher priority first

@dataclass
class SyncResult:
    """Result of a sync operation"""
    event: SyncEvent
    network_condition: NetworkCondition
    sync_duration: float
    success: bool
    error_msg: Optional[str] = None

class AdaptiveSyncScheduler:
    """
    Core adaptive synchronization scheduler
    TODO: Add ML-based prediction models
    """
    
    def __init__(self, node_id: str = "edge_node"):
        self.node_id = node_id
        self.sync_queue = PriorityQueue()
        self.network_monitor = NetworkMonitor()
        self.sync_history = []
        self.running = False
        self.sync_thread = None
        self.sync_callback = None  # Custom sync function
        
        # Adaptive parameters
        self.min_sync_interval = 1.0  # Minimum seconds between syncs
        self.max_sync_delay = 300.0   # Maximum delay in seconds
        self.batch_threshold = 5      # Number of events to batch together
        
        # Learning parameters
        self.success_rate_window = 50
        self.adaptive_weights = {
            'latency': 0.4,
            'bandwidth': 0.3,
            'priority': 0.2,
            'size': 0.1
        }
        
    def set_sync_callback(self, callback: Callable[[SyncEvent, NetworkCondition], SyncResult]):
        """Set custom sync execution function"""
        self.sync_callback = callback
        
    def should_sync_now(self, event: SyncEvent, network: NetworkCondition) -> bool:
        """
        Core decision algorithm: should we sync this event now?
        TODO: Replace with ML model
        """
        
        # Always sync critical events
        if event.priority >= 9:
            return True
            
        # Strong consistency requires immediate sync
        if event.consistency_level == "strong":
            return True
            
        # Network quality threshold
        quality_score = self._calculate_network_score(network)
        
        if quality_score < 30:  # Poor network
            return event.priority >= 8
        elif quality_score < 60:  # Average network
            return event.priority >= 6
        else:  # Good network
            return event.priority >= 4
            
    def calculate_sync_delay(self, event: SyncEvent, network: NetworkCondition) -> float:
        """
        Calculate optimal delay before sync attempt
        TODO: Add predictive modeling
        """
        base_delay = 2.0
        
        # Adjust based on network conditions
        quality_score = self._calculate_network_score(network)
        quality_factor = (100 - quality_score) / 100.0
        
        # Size-based delay
        size_factor = min(event.data_size / (1024 * 1024), 5.0)  # Max 5x for 1MB+
        
        # Priority override
        priority_factor = (11 - event.priority) / 10.0
        
        delay = base_delay * quality_factor * size_factor * priority_factor
        
        return min(max(delay, self.min_sync_interval), self.max_sync_delay)
        
    def _calculate_network_score(self, network: NetworkCondition) -> float:
        """Calculate network quality score (0-100)"""
        latency_score = max(0, 100 - (network.latency_ms / 5))
        bandwidth_score = min(100, network.bandwidth_mbps * 10)
        loss_score = max(0, 100 - (network.packet_loss * 10))
        
        return (
            latency_score * self.adaptive_weights['latency'] +
            bandwidth_score * self.adaptive_weights['bandwidth'] +
            loss_score * 0.3
        )
        
    def add_sync_event(self, event: SyncEvent):
        """Add new sync event to queue"""
        self.sync_queue.put((event.priority, time.time(), event))
        print(f"Added sync event: {event.data_id} (priority: {event.priority})")
        
    def batch_similar_events(self, events: List[SyncEvent]) -> List[List[SyncEvent]]:
        """
        Group similar events for batch processing
        TODO: Implement smart batching algorithms
        """
        if len(events) <= 1:
            return [events]
            
        # Simple batching by app type for now
        batches = {}
        for event in events:
            key = f"{event.app_type}_{event.consistency_level}"
            if key not in batches:
                batches[key] = []
            batches[key].append(event)
            
        return list(batches.values())
        
    def execute_sync(self, event: SyncEvent, network: NetworkCondition) -> SyncResult:
        """
        Execute sync operation
        TODO: Add real sync implementation with conflict resolution
        """
        start_time = time.time()
        
        if self.sync_callback:
            return self.sync_callback(event, network)
            
        # Default simulation
        print(f"[{self.node_id}] Syncing {event.data_id} "
              f"(size: {event.data_size}B, priority: {event.priority})")
        
        # Simulate network transfer time
        transfer_time = event.data_size / (network.bandwidth_mbps * 1024 * 1024 / 8)
        simulated_time = min(transfer_time + (network.latency_ms / 1000), 5.0)
        
        time.sleep(simulated_time)
        
        # Simulate occasional failures
        success = network.packet_loss < 5.0 and network.latency_ms < 1000
        
        sync_duration = time.time() - start_time
        
        result = SyncResult(
            event=event,
            network_condition=network,
            sync_duration=sync_duration,
            success=success,
            error_msg=None if success else "Network timeout"
        )
        
        self.sync_history.append(result)
        return result
        
    def process_sync_queue(self):
        """Main sync processing loop"""
        pending_events = []
        last_sync_time = 0
        
        while self.running:
            try:
                # Collect events from queue
                current_time = time.time()
                
                while not self.sync_queue.empty() and len(pending_events) < self.batch_threshold:
                    try:
                        priority, queued_time, event = self.sync_queue.get_nowait()
                        pending_events.append(event)
                    except:
                        break
                        
                if not pending_events:
                    time.sleep(0.1)
                    continue
                    
                # Get current network conditions
                network = self.network_monitor.get_current_conditions()
                
                # Process events
                events_to_sync = []
                events_to_delay = []
                
                for event in pending_events:
                    if self.should_sync_now(event, network):
                        events_to_sync.append(event)
                    else:
                        events_to_delay.append(event)
                        
                # Execute syncs
                if events_to_sync:
                    # Respect minimum sync interval
                    if current_time - last_sync_time < self.min_sync_interval:
                        time.sleep(self.min_sync_interval - (current_time - last_sync_time))
                        
                    # Batch similar events
                    batches = self.batch_similar_events(events_to_sync)
                    
                    for batch in batches:
                        for event in batch:
                            result = self.execute_sync(event, network)
                            if not result.success:
                                print(f"Sync failed for {event.data_id}: {result.error_msg}")
                                
                    last_sync_time = time.time()
                    
                # Re-queue delayed events
                for event in events_to_delay:
                    delay = self.calculate_sync_delay(event, network)
                    threading.Timer(delay, self._requeue_event, args=[event]).start()
                    
                pending_events.clear()
                
            except Exception as e:
                print(f"Error in sync processing: {e}")
                time.sleep(1)
                
    def _requeue_event(self, event: SyncEvent):
        """Re-queue a delayed event"""
        self.add_sync_event(event)
        
    def start(self):
        """Start the sync scheduler"""
        if self.running:
            return
            
        self.running = True
        self.network_monitor.start_monitoring()
        self.sync_thread = threading.Thread(target=self.process_sync_queue)
        self.sync_thread.daemon = True
        self.sync_thread.start()
        print(f"EdgeSync scheduler started for node: {self.node_id}")
        
    def stop(self):
        """Stop the sync scheduler"""
        self.running = False
        self.network_monitor.stop_monitoring()
        
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
            
        print(f"EdgeSync scheduler stopped for node: {self.node_id}")
        
    def get_performance_stats(self) -> Dict:
        """Get scheduler performance statistics"""
        if not self.sync_history:
            return {"total_syncs": 0}
            
        recent_history = self.sync_history[-self.success_rate_window:]
        
        total_syncs = len(recent_history)
        successful_syncs = sum(1 for r in recent_history if r.success)
        avg_duration = sum(r.sync_duration for r in recent_history) / total_syncs
        avg_priority = sum(r.event.priority for r in recent_history) / total_syncs
        
        return {
            "total_syncs": total_syncs,
            "success_rate": successful_syncs / total_syncs,
            "avg_sync_duration": avg_duration,
            "avg_priority": avg_priority,
            "queue_size": self.sync_queue.qsize()
        }
        
    def adjust_adaptive_weights(self, performance_feedback: Dict):
        """
        Adjust adaptive parameters based on performance
        TODO: Implement proper learning algorithm
        """
        success_rate = performance_feedback.get('success_rate', 0.5)
        
        if success_rate < 0.7:  # Poor performance
            # Be more conservative
            self.adaptive_weights['latency'] += 0.05
            self.adaptive_weights['bandwidth'] += 0.05
        elif success_rate > 0.9:  # Great performance
            # Be more aggressive
            self.adaptive_weights['priority'] += 0.05
            
        # Normalize weights
        total_weight = sum(self.adaptive_weights.values())
        if total_weight > 0:
            for key in self.adaptive_weights:
                self.adaptive_weights[key] /= total_weight

if __name__ == "__main__":
    # Basic testing
    scheduler = AdaptiveSyncScheduler("test_node")
    
    # Add some test events
    test_events = [
        SyncEvent("user_data", 1024, 8, time.time(), "edge1", "user_profile"),
        SyncEvent("sensor_reading", 256, 5, time.time(), "edge2", "iot_data"),
        SyncEvent("large_file", 1024*1024, 3, time.time(), "edge3", "file_sync")
    ]
    
    scheduler.start()
    
    for event in test_events:
        scheduler.add_sync_event(event)
        time.sleep(1)
        
    time.sleep(10)
    
    stats = scheduler.get_performance_stats()
    print("Performance Stats:", stats)
    
    scheduler.stop()
