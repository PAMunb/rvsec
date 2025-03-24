# rvandroid/llm/action_service.py
from typing import Dict, List, Any, Optional

from rvandroid.llm.service.action_generator import ActionGenerator
from rvandroid.llm.service.llm_manager import LLMManager
from rvandroid.llm.service.prompt_processor import PromptProcessor
from rvandroid.llm.service.response_processor import ResponseProcessor
from rvandroid.llm.service.state_analyzer import StateAnalyzer
from rvandroid.llm.service.transition_manager import TransitionManager

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.performance_monitor import PerformanceMonitor


class LLMActionService:
    """
    Orchestrates the AI-driven test action generation system by coordinating specialized components.

    ### Architectural Decisions:
    - Implements a facade pattern to coordinate specialized components
    - Follows the Single Responsibility Principle by delegating specialized functions
    - Maintains minimal direct dependencies through component-based approach
    - Enables configurability through dependency injection

    ### Role in the System:
    - Provides a unified interface for state processing and action generation
    - Coordinates the flow between state analysis, LLM interaction, and action generation
    - Manages lifecycle of AI-driven testing operations
    - Integrates with system-wide services like event bus and performance monitoring

    ### Integration Strategy:
    - Each specialized component handles a distinct responsibility
    - Communications through well-defined interfaces
    - Leverages system-wide services for cross-cutting concerns
    """

    def __init__(
            self,
            static_data: Optional[StaticAnalysisData] = None,
            config: Optional[ComponentConfigurator] = None,
            dynamic_wtg_file: str = "dynamic_wtg.json",
            **model_kwargs
    ):
        """
        Initialize the LLM action service with its component system.

        Args:
            static_data: Static analysis data for the application (optional)
            config: ComponentConfigurator instance
            dynamic_wtg_file: File to store/load dynamic transition graph
            **model_kwargs: Additional arguments for the model constructor
        """
        # Initialize system services
        self.event_bus = EventBus.get_instance()
        self.performance_monitor = PerformanceMonitor.get_instance()

        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.action_service",
            {
                CONTEXT_COMPONENT: "LLMActionService"
            }
        )

        # Store configuration
        self.config = config or ComponentConfigurator()
        self.static_data = static_data

        # Create specialized components
        self.transition_manager = TransitionManager(dynamic_wtg_file)
        self.llm_manager = LLMManager(config, **model_kwargs)
        self.prompt_processor = PromptProcessor(config, static_data)
        self.state_analyzer = StateAnalyzer(static_data)
        self.response_processor = ResponseProcessor(config)
        self.action_generator = ActionGenerator(config, static_data)

        # Record session creation event
        self.event_bus.publish_analysis_event(
            EventType.EXPERIMENT_STARTED,
            data={"service": "LLMActionService", "model": self.llm_manager.model_name},
            source="LLMActionService"
        )

        # Log initialization
        self.logger.info(
            f"Initialized LLM Action Service with model={self.llm_manager.model_name}, "
            f"strategy={config.strategy_class.__name__ if config and config.strategy_class else 'unknown'}"
        )

    def process_state(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process the current application state to generate AI-driven actions.

        This method coordinates specialized components to analyze the app state,
        generate prompts, interact with the LLM, parse responses, and produce actions.

        Args:
            state: Dictionary representing the current application state

        Returns:
            List of action dictionaries for test automation system execution
        """
        # Create context for performance monitoring
        app_package = state.get("package_name", "unknown")
        app_activity = state.get("activity", "unknown")
        context = {"package_name": app_package, "activity": app_activity}

        self.logger.info(f"Processing state for app: {app_package}, activity: {app_activity}")

        # Overall processing time measurement
        with self.performance_monitor.measure_time("state_processing_total", context):
            try:
                # Update and analyze state
                with self.performance_monitor.measure_time("state_analysis", context):
                    # Enrich state with transition guidance
                    transition_guidance = self.transition_manager.get_transition_guidance(app_activity)
                    state["transition_guidance"] = transition_guidance

                    # Update transition graph
                    self.transition_manager.update_transitions(state)

                    # Analyze state for enhanced context
                    self.state_analyzer.analyze_and_enhance_state(state)

                # Generate prompts
                with self.performance_monitor.measure_time("prompt_generation", context):
                    messages = self.prompt_processor.generate_prompts(state)

                    # Record prompt metrics
                    self.performance_monitor.record_metric(
                        name="prompt_length_system",
                        value=len(messages[0]['content']),
                        unit="chars",
                        context=context
                    )
                    self.performance_monitor.record_metric(
                        name="prompt_length_user",
                        value=len(messages[1]['content']),
                        unit="chars",
                        context=context
                    )

                # Call the LLM
                with self.performance_monitor.measure_time("llm_call", context):
                    response = self.llm_manager.generate(messages)

                # Process response and generate actions
                with self.performance_monitor.measure_time("action_generation", context):
                    # Parse LLM response into actions
                    available_action_ids = self.state_analyzer.get_available_action_ids(state)
                    actions, errors = self.response_processor.process_response(
                        response, available_action_ids, state
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

                    # Convert to framework-compatible format
                    droidbot_actions = self.action_generator.create_actions(actions, state)

                # Update transition graph with chosen actions
                with self.performance_monitor.measure_time("update_graph", context):
                    self.transition_manager.update_with_actions(state, droidbot_actions)
                    self.transition_manager.save()

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

                # Record error metrics
                self.performance_monitor.record_metric(
                    name="state_processing_error",
                    value=1,
                    context={**context, "error": str(e)}
                )

                # Generate fallback actions
                return self.action_generator.generate_fallback_actions(state)

    def cleanup(self):
        """
        Clean up resources used by the service and all its components.
        """
        self.logger.info("Cleaning up LLM Action Service resources")

        # Save transition data
        self.transition_manager.save()

        # Clean up LLM resources
        self.llm_manager.cleanup()

        # Publish service shutdown event
        self.event_bus.publish_analysis_event(
            EventType.EXPERIMENT_COMPLETED,
            data={"service": "LLMActionService"},
            source="LLMActionService"
        )
