"""
Action scorers for priority-based selection.

Each Scorer evaluates one aspect of action priority. Scores are summed
by the ActionRanker to determine final action ranking.

Scorer Architecture (9 scorers total):
  Prioritization:
    - MopScorer: MOP-reaching actions (with form-context deferral)
    - WtgScorer: WTG-guided navigation
    - SaturationScorer: Bonus for unsaturated states
    - ComponentPriorityScorer: Button/form/navigation priority
    - StrengthScorer: Success rate based priority
    - GradualDecayScorer: Exponential decay based on visit count
    - CoverageDensityScorer: Prioritizes actions leading to states with untested elements

  Penalties:
    - SystemElementFilter: Filters system UI elements
    - VisitationPenaltyScorer: Penalizes over-visited states

All scorer weights are configurable via RVAgentConfig for calibration.
"""

import logging
import math
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from rv_agent.memory.element_id import make_element_id_from_action
from rv_agent.constants import RVAgentConstants
from rv_agent.services.coordinate_utils import device_to_optimized

if TYPE_CHECKING:
    from rv_screen_parser.parser.screen.visitor.model import ItemAction
    from rv_agent.strategies.rvagent_strategy.ranking.context import RankingContext
    from rv_agent.config.agent_config import RVAgentConfig


logger = logging.getLogger(__name__)


class Scorer(ABC):
    """Base class for action scorers."""

    @abstractmethod
    def score(self, action: "ItemAction", context: "RankingContext") -> float:
        """
        Calculate score for an action.

        Args:
            action: Action to score
            context: Shared ranking context

        Returns:
            Score value (higher = higher priority)
        """
        pass


class MopScorer(Scorer):
    """
    Scores actions based on MOP (Monitored Operation) reachability.

    Actions that reach MOPs get high priority to focus testing effort
    on monitored operations from static analysis.
    """

    # Default values (used when config not provided)
    DEFAULT_DIRECT_SCORE = 300.0
    DEFAULT_TRANSITIVE_SCORE = 150.0

    def __init__(self, config: Optional["RVAgentConfig"] = None):
        """
        Initialize MopScorer.

        Args:
            config: Optional config with calibration parameters
        """
        if config:
            self.direct_score = config.mop_direct_score
            self.transitive_score = config.mop_transitive_score
        else:
            self.direct_score = self.DEFAULT_DIRECT_SCORE
            self.transitive_score = self.DEFAULT_TRANSITIVE_SCORE

    def score(self, action: "ItemAction", context: "RankingContext") -> float:
        # Defer MOP scoring for CLICK when untested text inputs exist on screen
        if (
            getattr(context, "has_untested_inputs", False)
            and getattr(action, "action_type", "") == "CLICK"
        ):
            return 0.0

        if action.directly_reaches_mop:
            return self.direct_score
        elif action.reaches_mop:
            return self.transitive_score
        return 0.0


class WtgScorer(Scorer):
    """
    Scores actions based on WTG (Window Transition Graph) guidance.

    Actions that lead to unvisited screens get high priority for
    navigation and state coverage.
    """

    DEFAULT_GUIDED_SCORE = 250.0

    def __init__(self, config: Optional["RVAgentConfig"] = None):
        """
        Initialize WtgScorer.

        Args:
            config: Optional config with calibration parameters
        """
        if config:
            self.guided_score = config.wtg_guided_score
        else:
            self.guided_score = self.DEFAULT_GUIDED_SCORE

    def score(self, action: "ItemAction", context: "RankingContext") -> float:
        if not context.transition_manager:
            return 0.0

        has_wtg = (
            hasattr(context.transition_manager, "wtg")
            and context.transition_manager.wtg is not None
        )
        if not has_wtg:
            return 0.0

        guidance = context.transition_manager.get_navigation_guidance(
            current_activity=context.screen_desc.activity,
            screen_desc=context.screen_desc,
        )

        if not guidance.get("has_static_guidance", False):
            return 0.0

        for suggestion in guidance.get("suggested_actions", []):
            if suggestion.get("action_id") == action.id:
                return self.guided_score

        return 0.0


