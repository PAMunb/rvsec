"""
Parallel execution manager with LLM model grouping strategy using existing TaskExecutor.

This component manages parallel execution of Task objects while optimizing GPU memory 
usage through intelligent grouping by LLM model. It uses existing rv-platform TaskExecutor
for individual task execution and coordinates model transitions.

### Architectural Decisions:
- **Model Grouping**: Groups Task objects by LLM model to minimize GPU memory operations
- **TaskExecutor Integration**: Uses existing rv-platform TaskExecutor for individual executions
- **Process Coordination**: Uses multiprocessing pool for parallel Task execution  
- **Transition Management**: Implements simple cleanup between model groups (ollama stop + sleep)
- **Failure Isolation**: Individual task failures don't affect other parallel executions

### Resource Management Strategy:
- **GPU Memory**: Only one LLM model loaded at a time across all workers
- **CPU Utilization**: User-configured worker count (3-10) without adaptive management
- **Emulator Management**: Delegates to existing rv-android-core EmulatorManager
- **Keep-Alive Strategy**: Uses 60-second keep-alive during model group execution

### Reuse from Old Test Framework:
- TestExecutor execution patterns and error handling
- EmulatorManager context management approach
- Task result processing and metrics collection
- Static analysis caching and integration patterns
"""

import os
import time
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import multiprocessing as mp

from rv_android_core.event import EventBus, EventType
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE, LOG_ERROR
from rv_android_core.util.logging.manager import LoggingManager
from rv_platform.execution.executor import TaskExecutor

from rv_test_framework.core.models import ModelGroup, TaskResult


def execute_single_task(
    task: Any,  # Task from rv-android-core
    worker_id: int,
    results_dir: str
) -> TaskResult:
    """
    Execute single Task object using existing TaskExecutor infrastructure.
    
    This function is executed in worker processes and reuses the execution patterns
    from the old test framework's TestExecutor.execute_test_case() method.
    
    ### Execution Steps (following old test framework patterns):
    1. Task includes emulator_port in additional_params configuration
    2. Create TaskExecutor instance using existing rv-platform infrastructure
    3. TaskExecutor coordinates EmulatorManager, ToolExecution, and result processing  
    4. RVAndroidTool extracts emulator_port from task configuration
    5. EmulatorManager uses assigned port for emulator operations
    6. Results automatically captured by existing infrastructure
    7. Clean up handled by existing component lifecycle
    
    Args:
        task: Task object from rv-android-core (includes all configuration)
        worker_id: Worker process identifier 
        results_dir: Directory for task results
        
    Returns:
        TaskResult with execution outcome and metrics
    """
    from datetime import datetime
    
    # Create task result object
    result = TaskResult(
        task_id=task.id,
        config_name=task.config.tool_config.additional_params.get("config_name", "unknown"),
        apk_name=task.config.apk_name,
        repetition=task.config.repetition
    )
    
    start_time = datetime.now()
    
    try:
        # Create TaskExecutor using existing infrastructure (following old TestExecutor patterns)
        task_executor = TaskExecutor(results_dir)
        
        # Execute task using existing TaskExecutor infrastructure
        # This delegates to all existing components (EmulatorComponent, ToolExecutionComponent, etc.)
        execution_success = task_executor.execute_task(task)
        
        end_time = datetime.now()
        result.execution_time = (end_time - start_time).total_seconds()
        result.success = execution_success
        
        # Set result file paths (following existing patterns)
        result.logcat_file = task.result.logcat_file if hasattr(task.result, 'logcat_file') else ""
        result.trace_file = task.result.trace_file if hasattr(task.result, 'trace_file') else ""
        
        # Extract metrics from task execution (following old test framework patterns)
        if hasattr(task, 'metrics') and task.metrics:
            result.metrics = task.metrics
        
    except Exception as e:
        end_time = datetime.now()
        result.execution_time = (end_time - start_time).total_seconds()
        result.success = False
        result.error_message = str(e)
    
    return result


