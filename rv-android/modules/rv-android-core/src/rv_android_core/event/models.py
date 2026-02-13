"""Event models for the RV-Android event system."""

from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional
from pydantic import Field

from rv_android_core.util.validation.base import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model


class EventChannel(Enum):
    """Event channels for organized event routing."""

    DEFAULT = "default"
    LIFECYCLE = "lifecycle"
    ANALYSIS = "analysis"
    ERROR = "error"


class EventType(Enum):
    """All event types supported by the RV-Android system.

    Serialization Warning:
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
    TASK_STARTED = auto()
    TASK_COMPLETED = auto()
    TASK_FAILED = auto()

    # Experiment lifecycle events
    EXPERIMENT_COMPLETED = auto()
    EXPERIMENT_FAILED = auto()

    # Workflow lifecycle events
    WORKFLOW_COMPLETED = auto()

    # Environment lifecycle events
    EMULATOR_STARTED = auto()
    APP_INSTALLED = auto()
    TOOL_STARTED = auto()
    TOOL_STOPPED = auto()

    # Instrumentation events
    MONITOR_GENERATED = auto()
    INSTRUMENTATION_COMPLETED = auto()
    STATIC_ANALYSIS_COMPLETED = auto()

    # Coverage and monitoring events
    COVERAGE_TRACKING_STARTED = auto()
    COVERAGE_TRACKING_STOPPED = auto()
    COVERAGE_UPDATED = auto()
    MOP_ERROR_DETECTED = auto()


@validated_model(['type', 'timestamp', 'source'])
class Event(BaseValidatedModel):
    """Base class for all events in the RV-Android system."""

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
        """Get the event name for compatibility with existing code."""
        return self.type.name

    def is_lifecycle_event(self) -> bool:
        """Check if this is a lifecycle-related event."""
        lifecycle_types = {
            EventType.TASK_STARTED, EventType.TASK_COMPLETED, EventType.TASK_FAILED,
            EventType.EXPERIMENT_COMPLETED, EventType.EXPERIMENT_FAILED,
            EventType.WORKFLOW_COMPLETED,
            EventType.EMULATOR_STARTED, EventType.TOOL_STARTED, EventType.TOOL_STOPPED
        }
        return self.type in lifecycle_types

    def is_analysis_event(self) -> bool:
        """Check if this is an analysis-related event."""
        analysis_types = {
            EventType.COVERAGE_UPDATED, EventType.COVERAGE_TRACKING_STARTED,
            EventType.COVERAGE_TRACKING_STOPPED,
            EventType.MOP_ERROR_DETECTED, EventType.STATIC_ANALYSIS_COMPLETED
        }
        return self.type in analysis_types

    def __str__(self) -> str:
        timestamp_str = self.timestamp.isoformat() if self.timestamp else "unknown"
        return f"{self.type.name} at {timestamp_str} from {self.source or 'unknown'}"


@validated_model(['type', 'timestamp', 'source', 'task_id'])
class TaskEvent(Event):
    """Event related to specific task execution and lifecycle."""

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
        """Get summary information about the task from this event."""
        return {
            'task_id': self.task_id,
            'event_type': self.type.name,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'config_keys': list(self.task_config.keys()),
            'detail_keys': list(self.details.keys())
        }

    def has_error_details(self) -> bool:
        """Check if this event contains error information."""
        return 'error' in self.details or 'exception' in self.details

    def __str__(self) -> str:
        return f"{self.type.name} for Task {self.task_id} at {self.timestamp.isoformat()}"


@validated_model(['type', 'timestamp', 'source', 'experiment_id'])
class ExperimentEvent(Event):
    """Event related to overall experiment execution and management."""

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
        """Get summary information about the experiment from this event."""
        return {
            'experiment_id': self.experiment_id,
            'event_type': self.type.name,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'affected_tasks_count': len(self.affected_tasks),
            'has_message': bool(self.message.strip())
        }

    def affects_task(self, task_id: str) -> bool:
        """Check if this event affects a specific task."""
        return task_id in self.affected_tasks

    def is_failure_event(self) -> bool:
        """Check if this event indicates an experiment failure."""
        return self.type == EventType.EXPERIMENT_FAILED

    def __str__(self) -> str:
        return f"{self.type.name} for Experiment {self.experiment_id}: {self.message}"


@validated_model(['type', 'timestamp', 'source', 'task_id'])
class CoverageEvent(TaskEvent):
    """Event related to coverage analysis during task execution."""

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
    """Event related to MOP (Monitored Operation) specification violations during task execution."""

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
    """Event for task tool execution timing correlation."""

    tool_execution_start: datetime = Field(
        ...,
        description="Timestamp when tool execution actually started"
    )

    def get_tool_execution_summary(self) -> Dict[str, Any]:
        """Get summary information about tool execution timing."""
        return {
            'task_id': self.task_id,
            'tool_execution_start': self.tool_execution_start.isoformat(),
            'event_timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'execution_delay': (self.tool_execution_start - self.timestamp).total_seconds()
        }

    def __str__(self) -> str:
        return f"{self.type.name} for Task {self.task_id} at {self.tool_execution_start.isoformat()}"


@validated_model(['type', 'timestamp', 'source', 'phase_name', 'execution_mode'])
class PhaseExecutionModeEvent(Event):
    """Event for workflow phase execution mode tracking."""

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
        """Get summary information about phase execution."""
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
        """Check if this phase was executed in fallback mode."""
        return self.execution_mode == 'fallback'

    def __str__(self) -> str:
        fallback_info = f" ({self.fallback_reason})" if self.fallback_reason else ""
        return f"Phase {self.phase_name} executed in {self.execution_mode} mode{fallback_info}"
