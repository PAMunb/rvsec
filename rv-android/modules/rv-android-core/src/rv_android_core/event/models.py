"""
Event models for RV-Android Core system.

This module provides validated event models for representing system events
with comprehensive type safety and standardized event lifecycle management.
"""

import threading
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional
from pydantic import Field

from rv_android_core.util.validation.base import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model


class EventPriority:
    """
    Standard priority levels for event processing.
    
    ### Architectural Decisions:
    - Uses integer constants for PriorityQueue compatibility
    - Lower values indicate higher priority (standard queue convention)
    - Provides standard levels for consistent usage across system
    - Enables priority-based event processing and routing
    
    ### Priority Levels:
    - CRITICAL: System-critical events requiring immediate processing
    - HIGH: Important lifecycle and error events
    - NORMAL: Standard operational events (default)
    - LOW: Background and informational events
    - BACKGROUND: Lowest priority events (logging, metrics)
    """
    
    CRITICAL = 0     # System-critical events requiring immediate processing
    HIGH = 10        # Important lifecycle and error events
    NORMAL = 50      # Standard operational events (default)
    LOW = 90         # Background and informational events
    BACKGROUND = 100 # Lowest priority events (logging, metrics)


class EventChannel(Enum):
    """
    Enumeration of event channels for organized event routing.
    
    ### Architectural Decisions:
    - Provides type safety for channel specification
    - Enables IDE autocomplete and validation
    - Supports clear channel responsibility documentation
    - Prevents runtime errors from invalid channel names
    
    ### Channel Responsibilities:
    - DEFAULT: General system events without specific category
    - LIFECYCLE: Task and experiment lifecycle events (including coverage and MOP events)
    - ANALYSIS: General analysis results and static analysis events
    - ERROR: Error events and exception handling notifications
    """
    
    DEFAULT = "default"      # General system events
    LIFECYCLE = "lifecycle"  # Task and experiment lifecycle events
    ANALYSIS = "analysis"    # General analysis results events
    ERROR = "error"         # Error and exception events


class EventType(Enum):
    """
    Enumeration of all event types supported by the RV-Android system.
    
    ### Architectural Decisions:
    - Uses auto() for automatic value assignment to prevent conflicts
    - Groups events by functional category for better organization
    - Supports both lifecycle and analysis event types
    - Enables extensible event system with clear categorization
    
    ### Event Categories:
    - Task lifecycle: Creation, execution, completion states
    - Experiment lifecycle: Overall experiment management
    - Analysis: Coverage, error detection, static analysis results
    - Environment: Emulator, app, and tool management
    - Configuration: System configuration changes
    
    ### Serialization Warning:
    This enum uses auto() for value assignment. The integer values are NOT
    guaranteed to be stable across code changes. Do NOT persist or serialize
    the integer values directly. Use the enum name (.name) for persistence.
    
    Example:
        # Correct for persistence
        event_name = event.type.name  # "TASK_STARTED"
        
        # Incorrect for persistence
        event_value = event.type.value  # 3 (may change)
    """
    
    # Task lifecycle events
    TASK_CREATED = auto()           # Task instance created in the system. Typical: Task configuration completed
    TASK_CONFIGURED = auto()        # Task configuration validated and applied. Typical: Before task execution
    TASK_STARTED = auto()           # Task execution initiated. Typical: Tool execution begins
    TASK_COMPLETED = auto()         # Task execution completed successfully. Typical: All analysis finished
    TASK_FAILED = auto()            # Task execution failed with error. Typical: Tool failure or timeout
    
    # Experiment lifecycle events
    EXPERIMENT_STARTED = auto()     # Experiment execution initiated. Typical: First task starts
    EXPERIMENT_COMPLETED = auto()   # Experiment execution completed successfully. Typical: All tasks finished
    EXPERIMENT_FAILED = auto()      # Experiment execution failed with error. Typical: Critical failure
    EXPERIMENT_PAUSED = auto()      # Experiment execution paused. Typical: Manual intervention
    EXPERIMENT_RESUMED = auto()     # Experiment execution resumed. Typical: After pause resolution
    EXPERIMENT_ERROR = auto()       # Experiment encountered recoverable error. Typical: Retry scenario
    
    # Workflow lifecycle events
    WORKFLOW_STARTED = auto()       # Workflow phase started. Typical: Analysis phase begins
    WORKFLOW_COMPLETED = auto()     # Workflow phase completed. Typical: Static analysis finished
    WORKFLOW_FAILED = auto()        # Workflow phase failed. Typical: Tool unavailable
    
    # Orchestration events
    ORCHESTRATION_EVENT = auto()    # General orchestration event. Typical: Coordinator actions
    
    # Generic events
    CUSTOM = auto()                 # Custom user-defined event. Typical: Plugin or extension events
    
    # Analysis events
    COVERAGE_UPDATED = auto()       # Coverage data updated. Typical: New coverage information available
    COVERAGE_TRACKING_STARTED = auto() # Coverage tracking initiated. Typical: Tool monitoring begins
    COVERAGE_TRACKING_STOPPED = auto() # Coverage tracking stopped. Typical: Analysis phase complete
    MOP_ERROR_DETECTED = auto()     # MOP specification violation detected. Typical: Runtime monitor trigger
    MONITOR_GENERATED = auto()      # Monitor artifact generated. Typical: Instrumentation complete
    INSTRUMENTATION_COMPLETED = auto() # APK instrumentation finished. Typical: Ready for execution
    STATIC_ANALYSIS_COMPLETED = auto() # Static analysis finished. Typical: WTG generation complete
    ANALYSIS_COMPLETED = auto()     # General analysis completed. Typical: All analysis phases done
    
    # Environment lifecycle events
    EMULATOR_STARTED = auto()       # Android emulator started. Typical: Before app installation
    EMULATOR_STOPPED = auto()       # Android emulator stopped. Typical: After experiment completion
    APP_INSTALLED = auto()          # Application installed on device. Typical: Before test execution
    TOOL_STARTED = auto()           # Tool execution started. Typical: DroidBot begins exploration
    TOOL_STOPPED = auto()           # Tool execution stopped. Typical: Exploration completed
    
    # Configuration events
    CONFIG_LOADED = auto()          # Configuration loaded from file. Typical: System startup
    CONFIG_SAVED = auto()           # Configuration saved to file. Typical: Settings update


