#!/usr/bin/env python3
"""
Unit tests for the screenshot dict->Pydantic conversion utilities.

This suite exercises ``rv_screen_parser.screenshot.converters`` in isolation:
the module is pure conversion logic (legacy dict -> typed models) with no
OpenCV/numpy/PIL dependency, so it can be tested without any image stack.

### Why the "returns None on failure" assertions
Every ``ScreenshotDataConverter.convert_*`` method is wrapped by
``@ErrorHandler.handle_errors(..., reraise=False)``. When a conversion raises
``RVValidationError`` internally, that exception is *absorbed* by the framework
error handler (it is registered as an absorbed type) and the decorated method
returns ``None`` instead of propagating. The tests therefore assert ``is None``
for invalid inputs rather than ``pytest.raises`` on the decorated methods. This
behaviour was verified empirically against the real ``ErrorHandler``, not
assumed.

The two module-level helpers ``convert_to_analysis_result`` and
``convert_element_list`` are NOT decorated, so their explicit ``raise``
statements propagate normally and are asserted with ``pytest.raises``.
"""

import dataclasses
import sys
import types
from pathlib import Path

import pytest

# Make the module's own src/ importable when the file is collected in isolation.
src_dir = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(src_dir))

# The screenshot package __init__ eagerly imports `screenshot_analyzer`, which
# imports OpenCV (cv2 -> numpy). `converters` needs neither. Under `coverage`,
# that numpy C-extension load fails with "cannot load module more than once per
# process". We register a lightweight stub for the analyzer submodule BEFORE
# importing converters so the package __init__ resolves the `ScreenshotAnalyzer`
# name from the stub and never touches cv2 — keeping this suite pure conversion
# logic and coverage-measurable in isolation.
_analyzer_stub = types.ModuleType("rv_screen_parser.screenshot.screenshot_analyzer")
_analyzer_stub.ScreenshotAnalyzer = object
sys.modules.setdefault(
    "rv_screen_parser.screenshot.screenshot_analyzer", _analyzer_stub
)

from rv_screen_parser.screenshot.converters import (  # noqa: E402
    ScreenshotDataConverter,
    convert_element_list,
    convert_to_analysis_result,
    get_converter,
)
from rv_screen_parser.screenshot.models import (  # noqa: E402
    BoundingBox,
    DetectedButton,
    DetectedText,
    DetectionMethod,
    ErrorIndicator,
    ErrorType,
    IconType,
    ImageDimensions,
    InteractiveElement,
    InteractiveElementType,
    ScreenshotAnalysisResult,
)


# --------------------------------------------------------------------------- #
# Valid input fixtures (equivalence-class representatives)
# --------------------------------------------------------------------------- #


def _valid_bbox_dict():
    return {"x": 0, "y": 0, "width": 10, "height": 10}


def _valid_text_dict():
    return {
        "text": "OK",
        "confidence": 95,
        "bbox": _valid_bbox_dict(),
        "is_button_like": True,
        "is_error_like": False,
    }


def _valid_button_dict():
    # area and aspect_ratio must be > 0; the model rejects the method defaults
    # of 0.0, so realistic positive values are required for the happy path.
    return {
        "x": 5,
        "y": 5,
        "width": 100,
        "height": 40,
        "area": 4000.0,
        "aspect_ratio": 2.5,
        "confidence": 0.9,
        "detection_method": "shape",
        "text": "Submit",
    }


def _valid_error_dict():
    return {
        "x": 1,
        "y": 2,
        "width": 50,
        "height": 50,
        "detection_method": "color",
        "confidence": 0.8,
        "error_type": "general_error",
        "icon_type": "error_circle",
        "text": "Invalid input",
    }


def _valid_interactive_dict():
    return {
        "x": 0,
        "y": 0,
        "width": 80,
        "height": 80,
        "type": "joystick",
        "confidence": 0.7,
        "detection_method": "shape",
    }


@pytest.fixture
def converter():
    """Fresh converter instance for the class-method tests."""
    return ScreenshotDataConverter()


# --------------------------------------------------------------------------- #
# convert_dimensions
# --------------------------------------------------------------------------- #


