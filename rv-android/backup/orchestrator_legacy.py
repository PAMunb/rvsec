"""
Experiment Orchestrator - High-Level Coordination for RV-Android Experiments

### Architectural Overview:
This module provides the primary orchestration interface for RV-Android experiments,
implementing a modern, configuration-driven approach that coordinates multiple testing
tools while maintaining clear separation of concerns and module independence.

### Key Architectural Decisions:
- **High-Level Coordination**: Provides a simplified interface for experiment execution
- **Configuration-Driven**: Uses ExperimentConfiguration for type-safe parameter management
- **Event Integration**: Leverages the event bus for monitoring and coordination
- **Module Independence**: Coordinates modules without violating their autonomy
- **Error Handling**: Comprehensive error handling with recovery strategies

### Role in the System:
- Primary interface for coordinating complex experiments
- Bridges CLI commands to low-level experiment execution
- Manages experiment lifecycle and resource coordination
- Provides unified error handling and logging across experiment phases
- Coordinates configuration distribution to dependent modules

### Design Patterns:
- **Facade Pattern**: Simplifies complex experiment orchestration
- **Coordinator Pattern**: Manages interaction between multiple components
- **Strategy Pattern**: Different execution strategies for different experiment types
- **Factory Pattern**: Creates appropriate experiment controllers and components
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from rv_android_core.event import EventBus, EventType, get_event_bus
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE, LOG_ERROR
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_tools.registry.registry import ToolRegistry

from rv_experiment.config import ExperimentConfiguration, ToolConfiguration
from rv_experiment.experiment.experiment_controller import ExperimentController


class ExperimentOrchestrator:
    """
    High-level orchestrator for RV-Android experiments.
    
    ### Architectural Decisions:
    - Provides a unified interface for different experiment types
    - Leverages existing ExperimentController for low-level execution
    - Implements configuration coordination across modules
    - Supports flexible experiment execution strategies
    
    ### Role in the System:
    - Primary interface for CLI and programmatic experiment execution
    - Coordinates configuration between modules while maintaining independence
    - Manages experiment lifecycle and resource allocation
    - Provides comprehensive error handling and recovery
    - Facilitates experiment monitoring and reporting
    
    ### Integration Points:
    - Integrates with ExperimentController for execution coordination
    - Uses ToolRegistry for dynamic tool discovery and loading
    - Coordinates with event bus for experiment monitoring
    - Interfaces with configuration management for parameter coordination
    """
    
    def __init__(self, config: ExperimentConfiguration, 
                 event_bus: Optional[EventBus] = None,
                 logger: Optional[Any] = None):
        """
        Initialize the experiment orchestrator.
        
        Args:
            config: Experiment configuration
            event_bus: Optional event bus for coordination
            logger: Optional logger for this orchestrator
        """
        self.config = config
        self.event_bus = event_bus or get_event_bus()
        
        # Initialize error handling and logging
        self.error_handler = ErrorHandler.get_instance()
        self.logging_manager = LoggingManager.get_instance()
        
        # Use provided logger or create new one
        if logger:
            self.logger = logger
        else:
            self.logger = self.logging_manager.get_logger(
                "rv_experiment.orchestrator",
                {CONTEXT_COMPONENT: "ExperimentOrchestrator"}
            )
        
        # Initialize tool registry
        self.tool_registry = ToolRegistry.get_instance()
        
        # Register configured tools before experiment execution
        self._register_configured_tools()
        
        # Create results directory
        self._setup_results_directory()
        
        # Setup experiment logging
        self._setup_experiment_logging()
        
        self.logger.info(f"ExperimentOrchestrator initialized for experiment: {self.config.name}")
    
    def _register_configured_tools(self):
        """
        Register experiment-specific tool configurations with the tool registry.
        
        ### Architectural Decisions:
        This method implements the configuration coordination pattern by registering
        tool variants that include experiment-specific configuration such as LLM
        settings, strategy preferences, and other coordinated parameters.
        
        ### Configuration Flow:
        1. Identify tools requiring experiment-specific configuration
        2. Extract tool configuration from experiment coordination methods
        3. Register configured variants with the tool registry
        4. Enable dynamic tool loading with proper configuration
        
        ### Role in the System:
        - Bridges experiment configuration with tool registry management
        - Enables dynamic tool configuration based on experiment objectives
        - Provides LLM integration for advanced testing tools like rvandroid
        - Ensures tool configuration consistency across experiment execution
        """
        try:
            # Register rvandroid with LLM configuration if it's in the tool list
            tool_names = [tc.name for tc in self.config.tool_configs] + self.config.tools
            
            if "rvandroid" in tool_names:
                self._register_rvandroid_with_llm_config()
            
            # Additional tool registration can be added here as needed
            # e.g., other tools that require experiment-specific configuration
            
        except Exception as e:
            self.error_handler.handle_error(e, {
                "component": "ExperimentOrchestrator",
                "operation": "register_configured_tools",
                "experiment_id": self.config.experiment_id,
                "tools": tool_names
            })
            # Non-fatal error - tools may still work with default configuration
            self.logger.warning(f"Could not register configured tools: {e}")
    
    def _register_rvandroid_with_llm_config(self):
        """
        Register rvandroid tool variants with experiment-specific LLM configuration.
        
        ### Architectural Decisions:
        This method creates configured rvandroid variants by combining the base
        rvandroid tool configuration with experiment-specific LLM settings,
        strategy preferences, and advanced testing parameters.
        
        ### Configuration Integration:
        - LLM Configuration: Provider, model, temperature, and connection settings
        - Strategy Configuration: Single action vs batch strategies, UI parsing preferences
        - Server Configuration: RVAndroid server connection and timeout settings
        - Memory Configuration: Long-term memory and history management settings
        
        ### Role in the System:
        - Enables advanced LLM-guided testing with experiment-specific parameters
        - Coordinates LLM provider selection with tool execution requirements
        - Provides consistent rvandroid configuration across experiment phases
        - Supports dynamic strategy selection based on experiment objectives
        """
        try:
            # Get comprehensive rvandroid configuration from experiment coordinator
            rvandroid_config = self.config.get_rvandroid_tool_config()
            
            # Register configured variant with experiment-specific settings
            self.tool_registry.register_variant(
                tool_name="rvandroid",
                variant_name="experiment_configured",
                parameters=rvandroid_config
            )
            
            # Also register specific strategy variants for easy selection
            llm_config = rvandroid_config.get("llm", {})
            strategy_config = rvandroid_config.get("strategy", {})
            
            # Register LLM-specific variants
            llm_provider = llm_config.get("provider", "ollama")
            llm_model = llm_config.get("model", "llama3")
            
            # Create variant name that reflects configuration
            configured_variant = f"{llm_provider}_{llm_model}_configured"
            self.tool_registry.register_variant(
                tool_name="rvandroid",
                variant_name=configured_variant,
                parameters=rvandroid_config
            )
            
            # Register batch strategy variant if enabled
            if strategy_config.get("use_batch_strategy", False):
                batch_variant = f"{llm_provider}_{llm_model}_batch_configured"
                self.tool_registry.register_variant(
                    tool_name="rvandroid",
                    variant_name=batch_variant,
                    parameters=rvandroid_config
                )
            
            self.logger.info(
                f"Registered rvandroid with LLM configuration: "
                f"provider={llm_provider}, model={llm_model}, "
                f"batch={strategy_config.get('use_batch_strategy', False)}"
            )
            
        except Exception as e:
            # Log error but don't fail experiment - rvandroid may work with defaults
            self.logger.error(f"Failed to register rvandroid with LLM configuration: {e}")
            raise
    
    def _setup_results_directory(self):
        """Set up the results directory for the experiment."""
        try:
            results_path = Path(self.config.output_dir)
            results_path.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Results directory created: {results_path}")
        except Exception as e:
            self.error_handler.handle_error(e, {
                "component": "ExperimentOrchestrator",
                "operation": "setup_results_directory",
                "output_dir": self.config.output_dir
            })
            raise
    
    def _setup_experiment_logging(self):
        """Set up file logging for the experiment."""
        try:
            log_dir = Path(self.config.output_dir) / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Configure file logging for this experiment
            self.logging_manager.setup_file_logging(
                log_dir=str(log_dir),
                experiment_id=self.config.experiment_id
            )
            
            self.logger.info(f"Experiment logging configured: {log_dir}")
        except Exception as e:
            self.error_handler.handle_error(e, {
                "component": "ExperimentOrchestrator",
                "operation": "setup_experiment_logging",
                "log_dir": log_dir
            })
            # Non-fatal error - continue without file logging
            self.logger.warning(f"Could not setup file logging: {e}")
    
    def _load_tools(self) -> List[AbstractTool]:
        """
        Load tools from configuration.
        
        Returns:
            List of loaded tools
            
        Raises:
            ValueError: If tools cannot be loaded
        """
        try:
            tools = []
            
            # Process tool configurations
            for tool_config in self.config.tool_configs:
                if not tool_config.enabled:
                    self.logger.info(f"Skipping disabled tool: {tool_config.name}")
                    continue
                
                # Load tool from registry with variant support
                if tool_config.variants:
                    # Try to get tool with variants first (if method exists)
                    if hasattr(self.tool_registry, 'get_tool_with_variants'):
                        tool = self.tool_registry.get_tool_with_variants(
                            tool_config.name, 
                            tool_config.variants
                        )
                    else:
                        # Fallback: get base tool and configure variants manually
                        tool = self.tool_registry.get_tool(tool_config.name)
                        if tool and hasattr(tool, 'configure_variants'):
                            tool.configure_variants(tool_config.variants)
                else:
                    # Get base tool
                    tool = self.tool_registry.get_tool(tool_config.name)
                
                if tool is None:
                    raise ValueError(f"Tool not found in registry: {tool_config.name}")
                
                # Configure tool parameters
                if tool_config.parameters:
                    for param, value in tool_config.parameters.items():
                        if hasattr(tool, param):
                            setattr(tool, param, value)
                
                # Set timeout override if specified
                if tool_config.timeout_override:
                    if hasattr(tool, 'timeout'):
                        tool.timeout = tool_config.timeout_override
                
                tools.append(tool)
                variant_info = f" with variants: {tool_config.variants}" if tool_config.variants else ""
                param_info = f" and parameters: {tool_config.parameters}" if tool_config.parameters else ""
                self.logger.info(f"Loaded tool: {tool_config.name}{variant_info}{param_info}")
            
            # Fallback to simple tool names if no tool configs
            if not tools and self.config.tools:
                for tool_name in self.config.tools:
                    tool = self.tool_registry.get_tool(tool_name)
                    if tool is None:
                        raise ValueError(f"Tool not found in registry: {tool_name}")
                    tools.append(tool)
                    self.logger.info(f"Loaded tool: {tool_name}")
            
            if not tools:
                raise ValueError("No tools loaded for experiment")
            
            return tools
            
        except Exception as e:
            self.error_handler.handle_error(e, {
                "component": "ExperimentOrchestrator",
                "operation": "load_tools",
                "tools": self.config.tools,
                "tool_configs": [tc.name for tc in self.config.tool_configs]
            })
            raise
    
    def _create_experiment_controller(self) -> ExperimentController:
        """
        Create and configure an ExperimentController instance.
        
        Returns:
            Configured ExperimentController
        """
        try:
            # Create controller with our configuration and event bus
            controller = ExperimentController(config=self.config, event_bus=self.event_bus)
            
            return controller
            
        except Exception as e:
            self.error_handler.handle_error(e, {
                "component": "ExperimentOrchestrator",
                "operation": "create_experiment_controller",
                "experiment_id": self.config.experiment_id
            })
            raise
    
    def execute_single_tool_experiment(self) -> bool:
        """
        Execute a single-tool experiment.
        
        Returns:
            True if experiment completed successfully, False otherwise
        """
        with self.logger.with_context(
            experiment_type="single_tool",
            experiment_id=self.config.experiment_id
        ):
            self.logger.info(LOG_START.format(
                operation=f"single-tool experiment ({self.config.name})"
            ))
            
            try:
                # Validate configuration
                self.config.validate()
                
                # Load tools
                tools = self._load_tools()
                
                if len(tools) > 1:
                    self.logger.warning(f"Multiple tools configured for single-tool experiment, using first: {tools[0].name}")
                    tools = [tools[0]]
                
                # Create and configure experiment controller
                controller = self._create_experiment_controller()
                
                # Execute experiment
                controller.execute(
                    repetitions=self.config.execution.repetitions,
                    timeouts=self.config.execution.timeouts,
                    tools=tools,
                    generate_monitors=self.config.processing.generate_monitors,
                    instrument=self.config.processing.instrument,
                    static_analysis=self.config.processing.static_analysis,
                    skip_experiment=self.config.processing.skip_experiment,
                    no_window=self.config.execution.no_window
                )
                
                self.logger.info(LOG_COMPLETE.format(
                    operation=f"single-tool experiment ({self.config.name})"
                ))
                return True
                
            except Exception as e:
                self.error_handler.handle_error(e, {
                    "component": "ExperimentOrchestrator",
                    "operation": "execute_single_tool_experiment",
                    "experiment_id": self.config.experiment_id,
                    "tools": [tc.name for tc in self.config.tool_configs]
                })
                
                self.logger.error(LOG_ERROR.format(
                    operation=f"single-tool experiment ({self.config.name})",
                    error=str(e)
                ))
                return False
    
    def execute_comparative_experiment(self) -> bool:
        """
        Execute a comparative experiment across multiple tools.
        
        Returns:
            True if experiment completed successfully, False otherwise
        """
        with self.logger.with_context(
            experiment_type="comparative",
            experiment_id=self.config.experiment_id
        ):
            self.logger.info(LOG_START.format(
                operation=f"comparative experiment ({self.config.name})"
            ))
            
            try:
                # Validate configuration
                self.config.validate()
                
                # Load tools
                tools = self._load_tools()
                
                if len(tools) < 2:
                    raise ValueError("Comparative experiment requires at least 2 tools")
                
                # Execute experiment for each tool separately to enable comparison
                results = {}
                
                for tool in tools:
                    self.logger.info(f"Running comparative experiment phase with tool: {tool.name}")
                    
                    # Create separate controller for each tool
                    controller = self._create_experiment_controller()
                    
                    # Create tool-specific results directory
                    tool_results_dir = Path(self.config.output_dir) / f"tool_{tool.name}"
                    tool_results_dir.mkdir(parents=True, exist_ok=True)
                    controller.results_dir = str(tool_results_dir)
                    
                    try:
                        # Execute experiment with single tool
                        controller.execute(
                            repetitions=self.config.execution.repetitions,
                            timeouts=self.config.execution.timeouts,
                            tools=[tool],
                            generate_monitors=self.config.processing.generate_monitors,
                            instrument=self.config.processing.instrument,
                            static_analysis=self.config.processing.static_analysis,
                            skip_experiment=self.config.processing.skip_experiment,
                            no_window=self.config.execution.no_window
                        )
                        
                        results[tool.name] = {"status": "success", "results_dir": str(tool_results_dir)}
                        self.logger.info(f"Completed comparative phase for tool: {tool.name}")
                        
                    except Exception as tool_error:
                        results[tool.name] = {"status": "failed", "error": str(tool_error)}
                        self.logger.error(f"Failed comparative phase for tool {tool.name}: {tool_error}")
                        
                        # Continue with other tools rather than failing entire experiment
                        continue
                
                # Generate comparative analysis if requested
                if self.config.processing.generate_reports:
                    self._generate_comparative_report(results)
                
                # Check if at least one tool succeeded
                successful_tools = [name for name, result in results.items() if result["status"] == "success"]
                
                if not successful_tools:
                    raise Exception("All tools failed in comparative experiment")
                
                self.logger.info(LOG_COMPLETE.format(
                    operation=f"comparative experiment ({self.config.name})"
                ))
                self.logger.info(f"Successful tools: {successful_tools}")
                return True
                
            except Exception as e:
                self.error_handler.handle_error(e, {
                    "component": "ExperimentOrchestrator",
                    "operation": "execute_comparative_experiment",
                    "experiment_id": self.config.experiment_id,
                    "tools": [tc.name for tc in self.config.tool_configs]
                })
                
                self.logger.error(LOG_ERROR.format(
                    operation=f"comparative experiment ({self.config.name})",
                    error=str(e)
                ))
                return False
    
    def execute_batch_experiment(self) -> bool:
        """
        Execute a batch experiment with comprehensive configuration.
        
        Returns:
            True if experiment completed successfully, False otherwise
        """
        with self.logger.with_context(
            experiment_type="batch",
            experiment_id=self.config.experiment_id
        ):
            self.logger.info(LOG_START.format(
                operation=f"batch experiment ({self.config.name})"
            ))
            
            try:
                # Validate configuration
                self.config.validate()
                
                # Load tools
                tools = self._load_tools()
                
                # Get applications to test
                applications = self.config.applications.get_applications()
                if not applications:
                    raise ValueError("No applications found for batch experiment")
                
                self.logger.info(f"Batch experiment with {len(tools)} tools and {len(applications)} applications")
                
                # Execute experiment
                controller = self._create_experiment_controller()
                
                # Execute with all configurations
                controller.execute(
                    repetitions=self.config.execution.repetitions,
                    timeouts=self.config.execution.timeouts,
                    tools=tools,
                    generate_monitors=self.config.processing.generate_monitors,
                    instrument=self.config.processing.instrument,
                    static_analysis=self.config.processing.static_analysis,
                    skip_experiment=self.config.processing.skip_experiment,
                    no_window=self.config.execution.no_window
                )
                
                self.logger.info(LOG_COMPLETE.format(
                    operation=f"batch experiment ({self.config.name})"
                ))
                return True
                
            except Exception as e:
                self.error_handler.handle_error(e, {
                    "component": "ExperimentOrchestrator",
                    "operation": "execute_batch_experiment",
                    "experiment_id": self.config.experiment_id,
                    "tools": [tc.name for tc in self.config.tool_configs]
                })
                
                self.logger.error(LOG_ERROR.format(
                    operation=f"batch experiment ({self.config.name})",
                    error=str(e)
                ))
                return False
    
    def _generate_comparative_report(self, results: Dict[str, Dict[str, Any]]):
        """
        Generate a comparative analysis report.
        
        Args:
            results: Results from comparative experiment
        """
        try:
            report_file = Path(self.config.output_dir) / "comparative_analysis.json"
            
            # Create summary report
            report = {
                "experiment_id": self.config.experiment_id,
                "experiment_name": self.config.name,
                "timestamp": datetime.now().isoformat(),
                "tools": list(results.keys()),
                "results": results,
                "summary": {
                    "total_tools": len(results),
                    "successful_tools": len([r for r in results.values() if r["status"] == "success"]),
                    "failed_tools": len([r for r in results.values() if r["status"] == "failed"])
                }
            }
            
            # Save report
            import json
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            self.logger.info(f"Comparative analysis report saved: {report_file}")
            
        except Exception as e:
            self.logger.warning(f"Could not generate comparative report: {e}")
    
    def get_experiment_status(self) -> Dict[str, Any]:
        """
        Get current experiment status.
        
        Returns:
            Dictionary with experiment status information
        """
        return {
            "experiment_id": self.config.experiment_id,
            "name": self.config.name,
            "output_dir": self.config.output_dir,
            "tools": [tc.name for tc in self.config.tool_configs],
            "created_at": self.config.created_at,
            "status": "configured"
        }