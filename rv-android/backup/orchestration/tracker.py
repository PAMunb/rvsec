# rvandroid/experiment/orchestration/tracker.py
"""
Execution tracking for experiment orchestration.

This module provides classes for tracking experiment execution, including
metrics collection, checkpoint creation, and status reporting.
"""

import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Set, Any, Optional

from rvandroid.experiment.orchestration.interfaces import IExecutionTracker
from rvandroid.util.logging.manager import LoggingManager


@dataclass
class ExecutionStatistics:
    """
    Statistics for experiment execution.
    
    ### Architectural Decisions:
    - Uses dataclass for type safety and serialization
    - Encapsulates all relevant execution metrics
    - Provides clear, structured data representation
    - Facilitates consistent metric tracking and reporting
    
    ### Role in the System:
    - Provides a structured container for execution metrics
    - Enables consistent metric representation and access
    - Facilitates serialization for reporting and checkpointing
    - Supports detailed execution analysis and monitoring
    """
    tasks_total: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_pending: int = 0
    tasks_running: int = 0
    execution_time: float = 0
    avg_task_time: float = 0
    peak_concurrency: int = 0
    retry_count: int = 0
    error_rate: float = 0.0
    current_concurrency: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        result = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        # Convert datetime objects to ISO format strings
        if self.start_time:
            result['start_time'] = self.start_time.isoformat()
        if self.end_time:
            result['end_time'] = self.end_time.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionStatistics':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary data
            
        Returns:
            ExecutionStatistics instance
        """
        # Convert ISO format strings back to datetime objects
        if 'start_time' in data and data['start_time']:
            data['start_time'] = datetime.fromisoformat(data['start_time'])
        if 'end_time' in data and data['end_time']:
            data['end_time'] = datetime.fromisoformat(data['end_time'])
        return cls(**data)
    
    def update(self, other: Dict[str, Any]) -> None:
        """
        Update statistics from another dict.
        
        Args:
            other: Dictionary with updates
        """
        for key, value in other.items():
            if hasattr(self, key):
                setattr(self, key, value)


@dataclass
class ExecutionCheckpoint:
    """
    Checkpoint for experiment execution.
    
    ### Architectural Decisions:
    - Uses dataclass for type safety and serialization
    - Encapsulates all necessary recovery information
    - Provides clear separation of concerns for checkpointing
    - Facilitates consistent checkpoint creation and restoration
    
    ### Role in the System:
    - Provides a structured container for checkpoint data
    - Enables consistent checkpoint representation and access
    - Facilitates serialization for storage and recovery
    - Supports experiment resumption and recovery
    """
    timestamp: datetime
    statistics: ExecutionStatistics
    completed_tasks: Set[str] = field(default_factory=set)
    failed_tasks: Set[str] = field(default_factory=set)
    pending_tasks: Set[str] = field(default_factory=set)
    running_tasks: Set[str] = field(default_factory=set)
    custom_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            'timestamp': self.timestamp.isoformat(),
            'statistics': self.statistics.to_dict(),
            'completed_tasks': list(self.completed_tasks),
            'failed_tasks': list(self.failed_tasks),
            'pending_tasks': list(self.pending_tasks),
            'running_tasks': list(self.running_tasks),
            'custom_data': self.custom_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionCheckpoint':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary data
            
        Returns:
            ExecutionCheckpoint instance
        """
        # Convert ISO format string back to datetime
        timestamp = datetime.fromisoformat(data['timestamp'])
        
        # Deserialize statistics
        statistics = ExecutionStatistics.from_dict(data['statistics'])
        
        # Convert lists back to sets
        completed_tasks = set(data['completed_tasks'])
        failed_tasks = set(data['failed_tasks'])
        pending_tasks = set(data['pending_tasks'])
        running_tasks = set(data.get('running_tasks', []))
        
        return cls(
            timestamp=timestamp,
            statistics=statistics,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            pending_tasks=pending_tasks,
            running_tasks=running_tasks,
            custom_data=data.get('custom_data', {})
        )
    
    def save_to_file(self, filepath: str) -> None:
        """
        Save checkpoint to file.
        
        Args:
            filepath: Path to save to
        """
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'ExecutionCheckpoint':
        """
        Load checkpoint from file.
        
        Args:
            filepath: Path to load from
            
        Returns:
            ExecutionCheckpoint instance
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)


class ExecutionTracker(IExecutionTracker):
    """
    Tracker for experiment execution.
    
    ### Architectural Decisions:
    - Implements a comprehensive execution tracking system
    - Supports detailed metrics and checkpoint capabilities
    - Enables thread-safe tracking in concurrent environments
    - Provides clear separation of tracking concerns
    
    ### Role in the System:
    - Tracks experiment execution progress and metrics
    - Provides checkpoint and recovery capabilities
    - Enables detailed progress and performance monitoring
    - Facilitates experiment status reporting and analysis
    """
    
    def __init__(self, experiment_id: str, results_dir: str):
        """
        Initialize the execution tracker.
        
        Args:
            experiment_id: Unique experiment ID
            results_dir: Results directory
        """
        self.experiment_id = experiment_id
        self.results_dir = results_dir
        self.statistics = ExecutionStatistics()
        self.statistics.start_time = datetime.now()
        
        # Task tracking
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.pending_tasks: Set[str] = set()
        self.running_tasks: Dict[str, datetime] = {}
        self.task_times: Dict[str, float] = {}
        
        # Checkpointing
        self.checkpoints: List[ExecutionCheckpoint] = []
        self.checkpoint_dir = os.path.join(results_dir, 'checkpoints')
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        
        # Custom data
        self.custom_data: Dict[str, Any] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Logging
        self.logger = LoggingManager.get_instance().get_logger(
            'experiment.orchestration.tracker',
            {
                'experiment_id': experiment_id,
                'component': 'ExecutionTracker'
            }
        )
    
    def track_task_start(self, task_id: str) -> None:
        """
        Track the start of a task.
        
        Args:
            task_id: ID of the started task
        """
        with self._lock:
            # Track running task
            self.running_tasks[task_id] = datetime.now()
            
            # Remove from pending if present
            if task_id in self.pending_tasks:
                self.pending_tasks.remove(task_id)
            
            # Update concurrency metrics
            current = len(self.running_tasks)
            self.statistics.tasks_running = current
            self.statistics.current_concurrency = current
            
            if current > self.statistics.peak_concurrency:
                self.statistics.peak_concurrency = current
    
    def track_task_completion(self, task_id: str, success: bool, execution_time: float) -> None:
        """
        Track the completion of a task.
        
        Args:
            task_id: ID of the completed task
            success: Whether the task completed successfully
            execution_time: Task execution time in seconds
        """
        with self._lock:
            # Remove from running tasks
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            
            # Update task status
            if success:
                self.completed_tasks.add(task_id)
                self.statistics.tasks_completed += 1
            else:
                self.failed_tasks.add(task_id)
                self.statistics.tasks_failed += 1
            
            # Update statistics
            self.statistics.tasks_running = len(self.running_tasks)
            self.statistics.tasks_pending = len(self.pending_tasks)
            self.statistics.current_concurrency = len(self.running_tasks)
            
            # Record task time
            self.task_times[task_id] = execution_time
            
            # Update average task time
            if self.statistics.tasks_completed > 0:
                completed_times = [
                    time for task_id, time in self.task_times.items()
                    if task_id in self.completed_tasks
                ]
                if completed_times:
                    self.statistics.avg_task_time = sum(completed_times) / len(completed_times)
            
            # Update error rate
            total_done = self.statistics.tasks_completed + self.statistics.tasks_failed
            if total_done > 0:
                self.statistics.error_rate = self.statistics.tasks_failed / total_done
            
            # Update total execution time
            if self.statistics.start_time:
                self.statistics.execution_time = (
                    datetime.now() - self.statistics.start_time
                ).total_seconds()
    
    def add_pending_task(self, task_id: str) -> None:
        """
        Add a task to the pending list.
        
        Args:
            task_id: ID of the pending task
        """
        with self._lock:
            self.pending_tasks.add(task_id)
            self.statistics.tasks_pending = len(self.pending_tasks)
            self.statistics.tasks_total = (
                self.statistics.tasks_completed +
                self.statistics.tasks_failed +
                self.statistics.tasks_pending +
                len(self.running_tasks)
            )
    
    def track_retry(self, task_id: str) -> None:
        """
        Track a task retry.
        
        Args:
            task_id: ID of the retried task
        """
        with self._lock:
            self.statistics.retry_count += 1
            
            # Move back to pending
            if task_id in self.failed_tasks:
                self.failed_tasks.remove(task_id)
                self.pending_tasks.add(task_id)
                self.statistics.tasks_failed -= 1
                self.statistics.tasks_pending = len(self.pending_tasks)
    
    def create_checkpoint(self) -> Dict[str, Any]:
        """
        Create a checkpoint of the current execution state.
        
        Returns:
            Checkpoint data
        """
        with self._lock:
            # Create checkpoint
            checkpoint = ExecutionCheckpoint(
                timestamp=datetime.now(),
                statistics=self.statistics,
                completed_tasks=self.completed_tasks.copy(),
                failed_tasks=self.failed_tasks.copy(),
                pending_tasks=self.pending_tasks.copy(),
                running_tasks=set(self.running_tasks.keys()),
                custom_data=self.custom_data.copy()
            )
            
            # Save checkpoint
            self.checkpoints.append(checkpoint)
            
            # Save to file
            checkpoint_path = os.path.join(
                self.checkpoint_dir, 
                f"checkpoint_{len(self.checkpoints)}.json"
            )
            checkpoint.save_to_file(checkpoint_path)
            
            self.logger.info(f"Created execution checkpoint: {checkpoint_path}")
            
            return checkpoint.to_dict()
    
    def restore_from_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        """
        Restore execution state from a checkpoint.
        
        Args:
            checkpoint: Checkpoint data
        """
        with self._lock:
            if isinstance(checkpoint, dict):
                # Convert dict to ExecutionCheckpoint
                cp = ExecutionCheckpoint.from_dict(checkpoint)
            else:
                cp = checkpoint
                
            # Update state
            self.statistics = cp.statistics
            self.completed_tasks = cp.completed_tasks.copy()
            self.failed_tasks = cp.failed_tasks.copy()
            self.pending_tasks = cp.pending_tasks.copy()
            
            # Reset running tasks
            self.running_tasks = {}
            
            # Update custom data
            self.custom_data = cp.custom_data.copy()
            
            self.logger.info(f"Restored from checkpoint: {cp.timestamp.isoformat()}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get current execution statistics.
        
        Returns:
            Statistics dictionary
        """
        with self._lock:
            # Update execution time
            if self.statistics.start_time:
                self.statistics.execution_time = (
                    datetime.now() - self.statistics.start_time
                ).total_seconds()
                
            # Convert to dict
            stats_dict = self.statistics.to_dict()
            
            # Add formatted times
            stats_dict['execution_time_formatted'] = self._format_time(
                self.statistics.execution_time
            )
            
            # Add task breakdown if available
            if hasattr(self, 'task_breakdown'):
                stats_dict['task_breakdown'] = self.task_breakdown
                
            return stats_dict
    
    def get_progress(self) -> float:
        """
        Get execution progress as a percentage.
        
        Returns:
            Progress percentage (0-100)
        """
        with self._lock:
            total = self.statistics.tasks_total
            if total == 0:
                return 0.0
                
            completed = self.statistics.tasks_completed + self.statistics.tasks_failed
            return (completed * 100.0) / total
    
    def format_progress(self) -> str:
        """
        Format progress information for logging.
        
        Returns:
            Formatted progress string
        """
        with self._lock:
            total = self.statistics.tasks_total
            completed = self.statistics.tasks_completed
            failed = self.statistics.tasks_failed
            pending = self.statistics.tasks_pending
            running = len(self.running_tasks)
            
            if total == 0:
                return "No tasks"
                
            progress = self.get_progress()
            return (
                f"Progress: {progress:.1f}% [{completed + failed}/{total}] "
                f"(completed: {completed}, failed: {failed}, "
                f"running: {running}, pending: {pending})"
            )
    
    def set_task_breakdown(self, tools: Dict[str, Dict[str, int]], apps: Dict[str, Dict[str, int]]) -> None:
        """
        Set task breakdown by tool and app.
        
        Args:
            tools: Tool breakdown
            apps: App breakdown
        """
        with self._lock:
            self.task_breakdown = {
                'tools': tools,
                'apps': apps
            }
    
    def record_experiment_end(self) -> None:
        """Record the end of the experiment."""
        with self._lock:
            self.statistics.end_time = datetime.now()
            if self.statistics.start_time:
                self.statistics.execution_time = (
                    self.statistics.end_time - self.statistics.start_time
                ).total_seconds()
            
            # Create final checkpoint
            self.create_checkpoint()
            
            # Save final statistics
            stats_path = os.path.join(self.results_dir, "execution_statistics.json")
            with open(stats_path, 'w') as f:
                json.dump(self.get_statistics(), f, indent=2)
                
            self.logger.info(f"Experiment execution completed. Statistics saved to {stats_path}")
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """
        Format time in seconds to human-readable string.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted time string
        """
        if seconds < 60:
            return f"{seconds:.1f}s"
            
        minutes = int(seconds // 60)
        seconds = seconds % 60
        
        if minutes < 60:
            return f"{minutes}m {seconds:.1f}s"
            
        hours = minutes // 60
        minutes = minutes % 60
        
        return f"{hours}h {minutes}m {seconds:.1f}s"