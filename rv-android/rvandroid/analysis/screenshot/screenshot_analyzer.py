#!/usr/bin/env python3
"""
Advanced Android Screenshot Analyzer

Efficiently extracts information from Android screenshots with
optimized text, button, and error detection. Follows the BaseAnalyzer pattern
for consistent integration with the analysis architecture.

This analyzer is particularly effective for:
- Detecting UI elements in games and custom-rendered interfaces
- Identifying error messages and indicators in various forms
- Providing actionable insights for test automation systems

Dependencies (Ubuntu):
sudo apt-get update
sudo apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    python3-pip \
    libopencv-dev \
    python3-opencv
pip3 install \
    pytesseract \
    opencv-python \
    Pillow \
    numpy
"""

import cv2
import numpy as np
import pytesseract
import json
import time
import sys
import os
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple, Set

from PIL import Image

from rvandroid.analysis.base_analyzer import BaseAnalyzer
from rvandroid.domain.static import StaticAnalysisData


@dataclass
class ScreenshotAnalysisResult:
    """Data class for screenshot analysis results."""
    image_path: str
    dimensions: Dict[str, int] = field(default_factory=dict)
    texts: List[Dict[str, Any]] = field(default_factory=list)
    buttons: List[Dict[str, Any]] = field(default_factory=list)
    error_indicators: List[Dict[str, Any]] = field(default_factory=list)
    interactive_elements: List[Dict[str, Any]] = field(default_factory=list)
    processing_time: float = 0.0
    success: bool = True
    error_message: str = ""

    def to_json(self) -> str:
        """Convert the result to a JSON string."""
        result_dict = {
            'image_path': self.image_path,
            'dimensions': self.dimensions,
            'texts': self.texts,
            'buttons': self.buttons,
            'error_indicators': self.error_indicators,
            'interactive_elements': self.interactive_elements,
            'processing_time': self.processing_time,
            'success': self.success
        }
        return json.dumps(result_dict)


