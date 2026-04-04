#!/usr/bin/env python3
"""
Image preprocessing component for screenshot analysis.

This module provides image preprocessing capabilities for optimizing
screenshot analysis, including grayscale conversion, contrast enhancement,
binary thresholding, and noise reduction operations.

### Architectural Role:
- Provides specialized image preprocessing for different analysis types
- Implements contrast enhancement algorithms for improved OCR accuracy
- Generates binary images optimized for contour detection
- Applies noise reduction techniques for cleaner analysis results

### Design Decisions:
- Uses OpenCV for image processing operations
- Implements multiple preprocessing strategies for different detection needs
- Provides both grayscale and binary preprocessing pipelines
- Optimizes parameters for mobile screenshot characteristics
"""

import cv2
import numpy as np

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVParsingError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class ImagePreprocessor:
    """
    Image preprocessing component for screenshot analysis operations.
    
    Provides optimized image preprocessing methods for text detection,
    contour analysis, and visual element identification.
    """
    
    def __init__(self):
        """Initialize image preprocessor with logging."""
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "screenshot.preprocessor",
            {CONTEXT_COMPONENT: "ImagePreprocessor"}
        )
    
    @ErrorHandler.handle_errors(component="ImagePreprocessor", phase="grayscale_conversion", reraise=True)
    def preprocess_grayscale(self, image: np.ndarray) -> np.ndarray:
        """
        Convert image to grayscale with enhanced contrast for text detection.
        
        This preprocessing pipeline is optimized for OCR operations and text
        detection by applying histogram equalization and light noise reduction.
        
        Args:
            image: Original color image as numpy array
            
        Returns:
            Enhanced grayscale image optimized for text detection
            
        Raises:
            RVParsingError: If image processing fails
        """
        if image is None:
            raise RVParsingError(
                "Cannot process null image",
                parser_type="ImagePreprocessor"
            )
        
        if len(image.shape) < 3:
            self.logger.warning("Image appears to already be grayscale")
            return image
        
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply histogram equalization to improve contrast
            # This helps with text detection in varied lighting conditions
            equalized = cv2.equalizeHist(gray)
            
            # Apply light Gaussian blur to reduce noise while preserving text edges
            blurred = cv2.GaussianBlur(equalized, (3, 3), 0)
            
            self.logger.debug(f"Converted to grayscale: {image.shape} -> {blurred.shape}")
            return blurred
            
        except Exception as e:
            raise RVParsingError(
                f"Failed to preprocess grayscale image: {str(e)}",
                parser_type="ImagePreprocessor"
            ) from e
    
    @ErrorHandler.handle_errors(component="ImagePreprocessor", phase="binary_conversion", reraise=True)
    def preprocess_binary(self, image: np.ndarray) -> np.ndarray:
        """
        Create a binary image optimized for shape and contour detection.
        
        Uses adaptive thresholding to handle varied lighting conditions
        and applies morphological operations for noise reduction.
        
        Args:
            image: Original color image as numpy array
            
        Returns:
            Binary image optimized for contour and shape detection
            
        Raises:
            RVParsingError: If image processing fails
        """
        if image is None:
            raise RVParsingError(
                "Cannot process null image",
                parser_type="ImagePreprocessor"
            )
        
        try:
            # Convert to grayscale first if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Apply Gaussian blur to reduce noise before thresholding
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Apply adaptive thresholding for better handling of varied lighting
            binary = cv2.adaptiveThreshold(
                blurred,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV,  # Invert for easier contour finding
                11,  # Block size for adaptive threshold
                2   # Constant subtracted from mean
            )
            
            # Apply morphological operations to clean up the binary image
            kernel = np.ones((3, 3), np.uint8)
            cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            self.logger.debug(f"Created binary image: {image.shape} -> {cleaned.shape}")
            return cleaned
            
        except Exception as e:
            raise RVParsingError(
                f"Failed to preprocess binary image: {str(e)}",
                parser_type="ImagePreprocessor"
            ) from e
    
    @ErrorHandler.handle_errors(component="ImagePreprocessor", phase="edge_detection")
    def preprocess_for_edge_detection(self, image: np.ndarray, 
                                    low_threshold: int = 50, 
                                    high_threshold: int = 150) -> np.ndarray:
        """
        Preprocess image for edge detection operations.
        
        Applies Canny edge detection with morphological operations to
        enhance edge connectivity for icon and symbol detection.
        
        Args:
            image: Original color image as numpy array
            low_threshold: Lower threshold for Canny edge detection
            high_threshold: Upper threshold for Canny edge detection
            
        Returns:
            Edge-enhanced image for icon detection
        """
        try:
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Apply edge detection
            edges = cv2.Canny(gray, low_threshold, high_threshold)
            
            # Apply morphological operations to connect nearby edges
            kernel = np.ones((3, 3), np.uint8)
            enhanced_edges = cv2.dilate(edges, kernel, iterations=1)
            
            self.logger.debug(f"Generated edge image with thresholds {low_threshold}-{high_threshold}")
            return enhanced_edges
            
        except Exception as e:
            self.logger.warning(f"Edge detection preprocessing failed: {e}")
            # Return original grayscale as fallback
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    
    @ErrorHandler.handle_errors(component="ImagePreprocessor", phase="noise_reduction")
    def reduce_noise(self, image: np.ndarray, kernel_size: int = 5) -> np.ndarray:
        """
        Apply noise reduction to improve analysis accuracy.
        
        Uses non-local means denoising for effective noise removal
        while preserving important edge information.
        
        Args:
            image: Input image as numpy array
            kernel_size: Size of the denoising kernel
            
        Returns:
            Denoised image
        """
        try:
            if len(image.shape) == 3:
                # Color image denoising
                denoised = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
            else:
                # Grayscale image denoising
                denoised = cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
            
            self.logger.debug(f"Applied noise reduction with kernel size {kernel_size}")
            return denoised
            
        except Exception as e:
            self.logger.warning(f"Noise reduction failed: {e}")
            # Return original image as fallback
            return image
    
    def enhance_contrast(self, image: np.ndarray, alpha: float = 1.5, beta: int = 0) -> np.ndarray:
        """
        Enhance image contrast for better element detection.
        
        Applies linear contrast enhancement using the formula:
        new_image = alpha * original_image + beta
        
        Args:
            image: Input image as numpy array
            alpha: Contrast control (1.0-3.0 typically)
            beta: Brightness control (-100 to 100 typically)
            
        Returns:
            Contrast-enhanced image
        """
        try:
            enhanced = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
            self.logger.debug(f"Enhanced contrast with alpha={alpha}, beta={beta}")
            return enhanced
            
        except Exception as e:
            self.logger.warning(f"Contrast enhancement failed: {e}")
            return image
    
    def validate_image(self, image: np.ndarray) -> bool:
        """
        Validate that an image is suitable for processing.
        
        Args:
            image: Image to validate
            
        Returns:
            True if image is valid for processing, False otherwise
        """
        if image is None:
            self.logger.error("Image is None")
            return False
        
        if not isinstance(image, np.ndarray):
            self.logger.error(f"Image is not numpy array: {type(image)}")
            return False
        
        if image.size == 0:
            self.logger.error("Image has zero size")
            return False
        
        if len(image.shape) not in [2, 3]:
            self.logger.error(f"Invalid image dimensions: {image.shape}")
            return False
        
        # Check if image has reasonable dimensions (not too small or too large)
        height, width = image.shape[:2]
        if width < 10 or height < 10:
            self.logger.error(f"Image too small: {width}x{height}")
            return False
        
        if width > 10000 or height > 10000:
            self.logger.warning(f"Image very large: {width}x{height}")
        
        return True


# Global instance for convenient access
_image_preprocessor = None

def get_image_preprocessor() -> ImagePreprocessor:
    """
    Get the global image preprocessor instance.
    
    Returns:
        ImagePreprocessor instance
    """
    global _image_preprocessor
    if _image_preprocessor is None:
        _image_preprocessor = ImagePreprocessor()
    return _image_preprocessor