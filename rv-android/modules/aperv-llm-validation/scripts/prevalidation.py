#!/usr/bin/env python3
"""Pre-validation: per-widget grounding test for smart_resize vs max-edge.

Tests VLM coordinate accuracy by asking Qwen3-VL to click on specific widgets
by name, without providing coordinates in the prompt. Compares 3 image processing
modes × 2 temperatures to isolate the image preprocessing variable.

Usage:
    uv run python scripts/prevalidation.py \
        --screenshots-dir /path/to/screenshots \
        --sglang-url http://192.168.0.36:30000/v1 \
        --output-dir results/prevalidation

References:
    - rvsec-vision-llm: 57.7% hit rate baseline (pure grounding, max-edge 1000px)
    - design.md Group 0.5: Pre-Validation Phase
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

# Add module to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aperv_llm_validation.constants import (
    ALWAYS_CLICKABLE_TYPES,
    DEFAULT_SGLANG_URL,
    DEVICE_HEIGHT,
    DEVICE_WIDTH,
    MAX_WIDGETS_PER_SCREENSHOT,
    QWEN_COORD_RANGE,
)
from aperv_llm_validation.data.uiautomator_parser import parse_uiautomator
from aperv_llm_validation.data.models import Widget
from aperv_llm_validation.infrastructure.response_cache import ResponseCache
from aperv_llm_validation.pipeline.image_processor import process_screenshot_with_dims
from aperv_llm_validation.pipeline.coordinate_normalizer import qwen_to_pixel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

RESIZE_MODES = ["max_edge", "smart_resize", "raw"]
TEMPERATURES = [0.01, 0.7]

CENTER_HIT_THRESHOLD = 50  # pixels — matches rvsec-vision-llm benchmark


def build_tool_schema(img_w: int, img_h: int) -> list[dict]:
    """Build tool schema with image-specific pixel ranges (matches rvsec-vision-llm v2 strict)."""
    return [
        {
            "type": "function",
            "function": {
                "name": "android_click",
                "description": (
                    f"Click on a UI element at the specified pixel coordinates. "
                    f"Screen is {img_w}x{img_h} pixels."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {
                            "type": "integer",
                            "description": f"X pixel coordinate (0-{img_w}, horizontal position from left edge)",
                        },
                        "y": {
                            "type": "integer",
                            "description": f"Y pixel coordinate (0-{img_h}, vertical position from top edge)",
                        },
                    },
                    "required": ["x", "y"],
                },
            },
        }
    ]


@dataclass
class GroundingResult:
    """Result of one per-widget grounding call."""

    screenshot_id: str
    app_name: str
    widget_text: str
    widget_class: str
    widget_bounds: str  # "left,top,right,bottom"
    resize_mode: str
    temperature: float
    predicted_qwen_x: int
    predicted_qwen_y: int
    img_w: int  # resized image width used in prompt
    img_h: int  # resized image height used in prompt
    predicted_pixel_x: int  # device pixels (after 2-step conversion)
    predicted_pixel_y: int
    bounds_hit: bool  # predicted pixel falls within widget bounds (strict, APE check)
    center_hit: bool  # predicted pixel within 50px of widget center (rvsec-vision-llm)
    distance_to_center: float  # Euclidean distance from prediction to widget center (device pixels)
    tokens_in: int
    tokens_out: int
    latency_ms: int
    error: str  # empty if no error


def select_widgets(widgets: list[Widget], max_count: int = MAX_WIDGETS_PER_SCREENSHOT) -> list[Widget]:
    """Select widgets for grounding test: must have text/content_desc, cap at max_count."""
    eligible = [w for w in widgets if w.text or w.content_desc]
    if len(eligible) <= max_count:
        return eligible
    # Select by area quintiles for diversity
    sorted_by_area = sorted(eligible, key=lambda w: w.area)
    step = max(1, len(sorted_by_area) // max_count)
    selected = sorted_by_area[::step][:max_count]
    return selected


def build_grounding_prompt(widget: Widget, screenshot_b64: str, img_w: int, img_h: int) -> list[dict]:
    """Build grounding prompt with image dimensions (matches rvsec-vision-llm v2 strict)."""
    display_text = widget.text if widget.text else widget.content_desc
    return [
        {
            "role": "system",
            "content": (
                f"You are an Android UI automation agent. "
                f"The screen image has dimensions {img_w}x{img_h} pixels.\n\n"
                f"CRITICAL RULES:\n"
                f"1. You MUST call the android_click tool for EVERY click request\n"
                f"2. NEVER respond with text only - ALWAYS use the tool\n"
                f"3. Provide EXACT coordinates by analyzing the image\n"
                f"The x coordinate must be between 0 and {img_w}, "
                f"y between 0 and {img_h}."
            ),
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{screenshot_b64}"},
                },
                {
                    "type": "text",
                    "text": f'Click on the element labeled "{display_text}"',
                },
            ],
        },
    ]


def _parse_coord_value(val) -> int | None:
    """Parse a coordinate value that may be int, float, or comma-separated string."""
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        val = val.strip()
        # Handle "498, 549" — take the first number
        if "," in val:
            return int(val.split(",")[0].strip())
        return int(val)
    return None


def _extract_xy(args: dict) -> tuple[int, int] | None:
    """Extract (x, y) from tool args, handling Qwen's quirky comma-separated format."""
    raw_x = args.get("x")
    raw_y = args.get("y")

    # Qwen3.5 sometimes puts both coords in x as "498, 549"
    if isinstance(raw_x, str) and "," in raw_x:
        parts = raw_x.split(",")
        if len(parts) >= 2:
            try:
                return int(parts[0].strip()), int(parts[1].strip())
            except ValueError:
                pass

    x = _parse_coord_value(raw_x)
    y = _parse_coord_value(raw_y)
    if x is not None and y is not None:
        return x, y
    return None


