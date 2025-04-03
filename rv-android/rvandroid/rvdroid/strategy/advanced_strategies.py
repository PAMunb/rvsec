# rvandroid/rvdroid/strategy/advanced_strategies.py
"""
Advanced strategies for RVDroid testing.

This module implements more sophisticated testing strategies that use
advanced algorithms and approaches for better exploration efficiency.
"""

import random
import time
from typing import List, Dict, Any, Optional, Set, Tuple

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription, ItemAction
from rvandroid.rvdroid.strategy.strategy import Strategy, StrategyRegistry


@StrategyRegistry.register
class ModelBasedStrategy(Strategy):
    """
    A model-based testing strategy that builds a model of the application and uses
    it to guide testing decisions.

    ### Architectural Decisions:
    - Builds an internal model of the application during exploration
    - Uses the model to guide exploration toward unexplored states
    - Balances exploration and exploitation based on the model
    - Prioritizes actions that may lead to new states

    ### Role in the System:
    - Uses past execution history to make informed decisions
    - Builds behavioral model of the application
    - Focuses exploration on promising areas
    - Avoids repeatedly exploring well-known paths
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the model-based strategy.

        Args:
            static_data: Optional static analysis data
        """
        super().__init__(static_data, "ModelBasedStrategy")
        
        # Behavioral model mapping states to actions and their outcomes
        self.model: Dict[str, Dict[int, Dict[str, Any]]] = {}
        
        # Action success rate tracking
        self.action_success_rates: Dict[int, float] = {}
        
        # Track unexplored actions for each state
        self.unexplored_actions: Dict[str, Set[int]] = {}
        
        # Exploration vs exploitation balance (higher means more exploration)
        self.exploration_weight = 0.7
        
        # Number of times a state has been visited
        self.state_visits: Dict[str, int] = {}
        
        # Track transitions between states
        self.transitions: Dict[str, Dict[str, List[int]]] = {}
        
        # Initialize metrics
        self.metrics = {
            "model_size": 0,
            "successful_predictions": 0,
            "total_predictions": 0
        }

    def generate_action(self, screen: ScreenDescription, state_data: Dict[str, Any], 
                        history: Optional[List[Dict[str, Any]]] = None) -> Optional[ItemAction]:
        """
        Generate the next action using model-based approach.

        Args:
            screen: Current screen description
            state_data: Current state data
            history: Optional execution history

        Returns:
            Next action to execute
        """
        state_fingerprint = state_data.get("fingerprint", "unknown")
        
        # Update state visits
        self.state_visits[state_fingerprint] = self.state_visits.get(state_fingerprint, 0) + 1
        
        # Collect all available actions
        all_actions = self._collect_actions(screen)
        if not all_actions:
            return None
            
        # Update unexplored actions for this state
        self._update_unexplored_actions(state_fingerprint, all_actions)
        
        # Check if we should explore or exploit
        if random.random() < self.exploration_weight:
            # Exploration: focus on unexplored actions
            return self._select_exploration_action(state_fingerprint, all_actions)
        else:
            # Exploitation: focus on high-value actions based on model
            return self._select_exploitation_action(state_fingerprint, all_actions)

    def update_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Update the model based on action feedback.

        Args:
            action: Executed action
            result: Action execution result
        """
        # Extract key information
        action_id = action.id
        success = result.get("success", False)
        previous_state = result.get("previous_state", "unknown")
        new_state = result.get("new_state", False)
        current_state = result.get("state_fingerprint", "unknown")
        
        # Update action success rate
        old_rate = self.action_success_rates.get(action_id, 0.5)
        old_count = self.metrics.get(f"action_{action_id}_count", 0)
        new_count = old_count + 1
        
        # Weighted update of success rate
        if new_count == 1:
            new_rate = 1.0 if success else 0.0
        else:
            new_rate = (old_rate * old_count + (1.0 if success else 0.0)) / new_count
            
        self.action_success_rates[action_id] = new_rate
        self.metrics[f"action_{action_id}_count"] = new_count
        
        # Update model for this state and action
        if previous_state not in self.model:
            self.model[previous_state] = {}
            
        if action_id not in self.model[previous_state]:
            self.model[previous_state][action_id] = {
                "success_count": 0,
                "failure_count": 0,
                "new_state_count": 0,
                "destinations": {}
            }
            
        # Update action stats in the model
        action_stats = self.model[previous_state][action_id]
        if success:
            action_stats["success_count"] += 1
        else:
            action_stats["failure_count"] += 1
            
        if new_state:
            action_stats["new_state_count"] += 1
            
        # Update destination tracking
        if success:
            if current_state not in action_stats["destinations"]:
                action_stats["destinations"][current_state] = 0
            action_stats["destinations"][current_state] += 1
            
        # Update model size metric
        self.metrics["model_size"] = sum(len(actions) for actions in self.model.values())
        
        # Update transition tracking
        if success:
            if previous_state not in self.transitions:
                self.transitions[previous_state] = {}
                
            if current_state not in self.transitions[previous_state]:
                self.transitions[previous_state][current_state] = []
                
            self.transitions[previous_state][current_state].append(action_id)
            
        # Update unexplored actions
        if success and previous_state in self.unexplored_actions:
            if action_id in self.unexplored_actions[previous_state]:
                self.unexplored_actions[previous_state].remove(action_id)
        
        # Check if we predicted outcome correctly based on our model
        self._update_prediction_metrics(previous_state, action_id, success, new_state, current_state)
        
        # Adjust exploration weight based on exploration progress
        # As we discover more of the app, we reduce exploration in favor of exploitation
        explored_states = len(self.model)
        if explored_states > 10:
            self.exploration_weight = max(0.3, 0.7 - (explored_states / 100))

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

    def _update_unexplored_actions(self, state_fingerprint: str, all_actions: List[ItemAction]) -> None:
        """
        Update the set of unexplored actions for a state.

        Args:
            state_fingerprint: State fingerprint
            all_actions: All available actions
        """
        # Initialize if needed
        if state_fingerprint not in self.unexplored_actions:
            self.unexplored_actions[state_fingerprint] = set(a.id for a in all_actions)
        else:
            # Update with any new actions
            current_action_ids = set(a.id for a in all_actions)
            missing_actions = current_action_ids - set(self.unexplored_actions[state_fingerprint])
            self.unexplored_actions[state_fingerprint].update(missing_actions)

    def _select_exploration_action(self, state_fingerprint: str, all_actions: List[ItemAction]) -> ItemAction:
        """
        Select an action focused on exploration.

        Args:
            state_fingerprint: State fingerprint
            all_actions: All available actions

        Returns:
            Selected action
        """
        # Prioritize completely unexplored actions
        if (state_fingerprint in self.unexplored_actions and 
                self.unexplored_actions[state_fingerprint]):
            # Find the action in the available actions
            unexplored_ids = self.unexplored_actions[state_fingerprint]
            unexplored_actions = [a for a in all_actions if a.id in unexplored_ids]
            if unexplored_actions:
                return random.choice(unexplored_actions)
        
        # Security-aware prioritization - prefer actions that might reach security code
        security_actions = [a for a in all_actions if getattr(a, 'reaches_mop', False)]
        if security_actions:
            return random.choice(security_actions)
        
        # Otherwise, just pick a random action
        return random.choice(all_actions)

    def _select_exploitation_action(self, state_fingerprint: str, all_actions: List[ItemAction]) -> ItemAction:
        """
        Select an action focused on exploitation of known good paths.

        Args:
            state_fingerprint: State fingerprint
            all_actions: All available actions

        Returns:
            Selected action
        """
        action_scores = {}
        
        # Score each action based on our model
        for action in all_actions:
            # Default score - neutral
            score = 0.5
            
            # Adjust based on action success rate
            if action.id in self.action_success_rates:
                score = self.action_success_rates[action.id]
                
            # Boost actions that reach security code
            if getattr(action, 'reaches_mop', False):
                score += 0.2
                
            # Additional boost for actions that directly reach security code
            if getattr(action, 'directly_reaches_mop', False):
                score += 0.3
                
            # If we have model data for this state and action, use it
            if (state_fingerprint in self.model and
                    action.id in self.model[state_fingerprint]):
                action_stats = self.model[state_fingerprint][action.id]
                
                # Boost actions that led to new states before
                if action_stats["new_state_count"] > 0:
                    new_state_ratio = action_stats["new_state_count"] / max(1, 
                                          action_stats["success_count"] + action_stats["failure_count"])
                    score += new_state_ratio * 0.3
                    
                # Boost actions that have diverse destinations
                if len(action_stats["destinations"]) > 1:
                    score += 0.2
                    
            action_scores[action.id] = score
            
        # Select the action with the highest score
        best_action_id = max(action_scores.items(), key=lambda x: x[1])[0]
        best_action = next((a for a in all_actions if a.id == best_action_id), None)
        
        # Fallback to random if something went wrong
        if not best_action:
            return random.choice(all_actions)
            
        return best_action

    def _update_prediction_metrics(self, state: str, action_id: int, 
                                  success: bool, new_state: bool, current_state: str) -> None:
        """
        Update metrics related to prediction accuracy.

        Args:
            state: Previous state
            action_id: Action ID
            success: Whether the action was successful
            new_state: Whether the action led to a new state
            current_state: Current state after action
        """
        # Only update if we have predictions in the model
        if state not in self.model or action_id not in self.model[state]:
            return
            
        self.metrics["total_predictions"] += 1
        
        # Check if success prediction was correct
        action_stats = self.model[state][action_id]
        success_rate_predicted = (action_stats["success_count"] / 
                                 max(1, action_stats["success_count"] + action_stats["failure_count"]))
        
        success_predicted = success_rate_predicted > 0.5
        if success_predicted == success:
            self.metrics["successful_predictions"] += 1
            
        # Calculate prediction accuracy
        if self.metrics["total_predictions"] > 0:
            self.metrics["prediction_accuracy"] = (self.metrics["successful_predictions"] / 
                                                  self.metrics["total_predictions"])


@StrategyRegistry.register
class GreedyStrategy(Strategy):
    """
    A greedy strategy that prioritizes actions with the highest potential value.
    
    ### Architectural Decisions:
    - Focuses on immediate rewards rather than long-term exploration
    - Prioritizes actions that reach security-sensitive code
    - Uses heuristics to identify high-value actions
    - Maintains action success history
    
    ### Role in the System:
    - Efficiently targets security-sensitive areas
    - Maximizes coverage of critical code paths
    - Complements exploration strategies with focused testing
    - Adapts to feedback from previous action executions
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the greedy strategy.

        Args:
            static_data: Optional static analysis data
        """
        super().__init__(static_data, "GreedyStrategy")
        
        # Track action success rates
        self.action_scores: Dict[int, float] = {}
        
        # Track how many times each action was executed
        self.action_attempts: Dict[int, int] = {}
        
        # Track new states discovered by each action
        self.action_new_states: Dict[int, int] = {}
        
        # Initialize metrics
        self.metrics = {
            "greedy_selections": 0,
            "security_actions_executed": 0
        }

    def generate_action(self, screen: ScreenDescription, state_data: Dict[str, Any], 
                        history: Optional[List[Dict[str, Any]]] = None) -> Optional[ItemAction]:
        """
        Generate the next action using greedy approach.

        Args:
            screen: Current screen description
            state_data: Current state data
            history: Optional execution history

        Returns:
            Next action to execute
        """
        # Collect all available actions
        all_actions = self._collect_actions(screen)
        if not all_actions:
            return None
            
        # Calculate value for each action
        action_values = self._calculate_action_values(all_actions)
        
        # Select action with highest value (with some randomness to avoid local maxima)
        if random.random() < 0.9:  # 90% greedy, 10% random exploration
            # Find the action with the highest value
            best_action_id = max(action_values.items(), key=lambda x: x[1])[0]
            best_action = next((a for a in all_actions if a.id == best_action_id), None)
            
            if best_action:
                self.metrics["greedy_selections"] += 1
                
                # Check if it's a security action
                if getattr(best_action, 'reaches_mop', False):
                    self.metrics["security_actions_executed"] += 1
                    
                return best_action
        
        # Random selection as fallback or exploration
        return random.choice(all_actions)

    def update_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Update action scores based on feedback.

        Args:
            action: Executed action
            result: Action execution result
        """
        # Extract key information
        action_id = action.id
        success = result.get("success", False)
        new_state = result.get("new_state", False)
        
        # Track attempts
        self.action_attempts[action_id] = self.action_attempts.get(action_id, 0) + 1
        
        # Update new state count
        if new_state:
            self.action_new_states[action_id] = self.action_new_states.get(action_id, 0) + 1
        
        # Current score and attempt count
        current_score = self.action_scores.get(action_id, 0.5)
        attempts = self.action_attempts[action_id]
        
        # Calculate reward
        reward = 0.0
        
        # Base reward for success
        if success:
            reward += 0.1
        else:
            reward -= 0.1
            
        # Reward for finding new states
        if new_state:
            reward += 0.5
            
        # Reward for activity transitions
        if result.get("activity_changed", False):
            reward += 0.3
            
        # Update score with decreasing learning rate as attempts increase
        learning_rate = 1.0 / max(1, attempts)
        new_score = current_score + learning_rate * (reward - current_score)
        
        # Ensure score is in [0, 1] range
        new_score = max(0.0, min(1.0, new_score))
        
        # Update score
        self.action_scores[action_id] = new_score

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

    def _calculate_action_values(self, actions: List[ItemAction]) -> Dict[int, float]:
        """
        Calculate value for each action.

        Args:
            actions: Available actions

        Returns:
            Dictionary mapping action IDs to their values
        """
        values = {}
        
        for action in actions:
            action_id = action.id
            
            # Start with a base value
            value = 0.5
            
            # Adjust value based on known score
            if action_id in self.action_scores:
                value = self.action_scores[action_id]
                
            # Boost for actions that reach security code
            if getattr(action, 'reaches_mop', False):
                value += 0.2
                
            # Extra boost for actions that directly reach security code
            if getattr(action, 'directly_reaches_mop', False):
                value += 0.3
                
            # Boost for actions that have found new states before
            if action_id in self.action_new_states and self.action_new_states[action_id] > 0:
                value += 0.1 * min(3, self.action_new_states[action_id])
                
            # Exploration bonus for less-tried actions (inverse of attempt count)
            attempts = self.action_attempts.get(action_id, 0)
            if attempts == 0:
                value += 0.2  # Bonus for untried actions
            else:
                value += 0.1 / attempts  # Diminishing bonus for repeated attempts
                
            values[action_id] = value
            
        return values


