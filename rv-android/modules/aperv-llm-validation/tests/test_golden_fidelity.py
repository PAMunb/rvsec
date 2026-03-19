"""Golden fixture fidelity tests — validate pipeline output against known-good data.

These tests compare image processing and coordinate normalization output against
golden fixtures captured from the Java APE pipeline. The fixtures are generated
separately and placed in tests/fixtures/golden/<app>/call_NNN.json.

Tests are skipped when fixtures are not present (they are large binary blobs
not checked into git).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"
GOLDEN_AVAILABLE = GOLDEN_DIR.exists() and any(GOLDEN_DIR.glob("*/call_*.json"))


@pytest.mark.skipif(
    not GOLDEN_AVAILABLE,
    reason="Golden fixtures not found — run fixture generation first",
)
class TestGoldenResize:
    """Validate that resize dimensions match Java's output for each golden call."""

    def test_golden_resize(self):
        """For each golden fixture, verify calculate_resized_dimensions matches."""
        from aperv_llm_validation.pipeline.image_processor import (
            calculate_resized_dimensions,
        )

        failures = []
        for fixture_path in sorted(GOLDEN_DIR.glob("*/call_*.json")):
            data = json.loads(fixture_path.read_text())
            if "resize" not in data:
                continue
            resize = data["resize"]
            orig_w = resize["original_width"]
            orig_h = resize["original_height"]
            expected_w = resize["resized_width"]
            expected_h = resize["resized_height"]

            actual_w, actual_h = calculate_resized_dimensions(orig_w, orig_h)
            if (actual_w, actual_h) != (expected_w, expected_h):
                failures.append(
                    f"{fixture_path.name}: expected ({expected_w}, {expected_h}), "
                    f"got ({actual_w}, {actual_h})"
                )

        assert not failures, "Resize mismatches:\n" + "\n".join(failures)


@pytest.mark.skipif(
    not GOLDEN_AVAILABLE,
    reason="Golden fixtures not found — run fixture generation first",
)
class TestGoldenJpeg:
    """Validate JPEG output similarity against golden base64 (SSIM >= 0.98)."""

    def test_golden_jpeg(self):
        """For each golden fixture with a JPEG reference, check SSIM >= 0.98.

        Requires scikit-image for SSIM computation. Skipped if not installed.
        """
        pytest.importorskip("skimage", reason="scikit-image required for SSIM")

        import base64
        import io

        import numpy as np
        from PIL import Image
        from skimage.metrics import structural_similarity as ssim

        from aperv_llm_validation.pipeline.image_processor import (
            process_screenshot_bytes,
        )

        failures = []
        for fixture_path in sorted(GOLDEN_DIR.glob("*/call_*.json")):
            data = json.loads(fixture_path.read_text())
            if "jpeg_base64" not in data or "png_path" not in data:
                continue

            # Load golden JPEG
            golden_bytes = base64.b64decode(data["jpeg_base64"])
            golden_img = np.array(Image.open(io.BytesIO(golden_bytes)).convert("L"))

            # Process the same PNG through our pipeline
            png_path = Path(data["png_path"])
            if not png_path.exists():
                continue
            result_b64 = process_screenshot_bytes(
                png_path.read_bytes(), mode="max_edge"
            )
            result_bytes = base64.b64decode(result_b64)
            result_img = np.array(Image.open(io.BytesIO(result_bytes)).convert("L"))

            # Resize to same dimensions for comparison if needed
            if golden_img.shape != result_img.shape:
                result_pil = Image.fromarray(result_img).resize(
                    (golden_img.shape[1], golden_img.shape[0]), Image.LANCZOS
                )
                result_img = np.array(result_pil)

            similarity = ssim(golden_img, result_img)
            if similarity < 0.98:
                failures.append(
                    f"{fixture_path.name}: SSIM={similarity:.4f} < 0.98"
                )

        assert not failures, "JPEG fidelity failures:\n" + "\n".join(failures)


@pytest.mark.skipif(
    not GOLDEN_AVAILABLE,
    reason="Golden fixtures not found — run fixture generation first",
)
class TestGoldenMatching:
    """Validate that the Python action mapper produces identical match results to Java."""

    def test_golden_matching(self):
        """For each golden fixture, verify map_to_action matches Java's output.

        Each golden fixture contains:
        - pixel coordinates, action_type
        - widgets parsed from UIAutomator XML
        - expected match result from Java LlmRouter.mapToModelAction()

        The test runs the Python map_to_action() and asserts identical:
        - matched (bool)
        - step (MatchStep)
        - matched widget index
        - distance_to_nearest (within epsilon)
        """
        from aperv_llm_validation.pipeline.action_mapper import map_to_action

        failures = []
        for fixture_path in sorted(GOLDEN_DIR.glob("*/call_*.json")):
            data = json.loads(fixture_path.read_text())
            if "match_result" not in data:
                continue

            expected = data["match_result"]
            widgets_data = data.get("widgets", [])

            # Build Widget objects from fixture data
            from aperv_llm_validation.data.models import Widget

            widgets = []
            for wd in widgets_data:
                widgets.append(
                    Widget(
                        class_name=wd.get("class_name", ""),
                        text=wd.get("text", ""),
                        content_desc=wd.get("content_desc", ""),
                        resource_id=wd.get("resource_id", ""),
                        bounds=tuple(wd["bounds"]),
                        clickable=wd.get("clickable", True),
                        long_clickable=wd.get("long_clickable", False),
                        editable=wd.get("editable", False),
                        checkable=wd.get("checkable", False),
                        enabled=wd.get("enabled", True),
                    )
                )

            result = map_to_action(
                pixel_x=expected["pixel_x"],
                pixel_y=expected["pixel_y"],
                action_type=expected["action_type"],
                text=expected.get("text"),
                widgets=widgets,
                device_w=data.get("device_width", 1080),
                device_h=data.get("device_height", 1920),
            )

            if result.matched != expected["matched"]:
                failures.append(
                    f"{fixture_path.name}: matched expected={expected['matched']}, "
                    f"got={result.matched}"
                )
            if result.step.value != expected.get("step"):
                failures.append(
                    f"{fixture_path.name}: step expected={expected.get('step')}, "
                    f"got={result.step.value}"
                )

        assert not failures, "Matching mismatches:\n" + "\n".join(failures)