def parse_click_response(response: dict) -> tuple[int, int] | None:
    """Extract (x, y) coordinates from LLM response. Returns None on failure."""
    try:
        choice = response["choices"][0]["message"]

        # Try native tool_calls first
        tool_calls = choice.get("tool_calls")
        if tool_calls:
            args = tool_calls[0]["function"]["arguments"]
            if isinstance(args, str):
                args = json.loads(args)
            return _extract_xy(args)

        # Try parsing from content text
        content = choice.get("content", "")
        if not content:
            return None

        # Try JSON in content
        for start_marker in ['{"name"', '{"x"']:
            idx = content.find(start_marker)
            if idx >= 0:
                # Find matching brace
                brace_count = 0
                for i in range(idx, len(content)):
                    if content[i] == "{":
                        brace_count += 1
                    elif content[i] == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            try:
                                obj = json.loads(content[idx : i + 1])
                                if "arguments" in obj:
                                    obj = obj["arguments"]
                                if "x" in obj and "y" in obj:
                                    return _extract_xy(obj)
                            except (json.JSONDecodeError, KeyError, ValueError):
                                pass
                            break
        return None
    except Exception:
        return None


def check_bounds_hit(pixel_x: int, pixel_y: int, widget: Widget) -> bool:
    """Check if predicted device pixel coordinates fall within widget bounds (strict)."""
    left, top, right, bottom = widget.bounds
    return left <= pixel_x <= right and top <= pixel_y <= bottom


def check_center_hit(pixel_x: int, pixel_y: int, widget: Widget) -> bool:
    """Check if predicted pixel is within 50px of widget center (rvsec-vision-llm criterion)."""
    return distance_to_center(pixel_x, pixel_y, widget) <= CENTER_HIT_THRESHOLD


def distance_to_center(pixel_x: int, pixel_y: int, widget: Widget) -> float:
    """Euclidean distance from predicted point to widget center in pixels."""
    cx, cy = widget.center
    return ((pixel_x - cx) ** 2 + (pixel_y - cy) ** 2) ** 0.5


def discover_screenshots(screenshots_dir: Path) -> list[tuple[str, Path, Path]]:
    """Find all PNG + UIAutomator XML pairs. Returns (app_name, png_path, xml_path)."""
    pairs = []
    for app_dir in sorted(screenshots_dir.iterdir()):
        if not app_dir.is_dir():
            continue
        app_name = app_dir.name
        for png_path in sorted(app_dir.glob("*.png")):
            xml_name = png_path.stem + ".uiautomator"
            xml_path = app_dir / xml_name
            if xml_path.exists():
                pairs.append((app_name, png_path, xml_path))
    return pairs


