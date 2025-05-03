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
from rvandroid.llm.service.action_generator import ActionGenerator, GeneratedAction
from rvandroid.llm.service.memory_manager import MemoryManager
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
    - Integrates memory systems for history-aware decision making

    ### Role in the System:
    - Provides a unified interface for state processing and action generation
    - Coordinates the flow between state analysis, LLM interaction, and action generation
    - Manages lifecycle of AI-driven testing operations
    - Integrates with system-wide services like event bus and performance monitoring
    - Ensures consistent handling of both single action and batch action strategies
    - Maintains historical context through integrated memory systems
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

        # Get app package from kwargs or use default
        app_package = model_kwargs.get("app_package", "unknown")  # TODO rever ... pegar de outra forma

        # Create specialized components
        self.transition_manager = TransitionManager()
        self.memory_manager = MemoryManager(app_package, static_data)
        self.state_enricher = StateEnricher(static_data, self.config)
        self.response_processor = ResponseProcessor(self.config)
        self.action_generator = ActionGenerator(self.config, static_data)
        self.llm_manager = LLMManager(self.config, **model_kwargs)

        # Initialize framework
        self.logger.info("Creating PromptFramework")
        self.framework = PromptFramework.create(self.config)

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
            f"strategy={config.strategy_class.__name__ if config and config.strategy_class else 'default'}"
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
        context = self._initialize_context(state)

        self.logger.info(
            f"Processing state for app: {state[StateEntry.PACKAGE_NAME]}, activity: {state[StateEntry.ACTIVITY]}")

        # Overall processing time measurement
        with self.performance_monitor.measure_time("state_processing_total", context):
            try:
                # Enrich state with additional information
                enriched_state = self.pre_process_state(state)

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

                # Process response into actions
                if not response:
                    self.logger.error("No response from LLM")
                    return self.convert_to_droidbot(self.action_generator.generate_fallback_actions(enriched_state))

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

                # Convert action descriptions to executable actions
                generated_actions = self.action_generator.create_actions(actions, enriched_state)

                self.post_process_state(enriched_state, generated_actions)

                # Publish success metrics
                self.performance_monitor.record_metric(
                    name="actions_generated",
                    value=len(generated_actions),
                    context=context
                )

                self.logger.info(f"Generated {len(generated_actions)} actions")
                return self.convert_to_droidbot(generated_actions)

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
                return self.convert_to_droidbot(self.action_generator.generate_fallback_actions(state))

    def pre_process_state(self, state: Dict[str, Any]) -> dict[str, Any]:
        # Enrich state with additional information
        enriched_state = self.state_enricher.enrich_state(state)

        # Update transitions with current state information
        self.transition_manager.update(enriched_state)

        # Update memory with current state information
        self.memory_manager.update_state(enriched_state)

        # Enrich state with historical information
        self.memory_manager.enrich_state_with_history(enriched_state)

        # Add transition guidance to state
        transition_guidance = self.transition_manager.get_transition_guidance(enriched_state)
        enriched_state[StateEntry.TRANSITION_GUIDANCE] = transition_guidance

        return enriched_state

    def post_process_state(self, state, generated_actions: list[GeneratedAction]):

        # Record actions in memory
        self.memory_manager.record_actions(state, generated_actions)

        # Update transition graph with chosen actions
        self.transition_manager.update_with_actions(state, generated_actions)

    def convert_to_droidbot(self, actions: List[GeneratedAction]) -> List[Dict[str, Any]]:
        """Convert generated actions to DroidBot-compatible format.

        Args:
            actions: List of GeneratedAction objects

        Returns:
            List of action dictionaries in DroidBot format
        """
        return [action.to_droidbot_format() for action in actions]

    # TODO deprecated
    def process_action_result(self, from_state: Dict[str, Any], to_state: Dict[str, Any],
                              action: Dict[str, Any], success: bool) -> None:
        """
        Process the result of an action execution.

        This method records the state transition and updates memory with the action result.

        Args:
            from_state: Source state
            to_state: Destination state
            action: Action that was executed (dictionary format)
            success: Whether the action execution was successful
        """
        try:
            # Get action ID and type
            action_id = action.get("action_id", action.get("id", "unknown"))
            action_type = action.get("action_type", "unknown")

            # Record transition in transition manager
            self.transition_manager.record_transition(from_state, to_state, action_id, action_type)

            # Create a basic Iteration with this action for the memory manager
            self.memory_manager.record_actions(from_state, [action])

            # No need to record transition in memory_manager as we don't have proper ItemAction objects
            # for the MemoryAction.from_item_action method

            self.logger.info(f"Processed action result: success={success}")

        except Exception as e:
            self.logger.error(f"Error processing action result: {e}")
            self.error_handler.handle_error(
                e,
                context={
                    "component": "LLMActionService",
                    "function": "process_action_result"
                }
            )

    def _initialize_state(self, state: Dict[str, Any]):
        """Initialize state with basic information.

        Args:
            state: Current application state
        """
        app_package = state.get(StateEntry.PACKAGE_NAME, "unknown")
        app_activity = state.get(StateEntry.ACTIVITY, "unknown").replace("/", "")
        state[StateEntry.PACKAGE_NAME] = app_package
        state[StateEntry.ACTIVITY] = app_activity

    def _initialize_context(self, state: Dict[str, Any]):
        context = {
            ContextEntry.APP_PACKAGE: state[StateEntry.PACKAGE_NAME],
            ContextEntry.APP_ACTIVITY: state[StateEntry.ACTIVITY],
            ContextEntry.MODEL_TYPE: self.config.llm_config.model_type,
            ContextEntry.MODEL_NAME: self.config.llm_config.model_name,
            ContextEntry.STRATEGY: self.config.llm_config.strategy_type,
            ContextEntry.VISITOR: self.config.visitor_class.__name__
        }
        return context

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

    # def get_current_strategy_type(self) -> str:
    #     """Get the current strategy type.
    #
    #     Used by the server to include strategy metadata in responses.
    #
    #     Returns:
    #         String indicating the current strategy type.
    #     """
    #     # If framework has a selected strategy, use it
    #     if hasattr(self.framework, 'strategy_registry') and self.framework.strategy_registry:
    #         strategy = self.framework.strategy_registry.get_strategy()
    #         if strategy:
    #             return strategy.name
    #
    #     # Return default strategy type
    #     return PromptStrategyType.STANDARD

    def record_prompt_metrics(self, messages: List[LLMMessage], context) -> None:
        """Record metrics about prompt size and content.

        Args:
            messages: List of LLMMessage objects
            context: Context for metrics
        """
        for message in messages:
            self.performance_monitor.record_metric(
                name=f"prompt_length_{message.role}",
                value=message.total_chars(),
                unit="chars",
                context=context
            )

    def clear_short_term_memory(self) -> None:
        """Clear the short-term memory."""
        self.memory_manager.clear_short_term_memory()
