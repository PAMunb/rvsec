# rvandroid/experiment_workflow/pre_processor.py
"""
Pre-processor component for RV-Android experiments.
Handles monitor generation, APK instrumentation, and static analysis.
"""
import os
from typing import List

from rv_android_core.app import App
from rv_android_core.constants import (
    EXTENSION_APK, EXTENSION_REACH, EXTENSION_GATOR,
    EXTENSION_GESDA, ENV_RVSEC_HOME
)
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import LOG_START, CONTEXT_COMPONENT, LOG_COMPLETE
from rv_android_core.util.logging.manager import LoggingManager
from rv_monitor_generator.runtime_verification_generator import RuntimeVerificationGenerator
from rv_monitor_generator.config import RVGeneratorConfig
from rv_android_core.event import EventBus, EventType
from rv_instrumentation.rvandroid import RVInstrumentation
from rv_experiment.config import ExperimentConfig


class PreProcessor:
    """
    A specialized component for handling the pre-processing phase of experiments.

    ### Architectural Decisions:
    - Separates pre-processing concerns from the main experiment controller
    - Provides a clear interface for configurable pre-processing operations
    - Encapsulates the logic for monitor generation, APK instrumentation, and static analysis
    - Enables independent testing and reuse of pre-processing functionality

    ### Role in the System:
    - Performs essential setup operations before experiment execution
    - Prepares applications for runtime monitoring and analysis
    - Generates and manages static analysis data for coverage tracking
    - Configures the experiment environment for successful execution
    """

    def __init__(self, config: ExperimentConfig, event_bus: EventBus):
        """
        Initialize the pre-processor.

        Args:
            config: Experiment configuration
            event_bus: Event bus for publishing events
        """
        self.config = config
        self.results_dir = config.output_dir
        self.event_bus = event_bus
        self.error_handler = ErrorHandler.get_instance()

        # Configure logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'experiment_workflow.pre_processor',
            {
                CONTEXT_COMPONENT: 'PreProcessor'
            }
        )

    def process(self, generate_monitors: bool, instrument: bool, static_analysis: bool):
        """
        Execute the pre-processing phase.

        Args:
            generate_monitors: Whether to generate monitors
            instrument: Whether to instrument APKs
            static_analysis: Whether to perform static analysis
        """
        with self.logger.with_context(phase="pre_processing"):
            self.logger.info(LOG_START.format(phase="APK pre-processing"))

            # Generate monitors if requested
            if generate_monitors:
                self._generate_monitors()

            # Instrument APKs if requested
            if instrument:
                self._instrument_apks()

            # Perform static analysis if requested
            if static_analysis:
                self._run_static_analysis()

            self.logger.info(LOG_COMPLETE.format(phase="APK pre-processing"))

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
                rv_config = self.config.get_monitored_operations_config()
                
                # Log configuration summary for transparency
                self.logger.info(f"Monitor generation using specs directory: {rv_config.mop_specs_dir}")
                
                # Instantiate with typed configuration
                rvsec = RuntimeVerificationGenerator(rv_config)
                
                # Execute monitor generation with configuration
                # Use mop_out directory from configuration or default from experiment output
                monitor_output_dir = rv_config.get_monitor_output_dir() if hasattr(rv_config, 'get_monitor_output_dir') else os.path.join(self.config.output_dir, "mop_out")
                rvsec.generate_monitors(monitor_output_dir)
                
                self.logger.info(LOG_COMPLETE.format(phase="monitor generation"))
                
                # Publish event for monitor generation completion
                self.event_bus.publish_experiment_event(
                    EventType.EXPERIMENT_STARTED,
                    experiment_id="monitor_generation",
                    message="Monitor generation completed successfully",
                    source="PreProcessor"
                )
                
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
                instrumentation_config = self.config.get_rv_instrumentation_config()
                
                # Log configuration summary for transparency
                self.logger.info(f"Instrumentation configuration: {instrumentation_config}")
                
                # Instantiate with configuration
                rvandroid = RVInstrumentation(instrumentation_config)
                
                # Get APK sources from experiment configuration
                apks = self.config.get_apk_list()
                if not apks:
                    raise ConfigurationError("No APK files available for instrumentation")
                
                # Determine APK directory from first APK
                apks_dir = os.path.dirname(apks[0]) if apks else self.config.apk_dir
                
                # Execute APK instrumentation with configuration
                rvandroid.instrument_apks(apks_dir=apks_dir, results_dir=self.config.output_dir)
                
                self.logger.info(LOG_COMPLETE.format(phase="APK instrumentation"))
                
                # Publish event for instrumentation completion
                self.event_bus.publish_experiment_event(
                    EventType.EXPERIMENT_STARTED,
                    experiment_id="apk_instrumentation",
                    message="APK instrumentation completed successfully",
                    source="PreProcessor"
                )
                
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
                static_config = self.config.get_static_analysis_config()
                
                # Log configuration summary for transparency
                self.logger.info(f"Static analysis configuration: {static_config}")

                # Find successfully instrumented APKs first
                # Static analysis should only be performed on original APKs that were
                # successfully instrumented, as only these will be used in experiments
                instrumented_apks = self._get_successfully_instrumented_apks()
                if not instrumented_apks:
                    self.logger.warning("No successfully instrumented APKs found for static analysis")
                    return

                # Get corresponding original APKs for static analysis
                # We analyze the original APKs (not instrumented ones) to avoid
                # analyzing monitor artifacts and maintain accurate baseline metrics
                original_apks_to_analyze = self._get_original_apks_for_instrumented(instrumented_apks)

                # Get available tools from static analysis configuration
                available_tools = static_config.get_static_analysis_tools()
                tool_names = list(available_tools.keys())
                self.logger.info(f"Running static analysis on {len(original_apks_to_analyze)} original APKs (corresponding to successfully instrumented APKs) with tools: {tool_names}")

                # Execute static analysis for each original APK that has a successful instrumentation
                for original_apk_path in original_apks_to_analyze:
                    app = App(original_apk_path)
                    
                    with self.logger.with_context(app_name=app.name):
                        try:
                            self.logger.info(LOG_START.format(
                                phase=f"static analysis for {app.name}"
                            ))

                            # Create APK-specific output directory
                            apk_output_dir = os.path.join(self.config.output_dir, app.name)
                            os.makedirs(apk_output_dir, exist_ok=True)
                            
                            # Create analyzer instance with APK-specific output directory
                            analyzer = StaticAnalyzer(app, config=static_config, output_dir=apk_output_dir)

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
                        app = App(os.path.join(self.config.get_instrumented_dir(), file))
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
        with self.logger.with_context(phase="find_successfully_instrumented_apks"):
            instrumented_apks = []
            instrumented_dir = self.config.get_instrumented_dir()
            
            if not os.path.exists(instrumented_dir):
                self.logger.warning(f"Instrumented directory not found: {instrumented_dir}")
                return instrumented_apks
            
            for file in os.listdir(instrumented_dir):
                if file.casefold().endswith(EXTENSION_APK):
                    instrumented_apks.append(file)
                    self.logger.debug(f"Found successfully instrumented APK: {file}")
            
            self.logger.info(f"Found {len(instrumented_apks)} successfully instrumented APKs")
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
                    self.logger.debug(f"Mapped instrumented APK '{instrumented_filename}' to original: {corresponding_original}")
                else:
                    self.logger.warning(f"No corresponding original APK found for instrumented: {instrumented_filename}")
            
            self.logger.info(f"Mapped {len(original_apks_to_analyze)} original APKs for static analysis")
            return original_apks_to_analyze
