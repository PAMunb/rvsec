# rvandroid/rvdroid/strategy/adaptive_strategies.py
"""
Adaptive strategies for RVDroid testing.

This module implements adaptive testing strategies that adjust their behavior
during execution without requiring pre-trained machine learning models.
"""

import random
import time
import math
import collections
from typing import List, Dict, Any, Optional, Set, Tuple, Deque

from rv_android_core.domain.static import StaticAnalysisData
from rv_screen_parser.parser.screen.visitor.model import ItemAction, ScreenDescription
from rvdroid_tool.strategy.strategy import Strategy, StrategyRegistry


@StrategyRegistry.register
class SimulatedAnnealingStrategy(Strategy):
    """
    A strategy based on simulated annealing principles for adaptive exploration.
    
    Simulated annealing is a probabilistic technique that balances exploration
    and exploitation by gradually reducing randomness over time, similar to the
    metallurgical annealing process.
    
    ### Architectural Decisions:
    - Uses temperature parameter to control exploration vs. exploitation balance
    - Gradually reduces temperature (randomness) over time
    - Accepts suboptimal actions with decreasing probability
    - Maintains action value estimates based on execution feedback
    
    ### Role in the System:
    - Allows broad exploration in early testing phases
    - Gradually focuses on high-value actions as testing progresses
    - Avoids getting stuck in local optima through probabilistic selection
    - Adapts to application behavior without requiring pre-training
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the simulated annealing strategy.
        
        Args:
            static_data: Optional static analysis data
        """
        super().__init__(static_data, "SimulatedAnnealingStrategy")
        
        # Action values (estimated utility)
        self.action_values: Dict[int, float] = {}
        
        # Initial temperature (controls randomness)
        self.initial_temperature = 10.0
        self.temperature = self.initial_temperature
        
        # Cooling rate (how fast temperature decreases)
        self.cooling_rate = 0.95
        
        # Minimum temperature 
        self.min_temperature = 0.1
        
        # Action executed count
        self.action_executed: Dict[int, int] = {}
        
        # Track performance metrics
        self.metrics = {
            "actions_executed": 0,
            "best_action_value": 0.0,
            "temperature": self.temperature,
            "exploration_rate": 1.0
        }
        
        # Keep track of security-relevant actions
        self.security_actions: Set[int] = set()
        
        # Start time for cooling schedule
        self.start_time = time.time()
        
        # Track states where actions were executed
        self.state_action_map: Dict[str, Dict[int, float]] = {}
        
        # Initialize logger
        self.logger.info("Initialized SimulatedAnnealingStrategy")
    
    def generate_action(self, screen: ScreenDescription, state_data: Dict[str, Any], 
                        history: Optional[List[Dict[str, Any]]] = None) -> Optional[ItemAction]:
        """
        Generate the next action using simulated annealing principles.
        
        Args:
            screen: Current screen description
            state_data: Current state data 
            history: Optional execution history
            
        Returns:
            Selected action or None if no actions available
        """
        # Collect available actions
        available_actions = self._collect_actions(screen)
        if not available_actions:
            return None
        
        # Update temperature based on elapsed time
        self._update_temperature()
        
        # Get current state identifier
        state_id = state_data.get("fingerprint", "unknown")
        
        # Initialize state-action map for this state if needed
        if state_id not in self.state_action_map:
            self.state_action_map[state_id] = {}
        
        # Calculate action values in this state
        action_values = {}
        for action in available_actions:
            action_id = action.id
            
            # Initialize with default value if not seen before
            if action_id not in self.action_values:
                self.action_values[action_id] = 0.5
                
            # Get base value
            value = self.action_values[action_id]
            
            # Adjust for security relevance
            if getattr(action, 'reaches_mop', False):
                value += 0.2
                self.security_actions.add(action_id)
            
            if getattr(action, 'directly_reaches_mop', False):
                value += 0.3
                self.security_actions.add(action_id)
            
            # Adjust for state-specific performance
            if action_id in self.state_action_map[state_id]:
                state_specific_value = self.state_action_map[state_id][action_id]
                # Blend global and state-specific value
                value = 0.3 * value + 0.7 * state_specific_value
            
            # Add exploration bonus for rarely executed actions
            exec_count = self.action_executed.get(action_id, 0)
            if exec_count == 0:
                value += 0.2  # Bonus for never-executed actions
            else:
                value += 0.1 / math.sqrt(exec_count)  # Diminishing bonus
                
            action_values[action_id] = value
        
        # Determine if we should explore or exploit
        if random.random() < self._get_exploration_probability():
            # Exploration: select randomly but still favor valuable actions
            return self._weighted_random_selection(available_actions, action_values)
        else:
            # Exploitation: select the best action with simulated annealing
            return self._annealing_selection(available_actions, action_values)
    
    def update_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Update action values based on execution feedback.
        
        Args:
            action: Executed action
            result: Execution result
        """
        # Extract key information
        action_id = action.id
        success = result.get("success", False)
        new_state = result.get("new_state", False)
        state_id = result.get("previous_state", "unknown")
        
        # Update execution count
        self.action_executed[action_id] = self.action_executed.get(action_id, 0) + 1
        self.metrics["actions_executed"] += 1
        
        # Calculate reward for this action
        reward = self._calculate_reward(action, result)
        
        # Update action value with learning rate that decreases with more executions
        learning_rate = 1.0 / math.sqrt(self.action_executed[action_id])
        current_value = self.action_values.get(action_id, 0.5)
        new_value = current_value + learning_rate * (reward - current_value)
        
        # Ensure value stays in [0,1] range
        new_value = max(0.0, min(1.0, new_value))
        self.action_values[action_id] = new_value
        
        # Update state-specific action value
        if state_id not in self.state_action_map:
            self.state_action_map[state_id] = {}
        
        current_state_value = self.state_action_map[state_id].get(action_id, 0.5)
        new_state_value = current_state_value + learning_rate * (reward - current_state_value)
        new_state_value = max(0.0, min(1.0, new_state_value))
        self.state_action_map[state_id][action_id] = new_state_value
        
        # Update metrics
        self.metrics["best_action_value"] = max(self.action_values.values()) if self.action_values else 0.0
        self.metrics["temperature"] = self.temperature
        self.metrics["exploration_rate"] = self._get_exploration_probability()
        
        # Log significant changes
        if new_value > current_value + 0.2:
            self.logger.info(f"Action {action_id} value increased significantly: {current_value:.2f} -> {new_value:.2f}")
    
    def _collect_actions(self, screen: ScreenDescription) -> List[ItemAction]:
        """
        Collect all available actions from a screen.
        
        Args:
            screen: Current screen description
            
        Returns:
            List of all available actions
        """
        all_actions = []
        for item in screen.items:
            all_actions.extend(item.actions)
        return all_actions
    
    def _update_temperature(self) -> None:
        """
        Update the temperature parameter based on time elapsed.
        
        This implementation uses a time-based cooling schedule that reduces
        temperature over the course of testing, eventually focusing on exploitation.
        """
        # Only cool if above minimum temperature
        if self.temperature <= self.min_temperature:
            return
            
        # Calculate elapsed time
        elapsed_time = time.time() - self.start_time
        
        # Cool based on time (every 30 seconds)
        elapsed_minutes = elapsed_time / 30  # Cool every 30 seconds
        
        # Calculate new temperature
        self.temperature = self.initial_temperature * (self.cooling_rate ** elapsed_minutes)
        
        # Enforce minimum temperature
        self.temperature = max(self.min_temperature, self.temperature)
    
    def _get_exploration_probability(self) -> float:
        """
        Calculate the probability of exploring instead of exploiting.
        
        Returns:
            Probability of exploration [0-1]
        """
        # Use temperature to determine exploration probability
        # Higher temperature = more exploration
        return self.temperature / self.initial_temperature
    
    def _weighted_random_selection(self, actions: List[ItemAction], values: Dict[int, float]) -> ItemAction:
        """
        Select an action using weighted random selection.
        
        Args:
            actions: List of actions to choose from
            values: Dictionary of action values
            
        Returns:
            Selected action
        """
        # Calculate selection weights
        weights = []
        for action in actions:
            # Default weight is 1.0
            weight = 1.0
            
            # Adjust weight by value
            if action.id in values:
                # Scale to make differences more significant
                weight = 1.0 + (values[action.id] * 2.0)
                
            weights.append(weight)
        
        # Normalize weights to sum to 1
        total = sum(weights)
        if total <= 0:
            # If all weights are non-positive, use uniform selection
            return random.choice(actions)
        
        # Convert to probabilities
        probs = [w/total for w in weights]
        
        # Weighted random selection
        return random.choices(actions, weights=probs, k=1)[0]
    
    def _annealing_selection(self, actions: List[ItemAction], values: Dict[int, float]) -> ItemAction:
        """
        Select an action using simulated annealing principles.
        
        Args:
            actions: List of actions to choose from
            values: Dictionary of action values
            
        Returns:
            Selected action
        """
        # Find the best action by value
        best_action = None
        best_value = -float('inf')
        
        for action in actions:
            value = values.get(action.id, 0.0)
            if value > best_value:
                best_value = value
                best_action = action
        
        # With some probability, accept a random action instead
        if random.random() < math.exp(-1.0 / self.temperature):
            candidate = random.choice(actions)
            # Only accept if different from best
            if candidate.id != best_action.id:
                return candidate
        
        return best_action
    
    def _calculate_reward(self, action: ItemAction, result: Dict[str, Any]) -> float:
        """
        Calculate reward for an action based on its results.
        
        Args:
            action: Executed action
            result: Execution result
            
        Returns:
            Reward value
        """
        # Start with neutral reward
        reward = 0.0
        
        # Basic success/failure reward
        if result.get("success", False):
            reward += 0.1
        else:
            reward -= 0.1
        
        # Reward for discovering new states
        if result.get("new_state", False):
            reward += 0.4
        
        # Reward for changing activity
        if result.get("activity_changed", False):
            reward += 0.3
        
        # Reward for reaching security-sensitive code
        if getattr(action, 'reaches_mop', False):
            reward += 0.2
        
        # Extra reward for directly reaching security code
        if getattr(action, 'directly_reaches_mop', False):
            reward += 0.3
        
        return reward


@StrategyRegistry.register
class PatternMatchingStrategy(Strategy):
    """
    A strategy that identifies and repeats successful action patterns.
    
    This strategy analyzes execution history to identify sequences of actions
    that consistently lead to valuable outcomes, then repeats those patterns
    when similar states are encountered.
    
    ### Architectural Decisions:
    - Maintains a library of successful action patterns
    - Recognizes state similarities to apply patterns in appropriate contexts
    - Combines pattern following with exploratory actions
    - Adapts pattern selection based on execution feedback
    
    ### Role in the System:
    - Leverages previously successful interaction patterns
    - Speeds up testing by reusing known effective sequences
    - Identifies and automates complex multi-step interactions
    - Learns from execution without requiring pre-training
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the pattern matching strategy.
        
        Args:
            static_data: Optional static analysis data
        """
        super().__init__(static_data, "PatternMatchingStrategy")
        
        # Maximum pattern length to track
        self.max_pattern_length = 5
        
        # Library of patterns (action sequences)
        self.patterns: Dict[str, Dict[str, Any]] = {}
        
        # Current state fingerprint
        self.current_state_id = "unknown"
        
        # Current pattern being executed (if any)
        self.current_pattern: Optional[List[int]] = None
        self.pattern_index = 0
        
        # Pattern success tracking
        self.pattern_success: Dict[str, float] = {}
        
        # Recent action history for pattern detection
        self.recent_actions: Deque[int] = collections.deque(maxlen=self.max_pattern_length * 2)
        self.recent_states: Deque[str] = collections.deque(maxlen=self.max_pattern_length * 2)
        self.recent_results: Deque[Dict[str, Any]] = collections.deque(maxlen=self.max_pattern_length * 2)
        
        # State similarity cache
        self.state_similarity: Dict[str, Dict[str, float]] = {}
        
        # Track action performance in each state
        self.state_action_success: Dict[str, Dict[int, float]] = {}
        
        # Security-related action tracking
        self.security_actions: Set[int] = set()
        
        # Action mapping for current screen
        self.action_map: Dict[int, ItemAction] = {}
        
        # Exploration probability
        self.exploration_prob = 0.3
        
        # Initialize metrics
        self.metrics = {
            "patterns_identified": 0,
            "pattern_executions": 0,
            "successful_pattern_executions": 0,
            "pattern_success_rate": 0.0
        }
        
        self.logger.info("Initialized PatternMatchingStrategy")
    
    def generate_action(self, screen: ScreenDescription, state_data: Dict[str, Any], 
                        history: Optional[List[Dict[str, Any]]] = None) -> Optional[ItemAction]:
        """
        Generate the next action using pattern matching.
        
        Args:
            screen: Current screen description
            state_data: Current state data
            history: Optional execution history
            
        Returns:
            Selected action or None if no actions available
        """
        # Update action map for the current screen
        self._update_action_map(screen)
        
        # Get current state fingerprint
        state_id = state_data.get("fingerprint", "unknown")
        self.current_state_id = state_id
        
        # Collect all available actions
        available_actions = list(self.action_map.values())
        if not available_actions:
            return None
        
        # If we're in the middle of executing a pattern, continue with next action
        if self.current_pattern and self.pattern_index < len(self.current_pattern):
            return self._continue_pattern(available_actions)
        
        # Decide whether to explore or follow a pattern
        if random.random() < self.exploration_prob:
            # Exploration: select action based on state-specific success rates
            return self._exploratory_action_selection(available_actions, state_id)
        else:
            # Try to find and follow a pattern for this state
            pattern_id = self._select_pattern_for_state(state_id)
            if pattern_id and pattern_id in self.patterns:
                # Start executing the selected pattern
                self.current_pattern = self.patterns[pattern_id]["actions"]
                self.pattern_index = 0
                self.metrics["pattern_executions"] += 1
                
                # Return the first action in the pattern
                return self._continue_pattern(available_actions)
            else:
                # No suitable pattern found, fall back to exploration
                return self._exploratory_action_selection(available_actions, state_id)
    
    def update_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Update pattern knowledge based on execution feedback.
        
        Args:
            action: Executed action
            result: Execution result
        """
        # Extract key information
        action_id = action.id
        success = result.get("success", False)
        new_state = result.get("new_state", False)
        state_id = result.get("previous_state", "unknown")  # State before action execution
        current_state = result.get("state_fingerprint", "unknown")  # State after action execution
        
        # Update state-action success rates
        self._update_state_action_success(state_id, action_id, success, new_state)
        
        # Update security action tracking
        if getattr(action, 'reaches_mop', False) or getattr(action, 'directly_reaches_mop', False):
            self.security_actions.add(action_id)
        
        # Update recent history
        self.recent_actions.append(action_id)
        self.recent_states.append(state_id)
        self.recent_results.append(result)
        
        # If we're executing a pattern, update its success tracking
        if self.current_pattern:
            if self.pattern_index >= len(self.current_pattern):
                # Pattern execution complete
                pattern_id = self._get_pattern_id(self.current_pattern)
                pattern_success = self.pattern_success.get(pattern_id, 0.5)
                
                # Calculate pattern reward based on final action
                pattern_reward = 0.0
                if success:
                    pattern_reward += 0.1
                if new_state:
                    pattern_reward += 0.4
                
                # Update pattern success rate
                execution_count = self.patterns[pattern_id]["execution_count"]
                new_success_rate = ((pattern_success * execution_count) + pattern_reward) / (execution_count + 1)
                self.pattern_success[pattern_id] = new_success_rate
                
                # Update pattern execution metrics
                self.patterns[pattern_id]["execution_count"] += 1
                if pattern_reward > 0:
                    self.patterns[pattern_id]["success_count"] += 1
                    self.metrics["successful_pattern_executions"] += 1
                
                # Reset current pattern
                self.current_pattern = None
                self.pattern_index = 0
        
        # Detect new patterns if we have enough history
        if len(self.recent_actions) >= 2:
            self._detect_patterns()
        
        # Update metrics
        if self.metrics["pattern_executions"] > 0:
            self.metrics["pattern_success_rate"] = (self.metrics["successful_pattern_executions"] / 
                                                 self.metrics["pattern_executions"])
    
    def _update_action_map(self, screen: ScreenDescription) -> None:
        """
        Update the mapping from action IDs to actions for the current screen.
        
        Args:
            screen: Current screen description
        """
        self.action_map = {}
        for item in screen.items:
            for action in item.actions:
                self.action_map[action.id] = action
    
    def _continue_pattern(self, available_actions: List[ItemAction]) -> Optional[ItemAction]:
        """
        Continue executing the current pattern.
        
        Args:
            available_actions: Currently available actions
            
        Returns:
            Next action in pattern or fallback action
        """
        if not self.current_pattern or self.pattern_index >= len(self.current_pattern):
            return None
        
        # Get the next action ID from the pattern
        action_id = self.current_pattern[self.pattern_index]
        self.pattern_index += 1
        
        # Check if this action is available
        if action_id in self.action_map:
            return self.action_map[action_id]
        
        # Action not available, abort pattern and fall back to exploration
        self.current_pattern = None
        self.pattern_index = 0
        return random.choice(available_actions)
    
    def _exploratory_action_selection(self, available_actions: List[ItemAction], 
                                     state_id: str) -> ItemAction:
        """
        Select an action for exploration rather than pattern following.
        
        Args:
            available_actions: Currently available actions
            state_id: Current state ID
            
        Returns:
            Selected action
        """
        # Initialize success rates for this state if needed
        if state_id not in self.state_action_success:
            self.state_action_success[state_id] = {}
        
        # Check for security-relevant actions
        security_actions = [a for a in available_actions if a.id in self.security_actions]
        if security_actions and random.random() < 0.4:
            return random.choice(security_actions)
        
        # Calculate values for available actions
        action_values = {}
        for action in available_actions:
            # Start with neutral value
            value = 0.5
            
            # Adjust based on state-specific success
            if action.id in self.state_action_success[state_id]:
                value = self.state_action_success[state_id][action.id]
            
            # Bonus for security actions
            if action.id in self.security_actions:
                value += 0.3
                
            # Bonus for reaching MOP
            if getattr(action, 'reaches_mop', False):
                value += 0.2
            
            if getattr(action, 'directly_reaches_mop', False):
                value += 0.3
                
            action_values[action.id] = value
        
        # Select action with highest value most of the time
        if random.random() < 0.7:
            best_action = max(available_actions, key=lambda a: action_values.get(a.id, 0))
            return best_action
        else:
            # Sometimes explore randomly
            return random.choice(available_actions)
    
    def _select_pattern_for_state(self, state_id: str) -> Optional[str]:
        """
        Select an appropriate pattern for the current state.
        
        Args:
            state_id: Current state ID
            
        Returns:
            Selected pattern ID or None if no suitable pattern
        """
        # Find patterns that start in similar states
        candidate_patterns = []
        
        for pattern_id, pattern_info in self.patterns.items():
            start_state = pattern_info["start_state"]
            
            # Check if states are similar
            similarity = self._calculate_state_similarity(state_id, start_state)
            
            # Get pattern success rate
            success_rate = self.pattern_success.get(pattern_id, 0.5)
            
            # Add to candidates if similar enough and somewhat successful
            if similarity > 0.7 and success_rate > 0.4:
                candidate_patterns.append((pattern_id, similarity * success_rate))
        
        # If we have candidates, select based on weighted probability
        if candidate_patterns:
            # Sort by combined score (similarity * success)
            candidate_patterns.sort(key=lambda x: x[1], reverse=True)
            
            # Select top pattern most of the time
            if random.random() < 0.8:
                return candidate_patterns[0][0]
            else:
                # Otherwise select randomly from candidates
                return random.choice(candidate_patterns)[0]
        
        return None
    
    def _calculate_state_similarity(self, state1: str, state2: str) -> float:
        """
        Calculate similarity between two states.
        
        Args:
            state1: First state ID
            state2: Second state ID
            
        Returns:
            Similarity score [0-1]
        """
        # Check cache first
        if state1 in self.state_similarity and state2 in self.state_similarity[state1]:
            return self.state_similarity[state1][state2]
        
        # For now, simple approach: same state = 1.0, different state = 0.5
        # This would be enhanced with state feature comparison in a real implementation
        similarity = 1.0 if state1 == state2 else 0.5
        
        # Cache the result
        if state1 not in self.state_similarity:
            self.state_similarity[state1] = {}
        self.state_similarity[state1][state2] = similarity
        
        return similarity
    
    def _update_state_action_success(self, state_id: str, action_id: int, 
                                   success: bool, new_state: bool) -> None:
        """
        Update success rates for actions in specific states.
        
        Args:
            state_id: State ID
            action_id: Action ID
            success: Whether action execution was successful
            new_state: Whether action led to a new state
        """
        # Initialize state-action tracking if needed
        if state_id not in self.state_action_success:
            self.state_action_success[state_id] = {}
        
        # Get current success rate
        current_rate = self.state_action_success[state_id].get(action_id, 0.5)
        
        # Calculate reward
        reward = 0.0
        if success:
            reward += 0.1
        if new_state:
            reward += 0.4
        
        # Action reaches security-sensitive code
        if action_id in self.security_actions:
            reward += 0.2
        
        # Update rate with diminishing learning rate
        attempts = self.metrics.get(f"action_{action_id}_attempts", 0) + 1
        self.metrics[f"action_{action_id}_attempts"] = attempts
        
        learning_rate = 1.0 / math.sqrt(max(1, attempts))
        new_rate = current_rate + learning_rate * (reward - current_rate)
        
        # Ensure rate is in [0,1] range
        new_rate = max(0.0, min(1.0, new_rate))
        
        # Store updated rate
        self.state_action_success[state_id][action_id] = new_rate
    
    def _detect_patterns(self) -> None:
        """
        Analyze action history to detect successful patterns.
        """
        # Need at least 2 actions to form a pattern
        if len(self.recent_actions) < 2:
            return
        
        # Look for patterns of different lengths
        max_length = min(self.max_pattern_length, len(self.recent_actions))
        
        for length in range(2, max_length + 1):
            # Extract recent actions as a pattern
            pattern = list(self.recent_actions)[-length:]
            pattern_id = self._get_pattern_id(pattern)
            
            # Check if this is a new pattern
            if pattern_id not in self.patterns:
                # Check if pattern ends with a valuable result
                last_result = self.recent_results[-1]
                
                if (last_result.get("success", False) and 
                        (last_result.get("new_state", False) or 
                         last_result.get("activity_changed", False))):
                    # This pattern led to a valuable outcome, store it
                    self.patterns[pattern_id] = {
                        "actions": pattern,
                        "start_state": self.recent_states[-length],
                        "execution_count": 1,
                        "success_count": 1,
                        "length": length,
                        "identified_at": time.time()
                    }
                    
                    self.pattern_success[pattern_id] = 0.7  # Initial optimistic value
                    self.metrics["patterns_identified"] += 1
                    
                    self.logger.info(f"Identified new valuable pattern of length {length}")
    
    def _get_pattern_id(self, pattern: List[int]) -> str:
        """
        Generate a unique ID for an action pattern.
        
        Args:
            pattern: List of action IDs
            
        Returns:
            Pattern ID string
        """
        return "-".join(str(action_id) for action_id in pattern)