class GradualDecayScorer(Scorer):
    """
    Scores actions with gradual decay based on visit count.

    Uses exponential decay to provide smoother priority transitions:
    - Visit 0: base_score (untested - highest priority)
    - Visit N: base_score * (decay_rate ^ N)
    - Visit >= min_visits: 0 (well tested - lowest priority)

    This prevents the "cliff effect" where elements drop from high to zero
    priority after a single interaction, causing premature abandonment.
    """

    DEFAULT_BASE_SCORE = 200.0
    DEFAULT_DECAY_RATE = 0.7
    DEFAULT_MIN_VISITS = 5

    def __init__(self, config: Optional["RVAgentConfig"] = None):
        """
        Initialize GradualDecayScorer.

        Args:
            config: Optional config with calibration parameters
        """
        if config:
            self.base_score = config.gradual_decay_base
            self.decay_rate = config.gradual_decay_rate
            self.min_visits = config.gradual_decay_min_visits
        else:
            self.base_score = self.DEFAULT_BASE_SCORE
            self.decay_rate = self.DEFAULT_DECAY_RATE
            self.min_visits = self.DEFAULT_MIN_VISITS

    def score(self, action: "ItemAction", context: "RankingContext") -> float:
        element_id = action.widget_id or make_element_id_from_action(action)
        if not element_id:
            return 0.0

        visit_count = context.ui_coverage.get_element_test_count(element_id)

        if visit_count >= self.min_visits:
            return 0.0

        return self.base_score * (self.decay_rate**visit_count)


class ComponentPriorityScorer(Scorer):
    """
    Scores actions based on component type priority.

    Priorities are configurable via RVAgentConfig for calibration.
    """

    DEFAULT_HIGH_PRIORITY = 50.0
    DEFAULT_MEDIUM_PRIORITY = 40.0

    # Component types categorized by priority level
    HIGH_PRIORITY_TYPES = frozenset(
        {
            # Buttons
            "Button",
            "ImageButton",
            "MaterialButton",
            "FloatingActionButton",
            "ExtendedFloatingActionButton",
            # Form inputs
            "EditText",
            "AutoCompleteTextView",
            "MultiAutoCompleteTextView",
            "TextInputEditText",
            # Dropdowns
            "Spinner",
            "AppCompatSpinner",
            # Navigation
            "DrawerLayout",
            "Tab",
            "TabLayout",
            "TabView",
            "ActionBar$Tab",
            "TabItem",
            "BottomNavigationItemView",
            "NavigationBarItemView",
            "NavigationBarView",
            "NavigationRailView",
            # Menus
            "ActionMenuItemView",
            "MenuItemView",
            "OverflowMenuButton",
            # Other
            "Chip",
            "LinearLayout",
        }
    )

    MEDIUM_PRIORITY_TYPES = frozenset(
        {
            # Toggles
            "CheckBox",
            "MaterialCheckBox",
            "AppCompatCheckBox",
            "Switch",
            "SwitchCompat",
            "SwitchMaterial",
            "ToggleButton",
            "AppCompatToggleButton",
            # Radio buttons
            "RadioButton",
            "MaterialRadioButton",
            "AppCompatRadioButton",
            # Sliders
            "SeekBar",
            "AppCompatSeekBar",
            "Slider",
            "RangeSlider",
            "RatingBar",
            # Content navigation
            "ViewPager",
            "RecyclerView",
            "CheckedTextView",
            "AppCompatCheckedTextView",
        }
    )

    # System actions have fixed priority
    SYSTEM_ACTION_SCORES = {
        "SystemAction_BACK": 30.0,
        "SystemAction_RESTART": 20.0,
    }

    def __init__(self, config: Optional["RVAgentConfig"] = None):
        """
        Initialize ComponentPriorityScorer.

        Args:
            config: Optional config with calibration parameters
        """
        if config:
            self.high_priority = config.component_high_priority
            self.medium_priority = config.component_medium_priority
        else:
            self.high_priority = self.DEFAULT_HIGH_PRIORITY
            self.medium_priority = self.DEFAULT_MEDIUM_PRIORITY

    def score(self, action: "ItemAction", context: "RankingContext") -> float:
        target_class = action.target_view.get("class", "") if action.target_view else ""
        simple_class = target_class.split(".")[-1] if target_class else ""

        # Check system actions first
        if simple_class in self.SYSTEM_ACTION_SCORES:
            return self.SYSTEM_ACTION_SCORES[simple_class]

        # Check high priority types
        if simple_class in self.HIGH_PRIORITY_TYPES:
            return self.high_priority
        for type_name in self.HIGH_PRIORITY_TYPES:
            if type_name in target_class:
                return self.high_priority

        # Check medium priority types
        if simple_class in self.MEDIUM_PRIORITY_TYPES:
            return self.medium_priority
        for type_name in self.MEDIUM_PRIORITY_TYPES:
            if type_name in target_class:
                return self.medium_priority

        return 0.0


