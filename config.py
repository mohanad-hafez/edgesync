#!/usr/bin/env python3
"""
Configuration settings for EdgeSync
TODO: Add CloudLab-specific network topology configs
"""

import os
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class NetworkConfig:
    """Network monitoring configuration"""
    default_target_host: str = "8.8.8.8"
    monitor_interval: float = 5.0
    ping_samples: int = 3
    bandwidth_test_size: int = 8192
    max_history_samples: int = 100

@dataclass
class SyncConfig:
    """Synchronization scheduler configuration"""
    min_sync_interval: float = 1.0
    max_sync_delay: float = 300.0
    batch_threshold: int = 5
    success_rate_window: int = 50
    
    # Priority thresholds for different network conditions
    priority_thresholds: Dict[str, int] = None
    
    def __post_init__(self):
        if self.priority_thresholds is None:
            self.priority_thresholds = {
                "poor_network": 8,      # Only high priority on poor network
                "average_network": 6,   # Medium+ priority on average network  
                "good_network": 4       # Low+ priority on good network
            }

@dataclass
class CloudLabConfig:
    """CloudLab-specific configuration"""
    # Multi-site setup for realistic edge-cloud testing
    sites: List[str] = None
    node_types: Dict[str, str] = None
    
    def __post_init__(self):
        if self.sites is None:
            self.sites = ["utah", "clemson", "wisconsin"]
            
        if self.node_types is None:
            self.node_types = {
                "edge": "c220g2",      # Smaller nodes for edge simulation
                "cloud": "c6420",      # Larger nodes for cloud simulation
                "storage": "r320"      # Storage-optimized nodes
            }

@dataclass
class ExperimentConfig:
    """Experiment configuration"""
    experiment_duration: int = 3600  # 1 hour default
    data_collection_interval: float = 10.0
    log_level: str = "INFO"
    results_dir: str = "results"
    
    # Workload parameters
    workload_types: List[str] = None
    
    def __post_init__(self):
        if self.workload_types is None:
            self.workload_types = [
                "user_profile",
                "sensor_data", 
                "file_sync",
                "chat_messages",
                "cache_updates"
            ]

class EdgeSyncConfig:
    """Main configuration class"""
    
    def __init__(self, config_file: str = None):
        self.network = NetworkConfig()
        self.sync = SyncConfig()
        self.cloudlab = CloudLabConfig()
        self.experiment = ExperimentConfig()
        
        # Load from file if provided
        if config_file and os.path.exists(config_file):
            self.load_from_file(config_file)
            
    def load_from_file(self, config_file: str):
        """Load configuration from JSON file"""
        import json
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
                
            # Update configurations
            if 'network' in config_data:
                for key, value in config_data['network'].items():
                    if hasattr(self.network, key):
                        setattr(self.network, key, value)
                        
            if 'sync' in config_data:
                for key, value in config_data['sync'].items():
                    if hasattr(self.sync, key):
                        setattr(self.sync, key, value)
                        
            print(f"Loaded configuration from {config_file}")
            
        except Exception as e:
            print(f"Error loading config file: {e}")
            
    def save_to_file(self, config_file: str):
        """Save current configuration to JSON file"""
        import json
        
        config_data = {
            'network': {
                'default_target_host': self.network.default_target_host,
                'monitor_interval': self.network.monitor_interval,
                'ping_samples': self.network.ping_samples,
                'bandwidth_test_size': self.network.bandwidth_test_size,
                'max_history_samples': self.network.max_history_samples
            },
            'sync': {
                'min_sync_interval': self.sync.min_sync_interval,
                'max_sync_delay': self.sync.max_sync_delay,
                'batch_threshold': self.sync.batch_threshold,
                'success_rate_window': self.sync.success_rate_window,
                'priority_thresholds': self.sync.priority_thresholds
            },
            'cloudlab': {
                'sites': self.cloudlab.sites,
                'node_types': self.cloudlab.node_types
            },
            'experiment': {
                'experiment_duration': self.experiment.experiment_duration,
                'data_collection_interval': self.experiment.data_collection_interval,
                'log_level': self.experiment.log_level,
                'results_dir': self.experiment.results_dir,
                'workload_types': self.experiment.workload_types
            }
        }
        
        try:
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            print(f"Configuration saved to {config_file}")
        except Exception as e:
            print(f"Error saving config file: {e}")
            
    def get_cloudlab_profile(self):
        """
        Generate CloudLab profile configuration
        TODO: Create actual geni-lib profile
        """
        profile_template = {
            "sites": self.cloudlab.sites,
            "nodes": {
                "edge_nodes": {
                    "count": 10,
                    "type": self.cloudlab.node_types["edge"],
                    "sites": ["utah", "clemson"]
                },
                "cloud_nodes": {
                    "count": 3,
                    "type": self.cloudlab.node_types["cloud"], 
                    "sites": ["wisconsin"]
                },
                "storage_nodes": {
                    "count": 2,
                    "type": self.cloudlab.node_types["storage"],
                    "sites": ["utah", "wisconsin"]
                }
            },
            "network": {
                "wan_emulation": True,
                "bandwidth_limits": {
                    "edge_to_cloud": "10Mbps",
                    "edge_to_edge": "100Mbps",
                    "cloud_internal": "1Gbps"
                },
                "latency_settings": {
                    "edge_to_cloud": "50ms",
                    "cross_site": "80ms"
                }
            }
        }
        
        return profile_template

# Default global config instance
config = EdgeSyncConfig()

# Environment-specific overrides
if os.getenv('EDGESYNC_ENV') == 'cloudlab':
    # CloudLab-specific settings
    config.network.default_target_host = "8.8.8.8"  # Will be overridden with actual cloud nodes
    config.experiment.results_dir = "/local/results"
    config.experiment.log_level = "DEBUG"
    
elif os.getenv('EDGESYNC_ENV') == 'local':
    # Local development settings
    config.network.monitor_interval = 2.0  # Faster monitoring for dev
    config.sync.min_sync_interval = 0.5
    config.experiment.experiment_duration = 300  # 5 minutes for quick tests

if __name__ == "__main__":
    # Demo configuration usage
    print("EdgeSync Configuration Demo")
    print("=" * 40)
    
    print(f"Network monitor interval: {config.network.monitor_interval}s")
    print(f"Sync batch threshold: {config.sync.batch_threshold}")
    print(f"CloudLab sites: {config.cloudlab.sites}")
    print(f"Experiment duration: {config.experiment.experiment_duration}s")
    
    # Save example config
    config.save_to_file("edgesync_config.json")
    
    # Show CloudLab profile
    print("\nCloudLab Profile Template:")
    import json
    print(json.dumps(config.get_cloudlab_profile(), indent=2))
