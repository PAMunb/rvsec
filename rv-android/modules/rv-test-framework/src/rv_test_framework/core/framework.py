"""
Test framework coordinator for RV-Android configuration evaluation.

This class orchestrates the complete testing lifecycle for evaluating different
configurations of AI-driven Android testing tools using existing rv-platform
infrastructure for task execution and management.

### Architectural Decisions:
- **Platform Integration**: Uses existing rv-platform TaskExecutor and Platform classes
- **Tool Registry**: Leverages rv-experiment's ExperimentToolRegistry for tool registration
- **Configuration Management**: Uses rv-platform ToolConfig directly
- **Execution Strategy**: Delegates to ParallelManager for model-grouped task execution
- **Result Processing**: Integrates with existing PerformanceMonitor for automatic metrics collection

### Integration Points:
- **rv-platform**: Uses Platform.run() and TaskExecutor for task execution
- **rv-android-core**: Uses Task, ToolConfig, and PerformanceMonitor infrastructure
- **rv-experiment**: Uses ExperimentToolRegistry for rvandroid tool registration
- **rvandroid-tool**: Creates RVAndroidTool instances through existing AbstractTool interface
"""

import os
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task, TaskConfiguration, TaskFactory
from rv_android_core.event import EventBus, EventType
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_platform.config.platform_config import ToolConfig as PlatformToolConfig
from rv_experiment.tools.experiment_tools import ExperimentToolRegistry

from rv_test_framework.core.models import (
    TestFrameworkConfig,
    TaskResult,
    ModelGroup,
    ExecutionSummary
    # EmulatorPortAllocation removed - using dynamic allocation
)