@validated_model(['type', 'timestamp', 'source'])
class Event(BaseValidatedModel):
    """
    Base class for all events in the RV-Android system.
    
    ### Architectural Decisions:
    - Inherits from BaseValidatedModel for comprehensive validation
    - Supports both positional and named parameter construction
    - Provides automatic timestamp generation for event ordering
    - Enables source tracking for debugging and audit trails
    
    ### Role in the System:
    - Serves as the foundation for all system event types
    - Provides consistent event structure across components
    - Enables event ordering and comparison for processing
    - Supports event tracing and debugging capabilities
    
    ### Usage Examples:
    ```python
    # Legacy positional style
    event = Event(EventType.CUSTOM, datetime.now(), "TestComponent")
    
    # Modern named parameter style
    event = Event(
        type=EventType.CUSTOM,
        timestamp=datetime.now(),
        source="TestComponent"
    )
    ```
    """
    
    type: EventType = Field(
        ...,
        description="Type of event from EventType enumeration"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the event occurred"
    )
    
    source: Optional[str] = Field(
        default=None,
        description="Component or source that generated the event"
    )
    
    @property
    def name(self) -> str:
        """
        Get the event name for compatibility with existing code.
        
        Returns:
            Event type name as string
        """
        return self.type.name
    
    def is_lifecycle_event(self) -> bool:
        """
        Check if this is a lifecycle-related event.
        
        Returns:
            True if event type indicates lifecycle changes
        """
        lifecycle_types = {
            EventType.TASK_CREATED, EventType.TASK_STARTED, EventType.TASK_COMPLETED, EventType.TASK_FAILED,
            EventType.EXPERIMENT_STARTED, EventType.EXPERIMENT_COMPLETED, EventType.EXPERIMENT_FAILED,
            EventType.WORKFLOW_STARTED, EventType.WORKFLOW_COMPLETED, EventType.WORKFLOW_FAILED,
            EventType.EMULATOR_STARTED, EventType.EMULATOR_STOPPED, EventType.TOOL_STARTED, EventType.TOOL_STOPPED
        }
        return self.type in lifecycle_types
    
    def is_analysis_event(self) -> bool:
        """
        Check if this is an analysis-related event.
        
        Returns:
            True if event type indicates analysis activities
        """
        analysis_types = {
            EventType.COVERAGE_UPDATED, EventType.COVERAGE_TRACKING_STARTED, EventType.COVERAGE_TRACKING_STOPPED,
            EventType.MOP_ERROR_DETECTED, EventType.STATIC_ANALYSIS_COMPLETED, EventType.ANALYSIS_COMPLETED
        }
        return self.type in analysis_types
    
    def __str__(self) -> str:
        """
        Get string representation of the event.
        
        Returns:
            Formatted string with event type, timestamp, and source
        """
        timestamp_str = self.timestamp.isoformat() if self.timestamp else "unknown"
        return f"{self.type.name} at {timestamp_str} from {self.source or 'unknown'}"
    
    def __lt__(self, other) -> bool:
        """
        Enable comparison for priority queue operations.
        
        Events are compared by timestamp for consistent ordering.
        Required for PriorityQueue to handle Event objects.
        
        Args:
            other: Another Event object to compare with
            
        Returns:
            True if this event is older (has earlier timestamp) than the other
        """
        if not isinstance(other, Event):
            return NotImplemented
        return self.timestamp < other.timestamp


