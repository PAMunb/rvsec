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
    EXTENSION_GESDA
)
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import LOG_START, CONTEXT_COMPONENT, LOG_COMPLETE
from rv_android_core.util.logging.manager import LoggingManager
from rv_monitor_generator.runtime_verification_generator import RuntimeVerificationGenerator
from rv_android_core.event.bus import EventBus, EventType
from rv_instrumentation.rvandroid import RVInstrumentation
from rv_experiment.config import ExperimentConfiguration


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

    def __init__(self, config: ExperimentConfiguration, event_bus: EventBus):
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
            self.logger.info(LOG_START.format(operation="APK pre-processing"))

            # Generate monitors if requested
            if generate_monitors:
                self._generate_monitors()

            # Instrument APKs if requested
            if instrument:
                self._instrument_apks()

            # Perform static analysis if requested
            if static_analysis:
                self._run_static_analysis()

            self.logger.info(LOG_COMPLETE.format(operation="APK pre-processing"))

    def _generate_monitors(self):
        """Generate runtime verification monitors using JavaMOP and RV-Monitor."""
        with self.logger.with_context(phase="generate_monitors"):
            self.logger.info(LOG_START.format(operation="monitor generation"))
            # TODO tratar config
            rvsec = RuntimeVerificationGenerator()
            rvsec.generate_monitors()
            self.logger.info(LOG_COMPLETE.format(operation="monitor generation"))

            # Publish event for monitor generation completion
            self.event_bus.publish_experiment_event(
                EventType.EXPERIMENT_STARTED,
                experiment_id="monitor_generation",
                message="Monitor generation completed",
                source="PreProcessor"
            )

    def _instrument_apks(self):
        """Instrument APKs with runtime verification monitors."""
        with self.logger.with_context(phase="instrument_apks"):
            self.logger.info(LOG_START.format(operation="APK instrumentation"))
            rvandroid = RVInstrumentation()
            # TODO: Update to use proper instrumentation method
            # rv_android_core.instrument_apks(results_dir=self.config.get_instrumented_dir())
            self.logger.info(LOG_COMPLETE.format(operation="APK instrumentation"))

            # Publish event for instrumentation completion
            self.event_bus.publish_experiment_event(
                EventType.EXPERIMENT_STARTED,
                experiment_id="apk_instrumentation",
                message="APK instrumentation completed",
                source="PreProcessor"
            )

    def _run_static_analysis(self):
        """
        Run static analysis on all instrumented APKs.
        
        Uses the StaticAnalyzer class to perform static analysis on APKs,
        following the standardized analyzer pattern.
        """
        from rv_android_core.analysis.static.static_analysis import StaticAnalyzer

        with self.logger.with_context(phase="static_analysis"):
            self.logger.info(LOG_START.format(operation="static analysis"))

            instrumented_apks = []
            for file in os.listdir(self.config.get_instrumented_dir()):
                if file.casefold().endswith(EXTENSION_APK):
                    instrumented_apks.append(file)

            self.logger.info(f"Running static analysis on {len(instrumented_apks)} APKs")

            for file in instrumented_apks:
                app = App(os.path.join(self.config.get_instrumented_dir(), file))
                base_name_template = app.name + "{}"
                gesda_file = os.path.join(self.config.get_instrumented_dir(), base_name_template.format(EXTENSION_GESDA))
                gator_file = os.path.join(self.config.get_instrumented_dir(), base_name_template.format(EXTENSION_GATOR))
                reach_file = os.path.join(self.config.get_instrumented_dir(), base_name_template.format(EXTENSION_REACH))

                with self.logger.with_context(app_name=app.name):
                    try:
                        self.logger.info(LOG_START.format(
                            operation=f"static analysis for {app.name}"
                        ))

                        # Create analyzer instance
                        analyzer = StaticAnalyzer(app, output_dir=self.config.get_instrumented_dir())

                        # Set custom output files if needed
                        analyzer.gesda_file = gesda_file
                        analyzer.gator_file = gator_file
                        analyzer.reach_file = reach_file

                        # Run analysis
                        result = analyzer.analyze()

                        # Get metrics for reporting
                        metrics = analyzer.get_metrics()

                        # Publish event with result data
                        self.event_bus.publish_analysis_event(
                            EventType.STATIC_ANALYSIS_COMPLETED,
                            data={
                                "app_name": app.name,
                                "success": result.success,
                                "execution_times": result.execution_times
                            },
                            source="PreProcessor"
                        )

                        self.logger.info(LOG_COMPLETE.format(
                            operation=f"static analysis for {app.name}"
                        ))
                    except Exception as e:
                        error_context = {
                            "component": "PreProcessor",
                            "operation": "static_analysis",
                            "app_name": app.name,
                            "gesda_file": gesda_file,
                            "gator_file": gator_file,
                            "reach_file": reach_file,
                            "results_dir": self.results_dir
                        }
                        self.error_handler.handle_error(e, error_context)

            self.logger.info(LOG_COMPLETE.format(operation="static analysis"))

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
