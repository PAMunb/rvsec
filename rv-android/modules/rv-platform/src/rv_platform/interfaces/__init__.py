# Platform interfaces
from rv_android_core.domain.task import TaskState
from rv_platform.interfaces.task_interfaces import (
    ITaskComponent,
    ITaskExecutor,
    ITaskStorage,
)

__all__ = ["TaskState", "ITaskComponent", "ITaskExecutor", "ITaskStorage"]