class ParallelManager:
    """
    Manages parallel Task execution with model-based grouping using existing infrastructure.
    
    This class reuses the execution patterns from the old test framework's TestRunner and
    TestExecutor, adapting them for model-grouped parallel execution.
    
    ### Execution Flow:
    1. Groups Task objects by LLM model type and name
    2. Executes each group with configured parallelism using TaskExecutor
    3. Manages simple model transitions (ollama stop + sleep)
    4. Aggregates results through existing PerformanceMonitor
    5. No complex resource management - user responsibility
    
    ### Reuse from Old Test Framework:
    - TestRunner.run_test_suite() coordination patterns
    - TestExecutor.execute_test_case() execution logic  
    - EmulatorManager context management approach
    - Result processing and CSV export patterns
    """
    
    @ErrorHandler.handle_errors(
        component="ParallelManager",
        phase="initialization"
    )
    def __init__(
        self, 
        max_workers: int = 5,
        results_dir: str = "./results",
        event_bus: Optional[EventBus] = None
    ):
        """
        Initialize parallel manager with simple configuration.
        
        ### Initialization Strategy:
        Sets up process pool for parallel execution, prepares for Task object execution
        using existing TaskExecutor infrastructure, following old TestRunner patterns.
        
        Args:
            max_workers: Maximum parallel task executions (user-defined)
            results_dir: Directory for execution results  
            event_bus: Optional event bus for coordination
        """
        self.max_workers = max_workers
        self.results_dir = results_dir
        self.event_bus = event_bus or EventBus.get_instance()
        
        # Setup logging using existing infrastructure
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'rv_test_framework.execution.parallel_manager',
            {CONTEXT_COMPONENT: 'ParallelManager'}
        )
        
        # Error handler integration
        self.error_handler = ErrorHandler.get_instance()
        
        # Execution state
        self.current_model: Optional[str] = None
        self.total_tasks_executed = 0
        self.total_tasks_successful = 0
        
        self.logger.info(f"ParallelManager initialized: {max_workers} workers")
    
    @ErrorHandler.handle_errors(
        component="ParallelManager",
        phase="model_group_execution"
    )
    def execute_model_groups(
        self, 
        model_groups: List[ModelGroup],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[TaskResult]:
        """
        Execute all model groups with model transitions.
        
        This method follows the old test framework's TestRunner.run_test_suite() patterns,
        adapting them for model-grouped execution with simple transitions.
        
        ### Execution Strategy:
        - Execute each model group sequentially to avoid GPU memory conflicts
        - Use parallel execution within each model group  
        - Implement simple model transitions (ollama stop + sleep)
        - Aggregate results from all model groups
        
        Args:
            model_groups: List of model groups to execute
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of all task execution results
        """
        with self.logger.with_context(
            total_groups=len(model_groups),
            phase="model_groups_execution"
        ):
            self.logger.info(LOG_START.format(phase=f"execution of {len(model_groups)} model groups"))
            
            all_results: List[TaskResult] = []
            
            for group_index, model_group in enumerate(model_groups):
                try:
                    # Report progress
                    if progress_callback:
                        progress_callback(
                            group_index, 
                            len(model_groups), 
                            f"Executing model group: {model_group.model_name}"
                        )
                    
                    # Execute model group
                    group_results = self._execute_model_group(model_group, group_index)
                    all_results.extend(group_results)
                    
                    # Model transition (except for last group)
                    if group_index < len(model_groups) - 1:
                        self._transition_model(
                            current_model=model_group.model_name,
                            next_group=model_groups[group_index + 1]
                        )
                
                except Exception as e:
                    self.logger.error(f"Error executing model group {model_group.model_name}: {e}")
                    
                    # Create failure results for all tasks in this group
                    for task in model_group.tasks:
                        failure_result = TaskResult(
                            task_id=task.id,
                            config_name=task.config.tool_config.additional_params.get("config_name", "unknown"),
                            apk_name=task.config.apk_name,
                            repetition=task.config.repetition,
                            success=False,
                            error_message=f"Model group execution failed: {str(e)}"
                        )
                        all_results.append(failure_result)
            
            # Final progress update
            if progress_callback:
                progress_callback(len(model_groups), len(model_groups), "All model groups completed")
            
            self.logger.info(LOG_COMPLETE.format(phase=f"execution of {len(model_groups)} model groups"))
            self.logger.info(f"Total tasks executed: {len(all_results)}")
            
            return all_results
    
    def _execute_model_group(self, model_group: ModelGroup, group_index: int) -> List[TaskResult]:
        """
        Execute single model group using parallel execution.
        
        This method uses the execution patterns from the old test framework's
        TestExecutor, adapting them for parallel task execution.
        
        Args:
            model_group: Model group to execute
            group_index: Index of current group for logging
            
        Returns:
            List of task results for this model group
        """
        with self.logger.with_context(
            model_name=model_group.model_name,
            model_type=model_group.model_type,
            task_count=len(model_group.tasks),
            group_index=group_index
        ):
            self.logger.info(LOG_START.format(
                phase=f"model group {model_group.model_name} ({len(model_group.tasks)} tasks)"
            ))
            
            results: List[TaskResult] = []
            
            # Execute tasks in parallel using ProcessPoolExecutor
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks for this model group
                future_to_task = {}
                
                for worker_id, task in enumerate(model_group.tasks):
                    future = executor.submit(
                        execute_single_task,
                        task,
                        worker_id % self.max_workers,  # Distribute across workers
                        self.results_dir
                    )
                    future_to_task[future] = task
                
                # Collect results as they complete
                for future in as_completed(future_to_task):
                    try:
                        result = future.result(timeout=None)  # No timeout - task handles its own timeout
                        results.append(result)
                        
                        # Update statistics
                        self.total_tasks_executed += 1
                        if result.success:
                            self.total_tasks_successful += 1
                        
                        # Log task completion
                        status = "SUCCESS" if result.success else f"FAILED: {result.error_message}"
                        self.logger.info(f"Task {result.task_id} completed: {status}")
                        
                    except Exception as e:
                        task = future_to_task[future]
                        self.logger.error(f"Task execution failed: {task.id}: {e}")
                        
                        # Create failure result
                        failure_result = TaskResult(
                            task_id=task.id,
                            config_name=task.config.tool_config.additional_params.get("config_name", "unknown"),
                            apk_name=task.config.apk_name,
                            repetition=task.config.repetition,
                            success=False,
                            error_message=str(e)
                        )
                        results.append(failure_result)
                        self.total_tasks_executed += 1
            
            successful_count = sum(1 for r in results if r.success)
            failed_count = len(results) - successful_count
            
            self.logger.info(LOG_COMPLETE.format(
                phase=f"model group {model_group.model_name}: {successful_count} successful, {failed_count} failed"
            ))
            
            return results
    
    def _transition_model(self, current_model: str, next_group: ModelGroup) -> None:
        """
        Perform simple model transition between groups.
        
        ### Transition Strategy:
        - Stop current model using ollama stop command  
        - Sleep for GPU memory cleanup
        - Log transition for monitoring
        
        Args:
            current_model: Current model name to stop
            next_group: Next model group to prepare for
        """
        with self.logger.with_context(
            current_model=current_model,
            next_model=next_group.model_name
        ):
            self.logger.info(LOG_START.format(phase=f"model transition: {current_model} -> {next_group.model_name}"))
            
            try:
                # Stop current model to free GPU memory
                if next_group.model_type == "ollama":
                    stop_cmd = ["ollama", "stop", current_model]
                    self.logger.info(f"Stopping model: {' '.join(stop_cmd)}")
                    
                    result = subprocess.run(
                        stop_cmd,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode != 0:
                        self.logger.warning(f"Model stop command failed: {result.stderr}")
                    else:
                        self.logger.info(f"Model {current_model} stopped successfully")
                
                # Sleep for GPU memory cleanup (simple approach)
                cleanup_time = 60  # seconds
                self.logger.info(f"Waiting {cleanup_time}s for GPU memory cleanup")
                time.sleep(cleanup_time)
                
                self.logger.info(LOG_COMPLETE.format(phase="model transition"))
                
            except subprocess.TimeoutExpired:
                self.logger.warning(f"Model stop command timed out for {current_model}")
            except Exception as e:
                self.logger.warning(f"Model transition failed: {e}")
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """
        Get execution statistics for monitoring and reporting.
        
        Returns:
            Dictionary with execution statistics
        """
        return {
            "total_tasks_executed": self.total_tasks_executed,
            "total_tasks_successful": self.total_tasks_successful,
            "total_tasks_failed": self.total_tasks_executed - self.total_tasks_successful,
            "success_rate": (
                self.total_tasks_successful / self.total_tasks_executed * 100
                if self.total_tasks_executed > 0 else 0
            ),
            "max_workers": self.max_workers,
            "results_directory": self.results_dir
        }