"""SimplifiedOrchestrator - DI-Ready Experiment Orchestration

### Architectural Overview:
This module implements the experiment orchestrator with a clean DI-ready design
that coordinates all aspects of experiment execution while integrating with
the dependency injection system for maximum flexibility and testability.

### Key Architectural Decisions:
- **DI Integration**: Integrated with dependency injection container
- **Factory Pattern**: Uses factory pattern for component creation
- **Error Handling**: Comprehensive error handling with decorators
- **Directory Management**: Standardized ./out/ directory structure
- **Monitored Operations**: Support for JCA crypto and generic specifications

### Role in the System:
- Primary coordinator for experiment execution
- Integrates all experiment phases and components
- Provides progress tracking and error handling
- Supports different specification sets (JCA vs generic)
- Enables clean testing through dependency injection

### Design Patterns:
- **Orchestrator Pattern**: Coordinates complex multi-step workflows
- **Factory Pattern**: Component creation through factory injection
- **Observer Pattern**: Progress and event notification
- **Command Pattern**: Encapsulated experiment operations
"""

import os
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.exceptions import ConfigurationError

from .config import SimpleExperimentConfig
from .di.interfaces import (
    IExperimentOrchestrator,
    IDirectoryManager,
    IComponentLifecycle
)


class SimplifiedOrchestrator(IExperimentOrchestrator, IComponentLifecycle):
    """
    Experiment orchestrator with DI-ready architecture.
    
    ### Architectural Overview:
    This orchestrator implements a clean architecture with factory-based component
    creation and clear dependency injection. It coordinates all experiment phases
    while providing comprehensive error handling and progress tracking.
    
    ### Key Architectural Decisions:
    - **Factory Injection**: Receives factories through dependency injection
    - **Simple Configuration**: Uses SimpleExperimentConfig for type-safe configuration
    - **Directory Management**: Standardized directory structure with IDirectoryManager
    - **Lifecycle Compliance**: Implements IComponentLifecycle for DI integration
    - **Error Recovery**: Comprehensive error handling with rollback capabilities
    
    ### Benefits:
    - Clean separation of concerns through dependency injection
    - Simplified testing through constructor injection
    - Comprehensive error handling and recovery
    - Type-safe configuration management
    - Standardized directory structure
    
    ### Role in the System:
    - Central coordinator for all experiment operations
    - Integrates monitor generation, instrumentation, and testing
    - Manages experiment state and progress tracking
    - Coordinates monitored operations across specification sets
    - Provides unified interface for experiment execution
    """
    
    def __init__(self, 
                 config: SimpleExperimentConfig,
                 directory_manager: Optional[IDirectoryManager] = None,
                 llm_factory=None,
                 strategy_factory=None,
                 tool_factory=None,
                 logger=None):
        """
        Initialize orchestrator with dependency injection.
        
        ### Dependency Injection:
        This constructor accepts all dependencies through injection, enabling
        clean testing and flexible component assembly. All dependencies are
        optional to support different deployment scenarios.
        
        Args:
            config: Experiment configuration
            directory_manager: Directory management implementation
            llm_factory: LLM factory for RVAndroid tool integration
            strategy_factory: Strategy factory for prompt generation
            tool_factory: Tool factory for testing tool creation
            logger: Logger instance for dependency injection
        """
        # Store configuration
        self.config = config
        
        # Logging setup
        if logger:
            self.logger = logger
        else:
            logging_manager = LoggingManager.get_instance()
            self.logger = logging_manager.get_logger(
                "rv_experiment.simplified_orchestrator",
                {CONTEXT_COMPONENT: "SimplifiedOrchestrator"}
            )
        
        # Set up error handling
        self.error_handler = ErrorHandler.get_instance()
        
        # Store factory dependencies
        self.directory_manager = directory_manager
        self.llm_factory = llm_factory
        self.strategy_factory = strategy_factory
        self.tool_factory = tool_factory
        
        # Orchestrator state
        self.experiment_id = config.experiment_id
        self.experiment_dir = Path(config.experiment_dir)
        self.current_phase = "initialized"
        self.progress = {
            "phase": "initialized",
            "percentage": 0,
            "current_operation": "Ready to start",
            "started_at": None,
            "completed_phases": []
        }
        self.results = {
            "experiment_id": self.experiment_id,
            "config": config.to_dict(),
            "phases": {},
            "summary": {}
        }
        
        # Component lifecycle state
        self.lifecycle_state = "created"
        
        self.logger.info(f"SimplifiedOrchestrator initialized for experiment: {self.experiment_id}")
    
    @ErrorHandler.handle_errors(
        component="SimplifiedOrchestrator",
        phase="setup_factories"
    )
    def _setup_factories(self) -> None:
        """
        Set up factories with intelligent defaults.
        
        ### Factory Setup Strategy:
        This method initializes factories with sensible defaults when they
        are not provided through dependency injection. It provides fallback
        creation for components while maintaining clean DI patterns.
        
        ### Setup Benefits:
        - Zero-configuration startup with sensible defaults
        - Full customization support through dependency injection
        - Clean separation between factory creation and usage
        """
        # Set up directory manager if not provided
        if not self.directory_manager:
            from .directory_manager import ExperimentDirectoryManager
            self.directory_manager = ExperimentDirectoryManager(
                base_dir=self.config.experiment_dir,
                logger=self.logger
            )
        
        # Set up LLM factory if not provided (for RVAndroid integration)
        if not self.llm_factory:
            try:
                from rv_llm.factories.llm_factory import LLMFactory
                self.llm_factory = LLMFactory()
                self.logger.debug("Created default LLMFactory")
            except ImportError:
                self.logger.warning("rv-llm module not available, RVAndroid tools will be disabled")
        
        # Set up strategy factory if not provided
        if not self.strategy_factory:
            try:
                from rv_llm.factories.strategy_factory import StrategyFactory
                self.strategy_factory = StrategyFactory()
                self.logger.debug("Created default StrategyFactory")
            except ImportError:
                self.logger.warning("Strategy factory not available")
        
        # Set up tool factory if not provided
        if not self.tool_factory:
            try:
                from rv_tools.registry.factory import ToolFactory
                self.tool_factory = ToolFactory()
                self.logger.debug("Created default ToolFactory")
            except ImportError:
                self.logger.warning("Tool factory not available")
        
        self.logger.info("Factory setup completed")
    
    # IComponentLifecycle implementation
    @ErrorHandler.handle_errors(
        component="SimplifiedOrchestrator",
        phase="initialize"
    )
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize orchestrator component.
        
        Args:
            config: Component configuration dictionary
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Validate configuration
            self.config.validate()
            
            # Set up factories
            self._setup_factories()
            
            # Ensure directory structure
            if self.directory_manager:
                self.directory_manager.create_full_structure()
            
            self.lifecycle_state = "initialized"
            self.logger.info("SimplifiedOrchestrator initialized successfully")
            return True
            
        except Exception as e:
            self.lifecycle_state = "error"
            self.logger.error(f"Failed to initialize orchestrator: {e}")
            return False
    
    def start(self) -> bool:
        """
        Start orchestrator component.
        
        Returns:
            True if start successful, False otherwise
        """
        if self.lifecycle_state != "initialized":
            self.logger.error(f"Cannot start from state: {self.lifecycle_state}")
            return False
        
        self.lifecycle_state = "started"
        self.logger.info("SimplifiedOrchestrator started")
        return True
    
    def stop(self) -> bool:
        """
        Stop orchestrator component.
        
        Returns:
            True if stop successful, False otherwise
        """
        self.lifecycle_state = "stopped"
        self.logger.info("SimplifiedOrchestrator stopped")
        return True
    
    def destroy(self) -> bool:
        """
        Destroy orchestrator component.
        
        Returns:
            True if destroy successful, False otherwise
        """
        self.lifecycle_state = "destroyed"
        self.logger.info("SimplifiedOrchestrator destroyed")
        return True
    
    def get_state(self) -> str:
        """
        Get current lifecycle state.
        
        Returns:
            Current lifecycle state
        """
        return self.lifecycle_state
    
    def is_healthy(self) -> bool:
        """
        Check if orchestrator is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        return self.lifecycle_state in ["initialized", "started"]
    
    # IExperimentOrchestrator implementation
    @ErrorHandler.handle_errors(
        component="SimplifiedOrchestrator",
        phase="execute"
    )
    def execute(self) -> bool:
        """
        Execute complete experiment workflow.
        
        ### Execution Strategy:
        This method coordinates the complete experiment execution including:
        1. Monitor generation for the specified monitored operations set
        2. APK instrumentation with the generated monitors
        3. Static analysis execution for baseline data
        4. Tool execution with progress tracking
        5. Result collection and summary generation
        
        ### Monitored Operations Integration:
        The orchestrator supports both JCA crypto and generic specification
        sets, ensuring proper monitor generation and instrumentation based
        on the configured specification_set.
        
        Returns:
            True if experiment completed successfully, False otherwise
        """
        try:
            self.progress["started_at"] = datetime.now().isoformat()
            self._update_progress("starting", 0, "Starting experiment execution")
            
            # Phase 1: Monitor Generation
            if self.config.generate_monitors:
                if not self._execute_monitor_generation():
                    return False
                self._update_progress("monitor_generation_complete", 20, "Monitor generation completed")
            
            # Phase 2: APK Instrumentation
            if self.config.instrument_apks:
                if not self._execute_instrumentation():
                    return False
                self._update_progress("instrumentation_complete", 40, "APK instrumentation completed")
            
            # Phase 3: Static Analysis
            if self.config.run_static_analysis:
                if not self._execute_static_analysis():
                    return False
                self._update_progress("static_analysis_complete", 60, "Static analysis completed")
            
            # Phase 4: Tool Execution
            if not self._execute_tools():
                return False
            self._update_progress("tool_execution_complete", 90, "Tool execution completed")
            
            # Phase 5: Results Collection
            if not self._collect_results():
                return False
            self._update_progress("completed", 100, "Experiment completed successfully")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Experiment execution failed: {e}")
            self._update_progress("failed", self.progress["percentage"], f"Experiment failed: {str(e)}")
            return False
    
    def _execute_monitor_generation(self) -> bool:
        """
        Execute monitor generation phase.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Generating monitors for specification set: {self.config.specification_set}")
            
            # Import monitor generator
            from rv_monitor_generator.runtime_verification_generator import RuntimeVerificationGenerator
            
            # Set up monitor generation configuration
            monitor_config = {
                "specification_set": self.config.specification_set,
                "output_dir": str(self.directory_manager.get_monitors_dir(self.config.specification_set)),
                "rvsec_root": os.getenv("RVSEC_HOME"),
                "timeout": 300
            }
            
            # Generate monitors
            generator = RuntimeVerificationGenerator()
            success = generator.generate_monitors(monitor_config)
            
            if success:
                self.results["phases"]["monitor_generation"] = {
                    "status": "completed",
                    "specification_set": self.config.specification_set,
                    "output_dir": monitor_config["output_dir"]
                }
                return True
            else:
                self.logger.error("Monitor generation failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Monitor generation phase failed: {e}")
            return False
    
    def _execute_instrumentation(self) -> bool:
        """
        Execute APK instrumentation phase.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Starting APK instrumentation")
            
            # Get APK list
            apks = self.config.get_apk_list()
            if not apks:
                self.logger.error("No APKs found for instrumentation")
                return False
            
            # Import instrumentation module
            from rv_instrumentation.rvandroid import RVAndroidInstrumenter
            
            # Set up instrumentation configuration
            instrumentation_config = {
                "input_apks": apks,
                "output_dir": str(self.directory_manager.get_instrumented_dir(self.config.specification_set)),
                "monitors_dir": str(self.directory_manager.get_monitors_dir(self.config.specification_set)),
                "specification_set": self.config.specification_set
            }
            
            # Instrument APKs
            instrumenter = RVAndroidInstrumenter()
            instrumented_apks = instrumenter.instrument_apks(instrumentation_config)
            
            if instrumented_apks:
                self.results["phases"]["instrumentation"] = {
                    "status": "completed",
                    "input_apks": apks,
                    "instrumented_apks": instrumented_apks,
                    "output_dir": instrumentation_config["output_dir"]
                }
                return True
            else:
                self.logger.error("APK instrumentation failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Instrumentation phase failed: {e}")
            return False
    
    def _execute_static_analysis(self) -> bool:
        """
        Execute static analysis phase.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Starting static analysis")
            
            # Import static analysis module
            from rv_static_analysis.analysis.static.static_analysis import StaticAnalysis
            
            # Get APK list
            apks = self.config.get_apk_list()
            
            # Set up static analysis configuration
            static_config = {
                "input_apks": apks,
                "output_dir": str(self.directory_manager.get_static_dir()),
                "tools": ["gator", "gesda", "reach"],
                "timeout": 600
            }
            
            # Run static analysis
            analyzer = StaticAnalysis()
            analysis_results = analyzer.analyze_apks(static_config)
            
            if analysis_results:
                self.results["phases"]["static_analysis"] = {
                    "status": "completed",
                    "results": analysis_results,
                    "output_dir": static_config["output_dir"]
                }
                return True
            else:
                self.logger.warning("Static analysis completed with no results")
                return True  # Not critical for experiment success
                
        except Exception as e:
            self.logger.error(f"Static analysis phase failed: {e}")
            return True  # Not critical for experiment success
    
    def _execute_tools(self) -> bool:
        """
        Execute testing tools phase.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Starting tool execution")
            
            tool_results = []
            
            for tool_spec in self.config.tools:
                if not self._execute_single_tool(tool_spec):
                    self.logger.error(f"Tool execution failed: {tool_spec['name']}")
                    return False
                
                tool_results.append({
                    "tool": tool_spec["name"],
                    "variants": tool_spec.get("variants", []),
                    "parameters": tool_spec.get("parameters", {}),
                    "status": "completed"
                })
            
            self.results["phases"]["tool_execution"] = {
                "status": "completed",
                "tools": tool_results
            }
            
            return True
            
        except Exception as e:
            self.logger.error(f"Tool execution phase failed: {e}")
            return False
    
    def _execute_single_tool(self, tool_spec: Dict[str, Any]) -> bool:
        """
        Execute a single testing tool.
        
        Args:
            tool_spec: Tool specification dictionary
            
        Returns:
            True if successful, False otherwise
        """
        tool_name = tool_spec["name"]
        self.logger.info(f"Executing tool: {tool_name}")
        
        try:
            # Create tool using factory
            if tool_name == "rvandroid" and self.llm_factory and self.strategy_factory:
                # Special handling for RVAndroid tool with LLM integration
                return self._execute_rvandroid_tool(tool_spec)
            else:
                # Standard tool execution
                if self.tool_factory:
                    tool = self.tool_factory.create_configured_tool(
                        tool_name,
                        experiment_dir=str(self.experiment_dir),
                        **tool_spec.get("parameters", {})
                    )
                    
                    # Execute tool with timeout
                    return tool.execute(
                        timeout=self.config.timeout,
                        repetitions=self.config.repetitions
                    )
                else:
                    self.logger.error("Tool factory not available")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Failed to execute tool {tool_name}: {e}")
            return False
    
    def _execute_rvandroid_tool(self, tool_spec: Dict[str, Any]) -> bool:
        """
        Execute RVAndroid tool with LLM integration.
        
        Args:
            tool_spec: RVAndroid tool specification
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create LLM instance
            llm_params = tool_spec.get("parameters", {})
            llm = self.llm_factory.create_ollama(
                model=llm_params.get("model", "llama3"),
                temperature=llm_params.get("temperature", 0.3)
            )
            
            # Create strategy instance
            strategy_type = "batch" if "batch" in tool_spec.get("variants", []) else "standard"
            if strategy_type == "batch":
                strategy = self.strategy_factory.create_batch_action(
                    batch_size=llm_params.get("batch_size", 3)
                )
            else:
                strategy = self.strategy_factory.create_standard()
            
            # Create and execute RVAndroid tool
            from rvandroid_tool.server import RVAndroidTool
            rvandroid_tool = RVAndroidTool(
                llm=llm,
                strategy=strategy,
                experiment_dir=str(self.experiment_dir)
            )
            
            return rvandroid_tool.execute(
                timeout=self.config.timeout,
                repetitions=self.config.repetitions
            )
            
        except Exception as e:
            self.logger.error(f"RVAndroid tool execution failed: {e}")
            return False
    
    def _collect_results(self) -> bool:
        """
        Collect and summarize experiment results.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Collecting experiment results")
            
            # Create results summary
            self.results["summary"] = {
                "experiment_id": self.experiment_id,
                "specification_set": self.config.specification_set,
                "completed_at": datetime.now().isoformat(),
                "execution_time": self._calculate_execution_time(),
                "phases_completed": list(self.results["phases"].keys()),
                "tools_executed": [tool["name"] for tool in self.config.tools],
                "apks_processed": len(self.config.get_apk_list()),
                "status": "completed"
            }
            
            # Save results to file
            results_file = self.experiment_dir / "results" / f"{self.experiment_id}_results.json"
            results_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(results_file, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            
            self.logger.info(f"Results saved to: {results_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to collect results: {e}")
            return False
    
    def _calculate_execution_time(self) -> Optional[float]:
        """
        Calculate experiment execution time.
        
        Returns:
            Execution time in seconds or None if not available
        """
        if "started_at" in self.progress:
            started = datetime.fromisoformat(self.progress["started_at"])
            now = datetime.now()
            return (now - started).total_seconds()
        return None
    
    def _update_progress(self, phase: str, percentage: int, operation: str) -> None:
        """
        Update experiment progress.
        
        Args:
            phase: Current phase name
            percentage: Completion percentage
            operation: Current operation description
        """
        self.current_phase = phase
        self.progress.update({
            "phase": phase,
            "percentage": percentage,
            "current_operation": operation
        })
        
        if phase not in self.progress["completed_phases"] and percentage > 0:
            self.progress["completed_phases"].append(phase)
        
        self.logger.info(f"Progress: {percentage}% - {operation}")
    
    def get_progress(self) -> Dict[str, Any]:
        """
        Get current experiment progress.
        
        Returns:
            Progress information dictionary
        """
        return self.progress.copy()
    
    def stop_experiment(self) -> bool:
        """
        Stop experiment execution gracefully.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            self.logger.info("Stopping experiment gracefully")
            self._update_progress("stopping", self.progress["percentage"], "Experiment stopped by user")
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop experiment: {e}")
            return False
    
    def get_results_summary(self) -> Dict[str, Any]:
        """
        Get experiment results summary.
        
        Returns:
            Results summary dictionary
        """
        return self.results.get("summary", {})
    
    def validate_configuration(self) -> bool:
        """
        Validate experiment configuration before execution.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            self.config.validate()
            self.logger.info("Configuration validation passed")
            return True
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False