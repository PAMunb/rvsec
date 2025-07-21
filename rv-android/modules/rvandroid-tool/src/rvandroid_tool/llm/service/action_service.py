"""
LLM Action Service with Unified Configuration Architecture

This module orchestrates the AI-driven test action generation system using unified
configuration management, eliminating parameter duplication and providing consistent
component initialization across the entire service.

### Architectural Overview:
This service coordinates the entire process of generating testing actions from the
current application state using unified configuration that combines LLM backend
configuration with prompt strategy configuration through composition.

### Key Features:
- Unified Configuration: Single configuration source for all service components
- Composition Architecture: Uses composed configurations instead of parameter duplication
- Strategy Integration: Full support for prompt strategies (BATCH_ACTION, STANDARD)
- Component Coordination: Orchestrates specialized components with consistent configuration
- Memory Integration: History-aware decision-making through memory systems

### Design Principles:
- Facade Pattern: Coordinates specialized components through unified interface
- Single Responsibility: Delegates specialized functions to dedicated components
- Dependency Injection: Configurable through dependency injection patterns
- Unified Framework: Standardized LLM interactions through PromptFramework
- Consistent Processing: All LLM responses processed in standardized format

### Integration Strategy:
- Receives unified RvAndroidToolConfig containing all necessary configuration
- Extracts LLM and prompt configurations from unified configuration
- Initializes all specialized components with appropriate configuration
- Provides unified interface for state processing and action generation
"""

from typing import Any, Dict, List

from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.event.bus import EventBus
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import LLMServiceError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.performance.performance_monitor import PerformanceMonitor
from rv_llm.llm.constants import ContextEntry, StateEntry
from rvandroid_tool.llm.prompt.rvandroid_framework import RVAndroidPromptFramework
from rvandroid_tool.config.tool_config import RvAndroidToolConfig
from rvandroid_tool.llm.service.action_generator import ActionGenerator
from rvandroid_tool.llm.service.llm_manager import LLMManager
from rvandroid_tool.llm.service.memory_manager import MemoryManager
from rvandroid_tool.llm.service.response_processor import ResponseProcessor
from rvandroid_tool.llm.service.state_enricher import StateEnricher
from rvandroid_tool.llm.service.transition_manager import TransitionManager


