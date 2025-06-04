# rvandroid/experiment/orchestration/execution.py
"""
Execution strategies for experiment orchestration.

This module provides implementations of different execution strategies for
experiment orchestration, including sequential, parallel, adaptive, and
priority-based strategies.
"""

import concurrent.futures
import threading
import time
from typing import Dict, List, Any, Optional, Callable, TypeVar, Set, Generic

from rvandroid.app import App
from rvandroid.experiment.core.interfaces import IExecutionContext
from rvandroid.experiment.event import EventBus, EventType, TaskEvent
from rvandroid.experiment.orchestration.interfaces import ExecutionStrategy, TaskPriority
from rvandroid.experiment.orchestration.tracker import IExecutionTracker
from rvandroid.experiment.task.interfaces import ITask, ITaskExecutor
from rvandroid.tools.registry import ToolRegistry
from rvandroid.tools.tool_spec import AbstractTool
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.performance_monitor import PerformanceMonitor


T = TypeVar('T', bound=ITask)


class BaseExecutionStrategy(Generic[T], ExecutionStrategy[T]):
    """
    Base implementation of execution strategy.
    
    ### Architectural Decisions:
    - Provides common functionality for all execution strategies
    - Implements thread-safe execution control
    - Supports cancellation, pause, and resume operations
    - Facilitates consistent execution behavior across strategies
    
    ### Role in the System:
    - Serves as the foundation for all execution strategies
    - Provides common execution control mechanisms
    - Enables consistent behavior across different strategies
    - Facilitates extension with new strategy implementations
    """
    
    def __init__(self, 
                event_bus: EventBus,
                tracker: IExecutionTracker,
                tool_registry: ToolRegistry,
                registered_apps: Dict[str, App]):
        """
        Initialize the execution strategy.
        
        Args:
            event_bus: Event bus for communication
            tracker: Execution tracker
            tool_registry: Tool registry
            registered_apps: Registered apps
        """
        self.event_bus = event_bus
        self.tracker = tracker
        self.tool_registry = tool_registry
        self.registered_apps = registered_apps
        
        # Execution control
        self.should_stop = False
        self.paused = False
        self.paused_lock = threading.Condition()
        
        # Logging
        self.logger = LoggingManager.get_instance().get_logger(
            'experiment.orchestration.execution',
            {
                'component': self.__class__.__name__
            }
        )
    
    def execute(self, tasks: List[T], **kwargs) -> Dict[str, Any]:
        """
        Execute a set of tasks according to the strategy.
        
        Args:
            tasks: List of tasks to execute
            **kwargs: Additional execution parameters
            
        Returns:
            Execution statistics and results
        """
        # This should be implemented by subclasses
        raise NotImplementedError("Subclasses must implement execute()")
    
    def cancel(self) -> None:
        """Cancel ongoing execution."""
        self.should_stop = True
        
        # If paused, resume first then cancel
        if self.paused:
            self.resume()
    
    def pause(self) -> None:
        """Pause ongoing execution."""
        with self.paused_lock:
            self.paused = True
            self.logger.info("Execution paused")
    
    def resume(self) -> None:
        """Resume paused execution."""
        with self.paused_lock:
            self.paused = False
            self.paused_lock.notify_all()
            self.logger.info("Execution resumed")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current execution status.
        
        Returns:
            Status dictionary with execution metrics
        """
        status = self.tracker.get_statistics()
        status.update({
            'paused': self.paused,
            'cancelled': self.should_stop,
            'progress': self.tracker.get_progress()
        })
        return status
    
    def _wait_if_paused(self) -> bool:
        """
        Wait if execution is paused.
        
        Returns:
            True if execution should continue, False if cancelled
        """
        if self.should_stop:
            return False
            
        if self.paused:
            with self.paused_lock:
                while self.paused and not self.should_stop:
                    self.paused_lock.wait()
                    
        return not self.should_stop
    
    def _create_task_executor(self, task: T) -> Optional[ITaskExecutor]:
        """
        Create a task executor for the task.
        
        Args:
            task: Task to execute
            
        Returns:
            Task executor or None if task cannot be executed
        """
        # Get tool
        tool_name = getattr(task.config, 'tool_name', None)
        if not tool_name:
            self.logger.error(f"Task {task.id} has no tool specified")
            return None
            
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            self.logger.error(f"Tool not found for task {task.id}: {tool_name}")
            task.mark_error(f"Tool not found: {tool_name}")
            return None
            
        # Get app
        app_name = getattr(task.config, 'apk_name', None)
        if not app_name:
            self.logger.error(f"Task {task.id} has no app specified")
            return None
            
        app = self.registered_apps.get(app_name)
        if not app:
            self.logger.error(f"App not found for task {task.id}: {app_name}")
            task.mark_error(f"App not found: {app_name}")
            return None
            
        # Ensure app is set
        task.set_app(app)
        
        # Import here to avoid circular imports
        from rvandroid.experiment.task.executor import TaskExecutor
        
        # Create executor
        return TaskExecutor(task, tool, self.event_bus)
    
    def _execute_task(self, task: T) -> bool:
        """
        Execute a single task.
        
        Args:
            task: Task to execute
            
        Returns:
            True if the task was executed successfully, False otherwise
        """
        task_id = task.id
        self.logger.info(f"Executing task {task_id}")
        
        # Track task start
        self.tracker.track_task_start(task_id)
        
        # Create executor
        executor = self._create_task_executor(task)
        if not executor:
            self.tracker.track_task_completion(task_id, False, 0)
            
            # Publish task failed event
            self.event_bus.publish_task_event(
                event_type=EventType.TASK_FAILED,
                task_id=task_id,
                task_config={},
                details={"error": "Failed to create task executor"},
                source=self.__class__.__name__,
                channel=EventBus.ERROR_CHANNEL
            )
            
            return False
            
        try:
            # Execute task
            start_time = time.time()
            success = executor.execute()
            execution_time = time.time() - start_time
            
            # Track task completion
            self.tracker.track_task_completion(task_id, success, execution_time)
            
            # Publish event
            if success:
                self.event_bus.publish_task_event(
                    event_type=EventType.TASK_COMPLETED,
                    task_id=task_id,
                    task_config={},
                    source=self.__class__.__name__,
                    channel=EventBus.LIFECYCLE_CHANNEL
                )
            else:
                self.event_bus.publish_task_event(
                    event_type=EventType.TASK_FAILED,
                    task_id=task_id,
                    task_config={},
                    details={"error": "Task execution failed"},
                    source=self.__class__.__name__,
                    channel=EventBus.ERROR_CHANNEL
                )
                
            return success
            
        except Exception as e:
            # Track failure
            self.tracker.track_task_completion(task_id, False, 0)
            
            # Publish event
            self.event_bus.publish_task_event(
                event_type=EventType.TASK_FAILED,
                task_id=task_id,
                task_config={},
                details={"error": str(e)},
                source=self.__class__.__name__,
                channel=EventBus.ERROR_CHANNEL
            )
            
            self.logger.error(f"Error executing task {task_id}: {e}")
            return False


class SequentialExecutionStrategy(BaseExecutionStrategy[T]):
    """
    Sequential execution strategy.
    
    ### Architectural Decisions:
    - Executes tasks one at a time in sequence
    - Provides predictable, deterministic execution ordering
    - Supports pause/resume and cancellation
    - Facilitates simple debugging and troubleshooting
    
    ### Role in the System:
    - Provides a baseline execution strategy
    - Enables reliable execution for sensitive tests
    - Supports scenarios requiring strict ordering
    - Facilitates debugging of task interactions
    """
    
    def execute(self, tasks: List[T], **kwargs) -> Dict[str, Any]:
        """
        Execute tasks sequentially.
        
        Args:
            tasks: List of tasks to execute
            **kwargs: Additional execution parameters
            
        Returns:
            Execution statistics and results
        """
        self.should_stop = False
        self.paused = False
        
        self.logger.info(f"Starting sequential execution of {len(tasks)} tasks")
        
        for task in tasks:
            # Check if execution should be stopped
            if self.should_stop:
                self.logger.info("Execution cancelled")
                break
                
            # Check if execution is paused
            if not self._wait_if_paused():
                break
                
            # Execute task
            self._execute_task(task)
            
        self.logger.info("Sequential execution completed")
        
        return self.tracker.get_statistics()


class ParallelExecutionStrategy(BaseExecutionStrategy[T]):
    """
    Parallel execution strategy.
    
    ### Architectural Decisions:
    - Executes tasks concurrently using a thread pool
    - Provides efficient resource utilization
    - Supports a configurable level of parallelism
    - Facilitates faster overall execution
    
    ### Role in the System:
    - Enables efficient execution of independent tasks
    - Provides scalable execution for large task sets
    - Supports high-throughput experiment scenarios
    - Facilitates optimal resource utilization
    """
    
    def __init__(self, 
                event_bus: EventBus,
                tracker: IExecutionTracker,
                tool_registry: ToolRegistry,
                registered_apps: Dict[str, App],
                max_workers: int = 4):
        """
        Initialize the parallel execution strategy.
        
        Args:
            event_bus: Event bus for communication
            tracker: Execution tracker
            tool_registry: Tool registry
            registered_apps: Registered apps
            max_workers: Maximum number of concurrent tasks
        """
        super().__init__(event_bus, tracker, tool_registry, registered_apps)
        self.max_workers = max_workers
        self.executor = None
    
    def execute(self, tasks: List[T], **kwargs) -> Dict[str, Any]:
        """
        Execute tasks in parallel.
        
        Args:
            tasks: List of tasks to execute
            **kwargs: Additional execution parameters
            
        Returns:
            Execution statistics and results
        """
        self.should_stop = False
        self.paused = False
        max_workers = kwargs.get('max_workers', self.max_workers)
        
        self.logger.info(
            f"Starting parallel execution of {len(tasks)} tasks with {max_workers} workers"
        )
        
        # Create thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            self.executor = executor
            
            # Submit tasks
            futures = []
            for task in tasks:
                # Check for cancellation
                if self.should_stop:
                    self.logger.info("Execution cancelled before all tasks were submitted")
                    break
                    
                # Wait if paused
                if not self._wait_if_paused():
                    break
                    
                # Submit task
                future = executor.submit(self._execute_task, task)
                futures.append(future)
                
            # Wait for all tasks to complete
            for future in concurrent.futures.as_completed(futures):
                # Check for cancellation
                if self.should_stop:
                    self.logger.info("Execution cancelled while waiting for tasks to complete")
                    break
                    
                # Get result (ignoring exceptions, they're handled in _execute_task)
                try:
                    future.result()
                except Exception:
                    pass
            
        self.executor = None
        self.logger.info("Parallel execution completed")
        
        return self.tracker.get_statistics()
    
    def cancel(self) -> None:
        """Cancel ongoing execution."""
        super().cancel()
        
        # Shut down executor if it exists
        if self.executor:
            self.executor.shutdown(wait=False)


class AdaptiveExecutionStrategy(BaseExecutionStrategy[T]):
    """
    Adaptive execution strategy.
    
    ### Architectural Decisions:
    - Dynamically adjusts concurrency based on system resources
    - Provides efficient, adaptive resource utilization
    - Integrates with system performance monitoring
    - Facilitates optimal execution in variable environments
    
    ### Role in the System:
    - Enables efficient execution in resource-constrained environments
    - Provides adaptive scaling based on system capabilities
    - Supports optimal resource utilization during execution
    - Facilitates execution in environments with varying load
    """
    
    def __init__(self, 
                event_bus: EventBus,
                tracker: IExecutionTracker,
                tool_registry: ToolRegistry,
                registered_apps: Dict[str, App],
                initial_workers: int = 2,
                max_workers: int = 8,
                resource_threshold: float = 0.8):
        """
        Initialize the adaptive execution strategy.
        
        Args:
            event_bus: Event bus for communication
            tracker: Execution tracker
            tool_registry: Tool registry
            registered_apps: Registered apps
            initial_workers: Initial number of workers
            max_workers: Maximum number of workers
            resource_threshold: Resource utilization threshold (0-1)
        """
        super().__init__(event_bus, tracker, tool_registry, registered_apps)
        self.initial_workers = initial_workers
        self.max_workers = max_workers
        self.resource_threshold = resource_threshold
        self.performance_monitor = PerformanceMonitor()
        self.current_workers = initial_workers
        self.executor = None
    
    def execute(self, tasks: List[T], **kwargs) -> Dict[str, Any]:
        """
        Execute tasks with adaptive concurrency.
        
        Args:
            tasks: List of tasks to execute
            **kwargs: Additional execution parameters
            
        Returns:
            Execution statistics and results
        """
        self.should_stop = False
        self.paused = False
        
        # Get parameters
        initial_workers = kwargs.get('initial_workers', self.initial_workers)
        max_workers = kwargs.get('max_workers', self.max_workers)
        resource_threshold = kwargs.get('resource_threshold', self.resource_threshold)
        
        self.current_workers = initial_workers
        
        self.logger.info(
            f"Starting adaptive execution of {len(tasks)} tasks "
            f"(initial workers: {initial_workers}, max: {max_workers})"
        )
        
        # Start performance monitoring
        self.performance_monitor.start()
        
        try:
            # Create thread pool with initial workers
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                self.executor = executor
                
                # Limit initial concurrency
                semaphore = threading.Semaphore(initial_workers)
                futures = []
                
                # Submit tasks
                for task in tasks:
                    # Check for cancellation
                    if self.should_stop:
                        self.logger.info("Execution cancelled before all tasks were submitted")
                        break
                        
                    # Wait if paused
                    if not self._wait_if_paused():
                        break
                        
                    # Check resource utilization and adjust concurrency
                    self._adjust_concurrency(resource_threshold)
                    
                    # Execute task with semaphore to control concurrency
                    future = executor.submit(
                        self._execute_with_semaphore, 
                        task, 
                        semaphore,
                        self.current_workers
                    )
                    futures.append(future)
                    
                # Wait for all tasks to complete
                for future in concurrent.futures.as_completed(futures):
                    # Check for cancellation
                    if self.should_stop:
                        self.logger.info("Execution cancelled while waiting for tasks to complete")
                        break
                        
                    # Get result (ignoring exceptions, they're handled in _execute_task)
                    try:
                        future.result()
                    except Exception:
                        pass
                
        finally:
            # Stop performance monitoring
            self.performance_monitor.stop()
            self.executor = None
            
        self.logger.info("Adaptive execution completed")
        
        return self.tracker.get_statistics()
    
    def _execute_with_semaphore(self, task: T, semaphore: threading.Semaphore, worker_count: int) -> bool:
        """
        Execute a task with semaphore-controlled concurrency.
        
        Args:
            task: Task to execute
            semaphore: Semaphore for concurrency control
            worker_count: Current worker count
            
        Returns:
            True if the task was executed successfully, False otherwise
        """
        acquired = False
        try:
            # Acquire semaphore with timeout
            acquired = semaphore.acquire(timeout=60)
            if not acquired:
                self.logger.warning(f"Failed to acquire semaphore for task {task.id}")
                return False
                
            # Execute task
            return self._execute_task(task)
            
        finally:
            # Release semaphore if acquired
            if acquired:
                semaphore.release()
    
    def _adjust_concurrency(self, threshold: float) -> None:
        """
        Adjust concurrency based on system resources.
        
        Args:
            threshold: Resource utilization threshold (0-1)
        """
        # Get current resource usage
        resource_usage = self.performance_monitor.get_current_usage()
        cpu_percent = resource_usage.get('cpu_percent', 0) / 100.0  # Convert to 0-1 range
        memory_percent = resource_usage.get('memory_percent', 0) / 100.0
        
        # Check if we should adjust concurrency
        if cpu_percent > threshold or memory_percent > threshold:
            # Reduce concurrency
            if self.current_workers > 1:
                self.current_workers = max(1, self.current_workers - 1)
                self.logger.info(
                    f"Reducing concurrency to {self.current_workers} workers "
                    f"(CPU: {cpu_percent:.1%}, Memory: {memory_percent:.1%})"
                )
        elif cpu_percent < threshold * 0.7 and memory_percent < threshold * 0.7:
            # Increase concurrency
            if self.current_workers < self.max_workers:
                self.current_workers += 1
                self.logger.info(
                    f"Increasing concurrency to {self.current_workers} workers "
                    f"(CPU: {cpu_percent:.1%}, Memory: {memory_percent:.1%})"
                )
    
    def cancel(self) -> None:
        """Cancel ongoing execution."""
        super().cancel()
        
        # Shut down executor if it exists
        if self.executor:
            self.executor.shutdown(wait=False)
            
        # Stop performance monitoring
        self.performance_monitor.stop()


class PriorityBasedExecutionStrategy(BaseExecutionStrategy[T]):
    """
    Priority-based execution strategy.
    
    ### Architectural Decisions:
    - Executes tasks based on their priority levels
    - Provides control over execution ordering
    - Supports dynamic priority adjustment
    - Facilitates fine-grained control over resource allocation
    
    ### Role in the System:
    - Enables prioritization of critical tasks
    - Provides resource allocation based on task importance
    - Supports scenarios requiring explicit ordering
    - Facilitates fine-grained control over execution order
    """
    
    def __init__(self, 
                event_bus: EventBus,
                tracker: IExecutionTracker,
                tool_registry: ToolRegistry,
                registered_apps: Dict[str, App],
                max_workers: int = 4):
        """
        Initialize the priority-based execution strategy.
        
        Args:
            event_bus: Event bus for communication
            tracker: Execution tracker
            tool_registry: Tool registry
            registered_apps: Registered apps
            max_workers: Maximum number of concurrent tasks
        """
        super().__init__(event_bus, tracker, tool_registry, registered_apps)
        self.max_workers = max_workers
        self.task_priorities: Dict[str, TaskPriority] = {}
        self.executor = None
    
    def set_task_priority(self, task_id: str, priority: TaskPriority) -> None:
        """
        Set the priority for a task.
        
        Args:
            task_id: Task ID
            priority: Task priority
        """
        self.task_priorities[task_id] = priority
    
    def get_task_priority(self, task: T) -> TaskPriority:
        """
        Get the priority for a task.
        
        Args:
            task: Task to get priority for
            
        Returns:
            Task priority
        """
        return self.task_priorities.get(task.id, TaskPriority.NORMAL)
    
    def execute(self, tasks: List[T], **kwargs) -> Dict[str, Any]:
        """
        Execute tasks based on their priority.
        
        Args:
            tasks: List of tasks to execute
            **kwargs: Additional execution parameters
            
        Returns:
            Execution statistics and results
        """
        self.should_stop = False
        self.paused = False
        max_workers = kwargs.get('max_workers', self.max_workers)
        
        # Get priority function
        priority_function = kwargs.get('prioritize_by')
        if priority_function:
            # Apply priorities using function
            for task in tasks:
                if task.id not in self.task_priorities:
                    self.task_priorities[task.id] = priority_function(task)
        
        # Sort tasks by priority
        sorted_tasks = sorted(tasks, key=self.get_task_priority)
        
        self.logger.info(
            f"Starting priority-based execution of {len(tasks)} tasks with {max_workers} workers"
        )
        
        # Create thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            self.executor = executor
            
            # Create priority queues
            priority_queues: Dict[TaskPriority, List[T]] = {}
            for priority in TaskPriority:
                priority_queues[priority] = []
                
            # Distribute tasks to priority queues
            for task in sorted_tasks:
                priority = self.get_task_priority(task)
                priority_queues[priority].append(task)
                
            # Execute tasks by priority
            futures = []
            for priority in sorted(TaskPriority, key=lambda p: p.value):
                priority_tasks = priority_queues[priority]
                
                self.logger.info(f"Executing {len(priority_tasks)} tasks with priority {priority.name}")
                
                # Submit all tasks at this priority level
                for task in priority_tasks:
                    # Check for cancellation
                    if self.should_stop:
                        self.logger.info("Execution cancelled before all tasks were submitted")
                        break
                        
                    # Wait if paused
                    if not self._wait_if_paused():
                        break
                        
                    # Submit task
                    future = executor.submit(self._execute_task, task)
                    futures.append(future)
                    
            # Wait for all tasks to complete
            for future in concurrent.futures.as_completed(futures):
                # Check for cancellation
                if self.should_stop:
                    self.logger.info("Execution cancelled while waiting for tasks to complete")
                    break
                    
                # Get result (ignoring exceptions, they're handled in _execute_task)
                try:
                    future.result()
                except Exception:
                    pass
            
        self.executor = None
        self.logger.info("Priority-based execution completed")
        
        return self.tracker.get_statistics()
    
    def cancel(self) -> None:
        """Cancel ongoing execution."""
        super().cancel()
        
        # Shut down executor if it exists
        if self.executor:
            self.executor.shutdown(wait=False)