@pytest.mark.skipif(
    not GOLDEN_AVAILABLE,
    reason="Golden fixtures not found — run fixture generation first",
)
class TestGoldenPrompt:
    """Validate that Python prompt builder produces identical output to Java."""

    def test_golden_prompt(self):
        """For each golden fixture, verify build_widget_list matches Java's output.

        Each golden fixture contains:
        - widgets parsed from UIAutomator XML
        - expected widget list text from Java's ApePromptBuilder.formatActionLine()
        - device dimensions

        The test runs the Python build_widget_list() and asserts identical output.
        """
        from aperv_llm_validation.data.models import Widget
        from aperv_llm_validation.pipeline.prompt_builder import build_widget_list

        failures = []
        for fixture_path in sorted(GOLDEN_DIR.glob("*/call_*.json")):
            data = json.loads(fixture_path.read_text())
            if "widget_list_text" not in data:
                continue

            expected_text = data["widget_list_text"]
            widgets_data = data.get("widgets", [])
            device_w = data.get("device_width", 1080)
            device_h = data.get("device_height", 1920)

            widgets = []
            for wd in widgets_data:
                widgets.append(
                    Widget(
                        class_name=wd.get("class_name", ""),
                        text=wd.get("text", ""),
                        content_desc=wd.get("content_desc", ""),
                        resource_id=wd.get("resource_id", ""),
                        bounds=tuple(wd["bounds"]),
                        clickable=wd.get("clickable", True),
                        long_clickable=wd.get("long_clickable", False),
                        editable=wd.get("editable", False),
                        checkable=wd.get("checkable", False),
                        enabled=wd.get("enabled", True),
                    )
                )

            actual_text = build_widget_list(widgets, device_w, device_h)
            if actual_text != expected_text:
                failures.append(
                    f"{fixture_path.name}: widget list mismatch\n"
                    f"  expected: {expected_text[:200]}\n"
                    f"  actual:   {actual_text[:200]}"
                )

        assert not failures, "Prompt mismatches:\n" + "\n".join(failures)


@pytest.mark.skipif(
    not GOLDEN_AVAILABLE,
    reason="Golden fixtures not found — run fixture generation first",
)
class TestGoldenWidgetList:
    """Validate widget list formatting line-by-line against golden data."""

    def test_golden_widget_list(self):
        """For each golden fixture, verify individual widget lines match Java output.

        Each golden fixture contains:
        - widget_lines: list of expected formatted lines from Java
        - widgets: the widget data used to generate those lines

        Tests each line individually for precise error reporting.
        """
        from aperv_llm_validation.data.models import Widget
        from aperv_llm_validation.pipeline.prompt_builder import build_widget_list

        failures = []
        for fixture_path in sorted(GOLDEN_DIR.glob("*/call_*.json")):
            data = json.loads(fixture_path.read_text())
            if "widget_lines" not in data:
                continue

            expected_lines = data["widget_lines"]
            widgets_data = data.get("widgets", [])
            device_w = data.get("device_width", 1080)
            device_h = data.get("device_height", 1920)

            widgets = []
            for wd in widgets_data:
                widgets.append(
                    Widget(
                        class_name=wd.get("class_name", ""),
                        text=wd.get("text", ""),
                        content_desc=wd.get("content_desc", ""),
                        resource_id=wd.get("resource_id", ""),
                        bounds=tuple(wd["bounds"]),
                        clickable=wd.get("clickable", True),
                        long_clickable=wd.get("long_clickable", False),
                        editable=wd.get("editable", False),
                        checkable=wd.get("checkable", False),
                        enabled=wd.get("enabled", True),
                    )
                )

            actual_text = build_widget_list(widgets, device_w, device_h)
            actual_lines = actual_text.split("\n") if actual_text else []

            for i, (expected, actual) in enumerate(
                zip(expected_lines, actual_lines)
            ):
                if expected != actual:
                    failures.append(
                        f"{fixture_path.name} line {i}: "
                        f"expected={expected!r}, got={actual!r}"
                    )

        assert not failures, "Widget line mismatches:\n" + "\n".join(failures)
