# rvandroid/experiment/event/factory.py
"""
Factory for creating standardized events.

This module provides the EventFactory class, which creates events with consistent
structure and metadata. It simplifies the process of creating events and ensures
that all events adhere to the same standards.
"""

from typing import Dict, Any, Optional

from rvandroid.experiment.event.events import (
    BaseEvent,
    TaskEvent,
    ExperimentEvent,
    AnalysisEvent,
    WorkflowEvent
)


class EventFactory:
    """
    Factory for creating standardized events in the RV-Android system.
    
    ### Architectural Decisions:
    - Implements the factory pattern for consistent event creation
    - Centralizes event creation logic and validation
    - Provides a clean interface for creating different event types
    - Ensures consistent metadata for all events
    
    ### Role in the System:
    - Creates events with standardized structure and metadata
    - Simplifies the process of creating events for publishers
    - Ensures all events adhere to the same standards
    - Provides a single point for event creation logic
    """
    
    @staticmethod
    def create_task_event(name: str, 
                        task_id: str,
                        task_config: Optional[Dict[str, Any]] = None,
                        details: Optional[Dict[str, Any]] = None,
                        source: Optional[str] = None) -> TaskEvent:
        """
        Create a task event.
        
        Args:
            name: Event name (use constants from rvandroid.experiment.event.constants)
            task_id: ID of the task this event relates to
            task_config: Optional configuration details for the task
            details: Optional additional details for the event
            source: Optional source of the event (component name)
            
        Returns:
            TaskEvent instance
        """
        return TaskEvent(
            _name=name,
            task_id=task_id,
            task_config=task_config or {},
            details=details or {},
            source=source
        )
        
    @staticmethod
    def create_experiment_event(name: str,
                              experiment_id: str,
                              message: Optional[str] = None,
                              details: Optional[Dict[str, Any]] = None,
                              source: Optional[str] = None) -> ExperimentEvent:
        """
        Create an experiment event.
        
        Args:
            name: Event name (use constants from rvandroid.experiment.event.constants)
            experiment_id: ID of the experiment this event relates to
            message: Optional message for the event
            details: Optional additional details for the event
            source: Optional source of the event (component name)
            
        Returns:
            ExperimentEvent instance
        """
        event_details = details or {}
        if message:
            event_details["message"] = message
            
        return ExperimentEvent(
            _name=name,
            experiment_id=experiment_id,
            details=event_details,
            source=source
        )
        
    @staticmethod
    def create_analysis_event(name: str,
                            data: Optional[Dict[str, Any]] = None,
                            related_task_id: Optional[str] = None,
                            source: Optional[str] = None) -> AnalysisEvent:
        """
        Create an analysis event.
        
        Args:
            name: Event name (use constants from rvandroid.experiment.event.constants)
            data: Optional analysis data for the event
            related_task_id: Optional ID of the related task
            source: Optional source of the event (component name)
            
        Returns:
            AnalysisEvent instance
        """
        return AnalysisEvent(
            _name=name,
            data=data or {},
            related_task_id=related_task_id,
            source=source
        )
        
    @staticmethod
    def create_workflow_event(name: str,
                           workflow_id: str,
                           experiment_id: str,
                           details: Optional[Dict[str, Any]] = None,
                           source: Optional[str] = None) -> WorkflowEvent:
        """
        Create a workflow event.
        
        Args:
            name: Event name (use constants from rvandroid.experiment.event.constants)
            workflow_id: ID of the workflow this event relates to
            experiment_id: ID of the experiment this workflow belongs to
            details: Optional additional details for the event
            source: Optional source of the event (component name)
            
        Returns:
            WorkflowEvent instance
        """
        return WorkflowEvent(
            _name=name,
            workflow_id=workflow_id,
            experiment_id=experiment_id,
            details=details or {},
            source=source
        )
        
    @staticmethod
    def create_base_event(name: str,
                        details: Optional[Dict[str, Any]] = None,
                        source: Optional[str] = None) -> BaseEvent:
        """
        Create a base event with minimal metadata.
        
        Args:
            name: Event name (use constants from rvandroid.experiment.event.constants)
            details: Optional additional details for the event
            source: Optional source of the event (component name)
            
        Returns:
            BaseEvent instance
        """
        return BaseEvent(
            _name=name,
            details=details or {},
            source=source
        )