"""
LangChain Service for RVAgent - Direct LLM integration.

Implementation EXACT according to plan with Phase 0 validated parameters.
LangChain + Ollama integration with Qwen 2.5VL 7B using scientifically validated parameters.
"""
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate

from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.error.error_handler import ErrorHandler

from ..constants import RVAgentConstants


# No Pydantic models needed - LLM returns JSON directly as per plan


@dataclass
class LLMMetrics:
    """Track LLM performance metrics."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_response_time: float = 0.0
    json_parse_failures: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls

    @property
    def average_response_time(self) -> float:
        if self.successful_calls == 0:
            return 0.0
        return self.total_response_time / self.successful_calls


class LangChainService:
    """
    LangChain service for RVAgent with Phase 0 validated parameters.

    SUBPROCESS ISOLATED PROCESS:
    - LoggingManager.get_instance() with own subprocess instance
    - ErrorHandler.get_instance() with own subprocess instance
    - Ollama direct integration (no intermediate server)
    - Phase 0 parameters: temp=0.25, top_p=0.8, top_k=50

    Target: br.unb.cic.cryptoapp - ReAct reasoning for autonomous decisions
    """

    def __init__(self, model_name: str = RVAgentConstants.DEFAULT_MODEL):
        """Initialize LangChain service with validated Phase 0 parameters."""

        # Process isolation - LoggingManager with own instance
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_agent.llm.langchain_service",
            {"component": "LangChainService"}
        )

        # ErrorHandler decorators available in subprocess
        self.error_handler = ErrorHandler.get_instance()

        self.model_name = model_name
        self.metrics = LLMMetrics()

        # Initialize Ollama with Phase 0 validated parameters
        self.llm = None
        self.prompt_template = None

        # Initialize components
        self._initialize_llm()
        self._initialize_prompt_template()

        self.logger.info(f"[RVAGENT_DEBUG] LangChainService initialized with {model_name}")

    def _initialize_llm(self) -> None:
        """Initialize Ollama LLM with Phase 0 validated parameters."""
        try:
            self.logger.info(f"[RVAGENT_DEBUG] Initializing Ollama with {self.model_name}...")

            # Phase 0 validated parameters (12,193 tests)
            self.llm = Ollama(
                model=self.model_name,
                temperature=RVAgentConstants.DEFAULT_TEMPERATURE,  # 0.25
                top_p=RVAgentConstants.DEFAULT_TOP_P,              # 0.8
                top_k=RVAgentConstants.DEFAULT_TOP_K,              # 50
                num_predict=RVAgentConstants.DEFAULT_MAX_TOKENS,   # 800
                format="json"  # Force JSON output
            )

            # Test connection
            test_response = self.llm.invoke("Test connection. Respond with: {\"status\": \"ready\"}")
            self.logger.info(f"[RVAGENT_DEBUG] ✅ Ollama connection test: {test_response[:100]}...")

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Ollama initialization failed: {e}")
            raise

    def _initialize_prompt_template(self) -> None:
        """Initialize ReAct prompt template."""
        try:
            # ReAct prompt template seguindo o plano
            react_template = """You are an autonomous Android testing agent using the ReAct (Reasoning + Acting) pattern.

Your task is to explore and test the Android application systematically.

CURRENT UI STATE:
Activity: {activity}
Package: {current_package}
Elements available: {element_count}

UI ELEMENTS (with coordinates):
{formatted_elements}

MEMORY CONTEXT:
{memory_context}

COVERAGE STATUS:
- Tested elements: {tested_elements}
- Untested elements: {untested_elements}
- Coverage: {coverage_percentage:.1f}%

EXPLORATION GUIDANCE:
{exploration_suggestions}

REACT DECISION:
Think step by step:
1. OBSERVE: What do you see on the current screen?
2. REASON: What should be tested next based on coverage and memory?
3. ACT: Choose the best action to maximize testing coverage.

CRITICAL REQUIREMENTS:
- Use coordinates EXACTLY as shown "at position (x, y)"
- Prioritize untested elements ([UNTESTED] annotation)
- Avoid well-tested elements ([WELL-TESTED] annotation)
- Provide clear reasoning for your decision

