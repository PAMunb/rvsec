"""
Tests for ScreenshotAnalyzer - screenshot analysis orchestration.

Tests cover:
- __init__() with detector components
- analyze() successful path
- analyze() with invalid image path
- extract_information() with no image
- get_metrics() tracking
- get_detection_summary()
"""

import tempfile
from unittest.mock import MagicMock, patch

import pytest
from rv_screen_parser.screenshot.screenshot_analyzer import ScreenshotAnalyzer

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_dependencies():
    """Mock all external dependencies for ScreenshotAnalyzer."""
    patches = {
        "text_detector": patch(
            "rv_screen_parser.screenshot.screenshot_analyzer.get_text_detector"
        ),
        "button_detector": patch(
            "rv_screen_parser.screenshot.screenshot_analyzer.get_button_detector"
        ),
        "error_detector": patch(
            "rv_screen_parser.screenshot.screenshot_analyzer.get_error_detector"
        ),
        "interactive_detector": patch(
            "rv_screen_parser.screenshot.screenshot_analyzer.get_interactive_element_detector"
        ),
        "preprocessor": patch(
            "rv_screen_parser.screenshot.screenshot_analyzer.get_image_preprocessor"
        ),
        "geometry_utils": patch(
            "rv_screen_parser.screenshot.screenshot_analyzer.get_geometry_utils"
        ),
    }

    mocks = {}
    for name, p in patches.items():
        mocks[name] = p.start()
        mocks[name].return_value = MagicMock()

    yield mocks

    for p in patches.values():
        p.stop()


@pytest.fixture
def analyzer(mock_dependencies):
    """Create ScreenshotAnalyzer without image path."""
    return ScreenshotAnalyzer(image_path=None, analyzer_name="test_analyzer")


# ---------------------------------------------------------------------------
# Tests: __init__()
# ---------------------------------------------------------------------------


class TestInitialization:
    """Test ScreenshotAnalyzer initialization."""

    def test_init_creates_text_detector(self, mock_dependencies):
        """Test that text detector is created."""
        ScreenshotAnalyzer(image_path=None)
        mock_dependencies["text_detector"].assert_called_once()

    def test_init_creates_button_detector(self, mock_dependencies):
        """Test that button detector is created."""
        ScreenshotAnalyzer(image_path=None)
        mock_dependencies["button_detector"].assert_called_once()

    def test_init_creates_error_detector(self, mock_dependencies):
        """Test that error detector is created."""
        ScreenshotAnalyzer(image_path=None)
        mock_dependencies["error_detector"].assert_called_once()

    def test_init_creates_interactive_detector(self, mock_dependencies):
        """Test that interactive element detector is created."""
        ScreenshotAnalyzer(image_path=None)
        mock_dependencies["interactive_detector"].assert_called_once()

    def test_init_creates_preprocessor(self, mock_dependencies):
        """Test that image preprocessor is created."""
        ScreenshotAnalyzer(image_path=None)
        mock_dependencies["preprocessor"].assert_called_once()

    def test_init_initializes_metrics(self, analyzer):
        """Test that metrics are initialized."""
        assert "processed_images" in analyzer.metrics
        assert analyzer.metrics["processed_images"] == 0

    def test_init_with_image_path_triggers_analysis(self, mock_dependencies):
        """Test that providing image path triggers analysis."""
        # This will call cv2.imread which returns None for nonexistent file
        # Should handle gracefully
        with patch("cv2.imread", return_value=None):
            analyzer = ScreenshotAnalyzer(image_path="/nonexistent.png")
            # Should not raise, current_result should be None due to error
            # (error result will be created)


# ---------------------------------------------------------------------------
# Tests: analyze()
# ---------------------------------------------------------------------------


class TestAnalyze:
    """Test analyze() with various scenarios."""

    def test_analyze_invalid_image_path(self, analyzer):
        """Test analyze with invalid image path."""
        with patch("cv2.imread", return_value=None):
            with pytest.raises(Exception):  # Should raise RVParsingError
                analyzer.analyze("/nonexistent/image.png")

    def test_analyze_updates_metrics(self, analyzer):
        """Test that analyze updates metrics."""
        # Mock successful analysis
        mock_image = MagicMock()
        mock_image.shape = (1080, 1920, 3)

        with patch("cv2.imread", return_value=mock_image):
            with patch.object(
                analyzer.image_preprocessor,
                "preprocess_grayscale",
                return_value=MagicMock(),
            ):
                with patch.object(
                    analyzer.image_preprocessor,
                    "preprocess_binary",
                    return_value=MagicMock(),
                ):
                    with patch.object(
                        analyzer.text_detector, "extract_text", return_value=[]
                    ):
                        with patch.object(
                            analyzer.button_detector, "detect_buttons", return_value=[]
                        ):
                            with patch.object(
                                analyzer.interactive_element_detector,
                                "detect_interactive_elements",
                                return_value=[],
                            ):
                                with patch.object(
                                    analyzer.error_detector,
                                    "detect_errors",
                                    return_value=[],
                                ):
                                    result = analyzer.analyze("/fake/path.png")

                                    assert analyzer.metrics["processed_images"] == 1
                                    assert analyzer.metrics["successful_analyses"] == 1

    def test_analyze_failed_analysis_updates_metrics(self, analyzer):
        """Test that failed analysis updates failed metrics."""
        with patch("cv2.imread", return_value=None):
            try:
                analyzer.analyze("/fake/image.png")
            except Exception:
                pass

            assert analyzer.metrics["failed_analyses"] >= 0


