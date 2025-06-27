# modules/rv-experiment/src/rv_experiment/experiment/workflow/pre_processor.py
"""
Pre-processor component for RV-Android experiments.
Handles monitor generation, APK instrumentation, and static analysis.

Implements runtime verification with automatic fallback when dependencies are unavailable.
"""
import os
from typing import List, Optional

from rv_android_core.app import App
from rv_android_core.constants import EXTENSION_APK
from rv_android_core.event import EventBus, EventType
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.exceptions import ConfigurationError, RVExperimentError
from rv_android_core.util.logging.constants import LOG_START, CONTEXT_COMPONENT, LOG_COMPLETE
from rv_android_core.util.logging.manager import LoggingManager
from rv_experiment.config import ExperimentConfig


class PreProcessor:
    """
    Pre-processor for experiment preparation with runtime verification support.

    ### Architecture:
    - Direct execution with automatic fallback
    - Runtime verification by default when dependencies are available
    - Fallback notifications when operating in degraded mode
    - Artifact reuse detection

    ### Execution:
    - Attempts full runtime verification first
    - Automatic fallback when ImportError occurs
    - Logs execution mode (full vs fallback)
    - Supports forced fallback mode via configuration
    
    ### Features:
    - Monitor generation with JavaMOP/RV-Monitor
    - APK instrumentation with runtime verification
    - Static analysis with multiple tools
    - Artifact reuse and validation
    - Graceful degradation when tools unavailable
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

        # Execution state tracking
        self.execution_mode = "unknown"
        self.fallback_reasons = []

    def process(self, generate_monitors: bool, instrument: bool, static_analysis: bool):
        """
        Execute the pre-processing phase with runtime verification support.

        Args:
            generate_monitors: Whether to generate monitors
            instrument: Whether to instrument APKs
            static_analysis: Whether to perform static analysis
        """
        with self.logger.with_context(phase="pre_processing"):
            self.logger.info(LOG_START.format(phase="APK pre-processing"))

            # Check if user forced fallback mode
            force_fallback = getattr(self.config, 'force_fallback_mode', False)
            if force_fallback:
                self.logger.warning("FALLBACK MODE FORCED by configuration")
                self.execution_mode = "forced_fallback"

            # Analyze artifact reuse potential
            reuse_analysis = self.config.analyze_artifact_reuse()
            can_skip_phases = reuse_analysis.get("can_skip_phases", {})
            
            if reuse_analysis.get("reuse_enabled", False):
                self.logger.info(f"Artifact reuse analysis: {reuse_analysis['reusable_artifacts']['overall']}")

            # Generate monitors if requested
            if generate_monitors:
                if can_skip_phases.get("monitor_generation", False):
                    self.logger.info("Skipping monitor generation - artifacts already exist")
                else:
                    self._generate_monitors(force_fallback)

            # Instrument APKs if requested  
            if instrument:
                if can_skip_phases.get("instrumentation", False):
                    self.logger.info("Skipping APK instrumentation - artifacts already exist")
                else:
                    self._instrument_apks(force_fallback)

            exit(1)

            # Perform static analysis if requested
            if static_analysis:
                if can_skip_phases.get("static_analysis", False):
                    self.logger.info("Skipping static analysis - artifacts already exist")
                else:
                    self._run_static_analysis(force_fallback)

            # Report execution summary
            self._log_execution_summary()
            self.logger.info(LOG_COMPLETE.format(phase="APK pre-processing"))

    @ErrorHandler.handle_errors(
        component="PreProcessor",
        phase="monitor_generation"
    )
    def _generate_monitors(self, force_fallback: bool = False):
        """
        Generate runtime verification monitors with automatic fallback.
        
        Args:
            force_fallback: Force fallback mode (skip full generation)
        """
        with self.logger.with_context(phase="generate_monitors"):
            self.logger.info(LOG_START.format(phase="monitor generation"))

            if force_fallback:
                self._generate_monitors_fallback()
                return

            # Try full monitor generation first
            try:
                self._generate_monitors_full()
                self.logger.info("✅ Monitor generation completed in FULL mode")
                if self.execution_mode == "unknown":
                    self.execution_mode = "full"
                    
            except ImportError as e:
                self.logger.warning(f"Monitor generator module unavailable: {e}")
                self._generate_monitors_fallback()
                
            except Exception as e:
                self.logger.error(f"Monitor generation failed: {e}")
                self._generate_monitors_fallback()

            self.logger.info(LOG_COMPLETE.format(phase="monitor generation"))

    def _generate_monitors_full(self):
        """Execute full monitor generation with runtime verification."""
        # Get configuration for monitor generation
        rv_config = self.config.get_monitored_operations_config()
        
        # Import runtime verification generator
        from rv_monitor_generator.runtime_verification_generator import RuntimeVerificationGenerator
        
        self.logger.info(f"Using specs directory: {rv_config.mop_specs_dir}")
        
        # Initialize and run generator
        generator = RuntimeVerificationGenerator(rv_config)
        monitor_output_dir = os.path.join(self.config.output_dir, "mop_out")
        
        success = generator.generate_monitors(monitor_output_dir)
        if not success:
            raise RVExperimentError("Monitor generation failed - no artifacts produced")
            
        # Publish event for coordination
        self.event_bus.publish_analysis_event(
            EventType.STATIC_ANALYSIS_COMPLETED,
            data={"phase": "monitor_generation", "mode": "full"},
            source="PreProcessor"
        )

    def _generate_monitors_fallback(self):
        """Fallback monitor generation (skip runtime verification)."""
        self.execution_mode = "fallback"
        self.fallback_reasons.append("Monitor generator module unavailable")
        
        self.logger.warning("🔄 FALLBACK: Continuing without runtime verification monitors")
        self.logger.warning("   Experiment will use original APKs without monitoring")
        
        # Ensure output directory exists for consistency
        monitor_output_dir = os.path.join(self.config.output_dir, "mop_out")
        os.makedirs(monitor_output_dir, exist_ok=True)

    @ErrorHandler.handle_errors(
        component="PreProcessor", 
        phase="apk_instrumentation"
    )
    def _instrument_apks(self, force_fallback: bool = False):
        """
        Instrument APKs with runtime verification monitors.
        
        Args:
            force_fallback: Force fallback mode (reuse existing APKs)
        """
        with self.logger.with_context(phase="instrument_apks"):
            self.logger.info(LOG_START.format(phase="APK instrumentation"))

            if force_fallback:
                self._instrument_apks_fallback()
                return

            # Try full instrumentation first
            try:
                self._instrument_apks_full()
                self.logger.info("✅ APK instrumentation completed in FULL mode")
                if self.execution_mode == "unknown":
                    self.execution_mode = "full"
                    
            except ImportError as e:
                self.logger.warning(f"Instrumentation module unavailable: {e}")
                self._instrument_apks_fallback()
                
            except Exception as e:
                self.logger.error(f"APK instrumentation failed: {e}")
                self._instrument_apks_fallback()

            self.logger.info(LOG_COMPLETE.format(phase="APK instrumentation"))

    def _instrument_apks_full(self):
        """Execute full APK instrumentation with monitors."""
        # Get instrumentation configuration
        instrumentation_config = self.config.get_rv_instrumentation_config()
        print(f"*** instrumentation_config={instrumentation_config}")
        
        # Import instrumentation module
        from rv_instrumentation.rvandroid import RVInstrumentation
        
        # Initialize instrumentation
        instrumenter = RVInstrumentation(instrumentation_config)
        
        # Get APK list for instrumentation
        apk_list = self.config.get_apk_list()
        if not apk_list:
            raise RVExperimentError("No APKs configured for instrumentation")
            
        self.logger.info(f"Instrumenting {len(apk_list)} APKs with runtime verification")
        
        # Execute instrumentation
        instrumented_dir = os.path.join(self.config.output_dir, "out")
        monitors_dir = os.path.join(self.config.output_dir, "mop_out")

        print(f">>> instrumented_dir={instrumented_dir}")
        
        success = instrumenter.instrument_apks(
            apks_dir=self.config.apk_dir,
            results_dir=instrumented_dir
        )
        
        if not success:
            raise RVExperimentError("APK instrumentation failed")

        # # Publish event for coordination
        # self.event_bus.publish_analysis_event(
        #     EventType.STATIC_ANALYSIS_COMPLETED,
        #     data={"phase": "apk_instrumentation", "mode": "full"},
        #     source="PreProcessor"
        # )

    def _instrument_apks_fallback(self):
        """Fallback APK instrumentation (reuse existing or copy original)."""
        if self.execution_mode != "fallback":
            self.execution_mode = "fallback"
            
        self.fallback_reasons.append("Reusing existing instrumented APKs")
        
        self.logger.warning("🔄 FALLBACK: Reusing existing instrumented APKs")
        
        # Check for existing instrumented APKs
        instrumented_dir = os.path.join(self.config.output_dir, "out")
        if os.path.exists(instrumented_dir) and os.listdir(instrumented_dir):
            self.logger.info(f"Found existing instrumented APKs in: {instrumented_dir}")
            return
            
        # Copy original APKs if no instrumented versions exist
        self.logger.warning("   No instrumented APKs found, copying original APKs")
        os.makedirs(instrumented_dir, exist_ok=True)
        
        apk_list = self.config.get_apk_list()
        for apk_path in apk_list:
            apk_name = os.path.basename(apk_path)
            dest_path = os.path.join(instrumented_dir, apk_name)
            if not os.path.exists(dest_path):
                import shutil
                shutil.copy2(apk_path, dest_path)
                self.logger.debug(f"Copied {apk_name} to instrumented directory")

    @ErrorHandler.handle_errors(
        component="PreProcessor",
        phase="static_analysis"
    )
    def _run_static_analysis(self, force_fallback: bool = False):
        """
        Run static analysis with automatic fallback.
        
        Args:
            force_fallback: Force fallback mode (skip static analysis)
        """
        with self.logger.with_context(phase="static_analysis"):
            self.logger.info(LOG_START.format(phase="static analysis"))

            if force_fallback:
                self._run_static_analysis_fallback()
                return

            # Try full static analysis first
            try:
                self._run_static_analysis_full()
                self.logger.info("✅ Static analysis completed in FULL mode")
                if self.execution_mode == "unknown":
                    self.execution_mode = "full"
                    
            except ImportError as e:
                self.logger.warning(f"Static analysis module unavailable: {e}")
                self._run_static_analysis_fallback()
                
            except Exception as e:
                self.logger.error(f"Static analysis failed: {e}")
                self._run_static_analysis_fallback()

            self.logger.info(LOG_COMPLETE.format(phase="static analysis"))

    def _run_static_analysis_full(self):
        """Execute full static analysis with all tools."""
        # Get static analysis configuration
        static_config = self.config.get_static_analysis_config()
        
        # Import static analysis module
        from rv_static_analysis.analysis.static.static_analysis import StaticAnalyzer
        
        # Get target APKs (prefer instrumented, fallback to original)
        target_apks = self._get_target_apks_for_analysis()
        if not target_apks:
            raise RVExperimentError("No APKs available for static analysis")
            
        self.logger.info(f"Running static analysis on {len(target_apks)} APKs")
        
        # Execute static analysis
        for apk_path in target_apks:
            apk_name = os.path.basename(apk_path)
            self.logger.info(f"Analyzing: {apk_name}")
            
            # Create App instance and analyzer
            app = App(app_path=apk_path)
            apk_output_dir = os.path.join(self.config.output_dir, apk_name)
            
            analyzer = StaticAnalyzer(
                app=app,
                config=static_config,
                output_dir=apk_output_dir
            )
            
            # Execute analysis
            result = analyzer.analyze()
            if not result.success:
                self.logger.warning(f"Static analysis failed for: {apk_name}")
            else:
                self.logger.info(f"Static analysis completed for: {apk_name}")

        # Publish event for coordination
        self.event_bus.publish_analysis_event(
            EventType.STATIC_ANALYSIS_COMPLETED,
            data={"phase": "static_analysis", "mode": "full"},
            source="PreProcessor"
        )

    def _run_static_analysis_fallback(self):
        """Fallback static analysis (skip analysis)."""
        if self.execution_mode != "fallback":
            self.execution_mode = "fallback"
            
        self.fallback_reasons.append("Static analysis module unavailable")
        
        self.logger.warning("🔄 FALLBACK: Skipping static analysis")
        self.logger.warning("   Coverage analysis will use execution logs only")

    def _get_target_apks_for_analysis(self) -> List[str]:
        """Get APKs for static analysis (prefer instrumented over original)."""
        target_apks = []
        
        # Try instrumented APKs first
        instrumented_dir = os.path.join(self.config.output_dir, "out")
        if os.path.exists(instrumented_dir):
            for file in os.listdir(instrumented_dir):
                if file.endswith(EXTENSION_APK):
                    target_apks.append(os.path.join(instrumented_dir, file))
        
        # Fallback to original APKs if no instrumented found
        if not target_apks:
            original_apks = self.config.get_apk_list()
            target_apks.extend(original_apks)
            
        return target_apks

    def get_instrumented_apks(self) -> List[App]:
        """
        Get list of instrumented APKs for execution.
        
        Returns:
            List of App objects for instrumented APKs
        """
        instrumented_apps = []
        instrumented_dir = os.path.join(self.config.output_dir, "out")

        print(f"*** instrumented_dir={instrumented_dir}")
        
        if os.path.exists(instrumented_dir):
            for file in os.listdir(instrumented_dir):
                if file.endswith(EXTENSION_APK):
                    app_path = os.path.join(instrumented_dir, file)
                    app = App(app_path=app_path)
                    instrumented_apps.append(app)
                    self.logger.debug(f"Found instrumented APK: {file}")
                    print(f">>>> Found instrumented APK: {file}")

        if not instrumented_apps:
            self.logger.warning("No instrumented APKs found, using original APKs")
            # Fallback to original APKs
            for apk_path in self.config.get_apk_list():
                app = App(app_path=apk_path)
                instrumented_apps.append(app)

        return instrumented_apps

    def _log_execution_summary(self):
        """Log summary of pre-processing execution."""
        if self.execution_mode == "full":
            self.logger.info("🟢 PRE-PROCESSING COMPLETED in FULL mode")
            self.logger.info("   Runtime verification enabled with all features")
        elif self.execution_mode == "fallback":
            self.logger.warning("🟡 PRE-PROCESSING COMPLETED in FALLBACK mode")
            self.logger.warning(f"   Degraded functionality - {len(self.fallback_reasons)} fallback scenarios:")
            for reason in self.fallback_reasons:
                self.logger.warning(f"   • {reason}")
        elif self.execution_mode == "forced_fallback":
            self.logger.warning("🟡 PRE-PROCESSING COMPLETED in FORCED FALLBACK mode")
            self.logger.warning("   Fallback mode explicitly requested by configuration")
        else:
            self.logger.info("ℹ️  PRE-PROCESSING COMPLETED")

    # Compatibility methods for existing interfaces
    def execute_monitor_generation(self, force_execution: bool = False):
        """Execute monitor generation phase independently."""
        self._generate_monitors(force_fallback=False)
        
    def execute_apk_instrumentation(self, force_execution: bool = False):
        """Execute APK instrumentation phase independently."""
        self._instrument_apks(force_fallback=False)
        
    def execute_static_analysis(self, force_execution: bool = False, target_apks: Optional[List[str]] = None):
        """Execute static analysis phase independently."""
        self._run_static_analysis(force_fallback=False)