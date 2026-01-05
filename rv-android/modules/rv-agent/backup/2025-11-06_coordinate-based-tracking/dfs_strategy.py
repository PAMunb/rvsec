"""
Depth-first exploration strategy with MOP prioritization.

Implements DFS exploration that prioritizes depth while incorporating
static analysis guidance for monitored operation coverage.
Supports both standalone mode (pure DFS) and guidance mode (LLM assist).
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
import logging
from rv_agent.strategies.base_strategy import BaseStrategy
from rv_agent.core.dynamic_state_graph import DynamicStateGraph
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription
from rv_android_core.domain.static import StaticAnalysisData

logger = logging.getLogger(__name__)


@dataclass
class DFSState:
    """
    DFS stack state for backtracking.

    Represents a node in the DFS traversal tree, enabling
    depth tracking and parent reference for backtracking.
    """
    screen_hash: str
    depth: int
    parent_hash: Optional[str]
    untested_count: int


class DFSStrategy(BaseStrategy):
    """
    Depth-first exploration strategy with MOP prioritization.

    ### Architectural Decisions:
    - Provides guidance, does not force actions
    - Prioritizes untested actions with MOP markers
    - Implements stack-based depth-first logic
    - Computes coverage context for informed decisions
    - Suggests backtracking when current screen exhausted

    ### Role in the System:
    - Generates priority rankings for system prompt
    - Determines exploration focus (deepen vs backtrack)
    - Queries graph state for guidance computation
    - Formats suggestions for LLM consumption
    - Maintains exploration stack implicitly via graph

    ### Integration Points:
    - Called by observe node to generate guidance
    - Queries DynamicStateGraph for state history
    - Accesses ScreenDescription for action enumeration
    - Uses StaticAnalysisData for MOP marker prioritization
    """

    def __init__(
        self,
        graph: DynamicStateGraph,
        static_data: Optional[StaticAnalysisData] = None
    ):
        """
        Initialize DFS strategy.

        Args:
            graph: Dynamic state graph for history tracking
            static_data: Optional static analysis data for MOP markers
        """
        self.graph = graph
        self.static_data = static_data

        # DFS standalone state
        self.state_stack: List[DFSState] = []
        self.visited_states: Set[str] = set()
        self.current_depth = 0

    def get_guidance(
        self,
        current_hash: str,
        screen_desc: ScreenDescription
    ) -> Dict[str, Any]:
        """
        Compute exploration guidance for current state.

        ### Architectural Decisions:
        - Prioritizes untested actions first
        - Ranks by MOP priority: [DM] > [M] > no marker
        - Suggests deepening if untested actions exist
        - Suggests backtracking if screen fully explored
        - Provides coverage context for awareness

        Returns guidance dictionary for system prompt integration:
        - priority_actions: Ranked list of suggested actions
        - exploration_focus: Current strategy directive
        - coverage_current: Coverage percentage for context
        """
        node = self.graph.states.get(current_hash)

        # Get all actions from screen description
        all_actions = screen_desc.get_all_actions()

        # DEBUG: Show raw screen description from parser
        logger.info("=" * 80)
        logger.info(f"📋 RAW SCREEN DESCRIPTION (hash={screen_hash[:8]}):")
        logger.info(f"   Activity: {screen_desc.activity}")
        logger.info(f"   Total items: {len(screen_desc.items)}")
        logger.info(f"   Total actions: {len(all_actions)}")
        logger.info("")
        # Show ALL items with actions (not just first 10)
        items_with_actions = [item for item in screen_desc.items if item.actions]
        for item in items_with_actions:
            logger.info(f"   - {item.base_description}")
            for action in item.actions:
                coords = action.get_execution_coordinates()
                bounds = action.target_view.get('bounds', [])
                logger.info(f"      • ID={action.id} {action.text} coords={coords} bounds={bounds}")
        items_without_actions = len(screen_desc.items) - len(items_with_actions)
        if items_without_actions > 0:
            logger.info(f"   ... and {items_without_actions} items without actions")
        logger.info("=" * 80)

        # Filter out system actions (SYSTEM_BACK, RESTART_APP)
        # Also filter actions in navigation bar area (y > 1794 in device space)
        # DFS controls navigation algorithmically, doesn't need system actions
        filtered_actions = []
        for action in all_actions:
            # Skip system actions
            if action.target_view.get('system_action', False):
                logger.debug(f"🚫 Filtering system action: ID={action.id} {action.text[:50]}")
                continue

            # Skip actions in navigation bar area (below y=1794)
            coords = action.get_execution_coordinates()
            if coords:
                x, y = coords
                # These are device coordinates from the dump (1080x1920)
                bounds = action.target_view.get('bounds', [])
                if y > 1794:  # Navigation bar starts at y=1794 in device space
                    logger.info(f"🚫 Filtering nav bar: ID={action.id} '{action.text[:40]}' coords=({x},{y}) bounds={bounds}")
                    continue

            filtered_actions.append(action)

        all_actions = filtered_actions

        # Identify untested actions
        if node:
            untested = [
                action for action in all_actions
                if action.id not in node.executed_actions
            ]
        else:
            # First visit - all actions untested
            untested = all_actions

        # Sort by MOP priority: [DM] > [M] > no marker
        priority = sorted(
            untested,
            key=lambda a: self._get_mop_priority(a),
            reverse=True
        )

        # DFS logic: deepen if untested exist, else backtrack
        if priority:
            focus = f"deepen (explore {len(priority)} untested actions)"
        else:
            focus = "backtrack (all actions tested, try back/navigation)"

        # Get coverage if node exists
        coverage = f"{node.get_coverage() * 100:.1f}%" if node else "0.0%"

        return {
            "priority_actions": [self._format_action(a) for a in priority[:5]],
            "exploration_focus": focus,
            "coverage_current": coverage,
            "untested_count": len(priority),
            "total_count": len(all_actions)
        }

    def record_transition(self, from_hash: str, to_hash: str):
        """
        Record state transition for strategy bookkeeping.

        DFS doesn't maintain explicit stack - relies on graph structure.

        Args:
            from_hash: Structural hash of source state
            to_hash: Structural hash of destination state
        """
        # DFS uses implicit stack via graph transitions
        # No additional bookkeeping needed
        pass

    def select_next_action(
        self,
        screen_hash: str,
        screen_desc: ScreenDescription
    ) -> Optional[Dict[str, Any]]:
        """
        Select next action using pure DFS algorithm.

        Implements depth-first search without LLM:
        1. If state is new, add to stack
        2. If untested actions exist, select one (DEEPEN)
        3. If state exhausted, execute BACK (BACKTRACK)
        4. If stack empty, exploration complete

        Args:
            screen_hash: Structural hash of current state
            screen_desc: Parsed screen description

        Returns:
            Action dictionary or None if exploration complete
        """
        logger.debug(f"DFS: Processing state {screen_hash[:8]}, depth={self.current_depth}")

        # DEBUG: Show raw screen description from parser
        logger.info("=" * 80)
        logger.info(f"📋 RAW SCREEN DESCRIPTION (hash={screen_hash[:8]}):")
        logger.info(f"   Activity: {screen_desc.activity}")
        all_actions_raw = screen_desc.get_all_actions()
        logger.info(f"   Total items: {len(screen_desc.items)}")
        logger.info(f"   Total actions: {len(all_actions_raw)}")
        logger.info("")
        # Show ALL items with actions (not just first 10)
        items_with_actions = [item for item in screen_desc.items if item.actions]
        for item in items_with_actions:
            logger.info(f"   - {item.base_description}")
            for action in item.actions:
                coords = action.get_execution_coordinates()
                bounds = action.target_view.get('bounds', [])
                logger.info(f"      • ID={action.id} {action.text} coords={coords} bounds={bounds}")
        items_without_actions = len(screen_desc.items) - len(items_with_actions)
        if items_without_actions > 0:
            logger.info(f"   ... and {items_without_actions} items without actions")
        logger.info("=" * 80)

        # Get or create node in graph
        if screen_hash not in self.graph.states:
            node = self.graph.get_or_create_state(
                screen_hash,
                screen_desc.activity,
                screen_desc
            )

            parent_hash = self.state_stack[-1].screen_hash if self.state_stack else None

            dfs_state = DFSState(
                screen_hash=screen_hash,
                depth=self.current_depth,
                parent_hash=parent_hash,
                untested_count=node.total_actions
            )
            self.state_stack.append(dfs_state)
            self.visited_states.add(screen_hash)

            logger.info(f"✨ DFS: NEW state at depth {self.current_depth}, {node.total_actions} actions")
            logger.info(f"   Hash: {screen_hash[:16]}... (full: {screen_hash})")
        else:
            node = self.graph.states[screen_hash]
            logger.info(f"🔄 DFS: REVISITED state (visit {node.visit_count}, executed: {len(node.executed_actions)})")
            logger.info(f"   Hash: {screen_hash[:16]}... (full: {screen_hash})")
            logger.info(f"   Previously executed actions: {sorted(node.executed_actions)}")

        # Get untested actions
        all_actions = screen_desc.get_all_actions()

        # Filter out system actions (SYSTEM_BACK, RESTART_APP)
        # Also filter actions in navigation bar area (y > 1794 in device space)
        # DFS controls navigation algorithmically, doesn't need system actions
        filtered_actions = []
        for action in all_actions:
            # Skip system actions
            if action.target_view.get('system_action', False):
                logger.debug(f"🚫 Filtering system action: ID={action.id} {action.text[:50]}")
                continue

            # Skip actions in navigation bar area (below y=1794)
            coords = action.get_execution_coordinates()
            if coords:
                x, y = coords
                # These are device coordinates from the dump (1080x1920)
                bounds = action.target_view.get('bounds', [])
                if y > 1794:  # Navigation bar starts at y=1794 in device space
                    logger.info(f"🚫 Filtering nav bar: ID={action.id} '{action.text[:40]}' coords=({x},{y}) bounds={bounds}")
                    continue

            filtered_actions.append(action)

        all_actions = filtered_actions

        # CRITICAL DEBUG: Trace untested filtering logic
        logger.info(f"🔍 FILTERING - State {screen_hash[:8]} has {len(node.executed_actions)} executed actions: {sorted(node.executed_actions)}")

        untested = []
        for action in all_actions:
            if action.id in node.executed_actions:
                logger.debug(f"   ❌ SKIP ID={action.id} (already executed) - {action.text[:40] if action.text else 'no-text'}")
            else:
                logger.debug(f"   ✅ KEEP ID={action.id} (untested) - {action.text[:40] if action.text else 'no-text'}")
                untested.append(action)

        # DEBUG: Show detailed state
        logger.info(f"📊 DFS DEBUG - State {screen_hash[:8]}:")
        logger.info(f"   Total actions: {len(all_actions)}")
        logger.info(f"   Executed: {len(node.executed_actions)} → {sorted(node.executed_actions)}")
        logger.info(f"   Untested: {len(untested)}")

        if untested:
            logger.info(f"   Available untested actions:")
            for i, action in enumerate(untested[:5]):  # Show first 5
                mop = "[DM]" if action.directly_reaches_mop else "[M]" if action.reaches_mop else ""
                logger.info(f"      {i+1}. ID={action.id} {action.text[:50] if action.text else 'no-text'} {mop}")

        # DEEPEN: Explore untested action
        if untested:
            # Prioritize by MOP markers
            priority_sorted = sorted(
                untested,
                key=lambda a: self._get_mop_priority(a),
                reverse=True
            )

            top_action = priority_sorted[0]
            self.current_depth += 1

            action_dict = self._action_to_dict(top_action)

            # CRITICAL: Mark action as executed BEFORE execution (to handle crashes)
            # If action crashes the app, at least it won't be repeated
            logger.info(f"✅ DFS DEEPEN: {action_dict['action_type']} ID={top_action.id} (priority {self._get_mop_priority(top_action)})")
            logger.info(f"   🔒 Pre-marking action ID={top_action.id} as executed on state {screen_hash[:8]}")
            self.graph.record_action(screen_hash=screen_hash, action_id=top_action.id)

            return action_dict

        # BACKTRACK: No untested actions
        logger.info(f"⬅️  DFS BACKTRACK: State exhausted ({len(all_actions)} actions all tested)")

        if self.state_stack:
            self.state_stack.pop()
            self.current_depth = max(0, self.current_depth - 1)

        return {"action_type": "BACK"}

    def select_untested_action(
        self,
        screen_hash: str,
        screen_desc: ScreenDescription
    ) -> Optional[Dict[str, Any]]:
        """
        Select untested action for fallback in hybrid mode.

        Used when loop is detected - provides algorithmic fallback
        that continues systematic exploration.

        Args:
            screen_hash: Structural hash of current state
            screen_desc: Parsed screen description

        Returns:
            Untested action with highest priority, or None
        """
        node = self.graph.states.get(screen_hash)
        if not node:
            return None

        all_actions = screen_desc.get_all_actions()
        untested = [
            action for action in all_actions
            if action.id not in node.executed_actions
        ]

        if not untested:
            return None

        # Prioritize by MOP markers
        priority_sorted = sorted(
            untested,
            key=lambda a: self._get_mop_priority(a),
            reverse=True
        )

        top_action = priority_sorted[0]

        logger.info(f"DFS Fallback: Selected untested action (priority {self._get_mop_priority(top_action)})")

        return self._action_to_dict(top_action)

    def _get_mop_priority(self, action: Any) -> int:
        """
        Compute priority score for action.

        ### Priority Levels:
        - 3: [DM] - Directly reaches monitored operation
        - 2: [M] - Reaches monitored operation transitively
        - 1: No marker - Regular action

        Args:
            action: ItemAction from ScreenDescription

        Returns:
            Priority score (higher = more important)
        """
        if getattr(action, 'directly_reaches_mop', False):
            return 3  # [DM]
        elif getattr(action, 'reaches_mop', False):
            return 2  # [M]
        else:
            return 1  # no marker

    def _action_to_dict(self, action: Any) -> Dict[str, Any]:
        """
        Convert ItemAction to action dictionary.

        Args:
            action: ItemAction from ScreenDescription

        Returns:
            Action dictionary with type, coordinates, description, ID
        """
        # Get action type - default to CLICK for interactive elements
        action_type = "CLICK"

        # For EditText, use TYPE_TEXT
        if hasattr(action, 'class_name') and 'EditText' in action.class_name:
            action_type = "TYPE_TEXT"

        # Get coordinates from action and convert to optimized space
        x, y = 0, 0
        if hasattr(action, 'coordinates') and action.coordinates:
            device_x, device_y = action.coordinates
            # Convert from device space (1080x1920) to optimized space (704x1248)
            # This matches what the LLM generates in optimized screenshots
            x = int(device_x * 704 / 1080)
            y = int(device_y * 1248 / 1920)

        # Get description
        description = ""
        if hasattr(action, 'text') and action.text:
            description = action.text
        elif hasattr(action, 'content_desc') and action.content_desc:
            description = action.content_desc
        elif hasattr(action, 'resource_id') and action.resource_id:
            description = action.resource_id.split('/')[-1]

        return {
            "action_type": action_type,
            "x": x,
            "y": y,
            "description": description,
            "id": action.id
        }

    def _format_action(self, action: Any) -> str:
        """
        Format action for display in guidance.

        Args:
            action: ItemAction from ScreenDescription

        Returns:
            Human-readable action description
        """
        desc = ""
        if hasattr(action, 'text') and action.text:
            desc = action.text
        elif hasattr(action, 'content_desc') and action.content_desc:
            desc = action.content_desc
        elif hasattr(action, 'resource_id') and action.resource_id:
            desc = action.resource_id.split('/')[-1]

        mop_marker = ""
        if getattr(action, 'directly_reaches_mop', False):
            mop_marker = " [DM]"
        elif getattr(action, 'reaches_mop', False):
            mop_marker = " [M]"

        return f"{desc}{mop_marker}" if desc else f"Action {action.id}{mop_marker}"
