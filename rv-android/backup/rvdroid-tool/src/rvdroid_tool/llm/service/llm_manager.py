"""
LLM Manager for RVDroid Strategic Guidance

### Architectural Overview:
This module provides LLM management specifically for RVDroid's strategic guidance system.
Unlike action generation systems, this manager focuses on high-level strategic advice
and testing direction, integrating with rv-llm framework components.

### Key Architectural Decisions:
- Uses rv-llm LLMComponentFactory for backend creation
- Implements guidance-specific prompting strategies
- Provides performance monitoring for guidance operations
- Integrates with rv-android-core error handling and logging

### Role in the System:
- Manages LLM lifecycle for guidance requests
- Coordinates with PromptFramework for guidance-specific prompts
- Processes LLM responses into structured guidance decisions
- Provides metrics and monitoring for guidance effectiveness

### Design Patterns:
- Facade Pattern: Simplifies LLM interactions for guidance use cases
- Factory Pattern: Uses LLMComponentFactory for LLM instance creation
- Decorator Pattern: Uses ErrorHandler for comprehensive error management
"""

import time
from typing import List, Dict, Optional, Any

from rv_android_core.event.bus import EventBus, EventType, EventChannel
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVLLMError, RVLLMConfigurationError, RVLLMProviderError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.performance.performance_monitor import PerformanceMonitor
from rv_llm.config.llm_config import LLMConfig
from rv_llm.factories import LLMComponentFactory
from rv_llm.llm.data_structures import LLMMessage, LLMResponse
from rv_llm.llm.language_model import LanguageModel

from rvdroid_tool.constants import PERFORMANCE_METRIC_PREFIX, GUIDANCE_LATENCY_THRESHOLD


