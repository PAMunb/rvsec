# rvandroid/experiment/core/context.py
"""
Context implementation for the unified execution framework.

This module provides the ExecutionContext class, which serves as a shared state
container for experiment workflows. The context is used to share configuration,
state, and results between different components of the workflow.
"""

import os
import threading
from typing import Dict, Any, Optional

from rvandroid.experiment.core.interfaces import IExecutionContext
from rvandroid.experiment.event import EventBus, get_event_bus
from rvandroid.util.logging.manager import LoggingManager


class ExecutionContext(IExecutionContext):
    """
    Execution context for experiment workflows.
    
    ### Architectural Decisions:
    - Implements a thread-safe, dictionary-based state container
    - Provides type-safe accessors for common context values
    - Supports hierarchical data structures with dot notation
    - Enables centralized state management for the entire workflow
    
    ### Role in the System:
    - Provides a shared state container for workflow execution
    - Enables communication between workflow components
    - Preserves state across workflow phases
    - Supports serialization and deserialization for persistence
    """
    
    def __init__(self, 
                experiment_id: str, 
                results_dir: str, 
                event_bus: Optional[EventBus] = None):
        """
        Initialize the execution context.
        
        Args:
            experiment_id: Unique identifier for the experiment
            results_dir: Directory where results will be stored
            event_bus: Event bus for communication (created if not provided)
        """
        self._experiment_id = experiment_id
        self._results_dir = results_dir
        self._event_bus = event_bus or get_event_bus()
        self._data: Dict[str, Any] = {}
        self._lock = threading.RLock()
        
        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'experiment.core.context',
            {
                'experiment_id': experiment_id,
                'component': 'ExecutionContext'
            }
        )
        
        # Ensure results directory exists
        os.makedirs(results_dir, exist_ok=True)
        
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the context.
        
        Supports hierarchical keys with dot notation (e.g., "config.timeout").
        
        Args:
            key: Key to retrieve
            default: Default value if key doesn't exist
            
        Returns:
            Value associated with the key, or default if not found
        """
        with self._lock:
            # Handle hierarchical keys
            if '.' in key:
                parts = key.split('.')
                current = self._data
                for part in parts[:-1]:
                    if part not in current or not isinstance(current[part], dict):
                        return default
                    current = current[part]
                return current.get(parts[-1], default)
            
            return self._data.get(key, default)
            
    def set(self, key: str, value: Any) -> None:
        """
        Set a value in the context.
        
        Supports hierarchical keys with dot notation (e.g., "config.timeout").
        Creates intermediate dictionaries if they don't exist.
        
        Args:
            key: Key to set
            value: Value to associate with the key
        """
        with self._lock:
            # Handle hierarchical keys
            if '.' in key:
                parts = key.split('.')
                current = self._data
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    elif not isinstance(current[part], dict):
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
            else:
                self._data[key] = value
                
    def has(self, key: str) -> bool:
        """
        Check if a key exists in the context.
        
        Supports hierarchical keys with dot notation (e.g., "config.timeout").
        
        Args:
            key: Key to check
            
        Returns:
            True if the key exists, False otherwise
        """
        with self._lock:
            # Handle hierarchical keys
            if '.' in key:
                parts = key.split('.')
                current = self._data
                for part in parts[:-1]:
                    if part not in current or not isinstance(current[part], dict):
                        return False
                    current = current[part]
                return parts[-1] in current
            
            return key in self._data
            
    def delete(self, key: str) -> None:
        """
        Delete a key from the context.
        
        Supports hierarchical keys with dot notation (e.g., "config.timeout").
        
        Args:
            key: Key to delete
        """
        with self._lock:
            # Handle hierarchical keys
            if '.' in key:
                parts = key.split('.')
                current = self._data
                for part in parts[:-1]:
                    if part not in current or not isinstance(current[part], dict):
                        return
                    current = current[part]
                if parts[-1] in current:
                    del current[parts[-1]]
            elif key in self._data:
                del self._data[key]
                
    def get_all(self) -> Dict[str, Any]:
        """
        Get all values from the context.
        
        Returns:
            Dictionary containing all key-value pairs in the context
        """
        with self._lock:
            # Return a copy to prevent external modification
            return self._data.copy()
            
    def clear(self) -> None:
        """Clear the context."""
        with self._lock:
            self._data.clear()
            
    def merge(self, other: Dict[str, Any]) -> None:
        """
        Merge another dictionary into the context.
        
        Performs a deep merge, preserving nested structures.
        
        Args:
            other: Dictionary to merge
        """
        with self._lock:
            self._deep_merge(self._data, other)
            
    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Recursively merge two dictionaries.
        
        Args:
            target: Target dictionary to merge into
            source: Source dictionary to merge from
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value
                
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the context to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the context
        """
        with self._lock:
            result = self._data.copy()
            result['_experiment_id'] = self._experiment_id
            result['_results_dir'] = self._results_dir
            return result
            
    @classmethod
    def from_dict(cls, data: Dict[str, Any], event_bus: Optional[EventBus] = None) -> 'ExecutionContext':
        """
        Create a context from a dictionary.
        
        Args:
            data: Dictionary with context data
            event_bus: Optional event bus
            
        Returns:
            New context instance
        """
        experiment_id = data.pop('_experiment_id', f"experiment_{id(data)}")
        results_dir = data.pop('_results_dir', os.path.join(os.getcwd(), 'results', experiment_id))
        
        context = cls(experiment_id, results_dir, event_bus)
        context._data = data
        return context
    
    # Typed property accessors
    
    @property
    def experiment_id(self) -> str:
        """
        Get the experiment ID.
        
        Returns:
            Experiment ID
        """
        return self._experiment_id
        
    @property
    def results_dir(self) -> str:
        """
        Get the results directory.
        
        Returns:
            Path to results directory
        """
        return self._results_dir
        
    @property
    def event_bus(self) -> EventBus:
        """
        Get the event bus.
        
        Returns:
            Event bus instance
        """
        return self._event_bus
        
    def get_int(self, key: str, default: int = 0) -> int:
        """
        Get an integer value from the context.
        
        Args:
            key: Key to retrieve
            default: Default value if key doesn't exist or isn't an integer
            
        Returns:
            Integer value
        """
        value = self.get(key, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
            
    def get_float(self, key: str, default: float = 0.0) -> float:
        """
        Get a float value from the context.
        
        Args:
            key: Key to retrieve
            default: Default value if key doesn't exist or isn't a float
            
        Returns:
            Float value
        """
        value = self.get(key, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
            
    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        Get a boolean value from the context.
        
        Args:
            key: Key to retrieve
            default: Default value if key doesn't exist or isn't a boolean
            
        Returns:
            Boolean value
        """
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', 'on', 'y')
        return default
        
    def get_str(self, key: str, default: str = "") -> str:
        """
        Get a string value from the context.
        
        Args:
            key: Key to retrieve
            default: Default value if key doesn't exist
            
        Returns:
            String value
        """
        value = self.get(key, default)
        if value is None:
            return default
        return str(value)
        
    def get_list(self, key: str, default: Optional[list] = None) -> list:
        """
        Get a list value from the context.
        
        Args:
            key: Key to retrieve
            default: Default value if key doesn't exist or isn't a list
            
        Returns:
            List value
        """
        if default is None:
            default = []
            
        value = self.get(key, default)
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        if isinstance(value, str) and ',' in value:
            return [item.strip() for item in value.split(',')]
        return default
        
    def get_dict(self, key: str, default: Optional[dict] = None) -> dict:
        """
        Get a dictionary value from the context.
        
        Args:
            key: Key to retrieve
            default: Default value if key doesn't exist or isn't a dictionary
            
        Returns:
            Dictionary value
        """
        if default is None:
            default = {}
            
        value = self.get(key, default)
        if isinstance(value, dict):
            return value
        return default