#!/usr/bin/env python3
"""
ErrorDetector integration tests using real screenshots.

These are characterization tests that document the current behavior of ErrorDetector
on real Android application screenshots. They validate detection accuracy on known
images and capture the expected false positive profile for colorful interfaces.

Test images are located in modules/rv-screen-parser/tests/images/.
"""

import cv2
import pytest
from pathlib import Path

from rv_screen_parser.screenshot.detectors.error_detector import ErrorDetector, get_error_detector
from rv_screen_parser.screenshot.detectors.text_detector import get_text_detector
from rv_screen_parser.screenshot.models import DetectedText, ErrorIndicator, ErrorType, DetectionMethod


IMAGES_DIR = Path(__file__).parent / "images"


@pytest.fixture
def detector():
    """Provide a fresh ErrorDetector instance for each test."""
    return ErrorDetector()


@pytest.fixture
def text_detector():
    """Provide a TextDetector instance for extracting texts from images."""
    return get_text_detector()


def _load_image_and_texts(image_path: Path, text_detector):
    """
    Load an image and extract texts using the TextDetector.

    Returns a tuple of (original_image, texts) ready for ErrorDetector.detect_errors().
    """
    original_image = cv2.imread(str(image_path))
    assert original_image is not None, f"Failed to load image: {image_path}"
    gray = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)
    texts = text_detector.extract_text(gray)
    return original_image, texts


