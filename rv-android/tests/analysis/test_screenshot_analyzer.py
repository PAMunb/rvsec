# tests/analysis/test_screenshot_analyzer.py
import os
import pytest
import numpy as np
import cv2
from PIL import Image
from unittest.mock import patch, MagicMock

from rvandroid.analysis.screenshot_analyzer import ScreenshotAnalyzer


class TestScreenshotAnalyzer:
    @pytest.fixture
    def sample_image(self, tmp_path):
        """Create a sample test image."""
        # Create a simple test image
        test_image_path = tmp_path / "test_screenshot.png"

        # Create a numpy array representing an image
        test_image = np.zeros((200, 300, 3), dtype=np.uint8)

        # Add some colored rectangles to simulate UI elements
        cv2.rectangle(test_image, (50, 50), (100, 100), (0, 255, 0), -1)  # Green button
        cv2.rectangle(test_image, (150, 150), (250, 180), (0, 0, 255), -1)  # Red error indicator

        # Add some text-like regions
        cv2.putText(test_image, "Test", (10, 20), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (255, 255, 255), 2)

        # Save the image
        cv2.imwrite(str(test_image_path), test_image)

        return str(test_image_path)

    def test_screenshot_analyzer_initialization(self, sample_image):
        """Test initialization of ScreenshotAnalyzer."""
        analyzer = ScreenshotAnalyzer(sample_image)

        assert analyzer.original_image is not None
        assert analyzer.gray_image is not None
        assert analyzer.binary_image is not None

        # Check image dimensions
        assert analyzer.original_image.shape[0] > 0
        assert analyzer.original_image.shape[1] > 0

    def test_preprocess_methods(self, sample_image):
        """Test image preprocessing methods."""
        analyzer = ScreenshotAnalyzer(sample_image)

        # Test grayscale conversion
        assert len(analyzer.gray_image.shape) == 2  # Grayscale images are 2D

        # Test binary image
        assert len(analyzer.binary_image.shape) == 2
        assert np.array_equal(
            np.unique(analyzer.binary_image),
            np.array([0, 255])  # Binary images should only have 0 and 255
        )

    def test_extract_text(self, sample_image):
        """Test text extraction method."""
        analyzer = ScreenshotAnalyzer(sample_image)

        # Mock pytesseract to return predictable results
        with patch('pytesseract.image_to_data') as mock_tesseract:
            mock_tesseract.return_value = {
                'text': ['Test', 'Button'],
                'conf': [90, 85],
                'left': [10, 50],
                'top': [20, 50],
                'width': [50, 70],
                'height': [20, 30]
            }

            texts = analyzer.extract_text()

            assert len(texts) > 0
            for text_info in texts:
                assert 'text' in text_info
                assert 'confidence' in text_info
                assert 'bbox' in text_info

    def test_detect_buttons(self, sample_image):
        """Test button detection method."""
        analyzer = ScreenshotAnalyzer(sample_image)

        buttons = analyzer.detect_buttons()

        assert len(buttons) > 0
        for button in buttons:
            assert 'x' in button
            assert 'y' in button
            assert 'width' in button
            assert 'height' in button
            assert 'area' in button

    def test_detect_error_indicators(self, sample_image):
        """Test error indicator detection method."""
        analyzer = ScreenshotAnalyzer(sample_image)

        error_indicators = analyzer.detect_error_indicators()

        assert len(error_indicators) > 0
        for indicator in error_indicators:
            assert 'x' in indicator
            assert 'y' in indicator
            assert 'width' in indicator
            assert 'height' in indicator
            assert 'area' in indicator
            assert 'red_intensity' in indicator

    def test_extract_information(self, sample_image):
        """Test comprehensive information extraction."""
        analyzer = ScreenshotAnalyzer(sample_image)

        results = analyzer.extract_information()

        assert 'texts' in results
        assert 'buttons' in results
        assert 'error_indicators' in results
        assert 'image_info' in results

        assert 'width' in results['image_info']
        assert 'height' in results['image_info']

    def test_invalid_image_path(self):
        """Test initialization with an invalid image path."""
        with pytest.raises(ValueError, match="Could not read image"):
            ScreenshotAnalyzer("/path/to/nonexistent/image.png")

    @patch('pytesseract.image_to_data')
    def test_text_extraction_error_handling(self, mock_tesseract, sample_image):
        """Test error handling during text extraction."""
        analyzer = ScreenshotAnalyzer(sample_image)

        # Simulate an error in pytesseract
        mock_tesseract.side_effect = Exception("Tesseract error")

        # Should not raise an exception, but return an empty list
        texts = analyzer.extract_text()
        assert len(texts) == 0

    def test_image_with_no_elements(self, tmp_path):
        """Test analysis of an image with no detectable elements."""
        # Create a blank image
        blank_image_path = tmp_path / "blank.png"
        blank_image = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.imwrite(str(blank_image_path), blank_image)

        analyzer = ScreenshotAnalyzer(str(blank_image_path))

        results = analyzer.extract_information()

        assert len(results['texts']) == 0
        assert len(results['buttons']) == 0
        assert len(results['error_indicators']) == 0
