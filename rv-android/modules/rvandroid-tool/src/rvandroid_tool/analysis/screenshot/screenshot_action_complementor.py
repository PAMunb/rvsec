"""
Screenshot Action Complementor for RV-Android.

This module provides comprehensive functionality to complement UI actions by analyzing
screenshots and associating visual elements with UI hierarchy elements through advanced
pattern recognition and geometric analysis.

### Architectural Overview:
The ScreenshotActionComplementor enhances testing capabilities by detecting elements
not present in the UI hierarchy, identifying error conditions through visual analysis,
and associating detected visual elements with existing UI hierarchy components.

### Key Components:
- **Association Strategies**: Pluggable algorithms for matching visual elements with UI components
- **Element Processing Pipeline**: Systematic processing of different visual element types
- **Visual-UI Mapping**: Comprehensive association between screenshot analysis and UI hierarchy
- **Error Integration**: Error indicator association with form fields and interactive elements

### Design Patterns:
- **Strategy Pattern**: Different association algorithms for various element types
- **Template Method**: Common processing pipeline with specialized steps
- **Component Integration**: Direct integration with rv-screen-parser Pydantic models
- **Error Handling**: Comprehensive error handling using rv-android-core decorators

### Integration Architecture:
- Consumes ScreenshotAnalysisResult from rv-screen-parser with typed Pydantic models
- Processes error indicators, buttons, text elements, and interactive components
- Associates visual elements with ScreenDescription hierarchy from rv-screen-parser
- Generates enhanced screen descriptions with visual complement information
"""

from typing import Dict, Any, List, Optional, Tuple

from rv_android_core.analysis.base_analyzer import BaseAnalyzer
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.widget import WidgetEventType
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVParsingError, RVValidationError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager

from rv_screen_parser.parser.screen.visitor.model import ItemAction, ScreenItem, ScreenDescription, Counter
from rv_screen_parser.screenshot.screenshot_analyzer import ScreenshotAnalyzer
from rv_screen_parser.screenshot.models import (
    DetectedText, DetectedButton, ErrorIndicator, InteractiveElement,
    ErrorType, DetectionMethod
)
from rv_llm.llm.constants import StateEntry


