# rv_platform/platform.py
"""
Main Platform class for rv-platform.

This module provides the primary interface for executing Android experiments
through the rv-platform system.
"""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.event import EventBus
from rv_android_core.app import App
from rv_tools import ToolFactory
from rv_platform.config.platform_config import PlatformConfig
from rv_platform.execution.task_model import Task, TaskConfiguration, TaskFactory
from rv_platform.execution.executor import TaskExecutor
from rv_platform.components.tool_execution import ToolExecutionComponent
from rv_platform.components.emulator import EmulatorComponent
from rv_platform.components.logcat import LogcatComponent
from rv_platform.components.coverage import CoverageComponent
from rv_platform.components.static_analysis import StaticAnalysisComponent


class Platform:
    """
    Main entry point for rv-platform execution.
    
    ### Architectural Decisions:
    - Provides simple, clean interface for standalone usage
    - Manages task generation and execution coordination
    - Integrates with existing rv-android-core infrastructure
    - Supports event-driven communication with external systems
    
    ### Role in the System:
    - Discovers APKs and generates tasks based on configuration
    - Orchestrates task execution with proper resource management
    - Collects and aggregates basic task-level results
    - Provides progress reporting through events and logging
    """

    def __init__(self, config: PlatformConfig, event_bus: Optional[EventBus] = None):
        """
        Initialize the platform with configuration.
        
        Args:
            config: Platform configuration
            event_bus: Optional event bus for communication
        """
        self.config = config
        self.event_bus = event_bus or EventBus.get_instance()
        
        # Validate configuration
        self.config.validate_dependencies()
        
        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger('platform.main')
        
        # Error handler
        self.error_handler = ErrorHandler.get_instance()
        
        # Task management
        self.task_factory = TaskFactory(Task)
        self.tasks: List[Task] = []
        
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
            
            # Execute tasks
            results = self._execute_tasks()
            
            # Generate summary
            summary = self._generate_summary(results)
            
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
                tool_variants = tool_config.variants if tool_config.variants else [tool_config.name]
                
                for variant in tool_variants:
                    for repetition in range(1, self.config.repetitions + 1):
                        for timeout in self.config.timeouts:
                            # Create task configuration
                            task_config = TaskConfiguration(
                                apk_name=apk_name,
                                repetition=repetition,
                                timeout=timeout,
                                tool_name=variant,
                                no_window=self.config.no_window
                            )
                            
                            # Create task
                            task = self.task_factory.create_task(task_config)
                            task.set_app(app)
                            
                            # Initialize task
                            task.initialize(self.config.results_dir)
                            
                            self.tasks.append(task)
                            task_count += 1
        
        self.logger.info(f"Generated {task_count} tasks")

    def _discover_apks(self) -> List[Path]:
        """
        Discover APK files in the configured directory.
        
        Returns:
            List of APK file paths
        """
        apks_dir = Path(self.config.apks_dir)
        apk_files = list(apks_dir.glob("*.apk"))
        
        if not apk_files:
            raise ValueError(f"No APK files found in directory: {self.config.apks_dir}")
        
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
                tool = self._load_tool(task.config.tool_name)
                
                # Create task executor
                executor = TaskExecutor(task, tool, self.event_bus)
                
                # Register all essential components in execution order
                components = [
                    StaticAnalysisComponent(task, self.config.apks_dir, self.event_bus),
                    EmulatorComponent(task, self.event_bus),
                    LogcatComponent(task, self.event_bus),
                    CoverageComponent(task, self.event_bus),
                    ToolExecutionComponent(task, tool, self.event_bus)
                ]
                
                for component in components:
                    executor.register_component(component)
                
                # Execute task
                success = executor.execute()
                
                # Collect result
                result = {
                    "task_id": task.id,
                    "apk_name": task.config.apk_name,
                    "tool_name": task.config.tool_name,
                    "repetition": task.config.repetition,
                    "timeout": task.config.timeout,
                    "success": success,
                    "execution_time": task.result.execution_time_seconds,
                    "error_message": task.result.error_message
                }
                results.append(result)
                
                self.logger.info(f"Task completed: {success}")
                
            except Exception as e:
                self.logger.error(f"Task execution failed: {e}")
                task.update_state(task.result.state.__class__.ERROR, str(e))
                
                result = {
                    "task_id": task.id,
                    "apk_name": task.config.apk_name,
                    "tool_name": task.config.tool_name,
                    "repetition": task.config.repetition,
                    "timeout": task.config.timeout,
                    "success": False,
                    "execution_time": 0,
                    "error_message": str(e)
                }
                results.append(result)
        
        return results

    def _load_tool(self, tool_name: str):
        """
        Load a tool by name.
        
        Args:
            tool_name: Name of the tool to load
            
        Returns:
            Tool instance
        """
        try:
            # Find tool configuration for the requested tool
            tool_config = None
            for config in self.config.tools:
                if config.name == tool_name:
                    tool_config = config
                    break
            
            if not tool_config:
                raise ValueError(f"Tool configuration not found for '{tool_name}'")
            
            # Create tool parameters including device_id
            tool_params = tool_config.parameters.copy()
            # Note: device_id will be set during emulator session in TaskExecutor
            
            # Use ToolFactory to create configured tool with parameters
            return self.tool_factory.create_configured_tool(
                tool_name=tool_config.name,
                variants=tool_config.variants,
                params=tool_params
            )
        except Exception as e:
            raise ValueError(f"Failed to load tool '{tool_name}': {e}")

    def _generate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate execution summary.
        
        Args:
            results: List of task results
            
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
            "success_rate": successful_tasks / total_tasks if total_tasks > 0 else 0,
            "total_execution_time": total_time,
            "average_execution_time": total_time / total_tasks if total_tasks > 0 else 0,
            "results": results
        }
        
        self.logger.info(f"Execution summary: {successful_tasks}/{total_tasks} tasks successful")
        return summary

    def get_tasks_summary(self) -> List[Dict[str, Any]]:
        """
        Get summary of all tasks.
        
        Returns:
            List of task summaries
        """
        return [task.to_dict() for task in self.tasks]