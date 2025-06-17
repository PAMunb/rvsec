# rvandroid/analysis/screenshot/screenshot_action_complementor.py
"""
Screenshot Action Complementor for RVDroid.

This module provides functionality to complement UI actions by analyzing
screenshots and associating visual elements with UI hierarchy elements.
It enhances testing capabilities by detecting elements not present in the
UI hierarchy and identifying error conditions.
"""

from typing import Dict, Any, List, Optional, Tuple

from rv_android_core.analysis.base_analyzer import BaseAnalyzer
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.widget import WidgetEventType
from rv_screen_parser.parser.screen.visitor.model import ItemAction, ScreenItem, ScreenDescription, Counter
from rv_screen_parser.screenshot.screenshot_analyzer import ScreenshotAnalyzer
from rv_llm.llm.constants import StateEntry


class AssociationStrategy:
    """Base class for element association strategies."""

    def calculate_match_score(self, visual_bounds, ui_element_data):
        """
        Calculate match score between visual and UI elements.

        Args:
            visual_bounds: Bounds of visual element
            ui_element_data: Data of UI element

        Returns:
            Match score between 0.0 and 1.0
        """
        # Default implementation uses overlap percentage
        overlap = self._calculate_overlap_percentage(
            visual_bounds[0][0], visual_bounds[0][1], visual_bounds[1][0], visual_bounds[1][1],
            ui_element_data["bounds"][0][0], ui_element_data["bounds"][0][1],
            ui_element_data["bounds"][1][0], ui_element_data["bounds"][1][1]
        )

        return overlap

    def _calculate_overlap_percentage(self, x1, y1, x2, y2, x3, y3, x4, y4):
        """
        Calculate the percentage of overlap between two rectangles.

        Args:
            x1, y1, x2, y2: First rectangle (top-left, bottom-right)
            x3, y3, x4, y4: Second rectangle (top-left, bottom-right)

        Returns:
            Overlap percentage (0.0 to 1.0) relative to the smaller rectangle
        """
        # Calculate intersection coordinates
        x_intersection = max(x1, x3)
        y_intersection = max(y1, y3)
        w_intersection = min(x2, x4) - x_intersection
        h_intersection = min(y2, y4) - y_intersection

        if w_intersection <= 0 or h_intersection <= 0:
            return 0.0

        intersection_area = w_intersection * h_intersection
        area1 = (x2 - x1) * (y2 - y1)
        area2 = (x4 - x3) * (y4 - y3)
        smaller_area = min(area1, area2)

        return intersection_area / smaller_area if smaller_area > 0 else 0.0


class ErrorAssociationStrategy(AssociationStrategy):
    """Strategy for associating error indicators with UI elements."""

    def calculate_match_score(self, visual_bounds, ui_element_data):
        """
        Calculate match score for error indicators.

        Args:
            visual_bounds: Bounds of error indicator
            ui_element_data: Data of UI element

        Returns:
            Match score between 0.0 and 1.0
        """
        overlap = super().calculate_match_score(visual_bounds, ui_element_data)

        # Prioritize input fields
        item = ui_element_data["item"]
        if "EditText" in item.view.get("class", ""):
            overlap *= 1.2  # Increase score for input fields

        # Prioritize elements that are near but not necessarily overlapping with the error
        if overlap < 0.1:
            # Check if the error is close to (likely below) the element
            visual_center_x = (visual_bounds[0][0] + visual_bounds[1][0]) / 2
            ui_center_x = (ui_element_data["bounds"][0][0] + ui_element_data["bounds"][1][0]) / 2

            # If the centers are aligned horizontally
            if abs(visual_center_x - ui_center_x) < (
                    ui_element_data["bounds"][1][0] - ui_element_data["bounds"][0][0]) / 2:
                # Check if error is below the element (common for validation errors)
                if (visual_bounds[0][1] >= ui_element_data["bounds"][1][1] and
                        visual_bounds[0][1] <= ui_element_data["bounds"][1][1] + 100):  # Within 100px below
                    return 0.7  # High score for typical validation error position

        return overlap


