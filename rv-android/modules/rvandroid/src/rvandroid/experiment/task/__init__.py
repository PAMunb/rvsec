# rvandroid/experiment/task/__init__.py
"""
Task execution subsystem for RV-Android experiments.

This module provides a comprehensive framework for defining, executing, and
tracking experiment tasks. It supports component-based task execution, state
machine-based lifecycle management, and robust error handling.
"""

# Export interfaces
from rv_android_core.experiment.task.interfaces import (
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
from rv_android_core.experiment.task.task_model import (
    TaskConfiguration,
    TaskResult,
    Task
)

# Export storage implementation
from rv_android_core.experiment.task.storage import TaskStorage

# Export executor implementation
from rv_android_core.experiment.task.executor import TaskExecutor

# Export component system
from rv_android_core.experiment.task.component import (
    BaseTaskComponent,
    ComponentRegistry,
    ComponentFactory
)

# Export task manager
from rv_android_core.experiment.task.manager import TaskManager

# Export component adapters
from rv_android_core.experiment.task.components.adapter import (
    LegacyCoverageComponentAdapter,
    LegacyEmulatorComponentAdapter,
    LegacyLogcatComponentAdapter,
    LegacyStaticAnalysisComponentAdapter,
    LegacyToolExecutionComponentAdapter,
    create_legacy_component_adapters
)

# Export all components
from rv_android_core.experiment.task.components import (
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
    # 'TaskFactory',
    
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
    # TODO deprecated
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