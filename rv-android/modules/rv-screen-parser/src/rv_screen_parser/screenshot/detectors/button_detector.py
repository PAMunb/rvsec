#!/usr/bin/env python3
"""
Button detection component for screenshot analysis.

This module provides comprehensive button detection capabilities using
shape analysis, text association, and confidence scoring to identify
clickable UI elements in mobile applications and games.

### Architectural Role:
- Implements multi-strategy button detection (shape-based and text-based)
- Provides confidence scoring based on geometric and visual characteristics
- Associates detected text with button elements for enhanced classification
- Generates validated DetectedButton models with comprehensive metadata

### Design Decisions:
- Uses contour analysis for shape-based button detection
- Implements confidence scoring based on multiple visual factors
- Supports both traditional UI buttons and game interface elements
- Integrates text detection results for improved button identification
"""

from typing import List, Optional, Tuple
import cv2
import numpy as np

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.exceptions import RVParsingError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager

from ..models import DetectedText, DetectedButton, DetectionMethod
from ..utils.geometry_utils import get_geometry_utils


class ButtonDetector:
    """
    Multi-strategy button detection component for screenshot analysis.
    
    Combines shape analysis, text association, and visual characteristics
    to identify clickable button elements with confidence scoring.
    """
    
    def __init__(self):
        """Initialize button detector with configuration parameters."""
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "screenshot.button_detector",
            {CONTEXT_COMPONENT: "ButtonDetector"}
        )
        self.geometry_utils = get_geometry_utils()
        
        # Button text indicators for enhanced detection
        self.button_text_indicators = [
            "ok", "cancel", "yes", "no", "submit", "login", "sign in", "register",
            "next", "previous", "continue", "back", "done", "save", "delete",
            "add", "remove", "close", "send", "search", "buy", "purchase",
            "confirm", "accept", "decline", "agree", "disagree", "play", "start",
            "settings", "menu", "options", "help", "skip", "retry", "reload"
        ]
    
    @ErrorHandler.handle_errors(component="ButtonDetector", phase="button_detection", reraise=True)
    def detect_buttons(self, binary_image: np.ndarray, original_image: np.ndarray, 
                      texts: List[DetectedText]) -> List[DetectedButton]:
        """
        Detect button elements using multiple detection strategies.
        
        Combines shape-based detection with text-based identification
        to find clickable UI elements with confidence scoring.
        
        Args:
            binary_image: Preprocessed binary image for contour detection
            original_image: Original color image for visual analysis
            texts: List of detected text elements for association
            
        Returns:
            List of validated DetectedButton models
            
        Raises:
            RVParsingError: If button detection fails
        """
        if binary_image is None or original_image is None:
            raise RVParsingError(
                "Cannot detect buttons with null images",
                parser_type="ButtonDetector"
            )
        
        buttons = []
        
        # Strategy 1: Shape-based button detection
        shape_buttons = self._detect_shape_buttons(binary_image, original_image, texts)
        buttons.extend(shape_buttons)
        
        # Strategy 2: Text-based button detection
        text_buttons = self._detect_text_buttons(texts, buttons)
        buttons.extend(text_buttons)
        
        # Sort buttons by confidence (higher first)
        buttons.sort(key=lambda b: b.confidence, reverse=True)
        
        self.logger.info(f"Detected {len(buttons)} buttons ({len(shape_buttons)} shape-based, {len(text_buttons)} text-based)")
        return buttons
    
    def _detect_shape_buttons(self, binary_image: np.ndarray, original_image: np.ndarray,
                             texts: List[DetectedText]) -> List[DetectedButton]:
        """
        Detect buttons based on shape analysis and contour detection.
        
        Args:
            binary_image: Binary image for contour detection
            original_image: Original image for visual analysis
            texts: Text elements for association
            
        Returns:
            List of shape-detected buttons
        """
        buttons = []
        
        # Find contours in binary image
        contours, _ = cv2.findContours(
            binary_image,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Get image dimensions for filtering
        height, width = original_image.shape[:2]
        min_button_area = (width * height) * 0.0005  # 0.05% of screen
        max_button_area = (width * height) * 0.1     # 10% of screen
        
        for contour in contours:
            try:
                button = self._analyze_contour_for_button(
                    contour, original_image, texts, min_button_area, max_button_area
                )
                if button:
                    buttons.append(button)
                    
            except Exception as e:
                self.logger.warning(f"Error analyzing contour for button: {e}")
                # Continue processing other contours
        
        return buttons
    
    def _analyze_contour_for_button(self, contour, original_image: np.ndarray,
                                   texts: List[DetectedText], min_area: float, 
                                   max_area: float) -> Optional[DetectedButton]:
        """
        Analyze a single contour to determine if it represents a button.
        
        Args:
            contour: OpenCV contour to analyze
            original_image: Original color image
            texts: Text elements for association
            min_area: Minimum button area threshold
            max_area: Maximum button area threshold
            
        Returns:
            DetectedButton if contour represents a button, None otherwise
        """
        # Calculate contour properties
        area = cv2.contourArea(contour)
        
        # Filter by area
        if area < min_area or area > max_area:
            return None
        
        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(contour)
        
        # Calculate aspect ratio
        aspect_ratio = w / h if h > 0 else 0
        
        # Skip very elongated shapes (likely not buttons)
        if aspect_ratio > 5 or aspect_ratio < 0.2:
            return None
        
        # Calculate contour approximation for shape analysis
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        
        # Get ROI for visual analysis
        roi = original_image[y:y + h, x:x + w]
        
        # Calculate button confidence
        height, width = original_image.shape[:2]
        button_confidence = self._calculate_button_confidence(
            contour, approx, roi, aspect_ratio, area, x, y, w, h, width, height, original_image
        )
        
        # Only create button if confidence is reasonable
        if button_confidence <= 0.4:
            return None
        
        # Check if the button contains text
        button_text = self._find_text_inside_button(x, y, w, h, texts)
        detection_method = DetectionMethod.SHAPE_WITH_TEXT if button_text else DetectionMethod.SHAPE
        
        # Increase confidence if it contains text
        final_confidence = min(button_confidence + (0.1 if button_text else 0.0), 1.0)
        
        try:
            return DetectedButton(
                x=x,
                y=y,
                width=w,
                height=h,
                area=float(area),
                aspect_ratio=float(aspect_ratio),
                confidence=float(final_confidence),
                detection_method=detection_method,
                text=button_text
            )
            
        except Exception as validation_error:
            self.logger.warning(f"Failed to create DetectedButton: {validation_error}")
            return None
    
    def _calculate_button_confidence(self, contour, approx, roi: np.ndarray,
                                   aspect_ratio: float, area: float,
                                   x: int, y: int, w: int, h: int,
                                   img_width: int, img_height: int,
                                   original_image: np.ndarray) -> float:
        """
        Calculate confidence score for a potential button based on multiple factors.
        
        Args:
            contour: Button contour
            approx: Approximated polygon
            roi: Button region of interest
            aspect_ratio: Width/height ratio
            area: Button area
            x, y, w, h: Button coordinates and dimensions
            img_width, img_height: Image dimensions
            original_image: Original color image
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        confidence = 0.0
        
        try:
            # Factor 1: Shape (rectangular buttons score higher)
            shape_score = self._calculate_shape_score(approx)
            confidence += shape_score * 0.3
            
            # Factor 2: Aspect ratio (buttons typically have reasonable ratios)
            aspect_score = self._calculate_aspect_score(aspect_ratio)
            confidence += aspect_score * 0.2
            
            # Factor 3: Color uniformity (buttons often have consistent color)
            color_score = self._calculate_color_uniformity_score(roi)
            confidence += color_score * 0.2
            
            # Factor 4: Position on screen (buttons often at specific locations)
            position_score = self._calculate_position_score(x, y, w, h, img_width, img_height)
            confidence += position_score * 0.15
            
            # Factor 5: Contrast with surroundings
            contrast_score = self._calculate_contrast_score(
                x, y, w, h, img_width, img_height, roi, original_image
            )
            confidence += contrast_score * 0.15
            
        except Exception as e:
            self.logger.warning(f"Error calculating button confidence: {e}")
            # Return partial confidence if some calculations fail
        
        return min(confidence, 1.0)
    
    def _calculate_shape_score(self, approx) -> float:
        """Calculate score based on button shape characteristics."""
        if len(approx) == 4:  # Rectangular shape
            return 1.0
        elif 4 < len(approx) < 8:  # Rounded rectangle
            return 0.8
        elif len(approx) >= 8:  # Near-circular
            return 0.6
        else:
            return 0.2
    
    def _calculate_aspect_score(self, aspect_ratio: float) -> float:
        """Calculate score based on aspect ratio (buttons typically 1:1 to 4:1)."""
        if 0.8 <= aspect_ratio <= 4.0:
            # Score decreases as we move away from ideal ratio of 2.0
            return 1.0 - (min(abs(aspect_ratio - 2.0), 1.0) / 1.2)
        else:
            return 0.0
    
    def _calculate_color_uniformity_score(self, roi: np.ndarray) -> float:
        """Calculate score based on color uniformity (buttons often have consistent color)."""
        try:
            if roi.size == 0:
                return 0.0
            
            hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            # Saturation uniformity indicates consistent color
            color_uniformity = 1.0 - (np.std(hsv_roi[:, :, 1]) / 128)
            return max(0.0, color_uniformity)
            
        except Exception:
            return 0.0
    
    def _calculate_position_score(self, x: int, y: int, w: int, h: int,
                                img_width: int, img_height: int) -> float:
        """Calculate score based on button position (common locations score higher)."""
        position_score = 0.0
        
        # Bottom of screen (common for navigation)
        if y + h > img_height * 0.8:
            position_score += 0.5
        
        # Right edge (common for action buttons)
        if x + w > img_width * 0.8:
            position_score += 0.3
        
        # Left edge (common for menu/back buttons)
        if x < img_width * 0.2:
            position_score += 0.3
        
        return min(position_score, 1.0)
    
    def _calculate_contrast_score(self, x: int, y: int, w: int, h: int,
                                img_width: int, img_height: int,
                                roi: np.ndarray, original_image: np.ndarray) -> float:
        """Calculate score based on contrast with surroundings."""
        try:
            # Create slightly larger ROI for background
            expand = 10
            bg_x = max(0, x - expand)
            bg_y = max(0, y - expand)
            bg_w = min(img_width - bg_x, w + 2 * expand)
            bg_h = min(img_height - bg_y, h + 2 * expand)
            
            if bg_w <= 0 or bg_h <= 0:
                return 0.0
            
            bg_roi = original_image[bg_y:bg_y + bg_h, bg_x:bg_x + bg_w]
            
            # Create mask to exclude the button itself
            mask = np.ones((bg_h, bg_w), dtype=np.uint8) * 255
            button_mask_x = x - bg_x
            button_mask_y = y - bg_y
            
            if (button_mask_y >= 0 and button_mask_x >= 0 and
                button_mask_y + h <= bg_h and button_mask_x + w <= bg_w):
                mask[button_mask_y:button_mask_y + h, button_mask_x:button_mask_x + w] = 0
            
            # Calculate color difference between button and surroundings
            hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            hsv_bg = cv2.cvtColor(bg_roi, cv2.COLOR_BGR2HSV)
            
            button_mean = cv2.mean(hsv_roi)
            bg_mean = cv2.mean(hsv_bg, mask)
            
            # Calculate color distance (simplified)
            color_distance = abs(button_mean[1] - bg_mean[1]) / 255.0
            return min(color_distance * 2.0, 1.0)
            
        except Exception:
            return 0.0
    
    def _detect_text_buttons(self, texts: List[DetectedText], 
                           existing_buttons: List[DetectedButton]) -> List[DetectedButton]:
        """
        Detect buttons based on text elements that look like button labels.
        
        Args:
            texts: List of detected text elements
            existing_buttons: Already detected buttons to avoid overlaps
            
        Returns:
            List of text-based detected buttons
        """
        text_buttons = []
        
        for text_element in texts:
            if not text_element.is_button_like:
                continue
            
            # Check if this text overlaps with existing buttons
            if self._text_overlaps_with_buttons(text_element, existing_buttons):
                continue
            
            # Create button around text with padding
            bbox = text_element.bbox
            x, y, w, h = bbox.x, bbox.y, bbox.width, bbox.height
            
            # Add padding around text for button area
            padding_x = int(w * 0.2)
            padding_y = int(h * 0.3)
            button_x = max(0, x - padding_x)
            button_y = max(0, y - padding_y)
            button_w = w + 2 * padding_x
            button_h = h + 2 * padding_y
            
            # Calculate confidence based on text characteristics
            confidence = 0.5
            if text_element.text.lower() in self.button_text_indicators:
                confidence = 0.8
            
            try:
                button = DetectedButton(
                    x=button_x,
                    y=button_y,
                    width=button_w,
                    height=button_h,
                    area=float(button_w * button_h),
                    aspect_ratio=float(button_w / button_h) if button_h > 0 else 1.0,
                    confidence=float(confidence),
                    detection_method=DetectionMethod.TEXT,
                    text=text_element.text
                )
                text_buttons.append(button)
                
            except Exception as validation_error:
                self.logger.warning(f"Failed to create text-based DetectedButton: {validation_error}")
                # Continue processing other text elements
        
        return text_buttons
    
    def _find_text_inside_button(self, x: int, y: int, w: int, h: int, 
                                texts: List[DetectedText]) -> Optional[str]:
        """
        Find text that appears inside a button bounding box.
        
        Args:
            x, y, w, h: Button coordinates and dimensions
            texts: List of detected text elements
            
        Returns:
            Button text if found, None otherwise
        """
        contained_texts = []
        
        for text_element in texts:
            bbox = text_element.bbox
            text_center_x = bbox.center_x
            text_center_y = bbox.center_y
            
            # Check if text center is inside button
            if x <= text_center_x <= x + w and y <= text_center_y <= y + h:
                contained_texts.append((text_element.text, text_element.confidence))
        
        if contained_texts:
            # Return the highest confidence text
            contained_texts.sort(key=lambda t: t[1], reverse=True)
            return contained_texts[0][0]
        
        return None
    
    def _text_overlaps_with_buttons(self, text_element: DetectedText,
                                  buttons: List[DetectedButton]) -> bool:
        """
        Check if text element overlaps with any existing button.
        
        Args:
            text_element: DetectedText element to check
            buttons: List of existing DetectedButton elements
            
        Returns:
            True if text overlaps with any button, False otherwise
        """
        bbox = text_element.bbox
        tx, ty, tw, th = bbox.x, bbox.y, bbox.width, bbox.height
        
        for button in buttons:
            bx, by, bw, bh = button.x, button.y, button.width, button.height
            
            try:
                overlap = self.geometry_utils.calculate_overlap_percentage(tx, ty, tw, th, bx, by, bw, bh)
                if overlap > 0.5:
                    return True
            except Exception as e:
                self.logger.warning(f"Error checking text-button overlap: {e}")
        
        return False
    
    def get_button_detection_summary(self, buttons: List[DetectedButton]) -> dict:
        """
        Get summary statistics about detected buttons.
        
        Args:
            buttons: List of detected buttons
            
        Returns:
            Dictionary with detection statistics
        """
        total_buttons = len(buttons)
        shape_buttons = sum(1 for b in buttons if b.detection_method in [DetectionMethod.SHAPE, DetectionMethod.SHAPE_WITH_TEXT])
        text_buttons = sum(1 for b in buttons if b.detection_method == DetectionMethod.TEXT)
        buttons_with_text = sum(1 for b in buttons if b.text)
        high_confidence = sum(1 for b in buttons if b.confidence >= 0.8)
        
        return {
            "total_buttons": total_buttons,
            "shape_based_buttons": shape_buttons,
            "text_based_buttons": text_buttons,
            "buttons_with_text": buttons_with_text,
            "high_confidence_buttons": high_confidence,
            "average_confidence": sum(b.confidence for b in buttons) / total_buttons if total_buttons > 0 else 0.0
        }


# Global instance for convenient access
_button_detector = None

def get_button_detector() -> ButtonDetector:
    """
    Get the global button detector instance.
    
    Returns:
        ButtonDetector instance
    """
    global _button_detector
    if _button_detector is None:
        _button_detector = ButtonDetector()
    return _button_detector