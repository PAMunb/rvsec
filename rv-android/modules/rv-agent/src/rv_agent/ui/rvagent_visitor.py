"""
RV-Agent custom screen visitor with full static analysis integration.

This visitor extends DefaultTextVisitor to provide:
- MOP marker enrichment ([M], [DM]) via widget → event → signature → method mapping
- WTG integration for navigation guidance
- Multiple widget matching strategies (resource-id, text, class+bounds)
- Graceful degradation when static_data is not available
"""

import logging
from typing import Dict, List, Optional

from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.widget import Widget
from rv_android_core.domain.wtg import WindowTransitionGraph
from rv_screen_parser.parser.screen.visitor.default_visitor import DefaultTextVisitor
from rv_screen_parser.parser.screen.visitor.model import (
    ItemAction,
    Node,
    ScreenDescription,
)


class RVAgentVisitor(DefaultTextVisitor):
    """
    Custom visitor for RV-Agent with full static analysis integration.

    Features:
    - MOP marker enrichment ([M], [DM]) via widget → event → signature → method
    - WTG integration for navigation guidance
    - Resource-ID and text-based widget matching with multiple fallback strategies
    - Activity-to-window matching with partial name support (via parent class)

    Attributes:
        wtg: Window Transition Graph for navigation analysis
        widget_cache: Cache of matched widgets to avoid repeated lookups
        mop_stats: Statistics about MOP marker assignments

    Note:
        Window matching is handled by AbstractScreenVisitor (parent) via
        Windows.get_window() which supports relative activity names.
    """

    def __init__(self, static_data: Optional[StaticAnalysisData], activity: str):
        """
        Initialize the RVAgentVisitor.

        Args:
            static_data: Static analysis data (optional). When None, visitor
                        operates without MOP enrichment.
            activity: Current activity name for window matching.
        """
        # Parent sets self.window via Windows.get_window(activity)
        super().__init__(static_data, activity)

        self.logger = logging.getLogger(__name__)

        # WTG integration
        self.wtg: Optional[WindowTransitionGraph] = None
        if static_data and hasattr(static_data, "wtg"):
            self.wtg = static_data.wtg

        # Cache and stats
        self.widget_cache: Dict[str, Optional[Widget]] = {}
        self.mop_stats = {
            "total_actions": 0,
            "mop_enriched": 0,
            "direct_mop": 0,
            "transitive_mop": 0,
            "widgets_matched": 0,
            "widgets_not_matched": 0,
        }

        self.logger.info(
            f"RVAgentVisitor initialized for activity '{activity}'. "
            f"Window: {self.window.name if self.window else 'None'}. "
            f"WTG: {'available' if self.wtg else 'not available'}"
        )

    def find_matching_widget(self, node_data: Dict) -> Optional[Widget]:
        """
        Find a matching widget with enhanced matching strategies.

        Extends parent's find_matching_widget with additional strategies:
        1. Resource ID match (inherited)
        2. Text content match (inherited)
        3. Hint text match
        4. Global widget search (across all windows)

        Args:
            node_data: Node data dictionary with UI element properties

        Returns:
            Matching Widget or None
        """
        # Generate cache key from node data
        cache_key = self._generate_cache_key(node_data)
        if cache_key in self.widget_cache:
            return self.widget_cache[cache_key]

        # Try parent implementation first (uses self.window)
        widget = super().find_matching_widget(node_data)
        if widget:
            self.widget_cache[cache_key] = widget
            self.mop_stats["widgets_matched"] += 1
            return widget

        # Try hint text match in current window
        hint = node_data.get("hint", "") or node_data.get("content-desc", "")
        if hint and self.window and hasattr(self.window, "widgets"):
            for widget_id, widget in self.window.widgets.items():
                if hasattr(widget, "hint") and widget.hint == hint:
                    self.widget_cache[cache_key] = widget
                    self.mop_stats["widgets_matched"] += 1
                    return widget

        # Try global widget search (all windows)
        if self.static_info and hasattr(self.static_info, "windows"):
            widget = self._find_widget_globally(node_data)
            if widget:
                self.widget_cache[cache_key] = widget
                self.mop_stats["widgets_matched"] += 1
                return widget

        # No match found
        self.widget_cache[cache_key] = None
        self.mop_stats["widgets_not_matched"] += 1
        return None

    def _find_widget_globally(self, node_data: Dict) -> Optional[Widget]:
        """
        Search for widget across all windows by resource_id name.

        This is the fallback when widget is not found in current window.
        GESDA sometimes maps widgets to different windows than runtime activity.

        Strategies:
        1. Try global widgets dict by name
        2. Search all windows by widget name (resource_id suffix)
        3. Search all windows by widget_id if available

        Args:
            node_data: Node data dictionary

        Returns:
            Matching Widget or None
        """
        if not self.static_info or not hasattr(self.static_info, "windows"):
            return None

        resource_id = node_data.get("resource-id", "") or node_data.get(
            "resource_id", ""
        )
        if not resource_id:
            return None

        # Extract widget name from resource_id
        parts = resource_id.split("/")
        widget_name = parts[-1] if len(parts) > 1 else parts[0]

        # Strategy 1: Try global widgets dict by name
        if hasattr(self.static_info.windows, "widgets"):
            if widget_name in self.static_info.windows.widgets:
                widget = self.static_info.windows.widgets[widget_name]
                self.logger.debug(
                    f"[WTG_FALLBACK] Found widget '{widget_name}' in global dict"
                )
                return widget

        # Strategy 2: Search ALL windows by widget name
        for window in self.static_info.windows.windows:
            if hasattr(window, "widgets") and window.widgets:
                widget = window.get_widget_by_name(widget_name)
                if widget:
                    self.logger.info(
                        f"[WTG_FALLBACK] Found widget '{widget_name}' in window '{window.name}' "
                        f"(current activity: {self.activity})"
                    )
                    return widget

        # Strategy 3: Also check by widget_id in global dict (numeric ID)
        # Some widgets are stored by ID not name
        for wid, widget in self.static_info.windows.widgets.items():
            if hasattr(widget, "name") and widget.name == widget_name:
                self.logger.debug(
                    f"[WTG_FALLBACK] Found widget by name match in global dict: {wid}"
                )
                return widget

        self.logger.debug(
            f"[WTG_FALLBACK] Widget '{widget_name}' not found in any window"
        )
        return None

    def _generate_cache_key(self, node_data: Dict) -> str:
        """Generate a unique cache key for node data."""
        resource_id = node_data.get("resource-id", "") or node_data.get(
            "resource_id", ""
        )
        text = node_data.get("text", "")
        bounds = str(node_data.get("bounds", ""))
        return f"{resource_id}|{text}|{bounds}"

    def _enrich_action_with_mop(self, action: ItemAction, node: Node) -> None:
        """
        Enrich action with MOP markers from static analysis.

        Sets reaches_mop and directly_reaches_mop based on:
        1. Find matching widget
        2. Find matching event in widget.events
        3. Look up method signature in Classes.methods
        4. Copy MOP flags from Method

        Also adds [M] or [DM] markers to action.text for LLM prompts.

        Args:
            action: ItemAction to enrich
            node: Node the action belongs to
        """
        self.mop_stats["total_actions"] += 1

        if not self.static_info or not hasattr(self.static_info, "classes"):
            return

        widget = self.find_matching_widget(node.data)
        if not widget:
            return

        if not hasattr(widget, "events") or not widget.events:
            return

        # Find matching event for this action type
        for event in widget.events:
            if not hasattr(event, "type") or not hasattr(event, "signature"):
                continue

            # Match event type to action event
            if event.type == action.event:
                # Look up method in Classes
                method = self.static_info.classes.methods.get(event.signature)
                if method:
                    action.reaches_mop = getattr(method, "reaches_mop", False)
                    action.directly_reaches_mop = getattr(
                        method, "directly_reaches_mop", False
                    )
                    action.callback_signature = event.signature
                    action.widget_id = getattr(widget, "id", None) or getattr(
                        widget, "widget_id", None
                    )

                    # Update stats
                    if action.directly_reaches_mop:
                        self.mop_stats["direct_mop"] += 1
                        self.mop_stats["mop_enriched"] += 1
                        # Add marker to text if not already present
                        if "[DM]" not in action.text:
                            action.text += " [DM]"
                    elif action.reaches_mop:
                        self.mop_stats["transitive_mop"] += 1
                        self.mop_stats["mop_enriched"] += 1
                        if "[M]" not in action.text:
                            action.text += " [M]"

                    self.logger.debug(
                        f"MOP enriched: {action.text} "
                        f"(reaches_mop={action.reaches_mop}, "
                        f"directly_reaches_mop={action.directly_reaches_mop})"
                    )
                break

    def get_possible_actions(self, node: Node, counter, **kwargs) -> List[ItemAction]:
        """
        Get possible actions for a node with MOP enrichment.

        Extends parent to add MOP marker enrichment for all actions.

        Args:
            node: Node to get actions for
            counter: Action counter
            **kwargs: Additional arguments for parent

        Returns:
            List of ItemAction with MOP markers
        """
        actions = super().get_possible_actions(node, counter, **kwargs)

        if actions:
            for action in actions:
                self._enrich_action_with_mop(action, node)

        return actions

    def get_screen_description(self) -> ScreenDescription:
        """
        Get screen description with MOP statistics logging.

        Returns:
            ScreenDescription with all items and MOP enrichment
        """
        description = super().get_screen_description()

        # Log MOP statistics
        self.logger.info(
            f"Screen parsed: {len(description.items)} items, "
            f"MOP stats: {self.mop_stats['mop_enriched']}/{self.mop_stats['total_actions']} enriched "
            f"({self.mop_stats['direct_mop']} [DM], {self.mop_stats['transitive_mop']} [M])"
        )

        return description

    def get_wtg_transitions(self) -> List[Dict]:
        """
        Get available WTG transitions from current activity.

        Returns:
            List of transition dicts with target, widget_id, event_type
        """
        if not self.wtg or not self.window:
            return []

        window_id = getattr(self.window, "id", None)
        if not window_id:
            return []

        try:
            return self.wtg.get_window_transitions(window_id)
        except Exception as e:
            self.logger.warning(f"Error getting WTG transitions: {e}")
            return []

    def get_mop_statistics(self) -> Dict:
        """
        Get MOP enrichment statistics.

        Returns:
            Dict with MOP statistics
        """
        return self.mop_stats.copy()