class TestConvertDimensions:
    """Traceability: dimensions conversion (width/height dict -> ImageDimensions)."""

    def test_valid_dimensions(self, converter):
        """Happy path: a well-formed dict yields a validated ImageDimensions."""
        result = converter.convert_dimensions({"width": 1080, "height": 1920})
        assert isinstance(result, ImageDimensions)
        assert (result.width, result.height) == (1080, 1920)

    def test_invalid_dimensions_returns_none(self, converter):
        """Boundary: missing keys default to 0, which violates gt=0; the
        RVValidationError raised inside is absorbed and the method returns None."""
        assert converter.convert_dimensions({}) is None


# --------------------------------------------------------------------------- #
# convert_bounding_box
# --------------------------------------------------------------------------- #


class TestConvertBoundingBox:
    """Traceability: bounding-box conversion (x/y/width/height -> BoundingBox)."""

    def test_valid_bounding_box(self, converter):
        """Happy path: produces a BoundingBox with the supplied coordinates."""
        result = converter.convert_bounding_box(
            {"x": 3, "y": 4, "width": 20, "height": 30}
        )
        assert isinstance(result, BoundingBox)
        assert (result.x, result.y, result.width, result.height) == (3, 4, 20, 30)

    def test_invalid_bounding_box_returns_none(self, converter):
        """Boundary: width/height default to 0 (violates gt=0) -> absorbed -> None."""
        assert converter.convert_bounding_box({"x": 0, "y": 0}) is None


# --------------------------------------------------------------------------- #
# convert_text_element
# --------------------------------------------------------------------------- #


class TestConvertTextElement:
    """Traceability: OCR text-element conversion (dict -> DetectedText)."""

    def test_valid_text_element(self, converter):
        """Happy path: nested bbox is converted and flags are carried through."""
        result = converter.convert_text_element(_valid_text_dict())
        assert isinstance(result, DetectedText)
        assert result.text == "OK"
        assert result.confidence == 95
        assert result.is_button_like is True
        assert isinstance(result.bbox, BoundingBox)

    def test_invalid_text_element_returns_none(self, converter):
        """Error case: empty text (min_length=1) triggers absorbed validation -> None."""
        bad = _valid_text_dict()
        bad["text"] = ""
        assert converter.convert_text_element(bad) is None


# --------------------------------------------------------------------------- #
# convert_button_element
# --------------------------------------------------------------------------- #


class TestConvertButtonElement:
    """Traceability: button-element conversion (dict -> DetectedButton)."""

    def test_valid_button_element(self, converter):
        """Happy path: string detection_method is mapped to the enum."""
        result = converter.convert_button_element(_valid_button_dict())
        assert isinstance(result, DetectedButton)
        assert result.detection_method == DetectionMethod.SHAPE
        assert result.text == "Submit"
        assert result.confidence == pytest.approx(0.9)

    def test_invalid_button_element_returns_none(self, converter):
        """Error case: confidence 5.0 is out of [0,1]; absorbed -> None."""
        bad = _valid_button_dict()
        bad["confidence"] = 5.0
        assert converter.convert_button_element(bad) is None


# --------------------------------------------------------------------------- #
# convert_error_indicator
# --------------------------------------------------------------------------- #


class TestConvertErrorIndicator:
    """Traceability: error-indicator conversion (dict -> ErrorIndicator)."""

    def test_valid_error_indicator_with_icon(self, converter):
        """Happy path: exercises the optional icon_type branch (present in dict)."""
        result = converter.convert_error_indicator(_valid_error_dict())
        assert isinstance(result, ErrorIndicator)
        assert result.error_type == ErrorType.GENERAL_ERROR
        assert result.detection_method == DetectionMethod.COLOR
        assert result.icon_type == IconType.ERROR_CIRCLE

    def test_valid_error_indicator_without_icon(self, converter):
        """Boundary: when 'icon_type' key is absent, icon_type stays None."""
        no_icon = _valid_error_dict()
        del no_icon["icon_type"]
        result = converter.convert_error_indicator(no_icon)
        assert isinstance(result, ErrorIndicator)
        assert result.icon_type is None

    def test_invalid_error_indicator_returns_none(self, converter):
        """Error case: negative width violates gt=0; absorbed -> None."""
        bad = _valid_error_dict()
        bad["width"] = -1
        assert converter.convert_error_indicator(bad) is None


# --------------------------------------------------------------------------- #
# convert_interactive_element
# --------------------------------------------------------------------------- #


