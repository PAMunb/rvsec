# rvandroid/rvdroid/orchestration/resources.py

"""
Resource management for RVDroid.

This module provides components for monitoring and managing system resources,
ensuring efficient operation during testing and preventing resource exhaustion.
"""

import os
import time
import threading
import psutil
from typing import Dict, Any, Optional, Callable, List, Tuple

from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.performance_monitor import PerformanceMonitor


class ResourceThreshold:
    """
    Threshold settings for resource monitoring.
    
    These values define warning and critical thresholds for 
    different system resources.
    """
    # Memory thresholds (percentage of system memory)
    MEMORY_WARNING = 80.0
    MEMORY_CRITICAL = 90.0
    
    # CPU thresholds (percentage of CPU utilization)
    CPU_WARNING = 85.0
    CPU_CRITICAL = 95.0
    
    # Disk thresholds (percentage of disk space used)
    DISK_WARNING = 85.0
    DISK_CRITICAL = 95.0
    
    # Thread count thresholds
    THREAD_WARNING = 50
    THREAD_CRITICAL = 80


class ResourceManager:
    """
    Manager for system resource monitoring and optimization.
    
    ### Architectural Decisions:
    - Implements a centralized resource monitoring system
    - Uses background thread for continual resource assessment
    - Provides automatic throttling to prevent resource exhaustion
    - Supports notification callbacks for resource-related events
    - Implements adaptive resource allocation based on system load
    
    ### Role in the System:
    - Monitors system resources during test execution
    - Prevents resource exhaustion that could impact testing
    - Provides early warning for potential performance issues
    - Enables adaptive execution based on available resources
    - Collects resource utilization metrics for analysis
    """
    
    def __init__(self, monitoring_interval: float = 5.0):
        """
        Initialize the resource manager.
        
        Args:
            monitoring_interval: Interval in seconds between resource checks
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.orchestration.resources",
            {CONTEXT_COMPONENT: "ResourceManager"}
        )
        
        # Initialize performance monitoring
        self.performance_monitor = PerformanceMonitor.get_instance()
        
        # Set monitoring parameters
        self.monitoring_interval = monitoring_interval
        self.running = False
        self.monitor_thread = None
        
        # Initialize resource trackers
        self.current_resources = {
            "memory_percent": 0.0,
            "system_memory_percent": 0.0,  # Add system memory percentage
            "cpu_percent": 0.0,
            "system_cpu_percent": 0.0,     # Add system CPU percentage
            "disk_percent": 0.0,
            "thread_count": 0,
            "io_counters": None,
            "timestamp": 0.0
        }
        
        # Resource history for trend analysis
        self.resource_history = []
        self.history_size = 12  # Keep last ~1 minute of history (assuming 5s interval)
        
        # Throttling state
        self.throttling_active = False
        self.throttling_level = 0  # 0=none, 1=light, 2=moderate, 3=severe
        
        # Callback registry
        self.threshold_callbacks = {
            "memory_warning": [],
            "memory_critical": [],
            "cpu_warning": [],
            "cpu_critical": [],
            "disk_warning": [],
            "disk_critical": [],
            "thread_warning": [],
            "thread_critical": []
        }
        
        self.logger.info("Resource manager initialized")
    
    def start_monitoring(self) -> bool:
        """
        Start resource monitoring in a background thread.
        
        Returns:
            True if started, False if already running
        """
        if self.running:
            self.logger.warning("Resource monitoring already running")
            return False
        
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="ResourceMonitor"
        )
        self.monitor_thread.start()
        
        self.logger.info("Resource monitoring started")
        return True
    
    def stop_monitoring(self) -> None:
        """
        Stop resource monitoring.
        """
        self.running = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
            
        self.logger.info("Resource monitoring stopped")
    
    def register_threshold_callback(self, resource_type: str, severity: str, 
                                   callback: Callable[[Dict[str, Any]], None]) -> bool:
        """
        Register a callback for resource threshold events.
        
        Args:
            resource_type: Resource type ('memory', 'cpu', 'disk', 'thread')
            severity: Threshold severity ('warning', 'critical')
            callback: Function to call when threshold is crossed
            
        Returns:
            True if registered, False if invalid type/severity
        """
        callback_key = f"{resource_type}_{severity}"
        
        if callback_key in self.threshold_callbacks:
            self.threshold_callbacks[callback_key].append(callback)
            self.logger.debug(f"Registered callback for {callback_key}")
            return True
        else:
            self.logger.warning(f"Invalid resource type or severity: {callback_key}")
            return False
    
    def get_current_resources(self) -> Dict[str, Any]:
        """
        Get current resource utilization.
        
        Returns:
            Dictionary with current resource stats
        """
        return dict(self.current_resources)
    
    def get_resource_history(self) -> List[Dict[str, Any]]:
        """
        Get resource utilization history.
        
        Returns:
            List of resource snapshots
        """
        return list(self.resource_history)
    
    def is_throttling_active(self) -> bool:
        """
        Check if resource throttling is active.
        
        Returns:
            True if throttling is active, False otherwise
        """
        return self.throttling_active
    
    def get_throttling_level(self) -> int:
        """
        Get current throttling level.
        
        Returns:
            Throttling level (0=none, 1=light, 2=moderate, 3=severe)
        """
        return self.throttling_level
    
    def get_recommended_delay(self) -> float:
        """
        Get recommended delay between operations based on system load.
        
        Returns:
            Recommended delay in seconds
        """
        if not self.throttling_active:
            return 0.1  # Base delay
        
        # Scale delay based on throttling level
        if self.throttling_level == 1:
            return 0.5  # Light throttling
        elif self.throttling_level == 2:
            return 1.0  # Moderate throttling
        elif self.throttling_level == 3:
            return 2.0  # Severe throttling
        
        return 0.1  # Default
    
    def _monitoring_loop(self) -> None:
        """
        Main monitoring loop that runs in a background thread.
        """
        try:
            while self.running:
                # Measure resource utilization
                with self.performance_monitor.measure_time("resource_check"):
                    self._check_resources()
                
                # Add to history
                self._update_history()
                
                # Check thresholds and trigger callbacks if needed
                self._check_thresholds()
                
                # Update throttling state
                self._update_throttling()
                
                # Sleep until next check
                time.sleep(self.monitoring_interval)
                
        except Exception as e:
            self.logger.error(f"Error in resource monitoring loop: {e}")
            self.running = False
    
    def _check_resources(self) -> None:
        """
        Check current resource utilization.
        """
        try:
            # Get process stats
            process = psutil.Process(os.getpid())
            process_stats = process.as_dict(attrs=['cpu_percent', 'memory_percent', 'num_threads', 'io_counters'])
            
            # Get system stats
            system_memory = psutil.virtual_memory().percent
            system_cpu = psutil.cpu_percent()
            
            # Get disk usage for current directory
            disk_usage = psutil.disk_usage(os.getcwd()).percent
            
            # Update current resources
            self.current_resources = {
                "memory_percent": process_stats['memory_percent'],
                "system_memory_percent": system_memory,
                "cpu_percent": process_stats['cpu_percent'],
                "system_cpu_percent": system_cpu,
                "disk_percent": disk_usage,
                "thread_count": process_stats['num_threads'],
                "io_counters": process_stats['io_counters'],
                "timestamp": time.time()
            }
        except Exception as e:
            self.logger.error(f"Error checking resources: {e}")
    
    def _update_history(self) -> None:
        """
        Update resource history with current snapshot.
        """
        # Add current snapshot to history
        self.resource_history.append(dict(self.current_resources))
        
        # Trim history if needed
        if len(self.resource_history) > self.history_size:
            self.resource_history = self.resource_history[-self.history_size:]
    
    def _check_thresholds(self) -> None:
        """
        Check if any resource thresholds have been crossed.
        """
        resources = self.current_resources
        
        # Check memory thresholds
        if resources['system_memory_percent'] >= ResourceThreshold.MEMORY_CRITICAL:
            self._trigger_threshold_callbacks("memory_critical", resources)
        elif resources['system_memory_percent'] >= ResourceThreshold.MEMORY_WARNING:
            self._trigger_threshold_callbacks("memory_warning", resources)
        
        # Check CPU thresholds
        if resources['system_cpu_percent'] >= ResourceThreshold.CPU_CRITICAL:
            self._trigger_threshold_callbacks("cpu_critical", resources)
        elif resources['system_cpu_percent'] >= ResourceThreshold.CPU_WARNING:
            self._trigger_threshold_callbacks("cpu_warning", resources)
        
        # Check disk thresholds
        if resources['disk_percent'] >= ResourceThreshold.DISK_CRITICAL:
            self._trigger_threshold_callbacks("disk_critical", resources)
        elif resources['disk_percent'] >= ResourceThreshold.DISK_WARNING:
            self._trigger_threshold_callbacks("disk_warning", resources)
        
        # Check thread thresholds
        if resources['thread_count'] >= ResourceThreshold.THREAD_CRITICAL:
            self._trigger_threshold_callbacks("thread_critical", resources)
        elif resources['thread_count'] >= ResourceThreshold.THREAD_WARNING:
            self._trigger_threshold_callbacks("thread_warning", resources)
    
    def _trigger_threshold_callbacks(self, threshold_key: str, resources: Dict[str, Any]) -> None:
        """
        Trigger callbacks for a specific threshold.
        
        Args:
            threshold_key: The threshold key (e.g., 'memory_warning')
            resources: Current resource statistics
        """
        for callback in self.threshold_callbacks.get(threshold_key, []):
            try:
                callback(resources)
            except Exception as e:
                self.logger.error(f"Error in {threshold_key} callback: {e}")
    
    def _update_throttling(self) -> None:
        """
        Update throttling state based on resource utilization.
        """
        resources = self.current_resources
        old_throttling_level = self.throttling_level
        
        # Check for critical thresholds (severe throttling)
        if (resources['system_memory_percent'] >= ResourceThreshold.MEMORY_CRITICAL or
                resources['system_cpu_percent'] >= ResourceThreshold.CPU_CRITICAL):
            self.throttling_active = True
            self.throttling_level = 3
        
        # Check for warning thresholds (moderate throttling)
        elif (resources['system_memory_percent'] >= ResourceThreshold.MEMORY_WARNING or
              resources['system_cpu_percent'] >= ResourceThreshold.CPU_WARNING):
            self.throttling_active = True
            self.throttling_level = 2
        
        # Check for mild load (light throttling)
        elif (resources['system_memory_percent'] >= ResourceThreshold.MEMORY_WARNING * 0.8 or
              resources['system_cpu_percent'] >= ResourceThreshold.CPU_WARNING * 0.8):
            self.throttling_active = True
            self.throttling_level = 1
        
        # Normal operation
        else:
            self.throttling_active = False
            self.throttling_level = 0
        
        # Log throttling changes
        if old_throttling_level != self.throttling_level:
            if self.throttling_level > 0:
                self.logger.info(f"Resource throttling activated: level {self.throttling_level}")
            else:
                self.logger.info("Resource throttling deactivated")
    
    def get_resource_recommendations(self) -> Dict[str, Any]:
        """
        Get recommendations for resource optimization.
        
        Returns:
            Dictionary with resource optimization recommendations
        """
        resources = self.current_resources
        recommendations = {
            "action_delay": self.get_recommended_delay(),
            "reduce_screenshot_frequency": False,
            "disable_llm": False,
            "reduce_history_size": False,
            "throttle_logging": False
        }
        
        # Ensure all required keys exist in resources
        if 'system_memory_percent' not in resources:
            # Initialize with safe default values if monitoring hasn't started yet
            self.logger.warning("System memory percent not found in resources, initializing with default values")
            resources['system_memory_percent'] = 0.0
            resources['system_cpu_percent'] = 0.0
            # If we're initializing these values, make sure we also initialize them in current_resources
            self.current_resources['system_memory_percent'] = 0.0
            self.current_resources['system_cpu_percent'] = 0.0
            
        # Check for critical resource conditions
        if resources['system_memory_percent'] >= ResourceThreshold.MEMORY_CRITICAL:
            recommendations["reduce_history_size"] = True
            recommendations["disable_llm"] = True
            recommendations["reduce_screenshot_frequency"] = True
            recommendations["throttle_logging"] = True
        
        elif resources['system_memory_percent'] >= ResourceThreshold.MEMORY_WARNING:
            recommendations["reduce_history_size"] = True
            recommendations["reduce_screenshot_frequency"] = True
        
        # Add additional recommendations based on CPU
        if resources['system_cpu_percent'] >= ResourceThreshold.CPU_CRITICAL:
            recommendations["action_delay"] *= 2  # Double the delay
            recommendations["disable_llm"] = True
        
        return recommendations
        
    def get_resource_status(self) -> Dict[str, Any]:
        """
        Get a simplified resource status for component use.
        
        Returns:
            Dictionary with key resource metrics
        """
        # Calculate normalized resource usage (0.0-1.0)
        memory_usage = self.current_resources.get('system_memory_percent', 0.0) / 100.0
        cpu_usage = self.current_resources.get('system_cpu_percent', 0.0) / 100.0
        
        return {
            "memory_usage": memory_usage,
            "cpu_usage": cpu_usage,
            "throttling_level": self.throttling_level,
            "timestamp": self.current_resources.get('timestamp', time.time())
        }
        
    def should_throttle_operation(self, operation_type: str) -> bool:
        """
        Determine if a specific operation should be throttled.
        
        Args:
            operation_type: Type of operation to check
                ('llm_query', 'screenshot', 'action', etc.)
                
        Returns:
            True if operation should be throttled, False otherwise
        """
        # Different throttling criteria based on operation type
        if operation_type == "llm_query":
            # LLM queries are resource-intensive, throttle aggressively
            return self.throttling_level >= 2
            
        elif operation_type == "screenshot":
            # Screenshots are moderately resource-intensive
            return self.throttling_level >= 1
            
        elif operation_type == "analysis":
            # Analysis operations are throttled under severe conditions
            return self.throttling_level >= 3
            
        elif operation_type == "action":
            # Actions are only throttled under severe conditions
            return self.throttling_level >= 3
            
        # Default is not to throttle
        return False
        
    def cleanup(self) -> None:
        """
        Clean up resource manager resources.
        """
        self.stop_monitoring()
        self.logger.info("Resource manager cleaned up")