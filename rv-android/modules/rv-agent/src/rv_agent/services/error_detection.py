"""
Visual error detection service for rv-agent.

Wraps rv-screen-parser's ErrorDetector with a 4-stage false-positive
filtering pipeline. The filtering rejects indicators that are likely
system UI elements or themed decorations rather than actual validation
errors.

### Filtering Pipeline:
1. **Confidence**: Reject indicators below a configurable threshold.
2. **Size**: Reject indicators whose width or height exceeds a maximum
   (large colored regions are usually backgrounds, not error icons).
3. **Region**: Reject indicators located in the top 5% (status bar) or
   bottom 6% (navigation bar) of the screen.
4. **Count**: If the number of remaining indicators exceeds a threshold,
   assume the screen has a colorful themed UI and reject all.
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Module-level imports allow tests to patch cv2 and ErrorDetector for isolation.
# When either dependency is missing at runtime, the detector gracefully degrades.
try:
    import cv2
    from rv_screen_parser.screenshot.detectors.error_detector import ErrorDetector
except ImportError:
    cv2 = None  # type: ignore[assignment]
    ErrorDetector = None  # type: ignore[assignment,misc]


@dataclass
class ValidationErrorResult:
    """Result of visual error detection with filtering metadata."""

    detected: bool
    error_indicators: list = field(default_factory=list)
    confidence: float = 0.0
    detection_method: str = "visual_color"
    filtered_by_size: int = 0
    filtered_by_region: int = 0
    filtered_by_count: bool = False


class VisualErrorDetector:
    """
    Wraps rv-screen-parser's ErrorDetector with false-positive filtering.

    The detector reads a screenshot from disk, runs color-based error
    detection, then applies four filtering stages to reduce false positives
    from system bars, themed UIs, and large decorative elements.
    """

    # Region filter thresholds matching RVAgentStrategy system action thresholds.
    SYSTEM_BAR_TOP_PERCENT = 0.05
    SYSTEM_BAR_BOTTOM_PERCENT = 0.06

    def __init__(self):
        self._cv2 = cv2
        self._detector_cls = ErrorDetector
        self._available = self._cv2 is not None and self._detector_cls is not None

    def detect(
        self,
        screenshot_path: str,
        confidence_threshold: float = 0.7,
        max_indicator_size: int = 80,
        max_indicator_count: int = 5,
    ) -> ValidationErrorResult:
        """
        Detect validation errors in a screenshot with 4-stage filtering.

        Filtering pipeline:
        1. Confidence: reject indicators below confidence_threshold
        2. Size: reject indicators where width OR height > max_indicator_size
        3. Region: reject indicators in system bar areas (top 5%, bottom 6%)
        4. Count: if remaining count > max_indicator_count, assume themed UI and reject all

        Returns ValidationErrorResult with detected=False on any failure (graceful degradation).
        """
        if not self._available:
            return ValidationErrorResult(detected=False)

        # Read image to get dimensions for region filter
        image = self._cv2.imread(screenshot_path)
        if image is None:
            return ValidationErrorResult(detected=False)

        height = image.shape[0]

        # Run color-based error detection (pass empty texts — we only use visual detection)
        try:
            detector_instance = self._detector_cls()
            raw_indicators = detector_instance.detect_errors(image, texts=[])
        except Exception:
            logger.warning("ErrorDetector.detect_errors failed", exc_info=True)
            return ValidationErrorResult(detected=False)

        # --- Stage 1: Confidence filter ---
        accepted = [i for i in raw_indicators if i.confidence >= confidence_threshold]

        # --- Stage 2: Size filter ---
        filtered_by_size = 0
        after_size = []
        for indicator in accepted:
            if indicator.width > max_indicator_size or indicator.height > max_indicator_size:
                filtered_by_size += 1
            else:
                after_size.append(indicator)

        # --- Stage 3: Region filter ---
        filtered_by_region = 0
        top_limit = height * self.SYSTEM_BAR_TOP_PERCENT
        bottom_limit = height * (1.0 - self.SYSTEM_BAR_BOTTOM_PERCENT)
        after_region = []
        for indicator in after_size:
            if indicator.y < top_limit or indicator.y > bottom_limit:
                filtered_by_region += 1
            else:
                after_region.append(indicator)

        # --- Stage 4: Count filter ---
        filtered_by_count = False
        if len(after_region) > max_indicator_count:
            filtered_by_count = True
            after_region = []

        max_conf = max((i.confidence for i in after_region), default=0.0)

        return ValidationErrorResult(
            detected=len(after_region) > 0,
            error_indicators=after_region,
            confidence=max_conf,
            detection_method="visual_color",
            filtered_by_size=filtered_by_size,
            filtered_by_region=filtered_by_region,
            filtered_by_count=filtered_by_count,
        )
