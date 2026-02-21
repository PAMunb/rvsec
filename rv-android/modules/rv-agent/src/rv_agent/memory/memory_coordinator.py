"""
Memory coordination system for multi-component memory management.

Coordinates updates across all memory systems and generates summaries
for stateless LLM context in each iteration.
"""

import logging
import time
from typing import Dict, Any, List, Optional

from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.memory.short_term import ShortTermMemory
from rv_agent.memory.long_term import LongTermMemory
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_agent.memory.agent_memory import AgentMemoryManager
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription


class MemoryCoordinator:
    """
    Coordinates memory updates across multiple memory systems.

    ### Architectural Decisions:
    - Centralizes memory coordination logic extracted from rv_agent.py
    - Manages five memory components: graph, short_term, long_term, ui_coverage, agent_memory
    - Generates stateless summaries for LLM context (~2500 tokens/iteration)
    - Tracks state discovery and transitions for exploration metrics
    - Provides continuation logic based on timeout
    - Maintains recent action window for loop detection

    ### Role in the System:
    - Coordinates all memory system updates after action execution
    - Generates memory summaries for next iteration context
    - Tracks exploration progress (states, transitions)
    - Manages action history window for validation
    - Provides continuation signals based on timeout

    ### Integration Points:
    - Used by RVAgent learn_node to update memories
    - Coordinates DynamicStateGraph state tracking
    - Updates ShortTermMemory with iteration records
    - Updates LongTermMemory with state visits
    - Updates UICoverageTracker with element interactions
    - Uses AgentMemoryManager for summary generation
    - Provides summaries to LLMClient for context construction
    """

    # Action type mapping from execution to internal format
    # Supports both uppercase (from execution) and lowercase (from tool results)
    ACTION_TYPE_MAPPING = {
        # Uppercase format (from execution/ToolExecutor)
        "CLICK": "click",
        "LONG_CLICK": "long_click",
        "SET_TEXT": "set_text",
        "SWIPE": "swipe",
        "SCROLL": "scroll",
        "SCROLL_UP": "scroll_up",
        "SCROLL_DOWN": "scroll_down",
        "SCROLL_LEFT": "scroll_left",
        "SCROLL_RIGHT": "scroll_right",
        "BACK": "key_event",
        "SYSTEM_BACK": "key_event",
        "HOME": "key_event",
        "PRESS_ENTER": "key_event",
        "UNKNOWN": "unknown",
        # Lowercase format (from LLM tool results)
        "click": "click",
        "long_click": "long_click",
        "set_text": "set_text",
        "swipe": "swipe",
        "scroll": "scroll",
        "back": "key_event",
        "home": "key_event",
        "press_enter": "key_event",
    }

    def __init__(
        self,
        dynamic_graph: DynamicStateGraph,
        short_term_memory: ShortTermMemory,
        long_term_memory: Optional[LongTermMemory],
        ui_coverage: UICoverageTracker,
        agent_memory: AgentMemoryManager,
        action_window_size: int = 10,
    ):
        """
        Initialize memory coordinator.

        Args:
            dynamic_graph: State graph for tracking exploration
            short_term_memory: Short-term memory for recent iterations
            long_term_memory: Optional long-term memory for state patterns
            ui_coverage: UI coverage tracker for element interactions
            agent_memory: Agent memory manager for summaries
            action_window_size: Size of recent action window for loop detection
        """
        self.dynamic_graph = dynamic_graph
        self.short_term = short_term_memory
        self.long_term = long_term_memory
        self.ui_coverage = ui_coverage
        self.agent_memory = agent_memory
        self.action_window_size = action_window_size

        self.logger = logging.getLogger(__name__)

    def update_memories(
        self,
        current_screen_hash: str,
        current_activity: str,
        screen_description: ScreenDescription,
        action: Optional[Dict[str, Any]],
        llm_reasoning: str,
        iteration: int,
        recent_action_window: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Update all memory systems with current iteration data.

        Args:
            current_screen_hash: Hash of current screen state
            current_activity: Current Android activity name
            screen_description: Parsed screen description
            action: Executed action dictionary (or None)
            llm_reasoning: LLM reasoning for this iteration
            iteration: Current iteration number
            recent_action_window: Recent action history

        Returns:
            Dictionary with:
            - recent_action_window: Updated action window
            - success: Whether all updates succeeded
        """
        self.logger.info(f"Updating memory systems (iteration {iteration})")

        # Update recent action window
        if action:
            recent_action_window.append(action)
            if len(recent_action_window) > self.action_window_size:
                recent_action_window = recent_action_window[-self.action_window_size :]

        try:
            # Update DynamicStateGraph
            self._update_dynamic_graph(
                current_screen_hash, current_activity, screen_description, action
            )

            # Update ShortTermMemory
            self._update_short_term(
                current_screen_hash, current_activity, action, llm_reasoning
            )

            # Update UICoverageTracker
            self._update_ui_coverage(current_screen_hash, screen_description)

            # Update LongTermMemory (if available)
            if self.long_term:
                self._update_long_term(
                    current_screen_hash, current_activity, screen_description
                )

            self.logger.info("Memory systems updated successfully")

            return {"recent_action_window": recent_action_window, "success": True}

        except Exception as e:
            self.logger.error(f"Memory update failed: {e}", exc_info=True)
            return {
                "recent_action_window": recent_action_window,
                "success": False,
                "error": str(e),
            }

    def generate_summaries(
        self,
        action: Optional[Dict[str, Any]],
        current_activity: str,
        visited_states: List[str],
        state_transitions: List[tuple],
    ) -> Dict[str, str]:
        """
        Generate memory summaries for next iteration context.

        Args:
            action: Last executed action
            current_activity: Current activity name
            visited_states: List of visited state hashes
            state_transitions: List of (from_hash, to_hash) transitions

        Returns:
            Dictionary with summary strings:
            - action_history_summary
            - exploration_summary
            - memory_insights
            - navigation_path
        """
        self.logger.debug("Generating memory summaries")

        try:
            # Record action in agent memory
            if action:
                self.agent_memory.record_action(
                    action=action,
                    activity=current_activity,
                    success=True,  # TODO(#18): Track actual action success via error detection
                )
                self.logger.debug("Recorded action in AgentMemoryManager")

            # Generate all summaries
            action_history = self.agent_memory.get_action_history_summary()
            exploration = self.agent_memory.get_exploration_summary(
                visited_states=visited_states, state_transitions=state_transitions
            )
            insights = self.agent_memory.get_memory_insights(current_activity)
            navigation = self.agent_memory.get_navigation_path()

            self.logger.info("Memory summaries generated successfully")

            return {
                "action_history_summary": action_history,
                "exploration_summary": exploration,
                "memory_insights": insights,
                "navigation_path": navigation,
            }

        except Exception as e:
            self.logger.error(f"Summary generation failed: {e}", exc_info=True)
            # Fallback summaries
            return {
                "action_history_summary": "No previous actions.",
                "exploration_summary": "Starting exploration.",
                "memory_insights": "No insights yet.",
                "navigation_path": "Starting navigation.",
            }

    def track_state_discovery(
        self,
        current_hash: str,
        previous_hash: Optional[str],
        visited_states: List[str],
        state_transitions: List[tuple],
    ) -> Dict[str, Any]:
        """
        Track state discovery and transitions.

        Args:
            current_hash: Current state hash
            previous_hash: Previous state hash (or None)
            visited_states: List of visited states
            state_transitions: List of transitions

        Returns:
            Dictionary with:
            - visited_states: Updated list
            - state_transitions: Updated list
            - new_state_discovered: Boolean
            - new_transition_discovered: Boolean
        """
        new_state = False
        new_transition = False

        # Track state discovery
        if current_hash and current_hash not in visited_states:
            visited_states.append(current_hash)
            new_state = True
            self.logger.debug(f"New state discovered: {current_hash[:12]}...")

        # Track transition
        if previous_hash and current_hash and previous_hash != current_hash:
            transition = (previous_hash, current_hash)
            if transition not in state_transitions:
                state_transitions.append(transition)
                new_transition = True
                self.logger.debug(
                    f"New transition: {previous_hash[:8]}... → {current_hash[:8]}..."
                )

        return {
            "visited_states": visited_states,
            "state_transitions": state_transitions,
            "new_state_discovered": new_state,
            "new_transition_discovered": new_transition,
        }

    def check_continuation(self, start_time: float, timeout: float) -> Dict[str, Any]:
        """
        Check if exploration should continue.

        Args:
            start_time: Exploration start timestamp
            timeout: Maximum execution time in seconds

        Returns:
            Dictionary with:
            - should_continue: Boolean
            - elapsed_time: Elapsed seconds
            - remaining_time: Remaining seconds
        """
        elapsed = time.time() - start_time
        remaining = max(0, timeout - elapsed)
        should_continue = elapsed < timeout

        self.logger.debug(
            f"Continuation check: elapsed={elapsed:.1f}s, "
            f"remaining={remaining:.1f}s, continue={should_continue}"
        )

        return {
            "should_continue": should_continue,
            "elapsed_time": elapsed,
            "remaining_time": remaining,
        }

    def _update_dynamic_graph(
        self,
        screen_hash: str,
        activity: str,
        screen_desc: ScreenDescription,
        action: Optional[Dict[str, Any]],
    ):
        """Update DynamicStateGraph with state and action information."""
        # Create or update state node
        node = self.dynamic_graph.get_or_create_state(
            screen_hash=screen_hash, activity=activity, screen_desc=screen_desc
        )
        self.logger.debug(
            f"Updated graph state: {screen_hash[:8]} (visits: {node.visit_count})"
        )

        # Add action to trace
        if action:
            self.dynamic_graph.record_action_to_trace(action)
            self.logger.debug(
                f"Added to trace (total: {len(self.dynamic_graph.current_trace)})"
            )

            # Record action execution with signature
            # Extract coordinates - try llm_coords first (from LLM tools), then x/y
            if "llm_coords" in action and isinstance(action["llm_coords"], tuple):
                action_coords = action["llm_coords"]
            else:
                action_coords = (action.get("x", 0), action.get("y", 0))

            action_type_raw = action.get("action_type", "UNKNOWN")
            action_type = self.ACTION_TYPE_MAPPING.get(action_type_raw, "unknown")

            action_signature = (action_coords, action_type)
            action_id = action.get("id", "unknown")

            # Enhanced logging for better visibility
            if action_type in (
                "swipe",
                "scroll",
                "scroll_up",
                "scroll_down",
                "scroll_left",
                "scroll_right",
            ):
                direction = action.get("direction", "unknown")
                self.logger.info(
                    f"↔️ SCROLL/SWIPE: {action_type} direction={direction} "
                    f"signature={action_signature} ID={action_id}"
                )
            else:
                self.logger.debug(
                    f"Recording action: ID={action_id} signature={action_signature}"
                )

            self.dynamic_graph.record_action(
                screen_hash=screen_hash, action_signature=action_signature
            )

    def _update_short_term(
        self,
        screen_hash: str,
        activity: str,
        action: Optional[Dict[str, Any]],
        llm_reasoning: str,
    ):
        """Update ShortTermMemory with iteration record."""
        state_dict = {"screen_hash": screen_hash, "activity": activity}
        actions_list = [action] if action else []

        self.short_term.record_iteration(
            state=state_dict, actions=actions_list, llm_reasoning=llm_reasoning
        )
        self.logger.debug("Updated ShortTermMemory")

    def _update_ui_coverage(self, screen_hash: str, screen_desc: ScreenDescription):
        """
        Update UICoverageTracker with screen element visibility.

        NOTE: Element visibility is already tracked by register_screen_elements()
        in parse_node.py. Real action interactions (CLICK, SET_TEXT, etc.) are
        recorded in execute_node.py. We no longer record "view" as an interaction
        because it pollutes action_distribution metrics (~91% were "view").
        """
        # Element registration is done in parse_node.py via register_screen_elements()
        # Real action tracking is done in execute_node.py via record_interaction()
        self.logger.debug(
            f"Screen has {len(screen_desc.items)} elements (visibility tracked via parse_node)"
        )

    def _update_long_term(
        self, screen_hash: str, activity: str, screen_desc: ScreenDescription
    ):
        """Update LongTermMemory with state visit."""
        self.long_term.record_state(
            state_hash=screen_hash,
            activity=activity,
            interactive_elements_count=len(screen_desc.items),
        )
        self.logger.debug(f"Updated LongTermMemory: state {screen_hash[:8]}")

    def get_all_statistics(self) -> Dict[str, Any]:
        """
        Unified facade for all memory statistics.

        Returns comprehensive statistics from all memory systems for metrics
        collection and analysis. This facade method provides a single point
        of access to statistics from:
        - UI coverage tracker
        - Short-term memory
        - Long-term memory (if enabled)
        - Dynamic state graph

        Returns:
            Dictionary with the following structure:
            {
                'ui_coverage': {...},  # From UICoverageTracker
                'short_term': {...},   # From ShortTermMemory
                'long_term': {...},    # From LongTermMemory (or {} if None)
                'dynamic_graph': {     # From DynamicStateGraph
                    'total_states': int,
                    'total_transitions': int
                }
            }
        """
        self.logger.debug("Collecting statistics from all memory systems")

        try:
            stats = {
                "ui_coverage": self.ui_coverage.get_overall_statistics(),
                "short_term": self.short_term.get_statistics(),
                "long_term": self.long_term.get_statistics() if self.long_term else {},
                "dynamic_graph": {
                    "total_states": len(self.dynamic_graph.states),
                    "total_transitions": len(self.dynamic_graph.transitions),
                },
            }

            self.logger.info(
                f"Statistics collected: "
                f"{stats['ui_coverage'].get('total_unique_elements', 0)} UI elements, "
                f"{stats['short_term'].get('iteration_count', 0)} iterations, "
                f"{stats['dynamic_graph']['total_states']} states"
            )

            return stats

        except Exception as e:
            self.logger.error(f"Failed to collect statistics: {e}", exc_info=True)
            # Return empty structure on error
            return {
                "ui_coverage": {},
                "short_term": {},
                "long_term": {},
                "dynamic_graph": {"total_states": 0, "total_transitions": 0},
            }
