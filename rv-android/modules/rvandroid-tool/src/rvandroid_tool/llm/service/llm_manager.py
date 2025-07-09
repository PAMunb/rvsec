"""
LLM Manager Service for Monitored Operations Testing

### Architectural Overview:
This module provides a modern LLM management service that integrates with the simplified
LLMConfig system for monitored operations testing. It manages LLM instances, generation,
and performance monitoring using clean, stateless operations.

### Key Architectural Decisions:
- **Modern Configuration**: Uses LLMConfig instead of legacy ComponentConfigurator
- **Factory Integration**: Uses LLMServiceFactory for all object creation
- **Performance Monitoring**: Comprehensive metrics tracking for LLM operations
- **Error Handling**: Robust error handling using rv-android-core decorators
- **Event Integration**: Publishes events for LLM lifecycle and operations

### Role in the System:
- Primary interface for language model interactions in monitored operations testing
- Manages LLM lifecycle with lazy initialization and proper cleanup
- Provides performance tracking and metrics collection
- Centralizes LLM configuration and instance management
- Integrates with the event system for monitoring and debugging

### Design Patterns:
- **Facade Pattern**: Provides simplified interface to complex LLM operations
- **Lazy Initialization**: Creates LLM instances only when needed
- **Decorator Pattern**: Uses ErrorHandler for comprehensive error management
- **Observer Pattern**: Publishes events for LLM operations and lifecycle
"""

import time
from typing import List, Dict, Optional, Any

from rv_android_core.event.bus import EventBus, EventType, EventChannel
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.performance.performance_monitor import PerformanceMonitor
from rv_llm.config.llm_config import LLMConfig
from rv_llm.factories import LLMComponentFactory
from rv_llm.llm.data_structures import LLMMessage, LLMResponse
from rv_llm.llm.language_model import LanguageModel


