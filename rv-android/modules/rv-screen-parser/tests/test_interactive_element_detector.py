"""Tests for screenshot.detectors.interactive_element_detector.

These tests exercise InteractiveElementDetector with REAL cv2 + numpy (no mocks),
mirroring the sibling ``test_error_detector.py`` conventions. The strategy is:

  A. Pure / near-pure helpers called directly (bulk of the coverage).
  B. Navigation detection driven by crafted DetectedText elements.
  C. Contour-driven detect_* strategies driven by crafted binary images.

Design justification: helpers are covered with Equivalence Partitioning (valid /
empty / degenerate input classes) and Boundary Value Analysis (thresholds such as
circularity 0.7, saturation 50/100, distance 30/60/100). The contour strategies
follow Basis Path Testing: images are crafted so each geometric branch executes.
"""

import math

import cv2
import numpy as np
import pytest
from rv_screen_parser.screenshot.detectors.interactive_element_detector import (
    InteractiveElementDetector,
    get_interactive_element_detector,
)
from rv_screen_parser.screenshot.models import (
    BoundingBox,
    DetectedText,
    DetectionMethod,
    InteractiveElement,
    InteractiveElementType,
)


def _square_contour(cx: int, cy: int, half: int = 10) -> np.ndarray:
    """Build a 4-point square contour centered at (cx, cy) as OpenCV expects."""
    return np.array(
        [
            [[cx - half, cy - half]],
            [[cx + half, cy - half]],
            [[cx + half, cy + half]],
            [[cx - half, cy + half]],
        ],
        dtype=np.int32,
    )


def _make_text(text: str, x: int, y: int, w: int = 40, h: int = 20) -> DetectedText:
    """Build a DetectedText with a valid bounding box."""
    return DetectedText(
        text=text,
        confidence=90,
        bbox=BoundingBox(x=x, y=y, width=w, height=h),
    )