class TestConvertInteractiveElement:
    """Traceability: interactive-element conversion (dict -> InteractiveElement)."""

    def test_valid_interactive_element(self, converter):
        """Happy path: both type and detection_method strings map to enums."""
        result = converter.convert_interactive_element(_valid_interactive_dict())
        assert isinstance(result, InteractiveElement)
        assert result.type == InteractiveElementType.JOYSTICK
        assert result.detection_method == DetectionMethod.SHAPE

    def test_invalid_interactive_element_returns_none(self, converter):
        """Error case: width defaults to 0 (violates gt=0); absorbed -> None."""
        bad = {"x": 0, "y": 0, "type": "joystick", "confidence": 0.5}
        assert converter.convert_interactive_element(bad) is None


# --------------------------------------------------------------------------- #
# Private enum converters: valid value AND ValueError -> default fallback
# --------------------------------------------------------------------------- #


class TestEnumConverters:
    """Basis-path coverage: each private enum mapper has a valid branch and a
    ValueError-default branch. Both are exercised for all four converters."""

    def test_detection_method_valid_and_default(self, converter):
        assert converter._convert_detection_method("color") == DetectionMethod.COLOR
        # Unknown string -> ValueError -> SHAPE default.
        assert converter._convert_detection_method("nope") == DetectionMethod.SHAPE

    def test_error_type_valid_and_default(self, converter):
        assert converter._convert_error_type("network_error") == ErrorType.NETWORK_ERROR
        assert converter._convert_error_type("nope") == ErrorType.UNKNOWN_ERROR

    def test_icon_type_valid_and_default(self, converter):
        assert converter._convert_icon_type("x_mark") == IconType.X_MARK
        assert converter._convert_icon_type("nope") == IconType.GENERIC_CIRCLE

    def test_interactive_element_type_valid_and_default(self, converter):
        assert (
            converter._convert_interactive_element_type("slider")
            == InteractiveElementType.SLIDER
        )
        assert (
            converter._convert_interactive_element_type("nope")
            == InteractiveElementType.JOYSTICK
        )


# --------------------------------------------------------------------------- #
# convert_analysis_result (full nested dict)
# --------------------------------------------------------------------------- #


class TestConvertAnalysisResult:
    """Traceability: full analysis-result assembly from a nested legacy dict."""

    def test_full_nested_result(self, converter):
        """Happy path: one element of every kind is converted and collected."""
        data = {
            "image_path": "/tmp/shot.png",
            "dimensions": {"width": 1080, "height": 1920},
            "texts": [_valid_text_dict()],
            "buttons": [_valid_button_dict()],
            "error_indicators": [_valid_error_dict()],
            "interactive_elements": [_valid_interactive_dict()],
            "processing_time": 1.5,
            "success": True,
            "error_message": "",
        }
        result = converter.convert_analysis_result(data)
        assert isinstance(result, ScreenshotAnalysisResult)
        assert result.total_elements == 4
        assert result.dimensions.width == 1080

    def test_per_element_failure_is_skipped_and_continues(self, converter, monkeypatch):
        """White-box: a per-element converter that raises is caught inside the
        loop (logged as a warning) and processing continues. We force each
        sub-converter to raise so all four continue-branches are exercised; the
        resulting model still builds successfully with zero elements collected.

        This path cannot be reached with plain invalid data because the decorated
        sub-converters absorb errors and return None rather than raising, so we
        patch them to raise explicitly."""

        def boom(_):
            raise ValueError("forced failure")

        monkeypatch.setattr(converter, "convert_text_element", boom)
        monkeypatch.setattr(converter, "convert_button_element", boom)
        monkeypatch.setattr(converter, "convert_error_indicator", boom)
        monkeypatch.setattr(converter, "convert_interactive_element", boom)

        data = {
            "image_path": "/tmp/shot.png",
            "dimensions": {"width": 100, "height": 200},
            "texts": [_valid_text_dict()],
            "buttons": [_valid_button_dict()],
            "error_indicators": [_valid_error_dict()],
            "interactive_elements": [_valid_interactive_dict()],
        }
        result = converter.convert_analysis_result(data)
        assert isinstance(result, ScreenshotAnalysisResult)
        assert result.total_elements == 0

    def test_invalid_result_returns_none(self, converter):
        """Error case: empty image_path violates min_length=1; the RVParsingError
        raised in the outer except is not absorbed but, with reraise=False, the
        decorator still returns None."""
        assert converter.convert_analysis_result({"image_path": ""}) is None


