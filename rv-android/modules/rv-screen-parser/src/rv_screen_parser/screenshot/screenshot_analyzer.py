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

### Architectural Decisions:
- Uses strongly typed Pydantic models for all analysis results
- Implements modular component architecture with specialized detectors
- Provides comprehensive validation for coordinate and confidence data
- Uses confidence scoring to prioritize detection results
- Integrates with framework error handling patterns

### Role in the System:
- Provides visual analysis capabilities that complement UI hierarchy inspection
- Integrates with the analysis pipeline for result management and action planning
- Enables testing of applications with custom rendering (games, canvas-based UIs)
- Detects error conditions that might not be visible in the UI hierarchy

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

import sys
import time
from typing import Dict, Any, Optional

import cv2

from rv_android_core.analysis.base_analyzer import BaseAnalyzer
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVParsingError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager

from rv_screen_parser.screenshot.models import (
    ScreenshotAnalysisResult, ImageDimensions
)
from rv_screen_parser.screenshot.detectors import (
    get_text_detector, get_button_detector, get_error_detector, 
    get_interactive_element_detector
)
from rv_screen_parser.screenshot.preprocessing import get_image_preprocessor
from rv_screen_parser.screenshot.utils import get_geometry_utils


class ScreenshotAnalyzer(BaseAnalyzer[ScreenshotAnalysisResult]):
    """
    Advanced analyzer for extracting information from Android screenshots.

    This analyzer coordinates specialized detection components to provide comprehensive
    analysis of UI elements, text, and error conditions in Android screenshots, with
    particular focus on:
    1. Detecting game UI elements not present in the UI hierarchy
    2. Identifying various types of error conditions visually
    3. Extracting actionable information for test automation

    ### Architectural Role:
    - Orchestrates specialized detector components for modular analysis
    - Provides visual analysis capabilities that complement UI hierarchy inspection
    - Integrates with the analysis pipeline for result management and action planning
    - Enables testing of applications with custom rendering (games, canvas-based UIs)
    - Detects error conditions that might not be visible in the UI hierarchy

    ### Design Decisions:
    - Uses dependency injection pattern with specialized detector components
    - Maintains same public interface while leveraging modular architecture
    - Employs type-safe Pydantic models for all analysis results
    - Uses confidence scoring to prioritize detection results
    - Implements comprehensive error handling and logging
    """

    def __init__(self, image_path: Optional[str] = None, analyzer_name: str = "screenshot",
                 static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the screenshot analyzer with enhanced component architecture.

        Args:
            image_path: Optional path to a screenshot image
            analyzer_name: Name identifier for the analyzer
            static_data: Optional static analysis data for context
        """
        super().__init__(analyzer_name, static_data)
        
        # Initialize enhanced logging and error handling
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "screenshot.analyzer",
            {CONTEXT_COMPONENT: "ScreenshotAnalyzer"}
        )
        self.error_handler = ErrorHandler.get_instance()
        
        # Initialize detector components with dependency injection
        self.text_detector = get_text_detector()
        self.button_detector = get_button_detector()
        self.error_detector = get_error_detector()
        self.interactive_element_detector = get_interactive_element_detector()
        self.image_preprocessor = get_image_preprocessor()
        self.geometry_utils = get_geometry_utils()
        
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
            # TODO

    @ErrorHandler.handle_errors(component="ScreenshotAnalyzer", phase="analysis", reraise=True)
    def analyze(self, image_path: str) -> ScreenshotAnalysisResult:
        """
        Analyze a screenshot using modular detector components.

        This is the main entry point for screenshot analysis, coordinating
        the specialized detection components and assembling the final result with
        comprehensive validation and error handling.

        Args:
            image_path: Path to the screenshot image

        Returns:
            ScreenshotAnalysisResult containing validated extracted information
            
        Raises:
            RVParsingError: If image cannot be loaded or analysis fails
            RVValidationError: If analysis result validation fails
        """
        start_time = time.time()
        self.logger.info(f"Analyzing screenshot: {image_path}")

        try:
            # Load and validate image
            original_image = cv2.imread(image_path)

            if original_image is None:
                raise RVParsingError(
                    f"Could not read image from path: {image_path}",
                    parser_type="ScreenshotAnalyzer"
                )

            # Create image dimensions
            dimensions = ImageDimensions(
                width=original_image.shape[1],
                height=original_image.shape[0]
            )

            # Preprocess images using component
            gray_image = self.image_preprocessor.preprocess_grayscale(original_image)
            binary_image = self.image_preprocessor.preprocess_binary(original_image)

            # Extract text elements using text detector component
            texts = self.text_detector.extract_text(gray_image)
            self.metrics["detected_texts"] += len(texts)

            # Detect button elements using button detector component
            buttons = self.button_detector.detect_buttons(binary_image, original_image, texts)
            self.metrics["detected_buttons"] += len(buttons)

            # Detect interactive elements using interactive element detector component
            interactive_elements = self.interactive_element_detector.detect_interactive_elements(
                binary_image, original_image, texts
            )
            self.metrics["detected_interactive_elements"] += len(interactive_elements)

            # Detect error indicators using error detector component
            error_indicators = self.error_detector.detect_errors(original_image, texts)
            self.metrics["detected_errors"] += len(error_indicators)

            # Calculate processing time
            processing_time = time.time() - start_time
            self.metrics["total_processing_time"] += processing_time

            # Create validated result using Pydantic model
            result = ScreenshotAnalysisResult(
                image_path=image_path,
                dimensions=dimensions,
                texts=texts,
                buttons=buttons,
                error_indicators=error_indicators,
                interactive_elements=interactive_elements,
                processing_time=processing_time,
                success=True,
                error_message=""
            )

            # Update success metrics
            self.metrics["processed_images"] += 1
            self.metrics["successful_analyses"] += 1
            
            self.log_processing_summary("screenshot", 1)
            self.logger.debug(f"Successfully analyzed screenshot with {result.total_elements} elements")
            
            return result

        except Exception as e:
            # Calculate processing time even for failed analyses
            processing_time = time.time() - start_time
            self.metrics["total_processing_time"] += processing_time
            self.metrics["failed_analyses"] += 1
            
            # Create error result
            try:
                error_result = ScreenshotAnalysisResult(
                    image_path=image_path,
                    dimensions=ImageDimensions(width=0, height=0),
                    processing_time=processing_time,
                    success=False,
                    error_message=str(e)
                )
                
                self.logger.error(f"Analysis failed for {image_path}: {str(e)}")
                return error_result
                
            except Exception as validation_error:
                # If we can't even create an error result, raise parsing error
                raise RVParsingError(
                    f"Screenshot analysis failed and could not create error result: {str(e)}",
                    parser_type="ScreenshotAnalyzer"
                ) from validation_error

    def extract_information(self) -> Dict[str, Any]:
        """
        Extract all information from the current screenshot with type-safe models.

        This method is used by the ScreenshotActionComplementor for integration
        with the action complement pipeline. It returns a dictionary with all
        extracted information converted to dictionaries for backward compatibility.

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

        # Convert Pydantic models to dictionaries for backward compatibility
        try:
            return {
                "texts": [text.model_dump() for text in self.current_result.texts],
                "buttons": [button.model_dump() for button in self.current_result.buttons],
                "error_indicators": [error.model_dump() for error in self.current_result.error_indicators],
                "interactive_elements": [element.model_dump() for element in self.current_result.interactive_elements]
            }
        except Exception as e:
            self.logger.error(f"Error converting models to dictionaries: {e}")
            return {
                "texts": [],
                "buttons": [],
                "error_indicators": [],
                "interactive_elements": []
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

    def get_detection_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive detection summary from all components.
        
        Returns:
            Dictionary with detection statistics from all detector components
        """
        if not self.current_result:
            return {"error": "No analysis result available"}
        
        try:
            summary = {
                "total_elements": self.current_result.total_elements,
                "processing_time": self.current_result.processing_time,
                "success": self.current_result.success
            }
            
            # Get component-specific summaries
            if self.current_result.texts:
                summary["text_summary"] = self.text_detector.get_text_classification_summary(
                    self.current_result.texts
                )
            
            if self.current_result.buttons:
                summary["button_summary"] = self.button_detector.get_button_detection_summary(
                    self.current_result.buttons
                )
            
            if self.current_result.error_indicators:
                summary["error_summary"] = self.error_detector.get_error_detection_summary(
                    self.current_result.error_indicators
                )
            
            if self.current_result.interactive_elements:
                summary["interactive_summary"] = self.interactive_element_detector.get_interactive_element_summary(
                    self.current_result.interactive_elements
                )
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating detection summary: {e}")
            return {"error": f"Summary generation failed: {str(e)}"}


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

        # Print detection summary
        print("\nDetection Summary:")
        summary = analyzer.get_detection_summary()
        for key, value in summary.items():
            print(f"  {key}: {value}")

        # Convert result to JSON-compatible dict and pretty print
        print("\nAnalysis Results:")
        print(result.to_json())

        print("\nError Indicators:")
        for error in result.error_indicators:
            print(f" - Error: {error.confidence} :: {error.text}")

    except Exception as e:
        print(f"Error processing screenshot: {e}")
        sys.exit(1)


if __name__ == '__main__':
    # image = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/001.png"
    image = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/009.png"
    main(image)