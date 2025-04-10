#!/usr/bin/env python3
"""
Advanced Android Screenshot Analyzer

Efficiently extracts information from Android screenshots with
optimized text and error detection. Follows the BaseAnalyzer pattern
for consistent integration with the analysis architecture.

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
from typing import Dict, List, Any, Optional, Tuple

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
    processing_time: float = 0.0
    success: bool = True
    error_message: str = ""


class ScreenshotAnalyzer(BaseAnalyzer[ScreenshotAnalysisResult]):
    """
    Advanced analyzer for extracting information from Android screenshots.
    
    Follows the BaseAnalyzer pattern for consistent integration with the
    analysis architecture. Extracts text, detects UI elements, and identifies
    potential error indicators from screenshots.
    
    ### Architectural Role:
    - Provides visual analysis capabilities for screenshots
    - Integrates with the analysis pipeline for result management
    - Extracts actionable information from visual data
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
            "failed_analyses": 0
        }
        
        # Store image path for later use
        self.current_image_path = image_path
        self.current_result = None
        
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
        
        This analyzer doesn't require initialization from static data
        but can use it for enhanced analysis if available.
        """
        if self.static_data and hasattr(self.static_data, 'windows'):
            self.logger.info(f"Initialized with static data containing {len(self.static_data.windows)} windows")
    
    def analyze(self, image_path: str) -> ScreenshotAnalysisResult:
        """
        Analyze a screenshot and extract information.
        
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
            
            # Detect buttons
            result.buttons = self._detect_buttons(binary_image)
            
            # Detect error indicators
            result.error_indicators = self._detect_error_indicators(original_image)
            
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
            Grayscale image
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply histogram equalization to improve contrast
        return cv2.equalizeHist(gray)
    
    def _preprocess_binary(self, image) -> np.ndarray:
        """
        Create a binary image with adaptive thresholding.
        
        Args:
            image: Original color image
            
        Returns:
            Binary image
        """
        # Convert to grayscale first
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive thresholding
        return cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )
    
    def _extract_text(self, gray_image) -> List[Dict[str, Any]]:
        """
        Extract text using multiple OCR techniques.
        
        Args:
            gray_image: Preprocessed grayscale image
            
        Returns:
            List of dictionaries with text and its coordinates
        """
        # Multiple Tesseract configurations for robust text detection
        configs = [
            # High precision mode with full character set
            r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,:;!?() -c preserve_interword_spaces=1',
            # Page segmentation mode for single uniform block of text
            r'--oem 3 --psm 11'
        ]
        
        texts = []
        for config in configs:
            # Try OCR with different configurations
            try:
                text_data = pytesseract.image_to_data(
                    gray_image,
                    output_type=pytesseract.Output.DICT,
                    config=config
                )
                
                # Process and filter text results
                for i in range(len(text_data['text'])):
                    # Stricter filtering of text
                    if (int(text_data['conf'][i]) > 50 and
                            len(text_data['text'][i].strip()) > 1):
                        texts.append({
                            'text': text_data['text'][i].strip(),
                            'confidence': int(text_data['conf'][i]),
                            'bbox': {
                                'x': int(text_data['left'][i]),
                                'y': int(text_data['top'][i]),
                                'width': int(text_data['width'][i]),
                                'height': int(text_data['height'][i])
                            }
                        })
            except Exception as e:
                self.logger.warning(f"OCR configuration failed: {e}")
        
        return texts
    
    def _detect_buttons(self, binary_image) -> List[Dict[str, Any]]:
        """
        Detect potential button regions using contour analysis.
        
        Args:
            binary_image: Preprocessed binary image
            
        Returns:
            List of button characteristics
        """
        # Find contours in binary image
        contours, _ = cv2.findContours(
            binary_image,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        buttons = []
        for contour in contours:
            # Filter contours to identify potential buttons
            area = cv2.contourArea(contour)
            if 50 < area < 5000:  # Adjust area range as needed
                x, y, w, h = cv2.boundingRect(contour)
                buttons.append({
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'area': area
                })
        
        return buttons
    
    def _detect_error_indicators(self, original_image) -> List[Dict[str, Any]]:
        """
        Detect error indicators in Android UI.
        
        This method identifies potential error indicators through multiple techniques:
        1. Color detection (red and orange error indicators)
        2. Text-based detection of error messages
        3. Common error icon detection
        4. Visual error pattern recognition
        
        Args:
            original_image: Original color image
            
        Returns:
            List of error indicator characteristics
        """
        error_indicators = []
        
        # 1. Color-based error detection (red and orange colors common in errors)
        color_indicators = self._detect_color_error_indicators(original_image)
        error_indicators.extend(color_indicators)
        
        # 2. Text-based error detection
        text_indicators = self._detect_text_error_indicators(original_image)
        error_indicators.extend(text_indicators)
        
        # 3. Icon-based error detection
        icon_indicators = self._detect_icon_error_indicators(original_image)
        error_indicators.extend(icon_indicators)
        
        # 4. Pattern-based error detection
        pattern_indicators = self._detect_error_patterns(original_image)
        error_indicators.extend(pattern_indicators)
        
        # Add error type classification to each indicator
        for indicator in error_indicators:
            # Check for existing type, otherwise infer type from detection method
            if 'error_type' not in indicator:
                if 'text' in indicator:
                    indicator['error_type'] = 'text_error'
                elif 'icon_match' in indicator:
                    indicator['error_type'] = 'icon_error'
                elif 'red_intensity' in indicator and indicator['red_intensity'] > 150:
                    indicator['error_type'] = 'color_error'
                elif 'pattern_match' in indicator:
                    indicator['error_type'] = 'visual_pattern_error'
                else:
                    indicator['error_type'] = 'unknown_error'
        
        return error_indicators
    
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
            if 50 < area < 5000:  # Adjust as needed
                x, y, w, h = cv2.boundingRect(contour)
                
                # Get region of interest (ROI)
                roi = original_image[y:y + h, x:x + w]
                
                # Calculate color intensity for classification
                red_intensity = np.mean(roi[:, :, 2])
                
                # Calculate aspect ratio to help with classification
                aspect_ratio = w / h if h > 0 else 0
                
                error_indicators.append({
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'area': area,
                    'red_intensity': float(red_intensity),
                    'aspect_ratio': float(aspect_ratio),
                    'detection_method': 'color',
                    'confidence': 0.7 if area > 200 else 0.5  # Higher confidence for larger areas
                })
        
        return error_indicators
    
    def _detect_text_error_indicators(self, original_image) -> List[Dict[str, Any]]:
        """
        Detect error indicators based on error message text.
        
        Args:
            original_image: Original color image
            
        Returns:
            List of text-based error indicators
        """
        # Preprocess for optimal text extraction
        gray_image = self._preprocess_grayscale(original_image)
        
        error_indicators = []
        
        # Error keywords commonly found in Android UIs
        error_keywords = [
            "error", "failed", "exception", "invalid", "not found", 
            "problem", "warning", "alert", "incorrect", "denied",
            "unable to", "cannot", "retry", "wrong", "expired",
            "crashed", "not available", "timeout", "sorry",
            "not valid", "required", "rejected", "fault"
        ]
        
        try:
            # Extract text with high precision configuration
            config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'
            text_data = pytesseract.image_to_data(
                gray_image,
                output_type=pytesseract.Output.DICT,
                config=config
            )
            
            # Check each text element for error keywords
            for i in range(len(text_data['text'])):
                text = text_data['text'][i].strip().lower()
                
                # Skip empty or low confidence text
                if not text or int(text_data['conf'][i]) < 60:
                    continue
                
                # Check if any error keyword is in the text
                for keyword in error_keywords:
                    if keyword in text:
                        # Extract position and dimensions
                        x = int(text_data['left'][i])
                        y = int(text_data['top'][i])
                        w = int(text_data['width'][i])
                        h = int(text_data['height'][i])
                        
                        # Calculate a confidence score (0.0-1.0)
                        # Higher for more exact matches and higher OCR confidence
                        base_confidence = int(text_data['conf'][i]) / 100.0
                        
                        # Higher confidence for exact matches of error terms
                        keyword_match_score = 0.7
                        if text == keyword:
                            keyword_match_score = 1.0
                        elif text.startswith(keyword) or text.endswith(keyword):
                            keyword_match_score = 0.9
                        
                        confidence = min(1.0, (base_confidence * 0.5) + (keyword_match_score * 0.5))
                        
                        error_indicators.append({
                            'x': x,
                            'y': y,
                            'width': w,
                            'height': h,
                            'text': text,
                            'error_keyword': keyword,
                            'ocr_confidence': int(text_data['conf'][i]),
                            'detection_method': 'text',
                            'confidence': confidence,
                            'error_type': 'text_error'
                        })
                        break  # No need to check other keywords
        
        except Exception as e:
            self.logger.warning(f"Text-based error detection failed: {e}")
        
        return error_indicators
    
    def _detect_icon_error_indicators(self, original_image) -> List[Dict[str, Any]]:
        """
        Detect error indicators based on common error icons.
        
        Args:
            original_image: Original color image
            
        Returns:
            List of icon-based error indicators
        """
        error_indicators = []
        
        # Load or create template features for common error icons
        # This uses simple shape detection since we don't have template images
        
        # Convert to grayscale
        gray = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)
        
        # Apply edge detection to identify shapes
        edges = cv2.Canny(gray, 50, 150)
        
        # Find contours from edges
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Identify circles (common in error icons like exclamation in circle)
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # Filter by reasonable icon sizes
            if 100 < area < 2000:
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                
                # Calculate circularity (4π × area / perimeter²)
                perimeter = cv2.arcLength(contour, True)
                circularity = 0
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter * perimeter)
                
                # Check if shape is approximately circular (common for error icons)
                if 0.7 < circularity < 1.3:
                    # Verify aspect ratio (roughly square)
                    aspect_ratio = w / h if h > 0 else 0
                    if 0.8 < aspect_ratio < 1.2:
                        # Check color inside potential icon
                        roi = original_image[y:y + h, x:x + w]
                        red_mean = np.mean(roi[:, :, 2])
                        
                        confidence = min(0.9, circularity * 0.7)
                        
                        # Higher confidence for red circular shapes
                        if red_mean > 150:
                            confidence += 0.1
                        
                        error_indicators.append({
                            'x': x,
                            'y': y,
                            'width': w,
                            'height': h,
                            'area': area,
                            'circularity': float(circularity),
                            'detection_method': 'icon',
                            'icon_match': 'circular_icon',
                            'confidence': confidence,
                            'error_type': 'icon_error'
                        })
                
                # Check for exclamation mark-like contours
                elif w < h * 0.5 and h > 30:
                    # More likely to be an exclamation mark if vertical and narrow
                    error_indicators.append({
                        'x': x,
                        'y': y,
                        'width': w,
                        'height': h,
                        'detection_method': 'icon',
                        'icon_match': 'exclamation_mark',
                        'confidence': 0.6,
                        'error_type': 'icon_error'
                    })
        
        return error_indicators
    
    def _detect_error_patterns(self, original_image) -> List[Dict[str, Any]]:
        """
        Detect error indicators based on visual patterns common in Android errors.
        
        Args:
            original_image: Original color image
            
        Returns:
            List of pattern-based error indicators
        """
        error_indicators = []
        
        # Get image dimensions
        height, width = original_image.shape[:2]
        
        # 1. Dialog pattern detection (common for error alerts)
        # Check for semi-transparent overlay with a centered rectangle
        
        # Convert to grayscale
        gray = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)
        
        # Apply threshold to identify potential dialog boundaries
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        
        # Apply morphological operations
        kernel = np.ones((5, 5), np.uint8)
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Look for rectangular contours that could be dialogs
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # Filter by area - dialog usually takes significant screen space
            min_dialog_area = width * height * 0.1  # At least 10% of screen
            max_dialog_area = width * height * 0.7  # At most 70% of screen
            
            if min_dialog_area < area < max_dialog_area:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Calculate center offset from screen center
                center_x = x + w/2
                center_y = y + h/2
                screen_center_x = width/2
                screen_center_y = height/2
                
                # Calculate how centered the rectangle is (0-1)
                x_centering = 1.0 - min(1.0, abs(center_x - screen_center_x) / (width/2))
                y_centering = 1.0 - min(1.0, abs(center_y - screen_center_y) / (height/2))
                centering = (x_centering + y_centering) / 2
                
                # Dialog is more likely if centered
                confidence = centering * 0.6
                
                # Check for title bar (often darker at top of dialog)
                if y > 20 and h > 100:
                    title_region = original_image[y:y+30, x:x+w]
                    main_region = original_image[y+30:y+h, x:x+w]
                    
                    title_brightness = np.mean(title_region)
                    main_brightness = np.mean(main_region)
                    
                    # If title is darker than main content, more likely a dialog
                    if title_brightness < main_brightness * 0.9:
                        confidence += 0.2
                
                # Only add if confidence is reasonable
                if confidence > 0.5:
                    error_indicators.append({
                        'x': x,
                        'y': y,
                        'width': w,
                        'height': h,
                        'area': area,
                        'centering': float(centering),
                        'detection_method': 'pattern',
                        'pattern_match': 'dialog_pattern',
                        'confidence': confidence,
                        'error_type': 'dialog_error'
                    })
        
        return error_indicators
    
    def extract_information(self) -> Dict[str, Any]:
        """
        Extract all information from the current screenshot.
        
        This method is used by the ScreenshotActionComplementor for integration
        with the action complement pipeline. It returns a dictionary with all
        extracted information in a format compatible with the complementor.
        
        Returns:
            Dictionary with extracted information including texts, buttons
            and error indicators
        """
        # Check that we have a valid image path stored
        if not hasattr(self, 'current_image_path') or not self.current_image_path:
            self.logger.error("No image path available for extraction")
            return {
                "texts": [],
                "buttons": [],
                "error_indicators": []
            }
            
        # Analyze the screenshot if not already done
        if not hasattr(self, 'current_result'):
            try:
                self.current_result = self.analyze(self.current_image_path)
            except Exception as e:
                self.logger.error(f"Error extracting information: {e}")
                return {
                    "texts": [],
                    "buttons": [],
                    "error_indicators": []
                }
                
        # Return extracted information in the expected format
        return {
            "texts": self.current_result.texts,
            "buttons": self.current_result.buttons,
            "error_indicators": self.current_result.error_indicators
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
            "average_processing_time": avg_time
        }


# Legacy API for backward compatibility
def analyze_screenshot(image_path: str) -> Dict[str, Any]:
    """
    Legacy method for screenshot analysis.
    
    This method provides backward compatibility with existing code.
    New code should use the ScreenshotAnalyzer class directly.
    
    Args:
        image_path: Path to the screenshot image
        
    Returns:
        Dictionary with extracted screenshot information
    """
    analyzer = ScreenshotAnalyzer()
    result = analyzer.analyze(image_path)
    
    # Convert to the old format
    return {
        'texts': result.texts,
        'buttons': result.buttons,
        'error_indicators': result.error_indicators,
        'image_info': result.dimensions
    }


def main():
    """
    Example usage demonstration
    """
    # Check if image path is provided
    if len(sys.argv) < 2:
        print("Usage: python screenshot_analyzer.py <path_to_screenshot>")
        sys.exit(1)
    
    # Get screenshot path from command line argument
    screenshot_path = sys.argv[1]
    
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
            'processing_time': result.processing_time,
            'success': result.success
        }
        print("\nAnalysis Results:")
        print(json.dumps(result_dict, indent=2))
        
    except Exception as e:
        print(f"Error processing screenshot: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()