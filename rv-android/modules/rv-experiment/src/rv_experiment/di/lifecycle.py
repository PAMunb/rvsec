"""
Component Lifecycle Management - DI System Lifecycle Support

### Architectural Overview:
This module implements comprehensive component lifecycle management for the DI system,
providing standardized initialization, startup, shutdown, and cleanup operations.
It supports complex component hierarchies with proper dependency ordering and
graceful error handling throughout the lifecycle.

### Key Architectural Decisions:
- **State Machine**: Clear lifecycle state transitions with validation
- **Event-Driven**: Lifecycle events enable component coordination and monitoring
- **Dependency-Aware**: Lifecycle operations respect component dependencies
- **Error Recovery**: Robust error handling with rollback capabilities
- **Monitoring Integration**: Comprehensive logging and monitoring throughout lifecycle

### Lifecycle States:
```
CREATED → INITIALIZED → STARTED → STOPPED → DESTROYED
    ↑         ↑           ↑          ↑         ↑
    │         │           │          │         │
    │         │           └──────────┘         │
    │         └─────────────────────────────────┘
    └───────────────────────────────────────────┘
```

### Role in the System:
- Provides standardized lifecycle management for all DI components
- Coordinates complex component startup and shutdown sequences
- Enables graceful system initialization and cleanup
- Supports component health monitoring and diagnostics
- Integrates with error handling and recovery mechanisms
"""

from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass
from datetime import datetime
import threading
from collections import defaultdict

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.exceptions import ConfigurationError, ValidationError

from .interfaces import IComponentLifecycle


class LifecycleState(Enum):
    """
    Enumeration of component lifecycle states.
    
    ### State Definitions:
    - **CREATED**: Component instantiated but not yet initialized
    - **INITIALIZED**: Component configured and ready for startup
    - **STARTED**: Component actively running and processing operations
    - **STOPPED**: Component stopped gracefully and can be restarted
    - **DESTROYED**: Component cleaned up and cannot be reused
    - **ERROR**: Component in error state requiring intervention
    """
    CREATED = "created"
    INITIALIZED = "initialized" 
    STARTED = "started"
    STOPPED = "stopped"
    DESTROYED = "destroyed"
    ERROR = "error"


class LifecycleEvent(Enum):
    """
    Enumeration of lifecycle events for component coordination.
    
    ### Event Types:
    - **BEFORE_INITIALIZE**: Fired before component initialization
    - **AFTER_INITIALIZE**: Fired after successful component initialization
    - **BEFORE_START**: Fired before component startup
    - **AFTER_START**: Fired after successful component startup
    - **BEFORE_STOP**: Fired before component shutdown
    - **AFTER_STOP**: Fired after successful component shutdown
    - **BEFORE_DESTROY**: Fired before component cleanup
    - **AFTER_DESTROY**: Fired after successful component cleanup
    - **ERROR_OCCURRED**: Fired when lifecycle error occurs
    """
    BEFORE_INITIALIZE = "before_initialize"
    AFTER_INITIALIZE = "after_initialize"
    BEFORE_START = "before_start"
    AFTER_START = "after_start"
    BEFORE_STOP = "before_stop"
    AFTER_STOP = "after_stop"
    BEFORE_DESTROY = "before_destroy"
    AFTER_DESTROY = "after_destroy"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class ComponentInfo:
    """
    Information about a managed component.
    
    ### Component Tracking:
    Stores comprehensive information about each component including its
    current state, dependencies, configuration, and lifecycle history.
    This enables proper dependency ordering and lifecycle coordination.
    """
    component: IComponentLifecycle
    name: str
    state: LifecycleState
    dependencies: Set[str]
    dependents: Set[str]
    config: Dict[str, Any]
    created_at: datetime
    state_history: List[tuple]  # (state, timestamp)
    error_info: Optional[Dict[str, Any]] = None


