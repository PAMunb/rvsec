"""
Coverage-optimized depth-first exploration with successor tracking.

Implements state space exploration with:
1. Successor state tracking to re-enable actions when destination states are incomplete
2. MOP-aware action prioritization
3. Plateau detection for automatic termination
4. Input field value variation generation
"""

import logging
from dataclasses import dataclass
from typing import Optional, List, Set, Tuple, TYPE_CHECKING
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ItemAction
from rv_android_core.domain.widget import WidgetEventType

from rv_agent.strategies.base_strategy import ExplorationStrategy
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_android_core.domain.static import StaticAnalysisData

from rv_agent.strategies.rvagent_strategy.successor_tracker import SuccessorTracker
from rv_agent.strategies.rvagent_strategy.plateau_detector import PlateauDetector
from rv_agent.strategies.rvagent_strategy.input_value_generator import InputValueGenerator
from rv_agent.strategies.rvagent_strategy.coverage_metrics import CoverageMetrics

if TYPE_CHECKING:
    from rv_agent.services.transition_manager import TransitionManager


logger = logging.getLogger(__name__)


@dataclass
class RVAgentState:
    """Represents a state in the DFS stack."""
    screen_hash: str
    depth: int
    parent_hash: Optional[str]
    untested_count: int


class RVAgentStrategy(ExplorationStrategy):
    """
    Depth-first exploration with successor state tracking.

    Tracks action-to-successor mappings and re-enables actions when
    destination states remain incompletely explored. Prevents premature
    backtracking in states that lead to partially explored destinations.

    Action prioritization: [DM] MOP > [M] MOP > untested UI > least tested UI

    Example scenario:
        State A: Click "Dropdown" → State B (menu with 3 items)
        If only 1/3 items tested in State B, action in State A is re-enabled
    """

    def __init__(
        self,
        graph: DynamicStateGraph,
        ui_coverage: UICoverageTracker,
        coordinate_converter=None,
        static_data: Optional[StaticAnalysisData] = None,
        transition_manager: Optional["TransitionManager"] = None,
        plateau_window: int = 10,
        max_input_variations: int = 3,
        target_package: Optional[str] = None
    ):
        """
        Initialize RVAgent exploration strategy.

        Args:
            graph: DynamicStateGraph for state/action tracking
            ui_coverage: UICoverageTracker for UI element coverage
            coordinate_converter: CoordinateConverter for device/optimized space
            static_data: Optional static analysis data (WTG, REACH)
            transition_manager: Optional TransitionManager for WTG-guided navigation
            plateau_window: Iterations without progress to detect plateau
            max_input_variations: Maximum test values per input field
            target_package: Target app package name for filtering external elements
        """
        self.graph = graph
        self.ui_coverage = ui_coverage
        self.converter = coordinate_converter
        self.static_data = static_data
        self.transition_manager = transition_manager
        self.target_package = target_package

        # Helper components
        self.successor_tracker = SuccessorTracker(graph)
        self.plateau_detector = PlateauDetector(window_size=plateau_window)
        self.value_generator = InputValueGenerator(max_variations=max_input_variations)
        self.coverage_metrics = CoverageMetrics(graph, ui_coverage)

        # DFS state
        self.state_stack: List[RVAgentState] = []
        self.visited_states: Set[str] = set()
        self.current_depth = 0

        # Previous state for transition tracking
        self.previous_hash: Optional[str] = None

        # Scroll tracking to avoid infinite scrolling loops
        self.scrolled_positions: Set[Tuple[str, str, str]] = set()

        logger.info(
            f"RVAgentStrategy initialized: plateau_window={plateau_window}, "
            f"max_variations={max_input_variations}, "
            f"transition_manager={'enabled' if transition_manager else 'disabled'}"
        )
        if target_package:
            logger.info(f"RVAgentStrategy: Filtering actions to package '{target_package}'")

    def select_next_action(
        self,
        current_hash: str,
        screen_desc: ScreenDescription
    ) -> Optional[ItemAction]:
        """
        Select next action using coverage-optimized DFS.

        Algorithm:
        1. Check plateau - return None if reached
        2. Create/update graph node
        3. Re-enable actions with incomplete successors
        4. Get untested actions (filtered)
        5. Prioritize: [DM] > [M] > Untested UI > Low test count
        6. Handle input fields with value generation
        7. Pre-mark action and update UI coverage

        Args:
            current_hash: Structural hash of current state
            screen_desc: Parsed screen with available actions

        Returns:
            Selected ItemAction, or None if state exhausted or plateau reached
        """
        logger.debug(f"RVAgent: Processing state {current_hash[:8]}, depth={self.current_depth}")

        # 1. Check plateau detection (informational only - does NOT stop exploration)
        if self.plateau_detector.is_plateau_reached():
            logger.info("Plateau detected - continuing exploration (timeout is only stop condition)")
            plateau_metrics = self.plateau_detector.get_metrics()
            logger.debug(f"Plateau metrics: {plateau_metrics}")

        # 2. Create or update graph node
        if current_hash not in self.graph.states:
            node = self.graph.get_or_create_state(
                current_hash,
                screen_desc.activity,
                screen_desc
            )

            parent_hash = self.state_stack[-1].screen_hash if self.state_stack else None

            rvagent_state = RVAgentState(
                screen_hash=current_hash,
                depth=self.current_depth,
                parent_hash=parent_hash,
                untested_count=node.total_actions
            )
            self.state_stack.append(rvagent_state)
            self.visited_states.add(current_hash)

            logger.info(f"RVAgent: New state at depth {self.current_depth}, {node.total_actions} actions")
        else:
            node = self.graph.states[current_hash]
            node.visit_count += 1
            logger.debug(f"RVAgent: Revisiting state (visit #{node.visit_count})")

        # 3. Re-enable actions with incomplete successors (prevents premature backtracking)
        re_enabled = self.successor_tracker.update_action_availability(current_hash)
        if re_enabled > 0:
            logger.info(f"Re-enabled {re_enabled} actions due to incomplete successors")

        # 4. Get untested actions and all filtered actions
        untested_actions = self._get_untested_actions(node, screen_desc)
        all_filtered_actions = self._get_all_filtered_actions(screen_desc)

        logger.info(
            f"RVAgent State Analysis - {current_hash[:8]}:\n"
            f"  Total actions: {len(screen_desc.items)}\n"
            f"  Filtered actions: {len(all_filtered_actions)}\n"
            f"  Executed: {len(node.executed_actions)}\n"
            f"  Untested: {len(untested_actions)}"
        )

        # Try to generate SWIPE action for scrollable containers (30% probability)
        # This reveals hidden content in lists, feeds, and scrollable views
        scroll_action = self._try_generate_scroll_action(
            screen_desc, node, self.scrolled_positions, probability=0.3
        )
        if scroll_action:
            self.current_depth += 1
            logger.info(f"RVAgent SCROLL: Generating scroll action to reveal content")
            return scroll_action

        # 5. Select action based on availability
        if untested_actions:
            # UNTESTED: Select priority action from untested
            selected_action = self._select_priority_action(untested_actions, screen_desc)
            if selected_action:
                logger.info(f"RVAgent DEEPEN: Selected UNTESTED action")
            else:
                # Fallback to first untested
                selected_action = untested_actions[0]
                logger.info(f"RVAgent DEEPEN: Fallback to first untested action")
        elif all_filtered_actions:
            # CONTINUOUS: All actions tested - select LEAST-EXECUTED action
            # Algorithm continues until timeout, never stops when "exhausted"
            # Filters out permanently failed actions to avoid repeated crashes
            selected_action = self._select_least_executed_action(node, all_filtered_actions)

            # If all actions have failed, fall through to BACK
            if selected_action is None:
                logger.info(f"RVAgent: All actions failed on state {current_hash[:8]}, returning BACK")
                back_action = ItemAction(
                    id=999,
                    text="BACK",
                    event=WidgetEventType.BACK,
                    reaches_mop=False,
                    directly_reaches_mop=False,
                    target_view={"system_action": True, "class": "SystemAction_BACK"},
                    coordinates=None,
                    text_input=None
                )
                return back_action

            action_signature = self._convert_signature_to_optimized(selected_action.coords_for_matching)
            exec_count = node.get_action_execution_count(action_signature)
            logger.info(f"RVAgent CONTINUOUS: Selected LEAST-EXECUTED action")
            logger.info(f"  Execution count: {exec_count} -> {exec_count + 1}")
        else:
            # No actions available (edge case) - return BACK to navigate
            logger.info(f"RVAgent: No actions available on state {current_hash[:8]}, returning BACK")
            back_action = ItemAction(
                id=999,
                text="BACK",
                event=WidgetEventType.BACK,
                reaches_mop=False,
                directly_reaches_mop=False,
                target_view={"system_action": True, "class": "SystemAction_BACK"},
                coordinates=None,
                text_input=None
            )
            return back_action

        self.current_depth += 1

        # 6. Handle input fields with value generation
        if selected_action.event == WidgetEventType.TEXT_CHANGE:
            original_action = selected_action
            selected_action = self._prepare_input_action(selected_action, current_hash)
            if not selected_action:
                # Value exhausted - mark action as executed to prevent re-selection
                action_signature = self._convert_signature_to_optimized(original_action.coords_for_matching)
                self.graph.record_action(screen_hash=current_hash, action_signature=action_signature)
                # Also mark in UI coverage tracker now that all variations are tested
                element_id = original_action.widget_id or f"coords:{original_action.coordinates}"
                self.ui_coverage.record_interaction(
                    element_id=element_id,
                    action_type=original_action.event.value,
                    screen_hash=current_hash,
                    success=True
                )
                logger.debug("Input values exhausted, marking action as executed and selecting different action")
                # Use iterative approach instead of recursion
                untested_actions = self._get_untested_actions(node, screen_desc)
                if untested_actions:
                    selected_action = self._select_priority_action(untested_actions, screen_desc) or untested_actions[0]
                else:
                    # Fallback to BACK if no untested actions
                    return ItemAction(
                        id=999,
                        text="BACK",
                        event=WidgetEventType.BACK,
                        reaches_mop=False,
                        directly_reaches_mop=False,
                        target_view={"system_action": True, "class": "SystemAction_BACK"},
                        coordinates=None,
                        text_input=None
                    )

        # 7. Pre-mark action as executed (crash handling)
        # NOTE: Skip TEXT_CHANGE actions - they should only be marked as executed
        # when all input variations are exhausted (handled in step 6 above).
        # Marking them here would prevent testing of remaining variations.
        if selected_action.event != WidgetEventType.TEXT_CHANGE:
            action_signature = self._convert_signature_to_optimized(selected_action.coords_for_matching)
            self.graph.record_action(screen_hash=current_hash, action_signature=action_signature)

        # 8. Update UI coverage tracker
        # NOTE: Skip TEXT_CHANGE actions - they should only be marked as tested
        # when all input variations are exhausted (handled in step 6 above).
        # Marking them here would cause priority selection to skip them prematurely.
        if selected_action.event != WidgetEventType.TEXT_CHANGE:
            element_id = selected_action.widget_id or f"coords:{selected_action.coordinates}"
            self.ui_coverage.record_interaction(
                element_id=element_id,
                action_type=selected_action.event.value,
                screen_hash=current_hash,
                success=True
            )

        # 9. Record MOP if applicable
        if selected_action.callback_signature:
            self.coverage_metrics.record_mop_execution(selected_action.callback_signature)

        logger.info(
            f"Selected action: {selected_action.event.value} "
            f"(priority={'[DM]' if selected_action.directly_reaches_mop else '[M]' if selected_action.reaches_mop else 'UI'})"
        )

        return selected_action

    def record_transition(
        self,
        from_hash: str,
        to_hash: str,
        action: ItemAction
    ):
        """
        Record state transition and update tracking components.

        Args:
            from_hash: Source state hash
            to_hash: Destination state hash
            action: Action that triggered transition
        """
        # Record in graph
        action_signature = self._convert_signature_to_optimized(action.coords_for_matching)
        self.graph.record_transition(from_hash, to_hash, [{"action": action}])

        # Update successor tracker (enables action re-enabling logic)
        self.successor_tracker.record_successor(from_hash, action_signature, to_hash)

        # Update plateau detector
        new_state = to_hash not in self.visited_states
        new_mop = action.callback_signature if action.callback_signature else None

        self.plateau_detector.record_iteration(
            discovered_new_state=new_state,
            new_mop_method=new_mop
        )

        # Update stack if new state
        if new_state and from_hash in self.visited_states:
            # Deepening - handled in select_next_action
            pass

        self.previous_hash = from_hash

        logger.debug(f"Transition recorded: {from_hash[:8]} → {to_hash[:8]}")

    def should_backtrack(self, current_hash: str) -> bool:
        """
        Determine if backtracking needed from current state.

        Logic:
        1. Check incomplete successors - if found, DON'T backtrack
        2. Check state exhaustion - backtrack if all actions executed

        Args:
            current_hash: Current state hash

        Returns:
            True if should backtrack
        """
        # Get state node
        node = self.graph.states.get(current_hash)
        if not node:
            logger.warning(f"State {current_hash[:8]} not in graph - backtracking")
            return True

        # Don't backtrack if successors incomplete (maintains exploration depth)
        if self.successor_tracker.has_incomplete_successors(current_hash):
            logger.info(
                f"Not backtracking from {current_hash[:8]}: "
                f"has actions with incomplete successors"
            )
            return False

        # Check state exhaustion
        exhausted = len(node.executed_actions) >= node.total_actions

        if exhausted:
            logger.info(
                f"Should backtrack from {current_hash[:8]}: "
                f"state exhausted ({len(node.executed_actions)}/{node.total_actions})"
            )

        return exhausted

    def _get_untested_actions(
        self,
        node,
        screen_desc: ScreenDescription
    ) -> List[ItemAction]:
        """
        Get untested actions filtered by various criteria.

        Filters:
        - Skip system actions (back/home/recent_apps buttons)
        - Skip actions from external packages (systemui, launcher, etc)
        - Skip already executed actions (by coordinate signature)

        Args:
            node: ScreenNode from graph
            screen_desc: Current screen description

        Returns:
            List of untested ItemActions
        """
        untested = []
        external_count = 0

        for item in screen_desc.items:
            # Filter by package - only include items from target app
            item_package = item.view.get('package', '')
            if self.target_package and item_package:
                if item_package != self.target_package:
                    external_count += 1
                    continue

            for action in item.actions:
                # Skip system actions
                if self._is_system_action(action):
                    continue

                # Check if already executed
                action_signature = self._convert_signature_to_optimized(action.coords_for_matching)

                if action_signature not in node.executed_actions:
                    untested.append(action)

        if external_count > 0:
            logger.info(f"Filtered {external_count} external package elements")

        return untested

    def _get_all_filtered_actions(
        self,
        screen_desc: ScreenDescription
    ) -> List[ItemAction]:
        """
        Get all actions filtered by package and system action criteria.

        Unlike _get_untested_actions, this returns ALL valid actions
        regardless of execution status, for continuous exploration.

        Args:
            screen_desc: Current screen description

        Returns:
            List of all valid ItemActions (excluding system/external)
        """
        filtered = []

        for item in screen_desc.items:
            # Filter by package - only include items from target app
            item_package = item.view.get('package', '')
            if self.target_package and item_package:
                if item_package != self.target_package:
                    continue

            for action in item.actions:
                # Skip system actions
                if self._is_system_action(action):
                    continue

                filtered.append(action)

        return filtered

    def _select_least_executed_action(
        self,
        node,
        actions: List[ItemAction]
    ) -> Optional[ItemAction]:
        """
        Select action with fewest executions for continuous exploration.

        When all actions have been tested at least once, prioritizes:
        1. Filter out permanently failed actions (crash-causing)
        2. Actions with fewer execution counts (least visited first)
        3. MOP priority as tiebreaker (higher MOP = selected first)

        This enables continuous exploration until timeout, always making
        progress on less-explored paths while avoiding repeated crashes.

        Args:
            node: ScreenNode with action execution counts
            actions: List of all available actions (already tested)

        Returns:
            Action with lowest execution count, or None if all actions failed
        """
        # Filter out permanently failed actions
        safe_actions = []
        for action in actions:
            action_signature = self._convert_signature_to_optimized(action.coords_for_matching)
            if not node.is_action_failed(action_signature):
                safe_actions.append(action)
            else:
                logger.debug(f"Skipping permanently failed action: {action_signature}")

        if not safe_actions:
            logger.warning(f"All actions have permanently failed on state {node.screen_hash[:8]}")
            return None

        def sort_key(action: ItemAction):
            action_signature = self._convert_signature_to_optimized(action.coords_for_matching)
            exec_count = node.get_action_execution_count(action_signature)
            # MOP priority: DM=3, M=2, regular=1
            mop_priority = 3 if action.directly_reaches_mop else (2 if action.reaches_mop else 1)
            # Sort by: (exec_count ASC, -mop_priority DESC)
            # Lower exec_count first, then higher MOP priority
            return (exec_count, -mop_priority)

        sorted_actions = sorted(safe_actions, key=sort_key)
        return sorted_actions[0]

    def _select_priority_action(
        self,
        actions: List[ItemAction],
        screen_desc: ScreenDescription
    ) -> Optional[ItemAction]:
        """
        Select highest priority action from candidates.

        Priority order:
        1. Direct MOP ([DM]) - directly reaches monitored operation
        2. Transitive MOP ([M]) - transitively reaches MOP
        3. WTG-guided actions - lead to unvisited screens (if TransitionManager available)
        4. Untested UI elements - never interacted with
        5. Least tested elements - lowest test count

        Args:
            actions: Candidate actions
            screen_desc: Screen description for context

        Returns:
            Selected action, or None if no valid candidates
        """
        if not actions:
            return None

        # Priority 1: Direct MOP
        dm_actions = [a for a in actions if a.directly_reaches_mop]
        if dm_actions:
            logger.debug(f"Selecting [DM] action (direct MOP)")
            return dm_actions[0]

        # Priority 2: Transitive MOP
        m_actions = [a for a in actions if a.reaches_mop]
        if m_actions:
            logger.debug(f"Selecting [M] action (transitive MOP)")
            return m_actions[0]

        # Priority 3: WTG-guided actions (lead to unvisited screens)
        if self.transition_manager:
            wtg_action = self._get_wtg_guided_action(actions, screen_desc)
            if wtg_action:
                logger.debug(f"Selecting WTG-guided action (leads to unvisited screen)")
                return wtg_action

        # Priority 4: Completely untested elements
        untested_ui = []
        for action in actions:
            element_id = action.widget_id or f"coords:{action.coordinates}"
            if self.ui_coverage.is_element_untested(element_id):
                untested_ui.append(action)

        if untested_ui:
            logger.debug(f"Selecting untested UI element")
            return untested_ui[0]

        # Priority 5: Least tested element
        def get_test_count(action):
            element_id = action.widget_id or f"coords:{action.coordinates}"
            return self.ui_coverage.get_element_test_count(element_id)

        least_tested = min(actions, key=get_test_count)
        logger.debug(f"Selecting least tested element (count={get_test_count(least_tested)})")
        return least_tested

    def _get_wtg_guided_action(
        self,
        actions: List[ItemAction],
        screen_desc: ScreenDescription
    ) -> Optional[ItemAction]:
        """
        Get action guided by WTG (Window Transition Graph) analysis.

        Uses TransitionManager to find actions that lead to unvisited screens,
        prioritizing exploration of new app areas over revisiting known screens.

        Args:
            actions: Available candidate actions
            screen_desc: Current screen description

        Returns:
            Action that leads to unvisited screen, or None if no guidance available
        """
        if not self.transition_manager:
            return None

        # Get navigation guidance from TransitionManager
        guidance = self.transition_manager.get_navigation_guidance(
            current_activity=screen_desc.activity,
            screen_desc=screen_desc
        )

        if not guidance.get("has_static_guidance"):
            return None

        # Get suggested actions (mapped from WTG to current screen)
        suggested = guidance.get("suggested_actions", [])
        if not suggested:
            return None

        # Log guidance info
        unvisited_count = len([t for t in guidance.get("unvisited_targets", []) if not t.get("visited")])
        if unvisited_count > 0:
            logger.info(f"WTG guidance: {unvisited_count} unvisited screens reachable from here")

        # Match suggested actions with available actions
        for suggestion in suggested:
            action_id = suggestion.get("action_id")
            if action_id is None:
                continue

            # Find matching action in candidates
            for action in actions:
                if action.id == action_id:
                    target = suggestion.get("target_activity", "unknown")
                    logger.info(f"WTG: Selected action leading to '{target}'")
                    return action

        return None

    def _prepare_input_action(
        self,
        action: ItemAction,
        current_hash: str
    ) -> Optional[ItemAction]:
        """
        Prepare input action with test value.

        Generates next test value for the input field. Returns None if
        all values have been tested.

        Args:
            action: TEXT_CHANGE action
            current_hash: Current state hash

        Returns:
            Action with test value, or None if exhausted
        """
        element_id = action.widget_id or f"coords:{action.coordinates}"
        is_mop = action.reaches_mop or action.directly_reaches_mop

        # Get next test value
        test_value = self.value_generator.get_next_value(element_id, is_mop=is_mop, input_type="text")

        if test_value is None:
            logger.debug(f"Input field {element_id}: all variations tested")
            return None

        # Create a NEW action with the text input value
        # IMPORTANT: Do NOT mutate the original action, as it may be selected again
        # with a different test value if input variations are not exhausted
        action_with_input = action.model_copy(update={'text_input': test_value})

        logger.info(f"Input field {element_id}: testing value '{test_value[:20]}'")
        return action_with_input

    def _convert_signature_to_optimized(
        self,
        signature: Tuple[Tuple[int, int], str]
    ) -> Tuple[Tuple[int, int], str]:
        """
        Convert action signature from device space to optimized space.

        Args:
            signature: ((device_x, device_y), action_type)

        Returns:
            ((optimized_x, optimized_y), action_type)
        """
        (device_x, device_y), action_type = signature

        if self.converter:
            optimized_x, optimized_y = self.converter.device_to_optimized(device_x, device_y)
        else:
            # Fallback conversion
            optimized_x = int(device_x * 704 / 1080)
            optimized_y = int(device_y * 1248 / 1920)

        return ((optimized_x, optimized_y), action_type)

    def _is_system_action(self, action: ItemAction) -> bool:
        """
        Check if action is a system action (navigation bar, etc).

        Args:
            action: Action to check

        Returns:
            True if system action (should skip)
        """
        # Get execution coordinates
        coords = action.coordinates
        if not coords:
            # No valid coordinates - skip this action
            return True

        x, y = coords

        # Skip navigation bar (bottom ~100px)
        if y > 1800:  # Device space
            return True

        # Skip status bar (top ~100px)
        if y < 100:
            return True

        return False

    def reset(self):
        """
        Reset exploration state.

        Clears DFS stack, visited states, successor mappings, plateau history,
        input value tracking, scroll positions, and MOP coverage. Graph and UI
        coverage are managed separately.
        """
        # Reset DFS state
        self.state_stack.clear()
        self.visited_states.clear()
        self.current_depth = 0
        self.previous_hash = None
        self.scrolled_positions.clear()

        # Reset tracking components (simple and direct)
        self.successor_tracker.successors.clear()
        self.successor_tracker.coverage_cache.clear()

        self.plateau_detector.state_discovery.clear()
        self.plateau_detector.mop_execution.clear()
        self.plateau_detector.mop_methods_seen.clear()
        self.plateau_detector.total_iterations = 0
        self.plateau_detector.total_states_discovered = 0
        self.plateau_detector.total_mop_methods_executed = 0

        self.value_generator.tested_values.clear()

        self.coverage_metrics.mop_methods_reached.clear()

        logger.info("RVAgentStrategy state reset")

    def get_statistics(self):
        """
        Get comprehensive strategy statistics.

        Returns:
            Dictionary with all component statistics
        """
        stats = {
            "strategy": "rvagent",
            "depth": self.current_depth,
            "states_visited": len(self.visited_states),
            "stack_size": len(self.state_stack),
            "coverage": self.coverage_metrics.get_summary(),
            "plateau": self.plateau_detector.get_metrics(),
            "successor_tracking": self.successor_tracker.get_statistics(),
            "input_generation": self.value_generator.get_statistics(),
        }

        # Add TransitionManager stats if available
        if self.transition_manager:
            stats["wtg_guidance"] = self.transition_manager.get_exploration_summary()

        return stats
