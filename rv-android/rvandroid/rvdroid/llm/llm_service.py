# rvandroid/rvdroid/llm/llm_service.py
"""
LLM service for RVDroid.

This module provides a service for integrating Large Language Models (LLMs)
into RVDroid's testing workflow, enabling strategic guidance for exploration.
"""

import time
from typing import Dict, Any, List, Optional

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.llm.llm import LanguageModel
from rvandroid.llm.model_factory import ModelFactory
from rvandroid.rvdroid.llm.context.context_builder import ContextBuilder
from rvandroid.rvdroid.llm.directives.directive_parser import DirectiveParser
from rvandroid.rvdroid.llm.prompts.prompt_manager import PromptManager
from rvandroid.util.error import retry
from rvandroid.util.exceptions import RVAndroidError
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.performance_monitor import PerformanceMonitor


class LLMService:
    """
    Service for integrating LLMs into RVDroid's testing workflow.

    ### Architectural Decisions:
    - Implements a central service for LLM interactions
    - Uses a layered architecture with prompt management, context preparation, and directive parsing
    - Provides efficient caching to minimize redundant queries
    - Handles error recovery and fallback mechanisms
    - Reuses the existing LLM abstractions from rv-android

    ### Role in the System:
    - Provides high-level strategic guidance for testing
    - Complements action generation strategies with broader insights
    - Adapts to different application contexts
    - Guides exploration toward security-sensitive areas
    - Helps overcome exploration plateaus

    ### Key Considerations:
    - Token efficiency for prompts to minimize costs
    - Intermittent LLM consultation rather than per-action decisions
    - Fallback mechanisms when LLM is unavailable or unhelpful
    - Proper logging of interactions for analysis
    - Integration with existing components
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None,
                 model_type: str = "ollama", model_name: str = "mistral:7b"):
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

        # Initialize cache
        self.query_cache: Dict[str, Dict[str, Any]] = {}
        self.max_cache_size = 100
        self.cache_expiry = 3600  # 1 hour in seconds

        self.logger.info(f"Initialized LLM service with {model_type}/{model_name}")

    def _initialize_model(self, model_type: str, model_name: str) -> Optional[LanguageModel]:
        """
        Initialize the LLM model.

        Args:
            model_type: Type of LLM to use
            model_name: Name of the model to use

        Returns:
            Initialized LanguageModel instance or None if initialization fails
        """
        try:
            self.logger.info(f"Initializing LLM: {model_type}/{model_name}")

            # Use the existing ModelFactory to create the model
            model = ModelFactory.create(model_type, model_name)

            self.logger.info(f"Successfully initialized LLM: {model}")
            return model

        except Exception as e:
            self.logger.error(f"Failed to initialize LLM: {e}")
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
                return cached_result["result"]

        # Measure performance
        with self.performance_monitor.measure_time("llm_guidance_generation"):
            try:
                # Prepare context for the model
                context = self.context_builder.build_context(state_data, exploration_context)

                # Generate prompt for the model
                prompt = self.prompt_manager.generate_prompt(query_type, context)

                # Convert prompt to messages format
                messages = [
                    {"role": "system", "content": prompt["system"]},
                    {"role": "user", "content": prompt["user"]}
                ]

                # Generate response from the model
                self.logger.info(f"Requesting {query_type} guidance from LLM")
                max_tokens = prompt.get("max_tokens", 800)

                response = self.model.generate(messages, max_new_tokens=max_tokens)

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

                return result

            except Exception as e:
                self.logger.error(f"Error getting LLM guidance: {e}")
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

            # Generate prompt for feedback
            prompt = self.prompt_manager.generate_prompt("action_feedback", context)

            # Convert prompt to messages format
            messages = [
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": prompt["user"]}
            ]

            # Generate response from the model
            self.logger.info("Requesting action feedback from LLM")
            response = self.model.generate(messages, max_new_tokens=400)

            # Parse suggestions from response
            suggestions = self.directive_parser.parse_suggestions(response)

            return {
                "feedback": response,
                "suggestions": suggestions
            }

        except Exception as e:
            self.logger.error(f"Error getting action feedback: {e}")
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

            # Generate prompt for strategy
            prompt = self.prompt_manager.generate_prompt("strategy", context)

            # Convert prompt to messages format
            messages = [
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": prompt["user"]}
            ]

            # Generate response from the model
            self.logger.info("Requesting exploration strategy from LLM")
            response = self.model.generate(messages, max_new_tokens=300)

            # Parse strategy from response
            strategy = self.directive_parser.parse_strategy(response)

            return strategy

        except Exception as e:
            self.logger.error(f"Error getting exploration strategy: {e}")
            return {"strategy": "random", "rationale": "Error in strategy generation"}

    def interpret_security_context(self, state_data: Dict[str, Any],
                                   security_operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get security context interpretation from the LLM.

        Args:
            state_data: Current application state data
            security_operations: List of security operations available in current state

        Returns:
            Dictionary with security context interpretation
        """
        if not self.model:
            self.logger.warning("LLM model not initialized, returning default security context")
            return {"risk_level": "unknown", "recommendations": []}

        try:
            # Prepare context for the model
            context = self.context_builder.build_security_context(state_data, security_operations)

            # Generate prompt for security interpretation
            prompt = self.prompt_manager.generate_prompt("security", context)

            # Convert prompt to messages format
            messages = [
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": prompt["user"]}
            ]

            # Generate response from the model
            self.logger.info("Requesting security context interpretation from LLM")
            response = self.model.generate(messages, max_new_tokens=500)

            # Parse security interpretation from response
            interpretation = self.directive_parser.parse_security_interpretation(response)

            return interpretation

        except Exception as e:
            self.logger.error(f"Error interpreting security context: {e}")
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
        elif query_type == "security":
            return {
                "query_type": "security",
                "guidance": "Focus on input validation and authentication flows.",
                "directives": [
                    {"type": "focus", "target": "input_validation", "priority": "high"},
                    {"type": "focus", "target": "authentication", "priority": "high"}
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
                self.model.clean()
                self.logger.info("LLM model resources cleaned up")
            except Exception as e:
                self.logger.error(f"Error cleaning up LLM model: {e}")
