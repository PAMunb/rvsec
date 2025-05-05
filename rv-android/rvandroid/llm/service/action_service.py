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
            static_data: StaticAnalysisData,
            config: ComponentConfigurator,
            app_package: str,
            **model_kwargs
    ):
        """Initialize the LLM action service with its component system.

        Args:
            static_data: Static analysis data for the application (optional)
            config: ComponentConfigurator instance
            app_package: Application package name for the target app
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
        self.app_package = app_package

        # Create specialized components
        self.transition_manager = TransitionManager(static_data)
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
                transition_detected = self.pre_process_state(state)

                # Generate prompt and get LLM response
                with self.performance_monitor.measure_time("llm_interaction", context):
                    # Create prompt context
                    prompt_context = self._create_prompt_context(state)

                    # Generate prompt messages
                    messages = self.framework.generate_prompt(state, prompt_context)

                    # Record prompt metrics if possible
                    self.record_prompt_metrics(messages, context)

                    # Get response from LLM
                    response: LLMResponse = self.llm_manager.generate(messages, self.config)
                    self.logger.debug(f"Received response: {response}")

                # Process response into actions
                if not response:
                    self.logger.error("No response from LLM")
                    return self.convert_to_droidbot(self.action_generator.generate_fallback_actions(state))

                # Extract response content
                response_text = response.content if hasattr(response, 'content') else str(response)

                # Process response into action descriptions
                actions, errors = self.response_processor.process_response(response_text, state)

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
                generated_actions = self.action_generator.create_actions(actions, state)

                self.post_process_state(state, generated_actions, transition_detected)

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

    def pre_process_state(self, state: Dict[str, Any]) -> bool:
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

    def post_process_state(self, state: Dict[str, Any], generated_actions: List[GeneratedAction], transition_detected: bool) -> None:
        """
        Post-process the state after action generation.
        
        This method updates component systems with the generated actions to maintain
        accurate state tracking and history.
        
        Args:
            state: Current application state
            generated_actions: List of generated actions to execute
            transition_detected: Whether a transition was detected during pre-processing
        """
        # Record actions in memory
        self.memory_manager.record_actions(state, generated_actions)

        # Note: The transition handling in this method is no longer needed
        # since transitions are properly handled in the process_action_result method

    def convert_to_droidbot(self, actions: List[GeneratedAction]) -> List[Dict[str, Any]]:
        """Convert generated actions to DroidBot-compatible format.

        Args:
            actions: List of GeneratedAction objects

        Returns:
            List of action dictionaries in DroidBot format
        """
        return [action.to_droidbot_format() for action in actions]

    def process_action_result(self, from_state: Dict[str, Any], to_state: Dict[str, Any],
                          action: Dict[str, Any], success: bool) -> None:
        """
        Process the result of an action execution.

        This method coordinates the recording of state transitions and action history. 
        When a transition is detected, it retrieves actions from the memory manager 
        and passes them to the transition manager to record the transition.

        Args:
            from_state: Source state
            to_state: Destination state
            action: Action that was executed (dictionary format)
            success: Whether the action execution was successful
        """
        try:
            # Get activity information
            from_activity = from_state.get(StateEntry.ACTIVITY, "unknown")
            to_activity = to_state.get(StateEntry.ACTIVITY, "unknown")
            
            # Detect if this is a transition between different activities
            is_transition = from_activity != to_activity
            
            # Convert the action dictionary to a GeneratedAction object
            generated_action = self._dict_to_generated_action(action)
            
            # Record action in memory manager
            self.memory_manager.record_actions(
                from_state, 
                [generated_action], 
                action_selection_reason="", 
                succeeded=success
            )
            
            # If this is a transition, record it in both memory manager and transition manager
            if is_transition:
                # First record the transition in memory manager
                self.memory_manager.record_transition(
                    from_state,
                    to_state,
                    generated_action,
                    success
                )
                
                # Get all actions from the current activity (before it changed)
                recent_actions = self.memory_manager.get_recent_activity_actions()
                
                # Also record the transition in transition manager with all relevant actions
                self.transition_manager.record_transition(
                    from_activity, 
                    to_activity, 
                    recent_actions
                )
                
                self.logger.info(
                    f"Recorded transition from {from_activity} to {to_activity} "
                    f"with {len(recent_actions)} actions"
                )
            
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
    
    def _dict_to_generated_action(self, action_dict: Dict[str, Any]):
        """
        Convert an action dictionary to a GeneratedAction object.
        
        Args:
            action_dict: Dictionary representation of an action
            
        Returns:
            GeneratedAction object
        """
        from rvandroid.domain.widget import WidgetEventType
        from rvandroid.parser.screen.visitor.model import ItemAction
        from rvandroid.llm.service.action_generator import GeneratedAction
        
        # Create an ItemAction as required by GeneratedAction
        event_type = getattr(WidgetEventType, action_dict.get("action_type", "CLICK"), WidgetEventType.CLICK)
        item_action = ItemAction(
            action_dict.get("action_id", 0),
            action_dict.get("text", f"{event_type.name}(?)"),
            event_type
        )
        
        # Create and return the GeneratedAction
        return GeneratedAction(
            item=item_action,
            params=action_dict.get("params", {}),
            coordinates=action_dict.get("coordinates", (0, 0)),
            target="",  # Deprecated field
            explanation=action_dict.get("explanation", "")
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
        state[StateEntry.STATIC_DATA] = self.static_data

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
        """Clear the short-term memory.
        
        Useful to reset the short-term memory when starting a new testing session
        or when manually forcing a context reset.
        """
        if self.memory_manager and hasattr(self.memory_manager, 'short_term'):
            self.memory_manager.short_term.clear()
            self.logger.info("Short-term memory cleared")