class RVDroidLLMManager:
    """
    LLM Manager specialized for RVDroid strategic guidance operations.
    
    ### Architectural Overview:
    This manager provides a clean interface for LLM interactions specifically
    tailored for RVDroid's guidance system. It uses the rv-llm framework
    components while providing guidance-specific functionality.
    
    ### Key Features:
    - Clean LLMConfig-based configuration following rv-llm patterns
    - Lazy initialization of LLM instances for optimal resource usage
    - Comprehensive performance monitoring for guidance operations
    - Robust error handling with detailed context and recovery
    - Event publishing for system monitoring and debugging
    - Guidance-specific response processing and validation
    
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
        component="RVDroidLLMManager",
        operation="initialization"
    )
    def __init__(self, config: LLMConfig, **model_kwargs):
        """
        Initialize the RVDroid LLM manager for strategic guidance operations.
        
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
        self.performance_monitor = PerformanceMonitor.get_instance()
        logging_manager = LoggingManager.get_instance()

        # Configure logging with component context
        self.logger = logging_manager.get_logger(
            "rvdroid_tool.llm.service.llm_manager",
            {CONTEXT_COMPONENT: "RVDroidLLMManager"}
        )

        # Initialize LLM lazily - only when needed
        self.llm: Optional[LanguageModel] = None

        self.logger.info(
            f"RVDroid LLM Manager initialized: backend={self.config.llm_type}, "
            f"model={self.config.model}"
        )

    @ErrorHandler.handle_errors(
        component="RVDroidLLMManager",
        operation="llm_initialization"
    )
    def _initialize_llm(self) -> None:
        """
        Initialize the LLM instance using factory pattern.
        
        ### Initialization Strategy:
        - Uses LLMComponentFactory for clean, type-safe LLM creation
        - Applies configuration validation before instance creation
        - Handles initialization failures with proper error reporting
        
        Raises:
            RuntimeError: If LLM initialization fails
            ImportError: If required LLM backend modules are not available
        """
        if self.is_initialized():
            return

        self.logger.info(f"Initializing {self.config.llm_type} LLM: {self.config.model}")

        try:
            # Create LLM instance using factory
            self.llm = LLMComponentFactory.create_llm(self.config)

            self.logger.info(f"Successfully initialized {self.config.llm_type} LLM")

        except ImportError as e:
            error_msg = f"Failed to import required modules for {self.config.llm_type}: {e}"
            self.logger.error(error_msg)

            raise RVLLMError(error_msg) from e

        except Exception as e:
            error_msg = f"Failed to initialize {self.config.llm_type} LLM: {e}"
            self.logger.error(error_msg)

            raise RVLLMError(error_msg) from e

    @ErrorHandler.handle_errors(
        component="RVDroidLLMManager",
        operation="guidance_generation"
    )
    def generate_guidance(self, messages: List[LLMMessage]) -> LLMResponse:
        """
        Generate strategic guidance using the LLM with comprehensive monitoring.
        
        ### Generation Strategy:
        - Ensures LLM is initialized before generation
        - Tracks performance metrics for guidance analysis and optimization
        - Provides comprehensive error handling and recovery
        - Monitors guidance latency and quality
        
        Args:
            messages: List of LLMMessage objects for guidance generation
            
        Returns:
            LLMResponse with generated guidance and metadata
            
        Raises:
            RuntimeError: If generation fails
            ValueError: If messages are invalid or empty
        """
        if not messages:
            raise ValueError("Messages list cannot be empty for guidance generation")

        context = {
            "llm_type": self.config.llm_type,
            "model": self.config.model,
            "guidance_id": str(time.time()),
            "operation": "guidance_generation"
        }

        # Initialize LLM if needed
        self._initialize_llm()

        # Track input metrics
        total_input_chars = sum(msg.total_chars() for msg in messages)
        self.performance_monitor.record_metric(
            name=f"{PERFORMANCE_METRIC_PREFIX}_guidance_input_chars",
            value=total_input_chars,
            unit="chars",
            context=context
        )

        # Log message details for debugging
        self.logger.debug(f"Generating guidance with {len(messages)} messages")
        for i, message in enumerate(messages):
            self.logger.debug(f"Message {i + 1} - Role: {message.role}")

        # Perform generation with timing
        start_time = time.time()
        try:
            # LLM inference
            response: LLMResponse = self.llm.generate(messages)
            elapsed_time = time.time() - start_time

            # Check latency threshold
            if elapsed_time > GUIDANCE_LATENCY_THRESHOLD:
                self.logger.warning(
                    f"Guidance generation exceeded threshold: {elapsed_time:.2f}s > {GUIDANCE_LATENCY_THRESHOLD}s"
                )

            # Log successful generation
            self.logger.info(f"Guidance generation completed in {elapsed_time:.2f}s")

            # Record response metrics
            self._record_guidance_metrics(response, context, elapsed_time)

            return response

        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"Guidance generation failed after {elapsed_time:.2f}s: {e}"
            self.logger.error(error_msg)

            # Record error metrics
            self.performance_monitor.record_metric(
                name=f"{PERFORMANCE_METRIC_PREFIX}_guidance_error",
                value=1,
                unit="error",
                context={**context, "error": str(e), "elapsed_time": elapsed_time}
            )

            raise RVLLMProviderError(error_msg) from e

    def get_configuration(self) -> LLMConfig:
        """
        Get the current LLM configuration.
        
        Returns:
            Current LLMConfig instance
        """
        return self.config

    @ErrorHandler.handle_errors(
        component="RVDroidLLMManager",
        operation="cleanup"
    )
    def cleanup(self) -> None:
        """
        Clean up LLM resources when they're no longer needed.
        
        ### Cleanup Strategy:
        - Safely disposes of LLM instance resources
        - Handles cleanup errors gracefully without affecting system
        - Logs cleanup operations for monitoring
        """
        if self.llm:
            try:
                if hasattr(self.llm, 'cleanup'):
                    self.llm.cleanup()
                self.llm = None
                self.logger.info("Successfully cleaned up RVDroid LLM resources")

            except Exception as e:
                self.logger.warning(f"Error during RVDroid LLM cleanup: {e}")

    def is_initialized(self) -> bool:
        """
        Check if the LLM has been initialized.
        
        Returns:
            True if LLM instance exists, False otherwise
        """
        return self.llm is not None

    def _record_guidance_metrics(self, response: LLMResponse, context: Dict[str, Any], elapsed_time: float) -> None:
        """
        Record comprehensive guidance metrics for performance analysis.
        
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
            name=f"{PERFORMANCE_METRIC_PREFIX}_guidance_response_chars",
            value=response.total_chars(),
            unit="chars",
            context=context
        )

        # Performance timing metrics
        self.performance_monitor.record_metric(
            name=f"{PERFORMANCE_METRIC_PREFIX}_guidance_time",
            value=elapsed_time,
            unit="seconds",
            context=context
        )

        # Token-based metrics if available
        if hasattr(response, 'input_tokens') and response.input_tokens:
            self.performance_monitor.record_metric(
                name=f"{PERFORMANCE_METRIC_PREFIX}_guidance_input_tokens",
                value=response.input_tokens,
                unit="tokens",
                context=context
            )

        if hasattr(response, 'output_tokens') and response.output_tokens:
            self.performance_monitor.record_metric(
                name=f"{PERFORMANCE_METRIC_PREFIX}_guidance_output_tokens",
                value=response.output_tokens,
                unit="tokens",
                context=context
            )

        # Duration-based metrics if available
        if hasattr(response, 'total_duration') and response.total_duration:
            self.performance_monitor.record_metric(
                name=f"{PERFORMANCE_METRIC_PREFIX}_guidance_total_duration",
                value=response.total_duration,
                unit="nanoseconds",
                context=context
            )