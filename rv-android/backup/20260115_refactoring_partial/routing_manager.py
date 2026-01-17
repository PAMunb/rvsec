"""
Decision routing management for multi-mode agent operation.

Routes exploration decisions between LLM-guided and algorithmic modes
based on configuration and validates actions against loop detection.
"""

import logging
import random
from typing import Dict, Any, Optional

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.routing.loop_detector import LoopDetector
from rv_agent.routing.fallback_manager import FallbackManager
from rv_agent.strategies.base_strategy import ExplorationStrategy


class RoutingManager:
    """
    Routes decisions between LLM and algorithmic strategies.

    Key Design Decisions:

    1. THREE EXECUTION MODES
       - pure_algorithm: Only algorithmic exploration (DFS/BFS), no LLM calls
       - llm_only: Only LLM-guided exploration, no algorithmic fallback
       - multimode: Probabilistic mix (default 70% LLM, 30% algorithm)

       WHY MULTIMODE: LLMs excel at semantic understanding (recognizing login forms,
       understanding UI context) but are expensive and can get stuck in loops.
       Algorithmic exploration is cheaper and systematic but lacks semantic understanding.
       The 70/30 mix balances coverage with cost-effectiveness.

    2. VALIDATION WITHOUT FALLBACK LOOPS
       Problem: If LLM action fails validation, routing to algorithm which routes
       back to LLM creates an infinite loop.
       Solution: Always return "execute" path. If validation fails, substitute
       a BACK action instead of the invalid action. No cycles, no fallback loops.

    3. LOOP DETECTION (for LLM mode only)
       The LLM can get stuck repeating the same action or clicking in the same area.
       We detect three types of loops:
       - Consecutive repetition: same action N times in a row
       - Sequence repetition: A-B-A-B-A-B pattern
       - Spatial clustering: clicks concentrated in small area

       WHY NOT FOR ALGORITHM: The algorithmic strategy has its own loop prevention
       (action marking, successor tracking, plateau detection). Adding loop detection
       would interfere with its systematic exploration.

    4. RESTART RECOVERY (inspired by APE/Fastbot)
       When the agent is stuck in the same state for MAX_BLOCKS_BEFORE_RESTART
       consecutive iterations, trigger app restart. This handles dead-end states
       that BACK cannot escape (modal dialogs, error screens without navigation).

    Counters track execution for 70/30 validation:
    - llm_executed: LLM actions that passed validation
    - algorithm_chosen: Algorithm path chosen by decision_router
    - forced_back_count: BACK actions from stuck detection
    - llm_validation_failed: LLM actions that failed validation
    - restart_count: App restarts triggered by stuck recovery
    """

    # Threshold for triggering app restart after consecutive same-state iterations
    MAX_BLOCKS_BEFORE_RESTART = 8

    def __init__(
        self,
        config: RVAgentConfig,
        loop_detector: LoopDetector,
        fallback_manager: FallbackManager,
        exploration_strategy: Optional[ExplorationStrategy] = None,
        target_package: Optional[str] = None
    ):
        """
        Initialize routing manager.

        Args:
            config: Agent configuration
            loop_detector: Loop detection component
            fallback_manager: Fallback management component
            exploration_strategy: Strategy for pure_algorithm/multimode
            target_package: Target app package name for restart actions
        """
        self.config = config
        self.loop_detector = loop_detector
        self.fallback_manager = fallback_manager
        self.exploration_strategy = exploration_strategy
        self.target_package = target_package

        # Counters for metrics
        self.llm_executed = 0           # LLM actions executed successfully
        self.algorithm_chosen = 0       # Algorithm path chosen
        self.forced_back_count = 0      # BACK from stuck detection
        self.llm_validation_failed = 0  # LLM actions that failed validation
        self.restart_count = 0          # App restarts from stuck recovery

        # State tracking for restart detection
        self.consecutive_same_state = 0
        self.last_state_hash: Optional[str] = None

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
            self.algorithm_chosen += 1
            self.logger.info("Mode: pure_algorithm -> algorithm path")
            return "algorithm"

        elif mode == "llm_only":
            self.logger.info("Mode: llm_only -> LLM path")
            return "llm"

        elif mode == "multimode":
            llm_probability = self.config.llm_probability

            if random.random() < llm_probability:
                self.logger.info(
                    f"Mode: multimode (p={llm_probability}) -> LLM path "
                    f"(llm_exec={self.llm_executed}, alg_chosen={self.algorithm_chosen})"
                )
                return "llm"
            else:
                self.algorithm_chosen += 1
                self.logger.info(
                    f"Mode: multimode (p={llm_probability}) -> algorithm path "
                    f"(llm_exec={self.llm_executed}, alg_chosen={self.algorithm_chosen})"
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
        Validate action and return execute path.

        Always returns validation_path="execute". If action is invalid
        or a loop is detected, returns a BACK action instead of the
        original action. No fallback cycle.

        In pure_algorithm mode, loop detection is skipped because the
        strategy has its own loop prevention (backtracking, successor
        tracking, plateau detection).

        Args:
            action: Action to validate (from LLM or Algorithm)
            recent_actions: Recent action history for loop detection
            decision_maker: Source of action ("llm", "algorithm", "stuck_recovery")

        Returns:
            Dictionary with:
            - validation_path: Always "execute"
            - loop_detected: Whether loop was detected
            - current_action: Original action or BACK if invalid
        """
        mode = self.config.get_agent_mode()

        # In pure_algorithm mode, only check for sequence repetition (A-B-A-B pattern)
        # Skip single-action loop detection as strategy may legitimately repeat actions
        if mode == "pure_algorithm":
            if not action or not action.get("action_type"):
                self.logger.warning(f"No action from {decision_maker} in pure_algorithm mode")
                return {
                    "validation_path": "execute",
                    "loop_detected": False,
                    "current_action": None
                }

            # Sequence repetition detection for pure_algorithm mode
            # This catches stuck loops like: CLICK-BACK-CLICK-BACK-CLICK-BACK
            is_seq_repetition, pattern, repetitions = self.loop_detector.detect_action_sequence_repetition(
                recent_actions
            )
            if is_seq_repetition:
                action_type = action.get("action_type", "UNKNOWN")
                self.logger.warning(
                    f"Sequence loop in pure_algorithm: {pattern} x{repetitions} "
                    f"-> trying different approach"
                )
                # In pure_algorithm, try a SCROLL action instead of BACK to escape the loop
                return {
                    "validation_path": "execute",
                    "loop_detected": True,
                    "current_action": self._create_scroll_action("sequence_loop_escape")
                }

            return {
                "validation_path": "execute",
                "loop_detected": False,
                "current_action": action
            }

        # Check for valid action
        if not action or not action.get("action_type"):
            if decision_maker == "llm":
                self.llm_validation_failed += 1
            self.logger.warning(
                f"No valid action from {decision_maker} -> executing BACK"
            )
            return {
                "validation_path": "execute",
                "loop_detected": True,
                "current_action": self._create_back_action("no_valid_action")
            }

        # Loop detection: consecutive similar actions
        is_loop, consecutive_count, threshold = self.loop_detector.detect_loop(
            recent_actions, action
        )
        if is_loop:
            if decision_maker == "llm":
                self.llm_validation_failed += 1
            action_type = action.get("action_type", "UNKNOWN")
            self.logger.warning(
                f"Loop detected from {decision_maker}: {action_type} repeated "
                f"{consecutive_count}x (threshold={threshold}) -> executing BACK"
            )
            return {
                "validation_path": "execute",
                "loop_detected": True,
                "current_action": self._create_back_action("loop_detected")
            }

        # Action sequence repetition detection
        is_seq_repetition, pattern, repetitions = self.loop_detector.detect_action_sequence_repetition(
            recent_actions
        )
        if is_seq_repetition:
            if decision_maker == "llm":
                self.llm_validation_failed += 1
            self.logger.warning(
                f"Sequence repetition from {decision_maker}: {pattern} x{repetitions} "
                f"-> executing BACK"
            )
            return {
                "validation_path": "execute",
                "loop_detected": True,
                "current_action": self._create_back_action("sequence_repetition")
            }

        # Spatial loop detection (clicks clustered in same area)
        is_spatial_loop = self.loop_detector.detect_spatial_loop(recent_actions)
        if is_spatial_loop:
            if decision_maker == "llm":
                self.llm_validation_failed += 1
            self.logger.warning(
                f"Spatial loop from {decision_maker}: clicks clustered -> executing BACK"
            )
            return {
                "validation_path": "execute",
                "loop_detected": True,
                "current_action": self._create_back_action("spatial_loop")
            }

        # Valid action
        if decision_maker == "llm":
            self.llm_executed += 1

        return {
            "validation_path": "execute",
            "loop_detected": False,
            "current_action": action
        }

    def _create_back_action(self, reason: str) -> Dict[str, Any]:
        """Create a BACK action for loop recovery."""
        return {
            "action_type": "BACK",
            "x": 0,
            "y": 0,
            "text": "",
            "source": "validation",
            "reason": reason
        }

    def _create_scroll_action(self, reason: str) -> Dict[str, Any]:
        """Create a SCROLL action to escape loops."""
        return {
            "action_type": "SCROLL",
            "direction": "down",
            "x": 0,
            "y": 0,
            "text": "",
            "source": "validation",
            "reason": reason
        }

    def _create_restart_action(self, reason: str) -> Dict[str, Any]:
        """Create a RESTART_APP action to escape dead-end states."""
        return {
            "action_type": "RESTART_APP",
            "package_name": self.target_package,
            "x": 0,
            "y": 0,
            "text": "",
            "source": "stuck_recovery",
            "reason": reason
        }

    def track_state_change(self, new_state_hash: str) -> Optional[Dict[str, Any]]:
        """
        Track state changes and detect if restart is needed.

        Called after each action execution. If the state remains unchanged
        for MAX_BLOCKS_BEFORE_RESTART consecutive iterations, returns a
        RESTART_APP action.

        Args:
            new_state_hash: Hash of the current screen state

        Returns:
            RESTART_APP action if stuck threshold exceeded, None otherwise
        """
        if new_state_hash == self.last_state_hash:
            self.consecutive_same_state += 1
            self.logger.debug(
                f"State unchanged: {self.consecutive_same_state}/{self.MAX_BLOCKS_BEFORE_RESTART}"
            )
        else:
            if self.consecutive_same_state > 0:
                self.logger.debug(
                    f"State changed after {self.consecutive_same_state} blocks"
                )
            self.consecutive_same_state = 0
            self.last_state_hash = new_state_hash

        if self.consecutive_same_state >= self.MAX_BLOCKS_BEFORE_RESTART:
            self.logger.warning(
                f"State blocked {self.consecutive_same_state}x, triggering app restart"
            )
            self.consecutive_same_state = 0
            self.restart_count += 1
            return self._create_restart_action("state_blocked")

        return None

    def get_decision_counters(self) -> Dict[str, Any]:
        """
        Get all decision counter values.

        Returns:
            Dictionary with counters and proportions
        """
        primary_total = self.llm_executed + self.algorithm_chosen
        llm_percentage = (self.llm_executed / primary_total * 100) if primary_total > 0 else 0
        algorithm_percentage = (self.algorithm_chosen / primary_total * 100) if primary_total > 0 else 0

        total_actions = (
            self.llm_executed +
            self.algorithm_chosen +
            self.forced_back_count +
            self.llm_validation_failed
        )

        return {
            # Primary counters (70/30 validation)
            "llm_executed": self.llm_executed,
            "algorithm_chosen": self.algorithm_chosen,
            "llm_percentage": llm_percentage,
            "algorithm_percentage": algorithm_percentage,

            # Event counters
            "forced_back": self.forced_back_count,
            "llm_validation_failed": self.llm_validation_failed,
            "restart_count": self.restart_count,

            # Totals
            "primary_total": primary_total,
            "total_actions": total_actions
        }
