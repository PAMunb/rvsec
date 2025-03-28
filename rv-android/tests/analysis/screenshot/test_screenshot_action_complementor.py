# tests/analysis/screenshot/test_screenshot_action_complementor.py
import os
import pytest
from unittest.mock import MagicMock, patch

from rvandroid.analysis.screenshot.screenshot_action_complementor import ScreenshotActionComplementor
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription, ScreenItem, ItemAction


class TestScreenshotActionComplementor:
    @pytest.fixture
    def sample_screen_description(self):
        """Create a sample screen description for testing."""
        # Create mock screen items
        items = [
            ScreenItem(
                view={
                    "class": "android.widget.EditText",
                    "resource_id": "input_field",
                    "bounds": [[100, 100], [300, 150]]
                },
                base_description="Input Field",
                actions=[
                    ItemAction(
                        id=1,
                        text="SET_TEXT",
                        event="TEXT_CHANGE",
                        target_view={"class": "android.widget.EditText"},
                        coordinates=(200, 125)
                    )
                ]
            )
        ]

        return ScreenDescription(
            activity="TestActivity",
            items=items
        )

    @pytest.fixture
    def sample_screenshot(self, tmp_path):
        """Create a sample screenshot for testing."""
        # Create a sample image for testing
        import cv2
        import numpy as np

        # Create a blank image
        image = np.zeros((400, 600, 3), dtype=np.uint8)

        # Add some sample elements
        cv2.rectangle(image, (50, 50), (150, 100), (0, 255, 0), -1)  # Green button
        cv2.rectangle(image, (200, 200), (300, 250), (0, 0, 255), -1)  # Red error indicator

        # Save the image
        screenshot_path = tmp_path / "screenshot.png"
        cv2.imwrite(str(screenshot_path), image)

        return str(screenshot_path)

    @patch('rvandroid.analysis.screenshot.screenshot_action_complementor.ScreenshotAnalyzer')
    def test_complement_screen_actions(self, mock_screenshot_analyzer, sample_screen_description, sample_screenshot):
        """Test complementing screen actions with screenshot analysis."""
        # Mock the screenshot analyzer to return predictable results
        mock_analyzer_instance = MagicMock()
        mock_analyzer_instance.extract_information.return_value = {
            'texts': [
                {
                    'text': 'OK',
                    'confidence': 90,
                    'bbox': {'x': 10, 'y': 10, 'width': 50, 'height': 20}
                }
            ],
            'buttons': [
                {
                    'x': 50,
                    'y': 50,
                    'width': 100,
                    'height': 50,
                    'area': 5000
                }
            ],
            'error_indicators': [
                {
                    'x': 200,
                    'y': 200,
                    'width': 100,
                    'height': 50,
                    'area': 5000,
                    'red_intensity': 200.0
                }
            ],
            'image_info': {
                'width': 600,
                'height': 400
            }
        }
        mock_screenshot_analyzer.return_value = mock_analyzer_instance

        # Create the complementor
        complementor = ScreenshotActionComplementor()

        # Complement screen actions
        enhanced_screen = complementor.complement_screen_actions(
            sample_screen_description,
            sample_screenshot
        )

        # Verify enhanced screen
        assert len(enhanced_screen.items) > len(sample_screen_description.items)

    # def test_button_text_detection(self, sample_screen_description):
    #     """Test detection of button-like text."""
    #     complementor = ScreenshotActionComplementor()
    #
    #     # Test button texts - exact matches
    #     button_texts = [
    #         "OK", "Submit", "Send", "Login", "Register",
    #         "Next", "Continue", "Yes", "No", "Cancel",
    #         "ok", "submit", "login", "register",
    #         "a", "ab", "abc"  # Short non-empty texts
    #     ]
    #
    #     non_button_texts = [
    #         "",  # Empty string
    #         "   ",  # Only whitespace
    #         "This is a very long description that cannot be a button",
    #         "Lorem ipsum dolor sit amet consectetur"
    #     ]
    #
    #     # Test button texts
    #     for text in button_texts:
    #         assert complementor._looks_like_button_text(text), f"Failed for text: '{text}'"
    #
    #     # Test non-button texts
    #     non_button_detection = {
    #         text: complementor._looks_like_button_text(text)
    #         for text in non_button_texts
    #     }
    #
    #     # Special handling for empty string to handle current implementation
    #     assert not non_button_detection[""], "Empty string should not be considered a button text"
    #
    #     # Remove empty string from further checking
    #     non_button_texts = [text for text in non_button_texts if text]
    #
    #     for text, is_button in non_button_detection.items():
    #         if text:  # Skip empty string which was already checked
    #             assert not is_button, f"Failed for text: '{text}'"

    def test_initialization(self, tmp_path):
        """Test initialization of ScreenshotActionComplementor."""
        complementor = ScreenshotActionComplementor(
            screenshot_dir=str(tmp_path),
            cache_size=5
        )

        assert complementor.screenshot_dir == str(tmp_path)
        assert complementor.cache_size == 5
        assert len(complementor.cache_keys) == 0
        assert len(complementor.analysis_cache) == 0

    def test_error_handling(self, sample_screen_description):
        """Test error handling when screenshot is invalid."""
        complementor = ScreenshotActionComplementor()

        # Patch the ScreenshotAnalyzer to raise an exception
        with patch(
                'rvandroid.analysis.screenshot.screenshot_action_complementor.ScreenshotAnalyzer') as mock_screenshot_analyzer:
            mock_screenshot_analyzer.side_effect = Exception("Test error")

            # Try with screenshot path
            result = complementor.complement_screen_actions(
                sample_screen_description,
                "/path/to/nonexistent/screenshot.png"
            )

            # Should return original screen description on error
            assert result == sample_screen_description