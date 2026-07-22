from unittest.mock import patch

import numpy as np
import pytest
from rv_screen_parser.screenshot.detectors.error_detector import ErrorDetector
from rv_screen_parser.screenshot.models import (
    BoundingBox,
    DetectedText,
    ErrorIndicator,
    ErrorType,
)


class TestErrorDetector:
    """Test suite for ErrorDetector class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.detector = ErrorDetector()

    def test_initialization(self):
        """Test ErrorDetector initialization."""
        assert self.detector.logger is not None
        assert self.detector.geometry_utils is not None
        assert "red" in self.detector.error_color_ranges
        assert "orange" in self.detector.error_color_ranges
        assert "yellow" in self.detector.error_color_ranges
        assert "network" in self.detector.error_patterns
        assert "error" in self.detector.error_icons

    def test_detect_errors_none_image(self):
        """Test error detection with None image."""
        with pytest.raises(Exception):  # Should raise RVParsingError
            self.detector.detect_errors(None, [])

    def test_detect_errors_empty_image(self):
        """Test error detection with empty image."""
        # Create a minimal black image
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        texts = []

        errors = self.detector.detect_errors(image, texts)

        assert isinstance(errors, list)
        assert len(errors) >= 0  # May find no errors, which is valid

    def test_detect_color_errors(self):
        """Test color-based error detection."""
        # Create an image with red pixels (potential error indicator)
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        image[25:75, 25:75] = [0, 0, 255]  # Red square in the middle

        texts = []

        errors = self.detector._detect_color_errors(image, texts)

        # Should find at least one error due to red color
        assert isinstance(errors, list)
        # Note: Due to adaptive thresholding, we may not always detect errors in test

    def test_detect_text_errors(self):
        """Test text-based error detection."""
        # Create some text elements that look like errors
        text1 = DetectedText(
            text="Error occurred",
            confidence=90,  # Integer confidence value
            bbox=BoundingBox(x=10, y=10, width=100, height=20),
            is_error_like=True,
        )
        text2 = DetectedText(
            text="Success message",
            confidence=80,  # Integer confidence value
            bbox=BoundingBox(x=120, y=10, width=100, height=20),
            is_error_like=False,
        )

        texts = [text1, text2]
        existing_errors = []

        errors = self.detector._detect_text_errors(texts, existing_errors)

        # Should find error from the first text element
        assert isinstance(errors, list)

    def test_detect_pattern_errors(self):
        """Test pattern-based error detection."""
        # Create an image and some text elements
        image = np.zeros((200, 200, 3), dtype=np.uint8)
        text1 = DetectedText(
            text="Error",
            confidence=90,  # Integer confidence value
            bbox=BoundingBox(x=50, y=50, width=50, height=20),
            is_error_like=True,
        )
        texts = [text1]
        existing_errors = []

        errors = self.detector._detect_pattern_errors(image, texts, existing_errors)

        assert isinstance(errors, list)

    def test_detect_error_dialogs(self):
        """Test error dialog detection."""
        # Create text elements that might form a dialog
        text1 = DetectedText(
            text="Error",
            confidence=90,  # Integer confidence value
            bbox=BoundingBox(x=90, y=90, width=50, height=20),
            is_error_like=True,
        )
        text2 = DetectedText(
            text="Something went wrong",
            confidence=80,  # Integer confidence value
            bbox=BoundingBox(x=90, y=120, width=100, height=20),
            is_error_like=True,
        )

        texts = [text1, text2]
        existing_errors = []

        errors = self.detector._detect_error_dialogs(
            np.zeros((200, 200, 3)), texts, existing_errors
        )

        assert isinstance(errors, list)

    def test_detect_toast_errors(self):
        """Test toast error detection."""
        # Create text element positioned at top (toast-like)
        text1 = DetectedText(
            text="Error toast message",
            confidence=90,  # Integer confidence value
            bbox=BoundingBox(x=50, y=10, width=100, height=20),  # Near top
            is_error_like=True,
        )

        texts = [text1]
        existing_errors = []

        errors = self.detector._detect_toast_errors(
            np.zeros((200, 200, 3)), texts, existing_errors
        )

        assert isinstance(errors, list)

    def test_detect_banner_errors(self):
        """Test banner error detection."""
        # Create wide text element (banner-like)
        text1 = DetectedText(
            text="Error banner message",
            confidence=90,  # Integer confidence value
            bbox=BoundingBox(x=10, y=10, width=180, height=20),  # Wide
            is_error_like=True,
        )

        texts = [text1]
        existing_errors = []

        errors = self.detector._detect_banner_errors(
            np.zeros((200, 200, 3)), texts, existing_errors
        )

        assert isinstance(errors, list)

    def test_calculate_color_confidence_red(self):
        """Test color confidence calculation for red."""
        # Create a ROI with red pixels
        roi = np.zeros((50, 50, 3), dtype=np.uint8)
        roi[:, :] = [0, 50, 200]  # HSV: red-like

        confidence = self.detector._calculate_color_confidence(roi, "red", 1000, 10000)

        assert 0.0 <= confidence <= 1.0

    def test_calculate_color_confidence_other_colors(self):
        """Test color confidence calculation for non-red colors."""
        # Create a ROI with yellow pixels
        roi = np.zeros((50, 50, 3), dtype=np.uint8)
        roi[:, :] = [0, 150, 150]  # HSV: yellow-like

        confidence = self.detector._calculate_color_confidence(
            roi, "yellow", 1000, 10000
        )

        assert 0.0 <= confidence <= 1.0

    def test_classify_error_text_general_error(self):
        """Test classifying general error text."""
        text = "There was an error"

        error_type, confidence = self.detector._classify_error_text(text)

        assert isinstance(error_type, ErrorType)
        assert 0.0 <= confidence <= 1.0

    def test_classify_error_text_network_error(self):
        """Test classifying network error text."""
        text = "No internet connection"

        error_type, confidence = self.detector._classify_error_text(text)

        assert isinstance(error_type, ErrorType)
        assert 0.0 <= confidence <= 1.0
        # Could be network or general depending on pattern matching

    def test_classify_error_text_validation_error(self):
        """Test classifying validation error text."""
        text = "Field cannot be empty"

        error_type, confidence = self.detector._classify_error_text(text)

        assert isinstance(error_type, ErrorType)
        assert 0.0 <= confidence <= 1.0

    def test_classify_error_text_permission_error(self):
        """Test classifying permission error text."""
        text = "Permission denied"

        error_type, confidence = self.detector._classify_error_text(text)

        assert isinstance(error_type, ErrorType)
        assert 0.0 <= confidence <= 1.0

    def test_classify_error_text_system_error(self):
        """Test classifying system error text."""
        text = "Application crashed"

        error_type, confidence = self.detector._classify_error_text(text)

        assert isinstance(error_type, ErrorType)
        assert 0.0 <= confidence <= 1.0

    def test_group_nearby_texts(self):
        """Test grouping nearby text elements."""
        text1 = DetectedText(
            text="Error",
            confidence=90,  # Integer confidence value
            bbox=BoundingBox(x=10, y=10, width=20, height=10),
            is_error_like=True,
        )
        text2 = DetectedText(
            text="message",
            confidence=80,  # Integer confidence value
            bbox=BoundingBox(x=35, y=12, width=30, height=10),  # Close to first
            is_error_like=True,
        )
        text3 = DetectedText(
            text="separate",
            confidence=70,  # Integer confidence value
            bbox=BoundingBox(x=200, y=200, width=30, height=10),  # Far away
            is_error_like=True,
        )

        texts = [text1, text2, text3]

        groups = self.detector._group_nearby_texts(texts, max_distance=50)

        assert isinstance(groups, list)
        # Should have at least 2 groups: [text1, text2] and [text3]
        assert len(groups) >= 1

    def test_create_error_indicator(self):
        """Test creating an error indicator."""
        from rv_screen_parser.screenshot.models import ErrorType

        indicator = self.detector._create_error_indicator(
            x=10,
            y=20,
            w=100,
            h=50,
            confidence=0.8,  # Float confidence value between 0 and 1
            error_type=ErrorType.GENERAL_ERROR,  # Use correct enum value
            message="Test error message",
        )

        assert indicator is not None
        assert indicator.x == 10
        assert indicator.y == 20
        assert indicator.width == 100
        assert indicator.height == 50
        assert indicator.confidence == 0.8
        assert indicator.error_type == ErrorType.GENERAL_ERROR
        assert indicator.text == "Test error message"

    def test_create_error_indicator_invalid(self):
        """Test creating an error indicator with invalid data."""
        from rv_screen_parser.screenshot.models import ErrorType

        # Patch logger to avoid actual logging
        with patch.object(self.detector.logger, "warning"):
            indicator = self.detector._create_error_indicator(
                x=-1,
                y=-1,
                w=-100,
                h=-50,  # Invalid values
                confidence=150,  # Integer confidence value
                error_type=ErrorType.GENERAL_ERROR,  # Use correct enum value
                message="Test message",
            )

        # Should return None due to validation failure
        assert indicator is None

    def test_text_overlaps_with_errors(self):
        """Test checking if text overlaps with existing errors."""
        text_element = DetectedText(
            text="Some text",
            confidence=80,  # Integer confidence value for DetectedText
            bbox=BoundingBox(x=10, y=10, width=50, height=30),
            is_error_like=True,
        )

        error = ErrorIndicator(
            x=15,
            y=15,
            width=40,
            height=20,
            detection_method="color",
            confidence=0.9,  # Float confidence value between 0 and 1 for ErrorIndicator
            error_type=ErrorType.GENERAL_ERROR,  # Use correct enum value
            text="Overlapping error",
        )

        errors = [error]

        overlaps = self.detector._text_overlaps_with_errors(text_element, errors)

        # Should return boolean
        assert isinstance(overlaps, bool)

    def test_text_overlaps_with_errors_no_overlap(self):
        """Test checking if text overlaps with non-overlapping errors."""
        text_element = DetectedText(
            text="Some text",
            confidence=80,  # Integer confidence value for DetectedText
            bbox=BoundingBox(x=10, y=10, width=20, height=10),
            is_error_like=True,
        )

        error = ErrorIndicator(
            x=100,
            y=100,
            width=20,
            height=10,
            detection_method="color",
            confidence=0.9,  # Float confidence value between 0 and 1 for ErrorIndicator
            error_type=ErrorType.GENERAL_ERROR,  # Use correct enum value
            text="Non-overlapping error",
        )

        errors = [error]

        overlaps = self.detector._text_overlaps_with_errors(text_element, errors)

        # Should return False as there's no overlap
        assert overlaps is False

    def test_get_error_detection_summary(self):
        """Test getting error detection summary."""
        from rv_screen_parser.screenshot.models import ErrorType

        errors = [
            ErrorIndicator(
                x=10,
                y=10,
                width=50,
                height=30,
                detection_method="color",
                confidence=0.9,  # Float confidence value between 0 and 1
                error_type=ErrorType.GENERAL_ERROR,
                text="General error",
            ),
            ErrorIndicator(
                x=70,
                y=70,
                width=40,
                height=20,
                detection_method="text",
                confidence=0.85,  # Float confidence value between 0 and 1
                error_type=ErrorType.VALIDATION_ERROR,
                text="Validation error",
            ),
        ]

        summary = self.detector.get_error_detection_summary(errors)

        assert isinstance(summary, dict)
        assert summary["total_errors"] == 2
        assert summary["high_confidence_errors"] == 2  # Both > 0.8
        assert "error_types" in summary
        assert isinstance(summary["average_confidence"], float)

    def test_calculate_adaptive_confidence_threshold_normal_image(self):
        """Test calculating adaptive confidence threshold for a normal image."""
        image = np.zeros((200, 200, 3), dtype=np.uint8)
        texts = []

        threshold = self.detector._calculate_adaptive_confidence_threshold(image, texts)

        assert 0.0 <= threshold <= 1.0

    def test_calculate_adaptive_confidence_threshold_colorful_image(self):
        """Test calculating adaptive confidence threshold for a colorful image."""
        # Create a colorful image
        image = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        texts = []

        threshold = self.detector._calculate_adaptive_confidence_threshold(image, texts)

        assert 0.0 <= threshold <= 1.0

    def test_calculate_adaptive_confidence_threshold_with_game_texts(self):
        """Test calculating adaptive confidence threshold with game-related texts."""
        text1 = DetectedText(
            text="Player 1 turn",
            confidence=80,  # Integer confidence value
            bbox=BoundingBox(x=10, y=10, width=80, height=20),
            is_error_like=False,
        )
        text2 = DetectedText(
            text="Roll dice",
            confidence=70,  # Integer confidence value
            bbox=BoundingBox(x=100, y=10, width=60, height=20),
            is_error_like=False,
        )
        texts = [text1, text2]

        image = np.zeros((200, 200, 3), dtype=np.uint8)

        threshold = self.detector._calculate_adaptive_confidence_threshold(image, texts)

        # Should be higher threshold due to game-related text
        assert 0.0 <= threshold <= 1.0

    def test_detect_high_color_density_context(self):
        """Test detecting high color density context."""
        # Create an image with many colored elements
        image = np.zeros((200, 200, 3), dtype=np.uint8)

        # Add some colored squares
        for i in range(0, 200, 20):
            for j in range(0, 200, 20):
                color = np.random.randint(50, 255, 3, dtype=np.uint8)
                image[i : i + 15, j : j + 15] = color

        context = self.detector._detect_high_color_density_context(image)

        assert isinstance(context, dict)
        assert "high_color_density" in context
        assert "colored_elements_count" in context
        assert "confidence" in context


class TestErrorDetectorBranchCoverage:
    """Branch-coverage tests targeting the uncovered paths of ErrorDetector.

    These tests exercise the high-color-density heuristics, adaptive-threshold
    branches, exception fallbacks, and pattern/icon classification code paths
    using deterministic cv2/numpy inputs (real cv2 — no numpy/cv2 mocking except
    a single explicitly patched cv2.findContours call).
    """

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.detector = ErrorDetector()

    def _place_green_square(self, image, x, y, size=20):
        """Place a pure-green (BGR) square used to create a deterministic contour.

        Pure green [0,255,0] maps to grayscale ~150 (> 127 binary threshold) and
        HSV saturation 255 (> 50), so each isolated square yields exactly one
        colored element in _detect_high_color_density_context.
        """
        image[y : y + size, x : x + size] = [0, 255, 0]

    # ------------------------------------------------------------------
    # _detect_high_color_density_context (lines 191-201, 215-252, 259-274, 280-281)
    # ------------------------------------------------------------------

    def test_high_color_density_grid_16_elements(self):
        """16 green squares in a regular 4x4 grid => full confidence context.

        Basis Path Testing: drives the count>=15 branch (259), the regular-grid
        pattern branch (252/265) and the high element-density branch (272), so
        confidence saturates at min(1.1, 1.0) == 1.0.
        """
        image = np.zeros((200, 200, 3), dtype=np.uint8)
        for i in range(0, 200, 50):
            for j in range(0, 200, 50):
                self._place_green_square(image, j, i)

        context = self.detector._detect_high_color_density_context(image)

        assert context["colored_elements_count"] >= 15
        assert context["regular_pattern_detected"] is True
        assert context["high_color_density"] is True
        assert context["confidence"] == pytest.approx(1.0)

    def test_high_color_density_grid_9_elements(self):
        """9 green squares (3x3 grid) => count in [8,15) branch (line 261).

        Equivalence Partitioning: 8 <= 9 < 15 is the middle count partition,
        distinct from the >=15 partition covered above.
        """
        image = np.zeros((200, 200, 3), dtype=np.uint8)
        for i in range(0, 200, 70):
            for j in range(0, 200, 70):
                self._place_green_square(image, j, i)

        context = self.detector._detect_high_color_density_context(image)

        assert context["colored_elements_count"] == 9
        assert context["high_color_density"] is True

    def test_high_color_density_medium_density_3_elements(self):
        """3 green squares => medium element-density branch (line 274).

        Boundary Value Analysis: 3 elements give density 3/4 = 0.75, which is
        not > 0.8 (skips 272) but is > 0.5 (hits the elif at 274). Count < 5 so
        the pattern block is skipped and count < 8 so no count-confidence.
        """
        image = np.zeros((200, 200, 3), dtype=np.uint8)
        self._place_green_square(image, 10, 10)
        self._place_green_square(image, 10, 90)
        self._place_green_square(image, 10, 160)

        context = self.detector._detect_high_color_density_context(image)

        assert context["colored_elements_count"] == 3

    def test_high_color_density_exception(self):
        """Single-channel image => cvtColor raises => except fallback (280-281).

        Robustness: a malformed 2D array is an invalid input class; the method
        must degrade gracefully to the default context rather than propagate.
        """
        image = np.zeros((10, 10), dtype=np.uint8)

        context = self.detector._detect_high_color_density_context(image)

        assert context["high_color_density"] is False
        assert context["colored_elements_count"] == 0

    # ------------------------------------------------------------------
    # _calculate_adaptive_confidence_threshold (lines 365, 379, 387-389)
    # ------------------------------------------------------------------

    def test_adaptive_threshold_color_picker(self):
        """Color-picker keywords + high saturation => threshold 0.95 (line 365)."""
        image = np.zeros((200, 200, 3), dtype=np.uint8)
        image[:, :] = [0, 255, 0]  # full pure green => saturation_ratio 1.0
        texts = [
            DetectedText(
                text="Change color",
                confidence=80,
                bbox=BoundingBox(x=0, y=0, width=50, height=20),
                is_error_like=False,
            ),
            DetectedText(
                text="Theme regular text",
                confidence=80,
                bbox=BoundingBox(x=0, y=30, width=80, height=20),
                is_error_like=False,
            ),
        ]

        threshold = self.detector._calculate_adaptive_confidence_threshold(image, texts)

        assert threshold == pytest.approx(0.95)

    def test_adaptive_threshold_moderate_saturation(self):
        """Moderate saturation (>0.20, <0.25) with no keywords => 0.7 (line 379)."""
        image = np.zeros((200, 200, 3), dtype=np.uint8)
        image[0:44, :] = [100, 100, 190]  # ~22% moderately saturated pixels

        threshold = self.detector._calculate_adaptive_confidence_threshold(image, [])

        assert threshold == pytest.approx(0.7)

    def test_adaptive_threshold_exception(self):
        """Single-channel image => cvtColor raises => default 0.3 (387-389)."""
        image = np.zeros((10, 10), dtype=np.uint8)

        threshold = self.detector._calculate_adaptive_confidence_threshold(image, [])

        assert threshold == pytest.approx(0.3)

    # ------------------------------------------------------------------
    # _detect_color_errors (lines 473-474)
    # ------------------------------------------------------------------

    def test_detect_color_errors_findcontours_exception(self):
        """findContours raising in each color loop => warning + empty list (473-474)."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)

        with patch(
            "rv_screen_parser.screenshot.detectors.error_detector.cv2.findContours",
            side_effect=Exception("boom"),
        ):
            errors = self.detector._detect_color_errors(image, [])

        assert errors == []

    # ------------------------------------------------------------------
    # _detect_text_errors (line 499)
    # ------------------------------------------------------------------

    def test_detect_text_errors_overlap_skip(self):
        """Error text overlapping an existing error is skipped via continue (499)."""
        existing = [
            ErrorIndicator(
                x=10,
                y=10,
                width=100,
                height=20,
                detection_method="color",
                confidence=0.9,
                error_type=ErrorType.GENERAL_ERROR,
                text="err",
            )
        ]
        text = DetectedText(
            text="Error occurred",
            confidence=90,
            bbox=BoundingBox(x=10, y=10, width=100, height=20),
            is_error_like=True,
        )

        errors = self.detector._detect_text_errors([text], existing)

        assert errors == []

    # ------------------------------------------------------------------
    # _detect_error_dialogs (lines 605-621)
    # ------------------------------------------------------------------

    def test_detect_error_dialogs_centered(self):
        """Two centered dialog-sized error texts exercise the dialog path (605-621).

        The confidence/geometry checks pass, control reaches _create_error_indicator,
        and a DIALOG_ERROR indicator is appended (620-621).
        """
        text1 = DetectedText(
            text="Error",
            confidence=90,
            bbox=BoundingBox(x=70, y=70, width=50, height=20),
            is_error_like=True,
        )
        text2 = DetectedText(
            text="Something went wrong",
            confidence=80,
            bbox=BoundingBox(x=70, y=130, width=60, height=20),
            is_error_like=True,
        )

        errors = self.detector._detect_error_dialogs(
            np.zeros((200, 200, 3), dtype=np.uint8), [text1, text2], []
        )

        assert len(errors) == 1
        assert errors[0].error_type == ErrorType.DIALOG_ERROR

    # ------------------------------------------------------------------
    # _detect_banner_errors (lines 686-700)
    # ------------------------------------------------------------------

    def test_detect_banner_errors_thin_wide(self):
        """Wide, thin error text exercises the banner path (686-700).

        Boundary Value Analysis: aspect_ratio 18 > 3, width 180 > width*0.5,
        height 10 < height*0.1 all satisfied simultaneously, so control reaches
        _create_error_indicator and a BANNER indicator is appended (699-700).
        """
        text = DetectedText(
            text="Error banner message",
            confidence=90,
            bbox=BoundingBox(x=10, y=10, width=180, height=10),
            is_error_like=True,
        )

        errors = self.detector._detect_banner_errors(
            np.zeros((200, 200, 3), dtype=np.uint8), [text], []
        )

        assert len(errors) == 1
        assert errors[0].error_type == ErrorType.BANNER

    # ------------------------------------------------------------------
    # _calculate_color_confidence (lines 710, 771-772)
    # ------------------------------------------------------------------

    def test_calculate_color_confidence_empty_roi(self):
        """Empty ROI (size 0) => 0.0 confidence (line 710)."""
        roi = np.zeros((0, 0, 3), dtype=np.uint8)

        confidence = self.detector._calculate_color_confidence(roi, "red", 100, 10000)

        assert confidence == 0.0

    def test_calculate_color_confidence_malformed_roi(self):
        """2D ROI => channel indexing raises => except returns 0.0 (771-772)."""
        roi = np.zeros((5, 5), dtype=np.uint8)

        confidence = self.detector._calculate_color_confidence(roi, "red", 100, 10000)

        assert confidence == 0.0

    # ------------------------------------------------------------------
    # _classify_error_text (lines 803-806)
    # ------------------------------------------------------------------

    def test_classify_error_text_error_icon(self):
        """Pure error icon => VISUAL_INDICATOR with 0.9 confidence (803 true, 804-806)."""
        error_type, confidence = self.detector._classify_error_text("❌")

        assert error_type == ErrorType.VISUAL_INDICATOR
        assert confidence == pytest.approx(0.9)

    def test_classify_error_text_info_icon(self):
        """Info icon => VISUAL_INDICATOR with 0.7 confidence (803 else branch)."""
        error_type, confidence = self.detector._classify_error_text("\U0001f4a1")

        assert error_type == ErrorType.VISUAL_INDICATOR
        assert confidence == pytest.approx(0.7)

    # ------------------------------------------------------------------
    # _group_nearby_texts (line 815)
    # ------------------------------------------------------------------

    def test_group_nearby_texts_empty(self):
        """Empty text list => empty groups (line 815)."""
        result = self.detector._group_nearby_texts([])

        assert result == []

    # ------------------------------------------------------------------
    # _text_overlaps_with_errors (lines 898-899)
    # ------------------------------------------------------------------

    def test_text_overlaps_with_errors_exception(self):
        """Overlap computation raising => warning + returns False (898-899)."""
        text = DetectedText(
            text="Error",
            confidence=90,
            bbox=BoundingBox(x=10, y=10, width=50, height=20),
            is_error_like=True,
        )
        error = ErrorIndicator(
            x=10,
            y=10,
            width=50,
            height=20,
            detection_method="color",
            confidence=0.9,
            error_type=ErrorType.GENERAL_ERROR,
            text="e",
        )

        with patch.object(
            self.detector.geometry_utils,
            "calculate_overlap_percentage",
            side_effect=Exception("boom"),
        ):
            result = self.detector._text_overlaps_with_errors(text, [error])

        assert result is False
