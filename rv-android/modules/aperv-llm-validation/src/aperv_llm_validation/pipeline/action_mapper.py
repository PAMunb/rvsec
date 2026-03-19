"""Action mapping algorithm — Python replica of LlmRouter.mapToModelAction() (commit b2852dd).

Maps pixel coordinates and action type to the best matching widget using the exact
5-step algorithm from the Java implementation:
1. Back action -> immediate match
2. Boundary rejection (top 5%, bottom 6%)
3. Bounds containment (smallest area widget containing the pixel)
4. Long-click retry (without type filter)
5. Euclidean fallback (nearest center within tolerance)
"""

from __future__ import annotations

import math

from aperv_llm_validation.constants import (
    BOUNDARY_BOTTOM_RATIO,
    BOUNDARY_TOP_RATIO,
    DEVICE_HEIGHT,
    DEVICE_WIDTH,
    INPUT_CLASS_NAMES,
    MIN_EUCLIDEAN_TOLERANCE,
)
from aperv_llm_validation.data.models import MatchResult, MatchStep, Widget


def map_to_action(
    pixel_x: int,
    pixel_y: int,
    action_type: str,
    text: str | None,
    widgets: list[Widget],
    device_w: int = DEVICE_WIDTH,
    device_h: int = DEVICE_HEIGHT,
) -> MatchResult:
    """Map pixel coordinates and action type to the best matching widget.

    Exact replica of LlmRouter.mapToModelAction() 5-step algorithm.
    Returns a MatchResult; the caller is responsible for no-match classification.
    """
    # Compute nearest widget info for all results
    nearest_dist, nearest_widget = _find_nearest_widget(pixel_x, pixel_y, widgets)

    # Step 1: Back action
    if action_type == "back":
        return MatchResult(
            matched=True,
            step=MatchStep.BACK,
            widget=None,
            action_type=action_type,
            pixel_x=pixel_x,
            pixel_y=pixel_y,
            qwen_x=0,
            qwen_y=0,
            distance_to_nearest=nearest_dist,
            nearest_widget=nearest_widget,
            classification=None,
        )

    # Step 2: Boundary rejection
    if pixel_y < device_h * BOUNDARY_TOP_RATIO or pixel_y > device_h * BOUNDARY_BOTTOM_RATIO:
        return MatchResult(
            matched=False,
            step=MatchStep.NO_MATCH,
            widget=None,
            action_type=action_type,
            pixel_x=pixel_x,
            pixel_y=pixel_y,
            qwen_x=0,
            qwen_y=0,
            distance_to_nearest=nearest_dist,
            nearest_widget=nearest_widget,
            classification=None,
        )

    if not widgets:
        return _no_match_result(
            action_type, pixel_x, pixel_y, nearest_dist, nearest_widget
        )

    is_type_text = action_type == "type_text"
    prefer_long_click = action_type == "long_click"

    # Step 3: Bounds containment pass
    best_bounds: Widget | None = None
    best_area = float("inf")

    for w in widgets:
        # For type_text: restrict to input-capable widgets
        if is_type_text and w.class_name not in INPUT_CLASS_NAMES:
            continue
        # For long_click: prefer long-clickable widgets in first pass
        if prefer_long_click and not w.long_clickable:
            continue
        if _contains(w.bounds, pixel_x, pixel_y):
            area = w.area
            if area < best_area:
                best_area = area
                best_bounds = w

    if best_bounds is not None:
        return _match_result(
            MatchStep.BOUNDS_MATCH, best_bounds, action_type, pixel_x, pixel_y,
            nearest_dist, nearest_widget,
        )

    # Step 4: Long-click retry without type filter
    if prefer_long_click:
        best_area = float("inf")
        for w in widgets:
            if _contains(w.bounds, pixel_x, pixel_y):
                area = w.area
                if area < best_area:
                    best_area = area
                    best_bounds = w
        if best_bounds is not None:
            return _match_result(
                MatchStep.LONG_CLICK_RETRY, best_bounds, action_type, pixel_x, pixel_y,
                nearest_dist, nearest_widget,
            )

    # Step 5: Euclidean fallback
    best_euclidean: Widget | None = None
    best_dist = float("inf")

    for w in widgets:
        if is_type_text and w.class_name not in INPUT_CLASS_NAMES:
            continue
        cx, cy = w.center
        dist = math.hypot(cx - pixel_x, cy - pixel_y)
        tolerance = max(MIN_EUCLIDEAN_TOLERANCE, min(w.width, w.height) / 2.0)
        if dist <= tolerance and dist < best_dist:
            best_dist = dist
            best_euclidean = w

    if best_euclidean is not None:
        return _match_result(
            MatchStep.EUCLIDEAN_MATCH, best_euclidean, action_type, pixel_x, pixel_y,
            nearest_dist, nearest_widget,
        )

    # No match found
    return _no_match_result(action_type, pixel_x, pixel_y, nearest_dist, nearest_widget)


def _contains(bounds: tuple[int, int, int, int], px: int, py: int) -> bool:
    """Check if pixel (px, py) is inside bounds (left, top, right, bottom).

    Uses Android Rect.contains() semantics: left <= px < right, top <= py < bottom.
    However, for matching purposes the Java code uses Rect.contains(x, y) which is
    left <= x <= right && top <= y <= bottom (inclusive on all sides).
    """
    left, top, right, bottom = bounds
    return left <= px <= right and top <= py <= bottom


def _find_nearest_widget(
    px: int, py: int, widgets: list[Widget]
) -> tuple[float, Widget | None]:
    """Find the nearest widget by Euclidean distance to center."""
    if not widgets:
        return (float("inf"), None)
    best_dist = float("inf")
    best_widget: Widget | None = None
    for w in widgets:
        cx, cy = w.center
        dist = math.hypot(cx - px, cy - py)
        if dist < best_dist:
            best_dist = dist
            best_widget = w
    return (best_dist, best_widget)


def _match_result(
    step: MatchStep,
    widget: Widget,
    action_type: str,
    pixel_x: int,
    pixel_y: int,
    nearest_dist: float,
    nearest_widget: Widget | None,
) -> MatchResult:
    return MatchResult(
        matched=True,
        step=step,
        widget=widget,
        action_type=action_type,
        pixel_x=pixel_x,
        pixel_y=pixel_y,
        qwen_x=0,
        qwen_y=0,
        distance_to_nearest=nearest_dist,
        nearest_widget=nearest_widget,
        classification=None,
    )


def _no_match_result(
    action_type: str,
    pixel_x: int,
    pixel_y: int,
    nearest_dist: float,
    nearest_widget: Widget | None,
) -> MatchResult:
    return MatchResult(
        matched=False,
        step=MatchStep.NO_MATCH,
        widget=None,
        action_type=action_type,
        pixel_x=pixel_x,
        pixel_y=pixel_y,
        qwen_x=0,
        qwen_y=0,
        distance_to_nearest=nearest_dist,
        nearest_widget=nearest_widget,
        classification=None,
    )
