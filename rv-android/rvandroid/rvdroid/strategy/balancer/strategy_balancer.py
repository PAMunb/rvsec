"""
Strategy balancer for RVDroid.

This module provides functionality to balance multiple testing strategies,
track their effectiveness, and adaptively adjust strategy selection
based on results and application state.
"""

import time
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

    Tracks strategy performance metrics, adjusts strategy weights based on
    effectiveness, and selects strategies based on application state and context.
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None,
                 strategies: Optional[List[str]] = None,
                 use_llm_guidance: bool = True):
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
                    return strategy_info["strategy"]

            return None

        except Exception as e:
            self.logger.error(f"Error consulting LLM for strategy: {e}")
            return None

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

    # Update the select_strategy method to use LLM guidance
    def select_strategy(self, state_data: Dict[str, Any]) -> Optional[Strategy]:
        """
        Select a strategy based on current weights and application state.

        Args:
            state_data: Current state data

        Returns:
            Selected strategy or None if no strategies available
        """
        if not self.strategies:
            self.logger.warning("No strategies available")
            return None

        # Update exploration phase if needed
        self._update_exploration_phase(state_data)

        # Get exploration history for LLM consultation
        exploration_history = []
        if hasattr(self, 'short_term_memory') and self.short_term_memory:
            exploration_history = list(self.short_term_memory.state_history)

        # Try to get strategy from LLM
        if self.use_llm_guidance:
            llm_strategy = self.consult_llm_for_strategy(state_data, exploration_history)
            if llm_strategy:
                return llm_strategy

        # Check for context-specific strategy selection
        context_strategy = self._select_context_specific_strategy(state_data)
        if context_strategy:
            return context_strategy

        # Use weighted random selection based on strategy weights
        import random
        total_weight = sum(s["weight"] for s in self.strategies)

        if total_weight <= 0:
            # If all weights are zero, use uniform selection
            return random.choice(self.strategies)["strategy"]

        # Weight-based selection
        selection = random.uniform(0, total_weight)
        current = 0

        for strategy_info in self.strategies:
            current += strategy_info["weight"]
            if selection <= current:
                return strategy_info["strategy"]

        # Fallback to first strategy
        return self.strategies[0]["strategy"]

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
        performance["total_actions"] += 1

        # Track successful actions
        if result.get("success", False):
            performance["successful_actions"] += 1
            performance["last_success_time"] = time.time()

        # Track new states
        if result.get("new_state", False):
            performance["new_states"] += 1

        # Track security operations
        if action.reaches_mop:
            performance["security_operations"] += 1

        # Update strategy weight based on performance
        self._update_strategy_weight(strategy_info, result)

        # Log performance update
        with self.performance_monitor.measure_time("strategy_performance_update"):
            # Record metrics for this strategy
            self.performance_monitor.record_metric(
                name=f"strategy_{strategy.name}_success_rate",
                value=self._calculate_success_rate(performance),
                unit="%",
                context={"strategy": strategy.name}
            )

            self.performance_monitor.record_metric(
                name=f"strategy_{strategy.name}_new_state_rate",
                value=self._calculate_new_state_rate(performance),
                unit="%",
                context={"strategy": strategy.name}
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

    def get_strategy_statistics(self) -> List[Dict[str, Any]]:
        """
        Get statistics about strategy performance.

        Returns:
            List of strategy statistics dictionaries
        """
        return [
            {
                "name": s["strategy"].name,
                "type": s["strategy"].__class__.__name__,
                "weight": s["weight"],
                "success_rate": self._calculate_success_rate(s["performance"]),
                "new_state_rate": self._calculate_new_state_rate(s["performance"]),
                "total_actions": s["performance"]["total_actions"],
                "new_states": s["performance"]["new_states"],
                "security_operations": s["performance"]["security_operations"]
            }
            for s in self.strategies
        ]

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
            "total_seconds": self.phase_duration
        }
