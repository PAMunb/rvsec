# rv_platform/platform.py
"""
Main Platform class for rv-platform.

This module provides the primary interface for executing Android experiments
through the rv-platform system.
"""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task, TaskConfiguration, TaskFactory
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_platform.components.coverage import CoverageComponent
from rv_platform.components.emulator import EmulatorComponent
from rv_platform.components.logcat import LogcatComponent
from rv_platform.components.result_processor import ResultProcessorComponent
from rv_platform.components.static_analysis import StaticAnalysisComponent
from rv_platform.components.tool_execution import ToolExecutionComponent
from rv_platform.config.platform_config import PlatformConfig
from rv_platform.execution.executor import TaskExecutor
from rv_platform.storage.task_storage import ExperimentMetadata, TaskStorage
from rv_tools import ToolFactory


class Platform:
    """
    Main entry point for rv-platform execution.
    
    ### Architectural Decisions:
    - Provides simple, clean interface for standalone usage
    - Manages task generation and execution coordination
    - Integrates with existing rv-android-core infrastructure
    ### Role in the System:
    - Discovers APKs and generates tasks based on configuration
    - Orchestrates task execution with proper resource management
    - Collects and aggregates basic task-level results
    - Provides progress reporting through logging
    """

    def __init__(self, config: PlatformConfig):
        """
        Initialize the platform with configuration.

        Args:
            config: Platform configuration
        """
        self.config = config

        # Validate configuration
        self.config.validate_dependencies()

        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'rv_platform.platform',
            {CONTEXT_COMPONENT: 'Platform'}
        )

        # Error handler
        self.error_handler = ErrorHandler.get_instance()

        # Task management with persistent storage
        self.task_factory = TaskFactory(Task)

        # Initialize TaskStorage for persistent task tracking
        tasks_file = os.path.join(config.results_dir, "tasks.json")
        self.task_storage = TaskStorage(tasks_file, self.task_factory)
        self.task_storage.load()

        # Tasks list for in-memory operations
        self.tasks: List[Task] = []
        self._skipped_count: int = 0

        # Tool factory
        self.tool_factory = ToolFactory()

        self.logger.info(f"Platform initialized with config: {self.config.apks_dir}")

    def run(self) -> Dict[str, Any]:
        """
        Execute the platform workflow.
        
        Returns:
            Summary of execution results
        """
        try:
            self.logger.info("Starting platform execution")

            # Generate tasks
            self._generate_tasks()

            # Store experiment metadata for continuation support
            config_dict = self.config.model_dump(mode="json")
            metadata = ExperimentMetadata.create_from_config(
                experiment_id=str(self.config.results_dir),
                config_dict=config_dict
            )
            self.task_storage.set_experiment_metadata(metadata)

            # Resume: skip tasks already completed in a previous run
            self._skip_completed_tasks()

            # Execute tasks
            results = self._execute_tasks()

            # Process experiment results (unless skipped)
            if not getattr(self.config, 'skip_result_processing', False):
                self._process_results()

            # Generate summary
            summary = self._generate_summary(results, self._skipped_count)

            self.logger.info("Platform execution completed successfully")
            return summary

        except Exception as e:
            self.error_handler.handle_error(e, {"phase": "platform_execution"})
            self.logger.error(f"Platform execution failed: {e}")
            raise

    def _generate_tasks(self) -> None:
        """Generate tasks based on configuration."""
        self.logger.info("Generating tasks")

        # Discover APKs
        apks = self._discover_apks()
        self.logger.info(f"Discovered {len(apks)} APK files")

        # Generate tasks for each combination
        task_count = 0
        for apk_path in apks:
            apk_name = apk_path.name

            # Create app instance
            app = App(str(apk_path))

            for tool_config in self.config.tools:
                # tool_config is rv_platform.ToolConfig with name="rvandroid", variants=["vision"]
                tool_name = tool_config.name  # Extract tool name (e.g., "rvandroid")
                tool_variants = tool_config.variants if tool_config.variants else ["default"]
                

                for variant_name in tool_variants:  # variant_name is "vision", not a tool specification
                    for repetition in range(1, self.config.repetitions + 1):
                        for timeout in self.config.timeouts:
                            # Create task configuration with ToolConfig
                            from rv_android_core.domain.task import ToolConfig as TaskToolConfig
                            
                            # Create TaskToolConfig correctly:
                            # - tool_name from tool_config.name (e.g., "rvandroid")
                            # - variant_name from variants list (e.g., "vision")
                            task_tool_config = TaskToolConfig(
                                tool_name=tool_name,
                                variant=variant_name,
                                additional_params=tool_config.parameters
                            )
                            
                            
                            # Set device_id from additional_params for parallel execution
                            device_id = tool_config.parameters.get(
                                'device_serial', 'emulator-5554'
                            )

                            task_config = TaskConfiguration(
                                apk_name=apk_name,
                                repetition=repetition,
                                timeout=timeout,
                                tool_config=task_tool_config,
                                no_window=self.config.no_window,
                                device_id=device_id
                            )

                            # Create task
                            task = self.task_factory.create_task(task_config)
                            task.set_app(app)

                            # Initialize task
                            task.initialize(self.config.results_dir)

                            self.tasks.append(task)
                            task_count += 1

        self.logger.info(f"Generated {task_count} tasks")

    def _skip_completed_tasks(self) -> None:
        """Skip tasks that were already completed in a previous run (resume support)."""
        completed_tasks = self.task_storage.get_completed_tasks()
        if not completed_tasks:
            return

        # Validate configuration consistency via checksum
        config_dict = self.config.model_dump(mode="json")
        if not self.task_storage.check_continuation_compatibility(config_dict):
            stored = self.task_storage.experiment_metadata.config_checksum[:8] if self.task_storage.experiment_metadata else "unknown"
            current = hashlib.sha256(json.dumps(config_dict, sort_keys=True).encode()).hexdigest()[:8]
            self.logger.warning(
                f"Config changed since last run (stored: {stored}, current: {current}) — resuming anyway"
            )

        def task_identity(task):
            tc = task.config
            return (tc.apk_name, tc.tool_config.tool_name, tc.tool_config.variant,
                    tc.repetition, tc.timeout)

        completed_ids = {task_identity(t) for t in completed_tasks}

        original_count = len(self.tasks)
        self.tasks = [t for t in self.tasks if task_identity(t) not in completed_ids]
        skipped = original_count - len(self.tasks)
        self._skipped_count = skipped

        if skipped > 0:
            self.logger.info(
                f"Resume: skipped {skipped} already-completed tasks "
                f"({len(self.tasks)} remaining)"
            )

    def _discover_apks(self) -> List[Path]:
        """
        Discover APK files in the configured directory.

        If apks_filter_file is set, only APKs whose filename appears in the
        filter file are included.

        Returns:
            List of APK file paths
        """
        apks_dir = Path(self.config.apks_dir)
        apk_files = list(apks_dir.glob("*.apk"))

        if not apk_files:
            raise ValueError(f"No APK files found in directory: {self.config.apks_dir}")

        if self.config.apks_filter_file:
            allowed = set(Path(self.config.apks_filter_file).read_text().strip().splitlines())
            apk_files = [f for f in apk_files if f.name in allowed]
            if not apk_files:
                raise ValueError(f"No APKs match filter: {self.config.apks_filter_file}")
            self.logger.info(f"Filtered to {len(apk_files)} APKs from filter file")

        return sorted(apk_files)

    def _execute_tasks(self) -> List[Dict[str, Any]]:
        """
        Execute all generated tasks.
        
        Returns:
            List of task execution results
        """
        self.logger.info(f"Executing {len(self.tasks)} tasks")
        results = []

        for i, task in enumerate(self.tasks, 1):
            self.logger.info(f"Executing task {i}/{len(self.tasks)}: {task}")

            try:
                # Load tool
                tool = self._load_tool(task.config.tool_config)

                # Create task executor with TaskStorage
                executor = TaskExecutor(task, tool, task_storage=self.task_storage)

                # Register all essential components in execution order
                components = [
                    StaticAnalysisComponent(task, self.config.apks_dir),
                    EmulatorComponent(task),
                    LogcatComponent(task),
                    CoverageComponent(task),
                    ToolExecutionComponent(task, tool)
                ]

                for component in components:
                    executor.register_component(component)

                # Execute task
                success = executor.execute()

                # Save task to persistent storage
                self.task_storage.update_task(task)

                # Collect result
                result = {
                    "task_id": task.id,
                    "apk_name": task.config.apk_name,
                    "tool_name": task.config.tool_config.get_full_tool_name(),
                    "repetition": task.config.repetition,
                    "timeout": task.config.timeout,
                    "success": success,
                    "execution_time": task.result.execution_time_seconds,
                    "error_message": task.result.error_message
                }
                results.append(result)

                self.logger.info(f"Task completed: {success}")

            except Exception as e:
                # Extract meaningful error message from exception chain
                error_message = self._extract_meaningful_error_message(e)

                self.logger.error(f"Task execution failed: {error_message}")
                task.update_state(task.result.state.__class__.ERROR, error_message)

                # Save failed task to persistent storage
                self.task_storage.update_task(task)

                result = {
                    "task_id": task.id,
                    "apk_name": task.config.apk_name,
                    "tool_name": task.config.tool_config.get_full_tool_name(),
                    "repetition": task.config.repetition,
                    "timeout": task.config.timeout,
                    "success": False,
                    "execution_time": task.result.execution_time_seconds if hasattr(task.result,
                                                                                    'execution_time_seconds') else 0,
                    "error_message": error_message
                }
                results.append(result)

        return results

    def _extract_meaningful_error_message(self, exception: Exception) -> str:
        """
        Extract a meaningful error message from an exception chain.
        
        Args:
            exception: The exception to extract message from
            
        Returns:
            A clear, user-friendly error message
        """
        from rv_android_core.util.error.exceptions import RVToolTimeoutError, RVToolExecutionError

        # Walk through the exception chain to find the root cause
        current = exception
        while current:
            # Check for timeout scenarios
            if isinstance(current, RVToolTimeoutError):
                tool_name = getattr(current, 'tool_name', 'unknown tool')
                timeout_seconds = getattr(current, 'timeout_seconds', None)
                if timeout_seconds:
                    return f"{tool_name} execution timed out after {timeout_seconds} seconds (expected behavior)"
                else:
                    return f"{tool_name} execution timed out (expected behavior)"

            # Check for tool execution errors
            if isinstance(current, RVToolExecutionError):
                tool_name = getattr(current, 'tool_name', 'unknown tool')
                return f"{tool_name}: {current.message}"

            # Check for other specific RV exceptions with meaningful messages
            if hasattr(current, 'message') and current.message:
                return current.message

            # Move to the cause of the current exception
            current = getattr(current, 'cause', None) or getattr(current, '__cause__', None)

        # Fallback to the original exception message
        return str(exception)

    def _load_tool(self, tool_config):
        """
        Load and configure a tool using ToolConfig specification.
        
        ### Breaking Change - Variant System Integration:
        This method now accepts ToolConfig instead of tool_name string to enable
        proper variant resolution and tool configuration with parameter overrides.
        
        ### Architecture Overview:
        - Accepts ToolConfig with tool_name, variant, and additional_params
        - Uses ToolFactory.create_tool() with resolved tool configuration
        - Eliminates platform-level tool configuration duplication
        - Enables clean configuration flow from experiment to tool execution
        
        Args:
            tool_config: ToolConfig instance with tool name, variant, and parameters
            
        Returns:
            Configured tool instance with variant-specific parameters
            
        Raises:
            ValueError: If tool loading or configuration fails
        """
        from rv_android_core.domain.task import ToolConfig
        
        try:
            # Ensure we have a ToolConfig instance
            if isinstance(tool_config, str):
                # Legacy string format - convert to ToolConfig for backward compatibility
                tool_config = ToolConfig.from_tool_specification(tool_config)
            elif not isinstance(tool_config, ToolConfig):
                raise ValueError(f"Expected ToolConfig instance, got {type(tool_config)}")
            
            # Use ToolFactory with new variant-based approach
            # The factory handles variant resolution, parameter merging, and tool configuration
            return self.tool_factory.create_tool(tool_config)
            
        except Exception as e:
            tool_name = getattr(tool_config, 'tool_name', str(tool_config))
            variant = getattr(tool_config, 'variant', 'unknown')
            raise ValueError(f"Failed to load tool '{tool_name}:{variant}': {e}")

    def _generate_summary(self, results: List[Dict[str, Any]],
                          skipped_count: int = 0) -> Dict[str, Any]:
        """
        Generate execution summary.

        Args:
            results: List of task results from this session
            skipped_count: Number of tasks skipped from previous runs (resume)

        Returns:
            Summary dictionary
        """
        total_tasks = len(results)
        successful_tasks = sum(1 for r in results if r["success"])
        failed_tasks = total_tasks - successful_tasks

        total_time = sum(r["execution_time"] for r in results)

        summary = {
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks,
            "skipped_tasks": skipped_count,
            "success_rate": successful_tasks / total_tasks if total_tasks > 0 else 0,
            "total_execution_time": total_time,
            "average_execution_time": total_time / total_tasks if total_tasks > 0 else 0,
            "results": results
        }

        self.logger.info(
            f"Execution summary: {successful_tasks}/{total_tasks} tasks successful"
            f" ({skipped_count} skipped from previous runs)"
        )
        return summary

    def get_tasks(self) -> List:
        """
        Get all task objects directly (no serialization).
        
        Returns:
            List of Task objects with static_data preserved
        """
        return self.tasks

    def get_tasks_summary(self) -> List[Dict[str, Any]]:
        """
        Get summary of all tasks (serialized format).
        
        Returns:
            List of task summaries
        """
        return [task.to_dict() for task in self.tasks]

    @ErrorHandler.handle_errors(component="Platform", phase="result_processing")
    def _process_results(self) -> None:
        """
        Generate CSV/JSON files from completed experiment tasks.
        
        This method processes completed tasks to generate standardized output
        files for analysis and research purposes.
        """
        self.logger.info("Processing experiment results")

        # Use TaskStorage as source of truth: includes completed tasks from all
        # sessions (previous runs loaded from tasks.json + current session).
        # Using self.tasks would only include tasks executed in this session,
        # missing tasks that were skipped during resume.
        all_completed = list(self.task_storage.get_completed_tasks())
        processor = ResultProcessorComponent(all_completed, self.config.results_dir)

        # Initialize and execute result processing
        processor.initialize({})
        processor.execute({})

        # Clean up
        processor.cleanup()

        self.logger.info("Experiment results processing completed")
