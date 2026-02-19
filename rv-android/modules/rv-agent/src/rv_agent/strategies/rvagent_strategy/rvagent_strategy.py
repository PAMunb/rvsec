"""
Coverage-optimized depth-first exploration with successor tracking.

Implements state space exploration with:
1. Successor state tracking to re-enable actions when destination states are incomplete
2. MOP-aware action prioritization via ActionRanker
3. Plateau detection for automatic termination
4. Input field value variation generation
"""

import logging
import random
from typing import Optional, List, Set, Tuple, Dict, TYPE_CHECKING
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ItemAction
from rv_android_core.domain.widget import WidgetEventType

from rv_agent.strategies.base_strategy import ExplorationStrategy
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_agent.memory.element_id import make_element_id_from_tuple
from rv_android_core.domain.static import StaticAnalysisData

from rv_agent.strategies.rvagent_strategy.successor_tracker import SuccessorTracker
from rv_agent.strategies.rvagent_strategy.plateau_detector import PlateauDetector
from rv_agent.strategies.rvagent_strategy.input_value_generator import InputValueGenerator
from rv_agent.strategies.rvagent_strategy.coverage_metrics import CoverageMetrics
from rv_agent.strategies.rvagent_strategy.ranking import (
    ActionRanker,
    RankingContext,
    MopScorer,
    WtgScorer,
    SaturationScorer,
    ComponentPriorityScorer,
    StrengthScorer,
    SystemElementFilter,
    VisitationPenaltyScorer,
)
from rv_agent import tracking as track
from rv_agent.constants import RVAgentConstants
from rv_agent.services.coordinate_utils import device_to_optimized

if TYPE_CHECKING:
    from rv_agent.services.transition_manager import TransitionManager
    from rv_agent.config.agent_config import RVAgentConfig

logger = logging.getLogger(__name__)


