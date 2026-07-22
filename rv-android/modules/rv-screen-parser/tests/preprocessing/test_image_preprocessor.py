"""
Tests for ImagePreprocessor - screenshot image preprocessing operations.

Tests cover:
- preprocess_grayscale() with histogram equalization
- preprocess_binary() with adaptive thresholding
- preprocess_for_edge_detection() with Canny
- reduce_noise() with non-local means
- enhance_contrast() with alpha/beta control
- validate_image() with various invalid inputs
- Global singleton access
"""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from rv_android_core.util.error.exceptions import RVParsingError
from rv_screen_parser.screenshot.preprocessing.image_preprocessor import (
    ImagePreprocessor,
    get_image_preprocessor,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def preprocessor():
    """Create ImagePreprocessor instance."""
    return ImagePreprocessor()


@pytest.fixture
def sample_color_image():
    """Create a sample color image (100x100x3)."""
    return np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)


@pytest.fixture
def sample_grayscale_image():
    """Create a sample grayscale image (100x100)."""
    return np.random.randint(0, 255, (100, 100), dtype=np.uint8)


# ---------------------------------------------------------------------------
# Tests: preprocess_grayscale()
# ---------------------------------------------------------------------------


class TestPreprocessGrayscale:
    """Test preprocess_grayscale() with histogram equalization."""

    def test_grayscale_converts_color_image(self, preprocessor, sample_color_image):
        """Test that color image is converted to grayscale."""
        result = preprocessor.preprocess_grayscale(sample_color_image)
        assert len(result.shape) == 2  # Grayscale

    def test_grayscale_preserves_dimensions(self, preprocessor, sample_color_image):
        """Test that grayscale preserves width/height."""
        result = preprocessor.preprocess_grayscale(sample_color_image)
        assert result.shape[0] == 100
        assert result.shape[1] == 100

    def test_grayscale_returns_grayscale_as_is(
        self, preprocessor, sample_grayscale_image
    ):
        """Test that already grayscale image is returned with warning."""
        result = preprocessor.preprocess_grayscale(sample_grayscale_image)
        assert len(result.shape) == 2

    def test_grayscale_raises_on_null(self, preprocessor):
        """Test that null image raises RVParsingError."""
        with pytest.raises(RVParsingError, match="Cannot process null image"):
            preprocessor.preprocess_grayscale(None)


# ---------------------------------------------------------------------------
# Tests: preprocess_binary()
# ---------------------------------------------------------------------------


class TestPreprocessBinary:
    """Test preprocess_binary() with adaptive thresholding."""

    def test_binary_converts_color_image(self, preprocessor, sample_color_image):
        """Test that color image is converted to binary."""
        result = preprocessor.preprocess_binary(sample_color_image)
        assert len(result.shape) == 2  # Binary is 2D

    def test_binary_preserves_dimensions(self, preprocessor, sample_color_image):
        """Test that binary preserves width/height."""
        result = preprocessor.preprocess_binary(sample_color_image)
        assert result.shape[0] == 100
        assert result.shape[1] == 100

    def test_binary_with_grayscale_input(self, preprocessor, sample_grayscale_image):
        """Test binary preprocessing with grayscale input."""
        result = preprocessor.preprocess_binary(sample_grayscale_image)
        assert len(result.shape) == 2

    def test_binary_raises_on_null(self, preprocessor):
        """Test that null image raises RVParsingError."""
        with pytest.raises(RVParsingError, match="Cannot process null image"):
            preprocessor.preprocess_binary(None)


# ---------------------------------------------------------------------------
# Tests: preprocess_for_edge_detection()
# ---------------------------------------------------------------------------


class TestPreprocessForEdgeDetection:
    """Test preprocess_for_edge_detection() with Canny."""

    def test_edge_detection_returns_edges(self, preprocessor, sample_color_image):
        """Test that edge detection returns edge image."""
        result = preprocessor.preprocess_for_edge_detection(sample_color_image)
        assert isinstance(result, np.ndarray)

    def test_edge_detection_with_custom_thresholds(
        self, preprocessor, sample_color_image
    ):
        """Test edge detection with custom thresholds."""
        result = preprocessor.preprocess_for_edge_detection(
            sample_color_image, low_threshold=30, high_threshold=100
        )
        assert isinstance(result, np.ndarray)

    def test_edge_detection_with_grayscale(self, preprocessor, sample_grayscale_image):
        """Test edge detection with grayscale input."""
        result = preprocessor.preprocess_for_edge_detection(sample_grayscale_image)
        assert isinstance(result, np.ndarray)

    def test_edge_detection_handles_exception(self, preprocessor):
        """Test edge detection handles exceptions gracefully (returns None via ErrorHandler)."""
        # ErrorHandler catches the exception and returns None
        result = preprocessor.preprocess_for_edge_detection("invalid")
        assert result is None