class LLMActionService:
    """
    Orchestrates the AI-driven test action generation system with unified configuration.
    
    This service coordinates the entire process of generating testing actions from the
    current application state, using unified configuration to ensure consistent behavior
    across all components.
    
    ### Architecture Overview:
    The service acts as a coordinator between multiple specialized components:
    - LLM backend management through LLMManager
    - Prompt generation through RVAndroidPromptFramework
    - State processing through specialized processors
    - Action generation through ActionGenerator
    
    ### Configuration Strategy:
    Uses composition to access both LLM and prompt configurations from the unified
    tool configuration, eliminating parameter duplication and ensuring configuration
    consistency.
    
    ### Component Initialization:
    1. Extract configurations from unified tool config
    2. Initialize LLM manager with backend configuration
    3. Create prompt framework with strategy configuration
    4. Initialize specialized processors with appropriate configurations
    
    ### Role in the System:
    - Provides unified interface for state processing and action generation
    - Coordinates flow between state analysis, LLM interaction, and action generation
    - Maintains consistent configuration across all specialized components
    - Enables history-aware decision-making through memory integration
    """

    @ErrorHandler.handle_errors(
        component="LLMActionService",
        operation="__init__"
    )
    def __init__(
            self,
            static_data: StaticAnalysisData,
            tool_config: RvAndroidToolConfig,
            **model_kwargs
    ):
        """
        Initialize LLM action service with unified configuration.
        
        This service orchestrates LLM-based action generation for Android testing,
        using unified configuration to ensure consistent behavior across all components.
        
        ### Architecture Overview:
        The service acts as a coordinator between multiple specialized components:
        - LLM backend management through LLMManager
        - Prompt generation through RVAndroidPromptFramework
        - State processing through specialized processors
        - Action generation through ActionGenerator
        
        ### Configuration Strategy:
        Uses composition to access both LLM and prompt configurations from the
        unified tool configuration, eliminating parameter duplication and
        ensuring configuration consistency.
        
        ### Component Initialization:
        1. Extract configurations from unified tool config
        2. Initialize LLM manager with backend configuration
        3. Create prompt framework with strategy configuration
        4. Initialize specialized processors with appropriate configurations
        
        Args:
            static_data: Static analysis data for the target application
            tool_config: Unified configuration containing LLM and prompt settings
            **model_kwargs: Additional model-specific parameters
            
        Raises:
            LLMServiceError: If service initialization fails
        """
        # Initialize logging with proper context
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "rvandroid_tool.llm.service.action_service",
            {CONTEXT_COMPONENT: "LLMActionService"}
        )
        self.logger.info("Initializing LLM Action Service ...")

        # Initialize event bus for lifecycle events
        self.event_bus = EventBus.get_instance()

        # Initialize performance monitoring
        self.performance_monitor = PerformanceMonitor.get_instance()

        # Store parameters
        self.tool_config = tool_config
        self.static_data = static_data

        # Extract configurations
        self.llm_config = tool_config.llm_config
        self.prompt_config = tool_config.prompt_config

        # Initialize LLM manager with backend configuration
        self.llm_manager = LLMManager(self.llm_config, **model_kwargs)

        # Initialize RVAndroid prompt framework with complete registration
        self.prompt_framework = RVAndroidPromptFramework.create(self.prompt_config)

        # Initialize specialized processors
        self.state_enricher = StateEnricher(static_data=static_data, config=self.llm_config)
        self.response_processor = ResponseProcessor(config=self.llm_config)
        self.action_generator = ActionGenerator(config=self.llm_config, static_data=static_data)

        # Initialize coordination components
        self.transition_manager = TransitionManager(static_data)
        self.memory_manager = MemoryManager(static_data)

        # Log successful initialization
        self.logger.info(
            f"LLM Action Service initialized - "
            f"Backend: {self.llm_config.llm_type}:{self.llm_config.model}, "
            f"Strategy: {self.prompt_config.strategy_type}, "
            f"Parser: {self.prompt_config.parser_type}, "
            f"Visitor: {self.prompt_config.visitor_type}"
        )

    @ErrorHandler.handle_errors(
        component="LLMActionService",
        operation="process_state"
    )
    def process_state(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process application state and generate testing actions.
        
        This method orchestrates the entire action generation pipeline using
        unified configuration and specialized components.
        
        ### Processing Pipeline:
        1. Enrich state with additional information
        2. Generate context-aware prompt using RVAndroidPromptFramework
        3. Process LLM response into structured actions
        4. Update memory with interaction history
        5. Return generated actions for execution
        
        Args:
            state: Current application state to process
            
        Returns:
            List of generated actions for execution
            
        Raises:
            LLMServiceError: If state processing fails
        """
        with self.performance_monitor.measure_time("process_state"):
            try:
                # Pre-process state with complete enrichment pipeline
                self._pre_process_state(state)

                # Create prompt context
                prompt_context = self._create_prompt_context(state)

                # Generate prompt messages using unified framework
                messages = self.prompt_framework.generate_prompt(state, prompt_context)


                print(f"****************** Messages: {len(messages)}")
                for msg in messages:
                    print(f"\n *** Message: {msg.role}")
                    for content in msg.content:
                        print(f"   - Content:\n{content.text}")


                # Process LLM interaction
                llm_response = self.llm_manager.generate(messages)

                # Check if response is valid
                if not llm_response:
                    self.logger.error("No response from LLM")
                    return []

                # Extract response content
                response_text = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)

                # Process response into action descriptions
                actions, errors = self.response_processor.process_response(response_text, state)

                # Report any errors
                for error in errors:
                    self.logger.warning(f"Response parsing issue: {error}")

                # Generate executable actions
                generated_actions = self.action_generator.create_actions(actions, state)

                # Update memory with interaction history
                self.memory_manager.record_actions(state, generated_actions)

                # Log processing results
                self.logger.info(
                    f"Processed state - Generated {len(generated_actions)} actions "
                    f"using strategy: {self.prompt_config.strategy_type}"
                )

                # Record LLM event
                # self.event_bus.publish_llm_event(llm_response, generated_actions)

                return [action.to_droidbot_format() for action in generated_actions]

            except Exception as e:
                self.logger.error(f"State processing failed: {e}")
                raise LLMServiceError(f"State processing failed: {e}")

    @ErrorHandler.handle_errors(
        component="LLMActionService",
        operation="get_configuration_info"
    )
    def get_configuration_info(self) -> Dict[str, Any]:
        """
        Get current service configuration information.
        
        Returns:
            Dictionary containing configuration details
        """
        return {
            "llm_backend": f"{self.llm_config.llm_type}:{self.llm_config.model}",
            "prompt_strategy": self.prompt_config.strategy_type,
            "parser_type": self.prompt_config.parser_type,
            "visitor_type": self.prompt_config.visitor_type,
            "server_port": self.tool_config.server_port,
            "debug_mode": self.tool_config.debug_mode
        }

    def _pre_process_state(self, state: Dict[str, Any]) -> bool:
        """
        Pre-process the state by enriching it with additional information.
        
        This method coordinates the state enrichment process, including:
        - Basic state enrichment (action decoding, screen analysis)
        - Transition management and guidance
        - Memory updates and history enrichment
        
        Args:
            state: Current application state
            
        Returns:
            bool: True if a transition (to other screen) was detected, False otherwise
        """
        self.logger.info(f"Pre-processing state: {state.get(StateEntry.ACTIVITY, 'unknown')}")

        # Initialize state with basic information
        self._initialize_state(state)

        # Enrich state with additional information
        self.state_enricher.enrich_state(state)

        # Update transitions with current state information
        transition_detected = self.transition_manager.update(state)

        # Update memory with current state information
        self.memory_manager.update(state)

        # Enrich state with historical information
        self.memory_manager.enrich_state_with_history(state)

        # Add transition guidance to state
        transition_guidance = self.transition_manager.get_transition_guidance(state)
        state[StateEntry.TRANSITION_GUIDANCE] = transition_guidance

        return transition_detected

    def _initialize_state(self, state: Dict[str, Any]):
        """Initialize state with basic information.

        Args:
            state: Current application state
        """
        app_package = state.get(StateEntry.PACKAGE_NAME, "unknown")
        app_activity = state.get(StateEntry.ACTIVITY, "unknown").replace("/", "")
        state[StateEntry.PACKAGE_NAME] = app_package
        state[StateEntry.ACTIVITY] = app_activity
        state[StateEntry.STATIC_DATA] = self.static_data

    def _create_prompt_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create context dictionary for prompt generation.

        Args:
            state: Current application state.

        Returns:
            Context dictionary with relevant information.
        """
        return {
            ContextEntry.APP_PACKAGE: state.get(StateEntry.PACKAGE_NAME, ""),
            ContextEntry.APP_ACTIVITY: state.get(StateEntry.ACTIVITY, ""),
            ContextEntry.ADDITIONAL_GUIDELINES: state.get(ContextEntry.ADDITIONAL_GUIDELINES, ""),
            ContextEntry.TESTING_HISTORY: state.get("testing_history", "")
        }

    @ErrorHandler.handle_errors(
        component="LLMActionService",
        operation="cleanup"
    )
    def cleanup(self):
        """Clean up service resources."""
        try:
            # Clean up specialized components
            if hasattr(self, 'llm_manager'):
                self.llm_manager.cleanup()

            if hasattr(self, 'memory_manager'):
                self.memory_manager.cleanup()

            self.logger.info("LLMActionService cleanup completed")

        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            raise LLMServiceError(f"Service cleanup failed: {e}")
