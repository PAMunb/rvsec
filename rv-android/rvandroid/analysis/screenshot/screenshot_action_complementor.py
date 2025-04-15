# rvandroid/analysis/screenshot/screenshot_action_complementor.py
"""
Screenshot Action Complementor for RVDroid.

This module provides functionality to complement UI actions detected
from the UI hierarchy with information derived from screenshot analysis,
enabling better testing of non-standard UI elements and error detection.
"""

import os
from typing import Dict, Any, List, Optional, Tuple

from rvandroid.analysis.base_analyzer import BaseAnalyzer
from rvandroid.analysis.screenshot_analyzer import ScreenshotAnalyzer
from rvandroid.parser.screen.visitor.model import ItemAction, ScreenItem, ScreenDescription, Counter
from rvandroid.domain.static import StaticAnalysisData


class ScreenshotActionComplementor(BaseAnalyzer[ScreenDescription]):
    """
    Complements screen actions with additional insights from screenshot analysis.

    ### Architectural Decisions:
    - Implements a non-intrusive complement to existing action detection
    - Uses visual analysis to identify interactive elements not in UI hierarchy
    - Provides error detection capabilities using visual cues
    - Maintains a cache to optimize performance with similar screens
    - Extends BaseAnalyzer for consistent interface

    ### Role in the System:
    - Enriches screen descriptions with visually-derived actions
    - Bridges the gap between UI automation and visual testing
    - Improves testing of non-standard UI elements and canvas-based apps
    - Enhances error detection based on visual indicators
    """

    def __init__(self, screenshot_dir: Optional[str] = None, 
                 cache_size: int = 10,
                 static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the screenshot action complementor.

        Args:
            screenshot_dir: Directory for storing screenshots (None to use temp)
            cache_size: Size of the screenshot analysis cache
            static_data: Optional static analysis data
        """
        super().__init__(analyzer_name="screenshot_complementor", static_data=static_data)

        # Set screenshot directory
        self.screenshot_dir = screenshot_dir or os.path.join(os.path.dirname(__file__), "screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)

        # Initialize cache
        self.cache_size = cache_size
        self.analysis_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_keys: List[str] = []

        # Action ID counter
        self.counter = Counter(1000)  # Start IDs from 1000 to avoid conflicts

        self.logger.info(f"Initialized screenshot action complementor with cache size {cache_size}")
        
    def _initialize_from_static_data(self) -> None:
        """
        Initialize from static analysis data.
        
        This component doesn't need static data initialization,
        but we implement the abstract method as required.
        """
        pass

    def analyze(self, data: Any) -> ScreenDescription:
        """
        Analyze data and return enhanced screen description.
        
        Handles two input types:
        - Tuple[ScreenDescription, str]: Screen description and screenshot path
        - Dict with 'screen_description' and 'screenshot_path' keys
        
        Args:
            data: The data to analyze
            
        Returns:
            Enhanced screen description
        """
        # Extract screen description and screenshot path from input
        if isinstance(data, tuple) and len(data) == 2:
            screen_description, screenshot_path = data
        elif isinstance(data, dict) and 'screen_description' in data and 'screenshot_path' in data:
            screen_description = data['screen_description']
            screenshot_path = data['screenshot_path']
        else:
            self.logger.error(f"Unsupported data format for analysis: {type(data)}")
            if isinstance(data, ScreenDescription):
                return data  # Return original description if that's what we got
            raise ValueError(f"Unsupported data format: {type(data)}")
            
        # Process with the traditional method
        return self.complement_screen_actions(screen_description, screenshot_path)

    def complement_screen_actions(self, screen_description: ScreenDescription,
                                  screenshot_path: str) -> ScreenDescription:
        """
        Complement existing actions with screenshot-derived insights.

        Args:
            screen_description: Original screen description
            screenshot_path: Path to the screenshot image

        Returns:
            Enhanced screen description with complementary actions
        """
        self.logger.debug(f"Complementing screen actions for {screen_description.activity}")

        try:
            # Check cache first
            cache_key = self._generate_cache_key(screenshot_path)
            cached_result = self._get_from_cache(cache_key)

            if cached_result:
                self.logger.debug("Using cached screenshot analysis")
                analysis_result = cached_result
            else:
                # Analyze screenshot
                self.logger.debug(f"Analyzing screenshot: {screenshot_path}")
                analyzer = ScreenshotAnalyzer(image_path=screenshot_path)
                analysis_result = analyzer.extract_information()

                # Cache the result
                self._add_to_cache(cache_key, analysis_result)

            # Process analysis result
            return self._process_analysis_result(screen_description, analysis_result)

        except Exception as e:
            self.logger.error(f"Error complementing screen actions: {e}")
            # Return original screen description on error
            return screen_description

    def _process_analysis_result(self, screen_description: ScreenDescription,
                                 analysis_result: Dict[str, Any]) -> ScreenDescription:
        """
        Process analysis result to enhance screen description.

        Args:
            screen_description: Original screen description
            analysis_result: Result from screenshot analysis

        Returns:
            Enhanced screen description
        """
        # Extract data from analysis result
        buttons = analysis_result.get("buttons", [])
        texts = analysis_result.get("texts", [])
        error_indicators = analysis_result.get("error_indicators", [])

        # Track existing items' bounding boxes
        existing_bounds: List[Tuple[int, int, int, int]] = []
        for item in screen_description.items:
            if "bounds" in item.view:
                bounds = item.view["bounds"]
                if isinstance(bounds, list) and len(bounds) == 2:
                    # Convert [[x1, y1], [x2, y2]] to (x1, y1, x2, y2)
                    existing_bounds.append((bounds[0][0], bounds[0][1], bounds[1][0], bounds[1][1]))

        # Process visual buttons that don't overlap with existing elements
        complementary_items = []

        # Identify error conditions first
        error_fields = set()
        error_count = 0

        for error in error_indicators:
            error_count += 1
            error_x = error.get("x", 0)
            error_y = error.get("y", 0)
            error_width = error.get("width", 0)
            error_height = error.get("height", 0)
            red_intensity = error.get("red_intensity", 0)

            # Check if this error indicator is near any existing elements
            found_matching_element = False
            for item in screen_description.items:
                if "bounds" in item.view:
                    bounds = item.view["bounds"]
                    if isinstance(bounds, list) and len(bounds) == 2:
                        item_x1, item_y1 = bounds[0]
                        item_x2, item_y2 = bounds[1]

                        # Check if error overlaps with item
                        if (self._check_overlap(
                                error_x, error_y, error_x + error_width, error_y + error_height,
                                item_x1, item_y1, item_x2, item_y2
                        )):
                            # Mark this element as having an error
                            item.view["has_error"] = True

                            # Add error intensity information
                            item.view["error_intensity"] = red_intensity

                            # Add this item to error fields
                            error_fields.add(id(item))
                            found_matching_element = True

            # If no matching element found, create a standalone error indicator
            if not found_matching_element:
                # Create visual indicator for standalone error
                error_item = self._create_visual_error_indicator(error)
                if error_item:
                    complementary_items.append(error_item)

        # Process visual buttons
        for button in buttons:
            button_x = button.get("x", 0)
            button_y = button.get("y", 0)
            button_width = button.get("width", 0)
            button_height = button.get("height", 0)

            # Check if this button overlaps with any existing element
            is_overlapping = False
            for x1, y1, x2, y2 in existing_bounds:
                if self._check_overlap(
                        button_x, button_y, button_x + button_width, button_y + button_height,
                        x1, y1, x2, y2
                ):
                    is_overlapping = True
                    break

            # If not overlapping, add as a new element
            if not is_overlapping:
                visual_button = self._create_visual_button(button)
                complementary_items.append(visual_button)

        # Look for important text areas that might be interactive
        for text_item in texts:
            text = text_item.get("text", "")
            confidence = text_item.get("confidence", 0)

            # Only consider high confidence text
            if confidence < 70:
                continue

            bbox = text_item.get("bbox", {})
            if not bbox:
                continue

            text_x = bbox.get("x", 0)
            text_y = bbox.get("y", 0)
            text_width = bbox.get("width", 0)
            text_height = bbox.get("height", 0)

            # Check if this text overlaps with any existing element
            is_overlapping = False
            for x1, y1, x2, y2 in existing_bounds:
                if self._check_overlap(
                        text_x, text_y, text_x + text_width, text_y + text_height,
                        x1, y1, x2, y2
                ):
                    is_overlapping = True
                    break

            # If not overlapping and looks like a button (e.g., "OK", "Cancel", etc.)
            if not is_overlapping and self._looks_like_button_text(text):
                visual_text_button = self._create_visual_text_button(text_item)
                complementary_items.append(visual_text_button)

        # Update original screen description to suggest errors for error fields
        for item in screen_description.items:
            if id(item) in error_fields:
                # If this is a text field with an error, prioritize interacting with it
                if "EditText" in item.view.get("class", ""):
                    # Add or update SET_TEXT action with high priority
                    set_text_action = None
                    for action in item.actions:
                        if "SET_TEXT" in action.text:
                            set_text_action = action
                            break

                    if set_text_action:
                        # Modify existing action text to indicate error
                        set_text_action.text = set_text_action.text.replace("SET_TEXT", "SET_TEXT (Error Field)")
                    else:
                        # Add new SET_TEXT action
                        action_id = self.counter.inc()
                        item.actions.append(ItemAction(
                            id=action_id,
                            text=f"SET_TEXT (Error Field) ({action_id})",
                            event="TEXT_CHANGE",
                            target_view=item.view,
                            coordinates=self._get_center_coordinates(item.view)
                        ))

        # Create new screen description with additional items
        all_items = screen_description.items + complementary_items
        enhanced_screen = ScreenDescription(screen_description.activity, all_items)
        
        # Log processing summary
        self.log_processing_summary("visual elements", len(complementary_items))
        if error_count > 0:
            self.log_processing_summary("error indicators", error_count)

        return enhanced_screen

    def _create_visual_button(self, button_data: Dict[str, Any]) -> Any:
        """
        Create a screen item for a visually detected button.

        Args:
            button_data: Button data from screenshot analysis

        Returns:
            ScreenItem representing the visual button
        """

        # Create view data
        button_x = button_data.get("x", 0)
        button_y = button_data.get("y", 0)
        button_width = button_data.get("width", 0)
        button_height = button_data.get("height", 0)

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
            "visual_element": True  # Mark as visually detected
        }

        # Create actions
        actions = []

        # Click action
        action_id = self.counter.inc()
        actions.append(ItemAction(
            id=action_id,
            text=f"CLICK (Visual) ({action_id})",
            event="CLICK",
            target_view=view_data,
            coordinates=((button_x + button_x + button_width) // 2, (button_y + button_y + button_height) // 2)
        ))

        # Long click action
        action_id = self.counter.inc()
        actions.append(ItemAction(
            id=action_id,
            text=f"LONG_CLICK (Visual) ({action_id})",
            event="LONG_CLICK",
            target_view=view_data,
            coordinates=((button_x + button_x + button_width) // 2, (button_y + button_y + button_height) // 2)
        ))

        # Create screen item
        return ScreenItem(
            view=view_data,
            base_description=f"Visual Button at ({button_x}, {button_y})",
            actions=actions
        )

    def _create_visual_text_button(self, text_data: Dict[str, Any]) -> Any:
        """
        Create a screen item for a text element that looks like a button.

        Args:
            text_data: Text data from screenshot analysis

        Returns:
            ScreenItem representing the visual text button
        """
        from rvandroid.parser.screen.visitor.model import ScreenItem

        # Extract text info
        text = text_data.get("text", "Button")
        confidence = text_data.get("confidence", 0)
        bbox = text_data.get("bbox", {})

        text_x = bbox.get("x", 0)
        text_y = bbox.get("y", 0)
        text_width = bbox.get("width", 0)
        text_height = bbox.get("height", 0)

        # Create view data
        view_data = {
            "class": "android.widget.Button",
            "resource_id": f"visual_text_button_{text_x}_{text_y}",
            "text": text,
            "bounds": [[text_x, text_y], [text_x + text_width, text_y + text_height]],
            "clickable": True,
            "checkable": False,
            "scrollable": False,
            "long_clickable": True,
            "focused": False,
            "selected": False,
            "visual_element": True,  # Mark as visually detected
            "confidence": confidence
        }

        # Create actions
        actions = []

        # Click action
        action_id = self.counter.inc()
        actions.append(ItemAction(
            id=action_id,
            text=f"CLICK (Visual Text: '{text}') ({action_id})",
            event="CLICK",
            target_view=view_data,
            coordinates=((text_x + text_x + text_width) // 2, (text_y + text_y + text_height) // 2)
        ))

        # Create screen item
        return ScreenItem(
            view=view_data,
            base_description=f"Visual Text Button '{text}' at ({text_x}, {text_y})",
            actions=actions
        )

    def _generate_cache_key(self, screenshot_path: str) -> str:
        """
        Generate a cache key for a screenshot.

        Args:
            screenshot_path: Path to the screenshot

        Returns:
            Cache key string
        """
        # Use file modification time and size for cache key
        try:
            file_stats = os.stat(screenshot_path)
            mod_time = file_stats.st_mtime
            file_size = file_stats.st_size

            # Combine path, size and modification time for a unique key
            return f"{screenshot_path}_{file_size}_{mod_time}"
        except:
            # Fallback to just the path if stats can't be read
            return screenshot_path

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get analysis result from cache.

        Args:
            cache_key: Cache key to look up

        Returns:
            Cached analysis result or None if not found
        """
        return self.analysis_cache.get(cache_key)

    def _add_to_cache(self, cache_key: str, analysis_result: Dict[str, Any]) -> None:
        """
        Add analysis result to cache.

        Args:
            cache_key: Cache key to store under
            analysis_result: Result to cache
        """
        # Add to cache
        self.analysis_cache[cache_key] = analysis_result

        # Add to key list for tracking cache size
        self.cache_keys.append(cache_key)

        # Trim cache if it's too large
        if len(self.cache_keys) > self.cache_size:
            # Remove oldest entry
            oldest_key = self.cache_keys.pop(0)
            if oldest_key in self.analysis_cache:
                del self.analysis_cache[oldest_key]

    def _check_overlap(self, x1: int, y1: int, x2: int, y2: int,
                       x3: int, y3: int, x4: int, y4: int) -> bool:
        """
        Check if two rectangles overlap.

        Args:
            x1, y1, x2, y2: Bounds of first rectangle (top-left, bottom-right)
            x3, y3, x4, y4: Bounds of second rectangle (top-left, bottom-right)

        Returns:
            True if rectangles overlap, False otherwise
        """
        # Check if one rectangle is to the left of the other
        if x2 < x3 or x4 < x1:
            return False

        # Check if one rectangle is above the other
        if y2 < y3 or y4 < y1:
            return False

        # If neither of the above, rectangles overlap
        return True

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

    def _create_visual_error_indicator(self, error_data: Dict[str, Any]) -> Any:
        """
        Create a screen item for a visual error indicator.

        Args:
            error_data: Error indicator data from screenshot analysis

        Returns:
            ScreenItem representing the visual error indicator
        """
        from rvandroid.parser.screen.visitor.model import ScreenItem

        # Extract error info
        error_x = error_data.get("x", 0)
        error_y = error_data.get("y", 0)
        error_width = error_data.get("width", 0)
        error_height = error_data.get("height", 0)
        red_intensity = error_data.get("red_intensity", 0)

        # Create view data
        view_data = {
            "class": "android.widget.TextView",  # Use TextView as base class
            "resource_id": f"visual_error_{error_x}_{error_y}",
            "text": "Error Indicator",
            "bounds": [[error_x, error_y], [error_x + error_width, error_y + error_height]],
            "clickable": True,
            "checkable": False,
            "scrollable": False,
            "long_clickable": False,
            "focused": False,
            "selected": False,
            "visual_element": True,  # Mark as visually detected
            "has_error": True,  # Mark as error
            "error_intensity": red_intensity
        }

        # Create actions
        actions = []

        # Click action
        action_id = self.counter.inc()
        actions.append(ItemAction(
            id=action_id,
            text=f"CLICK (Error Indicator) ({action_id})",
            event="CLICK",
            target_view=view_data,
            coordinates=((error_x + error_x + error_width) // 2, (error_y + error_y + error_height) // 2)
        ))

        # Create screen item
        return ScreenItem(
            view=view_data,
            base_description=f"Visual Error Indicator at ({error_x}, {error_y})",
            actions=actions
        )

    def _get_center_coordinates(self, view: Dict[str, Any]) -> Optional[Tuple[int, int]]:
        """
        Get center coordinates of a view.

        Args:
            view: View data dictionary

        Returns:
            (x, y) tuple of center coordinates or None if bounds not found
        """
        if "bounds" not in view:
            return None

        bounds = view["bounds"]
        if not isinstance(bounds, list) or len(bounds) != 2:
            return None

        try:
            x1, y1 = bounds[0]
            x2, y2 = bounds[1]
            return ((x1 + x2) // 2, (y1 + y2) // 2)
        except (TypeError, IndexError):
            return None
            
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get metrics from the analyzer.
        
        Returns:
            Dictionary containing metrics and their values
        """
        return {
            "cache_size": self.cache_size,
            "cache_utilization": len(self.cache_keys),
            "cache_hit_ratio": len(self.cache_keys) / self.cache_size if self.cache_size > 0 else 0
        }