class LLMManager:
    """
    Modern LLM Manager for monitored operations testing.
    
    ### Architectural Overview:
    This manager provides a clean, modern interface for LLM interactions using the
    simplified LLMConfig system. It handles LLM lifecycle management, performance
    monitoring, and error handling for monitored operations testing scenarios.
    
    ### Key Features:
    - Clean LLMConfig-based configuration without legacy dependencies
    - Lazy initialization of LLM instances for optimal resource usage
    - Comprehensive performance monitoring and metrics collection
    - Robust error handling with detailed context and recovery
    - Event publishing for system monitoring and debugging
    - Type-safe interfaces throughout the component
    
    ### Integration Strategy:
    - Uses LLMComponentFactory for all LLM instance creation
    - Integrates with rv-android-core utilities for logging and error handling
    - Publishes events through EventBus for system-wide monitoring
    - Provides metrics through PerformanceMonitor for analysis
    
    ### Performance Considerations:
    - Lazy initialization minimizes resource usage
    - Metrics collection for performance analysis and optimization
    - Proper cleanup procedures for resource management
    - Efficient event publishing for monitoring without performance impact
    """

    @ErrorHandler.handle_errors(
        component="LLMManager",
        operation="initialization"
    )
    def __init__(self, config: LLMConfig, **model_kwargs):
        """
        Initialize the modern LLM manager for monitored operations testing.
        
        ### Initialization Strategy:
        - Validates LLMConfig before proceeding with initialization
        - Sets up logging and performance monitoring infrastructure
        - Prepares for lazy LLM instance creation when needed
        - Configures event publishing for lifecycle monitoring
        
        Args:
            config: LLMConfig instance with validated configuration
            **model_kwargs: Additional model-specific arguments for customization
            
        Raises:
            ValueError: If configuration is invalid or incomplete
            RuntimeError: If initialization of supporting services fails
        """
        # Validate configuration before proceeding
        is_valid, errors = config.validate()
        if not is_valid:
            error_msg = f"Invalid LLM configuration: {', '.join(errors)}"
            raise ValueError(error_msg)

        self.config = config
        self.model_kwargs = model_kwargs

        # Get system services
        self.event_bus = EventBus.get_instance()
        self.performance_monitor = PerformanceMonitor.get_instance()
        logging_manager = LoggingManager.get_instance()

        # Configure logging with component context
        self.logger = logging_manager.get_logger(
            "llm.service.llm_manager",
            {CONTEXT_COMPONENT: "LLMManager"}
        )

        # Initialize LLM lazily - only when needed
        self.llm: Optional[LanguageModel] = None

        self.logger.info(
            f"LLM Manager initialized: backend={self.config.llm_type}, "
            f"model={self.config.model}, strategy={self.config.strategy_type}"
        )

    @ErrorHandler.handle_errors(
        component="LLMManager",
        operation="llm_initialization"
    )
    def _initialize_llm(self) -> None:
        """
        Initialize the LLM instance using modern factory pattern.
        
        ### Initialization Strategy:
        - Uses LLMComponentFactory for clean, type-safe LLM creation
        - Applies configuration validation before instance creation
        - Publishes initialization events for system monitoring
        - Handles initialization failures with proper error reporting
        
        Raises:
            RuntimeError: If LLM initialization fails
            ImportError: If required LLM backend modules are not available
        """
        if self.llm is not None:
            return

        self.logger.info(f"Initializing {self.config.llm_type} LLM: {self.config.model}")

        try:
            # Create LLM instance using modern factory
            self.llm = LLMComponentFactory.create_llm(self.config)

            self.logger.info(f"Successfully initialized {self.config.llm_type} LLM")

            # Publish LLM initialization event
            self.event_bus.publish_task_event(
                EventType.COVERAGE_TRACKING_STARTED,  # Reusing existing event type
                task_id="llm_manager",
                details={
                    "llm_type": self.config.llm_type,
                    "model": self.config.model,
                    "strategy_type": self.config.strategy_type,
                    "max_tokens": self.config.max_tokens
                },
                source="LLMManager",
                channel=EventChannel.LIFECYCLE
            )

        except ImportError as e:
            error_msg = f"Failed to import required modules for {self.config.llm_type}: {e}"
            self.logger.error(error_msg)

            # Publish error event
            self.event_bus.publish_error_event(
                e,
                {
                    "llm_type": self.config.llm_type,
                    "model": self.config.model,
                    "operation": "llm_initialization"
                }
            )

            raise RuntimeError(error_msg) from e

        except Exception as e:
            error_msg = f"Failed to initialize {self.config.llm_type} LLM: {e}"
            self.logger.error(error_msg)

            # Publish error event
            self.event_bus.publish_error_event(
                e,
                {
                    "llm_type": self.config.llm_type,
                    "model": self.config.model,
                    "operation": "llm_initialization"
                }
            )

            raise RuntimeError(error_msg) from e

    @ErrorHandler.handle_errors(
        component="LLMManager",
        operation="text_generation"
    )
    def generate(self, messages: List[LLMMessage], config_override: Optional[LLMConfig] = None) -> LLMResponse:
        """
        Generate text using the LLM with comprehensive performance tracking.
        
        ### Generation Strategy:
        - Ensures LLM is initialized before generation
        - Applies configuration overrides if provided
        - Tracks performance metrics for analysis and optimization
        - Provides comprehensive error handling and recovery
        - Publishes events for monitoring and debugging
        
        Args:
            messages: List of LLMMessage objects for generation
            config_override: Optional configuration overrides for this generation
            
        Returns:
            LLMResponse with generated text and metadata
            
        Raises:
            RuntimeError: If generation fails
            ValueError: If messages are invalid or empty
        """
        if not messages:
            raise ValueError("Messages list cannot be empty for generation")

        # Apply configuration override if provided
        effective_config = config_override if config_override else self.config

        # Validate override configuration if provided
        if config_override:
            is_valid, errors = config_override.validate()
            if not is_valid:
                raise ValueError(f"Invalid override configuration: {', '.join(errors)}")

        context = {
            "llm_type": effective_config.llm_type,
            "model": effective_config.model,
            "strategy_type": effective_config.strategy_type,
            "parser_type": effective_config.parser_type,
            "generation_id": str(time.time())
        }

        # Initialize LLM if needed
        self._initialize_llm()

        # Track input metrics
        total_input_chars = sum(msg.total_chars() for msg in messages)
        self.performance_monitor.record_metric(
            name="llm_input_chars",
            value=total_input_chars,
            unit="chars",
            context=context
        )

        # Log message details for debugging
        for i, message in enumerate(messages):
            self.logger.debug(f"Message {i + 1} - Role: {message.role}")
            for j, content in enumerate(message.content):
                self.logger.debug(f"  Content {j + 1}: {str(content)[:100]}...")

        # Perform generation with timing
        start_time = time.time()
        try:
            # Convert LLMConfig to parameters for LLM generation
            llm_params = effective_config.get_llm_parameters()
            response: LLMResponse = self.llm.generate(messages, llm_params)
            elapsed_time = time.time() - start_time

            # Log successful generation
            self.logger.info(
                f"LLM generation completed in {elapsed_time:.2f}s "
                f"({len(response.content)} tokens)"
            )

            # Record response metrics
            self._record_response_metrics(response, context, elapsed_time)

            return response

        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"Text generation failed after {elapsed_time:.2f}s: {e}"
            self.logger.error(error_msg)

            # Record error metrics
            self.performance_monitor.record_metric(
                name="llm_generation_error",
                value=1,
                unit="error",
                context={**context, "error": str(e), "elapsed_time": elapsed_time}
            )

            # Publish error event
            self.event_bus.publish_error_event(
                e,
                {**context, "elapsed_time": elapsed_time, "operation": "text_generation"}
            )

            raise RuntimeError(error_msg) from e

    @ErrorHandler.handle_errors(
        component="LLMManager",
        operation="configuration_update"
    )
    def update_configuration(self, new_config: LLMConfig) -> None:
        """
        Update the LLM configuration with validation and cleanup.
        
        ### Update Strategy:
        - Validates new configuration before applying changes
        - Determines if LLM instance needs to be recreated
        - Performs proper cleanup of existing resources if needed
        - Publishes configuration change events for monitoring
        
        Args:
            new_config: New LLMConfig instance with updated parameters
            
        Raises:
            ValueError: If new configuration is invalid
            
        Note:
            If the LLM type or model changes, the existing LLM instance will be
            cleaned up and a new one will be created on the next generation request.
        """
        # Validate new configuration
        is_valid, errors = new_config.validate()
        if not is_valid:
            raise ValueError(f"Invalid configuration update: {', '.join(errors)}")

        # Check if LLM instance needs to be recreated
        llm_changed = (
                new_config.llm_type != self.config.llm_type or
                new_config.model != self.config.model
        )

        old_config = self.config
        self.config = new_config

        # Clean up existing LLM if it needs to be recreated
        if llm_changed and self.llm:
            self.logger.info("LLM configuration changed, cleaning up existing instance")
            self.cleanup()

        self.logger.info(
            f"Updated LLM configuration: backend={self.config.llm_type}, "
            f"model={self.config.model}, strategy={self.config.strategy_type}"
        )

        # Publish configuration update event
        self.event_bus.publish_task_event(
            EventType.COVERAGE_TRACKING_STARTED,  # Reusing existing event type
            task_id="llm_manager",
            details={
                "old_config": {
                    "llm_type": old_config.llm_type,
                    "model": old_config.model,
                    "strategy_type": old_config.strategy_type
                },
                "new_config": {
                    "llm_type": new_config.llm_type,
                    "model": new_config.model,
                    "strategy_type": new_config.strategy_type
                },
                "llm_recreated": llm_changed
            },
            source="LLMManager",
            channel=EventChannel.LIFECYCLE
        )

    def get_configuration(self) -> LLMConfig:
        """
        Get the current LLM configuration.
        
        Returns:
            Current LLMConfig instance
        """
        return self.config

    @ErrorHandler.handle_errors(
        component="LLMManager",
        operation="cleanup"
    )
    def cleanup(self) -> None:
        """
        Clean up LLM resources when they're no longer needed.
        
        ### Cleanup Strategy:
        - Safely disposes of LLM instance resources
        - Handles cleanup errors gracefully without affecting system
        - Logs cleanup operations for monitoring
        - Publishes cleanup events for system awareness
        """
        if self.llm:
            try:
                if hasattr(self.llm, 'cleanup'):
                    self.llm.cleanup()
                self.llm = None
                self.logger.info("Successfully cleaned up LLM resources")

                # Publish cleanup event
                self.event_bus.publish_task_event(
                    EventType.COVERAGE_TRACKING_STARTED,  # Reusing existing event type
                    task_id="llm_manager",
                    details={
                        "operation": "llm_cleanup",
                        "llm_type": self.config.llm_type,
                        "model": self.config.model
                    },
                    source="LLMManager",
                    channel=EventChannel.LIFECYCLE
                )

            except Exception as e:
                self.logger.warning(f"Error during LLM cleanup: {e}")

    def is_initialized(self) -> bool:
        """
        Check if the LLM has been initialized.
        
        Returns:
            True if LLM instance exists, False otherwise
        """
        return self.llm is not None

    def _record_response_metrics(self, response: LLMResponse, context: Dict[str, Any], elapsed_time: float) -> None:
        """
        Record comprehensive response metrics for performance analysis.
        
        ### Metrics Strategy:
        - Records both content and performance metrics
        - Includes timing information for latency analysis
        - Provides context for metric correlation and analysis
        - Enables performance optimization and monitoring
        
        Args:
            response: LLMResponse object with generation results
            context: Context dictionary for metric correlation
            elapsed_time: Total generation time in seconds
        """
        # Response content metrics
        self.performance_monitor.record_metric(
            name="llm_response_chars",
            value=response.total_chars(),
            unit="chars",
            context=context
        )

        # Performance timing metrics
        self.performance_monitor.record_metric(
            name="llm_generation_time",
            value=elapsed_time,
            unit="seconds",
            context=context
        )

        # Token-based metrics if available
        if hasattr(response, 'input_tokens') and response.input_tokens:
            self.performance_monitor.record_metric(
                name="llm_input_tokens",
                value=response.input_tokens,
                unit="tokens",
                context=context
            )

        if hasattr(response, 'output_tokens') and response.output_tokens:
            self.performance_monitor.record_metric(
                name="llm_output_tokens",
                value=response.output_tokens,
                unit="tokens",
                context=context
            )

        # Duration-based metrics if available
        if hasattr(response, 'total_duration') and response.total_duration:
            self.performance_monitor.record_metric(
                name="llm_total_duration",
                value=response.total_duration,
                unit="nanoseconds",
                context=context
            )

        if hasattr(response, 'load_duration') and response.load_duration:
            self.performance_monitor.record_metric(
                name="llm_load_duration",
                value=response.load_duration,
                unit="nanoseconds",
                context=context
            )
