# modules/rv-experiment/src/rv_experiment/experiment/workflow/pre_processor.py
"""
Pre-processor with Strategy Pattern for Flexible Phase Execution

This module implements a pre-processor that supports flexible phase execution
through the Strategy Pattern, enabling independent phase execution, artifact reuse,
and graceful fallback scenarios for experiment workflows.

### Features:
- Strategy Pattern for execution modes (full vs fallback)
- Independent phase execution capabilities
- Artifact validation and reuse detection
- Graceful degradation with researcher notifications
- Error handling with detailed context

### Architecture:
- Pluggable execution strategies for different scenarios
- Separation of concerns between phases
- Fallback support for missing dependencies
- Structured logging for debugging
- Type-safe configuration management
"""
import os
from typing import List, Optional, Dict, Any

from rv_android_core.app import App
from rv_android_core.constants import (
    EXTENSION_APK
)
from rv_android_core.event import EventBus, EventType
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.exceptions import ConfigurationError, RVExperimentError
from rv_android_core.util.logging.constants import LOG_START, CONTEXT_COMPONENT, LOG_COMPLETE
from rv_android_core.util.logging.manager import LoggingManager
from rv_experiment.config import ExperimentConfig
from rv_instrumentation import RVInstrumentationConfig
from rv_instrumentation.rvandroid import RVInstrumentation
from rv_monitor_generator.config import RVGeneratorConfig
from rv_monitor_generator.runtime_verification_generator import RuntimeVerificationGenerator
from rv_static_analysis import RVStaticAnalysisConfig

# Strategy Pattern imports
from .strategies import (
    PhaseExecutionStrategy, 
    FullExecutionStrategy, 
    FallbackExecutionStrategy,
    PhaseResult, 
    PhaseExecutionMode, 
    PhaseExecutionContext
)


