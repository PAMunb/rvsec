"""
Coverage-optimized depth-first exploration with successor tracking.

Implement state space exploration with successor state tracking to re-enable
actions when destination states are incomplete, MOP-aware action prioritization
via ActionRanker with 9 weighted scorers, and plateau detection that boosts
stochastic selection probability to break out of deterministic cycles.

The strategy never declares a state "exhausted" -- when all actions have been
tested, it selects the least-executed action and continues until timeout. This
continuous exploration maximizes coverage of dynamic content and state-dependent
behaviors in Android applications.

### Role in the System:

- Primary algorithmic exploration strategy used by algorithm_node in the
  LangGraph workflow when the decision router selects the algorithm path
- Registered in strategy_registry under the name "rvagent" and created by
  AgentFactory during agent initialization
- Works alongside LLM-based exploration in multimode (default 30% algorithm)

### Integration Points:

- Input: ScreenDescription from rv-screen-parser, StaticAnalysisData from
  rv-static-analysis, TransitionManager for WTG-guided navigation
- Output: ItemAction selected for execution by execute_node
- Dependencies: DynamicStateGraph (state tracking), UICoverageTracker (element
  coverage), ActionRanker (composite scoring), SuccessorTracker (re-enabling),
  PlateauDetector (stagnation), PathBuffer (multi-step navigation),
  RewardPropagator (reward estimation), InputValueGenerator (test values)
"""

import logging
import math
import random
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

from rv_agent import tracking as track
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.memory.element_id import make_element_id_from_tuple
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_agent.strategies.base_strategy import ExplorationStrategy
from rv_agent.strategies.rvagent_strategy.coverage_metrics import CoverageMetrics
from rv_agent.strategies.rvagent_strategy.input_value_generator import (
    InputValueGenerator,
)
from rv_agent.strategies.rvagent_strategy.path_buffer import PathBuffer
from rv_agent.strategies.rvagent_strategy.plateau_detector import PlateauDetector
from rv_agent.strategies.rvagent_strategy.ranking import (
    ActionRanker,
    ComponentPriorityScorer,
    CoverageDensityScorer,
    GradualDecayScorer,
    MopScorer,
    RankingContext,
    SaturationScorer,
    StrengthScorer,
    SystemElementFilter,
    VisitationPenaltyScorer,
    WtgScorer,
)
from rv_agent.strategies.rvagent_strategy.reward_propagator import RewardPropagator
from rv_agent.strategies.rvagent_strategy.successor_tracker import SuccessorTracker
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.widget import WidgetEventType
from rv_screen_parser.parser.screen.visitor.model import ItemAction, ScreenDescription

if TYPE_CHECKING:
    from rv_agent.config.agent_config import RVAgentConfig
    from rv_agent.services.transition_manager import TransitionManager

logger = logging.getLogger(__name__)

