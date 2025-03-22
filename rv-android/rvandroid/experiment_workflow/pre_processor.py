# rvandroid/experiment_workflow/pre_processor.py
"""
Pre-processor component for RV-Android experiments.
Handles monitor generation, APK instrumentation, and static analysis.
"""
import os
from typing import List

from rvandroid.app import App
from rvandroid.constants import (
    EXTENSION_APK, EXTENSION_REACH, EXTENSION_GATOR,
    EXTENSION_GESDA
)
from rvandroid.experiment.event_system import EventBus, EventType
from rvandroid.rvandroid import RvAndroid
from rvandroid.rvsec import RVSec
from rvandroid.util.logging_manager import LoggingManager
from settings import INSTRUMENTED_DIR


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

    def __init__(self, results_dir: str, event_bus: EventBus):
        """
        Initialize the pre-processor.

        Args:
            results_dir: Directory for storing experiment results
            event_bus: Event bus for publishing events
        """
        self.results_dir = results_dir
        self.event_bus = event_bus

        # Configure logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'experiment_workflow.pre_processor',
            {
                LoggingManager.CONTEXT_COMPONENT: 'PreProcessor'
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
            self.logger.info(LoggingManager.LOG_START.format(operation="APK pre-processing"))

            # Generate monitors if requested
            if generate_monitors:
                self._generate_monitors()

            # Instrument APKs if requested
            if instrument:
                self._instrument_apks()

            # Perform static analysis if requested
            if static_analysis:
                self._run_static_analysis()

            self.logger.info(LoggingManager.LOG_COMPLETE.format(operation="APK pre-processing"))

    def _generate_monitors(self):
        """Generate runtime verification monitors using JavaMOP and RV-Monitor."""
        with self.logger.with_context(phase="generate_monitors"):
            self.logger.info(LoggingManager.LOG_START.format(operation="monitor generation"))
            rvsec = RVSec()
            rvsec.generate_monitors()
            self.logger.info(LoggingManager.LOG_COMPLETE.format(operation="monitor generation"))

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
            self.logger.info(LoggingManager.LOG_START.format(operation="APK instrumentation"))
            rvandroid = RvAndroid()
            rvandroid.instrument_apks(results_dir=INSTRUMENTED_DIR)
            self.logger.info(LoggingManager.LOG_COMPLETE.format(operation="APK instrumentation"))

            # Publish event for instrumentation completion
            self.event_bus.publish_experiment_event(
                EventType.EXPERIMENT_STARTED,
                experiment_id="apk_instrumentation",
                message="APK instrumentation completed",
                source="PreProcessor"
            )

    def _run_static_analysis(self):
        """Run static analysis on all instrumented APKs."""
        import rvandroid.analysis.static_analysis as static

        with self.logger.with_context(phase="static_analysis"):
            self.logger.info(LoggingManager.LOG_START.format(operation="static analysis"))

            instrumented_apks = []
            for file in os.listdir(INSTRUMENTED_DIR):
                if file.casefold().endswith(EXTENSION_APK):
                    instrumented_apks.append(file)

            self.logger.info(f"Running static analysis on {len(instrumented_apks)} APKs")

            for file in instrumented_apks:
                app = App(os.path.join(INSTRUMENTED_DIR, file))
                base_name_template = app.name + "{}"
                gesda_file = os.path.join(INSTRUMENTED_DIR, base_name_template.format(EXTENSION_GESDA))
                gator_file = os.path.join(INSTRUMENTED_DIR, base_name_template.format(EXTENSION_GATOR))
                reach_file = os.path.join(INSTRUMENTED_DIR, base_name_template.format(EXTENSION_REACH))

                with self.logger.with_context(app_name=app.name):
                    try:
                        self.logger.info(LoggingManager.LOG_START.format(
                            operation=f"static analysis for {app.name}"
                        ))
                        static.run_static_analysis(app, gesda_file, gator_file, reach_file)
                        self.event_bus.publish_analysis_event(
                            EventType.STATIC_ANALYSIS_COMPLETED,
                            data={"app_name": app.name},
                            source="PreProcessor"
                        )
                        self.logger.info(LoggingManager.LOG_COMPLETE.format(
                            operation=f"static analysis for {app.name}"
                        ))
                    except Exception as e:
                        self.logger.error(LoggingManager.LOG_ERROR.format(
                            operation=f"static analysis for {app.name}",
                            error=str(e)
                        ))

            self.logger.info(LoggingManager.LOG_COMPLETE.format(operation="static analysis"))

    def get_instrumented_apks(self) -> List[App]:
        """
        Get all instrumented APKs from the instrumented directory.

        Returns:
            List of App objects representing the instrumented APKs
        """
        with self.logger.with_context(phase="find_instrumented_apks"):
            apks = []
            for file in os.listdir(INSTRUMENTED_DIR):
                if file.casefold().endswith(EXTENSION_APK):
                    try:
                        app = App(os.path.join(INSTRUMENTED_DIR, file))
                        apks.append(app)
                        self.logger.debug(f"Found instrumented APK: {app.name}")
                    except Exception as e:
                        self.logger.error(LoggingManager.LOG_ERROR.format(
                            operation=f"processing APK {file}",
                            error=str(e)
                        ))

            return apks
       