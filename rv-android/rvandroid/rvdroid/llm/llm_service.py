"""
LLM service for RVDroid using MCP.

This module provides a service for integrating Large Language Models (LLMs)
into RVDroid's testing workflow, enabling strategic guidance for exploration
using the Model Context Protocol (MCP) architecture.
"""

import time
from typing import Dict, Any, List, Optional

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.llm.language_model import LanguageModel
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.data_structures import MCPConfiguration, LLMMessage, LLMRole, LLMTextContent
from rvandroid.rvdroid.llm.context.context_builder import ContextBuilder
from rvandroid.rvdroid.llm.directives.directive_parser import DirectiveParser
from rvandroid.rvdroid.llm.prompts.prompt_manager import PromptManager
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.error import retry
from rvandroid.util.exceptions import RVAndroidError
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.performance_monitor import PerformanceMonitor
from rvandroid.util.json_helpers import safe_json_parse


class LLMService:
    """
    Service for integrating LLMs into RVDroid's testing workflow using MCP.

    ### Architectural Decisions:
    - Implements a central service for LLM interactions
    - Uses a layered architecture with prompt management, context preparation, and directive parsing
    - Provides efficient caching to minimize redundant queries
    - Handles error recovery and fallback mechanisms
    - Uses the MCP framework and data structures for all LLM operations
    - Follows standardized communication protocols for language models

    ### Role in the System:
    - Provides high-level strategic guidance for testing
    - Complements action generation strategies with broader insights
    - Adapts to different application contexts
    - Guides exploration toward areas with monitored operations
    - Helps overcome exploration plateaus
    - Implements standard MCP interfaces for consistent LLM interactions
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None,
                 model_type: str = "ollama", model_name: str = "llama3.2:3b"):
        """
        Initialize the LLM service.

        Args:
            static_data: Optional static analysis data
            model_type: Type of LLM to use (ollama, huggingface, etc.)
            model_name: Name of the model to use
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.llm.service",
            {CONTEXT_COMPONENT: "LLMService"}
        )

        # Initialize error handler
        self.error_handler = ErrorHandler.get_instance()

        # Initialize performance monitor
        self.performance_monitor = PerformanceMonitor.get_instance()

        # Store static data
        self.static_data = static_data

        # Initialize LLM components
        self.prompt_manager = PromptManager()
        self.context_builder = ContextBuilder(static_data)
        self.directive_parser = DirectiveParser()

        # Initialize LLM model
        self.model_type = model_type
        self.model_name = model_name
        self.model = self._initialize_model(model_type, model_name)

        # Create MCP configuration
        self.model_config = MCPConfiguration(
            temperature=0.7,
            max_tokens=800,
            model_type=model_type,
            model_name=model_name
        )

        # Initialize cache
        self.query_cache: Dict[str, Dict[str, Any]] = {}
        self.max_cache_size = 100
        self.cache_expiry = 3600  # 1 hour in seconds

        self.logger.info(f"Initialized LLM service with {model_type}/{model_name} using MCP")

    def _initialize_model(self, model_type: str, model_name: str) -> Optional[LanguageModel]:
        """
        Initialize the LLM model using ComponentConfigurator.

        Args:
            model_type: Type of LLM to use
            model_name: Name of the model to use

        Returns:
            Initialized LanguageModel instance or None if initialization fails
        """
        try:
            self.logger.info(f"Initializing LLM: {model_type}/{model_name}")

            # Use ComponentConfigurator to create the model
            configurator = ComponentConfigurator(self.static_data)
            configurator.set_llm(
                model_type, 
                model_name,
                temperature=0.7,  # Default temperature
                max_tokens=800    # Default max tokens
            )
            model = configurator.create_llm()

            self.logger.info(f"Successfully initialized model: {model}")
            return model

        except Exception as e:
            self.logger.error(f"Failed to initialize model: {e}")
            from rvandroid.util.exceptions import RVAndroidError
            error = RVAndroidError(f"LLM initialization error: {str(e)}")
            self.error_handler.handle_error(
                error, 
                context={"model_type": model_type, "model_name": model_name}
            )
            return None

    @retry(max_attempts=3, retry_exceptions=[RVAndroidError])
    def get_strategic_guidance(self, query_type: str, state_data: Dict[str, Any],
                              exploration_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get strategic guidance from the LLM based on the current state and context.

        Args:
            query_type: Type of guidance to request (e.g., "exploration", "security", "general")
            state_data: Current application state data
            exploration_context: Additional context about the exploration status

        Returns:
            Dictionary with strategic guidance and directives
        """
        if not self.model:
            self.logger.warning("LLM model not initialized, returning empty guidance")
            return self._generate_fallback_guidance(query_type)

        # Check cache first
        cache_key = self._generate_cache_key(query_type, state_data, exploration_context)
        if cache_key in self.query_cache:
            cached_result = self.query_cache[cache_key]
            # Check if cached result is still valid
            if time.time() - cached_result["timestamp"] < self.cache_expiry:
                self.logger.debug(f"Using cached result for {query_type} guidance")
                self.performance_monitor.record_metric("cache_hit", 1, {"query_type": query_type})
                return cached_result["result"]

        # Measure performance
        with self.performance_monitor.measure_time("llm_guidance_generation"):
            try:
                # Prepare context for the model
                context = self.context_builder.build_context(state_data, exploration_context)

                # Generate MCP messages
                messages = self.prompt_manager.generate_mcp_messages(query_type, context)

                # Set max_tokens
                max_tokens = self.prompt_manager.get_max_tokens(query_type)
                self.model_config.max_tokens = max_tokens

                # Generate response from the model using MCP
                self.logger.info(f"Requesting {query_type} guidance from LLM using MCP")
                
                # Measure LLM call time
                with self.performance_monitor.measure_time("llm_call"):
                    # Use MCP generate_sync method
                    response_message = self.model.generate_sync(messages, self.model_config)
                    response = response_message.get_text_content()

                # Parse directives from response
                directives = self.directive_parser.parse_directives(response)

                # Build result
                result = {
                    "query_type": query_type,
                    "guidance": response,
                    "directives": directives,
                    "timestamp": time.time()
                }

                # Cache result
                self._update_cache(cache_key, result)

                # Record perf metrics
                self.performance_monitor.record_metric(
                    "llm_response_length", 
                    len(response), 
                    {"query_type": query_type}
                )
                
                return result

            except Exception as e:
                self.logger.error(f"Error getting LLM guidance: {e}")
                self.error_handler.handle_error(
                    "llm_guidance_error", 
                    str(e), 
                    context={"query_type": query_type}
                )
                # Fall back to default guidance
                return self._generate_fallback_guidance(query_type)

    def get_action_feedback(self, action_data: Dict[str, Any], result: Dict[str, Any],
                           state_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get feedback on an action result from the LLM.

        Args:
            action_data: Data about the action that was executed
            result: Result of the action execution
            state_data: Current application state data

        Returns:
            Dictionary with feedback about the action
        """
        if not self.model:
            self.logger.warning("LLM model not initialized, returning empty feedback")
            return {"feedback": "No model available for feedback", "suggestions": []}

        try:
            # Prepare context for the model
            context = self.context_builder.build_action_context(action_data, result, state_data)

            # Generate MCP messages
            messages = self.prompt_manager.generate_mcp_messages("action_feedback", context)

            # Get max_tokens
            max_tokens = self.prompt_manager.get_max_tokens("action_feedback")
            self.model_config.max_tokens = max_tokens

            # Generate response from the model using MCP
            self.logger.info("Requesting action feedback from LLM using MCP")
            
            # Use MCP generate_sync method
            response_message = self.model.generate_sync(messages, self.model_config)
            response = response_message.get_text_content()

            # Parse suggestions from response
            suggestions = self.directive_parser.parse_suggestions(response)

            # Record perf metrics
            self.performance_monitor.record_metric(
                "feedback_response_length", 
                len(response), 
                {"action_id": action_data.get("id", "unknown")}
            )

            return {
                "feedback": response,
                "suggestions": suggestions
            }

        except Exception as e:
            self.logger.error(f"Error getting action feedback: {e}")
            self.error_handler.handle_error(
                "action_feedback_error", 
                str(e), 
                context={"action_id": action_data.get("id", "unknown")}
            )
            return {"feedback": "Error getting feedback", "suggestions": []}

    def get_exploration_strategy(self, state_data: Dict[str, Any],
                                exploration_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get exploration strategy recommendations from the LLM.

        Args:
            state_data: Current application state data
            exploration_history: History of recent exploration states and actions

        Returns:
            Dictionary with exploration strategy recommendations
        """
        if not self.model:
            self.logger.warning("LLM model not initialized, returning default strategy")
            return {"strategy": "random", "rationale": "No model available for guidance"}

        try:
            # Prepare context for the model
            context = self.context_builder.build_strategy_context(state_data, exploration_history)

            # Generate MCP messages
            messages = self.prompt_manager.generate_mcp_messages("strategy", context)

            # Get max_tokens
            max_tokens = self.prompt_manager.get_max_tokens("strategy")
            self.model_config.max_tokens = max_tokens

            # Generate response from the model using MCP
            self.logger.info("Requesting exploration strategy from LLM using MCP")
            
            # Use MCP generate_sync method
            response_message = self.model.generate_sync(messages, self.model_config)
            response = response_message.get_text_content()

            # Parse strategy from response
            strategy = self.directive_parser.parse_strategy(response)

            # Record perf metrics
            self.performance_monitor.record_metric(
                "strategy_response_length", 
                len(response), 
                {"activity": state_data.get("activity", "unknown")}
            )

            return strategy

        except Exception as e:
            self.logger.error(f"Error getting exploration strategy: {e}")
            self.error_handler.handle_error(
                "strategy_error", 
                str(e), 
                context={"activity": state_data.get("activity", "unknown")}
            )
            return {"strategy": "random", "rationale": "Error in strategy generation"}

    def interpret_monitored_operations(self, state_data: Dict[str, Any],
                                     monitored_operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get interpretation of monitored operations from the LLM.

        Args:
            state_data: Current application state data
            monitored_operations: List of operations being monitored in the current state

        Returns:
            Dictionary with monitored operations interpretation
        """
        if not self.model:
            self.logger.warning("LLM model not initialized, returning default monitored operations interpretation")
            return {"risk_level": "unknown", "recommendations": []}

        try:
            # Prepare context for the model
            context = self.context_builder.build_monitored_operations_context(state_data, monitored_operations)

            # Generate MCP messages
            messages = self.prompt_manager.generate_mcp_messages("monitored_operations", context)

            # Get max_tokens
            max_tokens = self.prompt_manager.get_max_tokens("monitored_operations")
            self.model_config.max_tokens = max_tokens

            # Generate response from the model using MCP
            self.logger.info("Requesting monitored operations interpretation from LLM using MCP")
            
            # Use MCP generate_sync method
            response_message = self.model.generate_sync(messages, self.model_config)
            response = response_message.get_text_content()

            # Parse monitored operations interpretation from response
            interpretation = self.directive_parser.parse_monitored_operations_interpretation(response)

            # Record perf metrics
            self.performance_monitor.record_metric(
                "monitored_operations_response_length", 
                len(response), 
                {"activity": state_data.get("activity", "unknown")}
            )

            return interpretation

        except Exception as e:
            self.logger.error(f"Error interpreting monitored operations: {e}")
            self.error_handler.handle_error(
                "monitored_operations_interpretation_error", 
                str(e), 
                context={"activity": state_data.get("activity", "unknown")}
            )
            return {"risk_level": "unknown", "recommendations": []}

    def _generate_cache_key(self, query_type: str, state_data: Dict[str, Any],
                           context: Dict[str, Any]) -> str:
        """
        Generate a cache key for a query.

        Args:
            query_type: Type of guidance requested
            state_data: Current application state data
            context: Exploration context

        Returns:
            Cache key string
        """
        # Use state fingerprint and important context elements for the key
        fingerprint = state_data.get("fingerprint", "unknown")
        activity = state_data.get("activity", "unknown")
        phase = context.get("exploration_phase", "unknown")

        return f"{query_type}:{fingerprint}:{activity}:{phase}"

    def _update_cache(self, key: str, result: Dict[str, Any]) -> None:
        """
        Update the query cache with a new result.

        Args:
            key: Cache key
            result: Query result
        """
        # Add timestamp to result
        cache_entry = {
            "timestamp": time.time(),
            "result": result
        }

        # Add to cache
        self.query_cache[key] = cache_entry

        # Trim cache if it's too large
        if len(self.query_cache) > self.max_cache_size:
            # Remove oldest entries
            oldest_keys = sorted(self.query_cache.keys(),
                                key=lambda k: self.query_cache[k]["timestamp"])[:10]
            for old_key in oldest_keys:
                del self.query_cache[old_key]

    def _generate_fallback_guidance(self, query_type: str) -> Dict[str, Any]:
        """
        Generate fallback guidance when LLM is unavailable.

        Args:
            query_type: Type of guidance requested

        Returns:
            Dictionary with fallback guidance
        """
        if query_type == "exploration":
            return {
                "query_type": "exploration",
                "guidance": "Explore UI elements systematically. Focus on interactive elements.",
                "directives": [
                    {"type": "explore", "target": "interactive_elements", "priority": "high"},
                    {"type": "strategy", "name": "systematic", "duration": 300}
                ],
                "timestamp": time.time()
            }
        elif query_type == "monitored_operations":
            return {
                "query_type": "monitored_operations",
                "guidance": "Focus on input validation and API usage patterns.",
                "directives": [
                    {"type": "focus", "target": "input_validation", "priority": "high"},
                    {"type": "focus", "target": "api_usage", "priority": "high"}
                ],
                "timestamp": time.time()
            }
        else:
            return {
                "query_type": query_type,
                "guidance": "Continue with standard exploration approach.",
                "directives": [
                    {"type": "explore", "target": "all", "priority": "medium"}
                ],
                "timestamp": time.time()
            }

    def cleanup(self) -> None:
        """Clean up resources used by the LLM service."""
        if self.model:
            try:
                if hasattr(self.model, 'clean'):
                    self.model.clean()
                self.logger.info("LLM model resources cleaned up")
            except Exception as e:
                self.logger.error(f"Error cleaning up LLM model: {e}")
                self.error_handler.handle_error(
                    "llm_cleanup_error", 
                    str(e), 
                    context={"model_type": self.model_type, "model_name": self.model_name}
                )