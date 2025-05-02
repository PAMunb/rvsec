# rvandroid/llm/service/action_service.py
"""LLM action service for the prompt system.

This module defines the LLMActionService class, which orchestrates the
AI-driven test action generation system using the PromptFramework.
"""

from typing import Any, Dict, List, Optional

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.llm.constants import ContextEntry, PromptStrategyType, StateEntry
from rvandroid.llm.data_structures import LLMMessage, LLMResponse
from rvandroid.llm.prompt.framework import PromptFramework
from rvandroid.llm.service import LLMManager
from rvandroid.llm.service.action_generator import ActionGenerator
from rvandroid.llm.service.response_processor import ResponseProcessor
from rvandroid.llm.service.state_enricher import StateEnricher
from rvandroid.llm.service.transition_manager import TransitionManager
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.performance_monitor import PerformanceMonitor


class LLMActionService:
    """Orchestrates the AI-driven test action generation system.

    This service coordinates the entire process of generating testing actions
    from the current application state, including:
    - Enriching the state with additional information
    - Selecting the appropriate prompt strategy
    - Generating prompts using the PromptFramework
    - Processing LLM responses into executable actions

    ### Architectural Decisions:
    - Implements a facade pattern to coordinate specialized components
    - Follows the Single Responsibility Principle by delegating specialized functions
    - Maintains minimal direct dependencies through component-based approach
    - Enables configurability through dependency injection
    - Uses the unified PromptFramework for standardized LLM interactions
    - Processes all LLM responses in a consistent format with an "actions" array

    ### Role in the System:
    - Provides a unified interface for state processing and action generation
    - Coordinates the flow between state analysis, LLM interaction, and action generation
    - Manages lifecycle of AI-driven testing operations
    - Integrates with system-wide services like event bus and performance monitoring
    - Ensures consistent handling of both single action and batch action strategies
    """

    def __init__(
            self,
            static_data: Optional[StaticAnalysisData] = None,
            config: Optional[ComponentConfigurator] = None,
            **model_kwargs
    ):
        """Initialize the LLM action service with its component system.

        Args:
            static_data: Static analysis data for the application (optional)
            config: ComponentConfigurator instance
            **model_kwargs: Additional arguments for model creation
        """
        # Initialize system services
        self.event_bus = EventBus.get_instance()
        self.performance_monitor = PerformanceMonitor.get_instance()
        self.error_handler = ErrorHandler.get_instance()

        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.action_service",
            {CONTEXT_COMPONENT: "LLMActionService"}
        )

        # Store configuration
        self.config = config or ComponentConfigurator()
        self.static_data = static_data

        # Create specialized components
        self.transition_manager = TransitionManager()
        self.state_enricher = StateEnricher(static_data, self.config)
        self.response_processor = ResponseProcessor(self.config)
        self.action_generator = ActionGenerator(self.config, static_data)
        self.llm_manager = LLMManager(self.config, **model_kwargs)

        # Initialize framework
        self.logger.info("Creating PromptFramework")
        self.framework = PromptFramework.create(self.config)

        # Initialize memory system for pattern-based strategies
        self.memory = None
        try:
            from rvandroid.core.memory.long_term_memory import LongTermMemory
            app_package = model_kwargs.get("app_package", "unknown")
            self.memory = LongTermMemory(app_package, static_data)
            self.logger.info("Initialized long-term memory system")
        except ImportError:
            self.logger.warning("Long-term memory system not available")

        # Record session creation event
        self.event_bus.publish_analysis_event(
            EventType.EXPERIMENT_STARTED,
            data={"service": "LLMActionService", "model": self.config.llm_config.model_name},
            source="LLMActionService"
        )

        # Log initialization
        self.logger.info(
            f"Initialized LLM Action Service, "
            f"model={self.config.llm_config.model_name}, "
            f"strategy={config.strategy_class.__name__}"
        )

    def process_state(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process the current application state to generate AI-driven actions.

        This method coordinates specialized components to analyze the app state,
        generate prompts, interact with the LLM, parse responses, and produce actions.

        Args:
            state: Dictionary representing the current application state

        Returns:
            List of action dictionaries for test automation system execution
        """
        # Create context for performance monitoring
        self._initialize_state(state)
        context = {
            ContextEntry.APP_PACKAGE: state[StateEntry.PACKAGE_NAME],
            ContextEntry.APP_ACTIVITY: state[StateEntry.ACTIVITY]
        }

        self.logger.info(
            f"Processing state for app: {state[StateEntry.PACKAGE_NAME]}, activity: {state[StateEntry.ACTIVITY]}")

        # Overall processing time measurement
        with self.performance_monitor.measure_time("state_processing_total", context):
            try:
                # Enrich state with additional information
                enriched_state = self.state_enricher.enrich_state(state)

                # Update dynamic transition graph with information about the current state
                self.transition_manager.update_transitions(enriched_state)

                # Generate prompt and get LLM response
                with self.performance_monitor.measure_time("llm_interaction", context):
                    # Create prompt context
                    prompt_context = self._create_prompt_context(enriched_state)

                    # Generate prompt messages
                    messages = self.framework.generate_prompt(enriched_state, prompt_context)

                    # Record prompt metrics if possible
                    self.record_prompt_metrics(messages, context)

                    # Get response from LLM
                    response: LLMResponse = self.llm_manager.generate(messages, self.config)
                    self.logger.debug(f"Received response: {response}")

                    # Record response metrics
                    self.performance_monitor.record_metric(
                        name="response_length",
                        value=response.total_chars(),
                        unit="chars",
                        context=context
                    )

                # Process response into actions
                with self.performance_monitor.measure_time("action_generation", context):
                    if not response:
                        self.logger.error("No response from LLM")
                        return self.action_generator.generate_fallback_actions(enriched_state)

                    # Extract response content
                    response_text = response.content if hasattr(response, 'content') else str(response)

                    # Process response into action descriptions
                    actions, errors = self.response_processor.process_response(response_text, enriched_state)

                    # Record parsing metrics
                    self.performance_monitor.record_metric(
                        name="response_parsing_errors",
                        value=len(errors),
                        context=context
                    )

                    # Report any errors
                    for error in errors:
                        self.logger.warning(f"Response parsing issue: {error}")

                    # Special handling for batch strategies to extract pattern information
                    if self.get_current_strategy_type() == PromptStrategyType.BATCH_ACTION:
                        try:
                            import json
                            data = json.loads(self.parser.extract_json(response_text))
                            if "pattern_type" in data:
                                pattern_type = data["pattern_type"]
                                self.logger.info(f"Detected UI pattern in batch response: {pattern_type}")

                                # Store pattern information in state
                                enriched_state["batch_pattern_type"] = pattern_type
                                if "batch_explanation" in data:
                                    enriched_state["batch_explanation"] = data["batch_explanation"]
                        except Exception as e:
                            self.logger.warning(f"Failed to extract pattern information: {e}")

                    # Convert action descriptions to executable actions
                    droidbot_actions = self.action_generator.create_actions(actions, enriched_state)

                # Update transition graph with chosen actions
                with self.performance_monitor.measure_time("update_graph", context):
                    self.transition_manager.update_with_actions(state, droidbot_actions)

                # Publish success metrics
                self.performance_monitor.record_metric(
                    name="actions_generated",
                    value=len(droidbot_actions),
                    context=context
                )

                self.logger.info(f"Generated {len(droidbot_actions)} actions")
                return droidbot_actions

            except Exception as e:
                self.logger.error(f"Error processing state: {e}", exc_info=True)
                from rvandroid.util.exceptions import RVAndroidError
                error = RVAndroidError(f"State processing error: {str(e)}")
                self.error_handler.handle_error(error, context=context)

                # Record error metrics
                self.performance_monitor.record_metric(
                    name="state_processing_error",
                    value=1,
                    context={**context, "error": str(e)}
                )

                # Generate fallback actions
                return self.action_generator.generate_fallback_actions(state)

    def _initialize_state(self, state: Dict[str, Any]):
        """Initialize state with basic information.

        Args:
            state: Current application state
        """
        app_package = state.get(StateEntry.PACKAGE_NAME, "unknown")
        app_activity = state.get(StateEntry.ACTIVITY, "unknown").replace("/", "")
        state[StateEntry.PACKAGE_NAME] = app_package
        state[StateEntry.ACTIVITY] = app_activity

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

    def get_current_strategy_type(self) -> str:
        """Get the current strategy type.

        Used by the server to include strategy metadata in responses.

        Returns:
            String indicating the current strategy type.
        """
        # If framework has a selected strategy, use it
        if hasattr(self.framework, 'strategy_registry') and self.framework.strategy_registry:
            strategy = self.framework.strategy_registry.get_strategy()
            if strategy:
                return strategy.name

        # Return default strategy type
        return PromptStrategyType.STANDARD

    def get_detected_pattern_info(self) -> Dict[str, Any]:
        """Get information about the most recently detected UI pattern.

        Used by the server to include pattern metadata in responses.

        Returns:
            Dictionary with pattern type and confidence information.
        """
        return None

    def record_prompt_metrics(self, messages: List[LLMMessage], context) -> None:
        """Record metrics about prompt size and content.

        Args:
            messages: List of LLMMessage objects
            context: Context for metrics
        """
        for message in messages:
            self.performance_monitor.record_metric(
                name=f"prompt_length_{message.role}",
                value=len(message.content),
                unit="chars",
                context=context
            )
