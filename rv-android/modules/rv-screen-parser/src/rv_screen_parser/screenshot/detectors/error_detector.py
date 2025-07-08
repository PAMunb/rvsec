#!/usr/bin/env python3
"""
Error detection component for screenshot analysis.

This module provides comprehensive error indicator detection capabilities using
color analysis, text pattern matching, and icon recognition to identify
error conditions, warnings, and validation messages in mobile applications.

### Architectural Role:
- Implements multi-strategy error detection (color-based, text-based, icon-based)
- Provides pattern-based detection for dialogs, toasts, and validation errors
- Handles confidence scoring based on multiple visual and textual factors
- Generates validated ErrorIndicator models with comprehensive metadata

### Design Decisions:
- Uses HSV color space analysis for error color detection (reds, yellows)
- Implements text pattern matching for error message classification
- Supports icon-based detection for common error/warning symbols
- Integrates geometric analysis for error dialog and toast detection
"""

import re
from typing import List, Optional, Tuple, Set
import cv2
import numpy as np

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVParsingError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager

from ..models import DetectedText, ErrorIndicator, ErrorType, BoundingBox, DetectionMethod
from ..utils.geometry_utils import get_geometry_utils


class ErrorDetector:
    """
    Multi-strategy error detection component for screenshot analysis.

    Combines color analysis, text pattern matching, and icon recognition
    to identify error indicators with confidence scoring.
    """

    def __init__(self):
        """Initialize error detector with configuration parameters."""
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "screenshot.error_detector",
            {CONTEXT_COMPONENT: "ErrorDetector"}
        )
        self.geometry_utils = get_geometry_utils()

        # Error color ranges in HSV color space
        self.error_color_ranges = {
            "red": [(0, 100, 100), (10, 255, 255), (160, 100, 100), (180, 255, 255)],
            "orange": [(11, 100, 100), (25, 255, 255)],
            "yellow": [(26, 100, 100), (35, 255, 255)]
        }

        # Error text patterns by category
        self.error_patterns = {
            "network": [
                r'\b(no.{0,5}(internet|connection|network))\b',
                r'\b(connection.{0,10}(failed|error|timeout))\b',
                r'\b(server.{0,10}(unavailable|error|timeout))\b',
                r'\b(offline|disconnected)\b'
            ],
            "permission": [
                r'\b(permission.{0,10}denied)\b',
                r'\b(access.{0,10}denied)\b',
                r'\b(unauthorized|forbidden)\b',
                r'\b(needs?.{0,5}permission)\b'
            ],
            "validation": [
                r'\b(invalid.{0,10}(format|input|data))\b',
                r'\b(required.{0,5}field)\b',
                r'\b(too.{0,5}(short|long))\b',
                r'\b(must.{0,10}contain)\b',
                r'\b(cannot.{0,5}be.{0,5}empty)\b'
            ],
            "system": [
                r'\b(application.{0,10}(crashed|stopped|error))\b',
                r'\b(system.{0,5}error)\b',
                r'\b(unexpected.{0,5}error)\b',
                r'\b(something.{0,5}went.{0,5}wrong)\b'
            ],
            "general": [
                r'\b(error|failed|failure)\b',
                r'\b(warning|alert)\b',
                r'\b(problem|issue)\b',
                r'\b(incorrect|wrong)\b'
            ]
        }

        # Icon patterns for error detection (Unicode symbols commonly used)
        self.error_icons = {
            "warning": ["⚠", "⚠️", "!"],
            "error": ["✕", "✗", "❌", "⛔", "🚫"],
            "info": ["ℹ", "ℹ️", "💡"],
            "critical": ["🔥", "💥", "⭕"]
        }

    @ErrorHandler.handle_errors(component="ErrorDetector", phase="error_detection", reraise=True)
    def detect_errors(self, original_image: np.ndarray,
                      texts: List[DetectedText]) -> List[ErrorIndicator]:
        """
        Detect error indicators using multiple detection strategies.

        Combines color-based detection, text pattern matching, and icon recognition
        to find error conditions with confidence scoring.

        Args:
            original_image: Original color image for visual analysis
            texts: List of detected text elements for error text detection

        Returns:
            List of validated ErrorIndicator models

        Raises:
            RVParsingError: If error detection fails
        """
        if original_image is None:
            raise RVParsingError(
                "Cannot detect errors with null image",
                parser_type="ErrorDetector"
            )

        errors = []

        # Strategy 1: Color-based error detection (with adaptive thresholds)
        color_errors = self._detect_color_errors(original_image, texts)
        errors.extend(color_errors)

        # Strategy 2: Text-based error detection
        text_errors = self._detect_text_errors(texts, errors)
        errors.extend(text_errors)

        # Strategy 3: Pattern-based error detection (dialogs, toasts)
        pattern_errors = self._detect_pattern_errors(original_image, texts, errors)
        errors.extend(pattern_errors)

        # Sort errors by confidence (higher first)
        errors.sort(key=lambda e: e.confidence, reverse=True)

        self.logger.info(
            f"Detected {len(errors)} error indicators ({len(color_errors)} color-based, {len(text_errors)} text-based, {len(pattern_errors)} pattern-based)")
        return errors

    def _detect_high_color_density_context(self, original_image: np.ndarray) -> dict:
        """
        Detect high color density contexts that may produce false positive error indicators.
        
        Analyzes visual patterns to determine if the screen contains many colored elements
        that might be legitimate UI components rather than error indicators (e.g., colorful
        interfaces, games, data visualizations, etc.).
        
        Args:
            original_image: Original color image
            
        Returns:
            Dictionary with high color density context information
        """
        context = {
            "high_color_density": False,
            "colored_elements_count": 0,
            "regular_pattern_detected": False,
            "confidence": 0.0
        }
        
        try:
            height, width = original_image.shape[:2]
            hsv_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2HSV)
            
            # Count colored elements with high saturation (game pieces)
            colored_elements = []
            
            # Find contours for analysis
            gray = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 200 or area > 50000:  # Broader range for game piece size
                    continue
                
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h if h > 0 else 1.0
                
                # Check if roughly square/circular (typical for game pieces)
                if 0.3 <= aspect_ratio <= 3.0:  # More flexible aspect ratio
                    # Analyze color saturation in this region
                    roi = hsv_image[y:y+h, x:x+w]
                    if roi.size > 0:
                        avg_saturation = np.mean(roi[:, :, 1])
                        if avg_saturation > 50:  # Lower saturation threshold
                            colored_elements.append({
                                'x': x, 'y': y, 'w': w, 'h': h,
                                'saturation': avg_saturation
                            })
            
            context["colored_elements_count"] = len(colored_elements)
            
            # Check for regular patterns (characteristic of structured interfaces)
            if len(colored_elements) >= 5:
                centers = [(elem['x'] + elem['w']//2, elem['y'] + elem['h']//2) 
                          for elem in colored_elements]
                
                # Analyze spacing patterns
                x_positions = sorted(set(c[0] for c in centers))
                y_positions = sorted(set(c[1] for c in centers))
                
                # Check for regular spacing
                if len(x_positions) >= 2 and len(y_positions) >= 2:
                    x_spacings = [x_positions[i+1] - x_positions[i] for i in range(len(x_positions)-1)]
                    y_spacings = [y_positions[i+1] - y_positions[i] for i in range(len(y_positions)-1)]
                    
                    # Calculate coefficient of variation for spacing regularity
                    if x_spacings and y_spacings:
                        x_cv = np.std(x_spacings) / np.mean(x_spacings) if np.mean(x_spacings) > 0 else 1
                        y_cv = np.std(y_spacings) / np.mean(y_spacings) if np.mean(y_spacings) > 0 else 1
                        
                        # Detect regular patterns
                        if (x_cv < 0.6 and y_cv < 0.6) or (len(centers) >= 10 and (x_cv < 0.8 or y_cv < 0.8)):
                            context["regular_pattern_detected"] = True
            
            # Determine if this interface has high color density that may cause false positives
            confidence = 0.0
            
            # Factor 1: Number of colored elements
            if context["colored_elements_count"] >= 15:
                confidence += 0.4
            elif context["colored_elements_count"] >= 8:
                confidence += 0.3
            
            # Factor 2: Regular pattern suggests structured interface
            if context["regular_pattern_detected"]:
                confidence += 0.4
            
            # Factor 3: High density of colored elements relative to screen size
            element_density = context["colored_elements_count"] / ((width * height) / 10000)
            if element_density > 0.8:
                confidence += 0.3
            elif element_density > 0.5:
                confidence += 0.2
            
            context["confidence"] = min(confidence, 1.0)
            # High color density context if there are many colored elements or regular patterns
            context["high_color_density"] = confidence >= 0.4
            
            
        except Exception as e:
            self.logger.warning(f"Error detecting high color density context: {e}")
        
        return context

    def _calculate_adaptive_confidence_threshold(self, original_image: np.ndarray, texts: List[DetectedText]) -> float:
        """
        Calculate adaptive confidence threshold based on image characteristics.
        
        Uses simple heuristics to detect colorful interfaces that may produce 
        false positive error indicators.
        
        Args:
            original_image: Original color image
            texts: List of detected text elements for context
            
        Returns:
            Confidence threshold to use for error detection
        """
        try:
            height, width = original_image.shape[:2]
            
            # Quick saturation analysis
            hsv_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2HSV)
            saturation_channel = hsv_image[:, :, 1]
            
            # Count highly saturated pixels (indicative of colorful content)
            high_saturation_pixels = np.sum(saturation_channel > 100)
            total_pixels = width * height
            saturation_ratio = high_saturation_pixels / total_pixels
            
            # Check for game-like text patterns
            game_keywords = ["player", "turn", "roll", "dice", "score", "level", "game"]
            game_text_detected = any(
                any(keyword in text.text.lower() for keyword in game_keywords)
                for text in texts
            )
            
            # Adaptive threshold logic
            base_threshold = 0.3
            
            # Very high saturation content suggests highly colorful interface (games, visualizations, color pickers)
            if saturation_ratio > 0.4:
                base_threshold = 0.9  # Extremely colorful interfaces (color pickers)
            elif saturation_ratio > 0.3:
                base_threshold = 0.8
            elif saturation_ratio > 0.25:
                base_threshold = 0.7
            
            # Game text is a strong indicator for games
            if game_text_detected:
                base_threshold = max(base_threshold, 0.8)
            
            return base_threshold
            
        except Exception as e:
            self.logger.warning(f"Error calculating adaptive threshold: {e}")
            return 0.3  # Default threshold

    def _detect_color_errors(self, original_image: np.ndarray, texts: List[DetectedText]) -> List[ErrorIndicator]:
        """
        Detect errors based on color analysis (red, orange, yellow regions).

        Uses adaptive confidence thresholds based on the detected screen content
        to reduce false positives in colorful interfaces.

        Args:
            original_image: Original color image
            texts: List of detected text elements for context

        Returns:
            List of color-detected error indicators
        """
        errors = []

        # Convert to HSV for better color detection
        hsv_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2HSV)
        height, width = original_image.shape[:2]
        min_error_area = (width * height) * 0.0001  # 0.01% of screen
        max_error_area = (width * height) * 0.2  # 20% of screen
        
        # Use adaptive confidence threshold based on overall image characteristics
        confidence_threshold = self._calculate_adaptive_confidence_threshold(original_image, texts)

        for color_name, ranges in self.error_color_ranges.items():
            try:
                # Create mask for color ranges
                mask = np.zeros(hsv_image.shape[:2], dtype=np.uint8)

                if color_name == "red":
                    # Red wraps around in HSV, so we need two ranges
                    mask1 = cv2.inRange(hsv_image, np.array(ranges[0]), np.array(ranges[1]))
                    mask2 = cv2.inRange(hsv_image, np.array(ranges[2]), np.array(ranges[3]))
                    mask = cv2.bitwise_or(mask1, mask2)
                else:
                    mask = cv2.inRange(hsv_image, np.array(ranges[0]), np.array(ranges[1]))

                # Find contours in color mask
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area < min_error_area or area > max_error_area:
                        continue

                    # Get bounding rectangle
                    x, y, w, h = cv2.boundingRect(contour)

                    # Calculate confidence based on color intensity and area
                    roi = hsv_image[y:y + h, x:x + w]
                    confidence = self._calculate_color_confidence(roi, color_name, area, width * height)

                    if confidence > confidence_threshold:  # Adjusted confidence threshold based on context
                        error_indicator = self._create_error_indicator(
                            x, y, w, h, confidence, ErrorType.VISUAL_INDICATOR,
                            f"{color_name.title()} color error indicator"
                        )
                        if error_indicator:
                            errors.append(error_indicator)

            except Exception as e:
                self.logger.warning(f"Error in color detection for {color_name}: {e}")

        return errors

    def _detect_text_errors(self, texts: List[DetectedText],
                            existing_errors: List[ErrorIndicator]) -> List[ErrorIndicator]:
        """
        Detect errors based on text pattern matching.

        Args:
            texts: List of detected text elements
            existing_errors: Already detected errors to avoid duplicates

        Returns:
            List of text-based error indicators
        """
        text_errors = []

        for text_element in texts:
            if not text_element.is_error_like:
                continue

            # Check if this text overlaps with existing errors
            if self._text_overlaps_with_errors(text_element, existing_errors):
                continue

            # Classify error type based on text patterns
            error_type, confidence = self._classify_error_text(text_element.text)

            if confidence > 0.4:  # Minimum confidence for text errors
                bbox = text_element.bbox
                error_indicator = self._create_error_indicator(
                    bbox.x, bbox.y, bbox.width, bbox.height,
                    confidence, error_type, text_element.text
                )
                if error_indicator:
                    text_errors.append(error_indicator)

        return text_errors

    def _detect_pattern_errors(self, original_image: np.ndarray, texts: List[DetectedText],
                               existing_errors: List[ErrorIndicator]) -> List[ErrorIndicator]:
        """
        Detect errors based on UI patterns (dialogs, toasts, banners).

        Args:
            original_image: Original color image
            texts: List of detected text elements
            existing_errors: Already detected errors

        Returns:
            List of pattern-based error indicators
        """
        pattern_errors = []

        # Detect error dialogs
        dialog_errors = self._detect_error_dialogs(original_image, texts, existing_errors)
        pattern_errors.extend(dialog_errors)

        # Detect toast notifications
        toast_errors = self._detect_toast_errors(original_image, texts, existing_errors)
        pattern_errors.extend(toast_errors)

        # Detect banner/snackbar errors
        banner_errors = self._detect_banner_errors(original_image, texts, existing_errors)
        pattern_errors.extend(banner_errors)

        return pattern_errors

    def _detect_error_dialogs(self, original_image: np.ndarray, texts: List[DetectedText],
                              existing_errors: List[ErrorIndicator]) -> List[ErrorIndicator]:
        """Detect error dialogs based on geometric patterns and text clustering."""
        dialogs = []
        height, width = original_image.shape[:2]

        # Look for centered rectangular regions with error text
        error_texts = [t for t in texts if t.is_error_like]

        if not error_texts:
            return dialogs

        # Group nearby error texts that might form a dialog
        text_groups = self._group_nearby_texts(error_texts, max_distance=100)

        for group in text_groups:
            if len(group) < 2:  # Dialog should have multiple text elements
                continue

            # Calculate bounding box for the group
            min_x = min(t.bbox.x for t in group)
            min_y = min(t.bbox.y for t in group)
            max_x = max(t.bbox.x + t.bbox.width for t in group)
            max_y = max(t.bbox.y + t.bbox.height for t in group)

            dialog_w = max_x - min_x
            dialog_h = max_y - min_y

            # Check if it's dialog-sized and positioned
            if (width * 0.3 <= dialog_w <= width * 0.9 and
                    height * 0.2 <= dialog_h <= height * 0.7):

                # Check if it's roughly centered
                center_x = min_x + dialog_w / 2
                center_y = min_y + dialog_h / 2

                if (abs(center_x - width / 2) < width * 0.2 and
                        abs(center_y - height / 2) < height * 0.3):

                    # Calculate confidence based on text content and positioning
                    confidence = 0.6 + (len(group) * 0.1)  # More text = higher confidence
                    confidence = min(confidence, 0.9)

                    error_text = " ".join(t.text for t in group[:3])  # First 3 texts
                    dialog = self._create_error_indicator(
                        min_x, min_y, dialog_w, dialog_h,
                        confidence, ErrorType.DIALOG, error_text
                    )
                    if dialog:
                        dialogs.append(dialog)

        return dialogs

    def _detect_toast_errors(self, original_image: np.ndarray, texts: List[DetectedText],
                             existing_errors: List[ErrorIndicator]) -> List[ErrorIndicator]:
        """Detect toast notification errors at top/bottom of screen."""
        toasts = []
        height, width = original_image.shape[:2]

        error_texts = [t for t in texts if t.is_error_like]

        for text_element in error_texts:
            bbox = text_element.bbox

            # Check if text is positioned like a toast (top or bottom edge)
            is_top_toast = bbox.y < height * 0.15
            is_bottom_toast = bbox.y > height * 0.85

            if is_top_toast or is_bottom_toast:
                # Check if text spans reasonable width for a toast
                if bbox.width > width * 0.3:
                    confidence = 0.7 if is_top_toast else 0.6  # Top toasts more common

                    toast = self._create_error_indicator(
                        bbox.x, bbox.y, bbox.width, bbox.height,
                        confidence, ErrorType.TOAST, text_element.text
                    )
                    if toast:
                        toasts.append(toast)

        return toasts

    def _detect_banner_errors(self, original_image: np.ndarray, texts: List[DetectedText],
                              existing_errors: List[ErrorIndicator]) -> List[ErrorIndicator]:
        """Detect banner/snackbar errors (horizontal strips)."""
        banners = []
        height, width = original_image.shape[:2]

        error_texts = [t for t in texts if t.is_error_like]

        for text_element in error_texts:
            bbox = text_element.bbox
            aspect_ratio = bbox.width / bbox.height if bbox.height > 0 else 0

            # Look for wide, short text regions (banner-like)
            if (aspect_ratio > 3 and bbox.width > width * 0.5 and
                    bbox.height < height * 0.1):

                confidence = 0.5 + min(aspect_ratio / 10, 0.3)  # Higher aspect ratio = more banner-like

                banner = self._create_error_indicator(
                    bbox.x, bbox.y, bbox.width, bbox.height,
                    confidence, ErrorType.BANNER, text_element.text
                )
                if banner:
                    banners.append(banner)

        return banners

    def _calculate_color_confidence(self, roi: np.ndarray, color_name: str,
                                    area: float, total_area: float) -> float:
        """Calculate confidence score for color-based error detection."""
        try:
            if roi.size == 0:
                return 0.0

            confidence = 0.0

            # Factor 1: Color intensity (how "red" or "yellow" is it)
            if color_name == "red":
                # Look for high saturation and value in red range
                red_pixels = np.sum((roi[:, :, 1] > 150) & (roi[:, :, 2] > 150))
                intensity_score = red_pixels / roi.size if roi.size > 0 else 0
                confidence += intensity_score * 0.4
            elif color_name in ["orange", "yellow"]:
                # Look for high saturation
                saturated_pixels = np.sum(roi[:, :, 1] > 100)
                intensity_score = saturated_pixels / roi.size if roi.size > 0 else 0
                confidence += intensity_score * 0.3

            # Factor 2: Area relative to screen (not too big, not too small)
            area_ratio = area / total_area
            if 0.001 <= area_ratio <= 0.05:  # 0.1% to 5% of screen
                confidence += 0.3
            elif 0.0001 <= area_ratio <= 0.1:  # Broader range with lower score
                confidence += 0.2

            # Factor 3: Shape characteristics (error indicators often rectangular)
            confidence += 0.3  # Base shape score

            return min(confidence, 1.0)

        except Exception:
            return 0.0

    def _classify_error_text(self, text: str) -> Tuple[ErrorType, float]:
        """Classify error text and return error type with confidence."""
        text_lower = text.lower().strip()
        max_confidence = 0.0
        detected_type = ErrorType.GENERAL

        # Check against error patterns
        for error_category, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    confidence = 0.8 if error_category != "general" else 0.6
                    if confidence > max_confidence:
                        max_confidence = confidence
                        detected_type = ErrorType(error_category.upper())

        # Check for error icons in text
        for icon_category, icons in self.error_icons.items():
            if any(icon in text for icon in icons):
                icon_confidence = 0.9 if icon_category in ["error", "warning"] else 0.7
                if icon_confidence > max_confidence:
                    max_confidence = icon_confidence
                    detected_type = ErrorType.VISUAL_INDICATOR

        return detected_type, max_confidence

    def _group_nearby_texts(self, texts: List[DetectedText], max_distance: int = 100) -> List[List[DetectedText]]:
        """Group text elements that are close to each other."""
        if not texts:
            return []

        groups = []
        processed = set()

        for i, text in enumerate(texts):
            if i in processed:
                continue

            group = [text]
            processed.add(i)

            for j, other_text in enumerate(texts):
                if j in processed or i == j:
                    continue

                # Calculate distance between text centers
                center1_x = text.bbox.center_x
                center1_y = text.bbox.center_y
                center2_x = other_text.bbox.center_x
                center2_y = other_text.bbox.center_y

                distance = ((center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2) ** 0.5

                if distance <= max_distance:
                    group.append(other_text)
                    processed.add(j)

            if len(group) >= 1:  # Include single-text groups
                groups.append(group)

        return groups

    def _create_error_indicator(self, x: int, y: int, w: int, h: int,
                                confidence: float, error_type: ErrorType,
                                message: str) -> Optional[ErrorIndicator]:
        """Create a validated ErrorIndicator model."""
        try:
            return ErrorIndicator(
                x=x,
                y=y,
                width=w,
                height=h,
                detection_method=DetectionMethod.COLOR,  # Default to color detection
                confidence=float(confidence),
                error_type=error_type,
                text=message,
                area=float(w * h)
            )
        except Exception as validation_error:
            self.logger.warning(f"Failed to create ErrorIndicator: {validation_error}")
            return None

    def _text_overlaps_with_errors(self, text_element: DetectedText,
                                   errors: List[ErrorIndicator]) -> bool:
        """Check if text element overlaps with any existing error."""
        bbox = text_element.bbox
        tx, ty, tw, th = bbox.x, bbox.y, bbox.width, bbox.height

        for error in errors:
            ex, ey, ew, eh = error.bbox.x, error.bbox.y, error.bbox.width, error.bbox.height

            try:
                overlap = self.geometry_utils.calculate_overlap_percentage(tx, ty, tw, th, ex, ey, ew, eh)
                if overlap > 0.5:
                    return True
            except Exception as e:
                self.logger.warning(f"Error checking text-error overlap: {e}")

        return False

    def get_error_detection_summary(self, errors: List[ErrorIndicator]) -> dict:
        """
        Get summary statistics about detected errors.

        Args:
            errors: List of detected error indicators

        Returns:
            Dictionary with detection statistics
        """
        total_errors = len(errors)
        critical_errors = sum(1 for e in errors if e.error_type in [ErrorType.CRITICAL_ERROR, ErrorType.SYSTEM_ERROR])

        # Count by error type
        type_counts = {}
        for error in errors:
            error_type = error.error_type.value
            type_counts[error_type] = type_counts.get(error_type, 0) + 1

        high_confidence = sum(1 for e in errors if e.confidence >= 0.8)

        return {
            "total_errors": total_errors,
            "critical_errors": critical_errors,
            "high_confidence_errors": high_confidence,
            "error_types": type_counts,
            "average_confidence": sum(e.confidence for e in errors) / total_errors if total_errors > 0 else 0.0
        }


# Global instance for convenient access
_error_detector = None


def get_error_detector() -> ErrorDetector:
    """
    Get the global error detector instance.

    Returns:
        ErrorDetector instance
    """
    global _error_detector
    if _error_detector is None:
        _error_detector = ErrorDetector()
    return _error_detector