class ButtonAssociationStrategy(AssociationStrategy):
    """Strategy for associating visual buttons with UI elements."""

    def calculate_match_score(self, visual_bounds, ui_element_data):
        """
        Calculate match score for button associations.

        Args:
            visual_bounds: Bounds of visual button
            ui_element_data: Data of UI element

        Returns:
            Match score between 0.0 and 1.0
        """
        overlap = super().calculate_match_score(visual_bounds, ui_element_data)

        # Prioritize actual buttons and clickable elements
        item = ui_element_data["item"]
        if "Button" in item.view.get("class", "") or item.view.get("clickable", False):
            overlap *= 1.1  # Slightly increase score for buttons and clickable elements

        return overlap


class TextAssociationStrategy(AssociationStrategy):
    """Strategy for associating visual text with UI elements."""

    def calculate_match_score(self, visual_bounds, ui_element_data):
        """
        Calculate match score for text associations.

        Args:
            visual_bounds: Bounds of visual text
            ui_element_data: Data of UI element

        Returns:
            Match score between 0.0 and 1.0
        """
        # First calculate overlap as in the parent class
        overlap = super().calculate_match_score(visual_bounds, ui_element_data)

        # We can't access text from bounds (which is a list)
        # Instead, we need to get it from the associated text item data
        # which would be passed separately

        # Consider only the spatial relationship for now
        # Text content similarity would need to be handled in the calling method

        return overlap


class InteractiveElementAssociationStrategy(AssociationStrategy):
    """Strategy for associating interactive elements with UI elements."""

    def calculate_match_score(self, visual_bounds, ui_element_data):
        """
        Calculate match score for interactive element associations.

        Args:
            visual_bounds: Bounds of visual interactive element
            ui_element_data: Data of UI element

        Returns:
            Match score between 0.0 and 1.0
        """
        overlap = super().calculate_match_score(visual_bounds, ui_element_data)

        # Prioritize UI elements that can be interacted with
        item = ui_element_data["item"]
        is_interactive = (
                item.view.get("clickable", False) or
                item.view.get("scrollable", False) or
                item.view.get("long_clickable", False) or
                item.view.get("editable", False)
        )

        if is_interactive:
            overlap *= 1.2  # Increase score for interactive elements

        return overlap


