# rvandroid/rvdroid/strategy/balancer/strategy_balancer.py

"""
Strategy balancer for RVDroid.

This module provides functionality to balance multiple testing strategies,
track their effectiveness, and adaptively adjust strategy selection
based on results and application state.
"""

import time
import random
from typing import Dict, Any, List, Optional, Tuple

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription, ItemAction
from rvandroid.rvdroid.llm.llm_service import LLMService
from rvandroid.rvdroid.strategy.strategy import Strategy, StrategyRegistry
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.performance_monitor import PerformanceMonitor


class StrategyBalancer:
    """
    Balances multiple testing strategies and adaptively selects between them.
    Improved to be more stable and prioritize the preferred strategy.

    ### Architectural Decisions:
    - Simplified selection mechanism that strongly favors the preferred strategy
    - Detects exploration plateaus to trigger strategy changes only when needed
    - Maintains a stable preferred strategy with clear transition conditions
    - Reduces thrashing between strategies for more focused exploration
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None,
                 strategies: Optional[List[str]] = None,
                 use_llm_guidance: bool = False):
        """
        Initialize the strategy balancer.

        Args:
            static_data: Optional static analysis data
            strategies: List of strategy names to use
            use_llm_guidance: Whether to use LLM for strategy guidance
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.strategy.balancer",
            {CONTEXT_COMPONENT: "StrategyBalancer"}
        )

        # Initialize performance monitor
        self.performance_monitor = PerformanceMonitor.get_instance()

        # Use default strategies if none provided
        if not strategies:
            strategies = ["RandomStrategy", "GreedyStrategy", "ModelBasedStrategy"]

        # Create strategies
        self.strategies: List[Dict[str, Any]] = []
        for strategy_name in strategies:
            strategy = StrategyRegistry.create_strategy(strategy_name, static_data)
            if strategy:
                self.strategies.append({
                    "strategy": strategy,
                    "weight": 1.0,
                    "performance": {
                        "new_states": 0,
                        "successful_actions": 0,
                        "total_actions": 0,
                        "security_operations": 0,
                        "last_success_time": 0
                    }
                })

        # Normalize initial weights
        self._normalize_weights()

        # Initialize preferred strategy
        self.preferred_strategy_info = self.strategies[0] if self.strategies else None
        self.last_strategy_switch = time.time()

        # Modified properties for improved stability
        self.exploration_probability = 0.1  # Reduced from 0.3 - only 10% chance to explore non-preferred strategies
        self.strategy_switch_cooldown = 60  # Increased from 30 - wait 60 seconds between strategy switches
        self.plateau_detection_threshold = 5  # Number of consecutive actions in same state to detect plateau
        self.consecutive_same_state_counter = 0  # Track consecutive actions in same state
        self.last_state_fingerprint = None  # Track the last state for plateau detection

        # Track performance metrics at the overall strategy balancer level
        self.plateau_escapes = 0
        self.strategy_switches = 0

        # Initialize LLM service if needed
        self.use_llm_guidance = use_llm_guidance
        self.llm_service = LLMService(static_data) if use_llm_guidance else None
        self.last_llm_consultation = 0
        self.llm_consultation_interval = 120  # Only consult LLM every 2 minutes

        # Exploration state tracking
        self.current_phase = "exploration"  # exploration, coverage, security
        self.phase_start_time = time.time()
        self.phase_duration = 300  # 5 minutes per phase

        self.logger.info(f"Initialized strategy balancer with {len(self.strategies)} strategies")
        self.logger.info(
            f"Preferred strategy: {self.preferred_strategy_info['strategy'].name if self.preferred_strategy_info else 'None'}")
        if use_llm_guidance:
            self.logger.info("LLM guidance enabled")

    def consult_llm_for_strategy(self, state_data: Dict[str, Any],
                                 exploration_history: List[Dict[str, Any]]) -> Optional[Strategy]:
        """
        Consult the LLM for strategic guidance.

        Args:
            state_data: Current state data
            exploration_history: Recent exploration history

        Returns:
            Selected strategy based on LLM guidance or None if LLM is unavailable
        """
        if not self.llm_service or not self.use_llm_guidance:
            return None

        # Only consult LLM periodically to avoid too many calls
        current_time = time.time()
        if current_time - self.last_llm_consultation < self.llm_consultation_interval:
            return None

        try:
            # Get strategy recommendation from LLM
            strategy_recommendation = self.llm_service.get_exploration_strategy(
                state_data, exploration_history
            )

            # Update last consultation time
            self.last_llm_consultation = current_time

            # Extract strategy name
            strategy_name = strategy_recommendation.get("strategy", "")
            if not strategy_name:
                return None

            # Adjust strategy weights based on LLM recommendation
            self._adjust_strategy_weights_from_llm(strategy_name)

            # Find the recommended strategy
            for strategy_info in self.strategies:
                if strategy_info["strategy"].__class__.__name__.lower().startswith(strategy_name.lower()):
                    self.logger.info(f"Using LLM-recommended strategy: {strategy_info['strategy'].name}")

                    # Update preferred strategy
                    self.preferred_strategy_info = strategy_info
                    self.last_strategy_switch = current_time

                    return strategy_info["strategy"]

            return None

        except Exception as e:
            self.logger.error(f"Error consulting LLM for strategy: {e}")
            return None

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

        # Log if we're approaching a plateau
        if self.consecutive_same_state_counter >= (self.plateau_detection_threshold - 1):
            self.logger.debug(f"Approaching exploration plateau: {self.consecutive_same_state_counter} "
                              f"consecutive actions in state {state_fingerprint}")

        # Consider it a plateau if we've been in the same state for several consecutive actions
        return self.consecutive_same_state_counter >= self.plateau_detection_threshold

    def _adjust_strategy_weights_from_llm(self, strategy_name: str) -> None:
        """
        Adjust strategy weights based on LLM recommendation.

        Args:
            strategy_name: Name of the recommended strategy
        """
        # Boost the weight of the recommended strategy
        for strategy_info in self.strategies:
            if strategy_info["strategy"].__class__.__name__.lower().startswith(strategy_name.lower()):
                strategy_info["weight"] *= 2.0
            else:
                strategy_info["weight"] *= 0.8

        # Normalize weights
        self._normalize_weights()

    def select_strategy(self, state_data: Dict[str, Any]) -> Optional[Strategy]:
        """
        Select a strategy based on current state and exploration history.
        Simplified to heavily favor the preferred strategy with plateau detection.

        Args:
            state_data: Current state data

        Returns:
            Selected strategy or None if no strategies available
        """
        if not self.strategies:
            self.logger.warning("No strategies available")
            return None

        # Ensure we have a preferred strategy
        if not self.preferred_strategy_info and self.strategies:
            self.preferred_strategy_info = self.strategies[0]
            self.last_strategy_switch = time.time()
            self.logger.info(f"Setting initial preferred strategy: {self.preferred_strategy_info['strategy'].name}")

        # Get current state fingerprint
        current_state = state_data.get("fingerprint", "unknown")

        # Check if we're in a plateau (too many actions in the same state)
        in_plateau = self._is_in_plateau(current_state)

        current_time = time.time()
        cooldown_elapsed = current_time - self.last_strategy_switch > self.strategy_switch_cooldown

        # Strategy selection logic:
        # 1. If in plateau and cooldown has elapsed, switch strategies
        # 2. Otherwise, strongly prefer the current strategy

        if in_plateau and cooldown_elapsed:
            # We're stuck in a plateau and cooldown has elapsed - switch strategies
            other_strategies = [s for s in self.strategies if s != self.preferred_strategy_info]

            if other_strategies:
                # Find a strategy that has previously discovered states
                other_strategies.sort(
                    key=lambda s: (
                        s["performance"].get("new_states", 0),
                        s["performance"].get("successful_actions", 0)
                    ),
                    reverse=True
                )

                new_strategy_info = other_strategies[0]

                self.logger.info(
                    f"Switching from {self.preferred_strategy_info['strategy'].name} to "
                    f"{new_strategy_info['strategy'].name} to escape plateau"
                )

                # Update preferred strategy temporarily
                self.preferred_strategy_info = new_strategy_info
                self.last_strategy_switch = current_time
                self.strategy_switches += 1
                self.plateau_escapes += 1

                # Reset consecutive same state counter since we're trying a new strategy
                self.consecutive_same_state_counter = 0

                return new_strategy_info["strategy"]

        # Most of the time (90%), use the preferred strategy
        # Only occasionally (10%) try others for exploration
        if self.preferred_strategy_info and random.random() > self.exploration_probability:
            # Log that we're using the preferred strategy
            if random.random() < 0.1:  # Only log occasionally to avoid flooding logs
                self.logger.debug(f"Using preferred strategy: {self.preferred_strategy_info['strategy'].name}")
            return self.preferred_strategy_info["strategy"]
        else:
            # Occasionally try other strategies (exploration_probability chance)
            other_strategies = [s for s in self.strategies if s != self.preferred_strategy_info]
            if other_strategies:
                # Weight the selection by their weights
                total_weight = sum(s["weight"] for s in other_strategies)

                if total_weight <= 0:
                    # If all weights are zero, use uniform selection
                    selected_strategy_info = random.choice(other_strategies)
                else:
                    # Use weighted random selection
                    selection = random.uniform(0, total_weight)
                    current_sum = 0

                    selected_strategy_info = other_strategies[0]  # Default in case loop doesn't select one
                    for s in other_strategies:
                        current_sum += s["weight"]
                        if selection <= current_sum:
                            selected_strategy_info = s
                            break

                self.logger.debug(f"Exploring alternative strategy: {selected_strategy_info['strategy'].name}")
                return selected_strategy_info["strategy"]
            else:
                # Fall back to preferred strategy if no alternatives
                return self.preferred_strategy_info["strategy"] if self.preferred_strategy_info else None

    def update_performance(self, strategy: Strategy, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Update performance metrics for a strategy based on action result.
        More stable implementation that rewards strategies finding new states.

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
        performance["total_actions"] += 1

        # Track successful actions
        if result.get("success", False):
            performance["successful_actions"] += 1
            performance["last_success_time"] = time.time()

        # Track new states - this is most important for strategy selection
        if result.get("new_state", False):
            performance["new_states"] += 1

            # If this isn't the preferred strategy but it found a new state,
            # consider making it the preferred strategy
            if (strategy_info != self.preferred_strategy_info and
                    performance["new_states"] >= 2):  # Require at least 2 new states before promoting

                current_time = time.time()
                self.logger.info(
                    f"Setting preferred strategy to {strategy_info['strategy'].name} "
                    f"after discovering new state"
                )

                self.preferred_strategy_info = strategy_info
                self.last_strategy_switch = current_time

        # Track security operations
        if action.reaches_mop:
            performance["security_operations"] += 1

        # Only make minor adjustments to weights to maintain stability
        if result.get("new_state", False):
            # Reward strategies that find new states with small weight increase
            strategy_info["weight"] *= 1.05  # 5% increase

        # Normalize weights
        self._normalize_weights()

        # Skip updating preferred strategy here to reduce thrashing
        # We'll primarily update it in the select_strategy method when a plateau is detected

    def _consider_updating_preferred_strategy(self, strategy_info: Dict[str, Any]) -> None:
        """
        Consider updating the preferred strategy based on recent performance.

        Args:
            strategy_info: Strategy information that was just updated
        """
        current_time = time.time()

        # Only consider switching if cooldown has passed
        if current_time - self.last_strategy_switch < self.strategy_switch_cooldown:
            return

        # If we don't have a preferred strategy yet, use this one
        if not self.preferred_strategy_info:
            self.preferred_strategy_info = strategy_info
            self.last_strategy_switch = current_time
            self.logger.info(f"Setting initial preferred strategy: {strategy_info['strategy'].name}")
            return

        # Don't update if this is already the preferred strategy
        if strategy_info == self.preferred_strategy_info:
            return

        # Compare performance metrics
        current_perf = self.preferred_strategy_info["performance"]
        new_perf = strategy_info["performance"]

        # Calculate performance scores (weighted sum of different metrics)
        current_score = (
                self._calculate_success_rate(current_perf) * 0.3 +
                self._calculate_new_state_rate(current_perf) * 0.5 +
                (current_perf["security_operations"] / max(1, current_perf["total_actions"])) * 0.2
        )

        new_score = (
                self._calculate_success_rate(new_perf) * 0.3 +
                self._calculate_new_state_rate(new_perf) * 0.5 +
                (new_perf["security_operations"] / max(1, new_perf["total_actions"])) * 0.2
        )

        # Update preferred strategy if new strategy performs significantly better
        if new_score > current_score * 1.2:  # 20% better performance
            self.preferred_strategy_info = strategy_info
            self.last_strategy_switch = current_time
            self.logger.info(
                f"Switching preferred strategy from {self.preferred_strategy_info['strategy'].name} "
                f"to {strategy_info['strategy'].name} (score: {new_score:.2f} vs {current_score:.2f})"
            )

    def _update_strategy_weight(self, strategy_info: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        Update a strategy's weight based on its performance.

        Args:
            strategy_info: Strategy information dictionary
            result: Action execution result
        """
        # Get current weight and performance
        weight = strategy_info["weight"]
        performance = strategy_info["performance"]

        # Define weight adjustment factors
        success_factor = 1.05 if result.get("success", False) else 0.98
        new_state_factor = 1.2 if result.get("new_state", False) else 1.0
        mop_factor = 1.1 if result.get("security_operation", False) else 1.0

        # Calculate weight adjustment based on current phase
        if self.current_phase == "exploration":
            # In exploration phase, prioritize finding new states
            adjusted_weight = weight * success_factor * new_state_factor

        elif self.current_phase == "coverage":
            # In coverage phase, prioritize successful actions
            adjusted_weight = weight * success_factor * new_state_factor * 0.9

        elif self.current_phase == "security":
            # In security phase, prioritize security operations
            adjusted_weight = weight * success_factor * mop_factor

        else:
            # Default adjustment
            adjusted_weight = weight * success_factor

        # Apply adjustment with limits
        strategy_info["weight"] = max(0.1, min(10.0, adjusted_weight))

        # Normalize weights after adjustment
        self._normalize_weights()

    def _normalize_weights(self) -> None:
        """Normalize weights to sum to a fixed value."""
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

    def _update_exploration_phase(self, state_data: Dict[str, Any]) -> None:
        """
        Update the current exploration phase based on elapsed time and results.

        Args:
            state_data: Current state data
        """
        current_time = time.time()
        elapsed_in_phase = current_time - self.phase_start_time

        # Check if we should transition to next phase
        if elapsed_in_phase >= self.phase_duration:
            # Determine next phase
            if self.current_phase == "exploration":
                next_phase = "coverage"
            elif self.current_phase == "coverage":
                next_phase = "security"
            else:
                # Cycle back to exploration
                next_phase = "exploration"

            # Log phase transition
            self.logger.info(f"Transitioning from {self.current_phase} phase to {next_phase} phase")

            # Update phase tracking
            self.current_phase = next_phase
            self.phase_start_time = current_time

            # Adjust strategy weights for new phase
            self._adjust_weights_for_phase(next_phase)

            # Reset preferred strategy on phase change
            self.preferred_strategy_info = self._select_best_strategy_for_phase(next_phase)
            self.last_strategy_switch = current_time

            if self.preferred_strategy_info:
                self.logger.info(
                    f"New preferred strategy for {next_phase} phase: {self.preferred_strategy_info['strategy'].name}")

    def _select_best_strategy_for_phase(self, phase: str) -> Optional[Dict[str, Any]]:
        """
        Select the best strategy for a specific phase based on historical performance.

        Args:
            phase: Exploration phase

        Returns:
            Best strategy info for this phase or None if no strategies
        """
        if not self.strategies:
            return None

        # Define phase-specific scoring function
        if phase == "exploration":
            # For exploration, prioritize new state discovery
            def score_func(perf):
                return self._calculate_new_state_rate(perf)
        elif phase == "coverage":
            # For coverage, prioritize successful actions
            def score_func(perf):
                return self._calculate_success_rate(perf)
        elif phase == "security":
            # For security, prioritize security operations
            def score_func(perf):
                return perf["security_operations"] / max(1, perf["total_actions"]) * 100
        else:
            # Default scoring function
            def score_func(perf):
                return (self._calculate_success_rate(perf) +
                        self._calculate_new_state_rate(perf)) / 2

        # Score each strategy
        scored_strategies = []
        for strategy_info in self.strategies:
            perf = strategy_info["performance"]
            # Skip strategies with too few actions
            if perf["total_actions"] < 10:
                continue

            score = score_func(perf)
            scored_strategies.append((strategy_info, score))

        # Sort by score (highest first)
        scored_strategies.sort(key=lambda x: x[1], reverse=True)

        # Return best strategy or first if no scores
        if scored_strategies:
            return scored_strategies[0][0]
        else:
            return self.strategies[0] if self.strategies else None

    def _adjust_weights_for_phase(self, phase: str) -> None:
        """
        Adjust strategy weights based on the current exploration phase.

        Args:
            phase: Current exploration phase
        """
        for strategy_info in self.strategies:
            strategy = strategy_info["strategy"]
            strategy_type = strategy.__class__.__name__

            # Default weight adjustment factor
            weight_factor = 1.0

            # Adjust weights based on strategy type and phase
            if phase == "exploration":
                if strategy_type == "RandomStrategy":
                    weight_factor = 1.5  # Favor RandomStrategy for exploration
                elif strategy_type == "ModelBasedStrategy":
                    weight_factor = 0.8  # Less emphasis on model-based during exploration

            elif phase == "coverage":
                if strategy_type == "SystematicStrategy":
                    weight_factor = 1.5  # Favor SystematicStrategy for coverage
                elif strategy_type == "GreedyStrategy":
                    weight_factor = 1.2  # Moderately favor Greedy for coverage

            elif phase == "security":
                if strategy_type == "GreedyStrategy":
                    weight_factor = 1.5  # Favor GreedyStrategy for security testing
                # Adjust weight based on security operation performance
                security_operations = strategy_info["performance"]["security_operations"]
                if security_operations > 0:
                    weight_factor *= 1.5  # Bonus for strategies that found security operations

            # Apply weight adjustment
            strategy_info["weight"] *= weight_factor

        # Normalize weights after adjustment
        self._normalize_weights()

    def _select_context_specific_strategy(self, state_data: Dict[str, Any]) -> Optional[Strategy]:
        """
        Select a strategy based on the current application context.

        Args:
            state_data: Current state data

        Returns:
            Selected strategy or None for default selection
        """
        # Check for context information
        context_info = state_data.get("context_info", {})
        if not context_info:
            return None

        # Get primary context type
        context_type = context_info.get("primary_context", "")

        # Context-specific strategy selection
        if context_type == "authentication":
            # For authentication screens, prefer systematic or greedy strategies
            for strategy_info in self.strategies:
                strategy_type = strategy_info["strategy"].__class__.__name__
                if strategy_type in ["SystematicStrategy", "GreedyStrategy"]:
                    return strategy_info["strategy"]

        elif context_type == "payment":
            # For payment screens, prefer security-focused strategies (e.g., Greedy)
            for strategy_info in self.strategies:
                strategy_type = strategy_info["strategy"].__class__.__name__
                if strategy_type == "GreedyStrategy":
                    return strategy_info["strategy"]

        # No context-specific selection needed
        return None

    def _calculate_success_rate(self, performance: Dict[str, Any]) -> float:
        """
        Calculate success rate from performance metrics.

        Args:
            performance: Performance metrics dictionary

        Returns:
            Success rate as percentage
        """
        total_actions = performance["total_actions"]
        if total_actions == 0:
            return 0.0

        successful_actions = performance["successful_actions"]
        return (successful_actions / total_actions) * 100

    def _calculate_new_state_rate(self, performance: Dict[str, Any]) -> float:
        """
        Calculate new state discovery rate from performance metrics.

        Args:
            performance: Performance metrics dictionary

        Returns:
            New state discovery rate as percentage
        """
        total_actions = performance["total_actions"]
        if total_actions == 0:
            return 0.0

        new_states = performance["new_states"]
        return (new_states / total_actions) * 100

    def get_strategy_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about strategy performance and balancer behavior.

        Returns:
            Dictionary with detailed strategy statistics
        """
        # Get basic strategy stats
        strategy_stats = [
            {
                "name": s["strategy"].name,
                "type": s["strategy"].__class__.__name__,
                "weight": s["weight"],
                "success_rate": self._calculate_success_rate(s["performance"]),
                "new_state_rate": self._calculate_new_state_rate(s["performance"]),
                "total_actions": s["performance"]["total_actions"],
                "new_states": s["performance"]["new_states"],
                "security_operations": s["performance"]["security_operations"],
                "is_preferred": (s == self.preferred_strategy_info)
            }
            for s in self.strategies
        ]

        # Sort by weight (highest first)
        strategy_stats.sort(key=lambda x: x["weight"], reverse=True)

        # Add balancer statistics
        balancer_stats = {
            "preferred_strategy": self.preferred_strategy_info[
                "strategy"].name if self.preferred_strategy_info else "None",
            "last_strategy_switch": time.time() - self.last_strategy_switch if self.last_strategy_switch else 0,
            "strategy_switches": self.strategy_switches,
            "plateau_escapes": self.plateau_escapes,
            "exploration_probability": self.exploration_probability,
            "consecutive_same_state_actions": self.consecutive_same_state_counter,
            "in_plateau": self._is_in_plateau(self.last_state_fingerprint) if self.last_state_fingerprint else False,
            "strategy_switch_cooldown": self.strategy_switch_cooldown
        }

        return {
            "strategies": strategy_stats,
            "balancer": balancer_stats
        }

    def get_current_phase(self) -> Dict[str, Any]:
        """
        Get information about the current exploration phase.

        Returns:
            Dictionary with phase information
        """
        current_time = time.time()
        elapsed_in_phase = current_time - self.phase_start_time
        remaining_in_phase = max(0, self.phase_duration - elapsed_in_phase)

        return {
            "phase": self.current_phase,
            "elapsed_seconds": elapsed_in_phase,
            "remaining_seconds": remaining_in_phase,
            "total_seconds": self.phase_duration,
            "preferred_strategy": self.preferred_strategy_info[
                "strategy"].name if self.preferred_strategy_info else None
        }