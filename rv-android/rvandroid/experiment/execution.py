"""
Execution management module for RVAndroid framework.
Handles task execution, memory management and results tracking.
"""

import json
import logging
import os.path
from dataclasses import dataclass
from datetime import datetime
import shutil
from typing import Callable, Set, List, Dict, Optional

from rvandroid.app import App
from rvandroid.constants import (
    EXTENSION_METHODS,
    EXECUTION_MEMORY_FILENAME,
    EXTENSION_GESDA,
    EXTENSION_GATOR,
    EXTENSION_REACH
)
from rvandroid.experiment.memory import Memory
from rvandroid.experiment.task import Task, TaskStatus
from rvandroid.tools.tool_spec import AbstractTool
from settings import RESULTS_DIR, TIMESTAMP, INSTRUMENTED_DIR

# Configure module logger
logger = logging.getLogger(__name__)


@dataclass
class ExecutionStats:
    """Statistics about task execution progress"""
    total_tasks: int
    completed_tasks: int
    completion_percentage: float
    errors: List[str] = None

    @classmethod
    def from_memory(cls, memory: Memory) -> 'ExecutionStats':
        """Create statistics from Memory object"""
        total = len(memory.tasks)
        executed = sum(1 for task in memory.tasks if task.status == TaskStatus.EXECUTED)
        percentage = (executed * 100 / total) if total > 0 else 0.0
        errors = [
            f"task={task}, error={task.error}"
            for task in memory.tasks if task.error
        ]
        return cls(total, executed, round(percentage, 2), errors)


class ExecutionManager:
    """Manages the execution of tasks and maintains execution state"""

    def __init__(self):
        self.memory: Optional[Memory] = None
        self.tasks: List[Task] = []
        self.base_results_dir: str = ""
        self.memory_file: str = ""
        self.current_task: Optional[Task] = None
        self.executed_tasks: Set[Task] = set()
        self.start_time: datetime = datetime.now()
        self.finish_time: Optional[datetime] = None

    def create_memory(
            self,
            apks: List[App],
            repetitions: int,
            timeouts: List[int],
            tools: List[AbstractTool],
            memory_file: str,
            sort_key: Callable = lambda x: (x.repetition, x.timeout, x.tool, x.apk)
    ) -> None:
        """
        Creates or loads execution memory based on existing file.
        
        Args:
            apks: List of apps to process
            repetitions: Number of times to repeat each task
            timeouts: List of timeout values
            tools: List of tools to use
            memory_file: Path to memory file
            sort_key: Function to sort tasks
        """
        if os.path.exists(memory_file):
            self._resume_execution(memory_file)
        else:
            self._start_new_execution(repetitions, timeouts, tools, apks)

        self.tasks = self.memory.get_tasks(sort_key)
        self._init_executed_tasks()
        logger.info(f"Tasks: {self.get_statistics()}")
        logger.info(f"Execution memory file: {self.memory_file}")

    def _resume_execution(self, memory_file: str) -> None:
        """Resumes execution from existing memory file"""
        self.base_results_dir = os.path.dirname(memory_file)
        self.memory_file = memory_file
        self.memory = self._read_memory()

    def _start_new_execution(
            self,
            repetitions: int,
            timeouts: List[int],
            tools: List[AbstractTool],
            apks: List[App]
    ) -> None:
        """Starts new execution with given parameters"""
        self.base_results_dir = create_results_dir()
        self.memory_file = os.path.join(self.base_results_dir, EXECUTION_MEMORY_FILENAME)
        self.memory = self._create_new_memory(repetitions, timeouts, tools, apks)
        self._write_memory()

    def get_statistics(self) -> Dict:
        """Returns current execution statistics"""
        stats = ExecutionStats.from_memory(self.memory)
        return {
            "tasks": stats.total_tasks,
            "completed": stats.completed_tasks,
            "pct": stats.completion_percentage
        }

    def start_task(self, task: Task) -> None:
        """
        Initializes and starts a new task
        
        Args:
            task: Task to start
        """
        task.initialize(self.base_results_dir)
        self.current_task = task
        create_folder_if_not_exists(task.results_dir)
        copy_static_analysis_files(task.apk, task.results_dir)

    def finish_task(self, task: Task) -> None:
        """
        Marks task as complete and updates memory
        
        Args:
            task: Task to finish
        """
        task.status = TaskStatus.EXECUTED
        task.finish_time = datetime.now()
        self.executed_tasks.add(task)
        self.current_task = None
        self._write_memory()

    def task_error(self, task: Task, exception: Exception) -> None:
        """
        Handles task execution error
        
        Args:
            task: Failed task
            exception: Exception that occurred
        """
        task.error = str(exception)
        task.finish_time = datetime.now()
        self._write_memory()

    def _read_memory(self) -> Memory:
        """Reads execution memory from file"""
        logger.info(f"Reading execution memory file: {self.memory_file}")
        return Memory.read(self.memory_file)

    def _write_memory(self) -> None:
        """Writes current memory state to file"""
        logger.info(f"Writing execution memory file: {self.memory_file}")
        self.memory.write(self.memory_file)

    def _init_executed_tasks(self) -> None:
        """Initializes set of executed tasks from memory"""
        self.executed_tasks = {
            task for task in self.tasks if task.status == TaskStatus.EXECUTED
        }

    @staticmethod
    def _create_new_memory(
            repetitions: int,
            timeouts: List[int],
            tools_obj: List[AbstractTool],
            apks: List[App]
    ) -> Memory:
        """Creates new Memory instance with given parameters"""
        tools = [x.name for x in tools_obj]
        logger.info(
            "Creating new execution memory=[apks=%d, repetitions=%d, timeouts=%s, tools=%s]",
            len(apks), repetitions, timeouts, tools
        )
        memory = Memory()
        memory.init(repetitions, timeouts, tools, apks)
        return memory


# Utility functions
def create_results_dir() -> str:
    """Creates and returns path to results directory"""
    results_dir = os.path.join(RESULTS_DIR, TIMESTAMP)
    create_folder_if_not_exists(results_dir)
    return results_dir


def create_folder_if_not_exists(path: str) -> None:
    """Creates directory if it doesn't exist"""
    os.makedirs(path, exist_ok=True)


def copy_static_analysis_files(apk: str, app_results_dir: str) -> None:
    """
    Copies static analysis files for an app to results directory
    
    Args:
        apk: App identifier
        app_results_dir: Target directory for files
    """
    extensions = [EXTENSION_METHODS, EXTENSION_GESDA, EXTENSION_GATOR, EXTENSION_REACH]
    for extension in extensions:
        file_name = f"{apk}{extension}"
        file_path = os.path.join(INSTRUMENTED_DIR, file_name)
        if os.path.exists(file_path):
            shutil.copy(file_path, app_results_dir)


def get_execution_status(memory_file: str) -> str:
    """
    Returns JSON string with execution status
    
    Args:
        memory_file: Path to memory file
        
    Returns:
        JSON string with execution statistics
    """
    memory = Memory.read(memory_file)
    stats = ExecutionStats.from_memory(memory)
    return json.dumps({
        "tasks": stats.total_tasks,
        "completed": stats.completed_tasks,
        "pct": stats.completion_percentage,
        "errors": stats.errors
    }, indent=2)
