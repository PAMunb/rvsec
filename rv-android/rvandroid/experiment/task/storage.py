# rvandroid/experiment/task/storage.py
"""
Task storage system for persisting task information.

This module provides a robust storage mechanism for task state and results,
supporting atomic file operations, transaction management, and comprehensive
error handling.
"""

import json
import os
import shutil
import threading
from datetime import datetime
from typing import Dict, List, Optional

from rvandroid.experiment.task.interfaces import ITaskStorage, ITask, TaskState
from rvandroid.experiment.task.task_model import Task, TaskFactory
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.logging.manager import LoggingManager


class TaskStorage(ITaskStorage):
    """
    Manages task persistence with atomic operations and transaction support.
    
    ### Architectural Decisions:
    - Implements atomic file operations to prevent data corruption
    - Uses a thread-safe design for concurrent access
    - Provides transaction support for multi-step operations
    - Enables flexible task querying and filtering
    
    ### Role in the System:
    - Persists task information to disk
    - Retrieves task information from storage
    - Ensures data integrity during storage operations
    - Supports filtering and querying of tasks
    """

    def __init__(self, storage_file: str, task_factory: Optional[TaskFactory] = None):
        """
        Initialize storage with file path.

        Args:
            storage_file: Path to storage file
            task_factory: Optional TaskFactory for creating tasks
        """
        self.storage_file = storage_file
        self.task_factory = task_factory or TaskFactory(Task)

        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger('experiment.task_storage')

        # Task storage
        self.tasks: Dict[str, Task] = {}
        self.loaded = False

        # Thread synchronization
        self.lock = threading.RLock()

        # Transaction support
        self.in_transaction = False
        self.transaction_tasks: Dict[str, Task] = {}

    def load(self) -> bool:
        """
        Load tasks from storage file.

        Returns:
            True if loading succeeded, False otherwise
        """
        with self.lock:
            if not os.path.exists(self.storage_file):
                self.logger.info(f"Storage file {self.storage_file} does not exist, starting with empty storage")
                self.loaded = True
                return True

            try:
                self.logger.info(f"Loading tasks from {self.storage_file}")
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)

                    # Process tasks
                    for task_data in data.get("tasks", []):
                        task = self.task_factory.create_task_from_dict(task_data)
                        if task:
                            self.tasks[task.id] = task

                    self.logger.info(f"Loaded {len(self.tasks)} tasks")
                    self.loaded = True
                    return True

            except Exception as e:
                self.logger.error(f"Error loading tasks: {e}")
                error_handler = ErrorHandler.get_instance()
                error_context = {
                    "component": "TaskStorage",
                    "operation": "load_tasks",
                    "storage_file": self.storage_file
                }
                error_handler.handle_error(e, error_context)
                return False

    def save(self) -> bool:
        """
        Save tasks to storage file with atomic operations.
        Uses atomic file operations to prevent data corruption.

        Returns:
            True if saving succeeded, False otherwise
        """
        with self.lock:
            temp_file = None

            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)

                # Prepare data
                data = {
                    "version": 2,  # Version 2 uses UUID-based task IDs
                    "timestamp": datetime.now().isoformat(),
                    "tasks": [task.to_dict() for task in self.tasks.values()]
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
                error_handler = ErrorHandler.get_instance()
                error_context = {
                    "component": "TaskStorage",
                    "operation": "save_tasks",
                    "storage_file": self.storage_file,
                    "task_count": len(self.tasks)
                }
                error_handler.handle_error(e, error_context)

                # Clean up temporary file if it exists
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception as cleanup_error:
                        self.logger.warning(f"Failed to remove temporary file: {cleanup_error}")
                        error_handler.handle_error(cleanup_error, {
                            "component": "TaskStorage",
                            "operation": "cleanup_temp_file",
                            "temp_file": temp_file
                        })

                return False

    def add_task(self, task: ITask) -> None:
        """
        Add a task to storage.
        
        If a transaction is in progress, the task is added to the transaction
        buffer instead of being immediately stored.

        Args:
            task: Task to add
        """
        with self.lock:
            if self.in_transaction:
                self.transaction_tasks[task.id] = task
            else:
                self.tasks[task.id] = task
                self.logger.debug(f"Added task {task.id}")

    def update_task(self, task: ITask) -> None:
        """
        Update a task in storage and save changes.
        
        If a transaction is in progress, the task is updated in the transaction
        buffer instead of being immediately stored.

        Args:
            task: Task to update
        """
        with self.lock:
            if self.in_transaction:
                self.transaction_tasks[task.id] = task
            else:
                self.tasks[task.id] = task
                self.save()
                self.logger.debug(f"Updated task {task.id}")

    def get_task(self, task_id: str) -> Optional[ITask]:
        """
        Get a task by ID.
        
        If a transaction is in progress and the task has been modified in the
        transaction, the transactional version is returned.

        Args:
            task_id: Task ID

        Returns:
            Task if found, None otherwise
        """
        with self.lock:
            # Check transaction buffer first if in transaction
            if self.in_transaction and task_id in self.transaction_tasks:
                return self.transaction_tasks[task_id]

            return self.tasks.get(task_id)

    def get_tasks(self) -> List[ITask]:
        """
        Get all tasks.
        
        If a transaction is in progress, the returned list includes all tasks
        with any modifications from the transaction buffer.

        Returns:
            List of all tasks
        """
        with self.lock:
            if not self.in_transaction:
                return list(self.tasks.values())

            # Merge transaction tasks with base tasks
            result = self.tasks.copy()
            result.update(self.transaction_tasks)
            return list(result.values())

    def get_tasks_by_state(self, state: TaskState) -> List[ITask]:
        """
        Get tasks with specified state.
        
        If a transaction is in progress, the returned list includes all tasks
        with any modifications from the transaction buffer.

        Args:
            state: Task state to filter by

        Returns:
            List of matching tasks
        """
        return [task for task in self.get_tasks() if task.result.state == state]

    def get_completed_tasks(self) -> List[ITask]:
        """
        Get tasks that are completed.
        
        If a transaction is in progress, the returned list includes all tasks
        with any modifications from the transaction buffer.

        Returns:
            List of completed tasks
        """
        return self.get_tasks_by_state(TaskState.COMPLETED)

    def get_pending_tasks(self) -> List[ITask]:
        """
        Get tasks that are not yet completed, failed, or canceled.
        
        If a transaction is in progress, the returned list includes all tasks
        with any modifications from the transaction buffer.

        Returns:
            List of pending tasks
        """
        excluded_states = [TaskState.COMPLETED, TaskState.ERROR, TaskState.CANCELED, TaskState.ARCHIVED]
        return [task for task in self.get_tasks() if task.result.state not in excluded_states]

    def begin_transaction(self) -> None:
        """
        Begin a transaction for batching task updates.
        
        Transactions allow multiple task updates to be performed as a single
        atomic operation, ensuring consistency in the task storage.
        """
        with self.lock:
            if self.in_transaction:
                self.logger.warning("Transaction already in progress")
                return

            self.in_transaction = True
            self.transaction_tasks = {}
            self.logger.debug("Transaction started")

    def commit_transaction(self) -> bool:
        """
        Commit the current transaction, applying all changes.
        
        Returns:
            True if commit succeeded, False otherwise
        """
        with self.lock:
            if not self.in_transaction:
                self.logger.warning("No transaction in progress")
                return False

            try:
                # Apply all changes
                self.tasks.update(self.transaction_tasks)

                # Save changes
                result = self.save()

                # Reset transaction state
                self.in_transaction = False
                self.transaction_tasks = {}

                self.logger.debug(f"Transaction committed with {len(self.transaction_tasks)} changes")
                return result

            except Exception as e:
                self.logger.error(f"Error committing transaction: {e}")
                error_handler = ErrorHandler.get_instance()
                error_context = {
                    "component": "TaskStorage",
                    "operation": "commit_transaction",
                    "transaction_task_count": len(self.transaction_tasks)
                }
                error_handler.handle_error(e, error_context)
                return False

    def rollback_transaction(self) -> None:
        """
        Rollback the current transaction, discarding all changes.
        """
        with self.lock:
            if not self.in_transaction:
                self.logger.warning("No transaction in progress")
                return

            # Reset transaction state
            self.in_transaction = False
            count = len(self.transaction_tasks)
            self.transaction_tasks = {}

            self.logger.debug(f"Transaction rolled back, discarded {count} changes")

    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task from storage.
        
        If a transaction is in progress, the task is marked for deletion in the
        transaction buffer instead of being immediately removed.

        Args:
            task_id: ID of task to delete
            
        Returns:
            True if task was deleted, False if not found
        """
        with self.lock:
            if self.in_transaction:
                if task_id in self.tasks or task_id in self.transaction_tasks:
                    # Use None as a marker for deletion
                    self.transaction_tasks[task_id] = None  # type: ignore
                    self.logger.debug(f"Marked task {task_id} for deletion in transaction")
                    return True
                return False

            if task_id in self.tasks:
                del self.tasks[task_id]
                self.save()
                self.logger.debug(f"Deleted task {task_id}")
                return True
            return False

    def clear(self) -> bool:
        """
        Clear all tasks from storage.
        
        Returns:
            True if clear succeeded, False otherwise
        """
        with self.lock:
            if self.in_transaction:
                self.logger.warning("Cannot clear storage during transaction")
                return False

            self.tasks = {}
            result = self.save()
            self.logger.info("Cleared all tasks from storage")
            return result

    def get_tasks_by_apk(self, apk_name: str) -> List[ITask]:
        """
        Get tasks for a specific APK.
        
        Args:
            apk_name: APK name to filter by
            
        Returns:
            List of matching tasks
        """
        return [task for task in self.get_tasks() if task.config.apk_name == apk_name]

    def get_tasks_by_tool(self, tool_name: str) -> List[ITask]:
        """
        Get tasks for a specific tool.
        
        Args:
            tool_name: Tool name to filter by
            
        Returns:
            List of matching tasks
        """
        return [task for task in self.get_tasks() if task.config.tool_name == tool_name]

    def count_tasks_by_state(self) -> Dict[str, int]:
        """
        Count tasks by state.
        
        Returns:
            Dictionary mapping state names to counts
        """
        counts = {}
        for state in TaskState:
            counts[state.name] = len(self.get_tasks_by_state(state))
        return counts

    def bulk_update(self, tasks: List[ITask]) -> bool:
        """
        Update multiple tasks in a single transaction.
        
        Args:
            tasks: List of tasks to update
            
        Returns:
            True if all updates succeeded, False otherwise
        """
        with self.lock:
            try:
                self.begin_transaction()

                for task in tasks:
                    self.update_task(task)

                return self.commit_transaction()

            except Exception as e:
                self.logger.error(f"Error in bulk update: {e}")
                error_handler = ErrorHandler.get_instance()
                error_context = {
                    "component": "TaskStorage",
                    "operation": "bulk_update",
                    "task_count": len(tasks)
                }
                error_handler.handle_error(e, error_context)
                self.rollback_transaction()
                return False
