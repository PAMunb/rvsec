#!/usr/bin/env python3
"""
Exhaustive Coordinate Validation for Qwen3-VL Resolution

Tests coordinate conversion accuracy with new qwen3-vl optimized resolution.

Resolution Changes:
- OLD (Qwen2.5-VL): 728×1288 (multiples of 28)
- NEW (Qwen3-VL): 704×1248 (multiples of 32)

This script:
1. Tests scale factor calculations
2. Validates coordinate conversion both ways
3. Tests boundary conditions
4. Verifies coordinate accuracy with visual markers
5. Generates validation report
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from typing import Tuple, List, Dict

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rv_agent.core.coordinate_converter import CoordinateConverter
from rv_agent.core.screenshot_optimizer import ScreenshotOptimizer

# Test configuration
DEVICE_DIMENSIONS = (1080, 1920)
OPTIMIZED_DIMENSIONS_OLD = (728, 1288)  # Qwen2.5-VL
OPTIMIZED_DIMENSIONS_NEW = (704, 1248)  # Qwen3-VL

# Test points (device coordinates)
TEST_POINTS = [
    # Corners
    {"name": "Top-left corner", "device": (0, 0)},
    {"name": "Top-right corner", "device": (1080, 0)},
    {"name": "Bottom-left corner", "device": (0, 1920)},
    {"name": "Bottom-right corner", "device": (1080, 1920)},

    # Center
    {"name": "Center", "device": (540, 960)},

    # Typical UI elements (from CryptoApp test)
    {"name": "MESSAGE DIGEST button", "device": (540, 272)},
    {"name": "CIPHER button", "device": (540, 406)},
    {"name": "Text input field", "device": (540, 381)},
    {"name": "GENERATE HASH button", "device": (540, 503)},

    # Edge cases
    {"name": "Near left edge", "device": (50, 500)},
    {"name": "Near right edge", "device": (1030, 500)},
    {"name": "Near top edge", "device": (540, 50)},
    {"name": "Near bottom edge", "device": (540, 1870)},
]


def test_scale_factors():
    """Test that scale factors are calculated correctly."""
    print("="*80)
    print("1. SCALE FACTOR VALIDATION")
    print("="*80)

    converter_old = CoordinateConverter(DEVICE_DIMENSIONS, OPTIMIZED_DIMENSIONS_OLD)
    converter_new = CoordinateConverter(DEVICE_DIMENSIONS, OPTIMIZED_DIMENSIONS_NEW)

    print(f"\n📐 Old Configuration (Qwen2.5-VL):")
    print(f"   Device: {DEVICE_DIMENSIONS[0]}×{DEVICE_DIMENSIONS[1]}")
    print(f"   Optimized: {OPTIMIZED_DIMENSIONS_OLD[0]}×{OPTIMIZED_DIMENSIONS_OLD[1]}")
    print(f"   Scale to device X: {converter_old.scale_to_device_x:.6f}")
    print(f"   Scale to device Y: {converter_old.scale_to_device_y:.6f}")
    print(f"   Scale to optimized X: {converter_old.scale_to_optimized_x:.6f}")
    print(f"   Scale to optimized Y: {converter_old.scale_to_optimized_y:.6f}")

    print(f"\n📐 New Configuration (Qwen3-VL):")
    print(f"   Device: {DEVICE_DIMENSIONS[0]}×{DEVICE_DIMENSIONS[1]}")
    print(f"   Optimized: {OPTIMIZED_DIMENSIONS_NEW[0]}×{OPTIMIZED_DIMENSIONS_NEW[1]}")
    print(f"   Scale to device X: {converter_new.scale_to_device_x:.6f}")
    print(f"   Scale to device Y: {converter_new.scale_to_device_y:.6f}")
    print(f"   Scale to optimized X: {converter_new.scale_to_optimized_x:.6f}")
    print(f"   Scale to optimized Y: {converter_new.scale_to_optimized_y:.6f}")

    # Verify multiples
    print(f"\n🔍 Verification:")
    print(f"   OLD: 728 ÷ 28 = {728/28:.1f} ✅" if 728 % 28 == 0 else f"   OLD: 728 ÷ 28 = {728/28:.4f} ❌")
    print(f"   OLD: 1288 ÷ 28 = {1288/28:.1f} ✅" if 1288 % 28 == 0 else f"   OLD: 1288 ÷ 28 = {1288/28:.4f} ❌")
    print(f"   NEW: 704 ÷ 32 = {704/32:.1f} ✅" if 704 % 32 == 0 else f"   NEW: 704 ÷ 32 = {704/32:.4f} ❌")
    print(f"   NEW: 1248 ÷ 32 = {1248/32:.1f} ✅" if 1248 % 32 == 0 else f"   NEW: 1248 ÷ 32 = {1248/32:.4f} ❌")

    return converter_new


def test_bidirectional_conversion(converter: CoordinateConverter):
    """Test bidirectional conversion accuracy."""
    print(f"\n{'='*80}")
    print("2. BIDIRECTIONAL CONVERSION TEST")
    print("="*80)

    max_error = 0
    errors = []

    for point in TEST_POINTS:
        name = point["name"]
        dev_x, dev_y = point["device"]

        # Convert device → optimized → device
        opt_x, opt_y = converter.device_to_optimized(dev_x, dev_y)
        back_x, back_y = converter.optimized_to_device(opt_x, opt_y)

        # Calculate error
        error_x = abs(dev_x - back_x)
        error_y = abs(dev_y - back_y)
        error_total = (error_x**2 + error_y**2) ** 0.5

        max_error = max(max_error, error_total)

        status = "✅" if error_total <= 2 else "⚠️" if error_total <= 5 else "❌"

        print(f"\n{status} {name}:")
        print(f"   Device coords:    ({dev_x}, {dev_y})")
        print(f"   → Optimized:      ({opt_x}, {opt_y})")
        print(f"   → Back to device: ({back_x}, {back_y})")
        print(f"   Error: {error_total:.2f} pixels")

        if error_total > 2:
            errors.append({
                "name": name,
                "original": (dev_x, dev_y),
                "converted_back": (back_x, back_y),
                "error": error_total
            })

    print(f"\n📊 Summary:")
    print(f"   Maximum error: {max_error:.2f} pixels")
    print(f"   Points tested: {len(TEST_POINTS)}")
    print(f"   Errors > 2px: {len(errors)}")

    if errors:
        print(f"\n⚠️  Points with significant error:")
        for err in errors:
            print(f"   - {err['name']}: {err['error']:.2f}px")

    return max_error <= 5  # Accept up to 5 pixels error due to rounding


def test_bounds_validation(converter: CoordinateConverter):
    """Test bounds validation."""
    print(f"\n{'='*80}")
    print("3. BOUNDS VALIDATION TEST")
    print("="*80)

    test_cases = [
        {"name": "Valid center", "coords": (352, 624), "should_pass": True},
        {"name": "Valid top-left", "coords": (0, 0), "should_pass": True},
        {"name": "Valid bottom-right", "coords": (704, 1248), "should_pass": True},
        {"name": "Out of bounds X", "coords": (800, 600), "should_pass": False},
        {"name": "Out of bounds Y", "coords": (300, 1500), "should_pass": False},
        {"name": "Negative X", "coords": (-10, 600), "should_pass": False},
        {"name": "Negative Y", "coords": (300, -10), "should_pass": False},
    ]

    passed = 0
    failed = 0

    for case in test_cases:
        name = case["name"]
        x, y = case["coords"]
        should_pass = case["should_pass"]

        try:
            converter.validate_optimized_coords(x, y)
            result = "PASS"
            if should_pass:
                status = "✅"
                passed += 1
            else:
                status = "❌ UNEXPECTED"
                failed += 1
        except ValueError as e:
            result = f"FAIL: {e}"
            if not should_pass:
                status = "✅"
                passed += 1
            else:
                status = "❌ UNEXPECTED"
                failed += 1

        print(f"{status} {name}: ({x}, {y}) → {result}")

    print(f"\n📊 Summary:")
    print(f"   Passed: {passed}/{len(test_cases)}")
    print(f"   Failed: {failed}/{len(test_cases)}")

    return failed == 0


def test_typical_ui_elements(converter: CoordinateConverter):
    """Test conversion of typical UI element coordinates."""
    print(f"\n{'='*80}")
    print("4. TYPICAL UI ELEMENT COORDINATES TEST")
    print("="*80)

    # Simulate CryptoApp MESSAGE DIGEST button
    device_bounds = [[0, 217], [728, 296]]  # Original device bounds

    print(f"\n🔘 Example: MESSAGE DIGEST Button")
    print(f"   Device bounds: {device_bounds}")

    # Convert bounds
    opt_bounds = converter.bounds_device_to_optimized(device_bounds)
    print(f"   Optimized bounds: {opt_bounds}")

    # Calculate center in both spaces
    center_dev = ((device_bounds[0][0] + device_bounds[1][0]) // 2,
                  (device_bounds[0][1] + device_bounds[1][1]) // 2)
    center_opt = converter.calculate_center_optimized(device_bounds)

    print(f"   Center (device): {center_dev}")
    print(f"   Center (optimized): {center_opt}")

    # Verify conversion back
    center_back = converter.optimized_to_device(center_opt[0], center_opt[1])
    error = ((center_dev[0] - center_back[0])**2 + (center_dev[1] - center_back[1])**2) ** 0.5

    print(f"   Center back to device: {center_back}")
    print(f"   Error: {error:.2f} pixels")

    return error <= 5


def generate_visual_validation(converter: CoordinateConverter):
    """Generate visual validation report."""
    print(f"\n{'='*80}")
    print("5. GENERATING VISUAL VALIDATION")
    print("="*80)

    # Create a simple test image (simulating device screen)
    device_img = Image.new('RGB', DEVICE_DIMENSIONS, color='white')
    draw_dev = ImageDraw.Draw(device_img)

    # Create optimized version
    opt_img = Image.new('RGB', OPTIMIZED_DIMENSIONS_NEW, color='white')
    draw_opt = ImageDraw.Draw(opt_img)

    # Draw test points on both images
    for point in TEST_POINTS[:8]:  # First 8 points only
        dev_x, dev_y = point["device"]
        opt_x, opt_y = converter.device_to_optimized(dev_x, dev_y)

        # Draw on device image (red)
        draw_dev.ellipse([(dev_x-10, dev_y-10), (dev_x+10, dev_y+10)],
                        fill='red', outline='black', width=2)

        # Draw on optimized image (blue)
        draw_opt.ellipse([(opt_x-5, opt_y-5), (opt_x+5, opt_y+5)],
                        fill='blue', outline='black', width=1)

    # Save images
    device_img.save("/tmp/qwen3vl_validation_device.png")
    opt_img.save("/tmp/qwen3vl_validation_optimized.png")

    print(f"\n💾 Visual validation images saved:")
    print(f"   Device: /tmp/qwen3vl_validation_device.png")
    print(f"   Optimized: /tmp/qwen3vl_validation_optimized.png")

    return True


def main():
    """Run all validation tests."""
    print(f"\n{'='*80}")
    print("  QWEN3-VL COORDINATE VALIDATION TEST SUITE")
    print("="*80)
    print(f"\nTesting new resolution for Qwen3-VL:")
    print(f"  Device: {DEVICE_DIMENSIONS[0]}×{DEVICE_DIMENSIONS[1]}")
    print(f"  Optimized: {OPTIMIZED_DIMENSIONS_NEW[0]}×{OPTIMIZED_DIMENSIONS_NEW[1]}")
    print(f"  (Changed from {OPTIMIZED_DIMENSIONS_OLD[0]}×{OPTIMIZED_DIMENSIONS_OLD[1]} for Qwen2.5-VL)")

    # Run tests
    results = {}

    try:
        converter = test_scale_factors()
        results["scale_factors"] = True
    except Exception as e:
        print(f"\n❌ Scale factor test failed: {e}")
        results["scale_factors"] = False
        return

    try:
        results["bidirectional"] = test_bidirectional_conversion(converter)
    except Exception as e:
        print(f"\n❌ Bidirectional conversion test failed: {e}")
        results["bidirectional"] = False

    try:
        results["bounds"] = test_bounds_validation(converter)
    except Exception as e:
        print(f"\n❌ Bounds validation test failed: {e}")
        results["bounds"] = False

    try:
        results["ui_elements"] = test_typical_ui_elements(converter)
    except Exception as e:
        print(f"\n❌ UI elements test failed: {e}")
        results["ui_elements"] = False

    try:
        results["visual"] = generate_visual_validation(converter)
    except Exception as e:
        print(f"\n❌ Visual validation failed: {e}")
        results["visual"] = False

    # Final report
    print(f"\n{'='*80}")
    print("  FINAL VALIDATION REPORT")
    print("="*80)

    all_passed = all(results.values())

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_name.replace('_', ' ').title()}")

    print(f"\n{'='*80}")
    if all_passed:
        print("  ✅ ALL TESTS PASSED!")
        print(f"  Qwen3-VL coordinate conversion is ACCURATE and ready for use.")
    else:
        print("  ❌ SOME TESTS FAILED")
        print(f"  Review failures above and fix coordinate conversion.")
    print("="*80)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