def run_prevalidation(
    screenshots_dir: Path,
    sglang_url: str,
    output_dir: Path,
    cache_dir: Path,
    max_screenshots: int | None = None,
    modes: list[str] | None = None,
    temperatures: list[float] | None = None,
    extra_body: dict | None = None,
    model: str | None = None,
) -> list[GroundingResult]:
    """Run the full pre-validation: all widgets × modes × temperatures."""

    from aperv_llm_validation.pipeline.sglang_client import SglangClient

    modes = modes or RESIZE_MODES
    temperatures = temperatures or TEMPERATURES
    output_dir.mkdir(parents=True, exist_ok=True)

    # Health check
    client_kwargs = {"base_url": sglang_url}
    if model:
        client_kwargs["model"] = model
    client = SglangClient(**client_kwargs)
    if not client.health_check():
        logger.error("SGLang server not reachable at %s", sglang_url)
        sys.exit(1)
    logger.info("SGLang server OK at %s (model=%s)", sglang_url, model or "default")

    # Discover screenshots
    pairs = discover_screenshots(screenshots_dir)
    if max_screenshots:
        pairs = pairs[:max_screenshots]
    logger.info("Found %d screenshot+XML pairs", len(pairs))

    # Cache
    cache = ResponseCache(cache_dir)
    logger.info("Cache at %s (%d entries)", cache_dir, cache.stats()["total_entries"])

    results: list[GroundingResult] = []
    total_calls = 0
    total_hits = 0

    for pair_idx, (app_name, png_path, xml_path) in enumerate(pairs):
        screenshot_id = png_path.stem

        # Parse widgets
        widgets = parse_uiautomator(xml_path)
        selected = select_widgets(widgets)
        if not selected:
            logger.debug("No eligible widgets in %s/%s, skipping", app_name, screenshot_id)
            continue

        for mode in modes:
            # Process screenshot once per mode — get base64 AND resized dimensions
            try:
                b64, img_w, img_h = process_screenshot_with_dims(png_path, mode=mode)
            except Exception as e:
                logger.warning("Failed to process %s with mode %s: %s", png_path, mode, e)
                continue

            # Build tool schema with image-specific dimensions
            tools = build_tool_schema(img_w, img_h)

            for temp in temperatures:
                temp_client_kwargs = {
                    "base_url": sglang_url,
                    "temperature": temp,
                }
                if model:
                    temp_client_kwargs["model"] = model
                temp_client = SglangClient(**temp_client_kwargs)

                for widget in selected:
                    display_text = widget.text if widget.text else widget.content_desc
                    prompt_name = f"grounding_{display_text[:30]}"
                    bounds_str = f"{widget.bounds[0]},{widget.bounds[1]},{widget.bounds[2]},{widget.bounds[3]}"

                    def _error_result(error_msg: str, t_in: int = 0, t_out: int = 0, lat: int = 0) -> GroundingResult:
                        return GroundingResult(
                            screenshot_id=screenshot_id, app_name=app_name,
                            widget_text=display_text, widget_class=widget.class_name,
                            widget_bounds=bounds_str, resize_mode=mode, temperature=temp,
                            img_w=img_w, img_h=img_h,
                            predicted_qwen_x=0, predicted_qwen_y=0,
                            predicted_pixel_x=0, predicted_pixel_y=0,
                            bounds_hit=False, center_hit=False, distance_to_center=9999.0,
                            tokens_in=t_in, tokens_out=t_out, latency_ms=lat,
                            error=error_msg,
                        )

                    # Check cache
                    cached = cache.get(
                        screenshot=f"{app_name}/{screenshot_id}",
                        prompt=prompt_name,
                        rep_seed=0,
                        temperature=temp,
                        resize_mode=mode,
                    )

                    if cached:
                        response = cached["response"]
                        tokens_in = cached["tokens_in"]
                        tokens_out = cached["tokens_out"]
                        latency_ms = cached["latency_ms"]
                    else:
                        messages = build_grounding_prompt(widget, b64, img_w, img_h)
                        start_ms = int(time.time() * 1000)
                        try:
                            response = temp_client.call(messages, tools=tools, extra_body=extra_body)
                            latency_ms = int(time.time() * 1000) - start_ms
                            usage = response.get("usage", {})
                            tokens_in = usage.get("prompt_tokens", 0)
                            tokens_out = usage.get("completion_tokens", 0)

                            cache.put(
                                screenshot=f"{app_name}/{screenshot_id}",
                                prompt=prompt_name, rep_seed=0,
                                temperature=temp, resize_mode=mode,
                                response=response, tokens_in=tokens_in,
                                tokens_out=tokens_out, latency_ms=latency_ms,
                            )
                        except Exception as e:
                            results.append(_error_result(str(e)))
                            continue

                    # Parse response
                    coords = parse_click_response(response)
                    if coords is None:
                        results.append(_error_result("no_tool_call", tokens_in, tokens_out, latency_ms))
                        total_calls += 1
                        continue

                    qwen_x, qwen_y = coords

                    # 2-step coordinate conversion:
                    # 1. Qwen [0, 1000) → resized image pixels
                    img_px_x = int((qwen_x / QWEN_COORD_RANGE) * img_w)
                    img_px_y = int((qwen_y / QWEN_COORD_RANGE) * img_h)
                    # Clamp to image bounds
                    img_px_x = max(0, min(img_px_x, img_w - 1))
                    img_px_y = max(0, min(img_px_y, img_h - 1))
                    # 2. Resized image pixels → device pixels (for UIAutomator bounds check)
                    dev_px_x = int((img_px_x / img_w) * DEVICE_WIDTH)
                    dev_px_y = int((img_px_y / img_h) * DEVICE_HEIGHT)
                    dev_px_x = max(0, min(dev_px_x, DEVICE_WIDTH - 1))
                    dev_px_y = max(0, min(dev_px_y, DEVICE_HEIGHT - 1))

                    is_bounds_hit = check_bounds_hit(dev_px_x, dev_px_y, widget)
                    is_center_hit = check_center_hit(dev_px_x, dev_px_y, widget)
                    dist = distance_to_center(dev_px_x, dev_px_y, widget)

                    total_calls += 1
                    if is_center_hit:
                        total_hits += 1

                    results.append(GroundingResult(
                        screenshot_id=screenshot_id, app_name=app_name,
                        widget_text=display_text, widget_class=widget.class_name,
                        widget_bounds=bounds_str, resize_mode=mode, temperature=temp,
                        img_w=img_w, img_h=img_h,
                        predicted_qwen_x=qwen_x, predicted_qwen_y=qwen_y,
                        predicted_pixel_x=dev_px_x, predicted_pixel_y=dev_px_y,
                        bounds_hit=is_bounds_hit, center_hit=is_center_hit,
                        distance_to_center=round(dist, 1),
                        tokens_in=tokens_in, tokens_out=tokens_out,
                        latency_ms=latency_ms, error="",
                    ))

        if (pair_idx + 1) % 50 == 0:
            hit_rate = (total_hits / total_calls * 100) if total_calls else 0
            logger.info(
                "Progress: %d/%d screenshots, %d calls, %.1f%% hit rate",
                pair_idx + 1, len(pairs), total_calls, hit_rate,
            )

    # Write CSV
    csv_path = output_dir / "000_prevalidation_results.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[field for field in GroundingResult.__dataclass_fields__])
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))

    logger.info("Results written to %s (%d rows)", csv_path, len(results))

    # Print summary
    print_summary(results)

    return results


