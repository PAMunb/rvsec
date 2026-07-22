#!/usr/bin/env python3
"""
Analyze the base64 optimized image sent to LLM and verify coordinates.
"""

import base64
import io
from PIL import Image, ImageDraw

# This is the base64 string from the log (truncated in display but we can load it from the actual screenshot)
# Let's recreate the optimization process instead

from rv_agent.core.screenshot_optimizer import ScreenshotOptimizer

# Original screenshot
original_path = "/tmp/screenshot_1761748271.png"

# Optimize using the same method
optimizer = ScreenshotOptimizer()
optimized_b64 = optimizer.optimize(original_path)

# Decode base64 to image
print("=" * 60)
print("BASE64 OPTIMIZED IMAGE ANALYSIS")
print("=" * 60)

if optimized_b64:
    # Decode base64 to bytes
    image_bytes = base64.b64decode(optimized_b64)

    # Load image from bytes
    img_optimized = Image.open(io.BytesIO(image_bytes))
    opt_width, opt_height = img_optimized.size

    print(f"\n🔧 Optimized Image (sent to LLM): {opt_width}x{opt_height}")

    # Save the decoded optimized image
    optimized_path = "/tmp/optimized_decoded.png"
    img_optimized.save(optimized_path)
    print(f"💾 Decoded optimized image saved: {optimized_path}")

    # LLM coordinates (these should be for the optimized image)
    llm_coordinates = {
        "MESSAGE DIGEST": {"x": 50, "y": 150, "width": 300, "height": 50},
        "CIPHER": {"x": 50, "y": 275, "width": 300, "height": 50},
        "GENERATED": {"x": 50, "y": 400, "width": 300, "height": 50}
    }

    print(f"\n📍 LLM Coordinates (should match optimized image {opt_width}x{opt_height}):")
    print("-" * 60)

    # Draw coordinates on optimized image
    img_visual = img_optimized.copy()
    draw = ImageDraw.Draw(img_visual)

    for element, coords in llm_coordinates.items():
        x = coords['x']
        y = coords['y']
        width = coords['width']
        height = coords['height']
        center_x = x + width // 2
        center_y = y + height // 2

        print(f"{element}:")
        print(f"   Box: ({x}, {y}) to ({x + width}, {y + height})")
        print(f"   Center: ({center_x}, {center_y})")

        # Draw rectangle
        draw.rectangle(
            [(x, y), (x + width, y + height)],
            outline="red",
            width=2
        )

        # Draw center point
        center_size = 5
        draw.ellipse(
            [(center_x - center_size, center_y - center_size),
             (center_x + center_size, center_y + center_size)],
            fill="red",
            outline="yellow",
            width=2
        )

    # Save visualization
    visual_path = "/tmp/optimized_with_coordinates.png"
    img_visual.save(visual_path)
    print(f"\n💾 Visualization saved: {visual_path}")

    # Now calculate conversion for click
    print(f"\n" + "=" * 60)
    print("COORDINATE CONVERSION FOR android_click()")
    print("=" * 60)

    # Load original to get dimensions
    img_original = Image.open(original_path)
    orig_width, orig_height = img_original.size

    print(f"\n📱 Device Screen: {orig_width}x{orig_height}")
    print(f"🔧 Optimized Image: {opt_width}x{opt_height}")

    scale_x = orig_width / opt_width
    scale_y = orig_height / opt_height

    print(f"\n📐 Scale Factors:")
    print(f"   X: {scale_x:.4f}")
    print(f"   Y: {scale_y:.4f}")

    print(f"\n🔄 Coordinate Conversion Example (MESSAGE DIGEST center):")
    llm_center_x = 200  # From LLM
    llm_center_y = 175  # From LLM
    device_center_x = int(llm_center_x * scale_x)
    device_center_y = int(llm_center_y * scale_y)

    print(f"   LLM gives: ({llm_center_x}, {llm_center_y}) [on {opt_width}x{opt_height} image]")
    print(f"   android_click() needs: ({device_center_x}, {device_center_y}) [on {orig_width}x{orig_height} device]")

    print(f"\n⚠️  CRITICAL ISSUE:")
    print("-" * 60)
    print("1. LLM analyzes OPTIMIZED image (724x1288) and provides coordinates for it")
    print("2. android_click() sends coordinates to DEVICE (1080x1920)")
    print("3. android_tools.android_click() MUST convert coordinates before clicking!")
    print(f"4. Conversion formula: device_x = llm_x * {scale_x:.4f}, device_y = llm_y * {scale_y:.4f}")

    print(f"\n📝 SOLUTION:")
    print("-" * 60)
    print("Modify android_tools.android_click() to:")
    print("1. Store original device dimensions (1080x1920)")
    print("2. Store optimized dimensions (724x1288)")
    print("3. Convert incoming coordinates: (x, y) -> (x * scale_x, y * scale_y)")
    print("4. Then call device.click(converted_x, converted_y)")

    print("=" * 60)
else:
    print("ERROR: Could not optimize screenshot")