# ---------------------------------------------------------------------------
# Tests: reduce_noise()
# ---------------------------------------------------------------------------


class TestReduceNoise:
    """Test reduce_noise() with non-local means."""

    def test_reduce_noise_color_image(self, preprocessor, sample_color_image):
        """Test noise reduction on color image."""
        result = preprocessor.reduce_noise(sample_color_image)
        assert result.shape == sample_color_image.shape

    def test_reduce_noise_grayscale(self, preprocessor, sample_grayscale_image):
        """Test noise reduction on grayscale image."""
        result = preprocessor.reduce_noise(sample_grayscale_image)
        assert result.shape == sample_grayscale_image.shape

    def test_reduce_noise_custom_kernel(self, preprocessor, sample_color_image):
        """Test noise reduction with custom kernel size."""
        result = preprocessor.reduce_noise(sample_color_image, kernel_size=7)
        assert result.shape == sample_color_image.shape

    def test_reduce_noise_handles_exception(self, preprocessor):
        """Test noise reduction handles exceptions."""
        # Should return original image on failure
        result = preprocessor.reduce_noise("invalid")
        assert result == "invalid"


# ---------------------------------------------------------------------------
# Tests: enhance_contrast()
# ---------------------------------------------------------------------------


class TestEnhanceContrast:
    """Test enhance_contrast() with alpha/beta control."""

    def test_enhance_contrast_default_params(self, preprocessor, sample_color_image):
        """Test contrast enhancement with default parameters."""
        result = preprocessor.enhance_contrast(sample_color_image)
        assert result.shape == sample_color_image.shape

    def test_enhance_contrast_custom_alpha(self, preprocessor, sample_color_image):
        """Test contrast enhancement with custom alpha."""
        result = preprocessor.enhance_contrast(sample_color_image, alpha=2.0)
        assert result.shape == sample_color_image.shape

    def test_enhance_contrast_custom_beta(self, preprocessor, sample_color_image):
        """Test contrast enhancement with custom beta."""
        result = preprocessor.enhance_contrast(sample_color_image, alpha=1.0, beta=50)
        assert result.shape == sample_color_image.shape

    def test_enhance_contrast_handles_exception(self, preprocessor):
        """Test contrast enhancement handles exceptions."""
        result = preprocessor.enhance_contrast("invalid")
        # Should return original image on failure
        assert result == "invalid"


# ---------------------------------------------------------------------------
# Tests: validate_image()
# ---------------------------------------------------------------------------


class TestValidateImage:
    """Test validate_image() with various inputs."""

    def test_validate_null_image(self, preprocessor):
        """Test that null image is invalid."""
        assert preprocessor.validate_image(None) is False

    def test_validate_non_numpy(self, preprocessor):
        """Test that non-numpy is invalid."""
        assert preprocessor.validate_image("not an image") is False

    def test_validate_empty_array(self, preprocessor):
        """Test that empty array is invalid."""
        assert preprocessor.validate_image(np.array([])) is False

    def test_validate_invalid_dimensions(self, preprocessor):
        """Test that invalid dimensions are rejected."""
        # 1D array
        img = np.random.randint(0, 255, (100,), dtype=np.uint8)
        assert preprocessor.validate_image(img) is False

    def test_validate_too_small_image(self, preprocessor):
        """Test that too small image is invalid."""
        img = np.random.randint(0, 255, (5, 5, 3), dtype=np.uint8)
        assert preprocessor.validate_image(img) is False

    def test_validate_valid_color_image(self, preprocessor, sample_color_image):
        """Test that valid color image passes."""
        assert preprocessor.validate_image(sample_color_image) is True

    def test_validate_valid_grayscale(self, preprocessor, sample_grayscale_image):
        """Test that valid grayscale passes."""
        assert preprocessor.validate_image(sample_grayscale_image) is True

    def test_validate_very_large_image(self, preprocessor):
        """Test that very large image is valid but warned."""
        # Just check validation logic, don't create actual 10000px image
        img = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        assert preprocessor.validate_image(img) is True


# ---------------------------------------------------------------------------
# Tests: Global singleton
# ---------------------------------------------------------------------------


class TestGlobalSingleton:
    """Test get_image_preprocessor() singleton."""

    def test_get_preprocessor_returns_instance(self):
        """Test that get_image_preprocessor returns instance."""
        pp = get_image_preprocessor()
        assert isinstance(pp, ImagePreprocessor)

    def test_get_preprocessor_returns_same_instance(self):
        """Test singleton behavior."""
        pp1 = get_image_preprocessor()
        pp2 = get_image_preprocessor()
        assert pp1 is pp2
