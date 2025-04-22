# rvandroid/llm/service/llm_manager.py
"""
LLM Manager service for handling language model interactions.
Manages LLM instances, generation, and performance monitoring.
"""
import time
from typing import List, Dict, Optional, Any, Union

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.llm import MCPMessage
from rvandroid.llm.language_model import LanguageModel
from rvandroid.llm.llm_config import LLMConfiguration
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.performance_monitor import PerformanceMonitor
from rvandroid.llm.data_structures import MCPMessage

class LLMManager:
    """
    Manages language model instances and handles interactions with the LLM.

    ### Architectural Decisions:
    - Encapsulates LLM instantiation and lifecycle management
    - Integrates with the enhanced configuration system
    - Handles model-specific configuration and error handling
    - Provides a consistent interface for LLM interactions
    - Implements performance monitoring for LLM operations
    
    ### Role in the System:
    - Acts as the primary interface for language model interactions
    - Manages the lifecycle of language model instances
    - Provides error handling and recovery for LLM operations
    - Tracks performance metrics for language model usage
    - Centralizes LLM configuration and instance management
    """

    # TODO rever parametros do construtor (Union[ComponentConfigurator, LLMConfiguration])
    # TODO usar error handler
    # TODO usar o event bus direito
    def __init__(self, config: Union[ComponentConfigurator, LLMConfiguration], **model_kwargs):
        """
        Initialize the LLM manager.

        Args:
            config: Component configurator or LLMConfiguration instance
            **model_kwargs: Additional model-specific arguments
        """
        # Get system services
        self.event_bus = EventBus.get_instance()
        self.performance_monitor = PerformanceMonitor.get_instance()
        logging_manager = LoggingManager.get_instance()

        # Configure logging
        self.logger = logging_manager.get_logger(
            "llm.service.llm_manager",
            {CONTEXT_COMPONENT: "LLMManager"}
        )

        # Handle different configuration types
        self._set_configurator(config)

        self.model_kwargs = {**self.llm_config.get_model_kwargs(), **model_kwargs}

        # Initialize LLM lazily - only when needed
        self.llm: Optional[LanguageModel] = None

        self.logger.info(f"LLM Manager initialized with model_type={self.model_type}, model_name={self.model_name}")

    # TODO
    def _set_configurator(self, config: Union[ComponentConfigurator, LLMConfiguration]) -> None:
        # Handle different configuration types
        if isinstance(config, LLMConfiguration):
            self.llm_config = config
            self.configurator = None
        else:
            self.configurator = config
            self.llm_config = config.llm_config

        # Store configuration
        self.model_type = self.llm_config.get_model_type()
        self.model_name = self.llm_config.get_model_name()
        self.max_tokens = self.llm_config.get_max_tokens()

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
            # Create the LLM instance
            if self.configurator:
                # Use configurator-based creation if available
                self.llm = self.configurator.create_llm()
            else:
                # Create a temporary configurator to create the LLM
                temp_configurator = ComponentConfigurator()
                temp_configurator.set_llm(
                    self.model_type, 
                    self.model_name, 
                    **self.model_kwargs
                )
                self._set_configurator(temp_configurator)
                self.llm = temp_configurator.create_llm()
                
            self.logger.info(f"Successfully initialized {self.model_type} model")

            # Publish LLM initialization event
            self.event_bus.publish_analysis_event(
                # TODO: Use a more specific event type
                EventType.COVERAGE_TRACKING_STARTED,  # Reusing event type as "MODEL_INITIALIZED" doesn't exist
                data={
                    "model_type": self.model_type, 
                    "model_name": self.model_name,
                    "max_tokens": self.max_tokens
                },
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

    def generate(self, messages: List[MCPMessage], config: Optional[ComponentConfigurator]) -> MCPMessage:
        """
        Generate text using the LLM with performance tracking.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            generation_config: Optional configuration overrides for this generation

        Returns:
            Generated text response

        Raises:
            RuntimeError: If generation fails
        """
        if config:
            self._set_configurator(config)

        context = {
            "model_type": self.model_type,
            "model_name": self.model_name,
            "strategy": str(config.strategy_class),
            "parser": str(config.parser_class),
            "visitor": str(config.visitor_class)
        }

        # Initialize if needed
        self._initialize_llm()

        # Tracking metrics for total token count
        total_input_chars = sum(msg.total_chars() for msg in messages)
        self.performance_monitor.record_metric(
            name="llm_input_chars",
            value=total_input_chars,
            unit="chars",
            context=context
        )

        # Perform generation with timing
        start_time = time.time()
        try:
            response: MCPMessage = self.llm.generate_sync(messages, config.llm_config)
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
                value=response.total_chars(),
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

    def update_configuration(self, config: Union[Dict[str, Any], LLMConfiguration]) -> None:
        """
        Update the LLM configuration.
        
        Args:
            config: New configuration values or LLMConfiguration instance
            
        Note:
            If the model type or name changes, the existing LLM instance will be
            cleaned up and a new one will be created on the next generation request.
        """
        if isinstance(config, LLMConfiguration):
            new_config = config
        else:
            # Create a new configuration with updated values
            new_config = LLMConfiguration.from_dict({
                **self.llm_config.to_dict(),
                **config
            })
        
        # Check if model changed
        model_changed = (
            new_config.get_model_type() != self.model_type or
            new_config.get_model_name() != self.model_name
        )
        
        # Update configuration
        self.llm_config = new_config
        self.model_type = new_config.get_model_type()
        self.model_name = new_config.get_model_name()
        self.max_tokens = new_config.get_max_tokens()
        self.model_kwargs = new_config.get_model_kwargs()
        
        # Clean up existing LLM if model changed
        if model_changed and self.llm:
            self.cleanup()
            
        self.logger.info(f"Updated LLM configuration: model_type={self.model_type}, model_name={self.model_name}")

    def get_configuration(self) -> LLMConfiguration:
        """
        Get the current LLM configuration.
        
        Returns:
            Current LLMConfiguration instance
        """
        return self.llm_config

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

    def is_initialized(self) -> bool:
        """
        Check if the LLM has been initialized.
        
        Returns:
            True if initialized, False otherwise
        """
        return self.llm is not None