class ScreenshotAnalyzer(BaseAnalyzer[ScreenshotAnalysisResult]):
    """
    Advanced analyzer for extracting information from Android screenshots.

    This analyzer provides comprehensive detection of UI elements, text, and error conditions
    in Android screenshots, with particular focus on:
    1. Detecting game UI elements not present in the UI hierarchy
    2. Identifying various types of error conditions visually
    3. Extracting actionable information for test automation

    ### Architectural Role:
    - Provides visual analysis capabilities that complement UI hierarchy inspection
    - Integrates with the analysis pipeline for result management and action planning
    - Enables testing of applications with custom rendering (games, canvas-based UIs)
    - Detects error conditions that might not be visible in the UI hierarchy

    ### Design Decisions:
    - Employs multiple specialized detection techniques for different element types
    - Uses confidence scoring to prioritize detection results
    - Modular detector system for maintainability and extensibility
    - Advanced OCR configuration for improved text extraction
    """

    def __init__(self, image_path: Optional[str] = None, analyzer_name: str = "screenshot",
                 static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the screenshot analyzer.

        Args:
            image_path: Optional path to a screenshot image
            analyzer_name: Name identifier for the analyzer
            static_data: Optional static analysis data for context
        """
        super().__init__(analyzer_name, static_data)
        self.metrics = {
            "processed_images": 0,
            "total_processing_time": 0.0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "detected_texts": 0,
            "detected_buttons": 0,
            "detected_errors": 0,
            "detected_interactive_elements": 0
        }

        # Store image path for later use
        self.current_image_path = image_path
        self.current_result = None

        # Error keyword categories for improved classification
        self.error_keywords = {
            "general": [
                "error", "failed", "exception", "invalid", "not found",
                "problem", "warning", "alert", "incorrect", "denied",
                "unable to", "cannot", "retry", "wrong"
            ],
            "network": [
                "connection", "network", "offline", "server", "timeout",
                "unavailable", "no internet", "disconnected"
            ],
            "permission": [
                "permission", "access", "denied", "unauthorized", "requires",
                "needs access", "grant permission"
            ],
            "validation": [
                "required", "invalid format", "too short", "too long",
                "must contain", "cannot contain", "invalid character"
            ],
            "system": [
                "crashed", "stopped", "not responding", "relaunch",
                "restart", "system error"
            ]
        }

        # Button text indicators (common button labels)
        self.button_text_indicators = [
            "ok", "cancel", "yes", "no", "submit", "login", "sign in", "register",
            "next", "previous", "continue", "back", "done", "save", "delete",
            "add", "remove", "close", "send", "search", "buy", "purchase",
            "confirm", "accept", "decline", "agree", "disagree", "play", "start",
            "settings", "menu", "options", "help", "skip", "retry", "reload"
        ]

        # Initialize OCR configuration
        self.ocr_configs = [
            # High precision mode with full character set
            r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,:;!?() -c preserve_interword_spaces=1',
            # Page segmentation mode for single uniform block of text
            r'--oem 3 --psm 11'
        ]

        # If image path was provided, pre-analyze it
        if image_path:
            try:
                self.logger.debug(f"Pre-analyzing image: {image_path}")
                self.current_result = self.analyze(image_path)
            except Exception as e:
                self.logger.warning(f"Pre-analysis failed: {e}")
                self.current_result = None

    def _initialize_from_static_data(self) -> None:
        """
        Initialize with static analysis data.

        This analyzer can use static data to enhance detection, particularly
        by understanding the application's expected window structure and
        common UI patterns.
        """
        if self.static_data and hasattr(self.static_data, 'windows'):
            self.logger.info(f"Initialized with static data containing {len(self.static_data.windows.windows)} windows")

    def analyze(self, image_path: str) -> ScreenshotAnalysisResult:
        """
        Analyze a screenshot and extract information.

        This is the main entry point for screenshot analysis, coordinating
        the various detection components and assembling the final result.

        Args:
            image_path: Path to the screenshot image

        Returns:
            ScreenshotAnalysisResult containing extracted information
        """
        start_time = time.time()
        self.logger.info(f"Analyzing screenshot: {image_path}")

        # Initialize result
        result = ScreenshotAnalysisResult(image_path=image_path)

        try:
            # Load and preprocess image
            original_image = cv2.imread(image_path)

            # Validate image loading
            if original_image is None:
                raise ValueError(f"Could not read image from path: {image_path}")

            # Store image dimensions
            result.dimensions = {
                'width': original_image.shape[1],
                'height': original_image.shape[0]
            }

            # Create preprocessed images for different analyses
            gray_image = self._preprocess_grayscale(original_image)
            binary_image = self._preprocess_binary(original_image)

            # Extract text
            result.texts = self._extract_text(gray_image)
            self.metrics["detected_texts"] += len(result.texts)

            # Detect buttons and interactive elements
            result.buttons = self._detect_buttons(binary_image, original_image, result.texts)
            self.metrics["detected_buttons"] += len(result.buttons)

            # Detect game UI and other interactive elements
            result.interactive_elements = self._detect_interactive_elements(original_image, binary_image)
            self.metrics["detected_interactive_elements"] += len(result.interactive_elements)

            # Detect error indicators
            result.error_indicators = self._detect_error_indicators(original_image, result.texts)
            self.metrics["detected_errors"] += len(result.error_indicators)

            # Update metrics
            self.metrics["processed_images"] += 1
            self.metrics["successful_analyses"] += 1

        except Exception as e:
            self.logger.error(f"Error analyzing screenshot: {str(e)}")
            result.success = False
            result.error_message = str(e)
            self.metrics["failed_analyses"] += 1

        # Calculate processing time
        processing_time = time.time() - start_time
        result.processing_time = processing_time
        self.metrics["total_processing_time"] += processing_time

        self.log_processing_summary("screenshot", 1)
        return result

    def _preprocess_grayscale(self, image) -> np.ndarray:
        """
        Convert image to grayscale with enhanced contrast.

        Args:
            image: Original color image

        Returns:
            Enhanced grayscale image for text detection and analysis
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply histogram equalization to improve contrast
        equalized = cv2.equalizeHist(gray)

        # Apply light Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(equalized, (3, 3), 0)

        return blurred

    def _preprocess_binary(self, image) -> np.ndarray:
        """
        Create a binary image optimized for shape detection.

        Uses adaptive thresholding to better handle varied lighting conditions
        and contrast across the image.

        Args:
            image: Original color image

        Returns:
            Binary image for contour and shape detection
        """
        # Convert to grayscale first
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(
            blurred,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,  # Invert for easier contour finding
            11,  # Block size
            2  # Constant subtracted from mean
        )

        # Apply morphological operations to clean up the binary image
        kernel = np.ones((3, 3), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        return cleaned

    def _extract_text(self, gray_image) -> List[Dict[str, Any]]:
        """
        Extract text using multiple OCR techniques.

        Uses different Tesseract configurations to optimize text detection
        in various scenarios, then combines and filters the results.

        Args:
            gray_image: Preprocessed grayscale image

        Returns:
            List of dictionaries with text and its coordinates
        """
        detected_texts = []
        seen_texts = set()  # To track duplicate text in similar positions

        # Try multiple OCR configurations for better coverage
        for config in self.ocr_configs:
            try:
                text_data = pytesseract.image_to_data(
                    gray_image,
                    output_type=pytesseract.Output.DICT,
                    config=config
                )

                # Process and filter text results
                for i in range(len(text_data['text'])):
                    text = text_data['text'][i].strip()
                    confidence = int(text_data['conf'][i])

                    # Skip empty or very low confidence text
                    if len(text) <= 1 or confidence < 30:
                        continue

                    # Get position information
                    x = int(text_data['left'][i])
                    y = int(text_data['top'][i])
                    w = int(text_data['width'][i])
                    h = int(text_data['height'][i])

                    # Create a key to detect similar text in similar positions
                    position_key = f"{text}_{x // 10}_{y // 10}"

                    # Skip if we've already seen similar text in similar position
                    if position_key in seen_texts:
                        continue

                    seen_texts.add(position_key)

                    # Create text item with additional metadata
                    text_item = {
                        'text': text,
                        'confidence': confidence,
                        'bbox': {
                            'x': x,
                            'y': y,
                            'width': w,
                            'height': h
                        },
                        'is_button_like': self._is_button_text(text),
                        'is_error_like': self._is_error_text(text)
                    }

                    detected_texts.append(text_item)

            except Exception as e:
                self.logger.warning(f"OCR configuration failed: {str(e)}")

        # Sort texts by confidence (higher first)
        detected_texts.sort(key=lambda t: t['confidence'], reverse=True)

        # Remove duplicates with lower confidence
        filtered_texts = []
        seen_positions = set()

        for text in detected_texts:
            # Create a position signature
            x = text['bbox']['x']
            y = text['bbox']['y']
            w = text['bbox']['width']
            h = text['bbox']['height']

            # Check if this text significantly overlaps with already detected text
            overlap_found = False
            for pos in seen_positions:
                px, py, pw, ph = pos
                # Check for significant overlap
                if self._calculate_overlap_percentage(x, y, w, h, px, py, pw, ph) > 0.5:
                    overlap_found = True
                    break

            if not overlap_found:
                filtered_texts.append(text)
                seen_positions.add((x, y, w, h))

        return filtered_texts

    def _is_button_text(self, text: str) -> bool:
        """
        Check if text likely represents a button label.

        Args:
            text: The text to check

        Returns:
            True if text is likely a button label, False otherwise
        """
        text_lower = text.lower()

        # Check against known button labels
        if any(label == text_lower or label in text_lower for label in self.button_text_indicators):
            return True

        # Short text (likely a button)
        if len(text) <= 15 and text.isprintable() and not text.isspace():
            return True

        return False

    def _is_error_text(self, text: str) -> bool:
        """
        Check if text likely indicates an error message.

        Args:
            text: The text to check

        Returns:
            True if text is likely an error message, False otherwise
        """
        text_lower = text.lower()

        # Check against all error keywords categories
        for category, keywords in self.error_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return True

        return False

    def _detect_buttons(self, binary_image, original_image, texts) -> List[Dict[str, Any]]:
        """
        Detect button-like objects in the image.

        This method combines multiple detection strategies:
        1. Shape detection for standard button elements
        2. Text-based detection for text that looks like button labels
        3. Game UI detection for less conventional button designs

        Args:
            binary_image: Preprocessed binary image
            original_image: Original color image
            texts: Detected text elements

        Returns:
            List of button characteristics
        """
        buttons = []

        # 1. Find contours in binary image
        contours, _ = cv2.findContours(
            binary_image,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        # Get image dimensions for filtering
        height, width = original_image.shape[:2]
        min_button_area = (width * height) * 0.0005  # Minimum button size as percentage of screen
        max_button_area = (width * height) * 0.1  # Maximum button size as percentage of screen

        # Process each contour
        for contour in contours:
            # Calculate contour properties
            area = cv2.contourArea(contour)

            # Filter by area
            if area < min_button_area or area > max_button_area:
                continue

            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)

            # Calculate aspect ratio
            aspect_ratio = w / h if h > 0 else 0

            # Skip very elongated shapes (likely not buttons)
            if aspect_ratio > 5 or aspect_ratio < 0.2:
                continue

            # Calculate contour approximation for shape analysis
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)

            # Get ROI for texture and color analysis
            roi = original_image[y:y + h, x:x + w]

            # Calculate button confidence based on multiple factors
            button_confidence = self._calculate_button_confidence(
                contour, approx, roi, aspect_ratio, area, x, y, w, h, width, height, original_image
            )

            # Only add if confidence is reasonable
            if button_confidence > 0.4:
                button = {
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'area': float(area),
                    'aspect_ratio': float(aspect_ratio),
                    'confidence': float(button_confidence),
                    'detection_method': 'shape'
                }

                # Check if the button contains text
                button_text = self._find_text_inside_button(x, y, w, h, texts)
                if button_text:
                    button['text'] = button_text
                    button['confidence'] += 0.1  # Increase confidence if it contains text
                    button['detection_method'] = 'shape_with_text'

                buttons.append(button)

        # 2. Add buttons based on text appearance
        for text in texts:
            if text['is_button_like'] and not self._overlaps_with_buttons(text, buttons):
                bbox = text['bbox']
                x, y, w, h = bbox['x'], bbox['y'], bbox['width'], bbox['height']

                # Add padding around text for button area
                padding_x = int(w * 0.2)
                padding_y = int(h * 0.3)
                button_x = max(0, x - padding_x)
                button_y = max(0, y - padding_y)
                button_w = w + 2 * padding_x
                button_h = h + 2 * padding_y

                # Calculate confidence based on text characteristics
                confidence = 0.5
                if text['text'].lower() in self.button_text_indicators:
                    confidence = 0.8

                buttons.append({
                    'x': button_x,
                    'y': button_y,
                    'width': button_w,
                    'height': button_h,
                    'text': text['text'],
                    'confidence': float(confidence),
                    'detection_method': 'text',
                    'area': float(button_w * button_h),
                    'aspect_ratio': float(button_w / button_h) if button_h > 0 else 0
                })

        # Sort buttons by confidence (higher first)
        buttons.sort(key=lambda b: b['confidence'], reverse=True)

        return buttons

    def _calculate_button_confidence(
            self, contour, approx, roi, aspect_ratio, area,
            x, y, w, h, img_width, img_height, original_image) -> float:
        """
        Calculate confidence score for a potential button.

        This method combines multiple factors to determine how likely
        a detected shape is to be a button in a game or custom UI.

        Args:
            contour: Contour of the potential button
            approx: Approximated polygon of the contour
            roi: Region of interest (button image)
            aspect_ratio: Width/height ratio
            area: Area of the contour
            x, y, w, h: Button coordinates and dimensions
            img_width, img_height: Screenshot dimensions
            original_image: Original color image

        Returns:
            Confidence score (0.0 to 1.0)
        """
        confidence = 0.0

        # Factor 1: Shape (rectangular buttons score higher)
        rect_similarity = 0.0
        if len(approx) == 4:  # Rectangular shape
            rect_similarity = 1.0
        elif 4 < len(approx) < 8:  # Rounded rectangle
            rect_similarity = 0.8
        elif len(approx) >= 8:  # Near-circular
            rect_similarity = 0.6

        confidence += rect_similarity * 0.3

        # Factor 2: Aspect ratio (buttons typically have ratios between 1:1 and 4:1)
        aspect_score = 0.0
        if 0.8 <= aspect_ratio <= 4.0:
            aspect_score = 1.0 - (min(abs(aspect_ratio - 2.0), 1.0) / 1.2)

        confidence += aspect_score * 0.2

        # Factor 3: Uniform color or gradient (buttons often have consistent color)
        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        color_uniformity = 1.0 - (np.std(hsv_roi[:, :, 1]) / 128)  # Saturation uniformity

        confidence += color_uniformity * 0.2

        # Factor 4: Position on screen (buttons often at edges or corners)
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

        confidence += position_score * 0.15

        # Factor 5: Contrast with surroundings (buttons often stand out)
        try:
            # Create slightly larger ROI for background
            expand = 10
            bg_x = max(0, x - expand)
            bg_y = max(0, y - expand)
            bg_w = min(img_width - bg_x, w + 2 * expand)
            bg_h = min(img_height - bg_y, h + 2 * expand)

            if bg_w > 0 and bg_h > 0:
                bg_roi = original_image[bg_y:bg_y + bg_h, bg_x:bg_x + bg_w]

                # Create mask to exclude the button itself
                mask = np.ones((bg_h, bg_w), dtype=np.uint8) * 255
                button_mask_x = x - bg_x
                button_mask_y = y - bg_y
                mask[button_mask_y:button_mask_y + h, button_mask_x:button_mask_x + w] = 0

                # Calculate color difference between button and surroundings
                button_hsv = cv2.mean(hsv_roi)
                bg_hsv = cv2.mean(cv2.cvtColor(bg_roi, cv2.COLOR_BGR2HSV), mask)

                # Calculate color distance (simplified)
                color_distance = abs(button_hsv[1] - bg_hsv[1]) / 255.0
                contrast_score = min(color_distance * 2.0, 1.0)

                confidence += contrast_score * 0.15
        except Exception as e:
            self.logger.debug(f"Error calculating button contrast: {e}")

        return min(confidence, 1.0)

    def _find_text_inside_button(self, x, y, w, h, texts) -> Optional[str]:
        """
        Find text that appears inside a button bounding box.

        Args:
            x, y, w, h: Button coordinates and dimensions
            texts: List of detected text elements

        Returns:
            Button text if found, None otherwise
        """
        contained_texts = []

        for text in texts:
            bbox = text['bbox']
            tx = bbox['x']
            ty = bbox['y']
            tw = bbox['width']
            th = bbox['height']

            # Check if text center is inside button
            text_center_x = tx + tw // 2
            text_center_y = ty + th // 2

            if (x <= text_center_x <= x + w and y <= text_center_y <= y + h):
                # Text is inside button
                contained_texts.append((text['text'], text['confidence']))

        if contained_texts:
            # Return the highest confidence text
            contained_texts.sort(key=lambda t: t[1], reverse=True)
            return contained_texts[0][0]

        return None

    def _overlaps_with_buttons(self, text, buttons) -> bool:
        """
        Check if text overlaps with any existing button.

        Args:
            text: Text element to check
            buttons: List of detected buttons

        Returns:
            True if text overlaps with any button, False otherwise
        """
        bbox = text['bbox']
        tx = bbox['x']
        ty = bbox['y']
        tw = bbox['width']
        th = bbox['height']

        for button in buttons:
            bx = button['x']
            by = button['y']
            bw = button['width']
            bh = button['height']

            # Calculate overlap
            overlap = self._calculate_overlap_percentage(tx, ty, tw, th, bx, by, bw, bh)

            if overlap > 0.5:
                return True

        return False

    def _calculate_overlap_percentage(self, x1, y1, w1, h1, x2, y2, w2, h2) -> float:
        """
        Calculate the percentage of overlap between two rectangles.

        Args:
            x1, y1, w1, h1: First rectangle
            x2, y2, w2, h2: Second rectangle

        Returns:
            Overlap percentage (0.0 to 1.0) relative to the smaller rectangle
        """
        # Calculate intersection coordinates
        x_intersection = max(x1, x2)
        y_intersection = max(y1, y2)
        w_intersection = min(x1 + w1, x2 + w2) - x_intersection
        h_intersection = min(y1 + h1, y2 + h2) - y_intersection

        if w_intersection <= 0 or h_intersection <= 0:
            return 0.0

        intersection_area = w_intersection * h_intersection
        area1 = w1 * h1
        area2 = w2 * h2
        smaller_area = min(area1, area2)

        return intersection_area / smaller_area if smaller_area > 0 else 0.0

    def _detect_interactive_elements(self, original_image, binary_image) -> List[Dict[str, Any]]:
        """
        Detect interactive elements beyond standard buttons.

        This method specifically targets game UI elements like:
        - Joysticks and control pads
        - Sliders and progress bars
        - Custom toggles and switches
        - Menu icons and action buttons

        Args:
            original_image: Original color image
            binary_image: Preprocessed binary image

        Returns:
            List of detected interactive elements
        """
        interactive_elements = []
        height, width = original_image.shape[:2]

        # 1. Detect circular controls (joysticks, radial menus)
        contours, _ = cv2.findContours(
            binary_image,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        for contour in contours:
            area = cv2.contourArea(contour)

            # Skip very small or large areas
            min_area = width * height * 0.001
            max_area = width * height * 0.1
            if area < min_area or area > max_area:
                continue

            # Calculate circularity
            perimeter = cv2.arcLength(contour, True)
            circularity = 0
            if perimeter > 0:
                circularity = 4 * np.pi * area / (perimeter * perimeter)

            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h if h > 0 else 0

            # Detect joystick-like elements (circular with high circularity)
            if 0.7 < circularity < 1.3 and 0.8 < aspect_ratio < 1.2:
                confidence = min(0.8, circularity * 0.7)

                # Check position (virtual joysticks often at bottom corners)
                if (x < width * 0.3 and y > height * 0.6) or (x > width * 0.7 and y > height * 0.6):
                    confidence += 0.1

                interactive_elements.append({
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'type': 'joystick',
                    'confidence': float(confidence),
                    'detection_method': 'shape',
                    'circularity': float(circularity)
                })

        # 2. Detect slider-like elements (horizontal/vertical bars)
        for contour in contours:
            area = cv2.contourArea(contour)

            # Skip very small or large areas
            min_area = width * height * 0.0005
            max_area = width * height * 0.05
            if area < min_area or area > max_area:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h if h > 0 else 0

            # Horizontal sliders (width much greater than height)
            if aspect_ratio > 4.0 and h >= 10:
                # Check if it has consistent color/texture (typical for sliders)
                roi = original_image[y:y + h, x:x + w]
                hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                saturation_std = np.std(hsv_roi[:, :, 1])

                # Lower std deviation indicates more uniform color (slider track)
                if saturation_std < 50:
                    confidence = 0.6

                    # Sliders often in settings screens - check for location hints
                    if y > height * 0.2 and y < height * 0.8:  # Not at very top or bottom
                        confidence += 0.1

                    interactive_elements.append({
                        'x': x,
                        'y': y,
                        'width': w,
                        'height': h,
                        'type': 'slider_horizontal',
                        'confidence': float(confidence),
                        'detection_method': 'shape',
                        'aspect_ratio': float(aspect_ratio)
                    })

            # Vertical sliders (height much greater than width)
            elif aspect_ratio < 0.25 and w >= 10:
                # Similar checks as horizontal sliders
                roi = original_image[y:y + h, x:x + w]
                hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                saturation_std = np.std(hsv_roi[:, :, 1])

                if saturation_std < 50:
                    confidence = 0.6

                    # Vertical sliders often at screen edges
                    if x < width * 0.1 or x > width * 0.9:
                        confidence += 0.1

                    interactive_elements.append({
                        'x': x,
                        'y': y,
                        'width': w,
                        'height': h,
                        'type': 'slider_vertical',
                        'confidence': float(confidence),
                        'detection_method': 'shape',
                        'aspect_ratio': float(aspect_ratio)
                    })

        # 3. Detect grid-based menus (common in games)
        grid_elements = self._detect_grid_elements(binary_image, original_image)
        if grid_elements:
            interactive_elements.extend(grid_elements)

        # 4. Detect D-pad controls (common in games)
        dpad_elements = self._detect_dpad_controls(binary_image, original_image)
        if dpad_elements:
            interactive_elements.extend(dpad_elements)

        # Filter out overlapping elements, keeping the highest confidence ones
        non_overlapping = self._filter_overlapping_elements(interactive_elements)

        return non_overlapping

    def _detect_grid_elements(self, binary_image, original_image) -> List[Dict[str, Any]]:
        """
        Detect grid-based menu elements common in games.

        Args:
            binary_image: Preprocessed binary image
            original_image: Original color image

        Returns:
            List of detected grid elements
        """
        grid_elements = []
        height, width = original_image.shape[:2]

        # Find contours
        contours, _ = cv2.findContours(
            binary_image,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        # Filter contours to find potential grid cells
        potential_cells = []

        for contour in contours:
            area = cv2.contourArea(contour)

            # Skip very small or large areas
            min_area = width * height * 0.001
            max_area = width * height * 0.02
            if area < min_area or area > max_area:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h if h > 0 else 0

            # Grid cells typically have square-ish shape
            if 0.7 < aspect_ratio < 1.3:
                # Check for sharp corners (grid cells often have them)
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)

                if len(approx) == 4:  # Quadrilateral shape
                    potential_cells.append((x, y, w, h))

        # Check if we have enough cells to form a grid
        if len(potential_cells) >= 4:
            # Sort by position
            cells_by_row = sorted(potential_cells, key=lambda c: c[1])

            # Group cells by rows (cells in the same row have similar y-coordinates)
            rows = []
            current_row = [cells_by_row[0]]
            current_y = cells_by_row[0][1]

            for cell in cells_by_row[1:]:
                if abs(cell[1] - current_y) < cell[3] * 0.5:  # Within half a cell height
                    current_row.append(cell)
                else:
                    # Start a new row
                    rows.append(current_row)
                    current_row = [cell]
                    current_y = cell[1]

            # Add the last row
            if current_row:
                rows.append(current_row)

            # Check if we have a grid-like structure (at least 2 rows with multiple cells)
            grid_like = len(rows) >= 2 and all(len(row) >= 2 for row in rows[:2])

            if grid_like:
                # It's a grid! Add all cells as interactive elements
                confidence = 0.7

                for row in rows:
                    for (x, y, w, h) in row:
                        grid_elements.append({
                            'x': x,
                            'y': y,
                            'width': w,
                            'height': h,
                            'type': 'grid_cell',
                            'confidence': float(confidence),
                            'detection_method': 'grid'
                        })

        return grid_elements

    def _detect_dpad_controls(self, binary_image, original_image) -> List[Dict[str, Any]]:
        """
        Detect D-pad controls common in game interfaces.

        A D-pad typically consists of 4 directional buttons arranged in a cross pattern.
        This method looks for arrangements of buttons that match this pattern.

        Args:
            binary_image: Preprocessed binary image
            original_image: Original color image

        Returns:
            List of detected D-pad elements
        """
        dpad_elements = []
        height, width = original_image.shape[:2]

        # Find contours
        contours, _ = cv2.findContours(
            binary_image,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        # Filter contours to find potential directional buttons
        button_candidates = []

        for contour in contours:
            area = cv2.contourArea(contour)

            # Skip very small or large areas
            min_area = width * height * 0.0005
            max_area = width * height * 0.01
            if area < min_area or area > max_area:
                continue

            x, y, w, h = cv2.boundingRect(contour)

            # Check if it's a reasonable size for a directional button
            if w >= 20 and h >= 20:
                # Directional buttons often have triangular or arrow shapes
                # Let's check its shape complexity
                epsilon = 0.04 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)

                # Triangular or arrow-like shapes often have 3-6 points
                if 3 <= len(approx) <= 6:
                    button_candidates.append((x, y, w, h))

        # Check for D-pad arrangements (typically 4 buttons in a cross pattern)
        if len(button_candidates) >= 4:
            # Group candidates by proximity
            grouped = []
            processed = set()

            for i, (x1, y1, w1, h1) in enumerate(button_candidates):
                if i in processed:
                    continue

                group = [(x1, y1, w1, h1)]
                processed.add(i)

                center_x1 = x1 + w1 // 2
                center_y1 = y1 + h1 // 2

                for j, (x2, y2, w2, h2) in enumerate(button_candidates):
                    if j in processed or i == j:
                        continue

                    center_x2 = x2 + w2 // 2
                    center_y2 = y2 + h2 // 2

                    # Distance between centers
                    distance = np.sqrt((center_x2 - center_x1) ** 2 + (center_y2 - center_y1) ** 2)

                    # If close enough to be part of the same D-pad
                    if distance < (w1 + h1 + w2 + h2) / 2:
                        group.append((x2, y2, w2, h2))
                        processed.add(j)

                if len(group) >= 3:  # At least 3 directional buttons
                    grouped.append(group)

            # Check each group for D-pad pattern
            for group in grouped:
                if len(group) >= 3:  # At least 3 buttons (could be missing one direction)
                    # Calculate the bounding box of the entire D-pad
                    min_x = min(button[0] for button in group)
                    min_y = min(button[1] for button in group)
                    max_x = max(button[0] + button[2] for button in group)
                    max_y = max(button[1] + button[3] for button in group)

                    dpad_width = max_x - min_x
                    dpad_height = max_y - min_y

                    # D-pads are typically square-ish overall
                    aspect_ratio = dpad_width / dpad_height if dpad_height > 0 else 0

                    if 0.7 < aspect_ratio < 1.3:
                        confidence = 0.6 + (min(len(group), 4) / 10.0)  # Higher if we have all 4 buttons

                        # Common position for D-pads (usually left side of screen for movement)
                        if min_x < width * 0.4 and min_y > height * 0.5:
                            confidence += 0.1

                        # Add the entire D-pad as one interactive element
                        dpad_elements.append({
                            'x': min_x,
                            'y': min_y,
                            'width': dpad_width,
                            'height': dpad_height,
                            'type': 'dpad',
                            'confidence': float(confidence),
                            'detection_method': 'pattern',
                            'button_count': len(group)
                        })

                        # Also add individual directional buttons
                        for button_idx, (x, y, w, h) in enumerate(group):
                            dpad_elements.append({
                                'x': x,
                                'y': y,
                                'width': w,
                                'height': h,
                                'type': f'dpad_button_{button_idx}',
                                'parent_dpad': len(dpad_elements) - 1,  # Reference to the parent D-pad
                                'confidence': float(confidence - 0.1),
                                # Slightly lower confidence for individual buttons
                                'detection_method': 'pattern'
                            })

        return dpad_elements

    def _filter_overlapping_elements(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out overlapping elements, keeping those with higher confidence.

        Args:
            elements: List of detected elements

        Returns:
            Filtered list with non-overlapping elements
        """
        if not elements:
            return []

        # Sort by confidence (higher first)
        sorted_elements = sorted(elements, key=lambda e: e.get('confidence', 0), reverse=True)

        # Keep track of which elements to include
        included = []

        for element in sorted_elements:
            # Check if this element significantly overlaps with any included element
            has_overlap = False

            for included_element in included:
                x1, y1 = element['x'], element['y']
                w1, h1 = element['width'], element['height']

                x2, y2 = included_element['x'], included_element['y']
                w2, h2 = included_element['width'], included_element['height']

                # Calculate overlap percentage
                overlap = self._calculate_overlap_percentage(x1, y1, w1, h1, x2, y2, w2, h2)

                if overlap > 0.6:  # Significant overlap
                    has_overlap = True
                    break

            # If no significant overlap, include this element
            if not has_overlap:
                included.append(element)

        return included

    def _detect_error_indicators(self, original_image, texts) -> List[Dict[str, Any]]:
        """
        Detect error indicators in Android UI.

        This method identifies potential error indicators through multiple techniques:
        1. Color-based detection (red and orange error indicators)
        2. Text-based detection of error messages
        3. Error icon detection (exclamation marks, X symbols)
        4. Error dialog pattern recognition

        Args:
            original_image: Original color image
            texts: Detected text elements

        Returns:
            List of error indicator characteristics
        """
        error_indicators = []

        # 1. Color-based error detection (red and orange colors common in errors)
        color_indicators = self._detect_color_error_indicators(original_image)
        error_indicators.extend(color_indicators)

        # 2. Text-based error detection
        text_indicators = self._detect_text_error_indicators(texts)
        error_indicators.extend(text_indicators)

        # 3. Icon-based error detection
        icon_indicators = self._detect_icon_error_indicators(original_image)
        error_indicators.extend(icon_indicators)

        # 4. Pattern-based error detection (error dialogs, etc.)
        pattern_indicators = self._detect_error_patterns(original_image, texts)
        error_indicators.extend(pattern_indicators)

        # Process all error indicators to add type and classification
        processed_indicators = []
        for indicator in error_indicators:
            # Skip low confidence indicators
            if indicator.get('confidence', 0) < 0.4:
                continue

            # Classify error by type if not already set
            if 'error_type' not in indicator:
                indicator['error_type'] = self._classify_error_indicator(indicator)

            processed_indicators.append(indicator)

        # Sort by confidence
        processed_indicators.sort(key=lambda e: e.get('confidence', 0), reverse=True)

        # Remove overlapping errors, preferring higher confidence ones
        non_overlapping = self._filter_overlapping_elements(processed_indicators)

        return non_overlapping

    def _detect_color_error_indicators(self, original_image) -> List[Dict[str, Any]]:
        """
        Detect error indicators based on color (red and orange).

        Args:
            original_image: Original color image

        Returns:
            List of color-based error indicators
        """
        # Convert to HSV for better color detection
        hsv_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2HSV)
        height, width = original_image.shape[:2]

        error_indicators = []

        # Define color ranges in HSV

        # Red color (wraps around hue spectrum)
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 100, 100])
        upper_red2 = np.array([180, 255, 255])

        # Orange color
        lower_orange = np.array([11, 100, 100])
        upper_orange = np.array([25, 255, 255])

        # Process red color (which wraps around the hue spectrum)
        mask1 = cv2.inRange(hsv_image, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv_image, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(mask1, mask2)

        # Process orange color
        orange_mask = cv2.inRange(hsv_image, lower_orange, upper_orange)

        # Combine masks
        combined_mask = cv2.bitwise_or(red_mask, orange_mask)

        # Apply morphological operations to reduce noise
        kernel = np.ones((3, 3), np.uint8)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)

        # Find contours of colored regions
        contours, _ = cv2.findContours(
            combined_mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        # Process contours
        for contour in contours:
            area = cv2.contourArea(contour)
            min_area = width * height * 0.0005
            max_area = width * height * 0.1

            if min_area <= area <= max_area:
                x, y, w, h = cv2.boundingRect(contour)

                # Get region of interest (ROI)
                roi = original_image[y:y + h, x:x + w]

                # Calculate color intensity for classification
                b, g, r = cv2.split(roi)
                red_mean = np.mean(r)
                green_mean = np.mean(g)
                blue_mean = np.mean(b)

                # Red should be significantly higher than other colors
                red_dominance = red_mean / (green_mean + blue_mean + 1)

                # Calculate aspect ratio to help with classification
                aspect_ratio = w / h if h > 0 else 0

                confidence = 0.0

                # Red dominant colors are more likely to be errors
                if red_dominance > 1.3:
                    confidence = 0.6

                    # Check shape (error indicators are often circular or rectangular)
                    epsilon = 0.02 * cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, epsilon, True)

                    # Rectangular shape (common for error backgrounds)
                    if len(approx) == 4:
                        confidence += 0.1
                    # Circular/oval shape (common for error icons)
                    elif len(approx) >= 8:
                        # Check circularity
                        perimeter = cv2.arcLength(contour, True)
                        circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0

                        if 0.7 < circularity < 1.3:
                            confidence += 0.2

                if confidence >= 0.5:
                    error_indicators.append({
                        'x': x,
                        'y': y,
                        'width': w,
                        'height': h,
                        'area': float(area),
                        'red_dominance': float(red_dominance),
                        'detection_method': 'color',
                        'confidence': float(confidence),
                        'error_type': 'color_error'
                    })

        return error_indicators

    def _detect_text_error_indicators(self, texts) -> List[Dict[str, Any]]:
        """
        Detect error indicators based on error message text.

        Args:
            texts: List of detected text elements

        Returns:
            List of text-based error indicators
        """
        error_indicators = []

        for text in texts:
            if text.get('is_error_like', False):
                text_content = text['text'].lower()
                bbox = text['bbox']

                # Determine error category and confidence
                confidence = 0.6  # Base confidence for error-like text
                error_category = 'general'

                # Check specific error categories
                for category, keywords in self.error_keywords.items():
                    if any(keyword in text_content for keyword in keywords):
                        error_category = category
                        # Exact matches increase confidence
                        if any(keyword == text_content for keyword in keywords):
                            confidence = 0.9
                        break

                # Higher confidence for common error patterns
                if "error" in text_content or "failed" in text_content:
                    confidence += 0.1

                # If OCR confidence is low, reduce our error confidence
                ocr_confidence = text.get('confidence', 0)
                if ocr_confidence < 60:
                    confidence -= 0.1

                error_indicators.append({
                    'x': bbox['x'],
                    'y': bbox['y'],
                    'width': bbox['width'],
                    'height': bbox['height'],
                    'text': text['text'],
                    'detection_method': 'text',
                    'confidence': float(min(confidence, 1.0)),
                    'error_type': f'text_{error_category}_error',
                    'error_category': error_category
                })

        return error_indicators

    def _detect_icon_error_indicators(self, original_image) -> List[Dict[str, Any]]:
        """
        Detect error indicators based on common error icons.

        This method identifies error icons like:
        - Exclamation marks (!)
        - X symbols
        - Warning triangles
        - Information (i) symbols

        Args:
            original_image: Original color image

        Returns:
            List of icon-based error indicators
        """
        error_indicators = []
        height, width = original_image.shape[:2]

        # Convert to grayscale
        gray = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)

        # Apply edge detection to identify shapes
        edges = cv2.Canny(gray, 50, 150)

        # Apply morphological operations to connect nearby edges
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)

        # Find contours from edges
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Process each contour
        for contour in contours:
            area = cv2.contourArea(contour)

            # Filter by reasonable icon sizes
            min_area = width * height * 0.0005
            max_area = width * height * 0.01
            if area < min_area or area > max_area:
                continue

            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)

            # Calculate circularity (4π × area / perimeter²)
            perimeter = cv2.arcLength(contour, True)
            circularity = 0
            if perimeter > 0:
                circularity = 4 * np.pi * area / (perimeter * perimeter)

            # Calculate aspect ratio
            aspect_ratio = w / h if h > 0 else 0

            # Get region of interest (ROI)
            roi = original_image[y:y + h, x:x + w]

            icon_type = None
            confidence = 0.0

            # Check for circular icons (common for info/error)
            if 0.7 < circularity < 1.3 and 0.8 < aspect_ratio < 1.2:
                # Check color inside potential icon
                b, g, r = cv2.split(roi)
                red_mean = np.mean(r)
                blue_mean = np.mean(b)
                green_mean = np.mean(g)

                # Error icons often have red coloring
                if red_mean > 1.2 * max(blue_mean, green_mean):
                    icon_type = 'error_circle'
                    confidence = 0.7
                # Information icons often have blue coloring
                elif blue_mean > 1.2 * max(red_mean, green_mean):
                    icon_type = 'info_circle'
                    confidence = 0.6  # Lower confidence for info icons
                else:
                    icon_type = 'generic_circle'
                    confidence = 0.5

            # Check for triangle shapes (warning icons)
            elif len(cv2.approxPolyDP(contour, 0.04 * perimeter, True)) == 3:
                # Get color information
                b, g, r = cv2.split(roi)
                red_mean = np.mean(r)
                green_mean = np.mean(g)
                blue_mean = np.mean(b)

                # Warning triangles often have yellow/orange coloring
                if red_mean > 1.2 * blue_mean and green_mean > 1.2 * blue_mean:
                    icon_type = 'warning_triangle'
                    confidence = 0.8
                else:
                    icon_type = 'generic_triangle'
                    confidence = 0.6

            # Check for exclamation mark-like contours
            elif aspect_ratio < 0.5 and h >= w * 3:
                # Vertical and very narrow - likely an exclamation mark
                icon_type = 'exclamation_mark'
                confidence = 0.7

            # Check for X-like shapes
            elif 0.8 < aspect_ratio < 1.2:
                # X shapes typically have a particular contour structure
                # Try to detect diagonal lines

                # Convert ROI to binary
                roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                _, roi_binary = cv2.threshold(roi_gray, 127, 255, cv2.THRESH_BINARY)

                # Use Hough lines to detect straight lines
                lines = cv2.HoughLinesP(roi_binary, 1, np.pi / 180, threshold=int(w / 3),
                                        minLineLength=int(w / 2), maxLineGap=int(w / 4))

                if lines is not None and len(lines) >= 2:
                    diagonal_count = 0
                    for line in lines:
                        x1, y1, x2, y2 = line[0]
                        # Calculate line angle
                        angle = abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)

                        # Diagonal lines are around 45 or 135 degrees
                        if 30 < angle < 60 or 120 < angle < 150:
                            diagonal_count += 1

                    if diagonal_count >= 2:
                        # Additional checks for navigation icons vs error X

                        # Check if this is at the bottom navigation bar (common in Android)
                        is_in_nav_bar = y > height * 0.85

                        # Check if this is symmetric (navigation Xs tend to be more symmetric)
                        is_symmetric = abs(w - h) < min(w, h) * 0.2

                        # If it's in the navigation area, lower confidence significantly
                        if is_in_nav_bar:
                            confidence = 0.3  # Too low to be considered an error
                        else:
                            icon_type = 'x_mark'
                            confidence = 0.8

                            # Further check if it's a navigation icon by looking at neighbors
                            # Navigation icons usually appear in groups at similar y-positions
                            nav_icon_count = 0
                            for other_contour in contours:
                                if other_contour is contour:
                                    continue

                                ox, oy, ow, oh = cv2.boundingRect(other_contour)
                                if abs(oy - y) < h * 1.5 and oh > 0.5 * h and oh < 1.5 * h:
                                    nav_icon_count += 1

                            # If there are several similar icons at the same level,
                            # it's likely a navigation bar
                            if nav_icon_count >= 2:
                                confidence = 0.3  # Too low to be considered an error

            if icon_type and confidence >= 0.5:
                error_indicators.append({
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'area': float(area),
                    'circularity': float(circularity),
                    'detection_method': 'icon',
                    'icon_type': icon_type,
                    'confidence': float(confidence),
                    'error_type': 'icon_error'
                })

        return error_indicators

    def _detect_error_patterns(self, original_image, texts) -> List[Dict[str, Any]]:
        """
        Detect error indicators based on visual patterns common in Android errors.

        This method detects UI patterns that typically indicate errors:
        - Modal dialogs with error content
        - Toast messages
        - Snackbar notifications
        - Input field validation errors

        Args:
            original_image: Original color image
            texts: Detected text elements

        Returns:
            List of pattern-based error indicators
        """
        error_indicators = []
        height, width = original_image.shape[:2]

        # 1. Detect error dialogs
        dialog_indicators = self._detect_error_dialogs(original_image, texts)
        if dialog_indicators:
            error_indicators.extend(dialog_indicators)

        # 2. Detect form field validation errors
        # Look for error texts near input fields (typically shown below or to the right)
        validation_errors = []
        input_field_patterns = [
            # Common Android EditText heights (typically rectangular)
            {'min_aspect': 3.0, 'max_aspect': 8.0, 'min_height': 30, 'max_height': 60}
        ]

        # Convert to grayscale and threshold
        gray = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Potential input fields
        input_fields = []

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 100:  # Skip very small contours
                continue

            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h if h > 0 else 0

            # Check against common input field patterns
            for pattern in input_field_patterns:
                if (pattern['min_aspect'] <= aspect_ratio <= pattern['max_aspect'] and
                        pattern['min_height'] <= h <= pattern['max_height']):
                    input_fields.append((x, y, w, h))
                    break

        # Look for error texts near input fields
        for field in input_fields:
            field_x, field_y, field_w, field_h = field
            field_bottom = field_y + field_h
            field_right = field_x + field_w

            for text in texts:
                if not text.get('is_error_like', False):
                    continue

                bbox = text['bbox']
                text_x = bbox['x']
                text_y = bbox['y']

                # Error messages are typically below or to the right of fields
                is_below = (text_y >= field_bottom and
                            text_y <= field_bottom + field_h * 2 and
                            text_x + bbox['width'] >= field_x and
                            text_x <= field_right)

                is_right = (text_x >= field_right and
                            text_x <= field_right + field_w and
                            text_y + bbox['height'] >= field_y and
                            text_y <= field_bottom)

                if is_below or is_right:
                    validation_errors.append({
                        'x': text_x,
                        'y': text_y,
                        'width': bbox['width'],
                        'height': bbox['height'],
                        'text': text['text'],
                        'field_x': field_x,
                        'field_y': field_y,
                        'field_width': field_w,
                        'field_height': field_h,
                        'detection_method': 'validation',
                        'confidence': 0.8,  # High confidence for validation errors
                        'error_type': 'validation_error'
                    })

        error_indicators.extend(validation_errors)

        # 3. Detect toast-like notifications (usually at bottom of screen)
        toast_indicators = self._detect_toast_notifications(original_image, texts)
        if toast_indicators:
            error_indicators.extend(toast_indicators)

        return error_indicators

    def _detect_error_dialogs(self, original_image, texts) -> List[Dict[str, Any]]:
        """
        Detect error dialogs in Android UI.

        Error dialogs typically have:
        - A modal appearance (centered, with semi-transparent overlay)
        - A title (often containing error keywords)
        - A message explaining the error
        - Action buttons (OK, Cancel, Retry, etc.)

        Args:
            original_image: Original color image
            texts: Detected text elements

        Returns:
            List of dialog-based error indicators
        """
        dialog_indicators = []
        height, width = original_image.shape[:2]

        # Convert to grayscale
        gray = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)

        # Apply threshold to identify potential dialog boundaries
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

        # Apply morphological operations to connect dialog edges
        kernel = np.ones((10, 10), np.uint8)
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        # Find contours
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Look for rectangular contours that could be dialogs
        for contour in contours:
            area = cv2.contourArea(contour)

            # Filter by area - dialog usually takes significant screen space
            min_dialog_area = width * height * 0.1  # At least 10% of screen
            max_dialog_area = width * height * 0.8  # At most 80% of screen

            if area < min_dialog_area or area > max_dialog_area:
                continue

            x, y, w, h = cv2.boundingRect(contour)

            # Calculate how centered the rectangle is
            center_x = x + w / 2
            center_y = y + h / 2
            screen_center_x = width / 2
            screen_center_y = height / 2

            # Offset from center (0.0 = perfectly centered, 1.0 = at edge)
            x_offset = abs(center_x - screen_center_x) / (width / 2)
            y_offset = abs(center_y - screen_center_y) / (height / 2)
            offset = (x_offset + y_offset) / 2

            # Dialog is more likely if well-centered
            if offset > 0.4:  # Not well-centered
                continue

            # Check for title bar (often darker at top of dialog)
            has_title_bar = False
            title_height = min(50, h // 5)  # Typical title bar height

            if y > 5 and h > 100:
                title_region = original_image[y:y + title_height, x:x + w]
                main_region = original_image[y + title_height:y + h, x:x + w]

                title_brightness = np.mean(title_region)
                main_brightness = np.mean(main_region)

                # If title is darker than main content, more likely a dialog
                if title_brightness < main_brightness * 0.9:
                    has_title_bar = True

            # Check for texts inside dialog
            dialog_texts = []
            error_texts = []
            button_texts = []

            for text in texts:
                bbox = text['bbox']
                tx = bbox['x']
                ty = bbox['y']
                tw = bbox['width']
                th = bbox['height']

                # Check if text is inside dialog
                if x <= tx <= x + w and y <= ty <= y + h:
                    dialog_texts.append(text)

                    # Check if it looks like an error message
                    if text.get('is_error_like', False):
                        error_texts.append(text)

                    # Check if it looks like a button label
                    if text.get('is_button_like', False):
                        button_texts.append(text)

            # Dialog confidence score
            confidence = 0.0

            # Base confidence from visual characteristics
            base_confidence = 0.4

            # Adjust based on centering
            centering_score = 1.0 - offset
            base_confidence += centering_score * 0.2

            # Adjust based on having a title bar
            if has_title_bar:
                base_confidence += 0.1

            # Adjust based on containing buttons
            if len(button_texts) > 0:
                base_confidence += min(len(button_texts), 3) * 0.05

            # Higher confidence if it contains error text
            if len(error_texts) > 0:
                error_weight = min(len(error_texts), 2) * 0.2
                confidence = base_confidence + error_weight

                # Create the dialog error indicator
                dialog_indicators.append({
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'area': float(area),
                    'centering': float(1.0 - offset),
                    'detection_method': 'dialog',
                    'confidence': float(min(confidence, 1.0)),
                    'error_type': 'dialog_error',
                    'contains_texts': len(dialog_texts),
                    'contains_error_texts': len(error_texts),
                    'contains_buttons': len(button_texts)
                })

                # Also add the specific error texts as high-confidence error indicators
                for error_text in error_texts:
                    bbox = error_text['bbox']
                    dialog_indicators.append({
                        'x': bbox['x'],
                        'y': bbox['y'],
                        'width': bbox['width'],
                        'height': bbox['height'],
                        'text': error_text['text'],
                        'detection_method': 'dialog_text',
                        'confidence': 0.9,  # High confidence for error text in dialog
                        'error_type': 'dialog_text_error',
                        'parent_dialog': len(dialog_indicators) - 1  # Reference to parent dialog
                    })

        return dialog_indicators

    def _detect_toast_notifications(self, original_image, texts) -> List[Dict[str, Any]]:
        """
        Detect toast notifications that may indicate errors.

        Toast notifications in Android typically:
        - Appear at the bottom of the screen
        - Have a dark, semi-transparent background
        - Contain a short message
        - Have rounded corners

        Args:
            original_image: Original color image
            texts: Detected text elements

        Returns:
            List of toast notification error indicators
        """
        toast_indicators = []
        height, width = original_image.shape[:2]

        # Convert to grayscale
        gray = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)

        # Apply threshold to identify dark regions (toast backgrounds)
        _, thresh = cv2.threshold(gray, 70, 255, cv2.THRESH_BINARY_INV)

        # Apply morphological operations
        kernel = np.ones((5, 5), np.uint8)
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        # Find contours
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)

            # Toast size constraints
            min_toast_area = width * height * 0.01  # At least 1% of screen
            max_toast_area = width * height * 0.15  # At most 15% of screen

            if area < min_toast_area or area > max_toast_area:
                continue

            x, y, w, h = cv2.boundingRect(contour)

            # Toast position constraints (usually at bottom center)
            is_at_bottom = y > height * 0.7
            is_centered_x = abs((x + w / 2) - (width / 2)) < (width * 0.3)

            if not is_at_bottom:
                continue

            # Check aspect ratio (toast is usually wide and short)
            aspect_ratio = w / h if h > 0 else 0
            if aspect_ratio < 2 or aspect_ratio > 10:
                continue

            # Check if the region is dark (toast background is usually dark)
            roi = original_image[y:y + h, x:x + w]
            brightness = np.mean(roi)
            is_dark = brightness < 100

            if not is_dark:
                continue

            # Check for text inside the potential toast
            toast_texts = []
            error_texts = []

            for text in texts:
                bbox = text['bbox']
                tx = bbox['x']
                ty = bbox['y']
                tw = bbox['width']
                th = bbox['height']

                # Check if text is inside the potential toast
                if x <= tx <= x + w and y <= ty <= y + h:
                    toast_texts.append(text)

                    # Check if it looks like an error message
                    if text.get('is_error_like', False):
                        error_texts.append(text)

            # Toast must contain some text
            if not toast_texts:
                continue

            # Calculate confidence
            confidence = 0.6  # Base confidence for visual match

            # Higher if centered horizontally
            if is_centered_x:
                confidence += 0.1

            # Higher if it contains error text
            if error_texts:
                confidence += 0.2
                error_text = error_texts[0]['text']  # Use the first error text
            else:
                error_text = toast_texts[0]['text']  # Use the first text if no error text

            toast_indicators.append({
                'x': x,
                'y': y,
                'width': w,
                'height': h,
                'area': float(area),
                'text': error_text,
                'detection_method': 'toast',
                'confidence': float(confidence),
                'error_type': 'toast_notification',
                'contains_error_text': len(error_texts) > 0
            })

        return toast_indicators

    def _classify_error_indicator(self, indicator: Dict[str, Any]) -> str:
        """
        Classify an error indicator by type and severity.

        This method analyzes detected error indicators and determines their
        type and potential cause based on available information.

        Args:
            indicator: Detected error indicator

        Returns:
            Error type classification
        """
        # Default error type
        error_type = "unknown_error"

        # Get detection method
        method = indicator.get('detection_method', '')

        # Text-based classification
        if method == 'text':
            text = indicator.get('text', '').lower()

            # Check for category indicators
            if any(word in text for word in self.error_keywords['network']):
                error_type = "network_error"
            elif any(word in text for word in self.error_keywords['permission']):
                error_type = "permission_error"
            elif any(word in text for word in self.error_keywords['validation']):
                error_type = "validation_error"
            elif any(word in text for word in self.error_keywords['system']):
                error_type = "system_error"
            else:
                error_type = "general_error"

            # May already have a more specific classification
            if indicator.get('error_category'):
                error_type = f"{indicator['error_category']}_error"

        # Color-based classification
        elif method == 'color':
            error_type = "ui_error"

        # Icon-based classification
        elif method == 'icon':
            icon_type = indicator.get('icon_type', '')

            if 'warning' in icon_type:
                error_type = "warning"
            elif 'error' in icon_type:
                error_type = "critical_error"
            elif 'info' in icon_type:
                error_type = "info"
            elif 'exclamation' in icon_type:
                error_type = "alert"
            else:
                error_type = "visual_indicator"

        # Dialog, toast, or pattern-based classification
        elif method in ('dialog', 'toast', 'validation', 'pattern'):
            # These typically come pre-classified
            if indicator.get('error_type'):
                return indicator['error_type']

            # Add method as prefix if not already
            if not error_type.startswith(method):
                error_type = f"{method}_{error_type}"

        return error_type

    def extract_information(self) -> Dict[str, Any]:
        """
        Extract all information from the current screenshot.

        This method is used by the ScreenshotActionComplementor for integration
        with the action complement pipeline. It returns a dictionary with all
        extracted information in a format compatible with the complementor.

        Returns:
            Dictionary with extracted information including texts, buttons,
            interactive elements, and error indicators
        """
        # Check that we have a valid image path stored
        if not hasattr(self, 'current_image_path') or not self.current_image_path:
            self.logger.error("No image path available for extraction")
            return {
                "texts": [],
                "buttons": [],
                "error_indicators": [],
                "interactive_elements": []
            }

        # Analyze the screenshot if not already done
        if not hasattr(self, 'current_result') or not self.current_result:
            try:
                self.current_result = self.analyze(self.current_image_path)
            except Exception as e:
                self.logger.error(f"Error extracting information: {e}")
                return {
                    "texts": [],
                    "buttons": [],
                    "error_indicators": [],
                    "interactive_elements": []
                }

        # Return extracted information in the expected format
        return {
            "texts": self.current_result.texts,
            "buttons": self.current_result.buttons,
            "error_indicators": self.current_result.error_indicators,
            "interactive_elements": self.current_result.interactive_elements
        }

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get analyzer metrics.

        Returns:
            Dictionary containing metrics about screenshot analysis
        """
        # Calculate average processing time
        avg_time = 0.0
        if self.metrics["processed_images"] > 0:
            avg_time = (self.metrics["total_processing_time"] /
                        self.metrics["processed_images"])

        return {
            "processed_images": self.metrics["processed_images"],
            "successful_analyses": self.metrics["successful_analyses"],
            "failed_analyses": self.metrics["failed_analyses"],
            "total_processing_time": self.metrics["total_processing_time"],
            "average_processing_time": avg_time,
            "detected_texts": self.metrics["detected_texts"],
            "detected_buttons": self.metrics["detected_buttons"],
            "detected_errors": self.metrics["detected_errors"],
            "detected_interactive_elements": self.metrics["detected_interactive_elements"]
        }


def main(screenshot_path):
    """
    Example usage demonstration
    """
    try:
        # Create analyzer instance
        analyzer = ScreenshotAnalyzer()

        # Analyze screenshot
        result = analyzer.analyze(screenshot_path)

        # Print metrics
        print("Analysis Metrics:")
        metrics = analyzer.get_metrics()
        for key, value in metrics.items():
            print(f"  {key}: {value}")

        # Convert result to JSON and pretty print
        result_dict = {
            'image_path': result.image_path,
            'dimensions': result.dimensions,
            'texts': result.texts,
            'buttons': result.buttons,
            'error_indicators': result.error_indicators,
            'interactive_elements': result.interactive_elements,
            'processing_time': result.processing_time,
            'success': result.success
        }
        print("\nAnalysis Results:")
        print(json.dumps(result_dict, indent=2))

    except Exception as e:
        print(f"Error processing screenshot: {e}")
        sys.exit(1)


if __name__ == '__main__':
    # image = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/001.png"
    image = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/007.png"
    main(image)
