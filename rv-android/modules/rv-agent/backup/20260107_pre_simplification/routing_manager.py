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
    - Recovery mode after consecutive LLM failures

    ### Role in the System:
    - Central decision routing logic
    - Coordinates LLM and algorithmic paths
    - Validates LLM actions against loops
    - Triggers fallback when needed
    - Maintains exploration mode statistics
    - Activates recovery mode on persistent failures

    ### Integration Points:
    - Used by RVAgent decision_router node
    - Uses LoopDetector for validation
    - Uses FallbackManager for algorithmic fallback
    - Accesses ExplorationStrategy for pure_algorithm mode
    - Reports routing decisions to agent state
    """

    # Recovery mode thresholds
    RECOVERY_FAILURE_THRESHOLD = 3  # Consecutive failures to trigger recovery
    RECOVERY_ACTION_COUNT = 10       # Actions in recovery mode

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
        self.verbose_counters = config.get_verbose_counters()

        # === PRIMARY COUNTERS (validate 70/30 proportion) ===
        # These track probabilistic routing decisions
        self.llm_executed = 0        # LLM decided AND executed successfully
        self.algorithm_chosen = 0    # Router probabilistically chose algorithm

        # === AUXILIARY COUNTERS (special cases - not in 70/30) ===
        # These track fallbacks and forced actions
        self.llm_fallback = 0        # LLM failed validation → algorithm executed
        self.forced_back_count = 0   # BACK forced by stuck detection
        self.recovery_actions_count = 0  # Actions during recovery mode

        # Recovery mode tracking
        self.consecutive_llm_failures = 0
        self.recovery_mode_active = False
        self.recovery_actions_remaining = 0

        # Algorithm fallback loop prevention
        self.consecutive_algorithm_fallbacks = 0
        self.MAX_ALGORITHM_FALLBACKS = 5  # Force BACK after this many

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

        # Check recovery mode first - overrides normal routing
        if self.recovery_mode_active:
            self.recovery_actions_remaining -= 1
            self.recovery_actions_count += 1  # Count recovery actions separately

            self.logger.warning(
                f"Recovery mode active: forcing algorithm "
                f"({self.recovery_actions_remaining} actions remaining)"
            )
            if self.verbose_counters:
                self.logger.warning(
                    f"[COUNTER] recovery_action++ (now={self.recovery_actions_count}) | "
                    f"remaining={self.recovery_actions_remaining} | "
                    f"consecutive_failures={self.consecutive_llm_failures} | "
                    f"llm_exec={self.llm_executed} | alg_chosen={self.algorithm_chosen}"
                )

            # Exit recovery mode when counter reaches zero
            if self.recovery_actions_remaining <= 0:
                self.recovery_mode_active = False
                self.logger.info("✅ Recovery mode completed, returning to normal routing")

            return "algorithm"

        if mode == "pure_algorithm":
            self.algorithm_chosen += 1
            self.logger.info("Mode: pure_algorithm → algorithm path")
            return "algorithm"

        elif mode == "llm_only":
            # Note: Will increment llm_executed only if validation succeeds
            self.logger.info("Mode: llm_only → LLM path")
            return "llm"

        elif mode == "multimode":
            # Probabilistic routing
            llm_probability = self.config.llm_probability

            if random.random() < llm_probability:
                # Note: Will increment llm_executed only if validation succeeds
                self.logger.info(
                    f"Mode: multimode (p={llm_probability}) → LLM path "
                    f"(LLM_exec={self.llm_executed}, alg_chosen={self.algorithm_chosen})"
                )
                return "llm"
            else:
                self.algorithm_chosen += 1
                self.logger.info(
                    f"Mode: multimode (p={llm_probability}) → algorithm path "
                    f"(LLM_exec={self.llm_executed}, alg_chosen={self.algorithm_chosen})"
                )
                return "algorithm"

        else:
            self.logger.warning(f"Unknown mode: {mode}, defaulting to algorithm")
            self.algorithm_chosen += 1
            return "algorithm"

    def validate_action(
        self,
        action: Optional[Dict[str, Any]],
        recent_actions: list,
        decision_maker: str = "llm"
    ) -> Dict[str, Any]:
        """
        Unified validation for actions from LLM or Algorithm.

        Uses shared dynamic state graph (recent_actions) to detect loops
        regardless of action source. Prevents duplication of validation logic.

        NOTE: In pure_algorithm mode, loop detection is DISABLED because
        RVAgent strategy has its own loop prevention mechanisms:
        - Backtracking when states exhausted
        - Successor tracking
        - Plateau detection

        Args:
            action: Action to validate (from LLM or Algorithm)
            recent_actions: Recent action history from dynamic graph
            decision_maker: Source of action ("llm" or "algorithm")

        Returns:
            Dictionary with:
            - validation_path: "execute" or "algorithm_fallback"
            - loop_detected: Whether loop was detected
            - used_fallback: Whether fallback triggered
            - fallback_reason: Reason for fallback (if applicable)
            - current_action: Action to preserve for memory
        """
        # In pure_algorithm mode, SKIP loop detection entirely
        # RVAgent has its own loop prevention through backtracking and successor tracking
        mode = self.config.get_agent_mode()
        if mode == "pure_algorithm":
            # Only check for missing action
            if not action or not action.get("action_type"):
                self.logger.warning(
                    f"No valid action from {decision_maker} in pure_algorithm mode → returning None"
                )
                return {
                    "validation_path": "execute",
                    "loop_detected": False,
                    "used_fallback": False,
                    "current_action": None
                }

            # Valid action - no loop detection in pure_algorithm mode
            self.logger.debug(
                f"pure_algorithm mode: skipping loop detection for {action.get('action_type')}"
            )
            return {
                "validation_path": "execute",
                "loop_detected": False,
                "used_fallback": False,
                "current_action": action
            }

        # For LLM and multimode: perform loop detection
        # Check for missing action (LLM without tool calls, or Algorithm returned None)
        # All actions MUST use unified format with action_type (from ActionNormalizer)
        action_valid = action and action.get("action_type")
        if not action_valid:
            # Check if we're stuck in algorithm fallback loop
            if decision_maker == "algorithm":
                self.consecutive_algorithm_fallbacks += 1
                if self.consecutive_algorithm_fallbacks >= self.MAX_ALGORITHM_FALLBACKS:
                    # Force BACK action to break the loop
                    self.logger.warning(
                        f"Algorithm exhausted ({self.consecutive_algorithm_fallbacks} fallbacks) → forcing BACK"
                    )
                    self.forced_back_count += 1
                    self.consecutive_algorithm_fallbacks = 0  # Reset counter
                    return {
                        "validation_path": "execute",
                        "loop_detected": True,
                        "used_fallback": True,
                        "fallback_reason": "algorithm_exhausted",
                        "current_action": {
                            "action_type": "BACK",
                            "x": 0,
                            "y": 0
                        }
                    }

            self.llm_fallback += 1
            action_repr = "None" if action is None else f"dict(action_type={action.get('action_type')})"
            self.logger.warning(
                f"No valid action from {decision_maker} (action={action_repr}) → algorithm fallback"
            )
            if self.verbose_counters:
                self.logger.warning(
                    f"[COUNTER] llm_fallback++ (now={self.llm_fallback}) | "
                    f"reason=no_valid_action | decision_maker={decision_maker} | "
                    f"llm_exec={self.llm_executed} | alg_chosen={self.algorithm_chosen}"
                )
            self._record_llm_failure()
            return {
                "validation_path": "algorithm_fallback",
                "loop_detected": True,
                "used_fallback": True,
                "fallback_reason": "no_valid_action"
            }

        # Loop detection (consecutive similar actions)
        is_loop, consecutive_count, threshold = self.loop_detector.detect_loop(
            recent_actions,
            action
        )

        if is_loop:
            action_type = action.get("action_type", "UNKNOWN")

            # Track algorithm fallback loop
            if decision_maker == "algorithm":
                self.consecutive_algorithm_fallbacks += 1
                if self.consecutive_algorithm_fallbacks >= self.MAX_ALGORITHM_FALLBACKS:
                    self.logger.warning(
                        f"Algorithm loop exhausted ({self.consecutive_algorithm_fallbacks} fallbacks) → forcing BACK"
                    )
                    self.forced_back_count += 1
                    self.consecutive_algorithm_fallbacks = 0
                    return {
                        "validation_path": "execute",
                        "loop_detected": True,
                        "used_fallback": True,
                        "fallback_reason": "loop_exhausted",
                        "current_action": {
                            "action_type": "BACK",
                            "x": 0,
                            "y": 0
                        }
                    }

            self.llm_fallback += 1
            self.logger.warning(
                f"Loop from {decision_maker}: {action_type} repeated {consecutive_count}x "
                f"(threshold={threshold}) → algorithm fallback"
            )
            if self.verbose_counters:
                self.logger.warning(
                    f"[COUNTER] llm_fallback++ (now={self.llm_fallback}) | "
                    f"reason=loop_detected | decision_maker={decision_maker} | action_type={action_type} | "
                    f"consecutive={consecutive_count} | threshold={threshold} | "
                    f"llm_exec={self.llm_executed} | alg_chosen={self.algorithm_chosen}"
                )
            self._record_llm_failure()
            return {
                "validation_path": "algorithm_fallback",
                "loop_detected": True,
                "used_fallback": True,
                "fallback_reason": "loop_detected",
                "current_action": action
            }

        # Action sequence repetition detection
        is_seq_repetition, pattern, repetitions = self.loop_detector.detect_action_sequence_repetition(
            recent_actions
        )

        if is_seq_repetition:
            # Track algorithm fallback loop
            if decision_maker == "algorithm":
                self.consecutive_algorithm_fallbacks += 1
                if self.consecutive_algorithm_fallbacks >= self.MAX_ALGORITHM_FALLBACKS:
                    self.logger.warning(
                        f"Algorithm sequence loop exhausted ({self.consecutive_algorithm_fallbacks} fallbacks) → forcing BACK"
                    )
                    self.forced_back_count += 1
                    self.consecutive_algorithm_fallbacks = 0
                    return {
                        "validation_path": "execute",
                        "loop_detected": True,
                        "used_fallback": True,
                        "fallback_reason": "sequence_loop_exhausted",
                        "current_action": {
                            "action_type": "BACK",
                            "x": 0,
                            "y": 0
                        }
                    }

            self.llm_fallback += 1
            self.logger.warning(
                f"Action sequence repetition from {decision_maker}: pattern {pattern} repeated {repetitions}x "
                f"→ algorithm fallback"
            )
            if self.verbose_counters:
                self.logger.warning(
                    f"[COUNTER] llm_fallback++ (now={self.llm_fallback}) | "
                    f"reason=action_sequence_repetition | decision_maker={decision_maker} | "
                    f"pattern={pattern} | repetitions={repetitions} | "
                    f"llm_exec={self.llm_executed} | alg_chosen={self.algorithm_chosen}"
                )
            self._record_llm_failure()
            return {
                "validation_path": "algorithm_fallback",
                "loop_detected": True,
                "used_fallback": True,
                "fallback_reason": "action_sequence_repetition",
                "current_action": action
            }

        # Spatial loop detection (CLICKs clustered in same area)
        is_spatial_loop = self.loop_detector.detect_spatial_loop(recent_actions)

        if is_spatial_loop:
            # Track algorithm fallback loop
            if decision_maker == "algorithm":
                self.consecutive_algorithm_fallbacks += 1
                if self.consecutive_algorithm_fallbacks >= self.MAX_ALGORITHM_FALLBACKS:
                    # Force BACK action to break the spatial loop
                    self.logger.warning(
                        f"Algorithm spatial loop exhausted ({self.consecutive_algorithm_fallbacks} fallbacks) → forcing BACK"
                    )
                    self.forced_back_count += 1
                    self.consecutive_algorithm_fallbacks = 0
                    return {
                        "validation_path": "execute",
                        "loop_detected": True,
                        "used_fallback": True,
                        "fallback_reason": "spatial_loop_exhausted",
                        "current_action": {
                            "action_type": "BACK",
                            "x": 0,
                            "y": 0
                        }
                    }

            self.llm_fallback += 1
            self.logger.warning(
                f"Spatial loop from {decision_maker}: CLICKs clustered in same area → algorithm fallback"
            )
            if self.verbose_counters:
                recent_clicks = [
                    (a.get("x"), a.get("y"))
                    for a in recent_actions[-5:]
                    if a.get("action_type") == "CLICK"
                ]
                self.logger.warning(
                    f"[COUNTER] llm_fallback++ (now={self.llm_fallback}) | "
                    f"reason=spatial_loop_detected | decision_maker={decision_maker} | recent_clicks={recent_clicks} | "
                    f"llm_exec={self.llm_executed} | alg_chosen={self.algorithm_chosen}"
                )
            self._record_llm_failure()
            return {
                "validation_path": "algorithm_fallback",
                "loop_detected": True,
                "used_fallback": True,
                "fallback_reason": "spatial_loop_detected",
                "current_action": action
            }

        # Valid - proceed to execute
        action_type = action.get("action_type", "UNKNOWN")
        self.logger.debug(
            f"Validation from {decision_maker}: {action_type} valid (count={consecutive_count})"
        )

        # Count as executed if from LLM (enters 70/30 proportion)
        if decision_maker == "llm":
            self.llm_executed += 1
            # Reset failure counter on successful LLM validation
            self._reset_llm_failures()

        # Reset algorithm fallback counter on successful validation
        if decision_maker == "algorithm":
            self.consecutive_algorithm_fallbacks = 0

        return {
            "validation_path": "execute",
            "loop_detected": False,
            "used_fallback": False,
            "current_action": action
        }

    def get_decision_counters(self) -> Dict[str, int]:
        """
        Get all decision counter values.

        Returns:
            Dictionary with primary counters (70/30 validation) and auxiliary counters
        """
        # Calculate proportions
        primary_total = self.llm_executed + self.algorithm_chosen
        llm_percentage = (self.llm_executed / primary_total * 100) if primary_total > 0 else 0
        algorithm_percentage = (self.algorithm_chosen / primary_total * 100) if primary_total > 0 else 0

        # Total actions (all counters)
        total_actions = (
            self.llm_executed +
            self.algorithm_chosen +
            self.llm_fallback +
            self.forced_back_count +
            self.recovery_actions_count
        )

        return {
            # Primary counters (validate 70/30)
            "llm_executed": self.llm_executed,
            "algorithm_chosen": self.algorithm_chosen,
            "llm_percentage": llm_percentage,
            "algorithm_percentage": algorithm_percentage,

            # Auxiliary counters (special cases)
            "llm_fallback": self.llm_fallback,
            "forced_back": self.forced_back_count,
            "recovery_actions": self.recovery_actions_count,

            # Totals
            "primary_total": primary_total,
            "total_actions": total_actions
        }

    def _record_llm_failure(self):
        """
        Record LLM failure and activate recovery mode if threshold reached.

        Increments consecutive failure counter and activates recovery mode
        after RECOVERY_FAILURE_THRESHOLD consecutive failures.
        """
        self.consecutive_llm_failures += 1

        if self.consecutive_llm_failures >= self.RECOVERY_FAILURE_THRESHOLD:
            if not self.recovery_mode_active:
                self.logger.warning(
                    f"⚠️  {self.consecutive_llm_failures} consecutive LLM failures → "
                    f"Activating recovery mode ({self.RECOVERY_ACTION_COUNT} algorithm actions)"
                )
                self.recovery_mode_active = True
                self.recovery_actions_remaining = self.RECOVERY_ACTION_COUNT

    def _reset_llm_failures(self):
        """
        Reset LLM failure counter on successful validation.

        Resets the consecutive failure counter when LLM generates
        a valid, non-loop action.
        """
        if self.consecutive_llm_failures > 0:
            self.logger.debug(
                f"✅ LLM success after {self.consecutive_llm_failures} failures, "
                "resetting counter"
            )
            self.consecutive_llm_failures = 0
