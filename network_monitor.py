#!/usr/bin/env python3
"""
Network monitoring module for EdgeSync
Tracks network conditions between edge and cloud nodes
"""

import time
import subprocess
import statistics
import threading
from dataclasses import dataclass
from typing import List, Optional
import requests

@dataclass
class NetworkCondition:
    """Current network state"""
    latency_ms: float
    bandwidth_mbps: float
    packet_loss: float
    jitter_ms: float
    timestamp: float

class NetworkMonitor:
    """
    Monitor network conditions between edge and cloud
    TODO: Add support for multiple target hosts
    """
    
    def __init__(self, target_host="8.8.8.8", monitor_interval=5.0):
        self.target_host = target_host
        self.monitor_interval = monitor_interval
        self.conditions_history = []
        self.monitoring = False
        self.monitor_thread = None
        self.max_history = 100  # Keep last 100 measurements
        
    def measure_latency(self, samples=3):
        """Measure round-trip latency using ping"""
        latencies = []
        
        for _ in range(samples):
            try:
                result = subprocess.run([
                    'ping', '-c', '1', '-W', '2', self.target_host
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    # Parse ping output
                    for line in result.stdout.split('\n'):
                        if 'time=' in line:
                            time_str = line.split('time=')[1].split()[0]
                            latencies.append(float(time_str))
                            break
                            
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError):
                continue
                
        if not latencies:
            return 999.9  # High latency indicates problems
            
        return statistics.mean(latencies)
        
    def measure_jitter(self, samples=5):
        """Measure latency variation (jitter)"""
        latencies = []
        
        for _ in range(samples):
            try:
                result = subprocess.run([
                    'ping', '-c', '1', '-W', '1', self.target_host
                ], capture_output=True, text=True, timeout=2)
                
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'time=' in line:
                            time_str = line.split('time=')[1].split()[0]
                            latencies.append(float(time_str))
                            break
                            
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError):
                continue
                
        if len(latencies) < 2:
            return 0.0
            
        return statistics.stdev(latencies)
        
    def estimate_bandwidth(self):
        """
        Rough bandwidth estimation using HTTP download
        TODO: Use more sophisticated methods like iperf3
        """
        try:
            start_time = time.time()
            # Download small test file
            response = requests.get(
                'http://httpbin.org/bytes/8192', 
                timeout=10,
                headers={'User-Agent': 'EdgeSync-NetworkMonitor'}
            )
            end_time = time.time()
            
            if response.status_code == 200:
                duration = end_time - start_time
                bytes_transferred = len(response.content)
                
                if duration > 0:
                    bandwidth_bps = bytes_transferred / duration
                    return (bandwidth_bps * 8) / (1024 * 1024)  # Convert to Mbps
                    
        except requests.RequestException:
            pass
            
        return 1.0  # Conservative default
        
    def measure_packet_loss(self, samples=10):
        """
        Measure packet loss percentage
        TODO: Implement more sophisticated loss detection
        """
        try:
            result = subprocess.run([
                'ping', '-c', str(samples), '-W', '2', self.target_host
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'packet loss' in line:
                        loss_str = line.split('packet loss')[0].split()[-1]
                        return float(loss_str.replace('%', ''))
                        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError):
            pass
            
        return 0.0
        
    def get_current_conditions(self):
        """Get current network conditions"""
        latency = self.measure_latency()
        bandwidth = self.estimate_bandwidth()
        jitter = self.measure_jitter()
        packet_loss = self.measure_packet_loss()
        
        condition = NetworkCondition(
            latency_ms=latency,
            bandwidth_mbps=bandwidth,
            packet_loss=packet_loss,
            jitter_ms=jitter,
            timestamp=time.time()
        )
        
        # Add to history
        self.conditions_history.append(condition)
        if len(self.conditions_history) > self.max_history:
            self.conditions_history.pop(0)
            
        return condition
        
    def get_average_conditions(self, window_minutes=5):
        """Get average conditions over a time window"""
        if not self.conditions_history:
            return None
            
        cutoff_time = time.time() - (window_minutes * 60)
        recent_conditions = [
            c for c in self.conditions_history 
            if c.timestamp >= cutoff_time
        ]
        
        if not recent_conditions:
            return self.conditions_history[-1]  # Return most recent
            
        return NetworkCondition(
            latency_ms=statistics.mean(c.latency_ms for c in recent_conditions),
            bandwidth_mbps=statistics.mean(c.bandwidth_mbps for c in recent_conditions),
            packet_loss=statistics.mean(c.packet_loss for c in recent_conditions),
            jitter_ms=statistics.mean(c.jitter_ms for c in recent_conditions),
            timestamp=time.time()
        )
        
    def start_monitoring(self):
        """Start continuous network monitoring"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        print(f"Started network monitoring (target: {self.target_host})")
        
    def stop_monitoring(self):
        """Stop continuous monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("Stopped network monitoring")
        
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                self.get_current_conditions()
                time.sleep(self.monitor_interval)
            except Exception as e:
                print(f"Network monitoring error: {e}")
                time.sleep(self.monitor_interval)
                
    def get_network_quality_score(self):
        """
        Calculate a simple network quality score (0-100)
        Higher is better
        """
        if not self.conditions_history:
            return 50  # Unknown, assume average
            
        recent = self.conditions_history[-1]
        
        # Score based on latency (lower is better)
        latency_score = max(0, 100 - (recent.latency_ms / 5))
        
        # Score based on bandwidth (higher is better)
        bandwidth_score = min(100, recent.bandwidth_mbps * 10)
        
        # Score based on packet loss (lower is better)
        loss_score = max(0, 100 - (recent.packet_loss * 10))
        
        # Score based on jitter (lower is better)
        jitter_score = max(0, 100 - (recent.jitter_ms * 2))
        
        # Weighted average
        overall_score = (
            latency_score * 0.4 +
            bandwidth_score * 0.3 +
            loss_score * 0.2 +
            jitter_score * 0.1
        )
        
        return min(100, max(0, overall_score))

if __name__ == "__main__":
    # Basic testing
    monitor = NetworkMonitor()
    
    print("Testing network monitoring...")
    conditions = monitor.get_current_conditions()
    print(f"Latency: {conditions.latency_ms:.1f}ms")
    print(f"Bandwidth: {conditions.bandwidth_mbps:.1f}Mbps")
    print(f"Packet Loss: {conditions.packet_loss:.1f}%")
    print(f"Jitter: {conditions.jitter_ms:.1f}ms")
    print(f"Quality Score: {monitor.get_network_quality_score():.1f}/100")
