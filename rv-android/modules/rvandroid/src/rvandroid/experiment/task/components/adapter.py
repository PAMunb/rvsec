# rvandroid/experiment/task/components/adapter.py
"""
Adapter for converting existing components to the new component system.

This module provides adapters that wrap legacy component implementations to make
them compatible with the new task component interface. This facilitates a smooth
transition to the new system while maintaining compatibility with existing code.
"""

import logging
from typing import Dict, Any, Optional, Type, TypeVar, Generic

from rv_android_core.experiment.event import EventBus, get_event_bus
from rv_android_core.experiment.task.component import BaseTaskComponent
from rv_android_core.experiment.task.interfaces import ITask
from rv_android_core.experiment.task.task_model import Task
from rv_android_core.util.error.error_handler import ErrorHandler

# TODO deprecated???
class LegacyCoverageComponentAdapter(BaseTaskComponent):
    """
    Adapter for the legacy CoverageComponent.
    
    ### Architectural Decisions:
    - Wraps the legacy component to implement the new interface
    - Maps between old and new method signatures
    - Maintains compatibility with existing code
    - Enables gradual migration to the new system
    
    ### Role in the System:
    - Facilitates transition to the new component system
    - Enables reuse of existing component code
    - Ensures backward compatibility
    - Simplifies migration by eliminating the need to rewrite all components
    """
    
    def __init__(self, task: ITask, event_bus: Optional[EventBus] = None):
        """
        Initialize the adapter with a task and event bus.
        
        Args:
            task: Task to execute
            event_bus: Optional event bus for notifications
        """
        super().__init__("CoverageComponent", event_bus)
        
        # Import here to avoid circular imports
        from rv_android_core.experiment.task.components.coverage import CoverageComponent
        
        # Create the legacy component
        self.legacy_component = CoverageComponent(task, event_bus)
        self.task = task
        
    def _execute_impl(self, context: Dict[str, Any]) -> bool:
        """
        Execute the component's primary function.
        
        Args:
            context: Dictionary with task context information
            
        Returns:
            True if execution was successful, False otherwise
        """
        try:
            # Call legacy methods in sequence
            self.legacy_component.initialize_tracker()
            self.legacy_component.start_tracking()
            return True
        except Exception as e:
            self.logger.error(f"Error executing legacy coverage component: {e}")
            error_handler = ErrorHandler.get_instance()
            error_context = {
                "component": "LegacyCoverageComponentAdapter",
                "operation": "execute_coverage",
                "task_id": self.task.id
            }
            error_handler.handle_error(e, error_context)
            return False
            
    def cleanup(self, context: Dict[str, Any]) -> bool:
        """
        Clean up any resources used by the component.
        
        Args:
            context: Dictionary with task context information
            
        Returns:
            True if cleanup was successful, False otherwise
        """
        try:
            self.legacy_component.stop_tracking()
            self.legacy_component.process_results()
            return True
        except Exception as e:
            self.logger.error(f"Error cleaning up legacy coverage component: {e}")
            error_handler = ErrorHandler.get_instance()
            error_context = {
                "component": "LegacyCoverageComponentAdapter",
                "operation": "cleanup_coverage",
                "task_id": self.task.id
            }
            error_handler.handle_error(e, error_context)
            return False