Respond with valid JSON only:
{format_instructions}"""

            self.prompt_template = PromptTemplate(
                template=react_template,
                input_variables=[
                    "activity", "current_package", "element_count", "formatted_elements",
                    "memory_context", "tested_elements", "untested_elements",
                    "coverage_percentage", "exploration_suggestions"
                ],
                partial_variables={"format_instructions": "Return a JSON array with 1-3 actions: [{'action_type': 'click|set_text|scroll|back', 'element_id': 'identifier', 'coordinates': [x,y], 'text': 'if_needed', 'reasoning': 'explanation'}]"}
            )

            self.logger.debug("[RVAGENT_DEBUG] ReAct prompt template initialized")

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Prompt template initialization failed: {e}")
            raise

    def generate_react_decision(self, ui_state: Dict[str, Any],
                              memory_context: str,
                              coverage_stats: Dict[str, Any],
                              exploration_suggestions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Generate ReAct decision using LLM.

        Args:
            ui_state: Current UI state from DeviceInterface
            memory_context: Formatted memory context
            coverage_stats: UI coverage statistics
            exploration_suggestions: Suggested exploration actions

        Returns:
            ReactDecision as dictionary or None if failed
        """
        try:
            start_time = time.time()
            self.metrics.total_calls += 1

            # Prepare prompt variables
            prompt_vars = {
                "activity": ui_state.get("activity", "unknown"),
                "current_package": ui_state.get("current_package", "unknown"),
                "element_count": ui_state.get("element_count", 0),
                "formatted_elements": ui_state.get("formatted_elements", "No elements available"),
                "memory_context": memory_context,
                "tested_elements": coverage_stats.get("tested_elements", 0),
                "untested_elements": coverage_stats.get("untested_elements", 0),
                "coverage_percentage": coverage_stats.get("coverage_percentage", 0.0),
                "exploration_suggestions": self._format_exploration_suggestions(exploration_suggestions)
            }

            self.logger.debug(f"[RVAGENT_DEBUG] Generating ReAct decision for {prompt_vars['activity']}")

            # Generate prompt
            formatted_prompt = self.prompt_template.format(**prompt_vars)

            # Log prompt for debugging (truncated)
            self.logger.debug(f"[RVAGENT_DEBUG] Prompt (first 200 chars): {formatted_prompt[:200]}...")

            # Call LLM
            response = self.llm.invoke(formatted_prompt)
            response_time = time.time() - start_time

            self.logger.debug(f"[RVAGENT_DEBUG] LLM response received ({response_time:.2f}s): {response[:200]}...")

            # Parse JSON response directly
            try:
                import json
                parsed_response = json.loads(response.strip())
                # Ensure it's a list of actions
                if not isinstance(parsed_response, list):
                    parsed_response = [parsed_response]
                decision_dict = {"actions": parsed_response}

                # Update metrics
                self.metrics.successful_calls += 1
                self.metrics.total_response_time += response_time

                action_count = len(parsed_response)
                self.logger.info(f"[RVAGENT_DEBUG] ✅ ReAct decision generated: "
                               f"{action_count} actions")

                for i, action in enumerate(parsed_response):
                    action_type = action.get('action_type', 'unknown')
                    confidence = action.get('confidence', 0.0)
                    self.logger.info(f"[RVAGENT_DEBUG]   Action {i+1}: {action_type} "
                                   f"(confidence: {confidence:.2f})")

                return decision_dict

            except Exception as parse_error:
                self.logger.error(f"[RVAGENT_DEBUG] JSON parsing failed: {parse_error}")
                self.logger.error(f"[RVAGENT_DEBUG] Raw response: {response}")
                self.metrics.json_parse_failures += 1
                self.metrics.failed_calls += 1
                return None

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] ReAct decision generation failed: {e}")
            self.metrics.failed_calls += 1
            return None

    def _format_exploration_suggestions(self, suggestions: List[Dict[str, Any]]) -> str:
        """Format exploration suggestions for prompt."""
        if not suggestions:
            return "No specific suggestions available."

        formatted = []
        for i, suggestion in enumerate(suggestions[:3], 1):
            suggestion_type = suggestion.get("suggestion", "unknown")
            reason = suggestion.get("reason", "no reason provided")
            priority = suggestion.get("priority", "medium")

            formatted.append(f"{i}. {suggestion_type} ({priority} priority): {reason}")

        return "\n".join(formatted)

    def test_llm_connection(self) -> bool:
        """Test LLM connection and basic functionality."""
        try:
            self.logger.info("[RVAGENT_DEBUG] Testing LLM connection...")

            test_prompt = """Test the ReAct pattern with this simple scenario:

CURRENT UI STATE:
Activity: TestActivity
Elements: 3 buttons available
UI ELEMENTS: 1. "Submit" Button at position (100, 200)
             2. "Cancel" Button at position (200, 200)
             3. "Help" Button at position (300, 200)

MEMORY CONTEXT: No previous actions.
COVERAGE: 0% tested.

Use ReAct reasoning and respond with JSON format for testing connectivity."""

            response = self.llm.invoke(test_prompt)

            self.logger.info(f"[RVAGENT_DEBUG] Test response: {response[:150]}...")

            # Try to parse as JSON
            try:
                test_parsed = json.loads(response)
                self.logger.info("[RVAGENT_DEBUG] ✅ JSON parsing successful")
                return True
            except:
                self.logger.warning("[RVAGENT_DEBUG] ⚠️ JSON parsing failed but connection works")
                return True

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] LLM connection test failed: {e}")
            return False

    def get_metrics(self) -> Dict[str, Any]:
        """Get LLM performance metrics."""
        return {
            "total_calls": self.metrics.total_calls,
            "successful_calls": self.metrics.successful_calls,
            "failed_calls": self.metrics.failed_calls,
            "success_rate": self.metrics.success_rate,
            "average_response_time": self.metrics.average_response_time,
            "json_parse_failures": self.metrics.json_parse_failures,
            "model_name": self.model_name,
            "parameters": {
                "temperature": RVAgentConstants.DEFAULT_TEMPERATURE,
                "top_p": RVAgentConstants.DEFAULT_TOP_P,
                "top_k": RVAgentConstants.DEFAULT_TOP_K,
                "max_tokens": RVAgentConstants.DEFAULT_MAX_TOKENS
            }
        }

    def reset_metrics(self) -> None:
        """Reset performance metrics."""
        self.logger.info("[RVAGENT_DEBUG] Resetting LLM metrics...")
        self.metrics = LLMMetrics()
        self.logger.info("[RVAGENT_DEBUG] LLM metrics reset complete")