class TestFramework:
    """
    Coordinates evaluation of multiple tool configurations using existing platform infrastructure.
    
    ### Key Responsibilities:
    - Orchestrates complete testing lifecycle using rv-platform components
    - Registers external tools through rv-experiment registry
    - Converts ToolConfig configurations to Task objects
    - Groups tasks by LLM model for optimized parallel execution
    - Manages parallel task execution with proper resource allocation
    - Collects and aggregates results for analysis
    
    ### Execution Flow:
    1. Register external tools (rvandroid) via ExperimentToolRegistry
    2. Load configurations (ToolConfig instances)
    3. Generate tasks from APKs × configurations × repetitions × timeouts
    4. Group tasks by LLM model for GPU memory optimization
    5. Execute task groups in parallel with model transitions
    6. Collect results and generate metrics
    """

    @ErrorHandler.handle_errors(
        component="TestFramework",
        phase="initialization"
    )
    def __init__(self, config: TestFrameworkConfig):
        """
        Initialize test framework with configuration.
        
        Args:
            config: Test framework configuration with execution parameters
        """
        # Setup logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'rv_test_framework.core.framework',
            {CONTEXT_COMPONENT: 'TestFramework'}
        )
        
        self.logger.info("Initializing test framework")
        
        # Configuration
        self.config = config
        self.results_dir = Path(config.output_dir) / f"test_framework_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Register external tools (includes rvandroid)
        self._register_external_tools()
        
        # Task factory for creating task instances
        self.task_factory = TaskFactory(Task)
        
        # Task storage
        self.tasks = []
        self.results = []
        self.model_groups = []
        
        # Event bus for monitoring
        self.event_bus = EventBus.get_instance()
        
        self.logger.info(f"Test framework initialized with output: {self.results_dir}")
    
    def _register_external_tools(self) -> None:
        """Register external tools through rv-experiment registry."""
        try:
            registry = ExperimentToolRegistry.get_instance()
            registry.register_external_tools()
            self.logger.info("External tools registered (including rvandroid)")
        except Exception as e:
            self.logger.warning(f"Could not register external tools: {e}")
            # Non-fatal - tools may already be registered
    
    def load_configurations(self, config_source: Union[str, List[PlatformToolConfig]]) -> None:
        """
        Load test configurations from file or list.
        
        Args:
            config_source: Path to configuration file or list of PlatformToolConfig instances
        """
        if isinstance(config_source, str):
            # Load from file
            self.logger.info(f"Loading configurations from {config_source}")
            try:
                with open(config_source, 'r') as f:
                    configs_data = json.load(f)
                
                # Convert to ToolConfig instances
                configs = []
                for cfg in configs_data:
                    if isinstance(cfg, dict):
                        configs.append(PlatformToolConfig(**cfg))
                    else:
                        configs.append(cfg)
                
                self.config.configurations = configs
                self.logger.info(f"Loaded {len(configs)} configurations from file")
                
            except Exception as e:
                self.logger.error(f"Failed to load configurations: {e}")
                raise
        
        elif isinstance(config_source, list):
            # Direct list of ToolConfig
            self.config.configurations = config_source
            self.logger.info(f"Loaded {len(config_source)} configurations from list")
        
        else:
            raise ValueError(f"Invalid config source type: {type(config_source)}")
    
    def generate_tasks(self) -> None:
        """
        Generate tasks from configurations, APKs, repetitions and timeouts.
        Creates all combinations and groups by model for parallel execution.
        """
        self.logger.info("Generating tasks from configurations")
        
        # Discover APKs
        apks = self._discover_apks()
        if not apks:
            raise ValueError(f"No APKs found in {self.config.apks_dir}")
        
        # Generate task combinations
        task_id = 0
        for apk in apks:
            for config in self.config.configurations:
                for repetition in range(1, self.config.repetitions + 1):
                    for timeout in self.config.timeouts:
                        # Create task configuration from ToolConfig
                        task_config = self._create_task_config(
                            apk=apk,
                            tool_config=config,
                            repetition=repetition,
                            timeout=timeout
                        )
                        
                        # Create task using factory instance
                        task = self.task_factory.create_task(
                            config=task_config,
                            task_id=str(task_id)
                        )
                        
                        # Set task app (following rv-platform pattern)
                        task.set_app(apk)
                        
                        # Initialize task with results directory
                        task.initialize(str(self.results_dir))
                        
                        self.tasks.append(task)
                        task_id += 1
        
        self.logger.info(f"Generated {len(self.tasks)} tasks")
        
        # Group tasks by LLM model to optimize GPU memory usage during parallel execution
        # Each model group executes sequentially to prevent GPU memory conflicts
        # while tasks within each group execute in parallel
        self._group_by_model()
    
    def _discover_apks(self) -> List[App]:
        """
        Discover APK files in configured directory.
        
        Returns:
            List of App objects for discovered APKs
        """
        apks = []
        apk_dir = Path(self.config.apks_dir)
        
        for apk_file in apk_dir.glob("*.apk"):
            try:
                app = App(app_path=str(apk_file))
                apks.append(app)
                self.logger.debug(f"Discovered APK: {apk_file.name}")
            except Exception as e:
                self.logger.warning(f"Failed to load APK {apk_file}: {e}")
        
        return apks
    
    def _create_task_config(
        self,
        apk: App,
        tool_config: PlatformToolConfig,
        repetition: int,
        timeout: int
    ) -> TaskConfiguration:
        """
        Create TaskConfiguration from PlatformToolConfig.
        
        Args:
            apk: Application to test
            tool_config: Tool configuration with variants and parameters
            repetition: Repetition number
            timeout: Timeout in seconds
            
        Returns:
            TaskConfiguration for task creation
        """
        # Convert PlatformToolConfig to TaskConfiguration for rv-platform compatibility
        from rv_android_core.domain.task import ToolConfig as TaskToolConfig
        
        # Extract tool name and variant from PlatformToolConfig
        # Example: name="rvandroid", variants=["vision"] -> tool_name="rvandroid", variant="vision"
        tool_name = tool_config.name  # e.g., "rvandroid"
        variant_name = tool_config.variants[0] if tool_config.variants else "default"  # e.g., "vision"
        
        # Create TaskToolConfig with parameters passed through additional_params
        # This allows configuration parameters (like llm_model, prompt_strategy) to be passed to tools
        task_tool_config = TaskToolConfig(
            tool_name=tool_name,
            variant=variant_name,
            additional_params=tool_config.parameters
        )
        
        return TaskConfiguration(
            apk_name=apk.name,
            repetition=repetition,
            timeout=timeout,
            tool_config=task_tool_config
        )
    
    def _group_by_model(self) -> None:
        """
        Group tasks by LLM model for efficient execution.
        Automatically extracts model from ToolConfig parameters or variant.
        """
        self.logger.info("Grouping tasks by model")
        
        model_map = {}
        
        for task in self.tasks:
            # Extract model from task configuration
            model = self._extract_model_from_task(task)
            
            if model not in model_map:
                # Determine model type (assuming all models use ollama for now)
                model_type = "ollama"  # Could be extracted from model name if needed
                model_map[model] = ModelGroup(
                    model_name=model,
                    model_type=model_type,
                    tasks=[]
                )
            
            model_map[model].add_task(task)
        
        self.model_groups = list(model_map.values())
        
        for group in self.model_groups:
            self.logger.info(f"Model group {group.model_name}: {len(group.tasks)} tasks")
    
    def _extract_model_from_task(self, task: Any) -> str:
        """
        Extract LLM model from task configuration.
        
        Args:
            task: Task object with configuration
            
        Returns:
            Model identifier string
        """
        # Default model
        default_model = "gemma3:4b"
        
        if not hasattr(task, 'config') or not hasattr(task.config, 'tool_config'):
            return default_model
        
        tool_config = task.config.tool_config
        
        # Check additional parameters first
        if hasattr(tool_config, 'additional_params') and tool_config.additional_params:
            params = tool_config.additional_params
            if 'llm_model' in params:
                return params['llm_model']
            if 'model' in params:
                return params['model']
        
        # Check variant to determine default model
        if hasattr(tool_config, 'variant'):
            variant = tool_config.variant
            # Map variants to their default models
            variant_models = {
                'vision': 'gemma3:4b',
                'vision_ctx': 'gemma3:4b',
                'default': 'gemma3:4b',
                'claude': 'claude-sonnet'
            }
            if variant in variant_models:
                return variant_models[variant]
        
        return default_model
    
    @ErrorHandler.handle_errors(
        component="TestFramework",
        phase="execution"
    )
    def execute(self) -> ExecutionSummary:
        """
        Execute all tasks with model-grouped parallel execution.
        
        Returns:
            ExecutionSummary with results and statistics
        """
        from rv_test_framework.execution.parallel_manager import ParallelManager
        
        self.logger.info(f"🚀 EXECUTE: Starting execution of {len(self.tasks)} tasks")
        
        # Track execution time
        start_time = datetime.now()
        self.logger.info(f"📅 EXECUTE: Start time recorded: {start_time}")
        
        # Initialize parallel manager
        self.logger.info("⚙️  EXECUTE: Initializing ParallelManager...")
        parallel_manager = ParallelManager(
            max_workers=self.config.max_workers,
            results_dir=str(self.results_dir)
        )
        self.logger.info(f"✅ EXECUTE: ParallelManager initialized (max_workers={self.config.max_workers})")
        
        # Execute model groups with parallel execution within each group
        self.logger.info(f"🔄 EXECUTE: Executing {len(self.model_groups)} model groups...")
        self.results = parallel_manager.execute_model_groups(self.model_groups)
        self.logger.info(f"✅ EXECUTE: Model groups execution completed. Got {len(self.results)} results")
        
        # Calculate execution time
        self.logger.info("⏰ EXECUTE: Calculating execution time...")
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        self.logger.info(f"📊 EXECUTE: Execution time calculated: {execution_time:.1f} seconds")
        
        # Generate summary
        self.logger.info("📋 EXECUTE: Generating execution summary...")
        summary = self._generate_summary(start_time, end_time, execution_time)
        self.logger.info(f"✅ EXECUTE: Summary generated - {summary.successful_tasks}/{summary.total_tasks} successful")
        
        # Save results
        self.logger.info("💾 EXECUTE: Saving results to files...")
        self._save_results(summary)
        self.logger.info("✅ EXECUTE: Results saved successfully")
        
        self.logger.info(f"🎉 EXECUTE: Execution completed: {summary.successful_tasks}/{summary.total_tasks} successful")
        
        return summary
    
    def _generate_summary(self, start_time: datetime, end_time: datetime, execution_time: float) -> ExecutionSummary:
        """
        Generate execution summary from results.
        
        Args:
            start_time: Execution start time
            end_time: Execution end time
            execution_time: Total execution time in seconds
            
        Returns:
            ExecutionSummary with statistics
        """
        total_tasks = len(self.tasks)
        successful_tasks = sum(1 for r in self.results if r.success)
        failed_tasks = total_tasks - successful_tasks
        
        return ExecutionSummary(
            start_time=start_time,
            end_time=end_time,
            total_tasks=total_tasks,
            successful_tasks=successful_tasks,
            failed_tasks=failed_tasks,
            success_rate=(successful_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            total_execution_time=execution_time,
            results_directory=str(self.results_dir)
        )
    
    def _save_results(self, summary: ExecutionSummary) -> None:
        """
        Save results and summary to files using rv-platform ResultProcessorComponent.
        
        Args:
            summary: Execution summary to save
        """
        self.logger.info(f"💾 SAVE_RESULTS: Starting to save results to {self.results_dir}")
        
        # Save summary - Test Framework format (for compatibility)
        self.logger.info("📄 SAVE_RESULTS: Saving summary.json...")
        summary_file = self.results_dir / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary.dict(), f, indent=2, default=str)
        self.logger.info(f"✅ SAVE_RESULTS: summary.json saved ({summary_file.stat().st_size} bytes)")
        
        # Save detailed results - Test Framework format (for compatibility)
        self.logger.info("📄 SAVE_RESULTS: Saving results.json...")
        results_file = self.results_dir / "results.json"
        results_data = [asdict(r) for r in self.results]
        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)
        self.logger.info(f"✅ SAVE_RESULTS: results.json saved ({results_file.stat().st_size} bytes)")
        
        # Generate rv-platform standard result files (coverage.csv, errors.csv, etc.)
        # using ResultProcessorComponent to match sequential execution output
        self.logger.info(f"🔍 SAVE_RESULTS: Checking if tasks exist for ResultProcessorComponent ({len(self.tasks)} tasks)")
        if self.tasks:
            self.logger.info("🔧 SAVE_RESULTS: Generating rv-platform standard result files...")
            try:
                self.logger.info("📦 SAVE_RESULTS: Importing ResultProcessorComponent...")
                from rv_platform.components.result_processor import ResultProcessorComponent
                
                # Create result processor with completed tasks
                self.logger.info("⚙️  SAVE_RESULTS: Creating ResultProcessorComponent...")
                processor = ResultProcessorComponent(self.tasks, str(self.results_dir))
                self.logger.info("✅ SAVE_RESULTS: ResultProcessorComponent created")
                
                # Initialize and execute result processing (generates CSV files and structured JSON)
                self.logger.info("🔧 SAVE_RESULTS: Initializing ResultProcessorComponent...")
                processor.initialize({})
                self.logger.info("✅ SAVE_RESULTS: ResultProcessorComponent initialized")
                
                self.logger.info("⚙️  SAVE_RESULTS: Executing ResultProcessorComponent...")
                processor.execute({})
                self.logger.info("✅ SAVE_RESULTS: ResultProcessorComponent executed")
                
                self.logger.info("🧹 SAVE_RESULTS: Cleaning up ResultProcessorComponent...")
                processor.cleanup()
                self.logger.info("✅ SAVE_RESULTS: ResultProcessorComponent cleaned up")
                
                self.logger.info("🎉 SAVE_RESULTS: rv-platform standard result files generated successfully")
                
            except Exception as e:
                self.logger.error(f"❌ SAVE_RESULTS: Failed to generate rv-platform result files: {e}")
                import traceback
                self.logger.error(f"❌ SAVE_RESULTS: Traceback: {traceback.format_exc()}")
                # Don't fail the entire execution for result processing issues
        else:
            self.logger.warning("⚠️  SAVE_RESULTS: No tasks found, skipping ResultProcessorComponent")
        
        self.logger.info(f"🎉 SAVE_RESULTS: All results saved to {self.results_dir}")