class LegacyEmulatorComponentAdapter(BaseTaskComponent):
    """
    Adapter for the legacy EmulatorComponent.
    
    Wraps the legacy component to implement the new interface and manage
    the emulator lifecycle appropriately.
    """
    
    def __init__(self, task: ITask, event_bus: Optional[EventBus] = None):
        """
        Initialize the adapter with a task and event bus.
        
        Args:
            task: Task to execute
            event_bus: Optional event bus for notifications
        """
        super().__init__("EmulatorComponent", event_bus)
        
        # Import here to avoid circular imports
        from rv_android_core.experiment.task.components.emulator import EmulatorComponent
        
        # Create the legacy component
        self.legacy_component = EmulatorComponent(task, event_bus)
        self.task = task
        self.android = None
        
    def _execute_impl(self, context: Dict[str, Any]) -> bool:
        """
        Execute the component's primary function.
        
        Args:
            context: Dictionary with task context information
            
        Returns:
            True if execution was successful, False otherwise
        """
        try:
            # Start emulator and keep the Android instance
            self.android = self.legacy_component.start_emulator("RVSec")
            
            # Install app if needed
            if not self.task.config.skip_installation and self.android and self.task.app:
                self.legacy_component.install_app(self.android, self.task.app)
                
            return True
        except Exception as e:
            self.logger.error(f"Error executing legacy emulator component: {e}")
            error_handler = ErrorHandler.get_instance()
            error_context = {
                "component": "LegacyEmulatorComponentAdapter",
                "operation": "execute_emulator",
                "task_id": self.task.id
            }
            error_handler.handle_error(e, error_context)
            return False
            
    def cleanup(self, context: Dict[str, Any]) -> bool:
        """
        Clean up any resources used by the component.
        
        Args:
            context: Dictionary with task context information
            
        Returns:
            True if cleanup was successful, False otherwise
        """
        try:
            # Stop emulator if running
            if hasattr(self.legacy_component, 'stop_emulator'):
                self.legacy_component.stop_emulator()
            return True
        except Exception as e:
            self.logger.error(f"Error cleaning up legacy emulator component: {e}")
            error_handler = ErrorHandler.get_instance()
            error_context = {
                "component": "LegacyEmulatorComponentAdapter",
                "operation": "cleanup_emulator",
                "task_id": self.task.id
            }
            error_handler.handle_error(e, error_context)
            return False


class LegacyLogcatComponentAdapter(BaseTaskComponent):
    """
    Adapter for the legacy LogcatComponent.
    
    Wraps the legacy component to implement the new interface and manage
    logcat capture appropriately.
    """
    
    def __init__(self, task: ITask, event_bus: Optional[EventBus] = None):
        """
        Initialize the adapter with a task and event bus.
        
        Args:
            task: Task to execute
            event_bus: Optional event bus for notifications
        """
        super().__init__("LogcatComponent", event_bus)
        
        # Import here to avoid circular imports
        from rv_android_core.experiment.task.components.logcat import LogcatComponent
        
        # Create the legacy component
        self.legacy_component = LogcatComponent(task, event_bus)
        self.task = task
        
    def _execute_impl(self, context: Dict[str, Any]) -> bool:
        """
        Execute the component's primary function.
        
        Args:
            context: Dictionary with task context information
            
        Returns:
            True if execution was successful, False otherwise
        """
        try:
            # Start logcat capture
            self.legacy_component.start_capture()
            return True
        except Exception as e:
            self.logger.error(f"Error executing legacy logcat component: {e}")
            error_handler = ErrorHandler.get_instance()
            error_context = {
                "component": "LegacyLogcatComponentAdapter",
                "operation": "execute_logcat",
                "task_id": self.task.id
            }
            error_handler.handle_error(e, error_context)
            return False
            
    def cleanup(self, context: Dict[str, Any]) -> bool:
        """
        Clean up any resources used by the component.
        
        Args:
            context: Dictionary with task context information
            
        Returns:
            True if cleanup was successful, False otherwise
        """
        try:
            # Stop logcat capture
            self.legacy_component.stop_capture()
            return True
        except Exception as e:
            self.logger.error(f"Error cleaning up legacy logcat component: {e}")
            error_handler = ErrorHandler.get_instance()
            error_context = {
                "component": "LegacyLogcatComponentAdapter",
                "operation": "cleanup_logcat",
                "task_id": self.task.id
            }
            error_handler.handle_error(e, error_context)
            return False


