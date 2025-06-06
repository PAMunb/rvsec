# rvandroid/rvdroid/strategy/manager.py

"""
Strategy manager module for RVDroid.

This module provides a centralized manager for test strategies
that can be selected, configured, and applied during test execution.
"""

from typing import Dict, Any, List, Optional, Tuple

from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.parser.screen.visitor.model import ItemAction, ScreenDescription
from rv_android_core.rvdroid.core.component import Component
from rv_android_core.util.error.decorators import handle_error
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT

from rv_android_core.rvdroid.strategy.strategy import Strategy, StrategyRegistry


class StrategyManager(Component):
    """
    Centralized manager for RVDroid testing strategies.
    
    ### Architectural Decisions:
    - Implements a centralized management system for testing strategies
    - Provides dynamic strategy selection and configuration
    - Supports adaptive strategy switching based on testing context
    - Enables directive-based strategy adaptation from external sources
    - Integrates with the component-based architecture for lifecycle management
    
    ### Role in the System:
    - Coordinates strategy selection and execution during testing
    - Manages transition between strategies based on testing progress
    - Provides feedback on strategy effectiveness
    - Enables intelligent adaptation of testing approaches
    - Supports integration with external guidance systems (e.g., LLM)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None,
                 preferred_strategy: Optional[str] = None,
                 static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the strategy manager.
        
        Args:
            config: Optional configuration dictionary
            preferred_strategy: Optional name of the preferred strategy
            static_data: Optional static analysis data
        """
        super().__init__("StrategyManager", config)
        
        # Store static data
        self.static_data = static_data
        
        # Strategy configuration
        self.preferred_strategy_name = preferred_strategy
        self.strategy_weights: Dict[str, float] = {}
        
        # Current strategies
        self.active_strategy: Optional[Strategy] = None
        self.available_strategies: Dict[str, Strategy] = {}
        
        # Strategy performance metrics
        self.strategy_metrics: Dict[str, Dict[str, Any]] = {}
        
        # Strategy directives
        self.active_directives: List[Dict[str, Any]] = []
        
    @handle_error(level="ERROR")
    def initialize(self) -> bool:
        """
        Initialize the strategy manager.
        
        Returns:
            True if initialization succeeded, False otherwise
        """
        self.logger.info("Initializing strategy manager")
        
        # Register built-in strategies
        self._register_builtin_strategies()
        
        # Set initial strategy weights
        self._initialize_strategy_weights()
        
        # Set initial active strategy
        self._set_initial_strategy()
        
        self.initialized = True
        return True
        
    @handle_error(level="ERROR")
    def start(self) -> bool:
        """
        Start the strategy manager.
        
        Returns:
            True if start succeeded, False otherwise
        """
        if not self.initialized:
            self.logger.error("Cannot start: strategy manager not initialized")
            return False
            
        self.logger.info("Starting strategy manager")
        
        # Initialize metrics for all strategies
        for strategy_name in self.available_strategies:
            self.strategy_metrics[strategy_name] = {
                "actions_generated": 0,
                "successful_actions": 0,
                "new_states_discovered": 0,
                "last_success_time": 0
            }
            
        self.running = True
        return True
        
    @handle_error(level="ERROR")
    def stop(self) -> bool:
        """
        Stop the strategy manager.
        
        Returns:
            True if stop succeeded, False otherwise
        """
        if not self.running:
            self.logger.warning("Strategy manager is not running")
            return True
            
        self.logger.info("Stopping strategy manager")
        
        self.running = False
        return True
        
    @handle_error(level="ERROR")
    def cleanup(self) -> None:
        """
        Clean up strategy manager resources.
        """
        self.logger.info("Cleaning up strategy manager")
        
        # Clear strategies and metrics
        self.active_strategy = None
        self.available_strategies = {}
        self.strategy_metrics = {}
        self.active_directives = []
        
        self.initialized = False
        self.running = False
        
    @handle_error(level="WARN")
    def generate_action(self, screen: ScreenDescription, state_data: Dict[str, Any],
                       history: Optional[List[Dict[str, Any]]] = None) -> Optional[ItemAction]:
        """
        Generate the next action using the current strategy.
        
        Args:
            screen: Parsed screen description
            state_data: Raw state data
            history: Optional history of previous states and actions
            
        Returns:
            ItemAction to execute, or None if no action is available
        """
        if not self.running:
            self.logger.warning("Strategy manager is not running")
            return None
            
        if not self.active_strategy:
            self.logger.error("No active strategy available")
            return None
            
        # Check for adaptation based on directives
        should_switch = self._check_strategy_adaptation(state_data, history)
        
        if should_switch:
            # Strategy was switched, update log
            self.logger.info(f"Switched to strategy: {self.active_strategy.name}")
            
        # Generate action using active strategy
        try:
            action = self.active_strategy.generate_action(screen, state_data, history)
            
            if action:
                # Update metrics
                strategy_name = self.active_strategy.name
                self.strategy_metrics[strategy_name]["actions_generated"] += 1
                
                self.logger.debug(f"Generated action using {strategy_name}: {action.text}")
                
            return action
            
        except Exception as e:
            self.logger.error(f"Error generating action with strategy {self.active_strategy.name}: {e}")
            
            # Try to switch to a different strategy
            self._switch_to_fallback_strategy()
            
            # Try again with the new strategy
            if self.active_strategy:
                try:
                    return self.active_strategy.generate_action(screen, state_data, history)
                except Exception as fallback_error:
                    self.logger.error(f"Error with fallback strategy: {fallback_error}")
                    
            return None
            
    @handle_error(level="WARN")
    def update_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Update strategy based on action execution feedback.
        
        Args:
            action: Action that was executed
            result: Execution result with success status and state change info
        """
        if not self.running or not self.active_strategy:
            return
            
        # Update active strategy
        try:
            self.active_strategy.update_feedback(action, result)
        except Exception as e:
            self.logger.error(f"Error updating feedback for {self.active_strategy.name}: {e}")
            
        # Update metrics
        strategy_name = self.active_strategy.name
        metrics = self.strategy_metrics.get(strategy_name, {})
        
        if result.get("success", False):
            metrics["successful_actions"] = metrics.get("successful_actions", 0) + 1
            metrics["last_success_time"] = result.get("timestamp", 0)
            
        if result.get("new_state", False):
            metrics["new_states_discovered"] = metrics.get("new_states_discovered", 0) + 1
            
        # Update strategy weights based on performance
        self._update_strategy_weights(result)
        
    @handle_error(level="WARN")
    def apply_directive(self, directive: Dict[str, Any]) -> bool:
        """
        Apply a directive to modify strategy behavior.
        
        Args:
            directive: Directive to apply
            
        Returns:
            True if directive was applied successfully
        """
        directive_type = directive.get("type", "")
        
        if directive_type == "switch_strategy":
            # Switch to a specified strategy
            strategy_name = directive.get("strategy_name")
            if strategy_name and strategy_name in self.available_strategies:
                self._switch_active_strategy(strategy_name)
                
                # Add to active directives
                self.active_directives.append(directive)
                
                self.logger.info(f"Applied directive to switch to strategy: {strategy_name}")
                return True
                
        elif directive_type == "adjust_weights":
            # Adjust strategy weights
            weight_adjustments = directive.get("weights", {})
            if weight_adjustments:
                for strategy_name, weight in weight_adjustments.items():
                    if strategy_name in self.strategy_weights:
                        self.strategy_weights[strategy_name] = weight
                        
                # Normalize weights
                self._normalize_weights()
                
                # Add to active directives
                self.active_directives.append(directive)
                
                self.logger.info(f"Applied directive to adjust strategy weights")
                return True
                
        elif directive_type == "focus_patterns":
            # Focus on specific UI patterns
            patterns = directive.get("patterns", [])
            if patterns and self.active_strategy:
                # Pass pattern focus to strategy if supported
                if hasattr(self.active_strategy, "focus_on_patterns"):
                    self.active_strategy.focus_on_patterns(patterns)
                    
                    # Add to active directives
                    self.active_directives.append(directive)
                    
                    self.logger.info(f"Applied directive to focus on patterns: {patterns}")
                    return True
                    
        elif directive_type == "focus_actions":
            # Focus on specific action types
            action_types = directive.get("action_types", [])
            if action_types and self.active_strategy:
                # Pass action focus to strategy if supported
                if hasattr(self.active_strategy, "focus_on_actions"):
                    self.active_strategy.focus_on_actions(action_types)
                    
                    # Add to active directives
                    self.active_directives.append(directive)
                    
                    self.logger.info(f"Applied directive to focus on actions: {action_types}")
                    return True
                    
        self.logger.warning(f"Could not apply directive: {directive_type}")
        return False
        
    @handle_error(level="WARN")
    def process_suggestions(self, suggestions: List[Dict[str, Any]]) -> None:
        """
        Process suggestions from LLM or other sources.
        
        Args:
            suggestions: List of suggestions
        """
        if not self.running:
            return
            
        for suggestion in suggestions:
            suggestion_type = suggestion.get("type", "")
            
            if suggestion_type == "strategy":
                # Suggestion to change strategy
                strategy_name = suggestion.get("strategy_name")
                if strategy_name in self.available_strategies:
                    self._switch_active_strategy(strategy_name)
                    self.logger.info(f"Switched to suggested strategy: {strategy_name}")
                    
            elif suggestion_type == "focus":
                # Suggestion to focus on specific behaviors
                focus_area = suggestion.get("focus_area")
                if focus_area and self.active_strategy:
                    # Pass focus suggestion to strategy if supported
                    if hasattr(self.active_strategy, "set_focus"):
                        self.active_strategy.set_focus(focus_area)
                        self.logger.info(f"Set strategy focus to: {focus_area}")
                        
    def get_strategy_stats(self) -> Dict[str, Any]:
        """
        Get strategy statistics.
        
        Returns:
            Dictionary with strategy statistics
        """
        # Calculate success rates
        success_rates = {}
        new_state_rates = {}
        
        for strategy_name, metrics in self.strategy_metrics.items():
            actions_generated = metrics.get("actions_generated", 0)
            if actions_generated > 0:
                success_rates[strategy_name] = metrics.get("successful_actions", 0) / actions_generated
                new_state_rates[strategy_name] = metrics.get("new_states_discovered", 0) / actions_generated
            else:
                success_rates[strategy_name] = 0.0
                new_state_rates[strategy_name] = 0.0
                
        return {
            "active_strategy": self.active_strategy.name if self.active_strategy else None,
            "available_strategies": list(self.available_strategies.keys()),
            "strategy_weights": self.strategy_weights,
            "strategy_metrics": self.strategy_metrics,
            "success_rates": success_rates,
            "new_state_rates": new_state_rates,
            "active_directives": self.active_directives
        }
        
    def _register_builtin_strategies(self) -> None:
        """Register built-in strategies."""
        try:
            # Import built-in strategies
            from rv_android_core.rvdroid.strategy.basic_strategies import (
                RandomStrategy, 
                SystematicStrategy, 
                MonitoredOperationsFocusedStrategy
            )
            from rv_android_core.rvdroid.strategy.advanced_strategies import (
                PatternAwareStrategy,
                HistoryAwareStrategy
            )
            from rv_android_core.rvdroid.strategy.adaptive_strategies import (
                AdaptiveStrategy
            )
            
            # Register with registry
            StrategyRegistry.register(RandomStrategy)
            StrategyRegistry.register(SystematicStrategy)
            StrategyRegistry.register(MonitoredOperationsFocusedStrategy)
            StrategyRegistry.register(PatternAwareStrategy)
            StrategyRegistry.register(HistoryAwareStrategy)
            StrategyRegistry.register(AdaptiveStrategy)
            
            # Create strategy instances
            self.available_strategies["RandomStrategy"] = RandomStrategy(
                static_data=self.static_data
            )
            self.available_strategies["SystematicStrategy"] = SystematicStrategy(
                static_data=self.static_data
            )
            self.available_strategies["MonitoredOperationsFocusedStrategy"] = MonitoredOperationsFocusedStrategy(
                static_data=self.static_data
            )
            self.available_strategies["PatternAwareStrategy"] = PatternAwareStrategy(
                static_data=self.static_data
            )
            self.available_strategies["HistoryAwareStrategy"] = HistoryAwareStrategy(
                static_data=self.static_data
            )
            self.available_strategies["AdaptiveStrategy"] = AdaptiveStrategy(
                static_data=self.static_data
            )
            
            self.logger.info(f"Registered {len(self.available_strategies)} strategies")
            
        except ImportError as e:
            self.logger.warning(f"Could not register all built-in strategies: {e}")
            
    def _initialize_strategy_weights(self) -> None:
        """Initialize strategy weights."""
        # Set initial weights for all strategies
        for strategy_name in self.available_strategies:
            # Give higher weight to preferred strategy if specified
            if self.preferred_strategy_name and strategy_name == self.preferred_strategy_name:
                self.strategy_weights[strategy_name] = 0.5
            else:
                self.strategy_weights[strategy_name] = 0.1
                
        # Normalize weights
        self._normalize_weights()
        
    def _normalize_weights(self) -> None:
        """Normalize strategy weights to sum to 1.0."""
        total_weight = sum(self.strategy_weights.values())
        if total_weight > 0:
            for strategy_name in self.strategy_weights:
                self.strategy_weights[strategy_name] /= total_weight
                
    def _set_initial_strategy(self) -> None:
        """Set the initial active strategy."""
        if not self.available_strategies:
            self.logger.warning("No strategies available")
            return
            
        # Use preferred strategy if specified and available
        if (self.preferred_strategy_name and 
            self.preferred_strategy_name in self.available_strategies):
            self.active_strategy = self.available_strategies[self.preferred_strategy_name]
            self.logger.info(f"Using preferred strategy: {self.preferred_strategy_name}")
            return
            
        # Otherwise use the first available strategy
        strategy_name = next(iter(self.available_strategies))
        self.active_strategy = self.available_strategies[strategy_name]
        self.logger.info(f"Using default strategy: {strategy_name}")
        
    def _update_strategy_weights(self, result: Dict[str, Any]) -> None:
        """
        Update strategy weights based on performance.
        
        Args:
            result: Action execution result
        """
        if not self.active_strategy:
            return
            
        strategy_name = self.active_strategy.name
        
        # Adjust weights based on success
        if result.get("success", False):
            # Increase weight for successful strategy
            self.strategy_weights[strategy_name] *= 1.05
            
            # If new state discovered, boost weight further
            if result.get("new_state", False):
                self.strategy_weights[strategy_name] *= 1.1
                
        else:
            # Decrease weight for unsuccessful strategy
            self.strategy_weights[strategy_name] *= 0.95
            
        # Normalize weights
        self._normalize_weights()
        
    def _switch_active_strategy(self, strategy_name: str) -> bool:
        """
        Switch to a different strategy.
        
        Args:
            strategy_name: Name of strategy to switch to
            
        Returns:
            True if switch was successful
        """
        if strategy_name not in self.available_strategies:
            self.logger.warning(f"Strategy not available: {strategy_name}")
            return False
            
        self.active_strategy = self.available_strategies[strategy_name]
        self.logger.info(f"Switched to strategy: {strategy_name}")
        return True
        
    def _switch_to_fallback_strategy(self) -> None:
        """Switch to a fallback strategy if the current one fails."""
        # Find the strategy with the highest weight that's not the current one
        current_name = self.active_strategy.name if self.active_strategy else ""
        best_weight = 0.0
        best_strategy = None
        
        for name, weight in self.strategy_weights.items():
            if name != current_name and weight > best_weight:
                best_weight = weight
                best_strategy = name
                
        if best_strategy:
            self._switch_active_strategy(best_strategy)
        elif self.available_strategies:
            # If no good alternative, just pick any other strategy
            for name in self.available_strategies:
                if name != current_name:
                    self._switch_active_strategy(name)
                    break
                    
    def _check_strategy_adaptation(self, state_data: Dict[str, Any],
                                 history: Optional[List[Dict[str, Any]]]) -> bool:
        """
        Check if strategy should be adapted based on state and history.
        
        Args:
            state_data: Current state data
            history: State history
            
        Returns:
            True if strategy was switched
        """
        if not self.active_strategy:
            return False
            
        # Get current strategy name
        current_strategy = self.active_strategy.name
        
        # Detect if we're stuck in a cycle
        cycle_detected = self._detect_cycle(history)
        
        # Check for UI patterns in state data
        has_forms = "form_pattern" in state_data
        has_lists = "list_pattern" in state_data
        
        # Determine if we should switch based on context
        should_switch = False
        new_strategy = None
        
        if cycle_detected:
            # Switch to pattern-aware or random if we're stuck in a cycle
            if "PatternAwareStrategy" in self.available_strategies:
                new_strategy = "PatternAwareStrategy"
            elif "RandomStrategy" in self.available_strategies:
                new_strategy = "RandomStrategy"
                
            should_switch = True
            
        elif has_forms and current_strategy != "PatternAwareStrategy":
            # Switch to pattern-aware for forms
            if "PatternAwareStrategy" in self.available_strategies:
                new_strategy = "PatternAwareStrategy"
                should_switch = True
                
        elif has_lists and current_strategy != "SystematicStrategy":
            # Switch to systematic for lists
            if "SystematicStrategy" in self.available_strategies:
                new_strategy = "SystematicStrategy"
                should_switch = True
                
        # If a switch was determined, do it
        if should_switch and new_strategy:
            return self._switch_active_strategy(new_strategy)
            
        return False
        
    def _detect_cycle(self, history: Optional[List[Dict[str, Any]]]) -> bool:
        """
        Detect if we're stuck in a cycle.
        
        Args:
            history: State history
            
        Returns:
            True if cycle detected
        """
        if not history or len(history) < 6:
            return False
            
        # Check for repeating patterns of 2 or 3 states
        recent_states = [state.get("fingerprint") for state in history[-6:]]
        
        # Check for pattern of length 2
        if recent_states[-2:] == recent_states[-4:-2]:
            return True
            
        # Check for pattern of length 3
        if recent_states[-3:] == recent_states[-6:-3]:
            return True
            
        return False