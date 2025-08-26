"""
Test framework coordinator for RV-Android configuration evaluation.

This class orchestrates the complete testing lifecycle for evaluating different
configurations of AI-driven Android testing tools using existing rv-platform
infrastructure for task execution and management.

### Architectural Decisions:
- **Platform Integration**: Uses existing rv-platform TaskExecutor and Platform classes
- **Task Creation**: Leverages rv-android-core Task and ToolConfig models  
- **Configuration Management**: Uses predefined configurations without validation
- **Execution Strategy**: Delegates to ParallelManager for model-grouped task execution
- **Result Processing**: Integrates with existing PerformanceMonitor for automatic metrics collection

### Integration Points:
- **rv-platform**: Uses Platform.run() and TaskExecutor for task execution
- **rv-android-core**: Uses Task, ToolConfig, and PerformanceMonitor infrastructure
- **rv-llm**: Uses LLMConfig for configuration management
- **rvandroid-tool**: Creates RVAndroidTool instances through existing AbstractTool interface
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from rv_android_core.domain.app import App
from rv_android_core.domain.task import TaskConfiguration, TaskFactory, ToolConfig
from rv_android_core.event import EventBus, EventType
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE, LOG_ERROR
from rv_android_core.util.logging.manager import LoggingManager

from rv_test_framework.core.models import (
    TestFrameworkConfig,
    TaskResult,
    ModelGroup,
    ExecutionSummary,
    EmulatorPortAllocation
)


class TestFramework:
    """
    Coordinates evaluation of multiple tool configurations using existing platform infrastructure.
    
    ### Key Responsibilities:
    - Orchestrates complete testing lifecycle using rv-platform components
    - Converts predefined configurations to Task objects
    - Coordinates parallel execution through existing TaskExecutor pattern
    - Integrates results processing through PerformanceMonitor
    - Provides simple progress tracking without complex resource management
    
    ### Simplicity Principles:
    - User responsibility for configuration correctness and resource adequacy
    - Direct task execution without complex validation or adaptive management
    - Maximum reuse of existing infrastructure and patterns
    - Predictable behavior without "intelligent" automation
    """
    
    @ErrorHandler.handle_errors(
        component="TestFramework",
        phase="initialization"
    )
    def __init__(self, config: TestFrameworkConfig):
        """
        Initialize framework with existing platform components.
        
        ### Initialization Strategy:
        Sets up logging, loads predefined configurations, creates Task objects
        using existing rv-android-core infrastructure, and prepares for parallel execution.
        
        Args:
            config: Test framework configuration (user responsibility for correctness)
        """
        self.config = config
        self.start_time = datetime.now()
        
        # Setup results directory
        self.experiment_name = config.get_experiment_name()
        self.results_dir = os.path.join(config.output_dir, self.experiment_name)
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Initialize logging with existing infrastructure
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'rv_test_framework.core.framework',
            {CONTEXT_COMPONENT: 'TestFramework'}
        )
        
        # Error handler integration
        self.error_handler = ErrorHandler.get_instance()
        
        # Event bus for coordination
        self.event_bus = EventBus.get_instance()
        
        # Task management using existing infrastructure
        self.task_factory = TaskFactory()
        
        # Execution state
        self.tasks: List[Any] = []  # Task objects from rv-android-core
        self.model_groups: List[ModelGroup] = []
        self.results: List[TaskResult] = []
        self.emulator_ports = EmulatorPortAllocation()
        
        self.logger.info(f"TestFramework initialized: {self.experiment_name}")
        self.logger.info(f"Results directory: {self.results_dir}")
        self.logger.info(f"Max workers: {config.max_workers}")
    
    @ErrorHandler.handle_errors(
        component="TestFramework", 
        phase="configuration_loading"
    )
    def load_configurations(self, config_path: str) -> None:
        """
        Load predefined configurations from file.
        
        ### Configuration Strategy:
        Direct loading without validation - user responsibility for correctness.
        Uses existing LLMConfig and ToolConfig patterns for compatibility.
        
        Args:
            config_path: Path to configuration file (user ensures validity)
        """
        with self.logger.with_context(config_path=config_path):
            self.logger.info(LOG_START.format(phase="configuration loading"))
            
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
            with open(config_path, 'r') as f:
                configurations = json.load(f)
            
            # Store configurations directly - no validation
            self.config.configurations = configurations
            
            self.logger.info(f"Loaded {len(configurations)} configurations")
            self.logger.info(LOG_COMPLETE.format(phase="configuration loading"))
    
    @ErrorHandler.handle_errors(
        component="TestFramework",
        phase="task_generation"
    )
    def generate_tasks(self) -> None:
        """
        Generate Task objects from configurations using existing infrastructure.
        
        ### Task Creation Strategy:
        - Uses existing rv-android-core TaskFactory and TaskConfiguration
        - Leverages existing ToolConfig patterns for compatibility
        - Assigns emulator ports automatically for parallel execution
        - Groups tasks by LLM model for resource optimization
        """
        with self.logger.with_context(phase="task_generation"):
            self.logger.info(LOG_START.format(phase="task generation"))
            
            # Discover APKs using existing patterns
            apks = self._discover_apks()
            self.logger.info(f"Discovered {len(apks)} APK files")
            
            # Generate tasks for each configuration combination
            task_count = 0
            model_groups_dict: Dict[str, ModelGroup] = {}
            
            for config in self.config.configurations:
                config_name = config.get("name", f"config_{task_count}")
                llm_config = config.get("llm_config", {})
                tool_config = config.get("tool_config", {})
                
                # Extract model information for grouping
                model_name = llm_config.get("model", "unknown")
                model_type = llm_config.get("llm_type", "ollama")
                model_key = f"{model_type}:{model_name}"
                
                # Create or get model group
                if model_key not in model_groups_dict:
                    model_groups_dict[model_key] = ModelGroup(
                        model_name=model_name,
                        model_type=model_type
                    )
                
                # Generate tasks for each APK and repetition
                for apk in apks:
                    for repetition in range(1, self.config.repetitions + 1):
                        for timeout in self.config.timeouts:
                            # Create task configuration
                            task_config = self._create_task_configuration(
                                apk=apk,
                                config_name=config_name,
                                tool_config=tool_config,
                                repetition=repetition,
                                timeout=timeout,
                                worker_id=task_count % self.config.max_workers
                            )
                            
                            # Create Task using existing infrastructure
                            task = self.task_factory.create_task(task_config)
                            task.set_app(apk)
                            
                            # Initialize task with results directory
                            task.initialize(self.results_dir)
                            
                            # Add to collections
                            self.tasks.append(task)
                            model_groups_dict[model_key].add_task(task)
                            
                            task_count += 1
            
            # Store model groups
            self.model_groups = list(model_groups_dict.values())
            
            self.logger.info(f"Generated {task_count} tasks across {len(self.model_groups)} model groups")
            self.logger.info(LOG_COMPLETE.format(phase="task generation"))
    
    def _discover_apks(self) -> List[App]:
        """
        Discover APK files using existing App infrastructure.
        
        Returns:
            List of App objects for testing
        """
        apks = []
        apks_path = Path(self.config.apks_dir)
        
        if not apks_path.exists():
            raise FileNotFoundError(f"APKs directory not found: {self.config.apks_dir}")
        
        # Find APK files
        for apk_file in apks_path.glob("*.apk"):
            try:
                app = App(str(apk_file))
                apks.append(app)
                self.logger.debug(f"Found APK: {app.name}")
            except Exception as e:
                self.logger.warning(f"Failed to process APK {apk_file}: {e}")
        
        if not apks:
            raise ValueError(f"No valid APK files found in: {self.config.apks_dir}")
        
        return apks
    
    def _create_task_configuration(
        self, 
        apk: App, 
        config_name: str,
        tool_config: Dict[str, Any],
        repetition: int,
        timeout: int,
        worker_id: int
    ) -> TaskConfiguration:
        """
        Create TaskConfiguration using existing infrastructure.
        
        ### Configuration Strategy:
        - Uses existing TaskConfiguration and ToolConfig patterns
        - Assigns emulator ports for parallel execution
        - Includes framework-specific parameters in additional_params
        
        Args:
            apk: App object for testing
            config_name: Configuration identifier
            tool_config: Tool configuration from predefined configs
            repetition: Repetition number
            timeout: Execution timeout
            worker_id: Worker identifier for port assignment
            
        Returns:
            TaskConfiguration ready for Task creation
        """
        # Allocate emulator port for this worker
        device_name = self.emulator_ports.allocate_port(worker_id)
        
        # Create ToolConfig using existing patterns
        task_tool_config = ToolConfig(
            tool_name=tool_config.get("tool_name", "rvandroid"),
            variant=tool_config.get("variant", "default"),
            additional_params={
                **tool_config.get("additional_params", {}),
                "emulator_port": device_name,
                "config_name": config_name
            }
        )
        
        # Create TaskConfiguration
        return TaskConfiguration(
            apk_name=apk.name,
            repetition=repetition,
            timeout=timeout,
            tool_config=task_tool_config,
            no_window=self.config.no_window
        )
    
    @ErrorHandler.handle_errors(
        component="TestFramework",
        phase="execution"
    )
    def execute(self) -> ExecutionSummary:
        """
        Execute all tasks using parallel execution strategy.
        
        ### Execution Strategy:
        - Delegates to ParallelManager for model-grouped execution
        - Uses existing TaskExecutor infrastructure for individual tasks
        - Collects results through existing result processing
        - Maintains simplicity without complex resource management
        
        Returns:
            ExecutionSummary with results and statistics
        """
        with self.logger.with_context(phase="framework_execution"):
            self.logger.info(LOG_START.format(phase="test framework execution"))
            
            # Import ParallelManager for execution
            from rv_test_framework.execution.parallel_manager import ParallelManager
            
            # Create parallel manager
            parallel_manager = ParallelManager(
                max_workers=self.config.max_workers,
                results_dir=self.results_dir,
                event_bus=self.event_bus
            )
            
            # Execute model groups
            execution_results = parallel_manager.execute_model_groups(self.model_groups)
            
            # Process results
            summary = self._create_execution_summary(execution_results)
            
            # Save framework configuration and summary
            self._save_framework_state(summary)
            
            self.logger.info(LOG_COMPLETE.format(phase="test framework execution"))
            return summary
    
    def _create_execution_summary(self, execution_results: List[TaskResult]) -> ExecutionSummary:
        """
        Create execution summary from task results.
        
        Args:
            execution_results: List of task execution results
            
        Returns:
            ExecutionSummary with statistics and metadata
        """
        end_time = datetime.now()
        
        # Calculate basic statistics
        total_tasks = len(execution_results)
        successful_tasks = sum(1 for r in execution_results if r.success)
        failed_tasks = total_tasks - successful_tasks
        
        # Create summary
        summary = ExecutionSummary(
            start_time=self.start_time,
            end_time=end_time,
            total_tasks=total_tasks,
            successful_tasks=successful_tasks,
            failed_tasks=failed_tasks,
            total_model_groups=len(self.model_groups),
            max_workers_used=self.config.max_workers,
            results_directory=self.results_dir
        )
        
        # Calculate derived metrics
        summary.calculate_derived_metrics()
        
        # Store results for further processing
        self.results = execution_results
        
        return summary
    
    def _save_framework_state(self, summary: ExecutionSummary) -> None:
        """
        Save framework configuration and execution summary.
        
        Args:
            summary: Execution summary to save
        """
        # Save framework configuration
        config_file = os.path.join(self.results_dir, "framework_config.json")
        with open(config_file, 'w') as f:
            json.dump({
                "experiment_name": self.experiment_name,
                "max_workers": self.config.max_workers,
                "apks_dir": self.config.apks_dir,
                "repetitions": self.config.repetitions,
                "timeouts": self.config.timeouts,
                "no_window": self.config.no_window,
                "configurations": self.config.configurations,
                "emulator_port_mapping": self.emulator_ports.get_port_mapping()
            }, indent=2)
        
        # Save execution summary
        summary_file = os.path.join(self.results_dir, "execution_summary.json")
        with open(summary_file, 'w') as f:
            f.write(summary.model_dump_json(indent=2))
        
        self.logger.info(f"Framework state saved: {config_file}, {summary_file}")
    
    def get_results_summary(self) -> Dict[str, Any]:
        """
        Get basic results summary for reporting.
        
        Returns:
            Dictionary with key execution statistics
        """
        if not self.results:
            return {"status": "no_execution_data"}
        
        successful = sum(1 for r in self.results if r.success)
        failed = len(self.results) - successful
        
        return {
            "experiment_name": self.experiment_name,
            "total_tasks": len(self.results),
            "successful_tasks": successful,
            "failed_tasks": failed,
            "success_rate": (successful / len(self.results) * 100) if self.results else 0,
            "model_groups": len(self.model_groups),
            "results_directory": self.results_dir
        }