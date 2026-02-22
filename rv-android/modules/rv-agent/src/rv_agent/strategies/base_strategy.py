"""
Base interface for graph exploration strategies.

Defines the contract for algorithm-based exploration strategies (DFS, BFS, etc.)
that operate independently of LLM guidance. These strategies implement graph
traversal algorithms for systematic state space exploration.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from rv_screen_parser.parser.screen.visitor.model import ItemAction, ScreenDescription


class ExplorationStrategy(ABC):
    """
    Abstract base class for graph exploration strategies.

    ### Architectural Decisions:
    - Implements pure algorithmic exploration (no LLM integration)
    - Operates on state graph with coordinate-based action tracking
    - Provides action selection based on traversal algorithm
    - Supports static analysis guidance for MOP prioritization
    - Maintains algorithm-specific state (e.g., stack for DFS, queue for BFS)

    ### Role in the System:
    - Defines interface for DFS, BFS, and future traversal algorithms
    - Selects next action based on algorithm logic and state history
    - Tracks visited states and unexplored transitions
    - Integrates static analysis data for prioritization

    ### Integration Points:
    - Used by RoutingManager in pure_algorithm mode
    - Queries DynamicStateGraph for state history
    - Accesses ScreenDescription for available actions
    - Tracks actions by coordinates for non-deterministic UI parsing
    """

    @abstractmethod
    def select_next_action(
        self, current_hash: str, screen_desc: ScreenDescription
    ) -> Optional[ItemAction]:
        """
        Select next action to execute based on traversal algorithm.

        Args:
            current_hash: Structural hash of current UI state
            screen_desc: Parsed screen with UI elements and actions

        Returns:
            Selected ItemAction to execute, or None if exploration complete

        ### Implementation Requirements:
        - Must prioritize untested actions (track by coordinates)
        - Should incorporate MOP markers for prioritization if available
        - Must handle backtracking when current state is exhausted
        - Should track visited states to avoid infinite loops
        """

    @abstractmethod
    def record_transition(self, from_hash: str, to_hash: str, action: ItemAction):
        """
        Record state transition for strategy bookkeeping.

        Args:
            from_hash: Structural hash of source state
            to_hash: Structural hash of destination state
            action: Action that triggered the transition

        ### Implementation Requirements:
        - Must update algorithm-specific state (stack/queue)
        - Should track action by coordinates for repeatability
        - Must handle new state discovery and backtracking logic
        """

    @abstractmethod
    def should_backtrack(self, current_hash: str) -> bool:
        """
        Determine if backtracking is needed from current state.

        Args:
            current_hash: Structural hash of current state

        Returns:
            True if should backtrack, False if should continue exploring

        ### Implementation Requirements:
        - Must check if current state has unexplored actions
        - Should consider algorithm-specific backtracking conditions
        - Must handle dead-end states appropriately
        """

    @abstractmethod
    def reset(self):
        """
        Reset strategy state for new exploration session.

        ### Implementation Requirements:
        - Must clear all algorithm-specific state
        - Should reset visited states tracking
        - Must clear transition history
        """

    def _get_action_signature(self, action: ItemAction) -> Tuple[Tuple[int, int], str]:
        """
        Generate unique signature for action based on coordinates and type.

        Uses coordinates instead of IDs to handle non-deterministic UIAutomator
        parsing where element IDs may change between visits to the same screen.

        Args:
            action: ItemAction to generate signature for

        Returns:
            Tuple of ((x, y), action_type) as unique identifier
        """
        # Use center of bounds as stable coordinate reference
        if action.bounds and len(action.bounds) == 2:
            x1, y1 = action.bounds[0]
            x2, y2 = action.bounds[1]
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
        else:
            center_x, center_y = (0, 0)

        return ((center_x, center_y), action.action_type)

    def _has_mop_marker(self, action: ItemAction) -> bool:
        """
        Check if action has MOP marker for prioritization.

        Args:
            action: ItemAction to check

        Returns:
            True if action has MOP marker
        """
        return getattr(action, "directly_reaches_mop", False) or getattr(
            action, "reaches_mop", False
        )

    def _is_direct_mop(self, action: ItemAction) -> bool:
        """
        Check if action directly reaches MOP.

        Args:
            action: ItemAction to check

        Returns:
            True if action directly reaches MOP
        """
        return getattr(action, "directly_reaches_mop", False)

    def _try_generate_text_input(
        self, screen_desc: ScreenDescription, node, probability: float = 0.2
    ) -> Optional[ItemAction]:
        """
        Try to generate SET_TEXT action for EditText fields.

        This provides algorithmic text input capability with configurable probability.
        Useful for exploring form-based applications (71% of dataset has EditText fields).

        ### Strategy:
        - Activates with specified probability (default 20%)
        - Filters for EditText elements only
        - Selects untested EditText with lowest interaction count
        - Generates appropriate text based on hints/resource_id
        - Creates SET_TEXT ItemAction with inferred text

        Args:
            screen_desc: Parsed screen with UI elements
            node: ScreenNode with execution history
            probability: Probability of generating text input (0.0-1.0)

        Returns:
            SET_TEXT ItemAction if generated, None otherwise
        """
        import random

        # Probability gate: only proceed 20% of the time
        if random.random() > probability:
            return None

        # Filter for EditText elements
        text_fields = []
        for item in screen_desc.items:
            elem_class = item.view.get("class", "")
            if "EditText" in elem_class or "AutoCompleteTextView" in elem_class:
                # Get coordinates for this EditText
                bounds = item.view.get("bounds")
                if bounds and len(bounds) == 2:
                    x1, y1 = bounds[0]
                    x2, y2 = bounds[1]
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2

                    # Check if this EditText has been interacted with
                    # Use same signature format as regular actions
                    signature = ((center_x, center_y), "SET_TEXT")

                    # Convert to optimized space for comparison
                    from rv_agent.services import coordinate_utils

                    opt_x, opt_y = coordinate_utils.device_to_optimized(
                        center_x,
                        center_y,
                        (1080, 1920),  # device dimensions
                        (704, 1248),  # optimized dimensions
                    )
                    opt_signature = ((opt_x, opt_y), "SET_TEXT")

                    # Only consider if not yet executed
                    if opt_signature not in node.executed_actions:
                        text_fields.append(
                            {
                                "item": item,
                                "center_x": center_x,
                                "center_y": center_y,
                                "signature": signature,
                            }
                        )

        if not text_fields:
            return None

        # Select first untested EditText
        target = text_fields[0]
        item = target["item"]

        # Infer appropriate text based on hints
        hint = item.view.get("content_desc", "").lower()
        hint += " " + item.view.get("hint", "").lower()
        hint += " " + item.view.get("text", "").lower()
        hint += " " + item.view.get("resource_id", "").lower()

        # Determine text based on hints
        if "email" in hint or "e-mail" in hint or "mail" in hint:
            text = "test@example.com"
        elif "passw" in hint or "senha" in hint or "pwd" in hint:
            text = "Test123!"
        elif "name" in hint or "nome" in hint or "usuario" in hint or "user" in hint:
            text = "TestUser"
        elif "phone" in hint or "tel" in hint or "fone" in hint or "celular" in hint:
            text = "5511999999999"
        elif (
            "search" in hint or "busca" in hint or "pesquis" in hint or "query" in hint
        ):
            text = "test"
        elif "url" in hint or "site" in hint or "web" in hint or "link" in hint:
            text = "https://example.com"
        elif "number" in hint or "numero" in hint or "num" in hint:
            text = "123"
        elif "age" in hint or "idade" in hint:
            text = "25"
        elif (
            "message" in hint or "mensagem" in hint or "texto" in hint or "note" in hint
        ):
            text = "Test message"
        else:
            # Generic text for unknown fields
            text = "test123"

        # Create SET_TEXT ItemAction
        # We need to create an ItemAction object that represents typing text
        # id must be int, event is required, text describes the action
        from rv_screen_parser.parser.screen.visitor.model import WidgetEventType

        # Use hash of signature as unique int id
        action_id = hash(target["signature"]) & 0x7FFFFFFF  # Ensure positive int

        text_action = ItemAction(
            id=action_id,
            text=f"SET_TEXT ({text})",  # Action description in standard format
            event=WidgetEventType.TEXT_CHANGE,  # Text input event type
            target_view=item.view,
            coordinates=(target["center_x"], target["center_y"]),
        )

        import logging

        logger = logging.getLogger(__name__)
        resource_id = item.view.get("resource_id", "EditText").split("/")[-1]
        logger.info(f"📝 Algorithm generating SET_TEXT: '{text}' for {resource_id}")
        logger.info(f"   Hint analysis: {hint[:100]}...")

        return text_action

    def _detect_scrollable_containers(
        self, screen_desc: ScreenDescription
    ) -> List[Dict[str, Any]]:
        """
        Detect scrollable containers in the current screen.

        Identifies containers that can be scrolled to reveal additional content:
        - RecyclerView: Most common in modern Android apps
        - ScrollView: Traditional scrolling container
        - ListView: Legacy list implementation
        - NestedScrollView: For nested scrolling scenarios
        - HorizontalScrollView: For horizontal scrolling

        Args:
            screen_desc: Parsed screen description

        Returns:
            List of scrollable container info dicts with:
            - bounds: Container bounds [[x1, y1], [x2, y2]]
            - center: (center_x, center_y)
            - scrollable_type: Type of scrollable container
            - direction: 'vertical', 'horizontal', or 'both'
        """
        import logging

        logger = logging.getLogger(__name__)

        # Scrollable container types (ordered: more specific patterns first)
        # HorizontalScrollView must come before ScrollView to avoid false matches
        SCROLLABLE_TYPES = [
            ("HorizontalScrollView", "horizontal"),
            ("NestedScrollView", "vertical"),
            ("RecyclerView", "vertical"),
            ("ScrollView", "vertical"),
            ("ListView", "vertical"),
            ("ViewPager2", "horizontal"),
            ("ViewPager", "horizontal"),
        ]

        scrollables = []

        for item in screen_desc.items:
            view = item.view
            elem_class = view.get("class", "")

            # Check if this is a scrollable container
            scrollable_type = None
            direction = None

            for scroll_type, default_dir in SCROLLABLE_TYPES:
                if scroll_type in elem_class:
                    scrollable_type = scroll_type
                    direction = default_dir
                    break

            # Also check scrollable attribute
            if not scrollable_type and view.get("scrollable", False):
                scrollable_type = "scrollable"
                direction = "vertical"  # Default to vertical

            if scrollable_type:
                bounds = view.get("bounds", [])
                if bounds and len(bounds) == 2:
                    x1, y1 = bounds[0]
                    x2, y2 = bounds[1]
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2

                    # Skip if too small (likely not a content area)
                    width = x2 - x1
                    height = y2 - y1
                    if width < 100 or height < 100:
                        continue

                    scrollables.append(
                        {
                            "bounds": bounds,
                            "center": (center_x, center_y),
                            "scrollable_type": scrollable_type,
                            "direction": direction,
                            "resource_id": view.get("resource_id", ""),
                            "width": width,
                            "height": height,
                        }
                    )

                    logger.debug(
                        f"Found scrollable: {scrollable_type} at ({center_x}, {center_y}) "
                        f"direction={direction} size={width}x{height}"
                    )

        return scrollables

    def _try_generate_scroll_action(
        self,
        screen_desc: ScreenDescription,
        node,
        scrolled_positions: set,
        probability: float = 0.3,
    ) -> Optional[ItemAction]:
        """
        Try to generate SWIPE action for scrollable containers.

        This reveals hidden content in lists, feeds, and scrollable views.
        Uses a probability gate and tracks scrolled positions to avoid
        infinite scrolling loops.

        Args:
            screen_desc: Parsed screen description
            node: ScreenNode with execution history
            scrolled_positions: Set of already scrolled (screen_hash, container_id, direction)
            probability: Probability of generating scroll action (0.0-1.0)

        Returns:
            SWIPE ItemAction if generated, None otherwise
        """
        import logging
        import random

        logger = logging.getLogger(__name__)

        # Probability gate
        if random.random() > probability:
            return None

        # Detect scrollable containers
        scrollables = self._detect_scrollable_containers(screen_desc)

        if not scrollables:
            return None

        # Filter out already-scrolled containers
        screen_hash = getattr(node, "screen_hash", "unknown")
        unscrolled = []

        for container in scrollables:
            container_id = f"{container['resource_id']}|{container['bounds']}"
            scroll_key = (screen_hash, container_id, container["direction"])

            if scroll_key not in scrolled_positions:
                unscrolled.append((container, container_id))

        if not unscrolled:
            logger.debug("All scrollable containers already scrolled on this screen")
            return None

        # Select first unscrolled container
        target_container, container_id = unscrolled[0]

        # Calculate swipe coordinates based on direction
        center_x, center_y = target_container["center"]

        if target_container["direction"] == "vertical":
            # Swipe up to scroll down (reveal more content below)
            start_x = center_x
            start_y = center_y + target_container["height"] // 4  # Start lower
            end_x = center_x
            end_y = center_y - target_container["height"] // 4  # End higher
        else:  # horizontal
            # Swipe left to scroll right (reveal more content to the right)
            start_x = center_x + target_container["width"] // 4
            start_y = center_y
            end_x = center_x - target_container["width"] // 4
            end_y = center_y

        # Mark as scrolled
        scroll_key = (screen_hash, container_id, target_container["direction"])
        scrolled_positions.add(scroll_key)

        # Create SWIPE ItemAction
        from rv_screen_parser.parser.screen.visitor.model import WidgetEventType

        # Use hash as unique int id
        action_id = hash((start_x, start_y, end_x, end_y)) & 0x7FFFFFFF

        swipe_action = ItemAction(
            id=action_id,
            text=f"SWIPE ({target_container['direction']})",
            event=WidgetEventType.SCROLL,
            target_view={
                "class": target_container["scrollable_type"],
                "bounds": target_container["bounds"],
                "resource_id": target_container["resource_id"],
                "swipe_start": (start_x, start_y),
                "swipe_end": (end_x, end_y),
            },
            coordinates=(start_x, start_y),  # Start coordinates
        )

        logger.info(
            f"📜 Generating SWIPE action: {target_container['scrollable_type']} "
            f"({target_container['direction']}) from ({start_x}, {start_y}) to ({end_x}, {end_y})"
        )

        return swipe_action