class SystemElementFilter(Scorer):
    """
    Penalizes actions on system UI elements.

    Elements from system packages (systemui, android) should be avoided
    as they are not part of the target application.
    """

    SYSTEM_PENALTY = -5000.0
    SYSTEM_PACKAGES = frozenset({"com.android.systemui", "android"})

    def score(self, action: "ItemAction", context: "RankingContext") -> float:
        if not action.target_view:
            return 0.0

        package = action.target_view.get("package", "")
        if package in self.SYSTEM_PACKAGES:
            return self.SYSTEM_PENALTY

        return 0.0


class SaturationScorer(Scorer):
    """
    Bonus for actions in unsaturated states.

    Gives higher priority to actions when the current state still has
    many unexplored actions (low saturation rate).

    Score = unsaturated_bonus * (1 - saturation_rate)
    """

    DEFAULT_UNSATURATED_BONUS = 80.0

    def __init__(self, config: Optional["RVAgentConfig"] = None):
        """
        Initialize SaturationScorer.

        Args:
            config: Optional config with calibration parameters
        """
        if config:
            self.unsaturated_bonus = config.unsaturated_bonus
        else:
            self.unsaturated_bonus = self.DEFAULT_UNSATURATED_BONUS

    def score(self, action: "ItemAction", context: "RankingContext") -> float:
        node = context.graph.states.get(context.current_state_hash)
        if not node:
            return 0.0

        saturation = node.get_saturation_rate(threshold=2)
        if saturation >= 1.0:
            return 0.0

        return self.unsaturated_bonus * (1.0 - saturation)


class VisitationPenaltyScorer(Scorer):
    """
    Penalizes actions in frequently visited states.

    Uses logarithmic decay to avoid re-exploring over-visited states
    while still allowing some revisitation.

    Score = penalty_factor * log(1 + visit_count)
    """

    DEFAULT_PENALTY_FACTOR = -10.0

    def __init__(self, config: Optional["RVAgentConfig"] = None):
        """
        Initialize VisitationPenaltyScorer.

        Args:
            config: Optional config with calibration parameters
        """
        if config:
            self.penalty_factor = config.visitation_penalty_factor
        else:
            self.penalty_factor = self.DEFAULT_PENALTY_FACTOR

    def score(self, action: "ItemAction", context: "RankingContext") -> float:
        node = context.graph.states.get(context.current_state_hash)
        if not node:
            return 0.0

        visits = node.visit_count
        return self.penalty_factor * math.log(1 + visits)


