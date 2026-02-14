# rv_experiment/experiment/workflow/post_processor.py
"""
Clean post-processor component for RV-Android experiments.

This module provides minimal post-processing functionality focused only on
basic experiment diagnostics. All result processing is handled by rv-platform.
"""
import os

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE
from rv_android_core.util.logging.manager import LoggingManager
from rv_platform.storage.task_storage import TaskStorage
from rv_experiment.experiment.workflow.result_manager import ResultManager


class PostProcessor:
    """
    Clean post-processor component for basic experiment diagnostics.

    This component handles only basic post-processing functionality focused on
    experiment diagnostics. All CSV and JSON result processing is handled by
    rv-platform's ResultProcessorComponent for proper separation of concerns.

    ### Architectural Role:
    - Provides basic experiment completion diagnostics
    - Generates simple experiment metadata
    - No data processing or result generation

    ### Key Principles:
    - No result processing (delegated to rv-platform)
    - No data access from tasks or storage
    - Only basic diagnostics
    - Clean separation from data processing concerns
    """

    def __init__(self, results_dir: str):
        """
        Initialize the clean post-processor.

        Args:
            results_dir: Directory containing experiment results
        """
        self.results_dir = results_dir
        self.error_handler = ErrorHandler.get_instance()
        
        # Initialize TaskStorage to access tasks for ResultManager
        tasks_file = os.path.join(results_dir, "tasks.json")
        self.task_storage = TaskStorage(tasks_file)
        self.task_storage.load()

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
        Process experiment completion with basic diagnostics.
        
        This method handles only basic post-processing diagnostics.
        All result processing is handled by rv-platform automatically.
        """
        with self.logger.with_context(phase="post_processing"):
            self.logger.info(LOG_START.format(phase="experiment post-processing"))

            # Generate instrumentation errors JSON using ResultManager
            self._generate_instrumentation_errors()
            
            # Basic experiment completion diagnostics
            self._generate_completion_diagnostics()

            self.logger.info(LOG_COMPLETE.format(phase="experiment post-processing"))
            self.logger.info("Post-processing completed")

    def _generate_instrumentation_errors(self):
        """
        Generate instrumentation errors JSON using ResultManager.
        """
        with self.logger.with_context(phase="instrumentation_errors"):
            self.logger.info(LOG_START.format(phase="generating instrumentation errors JSON"))

            try:
                # Create ResultManager and generate instrumentation errors
                result_manager = ResultManager(self.results_dir, self.task_storage)
                result_manager.generate_reports()
                
                self.logger.info(LOG_COMPLETE.format(phase="instrumentation errors JSON generation"))
                
            except Exception as e:
                error_context = {
                    "component": "PostProcessor",
                    "operation": "instrumentation_errors_generation",
                    "results_dir": self.results_dir
                }
                self.error_handler.handle_error(e, error_context)

    def _generate_completion_diagnostics(self):
        """
        Generate basic completion diagnostics for the experiment.
        """
        with self.logger.with_context(phase="completion_diagnostics"):
            self.logger.info(LOG_START.format(phase="generating completion diagnostics"))

            try:
                # Generate basic diagnostic information
                diagnostic_info = {
                    "results_directory": self.results_dir,
                    "completion_timestamp": self._get_current_timestamp(),
                    "post_processing_completed": True
                }

                # Log diagnostic information
                self.logger.info(f"Experiment completion diagnostics: {diagnostic_info}")

                # Save basic completion diagnostics
                diagnostic_path = os.path.join(self.results_dir, "experiment_completion.json")
                self._save_diagnostics(diagnostic_path, diagnostic_info)

            except Exception as e:
                error_context = {
                    "component": "PostProcessor",
                    "operation": "completion_diagnostics",
                    "results_dir": self.results_dir
                }
                self.error_handler.handle_error(e, error_context)

            self.logger.info(LOG_COMPLETE.format(phase="generating completion diagnostics"))

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
            self.logger.info(f"Completion diagnostics saved to {diagnostic_path}")
        except Exception as e:
            self.logger.warning(f"Failed to save completion diagnostics to {diagnostic_path}: {e}")