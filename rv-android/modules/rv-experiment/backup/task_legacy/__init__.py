# rvandroid/experiment/task/__init__.py
"""
Task execution subsystem for RV-Android experiments.

This module provides a comprehensive framework for defining, executing, and
tracking experiment tasks. It supports component-based task execution, state
machine-based lifecycle management, and robust error handling.
"""

# Export interfaces (only remaining component and executor interfaces)
from rv_experiment.experiment.task.interfaces import (
    TaskState,
    ITaskComponent,
    ITaskExecutor,
    ITaskStorage
)

# Export model implementations (now the primary task types)
from rv_experiment.experiment.task.task_model import (
    TaskConfiguration,
    TaskResult,
    Task,
    TaskFactory
)

# Export storage implementation
from rv_experiment.experiment.task.storage import TaskStorage

# Export executor implementation
from rv_experiment.experiment.task.executor import TaskExecutor

# Export component system
from rv_experiment.experiment.task.component import (
    BaseTaskComponent,
    ComponentRegistry,
    ComponentFactory
)

# Export task manager - moved to backup
# from rv_experiment.experiment.task.manager import TaskManager

# Export component adapters
from rv_experiment.experiment.task.components.adapter import (
    LegacyCoverageComponentAdapter,
    LegacyEmulatorComponentAdapter,
    LegacyLogcatComponentAdapter,
    LegacyStaticAnalysisComponentAdapter,
    LegacyToolExecutionComponentAdapter,
    create_legacy_component_adapters
)

# Export all components
from rv_experiment.experiment.task.components import (
    StaticAnalysisComponent,
    CoverageComponent,
    EmulatorComponent,
    LogcatComponent,
    ToolExecutionComponent
)

# Define the public API
__all__ = [
    # Interfaces (only remaining component and executor interfaces)
    'TaskState',
    'ITaskComponent', 
    'ITaskExecutor',
    'ITaskStorage',
    
    # Models (now the primary task types)
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