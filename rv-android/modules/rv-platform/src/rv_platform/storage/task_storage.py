# rvandroid/experiment/task/storage.py
"""
Task storage system for persisting task information.

This module provides a robust storage mechanism for task state and results,
supporting atomic file operations, transaction management, and comprehensive
error handling.
"""

import hashlib
import json
import os
import shutil
import threading
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import Field
from rv_android_core.domain.task import Task, TaskFactory, TaskState
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.validation.base import BaseValidatedModel
from rv_platform.interfaces.task_interfaces import ITaskStorage


class ExperimentMetadata(BaseValidatedModel):
    """
    Minimal experiment metadata for storage and continuation support.

    ### Architectural Decisions:
    - Stores only essential runtime data to avoid duplication with ExperimentConfig
    - Uses config_checksum to detect configuration changes for continuation validation
    - Maintains minimal footprint for performance and storage efficiency
    - Provides experiment lifecycle tracking without config redundancy

    ### Role in the System:
    - Tracks experiment execution status and lifecycle
    - Enables experiment continuation detection and validation
    - Provides runtime statistics without duplicating configuration data
    - Supports experiment recovery and status reporting
    """

    experiment_id: str = Field(description="Unique experiment identifier")
    start_time: datetime = Field(description="Experiment start timestamp")
    config_checksum: str = Field(
        description="SHA-256 checksum of experiment configuration"
    )
    current_status: str = Field(
        default="running", description="Current experiment status"
    )

    @classmethod
    def create_from_config(
        cls, experiment_id: str, config_dict: Dict
    ) -> "ExperimentMetadata":
        """
        Create metadata from experiment configuration.

        Args:
            experiment_id: Unique experiment identifier
            config_dict: Experiment configuration dictionary

        Returns:
            ExperimentMetadata instance
        """
        # Calculate config checksum for continuation validation
        config_json = json.dumps(config_dict, sort_keys=True)
        config_checksum = hashlib.sha256(config_json.encode()).hexdigest()

        return cls(
            experiment_id=experiment_id,
            start_time=datetime.now(),
            config_checksum=config_checksum,
            current_status="running",
        )


class StorageConfig(BaseValidatedModel):
    """
    Configuration for task storage behavior and metadata management.

    ### Architectural Decisions:
    - Separates storage behavior configuration from experiment configuration
    - Provides fine-grained control over storage features and performance
    - Enables storage optimization strategies for different experiment types
    - Maintains backwards compatibility through sensible defaults

    ### Role in the System:
    - Controls storage feature enablement and behavior
    - Provides storage performance tuning capabilities
    - Enables experiment-specific storage optimization
    - Supports different storage strategies for various use cases
    """

    enable_metadata: bool = Field(
        default=True, description="Enable experiment metadata storage"
    )
    enable_statistics: bool = Field(
        default=True, description="Enable statistics calculation"
    )
    auto_save: bool = Field(
        default=True, description="Automatically save after task updates"
    )
    compression: bool = Field(default=False, description="Enable storage compression")
    backup_count: int = Field(default=3, description="Number of backup files to keep")


class ExperimentStatistics(BaseValidatedModel):
    """
    Runtime experiment statistics calculated from task data.

    ### Architectural Decisions:
    - Calculates statistics from task data rather than storing redundant information
    - Provides comprehensive experiment progress and performance metrics
    - Updates dynamically based on current task states
    - Optimized for frequent recalculation without performance impact

    ### Role in the System:
    - Provides real-time experiment progress information
    - Enables experiment monitoring and reporting
    - Supports experiment continuation decision making
    - Facilitates experiment performance analysis
    """

    total_tasks: int = Field(default=0, description="Total number of tasks")
    completed_tasks: int = Field(default=0, description="Number of completed tasks")
    failed_tasks: int = Field(default=0, description="Number of failed tasks")
    pending_tasks: int = Field(default=0, description="Number of pending tasks")
    completion_percentage: float = Field(
        default=0.0, description="Completion percentage"
    )
    average_execution_time: float = Field(
        default=0.0, description="Average task execution time in seconds"
    )
    total_execution_time: float = Field(
        default=0.0, description="Total execution time in seconds"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now, description="Last statistics update timestamp"
    )


