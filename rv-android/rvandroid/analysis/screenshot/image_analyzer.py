"""
Screenshot image analyzer module.

Provides advanced image analysis capabilities for Android screenshots,
integrated with the unified analysis architecture.
"""

import cv2
import numpy as np
import pytesseract
import time
import os
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple

from rvandroid.analysis.base_analyzer import BaseAnalyzer
from rvandroid.domain.static import StaticAnalysisData


@dataclass
class ImageAnalysisResult:
    """Data class for screenshot image analysis results."""
    image_path: str
    dimensions: Dict[str, int] = field(default_factory=dict)
    texts: List[Dict[str, Any]] = field(default_factory=list)
    elements: List[Dict[str, Any]] = field(default_factory=list)
    colors: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0
    success: bool = True
    error_message: str = ""


class ScreenshotImageAnalyzer(BaseAnalyzer[ImageAnalysisResult]):
    """
    Advanced image analyzer for extracting information from Android screenshots.
    
    This analyzer provides computer vision and OCR capabilities for
    understanding the contents of screenshots. It extracts text,
    identifies UI elements, and analyzes color distributions.
    
    ### Architectural Role:
    - Provides advanced computer vision capabilities
    - Extracts semantic information from screenshots
    - Integrates with the analysis system for result management
    """
    
    def __init__(self, analyzer_name: str = "image_analyzer", static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the image analyzer.
        
        Args:
            analyzer_name: Name identifier for the analyzer
            static_data: Optional static analysis data for context
        """
        super().__init__(analyzer_name, static_data)
        
        # Configure OCR
        self.ocr_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'
        
        # Initialize metrics
        self.metrics = {
            "processed_images": 0,
            "total_processing_time": 0.0,
            "detected_text_elements": 0,
            "detected_ui_elements": 0
        }
        
        # Store known UI element templates if available
        self.ui_templates = {}
        if static_data:
            self._load_ui_templates()
    
    def _initialize_from_static_data(self) -> None:
        """
        Initialize with static analysis data.
        
        Uses static data to understand the application's UI structure
        and optimize image analysis.
        """
        if self.static_data and hasattr(self.static_data, 'windows'):
            windows_count = len(self.static_data.windows)
            self.logger.info(f"Initialized with static data containing {windows_count} windows")
            
            # Extract window dimensions and other useful information
            if windows_count > 0:
                self._load_ui_templates()
    
    def _load_ui_templates(self) -> None:
        """Load UI element templates from static data if available."""
        # This would load templates for known UI elements to improve detection
        # Currently a placeholder - would be implemented based on available static data
        self.logger.debug("UI template loading is a placeholder - not fully implemented")
    
    def analyze(self, image_path: str) -> ImageAnalysisResult:
        """
        Analyze a screenshot image.
        
        Args:
            image_path: Path to the screenshot image
            
        Returns:
            ImageAnalysisResult containing extracted information
        """
        start_time = time.time()
        self.logger.info(f"Analyzing image: {image_path}")
        
        # Initialize result
        result = ImageAnalysisResult(image_path=image_path)
        
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Failed to load image from {image_path}")
            
            # Store image dimensions
            height, width, _ = image.shape
            result.dimensions = {"width": width, "height": height}
            
            # Process image in multiple ways
            result.texts = self._extract_text(image)
            result.elements = self._detect_ui_elements(image)
            result.colors = self._analyze_colors(image)
            
            # Update metrics
            self.metrics["processed_images"] += 1
            self.metrics["detected_text_elements"] += len(result.texts)
            self.metrics["detected_ui_elements"] += len(result.elements)
            
            result.success = True
            
        except Exception as e:
            self.logger.error(f"Image analysis failed: {str(e)}")
            result.success = False
            result.error_message = str(e)
        
        # Record processing time
        processing_time = time.time() - start_time
        result.processing_time = processing_time
        self.metrics["total_processing_time"] += processing_time
        
        self.log_processing_summary("image", 1)
        return result
    
    def _extract_text(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Extract text from the image using OCR.
        
        Args:
            image: OpenCV image
            
        Returns:
            List of detected text elements with positions and confidence
        """
        # Convert to grayscale and enhance for OCR
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        gray = cv2.equalizeHist(gray)
        
        try:
            # Extract text data
            text_data = pytesseract.image_to_data(
                gray, 
                output_type=pytesseract.Output.DICT,
                config=self.ocr_config
            )
            
            # Process and filter results
            texts = []
            for i in range(len(text_data['text'])):
                text = text_data['text'][i].strip()
                confidence = int(text_data['conf'][i])
                
                # Filter out low confidence and empty results
                if confidence > 50 and len(text) > 1:
                    texts.append({
                        'text': text,
                        'confidence': confidence,
                        'bbox': {
                            'x': int(text_data['left'][i]),
                            'y': int(text_data['top'][i]),
                            'width': int(text_data['width'][i]),
                            'height': int(text_data['height'][i])
                        }
                    })
            
            return texts
            
        except Exception as e:
            self.logger.warning(f"OCR processing error: {str(e)}")
            return []
    
    def _detect_ui_elements(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect UI elements like buttons, text fields, etc.
        
        Args:
            image: OpenCV image
            
        Returns:
            List of detected UI elements with positions and types
        """
        elements = []
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Perform morphological operations to close gaps
        kernel = np.ones((5, 5), np.uint8)
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(
            closed, 
            cv2.RETR_EXTERNAL, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Process contours
        for i, contour in enumerate(contours):
            # Filter by area
            area = cv2.contourArea(contour)
            if area < 100 or area > 50000:  # Skip too small or too large
                continue
                
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            
            # Calculate aspect ratio
            aspect_ratio = float(w) / h if h > 0 else 0
            
            # Determine element type based on shape
            element_type = "unknown"
            if 0.9 < aspect_ratio < 1.1 and w > 20:
                element_type = "button"  # Square-ish elements
            elif aspect_ratio > 3 and h < 50:
                element_type = "text_field"  # Wide elements
            elif aspect_ratio < 0.5:
                element_type = "scrollbar"  # Tall elements
                
            elements.append({
                'id': i,
                'type': element_type,
                'bbox': {
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h
                },
                'area': area,
                'aspect_ratio': aspect_ratio
            })
        
        return elements
    
    def _analyze_colors(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Analyze color distribution in the image.
        
        Args:
            image: OpenCV image
            
        Returns:
            Color analysis information
        """
        # Convert to HSV for better color analysis
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Calculate histograms
        h_hist = cv2.calcHist([hsv], [0], None, [180], [0, 180])
        s_hist = cv2.calcHist([hsv], [1], None, [256], [0, 256])
        v_hist = cv2.calcHist([hsv], [2], None, [256], [0, 256])
        
        # Normalize histograms
        h_hist = cv2.normalize(h_hist, h_hist, 0, 1, cv2.NORM_MINMAX)
        s_hist = cv2.normalize(s_hist, s_hist, 0, 1, cv2.NORM_MINMAX)
        v_hist = cv2.normalize(v_hist, v_hist, 0, 1, cv2.NORM_MINMAX)
        
        # Find dominant colors
        dominant_hue = int(np.argmax(h_hist))
        dominant_sat = int(np.argmax(s_hist))
        dominant_val = int(np.argmax(v_hist))
        
        # Color categories based on HSV
        color_category = "unknown"
        if dominant_sat < 50:
            if dominant_val < 50:
                color_category = "black"
            elif dominant_val > 200:
                color_category = "white"
            else:
                color_category = "gray"
        else:
            # Color wheel segmentation
            if 0 <= dominant_hue < 30 or 150 <= dominant_hue < 180:
                color_category = "red"
            elif 30 <= dominant_hue < 90:
                color_category = "green"
            elif 90 <= dominant_hue < 150:
                color_category = "blue"
                
        return {
            "dominant_hsv": [dominant_hue, dominant_sat, dominant_val],
            "dominant_category": color_category,
            "histograms": {
                "hue": h_hist.flatten().tolist(),
                "saturation": s_hist.flatten().tolist(),
                "value": v_hist.flatten().tolist()
            }
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get metrics about the image analysis process.
        
        Returns:
            Dictionary containing performance and result metrics
        """
        # Calculate average processing time and element counts
        avg_time = 0.0
        avg_text_count = 0.0
        avg_ui_count = 0.0
        
        if self.metrics["processed_images"] > 0:
            count = self.metrics["processed_images"]
            avg_time = self.metrics["total_processing_time"] / count
            avg_text_count = self.metrics["detected_text_elements"] / count
            avg_ui_count = self.metrics["detected_ui_elements"] / count
        
        return {
            "processed_images": self.metrics["processed_images"],
            "total_processing_time": self.metrics["total_processing_time"],
            "average_processing_time": avg_time,
            "total_text_elements": self.metrics["detected_text_elements"],
            "total_ui_elements": self.metrics["detected_ui_elements"],
            "average_text_per_image": avg_text_count,
            "average_ui_per_image": avg_ui_count
        }