@StrategyRegistry.register
class HeuristicComboStrategy(Strategy):
    """
    A strategy that combines multiple heuristics with adaptive weights.
    
    This strategy uses a collection of simple heuristics and dynamically
    adjusts their weights based on which ones are most effective in the
    current application context.
    
    ### Architectural Decisions:
    - Implements multiple complementary heuristics for action selection
    - Dynamically adjusts heuristic weights based on execution feedback
    - Combines heuristic outputs for balanced decision making
    - Adapts to application behavior through weight adjustments
    
    ### Role in the System:
    - Combines strengths of multiple selection approaches
    - Adapts to find most effective heuristics for each application
    - Balances multiple concerns (security, coverage, exploration)
    - Provides robust fallback mechanisms
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the heuristic combo strategy.
        
        Args:
            static_data: Optional static analysis data
        """
        super().__init__(static_data, "HeuristicComboStrategy")
        
        # Heuristic weights - adjusted during execution
        self.heuristic_weights = {
            "security_first": 1.0,      # Prioritize security-sensitive actions
            "novelty_seeking": 1.0,     # Favor actions not executed before
            "state_discovery": 1.0,     # Favor actions that found new states
            "coverage_driven": 1.0,     # Favor actions reaching uncovered code
            "systematic": 0.8,          # Systematic exploration of UI
            "interactive_first": 0.8,   # Prioritize interactive elements
            "text_field_focus": 0.7     # Focus on text input fields
        }
        
        # Action execution history
        self.action_executed: Dict[int, int] = {}
        
        # Action success tracking
        self.action_success: Dict[int, float] = {}
        
        # New state discovery tracking
        self.action_new_states: Dict[int, int] = {}
        
        # Track action performance in each state
        self.state_action_success: Dict[str, Dict[int, float]] = {}
        
        # Track states where each action was executed
        self.action_states: Dict[int, Set[str]] = {}
        
        # Systematic exploration tracking
        self.state_exploration_progress: Dict[str, float] = {}
        
        # Track element types for heuristics
        self.action_element_types: Dict[int, str] = {}
        
        # Security action tracking
        self.security_actions: Set[int] = set()
        
        # Metrics tracking
        self.metrics = {
            "actions_executed": 0,
            "successful_actions": 0,
            "new_states_discovered": 0,
            "security_actions_executed": 0,
            "heuristic_contributions": {}
        }
        
        # Track which heuristic recommended each action
        self.last_action_heuristics: Dict[int, str] = {}
        
        # Initialize logger
        self.logger.info("Initialized HeuristicComboStrategy")
    
    def generate_action(self, screen: ScreenDescription, state_data: Dict[str, Any], 
                        history: Optional[List[Dict[str, Any]]] = None) -> Optional[ItemAction]:
        """
        Generate the next action using combined heuristics.
        
        Args:
            screen: Current screen description
            state_data: Current state data
            history: Optional execution history
            
        Returns:
            Selected action or None if no actions available
        """
        # Collect available actions
        available_actions = self._collect_actions(screen)
        if not available_actions:
            return None
        
        # Current state fingerprint
        state_id = state_data.get("fingerprint", "unknown")
        
        # Calculate scores from each heuristic
        heuristic_scores = self._apply_heuristics(available_actions, state_id, state_data)
        
        # Combine heuristic scores using weights
        action_scores = self._combine_heuristic_scores(heuristic_scores)
        
        # Select action with highest combined score
        selected_action = self._select_best_action(available_actions, action_scores)
        
        # Record which heuristics contributed most to this selection
        self._record_heuristic_contribution(selected_action.id, heuristic_scores)
        
        return selected_action
    
    def update_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Update heuristic weights based on execution feedback.
        
        Args:
            action: Executed action
            result: Execution result
        """
        # Extract key information
        action_id = action.id
        success = result.get("success", False)
        new_state = result.get("new_state", False)
        state_id = result.get("previous_state", "unknown")
        
        # Update execution tracking
        self.action_executed[action_id] = self.action_executed.get(action_id, 0) + 1
        self.metrics["actions_executed"] += 1
        
        if success:
            self.metrics["successful_actions"] += 1
        
        if new_state:
            self.metrics["new_states_discovered"] += 1
            self.action_new_states[action_id] = self.action_new_states.get(action_id, 0) + 1
        
        # Update security action tracking
        if getattr(action, 'reaches_mop', False) or getattr(action, 'directly_reaches_mop', False):
            self.security_actions.add(action_id)
            self.metrics["security_actions_executed"] += 1
        
        # Update state-action tracking
        if action_id not in self.action_states:
            self.action_states[action_id] = set()
        self.action_states[action_id].add(state_id)
        
        # Update element type tracking
        if hasattr(action, 'target_view') and action.target_view:
            class_name = action.target_view.get("class", "")
            if "EditText" in class_name:
                self.action_element_types[action_id] = "text_field"
            elif "Button" in class_name:
                self.action_element_types[action_id] = "button"
            elif "Checkbox" in class_name:
                self.action_element_types[action_id] = "checkbox"
            else:
                self.action_element_types[action_id] = "other"
        
        # Update state-action success rates
        self._update_state_action_success(state_id, action_id, success, new_state)
        
        # Update action success rate
        old_success_rate = self.action_success.get(action_id, 0.5)
        attempts = self.action_executed[action_id]
        
        # Calculate new success rate
        if attempts == 1:
            new_success_rate = 1.0 if success else 0.0
        else:
            new_success_rate = ((old_success_rate * (attempts - 1)) + (1.0 if success else 0.0)) / attempts
        
        self.action_success[action_id] = new_success_rate
        
        # Update heuristic weights based on which heuristics recommended this action
        self._update_heuristic_weights(action_id, success, new_state)
    
    def _collect_actions(self, screen: ScreenDescription) -> List[ItemAction]:
        """
        Collect all available actions from a screen.
        
        Args:
            screen: Current screen description
            
        Returns:
            List of all available actions
        """
        all_actions = []
        for item in screen.items:
            all_actions.extend(item.actions)
        return all_actions
    
    def _apply_heuristics(self, actions: List[ItemAction], state_id: str, 
                         state_data: Dict[str, Any]) -> Dict[str, Dict[int, float]]:
        """
        Apply all heuristics to calculate scores for each action.
        
        Args:
            actions: Available actions
            state_id: Current state ID
            state_data: Current state data
            
        Returns:
            Dictionary mapping heuristic names to action score dictionaries
        """
        heuristic_scores = {}
        
        # Security-first heuristic
        security_scores = {}
        for action in actions:
            score = 0.5
            
            # Check if action reaches security code
            if getattr(action, 'reaches_mop', False):
                score += 0.3
            
            # Check if action directly reaches security code
            if getattr(action, 'directly_reaches_mop', False):
                score += 0.5
                
            # Mark as security action for tracking
            if score > 0.5:
                self.security_actions.add(action.id)
                
            security_scores[action.id] = score
        
        heuristic_scores["security_first"] = security_scores
        
        # Novelty-seeking heuristic
        novelty_scores = {}
        for action in actions:
            if action.id not in self.action_executed:
                # Never executed before
                novelty_scores[action.id] = 1.0
            else:
                # Diminishing score based on execution count
                executions = self.action_executed[action.id]
                novelty_scores[action.id] = 1.0 / math.sqrt(1 + executions)
        
        heuristic_scores["novelty_seeking"] = novelty_scores
        
        # State discovery heuristic
        discovery_scores = {}
        for action in actions:
            if action.id not in self.action_new_states:
                # No history of finding new states
                discovery_scores[action.id] = 0.5
            else:
                # Score based on how many new states this action has found
                new_states = self.action_new_states[action.id]
                executions = self.action_executed.get(action.id, 1)
                ratio = new_states / executions
                discovery_scores[action.id] = 0.5 + (ratio * 0.5)
        
        heuristic_scores["state_discovery"] = discovery_scores
        
        # Systematic exploration heuristic
        systematic_scores = {}
        
        # Initialize exploration progress for this state if needed
        if state_id not in self.state_exploration_progress:
            self.state_exploration_progress[state_id] = 0.0
            
        # Track which actions have been executed in this state
        executed_in_state = set()
        for action_id, states in self.action_states.items():
            if state_id in states:
                executed_in_state.add(action_id)
                
        # Calculate exploration progress
        progress = len(executed_in_state) / max(1, len(actions))
        self.state_exploration_progress[state_id] = progress
        
        # Favor actions not yet executed in this state
        for action in actions:
            if action.id not in executed_in_state:
                systematic_scores[action.id] = 0.8
            else:
                systematic_scores[action.id] = 0.2
        
        heuristic_scores["systematic"] = systematic_scores
        
        # Interactive element heuristic
        interactive_scores = {}
        for action in actions:
            score = 0.5
            
            # Check element type
            element_type = self.action_element_types.get(action.id, "unknown")
            
            if element_type == "button":
                score = 0.8
            elif element_type == "text_field":
                score = 0.7
            elif element_type == "checkbox":
                score = 0.6
                
            # Check for CLICK actions
            if "CLICK" in action.text:
                score += 0.1
                
            interactive_scores[action.id] = score
        
        heuristic_scores["interactive_first"] = interactive_scores
        
        # Text field focus heuristic
        text_field_scores = {}
        for action in actions:
            if (hasattr(action, 'target_view') and action.target_view and
                    "EditText" in action.target_view.get("class", "")):
                text_field_scores[action.id] = 1.0
            else:
                text_field_scores[action.id] = 0.3
        
        heuristic_scores["text_field_focus"] = text_field_scores
        
        # Coverage-driven heuristic (simplistic implementation)
        coverage_scores = {}
        for action in actions:
            # Base score 
            score = 0.5
            
            # If we have executed this action before, use success rate
            if action.id in self.action_success:
                score = self.action_success[action.id]
            
            # Bonus for actions that lead to new states (coverage proxy)
            if action.id in self.action_new_states:
                new_states = self.action_new_states[action.id]
                executions = self.action_executed.get(action.id, 1)
                ratio = new_states / executions
                score += ratio * 0.3
                
            coverage_scores[action.id] = score
        
        heuristic_scores["coverage_driven"] = coverage_scores
        
        return heuristic_scores
    
    def _combine_heuristic_scores(self, heuristic_scores: Dict[str, Dict[int, float]]) -> Dict[int, float]:
        """
        Combine scores from multiple heuristics into a single score per action.
        
        Args:
            heuristic_scores: Scores from each heuristic
            
        Returns:
            Combined scores for each action
        """
        combined_scores = {}
        
        # Get all action IDs
        action_ids = set()
        for heuristic_name, scores in heuristic_scores.items():
            action_ids.update(scores.keys())
        
        # Calculate weighted sum for each action
        for action_id in action_ids:
            score_sum = 0.0
            weight_sum = 0.0
            
            for heuristic_name, scores in heuristic_scores.items():
                if action_id in scores:
                    weight = self.heuristic_weights.get(heuristic_name, 1.0)
                    score_sum += scores[action_id] * weight
                    weight_sum += weight
            
            # Normalize by sum of weights
            if weight_sum > 0:
                combined_scores[action_id] = score_sum / weight_sum
            else:
                combined_scores[action_id] = 0.5
        
        return combined_scores
    
    def _select_best_action(self, actions: List[ItemAction], scores: Dict[int, float]) -> ItemAction:
        """
        Select the action with the highest score.
        
        Args:
            actions: Available actions
            scores: Action scores
            
        Returns:
            Selected action
        """
        # Find action with highest score
        best_action = None
        best_score = -float('inf')
        
        for action in actions:
            score = scores.get(action.id, 0.0)
            
            # Add a small random factor to break ties
            score += random.random() * 0.1
            
            if score > best_score:
                best_score = score
                best_action = action
        
        # If no action found, return a random one
        if best_action is None and actions:
            return random.choice(actions)
            
        return best_action
    
    def _record_heuristic_contribution(self, action_id: int, 
                                     heuristic_scores: Dict[str, Dict[int, float]]) -> None:
        """
        Record which heuristics contributed most to selecting an action.
        
        Args:
            action_id: Selected action ID
            heuristic_scores: Scores from each heuristic
        """
        # Find heuristic with highest score for this action
        best_heuristic = None
        best_score = -float('inf')
        
        for heuristic_name, scores in heuristic_scores.items():
            if action_id in scores and scores[action_id] > best_score:
                best_score = scores[action_id]
                best_heuristic = heuristic_name
        
        # Record which heuristic recommended this action
        if best_heuristic:
            self.last_action_heuristics[action_id] = best_heuristic
            
            # Update heuristic contribution metrics
            if best_heuristic not in self.metrics["heuristic_contributions"]:
                self.metrics["heuristic_contributions"][best_heuristic] = 0
            self.metrics["heuristic_contributions"][best_heuristic] += 1
    
    def _update_heuristic_weights(self, action_id: int, success: bool, new_state: bool) -> None:
        """
        Update heuristic weights based on action outcomes.
        
        Args:
            action_id: Executed action ID
            success: Whether execution was successful
            new_state: Whether a new state was discovered
        """
        # Get the heuristic that recommended this action
        recommending_heuristic = self.last_action_heuristics.get(action_id)
        if not recommending_heuristic:
            return
            
        # Calculate reward for the outcome
        reward = 0.0
        
        # Basic success/failure reward
        if success:
            reward += 0.1
        else:
            reward -= 0.1
            
        # Reward for discovering new states
        if new_state:
            reward += 0.4
            
        # Reward for security actions
        if action_id in self.security_actions:
            reward += 0.2
            
        # Update the weight for the recommending heuristic
        current_weight = self.heuristic_weights.get(recommending_heuristic, 1.0)
        
        # Learning rate decreases as more actions are executed
        learning_rate = 0.1 / math.sqrt(max(1, self.metrics["actions_executed"]))
        
        # Update weight
        new_weight = current_weight + learning_rate * reward
        
        # Ensure weight stays positive
        new_weight = max(0.1, new_weight)
        
        # Store updated weight
        self.heuristic_weights[recommending_heuristic] = new_weight
        
        # Log significant weight changes
        if abs(new_weight - current_weight) > 0.1:
            self.logger.info(f"Updated weight for {recommending_heuristic}: "
                          f"{current_weight:.2f} -> {new_weight:.2f}")
    
    def _update_state_action_success(self, state_id: str, action_id: int, 
                                   success: bool, new_state: bool) -> None:
        """
        Update success rates for actions in specific states.
        
        Args:
            state_id: State ID
            action_id: Action ID
            success: Whether action execution was successful
            new_state: Whether action led to a new state
        """
        # Initialize state-action tracking if needed
        if state_id not in self.state_action_success:
            self.state_action_success[state_id] = {}
        
        # Get current success rate
        current_rate = self.state_action_success[state_id].get(action_id, 0.5)
        
        # Calculate reward
        reward = 0.0
        if success:
            reward += 0.1
        if new_state:
            reward += 0.4
        
        # Update rate with diminishing learning rate
        executions = self.metrics.get(f"action_{action_id}_executions", 0) + 1
        self.metrics[f"action_{action_id}_executions"] = executions
        
        learning_rate = 1.0 / math.sqrt(max(1, executions))
        new_rate = current_rate + learning_rate * (reward - current_rate)
        
        # Ensure rate is in [0,1] range
        new_rate = max(0.0, min(1.0, new_rate))
        
        # Store updated rate
        self.state_action_success[state_id][action_id] = new_rate