@validated_model(['type', 'timestamp', 'source', 'task_id'])
class TaskEvent(Event):
    """
    Event related to specific task execution and lifecycle.
    
    ### Architectural Decisions:
    - Inherits from Event for consistent base functionality
    - Supports task identification via string IDs (UUID compatible)
    - Provides task configuration and detail tracking
    - Enables task-specific event filtering and analysis
    
    ### Role in the System:
    - Represents events specific to individual task execution
    - Tracks task lifecycle from creation to completion
    - Provides context for task-related debugging and analysis
    - Supports task progress monitoring and reporting
    
    ### Task Context:
    - task_id: Unique identifier for the task (supports UUID strings)
    - task_config: Configuration parameters relevant to the event
    - details: Additional context-specific information
    """
    
    task_id: str = Field(
        default="",
        description="Unique identifier for the task (supports UUID)"
    )
    
    task_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Task configuration parameters relevant to the event"
    )
    
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context-specific information for the event"
    )
    
    def get_task_summary(self) -> Dict[str, Any]:
        """
        Get summary information about the task from this event.
        
        Returns:
            Dictionary with task summary information
        """
        return {
            'task_id': self.task_id,
            'event_type': self.type.name,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'config_keys': list(self.task_config.keys()),
            'detail_keys': list(self.details.keys())
        }
    
    def has_error_details(self) -> bool:
        """
        Check if this event contains error information.
        
        Returns:
            True if event contains error details
        """
        return 'error' in self.details or 'exception' in self.details
    
    def __str__(self) -> str:
        """
        Get string representation of the task event.
        
        Returns:
            Formatted string with event type, task ID, and timestamp
        """
        return f"{self.type.name} for Task {self.task_id} at {self.timestamp.isoformat()}"


@validated_model(['type', 'timestamp', 'source', 'experiment_id'])
class ExperimentEvent(Event):
    """
    Event related to overall experiment execution and management.
    
    ### Architectural Decisions:
    - Inherits from Event for consistent base functionality
    - Supports experiment identification via string IDs
    - Tracks affected tasks for cross-task impact analysis
    - Provides messaging capability for experiment-level communication
    
    ### Role in the System:
    - Represents events at the experiment level above individual tasks
    - Tracks experiment lifecycle and state changes
    - Provides coordination information for multi-task experiments
    - Supports experiment-wide monitoring and reporting
    
    ### Experiment Context:
    - experiment_id: Unique identifier for the experiment
    - affected_tasks: List of task IDs affected by this event
    - message: Human-readable message describing the event
    """
    
    experiment_id: str = Field(
        default="",
        description="Unique identifier for the experiment"
    )
    
    affected_tasks: List[str] = Field(
        default_factory=list,
        description="List of task IDs affected by this event"
    )
    
    message: str = Field(
        default="",
        description="Human-readable message describing the event"
    )
    
    def get_experiment_summary(self) -> Dict[str, Any]:
        """
        Get summary information about the experiment from this event.
        
        Returns:
            Dictionary with experiment summary information
        """
        return {
            'experiment_id': self.experiment_id,
            'event_type': self.type.name,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'affected_tasks_count': len(self.affected_tasks),
            'has_message': bool(self.message.strip())
        }
    
    def affects_task(self, task_id: str) -> bool:
        """
        Check if this event affects a specific task.
        
        Args:
            task_id: Task ID to check
            
        Returns:
            True if the task is affected by this event
        """
        return task_id in self.affected_tasks
    
    def is_failure_event(self) -> bool:
        """
        Check if this event indicates an experiment failure.
        
        Returns:
            True if event type indicates failure
        """
        return self.type in {EventType.EXPERIMENT_FAILED, EventType.WORKFLOW_FAILED}
    
    def __str__(self) -> str:
        """
        Get string representation of the experiment event.
        
        Returns:
            Formatted string with event type, experiment ID, and message
        """
        return f"{self.type.name} for Experiment {self.experiment_id}: {self.message}"


