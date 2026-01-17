"""
Action scorers for priority-based selection.

Each Scorer evaluates one aspect of action priority. Scores are summed
by the ActionRanker to determine final action ranking.
"""

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from rv_agent.memory.element_id import make_element_id_from_action

if TYPE_CHECKING:
    from rv_screen_parser.parser.screen.visitor.model import ItemAction
    from rv_agent.strategies.rvagent_strategy.ranking.context import RankingContext


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

    Actions that reach MOPs get a priority bonus, but not so high as to
    dominate other factors like untested elements or WTG guidance.
    """

    DIRECT_MOP_SCORE = 100.0
    TRANSITIVE_MOP_SCORE = 50.0

    def score(self, action: "ItemAction", context: "RankingContext") -> float:
        if action.directly_reaches_mop:
            return self.DIRECT_MOP_SCORE
        elif action.reaches_mop:
            return self.TRANSITIVE_MOP_SCORE
        return 0.0


class WtgScorer(Scorer):
    """
    Scores actions based on WTG (Window Transition Graph) guidance.

    Actions that lead to unvisited screens get bonus priority.
    """

    WTG_GUIDED_SCORE = 100.0

    def score(self, action: "ItemAction", context: "RankingContext") -> float:
        if not context.transition_manager:
            return 0.0

        # Check if WTG is actually available
        has_wtg = hasattr(context.transition_manager, 'wtg') and context.transition_manager.wtg is not None
        if not has_wtg:
            return 0.0

        guidance = context.transition_manager.get_navigation_guidance(
            current_activity=context.screen_desc.activity,
            screen_desc=context.screen_desc
        )

        has_guidance = guidance.get("has_static_guidance", False)
        suggested = guidance.get("suggested_actions", [])

        if not has_guidance:
            return 0.0

        suggested_ids = [s.get("action_id") for s in suggested]

        # [DEBUG_ACTION_SELECTION] Log only when we have actual guidance
        target_class = action.target_view.get('class', 'unknown') if action.target_view else 'unknown'
        logger.info(f"[DEBUG_ACTION_SELECTION] WtgScorer: has_guidance={has_guidance} action_id={action.id} target={target_class} suggested_ids={suggested_ids[:5]}")

        for suggestion in suggested:
            if suggestion.get("action_id") == action.id:
                target_class = action.target_view.get('class', 'unknown') if action.target_view else 'unknown'
                logger.debug(f"[DEBUG_ACTION_SELECTION] WtgScorer: +100 for {target_class} id={action.id}")
                return self.WTG_GUIDED_SCORE

        return 0.0


class UntestedScorer(Scorer):
    """
    Scores actions based on UI element testing status.

    Elements that have never been interacted with get bonus priority.
    """

    UNTESTED_SCORE = 200.0

    def score(self, action: "ItemAction", context: "RankingContext") -> float:
        # Use standardized element ID
        element_id = action.widget_id or make_element_id_from_action(action)
        if not element_id:
            return 0.0

        is_untested = context.ui_coverage.is_element_untested(element_id)
        target_class = action.target_view.get('class', 'unknown') if action.target_view else 'unknown'

        # [DEBUG_ACTION_SELECTION] Log untested scoring
        logger.info(f"[DEBUG_UNTESTED] UntestedScorer: {target_class} id={element_id} untested={is_untested}")

        if is_untested:
            return self.UNTESTED_SCORE

        return 0.0


class ExecutionCountScorer(Scorer):
    """
    Scores actions inversely proportional to execution count.

    Less-executed actions get higher scores, promoting exploration diversity.
    """

    BASE_SCORE = 10.0

    def __init__(self, coordinate_converter=None):
        self.converter = coordinate_converter

    def score(self, action: "ItemAction", context: "RankingContext") -> float:
        node = context.graph.states.get(context.current_state_hash)
        if not node:
            return self.BASE_SCORE

        action_signature = self._convert_signature(action.coords_for_matching)
        exec_count = node.get_action_execution_count(action_signature)

        return self.BASE_SCORE / (1.0 + exec_count)

    def _convert_signature(self, signature):
        """Convert action signature to optimized space."""
        (device_x, device_y), action_type = signature

        if self.converter:
            optimized_x, optimized_y = self.converter.device_to_optimized(device_x, device_y)
        else:
            optimized_x = int(device_x * 704 / 1080)
            optimized_y = int(device_y * 1248 / 1920)

        return ((optimized_x, optimized_y), action_type)


class ComponentPriorityScorer(Scorer):
    """
    Scores actions based on component type priority.

    Auto-calibrated from UI dump analysis of 14 apps / 255 screens.
    Run scripts/calibrate_scores.py to regenerate scores.
    """

    # All interactive components have same base priority
    # UntestedScorer (+200) handles systematic visitation
    HIGH_PRIORITY = {
        "Spinner": 50.0,       # Dropdown menus
        "Button": 50.0,        # Primary actions
        "ImageButton": 50.0,   # Navigation and actions
        "EditText": 50.0,      # Form inputs
        "DrawerLayout": 50.0,  # Navigation drawer
    }

    # Medium priority: state changes, content navigation
    MEDIUM_PRIORITY = {
        "CheckBox": 40.0,         # Toggle state
        "Switch": 40.0,           # Toggle settings
        "RadioButton": 40.0,      # Selection options
        "ViewPager": 40.0,        # Screen navigation
        "RecyclerView": 40.0,     # Content lists
        "CheckedTextView": 40.0,  # Selectable list items
    }

    def score(self, action: "ItemAction", context: "RankingContext") -> float:
        target_class = action.target_view.get('class', '') if action.target_view else ''
        simple_class = target_class.split('.')[-1] if target_class else ''

        # Check high priority first
        for key, score in self.HIGH_PRIORITY.items():
            if simple_class == key or key in target_class:
                logger.debug(f"[DEBUG_ACTION_SELECTION] ComponentPriorityScorer: +{score} for {target_class} (HIGH)")
                return score

        # Then medium priority
        for key, score in self.MEDIUM_PRIORITY.items():
            if simple_class == key or key in target_class:
                logger.debug(f"[DEBUG_ACTION_SELECTION] ComponentPriorityScorer: +{score} for {target_class} (MED)")
                return score

        return 0.0


# Alias for backwards compatibility
DropdownScorer = ComponentPriorityScorer


class FailedActionScorer(Scorer):
    """
    Penalizes actions that have permanently failed.

    Actions that caused crashes or errors are heavily penalized to prevent
    repeated failures.
    """

    FAILED_PENALTY = -9999.0

    def __init__(self, coordinate_converter=None):
        self.converter = coordinate_converter

    def score(self, action: "ItemAction", context: "RankingContext") -> float:
        node = context.graph.states.get(context.current_state_hash)
        if not node:
            return 0.0

        action_signature = self._convert_signature(action.coords_for_matching)

        if node.is_action_failed(action_signature):
            return self.FAILED_PENALTY

        return 0.0

    def _convert_signature(self, signature):
        """Convert action signature to optimized space."""
        (device_x, device_y), action_type = signature

        if self.converter:
            optimized_x, optimized_y = self.converter.device_to_optimized(device_x, device_y)
        else:
            optimized_x = int(device_x * 704 / 1080)
            optimized_y = int(device_y * 1248 / 1920)

        return ((optimized_x, optimized_y), action_type)
