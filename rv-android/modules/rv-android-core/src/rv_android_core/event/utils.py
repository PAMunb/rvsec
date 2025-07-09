# rvandroid/experiment/event/utils.py
"""
Utility functions for working with events.

This module provides utility functions for working with events in the RV-Android
system, including filtering, event processing, and other common operations.
"""

from datetime import datetime
from typing import Dict, List, Optional, TypeVar, Set

# Import from models directly
from rv_android_core.event.models import (
    Event, EventType, TaskEvent, ExperimentEvent, CoverageEvent, MOPErrorEvent
)

# Type variable for events
T = TypeVar('T', bound=Event)


def filter_events_by_task(events: List[Event], task_id: str) -> List[TaskEvent]:
    """
    Filter events to only those related to a specific task.
    
    Args:
        events: List of events to filter
        task_id: Task ID to filter by
        
    Returns:
        List of TaskEvent instances related to the specified task
    """
    return [e for e in events
            if isinstance(e, TaskEvent) and e.task_id == task_id]


def filter_events_by_experiment(events: List[Event], experiment_id: str) -> List[ExperimentEvent]:
    """
    Filter events to only those related to a specific experiment.
    
    Args:
        events: List of events to filter
        experiment_id: Experiment ID to filter by
        
    Returns:
        List of ExperimentEvent instances related to the specified experiment
    """
    return [e for e in events
            if isinstance(e, ExperimentEvent) and e.experiment_id == experiment_id]


def filter_events_by_type(events: List[Event], event_type: EventType) -> List[Event]:
    """
    Filter events by their EventType.
    
    Args:
        events: List of events to filter
        event_type: EventType to filter by
        
    Returns:
        List of events of the specified type
    """
    return [e for e in events if e.type == event_type]


def filter_events_by_source(events: List[Event], source: str) -> List[Event]:
    """
    Filter events by their source.
    
    Args:
        events: List of events to filter
        source: Source to filter by
        
    Returns:
        List of events from the specified source
    """
    return [e for e in events if e.source == source]


def filter_events_by_time_range(events: List[Event],
                                start_time: Optional[datetime] = None,
                                end_time: Optional[datetime] = None) -> List[Event]:
    """
    Filter events by a time range.
    
    Args:
        events: List of events to filter
        start_time: Optional start time (inclusive)
        end_time: Optional end time (inclusive)
        
    Returns:
        List of events within the specified time range
    """
    result = events

    if start_time:
        result = [e for e in result if e.timestamp >= start_time]

    if end_time:
        result = [e for e in result if e.timestamp <= end_time]

    return result


def group_events_by_type(events: List[Event]) -> Dict[EventType, List[Event]]:
    """
    Group events by their EventType.
    
    Args:
        events: List of events to group
        
    Returns:
        Dictionary mapping EventType to lists of events
    """
    result: Dict[EventType, List[Event]] = {}

    for event in events:
        if event.type not in result:
            result[event.type] = []
        result[event.type].append(event)

    return result


def find_related_task_events(events: List[Event], task_id: str) -> List[Event]:
    """
    Find all events related to a specific task, including non-TaskEvent types.
    
    This finds not only TaskEvents for the task, but also AnalysisEvents that
    reference the task, and any other events that might be related.
    
    Args:
        events: List of events to search
        task_id: Task ID to find related events for
        
    Returns:
        List of all events related to the specified task
    """
    result = []

    for event in events:
        if isinstance(event, TaskEvent) and event.task_id == task_id:
            result.append(event)
        elif isinstance(event, AnalysisEvent) and event.related_task_id == task_id:
            result.append(event)
        elif isinstance(event, ExperimentEvent) and task_id in event.affected_tasks:
            result.append(event)

    return result


def extract_task_timeline(events: List[Event], task_id: str) -> List[Event]:
    """
    Extract events forming a task's timeline, sorted chronologically.
    
    Args:
        events: List of events to analyze
        task_id: Task ID to extract timeline for
        
    Returns:
        Chronologically sorted list of events related to the task
    """
    related_events = find_related_task_events(events, task_id)
    return sorted(related_events, key=lambda e: e.timestamp)


def find_unique_task_ids(events: List[Event]) -> Set[str]:
    """
    Find all unique task IDs mentioned in events.
    
    Args:
        events: List of events to analyze
        
    Returns:
        Set of unique task IDs
    """
    task_ids = set()

    for event in events:
        if isinstance(event, TaskEvent):
            task_ids.add(event.task_id)
        elif isinstance(event, AnalysisEvent) and event.related_task_id:
            task_ids.add(event.related_task_id)
        elif isinstance(event, ExperimentEvent):
            task_ids.update(event.affected_tasks)

    return task_ids


def find_unique_experiment_ids(events: List[Event]) -> Set[str]:
    """
    Find all unique experiment IDs mentioned in events.
    
    Args:
        events: List of events to analyze
        
    Returns:
        Set of unique experiment IDs
    """
    experiment_ids = set()

    for event in events:
        if isinstance(event, ExperimentEvent):
            experiment_ids.add(event.experiment_id)

    return experiment_ids
