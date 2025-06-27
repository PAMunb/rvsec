"""
Event models for RV-Android Core system.

This module provides validated event models for representing system events
with comprehensive type safety and standardized event lifecycle management.
"""

from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional
from pydantic import Field

from rv_android_core.util.validation.base import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model


class CoreEventType(Enum):
    """
    Enumeration of core event types for optimized event processing.
    
    ### Architectural Decisions:
    - Limited to 10 core events for performance optimization
    - Focuses on critical experiment lifecycle and error tracking
    - Enables high-performance event filtering in production
    - Maintains backwards compatibility through EventType mapping
    
    ### Core Event Categories:
    - Experiment lifecycle: Core experiment tracking (3 events)
    - Task lifecycle: Basic task execution tracking (3 events)
    - Tool execution: Critical tool operation tracking (1 event)
    - Analysis results: Coverage and error detection (2 events)
    - System errors: Error detection and handling (1 event)
    """
    
    # Experiment lifecycle (3 events)
    EXPERIMENT_STARTED = auto()
    EXPERIMENT_COMPLETED = auto()
    EXPERIMENT_FAILED = auto()
    
    # Task lifecycle (3 events)
    TASK_STARTED = auto()
    TASK_COMPLETED = auto()
    TASK_FAILED = auto()
    
    # Tool execution (1 event)
    TOOL_EXECUTION_STARTED = auto()
    
    # Analysis results (2 events)
    COVERAGE_UPDATED = auto()
    STATIC_ANALYSIS_COMPLETED = auto()
    
    # System errors (1 event)
    ERROR_DETECTED = auto()


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
    """
    
    # Task lifecycle events
    TASK_CREATED = auto()
    TASK_CONFIGURED = auto()
    TASK_STARTED = auto()
    TASK_COMPLETED = auto()
    TASK_FAILED = auto()

    # Experiment lifecycle events
    EXPERIMENT_STARTED = auto()
    EXPERIMENT_COMPLETED = auto()
    EXPERIMENT_FAILED = auto()
    EXPERIMENT_PAUSED = auto()
    EXPERIMENT_RESUMED = auto()

    # Workflow lifecycle events
    WORKFLOW_STARTED = auto()
    WORKFLOW_COMPLETED = auto()
    WORKFLOW_FAILED = auto()

    # Orchestration events
    ORCHESTRATION_EVENT = auto()

    # Generic events
    CUSTOM = auto()

    # Analysis events
    COVERAGE_UPDATED = auto()
    COVERAGE_TRACKING_STARTED = auto()
    COVERAGE_TRACKING_STOPPED = auto()
    ERROR_DETECTED = auto() # MOP error detection
    STATIC_ANALYSIS_COMPLETED = auto()
    ANALYSIS_COMPLETED = auto()
    NEW_METHOD_DISCOVERED = auto()

    # Environment lifecycle events
    EMULATOR_STARTED = auto()
    EMULATOR_STOPPED = auto()
    APP_INSTALLED = auto()
    TOOL_STARTED = auto()
    TOOL_STOPPED = auto()

    # Configuration events
    CONFIG_LOADED = auto()
    CONFIG_SAVED = auto()
    
    @classmethod
    def is_core(cls, event_type) -> bool:
        """
        Check if an event type is considered core.
        
        Args:
            event_type: EventType to check
            
        Returns:
            True if the event type is core for functionality
        """
        core_mapping = {
            cls.EXPERIMENT_STARTED: CoreEventType.EXPERIMENT_STARTED,
            cls.EXPERIMENT_COMPLETED: CoreEventType.EXPERIMENT_COMPLETED,
            cls.EXPERIMENT_FAILED: CoreEventType.EXPERIMENT_FAILED,
            cls.TASK_STARTED: CoreEventType.TASK_STARTED,
            cls.TASK_COMPLETED: CoreEventType.TASK_COMPLETED,
            cls.TASK_FAILED: CoreEventType.TASK_FAILED,
            cls.TOOL_STARTED: CoreEventType.TOOL_EXECUTION_STARTED,
            cls.COVERAGE_UPDATED: CoreEventType.COVERAGE_UPDATED,
            cls.STATIC_ANALYSIS_COMPLETED: CoreEventType.STATIC_ANALYSIS_COMPLETED,
            cls.ERROR_DETECTED: CoreEventType.ERROR_DETECTED,
        }
        return event_type in core_mapping
    
    @classmethod
    def to_core(cls, event_type):
        """
        Convert an EventType to its corresponding CoreEventType.
        
        Args:
            event_type: EventType to convert
            
        Returns:
            Corresponding CoreEventType or None if not core
        """
        core_mapping = {
            cls.EXPERIMENT_STARTED: CoreEventType.EXPERIMENT_STARTED,
            cls.EXPERIMENT_COMPLETED: CoreEventType.EXPERIMENT_COMPLETED,
            cls.EXPERIMENT_FAILED: CoreEventType.EXPERIMENT_FAILED,
            cls.TASK_STARTED: CoreEventType.TASK_STARTED,
            cls.TASK_COMPLETED: CoreEventType.TASK_COMPLETED,
            cls.TASK_FAILED: CoreEventType.TASK_FAILED,
            cls.TOOL_STARTED: CoreEventType.TOOL_EXECUTION_STARTED,
            cls.COVERAGE_UPDATED: CoreEventType.COVERAGE_UPDATED,
            cls.STATIC_ANALYSIS_COMPLETED: CoreEventType.STATIC_ANALYSIS_COMPLETED,
            cls.ERROR_DETECTED: CoreEventType.ERROR_DETECTED,
        }
        return core_mapping.get(event_type)


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
            EventType.ERROR_DETECTED, EventType.STATIC_ANALYSIS_COMPLETED, EventType.ANALYSIS_COMPLETED,
            EventType.NEW_METHOD_DISCOVERED
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


@validated_model(['type', 'timestamp', 'source'])
class AnalysisEvent(Event):
    """
    Event related to analysis results and monitored operations tracking.
    
    ### Architectural Decisions:
    - Inherits from Event for consistent base functionality
    - Supports flexible data payload for various analysis types
    - Optionally links to specific tasks for correlation
    - Enables analysis result tracking and aggregation
    
    ### Role in the System:
    - Represents events from analysis components (static, coverage, etc.)
    - Tracks analysis progress and results
    - Provides data for analysis result aggregation
    - Supports debugging of analysis processes
    
    ### Analysis Context:
    - data: Flexible payload containing analysis results
    - related_task_id: Optional task association for correlation
    - Used for tracking monitored operations detection and coverage
    """
    
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Analysis data and results payload"
    )
    
    related_task_id: Optional[str] = Field(
        default=None,
        description="Optional task ID for correlation with task execution"
    )
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """
        Get summary information about the analysis from this event.
        
        Returns:
            Dictionary with analysis summary information
        """
        return {
            'event_type': self.type.name,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'related_task_id': self.related_task_id,
            'data_keys': list(self.data.keys()),
            'has_task_relation': self.related_task_id is not None
        }
    
    def is_coverage_event(self) -> bool:
        """
        Check if this event is related to coverage analysis.
        
        Returns:
            True if event type indicates coverage analysis
        """
        coverage_types = {
            EventType.COVERAGE_UPDATED,
            EventType.COVERAGE_TRACKING_STARTED,
            EventType.COVERAGE_TRACKING_STOPPED
        }
        return self.type in coverage_types
    
    def is_monitored_operations_event(self) -> bool:
        """
        Check if this event is related to monitored operations.
        
        Returns:
            True if event data contains monitored operations information
        """
        return any(
            key in self.data 
            for key in ['monitored_operations', 'mop_detected', 'specification_violation']
        )
    
    def __str__(self) -> str:
        """
        Get string representation of the analysis event.
        
        Returns:
            Formatted string with event type, task relation, and timestamp
        """
        task_str = f" for Task {self.related_task_id}" if self.related_task_id else ""
        return f"{self.type.name}{task_str} at {self.timestamp.isoformat()}"


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