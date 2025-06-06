"""
Exploration optimizer for RVDroid.

This module provides an advanced exploration optimization system that guides
testing toward high-value targets based on a combination of static analysis,
runtime insights, and adaptive exploration strategies.
"""

from typing import Dict, Any, List, Optional, Set, Tuple

from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.parser.screen.visitor.model import ItemAction, ScreenDescription
from rv_android_core.rvdroid.memory.short_term.short_term_memory import ShortTermMemory
from rv_android_core.rvdroid.memory.long_term.long_term_memory import LongTermMemory
from rv_android_core.rvdroid.memory.patterns.pattern_recognition import PatternRecognition
from rv_android_core.rvdroid.analysis.static_analyzer import EnhancedStaticAnalyzer
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.performance_monitor import PerformanceMonitor


class ExplorationOptimizer:
    """
    Advanced exploration optimizer that guides testing toward high-value targets.
    
    ### Architectural Decisions:
    - Implements adaptive exploration phases with specialized targeting
    - Combines runtime observations with static analysis insights
    - Uses a multi-factor scoring system for dynamic prioritization
    - Maintains exploration state to prevent redundant exploration
    - Avoids common exploration pitfalls through pattern recognition
    
    ### Role in the System:
    - Guides testing strategies toward monitored methods
    - Balances breadth-first and depth-first exploration
    - Prevents getting stuck in exploration plateaus
    - Prioritizes paths that maximize specification coverage
    - Adapts guidance based on discovered application behavior
    
    ### Key Considerations:
    - Exploration efficiency in large state spaces
    - Balance between targeted testing and general coverage
    - Responsiveness to LLM directives
    - Dynamic adaptation to application feedback
    - Explicit distinction between specification types
    """

    def __init__(self, short_term_memory: ShortTermMemory,
                 long_term_memory: LongTermMemory,
                 pattern_recognition: PatternRecognition,
                 static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the exploration optimizer.
        
        Args:
            short_term_memory: Short-term memory component
            long_term_memory: Long-term memory component
            pattern_recognition: Pattern recognition component
            static_data: Optional static analysis data
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.memory.exploration_optimizer",
            {CONTEXT_COMPONENT: "ExplorationOptimizer"}
        )
        
        # Initialize performance monitor
        self.performance_monitor = PerformanceMonitor.get_instance()
        
        # Store components
        self.short_term_memory = short_term_memory
        self.long_term_memory = long_term_memory
        self.pattern_recognition = pattern_recognition
        
        # Create enhanced static analyzer if static data is provided
        self.static_analyzer = EnhancedStaticAnalyzer(static_data) if static_data else None
        
        # Exploration phases
        self.exploration_phases = [
            "initial_exploration",   # Initial breadth-first exploration
            "targeted_exploration",  # Target specific monitored methods
            "deep_exploration",      # Deep exploration of promising paths
            "coverage_optimization", # Focus on coverage gaps
            "regression_testing"     # Test previously discovered violations
        ]
        
        # Current exploration state
        self.exploration_phase = "initial_exploration"
        self.phase_start_time = 0
        self.phase_switch_count = 0
        
        # Exploration parameters - adjustable based on phase and directives
        self.exploration_parameters = {
            "breadth_factor": 0.7,          # Preference for breadth-first exploration
            "monitored_method_factor": 0.8, # Preference for monitored methods
            "crypto_spec_factor": 0.5,      # Preference for crypto specifications
            "general_api_factor": 0.5,      # Preference for general API specifications
            "novelty_factor": 0.6,          # Preference for unexplored elements
            "plateau_escape_factor": 0.3,   # Preference for escaping plateaus
            "randomization_factor": 0.2     # Random exploration to avoid stuck states
        }
        
        # Exploration statistics
        self.exploration_statistics = {
            "actions_attempted": 0,
            "new_states_discovered": 0,
            "monitored_methods_reached": 0,
            "crypto_specifications_reached": 0,
            "general_api_specifications_reached": 0,
            "exploration_plateaus_encountered": 0,
            "exploration_plateaus_escaped": 0,
            "phase_switches": 0
        }
        
        # Tracking for exploration
        self.visited_components: Set[str] = set()
        self.component_visit_counts: Dict[str, int] = {}
        self.recent_actions: List[int] = []
        self.action_scores: Dict[int, float] = {}
        
        # Track monitored method hits
        self.monitored_method_hits: Dict[str, int] = {}
        
        # Track activity coverage
        self.visited_activities: Set[str] = set()
        self.activity_visit_counts: Dict[str, int] = {}
        self.stuck_detection_count = 0
        
        # Monitored method classification tracking
        self.specification_coverage = {
            "crypto": {
                "reached": set(),
                "total": 0
            },
            "general_api": {
                "reached": set(),
                "total": 0
            }
        }
        
        # Initialize if we have static analysis
        if self.static_analyzer:
            self._initialize_from_static_analysis()
            
        self.logger.info("Initialized exploration optimizer")
        
    def _initialize_from_static_analysis(self) -> None:
        """
        Initialize exploration data from static analysis.
        
        Sets up initial knowledge about monitored methods, their types,
        and potential exploration targets based on static analysis.
        """
        if not self.static_analyzer:
            return
            
        # Count monitored methods by type
        crypto_methods = self.static_analyzer.get_monitored_methods("crypto")
        general_api_methods = self.static_analyzer.get_monitored_methods("general_api")
        
        self.specification_coverage["crypto"]["total"] = len(crypto_methods)
        self.specification_coverage["general_api"]["total"] = len(general_api_methods)
        
        total_monitored = len(self.static_analyzer.get_monitored_methods())
        
        # Log monitored method breakdown
        self.logger.info(f"Exploration targeting {total_monitored} monitored methods: " +
                       f"{len(crypto_methods)} crypto, {len(general_api_methods)} general API")
                       
        # Adjust exploration parameters based on application profile
        if crypto_methods and general_api_methods:
            # Balanced application with both types
            self.crypto_spec_factor = 0.6
            self.general_api_factor = 0.6
        elif crypto_methods and not general_api_methods:
            # Crypto-focused application
            self.crypto_spec_factor = 0.8
            self.general_api_factor = 0.3
        elif not crypto_methods and general_api_methods:
            # General API-focused application
            self.crypto_spec_factor = 0.3
            self.general_api_factor = 0.8
            
        # Initialize with windows that have monitored methods
        windows_with_monitored_methods = self.static_analyzer.get_windows_with_monitored_methods()
        self.logger.info(f"Identified {len(windows_with_monitored_methods)} windows with monitored methods")
        
    def record_action_result(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Record the result of an action execution.
        
        Args:
            action: Action that was executed
            result: Execution result
        """
        # Update statistics
        self.exploration_statistics["actions_attempted"] += 1
        
        # Track action
        self.recent_actions = (self.recent_actions + [action.id])[-10:]  # Keep last 10 actions
        
        # Update exploration state based on result
        success = result.get("success", False)
        new_state = result.get("new_state", False)
        
        # Track resource ID and component
        resource_id = ""
        if hasattr(action, 'target_view') and action.target_view:
            resource_id = action.target_view.get("resource_id", "")
            
        if resource_id:
            # Track component visits
            if resource_id not in self.visited_components:
                self.visited_components.add(resource_id)
                self.component_visit_counts[resource_id] = 1
            else:
                self.component_visit_counts[resource_id] += 1
                
        # Track new state discoveries
        if new_state:
            self.exploration_statistics["new_states_discovered"] += 1
            
            # Reset stuck detection if we found a new state
            self.stuck_detection_count = 0
        else:
            # Increment stuck detection counter
            self.stuck_detection_count += 1
            
            # Detect if we're stuck in a plateau
            if self.stuck_detection_count >= 5:
                self.exploration_statistics["exploration_plateaus_encountered"] += 1
                
                # Consider phase transition if stuck
                if self.exploration_phase == "initial_exploration":
                    self._transition_to_phase("targeted_exploration")
                    self.exploration_statistics["exploration_plateaus_escaped"] += 1
                    self.stuck_detection_count = 0
        
        # Track activity
        current_activity = result.get("current_state_activity", "unknown")
        if current_activity and current_activity != "unknown":
            if current_activity not in self.visited_activities:
                self.visited_activities.add(current_activity)
                self.activity_visit_counts[current_activity] = 1
            else:
                self.activity_visit_counts[current_activity] += 1
        
        # Check if action reached monitored methods
        if action.reaches_mop or action.directly_reaches_mop:
            self.exploration_statistics["monitored_methods_reached"] += 1
            
            # Track by specification type if we have static analysis
            if self.static_analyzer and resource_id:
                # Match the resource to monitored methods
                related_methods = self.static_analyzer.match_resource_to_monitored_methods(resource_id)
                
                for method_info in related_methods:
                    spec_type = method_info.get("specification_type", "unknown")
                    method_sig = method_info.get("signature", "")
                    
                    if not method_sig:
                        continue
                        
                    # Track method hit
                    if method_sig not in self.monitored_method_hits:
                        self.monitored_method_hits[method_sig] = 0
                    self.monitored_method_hits[method_sig] += 1
                    
                    # Track by specification type
                    if spec_type == "crypto":
                        self.exploration_statistics["crypto_specifications_reached"] += 1
                        self.specification_coverage["crypto"]["reached"].add(method_sig)
                    elif spec_type == "general_api":
                        self.exploration_statistics["general_api_specifications_reached"] += 1
                        self.specification_coverage["general_api"]["reached"].add(method_sig)
        
        # Evaluate exploration phase transition
        self._evaluate_phase_transition()
        
    def _evaluate_phase_transition(self) -> None:
        """
        Evaluate whether to transition to a different exploration phase.
        
        Analyzes current exploration performance to determine if a phase
        transition would be beneficial for effective testing.
        """
        # Skip if we haven't executed enough actions yet
        if self.exploration_statistics["actions_attempted"] < 20:
            return
            
        current_phase = self.exploration_phase
        
        # Transition logic based on current phase and progress
        if current_phase == "initial_exploration":
            # Transition to targeted exploration if:
            # 1. We've discovered a significant number of states
            # 2. We've visited multiple activities
            # 3. We've encountered monitored methods
            states_discovered = self.exploration_statistics["new_states_discovered"]
            activities_visited = len(self.visited_activities)
            
            if (states_discovered >= 10 and activities_visited >= 3) or \
               (self.exploration_statistics["monitored_methods_reached"] > 0 and states_discovered >= 5):
                self._transition_to_phase("targeted_exploration")
                
        elif current_phase == "targeted_exploration":
            # Transition to deep exploration if:
            # 1. We've reached several monitored methods
            # 2. We've plateaued in discovering new states
            monitored_reached = self.exploration_statistics["monitored_methods_reached"]
            actions_since_transition = self.exploration_statistics["actions_attempted"] - self.phase_start_time
            
            if (monitored_reached >= 5 and actions_since_transition >= 30) or \
               (self.stuck_detection_count >= 8):
                self._transition_to_phase("deep_exploration")
                
        elif current_phase == "deep_exploration":
            # Transition to coverage optimization if:
            # 1. We've reached a significant number of monitored methods
            # 2. We've been in deep exploration for a while
            actions_since_transition = self.exploration_statistics["actions_attempted"] - self.phase_start_time
            
            if actions_since_transition >= 50:
                self._transition_to_phase("coverage_optimization")
                
        elif current_phase == "coverage_optimization":
            # Transition to regression testing if:
            # 1. We've reached most potential monitored methods
            # 2. We've been optimizing coverage for a while
            actions_since_transition = self.exploration_statistics["actions_attempted"] - self.phase_start_time
            
            if actions_since_transition >= 50:
                self._transition_to_phase("regression_testing")
                
        elif current_phase == "regression_testing":
            # Potentially start over at targeted exploration
            actions_since_transition = self.exploration_statistics["actions_attempted"] - self.phase_start_time
            
            if actions_since_transition >= 30:
                self._transition_to_phase("targeted_exploration")
        
    def _transition_to_phase(self, new_phase: str) -> None:
        """
        Transition to a new exploration phase.
        
        Args:
            new_phase: Name of the new phase
        """
        if new_phase not in self.exploration_phases:
            self.logger.warning(f"Invalid exploration phase: {new_phase}")
            return
            
        old_phase = self.exploration_phase
        
        if old_phase == new_phase:
            return
            
        self.logger.info(f"Transitioning exploration phase: {old_phase} -> {new_phase}")
        
        # Update phase
        self.exploration_phase = new_phase
        self.phase_start_time = self.exploration_statistics["actions_attempted"]
        self.phase_switch_count += 1
        self.exploration_statistics["phase_switches"] += 1
        
        # Adjust parameters for the new phase
        self._adjust_parameters_for_phase(new_phase)
        
    def _adjust_parameters_for_phase(self, phase: str) -> None:
        """
        Adjust exploration parameters for a specific phase.
        
        Args:
            phase: Exploration phase
        """
        if phase == "initial_exploration":
            # Favor breadth-first exploration to discover application structure
            self.exploration_parameters["breadth_factor"] = 0.8
            self.exploration_parameters["novelty_factor"] = 0.8
            self.exploration_parameters["monitored_method_factor"] = 0.3
            self.exploration_parameters["randomization_factor"] = 0.2
            
        elif phase == "targeted_exploration":
            # Focus on reaching monitored methods
            self.exploration_parameters["breadth_factor"] = 0.4
            self.exploration_parameters["novelty_factor"] = 0.5
            self.exploration_parameters["monitored_method_factor"] = 0.9
            self.exploration_parameters["randomization_factor"] = 0.1
            
        elif phase == "deep_exploration":
            # Explore monitored methods more thoroughly
            self.exploration_parameters["breadth_factor"] = 0.2
            self.exploration_parameters["novelty_factor"] = 0.3
            self.exploration_parameters["monitored_method_factor"] = 0.7
            self.exploration_parameters["randomization_factor"] = 0.1
            
        elif phase == "coverage_optimization":
            # Focus on improving overall coverage
            self.exploration_parameters["breadth_factor"] = 0.6
            self.exploration_parameters["novelty_factor"] = 0.7
            self.exploration_parameters["monitored_method_factor"] = 0.5
            self.exploration_parameters["randomization_factor"] = 0.3
            
        elif phase == "regression_testing":
            # Revisit previously identified operations of interest
            self.exploration_parameters["breadth_factor"] = 0.3
            self.exploration_parameters["novelty_factor"] = 0.2
            self.exploration_parameters["monitored_method_factor"] = 0.9
            self.exploration_parameters["randomization_factor"] = 0.1
            
        # Log parameter adjustments
        self.logger.info(f"Adjusted parameters for phase {phase}: " +
                       f"breadth={self.exploration_parameters['breadth_factor']:.1f}, " +
                       f"novelty={self.exploration_parameters['novelty_factor']:.1f}, " +
                       f"monitored={self.exploration_parameters['monitored_method_factor']:.1f}")
        
    def optimize_action_selection(self, screen: ScreenDescription,
                                 state_data: Dict[str, Any],
                                 available_actions: List[ItemAction]) -> List[ItemAction]:
        """
        Optimize the selection of actions based on exploration strategy.
        
        Args:
            screen: Current screen description
            state_data: Current state data
            available_actions: List of available actions
            
        Returns:
            Prioritized list of actions
        """
        if not available_actions:
            return []
            
        with self.performance_monitor.measure_time("optimize_action_selection"):
            # Get current activity
            current_activity = state_data.get("activity", "unknown")
            
            # Get current window ID - don't rely on screen.id which doesn't exist
            current_window_id = state_data.get("window_id", "") or ""
            
            # If we don't have a window_id, try to get one from static data based on activity
            if not current_window_id and self.static_analyzer and hasattr(self.static_analyzer, 'activity_window_map'):
                if current_activity in self.static_analyzer.activity_window_map:
                    window = self.static_analyzer.activity_window_map[current_activity]
                    current_window_id = window.id
            
            # Score each action
            scored_actions = []
            
            for action in available_actions:
                # Calculate base score
                score = self._calculate_action_score(action, screen, state_data)
                
                # Store in scored actions
                scored_actions.append((action, score))
            
            # Sort by score (highest first)
            scored_actions.sort(key=lambda x: x[1], reverse=True)
            
            # Extract actions from scored tuples
            optimized_actions = [a for a, _ in scored_actions]
            
            # Log optimization details for top actions
            if len(optimized_actions) > 0:
                top_action = optimized_actions[0]
                self.logger.debug(f"Top action: {top_action.id} with score {scored_actions[0][1]:.2f}")
                
            return optimized_actions
            
    def _calculate_action_score(self, action: ItemAction, screen: ScreenDescription,
                               state_data: Dict[str, Any]) -> float:
        """
        Calculate a score for an action based on multiple factors.
        
        Args:
            action: Action to score
            screen: Current screen description
            state_data: Current state data
            
        Returns:
            Score for the action
        """
        # Start with a base score
        score = 1.0
        
        # Extract resource ID if available
        resource_id = ""
        if hasattr(action, 'target_view') and action.target_view:
            resource_id = action.target_view.get("resource_id", "")
        
        # Factor 1: Monitored method relevance
        if action.directly_reaches_mop:
            score *= (1.0 + self.exploration_parameters["monitored_method_factor"])
        elif action.reaches_mop:
            score *= (1.0 + (self.exploration_parameters["monitored_method_factor"] * 0.7))
            
        # Check if this component may reach monitored methods
        if self.static_analyzer and resource_id:
            related_methods = self.static_analyzer.match_resource_to_monitored_methods(resource_id)
            
            if related_methods:
                # Boost based on specification types
                crypto_methods = [m for m in related_methods if m.get("specification_type") == "crypto"]
                general_api_methods = [m for m in related_methods if m.get("specification_type") == "general_api"]
                
                if crypto_methods:
                    score *= (1.0 + (self.exploration_parameters["crypto_spec_factor"] * 0.5))
                if general_api_methods:
                    score *= (1.0 + (self.exploration_parameters["general_api_factor"] * 0.5))
        
        # Factor 2: Novelty - prefer previously unexplored items
        if resource_id in self.component_visit_counts:
            visit_count = self.component_visit_counts[resource_id]
            
            # Apply diminishing returns to repeat visits
            if visit_count == 0:
                score *= (1.0 + self.exploration_parameters["novelty_factor"])
            elif visit_count == 1:
                score *= (1.0 + (self.exploration_parameters["novelty_factor"] * 0.5))
            else:
                # Penalize frequently visited components
                score *= max(0.3, 1.0 - (min(visit_count, 10) * 0.07))
                
        else:
            # Boost completely new components
            score *= (1.0 + self.exploration_parameters["novelty_factor"])
        
        # Factor 3: Recency - avoid very recent actions
        if action.id in self.recent_actions:
            # More severe penalty for very recent actions
            recency_index = self.recent_actions[::-1].index(action.id)
            penalty = max(0.3, 1.0 - ((5 - recency_index) * 0.15))
            score *= penalty
            
        # Factor 4: Breadth vs. depth
        if self.exploration_parameters["breadth_factor"] > 0.5:
            # In breadth-first mode, prefer actions that might lead to new screens
            if hasattr(action, 'target_view') and action.target_view:
                view_class = action.target_view.get("class", "")
                view_text = action.target_view.get("text", "")
                
                # Buttons with text are likely navigation
                if "Button" in view_class and view_text:
                    score *= (1.0 + ((self.exploration_parameters["breadth_factor"] - 0.5) * 0.6))
                    
                # Menu items, tabs, etc.
                if any(nav in view_class for nav in ["Menu", "Tab", "Navigation"]):
                    score *= (1.0 + ((self.exploration_parameters["breadth_factor"] - 0.5) * 0.8))
        
        # Factor 5: Plateau escape
        if self.stuck_detection_count >= 3:
            # If potentially stuck, add randomization factor
            import random
            score *= (1.0 + (random.random() * self.exploration_parameters["randomization_factor"]))
            
        # Factor 6: Element type prioritization
        if hasattr(action, 'target_view') and action.target_view:
            view_class = action.target_view.get("class", "")
            
            # Prioritize interactive elements
            if "EditText" in view_class:
                score *= 1.3  # Text inputs are important
            elif "Spinner" in view_class or "DropDown" in view_class:
                score *= 1.2  # Selection elements often affect state
            elif "CheckBox" in view_class or "RadioButton" in view_class or "Toggle" in view_class:
                score *= 1.1  # Toggle controls affect state
                
        # Store the score for debugging/analysis
        self.action_scores[action.id] = score
            
        return score
        
    def get_recommendations(self, screen: ScreenDescription,
                           state_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get exploration recommendations for the current state.
        
        Args:
            screen: Current screen description
            state_data: Current state data
            
        Returns:
            Exploration recommendations
        """
        current_activity = state_data.get("activity", "unknown")
        
        # Get window ID from state data or try to derive it from activity
        current_window_id = state_data.get("window_id", "")
        
        # If we don't have a window_id, try to derive it from the current activity
        if not current_window_id and self.static_analyzer and hasattr(self.static_analyzer, 'activity_window_map'):
            if current_activity in self.static_analyzer.activity_window_map:
                window = self.static_analyzer.activity_window_map[current_activity]
                current_window_id = window.id
        
        # Generate a window ID from activity name if we still don't have one
        if not current_window_id:
            # Simple fallback - use activity name as window ID
            current_window_id = current_activity
        
        recommendations = {
            "exploration_phase": self.exploration_phase,
            "focus_elements": [],
            "avoid_elements": [],
            "navigation_suggestions": [],
            "exploration_status": "normal"
        }
        
        # Check for plateau
        if self.stuck_detection_count >= 5:
            recommendations["exploration_status"] = "plateau"
            
            # Recommend back navigation in case of plateau
            recommendations["navigation_suggestions"].append({
                "type": "back_navigation",
                "reason": "Potential exploration plateau detected"
            })
            
        # Use static analyzer for recommendations if available
        if self.static_analyzer:
            # Check if current window has monitored methods
            window_components = self.static_analyzer.get_components_reaching_monitored_methods(current_window_id)
            
            if window_components:
                # Suggest focusing on components with monitored methods
                for component in window_components:
                    recommendations["focus_elements"].append({
                        "component_id": component["component_id"],
                        "resource_id": component["resource_id"],
                        "reason": "Component may reach monitored methods"
                    })
                    
            else:
                # No monitored methods in current window, suggest navigation
                path_info = self.static_analyzer.get_path_to_nearest_monitored_method(current_window_id)
                
                if path_info:
                    recommendations["navigation_suggestions"].append({
                        "type": "navigational_path",
                        "target_activity": path_info["target_activity"],
                        "reason": "Window contains monitored methods"
                    })
        
        # Add recommendations based on exploration phase
        if self.exploration_phase == "initial_exploration":
            recommendations["strategy_suggestion"] = "Explore broadly to discover application structure"
        elif self.exploration_phase == "targeted_exploration":
            recommendations["strategy_suggestion"] = "Focus on components reaching monitored methods"
        elif self.exploration_phase == "deep_exploration":
            recommendations["strategy_suggestion"] = "Deep exploration of monitored method functionality"
        elif self.exploration_phase == "coverage_optimization":
            recommendations["strategy_suggestion"] = "Optimize coverage by exploring remaining areas"
        elif self.exploration_phase == "regression_testing":
            recommendations["strategy_suggestion"] = "Revisit previously discovered monitored methods"
            
        return recommendations
        
    def process_llm_directive(self, directive: Dict[str, Any]) -> bool:
        """
        Process a directive from the LLM to adjust exploration.
        
        Args:
            directive: LLM directive
            
        Returns:
            True if directive was processed successfully, False otherwise
        """
        directive_type = directive.get("type", "")
        
        # Process based on directive type
        if directive_type == "exploration_focus":
            # Adjust exploration focus
            focus = directive.get("focus", "")
            
            if focus == "breadth":
                self.exploration_parameters["breadth_factor"] = min(1.0, self.exploration_parameters["breadth_factor"] + 0.2)
                self.logger.info(f"Adjusted breadth factor to {self.exploration_parameters['breadth_factor']:.2f}")
                return True
                
            elif focus == "depth":
                self.exploration_parameters["breadth_factor"] = max(0.0, self.exploration_parameters["breadth_factor"] - 0.2)
                self.logger.info(f"Adjusted breadth factor to {self.exploration_parameters['breadth_factor']:.2f}")
                return True
                
            elif focus == "monitored_methods":
                self.exploration_parameters["monitored_method_factor"] = min(1.0, self.exploration_parameters["monitored_method_factor"] + 0.2)
                self.logger.info(f"Adjusted monitored method factor to {self.exploration_parameters['monitored_method_factor']:.2f}")
                return True
                
            elif focus == "crypto":
                self.exploration_parameters["crypto_spec_factor"] = min(1.0, self.exploration_parameters["crypto_spec_factor"] + 0.2)
                self.logger.info(f"Adjusted crypto factor to {self.exploration_parameters['crypto_spec_factor']:.2f}")
                return True
                
            elif focus == "general_api":
                self.exploration_parameters["general_api_factor"] = min(1.0, self.exploration_parameters["general_api_factor"] + 0.2)
                self.logger.info(f"Adjusted general API factor to {self.exploration_parameters['general_api_factor']:.2f}")
                return True
                
        elif directive_type == "phase_transition":
            # Transition to a specific phase
            target_phase = directive.get("phase", "")
            
            if target_phase in self.exploration_phases:
                self._transition_to_phase(target_phase)
                return True
                
        elif directive_type == "randomization":
            # Adjust randomization to escape plateaus
            randomization = directive.get("level", 0.3)
            
            if isinstance(randomization, (int, float)):
                self.exploration_parameters["randomization_factor"] = min(1.0, max(0.0, float(randomization)))
                self.logger.info(f"Adjusted randomization factor to {self.exploration_parameters['randomization_factor']:.2f}")
                return True
                
        return False
        
    def get_progress_summary(self) -> Dict[str, Any]:
        """
        Get a summary of exploration progress.
        
        Returns:
            Dictionary with exploration progress metrics
        """
        # Calculate coverage percentages
        crypto_coverage = 0.0
        general_api_coverage = 0.0
        
        if self.specification_coverage["crypto"]["total"] > 0:
            crypto_coverage = len(self.specification_coverage["crypto"]["reached"]) / self.specification_coverage["crypto"]["total"]
            
        if self.specification_coverage["general_api"]["total"] > 0:
            general_api_coverage = len(self.specification_coverage["general_api"]["reached"]) / self.specification_coverage["general_api"]["total"]
            
        # Create summary
        summary = {
            "exploration_phase": self.exploration_phase,
            "actions_attempted": self.exploration_statistics["actions_attempted"],
            "new_states_discovered": self.exploration_statistics["new_states_discovered"],
            "unique_activities_seen": len(self.visited_activities),
            "monitored_methods_reached": self.exploration_statistics["monitored_methods_reached"],
            "crypto_specifications": {
                "reached": len(self.specification_coverage["crypto"]["reached"]),
                "total": self.specification_coverage["crypto"]["total"],
                "coverage": crypto_coverage
            },
            "general_api_specifications": {
                "reached": len(self.specification_coverage["general_api"]["reached"]),
                "total": self.specification_coverage["general_api"]["total"],
                "coverage": general_api_coverage
            },
            "plateaus": {
                "encountered": self.exploration_statistics["exploration_plateaus_encountered"],
                "escaped": self.exploration_statistics["exploration_plateaus_escaped"]
            },
            "phase_switches": self.exploration_statistics["phase_switches"],
            "exploration_parameters": self.exploration_parameters
        }
        
        return summary