@validated_model(['type', 'timestamp', 'source', 'task_id'])
class CoverageEvent(TaskEvent):
    """
    Event related to coverage analysis during task execution.
    
    ### Architectural Decisions:
    - Inherits from TaskEvent for automatic task context and correlation
    - Provides specific coverage data structure for analysis
    - Supports both individual coverage entries and aggregate metrics
    - Enables direct correlation with executing task
    - Uses Optional coverage fields for both individual entries and metrics events
    
    ### Role in the System:
    - Represents coverage events that occur during task execution
    - Tracks coverage progress and results for specific tasks
    - Provides complete task context for coverage analysis
    - Supports coverage debugging with task execution details
    """
    
    coverage_entry: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional coverage log entry for individual method calls"
    )
    
    coverage_metrics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional coverage metrics for aggregate updates"
    )
    
    def get_coverage_summary(self) -> Dict[str, Any]:
        """Get summary of coverage data with task context."""
        summary = {
            'task_id': self.task_id,
            'task_config': self.task_config,
            'timestamp': self.timestamp.isoformat()
        }
        
        if self.coverage_entry:
            summary.update({
                'coverage_type': 'individual',
                'class': self.coverage_entry.get('clazz'),
                'method': self.coverage_entry.get('method'),
                'signature': self.coverage_entry.get('signature'),
                'time_since_start': self.coverage_entry.get('time_since_task_start')
            })
        
        if self.coverage_metrics:
            summary.update({
                'coverage_type': 'aggregate',
                'metrics': self.coverage_metrics
            })
        
        return summary


@validated_model(['type', 'timestamp', 'source', 'task_id'])
class MOPErrorEvent(TaskEvent):
    """
    Event related to MOP (Monitored Operation) specification violations during task execution.
    
    ### Architectural Decisions:
    - Inherits from TaskEvent for automatic task context and correlation
    - Provides specific MOP error data structure
    - Supports specification violation tracking during task execution
    - Enables direct correlation with executing task and its configuration
    - Uses Optional error log for consistency with coverage pattern
    
    ### Role in the System:
    - Represents MOP specification violations that occur during task execution
    - Tracks runtime monitoring results for specific tasks
    - Provides complete task context for violation analysis
    - Supports MOP debugging with task execution context
    """
    
    error_log: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional error log entry for MOP violations"
    )
    
    def get_violation_summary(self) -> Dict[str, Any]:
        """Get summary of MOP violation with task context."""
        summary = {
            'task_id': self.task_id,
            'task_config': self.task_config,
            'timestamp': self.timestamp.isoformat()
        }
        
        if self.error_log:
            summary.update({
                'spec': self.error_log.get('spec'),
                'error_type': self.error_log.get('error_type'),
                'class_name': self.error_log.get('class_full_name'),
                'method': self.error_log.get('method'),
                'message': self.error_log.get('message'),
                'time_since_start': self.error_log.get('time_since_task_start')
            })
        
        return summary


@validated_model(['type', 'timestamp', 'source', 'task_id', 'tool_execution_start'])
class TaskToolExecutionEvent(TaskEvent):
    """
    Event for task tool execution timing correlation.
    
    ### Architectural Decisions:
    - Inherits from TaskEvent for consistent task context
    - Provides precise timing correlation between task and tool execution
    - Supports accurate coverage timing measurement
    - Enables correlation of tool execution with analysis data
    
    ### Role in the System:
    - Tracks the exact moment when tool execution begins within a task
    - Enables accurate timing correlation for coverage analysis
    - Provides timing reference for experiment result processing
    - Supports debugging of task execution timing issues
    
    ### Timing Context:
    - tool_execution_start: Timestamp when tool execution actually began
    - Used for time_since_task_start calculations in coverage logs
    - Provides timing accuracy for experiment analysis
    """
    
    tool_execution_start: datetime = Field(
        ...,
        description="Timestamp when tool execution actually started"
    )
    
    def get_tool_execution_summary(self) -> Dict[str, Any]:
        """
        Get summary information about tool execution timing.
        
        Returns:
            Dictionary with tool execution timing information
        """
        return {
            'task_id': self.task_id,
            'tool_execution_start': self.tool_execution_start.isoformat(),
            'event_timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'execution_delay': (self.tool_execution_start - self.timestamp).total_seconds()
        }
    
    def __str__(self) -> str:
        """
        Get string representation of the tool execution event.
        
        Returns:
            Formatted string with event type, task ID, and tool execution timing
        """
        return f"{self.type.name} for Task {self.task_id} at {self.tool_execution_start.isoformat()}"


