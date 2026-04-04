#!/usr/bin/env python3
"""
Interactive element detection component for screenshot analysis.

This module provides comprehensive detection of interactive UI elements including
sliders, switches, input fields, navigation elements, and other clickable
components that may not be properly identified through standard UI hierarchy.

### Architectural Role:
- Implements multi-strategy interactive element detection using visual cues
- Provides pattern-based detection for form controls and navigation elements
- Handles confidence scoring based on geometric and visual characteristics
- Generates validated InteractiveElement models with comprehensive metadata

### Design Decisions:
- Uses edge detection and contour analysis for slider and progress bar detection
- Implements geometric pattern matching for switches and toggle elements
- Supports text field detection through border and cursor pattern analysis
- Integrates with existing text detection for enhanced element classification
"""

import math
from typing import List, Optional, Tuple
import cv2
import numpy as np

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVParsingError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager

from ..models import DetectedText, InteractiveElement, InteractiveElementType, DetectionMethod
from ..utils.geometry_utils import get_geometry_utils


class InteractiveElementDetector:
    """
    Multi-strategy interactive element detection component for screenshot analysis.
    
    Combines visual pattern analysis, geometric detection, and contextual information
    to identify interactive UI elements with confidence scoring.
    """
    
    def __init__(self):
        """Initialize interactive element detector with configuration parameters."""
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "screenshot.interactive_detector",
            {CONTEXT_COMPONENT: "InteractiveElementDetector"}
        )
        self.geometry_utils = get_geometry_utils()
        
        # Input field indicators for enhanced detection
        self.input_field_indicators = [
            "email", "password", "username", "phone", "name", "address",
            "search", "input", "enter", "type", "field", "@", ".com"
        ]
        
        # Navigation indicators
        self.navigation_indicators = [
            "next", "previous", "back", "forward", "home", "menu", "settings",
            "tab", "page", "→", "←", "↑", "↓", "▶", "◀", "⬆", "⬇"
        ]
        
        # Switch/toggle indicators
        self.switch_indicators = [
            "on", "off", "enable", "disable", "toggle", "switch"
        ]
    
    @ErrorHandler.handle_errors(component="InteractiveElementDetector", phase="element_detection", reraise=True)
    def detect_interactive_elements(self, binary_image: np.ndarray, original_image: np.ndarray, 
                                   texts: List[DetectedText]) -> List[InteractiveElement]:
        """
        Detect interactive elements using multiple detection strategies.
        
        Combines visual analysis, geometric patterns, and contextual information
        to find interactive UI elements with confidence scoring.
        
        Args:
            binary_image: Preprocessed binary image for contour detection
            original_image: Original color image for visual analysis
            texts: List of detected text elements for context
            
        Returns:
            List of validated InteractiveElement models
            
        Raises:
            RVParsingError: If interactive element detection fails
        """
        if binary_image is None or original_image is None:
            raise RVParsingError(
                "Cannot detect interactive elements with null images",
                parser_type="InteractiveElementDetector"
            )
        
        elements = []
        
        # Strategy 1: Slider and progress bar detection
        sliders = self._detect_sliders(binary_image, original_image, texts)
        elements.extend(sliders)
        
        # Strategy 2: Switch and toggle detection
        switches = self._detect_switches(binary_image, original_image, texts)
        elements.extend(switches)
        
        # Strategy 3: Input field detection
        input_fields = self._detect_input_fields(binary_image, original_image, texts)
        elements.extend(input_fields)
        
        # Strategy 4: Navigation element detection
        navigation = self._detect_navigation_elements(binary_image, original_image, texts)
        elements.extend(navigation)
        
        # Strategy 5: Generic clickable element detection
        clickables = self._detect_clickable_elements(binary_image, original_image, texts, elements)
        elements.extend(clickables)
        
        # Strategy 6: Board game element detection
        board_game_elements = self._detect_board_game_elements(binary_image, original_image, texts)
        elements.extend(board_game_elements)
        
        # Sort elements by confidence (higher first)
        elements.sort(key=lambda e: e.confidence, reverse=True)
        
        self.logger.info(f"Detected {len(elements)} interactive elements ({len(sliders)} sliders, {len(switches)} switches, {len(input_fields)} input fields, {len(navigation)} navigation, {len(clickables)} clickables, {len(board_game_elements)} board game elements)")
        return elements
    
    def _detect_sliders(self, binary_image: np.ndarray, original_image: np.ndarray,
                       texts: List[DetectedText]) -> List[InteractiveElement]:
        """
        Detect slider and progress bar elements.
        
        Args:
            binary_image: Binary image for contour detection
            original_image: Original image for visual analysis
            texts: Text elements for context
            
        Returns:
            List of detected slider elements
        """
        sliders = []
        height, width = original_image.shape[:2]
        
        # Find horizontal lines that could be sliders
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
        horizontal_lines = cv2.morphologyEx(binary_image, cv2.MORPH_OPEN, horizontal_kernel)
        
        # Find contours of horizontal lines
        contours, _ = cv2.findContours(horizontal_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            try:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                
                # Look for long, thin horizontal elements (sliders)
                if (aspect_ratio > 8 and w > width * 0.2 and h < height * 0.02 and
                    width * 0.1 <= w <= width * 0.9):
                    
                    # Check for slider thumb/handle nearby
                    thumb_confidence = self._detect_slider_thumb(original_image, x, y, w, h)
                    
                    # Calculate confidence based on aspect ratio and context
                    confidence = 0.5 + min(aspect_ratio / 20, 0.3) + thumb_confidence * 0.2
                    
                    # Check for nearby text that indicates a slider
                    nearby_text = self._find_nearby_text(x, y, w, h, texts, distance=50)
                    if nearby_text and any(word in nearby_text.lower() for word in ["volume", "brightness", "speed", "level", "amount"]):
                        confidence = min(confidence + 0.2, 1.0)
                    
                    if confidence >= 0.6:
                        slider = self._create_interactive_element(
                            x, y, w, h, confidence, InteractiveElementType.SLIDER,
                            f"Slider: {nearby_text}" if nearby_text else "Horizontal slider"
                        )
                        if slider:
                            sliders.append(slider)
                            
            except Exception as e:
                self.logger.warning(f"Error analyzing contour for slider: {e}")
        
        return sliders
    
    def _detect_switches(self, binary_image: np.ndarray, original_image: np.ndarray,
                        texts: List[DetectedText]) -> List[InteractiveElement]:
        """
        Detect switch and toggle elements.
        
        Args:
            binary_image: Binary image for contour detection
            original_image: Original image for visual analysis
            texts: Text elements for context
            
        Returns:
            List of detected switch elements
        """
        switches = []
        height, width = original_image.shape[:2]
        
        # Find small, rounded rectangular contours (potential switches)
        contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            try:
                cv2.contourArea(contour)
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                
                # Look for small, oval-shaped or rounded rectangular elements
                if (1.5 <= aspect_ratio <= 3.0 and
                    width * 0.02 <= w <= width * 0.15 and
                    height * 0.01 <= h <= height * 0.08):
                    
                    # Check if contour is rounded (switch-like)
                    epsilon = 0.02 * cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, epsilon, True)
                    
                    # Switches typically have many points (rounded) or are rectangular
                    roundness_score = 1.0 - (len(approx) / 20) if len(approx) > 4 else 0.8
                    
                    # Check for switch colors (often have different colors for on/off states)
                    roi = original_image[y:y + h, x:x + w]
                    color_variance = self._calculate_color_variance(roi)
                    
                    confidence = 0.4 + roundness_score * 0.3 + color_variance * 0.2
                    
                    # Check for nearby switch-related text
                    nearby_text = self._find_nearby_text(x, y, w, h, texts, distance=100)
                    if nearby_text:
                        if any(indicator in nearby_text.lower() for indicator in self.switch_indicators):
                            confidence = min(confidence + 0.3, 1.0)
                        elif any(word in nearby_text.lower() for word in ["notifications", "wifi", "bluetooth", "auto"]):
                            confidence = min(confidence + 0.2, 1.0)
                    
                    if confidence >= 0.5:
                        switch = self._create_interactive_element(
                            x, y, w, h, confidence, InteractiveElementType.SWITCH,
                            f"Switch: {nearby_text}" if nearby_text else "Toggle switch"
                        )
                        if switch:
                            switches.append(switch)
                            
            except Exception as e:
                self.logger.warning(f"Error analyzing contour for switch: {e}")
        
        return switches
    
    def _detect_input_fields(self, binary_image: np.ndarray, original_image: np.ndarray,
                            texts: List[DetectedText]) -> List[InteractiveElement]:
        """
        Detect input field elements.
        
        Args:
            binary_image: Binary image for contour detection
            original_image: Original image for visual analysis
            texts: Text elements for context
            
        Returns:
            List of detected input field elements
        """
        input_fields = []
        height, width = original_image.shape[:2]
        
        # Find rectangular contours that could be input fields
        contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            try:
                area = cv2.contourArea(contour)
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                
                # Look for rectangular elements with input field proportions
                if (3 <= aspect_ratio <= 10 and
                    width * 0.15 <= w <= width * 0.9 and
                    height * 0.03 <= h <= height * 0.12):
                    
                    # Check if contour is rectangular (input field-like)
                    epsilon = 0.02 * cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, epsilon, True)
                    
                    rectangularity = 1.0 if len(approx) == 4 else max(0, 1.0 - abs(len(approx) - 4) * 0.1)
                    
                    # Check for input field characteristics
                    roi = original_image[y:y + h, x:x + w]
                    border_score = self._detect_input_border(roi)
                    
                    confidence = 0.3 + rectangularity * 0.3 + border_score * 0.2
                    
                    # Check for input field related text nearby or inside
                    nearby_text = self._find_nearby_text(x, y, w, h, texts, distance=150)
                    inside_text = self._find_text_inside_element(x, y, w, h, texts)
                    
                    if nearby_text or inside_text:
                        text_content = (nearby_text or "") + " " + (inside_text or "")
                        if any(indicator in text_content.lower() for indicator in self.input_field_indicators):
                            confidence = min(confidence + 0.4, 1.0)
                        elif any(char in text_content for char in ["@", ".", "_", "-"]):
                            confidence = min(confidence + 0.3, 1.0)
                        elif "hint" in text_content.lower() or "placeholder" in text_content.lower():
                            confidence = min(confidence + 0.2, 1.0)
                    
                    if confidence >= 0.5:
                        field_type = self._classify_input_field(text_content if 'text_content' in locals() else "")
                        input_field = self._create_interactive_element(
                            x, y, w, h, confidence, field_type,
                            f"Input field: {text_content[:50]}" if 'text_content' in locals() and text_content else "Text input field"
                        )
                        if input_field:
                            input_fields.append(input_field)
                            
            except Exception as e:
                self.logger.warning(f"Error analyzing contour for input field: {e}")
        
        return input_fields
    
    def _detect_navigation_elements(self, binary_image: np.ndarray, original_image: np.ndarray,
                                   texts: List[DetectedText]) -> List[InteractiveElement]:
        """
        Detect navigation elements (arrows, page indicators, tabs).
        
        Args:
            binary_image: Binary image for contour detection
            original_image: Original image for visual analysis
            texts: Text elements for context
            
        Returns:
            List of detected navigation elements
        """
        navigation = []
        height, width = original_image.shape[:2]
        
        # Look for navigation-related text elements
        for text_element in texts:
            bbox = text_element.bbox
            text_content = text_element.text.lower()
            
            # Check if text contains navigation indicators
            nav_score = 0.0
            for indicator in self.navigation_indicators:
                if indicator in text_content:
                    nav_score += 0.3
            
            # Check for navigation symbols
            nav_symbols = ["→", "←", "↑", "↓", "▶", "◀", "⬆", "⬇", "⋯", "••"]
            for symbol in nav_symbols:
                if symbol in text_element.text:
                    nav_score += 0.5
            
            # Check position for common navigation locations
            position_score = 0.0
            
            # Bottom navigation
            if bbox.y > height * 0.85:
                position_score += 0.3
            # Top navigation
            elif bbox.y < height * 0.15:
                position_score += 0.2
            # Side navigation
            elif bbox.x < width * 0.1 or bbox.x > width * 0.9:
                position_score += 0.2
            
            confidence = min(nav_score + position_score, 1.0)
            
            if confidence >= 0.4:
                # Expand bounding box slightly for better interaction area
                expanded_x = max(0, bbox.x - 10)
                expanded_y = max(0, bbox.y - 10)
                expanded_w = min(width - expanded_x, bbox.width + 20)
                expanded_h = min(height - expanded_y, bbox.height + 20)
                
                nav_element = self._create_interactive_element(
                    expanded_x, expanded_y, expanded_w, expanded_h,
                    confidence, InteractiveElementType.NAVIGATION,
                    f"Navigation: {text_element.text}"
                )
                if nav_element:
                    navigation.append(nav_element)
        
        return navigation
    
    def _detect_clickable_elements(self, binary_image: np.ndarray, original_image: np.ndarray,
                                  texts: List[DetectedText], existing_elements: List[InteractiveElement]) -> List[InteractiveElement]:
        """
        Detect generic clickable elements not covered by other strategies.
        
        Args:
            binary_image: Binary image for contour detection
            original_image: Original image for visual analysis
            texts: Text elements for context
            existing_elements: Already detected elements to avoid duplicates
            
        Returns:
            List of detected clickable elements
        """
        clickables = []
        height, width = original_image.shape[:2]
        
        # Find medium-sized contours that could be clickable
        contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            try:
                area = cv2.contourArea(contour)
                x, y, w, h = cv2.boundingRect(contour)
                
                # Look for medium-sized elements
                if (width * 0.05 <= w <= width * 0.4 and
                    height * 0.03 <= h <= height * 0.2 and
                    area > (width * height) * 0.002):
                    
                    # Check if this overlaps with existing elements
                    if self._overlaps_with_existing(x, y, w, h, existing_elements):
                        continue
                    
                    # Calculate clickability score based on various factors
                    shape_score = self._calculate_shape_clickability(contour)
                    position_score = self._calculate_position_clickability(x, y, w, h, width, height)
                    
                    # Check for associated text
                    associated_text = self._find_text_inside_element(x, y, w, h, texts)
                    text_score = 0.2 if associated_text else 0.0
                    
                    confidence = min(shape_score + position_score + text_score, 1.0)
                    
                    if confidence >= 0.4:
                        clickable = self._create_interactive_element(
                            x, y, w, h, confidence, InteractiveElementType.CLICKABLE,
                            f"Clickable: {associated_text}" if associated_text else "Interactive element"
                        )
                        if clickable:
                            clickables.append(clickable)
                            
            except Exception as e:
                self.logger.warning(f"Error analyzing contour for clickable element: {e}")
        
        return clickables
    
    def _detect_slider_thumb(self, image: np.ndarray, track_x: int, track_y: int, 
                            track_w: int, track_h: int) -> float:
        """Detect slider thumb/handle near the track."""
        try:
            # Look for small circular or square elements near the track
            search_area = 20
            roi_x = max(0, track_x - search_area)
            roi_y = max(0, track_y - search_area)
            roi_w = min(image.shape[1] - roi_x, track_w + 2 * search_area)
            roi_h = min(image.shape[0] - roi_y, track_h + 2 * search_area)
            
            roi = image[roi_y:roi_y + roi_h, roi_x:roi_x + roi_w]
            gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
            
            # Use Hough circles to detect circular thumbs
            circles = cv2.HoughCircles(
                gray_roi, cv2.HOUGH_GRADIENT, dp=1, minDist=10,
                param1=50, param2=30, minRadius=5, maxRadius=track_h * 2
            )
            
            return 0.5 if circles is not None and len(circles[0]) > 0 else 0.0
            
        except Exception:
            return 0.0
    
    def _calculate_color_variance(self, roi: np.ndarray) -> float:
        """Calculate color variance in ROI (switches often have color variation)."""
        try:
            if roi.size == 0 or len(roi.shape) != 3:
                return 0.0
            
            # Calculate variance in each color channel
            variances = [np.var(roi[:, :, i]) for i in range(3)]
            avg_variance = np.mean(variances)
            
            # Normalize to 0-1 range
            return min(avg_variance / 1000, 1.0)
            
        except Exception:
            return 0.0
    
    def _detect_input_border(self, roi: np.ndarray) -> float:
        """Detect border patterns typical of input fields."""
        try:
            if roi.size == 0:
                return 0.0
            
            gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
            
            # Detect edges
            edges = cv2.Canny(gray_roi, 50, 150)
            
            # Check if edges form a rectangle (input field border)
            h, w = edges.shape
            
            # Check top and bottom edges
            top_edge = np.sum(edges[0:2, :]) > w * 0.3
            bottom_edge = np.sum(edges[h-2:h, :]) > w * 0.3
            
            # Check left and right edges
            left_edge = np.sum(edges[:, 0:2]) > h * 0.3
            right_edge = np.sum(edges[:, w-2:w]) > h * 0.3
            
            border_score = sum([top_edge, bottom_edge, left_edge, right_edge]) / 4.0
            return border_score
            
        except Exception:
            return 0.0
    
    def _classify_input_field(self, text_content: str) -> InteractiveElementType:
        """Classify input field type based on associated text."""
        # For now, return generic input field type since specific subtypes are not in enum
        return InteractiveElementType.INPUT_FIELD
    
    def _calculate_shape_clickability(self, contour) -> float:
        """Calculate how clickable a shape appears based on its geometry."""
        try:
            # Rectangular shapes are more likely to be clickable
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            if len(approx) == 4:
                return 0.3  # Rectangular
            elif 4 < len(approx) < 8:
                return 0.25  # Rounded rectangle
            else:
                return 0.1  # Other shapes
                
        except Exception:
            return 0.0
    
    def _calculate_position_clickability(self, x: int, y: int, w: int, h: int,
                                        img_width: int, img_height: int) -> float:
        """Calculate clickability based on position (UI elements often in specific areas)."""
        score = 0.0
        
        # Center area is often clickable
        center_x = x + w / 2
        center_y = y + h / 2
        
        if img_width * 0.2 <= center_x <= img_width * 0.8:
            score += 0.1
        
        if img_height * 0.2 <= center_y <= img_height * 0.8:
            score += 0.1
        
        return score
    
    def _find_nearby_text(self, x: int, y: int, w: int, h: int, 
                         texts: List[DetectedText], distance: int = 100) -> Optional[str]:
        """Find text near an element."""
        center_x = x + w / 2
        center_y = y + h / 2
        
        nearby_texts = []
        for text_element in texts:
            text_center_x = text_element.bbox.center_x
            text_center_y = text_element.bbox.center_y
            
            dist = math.sqrt((center_x - text_center_x) ** 2 + (center_y - text_center_y) ** 2)
            if dist <= distance:
                nearby_texts.append((text_element.text, dist))
        
        if nearby_texts:
            # Return closest text
            nearby_texts.sort(key=lambda t: t[1])
            return nearby_texts[0][0]
        
        return None
    
    def _find_text_inside_element(self, x: int, y: int, w: int, h: int, 
                                 texts: List[DetectedText]) -> Optional[str]:
        """Find text inside an element."""
        contained_texts = []
        
        for text_element in texts:
            bbox = text_element.bbox
            if (x <= bbox.center_x <= x + w and y <= bbox.center_y <= y + h):
                contained_texts.append(text_element.text)
        
        return " ".join(contained_texts) if contained_texts else None
    
    def _overlaps_with_existing(self, x: int, y: int, w: int, h: int,
                               existing_elements: List[InteractiveElement]) -> bool:
        """Check if element overlaps with existing detected elements."""
        for element in existing_elements:
            ex, ey, ew, eh = element.bbox.x, element.bbox.y, element.bbox.width, element.bbox.height
            
            try:
                overlap = self.geometry_utils.calculate_overlap_percentage(x, y, w, h, ex, ey, ew, eh)
                if overlap > 0.5:
                    return True
            except Exception as e:
                self.logger.warning(f"Error checking element overlap: {e}")
        
        return False
    
    def _create_interactive_element(self, x: int, y: int, w: int, h: int,
                                   confidence: float, element_type: InteractiveElementType,
                                   description: str) -> Optional[InteractiveElement]:
        """Create a validated InteractiveElement model."""
        try:
            return InteractiveElement(
                x=x,
                y=y,
                width=w,
                height=h,
                type=element_type,
                confidence=float(confidence),
                detection_method=DetectionMethod.PATTERN,  # Default to pattern detection
                aspect_ratio=float(w / h) if h > 0 else 1.0
            )
        except Exception as validation_error:
            self.logger.warning(f"Failed to create InteractiveElement: {validation_error}")
            return None
    
    def get_interactive_element_summary(self, elements: List[InteractiveElement]) -> dict:
        """
        Get summary statistics about detected interactive elements.
        
        Args:
            elements: List of detected interactive elements
            
        Returns:
            Dictionary with detection statistics
        """
        total_elements = len(elements)
        
        # Count by element type
        type_counts = {}
        for element in elements:
            element_type = element.type.value
            type_counts[element_type] = type_counts.get(element_type, 0) + 1
        
        enabled_elements = len(elements)  # Assume all are enabled by default
        high_confidence = sum(1 for e in elements if e.confidence >= 0.8)
        
        return {
            "total_elements": total_elements,
            "enabled_elements": enabled_elements,
            "high_confidence_elements": high_confidence,
            "element_types": type_counts,
            "average_confidence": sum(e.confidence for e in elements) / total_elements if total_elements > 0 else 0.0
        }
    
    def _detect_board_game_elements(self, binary_image: np.ndarray, original_image: np.ndarray,
                                   texts: List[DetectedText]) -> List[InteractiveElement]:
        """
        Detect board game elements using unified pattern recognition.
        
        Identifies interactive elements common to board games including:
        - Game pieces (circular/square colored elements)
        - Board positions (clickable grid cells)
        - Interactive game components based on geometric and color patterns
        
        This method uses a combined approach analyzing spatial arrangements,
        color contrast, geometric patterns, and size consistency to detect
        elements that represent playable components in board games.
        
        Args:
            binary_image: Binary image for contour detection
            original_image: Original image for color and pattern analysis
            texts: Text elements for contextual information
            
        Returns:
            List of detected board game interactive elements
        """
        board_elements = []
        
        try:
            height, width = original_image.shape[:2]
            hsv_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2HSV)
            
            # Find contours for analysis
            contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Analyze spatial patterns to identify grid-like arrangements
            grid_candidates = self._identify_grid_patterns(contours, width, height)
            
            # Process each contour for board game element characteristics
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 400 or area > 12000:  # Filter by reasonable game element size
                    continue
                
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h if h > 0 else 1.0
                
                # Filter out very thin or very wide elements
                if w < 15 or h < 15 or aspect_ratio > 10 or aspect_ratio < 0.1:
                    continue
                
                # Analyze geometric properties
                perimeter = cv2.arcLength(contour, True)
                circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
                
                # Extract region of interest for detailed analysis
                roi = original_image[y:y+h, x:x+w] if y+h <= height and x+w <= width else None
                if roi is None or roi.size == 0:
                    continue
                
                hsv_roi = hsv_image[y:y+h, x:x+w]
                
                # Calculate color characteristics
                saturation = np.mean(hsv_roi[:, :, 1])
                value = np.mean(hsv_roi[:, :, 2])
                hue_variance = np.var(hsv_roi[:, :, 0])
                
                # Determine element type and confidence based on characteristics
                element_type, confidence = self._classify_board_game_element(
                    area, aspect_ratio, circularity, saturation, value, hue_variance,
                    x, y, w, h, width, height, grid_candidates
                )
                
                if confidence > 0.4:  # Minimum confidence threshold
                    board_element = self._create_interactive_element(
                        x, y, w, h, confidence, element_type,
                        f"Board game element at ({x}, {y})"
                    )
                    if board_element:
                        board_element.circularity = circularity
                        board_elements.append(board_element)
                        
        except Exception as e:
            self.logger.warning(f"Error detecting board game elements: {e}")
        
        return board_elements
    
    def _identify_grid_patterns(self, contours, width: int, height: int) -> List[Tuple[int, int]]:
        """
        Identify regular grid patterns that suggest board game layouts.
        
        Analyzes spatial distribution of contours to detect regular arrangements
        characteristic of board games like chess, checkers, or ludo.
        
        Args:
            contours: List of detected contours
            width: Image width for normalization
            height: Image height for normalization
            
        Returns:
            List of (x, y) coordinates representing grid positions
        """
        grid_positions = []
        
        try:
            if len(contours) < 9:  # Need at least 3x3 grid for pattern detection
                return grid_positions
            
            # Extract centers of contours
            centers = []
            for contour in contours:
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    centers.append((cx, cy))
            
            if len(centers) < 9:
                return grid_positions
            
            # Sort centers by position
            centers.sort(key=lambda p: (p[1], p[0]))  # Sort by y first, then x
            
            # Analyze spacing patterns
            x_spacings = []
            y_spacings = []
            
            for i in range(len(centers) - 1):
                dx = abs(centers[i+1][0] - centers[i][0])
                dy = abs(centers[i+1][1] - centers[i][1])
                
                if dx > 20:  # Minimum spacing threshold
                    x_spacings.append(dx)
                if dy > 20:
                    y_spacings.append(dy)
            
            # Check for regular spacing (grid pattern)
            if x_spacings and y_spacings:
                avg_x_spacing = np.mean(x_spacings)
                avg_y_spacing = np.mean(y_spacings)
                
                # Look for consistent spacing (coefficient of variation < 0.3)
                x_cv = np.std(x_spacings) / avg_x_spacing if avg_x_spacing > 0 else 1
                y_cv = np.std(y_spacings) / avg_y_spacing if avg_y_spacing > 0 else 1
                
                if x_cv < 0.3 and y_cv < 0.3:  # Regular grid detected
                    grid_positions = centers
                    
        except Exception as e:
            self.logger.debug(f"Error identifying grid patterns: {e}")
        
        return grid_positions
    
    def _classify_board_game_element(self, area: float, aspect_ratio: float, circularity: float,
                                   saturation: float, value: float, hue_variance: float,
                                   x: int, y: int, w: int, h: int, img_width: int, img_height: int,
                                   grid_positions: List[Tuple[int, int]]) -> Tuple[InteractiveElementType, float]:
        """
        Classify board game element type based on visual and geometric characteristics.
        
        Analyzes multiple factors to determine if an element represents a game piece
        or board position, considering color, shape, size, and spatial context.
        
        Args:
            area: Element area in pixels
            aspect_ratio: Width to height ratio
            circularity: Shape circularity measure (0-1, where 1 is perfect circle)
            saturation: Average color saturation in HSV space
            value: Average brightness value
            hue_variance: Variance in hue values (indicates color uniformity)
            x, y, w, h: Element bounding box coordinates and dimensions
            img_width, img_height: Image dimensions
            grid_positions: Detected grid pattern positions
            
        Returns:
            Tuple of (element_type, confidence_score)
        """
        confidence = 0.0
        element_type = InteractiveElementType.BOARD_GAME_POSITION
        
        # Factor 1: Shape analysis
        if circularity > 0.7:  # Circular elements often represent game pieces
            confidence = min(confidence + 0.3, 1.0)
            element_type = InteractiveElementType.BOARD_GAME_PIECE
        elif 0.8 <= aspect_ratio <= 1.2:  # Square elements could be either
            confidence = min(confidence + 0.2, 1.0)
        
        # Factor 2: Color analysis
        if saturation > 100:  # Colored elements are likely game pieces
            confidence = min(confidence + 0.25, 1.0)
            element_type = InteractiveElementType.BOARD_GAME_PIECE
        elif saturation < 50 and value > 200:  # Light/white elements might be board positions
            confidence = min(confidence + 0.15, 1.0)
        
        # Factor 3: Size consistency (board game elements are often uniform)
        size_score = self._calculate_size_consistency_score(area, grid_positions, img_width, img_height)
        confidence = min(confidence + size_score * 0.2, 1.0)
        
        # Factor 4: Spatial positioning (elements in grid patterns)
        position_score = self._calculate_position_consistency_score(x, y, w, h, grid_positions)
        confidence = min(confidence + position_score * 0.25, 1.0)
        
        # Factor 5: Color uniformity (game pieces often have uniform colors)
        if hue_variance < 100:  # Low variance indicates uniform color
            confidence = min(confidence + 0.1, 1.0)
        
        return element_type, min(confidence, 1.0)
    
    def _calculate_size_consistency_score(self, area: float, grid_positions: List[Tuple[int, int]],
                                        img_width: int, img_height: int) -> float:
        """
        Calculate score based on size consistency with other detected elements.
        
        Board game elements typically have consistent sizes within the game.
        
        Args:
            area: Current element area
            grid_positions: List of grid position coordinates
            img_width, img_height: Image dimensions for normalization
            
        Returns:
            Consistency score (0.0 to 1.0)
        """
        if not grid_positions or len(grid_positions) < 3:
            return 0.5  # Neutral score when no pattern available
        
        # Calculate expected element size based on grid spacing
        total_area = img_width * img_height
        expected_element_area = total_area / (len(grid_positions) * 4)  # Rough estimate
        
        # Score based on how close the area is to expected size
        size_ratio = area / expected_element_area if expected_element_area > 0 else 0
        
        if 0.5 <= size_ratio <= 2.0:  # Within reasonable range
            return 1.0 - abs(size_ratio - 1.0)  # Closer to 1.0 = higher score
        
        return 0.0
    
    def _calculate_position_consistency_score(self, x: int, y: int, w: int, h: int,
                                            grid_positions: List[Tuple[int, int]]) -> float:
        """
        Calculate score based on alignment with detected grid pattern.
        
        Elements that align with grid patterns are more likely to be board game components.
        
        Args:
            x, y, w, h: Element bounding box
            grid_positions: List of detected grid positions
            
        Returns:
            Alignment score (0.0 to 1.0)
        """
        if not grid_positions:
            return 0.3  # Neutral score when no grid detected
        
        element_center_x = x + w // 2
        element_center_y = y + h // 2
        
        # Find closest grid position
        min_distance = float('inf')
        for gx, gy in grid_positions:
            distance = math.sqrt((element_center_x - gx) ** 2 + (element_center_y - gy) ** 2)
            min_distance = min(min_distance, distance)
        
        # Score based on proximity to grid positions
        if min_distance < 30:  # Very close to grid position
            return 1.0
        elif min_distance < 60:  # Reasonably close
            return 0.7
        elif min_distance < 100:  # Somewhat close
            return 0.4
        
        return 0.1  # Not aligned with grid
    


# Global instance for convenient access
_interactive_element_detector = None

def get_interactive_element_detector() -> InteractiveElementDetector:
    """
    Get the global interactive element detector instance.
    
    Returns:
        InteractiveElementDetector instance
    """
    global _interactive_element_detector
    if _interactive_element_detector is None:
        _interactive_element_detector = InteractiveElementDetector()
    return _interactive_element_detector