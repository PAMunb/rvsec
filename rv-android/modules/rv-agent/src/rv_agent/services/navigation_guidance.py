"""
Unified navigation guidance for algorithm and LLM.

Provides a consistent interface for exploration guidance based on
Window Transition Graph (WTG) analysis, usable by both algorithmic
strategies and LLM-based decision making.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from rv_screen_parser.parser.screen.visitor.model import ScreenDescription

if TYPE_CHECKING:
    from rv_agent.services.transition_manager import TransitionManager


logger = logging.getLogger(__name__)


@dataclass
class ExplorationContext:
    """
    Exploration context for current screen state.

    Contains guidance information that can be used by both
    algorithmic strategies and LLM prompts.
    """
    # Screens reachable from current position that haven't been visited
    unvisited_screens: List[str] = field(default_factory=list)

    # Actions suggested by WTG analysis (lead to unvisited screens)
    suggested_actions: List[Dict[str, Any]] = field(default_factory=list)

    # Current exploration progress metrics
    exploration_progress: Dict[str, Any] = field(default_factory=dict)

    # Whether static guidance is available
    has_guidance: bool = False

    # Priority targets (MOP-reaching screens)
    priority_targets: List[str] = field(default_factory=list)

    @property
    def has_unvisited(self) -> bool:
        """Check if there are unvisited screens."""
        return len(self.unvisited_screens) > 0

    @property
    def coverage_percent(self) -> float:
        """Get current coverage percentage."""
        return self.exploration_progress.get("coverage_percent", 0.0)


class NavigationGuidance:
    """
    Unified navigation guidance for algorithm and LLM.

    Wraps TransitionManager to provide a consistent interface for
    exploration guidance that works with both algorithmic strategies
    and LLM-based decision making.

    ### Architectural Decisions:
    - Single source of truth for navigation guidance
    - Format-agnostic context (ExplorationContext)
    - Separate formatting for LLM consumption
    - Graceful degradation when no static data available

    ### Role in the System:
    - Provides exploration context to RVAgentStrategy
    - Formats guidance text for LLM prompts
    - Tracks exploration progress across the app
    - Prioritizes MOP-reaching paths

    ### Integration Points:
    - Used by RVAgentStrategy for action selection
    - Used by LLM prompts for informed decision making
    - Receives data from TransitionManager
    - Updates exploration state during traversal
    """

    def __init__(self, transition_manager: Optional["TransitionManager"] = None):
        """
        Initialize NavigationGuidance.

        Args:
            transition_manager: Optional TransitionManager for WTG integration.
                              If None, guidance will be disabled.
        """
        self.transition_manager = transition_manager
        self._enabled = transition_manager is not None

        logger.info(
            f"NavigationGuidance initialized: "
            f"{'enabled' if self._enabled else 'disabled (no TransitionManager)'}"
        )

    @property
    def is_enabled(self) -> bool:
        """Check if guidance is available."""
        return self._enabled and self.transition_manager is not None

    def get_context(self, screen_desc: ScreenDescription) -> ExplorationContext:
        """
        Get exploration context for current screen.

        Retrieves navigation guidance from TransitionManager and
        packages it into an ExplorationContext usable by both
        algorithm and LLM.

        Args:
            screen_desc: Current screen description

        Returns:
            ExplorationContext with guidance information
        """
        if not self.is_enabled:
            return ExplorationContext(has_guidance=False)

        try:
            # Get raw guidance from TransitionManager
            guidance = self.transition_manager.get_navigation_guidance(
                current_activity=screen_desc.activity,
                screen_desc=screen_desc
            )

            # Extract unvisited screens
            unvisited_targets = guidance.get("unvisited_targets", [])
            unvisited_screens = [
                t.get("target_activity", "unknown")
                for t in unvisited_targets
                if not t.get("visited", True)
            ]

            # Extract priority targets (MOP-reaching)
            priority_targets = [
                t.get("target_activity", "unknown")
                for t in unvisited_targets
                if t.get("priority", 0) > 100  # High priority = MOP-reaching
            ]

            # Build context
            context = ExplorationContext(
                unvisited_screens=unvisited_screens,
                suggested_actions=guidance.get("suggested_actions", []),
                exploration_progress=guidance.get("exploration_progress", {}),
                has_guidance=guidance.get("has_static_guidance", False),
                priority_targets=priority_targets
            )

            if context.has_unvisited:
                logger.debug(
                    f"NavigationGuidance: {len(unvisited_screens)} unvisited screens, "
                    f"{len(context.suggested_actions)} suggested actions"
                )

            return context

        except Exception as e:
            logger.warning(f"NavigationGuidance: Error getting context: {e}")
            return ExplorationContext(has_guidance=False)

    def format_for_llm(self, context: ExplorationContext) -> str:
        """
        Format exploration context as text for LLM prompt.

        Creates a concise, informative text that can be included
        in the LLM prompt to guide its decision making.

        Args:
            context: ExplorationContext from get_context()

        Returns:
            Formatted string for LLM prompt, or empty string if no guidance
        """
        if not context.has_guidance:
            return ""

        lines = []

        # Unvisited screens
        if context.unvisited_screens:
            screens = context.unvisited_screens[:3]  # Limit to top 3
            screens_text = ", ".join(self._format_activity_name(s) for s in screens)
            lines.append(f"Unvisited screens reachable: {screens_text}")

            if len(context.unvisited_screens) > 3:
                lines.append(f"  (+{len(context.unvisited_screens) - 3} more)")

        # Priority targets (MOP-reaching)
        if context.priority_targets:
            targets = context.priority_targets[:2]
            targets_text = ", ".join(self._format_activity_name(t) for t in targets)
            lines.append(f"Priority targets (monitored operations): {targets_text}")

        # Suggested action
        if context.suggested_actions:
            action = context.suggested_actions[0]
            action_type = action.get("action_type", "click")
            action_text = action.get("action_text", "element")
            target = self._format_activity_name(action.get("target_activity", "unknown"))
            lines.append(f"Suggested: {action_type} on '{action_text}' to reach {target}")

        # Coverage progress
        if context.coverage_percent > 0:
            lines.append(f"Exploration progress: {context.coverage_percent:.0f}%")

        if not lines:
            return ""

        return "Navigation guidance:\n" + "\n".join(f"  - {line}" for line in lines)

    def format_for_llm_compact(self, context: ExplorationContext) -> str:
        """
        Format exploration context as compact text for LLM.

        Creates a minimal, one-line hint for space-constrained prompts.

        Args:
            context: ExplorationContext from get_context()

        Returns:
            Compact formatted string, or empty string if no guidance
        """
        if not context.has_guidance or not context.unvisited_screens:
            return ""

        count = len(context.unvisited_screens)
        first_screen = self._format_activity_name(context.unvisited_screens[0])

        if context.suggested_actions:
            action = context.suggested_actions[0]
            action_text = action.get("action_text", "")
            if action_text:
                return f"Hint: '{action_text}' leads to {first_screen} ({count} unvisited)"

        return f"Hint: {count} unvisited screens, try reaching {first_screen}"

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of navigation guidance state.

        Returns:
            Dictionary with guidance statistics
        """
        if not self.is_enabled:
            return {"enabled": False}

        summary = self.transition_manager.get_exploration_summary()
        summary["enabled"] = True
        return summary

    def _format_activity_name(self, activity: str) -> str:
        """
        Format activity name for display.

        Extracts the simple class name from full activity path.

        Args:
            activity: Full activity name (e.g., "com.example.MainActivity")

        Returns:
            Formatted name (e.g., "MainActivity")
        """
        if not activity:
            return "unknown"

        # Handle relative activity names (e.g., ".MainActivity")
        if activity.startswith("."):
            return activity[1:]

        # Extract class name from full path
        parts = activity.split(".")
        return parts[-1] if parts else activity
