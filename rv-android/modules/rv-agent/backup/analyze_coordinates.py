#!/usr/bin/env python3
"""
Analyze LLM coordinates and verify if conversion is needed.
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Screenshot paths
original_screenshot = "/tmp/screenshot_1761748271.png"

# Load images
print("=" * 60)
print("COORDINATE ANALYSIS")
print("=" * 60)

# Load original screenshot
img_original = Image.open(original_screenshot)
original_width, original_height = img_original.size
print(f"\n📱 Original Screenshot (device): {original_width}x{original_height}")

# Optimized dimensions (from log)
optimized_width, optimized_height = 724, 1288
print(f"🔧 Optimized Screenshot (sent to LLM): {optimized_width}x{optimized_height}")

# Calculate scale factors
scale_x = original_width / optimized_width
scale_y = original_height / optimized_height
print(f"\n📐 Scale Factors:")
print(f"   X: {scale_x:.4f} ({original_width}/{optimized_width})")
print(f"   Y: {scale_y:.4f} ({original_height}/{optimized_height})")

# LLM coordinates (from output) - these are for the OPTIMIZED image
llm_coordinates = {
    "MESSAGE DIGEST": {"x": 50, "y": 150, "width": 300, "height": 50},
    "CIPHER": {"x": 50, "y": 275, "width": 300, "height": 50},
    "GENERATED": {"x": 50, "y": 400, "width": 300, "height": 50}
}

print(f"\n📍 LLM Coordinates (for optimized {optimized_width}x{optimized_height}):")
print("-" * 60)
for element, coords in llm_coordinates.items():
    print(f"{element}:")
    print(f"   X={coords['x']}, Y={coords['y']}")
    print(f"   Width={coords['width']}, Height={coords['height']}")
    center_x = coords['x'] + coords['width'] // 2
    center_y = coords['y'] + coords['height'] // 2
    print(f"   Center: ({center_x}, {center_y})")

print(f"\n🔄 Converted Coordinates (for device {original_width}x{original_height}):")
print("-" * 60)

# Convert and visualize
img_visual = img_original.copy()
draw = ImageDraw.Draw(img_visual)

for element, coords in llm_coordinates.items():
    # Convert coordinates to device scale
    device_x = int(coords['x'] * scale_x)
    device_y = int(coords['y'] * scale_y)
    device_width = int(coords['width'] * scale_x)
    device_height = int(coords['height'] * scale_y)
    device_center_x = device_x + device_width // 2
    device_center_y = device_y + device_height // 2

    print(f"{element}:")
    print(f"   X={device_x}, Y={device_y}")
    print(f"   Width={device_width}, Height={device_height}")
    print(f"   Center: ({device_center_x}, {device_center_y})")

    # Draw rectangle on original image
    draw.rectangle(
        [(device_x, device_y), (device_x + device_width, device_y + device_height)],
        outline="red",
        width=3
    )

    # Draw center point
    center_size = 10
    draw.ellipse(
        [(device_center_x - center_size, device_center_y - center_size),
         (device_center_x + center_size, device_center_y + center_size)],
        fill="red",
        outline="yellow",
        width=2
    )

# Save visualization
output_path = "/tmp/coordinate_analysis.png"
img_visual.save(output_path)
print(f"\n💾 Visualization saved to: {output_path}")

print(f"\n⚠️  IMPORTANT FINDINGS:")
print("-" * 60)
print(f"1. LLM analyzes OPTIMIZED screenshot: {optimized_width}x{optimized_height}")
print(f"2. android_tools.py uses DEVICE coordinates: {original_width}x{original_height}")
print(f"3. CONVERSION IS REQUIRED before calling android_click()")
print(f"4. Scale factors: X={scale_x:.4f}, Y={scale_y:.4f}")
print(f"\n📝 Recommendation:")
print("   - LLM should provide coordinates for optimized image")
print("   - android_tools.android_click() should convert coordinates to device scale")
print("   - OR: LLM should be aware of device dimensions and provide device coordinates")
print("=" * 60)
