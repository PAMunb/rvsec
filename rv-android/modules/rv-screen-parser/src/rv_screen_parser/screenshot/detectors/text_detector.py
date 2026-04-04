#!/usr/bin/env python3
"""
Text detection component for screenshot analysis.

This module provides OCR-based text detection capabilities with specialized
algorithms for mobile UI text extraction, confidence filtering, and
contextual classification of text elements.

### Architectural Role:
- Implements OCR text extraction with multiple Tesseract configurations
- Provides text classification for button-like and error-like content
- Handles text deduplication and confidence-based filtering
- Generates validated DetectedText models with comprehensive metadata

### Design Decisions:
- Uses multiple OCR configurations for improved detection coverage
- Implements position-based deduplication to handle overlapping detections
- Provides contextual classification based on text content patterns
- Integrates with Pydantic models for type-safe result generation
"""

import re
from typing import List, Set, Tuple
import numpy as np
import pytesseract

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVParsingError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager

from ..models import DetectedText, BoundingBox
from ..utils.geometry_utils import get_geometry_utils


class TextDetector:
    """
    OCR-based text detection component for screenshot analysis.
    
    Provides comprehensive text extraction with confidence filtering,
    contextual classification, and deduplication capabilities.
    """
    
    def __init__(self):
        """Initialize text detector with OCR configurations and classification patterns."""
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "screenshot.text_detector",
            {CONTEXT_COMPONENT: "TextDetector"}
        )
        self.geometry_utils = get_geometry_utils()
        
        # Initialize OCR configurations for different detection scenarios
        self.ocr_configs = [
            # High precision mode with full character set
            r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,:;!?() -c preserve_interword_spaces=1',
            # Page segmentation mode for single uniform block of text
            r'--oem 3 --psm 11'
        ]
        
        # Button text indicators for classification
        self.button_text_indicators = [
            "ok", "cancel", "yes", "no", "submit", "login", "sign in", "register",
            "next", "previous", "continue", "back", "done", "save", "delete",
            "add", "remove", "close", "send", "search", "buy", "purchase",
            "confirm", "accept", "decline", "agree", "disagree", "play", "start",
            "settings", "menu", "options", "help", "skip", "retry", "reload"
        ]
        
        # Error keyword categories for classification
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
    
    @ErrorHandler.handle_errors(component="TextDetector", phase="text_extraction", reraise=True)
    def extract_text(self, gray_image: np.ndarray) -> List[DetectedText]:
        """
        Extract text elements from preprocessed grayscale image.
        
        Uses multiple OCR configurations to optimize text detection
        in various scenarios, then combines and filters the results into
        validated DetectedText models.
        
        Args:
            gray_image: Preprocessed grayscale image
            
        Returns:
            List of validated DetectedText models
            
        Raises:
            RVParsingError: If OCR processing fails completely
        """
        if gray_image is None:
            raise RVParsingError(
                "Cannot extract text from null image",
                parser_type="TextDetector"
            )
        
        detected_texts = []
        seen_texts: Set[str] = set()  # To track duplicate text in similar positions
        
        # Try multiple OCR configurations for better coverage
        for config_idx, config in enumerate(self.ocr_configs):
            try:
                self.logger.debug(f"Running OCR configuration {config_idx + 1}/{len(self.ocr_configs)}")
                
                text_data = pytesseract.image_to_data(
                    gray_image,
                    output_type=pytesseract.Output.DICT,
                    config=config
                )
                
                # Process and filter text results
                config_texts = self._process_ocr_results(text_data, seen_texts)
                detected_texts.extend(config_texts)
                
            except Exception as e:
                self.logger.warning(f"OCR configuration {config_idx + 1} failed: {str(e)}")
                # Continue with next configuration
        
        if not detected_texts:
            self.logger.warning("No text detected with any OCR configuration")
            return []
        
        # Sort texts by confidence (higher first)
        detected_texts.sort(key=lambda t: t.confidence, reverse=True)
        
        # Remove duplicates with lower confidence
        filtered_texts = self._remove_overlapping_text(detected_texts)
        
        self.logger.info(f"Extracted {len(filtered_texts)} text elements from {len(detected_texts)} detections")
        return filtered_texts
    
    def _process_ocr_results(self, text_data: dict, seen_texts: Set[str]) -> List[DetectedText]:
        """
        Process OCR results from Tesseract into DetectedText models.
        
        Args:
            text_data: OCR output dictionary from Tesseract
            seen_texts: Set of already seen text for deduplication
            
        Returns:
            List of DetectedText models from this OCR run
        """
        config_texts = []
        
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
            
            # Create validated text element using Pydantic model
            try:
                bbox = BoundingBox(x=x, y=y, width=w, height=h)
                text_element = DetectedText(
                    text=text,
                    confidence=confidence,
                    bbox=bbox,
                    is_button_like=self.is_button_text(text),
                    is_error_like=self.is_error_text(text)
                )
                config_texts.append(text_element)
                
            except Exception as validation_error:
                self.logger.warning(f"Failed to create DetectedText for '{text}': {validation_error}")
                # Continue processing other text elements
        
        return config_texts
    
    def _remove_overlapping_text(self, detected_texts: List[DetectedText]) -> List[DetectedText]:
        """
        Remove overlapping text detections, keeping higher confidence ones.
        
        Args:
            detected_texts: List of detected text elements sorted by confidence
            
        Returns:
            Filtered list with non-overlapping text elements
        """
        filtered_texts = []
        seen_positions: Set[Tuple[int, int, int, int]] = set()
        
        for text_element in detected_texts:
            bbox = text_element.bbox
            x, y, w, h = bbox.x, bbox.y, bbox.width, bbox.height
            
            # Check if this text significantly overlaps with already detected text
            overlap_found = False
            for pos in seen_positions:
                px, py, pw, ph = pos
                # Check for significant overlap
                try:
                    overlap = self.geometry_utils.calculate_overlap_percentage(x, y, w, h, px, py, pw, ph)
                    if overlap > 0.5:
                        overlap_found = True
                        break
                except Exception as e:
                    self.logger.warning(f"Error calculating text overlap: {e}")
            
            if not overlap_found:
                filtered_texts.append(text_element)
                seen_positions.add((x, y, w, h))
        
        return filtered_texts
    
    def is_button_text(self, text: str) -> bool:
        """
        Check if text likely represents a button label.
        
        Uses pattern matching and keyword detection to identify
        text that appears to be clickable button content.
        
        Args:
            text: The text to check
            
        Returns:
            True if text is likely a button label, False otherwise
        """
        if not text or not text.strip():
            return False
        
        text_lower = text.lower().strip()
        
        # Check against known button labels
        if any(label == text_lower or label in text_lower for label in self.button_text_indicators):
            return True
        
        # Short text with specific patterns (likely a button)
        if len(text) <= 15 and text.isprintable() and not text.isspace():
            # Check for button-like patterns
            if re.match(r'^[A-Z][a-z]+$', text):  # Capitalized word
                return True
            if re.match(r'^[A-Z\s]+$', text):  # All caps
                return True
            if any(char in text for char in ['→', '▶', '◀', '↑', '↓']):  # Navigation symbols
                return True
        
        return False
    
    def is_error_text(self, text: str) -> bool:
        """
        Check if text likely indicates an error message.
        
        Uses keyword matching across different error categories
        to identify error-related text content.
        
        Args:
            text: The text to check
            
        Returns:
            True if text is likely an error message, False otherwise
        """
        if not text or not text.strip():
            return False
        
        text_lower = text.lower().strip()
        
        # Check against all error keywords categories
        for category, keywords in self.error_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                self.logger.debug(f"Detected {category} error text: '{text}'")
                return True
        
        # Check for error patterns
        error_patterns = [
            r'\b(error|fail|exception)\b',
            r'\b(invalid|incorrect|wrong)\b',
            r'\b(cannot|unable|denied)\b',
            r'\b(required|missing)\b'
        ]
        
        for pattern in error_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    def get_text_classification_summary(self, texts: List[DetectedText]) -> dict:
        """
        Get summary statistics about detected text classifications.
        
        Args:
            texts: List of detected text elements
            
        Returns:
            Dictionary with classification statistics
        """
        total_texts = len(texts)
        button_texts = sum(1 for t in texts if t.is_button_like)
        error_texts = sum(1 for t in texts if t.is_error_like)
        high_confidence = sum(1 for t in texts if t.confidence >= 80)
        
        return {
            "total_texts": total_texts,
            "button_like_texts": button_texts,
            "error_like_texts": error_texts,
            "high_confidence_texts": high_confidence,
            "average_confidence": sum(t.confidence for t in texts) / total_texts if total_texts > 0 else 0.0
        }


# Global instance for convenient access
_text_detector = None

def get_text_detector() -> TextDetector:
    """
    Get the global text detector instance.
    
    Returns:
        TextDetector instance
    """
    global _text_detector
    if _text_detector is None:
        _text_detector = TextDetector()
    return _text_detector