@StrategyRegistry.register
class GeneticAlgorithmStrategy(Strategy):
    """
    A genetic algorithm-based strategy that evolves test sequences.
    
    ### Architectural Decisions:
    - Uses principles from genetic algorithms to evolve test sequences
    - Maintains a population of action sequences with fitness scores
    - Evolves the population through selection, crossover, and mutation
    - Adapts to feedback by adjusting sequence fitness
    
    ### Role in the System:
    - Generates optimized sequences of actions
    - Learns effective patterns from execution history
    - Adapts to application structure over time
    - Efficiently explores complex state spaces
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the genetic algorithm strategy.

        Args:
            static_data: Optional static analysis data
        """
        super().__init__(static_data, "GeneticAlgorithmStrategy")
        
        # Population of action sequences (each is a list of action IDs)
        self.population: List[List[int]] = []
        
        # Fitness scores for each sequence in the population
        self.fitness_scores: Dict[str, float] = {}
        
        # Maximum sequence length
        self.max_sequence_length = 5
        
        # Population size
        self.population_size = 10
        
        # Mutation rate
        self.mutation_rate = 0.2
        
        # Last sequence that was selected
        self.current_sequence: Optional[List[int]] = None
        
        # Position in the current sequence
        self.sequence_position = 0
        
        # Action success history for fitness calculation
        self.action_success: Dict[int, float] = {}
        
        # Action value for finding new states
        self.action_new_state_value: Dict[int, float] = {}
        
        # Mapping from action IDs to actions
        self.action_map: Dict[int, ItemAction] = {}
        
        # Track state fingerprints encountered during sequence execution
        self.sequence_states: List[str] = []
        
        # Initialize metrics
        self.metrics = {
            "generation": 0,
            "best_fitness": 0.0,
            "sequences_completed": 0
        }

    def generate_action(self, screen: ScreenDescription, state_data: Dict[str, Any], 
                        history: Optional[List[Dict[str, Any]]] = None) -> Optional[ItemAction]:
        """
        Generate the next action using genetic algorithm.

        Args:
            screen: Current screen description
            state_data: Current state data
            history: Optional execution history

        Returns:
            Next action to execute
        """
        # Keep track of the current state
        current_state = state_data.get("fingerprint", "unknown")
        if hasattr(self, 'sequence_states'):
            self.sequence_states.append(current_state)
        
        # Update action map with available actions
        self._update_action_map(screen)
        
        # If no current sequence or we've reached the end, select a new one
        if (self.current_sequence is None or 
                self.sequence_position >= len(self.current_sequence)):
            self._select_next_sequence(screen)
            self.sequence_position = 0
            self.sequence_states = [current_state]
            
        # If still no sequence, use fallback strategy
        if (self.current_sequence is None or 
                self.sequence_position >= len(self.current_sequence)):
            return self._fallback_action_selection(screen)
            
        # Get the next action ID from the sequence
        action_id = self.current_sequence[self.sequence_position]
        self.sequence_position += 1
        
        # If action is not available, use fallback
        if action_id not in self.action_map:
            return self._fallback_action_selection(screen)
            
        # Return the selected action
        return self.action_map[action_id]

    def update_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Update fitness scores based on action feedback.

        Args:
            action: Executed action
            result: Action execution result
        """
        # Extract key information
        action_id = action.id
        success = result.get("success", False)
        new_state = result.get("new_state", False)
        
        # Update action success rate
        old_success_rate = self.action_success.get(action_id, 0.5)
        attempts = self.metrics.get(f"action_{action_id}_attempts", 0) + 1
        self.metrics[f"action_{action_id}_attempts"] = attempts
        
        # Update success rate
        new_success_rate = ((old_success_rate * (attempts - 1)) + (1.0 if success else 0.0)) / attempts
        self.action_success[action_id] = new_success_rate
        
        # Update new state value
        old_new_state_value = self.action_new_state_value.get(action_id, 0.1)
        new_new_state_value = ((old_new_state_value * (attempts - 1)) + (1.0 if new_state else 0.0)) / attempts
        self.action_new_state_value[action_id] = new_new_state_value
        
        # If we have a current sequence, update its fitness
        if self.current_sequence and self.sequence_position > 0:
            # Get the sequence ID
            sequence_id = self._get_sequence_id(self.current_sequence)
            
            # Calculate reward for this action
            reward = 0.0
            
            # Base reward for success
            if success:
                reward += 0.1
            else:
                reward -= 0.1
                
            # Reward for finding new states
            if new_state:
                reward += 0.5
                
            # Reward for security-relevant actions
            if getattr(action, 'reaches_mop', False):
                reward += 0.2
                
            # Extra reward for direct security actions
            if getattr(action, 'directly_reaches_mop', False):
                reward += 0.3
                
            # Reward for activity transitions
            if result.get("activity_changed", False):
                reward += 0.3
                
            # Update sequence fitness
            old_fitness = self.fitness_scores.get(sequence_id, 0.0)
            position_weight = (self.sequence_position / len(self.current_sequence))
            
            # Earlier actions in sequence get less weight than later ones
            new_fitness = old_fitness + (reward * position_weight)
            self.fitness_scores[sequence_id] = new_fitness
            
            # If sequence is complete, evolve the population
            if self.sequence_position >= len(self.current_sequence):
                self._evolve_population()
                self.metrics["sequences_completed"] += 1

    def _update_action_map(self, screen: ScreenDescription) -> None:
        """
        Update the mapping from action IDs to actions.

        Args:
            screen: Current screen description
        """
        # Initialize if needed
        if not hasattr(self, 'action_map'):
            self.action_map = {}
            
        # Update with available actions
        for item in screen.items:
            for action in item.actions:
                self.action_map[action.id] = action

    def _select_next_sequence(self, screen: ScreenDescription) -> None:
        """
        Select the next sequence to execute.

        Args:
            screen: Current screen description
        """
        # If population is empty or too small, initialize it
        if len(self.population) < self.population_size:
            self._initialize_population(screen)
            
        # If still empty, can't select a sequence
        if not self.population:
            self.current_sequence = None
            return
            
        # Select a sequence based on fitness
        self.current_sequence = self._select_sequence()

    def _initialize_population(self, screen: ScreenDescription) -> None:
        """
        Initialize the population with random sequences.

        Args:
            screen: Current screen description
        """
        # Collect all available action IDs
        available_action_ids = []
        for item in screen.items:
            for action in item.actions:
                available_action_ids.append(action.id)
                
        # If no actions available, can't create sequences
        if not available_action_ids:
            return
            
        # Create random sequences
        while len(self.population) < self.population_size:
            # Randomly determine sequence length
            length = random.randint(2, self.max_sequence_length)
            
            # Create a random sequence
            sequence = [random.choice(available_action_ids) for _ in range(length)]
            
            # Add to population
            sequence_id = self._get_sequence_id(sequence)
            if sequence_id not in self.fitness_scores:
                self.population.append(sequence)
                self.fitness_scores[sequence_id] = 0.5  # Initial neutral fitness

    def _select_sequence(self) -> List[int]:
        """
        Select a sequence from the population based on fitness.

        Returns:
            Selected sequence
        """
        # Calculate selection probabilities based on fitness
        total_fitness = sum(self.fitness_scores.get(self._get_sequence_id(seq), 0.1) 
                            for seq in self.population)
        
        if total_fitness <= 0:
            # If all sequences have negative or zero fitness, use uniform selection
            return random.choice(self.population)
            
        # Use fitness-proportional selection
        selection_point = random.uniform(0, total_fitness)
        current_sum = 0
        
        for sequence in self.population:
            current_sum += self.fitness_scores.get(self._get_sequence_id(sequence), 0.1)
            if current_sum >= selection_point:
                return sequence
                
        # Fallback to last sequence if something went wrong
        return self.population[-1]

    def _evolve_population(self) -> None:
        """
        Evolve the population using genetic algorithm principles.
        """
        # Increment generation counter
        self.metrics["generation"] += 1
        
        # If population is too small, can't evolve
        if len(self.population) < 2:
            return
            
        # Select parents based on fitness
        parent1 = self._select_sequence()
        parent2 = self._select_sequence()
        
        # Create a child through crossover
        child = self._crossover(parent1, parent2)
        
        # Apply mutation
        child = self._mutate(child)
        
        # Replace the worst sequence in the population
        self._replace_worst_sequence(child)
        
        # Update best fitness metric
        best_fitness = max(self.fitness_scores.values()) if self.fitness_scores else 0.0
        self.metrics["best_fitness"] = best_fitness

    def _crossover(self, parent1: List[int], parent2: List[int]) -> List[int]:
        """
        Create a child sequence through crossover.

        Args:
            parent1: First parent sequence
            parent2: Second parent sequence

        Returns:
            Child sequence
        """
        # If parents are identical, return a copy of parent1
        if parent1 == parent2:
            return parent1.copy()
            
        # Single-point crossover
        crossover_point = random.randint(1, min(len(parent1), len(parent2)) - 1)
        
        child = parent1[:crossover_point] + parent2[crossover_point:]
        
        # Ensure child doesn't exceed maximum length
        if len(child) > self.max_sequence_length:
            child = child[:self.max_sequence_length]
            
        return child

    def _mutate(self, sequence: List[int]) -> List[int]:
        """
        Apply mutation to a sequence.

        Args:
            sequence: Sequence to mutate

        Returns:
            Mutated sequence
        """
        # Make a copy of the sequence
        mutated = sequence.copy()
        
        # No mutation if action map is empty
        if not self.action_map:
            return mutated
            
        # Get list of available action IDs
        available_actions = list(self.action_map.keys())
        if not available_actions:
            return mutated
            
        # Apply mutation with probability based on mutation rate
        for i in range(len(mutated)):
            if random.random() < self.mutation_rate:
                # Replace with a random action
                mutated[i] = random.choice(available_actions)
                
        return mutated

    def _replace_worst_sequence(self, new_sequence: List[int]) -> None:
        """
        Replace the worst sequence in the population.

        Args:
            new_sequence: New sequence to add
        """
        if not self.population:
            self.population.append(new_sequence)
            self.fitness_scores[self._get_sequence_id(new_sequence)] = 0.5
            return
            
        # Find the sequence with the lowest fitness
        worst_index = 0
        worst_fitness = float('inf')
        
        for i, sequence in enumerate(self.population):
            sequence_id = self._get_sequence_id(sequence)
            fitness = self.fitness_scores.get(sequence_id, 0.0)
            
            if fitness < worst_fitness:
                worst_fitness = fitness
                worst_index = i
                
        # Replace the worst sequence
        new_sequence_id = self._get_sequence_id(new_sequence)
        
        # Only replace if new sequence doesn't already exist
        if new_sequence_id not in self.fitness_scores:
            self.population[worst_index] = new_sequence
            self.fitness_scores[new_sequence_id] = 0.5  # Initial neutral fitness

    def _get_sequence_id(self, sequence: List[int]) -> str:
        """
        Generate a unique ID for a sequence.

        Args:
            sequence: Action sequence

        Returns:
            Sequence ID string
        """
        return "-".join(str(action_id) for action_id in sequence)

    def _fallback_action_selection(self, screen: ScreenDescription) -> Optional[ItemAction]:
        """
        Select an action using a fallback strategy.

        Args:
            screen: Current screen description

        Returns:
            Selected action
        """
        # Collect all available actions
        all_actions = []
        for item in screen.items:
            all_actions.extend(item.actions)
            
        if not all_actions:
            return None
            
        # Use heuristic-based selection
        security_actions = [a for a in all_actions if getattr(a, 'reaches_mop', False)]
        
        # Prioritize security actions if available
        if security_actions:
            return random.choice(security_actions)
            
        # Otherwise, select a random action
        return random.choice(all_actions)