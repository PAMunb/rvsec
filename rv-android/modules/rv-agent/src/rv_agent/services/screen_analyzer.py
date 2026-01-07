"""
Screen parsing and UI element formatting for agent interaction.

Processes UIAutomator dumps into ScreenDescription objects and formats
UI elements for LLM consumption with coordinate transformations.
"""

import logging
import time
from typing import Optional, Tuple, Dict, Any

from rv_screen_parser.constants import ScreenParserType
from rv_screen_parser.parser.screen.parser_factory import ParserFactory
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ScreenItem
from rv_android_core.domain.static import StaticAnalysisData
from rv_agent.ui.rvagent_visitor import RVAgentVisitor
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph, compute_screen_hash_from_description
from rv_agent.agent.device_interface import DeviceInterface
from rv_agent.memory.ui_coverage import UICoverageTracker


class ScreenProcessor:
    """
    Processes UI state and formats elements for agent consumption.

    ### Architectural Decisions:
    - Centralizes UI parsing and formatting logic
    - Transforms coordinates from device to optimized space
    - Categorizes UI elements by interaction type
    - Provides MOP marker integration for static analysis guidance
    - Handles external navigation detection and app restart

    ### Role in the System:
    - Captures and parses UIAutomator dumps
    - Generates ScreenDescription objects
    - Formats UI elements for LLM prompts
    - Computes screen hashes for state tracking
    - Detects and handles external navigation

    ### Integration Points:
    - Used by RVAgent parse_ui node
    - Provides input for LLM prompts
    - Supplies data to DynamicStateGraph
    - Works with coordinate conversion utilities
    """

    def __init__(
        self,
        device: DeviceInterface,
        dynamic_graph: DynamicStateGraph,
        ui_coverage: Optional[UICoverageTracker] = None,
        static_data: Optional[StaticAnalysisData] = None,
        device_dimensions: Tuple[int, int] = (1080, 1920),
        max_external_attempts: int = 3
    ):
        """
        Initialize screen processor.

        Args:
            device: Device interface for UI state capture
            dynamic_graph: Graph for state transition tracking
            ui_coverage: UI coverage tracker for element annotations
            static_data: Optional static analysis data for MOP markers
            device_dimensions: Device screen size (width, height)
            max_external_attempts: Maximum external navigation attempts before restart
        """
        self.device = device
        self.dynamic_graph = dynamic_graph
        self.ui_coverage = ui_coverage
        self.static_data = static_data
        self.device_dimensions = device_dimensions
        self.max_external_attempts = max_external_attempts

        # Initialize UI parser using factory pattern with RVAgentVisitor
        # for full static analysis integration (MOP markers, WTG navigation)
        self.parser = ParserFactory.create(
            ScreenParserType.UIAUTOMATOR,
            visitor_class=RVAgentVisitor
        )

        self.logger = logging.getLogger(__name__)

    def parse_current_screen(
        self,
        target_package: str,
        external_navigation_count: int = 0
    ) -> Dict[str, Any]:
        """
        Parse current UI state and detect external navigation.

        Args:
            target_package: Target application package name
            external_navigation_count: Current count of external navigations

        Returns:
            Dictionary with:
            - screen_hash: Structural hash of UI state
            - activity: Current activity name
            - screen_description: Parsed ScreenDescription object
            - is_external: Whether navigated outside target app
            - external_navigation_count: Updated external count
            - restart_occurred: Whether app was restarted
        """
        self.logger.info("Capturing and parsing UI state")

        # Get current UI state
        ui_state = self.device.get_current_ui_state()

        # Check external navigation
        current_package = ui_state.get('current_package', '')
        is_external = current_package and current_package != target_package

        # DEBUG: Always log package comparison
        self.logger.info(
            f"📦 PACKAGE CHECK: current='{current_package}' vs target='{target_package}' "
            f"-> is_external={is_external}, count={external_navigation_count}"
        )

        restart_occurred = False

        if is_external:
            external_navigation_count += 1
            self.logger.warning(
                f"External navigation: {current_package} "
                f"(attempt {external_navigation_count}/{self.max_external_attempts})"
            )

            # Restart app after max attempts
            if external_navigation_count >= self.max_external_attempts:
                self.logger.info("Max external attempts reached, restarting app")
                self._restart_app(target_package)
                restart_occurred = True
                external_navigation_count = 0

                # Re-capture state after restart
                time.sleep(2)
                ui_state = self.device.get_current_ui_state()
        else:
            # Reset counter when back in target app
            if external_navigation_count > 0:
                self.logger.info("Returned to target app")
                external_navigation_count = 0

        # Parse screen
        screen_description = self.parser.parse_screen(
            {"hierarchy": ui_state['xml'], "activity": ui_state['current_activity']},
            static_data=self.static_data
        )

        # Compute screen hash
        screen_hash = compute_screen_hash_from_description(screen_description)

        # Format UI elements for LLM/display
        ui_elements_text = self.format_ui_elements(screen_description)

        # Annotate elements with UI coverage status
        if self.ui_coverage:
            ui_elements_text = self.ui_coverage.annotate_screen_elements(ui_elements_text, screen_hash)
            self.logger.debug("UI coverage annotations applied")

        self.logger.info(f"Activity: {ui_state['current_activity']}")
        self.logger.info(f"Screen hash: {screen_hash[:12]}...")
        self.logger.info(f"UI elements: {len(screen_description.items)}")

        return {
            "screen_hash": screen_hash,
            "activity": ui_state['current_activity'],
            "screen_description": screen_description,
            "ui_elements_text": ui_elements_text,
            "is_external": is_external,
            "external_navigation_count": external_navigation_count,
            "restart_occurred": restart_occurred,
            # INSTRUMENTATION: Raw XML for hit classification
            "ui_xml": ui_state.get('xml', '')
        }

    def format_ui_elements(self, screen_description: ScreenDescription) -> str:
        """
        Format UI elements for LLM consumption with coordinate transformation.

        Categorizes elements into:
        1. Text Input Fields (EditText) - for SET_TEXT actions
        2. Dropdown Selectors (Spinner) - for selection flows
        3. Clickable Elements - buttons, images, etc.

        All coordinates are transformed to optimized space before presentation.

        Args:
            screen_description: Parsed screen description

        Returns:
            Formatted string with categorized UI elements
        """
        if not screen_description or not screen_description.items:
            return "No interactive elements found."

        # Categorize elements
        text_inputs = []
        spinners = []
        clickable_items = []

        for item in screen_description.items:
            if not item.view.get('clickable', False):
                continue

            elem_class = item.view.get('class', '')
            if 'EditText' in elem_class or 'AutoCompleteTextView' in elem_class:
                text_inputs.append(item)
            elif 'Spinner' in elem_class:
                spinners.append(item)
            else:
                clickable_items.append(item)

        # Check if we have any elements
        if not text_inputs and not spinners and not clickable_items:
            return "No interactive elements found."

        lines = []

        # Text input fields section
        if text_inputs:
            lines.extend([
                "=== TEXT INPUT FIELDS ===",
                "Use android_type_text() tool for these elements, NOT android_click()",
                ""
            ])
            for i, item in enumerate(text_inputs[:5], 1):
                desc = self._format_element(i, item, "TEXT INPUT")
                if desc:
                    lines.append(desc)
            lines.append("")

        # Dropdown selectors section
        if spinners:
            lines.extend([
                "=== DROPDOWN SELECTORS ===",
                "Use android_click() to open dropdown, then select option in next iteration",
                ""
            ])
            for i, item in enumerate(spinners[:5], 1):
                desc = self._format_element(i, item, "DROPDOWN")
                if desc:
                    lines.append(desc)
            lines.append("")

        # Clickable elements section
        if clickable_items:
            lines.extend([
                "=== CLICKABLE ELEMENTS ===",
                "Use android_click() for buttons, images, checkboxes, switches, icons",
                ""
            ])
            for i, item in enumerate(clickable_items[:10], 1):
                desc = self._format_element(i, item, None)
                if desc:
                    lines.append(desc)
            lines.append("")

        # Add coordinate system info
        lines.extend([
            "Coordinates are normalized [0, 1000) range",
            "Use EXACT coordinates from 'at position (x, y)' for tool calls"
        ])

        # Log categorization
        total_count = len(screen_description.items)
        self.logger.debug(
            f"UI description: {total_count} total, "
            f"{len(text_inputs)} text inputs, "
            f"{len(spinners)} spinners, "
            f"{len(clickable_items)} clickable"
        )

        if text_inputs:
            self.logger.info(f"{len(text_inputs)} text input field(s) detected - must use android_type_text")
        if spinners:
            self.logger.info(f"{len(spinners)} spinner(s) detected - click to open dropdown")

        return "\n".join(lines)

    def _format_element(
        self,
        index: int,
        item: ScreenItem,
        category_label: Optional[str] = None
    ) -> str:
        """
        Format single element with normalized [0, 1000) coordinates.

        Coordinates are normalized to [0, 1000) range to match Qwen3-VL's
        coordinate system. When LLM copies these coords, ActionNormalizer
        converts them back to device pixels correctly.

        Args:
            index: Element index in list
            item: ScreenItem to format
            category_label: Optional category label (e.g., "TEXT INPUT")

        Returns:
            Formatted element description or empty string if invalid bounds
        """
        elem_type = item.view.get('class', 'View').split('.')[-1]
        text = item.view.get('text', '')
        resource_id = item.view.get('resource_id', '').split('/')[-1]
        bounds = item.view.get('bounds')

        # Validate bounds
        if not (bounds and len(bounds) == 2 and len(bounds[0]) == 2 and len(bounds[1]) == 2):
            self.logger.debug(f"Element {index} has invalid bounds: {bounds}")
            return ""

        # Calculate center in device space
        device_center_x = (bounds[0][0] + bounds[1][0]) // 2
        device_center_y = (bounds[0][1] + bounds[1][1]) // 2

        # Convert to normalized [0, 1000) coordinates
        # This matches Qwen3-VL's coordinate system
        device_width, device_height = self.device_dimensions
        norm_x = int((device_center_x / device_width) * 1000)
        norm_y = int((device_center_y / device_height) * 1000)

        # Build description
        desc_parts = [f"{index}."]
        if category_label:
            desc_parts.append(f"[{category_label}]")
        desc_parts.append(elem_type)

        if text:
            desc_parts.append(f"'{text}'")
        if resource_id:
            desc_parts.append(f"({resource_id})")

        desc = " ".join(desc_parts)
        desc += f" at position ({norm_x}, {norm_y})"

        # Add actions and MOP markers
        if hasattr(item, 'actions') and item.actions:
            actions_text = ", ".join(action.text for action in item.actions if hasattr(action, 'text'))
            if actions_text:
                desc += f". Actions: {actions_text}"

            action = item.actions[0]
            if action.directly_reaches_mop:
                desc += " [DM]"
            elif action.reaches_mop:
                desc += " [M]"

        return desc

    def _restart_app(self, package_name: str):
        """
        Restart application.

        Args:
            package_name: Package name to restart
        """
        self.logger.info(f"Restarting app: {package_name}")
        self.device.stop_app(package_name)
        time.sleep(1)
        self.device.start_app(package_name)
        time.sleep(2)

    def detect_ui_mutation(
        self,
        before_desc: ScreenDescription,
        after_desc: ScreenDescription
    ) -> bool:
        """
        Detect subtle UI state changes even when structural hash is the same.

        Compares state attributes (enabled, checked, selected) between two
        screen descriptions to detect mutations that don't change the UI structure
        but affect interactivity.

        This is useful for detecting:
        - Buttons that become enabled after form validation
        - Checkboxes that get checked/unchecked
        - List items that get selected

        Args:
            before_desc: Screen description before action
            after_desc: Screen description after action

        Returns:
            True if UI mutation detected, False otherwise
        """
        if len(before_desc.items) != len(after_desc.items):
            # Element count changed - this is a structural change, not a mutation
            return True

        # Build element maps for robust comparison
        before_map = self._build_element_map(before_desc.items)
        after_map = self._build_element_map(after_desc.items)

        # Compare elements that exist in both states
        for element_id, before_view in before_map.items():
            if element_id not in after_map:
                # Element removed/added - structural change
                continue

            after_view = after_map[element_id]

            # Check for state mutations
            if before_view.get('enabled') != after_view.get('enabled'):
                self.logger.info(f"UI Mutation: 'enabled' changed for {element_id[:50]}")
                return True

            if before_view.get('checked') != after_view.get('checked'):
                self.logger.info(f"UI Mutation: 'checked' changed for {element_id[:50]}")
                return True

            if before_view.get('selected') != after_view.get('selected'):
                self.logger.info(f"UI Mutation: 'selected' changed for {element_id[:50]}")
                return True

        return False

    def _build_element_map(self, items) -> Dict[str, Dict]:
        """
        Build mapping of elements by unique identifier.

        The identifier is composed of: resource-id + class + bounds
        This ensures correct matching even when UIAutomator returns
        elements in different order between consecutive dumps.

        Args:
            items: List of ScreenItems

        Returns:
            Dict mapping element_id to view dict
        """
        element_map = {}

        for item in items:
            view = item.view

            # Compose unique identifier
            resource_id = view.get('resource-id', '')
            class_name = view.get('class', '')
            bounds = str(view.get('bounds', ''))
            element_id = f"{resource_id}|{class_name}|{bounds}"

            element_map[element_id] = view

        return element_map