class AssociationStrategy:
    """
    Base strategy for associating visual elements with UI hierarchy components.
    
    ### Architectural Role:
    Provides the foundation for different association algorithms that match
    visually detected elements with existing UI hierarchy components based
    on geometric, semantic, and contextual factors.
    
    ### Design Strategy:
    - Implements geometric overlap calculation as the base matching criterion
    - Supports extensible scoring through inheritance for specialized strategies
    - Maintains consistent interface for all association algorithms
    - Provides robust coordinate system handling for different screen densities
    """

    def calculate_match_score(self, visual_bounds: List[List[int]], ui_element_data: Dict[str, Any]) -> float:
        """
        Calculate match score between visual element bounds and UI element.

        Implements base geometric overlap calculation as the primary matching
        criterion for associating visual elements with UI hierarchy components.

        Args:
            visual_bounds: Visual element bounds in [[x1, y1], [x2, y2]] format
            ui_element_data: UI element data including bounds and ScreenItem

        Returns:
            Match score between 0.0 and 1.0 based on geometric overlap
        """
        overlap = self._calculate_overlap_percentage(
            visual_bounds[0][0], visual_bounds[0][1], visual_bounds[1][0], visual_bounds[1][1],
            ui_element_data["bounds"][0][0], ui_element_data["bounds"][0][1],
            ui_element_data["bounds"][1][0], ui_element_data["bounds"][1][1]
        )
        return overlap

    def _calculate_overlap_percentage(self, x1: int, y1: int, x2: int, y2: int, 
                                    x3: int, y3: int, x4: int, y4: int) -> float:
        """
        Calculate geometric overlap percentage between two rectangular regions.

        Implements precise intersection calculation for associating visual elements
        with UI hierarchy components based on spatial positioning.

        Args:
            x1, y1, x2, y2: First rectangle coordinates (top-left, bottom-right)
            x3, y3, x4, y4: Second rectangle coordinates (top-left, bottom-right)

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
    """
    Specialized association strategy for error indicators with form validation focus.
    
    ### Architectural Strategy:
    Prioritizes association with input fields and implements positional heuristics
    for common error indicator placement patterns in mobile applications.
    
    ### Error Association Patterns:
    - Prioritizes EditText and input field associations
    - Implements below-field positioning heuristics for validation errors
    - Supports icon-based error indicators adjacent to form controls
    - Handles error dialog and toast notification associations
    """

    def calculate_match_score(self, visual_bounds: List[List[int]], ui_element_data: Dict[str, Any]) -> float:
        """
        Calculate error indicator association score with UI element prioritization.

        Implements specialized scoring for error indicators that prioritizes
        input fields and applies positional heuristics for validation errors.

        Args:
            visual_bounds: Error indicator bounds from screenshot analysis
            ui_element_data: UI element data with ScreenItem and bounds

        Returns:
            Enhanced match score with input field prioritization
        """
        overlap = super().calculate_match_score(visual_bounds, ui_element_data)

        # Prioritize input fields for error association
        item = ui_element_data["item"]
        if "EditText" in item.view.get("class", ""):
            overlap *= 1.2  # Boost score for input fields

        # Handle below-field error positioning (common validation pattern)
        if overlap < 0.1:
            visual_center_x = (visual_bounds[0][0] + visual_bounds[1][0]) / 2
            ui_center_x = (ui_element_data["bounds"][0][0] + ui_element_data["bounds"][1][0]) / 2

            # Check horizontal alignment with UI element
            ui_width = ui_element_data["bounds"][1][0] - ui_element_data["bounds"][0][0]
            if abs(visual_center_x - ui_center_x) < ui_width / 2:
                # Check if error is positioned below the element (validation error pattern)
                if (visual_bounds[0][1] >= ui_element_data["bounds"][1][1] and
                        visual_bounds[0][1] <= ui_element_data["bounds"][1][1] + 100):
                    return 0.7  # High score for typical validation error positioning

        return overlap


class ButtonAssociationStrategy(AssociationStrategy):
    """
    Association strategy for visual button elements with clickable component focus.
    
    ### Design Strategy:
    Prioritizes association with Button classes and clickable elements while
    maintaining geometric overlap as the primary criterion.
    """

    def calculate_match_score(self, visual_bounds: List[List[int]], ui_element_data: Dict[str, Any]) -> float:
        """
        Calculate button association score with clickable element prioritization.

        Args:
            visual_bounds: Visual button bounds from screenshot analysis
            ui_element_data: UI element data with ScreenItem and bounds

        Returns:
            Match score with button and clickable element prioritization
        """
        overlap = super().calculate_match_score(visual_bounds, ui_element_data)

        # Prioritize actual buttons and clickable elements
        item = ui_element_data["item"]
        if "Button" in item.view.get("class", "") or item.view.get("clickable", False):
            overlap *= 1.1  # Moderate boost for button and clickable elements

        return overlap


class TextAssociationStrategy(AssociationStrategy):
    """
    Association strategy for detected text elements with TextView components.
    
    ### Design Strategy:
    Implements base geometric association for text elements while maintaining
    compatibility for future text-specific enhancements.
    """

    def calculate_match_score(self, visual_bounds: List[List[int]], ui_element_data: Dict[str, Any]) -> float:
        """
        Calculate text element association score.

        Args:
            visual_bounds: Text element bounds from OCR analysis
            ui_element_data: UI element data with ScreenItem and bounds

        Returns:
            Base geometric match score for text elements
        """
        return super().calculate_match_score(visual_bounds, ui_element_data)


class InteractiveElementAssociationStrategy(AssociationStrategy):
    """
    Association strategy for interactive elements with UI hierarchy components.
    
    ### Design Strategy:
    Handles association of detected interactive elements (sliders, switches, etc.)
    with corresponding UI hierarchy components based on geometric positioning.
    """

    def calculate_match_score(self, visual_bounds: List[List[int]], ui_element_data: Dict[str, Any]) -> float:
        """
        Calculate interactive element association score.

        Args:
            visual_bounds: Interactive element bounds from visual analysis
            ui_element_data: UI element data with ScreenItem and bounds

        Returns:
            Base geometric match score for interactive elements
        """
        return super().calculate_match_score(visual_bounds, ui_element_data)


class ScreenshotActionComplementor(BaseAnalyzer):
    """
    Advanced screenshot analysis integration for UI action complementation.

    ### Architectural Overview:
    This component serves as the bridge between screenshot visual analysis and UI hierarchy
    processing, enabling comprehensive testing of applications with non-standard UI elements,
    canvas-based interfaces, and visual error detection capabilities.

    ### Core Responsibilities:
    - **Visual Element Association**: Associates screenshot-detected elements with UI hierarchy
    - **Error Detection Integration**: Processes error indicators and associates with form fields
    - **Visual Button Detection**: Identifies visually rendered buttons not in UI hierarchy
    - **Interactive Element Processing**: Handles sliders, switches, and custom controls
    - **Screen Enhancement**: Generates enhanced screen descriptions with visual information

    ### Integration Architecture:
    - Consumes ScreenshotAnalysisResult with typed Pydantic models from rv-screen-parser
    - Processes ScreenDescription objects from rv-screen-parser visitor pattern
    - Integrates with StaticAnalysisData for application-specific context
    - Generates visual mapping for prompt system integration

    ### Design Patterns:
    - **Analyzer Pattern**: Inherits from BaseAnalyzer for consistent system integration
    - **Strategy Pattern**: Pluggable association algorithms for different element types
    - **Factory Pattern**: Element processing based on visual analysis results
    - **Component Integration**: Direct integration with rv-android-core error handling

    ### Error Handling Strategy:
    - Uses rv-android-core ErrorHandler decorators for all critical operations
    - Implements fallback mechanisms for association failures
    - Provides comprehensive logging through rv-android-core LoggingManager
    - Maintains system stability through exception isolation
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize screenshot action complementor with analysis infrastructure.

        Sets up the complete analysis pipeline including error handling, logging,
        visual element association strategies, and integration components.

        Args:
            static_data: Optional static analysis data for application context
        """
        super().__init__(analyzer_name="screenshot_complementor", static_data=static_data)

        # Initialize logging infrastructure
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvandroid_tool.analysis.screenshot.screenshot_action_complementor",
            {CONTEXT_COMPONENT: "ScreenshotActionComplementor"}
        )

        # Initialize error handling
        self.error_handler = ErrorHandler.get_instance()

        # Action ID counter for generated visual elements
        self.counter = Counter(1000)

        # Analysis state tracking
        self.visual_to_ui_associations = {}
        self.error_impacted_items = set()
        self.unmatched_visual_elements = []

        self.logger.info("Initialized ScreenshotActionComplementor with enhanced visual analysis")

    def _initialize_from_static_data(self) -> None:
        """
        Initialize analyzer from static analysis data.

        This component operates independently of static data but implements
        the required abstract method from BaseAnalyzer.
        """
        pass

    @ErrorHandler.handle_errors(component="ScreenshotActionComplementor", phase="analysis", reraise=True)
    def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze application state and generate visual element associations.

        Processes current application state containing screen description and screenshot
        to generate comprehensive visual element associations and enhanced descriptions.

        Args:
            state: Application state with ScreenDescription and screenshot path

        Returns:
            Enhanced state with visual mapping and screen description

        Raises:
            RVParsingError: If required state components are missing
            RVValidationError: If state validation fails
        """
        # Validate required state components
        if StateEntry.STRUCTURED_SCREEN not in state or StateEntry.SCREENSHOT_PATH not in state:
            raise RVParsingError(
                "Required state components missing: ScreenDescription or screenshot path",
                parser_type="ScreenshotActionComplementor"
            )

        screen_description: ScreenDescription = state[StateEntry.STRUCTURED_SCREEN]
        screenshot_path = state[StateEntry.SCREENSHOT_PATH]

        # Validate state component types
        if not isinstance(screen_description, ScreenDescription):
            raise RVValidationError(
                f"Expected ScreenDescription object, got {type(screen_description)}",
                field_name="structured_screen"
            )

        # Generate visual element associations
        return self.complement_screen_actions(screen_description, screenshot_path)

    @ErrorHandler.handle_errors(component="ScreenshotActionComplementor", phase="complement_generation", reraise=True)
    def complement_screen_actions(self, screen_description: ScreenDescription,
                                  screenshot_path: str) -> Dict[str, Any]:
        """
        Generate comprehensive screen action complementation with visual analysis.

        Performs complete visual analysis pipeline including screenshot processing,
        element association, and enhanced screen description generation.

        Args:
            screen_description: Original ScreenDescription from UI hierarchy analysis
            screenshot_path: Path to screenshot image for visual analysis

        Returns:
            Complete analysis result with enhanced screen and visual mapping

        Raises:
            RVParsingError: If screenshot analysis fails
        """
        try:
            # Reset analysis state for new processing
            self.visual_to_ui_associations.clear()
            self.error_impacted_items.clear()
            self.unmatched_visual_elements.clear()

            # Perform screenshot analysis with Pydantic models
            self.logger.debug(f"Analyzing screenshot for visual elements: {screenshot_path}")
            analyzer = ScreenshotAnalyzer(image_path=screenshot_path)
            analysis_result = analyzer.extract_information()

            # Create UI elements mapping for association
            ui_elements_map = self._create_ui_elements_map(screen_description)

            # Process visual elements with type-specific strategies
            error_mapping = self._process_error_indicators(
                analysis_result.get("error_indicators", []),
                ui_elements_map,
                screen_description
            )

            button_mapping = self._process_visual_buttons(
                analysis_result.get("buttons", []),
                ui_elements_map,
                screen_description
            )

            text_mapping = self._process_text_elements(
                analysis_result.get("texts", []),
                ui_elements_map,
                screen_description
            )

            interactive_mapping = self._process_interactive_elements(
                analysis_result.get("interactive_elements", []),
                ui_elements_map,
                screen_description
            )

            # Generate comprehensive visual mapping
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

            # Generate enhanced screen description with visual information
            enhanced_screen = self._enhance_screen_description(screen_description, visual_mapping)

            print(f" >>>>> NOVO screen description:\n{str(enhanced_screen)}")


            # Log processing summary
            total_elements = (len(error_mapping) + len(button_mapping) +
                              len(text_mapping) + len(interactive_mapping))
            self.log_processing_summary("visual elements", total_elements)

            return {
                "enhanced_screen": enhanced_screen,
                "visual_mapping": visual_mapping
            }

        except Exception as e:
            self.logger.error(f"Error in screenshot action complementation: {e}")
            # Return fallback structure on analysis failure
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
                    "metrics": {"error": "Analysis failed"}
                }
            }

    def _create_ui_elements_map(self, screen_description: ScreenDescription) -> Dict[str, Any]:
        """
        Create efficient UI element mapping for visual association operations.

        Generates spatial index of UI hierarchy elements with geometric properties
        for fast association lookup during visual element processing.

        Args:
            screen_description: ScreenDescription with UI hierarchy elements

        Returns:
            Spatial mapping of UI elements with bounds and geometric properties
        """
        ui_elements_map = {}

        for item in screen_description.items:
            if "bounds" in item.view:
                bounds = item.view["bounds"]
                if isinstance(bounds, list) and len(bounds) == 2:
                    # Create spatial lookup key from bounds
                    key = f"{bounds[0][0]}_{bounds[0][1]}_{bounds[1][0]}_{bounds[1][1]}"

                    ui_elements_map[key] = {
                        "item": item,
                        "bounds": bounds,
                        "center": self._calculate_center(bounds),
                        "area": self._calculate_area(bounds)
                    }

        return ui_elements_map

    def _calculate_center(self, bounds: List[List[int]]) -> Tuple[int, int]:
        """
        Calculate geometric center of rectangular bounds.

        Args:
            bounds: Rectangular bounds in [[x1, y1], [x2, y2]] format

        Returns:
            Center coordinates as (x, y) tuple
        """
        return (
            (bounds[0][0] + bounds[1][0]) // 2,
            (bounds[0][1] + bounds[1][1]) // 2
        )

    def _calculate_area(self, bounds: List[List[int]]) -> int:
        """
        Calculate rectangular area from bounds.

        Args:
            bounds: Rectangular bounds in [[x1, y1], [x2, y2]] format

        Returns:
            Area in square pixels
        """
        width = bounds[1][0] - bounds[0][0]
        height = bounds[1][1] - bounds[0][1]
        return width * height

    @ErrorHandler.handle_errors(component="ScreenshotActionComplementor", phase="error_processing")
    def _process_error_indicators(self,
                                  error_indicators: List[Dict[str, Any]],
                                  ui_elements_map: Dict[str, Any],
                                  screen_description: ScreenDescription) -> List[Dict[str, Any]]:
        """
        Process error indicators from screenshot analysis with UI association.

        Associates detected error indicators with UI hierarchy elements using
        specialized error association strategy and form field prioritization.

        Args:
            error_indicators: Error indicators from screenshot analysis (model_dump format)
            ui_elements_map: Spatial mapping of UI elements
            screen_description: Original screen description for context

        Returns:
            Processed error indicators with UI associations
        """
        result = []

        for error in error_indicators:
            # Extract coordinates directly from model_dump (flat structure)
            error_x = error.get("x", 0)
            error_y = error.get("y", 0)
            error_width = error.get("width", 0)
            error_height = error.get("height", 0)
            error_bounds = [[error_x, error_y], [error_x + error_width, error_y + error_height]]

            # Find associated UI element using error-specific strategy
            associated_item = self._find_associated_ui_element(
                error_bounds,
                ui_elements_map,
                ErrorAssociationStrategy()
            )

            # Process association results
            if associated_item:
                self.logger.debug(f"Associated error indicator with UI element: {associated_item.view.get('resource_id', 'unknown')}")
                
                # Add error information to associated UI element
                associated_item.complement["has_error"] = True
                if "errors" not in associated_item.complement:
                    associated_item.complement["errors"] = []
                associated_item.complement["errors"].append(error)

                # Add error annotation to element description for high-confidence errors
                confidence = error.get("confidence", 0)
                if confidence >= 0.8 and not associated_item.base_description.endswith(" [ERR]"):
                    associated_item.base_description += " [ERR]"
                    self.logger.debug(f"Added [ERR] annotation to UI element (confidence: {confidence})")

                # Track error-impacted items
                self.error_impacted_items.add(associated_item)

                # Create processed error with association
                processed_error = error.copy()
                processed_error["associated_item"] = associated_item
                result.append(processed_error)

            else:
                self.logger.debug(f"No UI association found for error indicator at ({error_x}, {error_y})")
                
                # Track unmatched visual elements
                processed_error = error.copy()
                processed_error["associated_item"] = None
                self.unmatched_visual_elements.append(processed_error)
                result.append(processed_error)

        return result

    @ErrorHandler.handle_errors(component="ScreenshotActionComplementor", phase="button_processing")
    def _process_visual_buttons(self,
                                buttons: List[Dict[str, Any]],
                                ui_elements_map: Dict[str, Any],
                                screen_description: ScreenDescription) -> List[Dict[str, Any]]:
        """
        Process visually detected buttons with UI hierarchy association.

        Associates detected visual buttons with UI hierarchy elements using
        button-specific association strategy and clickable element prioritization.

        Args:
            buttons: Visual buttons from screenshot analysis (model_dump format)
            ui_elements_map: Spatial mapping of UI elements
            screen_description: Original screen description for context

        Returns:
            Processed visual buttons with UI associations
        """
        result = []

        for button in buttons:
            # Extract coordinates directly from model_dump
            button_x = button.get("x", 0)
            button_y = button.get("y", 0)
            button_width = button.get("width", 0)
            button_height = button.get("height", 0)
            button_bounds = [[button_x, button_y], [button_x + button_width, button_y + button_height]]

            # Find associated UI element using button-specific strategy
            associated_item = self._find_associated_ui_element(
                button_bounds,
                ui_elements_map,
                ButtonAssociationStrategy()
            )

            # Process association results
            if associated_item:
                self.logger.debug(f"Associated visual button with UI element: {associated_item.view.get('resource_id', 'unknown')}")
                
                # Enhance UI element with visual button information
                associated_item.complement["has_visual_button"] = True
                associated_item.complement["visual_button_confidence"] = button.get("confidence", 0.0)

                # Create processed button with association
                processed_button = button.copy()
                processed_button["associated_item"] = associated_item
                result.append(processed_button)

            else:
                # Create new virtual button for unmatched visual elements
                virtual_button = self._create_virtual_button(button, screen_description)
                if virtual_button:
                    screen_description.items.append(virtual_button)

                processed_button = button.copy()
                processed_button["associated_item"] = virtual_button
                result.append(processed_button)

        return result

    @ErrorHandler.handle_errors(component="ScreenshotActionComplementor", phase="text_processing")
    def _process_text_elements(self,
                               texts: List[Dict[str, Any]],
                               ui_elements_map: Dict[str, Any],
                               screen_description: ScreenDescription) -> List[Dict[str, Any]]:
        """
        Process detected text elements with UI hierarchy association.

        Args:
            texts: Text elements from OCR analysis (model_dump format)
            ui_elements_map: Spatial mapping of UI elements
            screen_description: Original screen description for context

        Returns:
            Processed text elements with UI associations
        """
        result = []

        for text in texts:
            # Extract coordinates from model_dump
            text_x = text.get("x", 0)
            text_y = text.get("y", 0)
            text_width = text.get("width", 0)
            text_height = text.get("height", 0)
            text_bounds = [[text_x, text_y], [text_x + text_width, text_y + text_height]]

            # Find associated UI element
            associated_item = self._find_associated_ui_element(
                text_bounds,
                ui_elements_map,
                TextAssociationStrategy()
            )

            processed_text = text.copy()
            processed_text["associated_item"] = associated_item
            result.append(processed_text)

        return result

    @ErrorHandler.handle_errors(component="ScreenshotActionComplementor", phase="interactive_processing")
    def _process_interactive_elements(self,
                                      interactive_elements: List[Dict[str, Any]],
                                      ui_elements_map: Dict[str, Any],
                                      screen_description: ScreenDescription) -> List[Dict[str, Any]]:
        """
        Process detected interactive elements with UI hierarchy association.

        Args:
            interactive_elements: Interactive elements from visual analysis (model_dump format)
            ui_elements_map: Spatial mapping of UI elements
            screen_description: Original screen description for context

        Returns:
            Processed interactive elements with UI associations
        """
        result = []

        for element in interactive_elements:
            # Extract coordinates from model_dump
            elem_x = element.get("x", 0)
            elem_y = element.get("y", 0)
            elem_width = element.get("width", 0)
            elem_height = element.get("height", 0)
            elem_bounds = [[elem_x, elem_y], [elem_x + elem_width, elem_y + elem_height]]

            # Find associated UI element
            associated_item = self._find_associated_ui_element(
                elem_bounds,
                ui_elements_map,
                InteractiveElementAssociationStrategy()
            )

            processed_element = element.copy()
            processed_element["associated_item"] = associated_item
            result.append(processed_element)

        return result

    def _find_associated_ui_element(self,
                                    visual_bounds: List[List[int]],
                                    ui_elements_map: Dict[str, Any],
                                    strategy: AssociationStrategy) -> Optional[ScreenItem]:
        """
        Find best UI element association using specified strategy.

        Args:
            visual_bounds: Visual element bounds for association
            ui_elements_map: Spatial mapping of UI elements
            strategy: Association strategy for scoring

        Returns:
            Best matching ScreenItem or None if no suitable match
        """
        best_match = None
        best_score = 0.0

        for ui_element_data in ui_elements_map.values():
            score = strategy.calculate_match_score(visual_bounds, ui_element_data)
            if score > best_score:
                best_score = score
                best_match = ui_element_data["item"]

        # Return match if score meets minimum threshold
        return best_match if best_score > 0.3 else None

    def _create_virtual_button(self, button_data: Dict[str, Any], 
                               screen_description: ScreenDescription) -> Optional[ScreenItem]:
        """
        Create virtual ScreenItem for unmatched visual buttons.

        Args:
            button_data: Visual button data from screenshot analysis
            screen_description: Screen description for context

        Returns:
            Virtual ScreenItem for the visual button
        """
        try:
            # Create virtual view data for visual button
            virtual_view = {
                "content_description": f"Visual Button ({button_data.get('confidence', 0.0):.2f})",
                "class": "VirtualButton",
                "resource_id": f"virtual_button_{self.counter.increment()}",
                "bounds": [[button_data.get("x", 0), button_data.get("y", 0)],
                          [button_data.get("x", 0) + button_data.get("width", 0),
                           button_data.get("y", 0) + button_data.get("height", 0)]],
                "clickable": True
            }

            # Create virtual action for the button
            virtual_action = ItemAction(
                id=self.counter.increment(),
                text=f"CLICK Virtual Button ({self.counter.get_current()})",
                event=WidgetEventType.CLICK,
                target_view=virtual_view
            )

            # Create virtual ScreenItem
            virtual_item = ScreenItem(
                view=virtual_view,
                base_description=f"Virtual button detected through screenshot analysis",
                actions=[virtual_action],
                complement={"visual_detection": True, "confidence": button_data.get("confidence", 0.0)}
            )

            return virtual_item

        except Exception as e:
            self.logger.warning(f"Failed to create virtual button: {e}")
            return None

    def _enhance_screen_description(self, screen_description: ScreenDescription,
                                    visual_mapping: Dict[str, Any]) -> ScreenDescription:
        """
        Generate enhanced screen description with visual complement information.

        Args:
            screen_description: Original screen description
            visual_mapping: Visual element mapping results

        Returns:
            Enhanced screen description with visual information
        """
        # The screen description is already enhanced through processing
        # Visual information is integrated into ScreenItem complement fields
        return screen_description

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics about visual element processing.

        Returns:
            Dictionary containing analysis metrics and performance data
        """
        return {
            "visual_associations": len(self.visual_to_ui_associations),
            "error_impacted_items": len(self.error_impacted_items),
            "unmatched_elements": len(self.unmatched_visual_elements),
            "processing_components": ["error_indicators", "visual_buttons", "text_elements", "interactive_elements"]
        }