# rvandroid/llm/service/llm_manager.py
import time
from typing import List, Dict, Optional

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.experiment.event_system import EventBus, EventType
from rvandroid.llm.llm import LanguageModel
from rvandroid.util.logging_manager import LoggingManager
from rvandroid.util.performance_monitor import PerformanceMonitor


class LLMManager:
    """
    Manages language model instances and handles interactions with the LLM.

    ### Architectural Decisions:
    - Encapsulates LLM instantiation and lifecycle management
    - Handles model-specific configuration and error handling
    - Provides a consistent interface for LLM interactions
    - Implements performance monitoring for LLM operations

    ### Role in the System:
    - Manages the lifecycle of language model instances
    - Handles token limits and generation parameters
    - Provides error handling and recovery for LLM interactions
    - Reports performance metrics for LLM operations
    """

    def __init__(self, config: ComponentConfigurator, **model_kwargs):
        """
        Initialize the LLM manager.

        Args:
            config: Component configurator for LLM configuration
            **model_kwargs: Additional model-specific arguments
        """
        # Get system services
        self.event_bus = EventBus.get_instance()
        self.performance_monitor = PerformanceMonitor.get_instance()
        logging_manager = LoggingManager.get_instance()

        # Configure logging
        self.logger = logging_manager.get_logger(
            "llm.service.llm_manager",
            {LoggingManager.CONTEXT_COMPONENT: "LLMManager"}
        )

        # Store configuration
        self.config = config
        self.model_type = config.llm_config.get_model_type()
        self.model_name = config.llm_config.get_model_name()
        self.max_tokens = model_kwargs.pop("max_tokens", 800)
        self.model_kwargs = model_kwargs

        # Initialize LLM lazily - only when needed
        self.llm: Optional[LanguageModel] = None

        self.logger.info(f"LLM Manager initialized with model_type={self.model_type}, model_name={self.model_name}")

    def _initialize_llm(self) -> None:
        """
        Initialize the LLM instance if it doesn't already exist.

        Raises:
            RuntimeError: If LLM initialization fails
        """
        if self.llm is not None:
            return

        self.logger.info(f"Initializing {self.model_type} model: {self.model_name}")

        try:
            # Use the configurator to create the LLM instance
            self.llm = self.config.create_llm()
            self.logger.info(f"Successfully initialized {self.model_type} model")

            # Publish LLM initialization event
            self.event_bus.publish_analysis_event(
                EventType.COVERAGE_TRACKING_STARTED,  # Reusing event type as "MODEL_INITIALIZED" doesn't exist
                data={"model_type": self.model_type, "model_name": self.model_name},
                source="LLMManager"
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize LLM: {e}", exc_info=True)

            # Publish error event
            self.event_bus.publish_error_event(
                e,
                {"model_type": self.model_type, "model_name": self.model_name}
            )

            raise RuntimeError(f"Could not initialize {self.model_type} model: {str(e)}")

    def generate(self, messages: List[Dict[str, str]]) -> str:
        """
        Generate text using the LLM with performance tracking.

        Args:
            messages: List of message dictionaries with 'role' and 'content'

        Returns:
            Generated text response

        Raises:
            RuntimeError: If generation fails
        """
        context = {
            "model_type": self.model_type,
            "model_name": self.model_name
        }

        # Initialize if needed
        self._initialize_llm()

        # Tracking metrics for total token count
        total_input_chars = sum(len(msg["content"]) for msg in messages)
        self.performance_monitor.record_metric(
            name="llm_input_chars",
            value=total_input_chars,
            unit="chars",
            context=context
        )

        # Perform generation with timing
        start_time = time.time()
        try:
            response = self.llm.generate(messages, max_new_tokens=self.max_tokens)
            elapsed_time = time.time() - start_time

            # Log performance metrics
            self.logger.info(f"LLM response received in {elapsed_time:.2f} seconds")
            self.performance_monitor.record_metric(
                name="llm_response_time",
                value=elapsed_time,
                unit="s",
                context=context
            )
            self.performance_monitor.record_metric(
                name="llm_response_length",
                value=len(response),
                unit="chars",
                context=context
            )

            return response

        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(f"Error generating text with {self.model_type}: {e}", exc_info=True)

            # Record error metrics
            self.performance_monitor.record_metric(
                name="llm_error",
                value=1,
                unit="error",
                context={**context, "error": str(e), "elapsed": elapsed_time}
            )

            # Publish error event
            self.event_bus.publish_error_event(
                e,
                {**context, "elapsed": elapsed_time}
            )

            raise RuntimeError(f"Text generation failed: {str(e)}")

    def cleanup(self) -> None:
        """
        Clean up LLM resources when they're no longer needed.
        """
        if self.llm:
            try:
                self.llm.clean()
                self.llm = None
                self.logger.info("Cleaned up LLM resources")
            except Exception as e:
                self.logger.warning(f"Error cleaning up LLM: {e}")
               