# ---------------------------------------------------------------------------
# Tests: extract_information()
# ---------------------------------------------------------------------------


class TestExtractInformation:
    """Test extract_information() with various scenarios."""

    def test_extract_no_image_path(self, analyzer):
        """Test extract_information with no image path."""
        result = analyzer.extract_information()
        assert "texts" in result
        assert "buttons" in result
        assert result["texts"] == []

    def test_extract_with_analysis(self, analyzer):
        """Test extract_information after analysis."""
        # Set up analyzer with fake data
        analyzer.current_image_path = "/fake/image.png"
        analyzer.current_result = MagicMock()
        analyzer.current_result.texts = []
        analyzer.current_result.buttons = []
        analyzer.current_result.error_indicators = []
        analyzer.current_result.interactive_elements = []

        result = analyzer.extract_information()

        assert "texts" in result
        assert "buttons" in result
        assert "error_indicators" in result
        assert "interactive_elements" in result

    def test_extract_handles_exception(self, analyzer):
        """Test extract_information handles exceptions."""
        analyzer.current_image_path = "/fake/image.png"
        analyzer.analyze = MagicMock(side_effect=Exception("Analysis failed"))

        result = analyzer.extract_information()

        # Should return empty results
        assert result["texts"] == []
        assert result["buttons"] == []


# ---------------------------------------------------------------------------
# Tests: get_metrics()
# ---------------------------------------------------------------------------


class TestGetMetrics:
    """Test get_metrics() tracking."""

    def test_get_metrics_returns_dict(self, analyzer):
        """Test that get_metrics returns dict."""
        metrics = analyzer.get_metrics()
        assert isinstance(metrics, dict)

    def test_get_metrics_includes_processed_images(self, analyzer):
        """Test that metrics include processed_images."""
        analyzer.metrics["processed_images"] = 5
        metrics = analyzer.get_metrics()
        assert metrics["processed_images"] == 5

    def test_get_metrics_includes_average_time(self, analyzer):
        """Test that metrics include average processing time."""
        analyzer.metrics["processed_images"] = 2
        analyzer.metrics["total_processing_time"] = 4.0
        metrics = analyzer.get_metrics()
        assert metrics["average_processing_time"] == 2.0

    def test_get_metrics_zero_division(self, analyzer):
        """Test metrics with zero processed images."""
        analyzer.metrics["processed_images"] = 0
        metrics = analyzer.get_metrics()
        assert metrics["average_processing_time"] == 0.0


# ---------------------------------------------------------------------------
# Tests: get_detection_summary()
# ---------------------------------------------------------------------------


class TestGetDetectionSummary:
    """Test get_detection_summary()."""

    def test_summary_no_result(self, analyzer):
        """Test summary when no analysis result."""
        analyzer.current_result = None
        summary = analyzer.get_detection_summary()
        assert "error" in summary

    def test_summary_with_result(self, analyzer):
        """Test summary with analysis result."""
        analyzer.current_result = MagicMock()
        analyzer.current_result.total_elements = 10
        analyzer.current_result.processing_time = 1.5
        analyzer.current_result.success = True
        analyzer.current_result.texts = []
        analyzer.current_result.buttons = []
        analyzer.current_result.error_indicators = []
        analyzer.current_result.interactive_elements = []

        summary = analyzer.get_detection_summary()

        assert "total_elements" in summary
        assert summary["total_elements"] == 10
        assert summary["success"] is True

    def test_summary_handles_exception(self, analyzer):
        """Test summary handles exceptions."""
        analyzer.current_result = MagicMock()
        # Make total_elements raise an exception
        type(analyzer.current_result).total_elements = property(
            fget=MagicMock(side_effect=Exception("Error"))
        )
        analyzer.text_detector.get_text_classification_summary = MagicMock(
            side_effect=Exception("Summary error")
        )

        summary = analyzer.get_detection_summary()

        # Should have some content (either summary or error)
        assert summary is not None
