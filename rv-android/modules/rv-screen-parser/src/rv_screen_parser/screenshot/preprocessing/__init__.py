"""
Image preprocessing components for screenshot analysis.

This package provides image preprocessing capabilities including grayscale
conversion, contrast enhancement, binary thresholding, and noise reduction
optimized for different types of visual element detection.
"""

from .image_preprocessor import ImagePreprocessor, get_image_preprocessor

__all__ = ["ImagePreprocessor", "get_image_preprocessor"]
