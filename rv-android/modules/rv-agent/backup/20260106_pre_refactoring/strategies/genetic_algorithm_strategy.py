"""
Genetic Algorithm exploration strategy for RVAgent.

Uses evolutionary principles to evolve sequences of actions that maximize exploration
and coverage. Maintains a population of action sequences with fitness scores, evolving
them through selection, crossover, and mutation operations.
"""

import logging
import random
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from rv_agent.core.dynamic_state_graph import DynamicStateGraph
from rv_agent.strategies.base_strategy import ExplorationStrategy
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ItemAction
from rv_android_core.domain.static import StaticAnalysisData

logger = logging.getLogger(__name__)


@dataclass
class ActionSequence:
    """
    Represents a sequence of actions with fitness tracking.

    Uses coordinate signatures instead of volatile action IDs for stability
    across screen visits.
    """
    signatures: List[Tuple[Tuple[int, int], str]]  # List of action coordinate signatures
    fitness: float = 0.5  # Neutral initial fitness
    executions: int = 0
    new_states_discovered: int = 0


class GeneticAlgorithmStrategy(ExplorationStrategy):
    """
    Genetic algorithm strategy that evolves sequences of actions for optimal exploration.

    ### Algorithm Implementation:
    - **Population**: Maintains multiple action sequences (genomes)
    - **Selection**: Fitness-proportional selection for parent sequences
    - **Crossover**: Combines parent sequences to create offspring
    - **Mutation**: Random modifications to maintain diversity
    - **Fitness**: Tracks new state discovery, MOP coverage, success rates

    ### Key Innovation: Coordinate-Based Sequences
    Sequences use coordinate signatures instead of action IDs, ensuring
    stability when the same UI element appears in different parsing orders.

    ### Comparison to Other Strategies:
    - **DFS/BFS**: Fixed exploration pattern
    - **Greedy**: Single-step optimization
    - **SimulatedAnnealing**: Adaptive single actions
    - **GeneticAlgorithm**: Evolves multi-step action sequences

    ### Trade-offs:
    - **Advantages**: Learns effective patterns, handles complex state spaces, sequence optimization
    - **Disadvantages**: Slower convergence, more complex, requires longer test durations
    - **Best for**: Complex apps, long test sessions, discovering optimal action sequences
    """

    def __init__(
        self,
        graph: DynamicStateGraph,
        static_data: Optional[StaticAnalysisData] = None,
        coordinate_converter = None
    ):
        """
        Initialize genetic algorithm exploration strategy.

        Args:
            graph: Dynamic state graph for history tracking (shared memory)
            static_data: Optional static analysis data for MOP markers
            coordinate_converter: Optional coordinate converter for space transformations
        """
        self.graph = graph
        self.static_data = static_data
        self.converter = coordinate_converter

        # Population management
        self.population: List[ActionSequence] = []
        self.population_size = 10
        self.max_sequence_length = 5

        # Evolution parameters
        self.mutation_rate = 0.2
        self.generation = 0

        # Current sequence execution
        self.current_sequence: Optional[ActionSequence] = None
        self.sequence_position = 0
        self.sequence_start_hash: Optional[str] = None

        # Action mapping and tracking
        self.action_signature_map: Dict[Tuple[Tuple[int, int], str], ItemAction] = {}
        self.visited_states: Set[str] = set()
        self.states_in_sequence: List[str] = []

        # Performance metrics
        self.sequences_completed = 0
        self.best_fitness = 0.0

        logger.info(f"Genetic Algorithm strategy initialized (pop={self.population_size}, max_seq={self.max_sequence_length})")

    def select_next_action(
        self,
        current_hash: str,
        screen_desc: ScreenDescription
    ) -> Optional[ItemAction]:
        """
        Select next action using genetic algorithm with sequence execution.

        ### Selection Process:
        1. Update action signature map from current screen
        2. Check if current sequence is exhausted or invalid
        3. If needed, select new sequence from population (or initialize)
        4. Execute next action in sequence
        5. Fallback to heuristic selection if sequence fails

        Args:
            current_hash: Structural hash of current UI state
            screen_desc: Parsed screen with UI elements and actions

        Returns:
            Next action from sequence, or None if state exhausted
        """
        logger.debug(f"GeneticAlgo: Processing state {current_hash[:8]}, seq_pos={self.sequence_position}")

        # Create or update graph node
        if current_hash not in self.graph.states:
            node = self.graph.get_or_create_state(
                current_hash,
                screen_desc.activity,
                screen_desc
            )
            logger.info(f"GeneticAlgo: New state, {node.total_actions} actions")
        else:
            node = self.graph.states[current_hash]
            logger.info(f"GeneticAlgo: Revisited state (visit {node.visit_count})")

        self.visited_states.add(current_hash)

        # Track states visited in current sequence
        if self.current_sequence:
            self.states_in_sequence.append(current_hash)

        # Update action signature map
        self._update_action_signature_map(screen_desc)

        # Get all available actions
        all_actions = screen_desc.get_all_actions()
        filtered_actions = self._filter_actions(all_actions)
        untested_actions = self._get_untested_actions(node, filtered_actions)

        # Log exploration state
        logger.info(f"GeneticAlgo State Analysis - {current_hash[:8]}:")
        logger.info(f"  Generation: {self.generation}")
        logger.info(f"  Population size: {len(self.population)}")
        logger.info(f"  Total actions: {len(filtered_actions)}")
        logger.info(f"  Untested: {len(untested_actions)}")

        # Check if we need a new sequence
        sequence_exhausted = (
            self.current_sequence is None or
            self.sequence_position >= len(self.current_sequence.signatures)
        )

        if sequence_exhausted:
            # Complete current sequence if it exists
            if self.current_sequence and self.sequence_position > 0:
                self._complete_sequence()

            # Select new sequence
            if not untested_actions:
                logger.info(f"GeneticAlgo: State {current_hash[:8]} exhausted")
                return None

            self._select_new_sequence(current_hash, untested_actions)

        # If still no sequence, use fallback
        if self.current_sequence is None:
            logger.info("GeneticAlgo FALLBACK: Using heuristic selection")
            return self._fallback_selection(untested_actions)

        # Get next action from sequence
        action_signature = self.current_sequence.signatures[self.sequence_position]
        selected_action = self.action_signature_map.get(action_signature)

        # If action no longer available, use fallback
        if not selected_action or selected_action not in untested_actions:
            logger.info("GeneticAlgo FALLBACK: Sequence action unavailable")
            return self._fallback_selection(untested_actions)

        # Advance sequence position
        self.sequence_position += 1

        # Log selection
        logger.info(f"GeneticAlgo SEQUENCE: Action {self.sequence_position}/{len(self.current_sequence.signatures)}")
        logger.info(f"  Signature: {action_signature}")
        logger.info(f"  Fitness: {self.current_sequence.fitness:.2f}")
        logger.info(f"  Priority: {self._get_mop_priority(selected_action)}")

        # Mark action as executed
        self.graph.record_action(screen_hash=current_hash, action_signature=action_signature)

        return selected_action

    def record_transition(
        self,
        from_hash: str,
        to_hash: str,
        action: ItemAction
    ):
        """
        Record state transition and update sequence fitness.

        Args:
            from_hash: Structural hash of source state
            to_hash: Structural hash of destination state
            action: Action that triggered the transition
        """
        if not self.current_sequence:
            return

        # Calculate reward for this transition
        reward = 0.0

        # Reward for discovering new state
        if to_hash not in self.visited_states:
            reward += 0.5
            self.current_sequence.new_states_discovered += 1
            logger.debug(f"GeneticAlgo: Sequence discovered new state")

        # Reward for MOP coverage
        if getattr(action, 'directly_reaches_mop', False):
            reward += 0.3
        elif getattr(action, 'reaches_mop', False):
            reward += 0.2

        # Reward for successful execution
        reward += 0.1

        # Update fitness with position weighting (later actions weighted more)
        position_weight = self.sequence_position / len(self.current_sequence.signatures)
        self.current_sequence.fitness += reward * position_weight

        logger.debug(f"GeneticAlgo: Updated fitness to {self.current_sequence.fitness:.2f}")

    def should_backtrack(self, current_hash: str) -> bool:
        """
        Determine if backtracking is needed.

        Args:
            current_hash: Structural hash of current state

        Returns:
            True if all actions explored
        """
        node = self.graph.states.get(current_hash)
        if not node:
            return False

        return len(node.executed_actions) >= node.total_actions

    def reset(self):
        """Reset strategy state for new exploration session."""
        # Keep population for learning, reset execution state
        self.current_sequence = None
        self.sequence_position = 0
        self.sequence_start_hash = None
        self.states_in_sequence = []
        self.visited_states.clear()
        self.action_signature_map.clear()
        logger.info("GeneticAlgorithm strategy reset (population maintained)")

    def _update_action_signature_map(self, screen_desc: ScreenDescription):
        """
        Update mapping from coordinate signatures to actions.

        Args:
            screen_desc: Current screen description
        """
        self.action_signature_map.clear()

        for action in screen_desc.get_all_actions():
            signature = self._convert_signature_to_optimized(action.coords_for_matching)
            self.action_signature_map[signature] = action

    def _select_new_sequence(self, current_hash: str, available_actions: List[ItemAction]):
        """
        Select or create a new sequence for execution.

        Args:
            current_hash: Current state hash
            available_actions: Actions available for sequence creation
        """
        # Initialize population if needed
        if len(self.population) < self.population_size:
            self._initialize_population(available_actions)

        # If still no population, can't select
        if not self.population:
            self.current_sequence = None
            return

        # Select sequence based on fitness
        self.current_sequence = self._fitness_proportional_selection()
        self.sequence_position = 0
        self.sequence_start_hash = current_hash
        self.states_in_sequence = [current_hash]

        logger.info(f"GeneticAlgo: Selected sequence length={len(self.current_sequence.signatures)}, fitness={self.current_sequence.fitness:.2f}")

    def _initialize_population(self, available_actions: List[ItemAction]):
        """
        Initialize population with random sequences.

        Args:
            available_actions: Actions to build sequences from
        """
        if not available_actions:
            return

        # Convert actions to signatures
        signatures = [
            self._convert_signature_to_optimized(action.coords_for_matching)
            for action in available_actions
        ]

        while len(self.population) < self.population_size:
            # Random sequence length
            length = random.randint(2, min(self.max_sequence_length, len(signatures)))

            # Create random sequence
            sequence_sigs = random.sample(signatures, length)
            sequence = ActionSequence(signatures=sequence_sigs, fitness=0.5)

            self.population.append(sequence)

        logger.info(f"GeneticAlgo: Initialized population with {len(self.population)} sequences")

    def _fitness_proportional_selection(self) -> ActionSequence:
        """
        Select sequence from population using fitness-proportional selection.

        Returns:
            Selected sequence
        """
        # Calculate total fitness
        total_fitness = sum(max(0.1, seq.fitness) for seq in self.population)

        if total_fitness <= 0:
            return random.choice(self.population)

        # Roulette wheel selection
        selection_point = random.uniform(0, total_fitness)
        cumulative = 0

        for sequence in self.population:
            cumulative += max(0.1, sequence.fitness)
            if cumulative >= selection_point:
                return sequence

        return self.population[-1]

    def _complete_sequence(self):
        """
        Complete current sequence execution and trigger evolution.
        """
        if not self.current_sequence:
            return

        # Update sequence statistics
        self.current_sequence.executions += 1
        self.sequences_completed += 1

        logger.info(f"GeneticAlgo: Sequence completed")
        logger.info(f"  Final fitness: {self.current_sequence.fitness:.2f}")
        logger.info(f"  New states: {self.current_sequence.new_states_discovered}")
        logger.info(f"  States visited: {len(self.states_in_sequence)}")

        # Trigger evolution
        self._evolve_population()

    def _evolve_population(self):
        """
        Evolve population using genetic operators.

        Performs selection, crossover, mutation, and replacement.
        """
        if len(self.population) < 2:
            return

        self.generation += 1

        # Select two parents
        parent1 = self._fitness_proportional_selection()
        parent2 = self._fitness_proportional_selection()

        # Crossover
        child = self._crossover(parent1, parent2)

        # Mutation
        child = self._mutate(child)

        # Replace worst sequence
        self._replace_worst(child)

        # Update metrics
        self.best_fitness = max(seq.fitness for seq in self.population)

        logger.info(f"GeneticAlgo: Evolution gen={self.generation}, best_fitness={self.best_fitness:.2f}")

    def _crossover(self, parent1: ActionSequence, parent2: ActionSequence) -> ActionSequence:
        """
        Create offspring through single-point crossover.

        Args:
            parent1: First parent
            parent2: Second parent

        Returns:
            Child sequence
        """
        if parent1.signatures == parent2.signatures:
            return ActionSequence(signatures=parent1.signatures.copy(), fitness=0.5)

        # Single-point crossover
        min_len = min(len(parent1.signatures), len(parent2.signatures))
        if min_len <= 1:
            return ActionSequence(signatures=parent1.signatures.copy(), fitness=0.5)

        crossover_point = random.randint(1, min_len - 1)

        child_sigs = parent1.signatures[:crossover_point] + parent2.signatures[crossover_point:]

        # Enforce max length
        if len(child_sigs) > self.max_sequence_length:
            child_sigs = child_sigs[:self.max_sequence_length]

        return ActionSequence(signatures=child_sigs, fitness=0.5)

    def _mutate(self, sequence: ActionSequence) -> ActionSequence:
        """
        Apply mutation to sequence.

        Args:
            sequence: Sequence to mutate

        Returns:
            Mutated sequence
        """
        if not self.action_signature_map:
            return sequence

        mutated_sigs = sequence.signatures.copy()
        available_sigs = list(self.action_signature_map.keys())

        if not available_sigs:
            return sequence

        # Mutate each position with mutation_rate probability
        for i in range(len(mutated_sigs)):
            if random.random() < self.mutation_rate:
                mutated_sigs[i] = random.choice(available_sigs)

        return ActionSequence(signatures=mutated_sigs, fitness=0.5)

    def _replace_worst(self, new_sequence: ActionSequence):
        """
        Replace worst sequence in population with new sequence.

        Args:
            new_sequence: New sequence to add
        """
        if not self.population:
            self.population.append(new_sequence)
            return

        # Find worst sequence
        worst_idx = min(range(len(self.population)), key=lambda i: self.population[i].fitness)

        # Only replace if new sequence is different
        if new_sequence.signatures != self.population[worst_idx].signatures:
            self.population[worst_idx] = new_sequence
            logger.debug(f"GeneticAlgo: Replaced worst sequence (fitness={self.population[worst_idx].fitness:.2f})")

    def _fallback_selection(self, actions: List[ItemAction]) -> Optional[ItemAction]:
        """
        Fallback to heuristic selection when sequences fail.

        Args:
            actions: Available actions

        Returns:
            Selected action
        """
        if not actions:
            return None

        # Prioritize MOP actions
        mop_actions = [a for a in actions if getattr(a, 'reaches_mop', False)]
        if mop_actions:
            return random.choice(mop_actions)

        # Otherwise random
        return random.choice(actions)

    # Re-use filtering methods (same as Greedy/SimulatedAnnealing)
    def _filter_actions(self, actions: List[ItemAction]) -> List[ItemAction]:
        """Filter out system actions and navigation bar interactions."""
        filtered = []
        for action in actions:
            if action.target_view.get('system_action', False):
                continue
            coords = action.get_execution_coordinates()
            if not coords:
                logger.debug(f"Filtered action without coordinates: ID={action.id}")
                continue
            x, y = coords
            if y > 1794:
                continue
            filtered.append(action)
        return filtered

    def _get_untested_actions(self, node, actions: List[ItemAction]) -> List[ItemAction]:
        """Identify actions not yet executed on this state."""
        untested = []
        for action in actions:
            action_signature = self._convert_signature_to_optimized(action.coords_for_matching)
            if action_signature not in node.executed_actions:
                untested.append(action)
        return untested

    def _convert_signature_to_optimized(self, signature: Tuple[Tuple[int, int], str]) -> Tuple[Tuple[int, int], str]:
        """Convert action signature to optimized space."""
        if not self.converter:
            return signature
        coords, action_type = signature
        optimized_coords = self.converter.device_to_optimized(coords)
        return (optimized_coords, action_type)

    def _get_mop_priority(self, action: ItemAction) -> int:
        """Compute MOP priority score."""
        if getattr(action, 'directly_reaches_mop', False):
            return 3
        elif getattr(action, 'reaches_mop', False):
            return 2
        return 1