@validated_model(['type', 'timestamp', 'source', 'phase_name', 'execution_mode'])
class PhaseExecutionModeEvent(Event):
    """
    Event for workflow phase execution mode tracking.
    
    ### Architectural Decisions:
    - Inherits from Event for general event functionality
    - Tracks phase execution modes (full, fallback, skipped)
    - Provides context for experiment degradation scenarios
    - Supports workflow debugging and optimization
    
    ### Role in the System:
    - Tracks how each phase was executed in the workflow
    - Enables detection of fallback scenarios and degraded execution
    - Provides data for workflow optimization and reliability analysis
    - Supports experiment result interpretation with execution context
    
    ### Phase Context:
    - phase_name: Name of the workflow phase being executed
    - execution_mode: Mode used for execution (full/fallback/skipped)
    - fallback_reason: Optional reason for degraded execution
    """
    
    phase_name: str = Field(
        ...,
        description="Name of the workflow phase"
    )
    
    execution_mode: str = Field(
        ...,
        description="Execution mode used (full, fallback, skipped, failed)"
    )
    
    fallback_reason: Optional[str] = Field(
        default=None,
        description="Reason for fallback execution if applicable"
    )
    
    artifacts_available: Dict[str, bool] = Field(
        default_factory=dict,
        description="Availability of artifacts for this phase"
    )
    
    def get_phase_summary(self) -> Dict[str, Any]:
        """
        Get summary information about phase execution.
        
        Returns:
            Dictionary with phase execution information
        """
        return {
            'phase_name': self.phase_name,
            'execution_mode': self.execution_mode,
            'fallback_reason': self.fallback_reason,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'artifacts_available': self.artifacts_available,
            'is_degraded': self.execution_mode in ['fallback', 'skipped', 'failed']
        }
    
    def is_fallback_execution(self) -> bool:
        """
        Check if this phase was executed in fallback mode.
        
        Returns:
            True if phase was executed with fallback
        """
        return self.execution_mode == 'fallback'
    
    def __str__(self) -> str:
        """
        Get string representation of the phase execution event.
        
        Returns:
            Formatted string with phase name, execution mode, and timestamp
        """
        fallback_info = f" ({self.fallback_reason})" if self.fallback_reason else ""
        return f"Phase {self.phase_name} executed in {self.execution_mode} mode{fallback_info}"


class EventHistoryManager:
    """
    Manages event history with memory-efficient storage and retrieval.
    
    ### Architectural Decisions:
    - Implements circular buffer for memory efficiency
    - Provides filtering and querying capabilities
    - Supports thread-safe operations
    - Maintains configurable history size limits
    - Memory-only storage with no persistence requirements
    
    ### Role in the System:
    - Manages event storage with automatic size limits
    - Provides efficient filtering and querying
    - Supports debugging and audit trail functionality
    - Prevents memory leaks from unlimited history growth
    - Centralizes all history management logic from EventBus
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize the event history manager.
        
        Args:
            max_size: Maximum number of events to store in memory
        """
        self._history: List[Event] = []
        self._max_size = max_size
        self._lock = threading.Lock()
    
    def add_event(self, event: Event) -> None:
        """Add event to history with automatic size management."""
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_size:
                self._history = self._history[-self._max_size:]
    
    def get_events(self, 
                   event_type: Optional[EventType] = None,
                   since: Optional[datetime] = None,
                   source: Optional[str] = None,
                   task_id: Optional[str] = None,
                   limit: int = 100) -> List[Event]:
        """Get events with optional filtering."""
        with self._lock:
            events = self._history.copy()
        
        # Apply filters
        if event_type:
            events = [e for e in events if e.type == event_type]
        if since:
            events = [e for e in events if e.timestamp >= since]
        if source:
            events = [e for e in events if e.source == source]
        if task_id:
            events = [e for e in events if isinstance(e, TaskEvent) and e.task_id == task_id]
        
        # Sort and limit
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]
    
    def clear(self) -> None:
        """Clear all events from history."""
        with self._lock:
            self._history.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get history statistics."""
        with self._lock:
            event_counts = {}
            for event in self._history:
                event_counts[event.type.name] = event_counts.get(event.type.name, 0) + 1
            
            return {
                'total_events': len(self._history),
                'event_type_counts': event_counts,
                'oldest_event': self._history[0].timestamp if self._history else None,
                'newest_event': self._history[-1].timestamp if self._history else None
            }