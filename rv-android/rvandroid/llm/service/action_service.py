# rvandroid/llm/service/action_service.py
"""LLM Action Service implementation using MCP framework."""

from typing import Dict, List, Any, Optional
import logging

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.llm.language_model import LanguageModel
from rvandroid.llm.data_structures import MCPConfiguration, MCPMessage, MCPRole, MCPTextContent
from rvandroid.llm.service.action_generator import ActionGenerator
from rvandroid.llm.service.prompt_processor import PromptProcessor
from rvandroid.llm.service.response_processor import ResponseProcessor
from rvandroid.llm.service.state_analyzer import StateAnalyzer
from rvandroid.llm.service.transition_manager import TransitionManager
from rvandroid.util.error.error_handler import ErrorHandler
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
    - Uses MCP framework for standardized LLM interactions

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
        """
        Initialize the LLM action service with its component system.

        Args:
            static_data: Static analysis data for the application (optional)
            config: ComponentConfigurator instance
            dynamic_wtg_file: File to store/load dynamic transition graph
            use_batch_strategy: Whether to enable batch action strategy
            **model_kwargs: Additional arguments for the model constructor
        """
        # Initialize system services
        self.event_bus = EventBus.get_instance()
        self.performance_monitor = PerformanceMonitor.get_instance()
        self.error_handler = ErrorHandler.get_instance()

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
        self.transition_manager = TransitionManager()
        self.state_analyzer = StateAnalyzer(static_data)
        self.prompt_processor = PromptProcessor(config, static_data)
        self.response_processor = ResponseProcessor(config)
        self.action_generator = ActionGenerator(config, static_data)
        
        # Create language model
        self.logger.info("Creating Language Model")
        try:
            self.model = self.config.create_llm()
            self.logger.info(f"Created {self.model.__class__.__name__} with model {self.model.model_name}")
        except Exception as e:
            self.logger.error(f"Error creating language model: {e}", exc_info=True)
            from rvandroid.util.exceptions import RVAndroidError
            llm_error = RVAndroidError(f"LLM initialization error: {str(e)}")
            self.error_handler.handle_error(llm_error, context={"service": "LLMActionService"})
            raise
        
        # Create model configuration
        self.model_config = MCPConfiguration(
            temperature=self.config.llm_config.temperature,
            max_tokens=self.config.llm_config.max_tokens,
            model_type=self.config.llm_config.model_type,
            model_name=self.config.llm_config.model_name
        )
        
        # Initialize memory system for pattern-based strategies
        self.memory = None
        try:
            from rvandroid.core.memory.long_term_memory import LongTermMemory
            app_package = model_kwargs.get("app_package", "unknown")
            self.memory = LongTermMemory(app_package, static_data)
            self.logger.info("Initialized long-term memory system")
        except ImportError:
            self.logger.warning("Long-term memory system not available")
        
        # # Initialize batch action strategy if enabled
        # self.batch_strategy = None
        # if use_batch_strategy:
        #     try:
        #         from rvandroid.core.strategies.flow_based_batch_strategy import FlowBasedBatchActionStrategy
        #         self.batch_strategy = FlowBasedBatchActionStrategy(static_data, self.memory)
        #         self.logger.info("Initialized flow-based batch action strategy")
        #     except ImportError:
        #         self.logger.warning("Batch action strategy not available")

        # Record session creation event
        self.event_bus.publish_analysis_event(
            EventType.EXPERIMENT_STARTED,
            data={"service": "LLMActionService", "model": self.model.model_name},
            source="LLMActionService"
        )

        # Log initialization
        strategy_info = f"strategy={config.strategy_class.__name__ if config and config.strategy_class else 'unknown'}"
        # batch_info = f", batch_strategy={'enabled' if self.batch_strategy else 'disabled'}"
        
        self.logger.info(
            f"Initialized LLM Action Service with model={self.model.model_name}, "
            f"{strategy_info}"
        )

    def process_state(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process the current application state to generate AI-driven actions.

        This method coordinates specialized components to analyze the app state,
        generate prompts, interact with the LLM, parse responses, and produce actions.
        It now supports both single-action and batch action generation based on UI patterns.

        Args:
            state: Dictionary representing the current application state

        Returns:
            List of action dictionaries for test automation system execution
        """
        # # Clean up redundant state data
        # # Remove the 'views' list if we already have a view_tree, as it's duplicative
        # if 'view_tree' in state and 'views' in state:
        #     self.logger.debug("Removing duplicate 'views' from state to reduce size")
        #     del state['views']
        # Create context for performance monitoring
        app_package = state.get("package_name", "unknown")
        app_activity = state.get("activity", "unknown")
        context = {"package_name": app_package, "activity": app_activity}

        self.logger.info(f"Processing state for app: {app_package}, activity: {app_activity}")

        # Overall processing time measurement
        with self.performance_monitor.measure_time("state_processing_total", context):
            try:
                # Parse the screen for pattern detection if using batch strategy
                screen_description = None
                with self.performance_monitor.measure_time("screen_parsing", context):
                    screen_description = self.prompt_processor.parse_screen(state)
                    state["screen_description"] = screen_description

                # Check if we should use batch action generation
                # use_batch = False
                # if (hasattr(self, 'batch_strategy') and self.batch_strategy is not None and
                #     screen_description is not None):
                #     with self.performance_monitor.measure_time("batch_detection", context):
                #         use_batch = self.batch_strategy.should_generate_batch(screen_description, state)
                #         if use_batch:
                #             self.logger.info("Using batch action generation strategy")
                #             self.performance_monitor.record_metric(
                #                 name="batch_strategy_used",
                #                 value=1,
                #                 context=context
                #             )
                #         else:
                #             self.logger.debug("Using single action generation strategy")

                # Update and analyze state
                with self.performance_monitor.measure_time("state_analysis", context):
                    # Enrich state with transition guidance
                    transition_guidance = self.transition_manager.get_transition_guidance(app_activity)
                    state["transition_guidance"] = transition_guidance

                    # Update transition graph
                    self.transition_manager.update_transitions(state)

                    # Analyze state for enhanced context
                    self.state_analyzer.analyze_and_enhance_state(state)

                # # Try batch action generation if appropriate
                # if use_batch:
                #     with self.performance_monitor.measure_time("batch_generation", context):
                #         batch_actions = self.batch_strategy.generate_batch_actions(screen_description, state)
                #
                #         if batch_actions and len(batch_actions) >= 2:
                #             self.logger.info(f"Generated {len(batch_actions)} batch actions")
                #
                #             # Track which strategy was used
                #             self.last_used_strategy = "flow_based_batch_action"
                #
                #             # Extract and store pattern information from the batch generation
                #             if hasattr(self.batch_strategy, 'get_last_pattern_info'):
                #                 pattern_info = self.batch_strategy.get_last_pattern_info()
                #                 if pattern_info:
                #                     self.logger.info(f"Detected UI pattern: {pattern_info.get('type')} (confidence: {pattern_info.get('confidence', 0)})")
                #                     self._last_pattern_info = pattern_info
                #
                #             # Record batch metrics
                #             self.performance_monitor.record_metric(
                #                 name="batch_size",
                #                 value=len(batch_actions),
                #                 context=context
                #             )
                #
                #             # Update transition graph with batch actions
                #             with self.performance_monitor.measure_time("update_graph", context):
                #                 self.transition_manager.update_with_actions(state, batch_actions)
                #
                #             return batch_actions
                #         else:
                #             self.logger.info("Batch generation did not produce valid actions, falling back to single action")
                #
                # # If batch generation was not used or didn't produce valid results, use standard approach
                
                # Generate prompts using MCP format
                with self.performance_monitor.measure_time("prompt_generation", context):
                    raw_messages = self.prompt_processor.generate_prompts(state)
                    
                    # Convert to MCP messages
                    messages = []
                    for msg in raw_messages:
                        role = MCPRole.SYSTEM if msg['role'] == 'system' else MCPRole.USER
                        content = [MCPTextContent(text=msg['content'])]
                        messages.append(MCPMessage(role=role, content=content))

                    # Record prompt metrics
                    self.performance_monitor.record_metric(
                        name="prompt_length_system",
                        value=len(raw_messages[0]['content']),
                        unit="chars",
                        context=context
                    )
                    self.performance_monitor.record_metric(
                        name="prompt_length_user",
                        value=len(raw_messages[1]['content']),
                        unit="chars",
                        context=context
                    )

                # Call the LLM using MCP
                with self.performance_monitor.measure_time("llm_call", context):
                    try:
                        response_message = self.model.generate_sync(messages, self.model_config)
                        response = response_message.get_text_content()
                    except Exception as e:
                        self.logger.error(f"LLM call failed: {e}", exc_info=True)
                        from rvandroid.util.exceptions import RVAndroidError
                        llm_error = RVAndroidError(f"LLM generation error: {str(e)}")
                        self.error_handler.handle_error(llm_error, context=context)
                        raise

                # Process response and generate actions
                with self.performance_monitor.measure_time("action_generation", context):
                    # Initialize strategy as single action
                    # self.last_used_strategy = "single_action"
                    
                    # Parse LLM response into actions
                    available_action_ids = state.get("available_actions", [])
                    if not available_action_ids:
                        available_action_ids = self.state_analyzer.get_available_action_ids(state)
                        self.logger.debug(f"Got {len(available_action_ids)} action IDs from state analyzer")
                    else:
                        self.logger.debug(f"Using {len(available_action_ids)} action IDs from state")
                        
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
                    
                    # # Update strategy based on number of actions generated
                    # if len(droidbot_actions) > 1:
                    #     self.last_used_strategy = "flow_based_batch_action"
                    #     self.logger.info(f"Setting batch strategy for {len(droidbot_actions)} actions")

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

    def get_current_strategy_type(self) -> str:
        """
        Get the current strategy type (single action or batch action).
        Used by the server to include strategy metadata in responses.
        
        Returns:
            String indicating the current strategy type
        """
        if self.config and self.config.llm_config and self.config.llm_config.strategy_type:
            strategy_type = self.config.llm_config.strategy_type
        else:
            strategy_type = "single_action" # TODO usar constante
        self.logger.debug(f"Current prompt strategy: {strategy_type}")
        return strategy_type
        
    def get_detected_pattern_info(self) -> Dict[str, Any]:
        """
        Get information about the most recently detected UI pattern.
        Used by the server to include pattern metadata in responses.
        
        Returns:
            Dictionary with pattern type and confidence information
        """
        # First, check if we have stored pattern info from a batch action
        if hasattr(self, '_last_pattern_info') and self._last_pattern_info:
            self.logger.debug(f"Using stored pattern info: {self._last_pattern_info}")
            return self._last_pattern_info
            
        # # Next, try to get pattern info from the batch strategy
        # if hasattr(self, 'batch_strategy') and self.batch_strategy is not None:
        #     if hasattr(self.batch_strategy, 'get_last_pattern_info'):
        #         pattern_info = self.batch_strategy.get_last_pattern_info()
        #         if pattern_info:
        #             self.logger.debug(f"Using pattern info from batch strategy: {pattern_info}")
        #             # Store for future use
        #             self._last_pattern_info = pattern_info
        #             return pattern_info
            
        # # If no pattern info is available, return a default based on strategy
        # if hasattr(self, 'last_used_strategy') and "batch" in self.last_used_strategy:
        #     default_info = {
        #         "type": "unknown",
        #         "confidence": 0.5
        #     }
        #     self.logger.debug(f"Using default pattern info for batch strategy: {default_info}")
        #     return default_info
            
        return None

    # deprecated
    def handle_batch_action_error(self, error_data: Dict[str, Any]) -> None:
        """
        Handle error reports from batch action execution.
        
        Args:
            error_data: Dictionary with error information
        """
        self.logger.warning(f"Received batch action error: {error_data.get('error_message')}")
        
        # Record error metrics
        context = {
            "batch_id": error_data.get("batch_id", "unknown"),
            "action_index": error_data.get("action_index", -1),
            "error_type": error_data.get("error_type", "unknown")
        }
        
        self.performance_monitor.record_metric(
            name="batch_action_error",
            value=1,
            context=context
        )
        
        # Update memory system with execution failure if available
        # TODO
        # if hasattr(self, 'memory') and self.memory is not None:
        #     batch_id = error_data.get("batch_id")
        #     action = error_data.get("action")
        #
        #     if batch_id and action:
        #         self.memory.record_action_failure(
        #             batch_id=batch_id,
        #             action_data=action,
        #             error_message=error_data.get("error_message")
        #         )

    # deprecated
    def handle_batch_execution_result(self, result_data: Dict[str, Any]) -> None:
        """
        Handle result reports from batch action execution.
        
        Args:
            result_data: Dictionary with execution results
        """
        batch_id = result_data.get("batch_id", "unknown")
        success_rate = result_data.get("success_rate", 0)
        pattern_type = result_data.get("pattern_type", "unknown")
        
        self.logger.info(f"Received batch execution result: " +
                   f"batch_id={batch_id}, success_rate={success_rate:.2f}, pattern={pattern_type}")
        
        # Record batch metrics
        context = {
            "batch_id": batch_id,
            "pattern_type": pattern_type,
            "total_actions": result_data.get("total_actions", 0),
            "executed_actions": result_data.get("executed_actions", 0)
        }
        
        self.performance_monitor.record_metric(
            name="batch_execution_success_rate",
            value=success_rate,
            context=context
        )
        
        # If batch had pattern info, record pattern-specific metrics
        if pattern_type != "unknown":
            self.performance_monitor.record_metric(
                name=f"pattern_execution_success_{pattern_type}",
                value=success_rate,
                context=context
            )
            
        # Update global batch statistics for pattern effectiveness analysis
        if not hasattr(self, 'batch_statistics'):
            self.batch_statistics = {
                "total_batches": 0,
                "successful_batches": 0,
                "patterns": {}
            }
            
        self.batch_statistics["total_batches"] += 1
        if success_rate >= 0.9:  # Consider a batch successful if 90% of actions succeeded
            self.batch_statistics["successful_batches"] += 1
            
        if pattern_type != "unknown":
            if pattern_type not in self.batch_statistics["patterns"]:
                self.batch_statistics["patterns"][pattern_type] = {
                    "total": 0,
                    "successful": 0
                }
                
            self.batch_statistics["patterns"][pattern_type]["total"] += 1
            if success_rate >= 0.9:
                self.batch_statistics["patterns"][pattern_type]["successful"] += 1
    
    def update_config(self, 
                     temperature: Optional[float] = None,
                     max_tokens: Optional[int] = None) -> None:
        """
        Update configuration parameters.
        
        Args:
            temperature: Optional new temperature value
            max_tokens: Optional new max_tokens value
        """
        if temperature is not None:
            self.model_config.temperature = temperature
            self.logger.info(f"Updated temperature to {temperature}")
            
        if max_tokens is not None:
            self.model_config.max_tokens = max_tokens
            self.logger.info(f"Updated max_tokens to {max_tokens}")
    
    def cleanup(self):
        """
        Clean up resources used by the service and all its components.
        """
        self.logger.info("Cleaning up LLM Action Service resources")

        # Save transition data
        # self.transition_manager.save()
        
        # Log batch statistics if available
        # TODO
        # if hasattr(self, 'batch_statistics'):
        #     total = self.batch_statistics["total_batches"]
        #     successful = self.batch_statistics["successful_batches"]
        #     success_rate = successful / total if total > 0 else 0
        #
        #     self.logger.info(f"Batch action statistics: {successful}/{total} successful batches ({success_rate:.2f})")
        #
        #     # Log pattern-specific statistics
        #     for pattern, stats in self.batch_statistics["patterns"].items():
        #         pattern_total = stats["total"]
        #         pattern_successful = stats["successful"]
        #         pattern_rate = pattern_successful / pattern_total if pattern_total > 0 else 0
        #
        #         self.logger.info(f"Pattern '{pattern}' statistics: {pattern_successful}/{pattern_total} " +
        #                    f"successful batches ({pattern_rate:.2f})")

        # Clean up the model if it has a cleanup method
        if hasattr(self, 'model') and self.model is not None and hasattr(self.model, 'cleanup'):
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