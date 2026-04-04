"""
Unit tests for VisualErrorDetector service.

Tests the 4-stage false-positive filtering pipeline that wraps
rv-screen-parser's ErrorDetector for use in rv-agent validation.

All tests use mocks — no real screenshots or cv2 processing.
"""

from unittest.mock import patch, MagicMock

from rv_agent.services.error_detection import VisualErrorDetector


def _make_indicator(x=100, y=500, width=52, height=51, confidence=0.80):
    """Create a mock ErrorIndicator with the given parameters."""
    indicator = MagicMock()
    indicator.x = x
    indicator.y = y
    indicator.width = width
    indicator.height = height
    indicator.confidence = confidence
    return indicator


class TestVisualErrorDetector:
    """Tests for VisualErrorDetector with 4-stage filtering."""

    @patch("rv_agent.services.error_detection.cv2")
    @patch("rv_agent.services.error_detection.ErrorDetector")
    def test_error_detected(self, mock_detector_cls, mock_cv2):
        """Two valid indicators in content area pass all filters."""
        # Arrange: cv2.imread returns a 1080x1920 image
        mock_image = MagicMock()
        mock_image.shape = (1920, 1080, 3)
        mock_cv2.imread.return_value = mock_image

        ind1 = _make_indicator(x=100, y=500, width=52, height=51, confidence=0.80)
        ind2 = _make_indicator(x=200, y=600, width=48, height=45, confidence=0.80)
        mock_detector_cls.return_value.detect_errors.return_value = [ind1, ind2]

        # Act
        detector = VisualErrorDetector()
        result = detector.detect("/fake/screenshot.png")

        # Assert
        assert result.detected is True
        assert len(result.error_indicators) == 2
        assert result.confidence == 0.80
        assert result.detection_method == "visual_color"
        assert result.filtered_by_size == 0
        assert result.filtered_by_region == 0
        assert result.filtered_by_count is False

    @patch("rv_agent.services.error_detection.cv2")
    @patch("rv_agent.services.error_detection.ErrorDetector")
    def test_no_error(self, mock_detector_cls, mock_cv2):
        """Empty indicator list results in detected=False."""
        mock_image = MagicMock()
        mock_image.shape = (1920, 1080, 3)
        mock_cv2.imread.return_value = mock_image
        mock_detector_cls.return_value.detect_errors.return_value = []

        detector = VisualErrorDetector()
        result = detector.detect("/fake/screenshot.png")

        assert result.detected is False
        assert result.error_indicators == []
        assert result.confidence == 0.0

    @patch("rv_agent.services.error_detection.cv2")
    @patch("rv_agent.services.error_detection.ErrorDetector")
    def test_missing_image(self, mock_detector_cls, mock_cv2):
        """cv2.imread returns None — graceful fallback."""
        mock_cv2.imread.return_value = None

        detector = VisualErrorDetector()
        result = detector.detect("/nonexistent/path.png")

        assert result.detected is False
        assert result.error_indicators == []
        assert result.confidence == 0.0
        # ErrorDetector.detect_errors should not be called
        mock_detector_cls.return_value.detect_errors.assert_not_called()

    @patch("rv_agent.services.error_detection.ErrorDetector", None)
    @patch("rv_agent.services.error_detection.cv2", None)
    def test_cv2_import_failure(self):
        """cv2 import failure results in detected=False, no exception."""
        detector = VisualErrorDetector()
        result = detector.detect("/fake/screenshot.png")

        assert result.detected is False
        assert result.error_indicators == []
        assert result.confidence == 0.0

    @patch("rv_agent.services.error_detection.cv2")
    @patch("rv_agent.services.error_detection.ErrorDetector")
    def test_confidence_filter(self, mock_detector_cls, mock_cv2):
        """Indicator with confidence 0.4 rejected by threshold 0.7."""
        mock_image = MagicMock()
        mock_image.shape = (1920, 1080, 3)
        mock_cv2.imread.return_value = mock_image

        low_conf = _make_indicator(confidence=0.4)
        mock_detector_cls.return_value.detect_errors.return_value = [low_conf]

        detector = VisualErrorDetector()
        result = detector.detect("/fake/screenshot.png", confidence_threshold=0.7)

        assert result.detected is False
        assert result.error_indicators == []
        assert result.confidence == 0.0

    @patch("rv_agent.services.error_detection.cv2")
    @patch("rv_agent.services.error_detection.ErrorDetector")
    def test_size_filter(self, mock_detector_cls, mock_cv2):
        """Indicator 150x150 rejected by max_indicator_size=80."""
        mock_image = MagicMock()
        mock_image.shape = (1920, 1080, 3)
        mock_cv2.imread.return_value = mock_image

        large = _make_indicator(width=150, height=150, confidence=0.85)
        mock_detector_cls.return_value.detect_errors.return_value = [large]

        detector = VisualErrorDetector()
        result = detector.detect("/fake/screenshot.png", max_indicator_size=80)

        assert result.detected is False
        assert result.error_indicators == []
        assert result.filtered_by_size == 1

    @patch("rv_agent.services.error_detection.cv2")
    @patch("rv_agent.services.error_detection.ErrorDetector")
    def test_region_filter_top(self, mock_detector_cls, mock_cv2):
        """Indicator at y=30 on 1920-height image rejected (top 5% = y < 96)."""
        mock_image = MagicMock()
        mock_image.shape = (1920, 1080, 3)
        mock_cv2.imread.return_value = mock_image

        top_bar = _make_indicator(y=30, confidence=0.85)
        mock_detector_cls.return_value.detect_errors.return_value = [top_bar]

        detector = VisualErrorDetector()
        result = detector.detect("/fake/screenshot.png")

        assert result.detected is False
        assert result.error_indicators == []
        assert result.filtered_by_region == 1

    @patch("rv_agent.services.error_detection.cv2")
    @patch("rv_agent.services.error_detection.ErrorDetector")
    def test_region_filter_bottom(self, mock_detector_cls, mock_cv2):
        """Indicator at y=1870 on 1920-height image rejected (bottom 6% = y > 1804.8)."""
        mock_image = MagicMock()
        mock_image.shape = (1920, 1080, 3)
        mock_cv2.imread.return_value = mock_image

        bottom_bar = _make_indicator(y=1870, confidence=0.85)
        mock_detector_cls.return_value.detect_errors.return_value = [bottom_bar]

        detector = VisualErrorDetector()
        result = detector.detect("/fake/screenshot.png")

        assert result.detected is False
        assert result.error_indicators == []
        assert result.filtered_by_region == 1

    @patch("rv_agent.services.error_detection.cv2")
    @patch("rv_agent.services.error_detection.ErrorDetector")
    def test_region_filter_pass(self, mock_detector_cls, mock_cv2):
        """Indicator at y=500 passes region filter (content area)."""
        mock_image = MagicMock()
        mock_image.shape = (1920, 1080, 3)
        mock_cv2.imread.return_value = mock_image

        content = _make_indicator(y=500, confidence=0.85)
        mock_detector_cls.return_value.detect_errors.return_value = [content]

        detector = VisualErrorDetector()
        result = detector.detect("/fake/screenshot.png")

        assert result.detected is True
        assert len(result.error_indicators) == 1
        assert result.filtered_by_region == 0

    @patch("rv_agent.services.error_detection.cv2")
    @patch("rv_agent.services.error_detection.ErrorDetector")
    def test_count_filter(self, mock_detector_cls, mock_cv2):
        """8 valid indicators rejected by max_indicator_count=5 (assumes themed UI)."""
        mock_image = MagicMock()
        mock_image.shape = (1920, 1080, 3)
        mock_cv2.imread.return_value = mock_image

        indicators = [
            _make_indicator(y=300 + i * 50, confidence=0.80) for i in range(8)
        ]
        mock_detector_cls.return_value.detect_errors.return_value = indicators

        detector = VisualErrorDetector()
        result = detector.detect("/fake/screenshot.png", max_indicator_count=5)

        assert result.detected is False
        assert result.error_indicators == []
        assert result.filtered_by_count is True

    @patch("rv_agent.services.error_detection.cv2")
    @patch("rv_agent.services.error_detection.ErrorDetector")
    def test_mixed_sizes(self, mock_detector_cls, mock_cv2):
        """3 small + 2 large indicators: 2 large rejected by size, 3 small pass."""
        mock_image = MagicMock()
        mock_image.shape = (1920, 1080, 3)
        mock_cv2.imread.return_value = mock_image

        small1 = _make_indicator(x=100, y=400, width=40, height=35, confidence=0.85)
        small2 = _make_indicator(x=200, y=500, width=50, height=45, confidence=0.80)
        small3 = _make_indicator(x=300, y=600, width=30, height=28, confidence=0.75)
        large1 = _make_indicator(x=400, y=700, width=120, height=50, confidence=0.90)
        large2 = _make_indicator(x=500, y=800, width=60, height=100, confidence=0.88)

        mock_detector_cls.return_value.detect_errors.return_value = [
            small1,
            small2,
            small3,
            large1,
            large2,
        ]

        detector = VisualErrorDetector()
        result = detector.detect("/fake/screenshot.png", max_indicator_size=80)

        assert result.detected is True
        assert len(result.error_indicators) == 3
        assert result.filtered_by_size == 2
        assert result.confidence == 0.85  # max of the 3 small ones
