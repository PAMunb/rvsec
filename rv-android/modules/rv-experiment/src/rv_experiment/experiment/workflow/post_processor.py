# rv_experiment/experiment/workflow/post_processor.py
"""
Simplified post-processor component for RV-Android experiments.

This module provides minimal post-processing functionality focused on
experiment diagnostics and coordination.
"""
import os

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.event import EventBus, EventType


class PostProcessor:
    """
    Simplified post-processor component for RV-Android experiments.

    This component handles only basic post-processing functionality focused on
    experiment diagnostics. CSV and JSON result processing is now handled by
    rv-platform's ResultProcessorComponent for better separation of concerns.

    ### Architectural Role:
    - Handles experiment-level diagnostics and error reporting
    - Coordinates with ResultManager for instrumentation error tracking
    - Provides basic post-experiment analysis capabilities
    - Delegates complex data processing to rv-platform

    ### Key Capabilities:
    - Generate diagnostic information about experiment execution
    - Coordinate with simplified ResultManager for basic reporting
    - Provide experiment completion notifications
    - Handle post-processing error scenarios gracefully

    ### Integration Points:
    - Uses ErrorHandler decorator for error processing
    - Uses LoggingManager for consistent logging with context support
    - Publishes experiment events through EventBus
    - Coordinates with ResultManager for basic experiment metadata
    """

    def __init__(self, results_dir: str, event_bus: EventBus, execution_controller=None, result_manager=None):
        """
        Initialize the simplified post-processor.

        Args:
            results_dir: Directory containing experiment results
            event_bus: Event bus for publishing events
            execution_controller: Reference to the execution controller
            result_manager: Result manager for basic reporting
        """
        self.results_dir = results_dir
        self.event_bus = event_bus
        self.execution_controller = execution_controller
        self.result_manager = result_manager
        self.error_handler = ErrorHandler.get_instance()

        # Configure logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'experiment.workflow.post_processor',
            {
                CONTEXT_COMPONENT: 'PostProcessor'
            }
        )

    def process(self):
        """
        Process experiment results after execution.
        
        This method handles basic post-processing and coordinates with
        ResultManager for instrumentation error tracking. Complex data
        processing is delegated to rv-platform's ResultProcessorComponent.
        """
        with self.logger.with_context(phase="post_processing"):
            self.logger.info(LOG_START.format(phase="experiment post-processing"))

            # Basic experiment diagnostics
            self._generate_experiment_diagnostics()

            # Coordinate with ResultManager for basic reporting
            self._coordinate_basic_reporting()

            self.logger.info(LOG_COMPLETE.format(phase="experiment post-processing"))

            # Notify that post-processing is complete
            self.event_bus.publish_experiment_event(
                EventType.EXPERIMENT_COMPLETED,
                experiment_id="post_processing",
                message="Experiment post-processing completed",
                source="PostProcessor"
            )

    def _generate_experiment_diagnostics(self):
        """
        Generate basic diagnostic information about the experiment execution.
        """
        with self.logger.with_context(phase="diagnostics"):
            self.logger.info(LOG_START.format(phase="generating experiment diagnostics"))

            try:
                # Generate basic diagnostic information
                diagnostic_info = {
                    "results_directory": self.results_dir,
                    "has_result_manager": self.result_manager is not None,
                    "has_execution_controller": self.execution_controller is not None,
                    "diagnostic_timestamp": self._get_current_timestamp()
                }

                # Log diagnostic information
                self.logger.info(f"Experiment diagnostics: {diagnostic_info}")

                # Save basic diagnostics if needed
                diagnostic_path = os.path.join(self.results_dir, "experiment_diagnostics.json")
                self._save_diagnostics(diagnostic_path, diagnostic_info)

            except Exception as e:
                error_context = {
                    "component": "PostProcessor",
                    "operation": "generating_diagnostics",
                    "results_dir": self.results_dir
                }
                self.error_handler.handle_error(e, error_context)

            self.logger.info(LOG_COMPLETE.format(phase="generating experiment diagnostics"))

    def _coordinate_basic_reporting(self):
        """
        Coordinate with ResultManager for basic experiment reporting.
        
        This method delegates to ResultManager for instrumentation error
        tracking and basic metadata generation.
        """
        with self.logger.with_context(phase="basic_reporting"):
            self.logger.info(LOG_START.format(phase="basic experiment reporting"))

            try:
                if self.result_manager:
                    self.logger.info("Coordinating with ResultManager for basic reporting")
                    # ResultManager handles instrumentation errors and basic metadata
                    self.result_manager.generate_reports()
                    self.logger.info("Basic reporting completed by ResultManager")
                else:
                    self.logger.warning("No ResultManager available - basic reporting skipped")

            except Exception as e:
                error_context = {
                    "component": "PostProcessor",
                    "operation": "basic_reporting",
                    "results_dir": self.results_dir,
                    "has_result_manager": self.result_manager is not None
                }
                self.error_handler.handle_error(e, error_context)

            self.logger.info(LOG_COMPLETE.format(phase="basic experiment reporting"))

    def _get_current_timestamp(self) -> str:
        """
        Get current timestamp for diagnostics.
        
        Returns:
            ISO format timestamp string
        """
        from datetime import datetime
        return datetime.now().isoformat()

    def _save_diagnostics(self, diagnostic_path: str, diagnostic_info: dict):
        """
        Save diagnostic information to file.
        
        Args:
            diagnostic_path: Path to save diagnostics
            diagnostic_info: Diagnostic information to save
        """
        import json
        
        try:
            with open(diagnostic_path, 'w', encoding='utf-8') as f:
                json.dump(diagnostic_info, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Experiment diagnostics saved to {diagnostic_path}")
        except Exception as e:
            self.logger.warning(f"Failed to save diagnostics to {diagnostic_path}: {e}")