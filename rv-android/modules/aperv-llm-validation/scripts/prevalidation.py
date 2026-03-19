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
    MAX_WIDGETS_PER_SCREENSHOT,
    QWEN_COORD_RANGE,
)
from aperv_llm_validation.data.uiautomator_parser import parse_uiautomator
from aperv_llm_validation.data.models import Widget
from aperv_llm_validation.infrastructure.response_cache import ResponseCache
from aperv_llm_validation.pipeline.image_processor import process_screenshot
from aperv_llm_validation.pipeline.coordinate_normalizer import qwen_to_pixel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

RESIZE_MODES = ["max_edge", "smart_resize", "raw"]
TEMPERATURES = [0.01, 0.7]

TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "click",
            "description": "Click on the element at the given coordinates",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate [0, 1000)"},
                    "y": {"type": "integer", "description": "Y coordinate [0, 1000)"},
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
    predicted_pixel_x: int
    predicted_pixel_y: int
    hit: bool  # predicted pixel falls within widget bounds
    distance_to_center: float  # Euclidean distance from prediction to widget center (pixels)
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


def build_grounding_prompt(widget: Widget, screenshot_b64: str) -> list[dict]:
    """Build a simple grounding prompt: 'Click on the element labeled [text]'."""
    display_text = widget.text if widget.text else widget.content_desc
    return [
        {
            "role": "system",
            "content": "Click on the specified element. Return coordinates in [0, 1000) range.",
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
            return int(args["x"]), int(args["y"])

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
                                    return int(obj["x"]), int(obj["y"])
                            except (json.JSONDecodeError, KeyError, ValueError):
                                pass
                            break
        return None
    except Exception:
        return None


def check_hit(pixel_x: int, pixel_y: int, widget: Widget) -> bool:
    """Check if predicted pixel coordinates fall within widget bounds."""
    left, top, right, bottom = widget.bounds
    return left <= pixel_x <= right and top <= pixel_y <= bottom


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
) -> list[GroundingResult]:
    """Run the full pre-validation: all widgets × modes × temperatures."""

    from aperv_llm_validation.pipeline.sglang_client import SglangClient

    modes = modes or RESIZE_MODES
    temperatures = temperatures or TEMPERATURES
    output_dir.mkdir(parents=True, exist_ok=True)

    # Health check
    client = SglangClient(base_url=sglang_url)
    if not client.health_check():
        logger.error("SGLang server not reachable at %s", sglang_url)
        sys.exit(1)
    logger.info("SGLang server OK at %s", sglang_url)

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
            # Process screenshot once per mode
            try:
                b64 = process_screenshot(png_path, resize_mode=mode)
            except Exception as e:
                logger.warning("Failed to process %s with mode %s: %s", png_path, mode, e)
                continue

            for temp in temperatures:
                temp_client = SglangClient(
                    base_url=sglang_url,
                    temperature=temp,
                )

                for widget in selected:
                    display_text = widget.text if widget.text else widget.content_desc
                    prompt_name = f"grounding_{display_text[:30]}"

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
                        messages = build_grounding_prompt(widget, b64)
                        start_ms = int(time.time() * 1000)
                        try:
                            response = temp_client.call(messages, tools=TOOL_SCHEMA)
                            latency_ms = int(time.time() * 1000) - start_ms
                            usage = response.get("usage", {})
                            tokens_in = usage.get("prompt_tokens", 0)
                            tokens_out = usage.get("completion_tokens", 0)

                            cache.put(
                                screenshot=f"{app_name}/{screenshot_id}",
                                prompt=prompt_name,
                                rep_seed=0,
                                temperature=temp,
                                resize_mode=mode,
                                response=response,
                                tokens_in=tokens_in,
                                tokens_out=tokens_out,
                                latency_ms=latency_ms,
                            )
                        except Exception as e:
                            results.append(GroundingResult(
                                screenshot_id=screenshot_id, app_name=app_name,
                                widget_text=display_text, widget_class=widget.class_name,
                                widget_bounds=f"{widget.bounds[0]},{widget.bounds[1]},{widget.bounds[2]},{widget.bounds[3]}",
                                resize_mode=mode, temperature=temp,
                                predicted_qwen_x=0, predicted_qwen_y=0,
                                predicted_pixel_x=0, predicted_pixel_y=0,
                                hit=False, distance_to_center=9999.0,
                                tokens_in=0, tokens_out=0, latency_ms=0,
                                error=str(e),
                            ))
                            continue

                    # Parse response
                    coords = parse_click_response(response)
                    if coords is None:
                        results.append(GroundingResult(
                            screenshot_id=screenshot_id, app_name=app_name,
                            widget_text=display_text, widget_class=widget.class_name,
                            widget_bounds=f"{widget.bounds[0]},{widget.bounds[1]},{widget.bounds[2]},{widget.bounds[3]}",
                            resize_mode=mode, temperature=temp,
                            predicted_qwen_x=0, predicted_qwen_y=0,
                            predicted_pixel_x=0, predicted_pixel_y=0,
                            hit=False, distance_to_center=9999.0,
                            tokens_in=tokens_in, tokens_out=tokens_out,
                            latency_ms=latency_ms, error="no_tool_call",
                        ))
                        total_calls += 1
                        continue

                    qwen_x, qwen_y = coords
                    pixel_x, pixel_y = qwen_to_pixel(qwen_x, qwen_y)

                    is_hit = check_hit(pixel_x, pixel_y, widget)
                    dist = distance_to_center(pixel_x, pixel_y, widget)

                    total_calls += 1
                    if is_hit:
                        total_hits += 1

                    results.append(GroundingResult(
                        screenshot_id=screenshot_id, app_name=app_name,
                        widget_text=display_text, widget_class=widget.class_name,
                        widget_bounds=f"{widget.bounds[0]},{widget.bounds[1]},{widget.bounds[2]},{widget.bounds[3]}",
                        resize_mode=mode, temperature=temp,
                        predicted_qwen_x=qwen_x, predicted_qwen_y=qwen_y,
                        predicted_pixel_x=pixel_x, predicted_pixel_y=pixel_y,
                        hit=is_hit, distance_to_center=round(dist, 1),
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

    print(f"\n{'Mode':<15} {'Temp':<8} {'Calls':<8} {'Hits':<8} {'Hit Rate':<10} {'Avg Dist':<10}")
    print("-" * 60)

    for (mode, temp), group in sorted(groups.items()):
        valid = [r for r in group if not r.error]
        hits = sum(1 for r in valid if r.hit)
        total = len(valid)
        hit_rate = hits / total * 100 if total else 0
        avg_dist = sum(r.distance_to_center for r in valid) / total if total else 0
        print(f"{mode:<15} {temp:<8.2f} {total:<8} {hits:<8} {hit_rate:<10.1f}% {avg_dist:<10.1f}px")

    # Per widget class breakdown
    print(f"\n{'Widget Class':<40} {'Calls':<8} {'Hits':<8} {'Hit Rate':<10}")
    print("-" * 66)
    class_groups: dict[str, list[GroundingResult]] = {}
    for r in results:
        if r.error:
            continue
        simple = r.widget_class.rsplit(".", 1)[-1] if "." in r.widget_class else r.widget_class
        class_groups.setdefault(simple, []).append(r)
    for cls_name, group in sorted(class_groups.items(), key=lambda x: -len(x[1])):
        hits = sum(1 for r in group if r.hit)
        total = len(group)
        hit_rate = hits / total * 100 if total else 0
        print(f"{cls_name:<40} {total:<8} {hits:<8} {hit_rate:<10.1f}%")

    # Per app breakdown (best mode only — mode with highest global hit rate)
    best_mode = max(
        ((mode, temp) for (mode, temp) in groups),
        key=lambda k: sum(1 for r in groups[k] if r.hit and not r.error) / max(1, len([r for r in groups[k] if not r.error])),
    )
    print(f"\nPer-app hit rate (best condition: {best_mode[0]} temp={best_mode[1]}):")
    print(f"{'App':<30} {'Calls':<8} {'Hits':<8} {'Hit Rate':<10}")
    print("-" * 56)
    app_groups: dict[str, list[GroundingResult]] = {}
    for r in groups[best_mode]:
        if r.error:
            continue
        app_groups.setdefault(r.app_name, []).append(r)
    for app_name, group in sorted(app_groups.items()):
        hits = sum(1 for r in group if r.hit)
        total = len(group)
        hit_rate = hits / total * 100 if total else 0
        print(f"{app_name:<30} {total:<8} {hits:<8} {hit_rate:<10.1f}%")

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
    args = parser.parse_args()

    run_prevalidation(
        screenshots_dir=args.screenshots_dir,
        sglang_url=args.sglang_url,
        output_dir=args.output_dir,
        cache_dir=args.cache_dir,
        max_screenshots=args.max_screenshots,
        modes=args.modes,
        temperatures=args.temperatures,
    )


if __name__ == "__main__":
    main()
