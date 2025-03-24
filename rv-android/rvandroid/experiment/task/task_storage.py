# rvandroid/experiment/task_storage.py
"""
Task storage system for persisting task information.
Provides a more robust storage mechanism for task state and results.
"""
import json
import logging
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any

from rvandroid.experiment.task.task_model import Task, TaskConfiguration, TaskStatus


class TaskStorage:
    """
    Manages task persistence and provides transaction support.
    Implements a more robust storage mechanism for task state.
    """

    def __init__(self, storage_file: str):
        """
        Initialize storage with file path.

        Args:
            storage_file: Path to storage file
        """
        self.storage_file = storage_file
        self.logger = logging.getLogger(__name__)
        self.tasks: Dict[int, Task] = {}
        self.loaded = False

    def load(self) -> bool:
        """
        Load tasks from storage file.

        Returns:
            True if loading succeeded, False otherwise
        """
        if not os.path.exists(self.storage_file):
            self.logger.info(f"Storage file {self.storage_file} does not exist, starting with empty storage")
            self.loaded = True
            return True

        try:
            self.logger.info(f"Loading tasks from {self.storage_file}")
            with open(self.storage_file, 'r') as f:
                data = json.load(f)

                # Set task counter to max ID + 1
                max_id = 0

                # Process tasks
                for task_data in data.get("tasks", []):
                    task = self._deserialize_task(task_data)
                    if task:
                        self.tasks[task.id] = task
                        max_id = max(max_id, task.id)

                # Set next task ID
                Task._next_id = max_id + 1

                self.logger.info(f"Loaded {len(self.tasks)} tasks")
                self.loaded = True
                return True

        except Exception as e:
            self.logger.error(f"Error loading tasks: {e}")
            return False

    def save(self) -> bool:
        """
        Save tasks to storage file with improved error handling.
        Uses atomic file operations to prevent data corruption.

        Returns:
            True if saving succeeded, False otherwise
        """
        temp_file = None

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)

            # Prepare data
            data = {
                "version": 1,
                "timestamp": datetime.now().isoformat(),
                "tasks": [self._serialize_task(task) for task in self.tasks.values()]
            }

            # Create a temporary file in the same directory
            temp_file = f"{self.storage_file}.tmp"

            # Write to the temporary file first
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)

                # Ensure data is written to disk
                f.flush()
                os.fsync(f.fileno())

            # Atomic rename to avoid partial writes
            shutil.move(temp_file, self.storage_file)

            self.logger.info(f"Saved {len(self.tasks)} tasks to {self.storage_file}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving tasks: {e}")

            # Clean up temporary file if it exists
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as cleanup_error:
                    self.logger.warning(f"Failed to remove temporary file: {cleanup_error}")

            return False

    def add_task(self, task: Task) -> None:
        """
        Add a task to storage.

        Args:
            task: Task to add
        """
        self.tasks[task.id] = task

    def update_task(self, task: Task) -> None:
        """
        Update a task in storage.

        Args:
            task: Task to update
        """
        self.tasks[task.id] = task
        self.save()

    def get_task(self, task_id: int) -> Optional[Task]:
        """
        Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task if found, None otherwise
        """
        return self.tasks.get(task_id)

    def get_tasks(self) -> List[Task]:
        """
        Get all tasks.

        Returns:
            List of all tasks
        """
        return list(self.tasks.values())

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """
        Get tasks with specified status.

        Args:
            status: Task status to filter by

        Returns:
            List of matching tasks
        """
        return [task for task in self.tasks.values() if task.result.status == status]

    def get_pending_tasks(self) -> List[Task]:
        """
        Get tasks that are not yet executed or failed.

        Returns:
            List of pending tasks
        """
        return [task for task in self.tasks.values()
                if task.result.status not in [TaskStatus.EXECUTED, TaskStatus.ERROR]]

    def _serialize_task(self, task: Task) -> Dict[str, Any]:
        """
        Serialize a task to dictionary.

        Args:
            task: Task to serialize

        Returns:
            Dictionary representation
        """
        return {
            "id": task.id,
            "config": {
                "apk_name": task.config.apk_name,
                "repetition": task.config.repetition,
                "timeout": task.config.timeout,
                "tool_name": task.config.tool_name,
                "no_window": task.config.no_window,
                "clean_logcat": task.config.clean_logcat,
                "skip_installation": task.config.skip_installation,
                "device_id": task.config.device_id
            },
            "result": task.result.to_dict()
        }

    def _deserialize_task(self, data: Dict[str, Any]) -> Optional[Task]:
        """
        Deserialize a task from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            Task instance
        """
        try:
            # Create config
            config_data = data.get("config", {})
            config = TaskConfiguration(
                apk_name=config_data.get("apk_name", ""),
                repetition=config_data.get("repetition", 1),
                timeout=config_data.get("timeout", 60),
                tool_name=config_data.get("tool_name", ""),
                no_window=config_data.get("no_window", False),
                clean_logcat=config_data.get("clean_logcat", True),
                skip_installation=config_data.get("skip_installation", False),
                device_id=config_data.get("device_id", "emulator-5554")
            )

            # Create task with given ID
            task = Task(config)
            task.id = data.get("id", task.id)

            # Set result
            result_data = data.get("result", {})
            task.result.status = TaskStatus[result_data.get("status", "CREATED")]

            # Parse dates
            if result_data.get("start_time"):
                task.result.start_time = datetime.fromisoformat(result_data["start_time"])
            if result_data.get("end_time"):
                task.result.end_time = datetime.fromisoformat(result_data["end_time"])

            task.result.execution_time_seconds = result_data.get("execution_time_seconds", 0)
            task.result.error_message = result_data.get("error_message")
            task.result.logcat_file = result_data.get("logcat_file", "")
            task.result.trace_file = result_data.get("trace_file", "")

            return task

        except Exception as e:
            self.logger.error(f"Error deserializing task: {e}")
            return None
