"""
Decision routing management for multi-mode agent operation.

Routes exploration decisions between LLM-guided and algorithmic modes
based on configuration, validation results, and loop detection.
"""

import logging
import random
from typing import Dict, Any, Optional

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.routing.loop_detector import LoopDetector
from rv_agent.routing.fallback_manager import FallbackManager
from rv_agent.strategies.base_strategy import ExplorationStrategy
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription


class RoutingManager:
    """
    Routes decisions between LLM and algorithmic strategies.

    ### Architectural Decisions:
    - Supports three modes: pure_algorithm, llm_only, multimode
    - Implements probabilistic routing for multimode
    - Integrates loop detection for validation
    - Provides fallback when LLM fails
    - Tracks decision counters for reporting

    ### Role in the System:
    - Central decision routing logic
    - Coordinates LLM and algorithmic paths
    - Validates LLM actions against loops
    - Triggers fallback when needed
    - Maintains exploration mode statistics

    ### Integration Points:
    - Used by RVAgent decision_router node
    - Uses LoopDetector for validation
    - Uses FallbackManager for algorithmic fallback
    - Accesses ExplorationStrategy for pure_algorithm mode
    - Reports routing decisions to agent state
    """

    def __init__(
        self,
        config: RVAgentConfig,
        loop_detector: LoopDetector,
        fallback_manager: FallbackManager,
        exploration_strategy: Optional[ExplorationStrategy] = None
    ):
        """
        Initialize routing manager.

        Args:
            config: Agent configuration
            loop_detector: Loop detection component
            fallback_manager: Fallback management component
            exploration_strategy: Strategy for pure_algorithm/multimode fallback
        """
        self.config = config
        self.loop_detector = loop_detector
        self.fallback_manager = fallback_manager
        self.exploration_strategy = exploration_strategy

        # Decision counters
        self.llm_decisions = 0
        self.algorithm_decisions = 0

        self.logger = logging.getLogger(__name__)

    def route_decision(self, iteration: int) -> str:
        """
        Determine which path to take for current iteration.

        Args:
            iteration: Current iteration number

        Returns:
            Decision path: "llm", "algorithm", or "end"
        """
        mode = self.config.get_agent_mode()

        self.logger.info(f"Routing decision (mode={mode}, iteration={iteration})")

        if mode == "pure_algorithm":
            self.algorithm_decisions += 1
            self.logger.info("Mode: pure_algorithm → algorithm path")
            return "algorithm"

        elif mode == "llm_only":
            self.llm_decisions += 1
            self.logger.info("Mode: llm_only → LLM path")
            return "llm"

        elif mode == "multimode":
            # Probabilistic routing
            llm_probability = self.config.llm_probability

            if random.random() < llm_probability:
                self.llm_decisions += 1
                self.logger.info(
                    f"Mode: multimode (p={llm_probability}) → LLM path "
                    f"(LLM={self.llm_decisions}, alg={self.algorithm_decisions})"
                )
                return "llm"
            else:
                self.algorithm_decisions += 1
                self.logger.info(
                    f"Mode: multimode (p={llm_probability}) → algorithm path "
                    f"(LLM={self.llm_decisions}, alg={self.algorithm_decisions})"
                )
                return "algorithm"

        else:
            self.logger.warning(f"Unknown mode: {mode}, defaulting to algorithm")
            self.algorithm_decisions += 1
            return "algorithm"

    def validate_llm_action(
        self,
        llm_action: Optional[Dict[str, Any]],
        recent_actions: list,
        has_tool_calls: bool
    ) -> Dict[str, Any]:
        """
        Validate LLM-generated action and determine path.

        Args:
            llm_action: Extracted action from LLM response
            recent_actions: Recent action history
            has_tool_calls: Whether LLM generated tool calls

        Returns:
            Dictionary with:
            - validation_path: "execute" or "algorithm_fallback"
            - loop_detected: Whether loop was detected
            - used_fallback: Whether fallback triggered
            - fallback_reason: Reason for fallback (if applicable)
            - current_action: Action to preserve for memory
        """
        # Check for missing tool calls
        if not has_tool_calls:
            self.logger.warning("No tool calls from LLM → algorithm fallback")
            self.algorithm_decisions += 1  # Count as algorithm decision
            return {
                "validation_path": "algorithm_fallback",
                "loop_detected": True,
                "used_fallback": True,
                "fallback_reason": "no_tool_calls"
            }

        # Check for invalid action
        if not llm_action:
            self.logger.warning("Could not extract action → algorithm fallback")
            self.algorithm_decisions += 1
            return {
                "validation_path": "algorithm_fallback",
                "loop_detected": True,
                "used_fallback": True,
                "fallback_reason": "invalid_action"
            }

        # Loop detection
        is_loop, consecutive_count, threshold = self.loop_detector.detect_loop(
            recent_actions,
            llm_action
        )

        if is_loop:
            action_type = llm_action.get("action_type", "UNKNOWN")
            self.logger.warning(
                f"Loop: {action_type} repeated {consecutive_count}x "
                f"(threshold={threshold}) → algorithm fallback"
            )
            self.algorithm_decisions += 1
            return {
                "validation_path": "algorithm_fallback",
                "loop_detected": True,
                "used_fallback": True,
                "fallback_reason": "loop_detected",
                "current_action": llm_action
            }

        # Valid - proceed to execute
        action_type = llm_action.get("action_type", "UNKNOWN")
        self.logger.debug(
            f"Validation: {action_type} valid (count={consecutive_count})"
        )

        return {
            "validation_path": "execute",
            "loop_detected": False,
            "used_fallback": False,
            "current_action": llm_action
        }

    def get_decision_counters(self) -> Dict[str, int]:
        """
        Get current decision counter values.

        Returns:
            Dictionary with llm_decisions and algorithm_decisions
        """
        return {
            "llm_decisions": self.llm_decisions,
            "algorithm_decisions": self.algorithm_decisions
        }
