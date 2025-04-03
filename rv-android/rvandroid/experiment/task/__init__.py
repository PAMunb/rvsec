# rvandroid/experiment/task/__init__.py
"""
Task execution subsystem for RV-Android experiments.

This module provides a comprehensive framework for defining, executing, and
tracking experiment tasks. It supports component-based task execution, state
machine-based lifecycle management, and robust error handling.
"""

# Export interfaces
from rvandroid.experiment.task.interfaces import (
    TaskState,
    ITaskConfiguration,
    ITaskResult,
    ITask,
    ITaskComponent,
    ITaskExecutor,
    ITaskStorage,
    ITaskFactory
)

# Export model implementations
from rvandroid.experiment.task.models import (
    TaskConfiguration,
    TaskResult,
    Task,
    TaskFactory
)

# Export storage implementation
from rvandroid.experiment.task.storage import TaskStorage

# Export executor implementation
from rvandroid.experiment.task.executor import TaskExecutor

# Export component system
from rvandroid.experiment.task.component import (
    BaseTaskComponent,
    ComponentRegistry,
    ComponentFactory
)

# Export task manager
from rvandroid.experiment.task.manager import TaskManager

# Export component adapters
from rvandroid.experiment.task.components.adapter import (
    LegacyCoverageComponentAdapter,
    LegacyEmulatorComponentAdapter,
    LegacyLogcatComponentAdapter,
    LegacyStaticAnalysisComponentAdapter,
    LegacyToolExecutionComponentAdapter,
    create_legacy_component_adapters
)

# Export all components
from rvandroid.experiment.task.components import (
    StaticAnalysisComponent,
    CoverageComponent,
    EmulatorComponent,
    LogcatComponent,
    ToolExecutionComponent
)

# Define the public API
__all__ = [
    # Interfaces
    'TaskState',
    'ITaskConfiguration',
    'ITaskResult',
    'ITask',
    'ITaskComponent',
    'ITaskExecutor',
    'ITaskStorage',
    'ITaskFactory',
    
    # Models
    'TaskConfiguration',
    'TaskResult',
    'Task',
    'TaskFactory',
    
    # Storage
    'TaskStorage',
    
    # Executor
    'TaskExecutor',
    
    # Component system
    'BaseTaskComponent',
    'ComponentRegistry',
    'ComponentFactory',
    
    # Task manager
    'TaskManager',
    
    # Component adapters
    'LegacyCoverageComponentAdapter',
    'LegacyEmulatorComponentAdapter',
    'LegacyLogcatComponentAdapter',
    'LegacyStaticAnalysisComponentAdapter',
    'LegacyToolExecutionComponentAdapter',
    'create_legacy_component_adapters',
    
    # Components
    'StaticAnalysisComponent',
    'CoverageComponent',
    'EmulatorComponent',
    'LogcatComponent',
    'ToolExecutionComponent'
]