# --------------------------------------------------------------------------- #
# get_converter (singleton)
# --------------------------------------------------------------------------- #


def test_get_converter_is_singleton():
    """Repeated calls must return the exact same instance (module-global cache)."""
    first = get_converter()
    second = get_converter()
    assert first is second
    assert isinstance(first, ScreenshotDataConverter)


# --------------------------------------------------------------------------- #
# convert_to_analysis_result (dict path, dataclass path, object path, error)
# --------------------------------------------------------------------------- #


@dataclasses.dataclass
class _LegacyResult:
    """Minimal dataclass standing in for a legacy analysis-result object."""

    image_path: str
    dimensions: dict


class _LegacyObject:
    """Plain (non-dataclass) object carrying analysis attributes via __dict__."""

    def __init__(self):
        self.image_path = "/tmp/obj.png"
        self.dimensions = {"width": 640, "height": 480}


class TestConvertToAnalysisResult:
    """Traceability: unified entry point accepting dict / dataclass / object."""

    def test_dict_path(self):
        """A plain dict is passed straight through to the converter."""
        result = convert_to_analysis_result(
            {"image_path": "/tmp/a.png", "dimensions": {"width": 100, "height": 100}}
        )
        assert isinstance(result, ScreenshotAnalysisResult)
        assert result.image_path == "/tmp/a.png"

    def test_dataclass_path(self):
        """A dataclass is flattened via dataclasses.asdict before conversion."""
        legacy = _LegacyResult(
            image_path="/tmp/dc.png", dimensions={"width": 320, "height": 240}
        )
        result = convert_to_analysis_result(legacy)
        assert isinstance(result, ScreenshotAnalysisResult)
        assert result.image_path == "/tmp/dc.png"
        assert result.dimensions.width == 320

    def test_plain_object_path(self):
        """A non-dataclass object falls back to its __dict__ for conversion."""
        result = convert_to_analysis_result(_LegacyObject())
        assert isinstance(result, ScreenshotAnalysisResult)
        assert result.image_path == "/tmp/obj.png"
        assert result.dimensions.height == 480

    def test_non_dict_raises_parsing_error(self):
        """A value that is neither dict nor object-with-__dict__ (e.g. a list)
        cannot be converted and must raise RVParsingError. This helper is not
        decorated, so the exception propagates."""
        from rv_android_core.util.error.exceptions import RVParsingError

        with pytest.raises(RVParsingError):
            convert_to_analysis_result([1, 2, 3])


# --------------------------------------------------------------------------- #
# convert_element_list
# --------------------------------------------------------------------------- #


class TestConvertElementList:
    """Traceability: batch conversion keyed by element_type string."""

    @pytest.mark.parametrize(
        "element_type, sample, model",
        [
            ("text", _valid_text_dict(), DetectedText),
            ("button", _valid_button_dict(), DetectedButton),
            ("error", _valid_error_dict(), ErrorIndicator),
            ("interactive", _valid_interactive_dict(), InteractiveElement),
        ],
    )
    def test_valid_element_types(self, element_type, sample, model):
        """Equivalence classes: each supported element_type converts its list."""
        result = convert_element_list([sample], element_type)
        assert len(result) == 1
        assert isinstance(result[0], model)

    def test_invalid_element_type_raises_validation_error(self):
        """Error case: an unsupported element_type raises RVValidationError. The
        helper is undecorated, so the exception propagates to the caller."""
        from rv_android_core.util.error.exceptions import RVValidationError

        with pytest.raises(RVValidationError):
            convert_element_list([_valid_text_dict()], "unknown_type")

    def test_failing_element_is_skipped_with_warning(self, monkeypatch):
        """White-box: an element whose converter raises is skipped (warning) and
        the loop continues over the rest. The bound converter method is patched
        to raise because the decorated original would otherwise absorb and return
        None instead of raising."""

        def boom(_):
            raise ValueError("forced failure")

        singleton = get_converter()
        monkeypatch.setattr(singleton, "convert_text_element", boom)

        result = convert_element_list([_valid_text_dict(), _valid_text_dict()], "text")
        assert result == []