class TestErrorDetectorIntegration:
    """Integration tests for ErrorDetector using real screenshots."""

    def test_cryptoapp_errors_detected(self, detector, text_detector):
        """
        Validate that ErrorDetector finds error indicators on a form with validation errors.

        The cryptoapp_009_errors.png screenshot contains two red circular error icons
        with white exclamation marks, positioned next to required form fields (a dropdown
        and a text input). These are bright red (~#FF0000) validation indicators that
        should be detected by color-based analysis.
        """
        image_path = IMAGES_DIR / "cryptoapp_009_errors.png"
        original_image, texts = _load_image_and_texts(image_path, text_detector)

        errors = detector.detect_errors(original_image, texts)

        # The image has two red validation icons; both should be detected
        assert len(errors) >= 1, (
            f"Expected >= 1 error indicator on form with validation errors, got {len(errors)}"
        )

        for error in errors:
            # All detected errors should use color-based detection (the icons are red circles)
            assert error.detection_method == DetectionMethod.COLOR, (
                f"Expected COLOR detection method, got {error.detection_method}"
            )
            # Confidence should be at least 0.7 for clear red validation icons
            assert error.confidence >= 0.7, (
                f"Expected confidence >= 0.7 for red validation icon, got {error.confidence}"
            )
            # Error type should be VISUAL_INDICATOR (color-based detection classifies them this way)
            assert error.error_type == ErrorType.VISUAL_INDICATOR, (
                f"Expected VISUAL_INDICATOR type, got {error.error_type}"
            )

    def test_cryptoapp_normal_no_errors(self, detector, text_detector):
        """
        Validate that ErrorDetector finds no errors on a normal form screen.

        The cryptoapp_005_normal.png screenshot shows the same form as
        cryptoapp_009_errors.png but without validation errors. The interface
        is clean with no red indicators, so zero errors should be detected.
        """
        image_path = IMAGES_DIR / "cryptoapp_005_normal.png"
        original_image, texts = _load_image_and_texts(image_path, text_detector)

        errors = detector.detect_errors(original_image, texts)

        assert len(errors) == 0, (
            f"Expected 0 error indicators on clean form screen, got {len(errors)}"
        )

    def test_cryptoapp_initial_no_errors(self, detector, text_detector):
        """
        Validate that ErrorDetector finds no errors on the app's initial menu screen.

        The cryptoapp_001_initial.png screenshot shows the main menu with three
        blue buttons (MESSAGE DIGEST, CIPHER, GENERATED) on a white background.
        No error indicators should be present.
        """
        image_path = IMAGES_DIR / "cryptoapp_001_initial.png"
        if not image_path.exists():
            pytest.skip(f"Test image not found: {image_path}")

        original_image, texts = _load_image_and_texts(image_path, text_detector)

        errors = detector.detect_errors(original_image, texts)

        assert len(errors) == 0, (
            f"Expected 0 error indicators on initial menu screen, got {len(errors)}"
        )

    def test_hourlyreminder_adaptive_threshold_suppresses_false_positives(self, detector, text_detector):
        """
        Validate that the adaptive confidence threshold suppresses false positives
        on a pink/magenta-themed alarm app.

        The hourlyreminder_003_settings.png screenshot has bright pink/magenta UI
        elements (time display, weekday selectors, floating action button). Without
        adaptive thresholding, the color-based detector would flag these as errors.
        The adaptive threshold detects game/alarm text keywords and raises the
        confidence threshold, correctly filtering out the pink UI elements.
        """
        image_path = IMAGES_DIR / "hourlyreminder_003_settings.png"
        if not image_path.exists():
            pytest.skip(f"Test image not found: {image_path}")

        original_image, texts = _load_image_and_texts(image_path, text_detector)

        errors = detector.detect_errors(original_image, texts)

        # The adaptive threshold correctly suppresses false positives from pink UI
        assert len(errors) == 0, (
            f"Expected 0 errors (adaptive threshold should suppress pink UI false positives), "
            f"got {len(errors)}"
        )

    def test_dnshero_known_false_positives(self, detector, text_detector):
        """
        Document false positive behavior on the DNS Hero app.

        The dnshero_002_main.png screenshot contains colored status indicators and
        bar charts that the color-based detector interprets as error indicators.
        This is a known false positive scenario: the app uses red/orange/yellow
        colors for data visualization, not for error reporting. The test documents
        the current detection count and verifies that some indicators have large
        bounding boxes (typical of bar chart regions being flagged).
        """
        image_path = IMAGES_DIR / "dnshero_002_main.png"
        if not image_path.exists():
            pytest.skip(f"Test image not found: {image_path}")

        original_image, texts = _load_image_and_texts(image_path, text_detector)

        errors = detector.detect_errors(original_image, texts)

        # DNS Hero produces multiple false positives from its colored data visualization
        assert len(errors) >= 3, (
            f"Expected >= 3 false positive indicators from colored charts, got {len(errors)}"
        )

        # Some false positives should have large bounding boxes (chart regions)
        large_indicators = [e for e in errors if e.width > 100 or e.height > 100]
        assert len(large_indicators) >= 1, (
            f"Expected >= 1 large indicator (chart region), got {len(large_indicators)}"
        )

        # All should be color-based detections
        for error in errors:
            assert error.detection_method == DetectionMethod.COLOR, (
                f"Expected COLOR detection method for data visualization false positive, "
                f"got {error.detection_method}"
            )

    def test_hex_adaptive_threshold_suppresses_false_positives(self, detector, text_detector):
        """
        Validate that the adaptive threshold suppresses false positives on a
        high-contrast hex strategy game.

        The hex_003_gameplay.png screenshot has large red and blue territory regions.
        The adaptive threshold detects the high color saturation and raises the
        confidence bar, correctly filtering out the game board colors.
        """
        image_path = IMAGES_DIR / "hex_003_gameplay.png"
        if not image_path.exists():
            pytest.skip(f"Test image not found: {image_path}")

        original_image, texts = _load_image_and_texts(image_path, text_detector)

        errors = detector.detect_errors(original_image, texts)

        # The adaptive threshold correctly suppresses false positives from game colors
        assert len(errors) == 0, (
            f"Expected 0 errors (adaptive threshold should suppress game color false positives), "
            f"got {len(errors)}"
        )

    def test_get_error_detector_factory(self):
        """Validate that get_error_detector() returns a usable singleton instance."""
        detector1 = get_error_detector()
        detector2 = get_error_detector()

        assert detector1 is detector2, "get_error_detector() should return the same instance"
        assert isinstance(detector1, ErrorDetector)

    def test_error_detection_summary_on_real_image(self, detector, text_detector):
        """
        Validate get_error_detection_summary() output on the cryptoapp error screenshot.

        This test exercises the summary method with real detection results to ensure
        it correctly aggregates error counts, types, and confidence statistics.
        """
        image_path = IMAGES_DIR / "cryptoapp_009_errors.png"
        original_image, texts = _load_image_and_texts(image_path, text_detector)

        errors = detector.detect_errors(original_image, texts)
        summary = detector.get_error_detection_summary(errors)

        assert isinstance(summary, dict)
        assert summary["total_errors"] == len(errors)
        assert summary["total_errors"] >= 1
        assert summary["average_confidence"] >= 0.7
        assert ErrorType.VISUAL_INDICATOR.value in summary["error_types"]