class CoverageDensityScorer(Scorer):
    """
    Scores actions based on the coverage gap of their destination state.

    If the successor tracker knows where an action leads (known transition),
    the scorer queries the UI coverage tracker for how many elements remain
    untested at the destination. Actions leading to states with more untested
    elements get higher scores.

    For unknown transitions (destination not yet observed), a neutral score
    of weight * 0.5 is assigned to encourage exploration of new paths.

    Formula:
        known destination:   weight * coverage_gap(destination)
        unknown destination: weight * 0.5
        no tracker/coverage: 0.0
    """

    DEFAULT_WEIGHT = 200.0

    def __init__(
        self, coordinate_converter=None, config: Optional["RVAgentConfig"] = None
    ):
        """
        Initialize CoverageDensityScorer.

        Args:
            coordinate_converter: Converter for coordinate spaces
            config: Optional config with calibration parameters
        """
        self.converter = coordinate_converter
        if config:
            self.weight = config.coverage_density_weight
        else:
            self.weight = self.DEFAULT_WEIGHT

    def score(self, action: "ItemAction", context: "RankingContext") -> float:
        if not context.successor_tracker or not context.ui_coverage:
            return 0.0

        # Convert to optimized coordinate space (SuccessorTracker uses optimized coords)
        action_signature = self._convert_signature(action.coords_for_matching)

        destination = context.successor_tracker.get_action_destination(
            context.current_state_hash, action_signature
        )

        if destination is None:
            # Unknown transition - moderate score to encourage exploration
            return self.weight * 0.5

        # Known destination - score based on coverage gap
        coverage_gap = context.ui_coverage.get_coverage_gap(destination)
        return self.weight * coverage_gap

    def _convert_signature(self, signature):
        """Convert action signature to optimized space."""
        (device_x, device_y), action_type = signature

        if self.converter:
            optimized_x, optimized_y = self.converter.device_to_optimized(
                device_x, device_y
            )
        else:
            optimized_x, optimized_y = device_to_optimized(
                device_x,
                device_y,
                (
                    RVAgentConstants.DEFAULT_DEVICE_WIDTH,
                    RVAgentConstants.DEFAULT_DEVICE_HEIGHT,
                ),
                (
                    RVAgentConstants.SCREENSHOT_TARGET_WIDTH,
                    RVAgentConstants.SCREENSHOT_TARGET_HEIGHT,
                ),
            )

        return ((optimized_x, optimized_y), action_type)


class StrengthScorer(Scorer):
    """
    Scores actions based on historical success rate.

    Actions that have led to state transitions (successes) are prioritized
    over actions that didn't cause any change.

    Score = weight * strength
    - strength = successes / executions (0.5 for untested)
    """

    DEFAULT_WEIGHT = 50.0
    DEFAULT_REWARD_SCORE_WEIGHT = 1.0

    def __init__(
        self, coordinate_converter=None, config: Optional["RVAgentConfig"] = None
    ):
        """
        Initialize StrengthScorer.

        Args:
            coordinate_converter: Converter for coordinate spaces
            config: Optional config with calibration parameters
        """
        self.converter = coordinate_converter
        if config:
            self.weight = config.strength_weight
            self.reward_score_weight = config.reward_score_weight
        else:
            self.weight = self.DEFAULT_WEIGHT
            self.reward_score_weight = self.DEFAULT_REWARD_SCORE_WEIGHT

    def score(self, action: "ItemAction", context: "RankingContext") -> float:
        node = context.graph.states.get(context.current_state_hash)
        if not node:
            return self.weight * 0.5  # Neutral for unknown states

        action_signature = self._convert_signature(action.coords_for_matching)
        strength = node.get_action_strength(action_signature)
        cumulative_reward = node.action_cumulative_reward.get(action_signature, 0.0)

        return self.weight * strength + self.reward_score_weight * cumulative_reward

    def _convert_signature(self, signature):
        """Convert action signature to optimized space."""
        (device_x, device_y), action_type = signature

        if self.converter:
            optimized_x, optimized_y = self.converter.device_to_optimized(
                device_x, device_y
            )
        else:
            optimized_x, optimized_y = device_to_optimized(
                device_x,
                device_y,
                (
                    RVAgentConstants.DEFAULT_DEVICE_WIDTH,
                    RVAgentConstants.DEFAULT_DEVICE_HEIGHT,
                ),
                (
                    RVAgentConstants.SCREENSHOT_TARGET_WIDTH,
                    RVAgentConstants.SCREENSHOT_TARGET_HEIGHT,
                ),
            )

        return ((optimized_x, optimized_y), action_type)
