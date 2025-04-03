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
        Detect error indicators typically shown in red.
        
        Args:
            original_image: Original color image
            
        Returns:
            List of error indicator characteristics
        """
        # Convert to HSV for better color detection
        hsv_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2HSV)
        
        # Define red color ranges in HSV
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 100, 100])
        upper_red2 = np.array([180, 255, 255])
        
        # Create masks for red color ranges
        mask1 = cv2.inRange(hsv_image, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv_image, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(mask1, mask2)
        
        # Find contours of red regions
        contours, _ = cv2.findContours(
            red_mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        error_indicators = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 50 < area < 5000:  # Adjust as needed
                x, y, w, h = cv2.boundingRect(contour)
                
                # Calculate red intensity
                red_intensity = np.mean(original_image[y:y + h, x:x + w, 2])
                
                error_indicators.append({
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'area': area,
                    'red_intensity': float(red_intensity)
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