class ScreenshotActionComplementor(BaseAnalyzer[ScreenDescription]):
    """
    Complements screen actions with additional insights from screenshot analysis.

    This component bridges the gap between UI hierarchy-based testing and visual testing
    by associating visually detected elements with UI hierarchy elements. It enables:

    1. Detection of interactive elements not present in the UI hierarchy
    2. Identification of error conditions through visual cues
    3. Enhancement of existing UI elements with visual information

    ### Architectural Decisions:
    - Uses direct object associations rather than ID-based mappings
    - Maintains backward compatibility while enhancing information
    - Separates detection from association for better maintainability
    - Prioritizes error detection and association with input fields

    ### Role in the System:
    - Enhances screen descriptions with visually-derived information
    - Improves testing of non-standard UI elements and canvas-based apps
    - Provides error detection capabilities using visual analysis
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the screenshot action complementor.

        Args:
            static_data: Optional static analysis data
        """
        super().__init__(analyzer_name="screenshot_complementor", static_data=static_data)

        # Action ID counter - start IDs from 1000 to avoid conflicts
        self.counter = Counter(1000)

        # Analysis results
        self.visual_to_ui_associations = {}
        self.error_impacted_items = set()
        self.unmatched_visual_elements = []

        self.logger.info("Initialized screenshot action complementor")

    def _initialize_from_static_data(self) -> None:
        """
        Initialize from static analysis data.

        This component doesn't need static data initialization,
        but we implement the abstract method as required.
        """
        pass

    def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze data and produce visual element associations.

        Args:
            state: The current application state containing screen description and screenshot path.

        Returns:
            Dictionary containing visual element associations and mappings

        Raises:
            ValueError: If required state information is missing
        """
        # Extract screen description and screenshot path from input
        if StateEntry.STRUCTURED_SCREEN in state and StateEntry.SCREENSHOT_PATH in state:
            screen_description = state.get(StateEntry.STRUCTURED_SCREEN)
            screenshot_path = state.get(StateEntry.SCREENSHOT_PATH)
        else:
            self.logger.error("The state does not have the necessary information for analysis")
            raise ValueError("Necessary information not provided: screen_description or screenshot_path")

        # Perform the analysis
        return self.complement_screen_actions(screen_description, screenshot_path)

    def complement_screen_actions(self, screen_description: ScreenDescription,
                                  screenshot_path: str) -> Dict[str, Any]:
        """
        Complement existing UI elements with screenshot-derived insights.

        This method analyzes a screenshot to identify visual elements and errors,
        then associates them with existing UI elements in the screen description.

        Args:
            screen_description: Original screen description
            screenshot_path: Path to the screenshot image

        Returns:
            Dictionary containing visual element associations and complementary information
        """
        self.logger.debug(f"Complementing screen actions for {screen_description.activity}")

        try:
            # Reset state for this analysis
            self.visual_to_ui_associations = {}
            self.error_impacted_items = set()
            self.unmatched_visual_elements = []

            # Analyze screenshot
            self.logger.debug(f"Analyzing screenshot: {screenshot_path}")
            analyzer = ScreenshotAnalyzer(image_path=screenshot_path)
            analysis_result = analyzer.extract_information()

            # Create mapping of existing UI elements with their bounds
            ui_elements_map = self._create_ui_elements_map(screen_description)

            # Process error indicators first (priority association)
            error_mapping = self._process_error_indicators(
                analysis_result.get("error_indicators", []),
                ui_elements_map,
                screen_description
            )

            # Process visual buttons
            button_mapping = self._process_visual_buttons(
                analysis_result.get("buttons", []),
                ui_elements_map,
                screen_description
            )

            # Process important text areas
            text_mapping = self._process_text_elements(
                analysis_result.get("texts", []),
                ui_elements_map,
                screen_description
            )

            # Process other interactive elements
            interactive_mapping = self._process_interactive_elements(
                analysis_result.get("interactive_elements", []),
                ui_elements_map,
                screen_description
            )

            # Create the result mapping
            visual_mapping = {
                "error_indicators": error_mapping,
                "visual_buttons": button_mapping,
                "text_elements": text_mapping,
                "interactive_elements": interactive_mapping,
                "error_impacted_items": list(self.error_impacted_items),
                "unmatched_elements": self.unmatched_visual_elements,
                "metrics": {
                    "error_indicators_count": len(error_mapping),
                    "visual_buttons_count": len(button_mapping),
                    "text_elements_count": len(text_mapping),
                    "interactive_elements_count": len(interactive_mapping),
                    "error_impacted_items_count": len(self.error_impacted_items),
                    "unmatched_elements_count": len(self.unmatched_visual_elements)
                }
            }

            # For backward compatibility, also update the screen description
            enhanced_screen = self._enhance_screen_description(
                screen_description,
                visual_mapping
            )

            # Log processing summary
            total_elements = (len(error_mapping) + len(button_mapping) +
                              len(text_mapping) + len(interactive_mapping))
            self.log_processing_summary("visual elements", total_elements)

            # Return both the enhanced screen description and the visual mapping
            return {
                "enhanced_screen": enhanced_screen,
                "visual_mapping": visual_mapping
            }

        except Exception as e:
            self.logger.error(f"Error complementing screen actions: {e}")
            import traceback
            print(traceback.format_exc())
            # Return original screen description on error
            return {
                "enhanced_screen": screen_description,
                "visual_mapping": {
                    "error": str(e),
                    "error_indicators": [],
                    "visual_buttons": [],
                    "text_elements": [],
                    "interactive_elements": [],
                    "error_impacted_items": [],
                    "unmatched_elements": [],
                    "metrics": {
                        "error": "Failed to analyze screenshot"
                    }
                }
            }

    def _create_ui_elements_map(self, screen_description: ScreenDescription) -> Dict[str, Any]:
        """
        Create a mapping of UI elements with their bounds for faster lookup.

        Args:
            screen_description: Screen description containing UI elements

        Returns:
            Dictionary mapping element IDs to their data including bounds
        """
        ui_elements_map = {}

        for item in screen_description.items:
            if "bounds" in item.view:
                bounds = item.view["bounds"]
                if isinstance(bounds, list) and len(bounds) == 2:
                    # Create a lookup key based on bounds
                    key = f"{bounds[0][0]}_{bounds[0][1]}_{bounds[1][0]}_{bounds[1][1]}"

                    # Store the actual ScreenItem object for direct access
                    ui_elements_map[key] = {
                        "item": item,
                        "bounds": bounds,
                        "center": self._calculate_center(bounds),
                        "area": self._calculate_area(bounds)
                    }

        return ui_elements_map

    def _calculate_center(self, bounds: List[List[int]]) -> Tuple[int, int]:
        """
        Calculate the center point of a bounding box.

        Args:
            bounds: Bounds in format [[x1, y1], [x2, y2]]

        Returns:
            (x, y) tuple of center coordinates
        """
        return (
            (bounds[0][0] + bounds[1][0]) // 2,
            (bounds[0][1] + bounds[1][1]) // 2
        )

    def _calculate_area(self, bounds: List[List[int]]) -> int:
        """
        Calculate the area of a bounding box.

        Args:
            bounds: Bounds in format [[x1, y1], [x2, y2]]

        Returns:
            Area in pixels²
        """
        width = bounds[1][0] - bounds[0][0]
        height = bounds[1][1] - bounds[0][1]
        return width * height

    def _process_error_indicators(self,
                                  error_indicators: List[Dict[str, Any]],
                                  ui_elements_map: Dict[str, Any],
                                  screen_description: ScreenDescription) -> List[Dict[str, Any]]:
        """
        Process error indicators and associate them with UI elements.

        Args:
            error_indicators: List of error indicators from screenshot analysis
            ui_elements_map: Mapping of UI elements with their bounds
            screen_description: Original screen description

        Returns:
            List of error indicators with associations
        """
        result = []

        for error in error_indicators:
            error_x = error.get("x", 0)
            error_y = error.get("y", 0)
            error_width = error.get("width", 0)
            error_height = error.get("height", 0)
            error_bounds = [[error_x, error_y], [error_x + error_width, error_y + error_height]]

            # Find associated UI elements
            associated_item = self._find_associated_ui_element(
                error_bounds,
                ui_elements_map,
                ErrorAssociationStrategy()
            )

            # Process association
            if associated_item:
                self.logger.debug(f"Associated item: {associated_item}")
                # Add error information to the UI element
                associated_item.complement["has_error"] = True
                if "errors" not in associated_item.complement:
                    associated_item.complement["errors"] = []
                associated_item.complement["errors"].append(error)
                # associated_item.view["error_type"] = error.get("error_type", "unknown_error")
                # associated_item.view["error_confidence"] = error.get("confidence", 0.0)
                #
                # # If it's an edit text, mark it for special handling
                # if "EditText" in associated_item.view.get("class", ""):
                #     self.error_impacted_items.add(associated_item)

                # Add association information to the error
                processed_error = error.copy()
                processed_error["associated_item"] = associated_item
                result.append(processed_error)

            else:
                self.logger.debug(f"No associated item found for error: {error}")
                # No associated UI element, create as a standalone element
                processed_error = error.copy()
                processed_error["associated_item"] = None
                self.unmatched_visual_elements.append(processed_error)
                result.append(processed_error)

        return result

    def _process_visual_buttons(self,
                                buttons: List[Dict[str, Any]],
                                ui_elements_map: Dict[str, Any],
                                screen_description: ScreenDescription) -> List[Dict[str, Any]]:
        """
        Process visually detected buttons and associate them with UI elements.

        Args:
            buttons: List of button data from screenshot analysis
            ui_elements_map: Mapping of UI elements with their bounds
            screen_description: Original screen description

        Returns:
            List of buttons with associations
        """
        result = []

        for button in buttons:
            button_x = button.get("x", 0)
            button_y = button.get("y", 0)
            button_width = button.get("width", 0)
            button_height = button.get("height", 0)
            button_bounds = [[button_x, button_y], [button_x + button_width, button_y + button_height]]

            # Find associated UI elements
            associated_item = self._find_associated_ui_element(
                button_bounds,
                ui_elements_map,
                ButtonAssociationStrategy()
            )

            # Process association
            if associated_item:
                # Add visual button information to the UI element
                associated_item.complement["has_visual_button"] = True
                if "visual_button" not in associated_item.complement:
                    associated_item.complement["visual_button"] = []
                associated_item.complement["visual_button"].append(button)

                # Add association information to the button
                processed_button = button.copy()
                processed_button["associated_item"] = associated_item
                result.append(processed_button)

            else:
                # No associated UI element, create as a standalone element
                processed_button = button.copy()
                processed_button["associated_item"] = None
                self.unmatched_visual_elements.append(processed_button)
                result.append(processed_button)

        return result

    def _process_text_elements(self,
                               texts: List[Dict[str, Any]],
                               ui_elements_map: Dict[str, Any],
                               screen_description: ScreenDescription) -> List[Dict[str, Any]]:
        """
        Process text elements and associate them with UI elements.

        Args:
            texts: List of text data from screenshot analysis
            ui_elements_map: Mapping of UI elements with their bounds
            screen_description: Original screen description

        Returns:
            List of texts with associations
        """
        result = []

        for text_item in texts:
            # Only consider high confidence text
            confidence = text_item.get("confidence", 0)
            if confidence < 70:
                continue

            bbox = text_item.get("bbox", {})
            if not bbox:
                continue

            text_x = bbox.get("x", 0)
            text_y = bbox.get("y", 0)
            text_width = bbox.get("width", 0)
            text_height = bbox.get("height", 0)
            text_bounds = [[text_x, text_y], [text_x + text_width, text_y + text_height]]

            # Find associated UI elements
            associated_item = self._find_associated_ui_element(
                text_bounds,
                ui_elements_map,
                TextAssociationStrategy()
            )

            # Process association
            if associated_item:
                # Add visual text information to the UI element
                associated_item.complement["has_visual_text"] = True
                if "visual_text" not in associated_item.complement:
                    associated_item.complement["visual_text"] = []
                associated_item.complement["visual_text"].append(text_item)

                # Add association information to the text
                processed_text = text_item.copy()
                processed_text["associated_item"] = associated_item
                result.append(processed_text)

            else:
                # Check if it looks like a button
                if self._looks_like_button_text(text_item.get("text", "")):
                    processed_text = text_item.copy()
                    processed_text["associated_item"] = None
                    processed_text["is_button_like"] = True
                    self.unmatched_visual_elements.append(processed_text)
                    result.append(processed_text)
                else:
                    # Just a regular text with no UI association
                    processed_text = text_item.copy()
                    processed_text["associated_item"] = None
                    result.append(processed_text)

        return result

    def _process_interactive_elements(self,
                                      elements: List[Dict[str, Any]],
                                      ui_elements_map: Dict[str, Any],
                                      screen_description: ScreenDescription) -> List[Dict[str, Any]]:
        """
        Process interactive elements and associate them with UI elements.

        Args:
            elements: List of interactive elements from screenshot analysis
            ui_elements_map: Mapping of UI elements with their bounds
            screen_description: Original screen description

        Returns:
            List of interactive elements with associations
        """
        result = []

        for element in elements:
            element_x = element.get("x", 0)
            element_y = element.get("y", 0)
            element_width = element.get("width", 0)
            element_height = element.get("height", 0)
            element_bounds = [[element_x, element_y], [element_x + element_width, element_y + element_height]]

            # Find associated UI elements
            associated_item = self._find_associated_ui_element(
                element_bounds,
                ui_elements_map,
                InteractiveElementAssociationStrategy()
            )

            # Process association
            if associated_item:
                # Add interactive element information to the UI element
                associated_item.complement["has_interactive_element"] = True
                if "interactive_element" not in associated_item.complement:
                    associated_item.complement["interactive_element"] = []
                associated_item.complement["interactive_element"].append(element)

                # Add association information to the element
                processed_element = element.copy()
                processed_element["associated_item"] = associated_item
                result.append(processed_element)

            else:
                # No associated UI element, create as a standalone element
                processed_element = element.copy()
                processed_element["associated_item"] = None
                self.unmatched_visual_elements.append(processed_element)
                result.append(processed_element)

        return result

    def _find_associated_ui_element(self,
                                    visual_bounds: List[List[int]],
                                    ui_elements_map: Dict[str, Any],
                                    strategy: AssociationStrategy) -> Optional[ScreenItem]:
        """
        Find the UI element that best matches the visual element using a specific strategy.

        Args:
            visual_bounds: Bounds of the visual element
            ui_elements_map: Mapping of UI elements with their bounds
            strategy: Strategy for calculating match scores

        Returns:
            Best matching ScreenItem or None if no good match found
        """
        best_match = None
        best_score = 0.0

        for _, ui_data in ui_elements_map.items():
            # Calculate match score using the provided strategy
            score = strategy.calculate_match_score(visual_bounds, ui_data)

            if score > best_score:
                best_score = score
                best_match = ui_data["item"]

        # Only return if the score is above a minimum threshold
        return best_match if best_score >= 0.1 else None

    def _enhance_screen_description(self,
                                    screen_description: ScreenDescription,
                                    visual_mapping: Dict[str, Any]) -> ScreenDescription:
        """
        Enhance the original screen description with information from visual analysis.
        This is for backward compatibility with existing code.

        Args:
            screen_description: Original screen description
            visual_mapping: Visual element mapping from analysis

        Returns:
            Enhanced screen description with complementary items
        """
        # Create complementary items for unmatched visual elements
        complementary_items = []

        # Process unmatched visual buttons
        for element in visual_mapping["unmatched_elements"]:
            element_type = element.get("type", "")

            if "button" in str(element_type).lower() or element.get("is_button_like", False):
                # Create a visual button
                visual_button = self._create_visual_button(element)
                complementary_items.append(visual_button)

            elif "error" in str(element_type).lower():
                # Create a visual error indicator
                error_item = self._create_visual_error_indicator(element)
                if error_item:
                    complementary_items.append(error_item)

        # Create new screen description with additional items
        all_items = screen_description.items + complementary_items
        enhanced_screen = ScreenDescription(screen_description.activity, all_items)

        return enhanced_screen

    def _create_visual_button(self, button_data: Dict[str, Any]) -> ScreenItem:
        """
        Create a screen item for a visually detected button.

        Args:
            button_data: Button data from screenshot analysis

        Returns:
            ScreenItem representing the visual button
        """
        # Extract coordinates
        button_x = button_data.get("x", 0)
        button_y = button_data.get("y", 0)
        button_width = button_data.get("width", 0)
        button_height = button_data.get("height", 0)

        # Create view data
        view_data = {
            "class": "android.widget.Button",
            "resource_id": f"visual_button_{button_x}_{button_y}",
            "bounds": [[button_x, button_y], [button_x + button_width, button_y + button_height]],
            "clickable": True,
            "checkable": False,
            "scrollable": False,
            "long_clickable": True,
            "focused": False,
            "selected": False,
            "visual_element": True,  # Mark as visually detected
            "confidence": button_data.get("confidence", 0.0)
        }

        # Add text if available
        if "text" in button_data:
            view_data["text"] = button_data["text"]

        # Calculate center coordinates
        center_x = button_x + button_width // 2
        center_y = button_y + button_height // 2
        coordinates = (center_x, center_y)

        # Create actions
        actions = []

        # Click action
        action_id = self.counter.increment()
        actions.append(ItemAction(
            id=action_id,
            text=f"CLICK (Visual) ({action_id})",
            event=WidgetEventType.CLICK,
            target_view=view_data,
            coordinates=coordinates
        ))

        # # Long click action
        # action_id = self.counter.inc()
        # actions.append(ItemAction(
        #     id=action_id,
        #     text=f"LONG_CLICK (Visual) ({action_id})",
        #     event=WidgetEventType.LONG_CLICK,
        #     target_view=view_data,
        #     coordinates=coordinates
        # ))

        # Create description
        description = "Visual Button"
        if "text" in view_data:
            description += f" with text '{view_data['text']}'"

        # Create screen item
        return ScreenItem(
            view=view_data,
            base_description=description,
            actions=actions
        )

    def _create_visual_error_indicator(self, error_data: Dict[str, Any]) -> Optional[ScreenItem]:
        """
        Create a screen item for a visual error indicator.

        Args:
            error_data: Error indicator data from screenshot analysis

        Returns:
            ScreenItem representing the visual error indicator
        """
        # Extract coordinates
        error_x = error_data.get("x", 0)
        error_y = error_data.get("y", 0)
        error_width = error_data.get("width", 0)
        error_height = error_data.get("height", 0)

        # Create view data
        view_data = {
            "class": "android.widget.TextView",  # Use TextView as base class
            "resource_id": f"visual_error_{error_x}_{error_y}",
            "text": error_data.get("text", "Error Indicator"),
            "bounds": [[error_x, error_y], [error_x + error_width, error_y + error_height]],
            "clickable": True,
            "checkable": False,
            "scrollable": False,
            "long_clickable": False,
            "focused": False,
            "selected": False,
            "visual_element": True,  # Mark as visually detected
            "has_error": True,  # Mark as error
            "error_type": error_data.get("error_type", "unknown_error"),
            "confidence": error_data.get("confidence", 0.0)
        }

        # Calculate center coordinates
        center_x = error_x + error_width // 2
        center_y = error_y + error_height // 2
        coordinates = (center_x, center_y)

        # Create actions
        actions = []

        # Click action
        action_id = self.counter.increment()
        actions.append(ItemAction(
            id=action_id,
            text=f"CLICK (Error Indicator) ({action_id})",
            event=WidgetEventType.CLICK,
            target_view=view_data,
            coordinates=coordinates
        ))

        # Create description
        description = f"Visual Error Indicator: {view_data['error_type']}"
        if "text" in view_data and view_data["text"] != "Error Indicator":
            description += f" - '{view_data['text']}'"

        # Create screen item
        return ScreenItem(
            view=view_data,
            base_description=description,
            actions=actions
        )

    def _looks_like_button_text(self, text: str) -> bool:
        """
        Check if text looks like it might be a button label.

        Args:
            text: Text to check

        Returns:
            True if text looks like a button label
        """
        # Common button text patterns
        button_texts = [
            "ok", "cancel", "yes", "no", "submit", "login", "sign in", "register",
            "next", "previous", "continue", "back", "done", "save", "delete",
            "add", "remove", "close", "send", "search", "buy", "purchase",
            "confirm", "accept", "decline", "agree", "disagree"
        ]

        # Check if text matches any common button pattern
        text_lower = text.lower()

        # Exact match with button texts
        if text_lower in button_texts:
            return True

        # Short text (likely a button)
        if len(text) <= 15 and text.isprintable() and not text.isspace():
            return True

        return False

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get metrics from the analyzer.

        Returns:
            Dictionary containing metrics and their values
        """
        return {
            "error_impacted_items_count": len(self.error_impacted_items),
            "unmatched_visual_elements_count": len(self.unmatched_visual_elements)
        }
