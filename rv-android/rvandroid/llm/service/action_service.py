"""LLM action service for the prompt system.

This module defines the LLMActionService class, which orchestrates the
AI-driven test action generation system using the PromptFramework.
"""

from typing import Any, Dict, List, Optional

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.llm.constants import ContextEntry, PromptStrategyType, StateEntry
from rvandroid.llm.data_structures import MCPMessage, MCPResponse
from rvandroid.llm.prompt.framework import PromptFramework
from rvandroid.llm.service import LLMManager
from rvandroid.llm.service.action_generator import ActionGenerator
from rvandroid.llm.service.response_processor import ResponseProcessor
from rvandroid.llm.service.state_enricher import StateEnricher
from rvandroid.llm.service.transition_manager import TransitionManager
from rvandroid.parser.screen.visitor.model import ItemAction
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
    
    ### Role in the System:
    - Provides a unified interface for state processing and action generation
    - Coordinates the flow between state analysis, LLM interaction, and action generation
    - Manages lifecycle of AI-driven testing operations
    - Integrates with system-wide services like event bus and performance monitoring
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
        app_package = state.get(StateEntry.PACKAGE_NAME, "unknown")
        app_activity = state.get(StateEntry.ACTIVITY, "unknown").replace("/", "")
        state[StateEntry.ACTIVITY] = app_activity
        context = {
            ContextEntry.APP_PACKAGE: app_package,
            ContextEntry.APP_ACTIVITY: app_activity
        }

        self.logger.info(f"Processing state for app: {app_package}, activity: {app_activity}")

        # Overall processing time measurement
        with self.performance_monitor.measure_time("state_processing_total", context):
            try:
                # Enrich state with additional information
                enriched_state = self.state_enricher.enrich_state(state)

                # Update dynamic transition graph with information about the current state
                self.transition_manager.update_transitions(enriched_state)

                # Generate prompt and get LLM response
                with self.performance_monitor.measure_time("llm_interaction", context):
                    # TODO criar o contexto direito
                    prompt_context = self._create_prompt_context(enriched_state)

                    messages = self.framework.generate_mcp_prompt(enriched_state, prompt_context)

                    # Record prompt metrics if possible
                    self.record_prompt_metrics(messages, context)

                    response: MCPResponse = self.llm_manager.generate(messages, self.config)
                    self.logger.debug(f"Received response: {response}")

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

                    # Get available action IDs
                    available_actions: Dict[int, ItemAction] = enriched_state.get(StateEntry.AVAILABLE_ACTIONS, {})
                    available_action_ids = [str(action) for action in available_actions.keys()]

                    # Process response into action descriptions
                    actions, errors = self.response_processor.process_response(
                        response_text, available_action_ids, enriched_state
                    )

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

    def update_config(self,
                      temperature: Optional[float] = None,
                      max_tokens: Optional[int] = None) -> None:
        """Update configuration parameters.
        
        Args:
            temperature: Optional new temperature value
            max_tokens: Optional new max_tokens value
        """
        if not self.model:
            self.logger.warning("Cannot update config: No model available")
            return

        if temperature is not None:
            if hasattr(self.model, 'update_config'):
                self.model.update_config(temperature=temperature)
                self.logger.info(f"Updated temperature to {temperature}")
            else:
                self.logger.warning("Model does not support updating temperature")

        if max_tokens is not None:
            if hasattr(self.model, 'update_config'):
                self.model.update_config(max_tokens=max_tokens)
                self.logger.info(f"Updated max_tokens to {max_tokens}")
            else:
                self.logger.warning("Model does not support updating max_tokens")

    def cleanup(self):
        """Clean up resources used by the service and all its components."""
        self.logger.info("Cleaning up LLM Action Service resources")

        # Save transition data if needed
        # self.transition_manager.save()

        # Clean up the model if it has a cleanup method
        if self.model and hasattr(self.model, 'cleanup'):
            try:
                self.logger.info("Cleaning up LLM model")
                self.model.cleanup()
            except Exception as e:
                self.logger.warning(f"Error cleaning up model: {e}")

        # Publish service shutdown event
        self.event_bus.publish_analysis_event(
            EventType.EXPERIMENT_COMPLETED,
            data={"service": "LLMActionService"},
            source="LLMActionService"
        )

    def record_prompt_metrics(self, messages: List[MCPMessage], context) -> None:
        for message in messages:
            self.performance_monitor.record_metric(
                name=f"prompt_length_{message.role}",
                value=len(message.content),
                unit="chars",
                context=context
                )
