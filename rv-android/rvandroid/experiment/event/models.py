# rvandroid/experiment/event/models.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Any, Optional


class EventType(Enum):
    """Event types for the experiment execution system"""
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

    # Analysis events
    COVERAGE_UPDATED = auto()
    COVERAGE_TRACKING_STARTED = auto()
    COVERAGE_TRACKING_STOPPED = auto()
    ERROR_DETECTED = auto()
    STATIC_ANALYSIS_COMPLETED = auto()
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


@dataclass
class Event:
    """Base class for all events in the system"""
    type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.type.name} at {self.timestamp.isoformat()} from {self.source or 'unknown'}"


@dataclass
class TaskEvent(Event):
    """Event related to a specific task"""
    task_id: int = 0
    task_config: Dict[str, Any] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.type.name} for Task {self.task_id} at {self.timestamp.isoformat()}"


@dataclass
class ExperimentEvent(Event):
    """Event related to the overall experiment"""
    experiment_id: str = ""
    affected_tasks: List[int] = field(default_factory=list)
    message: str = ""

    def __str__(self) -> str:
        return f"{self.type.name} for Experiment {self.experiment_id}: {self.message}"


@dataclass
class AnalysisEvent(Event):
    """Event related to analysis results"""
    data: Dict[str, Any] = field(default_factory=dict)
    related_task_id: Optional[int] = None

    def __str__(self) -> str:
        task_str = f" for Task {self.related_task_id}" if self.related_task_id else ""
        return f"{self.type.name}{task_str} at {self.timestamp.isoformat()}"
   