class TestInteractiveElementDetector:
    """Test suite for InteractiveElementDetector."""

    def setup_method(self):
        """Create a fresh detector before each test."""
        self.detector = InteractiveElementDetector()

    # ------------------------------------------------------------------
    # Initialization / top-level dispatch
    # ------------------------------------------------------------------
    def test_initialization(self):
        """Detector wires up logger, geometry utils and indicator lists."""
        assert self.detector.logger is not None
        assert self.detector.geometry_utils is not None
        assert "email" in self.detector.input_field_indicators
        assert "next" in self.detector.navigation_indicators
        assert "toggle" in self.detector.switch_indicators

    def test_detect_interactive_elements_null_images_raises(self):
        """Null images must raise (RVParsingError propagates, reraise=True)."""
        with pytest.raises(Exception):
            self.detector.detect_interactive_elements(None, None, [])

    def test_detect_interactive_elements_blank_returns_list(self):
        """Blank images dispatch every strategy and return an empty list."""
        binary = np.zeros((200, 200), dtype=np.uint8)
        original = np.zeros((200, 200, 3), dtype=np.uint8)

        result = self.detector.detect_interactive_elements(binary, original, [])

        assert isinstance(result, list)
        assert result == []

    # ------------------------------------------------------------------
    # A. Pure / near-pure helpers
    # ------------------------------------------------------------------
    def test_detect_slider_thumb_blank_returns_zero(self):
        """HoughCircles finds nothing on a blank ROI -> 0.0."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        assert self.detector._detect_slider_thumb(image, 10, 40, 50, 4) == 0.0

    def test_detect_slider_thumb_bad_image_returns_zero(self):
        """A malformed image triggers the defensive except -> 0.0."""
        bogus = np.zeros((10,), dtype=np.uint8)  # 1-D: image.shape[1] raises
        assert self.detector._detect_slider_thumb(bogus, 0, 0, 5, 5) == 0.0

    def test_color_variance_with_variation(self):
        """A 3-channel ROI with contrast yields a variance in [0, 1]."""
        roi = np.zeros((10, 10, 3), dtype=np.uint8)
        roi[:5, :, :] = 255  # half white, half black -> high variance
        result = self.detector._calculate_color_variance(roi)
        assert 0.0 < result <= 1.0

    def test_color_variance_empty_roi(self):
        """An empty ROI (size == 0) -> 0.0."""
        assert self.detector._calculate_color_variance(np.zeros((0, 0, 3))) == 0.0

    def test_color_variance_grayscale_roi(self):
        """A 2-D grayscale ROI (len(shape) != 3) -> 0.0."""
        assert self.detector._calculate_color_variance(np.zeros((10, 10))) == 0.0

    def test_input_border_with_rectangle(self):
        """A ROI with a drawn white border yields a border score in [0, 1]."""
        roi = np.zeros((40, 80, 3), dtype=np.uint8)
        cv2.rectangle(roi, (0, 0), (79, 39), (255, 255, 255), 2)
        score = self.detector._detect_input_border(roi)
        assert 0.0 <= score <= 1.0

    def test_input_border_empty_roi(self):
        """An empty ROI (size == 0) -> 0.0."""
        assert self.detector._detect_input_border(np.zeros((0, 0, 3))) == 0.0

    def test_input_border_grayscale_roi(self):
        """A 2-D grayscale ROI skips cvtColor and still returns a float in [0, 1]."""
        roi = np.zeros((40, 80), dtype=np.uint8)
        cv2.rectangle(roi, (0, 0), (79, 39), 255, 2)
        score = self.detector._detect_input_border(roi)
        assert 0.0 <= score <= 1.0

    def test_classify_input_field(self):
        """Input-field classification returns the generic INPUT_FIELD type."""
        assert (
            self.detector._classify_input_field("email @ .com")
            == InteractiveElementType.INPUT_FIELD
        )

    def test_shape_clickability_rectangular(self):
        """A 4-point square contour is scored as rectangular -> 0.3."""
        assert self.detector._calculate_shape_clickability(_square_contour(20, 20)) == 0.3

    def test_shape_clickability_many_points(self):
        """A many-vertex (circle-like) contour scores lower (<= 0.3)."""
        pts = cv2.ellipse2Poly((50, 50), (40, 40), 0, 0, 360, 10)
        contour = pts.reshape(-1, 1, 2).astype(np.int32)
        assert 0.0 <= self.detector._calculate_shape_clickability(contour) <= 0.3

    def test_shape_clickability_rounded_rectangle(self):
        """A 5-7 vertex (rounded) contour scores 0.25."""
        # Regular hexagon: approxPolyDP preserves its 6 corners -> 4 < len < 8.
        cx, cy, r = 100, 100, 40
        pts = np.array(
            [
                [[int(cx + r * math.cos(a)), int(cy + r * math.sin(a))]]
                for a in [i * math.pi / 3 for i in range(6)]
            ],
            dtype=np.int32,
        )
        assert self.detector._calculate_shape_clickability(pts) == 0.25

    def test_shape_clickability_bad_contour(self):
        """A degenerate contour triggers the defensive except -> 0.0."""
        assert self.detector._calculate_shape_clickability(np.array([])) == 0.0

    def test_position_clickability_centered(self):
        """An element in the central band gets both x and y bonuses -> 0.2."""
        score = self.detector._calculate_position_clickability(
            450, 450, 100, 100, 1000, 1000
        )
        assert score == pytest.approx(0.2)

    def test_position_clickability_corner(self):
        """An element at the top-left corner earns no positional bonus -> 0.0."""
        score = self.detector._calculate_position_clickability(0, 0, 10, 10, 1000, 1000)
        assert score == 0.0

    def test_find_nearby_text_returns_closest(self):
        """The closest text within the distance threshold is returned."""
        far = _make_text("far", x=200, y=200)
        near = _make_text("near", x=105, y=105)
        result = self.detector._find_nearby_text(
            100, 100, 10, 10, [far, near], distance=50
        )
        assert result == "near"

    def test_find_nearby_text_none_when_far(self):
        """No text within the distance threshold -> None."""
        far = _make_text("far", x=500, y=500)
        result = self.detector._find_nearby_text(
            0, 0, 10, 10, [far], distance=20
        )
        assert result is None

    def test_find_text_inside_element(self):
        """A text whose center lies inside the box is returned (joined)."""
        inside = _make_text("hello", x=30, y=30, w=10, h=10)
        result = self.detector._find_text_inside_element(0, 0, 100, 100, [inside])
        assert "hello" in result

    def test_find_text_inside_element_none(self):
        """No contained text -> None."""
        outside = _make_text("outside", x=500, y=500)
        result = self.detector._find_text_inside_element(0, 0, 50, 50, [outside])
        assert result is None

    def test_overlaps_with_existing_true(self):
        """Identical boxes overlap fully (> 50%) -> True."""
        existing = [
            InteractiveElement(
                x=10,
                y=10,
                width=100,
                height=100,
                type=InteractiveElementType.CLICKABLE,
                confidence=0.9,
                detection_method=DetectionMethod.PATTERN,
                aspect_ratio=1.0,
            )
        ]
        assert self.detector._overlaps_with_existing(10, 10, 100, 100, existing) is True

    def test_overlaps_with_existing_false(self):
        """Disjoint boxes do not overlap -> False."""
        existing = [
            InteractiveElement(
                x=10,
                y=10,
                width=20,
                height=20,
                type=InteractiveElementType.CLICKABLE,
                confidence=0.9,
                detection_method=DetectionMethod.PATTERN,
                aspect_ratio=1.0,
            )
        ]
        assert self.detector._overlaps_with_existing(500, 500, 20, 20, existing) is False

    def test_overlaps_with_existing_empty(self):
        """No existing elements -> False."""
        assert self.detector._overlaps_with_existing(0, 0, 10, 10, []) is False

    def test_create_interactive_element_valid(self):
        """Valid arguments produce an InteractiveElement with aspect_ratio = w/h."""
        element = self.detector._create_interactive_element(
            10, 20, 100, 50, 0.75, InteractiveElementType.CLICKABLE, "desc"
        )
        assert element is not None
        assert element.x == 10 and element.y == 20
        assert element.width == 100 and element.height == 50
        assert element.type == InteractiveElementType.CLICKABLE
        assert element.confidence == pytest.approx(0.75)
        assert element.aspect_ratio == pytest.approx(2.0)

    def test_create_interactive_element_invalid_returns_none(self):
        """Out-of-range confidence fails validation -> None (defensive branch)."""
        element = self.detector._create_interactive_element(
            10, 20, 100, 50, 5.0, InteractiveElementType.CLICKABLE, "desc"
        )
        assert element is None

    # ------------------------------------------------------------------
    # Summary statistics
    # ------------------------------------------------------------------
    def test_summary_empty(self):
        """An empty element list yields zeroed statistics."""
        summary = self.detector.get_interactive_element_summary([])
        assert summary["total_elements"] == 0
        assert summary["average_confidence"] == 0.0
        assert summary["element_types"] == {}

    def test_summary_with_elements(self):
        """Mixed elements are counted by type with correct averages."""
        elements = [
            InteractiveElement(
                x=0,
                y=0,
                width=10,
                height=10,
                type=InteractiveElementType.CLICKABLE,
                confidence=0.9,
                detection_method=DetectionMethod.PATTERN,
                aspect_ratio=1.0,
            ),
            InteractiveElement(
                x=0,
                y=0,
                width=10,
                height=10,
                type=InteractiveElementType.SWITCH,
                confidence=0.6,
                detection_method=DetectionMethod.PATTERN,
                aspect_ratio=1.0,
            ),
            InteractiveElement(
                x=0,
                y=0,
                width=10,
                height=10,
                type=InteractiveElementType.CLICKABLE,
                confidence=0.3,
                detection_method=DetectionMethod.PATTERN,
                aspect_ratio=1.0,
            ),
        ]
        summary = self.detector.get_interactive_element_summary(elements)
        assert summary["total_elements"] == 3
        assert summary["element_types"]["clickable"] == 2
        assert summary["element_types"]["switch"] == 1
        assert summary["high_confidence_elements"] == 1  # only the 0.9 one >= 0.8
        assert summary["average_confidence"] == pytest.approx((0.9 + 0.6 + 0.3) / 3)

    # ------------------------------------------------------------------
    # Grid pattern identification
    # ------------------------------------------------------------------
    def test_identify_grid_patterns_too_few(self):
        """Fewer than 9 contours -> no grid ([])."""
        contours = [_square_contour(10 * i, 10 * i) for i in range(5)]
        assert self.detector._identify_grid_patterns(contours, 500, 500) == []

    def test_identify_grid_patterns_degenerate_moments(self):
        """9+ zero-area (line) contours yield < 9 centroids -> []."""
        # Two-point line contours have m00 == 0, so no centroid is extracted.
        contours = [
            np.array([[[i, 0]], [[i + 10, 0]]], dtype=np.int32) for i in range(9)
        ]
        assert self.detector._identify_grid_patterns(contours, 500, 500) == []

    def test_identify_grid_patterns_regular(self):
        """A uniform diagonal grid (low CV) is detected and centers returned."""
        # Diagonal keeps sorted-order spacings uniform (dx = dy = 50) -> CV = 0.
        contours = [_square_contour(50 + 50 * i, 50 + 50 * i) for i in range(9)]
        centers = self.detector._identify_grid_patterns(contours, 600, 600)
        assert len(centers) == 9

    def test_identify_grid_patterns_irregular(self):
        """Irregular spacing (CV >= 0.3) is rejected -> []."""
        positions = [0, 30, 120, 150, 240, 270, 360, 390, 480]
        contours = [_square_contour(30 + p, 30 + p) for p in positions]
        assert self.detector._identify_grid_patterns(contours, 600, 600) == []

    # ------------------------------------------------------------------
    # Board game classification (pure)
    # ------------------------------------------------------------------
    @pytest.mark.parametrize(
        "circularity,aspect_ratio,saturation,value,hue_variance,expected_type",
        [
            # circularity > 0.7 -> PIECE
            (0.9, 2.0, 0, 0, 500, InteractiveElementType.BOARD_GAME_PIECE),
            # square aspect ratio branch, no color -> POSITION
            (0.5, 1.0, 60, 60, 500, InteractiveElementType.BOARD_GAME_POSITION),
            # high saturation -> PIECE
            (0.5, 3.0, 150, 60, 500, InteractiveElementType.BOARD_GAME_PIECE),
            # low saturation + bright -> POSITION
            (0.5, 3.0, 30, 210, 500, InteractiveElementType.BOARD_GAME_POSITION),
            # low hue variance bonus -> POSITION
            (0.5, 3.0, 60, 60, 50, InteractiveElementType.BOARD_GAME_POSITION),
        ],
    )
    def test_classify_board_game_element_branches(
        self, circularity, aspect_ratio, saturation, value, hue_variance, expected_type
    ):
        """Each classification factor branch produces the expected type in [0, 1]."""
        element_type, confidence = self.detector._classify_board_game_element(
            area=1600,
            aspect_ratio=aspect_ratio,
            circularity=circularity,
            saturation=saturation,
            value=value,
            hue_variance=hue_variance,
            x=90,
            y=90,
            w=20,
            h=20,
            img_width=500,
            img_height=500,
            grid_positions=[],
        )
        assert element_type == expected_type
        assert 0.0 <= confidence <= 1.0

    def test_classify_board_game_element_with_grid(self):
        """A populated grid exercises the size/position consistency sub-scores."""
        grid = [(100, 100), (200, 100), (100, 200), (200, 200)]
        element_type, confidence = self.detector._classify_board_game_element(
            area=15625,
            aspect_ratio=1.0,
            circularity=0.9,
            saturation=150,
            value=210,
            hue_variance=50,
            x=90,
            y=90,
            w=20,
            h=20,
            img_width=500,
            img_height=500,
            grid_positions=grid,
        )
        assert isinstance(element_type, InteractiveElementType)
        assert 0.0 <= confidence <= 1.0

    # ------------------------------------------------------------------
    # Size / position consistency scores
    # ------------------------------------------------------------------
    def test_size_consistency_too_few_positions(self):
        """Fewer than 3 grid positions -> neutral 0.5."""
        assert (
            self.detector._calculate_size_consistency_score(1000, [(1, 1)], 500, 500)
            == 0.5
        )

    def test_size_consistency_close_to_expected(self):
        """An area near the expected size yields a positive score in (0, 1]."""
        grid = [(0, 0), (1, 1), (2, 2), (3, 3)]
        expected = (500 * 500) / (len(grid) * 4)  # 15625
        score = self.detector._calculate_size_consistency_score(
            expected, grid, 500, 500
        )
        assert 0.0 < score <= 1.0

    def test_size_consistency_far_from_expected(self):
        """An area far from the expected size -> 0.0."""
        grid = [(0, 0), (1, 1), (2, 2), (3, 3)]
        assert (
            self.detector._calculate_size_consistency_score(1, grid, 500, 500) == 0.0
        )

    @pytest.mark.parametrize(
        "grid,x,y,expected",
        [
            ([], 0, 0, 0.3),  # empty grid -> neutral
            ([(105, 105)], 95, 95, 1.0),  # center (105,105) distance 0 < 30
            ([(140, 140)], 95, 95, 0.7),  # distance ~49 < 60
            ([(160, 160)], 95, 95, 0.4),  # distance ~78 < 100
            ([(400, 400)], 95, 95, 0.1),  # far -> 0.1
        ],
    )
    def test_position_consistency_score(self, grid, x, y, expected):
        """Proximity to a grid position maps to the graded score."""
        score = self.detector._calculate_position_consistency_score(x, y, 20, 20, grid)
        assert score == pytest.approx(expected)

    # ------------------------------------------------------------------
    # Module singleton
    # ------------------------------------------------------------------
    def test_get_interactive_element_detector_singleton(self):
        """The module accessor returns a shared singleton instance."""
        first = get_interactive_element_detector()
        second = get_interactive_element_detector()
        assert first is second
        assert isinstance(first, InteractiveElementDetector)

    # ------------------------------------------------------------------
    # B. Navigation detection (text-driven)
    # ------------------------------------------------------------------
    def test_navigation_bottom_word(self):
        """A nav word at the bottom of the screen creates a NAVIGATION element."""
        binary = np.zeros((200, 200), dtype=np.uint8)
        original = np.zeros((200, 200, 3), dtype=np.uint8)
        texts = [_make_text("next", x=50, y=180, w=40, h=15)]  # y > 170 (bottom)

        result = self.detector._detect_navigation_elements(binary, original, texts)

        assert any(e.type == InteractiveElementType.NAVIGATION for e in result)

    def test_navigation_symbol(self):
        """A navigation symbol contributes a strong score -> element created."""
        binary = np.zeros((200, 200), dtype=np.uint8)
        original = np.zeros((200, 200, 3), dtype=np.uint8)
        texts = [_make_text("→", x=90, y=90, w=20, h=20)]  # right arrow, middle

        result = self.detector._detect_navigation_elements(binary, original, texts)

        assert any(e.type == InteractiveElementType.NAVIGATION for e in result)

    def test_navigation_side_position(self):
        """A nav word on the left edge earns a side-navigation bonus."""
        binary = np.zeros((200, 200), dtype=np.uint8)
        original = np.zeros((200, 200, 3), dtype=np.uint8)
        texts = [_make_text("menu", x=5, y=100, w=15, h=15)]  # x < 20 (side)

        result = self.detector._detect_navigation_elements(binary, original, texts)

        assert any(e.type == InteractiveElementType.NAVIGATION for e in result)

    def test_navigation_top_position(self):
        """A nav word near the top of the screen earns a top-navigation bonus."""
        binary = np.zeros((200, 200), dtype=np.uint8)
        original = np.zeros((200, 200, 3), dtype=np.uint8)
        texts = [_make_text("home menu", x=50, y=5, w=60, h=15)]  # y < 30 (top)

        result = self.detector._detect_navigation_elements(binary, original, texts)

        assert any(e.type == InteractiveElementType.NAVIGATION for e in result)

    def test_navigation_no_indicator(self):
        """Plain centered text is below threshold -> no navigation element."""
        binary = np.zeros((200, 200), dtype=np.uint8)
        original = np.zeros((200, 200, 3), dtype=np.uint8)
        texts = [_make_text("hello", x=90, y=90, w=20, h=20)]

        result = self.detector._detect_navigation_elements(binary, original, texts)

        assert result == []

    # ------------------------------------------------------------------
    # C. Contour-driven detection strategies
    # ------------------------------------------------------------------
    def test_detect_sliders(self):
        """A long thin horizontal bar is detected as a SLIDER."""
        binary = np.zeros((400, 400), dtype=np.uint8)
        cv2.rectangle(binary, (50, 100), (150, 103), 255, -1)  # w=100, h=3
        original = np.zeros((400, 400, 3), dtype=np.uint8)
        texts = [_make_text("volume", x=90, y=95, w=30, h=15)]  # nearby-text branch

        sliders = self.detector._detect_sliders(binary, original, texts)

        assert any(e.type == InteractiveElementType.SLIDER for e in sliders)

    def test_detect_switches(self):
        """A small 2.5:1 rounded rectangle is detected as a SWITCH."""
        binary = np.zeros((500, 500), dtype=np.uint8)
        cv2.rectangle(binary, (100, 100), (150, 120), 255, -1)  # w=50, h=20, aspect 2.5
        original = np.zeros((500, 500, 3), dtype=np.uint8)
        texts = [_make_text("wifi", x=120, y=110, w=30, h=15)]

        switches = self.detector._detect_switches(binary, original, texts)

        assert any(e.type == InteractiveElementType.SWITCH for e in switches)

    def test_detect_switches_indicator_text(self):
        """A switch-indicator word ('toggle') boosts confidence via the if-branch."""
        binary = np.zeros((500, 500), dtype=np.uint8)
        cv2.rectangle(binary, (100, 100), (150, 120), 255, -1)
        original = np.zeros((500, 500, 3), dtype=np.uint8)
        texts = [_make_text("toggle", x=120, y=110, w=30, h=15)]

        switches = self.detector._detect_switches(binary, original, texts)

        assert any(e.type == InteractiveElementType.SWITCH for e in switches)

    def test_detect_input_fields_char_hint_branch(self):
        """Text with a separator char ('.') hits the char-based confidence elif."""
        binary = np.zeros((500, 500), dtype=np.uint8)
        cv2.rectangle(binary, (50, 50), (350, 90), 255, -1)
        original = np.zeros((500, 500, 3), dtype=np.uint8)
        texts = [_make_text("3.5", x=180, y=60, w=40, h=20)]  # '.' but no indicator word

        fields = self.detector._detect_input_fields(binary, original, texts)

        assert any(e.type == InteractiveElementType.INPUT_FIELD for e in fields)

    def test_detect_input_fields_placeholder_branch(self):
        """Text containing 'hint' hits the placeholder/hint confidence elif."""
        binary = np.zeros((500, 500), dtype=np.uint8)
        cv2.rectangle(binary, (50, 50), (350, 90), 255, -1)
        original = np.zeros((500, 500, 3), dtype=np.uint8)
        texts = [_make_text("hint here", x=180, y=60, w=40, h=20)]

        fields = self.detector._detect_input_fields(binary, original, texts)

        assert isinstance(fields, list)

    def test_detect_input_fields(self):
        """A wide rectangle with an inside input hint is detected as INPUT_FIELD."""
        binary = np.zeros((500, 500), dtype=np.uint8)
        cv2.rectangle(binary, (50, 50), (350, 90), 255, -1)  # w=300, h=40, aspect 7.5
        original = np.zeros((500, 500, 3), dtype=np.uint8)
        texts = [_make_text("email", x=180, y=60, w=40, h=20)]  # inside the box

        fields = self.detector._detect_input_fields(binary, original, texts)

        assert any(e.type == InteractiveElementType.INPUT_FIELD for e in fields)

    def test_detect_clickable_elements(self):
        """A medium rectangle with no overlap is detected as CLICKABLE."""
        binary = np.zeros((500, 500), dtype=np.uint8)
        cv2.rectangle(binary, (100, 100), (220, 180), 255, -1)  # w=120, h=80
        original = np.zeros((500, 500, 3), dtype=np.uint8)
        texts = [_make_text("submit", x=150, y=130, w=40, h=20)]  # inside -> text_score

        clickables = self.detector._detect_clickable_elements(
            binary, original, texts, existing_elements=[]
        )

        assert any(e.type == InteractiveElementType.CLICKABLE for e in clickables)

    def test_detect_clickable_elements_overlap_skipped(self):
        """A candidate overlapping an existing element is skipped (continue)."""
        binary = np.zeros((500, 500), dtype=np.uint8)
        cv2.rectangle(binary, (100, 100), (220, 180), 255, -1)
        original = np.zeros((500, 500, 3), dtype=np.uint8)
        existing = [
            InteractiveElement(
                x=100,
                y=100,
                width=120,
                height=80,
                type=InteractiveElementType.CLICKABLE,
                confidence=0.9,
                detection_method=DetectionMethod.PATTERN,
                aspect_ratio=1.5,
            )
        ]

        clickables = self.detector._detect_clickable_elements(
            binary, original, [], existing_elements=existing
        )

        assert clickables == []

    def test_detect_board_game_elements(self):
        """Colored squares are detected as board game elements with circularity set."""
        binary = np.zeros((500, 500), dtype=np.uint8)
        original = np.zeros((500, 500, 3), dtype=np.uint8)
        # Three saturated blue squares (40x40, area=1600) -> saturation high -> PIECE
        for cx in (100, 200, 300):
            cv2.rectangle(binary, (cx, 100), (cx + 40, 140), 255, -1)
            cv2.rectangle(original, (cx, 100), (cx + 40, 140), (255, 0, 0), -1)

        elements = self.detector._detect_board_game_elements(binary, original, [])

        assert len(elements) >= 1
        assert all(e.circularity is not None for e in elements)
        for e in elements:
            assert isinstance(e, InteractiveElement)
            assert e.type in (
                InteractiveElementType.BOARD_GAME_PIECE,
                InteractiveElementType.BOARD_GAME_POSITION,
            )

    def test_detect_board_game_elements_filters_out_of_range(self):
        """Shapes outside the size/aspect filters are skipped (continue branches)."""
        binary = np.zeros((500, 500), dtype=np.uint8)
        original = np.zeros((500, 500, 3), dtype=np.uint8)
        cv2.rectangle(binary, (50, 50), (60, 60), 255, -1)  # area ~100 < 400 -> skip
        cv2.rectangle(binary, (100, 100), (110, 160), 255, -1)  # w=10 < 15 -> skip

        elements = self.detector._detect_board_game_elements(binary, original, [])

        assert elements == []
