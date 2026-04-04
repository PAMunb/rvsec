"""
Decision routing management for multi-mode agent operation.

Route exploration decisions between LLM-guided and algorithmic modes
based on configuration. Support three execution modes (pure_algorithm,
llm_only, multimode) with probabilistic routing and validation-based
action filtering.

### Architectural Decisions:

- Probabilistic routing: multimode uses random threshold against llm_probability
- No fallback loops: invalid actions become BACK, never re-route to LLM
- Stuck detection delegated to learn_node for evidence-based detection

### Role in the System:

- Called by decision_router_node during workflow execution
- Validates actions before execution in validate_action_node
- Tracks execution counters for 70/30 proportion monitoring

### Integration Points:

- Input: RVAgentConfig for mode and probability settings
- Output: Decision path ("llm", "algorithm", "end") and validation results
- Dependencies: FallbackManager, ExplorationStrategy
"""

import logging
import random
from typing import Any, Dict, Optional

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.routing.fallback_manager import FallbackManager
from rv_agent.strategies.base_strategy import ExplorationStrategy


class RoutingManager:
    """
    Routes decisions between LLM and algorithmic strategies.

    ### Architectural Decisions:

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

    3. STUCK DETECTION (delegated to learn_node)
       Stuck detection is handled by learn_node based on screen_hash changes.
       This provides evidence-based detection (screen actually unchanged) rather
       than heuristic-based loop detection (action patterns).

       The algorithmic strategy also has its own loop prevention (action marking,
       successor tracking, plateau detection).

    Counters track execution for 70/30 validation:
    - llm_executed: LLM actions that passed validation
    - algorithm_chosen: Algorithm path chosen by decision_router
    - forced_back_count: BACK actions from stuck detection
    - llm_validation_failed: LLM actions that failed validation (null actions only)
    """

    def __init__(
        self,
        config: RVAgentConfig,
        fallback_manager: FallbackManager,
        exploration_strategy: Optional[ExplorationStrategy] = None,
    ):
        """
        Initialize routing manager.

        Args:
            config: Agent configuration
            fallback_manager: Fallback management component
            exploration_strategy: Strategy for pure_algorithm/multimode

        State:
            self.llm_executed: Count of LLM actions that passed validation.
            self.algorithm_chosen: Count of algorithm path selections.
            self.forced_back_count: Count of BACK actions from stuck detection.
            self.llm_validation_failed: Count of LLM actions that failed validation.
        """
        self.config = config
        self.fallback_manager = fallback_manager
        self.exploration_strategy = exploration_strategy

        # Initialize random seed for reproducibility (multimode routing)
        if config.seed is not None:
            random.seed(config.seed)
            logging.getLogger(__name__).info(
                f"RoutingManager: Random seed initialized: {config.seed}"
            )

        # Counters for metrics
        self.llm_executed = 0  # LLM actions executed successfully
        self.algorithm_chosen = 0  # Algorithm path chosen
        self.forced_back_count = 0  # BACK from stuck detection
        self.llm_validation_failed = 0  # LLM actions that failed validation

        self.logger = logging.getLogger(__name__)

    @property
    def mode(self) -> str:
        """Get current agent mode from config."""
        return self.config.get_agent_mode()

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
            # Probabilistic coin flip each iteration. The 70/30 default ratio
            # was calibrated empirically: LLM excels at semantic actions (login,
            # form filling) while algorithm covers systematic DFS exploration.
            # Over hundreds of iterations this converges to the configured ratio.
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
        decision_maker: str = "llm",
    ) -> Dict[str, Any]:
        """
        Validate action before execution.

        Stuck detection is handled by learn_node based on screen_hash changes.
        This method only checks for null actions.

        Args:
            action: Action to validate
            recent_actions: Recent action history (unused, kept for interface compatibility)
            decision_maker: Source of the action ("llm" or "algorithm")

        Returns:
            Dict with validation_path, loop_detected, and current_action
        """
        # Only null-action check here. Loop/stuck detection is evidence-based
        # in learn_node (screen hash unchanged), not heuristic-based here.
        # Returning "execute" with a BACK action (not re-routing to algorithm)
        # prevents fallback cycles between LLM and algorithm paths.
        if not action or not action.get("action_type"):
            if decision_maker == "llm":
                self.llm_validation_failed += 1
            self.logger.warning(
                f"No valid action from {decision_maker} -> executing BACK"
            )
            return {
                "validation_path": "execute",
                "loop_detected": True,
                "current_action": self._create_back_action("no_valid_action"),
            }

        # Track execution metrics.
        # algorithm_chosen is incremented in route_decision() (before execution)
        # but llm_executed is incremented here (after validation). This asymmetry
        # exists because LLM actions can fail validation (null tool calls), so we
        # only count them as "executed" when they pass. Algorithm actions always pass.
        if decision_maker == "llm":
            self.llm_executed += 1

        return {
            "validation_path": "execute",
            "loop_detected": False,
            "current_action": action,
        }

    def _create_back_action(self, reason: str) -> Dict[str, Any]:
        """Create a BACK action for loop recovery."""
        return {
            "action_type": "BACK",
            "x": 0,
            "y": 0,
            "text": "",
            "source": "validation",
            "reason": reason,
        }

    def get_decision_counters(self) -> Dict[str, Any]:
        """Get all decision counter values.

        Returns:
            Dictionary with keys:
            - "llm_executed" (int): LLM actions executed successfully.
            - "algorithm_chosen" (int): Algorithm path chosen count.
            - "llm_percentage" (float): LLM proportion of primary actions.
            - "algorithm_percentage" (float): Algorithm proportion of primary actions.
            - "forced_back" (int): BACK actions from stuck detection.
            - "llm_validation_failed" (int): LLM actions that failed validation.
            - "restart_count" (int): App restarts from Level 2 stuck recovery.
            - "error_recovery_count" (int): Error recovery actions (force_fill_input).
            - "primary_total" (int): Sum of llm_executed and algorithm_chosen.
            - "total_actions" (int): All actions including forced and failed.
        """
        from rv_agent import tracking as track

        primary_total = self.llm_executed + self.algorithm_chosen
        llm_percentage = (
            (self.llm_executed / primary_total * 100) if primary_total > 0 else 0
        )
        algorithm_percentage = (
            (self.algorithm_chosen / primary_total * 100) if primary_total > 0 else 0
        )

        total_actions = (
            self.llm_executed
            + self.algorithm_chosen
            + self.forced_back_count
            + self.llm_validation_failed
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
            "restart_count": track._counters["restart_count"],
            "error_recovery_count": track._counters["error_recovery_count"],
            # Totals
            "primary_total": primary_total,
            "total_actions": total_actions,
        }