# Input type patterns for field inference (password flag > hint > content_desc > resource_id)
_INPUT_TYPE_PATTERNS = [
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


def _infer_input_type(target_view: Optional[Dict]) -> str:
    """Infer input field type from target_view attributes.

    Check view attributes in priority order: password flag, hint text,
    content description, resource ID. Match against _INPUT_TYPE_PATTERNS
    keywords to determine the semantic input type for value generation.

    Args:
        target_view: Widget view dictionary with UI attributes, or None.

    Returns:
        Input type string (e.g., "email", "password", "phone", "text").
        Defaults to "text" when no pattern matches or target_view is None.
    """
    if not target_view:
        return "text"
    if target_view.get("password") or target_view.get("is_password"):
        return "password"
    for field in [
        (target_view.get("hint") or ""),
        (
            target_view.get("content-desc")
            or target_view.get("content_description")
            or ""
        ),
        (target_view.get("resource-id") or target_view.get("resource_id") or ""),
    ]:
        lower = field.lower()
        if not lower:
            continue
        for input_type, keywords in _INPUT_TYPE_PATTERNS:
            if any(kw in lower for kw in keywords):
                return input_type
    return "text"


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
       regular UI exploration. This focuses testing effort on specification-critical
       code paths where monitored operations are triggered.

    Action prioritization: [DM] MOP > [M] MOP > WTG > untested UI > least tested

    Example - Successor Tracking:
        State A: Click "Dropdown" → State B (menu with 3 items)
        If only 1/3 items tested in State B, action in State A is re-enabled
    """

    # BACK action identifier
    BACK_ACTION_ID = 999

    # Max times TIER3 backtrack to the same state can fail before skipping it
    MAX_BACKTRACK_FAILURES = 3

    # Scroll action probability
    # Scroll probability reduced from 0.3 to 0.15 and moved to AFTER untested actions
    # Scroll only triggers when all visible actions are tested, to reveal hidden content
    SCROLL_PROBABILITY = 0.15

    # System action detection thresholds (percentage of screen height)
    NAVBAR_Y_PERCENT = 0.94  # Actions below 94% of screen height are navbar
    STATUSBAR_Y_PERCENT = 0.05  # Actions above 5% of screen height are statusbar

    # System packages that render dialogs/alerts for apps
    # These should NOT be filtered out even when target_package is set,
    # because they render UI elements that are part of the app's flow
    # (e.g., permission dialogs, compatibility warnings, system alerts)
    SYSTEM_DIALOG_PACKAGES = frozenset(
        {
            "android",  # System dialogs, alerts, compatibility warnings
            "com.android.packageinstaller",  # Permission dialogs, install prompts
            "com.android.permissioncontroller",  # Runtime permission dialogs (Android 10+)
            "com.google.android.permissioncontroller",  # Google's permission controller
        }
    )

    def __init__(
        self,
        graph: DynamicStateGraph,
        ui_coverage: UICoverageTracker,
        config: "RVAgentConfig",
        static_data: Optional[StaticAnalysisData] = None,
        transition_manager: Optional["TransitionManager"] = None,
        coordinate_converter=None,
        device_dimensions: Optional[Tuple[int, int]] = None,
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
            self.action_ranker: Composite scorer with registered scorers.
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
        self.value_generator = InputValueGenerator(
            max_variations=config.max_input_variations,
            mop_max_variations=config.mop_max_input_variations,
        )
        self.coverage_metrics = CoverageMetrics(graph, ui_coverage)

        # Action ranking system with configurable scorer weights
        self.action_ranker = ActionRanker(
            scorers=[
                # Prioritization scorers
                MopScorer(config=config),
                WtgScorer(config=config),
                SaturationScorer(config=config),
                ComponentPriorityScorer(config=config),
                StrengthScorer(config=config),
                GradualDecayScorer(config=config),
                CoverageDensityScorer(config=config),
                # Penalty scorers
                SystemElementFilter(),
                VisitationPenaltyScorer(config=config),
            ]
        )

        # N-step reward propagator for action value estimation
        self.reward_propagator = RewardPropagator(config=config)

        # PathBuffer for multi-step navigation (backtrack, MOP, coverage paths)
        self.path_buffer = PathBuffer(
            transition_manager=transition_manager,
            successor_tracker=self.successor_tracker,
            ui_coverage_tracker=ui_coverage,
            config=config,
        )

        # Previous state for transition tracking
        self.previous_hash: Optional[str] = None

        # Scroll tracking to avoid infinite scrolling loops
        self.scrolled_positions: Set[Tuple[str, str, str]] = set()

        # Iteration counter for tracking
        self._current_iteration = 0

        # Current state hash, set at the start of each select_next_action call.
        # Used by _build_ranking_context to pass the correct hash to scorers.
        self._current_hash: str = ""

        # Backtrack failure tracking: state_hash -> consecutive failure count.
        # When TIER3 backtrack to a state fails N times, skip that state.
        self._backtrack_failures: Dict[str, int] = {}

        # Tracks whether the current iteration discovered a new state.
        # Set in select_next_action() BEFORE get_or_create_state() adds it
        # to the graph. Used by record_transition() to pass the correct
        # discovered_new_state flag to PlateauDetector.
        self._last_is_new_state: bool = False

        logger.info(
            f"RVAgentStrategy initialized: plateau_window={config.plateau_window}, "
            f"max_variations={config.max_input_variations}, "
            f"transition_manager={'enabled' if transition_manager else 'disabled'}, "
            f"stochastic_prob={config.stochastic_probability}, temp={config.stochastic_temperature}"
        )
        logger.info(
            f"RVAgentStrategy: Filtering actions to package '{config.package_name}'"
        )

    def select_next_action(
        self, current_hash: str, screen_desc: ScreenDescription
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
        # Store current_hash for use by _build_ranking_context and other
        # internal methods that don't receive it as a parameter.
        self._current_hash = current_hash

        # _current_iteration is set externally by algorithm_node from the
        # agent loop's iteration counter, ensuring all RVTRACK logs use the
        # same iteration number as rv_agent.py's main loop.

        # 1. Plateau detection: when no progress for window_size iterations,
        # escalate by increasing stochastic probability to break out of cycles.
        # Does NOT terminate — timeout is still the only stop condition.
        if self.plateau_detector.is_plateau_reached():
            plateau_metrics = self.plateau_detector.get_metrics()
            logger.info(
                f"Plateau detected (window={plateau_metrics['window_size']}) — "
                f"increasing stochastic probability to break exploration cycle"
            )
            # Temporarily boost stochastic probability to 0.5 to inject randomness
            # and break out of deterministic cycles (restored on new state discovery)
            if self.stochastic_probability < 0.5:
                self.stochastic_probability = 0.5

        # 2. Create or update graph node
        is_new_state = current_hash not in self.graph.states
        self._last_is_new_state = is_new_state
        if is_new_state:
            node = self.graph.get_or_create_state(
                current_hash, screen_desc.activity, screen_desc
            )
            # Restore stochastic probability after plateau-induced boost
            self.stochastic_probability = self.config.stochastic_probability
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
        saturation_rate = node.get_saturation_rate()
        track.saturation(
            iter=self._current_iteration,
            state_hash=current_hash,
            rate=saturation_rate,
            threshold=0.9,  # Coverage threshold for re-enablement
        )

        logger.info(
            f"RVAgent State Analysis - {current_hash[:8]}:\n"
            f"  Total actions: {len(screen_desc.items)}\n"
            f"  Filtered actions: {len(all_filtered_actions)}\n"
            f"  Executed: {len(node.executed_actions)}\n"
            f"  Untested: {len(untested_actions)}\n"
            f"  Saturation: {saturation_rate:.1%}"
        )

        # 5. Select action using tiered priority
        # Tier 1: PathBuffer (buffered multi-step path in progress)
        # Tier 2: Untested actions
        # Tier 3: Proactive backtracking (saturation >= threshold)
        # Tier 4: Scored continuous mode (ActionRanker on all actions)
        # Tier 5: BACK fallback
        selected_action = None

        # TIER 1 - BUFFERED PATH: Return next action from active path buffer
        if self.path_buffer.is_active:
            buffered = self.path_buffer.get_next_action()
            if buffered:
                selected_action = buffered
                track.strategy(
                    iter=self._current_iteration,
                    mode="tier1_buffer",
                    action_type=str(buffered.event),
                    reason=f"remaining={self.path_buffer.remaining_steps}",
                )
                logger.info(
                    f"RVAgent TIER1: Using buffered action "
                    f"({self.path_buffer.remaining_steps} remaining)"
                )
                # Skip directly to pre-mark and return
                # (buffered actions are already validated by the planner)

        if not selected_action and untested_actions:
            # TIER 2 - UNTESTED: Select priority action from untested
            selected_action = self._select_priority_action(
                untested_actions, screen_desc
            )
            if selected_action:
                track.strategy(
                    iter=self._current_iteration,
                    mode="tier2_untested",
                    action_type=str(selected_action.event),
                    reason="priority_untested",
                )
                logger.info("RVAgent TIER2: Selected UNTESTED action")
            else:
                selected_action = untested_actions[0]
                track.strategy(
                    iter=self._current_iteration,
                    mode="tier2_untested",
                    action_type=str(selected_action.event),
                    reason="fallback_first",
                )
                logger.info("RVAgent TIER2: Fallback to first untested action")

        elif self.should_backtrack(current_hash):
            # TIER 3 - PROACTIVE BACKTRACKING: saturation >= threshold
            # Try planning paths: coverage > MOP > backtrack (C > B > A)
            # Skip planning if cooling down after a resolution failure (D8)
            if not self.path_buffer.is_active and not self.path_buffer.is_cooling_down:
                planned = (
                    self.path_buffer.plan_coverage_path(current_hash)
                    or self.path_buffer.plan_mop_path(
                        screen_desc.activity,
                        self._get_mop_data(),
                        possible_actions=list(screen_desc.get_all_actions()),
                        current_iteration=self._current_iteration,
                    )
                    or self.path_buffer.plan_backtrack_path(current_hash)
                )
                if planned:
                    buffered = self.path_buffer.get_next_action()
                    if buffered:
                        selected_action = buffered
                        track.strategy(
                            iter=self._current_iteration,
                            mode="tier3_backtrack",
                            action_type=str(buffered.event),
                            reason="proactive_backtrack",
                        )
                        logger.info("RVAgent TIER3: Using path buffer action")

            if not selected_action:
                if all_filtered_actions:
                    # Path plans failed or cooling down — fall through to Tier 4
                    # instead of forcing RESTART (D8). Tier 4 uses score decay to
                    # select the least-explored action on the current screen.
                    logger.info(
                        f"RVAgent TIER3: Saturation {saturation_rate:.1%} >= threshold, "
                        f"no path plan — falling through to Tier 4"
                    )
                else:
                    # No actions available at all — RESTART is the only option
                    logger.info(
                        f"RVAgent TIER3: Saturation {saturation_rate:.1%} >= threshold, "
                        f"no path plan and no actions — forcing RESTART"
                    )
                    track.strategy(
                        iter=self._current_iteration,
                        mode="tier3_restart",
                        action_type="RESTART_APP",
                        reason="saturated_no_path_no_actions",
                    )
                    return self._create_restart_action()

        if not selected_action and all_filtered_actions:
            # TIER 4 - SCORED CONTINUOUS: All visible actions tested
            # Try scroll to reveal hidden content (15% prob)
            scroll_action = self._try_generate_scroll_action(
                screen_desc,
                node,
                self.scrolled_positions,
                probability=self.config.scroll_probability,
            )
            if scroll_action:
                logger.info("RVAgent SCROLL: scrolling to reveal more content")
                return scroll_action

            # Select action using scored selection with execution-count decay.
            # Tier 4: all actions tested, so MopScorer applies at full weight (INV-AGT-39).
            # Score decay: effective_score = base_score / (1 + log2(execution_count))
            # prevents the same high-score action from being selected hundreds of times.
            selected_action = self._select_with_score_decay(
                all_filtered_actions, screen_desc, node
            )

            if selected_action is None:
                logger.info(
                    f"RVAgent: All actions scored zero on {current_hash[:8]}, returning BACK"
                )
                return self._create_back_action()

            # Action signatures use device-space coordinates (INV-AGT-40)
            exec_count = node.get_action_execution_count(
                selected_action.coords_for_matching
            )
            track.strategy(
                iter=self._current_iteration,
                mode="tier4_scored",
                action_type=str(selected_action.event),
                reason=f"count={exec_count}",
            )
            logger.info(f"RVAgent TIER4: Selected SCORED action (count: {exec_count})")

        if not selected_action:
            # TIER 5 - No actions available
            logger.info(
                f"RVAgent: No actions available on state {current_hash[:8]}, returning BACK"
            )
            return self._create_back_action()

        # 6. Handle input fields with value generation
        if selected_action.event == WidgetEventType.TEXT_CHANGE:
            original_action = selected_action
            selected_action = self._prepare_input_action(selected_action, current_hash)
            if not selected_action:
                # Value exhausted - mark action as executed to prevent re-selection
                # Action signatures use device-space coordinates (INV-AGT-40)
                widget_cls = (
                    original_action.target_view.get("class", "")
                    if original_action.target_view
                    else ""
                )
                self.graph.record_action(
                    screen_hash=current_hash,
                    action_signature=original_action.coords_for_matching,
                    widget_class=widget_cls,
                )
                # Also mark in UI coverage tracker now that all variations are tested
                element_id = original_action.widget_id or make_element_id_from_tuple(
                    original_action.coordinates
                )
                comp_class = (
                    original_action.target_view.get("class", "")
                    if original_action.target_view
                    else ""
                )
                comp_type = comp_class.split(".")[-1] if comp_class else "Unknown"
                self.ui_coverage.record_interaction(
                    element_id=element_id,
                    action_type=original_action.event.name,  # Use .name (string) not .value (int)
                    screen_hash=current_hash,
                    success=True,
                    component_type=comp_type,
                )
                logger.debug(
                    "Input values exhausted, marking action as executed and selecting different action"
                )
                # Use iterative approach instead of recursion
                untested_actions = self._get_untested_actions(node, screen_desc)
                if untested_actions:
                    selected_action = (
                        self._select_priority_action(untested_actions, screen_desc)
                        or untested_actions[0]
                    )
                else:
                    # Fallback to BACK if no untested actions
                    return self._create_back_action()

        # 7. Pre-mark action as executed BEFORE actual execution
        # WHY: If the app crashes during execution, we won't retry the same action.
        # The action is already in executed_actions, so next iteration selects different action.
        # EXCEPTION: TEXT_CHANGE actions are marked only when all input variations are exhausted
        # (step 6), because we want to test multiple values (e.g., "test", "123", "@#$").
        if selected_action.event != WidgetEventType.TEXT_CHANGE:
            # Pre-mark uses device-space coordinates (INV-AGT-40)
            premark_widget_cls = (
                selected_action.target_view.get("class", "")
                if selected_action.target_view
                else ""
            )
            self.graph.record_action(
                screen_hash=current_hash,
                action_signature=selected_action.coords_for_matching,
                widget_class=premark_widget_cls,
            )

        # NOTE: UI coverage tracking is now unified in execute_node.py (post-execution)
        # This ensures consistent tracking for both algorithm and LLM actions.

        # 8. Record MOP if applicable
        if selected_action.callback_signature:
            self.coverage_metrics.record_mop_execution(
                selected_action.callback_signature
            )

        logger.info(
            f"Selected action: {selected_action.event.name} "
            f"(priority="
            f"{'[DM]' if selected_action.directly_reaches_mop else '[M]' if selected_action.reaches_mop else 'UI'})"
        )

        return selected_action

    def record_transition(self, from_hash: str, to_hash: str, action_signature: tuple):
        """
        Record state transition and update tracking components.

        Accepts action_signature as a tuple ((x, y), action_type) directly,
        matching the one-iteration offset fix where execute_node passes
        previous_action_signature instead of the current ItemAction.

        Args:
            from_hash: Source state hash
            to_hash: Destination state hash
            action_signature: Device-space action signature ((x, y), action_type)
        """
        # Update plateau detector for ALL iterations (including self-loops)
        # to correctly detect stagnation. The flag was stored by
        # select_next_action() instead of checking `to_hash not in
        # self.graph.states`, because by the time record_transition() runs
        # the state was already added to the graph by get_or_create_state().
        new_state = self._last_is_new_state
        self.plateau_detector.record_iteration(
            discovered_new_state=new_state, new_mop_method=None
        )
        track.strategy(
            iter=self._current_iteration,
            mode="plateau",
            action_type="record",
            reason=f"discovered_new={new_state}",
        )

        # Self-loop guard: skip graph/successor recording for same-state
        # transitions — they provide zero exploration benefit and pollute
        # the successor re-enable mechanism.
        if from_hash == to_hash:
            track.self_loop_guard(
                iter=0,
                state_hash=from_hash,
                action_sig=str(action_signature),
            )
            return

        # Record in graph
        coords = action_signature[0]
        action_type = action_signature[1]
        self.graph.record_action_to_trace({"action": action_type, "coords": coords})
        self.graph.record_transition(from_hash, to_hash)

        # Update successor tracker (enables action re-enabling logic)
        self.successor_tracker.record_successor(from_hash, action_signature, to_hash)

        self.previous_hash = from_hash

        logger.debug(f"Transition recorded: {from_hash[:8]} → {to_hash[:8]}")

    def should_backtrack(self, current_hash: str) -> bool:
        """
        Determine if backtracking needed from current state.

        Uses saturation threshold: backtrack when saturation_rate >= threshold.
        Saturation measures how many actions have been executed 2+ times.

        Logic:
        1. Check incomplete successors - if found, DON'T backtrack
        2. Check saturation against config threshold (default 0.8)

        Args:
            current_hash: Current state hash

        Returns:
            True if should backtrack
        """
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

        # Check saturation against threshold
        saturation = node.get_saturation_rate()
        should = saturation >= self.config.backtrack_saturation_threshold

        if should:
            logger.info(
                f"Should backtrack from {current_hash[:8]}: "
                f"saturation {saturation:.1%} >= threshold {self.config.backtrack_saturation_threshold:.1%}"
            )

        return should

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
            text_input=None,
        )

    def _create_restart_action(self) -> ItemAction:
        """
        Create RESTART_APP action to reset to app entry point.

        Used by TIER3 when all path plans fail and state is saturated,
        to escape oscillation between fully-explored states.

        Returns:
            ItemAction configured as RESTART_APP action with package name
        """
        return ItemAction(
            id=self.BACK_ACTION_ID,
            text=f"RESTART_APP:{self.target_package}",
            event=WidgetEventType.RESTART,
            reaches_mop=False,
            directly_reaches_mop=False,
            target_view={
                "system_action": True,
                "class": "SystemAction_RESTART",
                "package_name": self.target_package,
            },
            coordinates=None,
            text_input=None,
        )

    def _get_untested_actions(
        self, node, screen_desc: ScreenDescription
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
            # Action signatures use device-space coordinates (INV-AGT-40)
            if action.coords_for_matching not in node.executed_actions:
                untested.append(action)

        return untested

    def _get_all_filtered_actions(
        self, screen_desc: ScreenDescription
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
            item_package = item.view.get("package", "")

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
        self, node, actions: List[ItemAction]
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
            # Action signatures use device-space coordinates (INV-AGT-40)
            exec_count = node.get_action_execution_count(action.coords_for_matching)
            # MOP priority: DM=3, M=2, regular=1
            mop_priority = (
                3 if action.directly_reaches_mop else (2 if action.reaches_mop else 1)
            )
            # Sort by: (exec_count ASC, -mop_priority DESC)
            # Lower exec_count first, then higher MOP priority
            return (exec_count, -mop_priority)

        sorted_actions = sorted(actions, key=sort_key)
        return sorted_actions[0]

    def _select_priority_action(
        self,
        actions: List[ItemAction],
        screen_desc: ScreenDescription,
        force_no_untested_inputs: bool = False,
    ) -> Optional[ItemAction]:
        """
        Select action using ActionRanker with optional Gumbel-max stochastic selection.

        Uses stochastic_probability to decide between deterministic (select_best)
        and stochastic (select_stochastic with Gumbel-max) selection. Stochastic
        selection adds controlled randomness while preserving priority order.

        Delegates scoring to registered Scorers (9 total):
        Prioritization:
        - MopScorer: +500 (direct), +300 (transitive), deferred on forms
        - WtgScorer: +150 (WTG-guided navigation)
        - SaturationScorer: +100 * (1 - saturation_rate)
        - ComponentPriorityScorer: +50 (buttons), +40 (toggles)
        - StrengthScorer: +50 * success_rate
        - GradualDecayScorer: 200 * 0.7^visits (0 after 5)
        - CoverageDensityScorer: 200 * coverage_gap

        Penalties:
        - SystemElementFilter: -5000 (system UI elements)
        - VisitationPenaltyScorer: -15 * log(1 + visits)

        Args:
            actions: Candidate actions
            screen_desc: Screen description for context
            force_no_untested_inputs: Override has_untested_inputs to False (Tier 4)

        Returns:
            Selected action, or None if no valid candidates
        """
        if not actions:
            return None

        context = self._build_ranking_context(screen_desc)
        if force_no_untested_inputs:
            context.has_untested_inputs = False

        # Score all actions for tracking (with full details for calibration)
        scored_actions = []
        scored_actions_full = []
        for action in actions:
            total_score = self.action_ranker.score_action(action, context)
            coords = action.coordinates if action.coordinates else (0, 0)
            priority = (
                "DM"
                if action.directly_reaches_mop
                else ("M" if action.reaches_mop else "")
            )
            action_type = action.event.name if action.event else "UNKNOWN"

            # Extract component type from target_view
            comp_class = (
                action.target_view.get("class", "") if action.target_view else ""
            )
            comp_type = comp_class.split(".")[-1] if comp_class else "Unknown"

            scored_actions.append((coords, total_score, priority))
            scored_actions_full.append(
                (coords, total_score, priority, comp_type, action_type)
            )

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
            priority = (
                "DM"
                if selected.directly_reaches_mop
                else ("M" if selected.reaches_mop else "UI")
            )
            coords = selected.coordinates if selected.coordinates else (0, 0)
            score = self.action_ranker.score_action(selected, context)
            action_type = selected.event.name if selected.event else "UNKNOWN"

            track.select(
                iter=self._current_iteration,
                mode=selection_mode,
                action=action_type,
                coords=coords,
                score=score,
                priority=priority,
            )

        return selected

    def _select_with_score_decay(
        self,
        actions: List[ItemAction],
        screen_desc: ScreenDescription,
        node,
    ) -> Optional[ItemAction]:
        """
        Select action with execution-count score decay for TIER4.

        Applies effective_score = base_score / (1 + log2(execution_count))
        to prevent the same high-score action from monopolizing selection.
        Without decay, a CLICK with score 825 can be selected 200+ times
        consecutively because it always has the highest base score.

        Args:
            actions: All filtered actions (tested + untested)
            screen_desc: Screen description for context
            node: ScreenNode with execution counts

        Returns:
            Action with highest decayed score, or None if all score zero
        """
        if not actions:
            return None

        # Filter out system actions (BACK, RESTART) from Tier 4.
        # Tier 4 explores real UI widgets; BACK is the Tier 5 fallback.
        # System actions accumulate inflated scores from CoverageDensityScorer
        # (unknown destination bonus), GradualDecayScorer (fresh decay), and
        # StrengthScorer (high success rate), outscoring real widgets.
        real_actions = [
            a for a in actions if not (a.target_view or {}).get("system_action")
        ]
        filtered_count = len(actions) - len(real_actions)
        if filtered_count > 0:
            track._counters["system_action_filtered"] += filtered_count
        if not real_actions:
            return None

        context = self._build_ranking_context(screen_desc)
        context.has_untested_inputs = False  # Tier 4 semantics

        best_action = None
        best_decayed_score = float("-inf")

        for action in real_actions:
            base_score = self.action_ranker.score_action(action, context)
            # Action signatures use device-space coordinates (INV-AGT-40)
            exec_count = node.get_action_execution_count(action.coords_for_matching)

            # Score decay: reduce attractiveness as execution count grows.
            # Positive scores are divided (smaller = less attractive).
            # Negative scores are multiplied (more negative = less attractive).
            if exec_count > 0:
                decay_factor = 1 + math.log2(exec_count)
                if base_score >= 0:
                    decayed_score = base_score / decay_factor
                else:
                    decayed_score = base_score * decay_factor
            else:
                decayed_score = base_score

            if decayed_score > best_decayed_score:
                best_decayed_score = decayed_score
                best_action = action

        return best_action

    def _build_ranking_context(self, screen_desc: ScreenDescription) -> RankingContext:
        """
        Build ranking context for Scorers.

        Args:
            screen_desc: Current screen description

        Returns:
            RankingContext with all required data for scoring
        """
        return RankingContext(
            screen_desc=screen_desc,
            graph=self.graph,
            ui_coverage=self.ui_coverage,
            current_state_hash=self._current_hash,
            visited_activities=self._get_visited_activities(),
            transition_manager=self.transition_manager,
            has_untested_inputs=self._has_untested_inputs(screen_desc),
            successor_tracker=self.successor_tracker,
        )

    def _has_untested_inputs(self, screen_desc: ScreenDescription) -> bool:
        """Check if the current screen has EditText actions with remaining test values.

        Args:
            screen_desc: Current screen description with all parsed actions.

        Returns:
            True if any EditText action has remaining input variations to test.
        """
        for action in screen_desc.get_all_actions():
            target_class = (
                action.target_view.get("class", "") if action.target_view else ""
            )
            if "EditText" not in target_class:
                continue
            element_id = action.widget_id or (
                make_element_id_from_tuple(action.coordinates)
                if action.coordinates
                else None
            )
            is_mop = action.reaches_mop or action.directly_reaches_mop
            if element_id and self.value_generator.has_remaining_values(
                element_id, is_mop=is_mop
            ):
                return True
        return False

    def record_backtrack_failure(self, target_hash: str) -> None:
        """Record a failed backtrack attempt to a target state.

        When the same target accumulates MAX_BACKTRACK_FAILURES failures,
        TIER3 will skip it in future path planning.

        Args:
            target_hash: State hash of the backtrack target that failed.
        """
        count = self._backtrack_failures.get(target_hash, 0) + 1
        self._backtrack_failures[target_hash] = count
        logger.info(
            f"Backtrack failure to {target_hash[:8]}: "
            f"{count}/{self.MAX_BACKTRACK_FAILURES}"
        )

    def _get_mop_data(self):
        """Get MOP data from static analysis for path planning."""
        return self.static_data

    def _get_visited_activities(self) -> Set[str]:
        """Get set of visited activity names from transition_manager or graph."""
        if self.transition_manager:
            return self.transition_manager._visited_activities
        activities = set()
        for node in self.graph.states.values():
            if node.activity:
                activities.add(node.activity)
        return activities

    def _prepare_input_action(
        self, action: ItemAction, current_hash: str
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

        # Infer input type from target_view (password flag > hint > content_desc > resource_id)
        input_type = _infer_input_type(action.target_view)

        # Get next test value
        test_value = self.value_generator.get_next_value(
            element_id, is_mop=is_mop, input_type=input_type
        )

        if test_value is None:
            logger.debug(f"Input field {element_id}: all variations tested")
            return None

        # Create a NEW action with the text input value
        # IMPORTANT: Do NOT mutate the original action, as it may be selected again
        # with a different test value if input variations are not exhausted
        action_with_input = action.model_copy(update={"text_input": test_value})

        logger.info(
            f"Input field {element_id} ({input_type}): testing value '{test_value[:20]}'"
        )
        return action_with_input

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
        view_class = target_view.get("class", "")
        if view_class in ("SystemAction_BACK", "SystemAction_RESTART"):
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

        Clear successor mappings, plateau history, input value tracking,
        scroll positions, backtrack failure counts, and MOP coverage.
        Graph and UI coverage are managed separately.
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

        # Reset gh26 state
        self._backtrack_failures.clear()
        self.stochastic_probability = self.config.stochastic_probability

        logger.info("RVAgentStrategy state reset")

    def get_statistics(self):
        """Get comprehensive strategy statistics.

        Returns:
            Dictionary with keys:
            - "strategy" (str): Strategy name ("rvagent").
            - "states_visited" (int): Number of unique states visited.
            - "coverage" (dict): MOP coverage metrics from CoverageMetrics.
            - "plateau" (dict): Plateau detection metrics from PlateauDetector.
            - "successor_tracking" (dict): Successor tracker statistics.
            - "input_generation" (dict): Input value generator statistics.
            - "wtg_guidance" (dict): TransitionManager stats (present only
                when transition_manager is available).
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
