# modules/rv-experiment/src/rv_experiment/experiment/workflow/pre_processor.py
"""
Pre-processor component for RV-Android experiments.
Handles monitor generation, APK instrumentation, and static analysis.
"""
import os
from typing import List

from rv_android_core.constants import EXTENSION_APK
from rv_android_core.domain.app import App
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import LOG_START, CONTEXT_COMPONENT, LOG_COMPLETE
from rv_android_core.util.logging.manager import LoggingManager
from rv_experiment.config import ExperimentConfig
from rv_experiment.constants import MONITORS_DIR, INSTRUMENTED_APKS_DIR


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

    def __init__(self, config: ExperimentConfig):
        """
        Initialize the pre-processor.

        Args:
            config: Experiment configuration
        """
        self.config = config
        self.results_dir = config.output_dir
        self.error_handler = ErrorHandler.get_instance()

        # Configure logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'rv_experiment.experiment.workflow.pre_processor',
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
            else:
                self.logger.warning("Skipping monitor generation")

            # Instrument APKs if requested
            if instrument:
                self._instrument_apks()
            else:
                self.logger.warning("Skipping APK instrumentation")

            # Perform static analysis if requested
            if static_analysis:
                self._run_static_analysis()
            else:
                self.logger.warning("Skipping static analysis")

            self.logger.info(LOG_COMPLETE.format(phase="APK pre-processing"))
            self.logger.info("Pre-processing phase completed")

    def _generate_monitors(self):
        """Generate runtime verification monitors using JavaMOP and RV-Monitor."""
        with self.logger.with_context(phase="generate_monitors"):
            self.logger.info(LOG_START.format(phase="monitor generation"))

            try:
                # Ensure monitor output directory exists
                monitor_output_dir = os.path.join(self.config.output_dir, MONITORS_DIR)
                os.makedirs(monitor_output_dir, exist_ok=True)

                # Get monitored operations configuration
                rv_config = self.config.get_monitored_operations_config()

                # Import and use monitor generator
                from rv_monitor_generator.runtime_verification_generator import RuntimeVerificationGenerator

                generator = RuntimeVerificationGenerator(rv_config)

                success = generator.generate_monitors(monitor_output_dir)
                if not success:
                    self.logger.warning("Monitor generation failed")
                else:
                    self.logger.info(LOG_COMPLETE.format(phase="monitor generation"))
                    self.logger.info("Monitors generated")

            except ImportError:
                self.logger.warning("Monitor generator module not available - skipping monitor generation")
            except Exception as e:
                error_context = {
                    "component": "PreProcessor",
                    "operation": "monitor_generation",
                    "config": str(rv_config) if 'rv_config' in locals() else "unavailable"
                }
                self.error_handler.handle_error(e, error_context)

    def _instrument_apks(self):
        """Instrument APKs with runtime verification monitors."""
        with self.logger.with_context(phase="instrument_apks"):
            self.logger.info(LOG_START.format(phase="APK instrumentation"))

            try:
                # Ensure required directories exist
                instrumented_dir = os.path.join(self.config.output_dir, INSTRUMENTED_APKS_DIR)
                os.makedirs(instrumented_dir, exist_ok=True)

                # Get instrumentation configuration (monitors should already be generated)
                instrumentation_config = self.config.get_rv_instrumentation_config()

                # Import instrumentation module
                from rv_instrumentation import RVInstrumentation

                instrumenter = RVInstrumentation(instrumentation_config)
                apk_list = self.config.get_apk_list()

                if not apk_list:
                    self.logger.warning("No APKs configured for instrumentation")
                    return

                # Execute instrumentation
                instrumented_dir = os.path.join(self.config.output_dir, INSTRUMENTED_APKS_DIR)
                success = instrumenter.instrument_apks(
                    apks_dir=self.config.apks_dir,
                    results_dir=instrumented_dir,
                    apk_paths=apk_list
                )

                if not success:
                    self.logger.error("APK instrumentation failed")
                else:
                    # Note: Instrumentation errors JSON will be generated by ResultManager
                    # during post-processing with access to experiment results directory
                    self.logger.info(LOG_COMPLETE.format(phase="APK instrumentation"))
                    self.logger.info("Instrumentation completed")

            except ImportError:
                self.logger.warning("Instrumentation module not available - copying original APKs")
                self._copy_original_apks()
                # Note: Instrumentation errors will be tracked and reported by ResultManager
            except Exception as e:
                error_context = {
                    "component": "PreProcessor",
                    "operation": "apk_instrumentation",
                    "apks_dir": self.config.apks_dir,
                    "output_dir": self.config.output_dir
                }
                self.error_handler.handle_error(e, error_context)
                self._copy_original_apks()
                # Note: Instrumentation errors will be tracked and reported by ResultManager


    def _copy_original_apks(self):
        """Copy original APKs to output directory as fallback."""
        instrumented_dir = os.path.join(self.config.output_dir, INSTRUMENTED_APKS_DIR)
        os.makedirs(instrumented_dir, exist_ok=True)

        import shutil
        for apk_path in self.config.get_apk_list():
            apk_name = os.path.basename(apk_path)
            dest_path = os.path.join(instrumented_dir, apk_name)
            if not os.path.exists(dest_path):
                shutil.copy2(apk_path, dest_path)
                self.logger.debug(f"Copied {apk_name} to instrumented directory")

    def _run_static_analysis(self):
        """
        Run static analysis on all instrumented APKs.
        
        Uses the StaticAnalyzer class to perform static analysis on APKs,
        following the standardized analyzer pattern.
        """
        with self.logger.with_context(phase="static_analysis"):
            self.logger.info(LOG_START.format(phase="static analysis"))

            try:
                # Import static analysis module
                from rv_static_analysis.analysis.static.static_analysis import StaticAnalyzer

                # Get static analysis configuration
                static_config = self.config.get_static_analysis_config()

                # Get target APKs (prefer instrumented, fallback to original)
                target_apks = self._get_target_apks_for_analysis()
                if not target_apks:
                    self.logger.warning("No APKs available for static analysis")
                    return

                self.logger.info(f"Running static analysis on {len(target_apks)} APKs")

                for apk_path in target_apks:
                    apk_name = os.path.basename(apk_path)

                    with self.logger.with_context(app_name=apk_name):
                        try:
                            self.logger.info(LOG_START.format(phase=f"static analysis for {apk_name}"))

                            # Use instrumented APKs directory for static analysis output
                            # This keeps APKs and their static analysis files together
                            apk_output_dir = os.path.join(self.config.output_dir, INSTRUMENTED_APKS_DIR)
                            os.makedirs(apk_output_dir, exist_ok=True)

                            # Create App instance and analyzer
                            app = App(app_path=apk_path)

                            analyzer = StaticAnalyzer(
                                app=app,
                                config=static_config,
                                output_dir=apk_output_dir
                            )

                            # Execute analysis
                            result = analyzer.analyze()

                            if not result.success:
                                self.logger.warning(f"Static analysis failed for {apk_name}: {result.errors}")
                            else:
                                self.logger.info(LOG_COMPLETE.format(phase=f"static analysis for {apk_name}"))

                        except Exception as e:
                            error_context = {
                                "component": "PreProcessor",
                                "operation": "static_analysis",
                                "app_name": apk_name,
                                "apk_path": apk_path
                            }
                            self.error_handler.handle_error(e, error_context)

                self.logger.info(LOG_COMPLETE.format(phase="static analysis"))
                self.logger.info("Static analysis completed")

            except ImportError:
                self.logger.warning("Static analysis module not available - skipping static analysis")
            except Exception as e:
                error_context = {
                    "component": "PreProcessor",
                    "operation": "static_analysis_setup",
                    "output_dir": self.config.output_dir
                }
                self.error_handler.handle_error(e, error_context)


    def _get_target_apks_for_analysis(self) -> List[str]:
        """Get original APKs for static analysis.

        GATOR/Soot cannot process instrumented APKs because the AspectJ-woven
        bytecode causes TypeResolver errors. Static analysis always runs on
        original APKs; the output goes to instrumented_apks/ so rv-platform
        finds the JSON alongside the instrumented APK.
        """
        return self.config.get_apk_list()

    def get_instrumented_apks(self) -> List[App]:
        """
        Get all instrumented APKs from the instrumented directory.

        Returns:
            List of App objects representing the instrumented APKs
        """
        with self.logger.with_context(phase="find_instrumented_apks"):
            apks = []
            instrumented_dir = os.path.join(self.config.output_dir, INSTRUMENTED_APKS_DIR)

            if os.path.exists(instrumented_dir):
                for file in os.listdir(instrumented_dir):
                    if file.endswith(EXTENSION_APK):
                        try:
                            app_path = os.path.join(instrumented_dir, file)
                            app = App(app_path=app_path)
                            apks.append(app)
                            self.logger.debug(f"Found instrumented APK: {file}")
                        except Exception as e:
                            error_context = {
                                "component": "PreProcessor",
                                "operation": "processing_apk",
                                "file_name": file,
                                "instrumented_dir": instrumented_dir
                            }
                            self.error_handler.handle_error(e, error_context)

            # Fallback to original APKs if no instrumented found
            if not apks:
                self.logger.warning("No instrumented APKs found, using original APKs")
                for apk_path in self.config.get_apk_list():
                    app = App(app_path=apk_path)
                    apks.append(app)

            return apks