class PreProcessor:
    """
    Pre-processor with Strategy Pattern for flexible phase execution.

    ### Architecture:
    - Strategy Pattern for pluggable execution modes (full vs fallback)
    - Independent phase execution capabilities
    - Artifact validation and reuse detection
    - Graceful degradation with researcher notifications
    - Error handling with detailed context

    ### Features:
    - Execute phases independently or as a coordinated workflow
    - Artifact reuse detection and validation
    - Fallback execution when dependencies are unavailable
    - Notification of degraded mode operations
    - Performance monitoring and execution metrics
    
    ### Strategy Pattern Implementation:
    - FullExecutionStrategy: Complete execution without fallbacks
    - FallbackExecutionStrategy: Graceful degradation with notifications
    - Strategy selection based on environment and configuration
    
    ### Responsibilities:
    - Orchestrates pre-processing phases with execution strategies
    - Handles experiment preparation despite missing dependencies
    - Manages artifact reuse across experiment iterations
    - Communicates execution mode and limitations
    """

    def __init__(self, config: ExperimentConfig, event_bus: EventBus, 
                 enable_fallback: bool = True):
        """
        Initialize the pre-processor with strategy support.

        Args:
            config: Experiment configuration
            event_bus: Event bus for publishing coordination events
            enable_fallback: Whether to enable fallback execution strategy
        """
        self.config = config
        self.results_dir = config.output_dir
        self.event_bus = event_bus
        self.error_handler = ErrorHandler.get_instance()
        self.enable_fallback = enable_fallback

        # Configure logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'rv_experiment.workflow.pre_processor',
            {
                CONTEXT_COMPONENT: 'PreProcessor'
            }
        )
        
        # Initialize strategy pattern
        self.execution_strategy = self._create_execution_strategy()
        self.phase_results: Dict[str, PhaseResult] = {}
        
        # Artifact validation cache
        self.artifact_validation_cache: Dict[str, Dict[str, bool]] = {}
        
        self.logger.info(
            f"PreProcessor initialized with {self.execution_strategy.__class__.__name__}"
        )

    def process(self, generate_monitors: bool, instrument: bool, static_analysis: bool,
                force_execution: bool = False) -> Dict[str, PhaseResult]:
        """
        Execute the pre-processing phase with strategy pattern support.

        Args:
            generate_monitors: Whether to generate runtime verification monitors
            instrument: Whether to instrument APKs with monitors
            static_analysis: Whether to perform static analysis
            force_execution: Force execution even if valid artifacts exist
            
        Returns:
            Dictionary mapping phase names to their execution results
        """
        with self.logger.with_context(phase="pre_processing"):
            self.logger.info(f"Starting pre-processing with {self.execution_strategy.__class__.__name__}")
            
            # Execute phases using strategy pattern
            if generate_monitors:
                result = self.execute_monitor_generation(force_execution=force_execution)
                self.phase_results["monitor_generation"] = result
                
            if instrument:
                result = self.execute_apk_instrumentation(force_execution=force_execution)
                self.phase_results["apk_instrumentation"] = result
                
            if static_analysis:
                result = self.execute_static_analysis(force_execution=force_execution)
                self.phase_results["static_analysis"] = result
            
            # Log processing summary
            self._log_processing_summary()
            
            self.logger.info("Pre-processing completed")
            return self.phase_results
    
    def _create_execution_strategy(self) -> PhaseExecutionStrategy:
        """
        Create appropriate execution strategy based on configuration and environment.
        
        Returns:
            Configured execution strategy instance
        """
        if self.enable_fallback:
            strategy = FallbackExecutionStrategy(self.config)
        else:
            strategy = FullExecutionStrategy(self.config)
            
        self.logger.info(f"Selected execution strategy: {strategy.__class__.__name__}")
        return strategy
    
    @ErrorHandler.handle_errors(
        component="PreProcessor",
        phase="independent_monitor_generation"
    )
    def execute_monitor_generation(self, force_execution: bool = False) -> PhaseResult:
        """
        Execute monitor generation phase independently using strategy pattern.
        
        Args:
            force_execution: Force generation even if valid monitors exist
            
        Returns:
            PhaseResult with execution details and artifact information
        """
        self.logger.info("Executing independent monitor generation")
        
        # Create execution context
        context = PhaseExecutionContext(
            experiment_config=self.config,
            phase_name="monitor_generation",
            force_execution=force_execution,
            validate_artifacts=True,
            enable_fallback=self.enable_fallback,
            artifact_directories={
                "monitors": "mop_out",
                "specs": getattr(self.config.get_monitored_operations_config(), 'mop_specs_dir', '')
            }
        )
        
        # Execute using strategy pattern
        result = self.execution_strategy.execute_phase(context)
        
        # Publish event for workflow coordination
        self._publish_phase_completion_event("monitor_generation", result)
        
        return result
    
    @ErrorHandler.handle_errors(
        component="PreProcessor",
        phase="independent_apk_instrumentation"
    )
    def execute_apk_instrumentation(self, force_execution: bool = False) -> PhaseResult:
        """
        Execute APK instrumentation phase independently using strategy pattern.
        
        Args:
            force_execution: Force instrumentation even if valid APKs exist
            
        Returns:
            PhaseResult with execution details and artifact information
        """
        self.logger.info("Executing independent APK instrumentation")
        
        # Create execution context
        context = PhaseExecutionContext(
            experiment_config=self.config,
            phase_name="apk_instrumentation",
            force_execution=force_execution,
            validate_artifacts=True,
            enable_fallback=self.enable_fallback,
            artifact_directories={
                "monitors": "mop_out",
                "instrumented": "out",
                "original_apks": self.config.apk_dir
            }
        )
        
        # Execute using strategy pattern
        result = self.execution_strategy.execute_phase(context)
        
        # Publish event for workflow coordination
        self._publish_phase_completion_event("apk_instrumentation", result)
        
        return result
    
    @ErrorHandler.handle_errors(
        component="PreProcessor",
        phase="independent_static_analysis"
    )
    def execute_static_analysis(self, force_execution: bool = False,
                              target_apks: Optional[List[str]] = None) -> PhaseResult:
        """
        Execute static analysis phase independently using strategy pattern.
        
        Args:
            force_execution: Force analysis even if valid results exist
            target_apks: Specific APKs to analyze, or None for auto-selection
            
        Returns:
            PhaseResult with execution details and artifact information
        """
        self.logger.info("Executing independent static analysis")
        
        # Create execution context
        context = PhaseExecutionContext(
            experiment_config=self.config,
            phase_name="static_analysis",
            force_execution=force_execution,
            validate_artifacts=True,
            enable_fallback=self.enable_fallback,
            artifact_directories={
                "instrumented": "out",
                "original_apks": self.config.apk_dir,
                "analysis_results": self.config.output_dir
            },
            resource_constraints={
                "target_apks": target_apks
            }
        )
        
        # Execute using strategy pattern
        result = self.execution_strategy.execute_phase(context)
        
        # Publish event for workflow coordination
        self._publish_phase_completion_event("static_analysis", result)
        
        return result
    
    def get_phase_result(self, phase_name: str) -> Optional[PhaseResult]:
        """
        Get execution result for a specific phase.
        
        Args:
            phase_name: Name of the phase to get result for
            
        Returns:
            PhaseResult if phase was executed, None otherwise
        """
        return self.phase_results.get(phase_name)
    
    def get_all_phase_results(self) -> Dict[str, PhaseResult]:
        """
        Get all phase execution results.
        
        Returns:
            Dictionary mapping phase names to their results
        """
        return self.phase_results.copy()
    
    def _publish_phase_completion_event(self, phase_name: str, result: PhaseResult) -> None:
        """
        Publish phase completion event for workflow coordination.
        
        Args:
            phase_name: Name of the completed phase
            result: Phase execution result
        """
        try:
            # Publish event for timing coordination
            self.event_bus.publish_system_event(
                EventType.STATIC_ANALYSIS_COMPLETED,  # Use existing event type
                data={
                    "phase_name": phase_name,
                    "execution_mode": result.execution_mode.value,
                    "success": result.success,
                    "artifacts_count": result.artifacts.total_artifacts,
                    "execution_time": result.execution_time,
                    "is_degraded": result.is_degraded,
                    "fallback_reason": result.fallback_reason
                },
                source="PreProcessor"
            )
        except Exception as e:
            self.logger.warning(f"Failed to publish phase completion event: {e}")
    
    def _log_processing_summary(self) -> None:
        """
        Log summary of all phase executions.
        """
        if not self.phase_results:
            return
            
        self.logger.info("Pre-processing Summary:")
        
        total_artifacts = 0
        degraded_phases = []
        failed_phases = []
        
        for phase_name, result in self.phase_results.items():
            status = "success" if result.success else "failed"
            mode = result.execution_mode.value
            
            self.logger.info(
                f"  {phase_name}: {status}, {mode} mode, "
                f"{result.artifacts.total_artifacts} artifacts, "
                f"{result.execution_time:.2f}s" if result.execution_time else "time=N/A"
            )
            
            total_artifacts += result.artifacts.total_artifacts
            
            if result.is_degraded:
                degraded_phases.append(phase_name)
                
            if not result.success:
                failed_phases.append(phase_name)
        
        self.logger.info(f"Total artifacts: {total_artifacts}")
        
        if degraded_phases:
            self.logger.warning(f"Degraded phases: {', '.join(degraded_phases)}")
            
        if failed_phases:
            self.logger.error(f"Failed phases: {', '.join(failed_phases)}")

    # Legacy method implementations for backward compatibility
    def _generate_monitors(self):
        """
        Generate runtime verification monitors using JavaMOP and RV-Monitor.
        
        ### Architecture:
        This method implements the configuration coordination pattern by obtaining
        the configured RVGeneratorConfig from the experiment configuration
        and using it to instantiate the RuntimeVerificationGenerator with
        required dependencies.
        
        ### Configuration Flow:
        1. Extract RVGeneratorConfig from experiment configuration
        2. Instantiate RuntimeVerificationGenerator with configuration
        3. Execute monitor generation with parameters
        4. Publish completion event for workflow coordination
        
        ### Role in the System:
        - Bridges experiment configuration with monitor generation execution
        - Ensures consistent monitor generation across different experiment scenarios
        - Provides error handling and event coordination
        - Validates configuration before execution to fail fast
        """
        with self.logger.with_context(phase="generate_monitors"):
            self.logger.info(LOG_START.format(phase="monitor generation"))

            try:
                # Get RVGeneratorConfig from experiment configuration
                # This uses the configuration class with custom specs support
                rv_config: RVGeneratorConfig = self.config.get_monitored_operations_config()

                # Log configuration summary for transparency
                self.logger.info(f"Monitor generation using specs directory: {rv_config.mop_specs_dir}")

                # Instantiate with typed configuration
                rvsec = RuntimeVerificationGenerator(rv_config)

                # Execute monitor generation with configuration
                # Use mop_out directory from experiment output directory
                monitor_output_dir = os.path.join(self.config.output_dir, "mop_out")
                rvsec.generate_monitors(monitor_output_dir)

                self.logger.info(LOG_COMPLETE.format(phase="monitor generation"))

                # Publish event for monitor generation completion
                # self.event_bus.publish_experiment_event(
                #     EventType.EXPERIMENT_STARTED,
                #     experiment_id="monitor_generation",
                #     message="Monitor generation completed successfully",
                #     source="PreProcessor"
                # )

            except Exception as e:
                error_context = {
                    "component": "PreProcessor",
                    "operation": "monitor_generation",
                    "experiment_id": self.config.experiment_id,
                    "config_summary": str(self.config.get_module_config("rv-monitor-generator"))
                }
                self.error_handler.handle_error(e, error_context)
                raise

    def _instrument_apks(self):
        """
        Instrument APKs with runtime verification monitors.
        
        ### Architecture:
        This method coordinates APK instrumentation by obtaining the
        InstrumentationConfig from the experiment configuration and using it
        to execute instrumentation with consistent parameters across the
        experiment lifecycle.
        
        ### Configuration Flow:
        1. Extract InstrumentationConfig from experiment configuration
        2. Instantiate RVInstrumentation with configuration
        3. Execute APK instrumentation with input/output directories
        4. Publish completion event for workflow coordination
        
        ### Role in the System:
        - Links monitor generation output with APK instrumentation input
        - Ensures consistent directory structure across experiment phases
        - Provides error handling and progress tracking
        - Coordinates instrumentation parameters with experiment objectives
        """
        with self.logger.with_context(phase="instrument_apks"):
            self.logger.info(LOG_START.format(phase="APK instrumentation"))

            try:
                # Get configuration from experiment coordinator
                instrumentation_config: RVInstrumentationConfig = self.config.get_rv_instrumentation_config()

                # Log configuration summary for transparency
                self.logger.info(f"Instrumentation configuration: {instrumentation_config}")

                # Instantiate with configuration
                rvandroid = RVInstrumentation(instrumentation_config)

                # Get APK sources from experiment configuration
                apks = self.config.get_apk_list()
                if not apks:
                    raise ConfigurationError("No APK files available for instrumentation")

                # Execute APK instrumentation with configuration
                # Use instrumented_dir from configuration as results_dir for instrumented APKs
                rvandroid.instrument_apks(apks_dir=self.config.apk_dir, results_dir=instrumentation_config.instrumented_dir)

                self.logger.info(LOG_COMPLETE.format(phase="APK instrumentation"))

                # Publish event for instrumentation completion
                # self.event_bus.publish_experiment_event(
                #     EventType.EXPERIMENT_STARTED,
                #     experiment_id="apk_instrumentation",
                #     message="APK instrumentation completed successfully",
                #     source="PreProcessor"
                # )

            except Exception as e:
                error_context = {
                    "component": "PreProcessor",
                    "operation": "apk_instrumentation",
                    "experiment_id": self.config.experiment_id,
                    "config_summary": str(self.config.get_module_config("rv-instrumentation"))
                }
                self.error_handler.handle_error(e, error_context)
                raise

    def _run_static_analysis(self):
        """
        Run static analysis on all instrumented APKs.
        
        ### Architecture:
        This method coordinates static analysis execution by obtaining the
        StaticAnalysisConfig from the experiment configuration and using it to
        execute analysis with consistent tool selection and parameter coordination
        across the experiment lifecycle.
        
        ### Configuration Flow:
        1. Extract StaticAnalysisConfig from experiment configuration
        2. Instantiate StaticAnalyzer with configuration
        3. Execute static analysis on instrumented APKs with parameters
        4. Publish completion events for workflow coordination and result tracking
        
        ### Role in the System:
        - Coordinates static analysis tool execution with experiment objectives
        - Ensures analysis results are stored in consistent locations for task access
        - Provides error handling and progress tracking
        - Links instrumentation output with static analysis input processing
        """
        try:
            from rv_static_analysis.analysis.static.static_analysis import StaticAnalyzer
        except ImportError:
            self.logger.error("rv-static-analysis module not available. Skipping static analysis.")
            return

        with self.logger.with_context(phase="static_analysis"):
            self.logger.info(LOG_START.format(phase="static analysis"))

            try:
                # Get configuration from experiment coordinator
                static_config: RVStaticAnalysisConfig = self.config.get_static_analysis_config()

                # Log configuration summary for transparency
                self.logger.info(f"Static analysis configuration: {static_config}")

                # Select APKs for analysis based on configuration
                apks_to_analyze = self._select_apks_for_analysis()
                if not apks_to_analyze:
                    self.logger.warning("No APKs available for static analysis")
                    return

                # Get available tools from static analysis configuration
                # TODO remover/rever essa abstracao de tools
                available_tools = static_config.get_static_analysis_tools()
                tool_names = list(available_tools.keys())
                apk_type = "instrumented" if self.config.analyze_instrumented_apks else "original"
                self.logger.info(
                    f"Running static analysis on {len(apks_to_analyze)} {apk_type} APKs with tools: {tool_names}")

                # Execute static analysis for each selected APK
                for apk_path in apks_to_analyze:
                    app = App(app_path=apk_path)

                    with self.logger.with_context(app_name=app.name):
                        try:
                            self.logger.info(LOG_START.format(
                                phase=f"static analysis for {app.name}"
                            ))

                            # Create APK-specific output directory
                            apk_output_dir = os.path.join(self.config.output_dir, app.name)
                            os.makedirs(apk_output_dir, exist_ok=True)

                            # Create analyzer instance with APK-specific output directory
                            analyzer = StaticAnalyzer(app=app, config=static_config, output_dir=apk_output_dir)

                            # Execute analysis with coordinated configuration
                            result = analyzer.analyze()

                            # Get metrics for reporting and coordination
                            metrics = analyzer.get_metrics()

                            # Publish event with comprehensive result data
                            self.event_bus.publish_analysis_event(
                                EventType.STATIC_ANALYSIS_COMPLETED,
                                data={
                                    "app_name": app.name,
                                    "success": result.success,
                                    "execution_times": result.execution_times,
                                    "tools_executed": tool_names,
                                    "metrics": metrics
                                },
                                source="PreProcessor"
                            )

                            self.logger.info(LOG_COMPLETE.format(
                                phase=f"static analysis for {app.name}"
                            ))

                        except Exception as e:
                            error_context = {
                                "component": "PreProcessor",
                                "operation": "static_analysis",
                                "app_name": app.name,
                                "static_config": str(static_config),
                                "experiment_id": self.config.experiment_id
                            }
                            self.error_handler.handle_error(e, error_context)
                            # Continue with next APK rather than failing entire analysis

                self.logger.info(LOG_COMPLETE.format(phase="static analysis"))

            except Exception as e:
                error_context = {
                    "component": "PreProcessor",
                    "operation": "static_analysis_coordination",
                    "experiment_id": self.config.experiment_id,
                    "config_summary": str(self.config.get_module_config("rv-static-analysis"))
                }
                self.error_handler.handle_error(e, error_context)
                raise

    def get_instrumented_apks(self) -> List[App]:
        """
        Get all instrumented APKs from the instrumented directory.

        Returns:
            List of App objects representing the instrumented APKs
        """
        with self.logger.with_context(phase="find_instrumented_apks"):
            apks = []
            for file in os.listdir(self.config.get_instrumented_dir()):
                if file.casefold().endswith(EXTENSION_APK):
                    try:
                        app = App(app_path=os.path.join(self.config.get_instrumented_dir(), file))
                        apks.append(app)
                        self.logger.debug(f"Found instrumented APK: {app.name}")
                    except Exception as e:
                        error_context = {
                            "component": "PreProcessor",
                            "operation": "processing_apk",
                            "file_name": file,
                            "instrumented_dir": self.config.get_instrumented_dir()
                        }
                        self.error_handler.handle_error(e, error_context)

            return apks

    def _get_successfully_instrumented_apks(self) -> List[str]:
        """
        Get list of successfully instrumented APK filenames from the instrumented directory.
        
        ### Architectural Logic:
        This method identifies APKs that were successfully instrumented by checking
        the instrumented directory. Only APKs that exist in this directory are
        considered successfully instrumented and eligible for experiment execution.
        
        Returns:
            List of instrumented APK filenames (not full paths)
        """
        with self.logger.with_context(phase="find_instrumented_apks"):
            instrumented_apks = []
            instrumented_dir = self.config.get_instrumented_dir()

            if not os.path.exists(instrumented_dir):
                self.logger.warning(f"Instrumented directory not found: {instrumented_dir}")
                return instrumented_apks

            for file in os.listdir(instrumented_dir):
                if file.casefold().endswith(EXTENSION_APK):
                    instrumented_apks.append(file)
                    self.logger.debug(f"Found instrumented APK: {file}")

            self.logger.info(f"Found {len(instrumented_apks)} instrumented APKs")
            return instrumented_apks

    def _get_original_apks_for_instrumented(self, instrumented_apk_filenames: List[str]) -> List[str]:
        """
        Get original APK paths corresponding to successfully instrumented APKs.
        
        ### Architectural Logic:
        This method maps instrumented APK filenames back to their original APK paths
        for static analysis. The static analysis must be performed on original APKs
        to avoid analyzing monitor artifacts while maintaining correspondence with
        the instrumented APKs that will be used in experiments.
        
        ### Mapping Strategy:
        - Instrumented APKs typically have the same filename as originals
        - We match by filename and verify the original APK exists
        - Only return original APKs that have corresponding instrumented versions
        
        Args:
            instrumented_apk_filenames: List of instrumented APK filenames
            
        Returns:
            List of original APK full paths corresponding to instrumented APKs
        """
        with self.logger.with_context(phase="map_original_apks_for_instrumented"):
            original_apks_to_analyze = []
            all_original_apks = self.config.get_apk_list()

            for instrumented_filename in instrumented_apk_filenames:
                # Find corresponding original APK
                corresponding_original = None

                for original_apk_path in all_original_apks:
                    original_filename = os.path.basename(original_apk_path)

                    # Match by filename (instrumented APKs typically keep original name)
                    if original_filename == instrumented_filename:
                        corresponding_original = original_apk_path
                        break

                if corresponding_original:
                    original_apks_to_analyze.append(corresponding_original)
                    self.logger.debug(
                        f"Mapped instrumented APK '{instrumented_filename}' to original: {corresponding_original}")
                else:
                    self.logger.warning(
                        f"No corresponding original APK found for instrumented: {instrumented_filename}")

            self.logger.info(f"Mapped {len(original_apks_to_analyze)} original APKs for static analysis")
            return original_apks_to_analyze
    
    @ErrorHandler.handle_errors(component="PreProcessor", phase="select_apks_for_analysis")
    def _select_apks_for_analysis(self) -> List[str]:
        """
        Select APKs for static analysis based on configuration and availability.
        
        ### APK Selection Strategy:
        - Uses instrumented APKs if available and configured to do so
        - Falls back to original APKs if instrumented APKs unavailable
        - Respects artifact reuse configuration settings
        - Provides clear logging about selection decisions
        
        Returns:
            List of APK paths selected for static analysis
        """
        # Get directory manager for artifact detection
        directory_manager = self.config.get_directory_manager()
        
        # Check for instrumented APKs if preferred
        if self.config.analyze_instrumented_apks:
            instrumented_apks = directory_manager.check_instrumented_apks(self.config.specification_set)
            if instrumented_apks:
                # Convert filenames to full paths
                instrumented_dir = directory_manager.get_instrumented_dir(self.config.specification_set)
                apk_paths = [os.path.join(str(instrumented_dir), apk) for apk in instrumented_apks]
                self.logger.info(f"Using {len(apk_paths)} instrumented APKs for static analysis")
                return apk_paths
            else:
                self.logger.warning("No instrumented APKs found, falling back to original APKs")
        
        # Use original APKs as default or fallback
        original_apks = self.config.get_apk_list()
        if original_apks:
            self.logger.info(f"Using {len(original_apks)} original APKs for static analysis")
            return original_apks
        
        # No APKs available
        self.logger.error("No APKs available for static analysis")
        return []
