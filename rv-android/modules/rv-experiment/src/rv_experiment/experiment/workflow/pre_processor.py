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
        
        ### Architectural Decisions:
        This method implements the configuration coordination pattern by obtaining
        the properly configured RVGeneratorConfig from the experiment configuration
        and using it to instantiate the RuntimeVerificationGenerator with all
        required dependencies.
        
        ### Configuration Flow:
        1. Extract validated RVGeneratorConfig from experiment configuration
        2. Instantiate RuntimeVerificationGenerator with proper configuration
        3. Execute monitor generation with coordinated parameters
        4. Publish completion event for workflow coordination
        
        ### Role in the System:
        - Bridges experiment configuration with monitor generation execution
        - Ensures consistent monitor generation across different experiment scenarios
        - Provides proper error handling and event coordination
        - Validates configuration before execution to fail fast
        """
        with self.logger.with_context(phase="generate_monitors"):
            self.logger.info(LOG_START.format(phase="monitor generation"))
            
            try:
                # Get RVSEC_HOME from environment variable
                rvsec_root = os.getenv(ENV_RVSEC_HOME)
                if not rvsec_root:
                    raise RuntimeError(
                        f"Environment variable {ENV_RVSEC_HOME} not set. "
                        "This is required for monitor generation."
                    )
                
                # Create RVGeneratorConfig instance using typed configuration
                rv_config = RVGeneratorConfig(rvsec_root=rvsec_root)
                
                # Log configuration summary for transparency
                self.logger.info(f"Monitor generation using RVSEC_HOME: {rvsec_root}")
                
                # Instantiate with proper typed configuration
                rvsec = RuntimeVerificationGenerator(rv_config)
                
                # Execute monitor generation with coordinated configuration
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
        
        ### Architectural Decisions:
        This method coordinates APK instrumentation by obtaining the proper
        InstrumentationConfig from the experiment configuration and using it
        to execute instrumentation with consistent parameters across the
        experiment lifecycle.
        
        ### Configuration Flow:
        1. Extract validated InstrumentationConfig from experiment configuration
        2. Instantiate RVInstrumentation with proper configuration
        3. Execute APK instrumentation with coordinated input/output directories
        4. Publish completion event for workflow coordination
        
        ### Role in the System:
        - Links monitor generation output with APK instrumentation input
        - Ensures consistent directory structure across experiment phases
        - Provides proper error handling and progress tracking
        - Coordinates instrumentation parameters with experiment objectives
        """
        with self.logger.with_context(phase="instrument_apks"):
            self.logger.info(LOG_START.format(phase="APK instrumentation"))
            
            try:
                # Get validated configuration from experiment coordinator
                instrumentation_config = self.config.get_rv_instrumentation_config()
                
                # Log configuration summary for transparency
                self.logger.info(f"Instrumentation configuration: {instrumentation_config}")
                
                # Instantiate with proper configuration
                rvandroid = RVInstrumentation(instrumentation_config)
                
                # Execute APK instrumentation with coordinated configuration
                rvandroid.instrument_apks()
                
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
        
        ### Architectural Decisions:
        This method coordinates static analysis execution by obtaining the proper
        StaticAnalysisConfig from the experiment configuration and using it to
        execute analysis with consistent tool selection and parameter coordination
        across the experiment lifecycle.
        
        ### Configuration Flow:
        1. Extract validated StaticAnalysisConfig from experiment configuration
        2. Instantiate StaticAnalyzer with proper configuration
        3. Execute static analysis on instrumented APKs with coordinated parameters
        4. Publish completion events for workflow coordination and result tracking
        
        ### Role in the System:
        - Coordinates static analysis tool execution with experiment objectives
        - Ensures analysis results are stored in consistent locations for task access
        - Provides comprehensive error handling and progress tracking
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
                # Get validated configuration from experiment coordinator
                static_config = self.config.get_rv_static_analysis_config()
                
                # Log configuration summary for transparency
                self.logger.info(f"Static analysis configuration: {static_config}")

                # Discover instrumented APKs for analysis
                instrumented_apks = []
                instrumented_dir = self.config.get_instrumented_dir()
                
                if not os.path.exists(instrumented_dir):
                    self.logger.warning(f"Instrumented directory not found: {instrumented_dir}")
                    return
                
                for file in os.listdir(instrumented_dir):
                    if file.casefold().endswith(EXTENSION_APK):
                        instrumented_apks.append(file)

                self.logger.info(f"Running static analysis on {len(instrumented_apks)} APKs with tools: {static_config.tools}")

                # Execute static analysis for each instrumented APK
                for file in instrumented_apks:
                    app = App(os.path.join(instrumented_dir, file))
                    
                    with self.logger.with_context(app_name=app.name):
                        try:
                            self.logger.info(LOG_START.format(
                                phase=f"static analysis for {app.name}"
                            ))

                            # Create analyzer instance with proper configuration
                            analyzer = StaticAnalyzer(app, config=static_config)

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
                                    "tools_executed": static_config.tools,
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
