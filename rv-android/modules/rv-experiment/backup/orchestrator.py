"""
Experiment Orchestrator for Android Testing Coordination

### Architectural Overview:
This module implements clean orchestration architecture for Android testing experiments,
providing factory-based component creation with just-in-time configuration and direct 
parameter passing for modular experiment execution.

### Key Architectural Decisions:
- **Clean Design**: Direct class naming and focused responsibility (ExperimentOrchestrator)
- **Factory Pattern**: Factory-based component creation for clean module integration
- **Just-in-Time Configuration**: Sub-modules configured only when accessed
- **Simple Parameter Passing**: Direct parameter passing for module coordination
- **DI-Ready Design**: Structure optimized for dependency injection containers
- **Monitored Operations**: Support for JCA crypto and generic programming pattern monitoring

### Role in the System:
- Primary orchestration interface for experiment execution
- Factory coordinator for component creation and configuration
- Just-in-time configuration provider for sub-modules
- Event bus coordinator for experiment monitoring and progress tracking
- Error handling coordinator using rv-android-core patterns

### Design Patterns:
- **Facade Pattern**: Simplified interface for complex experiment orchestration
- **Factory Pattern**: Component creation through factory methods
- **Just-in-Time Pattern**: Configuration created only when needed
- **Strategy Pattern**: Different execution strategies for different experiment types
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

from rv_experiment.config import CLIExperimentConfig, ExperimentConfig, ToolConfiguration


class ExperimentOrchestrator:
    """
    Clean experiment orchestrator implementing factory patterns and just-in-time configuration.
    
    ### Architectural Overview:
    This class implements clean architecture principles, providing a simplified
    orchestration interface that coordinates experiment execution through
    factory-based component creation and just-in-time configuration.
    
    ### Key Features:
    - **Clean Design**: Direct class naming and focused responsibility
    - **Factory Pattern**: Component creation through factory methods for clean module integration
    - **Just-in-Time Configuration**: Sub-modules configured only when accessed
    - **Simple Parameter Passing**: Direct parameter passing for module coordination
    - **DI-Ready Design**: Structure optimized for dependency injection containers
    - **Monitored Operations**: Support for JCA crypto and generic programming pattern monitoring
    
    ### Role in the System:
    - Primary interface for all experiment execution scenarios
    - Factory coordinator for component creation with just-in-time configuration
    - Event bus coordinator for experiment monitoring and progress tracking
    - Error handling coordinator using rv-android-core ErrorHandler patterns
    - Results coordinator for experiment output management
    
    ### Design Philosophy:
    This orchestrator follows the "do one thing well" principle, focusing solely on
    experiment execution coordination with clean separation of concerns and
    modular component integration.
    """
    
    def __init__(self, config: CLIExperimentConfig, 
                 event_bus: Optional[EventBus] = None,
                 logger: Optional[Any] = None):
        """
        Initialize the clean experiment orchestrator.
        
        ### Architectural Decisions:
        - Uses CLIExperimentConfig for simplified configuration interface
        - Accepts optional event bus and logger for flexible integration
        - Initializes only essential components using rv-android-core patterns
        - Prepares factory-based component creation infrastructure
        
        Args:
            config: CLI experiment configuration with all necessary parameters
            event_bus: Optional event bus for coordination (gets default if not provided)
            logger: Optional logger for this orchestrator (creates new if not provided)
        """
        self.config = config
        self.event_bus = event_bus or get_event_bus()
        
        # Initialize error handling and logging using rv-android-core patterns
        self.error_handler = ErrorHandler.get_instance()
        self.logging_manager = LoggingManager.get_instance()
        
        # Use provided logger or create new one with proper context
        if logger:
            self.logger = logger
        else:
            self.logger = self.logging_manager.get_logger(
                "rv_experiment.orchestrator",
                {CONTEXT_COMPONENT: "ExperimentOrchestrator"}
            )
        
        # Initialize tool registry for factory-based tool creation
        self.tool_registry = ToolRegistry.get_instance()
        
        # Setup experiment environment with factory pattern
        self._setup_experiment_environment()
        
        self.logger.info(f"ExperimentOrchestrator initialized for experiment: {self.config.experiment_id}")
    
    @ErrorHandler.handle_errors(
        component="ExperimentOrchestrator",
        phase="setup_experiment_environment",
    )
    def _setup_experiment_environment(self):
        """
        Setup experiment environment using factory patterns and just-in-time configuration.
        
        ### Architectural Decisions:
        This method implements the factory pattern setup by preparing the experiment
        environment without complex upfront coordination. It creates directory structures
        and initializes logging using just-in-time configuration principles.
        
        ### Factory Pattern Implementation:
        - Creates experiment directory structure using standard ./out/ layout
        - Initializes experiment-specific logging configuration
        - Prepares component factory infrastructure for tool creation
        - Sets up event bus integration for experiment monitoring
        
        ### Role in the System:
        - Prepares experiment environment for factory-based component creation
        - Establishes standard directory structure for experiment outputs
        - Configures experiment-specific logging and monitoring
        - Ensures experiment environment is ready for clean execution
        """
        try:
            # Create experiment directory structure using standard ./out/ layout
            exp_base_dir = Path(self.config.experiment_dir)
            exp_dir = exp_base_dir / "experiments" / self.config.experiment_id
            exp_dir.mkdir(parents=True, exist_ok=True)
            
            # Create standard subdirectories for experiment outputs
            subdirs = ["instrumented", "monitors", "static_analysis", "results", "logs"]
            for subdir in subdirs:
                (exp_dir / subdir).mkdir(exist_ok=True)
            
            # Store full experiment path for component creation
            self.experiment_path = str(exp_dir)
            
            # Setup experiment-specific logging using just-in-time configuration
            log_dir = exp_dir / "logs"
            self.logging_manager.setup_file_logging(
                log_dir=str(log_dir),
                experiment_id=self.config.experiment_id
            )
            
            self.logger.info(f"Experiment environment created: {self.experiment_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to setup experiment environment: {e}")
            raise
    
    @ErrorHandler.handle_errors(
        component="ExperimentOrchestrator",
        phase="load_tools",
    )
    def _load_tools(self) -> List[AbstractTool]:
        """
        Load tools using factory pattern with just-in-time configuration.
        
        ### Factory Pattern Implementation:
        This method implements the factory pattern for tool creation, eliminating
        complex tool coordination in favor of direct tool loading with parameter
        injection based on the modern tool specification DSL.
        
        ### Tool Specification DSL Support:
        - Parses tool:variant:variant@param=value specifications
        - Creates tool instances with variant and parameter configuration
        - Provides factory-based tool creation with dependency injection readiness
        - Supports just-in-time tool configuration for different experiment types
        
        ### Just-in-Time Configuration:
        - Tools configured only when loaded, not upfront
        - Configuration derived from experiment parameters
        - Module independence maintained through simple parameter passing
        - Factory pattern enables clean component creation
        
        Returns:
            List of loaded and configured tools ready for experiment execution
            
        Raises:
            ValueError: If tools cannot be loaded from registry
            ConfigurationError: If tool configuration is invalid
        """
        try:
            loaded_tools = []
            
            # Process tools using modern specification format
            for tool_spec in self.config.tools:
                tool_name = tool_spec["name"]
                tool_variants = tool_spec.get("variants", [])
                tool_parameters = tool_spec.get("parameters", {})
                
                # Load tool from registry using factory pattern
                tool = self.tool_registry.get_tool(tool_name)
                if tool is None:
                    raise ValueError(f"Tool not found in registry: {tool_name}")
                
                # Configure tool variants if specified
                if tool_variants and hasattr(tool, 'configure_variants'):
                    tool.configure_variants(tool_variants)
                
                # Apply tool parameters using direct parameter injection
                for param_name, param_value in tool_parameters.items():
                    if hasattr(tool, param_name):
                        setattr(tool, param_name, param_value)
                    else:
                        self.logger.warning(f"Parameter '{param_name}' not supported by tool '{tool_name}'")
                
                # Apply timeout override if specified in configuration
                if hasattr(tool, 'timeout'):
                    tool.timeout = self.config.timeout
                
                loaded_tools.append(tool)
                
                # Log tool loading with variant and parameter information
                variant_info = f" with variants: {tool_variants}" if tool_variants else ""
                param_info = f" and parameters: {tool_parameters}" if tool_parameters else ""
                self.logger.info(f"Loaded tool: {tool_name}{variant_info}{param_info}")
            
            if not loaded_tools:
                raise ValueError("No tools loaded for experiment")
            
            return loaded_tools
            
        except Exception as e:
            self.logger.error(f"Failed to load tools: {e}")
            raise
    
    @ErrorHandler.handle_errors(
        component="ExperimentOrchestrator",
        phase="execute_monitor_generation",
    )
    def _execute_monitor_generation(self) -> bool:
        """
        Execute monitor generation using just-in-time configuration.
        
        ### Just-in-Time Configuration Pattern:
        This method implements just-in-time configuration for monitor generation,
        creating rv-monitor-generator configuration only when needed and executing
        monitor generation based on the selected specification set.
        
        ### Monitored Operations Support:
        - **JCA Specification Set**: Java Cryptography Architecture API monitoring
        - **Generic Specification Set**: Generic programming patterns monitoring
        - **Custom Specification Set**: User-defined monitored operations
        
        ### Role in the System:
        - Coordinates monitor generation for selected specification set
        - Creates just-in-time configuration for rv-monitor-generator module
        - Manages monitor output for subsequent instrumentation phase
        - Provides specification set validation and error handling
        
        Returns:
            True if monitor generation completed successfully, False otherwise
        """
        if not self.config.generate_monitors:
            self.logger.info("Monitor generation skipped by configuration")
            return True
        
        try:
            self.logger.info(f"Starting monitor generation for specification set: {self.config.specification_set}")
            
            # Just-in-time configuration for monitor generation
            monitor_config = self._create_monitor_generation_config()
            
            # Import and use rv-monitor-generator with just-in-time configuration
            try:
                from rv_monitor_generator import RuntimeVerificationGenerator
                from rv_monitor_generator.config import RVGeneratorConfig
                
                # Create typed configuration instance
                rv_config = RVGeneratorConfig(rvsec_root=monitor_config["rvsec_root"])
                generator = RuntimeVerificationGenerator(rv_config)
                output_dir = monitor_config.get("output_dir", os.path.join(self.experiment_path, "monitors"))
                success = generator.generate_monitors(output_dir)
                
                if success:
                    self.logger.info("Monitor generation completed successfully")
                    return True
                else:
                    self.logger.error("Monitor generation failed")
                    return False
                    
            except ImportError:
                self.logger.warning("rv-monitor-generator module not available, skipping monitor generation")
                return True
            
        except Exception as e:
            self.logger.error(f"Monitor generation failed: {e}")
            return False
    
    def _create_monitor_generation_config(self) -> Dict[str, Any]:
        """
        Create just-in-time configuration for monitor generation.
        
        ### Just-in-Time Configuration Pattern:
        This method creates monitor generation configuration only when needed,
        eliminating complex upfront coordination while providing specification
        set specific configuration for different monitored operations types.
        
        Returns:
            Dictionary with monitor generation configuration
        """
        rvsec_root = os.getenv("RVSEC_HOME")
        if not rvsec_root:
            raise ValueError("RVSEC_HOME environment variable not set")
        
        # Base configuration with experiment-specific parameters
        config = {
            "rvsec_root": rvsec_root,
            "output_dir": os.path.join(self.experiment_path, "monitors"),
            "timeout": 300,
            "specification_set": self.config.specification_set
        }
        
        # Specification set specific configuration
        if self.config.specification_set == "jca":
            config.update({
                "mop_specs_dir": os.path.join(rvsec_root, "specs", "jca"),
                "focus": "JCA cryptography API monitored operations"
            })
        elif self.config.specification_set == "generic":
            config.update({
                "mop_specs_dir": os.path.join(rvsec_root, "specs", "generic"),
                "focus": "Generic programming patterns monitored operations"
            })
        elif self.config.specification_set == "custom":
            config.update({
                "mop_specs_dir": os.path.join(rvsec_root, "specs", "custom"),
                "focus": "Custom monitored operations specification set"
            })
        
        return config
    
    @ErrorHandler.handle_errors(
        component="ExperimentOrchestrator",
        phase="execute_instrumentation",
    )
    def _execute_instrumentation(self) -> bool:
        """
        Execute APK instrumentation using just-in-time configuration.
        
        ### Just-in-Time Configuration Pattern:
        This method implements just-in-time configuration for APK instrumentation,
        creating rv-instrumentation configuration only when needed and coordinating
        instrumentation with monitor integration.
        
        ### Role in the System:
        - Coordinates APK instrumentation with monitor integration
        - Creates just-in-time configuration for rv-instrumentation module
        - Manages instrumented APK output for subsequent experiment execution
        - Provides instrumentation validation and error handling
        
        Returns:
            True if instrumentation completed successfully, False otherwise
        """
        if not self.config.instrument_apks:
            self.logger.info("APK instrumentation skipped by configuration")
            return True
        
        try:
            self.logger.info("Starting APK instrumentation")
            
            # Just-in-time configuration for instrumentation
            instrumentation_config = self._create_instrumentation_config()
            
            # Import and use rv-instrumentation with typed configuration
            try:
                from rv_instrumentation.config import InstrumentationConfig
                from rv_instrumentation import InstrumentationTool
                
                # Create typed configuration instance
                instrumentation_config_obj = InstrumentationConfig(**instrumentation_config)
                instrumentation_tool = InstrumentationTool(instrumentation_config_obj)
                success = instrumentation_tool.instrument_apks()
                
                if success:
                    self.logger.info("APK instrumentation completed successfully")
                    return True
                else:
                    self.logger.error("APK instrumentation failed")
                    return False
                    
            except ImportError:
                self.logger.warning("rv-instrumentation module not available, skipping instrumentation")
                return True
            
        except Exception as e:
            self.logger.error(f"APK instrumentation failed: {e}")
            return False
    
    def _create_instrumentation_config(self) -> Dict[str, Any]:
        """
        Create just-in-time configuration for APK instrumentation.
        
        ### Just-in-Time Configuration Pattern:
        This method creates instrumentation configuration only when needed,
        deriving parameters from experiment configuration and providing
        monitor integration for instrumented APK generation.
        
        Returns:
            Dictionary with instrumentation configuration
        """
        apks = self.config.get_apk_list()
        if not apks:
            raise ValueError("No APK files available for instrumentation")
        
        # Use APK directory or derive from first APK
        first_apk = Path(apks[0])
        input_dir = self.config.apk_dir if self.config.apk_dir else str(first_apk.parent)
        
        return {
            "input_dir": input_dir,
            "output_dir": os.path.join(self.experiment_path, "instrumented"),
            "monitor_output_dir": os.path.join(self.experiment_path, "monitors"),
            "enable_coverage": True,
            "instrumentation_level": "method",
            "keystore_password": "password"
        }
    
    @ErrorHandler.handle_errors(
        component="ExperimentOrchestrator",
        phase="execute_static_analysis",
    )
    def _execute_static_analysis(self) -> bool:
        """
        Execute static analysis using just-in-time configuration.
        
        ### Just-in-Time Configuration Pattern:
        This method implements just-in-time configuration for static analysis,
        creating rv-static-analysis configuration only when needed and executing
        static analysis tools for experiment APKs.
        
        ### Role in the System:
        - Coordinates static analysis tool execution for experiment APKs
        - Creates just-in-time configuration for rv-static-analysis module
        - Manages static analysis results for coverage tracking and analysis
        - Provides static analysis validation and error handling
        
        Returns:
            True if static analysis completed successfully, False otherwise
        """
        if not self.config.run_static_analysis:
            self.logger.info("Static analysis skipped by configuration")
            return True
        
        try:
            self.logger.info("Starting static analysis")
            
            # Just-in-time configuration for static analysis
            static_analysis_config = self._create_static_analysis_config()
            
            # Import and use rv-static-analysis with typed configuration
            try:
                from rv_static_analysis.config import StaticAnalysisConfig
                from rv_static_analysis import StaticAnalysisTool
                
                # Create typed configuration instance
                static_analysis_config_obj = StaticAnalysisConfig(**static_analysis_config)
                static_analysis_tool = StaticAnalysisTool(static_analysis_config_obj)
                success = static_analysis_tool.analyze_apks()
                
                if success:
                    self.logger.info("Static analysis completed successfully")
                    return True
                else:
                    self.logger.error("Static analysis failed")
                    return False
                    
            except ImportError:
                self.logger.warning("rv-static-analysis module not available, skipping static analysis")
                return True
            
        except Exception as e:
            self.logger.error(f"Static analysis failed: {e}")
            return False
    
    def _create_static_analysis_config(self) -> Dict[str, Any]:
        """
        Create just-in-time configuration for static analysis.
        
        ### Just-in-Time Configuration Pattern:
        This method creates static analysis configuration only when needed,
        providing intelligent defaults for tool selection and execution
        parameters based on experiment requirements.
        
        Returns:
            Dictionary with static analysis configuration
        """
        apks = self.config.get_apk_list()
        
        return {
            "apk_list": apks,
            "tools": ["gator", "gesda", "reach"],
            "output_dir": os.path.join(self.experiment_path, "static_analysis"),
            "timeout": 600,
            "parallel_execution": False,
            "max_parallel_tools": 2
        }
    
    @ErrorHandler.handle_errors(
        component="ExperimentOrchestrator",
        phase="execute_tools",
    )
    def _execute_tools(self, tools: List[AbstractTool]) -> bool:
        """
        Execute testing tools using factory pattern and direct coordination.
        
        ### Factory Pattern Implementation:
        This method implements the factory pattern for tool execution, providing
        direct tool coordination without complex execution controllers. It manages
        tool execution lifecycle and result collection using clean patterns.
        
        ### Tool Execution Strategy:
        - Direct tool execution with timeout management
        - Per-tool result collection and validation
        - Event bus integration for progress monitoring
        - Error handling with recovery strategies
        
        Args:
            tools: List of loaded tools ready for execution
            
        Returns:
            True if at least one tool executed successfully, False otherwise
        """
        try:
            self.logger.info(f"Starting tool execution with {len(tools)} tools")
            
            # Get instrumented APKs or original APKs for tool execution
            # Following original pattern: look for instrumented APKs in global ./out/ directory
            from rv_experiment.constants import INSTRUMENTED_DIR
            instrumented_apks = []
            
            # Check if instrumentation actually produced APKs in the global instrumented directory
            if self.config.instrument_apks and os.path.exists(INSTRUMENTED_DIR):
                instrumented_apks = [str(p) for p in Path(INSTRUMENTED_DIR).glob("*.apk")]
                self.logger.info(f"Found {len(instrumented_apks)} APKs in instrumented directory: {INSTRUMENTED_DIR}")
            
            # Use instrumented APKs if available, otherwise use original APKs
            if instrumented_apks:
                apks = instrumented_apks
                self.logger.info(f"Using {len(instrumented_apks)} instrumented APKs")
            else:
                apks = self.config.get_apk_list()
                self.logger.info(f"Using {len(apks)} original APKs from {self.config.apk_dir}")
            
            if not apks:
                raise ValueError("No APK files available for tool execution")
            
            successful_executions = 0
            
            # Execute each tool with direct coordination
            for tool in tools:
                for repetition in range(self.config.repetitions):
                    for apk in apks:
                        try:
                            self.logger.info(f"Executing {tool.name} on {Path(apk).name} (repetition {repetition + 1})")
                            
                            # Create tool-specific result directory
                            tool_result_dir = os.path.join(
                                self.experiment_path, "results", 
                                f"{tool.name}_rep{repetition + 1}_{Path(apk).stem}"
                            )
                            Path(tool_result_dir).mkdir(parents=True, exist_ok=True)
                            
                            # Execute tool with timeout and result collection
                            success = self._execute_single_tool(tool, apk, tool_result_dir)
                            
                            if success:
                                successful_executions += 1
                                self.logger.info(f"Tool execution successful: {tool.name}")
                            else:
                                self.logger.warning(f"Tool execution failed: {tool.name}")
                                
                        except Exception as tool_error:
                            self.logger.error(f"Tool execution error for {tool.name}: {tool_error}")
                            continue
            
            # Determine overall success based on execution results
            if successful_executions > 0:
                self.logger.info(f"Tool execution completed with {successful_executions} successful executions")
                return True
            else:
                self.logger.error("All tool executions failed")
                return False
            
        except Exception as e:
            self.logger.error(f"Tool execution phase failed: {e}")
            return False
    
    def _execute_single_tool(self, tool: AbstractTool, apk: str, result_dir: str) -> bool:
        """
        Execute a single tool with timeout and result management.
        
        ### Direct Tool Execution Pattern:
        This method implements direct tool execution without complex execution
        controllers, providing clean tool lifecycle management with timeout
        control and result collection.
        
        Args:
            tool: Tool instance to execute
            apk: APK file path for tool execution
            result_dir: Directory for tool results
            
        Returns:
            True if tool execution completed successfully, False otherwise
        """
        try:
            # Create App object from APK path
            from rv_android_core.app import App
            app = App(apk)
            
            # Configure tool for execution
            if hasattr(tool, 'set_output_dir'):
                tool.set_output_dir(result_dir)
            
            if hasattr(tool, 'set_timeout'):
                tool.set_timeout(self.config.timeout)
            
            # Execute tool with App object (following original pattern)
            if hasattr(tool, 'execute'):
                return tool.execute(app)
            elif hasattr(tool, 'run'):
                return tool.run(app)
            else:
                self.logger.error(f"Tool {tool.name} does not have execute() or run() method")
                return False
                
        except Exception as e:
            self.logger.error(f"Single tool execution failed: {e}")
            return False
    
    def execute_single_tool_experiment(self) -> bool:
        """
        Execute a single-tool experiment using clean orchestration.
        
        ### Clean Orchestration Pattern:
        This method implements clean orchestration for single-tool experiments,
        eliminating complex coordination patterns in favor of direct execution
        flow with factory-based component creation.
        
        Returns:
            True if experiment completed successfully, False otherwise
        """
        with self.logger.with_context(
            experiment_type="single_tool",
            experiment_id=self.config.experiment_id
        ):
            self.logger.info(LOG_START.format(phase="single-tool experiment"))
            
            try:
                # Validate configuration
                self.config.validate()
                
                # Execute processing phases in sequence
                if not self._execute_monitor_generation():
                    return False
                
                if not self._execute_instrumentation():
                    return False
                
                if not self._execute_static_analysis():
                    return False
                
                # Load and execute tools
                tools = self._load_tools()
                if len(tools) > 1:
                    self.logger.warning(f"Multiple tools configured for single-tool experiment, using first: {tools[0].name}")
                    tools = [tools[0]]
                
                if not self._execute_tools(tools):
                    return False
                
                self.logger.info(LOG_COMPLETE.format(phase="single-tool experiment"))
                return True
                
            except Exception as e:
                self.logger.error(LOG_ERROR.format(phase="single-tool experiment", error=str(e)))
                return False
    
    def execute_comparative_experiment(self) -> bool:
        """
        Execute a comparative experiment using clean orchestration.
        
        ### Clean Orchestration Pattern:
        This method implements clean orchestration for comparative experiments,
        executing multiple tools separately for comparison while maintaining
        clean separation of results and error handling.
        
        Returns:
            True if experiment completed successfully, False otherwise
        """
        with self.logger.with_context(
            experiment_type="comparative",
            experiment_id=self.config.experiment_id
        ):
            self.logger.info(LOG_START.format(phase="comparative experiment"))
            
            try:
                # Validate configuration
                self.config.validate()
                
                # Execute shared processing phases once
                if not self._execute_monitor_generation():
                    return False
                
                if not self._execute_instrumentation():
                    return False
                
                if not self._execute_static_analysis():
                    return False
                
                # Load tools for comparison
                tools = self._load_tools()
                if len(tools) < 2:
                    raise ValueError("Comparative experiment requires at least 2 tools")
                
                # Execute each tool separately for comparison
                successful_tools = 0
                
                for tool in tools:
                    self.logger.info(f"Executing comparative phase with tool: {tool.name}")
                    
                    try:
                        if self._execute_tools([tool]):
                            successful_tools += 1
                            self.logger.info(f"Comparative phase successful for tool: {tool.name}")
                        else:
                            self.logger.warning(f"Comparative phase failed for tool: {tool.name}")
                            
                    except Exception as tool_error:
                        self.logger.error(f"Comparative phase error for tool {tool.name}: {tool_error}")
                        continue
                
                # Generate comparative analysis
                self._generate_comparative_analysis(tools, successful_tools)
                
                if successful_tools > 0:
                    self.logger.info(LOG_COMPLETE.format(phase="comparative experiment"))
                    return True
                else:
                    self.logger.error("All tools failed in comparative experiment")
                    return False
                
            except Exception as e:
                self.logger.error(LOG_ERROR.format(phase="comparative experiment", error=str(e)))
                return False
    
    def execute_batch_experiment(self) -> bool:
        """
        Execute a batch experiment using clean orchestration.
        
        ### Clean Orchestration Pattern:
        This method implements clean orchestration for batch experiments,
        executing all tools on all APKs with comprehensive result collection
        and analysis generation.
        
        Returns:
            True if experiment completed successfully, False otherwise
        """
        with self.logger.with_context(
            experiment_type="batch",
            experiment_id=self.config.experiment_id
        ):
            self.logger.info(LOG_START.format(phase="batch experiment"))
            
            try:
                # Validate configuration
                self.config.validate()
                
                # Execute processing phases
                if not self._execute_monitor_generation():
                    return False
                
                if not self._execute_instrumentation():
                    return False
                
                if not self._execute_static_analysis():
                    return False
                
                # Load tools and execute batch experiment
                tools = self._load_tools()
                apks = self.config.get_apk_list()
                
                self.logger.info(f"Batch experiment with {len(tools)} tools and {len(apks)} APKs")
                
                if not self._execute_tools(tools):
                    return False
                
                # Generate batch analysis
                self._generate_batch_analysis(tools, apks)
                
                self.logger.info(LOG_COMPLETE.format(phase="batch experiment"))
                return True
                
            except Exception as e:
                self.logger.error(LOG_ERROR.format(phase="batch experiment", error=str(e)))
                return False
    
    def _generate_comparative_analysis(self, tools: List[AbstractTool], successful_tools: int):
        """
        Generate comparative analysis report for tool comparison.
        
        Args:
            tools: List of tools that were executed
            successful_tools: Number of tools that executed successfully
        """
        try:
            analysis_file = Path(self.experiment_path) / "comparative_analysis.json"
            
            analysis = {
                "experiment_id": self.config.experiment_id,
                "experiment_type": "comparative",
                "timestamp": datetime.now().isoformat(),
                "specification_set": self.config.specification_set,
                "tools": [tool.name for tool in tools],
                "successful_tools": successful_tools,
                "total_tools": len(tools),
                "success_rate": successful_tools / len(tools) if tools else 0,
                "metadata": self.config.metadata
            }
            
            import json
            with open(analysis_file, 'w') as f:
                json.dump(analysis, f, indent=2)
            
            self.logger.info(f"Comparative analysis saved: {analysis_file}")
            
        except Exception as e:
            self.logger.warning(f"Could not generate comparative analysis: {e}")
    
    def _generate_batch_analysis(self, tools: List[AbstractTool], apks: List[str]):
        """
        Generate batch analysis report for comprehensive experiment.
        
        Args:
            tools: List of tools that were executed
            apks: List of APKs that were processed
        """
        try:
            analysis_file = Path(self.experiment_path) / "batch_analysis.json"
            
            analysis = {
                "experiment_id": self.config.experiment_id,
                "experiment_type": "batch",
                "timestamp": datetime.now().isoformat(),
                "specification_set": self.config.specification_set,
                "tools": [tool.name for tool in tools],
                "apks": [Path(apk).name for apk in apks],
                "total_executions": len(tools) * len(apks) * self.config.repetitions,
                "repetitions": self.config.repetitions,
                "timeout": self.config.timeout,
                "metadata": self.config.metadata
            }
            
            import json
            with open(analysis_file, 'w') as f:
                json.dump(analysis, f, indent=2)
            
            self.logger.info(f"Batch analysis saved: {analysis_file}")
            
        except Exception as e:
            self.logger.warning(f"Could not generate batch analysis: {e}")
    
    def get_experiment_status(self) -> Dict[str, Any]:
        """
        Get current experiment status for monitoring and reporting.
        
        Returns:
            Dictionary with comprehensive experiment status information
        """
        return {
            "experiment_id": self.config.experiment_id,
            "experiment_path": self.experiment_path,
            "specification_set": self.config.specification_set,
            "tools": [tool["name"] for tool in self.config.tools],
            "processing_phases": {
                "generate_monitors": self.config.generate_monitors,
                "instrument_apks": self.config.instrument_apks,
                "run_static_analysis": self.config.run_static_analysis
            },
            "execution_config": {
                "timeout": self.config.timeout,
                "repetitions": self.config.repetitions
            },
            "status": "configured"
        }