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
import time
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

from rv_agent import tracking as track
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.memory.element_id import make_element_id_from_tuple
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_agent.strategies.base_strategy import ExplorationStrategy
from rv_agent.strategies.rvagent_strategy.coverage_metrics import CoverageMetrics
from rv_agent.strategies.rvagent_strategy.input_value_generator import (
    InputValueGenerator,
    infer_input_type,
)
from rv_agent.strategies.rvagent_strategy.path_buffer import PathBuffer
from rv_agent.strategies.rvagent_strategy.plateau_detector import PlateauDetector
from rv_agent.metrics.step_trace import (
    attribute_decision_source,
    scorer_boosts,
)
from rv_agent.strategies.rvagent_strategy.ranking import (
    RankingContext,
    ScoringPipeline,
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

# Maximum labels the ±2 containment lookup feeds to type inference, and the pixel
# radius within which a text label counts as "near" the input widget. The radius
# is a spatial proxy for the ±2 hierarchy containment: in a form, the field label
# sits directly above or beside its input, so the nearest labels are its siblings.
_MAX_NEARBY_LABELS = 2
_NEARBY_LABEL_RADIUS_PX = 400


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

        # Seeded RNG threaded through every stochastic choice (INV-AGT-53): the
        # stochastic-vs-deterministic mode draw in _select_priority_action and
        # the Gumbel-max sampling in ActionRanker (passed to from_config below).
        # random.Random(None) seeds from system entropy, so an unset seed stays
        # non-reproducible — the documented base behavior. seed is arm-neutral
        # (a shared fair-test control), so pure_mode does NOT zero it.
        self._rng = random.Random(config.seed)
        if config.seed is not None:
            logger.info(f"Random seed initialized: {config.seed}")

        # Use runtime device_dimensions if provided, otherwise from config
        self.device_dimensions = device_dimensions or config.device_dimensions
        self.target_package = config.package_name

        # Gumbel-max stochastic selection parameters.
        # stochastic_probability controls how often we use Gumbel-max sampling
        # instead of deterministic argmax. This prevents the agent from always
        # selecting the highest-scored action, which causes deterministic cycles.
        # stochastic_temperature controls the "randomness spread" of Gumbel noise:
        # higher temperature = more uniform selection, lower = closer to argmax.
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

        # Action ranking system assembled from config by ScoringPipeline --
        # the single assembly point for scorers (INV-AGT-42). The pipeline
        # applies the pure_mode kill-switch, selects the scorers enabled for
        # this arm, and logs the composition as one [RV-ARCH] audit line.
        # Scores are additive: ActionRanker sums each enabled scorer's score.
        # The seeded RNG is threaded in so Gumbel-max sampling is reproducible.
        self.action_ranker = ScoringPipeline.from_config(config, rng=self._rng)

        # N-step reward propagator for action value estimation.
        # When positive events occur (new state discovered, MOP triggered),
        # rewards propagate backward through the last N=5 actions with gamma
        # discounting. This teaches the agent which action sequences lead to
        # valuable outcomes. Cumulative rewards are clamped to [-15, +15].
        self.reward_propagator = RewardPropagator(config=config)

        # PathBuffer for multi-step navigation (backtrack, MOP, coverage paths).
        # Stores a pre-planned sequence of actions and dispenses one per iteration.
        # Three planning strategies: A (backtrack to unsaturated ancestor),
        # B (navigate to MOP-rich activity via WTG), C (coverage-directed).
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

        # BACK/MENU consecutive-pick cap counter (INV-AGT-51). Counts how many
        # BACK decisions have been returned in a row; reset by any non-BACK
        # decision. Only consulted when config.back_menu_pick_cap > 0.
        self._consecutive_back_menu: int = 0

        # E-mín launcher dose state (INV-AGT-47 dose control). All three are
        # consulted only when config.trigger_mop_first is set (the launcher gate).
        #   _launch_denylist: activities whose launch failed — never re-launched
        #                     in this run (Scenario "Failed Launch Enters Denylist").
        #   _launch_count:    direct launches dispatched this run, capped by
        #                     config.launch_cap (Scenario "Per-Run Launch Cap").
        #   _steps_since_launch: cadence counter; the launcher fires once every
        #                     config.launch_cadence selection steps.
        self._launch_denylist: Set[str] = set()
        self._launch_count: int = 0
        self._steps_since_launch: int = 0

        # Per-step decision-source attribution (fair-test E, INV-AGT-52). The
        # last attributed source and its boosts are recomputed at each scored
        # selection. The optional StepTraceWriter is attached by the agent via
        # enable_step_trace when a trace path is configured; _trace_start anchors
        # the wall-clock offset written as clock= on each row.
        self.last_decision_source: str = "base"
        self._last_boosts: Dict[str, float] = {}
        self._step_trace = None
        self._trace_start: float = time.monotonic()

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

        # Foreign-activity guard (INV-AGT-51): when the foreground activity is
        # foreign to the target package, escape instead of ranking/executing the
        # foreign screen's widgets. Off by default (byte-identical to base).
        if self.config.foreign_activity_guard and self._is_foreign_foreground(
            screen_desc
        ):
            foreign_pkg = self._foreground_package(screen_desc)
            track.foreign_activity_escape(
                iter=self._current_iteration,
                activity=screen_desc.activity,
                package=foreign_pkg,
            )
            logger.info(
                f"Foreign-activity guard: escaping foreign foreground "
                f"'{screen_desc.activity}' (package={foreign_pkg})"
            )
            # Raw escape BACK — independent of the BACK/MENU pick cap (port of
            # APE-RV: the foreign-guard BACK is a raw key event, not a
            # discretionary pick, so it never feeds the cap counter).
            return self._create_back_action()

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

        # 5. Select action using 5-tier priority cascade.
        # Tiers are evaluated in order; the first tier that produces an action wins.
        # This ordering ensures: active plans complete (T1), fresh actions get tried
        # (T2), saturated states trigger escape plans (T3), tested actions get
        # revisited with score decay (T4), and BACK is the last resort (T5).
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
            # TIER 3 - PROACTIVE BACKTRACKING: saturation >= threshold.
            # Instead of continuing to re-execute tested actions on this screen,
            # plan a multi-step path to escape to a more productive state.
            # Strategy priority: C (coverage-directed) > B (MOP-directed) > A (ancestor).
            # Cooling down prevents rapid re-planning after a failed resolution (D8).
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
                    return self._apply_back_menu_cap(self._create_restart_action())

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
                return self._apply_back_menu_cap(scroll_action)

            # Select action using scored selection with logarithmic execution-count decay.
            # Tier 4 runs when all visible actions have been tested at least once.
            # Without decay, a CLICK with score 825 (from MOP + component priority)
            # would be selected 200+ times consecutively. The log2 decay formula
            # ensures gradual score reduction: after 8 executions, effective score
            # is reduced to ~25% of base score, allowing lower-scored actions to win.
            selected_action = self._select_with_score_decay(
                all_filtered_actions, screen_desc, node
            )

            if selected_action is None:
                logger.info(
                    f"RVAgent: All actions scored zero on {current_hash[:8]}, returning BACK"
                )
                return self._apply_back_menu_cap(self._create_back_action())

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
            return self._apply_back_menu_cap(self._create_back_action())

        # 6. Handle input fields with value generation.
        # TEXT_CHANGE actions (EditText fields) are tested with multiple values
        # (e.g., valid email, empty string, special characters, long text) to
        # maximize code path coverage. Each input field gets up to max_variations
        # (11 for MOP-reaching fields, fewer for regular fields).
        if selected_action.event == WidgetEventType.TEXT_CHANGE:
            original_action = selected_action
            selected_action = self._prepare_input_action(
                selected_action, current_hash, screen_desc
            )
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
                    return self._apply_back_menu_cap(self._create_back_action())

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
            f"{'[DM]' if selected_action.directly_reaches_target else '[M]' if selected_action.reaches_target else 'UI'})"
        )

        return self._apply_back_menu_cap(selected_action)

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
        # Update plateau detector for ALL iterations (including self-loops).
        # The "new state" flag is stored by select_next_action() BEFORE
        # get_or_create_state() adds it to the graph. If we checked
        # `to_hash not in self.graph.states` here, it would always be False
        # because the state was already added earlier in the same iteration.
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

        # Self-loop guard: skip graph/successor recording for same-state transitions.
        # Without this guard, actions that don't change the screen (e.g., clicking
        # a disabled button) would create self-loop edges in the graph AND poison
        # the successor tracker, causing the action to be re-enabled endlessly
        # (since its "destination" state always has untested actions -- itself).
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
            reaches_target=False,
            directly_reaches_target=False,
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
            reaches_target=False,
            directly_reaches_target=False,
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

            # Filter by package - only include items from target app.
            # System dialog packages (e.g., permission dialogs, compatibility warnings)
            # are allowed through because they are part of the app's user flow,
            # even though they render under a different package name.
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
                3 if action.directly_reaches_target else (2 if action.reaches_target else 1)
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
                if action.directly_reaches_target
                else ("M" if action.reaches_target else "")
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

        # Stochastic vs deterministic selection.
        # Gumbel-max sampling adds noise proportional to temperature, making
        # lower-ranked actions occasionally win. This breaks deterministic cycles
        # (e.g., always clicking the same high-score button) while still
        # respecting the general priority order. Probability is boosted
        # to 0.5 during plateau detection to inject more randomness.
        use_stochastic = self._rng.random() < self.stochastic_probability
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
                if selected.directly_reaches_target
                else ("M" if selected.reaches_target else "UI")
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

            # Attribute exactly one decision_source to this scored decision
            # (INV-AGT-52) and record the per-step trace row. Precedence
            # mop > wtg > menu > form > coverage; base when no steering scorer
            # contributed (the pure arm always attributes base).
            self._last_boosts = scorer_boosts(
                selected, context, self.action_ranker.scorers
            )
            self.last_decision_source = attribute_decision_source(
                selected, context, self.action_ranker.scorers
            )
            self._write_trace_row(
                screen_desc, context.current_state_hash, selected, action_type
            )

        return selected

    def enable_step_trace(self, writer) -> None:
        """Attach a StepTraceWriter and reset the wall-clock origin.

        Called by the agent when ``metrics_output_dir`` is configured. Until
        attached, attribution is still computed (``last_decision_source``) but no
        CSV rows are written.
        """
        self._step_trace = writer
        self._trace_start = time.monotonic()

    def _write_trace_row(
        self,
        screen_desc: ScreenDescription,
        state_hash: str,
        selected: ItemAction,
        action_type: str,
    ) -> None:
        """Write one attribution row to the step-trace CSV, if a writer is attached."""
        if self._step_trace is None:
            return
        try:
            clock_ms = int((time.monotonic() - self._trace_start) * 1000)
            coords = selected.coordinates if selected.coordinates else (0, 0)
            self._step_trace.write_row(
                step=self._current_iteration,
                clock_ms=clock_ms,
                activity=getattr(screen_desc, "activity", "") or "",
                state=state_hash or "",
                action=f"{action_type}@{coords}",
                decision_source=self.last_decision_source,
                boosts=self._last_boosts,
            )
        except Exception as e:
            logger.warning(f"Failed to write step-trace row: {e}")

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
            # This asymmetry ensures both positive and negative scores become
            # "less desirable" with more executions. Example: score=800, count=8
            # -> 800 / (1 + 3) = 200. Score=-100, count=8 -> -100 * 4 = -400.
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
            is_mop = action.reaches_target or action.directly_reaches_target
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

    def order_activity_launch_queue(self, activities: List[str]) -> List[str]:
        """
        Order the activity launch queue MOP-first (E-mín, INV-AGT-47).

        Port of ``SataAgent.selectTriggerCandidate`` ordering semantics: when
        ``trigger_mop_first`` is set, activities that reach a monitored operation
        (``TransitionManager.activity_has_mop`` — the A′-augmented predicate) are
        launched before all others. The partition is stable, so relative order
        within the MOP group and within the non-MOP group is unchanged. With the
        flag off (or no ``TransitionManager``), the queue is returned untouched.

        Activities are launched through the normal launcher; this ordering never
        uses component-trigger intents (those dispatch non-activity components).

        Args:
            activities: The activity launch queue, in its natural order.

        Returns:
            A new list ordered MOP-first when ``trigger_mop_first`` is set,
            otherwise a copy of the input order.
        """
        if not self.config.trigger_mop_first or not self.transition_manager:
            return list(activities)

        mop_first: List[str] = []
        rest: List[str] = []
        for activity in activities:
            if self.transition_manager.activity_has_mop(activity):
                mop_first.append(activity)
            else:
                rest.append(activity)
        return mop_first + rest

    def maybe_launch_activity(
        self, activities: List[str], visited: Optional[Set[str]] = None
    ) -> Optional[str]:
        """
        Pick the next activity to launch under the dose policy, or None (INV-AGT-47).

        Dose control over the E-mín launcher (design Data Flow step 5): activities
        are first ordered MOP-first (``order_activity_launch_queue``), then the
        first activity that is neither already visited nor denylisted is launched —
        but only when the cadence/cap gate allows a launch this step. When the gate
        does not allow it, or no eligible activity remains, None is returned and the
        agent continues normal UI-driven exploration unaffected.

        The step counter advances on every call (a "launch opportunity"). It is
        reset to zero only at a firing point, so the launcher fires once every
        ``config.launch_cadence`` calls. The per-run budget (``config.launch_cap``)
        is consumed only when an activity is actually selected — an opportunity that
        fires but finds no eligible activity costs no budget. Port of
        ``SataAgent.selectNewActionNonnull`` launcher block + ``shouldFireLauncher``.

        Args:
            activities: The candidate activity launch queue, in natural order.
            visited: Activities already reached this run (skipped). When None, the
                strategy's visited set is used (``_get_visited_activities``).

        Returns:
            The activity name to launch, or None when the dose gate blocks a launch
            or no eligible activity remains.
        """
        self._steps_since_launch += 1
        if not self._launcher_should_fire():
            return None
        # Firing point: reset the cadence counter regardless of the outcome so
        # firing stays periodic and the queue is not re-scanned every step.
        self._steps_since_launch = 0
        if visited is None:
            visited = self._get_visited_activities()
        candidate = self._select_launch_candidate(activities, visited)
        if candidate is not None:
            # Budget consumed only on an actual launch (Scenario "Per-Run Launch Cap").
            self._launch_count += 1
        return candidate

    def _launcher_should_fire(self) -> bool:
        """
        Report whether the dose gate permits a direct launch this step.

        The launcher fires only when it is enabled (``trigger_mop_first``), the
        cadence period has elapsed (``_steps_since_launch >= config.launch_cadence``),
        and the per-run budget is not exhausted (``config.launch_cap == 0`` means
        unlimited, otherwise fire only while ``_launch_count < config.launch_cap``).
        With ``trigger_mop_first`` off this is a byte-identical no-op — the pure arm
        never launches.
        """
        if not self.config.trigger_mop_first:
            return False
        if self._steps_since_launch < self.config.launch_cadence:
            return False
        cap = self.config.launch_cap
        return cap == 0 or self._launch_count < cap

    def _select_launch_candidate(
        self, activities: List[str], visited: Set[str]
    ) -> Optional[str]:
        """
        Return the first MOP-first-ordered activity eligible to launch, or None.

        Eligibility: not already visited and not on the failed-launch denylist. The
        queue is ordered MOP-first via ``order_activity_launch_queue`` so, when
        ``trigger_mop_first`` is set, MOP-reaching activities are preferred.
        """
        for activity in self.order_activity_launch_queue(activities):
            if activity in visited or activity in self._launch_denylist:
                continue
            return activity
        return None

    def record_launch_failure(self, activity: str) -> None:
        """
        Denylist an activity whose launch failed (spec Scenario "Failed Launch").

        A denylisted activity is never returned by ``maybe_launch_activity`` again
        in the same run, so a launch that does not reach the foreground is not
        retried and wasted. The denylist is cleared on ``reset`` (per-run scope).
        """
        self._launch_denylist.add(activity)

    def _foreground_package(self, screen_desc: ScreenDescription) -> str:
        """Return the dominant package of the current screen's actionable items.

        Uses the most frequent non-empty item package as the foreground package.
        Returns "" when no item carries package information.
        """
        counts: Dict[str, int] = {}
        for item in screen_desc.items:
            pkg = item.view.get("package", "")
            if pkg:
                counts[pkg] = counts.get(pkg, 0) + 1
        if not counts:
            return ""
        return max(counts, key=counts.get)

    def _is_foreign_foreground(self, screen_desc: ScreenDescription) -> bool:
        """Report whether the foreground screen is foreign to the target package.

        Foreign means every actionable item belongs to a package that is neither
        the target package nor a system-dialog package (permission dialogs,
        alerts). Screens with no package information cannot be judged and are
        treated as native, so the guard never escapes on ambiguous input.
        """
        if not self.target_package:
            return False
        packages = {
            item.view.get("package", "")
            for item in screen_desc.items
            if item.view.get("package")
        }
        if not packages:
            return False
        return all(
            pkg != self.target_package and pkg not in self.SYSTEM_DIALOG_PACKAGES
            for pkg in packages
        )

    def _apply_back_menu_cap(self, action: ItemAction) -> ItemAction:
        """Apply the BACK/MENU consecutive-pick cap to a chosen action (INV-AGT-51).

        Counts consecutive BACK decisions; once ``back_menu_pick_cap`` is
        reached, a further BACK pick is filtered and replaced by a relaunch
        (RESTART) so the agent breaks out of a BACK loop instead of spamming it.
        Any non-BACK decision lifts the filter by resetting the streak. With the
        cap at 0 (default) this is a byte-identical no-op — the base policy sees
        the action unchanged and the streak counter is never consulted.

        Note: there is no MENU action in the current parse; BACK is the only
        menu-style system decision the strategy emits, so the cap operates on
        BACK. RESTART (the escape) is not itself counted as a BACK pick.

        Args:
            action: The action the strategy is about to return.

        Returns:
            The same action, or a relaunch action when the cap filters a BACK.
        """
        cap = self.config.back_menu_pick_cap
        if cap <= 0:
            return action

        if action.event == WidgetEventType.BACK:
            if self._consecutive_back_menu >= cap:
                track.back_menu_cap_filtered(iter=self._current_iteration, cap=cap)
                logger.info(
                    f"BACK/MENU cap reached ({cap}): filtering BACK, relaunching"
                )
                self._consecutive_back_menu = 0
                return self._create_restart_action()
            self._consecutive_back_menu += 1
            return action

        # Any non-BACK decision lifts the cap for the next round.
        self._consecutive_back_menu = 0
        return action

    def _prepare_input_action(
        self,
        action: ItemAction,
        current_hash: str,
        screen_desc: Optional[ScreenDescription] = None,
    ) -> Optional[ItemAction]:
        """
        Prepare input action with test value.

        Generates next test value for the input field. Returns None if
        all values have been tested.

        Args:
            action: TEXT_CHANGE action
            current_hash: Current state hash
            screen_desc: Current screen, used to source ±2 containment labels for
                typed-input inference (fair-test F). Optional so callers/tests
                without a screen fall back to the widget's own attributes.

        Returns:
            Action with test value, or None if exhausted
        """
        element_id = action.widget_id or make_element_id_from_tuple(action.coordinates)
        is_mop = action.reaches_target or action.directly_reaches_target

        # Infer input type from the widget's own attributes first, then from the
        # nearest on-screen labels (±2 containment proxy). Token-based matching.
        nearby_labels = self._nearby_labels(action, screen_desc)
        input_type = infer_input_type(action.target_view, nearby_labels)

        # Get next test value
        test_value = self.value_generator.get_next_value(
            element_id, is_mop=is_mop, input_type=input_type
        )

        if test_value is None:
            logger.debug(f"Input field {element_id}: all variations tested")
            return None

        # Create a NEW action with the text input value.
        # IMPORTANT: Do NOT mutate the original action. ItemActions from the
        # ScreenDescription are shared references -- mutating text_input would
        # permanently change the action for all future iterations on this screen.
        # model_copy() creates a shallow Pydantic clone with only text_input overridden.
        action_with_input = action.model_copy(update={"text_input": test_value})

        logger.info(
            f"Input field {element_id} ({input_type}): testing value '{test_value[:20]}'"
        )
        return action_with_input

    def _nearby_labels(
        self, action: ItemAction, screen_desc: Optional[ScreenDescription]
    ) -> List[str]:
        """Return the texts of on-screen labels nearest the input widget.

        Spatial proxy for ±2 hierarchy containment (fair-test F): a form field's
        label sits directly above or beside its input, so the closest text labels
        within ``_NEARBY_LABEL_RADIUS_PX`` are effectively its siblings. Returns up
        to ``_MAX_NEARBY_LABELS`` label texts, nearest first; empty when no screen
        is available or no label is close enough. The input widget itself is
        skipped (zero distance).
        """
        if screen_desc is None:
            return []
        origin = action.coordinates or self._widget_center(action.target_view)
        if origin is None:
            return []

        candidates: List[Tuple[float, str]] = []
        for item in getattr(screen_desc, "items", None) or []:
            view = getattr(item, "view", None) or {}
            text = (view.get("text") or "").strip()
            if not text:
                continue
            center = self._widget_center(view)
            if center is None:
                continue
            distance = math.hypot(center[0] - origin[0], center[1] - origin[1])
            if distance == 0 or distance > _NEARBY_LABEL_RADIUS_PX:
                continue
            candidates.append((distance, text))

        candidates.sort(key=lambda pair: pair[0])
        return [text for _, text in candidates[:_MAX_NEARBY_LABELS]]

    @staticmethod
    def _widget_center(view: Optional[Dict]) -> Optional[Tuple[int, int]]:
        """Compute a widget's bounds center (x, y), or None when unparseable.

        Accepts the ``[[x1, y1], [x2, y2]]`` bounds shape used by the screen parser.
        """
        if not view:
            return None
        bounds = view.get("bounds")
        if isinstance(bounds, (list, tuple)) and len(bounds) == 2:
            try:
                (x1, y1), (x2, y2) = bounds
                return ((int(x1) + int(x2)) // 2, (int(y1) + int(y2)) // 2)
            except (TypeError, ValueError):
                return None
        return None

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
        self._consecutive_back_menu = 0

        # Reset E-mín launcher dose state (per-run scope, INV-AGT-47).
        self._launch_denylist.clear()
        self._launch_count = 0
        self._steps_since_launch = 0

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