class RVAgentStrategy(ExplorationStrategy):
    """
    Depth-first exploration with successor state tracking.

    ### Architectural Decisions:

    1. SUCCESSOR TRACKING (SuccessorTracker)
       Problem: Standard DFS marks actions as "done" after one execution, but some
       actions lead to states with multiple sub-options (e.g., dropdown menus).
       Solution: Track which state each action leads to. If that destination state
       has untested actions, re-enable the original action for re-execution.
       This prevents premature backtracking from states like "Settings" that lead
       to screens with many unexplored options.

    2. CONTINUOUS EXPLORATION (no "exhausted" state)
       Problem: Traditional exploration stops when all actions are tested once,
       but Android apps often have dynamic content and time-dependent behaviors.
       Solution: Never declare a state "exhausted". When all actions are tested,
       select the least-executed action and continue until timeout. This maximizes
       coverage of dynamic content and state-dependent behaviors.

    3. PRE-MARKING ACTIONS
       Problem: If the app crashes during action execution, we might retry the
       same crash-causing action indefinitely.
       Solution: Mark actions as executed BEFORE execution. If crash occurs, the
       action is already marked and won't be retried. Failed actions are tracked
       separately and filtered from future selection.

    4. MOP PRIORITIZATION
       Problem: Random exploration wastes time on UI elements that don't trigger
       monitored operations (the focus of runtime verification).
       Solution: Prioritize actions that reach MOPs (from static analysis) over
       regular UI exploration. This focuses testing effort on security-relevant
       or specification-critical code paths.

    Action prioritization: [DM] MOP > [M] MOP > WTG > untested UI > least tested

    Example - Successor Tracking:
        State A: Click "Dropdown" → State B (menu with 3 items)
        If only 1/3 items tested in State B, action in State A is re-enabled
    """

    # BACK action identifier
    BACK_ACTION_ID = 999

    # Scroll action probability
    # Scroll probability reduced from 0.3 to 0.15 and moved to AFTER untested actions
    # Scroll only triggers when all visible actions are tested, to reveal hidden content
    SCROLL_PROBABILITY = 0.15

    # System action detection thresholds (percentage of screen height)
    NAVBAR_Y_PERCENT = 0.94   # Actions below 94% of screen height are navbar
    STATUSBAR_Y_PERCENT = 0.05  # Actions above 5% of screen height are statusbar

    # System packages that render dialogs/alerts for apps
    # These should NOT be filtered out even when target_package is set,
    # because they render UI elements that are part of the app's flow
    # (e.g., permission dialogs, compatibility warnings, system alerts)
    SYSTEM_DIALOG_PACKAGES = frozenset({
        "android",                      # System dialogs, alerts, compatibility warnings
        "com.android.packageinstaller", # Permission dialogs, install prompts
        "com.android.permissioncontroller",  # Runtime permission dialogs (Android 10+)
        "com.google.android.permissioncontroller",  # Google's permission controller
    })

    def __init__(
        self,
        graph: DynamicStateGraph,
        ui_coverage: UICoverageTracker,
        config: "RVAgentConfig",
        static_data: Optional[StaticAnalysisData] = None,
        transition_manager: Optional["TransitionManager"] = None,
        coordinate_converter=None,
        device_dimensions: Optional[Tuple[int, int]] = None
    ):
        """
        Initialize RVAgent exploration strategy.

        Args:
            graph: DynamicStateGraph for state/action tracking
            ui_coverage: UICoverageTracker for UI element coverage
            config: RVAgentConfig with all calibration parameters
            static_data: Optional static analysis data (WTG, REACH)
            transition_manager: Optional TransitionManager for WTG-guided navigation
            coordinate_converter: CoordinateConverter for device/optimized space
            device_dimensions: Device screen size (width, height) - overrides config if provided

        State:
            self.successor_tracker: Tracks action-to-state mappings for re-enabling.
            self.plateau_detector: Detects exploration stagnation over sliding window.
            self.value_generator: Generates test values for input fields.
            self.coverage_metrics: Tracks MOP method execution coverage.
            self.action_ranker: Composite scorer with 8 registered scorers.
            self.previous_hash: Last state hash for transition tracking.
            self.scrolled_positions: Tracks scroll positions to avoid loops.
        """
        self.graph = graph
        self.ui_coverage = ui_coverage
        self.config = config
        self.converter = coordinate_converter
        self.static_data = static_data
        self.transition_manager = transition_manager

        # Initialize random seed for reproducibility
        if config.seed is not None:
            random.seed(config.seed)
            logger.info(f"Random seed initialized: {config.seed}")

        # Use runtime device_dimensions if provided, otherwise from config
        self.device_dimensions = device_dimensions or config.device_dimensions
        self.target_package = config.package_name

        # Gumbel-max stochastic selection parameters from config
        self.stochastic_probability = config.stochastic_probability
        self.stochastic_temperature = config.stochastic_temperature

        # Helper components with config parameters
        self.successor_tracker = SuccessorTracker(graph, config=config)
        self.plateau_detector = PlateauDetector(window_size=config.plateau_window)
        self.value_generator = InputValueGenerator(max_variations=config.max_input_variations)
        self.coverage_metrics = CoverageMetrics(graph, ui_coverage)

        # Action ranking system with configurable scorer weights
        self.action_ranker = ActionRanker(scorers=[
            # Prioritization scorers
            MopScorer(config=config),
            WtgScorer(config=config),
            SaturationScorer(config=config),
            ComponentPriorityScorer(config=config),
            StrengthScorer(coordinate_converter=coordinate_converter, config=config),
            # Penalty scorers
            SystemElementFilter(),
            VisitationPenaltyScorer(config=config),
        ])

        # Previous state for transition tracking
        self.previous_hash: Optional[str] = None

        # Scroll tracking to avoid infinite scrolling loops
        self.scrolled_positions: Set[Tuple[str, str, str]] = set()

        # Iteration counter for tracking
        self._current_iteration = 0

        logger.info(
            f"RVAgentStrategy initialized: plateau_window={config.plateau_window}, "
            f"max_variations={config.max_input_variations}, "
            f"transition_manager={'enabled' if transition_manager else 'disabled'}, "
            f"stochastic_prob={config.stochastic_probability}, temp={config.stochastic_temperature}"
        )
        logger.info(f"RVAgentStrategy: Filtering actions to package '{config.package_name}'")

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
        self._current_iteration += 1

        # 1. Plateau detection is informational only
        # WHY: We don't stop on plateau because:
        # - Dynamic content may appear later (e.g., after login, after delay)
        # - Time-dependent behaviors may trigger new states
        # - The timeout is the only reliable termination condition
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

            logger.info(f"RVAgent: New state, {node.total_actions} actions")
        else:
            node = self.graph.states[current_hash]
            node.visit_count += 1
            logger.debug(f"RVAgent: Revisiting state (visit #{node.visit_count})")

        # 3. Re-enable actions whose destination states have untested actions
        # WHY: An action like "Open Settings" should be re-enabled if the Settings
        # screen still has unexplored options. This solves the "combobox problem"
        # where clicking a dropdown once doesn't explore all menu items.
        re_enabled = self.successor_tracker.update_action_availability(current_hash)
        if re_enabled > 0:
            logger.info(f"Re-enabled {re_enabled} actions due to incomplete successors")

        # 4. Get untested actions and all filtered actions
        untested_actions = self._get_untested_actions(node, screen_desc)
        all_filtered_actions = self._get_all_filtered_actions(screen_desc)

        # Track saturation metrics
        saturation_rate = node.get_saturation_rate(threshold=2)
        track.saturation(
            iter=self._current_iteration,
            state_hash=current_hash,
            rate=saturation_rate,
            threshold=0.9  # Coverage threshold for re-enablement
        )

        logger.info(
            f"RVAgent State Analysis - {current_hash[:8]}:\n"
            f"  Total actions: {len(screen_desc.items)}\n"
            f"  Filtered actions: {len(all_filtered_actions)}\n"
            f"  Executed: {len(node.executed_actions)}\n"
            f"  Untested: {len(untested_actions)}\n"
            f"  Saturation: {saturation_rate:.1%}"
        )

        # 5. Select action based on availability
        # Priority: untested actions first, then scroll to reveal more, then least-executed
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
            # CONTINUOUS: All visible actions tested
            # Before re-testing actions, try scroll to reveal hidden content (15% prob)
            # This may expose new untested elements in lists/scrollable views
            scroll_action = self._try_generate_scroll_action(
                screen_desc, node, self.scrolled_positions, probability=0.15
            )
            if scroll_action:
                logger.info(f"RVAgent SCROLL: All visible actions tested, scrolling to reveal more content")
                return scroll_action

            # No scroll needed/possible - select LEAST-EXECUTED action
            # Algorithm continues until timeout, never stops when "exhausted"
            # Filters out permanently failed actions to avoid repeated crashes
            selected_action = self._select_least_executed_action(node, all_filtered_actions)

            # If all actions have failed, fall through to BACK
            if selected_action is None:
                logger.info(f"RVAgent: All actions failed on state {current_hash[:8]}, returning BACK")
                return self._create_back_action()

            action_signature = self._convert_signature_to_optimized(selected_action.coords_for_matching)
            exec_count = node.get_action_execution_count(action_signature)
            logger.info(f"RVAgent CONTINUOUS: Selected LEAST-EXECUTED action")
            logger.info(f"  Execution count: {exec_count} -> {exec_count + 1}")
        else:
            # No actions available (edge case) - return BACK to navigate
            logger.info(f"RVAgent: No actions available on state {current_hash[:8]}, returning BACK")
            return self._create_back_action()

        # 6. Handle input fields with value generation
        if selected_action.event == WidgetEventType.TEXT_CHANGE:
            original_action = selected_action
            selected_action = self._prepare_input_action(selected_action, current_hash)
            if not selected_action:
                # Value exhausted - mark action as executed to prevent re-selection
                action_signature = self._convert_signature_to_optimized(original_action.coords_for_matching)
                self.graph.record_action(screen_hash=current_hash, action_signature=action_signature)
                # Also mark in UI coverage tracker now that all variations are tested
                element_id = original_action.widget_id or make_element_id_from_tuple(original_action.coordinates)
                comp_class = original_action.target_view.get('class', '') if original_action.target_view else ''
                comp_type = comp_class.split('.')[-1] if comp_class else 'Unknown'
                self.ui_coverage.record_interaction(
                    element_id=element_id,
                    action_type=original_action.event.name,  # Use .name (string) not .value (int)
                    screen_hash=current_hash,
                    success=True,
                    component_type=comp_type
                )
                logger.debug("Input values exhausted, marking action as executed and selecting different action")
                # Use iterative approach instead of recursion
                untested_actions = self._get_untested_actions(node, screen_desc)
                if untested_actions:
                    selected_action = self._select_priority_action(untested_actions, screen_desc) or untested_actions[0]
                else:
                    # Fallback to BACK if no untested actions
                    return self._create_back_action()

        # 7. Pre-mark action as executed BEFORE actual execution
        # WHY: If the app crashes during execution, we won't retry the same action.
        # The action is already in executed_actions, so next iteration selects different action.
        # EXCEPTION: TEXT_CHANGE actions are marked only when all input variations are exhausted
        # (step 6), because we want to test multiple values (e.g., "test", "123", "@#$").
        if selected_action.event != WidgetEventType.TEXT_CHANGE:
            action_signature = self._convert_signature_to_optimized(selected_action.coords_for_matching)
            self.graph.record_action(screen_hash=current_hash, action_signature=action_signature)

        # NOTE: UI coverage tracking is now unified in execute_node.py (post-execution)
        # This ensures consistent tracking for both algorithm and LLM actions.

        # 8. Record MOP if applicable
        if selected_action.callback_signature:
            self.coverage_metrics.record_mop_execution(selected_action.callback_signature)

        logger.info(
            f"Selected action: {selected_action.event.name} "
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
        new_state = to_hash not in self.graph.states
        new_mop = action.callback_signature if action.callback_signature else None

        self.plateau_detector.record_iteration(
            discovered_new_state=new_state,
            new_mop_method=new_mop
        )

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

    def _create_back_action(self) -> ItemAction:
        """
        Create BACK action for navigation.

        Returns:
            ItemAction configured as BACK navigation action
        """
        return ItemAction(
            id=self.BACK_ACTION_ID,
            text="BACK",
            event=WidgetEventType.BACK,
            reaches_mop=False,
            directly_reaches_mop=False,
            target_view={"system_action": True, "class": "SystemAction_BACK"},
            coordinates=None,
            text_input=None
        )

    def _get_untested_actions(
        self,
        node,
        screen_desc: ScreenDescription
    ) -> List[ItemAction]:
        """
        Get untested actions (not yet executed) from current screen.

        Args:
            node: ScreenNode from graph
            screen_desc: Current screen description

        Returns:
            List of untested ItemActions
        """
        all_actions = self._get_all_filtered_actions(screen_desc)
        untested = []

        for action in all_actions:
            action_signature = self._convert_signature_to_optimized(action.coords_for_matching)
            if action_signature not in node.executed_actions:
                untested.append(action)

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
            item_package = item.view.get('package', '')

            # Filter by package - only include items from target app
            # BUT allow system dialog packages (they render UI as part of app flow)
            if self.target_package and item_package:
                if item_package != self.target_package:
                    # Allow system dialog packages (permission dialogs, alerts, etc.)
                    if item_package not in self.SYSTEM_DIALOG_PACKAGES:
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
        1. Actions with fewer execution counts (least visited first)
        2. MOP priority as tiebreaker (higher MOP = selected first)

        This enables continuous exploration until timeout, always making
        progress on less-explored paths.

        Args:
            node: ScreenNode with action execution counts
            actions: List of all available actions (already tested)

        Returns:
            Action with lowest execution count, or None if no actions available
        """
        if not actions:
            return None

        def sort_key(action: ItemAction):
            action_signature = self._convert_signature_to_optimized(action.coords_for_matching)
            exec_count = node.get_action_execution_count(action_signature)
            # MOP priority: DM=3, M=2, regular=1
            mop_priority = 3 if action.directly_reaches_mop else (2 if action.reaches_mop else 1)
            # Sort by: (exec_count ASC, -mop_priority DESC)
            # Lower exec_count first, then higher MOP priority
            return (exec_count, -mop_priority)

        sorted_actions = sorted(actions, key=sort_key)
        return sorted_actions[0]

    def _select_priority_action(
        self,
        actions: List[ItemAction],
        screen_desc: ScreenDescription
    ) -> Optional[ItemAction]:
        """
        Select action using ActionRanker with optional Gumbel-max stochastic selection.

        Uses stochastic_probability to decide between deterministic (select_best)
        and stochastic (select_stochastic with Gumbel-max) selection. Stochastic
        selection adds controlled randomness while preserving priority order.

        Delegates scoring to registered Scorers (7 total):
        Prioritization:
        - MopScorer: +300 (direct), +150 (transitive MOP)
        - WtgScorer: +250 (WTG-guided navigation)
        - SaturationScorer: +80 * (1 - saturation_rate)
        - ComponentPriorityScorer: +50 (buttons), +40 (toggles)
        - StrengthScorer: +50 * success_rate

        Penalties:
        - SystemElementFilter: -5000 (system UI elements)
        - VisitationPenaltyScorer: -10 * log(1 + visits)

        Args:
            actions: Candidate actions
            screen_desc: Screen description for context

        Returns:
            Selected action, or None if no valid candidates
        """
        if not actions:
            return None

        context = self._build_ranking_context(screen_desc)

        # Score all actions for tracking (with full details for calibration)
        scored_actions = []
        scored_actions_full = []
        for action in actions:
            total_score = self.action_ranker.score_action(action, context)
            coords = action.coordinates if action.coordinates else (0, 0)
            priority = "DM" if action.directly_reaches_mop else ("M" if action.reaches_mop else "")
            action_type = action.event.name if action.event else "UNKNOWN"

            # Extract component type from target_view
            comp_class = action.target_view.get('class', '') if action.target_view else ''
            comp_type = comp_class.split('.')[-1] if comp_class else 'Unknown'

            scored_actions.append((coords, total_score, priority))
            scored_actions_full.append((coords, total_score, priority, comp_type, action_type))

        # Sort by score descending
        scored_actions.sort(key=lambda x: x[1], reverse=True)
        scored_actions_full.sort(key=lambda x: x[1], reverse=True)

        # Track top 5 ranked actions (INFO level)
        track.rank(iter=self._current_iteration, actions=scored_actions[:5])

        # Track ALL actions with component type (DEBUG level - for calibration)
        track.rank_full(iter=self._current_iteration, actions=scored_actions_full)

        # Use stochastic selection based on configured probability
        use_stochastic = random.random() < self.stochastic_probability
        if use_stochastic and len(actions) > 1:
            selected = self.action_ranker.select_stochastic(
                actions, context, temperature=self.stochastic_temperature
            )
            selection_mode = "stochastic"
        else:
            selected = self.action_ranker.select_best(actions, context)
            selection_mode = "deterministic"

        if selected:
            priority = "DM" if selected.directly_reaches_mop else ("M" if selected.reaches_mop else "UI")
            coords = selected.coordinates if selected.coordinates else (0, 0)
            score = self.action_ranker.score_action(selected, context)
            action_type = selected.event.name if selected.event else "UNKNOWN"

            track.select(
                iter=self._current_iteration,
                mode=selection_mode,
                action=action_type,
                coords=coords,
                score=score,
                priority=priority
            )

        return selected

    def _build_ranking_context(self, screen_desc: ScreenDescription) -> RankingContext:
        """
        Build ranking context for Scorers.

        Args:
            screen_desc: Current screen description

        Returns:
            RankingContext with all required data for scoring
        """
        current_hash = self.graph.get_current_state_hash() if hasattr(self.graph, 'get_current_state_hash') else ""

        return RankingContext(
            screen_desc=screen_desc,
            graph=self.graph,
            ui_coverage=self.ui_coverage,
            current_state_hash=current_hash,
            visited_activities=self._get_visited_activities(),
            transition_manager=self.transition_manager,
        )

    def _get_visited_activities(self) -> Set[str]:
        """Get set of visited activity names from transition_manager or graph."""
        if self.transition_manager:
            return self.transition_manager._visited_activities
        activities = set()
        for node in self.graph.states.values():
            if node.activity:
                activities.add(node.activity)
        return activities

    def _infer_input_type(self, target_view: Optional[Dict]) -> str:
        """Infer input type from target_view data.

        Priority: password flag > hint > content_description > resource_id.
        Hint is the most reliable signal (e.g., "Email", "Password").
        """
        if not target_view:
            return "text"

        # Password field detection (from UIAutomator password flag)
        if target_view.get('password') or target_view.get('is_password'):
            return "password"

        # Check hint, content_description, and resource_id (in priority order)
        fields_to_check = [
            (target_view.get('hint') or ''),
            (target_view.get('content-desc') or target_view.get('content_description') or ''),
            (target_view.get('resource-id') or target_view.get('resource_id') or ''),
        ]

        # Pattern matching across all fields
        type_patterns = [
            ("email", ["email", "e-mail"]),
            ("phone", ["phone", "mobile", "tel"]),
            ("url", ["url", "website", "link"]),
            ("search", ["search", "query", "find"]),
            ("date", ["date", "birthday", "dob"]),
            ("time", ["time", "hour"]),
            ("number", ["number", "amount", "quantity", "price"]),
            ("zip", ["zip", "postal", "cep"]),
            ("verification_code", ["code", "otp", "verification", "pin"]),
            ("username", ["username", "user_name", "login"]),
            ("name", ["name", "nome"]),
            ("address", ["address", "endereco"]),
        ]

        for field_value in fields_to_check:
            lower = field_value.lower()
            if not lower:
                continue
            for input_type, keywords in type_patterns:
                if any(kw in lower for kw in keywords):
                    return input_type

        return "text"

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
        element_id = action.widget_id or make_element_id_from_tuple(action.coordinates)
        is_mop = action.reaches_mop or action.directly_reaches_mop

        # Infer input type from target_view
        input_type = self._infer_input_type(action.target_view)

        # Get next test value
        test_value = self.value_generator.get_next_value(element_id, is_mop=is_mop, input_type=input_type)

        if test_value is None:
            logger.debug(f"Input field {element_id}: all variations tested")
            return None

        # Create a NEW action with the text input value
        # IMPORTANT: Do NOT mutate the original action, as it may be selected again
        # with a different test value if input variations are not exhausted
        action_with_input = action.model_copy(update={'text_input': test_value})

        logger.info(f"Input field {element_id} ({input_type}): testing value '{test_value[:20]}'")
        return action_with_input

    def _convert_signature_to_optimized(
        self,
        signature: Tuple[Tuple[int, int], str]
    ) -> Tuple[Tuple[int, int], str]:
        """
        Convert action signature from device space to optimized space.

        WHY COORDINATE CONVERSION:
        The same UI element may have different pixel coordinates across:
        - Different device resolutions (1080p vs 1440p)
        - Same device with different DPI settings
        - Emulator vs physical device

        By converting to a normalized "optimized space" (704x1248), we can:
        - Match actions across sessions even if device resolution changes
        - Use screenshots resized to optimized dimensions for LLM processing
        - Maintain consistent action signatures in the state graph

        Args:
            signature: ((device_x, device_y), action_type)

        Returns:
            ((optimized_x, optimized_y), action_type)
        """
        (device_x, device_y), action_type = signature

        if self.converter:
            optimized_x, optimized_y = self.converter.device_to_optimized(device_x, device_y)
        else:
            # Fallback: use default device dimensions
            optimized_x, optimized_y = device_to_optimized(
                device_x, device_y,
                (RVAgentConstants.DEFAULT_DEVICE_WIDTH, RVAgentConstants.DEFAULT_DEVICE_HEIGHT),
                (RVAgentConstants.SCREENSHOT_TARGET_WIDTH, RVAgentConstants.SCREENSHOT_TARGET_HEIGHT)
            )

        return ((optimized_x, optimized_y), action_type)

    def _is_system_action(self, action: ItemAction) -> bool:
        """
        Check if action is a system action (navigation bar, status bar).

        Uses percentage-based thresholds to work across different screen resolutions.

        NOTE: BACK and RESTART are virtual system actions that should be ALLOWED
        for navigation purposes. They have coordinates=None but are valid actions.

        Args:
            action: Action to check

        Returns:
            True if system action (should skip)
        """
        # Allow BACK and RESTART actions - they are valid navigation actions
        target_view = action.target_view or {}
        view_class = target_view.get('class', '')
        if view_class in ('SystemAction_BACK', 'SystemAction_RESTART'):
            return False  # Don't skip these - they are valid!

        coords = action.coordinates
        if not coords:
            return True

        x, y = coords
        screen_height = self.device_dimensions[1]

        # Skip navigation bar (bottom ~6% of screen)
        if y > screen_height * self.NAVBAR_Y_PERCENT:
            return True

        # Skip status bar (top ~5% of screen)
        if y < screen_height * self.STATUSBAR_Y_PERCENT:
            return True

        return False

    def reset(self):
        """
        Reset exploration state.

        Clears DFS stack, visited states, successor mappings, plateau history,
        input value tracking, scroll positions, and MOP coverage. Graph and UI
        coverage are managed separately.
        """
        self.previous_hash = None
        self.scrolled_positions.clear()
        self._current_iteration = 0

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
        """Get comprehensive strategy statistics.

        Returns:
            Dictionary with keys:
            - "strategy" (str): Strategy name ("rvagent").
            - "depth" (int): Current DFS depth.
            - "states_visited" (int): Number of unique states visited.
            - "stack_size" (int): Current DFS stack size.
            - "coverage" (dict): MOP coverage metrics from CoverageMetrics.
            - "plateau" (dict): Plateau detection metrics from PlateauDetector.
            - "successor_tracking" (dict): Successor tracker statistics.
            - "input_generation" (dict): Input value generator statistics.
            - "wtg_guidance" (dict): TransitionManager stats (if available).
        """
        stats = {
            "strategy": "rvagent",
            "states_visited": len(self.graph.states),
            "coverage": self.coverage_metrics.get_summary(),
            "plateau": self.plateau_detector.get_metrics(),
            "successor_tracking": self.successor_tracker.get_statistics(),
            "input_generation": self.value_generator.get_statistics(),
        }

        # Add TransitionManager stats if available
        if self.transition_manager:
            stats["wtg_guidance"] = self.transition_manager.get_exploration_summary()

        return stats