class LegacyStaticAnalysisComponentAdapter(BaseTaskComponent):
    """
    Adapter for the legacy StaticAnalysisComponent.
    
    Wraps the legacy component to implement the new interface for loading
    static analysis data.
    """
    
    def __init__(self, task: ITask, event_bus: Optional[EventBus] = None):
        """
        Initialize the adapter with a task and event bus.
        
        Args:
            task: Task to execute
            event_bus: Optional event bus for notifications
        """
        super().__init__("StaticAnalysisComponent", event_bus)
        
        # Import here to avoid circular imports
        from rv_android_core.experiment.task.components.static_analysis import StaticAnalysisComponent
        
        # Create the legacy component
        self.legacy_component = StaticAnalysisComponent(task, event_bus)
        self.task = task
        
    def _execute_impl(self, context: Dict[str, Any]) -> bool:
        """
        Execute the component's primary function.
        
        Args:
            context: Dictionary with task context information
            
        Returns:
            True if execution was successful, False otherwise
        """
        try:
            # Load static analysis data
            return self.legacy_component.load_static_data(context)
        except Exception as e:
            self.logger.error(f"Error executing legacy static analysis component: {e}")
            error_handler = ErrorHandler.get_instance()
            error_context = {
                "component": "LegacyStaticAnalysisComponentAdapter",
                "operation": "execute_static_analysis",
                "task_id": self.task.id
            }
            error_handler.handle_error(e, error_context)
            return False
            
    def cleanup(self, context: Dict[str, Any]) -> bool:
        """
        Clean up any resources used by the component.
        
        Args:
            context: Dictionary with task context information
            
        Returns:
            True if cleanup was successful, False otherwise
        """
        # No cleanup needed for static analysis
        return True


class LegacyToolExecutionComponentAdapter(BaseTaskComponent):
    """
    Adapter for the legacy ToolExecutionComponent.
    
    Wraps the legacy component to implement the new interface for executing
    testing tools.
    """
    
    def __init__(self, task: ITask, tool: Any, event_bus: Optional[EventBus] = None):
        """
        Initialize the adapter with a task, tool, and event bus.
        
        Args:
            task: Task to execute
            tool: Tool implementation to use
            event_bus: Optional event bus for notifications
        """
        super().__init__("ToolExecutionComponent", event_bus)
        
        # Import here to avoid circular imports
        from rv_android_core.experiment.task.components.tool_execution import ToolExecutionComponent
        
        # Create the legacy component
        self.legacy_component = ToolExecutionComponent(task, tool, event_bus)
        self.task = task
        
    def _execute_impl(self, context: Dict[str, Any]) -> bool:
        """
        Execute the component's primary function.
        
        Args:
            context: Dictionary with task context information
            
        Returns:
            True if execution was successful, False otherwise
        """
        try:
            # Execute the tool
            self.legacy_component.execute_tool()
            return True
        except Exception as e:
            self.logger.error(f"Error executing legacy tool execution component: {e}")
            error_handler = ErrorHandler.get_instance()
            error_context = {
                "component": "LegacyToolExecutionComponentAdapter",
                "operation": "execute_tool",
                "task_id": self.task.id
            }
            error_handler.handle_error(e, error_context)
            return False
            
    def cleanup(self, context: Dict[str, Any]) -> bool:
        """
        Clean up any resources used by the component.
        
        Args:
            context: Dictionary with task context information
            
        Returns:
            True if cleanup was successful, False otherwise
        """
        try:
            # Clean up tool processes
            self.legacy_component.cleanup_processes()
            return True
        except Exception as e:
            self.logger.error(f"Error cleaning up legacy tool execution component: {e}")
            error_handler = ErrorHandler.get_instance()
            error_context = {
                "component": "LegacyToolExecutionComponentAdapter",
                "operation": "cleanup_tool",
                "task_id": self.task.id
            }
            error_handler.handle_error(e, error_context)
            return False


def create_legacy_component_adapters(task: Task, tool: Any, event_bus: Optional[EventBus] = None) -> Dict[str, BaseTaskComponent]:
    """
    Create adapters for all legacy components.
    
    Args:
        task: Task to execute
        tool: Tool to use
        event_bus: Optional event bus
        
    Returns:
        Dictionary mapping component names to adapters
    """
    adapters = {
        "StaticAnalysis": LegacyStaticAnalysisComponentAdapter(task, event_bus),
        "Coverage": LegacyCoverageComponentAdapter(task, event_bus),
        "Emulator": LegacyEmulatorComponentAdapter(task, event_bus),
        "Logcat": LegacyLogcatComponentAdapter(task, event_bus),
        "ToolExecution": LegacyToolExecutionComponentAdapter(task, tool, event_bus)
    }
    
    return adapters