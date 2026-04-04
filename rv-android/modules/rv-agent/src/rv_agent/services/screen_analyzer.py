"""
Process Android UI state for agent consumption.

Parse UIAutomator XML dumps into ScreenDescription objects, format UI
elements with priority scores for LLM prompts, and detect external
navigation away from the target application.

Coordinate normalization converts device pixel bounds to the Qwen3-VL
[0, 1000) coordinate space so that the LLM and ActionNormalizer share
a consistent reference frame. Elements are scored by test status
(UNTESTED > TESTED > WELL-TESTED) with MOP bonuses, then sorted so
the LLM sees the highest-priority actions first.
"""

import logging
import time
from typing import Any, Dict, Optional, Tuple

from rv_agent.agent.device_interface import DeviceInterface
from rv_agent.agent.dynamic_state_graph import (
    DynamicStateGraph,
    compute_screen_hash_from_description,
)
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_agent.ui.rvagent_visitor import RVAgentVisitor
from rv_android_core.domain.static import StaticAnalysisData
from rv_screen_parser.constants import ScreenParserType
from rv_screen_parser.parser.screen.parser_factory import ParserFactory
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ScreenItem

# Launcher packages where pressing BACK does nothing useful.
# When detected, immediately restart instead of wasting iterations.
LAUNCHER_PACKAGES = frozenset(
    {
        "com.google.android.apps.nexuslauncher",
        "com.android.launcher3",
        "com.android.launcher",
    }
)


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
        max_external_attempts: int = 3,
    ):
        """Initialize screen processor.

        Args:
            device: Device interface for UI state capture.
            dynamic_graph: Graph for state transition tracking.
            ui_coverage: UI coverage tracker for element annotations.
            static_data: Optional static analysis data for MOP markers.
            device_dimensions: Device screen size (width, height) in pixels.
            max_external_attempts: Maximum external navigation attempts before
                triggering app restart.

        State:
            self.parser: UIAutomator parser configured with RVAgentVisitor for
                MOP enrichment and global widget search. Created once at init.
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
            ScreenParserType.UIAUTOMATOR, visitor_class=RVAgentVisitor
        )

        self.logger = logging.getLogger(__name__)

    def parse_current_screen(
        self, target_package: str, external_navigation_count: int = 0
    ) -> Dict[str, Any]:
        """Parse current UI state and detect external navigation.

        Args:
            target_package: Target application package name.
            external_navigation_count: Current count of external navigations.

        Returns:
            Dictionary with keys:
            - "screen_hash" (str): Structural hash of UI state.
            - "activity" (str): Current activity name.
            - "screen_description" (ScreenDescription): Parsed screen, or None
                on device communication failure.
            - "ui_elements_text" (str): Formatted element list sorted by score.
            - "is_external" (bool): Whether navigated outside target app.
            - "external_navigation_count" (int): Updated external count.
            - "restart_occurred" (bool): Whether app was restarted.
            - "ui_xml" (str): Raw UIAutomator XML dump.
        """
        self.logger.info("Capturing and parsing UI state")

        # Phase 1: Capture current UI state from device
        ui_state = self.device.get_current_ui_state()

        if ui_state is None:
            self.logger.error(
                "UI state is None (device communication failure), "
                "returning external state to trigger relaunch"
            )
            return self._make_external_fallback_result(external_navigation_count)

        # Phase 2: Detect and handle external navigation
        current_package = ui_state.get("current_package", "")
        is_external = current_package and current_package != target_package

        # DEBUG: Always log package comparison
        self.logger.info(
            f"📦 PACKAGE CHECK: current='{current_package}' vs target='{target_package}' "
            f"-> is_external={is_external}, count={external_navigation_count}"
        )

        restart_occurred = False

        if is_external:
            external_navigation_count += 1

            # Launcher detection: pressing BACK on the home screen does nothing,
            # so immediately trigger restart instead of wasting iterations
            is_launcher = current_package in LAUNCHER_PACKAGES
            if is_launcher:
                self.logger.warning(
                    f"Launcher detected ({current_package}), "
                    "triggering immediate restart"
                )

            self.logger.warning(
                f"External navigation: {current_package} "
                f"(attempt {external_navigation_count}/{self.max_external_attempts})"
            )

            # Restart app after max attempts or immediately on launcher
            if is_launcher or external_navigation_count >= self.max_external_attempts:
                self.logger.info("Max external attempts reached, restarting app")
                restart_occurred = True
                external_navigation_count = (
                    0  # Reset BEFORE restart to prevent infinite loop
                )
                try:
                    self._restart_app(target_package)
                except Exception as e:
                    self.logger.warning(f"App restart failed: {e}")
                # Re-capture state after restart attempt (whether it succeeded or not)
                time.sleep(2)
                ui_state = self.device.get_current_ui_state()
                if ui_state is None:
                    self.logger.error(
                        "UI state is None after restart attempt, "
                        "returning external state to trigger relaunch"
                    )
                    return self._make_external_fallback_result(
                        external_navigation_count
                    )
        else:
            # Reset counter when back in target app
            if external_navigation_count > 0:
                self.logger.info("Returned to target app")
                external_navigation_count = 0

        # Phase 3: Parse screen and format elements for LLM
        screen_description = self.parser.parse_screen(
            {"hierarchy": ui_state["xml"], "activity": ui_state["current_activity"]},
            static_data=self.static_data,
        )

        screen_hash = compute_screen_hash_from_description(screen_description)
        ui_elements_text = self.format_ui_elements(screen_description, screen_hash)

        # Phase 4: Log diagnostics
        untested = ui_elements_text.count("[UNTESTED]")
        tested = ui_elements_text.count("[TESTED-")
        well_tested = ui_elements_text.count("[WELL-TESTED]")
        self.logger.info(
            f"Elements: untested={untested} tested={tested} well_tested={well_tested}"
        )

        self.logger.info(f"Activity: {ui_state['current_activity']}")
        self.logger.info(f"Screen hash: {screen_hash[:12]}...")
        self.logger.info(f"UI elements: {len(screen_description.items)}")

        return {
            "screen_hash": screen_hash,
            "activity": ui_state["current_activity"],
            "screen_description": screen_description,
            "ui_elements_text": ui_elements_text,
            "is_external": is_external,
            "external_navigation_count": external_navigation_count,
            "restart_occurred": restart_occurred,
            "ui_xml": ui_state.get("xml", ""),
        }

    def format_ui_elements(
        self, screen_description: ScreenDescription, screen_hash: str = ""
    ) -> str:
        """Format UI elements with test status, scores, and MOP markers.

        Output format (sorted by score, highest first):
            1. [UNTESTED] Button 'Submit' at position (500, 416) [score:260]
            2. [TESTED-1x] EditText 'Password' at position (500, 312) [score:140]

        Score calculation:
            - Base: UNTESTED=200, TESTED-1x=140, TESTED-2x=98, WELL-TESTED=50
            - MOP bonus: +100 for [DM], +50 for [M]

        Args:
            screen_description: Parsed screen description.
            screen_hash: Screen hash for test count lookup.

        Returns:
            Formatted string with elements sorted by priority score.
        """
        if not screen_description or not screen_description.items:
            return "No interactive elements found."

        # Filter to interactive elements - those with actions created by visitor
        # Exclude system actions (BACK, RESTART) - LLM has dedicated tools for these
        interactive_items = [
            item
            for item in screen_description.items
            if item.actions
            and not item.view.get("class", "").startswith("SystemAction_")
        ]

        if not interactive_items:
            return "No interactive elements found."

        # Process each element with scores
        scored_elements = []
        for item in interactive_items:
            element_data = self._process_element(item, screen_hash)
            if element_data:
                scored_elements.append(element_data)

        if not scored_elements:
            return "No interactive elements found."

        # Sort by score descending
        scored_elements.sort(key=lambda x: x["score"], reverse=True)

        # Format output with sequential numbering
        lines = []
        for i, elem in enumerate(scored_elements, 1):
            line = f"{i}. {elem['tag']} {elem['description']} at position ({elem['x']}, {elem['y']}) [score:{elem['score']}]"
            lines.append(line)

        self.logger.debug(f"Formatted {len(lines)} elements (sorted by score)")

        return "\n".join(lines)

    def _process_element(self, item: ScreenItem, screen_hash: str) -> dict:
        """Process single element into scored description with device-space element IDs.

        Element IDs use device-space coordinates (INV-AGT-40) for consistency with
        register_screen_elements() and find_nearest_element(). The normalized [0,1000)
        coordinates are only used in the text prompt for Qwen3-VL.

        Args:
            item: ScreenItem to process.
            screen_hash: Screen hash for test count lookup.

        Returns:
            Dict with description, tag, score, and coordinates, or None
            if bounds are missing or malformed.
        """
        elem_type = item.view.get("class", "View").split(".")[-1]
        text = item.view.get("text", "")
        bounds = item.view.get("bounds")

        if not (
            bounds and len(bounds) == 2 and len(bounds[0]) == 2 and len(bounds[1]) == 2
        ):
            return None

        # Compute center in device space for element ID tracking (INV-AGT-40)
        device_center_x = (bounds[0][0] + bounds[1][0]) // 2
        device_center_y = (bounds[0][1] + bounds[1][1]) // 2

        # Normalize to [0, 1000) for the LLM text prompt (Qwen3-VL coordinate system)
        device_width, device_height = self.device_dimensions
        norm_x = int((device_center_x / device_width) * 1000)
        norm_y = int((device_center_y / device_height) * 1000)

        test_count = 0
        if self.ui_coverage:
            from rv_agent.memory.element_id import make_element_id

            # Use device-space coordinates for element IDs (matches register_screen_elements)
            element_id = make_element_id(device_center_x, device_center_y)
            test_count = self.ui_coverage.get_element_test_count(element_id)
            # Track element for this screen
            if screen_hash:
                if screen_hash not in self.ui_coverage.screen_elements:
                    self.ui_coverage.screen_elements[screen_hash] = set()
                self.ui_coverage.screen_elements[screen_hash].add(element_id)

        # TODO(#21): Usar os scorers reais do rvagent_strategy (MopScorer, WtgScorer,
        # GradualDecayScorer, ComponentPriorityScorer, etc.) em vez desta versao
        # simplificada. Isso requer passar os scorers como dependencia.
        if test_count == 0:
            tag = "[UNTESTED]"
            base_score = 200
        elif test_count == 1:
            tag = "[TESTED-1x]"
            base_score = 140
        elif test_count <= 3:
            tag = f"[TESTED-{test_count}x]"
            base_score = 98
        else:
            tag = "[WELL-TESTED]"
            base_score = 50

        mop_bonus = 0
        mop_marker = ""
        if hasattr(item, "actions") and item.actions:
            action = item.actions[0]
            if action.directly_reaches_mop:
                mop_bonus = 100
                mop_marker = " [DM]"
            elif action.reaches_mop:
                mop_bonus = 50
                mop_marker = " [M]"

        total_score = base_score + mop_bonus

        content_desc = item.view.get("content_description", "")
        parts = [elem_type]
        if text:
            parts.append(f"'{text}'")
        elif content_desc:
            # Use content description when text is empty (e.g., "Open navigation drawer" for menu)
            parts.append(f"'{content_desc}'")
        description = " ".join(parts) + mop_marker

        return {
            "description": description,
            "tag": tag,
            "score": total_score,
            "x": norm_x,
            "y": norm_y,
            "test_count": test_count,
        }

    def _restart_app(self, package_name: str):
        """Restart application after dismissing any system dialogs.

        Press BACK before relaunching to dismiss modal system dialogs
        (ResolverActivity, permission dialogs, crash dialogs) that would
        otherwise block the launch intent from bringing the target app
        to the foreground.

        Args:
            package_name: Package name to restart.
        """
        self.logger.info(f"Restarting app: {package_name}")

        # Dismiss any system dialog (ResolverActivity, permissions, crash dialogs)
        # that may be blocking the target app from reaching the foreground
        self.device.back()
        time.sleep(1)

        self.device.stop_app(package_name)
        time.sleep(1)
        self.device.start_app(package_name)
        time.sleep(2)

    def _make_external_fallback_result(
        self, external_navigation_count: int
    ) -> Dict[str, Any]:
        """Build a safe fallback result when UI state cannot be captured.

        Return a result dict with is_external=True and restart_occurred=True
        so the caller triggers a relaunch on the next iteration.

        Args:
            external_navigation_count: Current external navigation count.

        Returns:
            Dictionary matching parse_current_screen schema with empty/None
            values and restart_occurred=True to force relaunch.
        """
        return {
            "screen_hash": "",
            "activity": "unknown",
            "screen_description": None,
            "ui_elements_text": "No interactive elements found.",
            "is_external": True,
            "external_navigation_count": external_navigation_count,
            "restart_occurred": True,
            "ui_xml": "",
        }

    def detect_ui_mutation(
        self, before_desc: ScreenDescription, after_desc: ScreenDescription
    ) -> bool:
        """Detect subtle UI state changes even when structural hash is the same.

        Compare state attributes (enabled, checked, selected) between two
        screen descriptions to detect mutations that do not change UI structure
        but affect interactivity. Useful for detecting buttons that become
        enabled after form validation, checkboxes toggled, or list items
        selected.

        Args:
            before_desc: Screen description before action.
            after_desc: Screen description after action.

        Returns:
            True if UI mutation detected, False otherwise.
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
            if before_view.get("enabled") != after_view.get("enabled"):
                self.logger.info(
                    f"UI Mutation: 'enabled' changed for {element_id[:50]}"
                )
                return True

            if before_view.get("checked") != after_view.get("checked"):
                self.logger.info(
                    f"UI Mutation: 'checked' changed for {element_id[:50]}"
                )
                return True

            if before_view.get("selected") != after_view.get("selected"):
                self.logger.info(
                    f"UI Mutation: 'selected' changed for {element_id[:50]}"
                )
                return True

        return False

    def _build_element_map(self, items) -> Dict[str, Dict]:
        """Build mapping of elements by unique identifier.

        The identifier is composed of resource-id + class + bounds, which
        ensures correct matching even when UIAutomator returns elements
        in different order between consecutive dumps.

        Args:
            items: List of ScreenItems.

        Returns:
            Dict mapping element_id to view dict.
        """
        element_map = {}

        for item in items:
            view = item.view
            resource_id = view.get("resource-id", "")
            class_name = view.get("class", "")
            bounds = str(view.get("bounds", ""))
            element_id = f"{resource_id}|{class_name}|{bounds}"

            element_map[element_id] = view

        return element_map
