# rvandroid/experiment/event/events.py
"""
Event implementations for the event system.

This module provides concrete implementations of events for different
purposes, such as task events, experiment events, and analysis events.
These events are used for communication between components in the system.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from rvandroid.experiment.event.interfaces import IEvent


@dataclass
class BaseEvent(IEvent):
    """
    Base implementation for all events in the RV-Android system.
    
    ### Architectural Decisions:
    - Uses dataclass for concise implementation
    - Provides consistent event metadata
    - Supports flexible event payloads
    - Enables standardized event serialization
    
    ### Role in the System:
    - Serves as the foundation for all event types
    - Provides common event metadata
    - Enables uniform event handling and processing
    - Facilitates consistent event serialization
    """

    _name: str
    details: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None
    _event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    _timestamp: float = field(default_factory=time.time)

    @property
    def event_id(self) -> str:
        """
        Get the unique identifier for this event.
        
        Returns:
            A unique string identifier for this event instance
        """
        return self._event_id

    @property
    def timestamp(self) -> float:
        """
        Get the timestamp for this event.
        
        Returns:
            The time when this event was created, as seconds since epoch
        """
        return self._timestamp
        
    @property
    def name(self) -> str:
        """
        Get the event name.
        
        Returns:
            The name of this event type, used for subscription matching
        """
        return self._name
        
    @name.setter
    def name(self, value: str) -> None:
        """
        Set the event name.
        
        Args:
            value: New event name
        """
        self._name = value

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert event to dictionary for serialization.
        
        Returns:
            A dictionary representation of this event
        """
        return {
            "event_id": self.event_id,
            "name": self.name,
            "timestamp": self.timestamp,
            "source": self.source,
            "details": self.details
        }


@dataclass
class TaskEvent(BaseEvent):
    """    Event related to task execution.
    
    ### Architectural Decisions:
    - Extends BaseEvent with task-specific metadata
    - Provides structured representation of task events
    - Standardizes task event format
    - Enables task-based filtering and routing
    
    ### Role in the System:
    - Represents events related to task execution
    - Enables tracking of task lifecycle events
    - Facilitates task-based event filtering
    - Provides context for task-related operations
    """

    task_id: str = ""
    task_config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert event to dictionary for serialization.
        
        Returns:
            A dictionary representation of this event
        """
        base_dict = super().to_dict()
        base_dict.update({
            "task_id": self.task_id,
            "task_config": self.task_config
        })
        return base_dict


@dataclass
class ExperimentEvent(BaseEvent):
    """
    Event related to experiment execution.
    
    ### Architectural Decisions:
    - Extends BaseEvent with experiment-specific metadata
    - Provides structured representation of experiment events
    - Standardizes experiment event format
    - Enables experiment-based filtering and routing
    
    ### Role in the System:
    - Represents events related to experiment execution
    - Enables tracking of experiment lifecycle events
    - Facilitates experiment-based event filtering
    - Provides context for experiment-related operations
    """

    experiment_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert event to dictionary for serialization.
        
        Returns:
            A dictionary representation of this event
        """
        base_dict = super().to_dict()
        base_dict.update({
            "experiment_id": self.experiment_id
        })
        return base_dict


@dataclass
class AnalysisEvent(BaseEvent):
    """
    Event related to analysis results.
    
    ### Architectural Decisions:
    - Extends BaseEvent with analysis-specific metadata
    - Provides structured representation of analysis events
    - Standardizes analysis event format
    - Enables analysis-based filtering and routing
    
    ### Role in the System:
    - Represents events related to analysis operations
    - Enables tracking of analysis lifecycle events
    - Facilitates analysis-based event filtering
    - Provides context for analysis-related operations
    """

    data: Dict[str, Any] = field(default_factory=dict)
    related_task_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert event to dictionary for serialization.
        
        Returns:
            A dictionary representation of this event
        """
        base_dict = super().to_dict()
        base_dict.update({
            "data": self.data,
            "related_task_id": self.related_task_id
        })
        return base_dict


@dataclass
class WorkflowEvent(BaseEvent):
    """
    Event related to workflow execution.
    
    ### Architectural Decisions:
    - Extends BaseEvent with workflow-specific metadata
    - Provides structured representation of workflow events
    - Standardizes workflow event format
    - Enables workflow-based filtering and routing
    
    ### Role in the System:
    - Represents events related to workflow execution
    - Enables tracking of workflow lifecycle events
    - Facilitates workflow-based event filtering
    - Provides context for workflow-related operations
    """

    workflow_id: str = ""
    experiment_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert event to dictionary for serialization.
        
        Returns:
            A dictionary representation of this event
        """
        base_dict = super().to_dict()
        base_dict.update({
            "workflow_id": self.workflow_id,
            "experiment_id": self.experiment_id
        })
        return base_dict