def print_summary(results: list[GroundingResult]) -> None:
    """Print hit rate summary per mode × temperature."""
    print("\n" + "=" * 70)
    print("PRE-VALIDATION SUMMARY")
    print("=" * 70)

    # Group by mode × temperature
    groups: dict[tuple[str, float], list[GroundingResult]] = {}
    for r in results:
        key = (r.resize_mode, r.temperature)
        groups.setdefault(key, []).append(r)

    print(f"\n{'Mode':<15} {'Temp':<6} {'Calls':<7} {'Bounds':<8} {'B.Rate':<8} {'Center':<8} {'C.Rate':<8} {'Avg Dist':<10}")
    print("-" * 78)

    for (mode, temp), group in sorted(groups.items()):
        valid = [r for r in group if not r.error]
        bounds_hits = sum(1 for r in valid if r.bounds_hit)
        center_hits = sum(1 for r in valid if r.center_hit)
        total = len(valid)
        bounds_rate = bounds_hits / total * 100 if total else 0
        center_rate = center_hits / total * 100 if total else 0
        avg_dist = sum(r.distance_to_center for r in valid) / total if total else 0
        print(f"{mode:<15} {temp:<6.2f} {total:<7} {bounds_hits:<8} {bounds_rate:<7.1f}% {center_hits:<8} {center_rate:<7.1f}% {avg_dist:<10.1f}px")

    if not groups:
        print("\nNo valid results to analyze.")
        return

    # Per widget class breakdown
    print(f"\n{'Widget Class':<30} {'Calls':<7} {'Bounds':<8} {'B.Rate':<8} {'Center':<8} {'C.Rate':<8}")
    print("-" * 70)
    class_groups: dict[str, list[GroundingResult]] = {}
    for r in results:
        if r.error:
            continue
        simple = r.widget_class.rsplit(".", 1)[-1] if "." in r.widget_class else r.widget_class
        class_groups.setdefault(simple, []).append(r)
    for cls_name, group in sorted(class_groups.items(), key=lambda x: -len(x[1])):
        bounds_hits = sum(1 for r in group if r.bounds_hit)
        center_hits = sum(1 for r in group if r.center_hit)
        total = len(group)
        bounds_rate = bounds_hits / total * 100 if total else 0
        center_rate = center_hits / total * 100 if total else 0
        print(f"{cls_name:<30} {total:<7} {bounds_hits:<8} {bounds_rate:<7.1f}% {center_hits:<8} {center_rate:<7.1f}%")

    # Per app breakdown (best mode by center_hit rate)
    best_mode = max(
        ((mode, temp) for (mode, temp) in groups),
        key=lambda k: sum(1 for r in groups[k] if r.center_hit and not r.error) / max(1, len([r for r in groups[k] if not r.error])),
    )
    print(f"\nPer-app center_hit rate (best condition: {best_mode[0]} temp={best_mode[1]}):")
    print(f"{'App':<35} {'Calls':<7} {'Center':<8} {'C.Rate':<8}")
    print("-" * 58)
    app_groups: dict[str, list[GroundingResult]] = {}
    for r in groups[best_mode]:
        if r.error:
            continue
        app_groups.setdefault(r.app_name, []).append(r)
    for app_name, group in sorted(app_groups.items()):
        center_hits = sum(1 for r in group if r.center_hit)
        total = len(group)
        center_rate = center_hits / total * 100 if total else 0
        print(f"{app_name:<35} {total:<7} {center_hits:<8} {center_rate:<7.1f}%")

    errors = sum(1 for r in results if r.error)
    if errors:
        print(f"\nErrors: {errors} calls failed")

    print()


