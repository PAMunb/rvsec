# rvandroid/rvdroid/strategy/balancer/strategy_balancer.py

"""
Strategy balancer for RVDroid.

This module provides a simplified mechanism to select and balance testing strategies
based on their performance, exploration needs, and current application state.
"""

import random
import time
from typing import Dict, Any, List, Optional

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.visitor.base_visitor import ItemAction
from rvandroid.rvdroid.strategy.strategy import Strategy, StrategyRegistry
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.performance_monitor import PerformanceMonitor


class StrategyBalancer:
    """
    Balances multiple testing strategies and adaptively selects between them.

    Uses a combination of performance tracking, exploration needs assessment,
    and state analysis to determine the most appropriate strategy for the
    current testing context.

    ### Architectural Decisions:
    - Simple selection mechanism that strongly favors high-performing strategies
    - Clear detection of exploration plateaus to trigger strategy changes
    - Minimal state tracking to reduce overhead
    - Focused exploration phases with distinct strategy preferences
    - Optional LLM guidance for smarter strategy selection
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None,
                 strategies: Optional[List[str]] = None,
                 use_llm_guidance: bool = False):
        """
        Initialize the strategy balancer.

        Args:
            static_data: Optional static analysis data
            strategies: List of strategy names to use
            use_llm_guidance: Whether to use LLM guidance for strategy selection
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.strategy.balancer",
            {CONTEXT_COMPONENT: "StrategyBalancer"}
        )

        # Initialize performance monitor
        self.performance_monitor = PerformanceMonitor.get_instance()

        # Store LLM guidance setting
        self.use_llm_guidance = use_llm_guidance

        # Use default strategies if none provided
        if not strategies:
            strategies = ["RandomStrategy", "SecurityFocusedStrategy"]

            # Add VisualAwareStrategy if using LLM (it's more sophisticated)
            if use_llm_guidance and "VisualAwareStrategy" not in strategies:
                strategies.append("VisualAwareStrategy")

        # Create strategies - with direct class instantiation fallback
        self.strategies: List[Dict[str, Any]] = []

        # First try registry
        for strategy_name in strategies:
            try:
                strategy = StrategyRegistry.create_strategy(strategy_name, static_data)
                if strategy:
                    self.strategies.append({
                        "strategy": strategy,
                        "weight": 1.0,
                        "performance": {
                            "new_states": 0,
                            "successful_actions": 0,
                            "total_actions": 0
                        }
                    })
                    self.logger.info(f"Created strategy via registry: {strategy_name}")
                else:
                    self.logger.warning(f"Failed to create strategy from registry: {strategy_name}")
            except Exception as e:
                self.logger.error(f"Error creating strategy {strategy_name}: {e}")

        # If no strategies were created, create emergency direct instances
        if not self.strategies:
            self.logger.warning("No strategies could be created from registry, using direct instantiation")
            try:
                from rvandroid.rvdroid.strategy.basic_strategies import RandomStrategy
                strategy = RandomStrategy(static_data)
                self.strategies.append({
                    "strategy": strategy,
                    "weight": 1.0,
                    "performance": {
                        "new_states": 0,
                        "successful_actions": 0,
                        "total_actions": 0
                    }
                })
                self.logger.info("Directly created RandomStrategy as fallback")
            except Exception as e:
                self.logger.error(f"Error with direct strategy creation: {e}")

        # Normalize initial weights if we have strategies
        if self.strategies:
            self._normalize_weights()
        else:
            self.logger.critical("NO STRATEGIES COULD BE CREATED - TESTING WILL FAIL")
            # TODO throw exception

        # Initialize preferred strategy
        self.preferred_strategy_info = self.strategies[0] if self.strategies else None
        self.last_strategy_switch = time.time()

        # Exploration tracking
        self.exploration_probability = 0.2  # 20% chance to explore non-preferred strategies

        # If using LLM guidance, adjust exploration probability
        if use_llm_guidance:
            self.exploration_probability = 0.3  # Higher exploration with LLM to gather more data

        self.strategy_switch_cooldown = 30  # 30 seconds between strategy switches
        self.plateau_detection_threshold = 5  # 5 actions in same state = plateau
        self.consecutive_same_state_counter = 0
        self.last_state_fingerprint = None

        # Activity exploration tracking (to fix the exploration issue)
        self.visited_activities = set()
        self.activity_visit_counts = {}

        # Performance tracking
        self.plateau_escapes = 0
        self.strategy_switches = 0

        # LLM-specific settings
        self.llm_guidance_received = False  # Track if we've received guidance
        self.llm_suggested_strategies = set()  # Strategies suggested by LLM

        self.logger.info(f"Initialized strategy balancer with {len(self.strategies)} strategies" +
                         (", LLM guidance enabled" if use_llm_guidance else ""))

    def select_strategy(self, state_data: Dict[str, Any]) -> Optional[Strategy]:
        """
        Select a strategy based on current state and exploration needs.

        Args:
            state_data: Current state data

        Returns:
            Selected strategy or None if no strategies available
        """
        if not self.strategies:
            return None

        # Get current state and activity information
        current_state = state_data.get("fingerprint", "unknown")
        current_activity = state_data.get("activity", "unknown")

        # Track activity visits
        if current_activity not in self.visited_activities:
            self.visited_activities.add(current_activity)
            self.activity_visit_counts[current_activity] = 1
        else:
            self.activity_visit_counts[current_activity] = self.activity_visit_counts.get(current_activity, 0) + 1

        # Check if we're in a plateau
        in_plateau = self._is_in_plateau(current_state)
        current_time = time.time()
        cooldown_elapsed = current_time - self.last_strategy_switch > self.strategy_switch_cooldown

        # Strategy selection logic
        if in_plateau and cooldown_elapsed:
            # We're stuck in a plateau - select strategy that prioritizes exploration
            return self._select_exploration_strategy()

        # Check if we've overexplored this activity (fix for repeated visits)
        activity_count = self.activity_visit_counts.get(current_activity, 0)
        if activity_count > 10 and len(self.visited_activities) > 1 and cooldown_elapsed:
            # We've spent too much time in this activity - force exploration
            self.logger.info(
                f"Activity {current_activity} appears overexplored (count={activity_count}), forcing exploration")
            return self._select_exploration_strategy()

        # Most of the time, use the preferred strategy
        if self.preferred_strategy_info and random.random() > self.exploration_probability:
            return self.preferred_strategy_info["strategy"]
        else:
            # Occasionally try other strategies
            other_strategies = [s for s in self.strategies if s != self.preferred_strategy_info]
            if other_strategies:
                return random.choice(other_strategies)["strategy"]
            else:
                return self.preferred_strategy_info["strategy"] if self.preferred_strategy_info else None

    def _select_exploration_strategy(self) -> Strategy:
        """
        Select a strategy that prioritizes exploration.

        Returns:
            Strategy that emphasizes exploration
        """
        # Look for strategies that have discovered new states
        exploration_strategies = sorted(
            self.strategies,
            key=lambda s: s["performance"].get("new_states", 0),
            reverse=True
        )

        # Prefer a different strategy than the current one
        for strategy_info in exploration_strategies:
            if strategy_info != self.preferred_strategy_info:
                self.logger.info(f"Switching to exploration strategy: {strategy_info['strategy'].name}")

                # Update preferred strategy temporarily
                self.preferred_strategy_info = strategy_info
                self.last_strategy_switch = time.time()
                self.strategy_switches += 1
                self.plateau_escapes += 1

                # Reset consecutive same state counter
                self.consecutive_same_state_counter = 0

                return strategy_info["strategy"]

        # If no alternative, keep current strategy
        return self.preferred_strategy_info["strategy"] if self.preferred_strategy_info else self.strategies[0][
            "strategy"]

    def _is_in_plateau(self, state_fingerprint: str) -> bool:
        """
        Determine if exploration is currently in a plateau.

        Args:
            state_fingerprint: Current state fingerprint

        Returns:
            True if exploration is stuck in a plateau, False otherwise
        """
        # Check if we're in the same state as before
        if self.last_state_fingerprint == state_fingerprint:
            self.consecutive_same_state_counter += 1
        else:
            # Reset counter when state changes
            self.consecutive_same_state_counter = 0
            self.last_state_fingerprint = state_fingerprint

        # Consider it a plateau if we've been in the same state for several consecutive actions
        return self.consecutive_same_state_counter >= self.plateau_detection_threshold

    def update_performance(self, strategy: Strategy, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Update performance metrics for a strategy based on action result.

        Args:
            strategy: Strategy that generated the action
            action: Action that was executed
            result: Execution result
        """
        # Find strategy info
        strategy_info = next((s for s in self.strategies if s["strategy"] == strategy), None)
        if not strategy_info:
            return

        # Update performance metrics
        performance = strategy_info["performance"]

        # Track total actions
        performance["total_actions"] = performance.get("total_actions", 0) + 1

        # Track successful actions
        if result.get("success", False):
            performance["successful_actions"] = performance.get("successful_actions", 0) + 1

        # Track new states - most important for strategy selection
        if result.get("new_state", False):
            performance["new_states"] = performance.get("new_states", 0) + 1

            # Strongly favor strategies that discover new states
            strategy_info["weight"] *= 1.2

            # Consider making this the preferred strategy if it's performing well
            if (strategy_info != self.preferred_strategy_info and
                    performance.get("new_states", 0) >
                    self.preferred_strategy_info["performance"].get("new_states", 0) * 0.8):
                self.logger.info(
                    f"Switching preferred strategy to {strategy_info['strategy'].name} after discovering new state")
                self.preferred_strategy_info = strategy_info
                self.last_strategy_switch = time.time()

        # Normalize weights
        self._normalize_weights()

    def _normalize_weights(self) -> None:
        """Normalize strategy weights to sum to the number of strategies."""
        total_weight = sum(s["weight"] for s in self.strategies)

        if total_weight <= 0:
            # Reset to equal weights if all weights are zero
            for strategy_info in self.strategies:
                strategy_info["weight"] = 1.0
        else:
            # Normalize to sum to the number of strategies
            target_sum = len(self.strategies)
            for strategy_info in self.strategies:
                strategy_info["weight"] = (strategy_info["weight"] / total_weight) * target_sum

    def get_strategy_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about strategy performance.

        Returns:
            Dictionary with strategy statistics
        """
        return {
            "strategies": [
                {
                    "name": s["strategy"].name,
                    "weight": s["weight"],
                    "new_states": s["performance"].get("new_states", 0),
                    "successful_actions": s["performance"].get("successful_actions", 0),
                    "total_actions": s["performance"].get("total_actions", 0),
                    "is_preferred": (s == self.preferred_strategy_info)
                }
                for s in self.strategies
            ],
            "visited_activities": len(self.visited_activities),
            "strategy_switches": self.strategy_switches,
            "plateau_escapes": self.plateau_escapes
        }