class ComponentLifecycleManager:
    """
    Centralized manager for component lifecycle operations.
    
    ### Architectural Overview:
    This manager coordinates the lifecycle of all DI components, ensuring proper
    initialization order based on dependencies, graceful startup and shutdown
    sequences, and comprehensive error handling throughout the lifecycle.
    
    ### Key Architectural Decisions:
    - **Dependency Graph**: Maintains complete dependency graph for proper ordering
    - **Event System**: Provides lifecycle event system for component coordination
    - **Thread Safety**: All operations are thread-safe for concurrent environments
    - **Error Recovery**: Comprehensive error handling with rollback capabilities
    - **State Validation**: Validates all state transitions and prevents invalid operations
    
    ### Lifecycle Coordination:
    - Topological sorting of dependencies for proper initialization order
    - Reverse dependency order for graceful shutdown
    - Event-driven coordination between dependent components
    - Health monitoring and automatic recovery mechanisms
    - Comprehensive logging and diagnostics throughout lifecycle
    
    ### Role in the System:
    - Primary lifecycle coordinator for all DI components
    - Provides dependency-aware initialization and shutdown sequences
    - Enables component health monitoring and diagnostics
    - Supports graceful system startup and shutdown
    - Integrates with error handling and recovery systems
    """
    
    def __init__(self, logger=None):
        """
        Initialize component lifecycle manager.
        
        ### Initialization Strategy:
        - Sets up component registry and dependency tracking
        - Initializes event system for lifecycle coordination
        - Configures logging and error handling
        - Prepares manager for component registration and lifecycle operations
        
        Args:
            logger: Optional logger instance for DI container injection
        """
        # DI-ready logging setup
        if logger:
            self.logger = logger
        else:
            logging_manager = LoggingManager.get_instance()
            self.logger = logging_manager.get_logger(
                "rv_experiment.di.lifecycle",
                {CONTEXT_COMPONENT: "ComponentLifecycleManager"}
            )
        
        # Component registry and state management
        self.components: Dict[str, ComponentInfo] = {}
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        
        # Event system
        self.event_handlers: Dict[LifecycleEvent, List[Callable]] = defaultdict(list)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Manager state
        self.is_shutting_down = False
        
        self.logger.info("ComponentLifecycleManager initialized")
    
    @ErrorHandler.handle_errors(
        component="ComponentLifecycleManager",
        phase="register_component",
    )
    def register_component(self, name: str, component: IComponentLifecycle,
                          dependencies: List[str] = None,
                          config: Dict[str, Any] = None) -> None:
        """
        Register component for lifecycle management.
        
        ### Registration Strategy:
        - Validates component implements required interface
        - Records component dependencies for proper ordering
        - Updates dependency graphs for lifecycle coordination
        - Initializes component state tracking
        
        Args:
            name: Unique component name
            component: Component implementing IComponentLifecycle
            dependencies: List of component names this component depends on
            config: Component configuration dictionary
            
        Raises:
            ValueError: If component name already registered or dependencies invalid
            TypeError: If component doesn't implement IComponentLifecycle
        """
        if not isinstance(component, IComponentLifecycle):
            raise TypeError(f"Component {name} must implement IComponentLifecycle")
        
        with self._lock:
            if name in self.components:
                raise ValueError(f"Component {name} already registered")
            
            dependencies = set(dependencies or [])
            
            # Validate dependencies exist or will be registered
            # Note: We don't validate existence here to allow forward dependencies
            
            # Create component info
            component_info = ComponentInfo(
                component=component,
                name=name,
                state=LifecycleState.CREATED,
                dependencies=dependencies,
                dependents=set(),
                config=config or {},
                created_at=datetime.now(),
                state_history=[(LifecycleState.CREATED, datetime.now())]
            )
            
            self.components[name] = component_info
            
            # Update dependency graphs
            self.dependency_graph[name] = dependencies
            for dep in dependencies:
                self.reverse_dependency_graph[dep].add(name)
            
            self.logger.info(f"Registered component: {name} with dependencies: {dependencies}")
    
    def add_event_handler(self, event: LifecycleEvent, handler: Callable) -> None:
        """
        Add event handler for lifecycle events.
        
        Args:
            event: Lifecycle event to handle
            handler: Callable to handle the event
        """
        with self._lock:
            self.event_handlers[event].append(handler)
            self.logger.debug(f"Added event handler for {event.value}")
    
    def _fire_event(self, event: LifecycleEvent, component_name: str, 
                   **kwargs) -> None:
        """
        Fire lifecycle event to all registered handlers.
        
        Args:
            event: Lifecycle event to fire
            component_name: Name of component the event relates to
            **kwargs: Additional event data
        """
        handlers = self.event_handlers.get(event, [])
        for handler in handlers:
            try:
                handler(event, component_name, **kwargs)
            except Exception as e:
                self.logger.warning(f"Event handler error for {event.value}: {e}")
    
    def _update_component_state(self, component_name: str, 
                               new_state: LifecycleState,
                               error_info: Dict[str, Any] = None) -> None:
        """
        Update component state and record history.
        
        Args:
            component_name: Name of component to update
            new_state: New lifecycle state
            error_info: Optional error information if state is ERROR
        """
        component_info = self.components[component_name]
        old_state = component_info.state
        
        component_info.state = new_state
        component_info.state_history.append((new_state, datetime.now()))
        
        if error_info:
            component_info.error_info = error_info
        
        self.logger.debug(f"Component {component_name}: {old_state.value} → {new_state.value}")
    
    def _get_initialization_order(self) -> List[str]:
        """
        Get component initialization order based on dependencies.
        
        Returns:
            List of component names in initialization order
            
        Raises:
            ConfigurationError: If circular dependencies detected
        """
        # Topological sort using Kahn's algorithm
        in_degree = defaultdict(int)
        for component in self.components:
            in_degree[component] = len(self.dependency_graph[component])
        
        # Start with components that have no dependencies
        queue = [comp for comp in self.components if in_degree[comp] == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            # Update in-degrees of dependents
            for dependent in self.reverse_dependency_graph[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        # Check for circular dependencies
        if len(result) != len(self.components):
            remaining = set(self.components.keys()) - set(result)
            raise ConfigurationError(f"Circular dependencies detected: {remaining}")
        
        return result
    
    @ErrorHandler.handle_errors(
        component="ComponentLifecycleManager",
        phase="initialize_all",
    )
    def initialize_all(self) -> bool:
        """
        Initialize all registered components in dependency order.
        
        ### Initialization Strategy:
        - Calculates proper initialization order using topological sort
        - Initializes components in dependency order with error handling
        - Fires lifecycle events for coordination
        - Provides rollback on failure
        
        Returns:
            True if all components initialized successfully, False otherwise
        """
        with self._lock:
            if self.is_shutting_down:
                self.logger.warning("Cannot initialize during shutdown")
                return False
            
            self.logger.info("Starting component initialization")
            
            try:
                initialization_order = self._get_initialization_order()
                initialized_components = []
                
                for component_name in initialization_order:
                    component_info = self.components[component_name]
                    
                    if component_info.state != LifecycleState.CREATED:
                        self.logger.warning(f"Component {component_name} not in CREATED state: {component_info.state}")
                        continue
                    
                    self.logger.info(f"Initializing component: {component_name}")
                    
                    # Fire before event
                    self._fire_event(LifecycleEvent.BEFORE_INITIALIZE, component_name)
                    
                    try:
                        # Initialize component
                        success = component_info.component.initialize(component_info.config)
                        
                        if success:
                            self._update_component_state(component_name, LifecycleState.INITIALIZED)
                            initialized_components.append(component_name)
                            
                            # Fire after event
                            self._fire_event(LifecycleEvent.AFTER_INITIALIZE, component_name)
                            
                            self.logger.info(f"Successfully initialized component: {component_name}")
                        else:
                            self._update_component_state(component_name, LifecycleState.ERROR,
                                                       {"error": "Component initialization returned False"})
                            self._fire_event(LifecycleEvent.ERROR_OCCURRED, component_name)
                            
                            # Rollback initialized components
                            self._rollback_initialization(initialized_components)
                            return False
                            
                    except Exception as e:
                        error_info = {"error": str(e), "exception_type": type(e).__name__}
                        self._update_component_state(component_name, LifecycleState.ERROR, error_info)
                        self._fire_event(LifecycleEvent.ERROR_OCCURRED, component_name, error=e)
                        
                        self.logger.error(f"Failed to initialize component {component_name}: {e}")
                        
                        # Rollback initialized components
                        self._rollback_initialization(initialized_components)
                        return False
                
                self.logger.info("All components initialized successfully")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to initialize components: {e}")
                return False
    
    def _rollback_initialization(self, initialized_components: List[str]) -> None:
        """
        Rollback initialization of components in reverse order.
        
        Args:
            initialized_components: List of components to rollback
        """
        self.logger.warning("Rolling back component initialization")
        
        for component_name in reversed(initialized_components):
            try:
                component_info = self.components[component_name]
                component_info.component.destroy()
                self._update_component_state(component_name, LifecycleState.CREATED)
                self.logger.debug(f"Rolled back component: {component_name}")
            except Exception as e:
                self.logger.error(f"Failed to rollback component {component_name}: {e}")
    
    @ErrorHandler.handle_errors(
        component="ComponentLifecycleManager",
        phase="start_all",
    )
    def start_all(self) -> bool:
        """
        Start all initialized components.
        
        Returns:
            True if all components started successfully, False otherwise
        """
        with self._lock:
            if self.is_shutting_down:
                self.logger.warning("Cannot start during shutdown")
                return False
            
            self.logger.info("Starting all components")
            
            # Get components in initialization order
            try:
                start_order = self._get_initialization_order()
                started_components = []
                
                for component_name in start_order:
                    component_info = self.components[component_name]
                    
                    if component_info.state != LifecycleState.INITIALIZED:
                        self.logger.warning(f"Component {component_name} not in INITIALIZED state: {component_info.state}")
                        continue
                    
                    self.logger.info(f"Starting component: {component_name}")
                    
                    # Fire before event
                    self._fire_event(LifecycleEvent.BEFORE_START, component_name)
                    
                    try:
                        success = component_info.component.start()
                        
                        if success:
                            self._update_component_state(component_name, LifecycleState.STARTED)
                            started_components.append(component_name)
                            
                            # Fire after event
                            self._fire_event(LifecycleEvent.AFTER_START, component_name)
                            
                            self.logger.info(f"Successfully started component: {component_name}")
                        else:
                            self._update_component_state(component_name, LifecycleState.ERROR,
                                                       {"error": "Component start returned False"})
                            self._fire_event(LifecycleEvent.ERROR_OCCURRED, component_name)
                            return False
                            
                    except Exception as e:
                        error_info = {"error": str(e), "exception_type": type(e).__name__}
                        self._update_component_state(component_name, LifecycleState.ERROR, error_info)
                        self._fire_event(LifecycleEvent.ERROR_OCCURRED, component_name, error=e)
                        
                        self.logger.error(f"Failed to start component {component_name}: {e}")
                        return False
                
                self.logger.info("All components started successfully")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to start components: {e}")
                return False
    
    @ErrorHandler.handle_errors(
        component="ComponentLifecycleManager",
        phase="stop_all",
    )
    def stop_all(self) -> bool:
        """
        Stop all started components in reverse dependency order.
        
        Returns:
            True if all components stopped successfully, False otherwise
        """
        with self._lock:
            self.is_shutting_down = True
            
            self.logger.info("Stopping all components")
            
            try:
                # Get components in reverse initialization order
                stop_order = list(reversed(self._get_initialization_order()))
                
                for component_name in stop_order:
                    component_info = self.components[component_name]
                    
                    if component_info.state != LifecycleState.STARTED:
                        continue
                    
                    self.logger.info(f"Stopping component: {component_name}")
                    
                    # Fire before event
                    self._fire_event(LifecycleEvent.BEFORE_STOP, component_name)
                    
                    try:
                        success = component_info.component.stop()
                        
                        if success:
                            self._update_component_state(component_name, LifecycleState.STOPPED)
                            
                            # Fire after event
                            self._fire_event(LifecycleEvent.AFTER_STOP, component_name)
                            
                            self.logger.info(f"Successfully stopped component: {component_name}")
                        else:
                            self.logger.warning(f"Component {component_name} stop returned False")
                            
                    except Exception as e:
                        error_info = {"error": str(e), "exception_type": type(e).__name__}
                        self._update_component_state(component_name, LifecycleState.ERROR, error_info)
                        self._fire_event(LifecycleEvent.ERROR_OCCURRED, component_name, error=e)
                        
                        self.logger.error(f"Failed to stop component {component_name}: {e}")
                
                self.logger.info("Component shutdown completed")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to stop components: {e}")
                return False
            finally:
                self.is_shutting_down = False
    
    def get_component_state(self, component_name: str) -> Optional[LifecycleState]:
        """
        Get current state of component.
        
        Args:
            component_name: Name of component to check
            
        Returns:
            Current component state or None if not found
        """
        with self._lock:
            component_info = self.components.get(component_name)
            return component_info.state if component_info else None
    
    def get_all_component_states(self) -> Dict[str, LifecycleState]:
        """
        Get states of all registered components.
        
        Returns:
            Dictionary mapping component names to their current states
        """
        with self._lock:
            return {name: info.state for name, info in self.components.items()}
    
    def get_healthy_components(self) -> List[str]:
        """
        Get list of components in healthy states.
        
        Returns:
            List of component names in healthy states
        """
        healthy_states = {LifecycleState.INITIALIZED, LifecycleState.STARTED}
        
        with self._lock:
            healthy_components = []
            for name, info in self.components.items():
                if info.state in healthy_states:
                    try:
                        if info.component.is_healthy():
                            healthy_components.append(name)
                    except Exception as e:
                        self.logger.warning(f"Health check failed for {name}: {e}")
            
            return healthy_components
    
    def get_component_info(self, component_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about component.
        
        Args:
            component_name: Name of component to get info for
            
        Returns:
            Component information dictionary or None if not found
        """
        with self._lock:
            component_info = self.components.get(component_name)
            if not component_info:
                return None
            
            return {
                "name": component_info.name,
                "state": component_info.state.value,
                "dependencies": list(component_info.dependencies),
                "dependents": list(component_info.dependents),
                "created_at": component_info.created_at.isoformat(),
                "state_history": [(state.value, timestamp.isoformat()) 
                                for state, timestamp in component_info.state_history],
                "error_info": component_info.error_info,
                "is_healthy": self._check_component_health(component_name)
            }
    
    def _check_component_health(self, component_name: str) -> bool:
        """
        Check health of specific component.
        
        Args:
            component_name: Name of component to check
            
        Returns:
            True if component is healthy, False otherwise
        """
        try:
            component_info = self.components.get(component_name)
            if not component_info:
                return False
            
            return component_info.component.is_healthy()
        except Exception:
            return False