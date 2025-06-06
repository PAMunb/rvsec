# rvandroid/rvdroid/core/action_manager.py

"""
Action management for RVDroid.

This module provides components for managing actions, including generation,
optimization, execution, and feedback processing.
"""

import time
import random
from typing import Dict, Any, Optional, List, Set, Tuple

from rv_android_core.parser.screen.visitor.model import ItemAction, ScreenDescription
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.widget import WidgetEventType
from rv_android_core.rvdroid.core.component import Component
from rv_android_core.rvdroid.executor.action_executor import ActionExecutor
from rv_android_core.rvdroid.memory.memory_system import MemorySystem
from rv_android_core.rvdroid.strategy.strategy import Strategy, StrategyRegistry
from rv_android_core.rvdroid.strategy.balancer.strategy_balancer import StrategyBalancer
from rv_android_core.util.error.decorators import handle_error
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class ActionManager(Component):
    """
    Manager for action generation, optimization, and execution in RVDroid.
    
    ### Architectural Decisions:
    - Separates action management from state management and core service
    - Provides centralized action optimization using memory system
    - Integrates with strategy system to generate contextually appropriate actions
    - Manages fallback action generation for robust operation
    - Implements feedback loop for strategy optimization
    
    ### Role in the System:
    - Generates appropriate test actions based on current application state
    - Optimizes actions to maximize testing efficiency and coverage
    - Executes actions and processes results
    - Provides feedback to strategy system for improvement
    - Ensures testing can continue even in problematic states
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the action manager.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__("ActionManager", config)
        
        # Extract configuration
        self.static_data = config.get("static_data") if config else None
        self.memory_system = config.get("memory_system")
        self.device_id = config.get("device_id", "emulator-5554")
        self.preferred_strategy_name = config.get("preferred_strategy", "SpecificationFocusedStrategy")
        
        # Initialize components
        self.action_executor = None
        self.strategy_balancer = None
        self.current_strategy = None
        
        # Statistics
        self.stats = {
            "actions_executed": 0,
            "successful_actions": 0,
            "action_generation_errors": 0,
            "action_execution_errors": 0,
        }
        
        # Initialize flags and tracking
        self.last_action = None
        self.visited_activities = set()
        self.activity_visit_counts = {}
        
    @handle_error(level="ERROR")
    def initialize(self) -> bool:
        """
        Initialize the action manager.
        
        Returns:
            True if initialization succeeded, False otherwise
        """
        self.logger.info("Initializing action manager")
        
        # Create action executor
        try:
            self.action_executor = ActionExecutor(self.device_id)
            self.logger.debug(f"Created action executor for device {self.device_id}")
        except Exception as e:
            self.logger.error(f"Failed to create action executor: {e}")
            return False
        
        # Ensure strategies are registered
        self._ensure_strategies_registered()
        
        # Create strategy balancer
        try:
            use_llm = self.config.get("use_llm", True)
            self.strategy_balancer = StrategyBalancer(self.static_data, use_llm_guidance=use_llm)
            self.logger.debug("Created strategy balancer")
        except Exception as e:
            self.logger.error(f"Failed to create strategy balancer: {e}")
            return False
        
        # Set preferred strategy if specified
        if self.preferred_strategy_name:
            self._set_preferred_strategy(self.preferred_strategy_name)
        
        # Initialize tracking
        self.visited_activities = set()
        self.activity_visit_counts = {}
        self.last_action = None
        
        # Reset statistics
        self.stats = {
            "actions_executed": 0,
            "successful_actions": 0,
            "action_generation_errors": 0,
            "action_execution_errors": 0,
        }
        
        self.initialized = True
        return True
        
    @handle_error(level="ERROR")
    def start(self) -> bool:
        """
        Start the action manager.
        
        Returns:
            True if start succeeded, False otherwise
        """
        if not self.initialized:
            self.logger.error("Cannot start: action manager not initialized")
            return False
            
        self.logger.info("Starting action manager")
        
        # Verify component dependencies
        if not self.memory_system:
            self.logger.error("Cannot start: missing memory system")
            return False
            
        if not self.strategy_balancer:
            self.logger.error("Cannot start: missing strategy balancer")
            return False
            
        if not self.action_executor:
            self.logger.error("Cannot start: missing action executor")
            return False
            
        # Get initial strategy if needed - using an empty state dictionary to avoid the error
        if not self.current_strategy and self.strategy_balancer.strategies:
            # Create a minimal state dictionary for the initial strategy selection
            empty_state = {"fingerprint": "initial", "activity": "initial"}
            self.current_strategy = self.strategy_balancer.select_strategy(empty_state)
            if self.current_strategy:
                self.logger.info(f"Selected initial strategy: {self.current_strategy.name}")
        
        self.running = True
        return True
        
    @handle_error(level="ERROR")
    def stop(self) -> bool:
        """
        Stop the action manager.
        
        Returns:
            True if stop succeeded, False otherwise
        """
        if not self.running:
            self.logger.warning("Action manager is not running")
            return True
            
        self.logger.info("Stopping action manager")
        
        # Cleanup resources
        if self.action_executor:
            try:
                self.action_executor.cleanup()
            except Exception as e:
                self.logger.warning(f"Error during action executor cleanup: {e}")
        
        self.running = False
        return True
        
    @handle_error(level="ERROR")
    def cleanup(self) -> None:
        """
        Clean up action manager resources.
        """
        self.logger.info("Cleaning up action manager")
        
        # Cleanup action executor
        if self.action_executor:
            try:
                self.action_executor.cleanup()
            except Exception as e:
                self.logger.warning(f"Error during action executor cleanup: {e}")
            self.action_executor = None
        
        # Reset strategy state
        self.current_strategy = None
        self.strategy_balancer = None
        
        # Clear tracking data
        self.visited_activities = set()
        self.activity_visit_counts = {}
        self.last_action = None
        
        self.initialized = False
        self.running = False

    @handle_error(level="WARN")
    def generate_action(self, screen: ScreenDescription, state: Dict[str, Any]) -> Optional[ItemAction]:
        """
        Generate the next action to execute based on current state.
        
        Args:
            screen: Current screen description
            state: Current state information
            
        Returns:
            Generated action or None if no action could be generated
        """
        if not self.running:
            self.logger.warning("Action manager is not running")
            return None
        
        if not screen or not screen.items:
            self.logger.warning("No screen or items available for action generation")
            return None
        
        try:
            # Ensure we have a valid strategy
            if not self.current_strategy:
                if not self._ensure_valid_strategy():
                    self.logger.error("Failed to ensure valid strategy")
                    return None
            
            # Track current activity and visited activities
            current_activity = state.get("activity", "unknown")
            
            # Update activity tracking
            self.visited_activities.add(current_activity)
            self.activity_visit_counts[current_activity] = self.activity_visit_counts.get(current_activity, 0) + 1
            
            # Get all actions from screen
            all_actions = []
            for item in screen.items:
                all_actions.extend(item.actions)
            
            # If no actions are available, return None early
            if not all_actions:
                self.logger.warning("No UI actions available")
                return None
            
            # Ensure BACK action is available
            all_actions = self._ensure_back_action_available(all_actions)
            
            # Check if this activity is potentially overexplored
            activity_count = self.activity_visit_counts.get(current_activity, 0)
            is_overexplored = activity_count > 10 and len(self.visited_activities) > 1
            
            # Optimize using memory system if available
            optimized_actions = all_actions
            if self.memory_system and hasattr(self.memory_system, 'optimize_actions'):
                try:
                    optimized_actions = self.memory_system.optimize_actions(
                        screen, state, all_actions
                    )
                except Exception as e:
                    self.logger.error(f"Memory system optimization failed: {e}, using all actions")
                    optimized_actions = all_actions
            
            # If the activity is overexplored, prioritize actions that might lead elsewhere
            if is_overexplored:
                self.logger.info(
                    f"Activity {current_activity} appears overexplored (visits={activity_count}), prioritizing navigation")
                
                # Look for navigation-related actions and monitored methods
                monitored_method_actions = []
                navigation_actions = []
                other_actions = []
                
                for action in optimized_actions:
                    # First prioritize actions that reach monitored methods
                    if hasattr(action, 'reaches_mop') and action.reaches_mop:
                        monitored_method_actions.append(action)
                        continue
                    
                    # Then check if this looks like a navigation action
                    is_navigation = False
                    
                    # Check action properties for navigation potential
                    if hasattr(action, 'target_view') and action.target_view:
                        class_name = action.target_view.get("class", "")
                        text = action.target_view.get("text", "")
                        resource_id = action.target_view.get("resource_id", "")
                        
                        # Check if this component might relate to monitored methods
                        static_analyzer = None
                        if hasattr(self.memory_system, 'exploration_optimizer') and \
                           hasattr(self.memory_system.exploration_optimizer, 'static_analyzer'):
                            static_analyzer = self.memory_system.exploration_optimizer.static_analyzer
                        
                        if static_analyzer and resource_id:
                            related_methods = static_analyzer.match_resource_to_monitored_methods(resource_id)
                            if related_methods:
                                # This component might reach monitored methods
                                monitored_method_actions.append(action)
                                continue
                        
                        # Buttons with text are likely navigation elements
                        if "Button" in class_name and text and "CLICK" in action.text:
                            is_navigation = True
                        
                        # Menu items, tabs, and similar UI elements are likely navigation
                        elif any(nav_term in class_name for nav_term in ["Menu", "Tab", "Nav", "Toolbar"]):
                            is_navigation = True
                    
                    # Add to appropriate list
                    if is_navigation:
                        navigation_actions.append(action)
                    else:
                        other_actions.append(action)
                
                # Prioritize based on exploration goals
                if monitored_method_actions:
                    self.logger.debug(f"Selected action related to monitored methods in overexplored activity")
                    return monitored_method_actions[0]  # Use the first monitored method action
                elif navigation_actions:
                    self.logger.debug(f"Selected navigation action to leave overexplored activity")
                    return navigation_actions[0]  # Use the first navigation action
            
            # Use strategy to select from optimized actions
            action = None
            try:
                action = self.current_strategy.generate_action(
                    screen,
                    state,
                    []  # No need to pass history - memory system already used it
                )
            except Exception as e:
                self.logger.error(f"Strategy action generation failed: {e}")
                self.stats["action_generation_errors"] += 1
                
                # Fall back to a random action
                if optimized_actions:
                    action = random.choice(optimized_actions)
                    self.logger.info(f"Selected random action after strategy failure: {action.id}")
            
            if action:
                self.logger.debug(f"Generated action {action.id}: {action.text}")
                return action
            
            # If strategy couldn't select an action, use the first optimized action
            if optimized_actions:
                self.logger.debug(f"Strategy didn't select an action, using first optimized action")
                return optimized_actions[0]
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error generating action: {e}")
            self.stats["action_generation_errors"] += 1
            return None

    @handle_error(level="WARN")    
    def execute_action(self, action: ItemAction) -> Dict[str, Any]:
        """
        Execute an action and return result information.
        
        Args:
            action: Action to execute
            
        Returns:
            Result dictionary with execution details
        """
        if not self.running:
            self.logger.warning("Action manager is not running")
            return {"success": False, "error": "Action manager not running"}
        
        if not action:
            self.logger.warning("No action provided for execution")
            return {"success": False, "error": "No action provided"}
        
        # Record action for later reference
        self.last_action = action
        
        # Execute the action
        success = False
        try:
            success = self.action_executor.execute_item_action(action)
            self.stats["actions_executed"] += 1
            
            if success:
                self.stats["successful_actions"] += 1
            
        except Exception as e:
            self.logger.error(f"Error executing action: {e}")
            self.stats["action_execution_errors"] += 1
            return {
                "success": False,
                "error": str(e),
                "action_id": action.id,
                "action_text": action.text
            }
        
        # Process action in memory system
        if self.memory_system:
            try:
                self.memory_system.process_action(action, success)
            except Exception as e:
                self.logger.warning(f"Error processing action in memory system: {e}")
        
        # Create result
        result = {
            "success": success,
            "action_id": action.id,
            "action_text": action.text,
            "strategy": self.current_strategy.name if self.current_strategy else "emergency"
        }
        
        return result
        
    @handle_error(level="WARN")
    def update_feedback(self, action: ItemAction, result: Dict[str, Any], 
                      previous_state: Optional[Dict[str, Any]] = None, 
                      current_state: Optional[Dict[str, Any]] = None) -> None:
        """
        Update strategy and memory system with feedback from action execution.
        
        Args:
            action: Executed action
            result: Execution result
            previous_state: State before action execution
            current_state: State after action execution
        """
        if not self.running:
            self.logger.warning("Action manager is not running")
            return
        
        # Update strategy feedback if available
        if self.current_strategy:
            try:
                self.current_strategy.update_feedback(action, result)
            except Exception as e:
                self.logger.warning(f"Error updating strategy feedback: {e}")
        
        # Update strategy balancer if available
        if self.strategy_balancer and self.current_strategy:
            try:
                self.strategy_balancer.update_performance(self.current_strategy, action, result)
            except Exception as e:
                self.logger.warning(f"Error updating strategy balancer: {e}")
        
    def generate_fallback_action(self, screen: Optional[ScreenDescription] = None) -> Optional[ItemAction]:
        """
        Generate a fallback action when normal action generation fails.
        
        Args:
            screen: Optional screen description
            
        Returns:
            Fallback action or None if no action available
        """
        if not screen or not screen.items:
            # If no screen or items, try to create a BACK action
            back_action = ItemAction(
                id=9999,
                text="BACK (Fallback)",
                event=WidgetEventType.KEY,
                target_view=None,
                coordinates=None
            )
            back_action.is_back = True
            back_action.reaches_mop = False
            back_action.directly_reaches_mop = False
            
            self.logger.info("No screen elements, creating fallback BACK action")
            return back_action
        
        # First, try to find a BACK action in the existing actions
        all_actions = []
        for item in screen.items:
            all_actions.extend(item.actions)
        
        # Look for BACK actions
        back_actions = [a for a in all_actions if "BACK" in a.text.upper()]
        if back_actions:
            self.logger.info("Using BACK action as fallback")
            return back_actions[0]
        
        # If no BACK action, select a random action
        if all_actions:
            return random.choice(all_actions)
        
        return None
        
    def get_available_strategies(self) -> List[str]:
        """
        Get list of available strategies.
        
        Returns:
            List of strategy names
        """
        return StrategyRegistry.list_strategies()
        
    def set_strategy(self, strategy_name: str) -> bool:
        """
        Set the current strategy by name.
        
        Args:
            strategy_name: Name of strategy to use
            
        Returns:
            True if strategy was set successfully, False otherwise
        """
        return self._set_preferred_strategy(strategy_name)
        
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get action execution statistics.
        
        Returns:
            Dictionary with statistics
        """
        stats = self.stats.copy()
        
        # Calculate success rate
        if stats["actions_executed"] > 0:
            stats["success_rate"] = stats["successful_actions"] / stats["actions_executed"]
        else:
            stats["success_rate"] = 0.0
            
        # Get strategy information
        if self.strategy_balancer:
            stats["strategy_info"] = self.strategy_balancer.get_strategy_statistics()
            
        # Current strategy
        if self.current_strategy:
            stats["current_strategy"] = self.current_strategy.name
            
        return stats
        
    def _ensure_valid_strategy(self) -> bool:
        """
        Ensure we have a valid strategy by trying different approaches.
        
        Returns:
            True if a valid strategy was set, False otherwise
        """
        try:
            # First try to use strategy balancer
            if self.strategy_balancer:
                self.current_strategy = self.strategy_balancer.select_strategy()
                
            # If still no strategy, create a default one
            if not self.current_strategy:
                from rv_android_core.rvdroid.strategy.basic_strategies import RandomStrategy
                self.current_strategy = RandomStrategy(self.static_data)
                self.logger.info("Created RandomStrategy directly as fallback")
                
            return self.current_strategy is not None
            
        except Exception as e:
            self.logger.error(f"Failed to create strategy: {e}")
            # Final fallback: create an extremely simple strategy
            self.current_strategy = self._create_emergency_strategy()
            return self.current_strategy is not None
            
    def _ensure_back_action_available(self, actions: List[ItemAction]) -> List[ItemAction]:
        """
        Ensure that a BACK action is available in the action list.
        
        Args:
            actions: Original list of actions
            
        Returns:
            List with BACK action added if not already present
        """
        # Check if BACK action already exists
        has_back = any("BACK" in action.text.upper() for action in actions)
        
        if not has_back:
            # Create a BACK action
            # Generate a unique ID for the BACK action
            action_id = max([action.id for action in actions], default=0) + 1000
            
            # Create the BACK action
            back_action = ItemAction(
                id=action_id,
                text=f"BACK ({action_id})",
                event=WidgetEventType.KEY,
                target_view=None,
                coordinates=None
            )
            
            # Add an is_back flag to make it easily identifiable
            back_action.is_back = True
            
            # Add reaches_mop=False and directly_reaches_mop=False attributes
            back_action.reaches_mop = False
            back_action.directly_reaches_mop = False
            
            # Add to the actions list
            self.logger.debug(f"Adding BACK action {action_id} to available actions")
            return actions + [back_action]
            
        return actions
        
    def _create_emergency_strategy(self) -> Strategy:
        """
        Create an emergency, bare-bones strategy for when all other strategies fail.
        
        This is a last-resort approach to ensure the system can continue testing.
        
        Returns:
            A minimal working Strategy implementation
        """
        from rv_android_core.rvdroid.strategy.strategy import Strategy
        import random
        
        class EmergencyStrategy(Strategy):
            def __init__(self, static_data=None):
                super().__init__(static_data, "EmergencyStrategy")
                
            def generate_action(self, screen, state_data, history=None):
                """Simply pick a random action or back button."""
                all_actions = []
                back_actions = []
                
                # Collect all actions
                for item in screen.items:
                    for action in item.actions:
                        all_actions.append(action)
                        if "BACK" in action.text.upper():
                            back_actions.append(action)
                
                # Prioritize back actions
                if back_actions and random.random() < 0.3:  # 30% chance to use back
                    return random.choice(back_actions)
                
                # Otherwise pick a random action
                if all_actions:
                    return random.choice(all_actions)
                
                return None
                
            def update_feedback(self, action, result):
                """Do nothing for this emergency strategy."""
                pass
                
        # Create and return instance
        return EmergencyStrategy(self.static_data)
        
    def _set_preferred_strategy(self, strategy_name: str) -> bool:
        """
        Set the preferred strategy by name or class type.
        
        Args:
            strategy_name: Name of the strategy class or strategy instance (case-insensitive)
            
        Returns:
            True if strategy was found and set as preferred, False otherwise
        """
        if not self.strategy_balancer or not self.strategy_balancer.strategies:
            self.logger.warning(f"Cannot set preferred strategy: no strategy balancer or strategies available")
            return False
            
        # Normalize the strategy name for comparison
        normalized_name = strategy_name.lower()
        # Add "Strategy" suffix if not already present
        if not normalized_name.endswith("strategy"):
            normalized_name = f"{normalized_name}strategy"
            
        # Try to find the strategy by class name match
        matched_strategy_info = None
        
        for strategy_info in self.strategy_balancer.strategies:
            strategy = strategy_info["strategy"]
            strategy_class_name = strategy.__class__.__name__.lower()
            strategy_instance_name = strategy.name.lower()
            
            # Check for match with class name or instance name (case-insensitive)
            if normalized_name == strategy_class_name or normalized_name == strategy_instance_name:
                matched_strategy_info = strategy_info
                break
                
        # If we didn't find an exact match, try a partial match
        if not matched_strategy_info:
            for strategy_info in self.strategy_balancer.strategies:
                strategy = strategy_info["strategy"]
                strategy_class_name = strategy.__class__.__name__.lower()
                
                # Check if the provided name is a prefix of the strategy class name
                if strategy_class_name.startswith(normalized_name.replace("strategy", "")):
                    matched_strategy_info = strategy_info
                    break
                    
        # If still no match, attempt to create the strategy directly
        if not matched_strategy_info:
            strategy_class_name = normalized_name.capitalize() if not normalized_name.startswith(
                "visual") else "VisualAwareStrategy"
                
            # Try to dynamically create the strategy
            try:
                # Import the strategy module
                if strategy_class_name == "VisualAwareStrategy":
                    from rv_android_core.rvdroid.strategy.visual_aware_strategy import VisualAwareStrategy as StrategyClass
                elif strategy_class_name == "RandomStrategy":
                    from rv_android_core.rvdroid.strategy.basic_strategies import RandomStrategy as StrategyClass
                elif strategy_class_name == "SystematicStrategy":
                    from rv_android_core.rvdroid.strategy.basic_strategies import SystematicStrategy as StrategyClass
                elif strategy_class_name in ["SecurityfocusedStrategy", "SecurityFocusedStrategy", 
                                          "SpecificationfocusedStrategy", "MonitoredmethodfocusedStrategy", 
                                          "MonitoredMethodFocusedStrategy"]:
                    from rv_android_core.rvdroid.strategy.basic_strategies import SpecificationFocusedStrategy as StrategyClass
                elif strategy_class_name == "Systematicstrategy":  # Fix for the specific error reported
                    from rv_android_core.rvdroid.strategy.basic_strategies import SystematicStrategy as StrategyClass
                    self.logger.info(f"Using SystematicStrategy for '{strategy_class_name}' request")
                else:
                    self.logger.error(f"Unknown strategy class: {strategy_class_name}")
                    # Use RandomStrategy as fallback instead of failing
                    self.logger.info(f"Using RandomStrategy as fallback for unknown strategy: {strategy_class_name}")
                    from rv_android_core.rvdroid.strategy.basic_strategies import RandomStrategy as StrategyClass
                    
                # Create the strategy
                strategy_instance = StrategyClass(self.static_data)
                
                # Add to strategy balancer
                strategy_info = {
                    "strategy": strategy_instance,
                    "weight": 1.0,
                    "performance": {
                        "new_states": 0,
                        "successful_actions": 0,
                        "total_actions": 0
                    }
                }
                
                self.strategy_balancer.strategies.append(strategy_info)
                matched_strategy_info = strategy_info
                
                # Re-normalize weights
                if hasattr(self.strategy_balancer, '_normalize_weights'):
                    self.strategy_balancer._normalize_weights()
                    
                self.logger.info(f"Created and added strategy: {strategy_class_name}")
                
            except Exception as e:
                self.logger.error(f"Failed to create strategy {strategy_class_name}: {e}")
                return False
                
        # Set the matched strategy as preferred
        if matched_strategy_info:
            # Set as preferred
            self.strategy_balancer.preferred_strategy_info = matched_strategy_info
            self.strategy_balancer.last_strategy_switch = time.time()
            
            # Set current strategy
            self.current_strategy = matched_strategy_info["strategy"]
            
            self.logger.info(
                f"Set preferred strategy to {matched_strategy_info['strategy'].__class__.__name__} ({matched_strategy_info['strategy'].name})")
            return True
        else:
            self.logger.warning(f"Could not find strategy matching '{strategy_name}'")
            return False
            
    def _ensure_strategies_registered(self):
        """
        Ensure all strategy classes are properly registered with the registry.
        
        This method checks if all required strategy classes are registered with
        the StrategyRegistry and registers any missing strategies. It supports
        both legacy names (like 'SecurityFocusedStrategy') and the new 'SpecificationFocusedStrategy'
        name for backward compatibility.
        """
        from rv_android_core.rvdroid.strategy.strategy import StrategyRegistry
        from rv_android_core.rvdroid.strategy.basic_strategies import (
            RandomStrategy,
            SystematicStrategy,
            MonitoredOperationsFocusedStrategy
        )
        from rv_android_core.rvdroid.strategy.visual_aware_strategy import VisualAwareStrategy
        
        # Check if strategies are registered
        registered_strategies = StrategyRegistry.list_strategies()
        self.logger.info(f"Currently registered strategies: {registered_strategies}")
        
        # Register any missing strategies
        for strategy_class in [RandomStrategy, SystematicStrategy, MonitoredOperationsFocusedStrategy, VisualAwareStrategy]:
            class_name = strategy_class.__name__
            if class_name not in registered_strategies:
                self.logger.info(f"Registering missing strategy: {class_name}")
                StrategyRegistry.register(strategy_class)
                
        # Verify registration
        registered_strategies = StrategyRegistry.list_strategies()
        self.logger.info(f"Updated registered strategies: {registered_strategies}")