def main():
    parser = argparse.ArgumentParser(description="Pre-validation: per-widget grounding test")
    parser.add_argument("--screenshots-dir", type=Path, required=True,
                        help="Directory with app_name/screenshot.png + .uiautomator pairs")
    parser.add_argument("--sglang-url", default=DEFAULT_SGLANG_URL,
                        help=f"SGLang server URL (default: {DEFAULT_SGLANG_URL})")
    parser.add_argument("--output-dir", type=Path, default=Path("results"),
                        help="Output directory for CSV and reports (default: results/)")
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache"),
                        help="Cache directory (default: .cache/)")
    parser.add_argument("--max-screenshots", type=int, default=None,
                        help="Limit number of screenshots (for quick tests)")
    parser.add_argument("--modes", nargs="+", choices=RESIZE_MODES, default=None,
                        help="Image processing modes to test (default: all 3)")
    parser.add_argument("--temperatures", nargs="+", type=float, default=None,
                        help="Temperatures to test (default: 0.01, 0.7)")
    parser.add_argument("--model", type=str, default=None,
                        help="Model name to use (default: 'default')")
    parser.add_argument("--disable-thinking", action="store_true",
                        help="Disable thinking mode (Qwen3.5+ models)")
    args = parser.parse_args()

    extra_body = None
    if args.disable_thinking:
        extra_body = {"chat_template_kwargs": {"enable_thinking": False}}

    run_prevalidation(
        screenshots_dir=args.screenshots_dir,
        sglang_url=args.sglang_url,
        output_dir=args.output_dir,
        cache_dir=args.cache_dir,
        max_screenshots=args.max_screenshots,
        modes=args.modes,
        temperatures=args.temperatures,
        extra_body=extra_body,
        model=args.model,
    )


if __name__ == "__main__":
    main()