class TaskStorage(ITaskStorage):
    """
    Manages task persistence with atomic operations, transaction support, and experiment metadata.

    ### Architectural Decisions:
    - Implements atomic file operations to prevent data corruption
    - Uses a thread-safe design for concurrent access
    - Provides transaction support for multi-step operations
    - Includes minimal experiment metadata for continuation support
    - Enables flexible task querying and filtering with enhanced statistics

    ### Role in the System:
    - Persists task information to disk with experiment metadata
    - Retrieves task information from storage with continuation support
    - Ensures data integrity during storage operations
    - Supports filtering and querying of tasks with statistics
    - Provides experiment continuation and recovery capabilities
    """

    def __init__(
        self,
        storage_file: str,
        task_factory: Optional[TaskFactory] = None,
        storage_config: Optional[StorageConfig] = None,
        experiment_metadata: Optional[ExperimentMetadata] = None,
    ):
        """
        Initialize storage with file path and metadata support.

        Args:
            storage_file: Path to the JSON file for task persistence. Created
                on first save if it does not exist.
            task_factory: Factory for creating Task instances from serialized
                data. Defaults to TaskFactory(Task).
            storage_config: Controls storage behavior (auto-save, metadata,
                statistics, compression). Defaults to StorageConfig().
            experiment_metadata: Experiment metadata for continuation support.
                Can also be set later via set_experiment_metadata().

        State:
            tasks: Dict mapping task IDs to Task objects (the in-memory store).
            loaded: Whether load() has been called successfully.
            lock: RLock for thread-safe access to tasks and transactions.
            in_transaction: Whether a transaction is currently active.
            transaction_tasks: Buffered task changes during an active transaction.
        """
        self.storage_file = storage_file
        self.task_factory = task_factory or TaskFactory(Task)
        self.storage_config = storage_config or StorageConfig()
        self.experiment_metadata = experiment_metadata

        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_platform.storage.task_storage", {CONTEXT_COMPONENT: "TaskStorage"}
        )

        # In-memory task store, keyed by task ID. This is the authoritative
        # representation of all known tasks: both loaded from disk and added
        # during the current session. Persisted to disk via save().
        self.tasks: Dict[str, Task] = {}
        self.loaded = False

        # RLock (reentrant) because save() may be called from within update_task(),
        # which already holds the lock. A regular Lock would deadlock in that case.
        self.lock = threading.RLock()

        # Transaction support for batching multiple updates into a single atomic
        # disk write. Without transactions, each update_task() triggers a save(),
        # which is fine for single-task updates but expensive for bulk operations.
        self.in_transaction = False
        self.transaction_tasks: Dict[str, Task] = {}

        # Statistics cache with a 10-second TTL. Avoids recomputing stats on
        # every call during rapid polling (e.g., progress reporting) while still
        # reflecting recent task completions.
        self._statistics_cache: Optional[ExperimentStatistics] = None
        self._statistics_cache_time: Optional[datetime] = None

    def load(self) -> bool:
        """
        Load tasks from storage file.

        Returns:
            True if loading succeeded, False otherwise
        """
        with self.lock:
            if not os.path.exists(self.storage_file):
                self.logger.info(
                    f"Storage file {self.storage_file} does not exist, starting with empty storage"
                )
                self.loaded = True
                return True

            try:
                self.logger.info(f"Loading tasks from {self.storage_file}")
                with open(self.storage_file, "r") as f:
                    data = json.load(f)

                    # Process tasks
                    for task_data in data.get("tasks", []):
                        task = self.task_factory.create_task_from_dict(task_data)
                        if task:
                            self.tasks[task.id] = task

                    # Load experiment metadata if available and enabled
                    if self.storage_config.enable_metadata and "experiment" in data:
                        experiment_data = data["experiment"]
                        self.experiment_metadata = ExperimentMetadata(**experiment_data)
                        self.logger.info(
                            f"Loaded experiment metadata for {self.experiment_metadata.experiment_id}"
                        )

                    # Log statistics if available
                    if "statistics" in data:
                        stats_data = data["statistics"]
                        self.logger.info(
                            f"Previous experiment statistics: "
                            f"{stats_data.get('completed_tasks', 0)}/{stats_data.get('total_tasks', 0)} tasks completed "
                            f"({stats_data.get('completion_percentage', 0):.1f}%)"
                        )

                    self.logger.info(f"Loaded {len(self.tasks)} tasks")
                    self.loaded = True
                    return True

            except Exception as e:
                self.logger.error(f"Error loading tasks: {e}")
                error_handler = ErrorHandler.get_instance()
                error_context = {
                    "component": "TaskStorage",
                    "operation": "load_tasks",
                    "storage_file": self.storage_file,
                }
                error_handler.handle_error(e, error_context)
                return False

    def save(self) -> bool:
        """
        Save tasks to storage file with atomic write-then-rename.

        Write to a temporary file first, fsync, then atomically rename to
        the target path. Include experiment metadata and statistics when
        enabled in StorageConfig.

        Returns:
            True if saving succeeded, False otherwise. On failure, the
            temporary file is cleaned up if possible.
        """
        with self.lock:
            temp_file = None

            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)

                # Prepare the complete persistence payload. Version 3 includes
                # experiment metadata (config checksum for resume validation) and
                # per-task coverage_metrics (fallback when LogcatRepository is
                # not available on resume).
                data = {
                    "version": 3,
                    "timestamp": datetime.now().isoformat(),
                    "tasks": [task.to_dict() for task in self.tasks.values()],
                }

                # Add experiment metadata if enabled and available
                if self.storage_config.enable_metadata and self.experiment_metadata:
                    # Serialize datetime objects to ISO format for JSON compatibility
                    metadata_dict = self.experiment_metadata.model_dump()
                    metadata_dict["start_time"] = (
                        self.experiment_metadata.start_time.isoformat()
                    )
                    data["experiment"] = metadata_dict

                # Add statistics if enabled
                if self.storage_config.enable_statistics:
                    statistics = self._calculate_statistics()
                    # Serialize datetime objects to ISO format for JSON compatibility
                    stats_dict = statistics.model_dump()
                    stats_dict["last_updated"] = statistics.last_updated.isoformat()
                    data["statistics"] = stats_dict

                # Atomic write: write to temp file first, then rename. This prevents
                # corrupted tasks.json if the process is killed mid-write.
                # shutil.move is used instead of os.rename because the temp file
                # and target may be on different filesystems in Docker containers.
                temp_file = f"{self.storage_file}.tmp"

                with open(temp_file, "w") as f:
                    json.dump(data, f, indent=2)

                    # fsync ensures data reaches the physical disk, not just
                    # the OS page cache. Without this, a power failure after
                    # rename could leave an empty file.
                    f.flush()
                    os.fsync(f.fileno())

                shutil.move(temp_file, self.storage_file)

                self.logger.info(
                    f"Saved {len(self.tasks)} tasks to {self.storage_file}"
                )
                return True

            except Exception as e:
                self.logger.error(f"Error saving tasks: {e}")
                error_handler = ErrorHandler.get_instance()
                error_context = {
                    "component": "TaskStorage",
                    "operation": "save_tasks",
                    "storage_file": self.storage_file,
                    "task_count": len(self.tasks),
                }
                error_handler.handle_error(e, error_context)

                # Clean up temporary file if it exists
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception as cleanup_error:
                        self.logger.warning(
                            f"Failed to remove temporary file: {cleanup_error}"
                        )
                        error_handler.handle_error(
                            cleanup_error,
                            {
                                "component": "TaskStorage",
                                "operation": "cleanup_temp_file",
                                "temp_file": temp_file,
                            },
                        )

                return False

    def add_task(self, task: Task) -> None:
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
                # Clear statistics cache when tasks are added
                self._statistics_cache = None
                self.logger.debug(f"Added task {task.id}")

    def update_task(self, task: Task) -> None:
        """
        Update a task in storage and save changes if auto_save is enabled.

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
                # Clear statistics cache when tasks are updated
                self._statistics_cache = None
                if self.storage_config.auto_save:
                    self.save()
                self.logger.debug(f"Updated task {task.id}")

    def get_task(self, task_id: str) -> Optional[Task]:
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

    def get_tasks(self) -> List[Task]:
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

    def get_tasks_by_state(self, state: TaskState) -> List[Task]:
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

    def get_completed_tasks(self) -> List[Task]:
        """
        Get tasks that are completed.

        If a transaction is in progress, the returned list includes all tasks
        with any modifications from the transaction buffer.

        Returns:
            List of completed tasks
        """
        return self.get_tasks_by_state(TaskState.COMPLETED)

    def get_pending_tasks(self) -> List[Task]:
        """
        Get tasks that are not yet completed, failed, or canceled.

        If a transaction is in progress, the returned list includes all tasks
        with any modifications from the transaction buffer.

        Returns:
            List of pending tasks
        """
        excluded_states = [
            TaskState.COMPLETED,
            TaskState.ERROR,
            TaskState.CANCELED,
            TaskState.ARCHIVED,
        ]
        return [
            task
            for task in self.get_tasks()
            if task.result.state not in excluded_states
        ]

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

            # Transaction buffer: changes accumulate here instead of going
            # to self.tasks. On commit, the buffer is merged into self.tasks
            # and saved in a single atomic write. On rollback, the buffer is
            # discarded and self.tasks remains untouched.
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

                self.logger.debug(
                    f"Transaction committed with {len(self.transaction_tasks)} changes"
                )
                return result

            except Exception as e:
                self.logger.error(f"Error committing transaction: {e}")
                error_handler = ErrorHandler.get_instance()
                error_context = {
                    "component": "TaskStorage",
                    "operation": "commit_transaction",
                    "transaction_task_count": len(self.transaction_tasks),
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
                    # Use None as a sentinel for "delete on commit". The commit
                    # handler must check for None entries and remove them from
                    # self.tasks instead of merging them.
                    self.transaction_tasks[task_id] = None  # type: ignore
                    self.logger.debug(
                        f"Marked task {task_id} for deletion in transaction"
                    )
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

    def get_tasks_by_apk(self, apk_name: str) -> List[Task]:
        """
        Get tasks for a specific APK.

        Args:
            apk_name: APK name to filter by

        Returns:
            List of matching tasks
        """
        return [task for task in self.get_tasks() if task.config.apk_name == apk_name]

    def get_tasks_by_tool(self, tool_name: str) -> List[Task]:
        """
        Get tasks for a specific tool.

        Args:
            tool_name: Tool name to filter by

        Returns:
            List of matching tasks
        """
        return [
            task
            for task in self.get_tasks()
            if task.config.tool_config.name == tool_name
        ]

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

    def bulk_update(self, tasks: List[Task]) -> bool:
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
                    "task_count": len(tasks),
                }
                error_handler.handle_error(e, error_context)
                self.rollback_transaction()
                return False

    @ErrorHandler.handle_errors(component="TaskStorage", phase="statistics")
    def _calculate_statistics(self) -> ExperimentStatistics:
        """
        Calculate experiment statistics from current task data.

        Count tasks by state, compute completion percentage, and aggregate
        execution times across all tasks with positive execution time.

        Returns:
            ExperimentStatistics populated with total/completed/failed/pending
            counts, completion percentage, and execution time aggregates.
        """
        tasks = list(self.tasks.values())
        total_tasks = len(tasks)

        if total_tasks == 0:
            return ExperimentStatistics()

        # Count tasks by state
        completed_tasks = len(
            [t for t in tasks if t.result.state == TaskState.COMPLETED]
        )
        failed_tasks = len([t for t in tasks if t.result.state == TaskState.ERROR])
        pending_tasks = len(
            [
                t
                for t in tasks
                if t.result.state
                not in [TaskState.COMPLETED, TaskState.ERROR, TaskState.CANCELED]
            ]
        )

        # Calculate percentages
        completion_percentage = (
            (completed_tasks / total_tasks) * 100.0 if total_tasks > 0 else 0.0
        )

        # Calculate execution times
        execution_times = [
            t.result.execution_time_seconds
            for t in tasks
            if t.result.execution_time_seconds > 0
        ]

        total_execution_time = sum(execution_times)
        average_execution_time = (
            total_execution_time / len(execution_times) if execution_times else 0.0
        )

        return ExperimentStatistics(
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            pending_tasks=pending_tasks,
            completion_percentage=completion_percentage,
            average_execution_time=average_execution_time,
            total_execution_time=total_execution_time,
            last_updated=datetime.now(),
        )

    def get_statistics(self) -> ExperimentStatistics:
        """
        Get current experiment statistics with caching.

        Returns:
            ExperimentStatistics with current metrics
        """
        with self.lock:
            now = datetime.now()

            # 10-second cache TTL avoids recalculating statistics on every call
            # during tight monitoring loops while keeping data reasonably fresh.
            if (
                self._statistics_cache
                and self._statistics_cache_time
                and (now - self._statistics_cache_time).total_seconds() < 10
            ):
                return self._statistics_cache

            # Calculate fresh statistics
            self._statistics_cache = self._calculate_statistics()
            self._statistics_cache_time = now

            return self._statistics_cache

    def set_experiment_metadata(self, metadata: ExperimentMetadata) -> None:
        """
        Set experiment metadata for the storage.

        Args:
            metadata: ExperimentMetadata to set
        """
        with self.lock:
            self.experiment_metadata = metadata
            self.logger.debug(f"Set experiment metadata for {metadata.experiment_id}")

    def get_experiment_metadata(self) -> Optional[ExperimentMetadata]:
        """
        Get current experiment metadata.

        Returns:
            ExperimentMetadata if available, None otherwise
        """
        return self.experiment_metadata

    def update_experiment_status(self, status: str) -> None:
        """
        Update experiment status in metadata.

        Args:
            status: New experiment status
        """
        with self.lock:
            if self.experiment_metadata:
                self.experiment_metadata.current_status = status
                if self.storage_config.auto_save:
                    self.save()
                self.logger.debug(f"Updated experiment status to: {status}")

    def check_continuation_compatibility(self, config_dict: Dict) -> bool:
        """
        Check if experiment can be continued with given configuration.

        Args:
            config_dict: New experiment configuration

        Returns:
            True if continuation is compatible, False otherwise
        """
        if not self.experiment_metadata:
            return False

        # Checksum comparison detects ANY config change (tools, timeouts,
        # repetitions, APK directory, etc.). sort_keys=True ensures deterministic
        # serialization so the same config always produces the same hash.
        # A mismatch is a WARNING, not an error: resume proceeds anyway because
        # task identity matching (not config equality) determines what to skip.
        config_json = json.dumps(config_dict, sort_keys=True)
        new_checksum = hashlib.sha256(config_json.encode()).hexdigest()

        compatible = new_checksum == self.experiment_metadata.config_checksum

        if not compatible:
            self.logger.debug(
                f"Configuration checksum mismatch: "
                f"stored={self.experiment_metadata.config_checksum[:8]}, "
                f"new={new_checksum[:8]}"
            )

        return compatible
