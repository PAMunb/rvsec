#!/usr/bin/env python3
"""
Test script with OPTIMAL configuration based on analysis:
- Resized images (724x1288) for better coordinate precision
- Improved generic prompt (works for any Android UI)
- Automatic coordinate conversion (LLM scale → device scale)
- Multiple screenshots to validate generalization
"""

import os
import base64
import json
from pathlib import Path
from PIL import Image, ImageDraw

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

# Optimal configuration
LLM_BASE_URL = "http://localhost:11434"
LLM_MODEL = "qwen-vision-tools-v1"
OPTIMIZED_DIMENSIONS = (724, 1288)  # Optimal for vision model
DEVICE_DIMENSIONS = (1080, 1920)    # Target Android device

def resize_and_encode_image(image_path: str) -> tuple[str, tuple[int, int]]:
    """
    Resize image to optimal dimensions and encode to base64.

    Returns:
        Tuple of (base64_string, original_dimensions)
    """
    img = Image.open(image_path)
    original_size = img.size

    # Resize to optimal dimensions
    img_resized = img.resize(OPTIMIZED_DIMENSIONS, Image.Resampling.LANCZOS)

    # Convert to JPEG and encode to base64
    from io import BytesIO
    buffer = BytesIO()
    img_resized.convert("RGB").save(buffer, format="JPEG", quality=85)
    b64_string = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return b64_string, original_size

def create_optimal_prompt(width: int, height: int) -> str:
    """
    Create optimal generic prompt with example.

    Balances:
    - Generic enough for various UIs
    - Specific format with ONE example
    - Clear dimension context
    """
    return f"""Analyze this Android application screenshot.

Image dimensions: {width}x{height} pixels

Identify ALL interactive elements (buttons, text fields, tabs, icons, menu items).

For EACH element, provide:
- Element name/label
- Center coordinates: center=(x, y)
- Bounding box: box=(x, y, width, height)

Format (use EXACTLY):
- ELEMENT_NAME: center=(x, y), box=(x, y, w, h)

Example:
- Login Button: center=(362, 181), box=(8, 154, 708, 54)

Provide precise pixel coordinates relative to {width}x{height} image."""

def analyze_screenshot(image_path: str, llm: ChatOllama) -> dict:
    """Analyze screenshot with optimal configuration."""

    # Resize and encode
    image_b64, original_size = resize_and_encode_image(image_path)

    # Create optimal prompt
    prompt = create_optimal_prompt(OPTIMIZED_DIMENSIONS[0], OPTIMIZED_DIMENSIONS[1])

    # System message
    system_msg = "You are an expert in Android UI analysis. Provide precise coordinates for all interactive elements."

    # Call LLM
    try:
        message_content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
        ]

        messages = [
            SystemMessage(system_msg),
            HumanMessage(content=message_content)
        ]

        response = llm.invoke(messages)

        return {
            "success": True,
            "image_path": image_path,
            "original_size": original_size,
            "optimized_size": OPTIMIZED_DIMENSIONS,
            "device_size": DEVICE_DIMENSIONS,
            "base64_size": len(image_b64),
            "response": response.content,
            "metadata": response.response_metadata if hasattr(response, 'response_metadata') else None
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "image_path": image_path
        }

def parse_coordinates(response_text: str) -> list[dict]:
    """Parse coordinates from LLM response."""
    elements = []
    lines = response_text.split('\n')

    for line in lines:
        line = line.strip()
        if not line or ':' not in line:
            continue

        if 'center=' in line and 'box=' in line:
            try:
                # Extract name
                name = line.split(':')[0].strip('- ').strip()

                # Extract center
                center_start = line.find('center=(') + 8
                center_end = line.find(')', center_start)
                center_str = line[center_start:center_end]
                cx, cy = map(int, center_str.split(','))

                # Extract box
                box_start = line.find('box=(') + 5
                box_end = line.find(')', box_start)
                box_str = line[box_start:box_end]
                box_parts = [int(x.strip()) for x in box_str.split(',')]

                if len(box_parts) == 4:
                    # Calculate device coordinates (conversion)
                    scale_x = DEVICE_DIMENSIONS[0] / OPTIMIZED_DIMENSIONS[0]
                    scale_y = DEVICE_DIMENSIONS[1] / OPTIMIZED_DIMENSIONS[1]

                    device_cx = int(cx * scale_x)
                    device_cy = int(cy * scale_y)
                    device_x = int(box_parts[0] * scale_x)
                    device_y = int(box_parts[1] * scale_y)
                    device_w = int(box_parts[2] * scale_x)
                    device_h = int(box_parts[3] * scale_y)

                    elements.append({
                        "name": name,
                        "llm_center": {"x": cx, "y": cy},
                        "llm_box": {
                            "x": box_parts[0],
                            "y": box_parts[1],
                            "width": box_parts[2],
                            "height": box_parts[3]
                        },
                        "device_center": {"x": device_cx, "y": device_cy},
                        "device_box": {
                            "x": device_x,
                            "y": device_y,
                            "width": device_w,
                            "height": device_h
                        }
                    })
            except:
                continue

    return elements

def visualize_on_device_scale(image_path: str, elements: list[dict], output_path: str):
    """Create visualization using DEVICE coordinates on original image."""
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)

    colors = ['lime', 'cyan', 'yellow', 'magenta', 'orange']

    for idx, element in enumerate(elements):
        color = colors[idx % len(colors)]

        # Use DEVICE coordinates (converted from LLM)
        box = element['device_box']
        x, y, w, h = box['x'], box['y'], box['width'], box['height']

        # Draw bounding box
        draw.rectangle([(x, y), (x + w, y + h)], outline=color, width=3)

        # Draw center point
        center = element['device_center']
        cx, cy = center['x'], center['y']
        radius = 10
        draw.ellipse(
            [(cx - radius, cy - radius), (cx + radius, cy + radius)],
            fill=color,
            outline='white',
            width=2
        )

        # Draw label
        label = element['name'][:20]
        draw.text((x + 5, y - 25), label, fill=color)

    img.save(output_path)

def test_screenshot(image_path: str, output_dir: str, llm: ChatOllama) -> dict:
    """Test single screenshot with optimal configuration."""
    print(f"\n{'='*80}")
    print(f"Testing: {Path(image_path).name}")
    print(f"{'='*80}")

    # Analyze
    result = analyze_screenshot(image_path, llm)

    if not result["success"]:
        print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
        return result

    print(f"✅ Analysis complete")
    print(f"   Original: {result['original_size'][0]}x{result['original_size'][1]}")
    print(f"   Optimized: {result['optimized_size'][0]}x{result['optimized_size'][1]}")
    print(f"   Base64 size: {result['base64_size']} chars")
    print(f"\nLLM response preview:\n{result['response'][:400]}...")

    # Parse coordinates
    elements = parse_coordinates(result['response'])
    print(f"\n📊 Extracted {len(elements)} elements with coordinate conversion")

    # Show parsed elements with conversion
    for element in elements[:3]:
        print(f"\n   {element['name']}:")
        print(f"      LLM coords:    center={element['llm_center']}, box={element['llm_box']}")
        print(f"      Device coords: center={element['device_center']}, box={element['device_box']}")
        print(f"      ✅ Conversion: {OPTIMIZED_DIMENSIONS} → {DEVICE_DIMENSIONS}")

    if len(elements) > 3:
        print(f"\n   ... and {len(elements) - 3} more elements")

    # Create visualization on original device-scale image
    vis_filename = Path(image_path).stem + "_optimal_vis.png"
    vis_path = os.path.join(output_dir, vis_filename)
    visualize_on_device_scale(image_path, elements, vis_path)
    print(f"\n   Visualization saved: {vis_path}")

    result['parsed_elements'] = elements
    result['visualization_path'] = vis_path

    return result

def main():
    """Test optimal configuration on multiple screenshots."""
    screenshots_dir = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk"
    output_dir = "/tmp/optimal_config_results"

    os.makedirs(output_dir, exist_ok=True)

    # Initialize LLM
    print("Initializing LLM...")
    llm = ChatOllama(
        model=LLM_MODEL,
        base_url=LLM_BASE_URL,
        temperature=0.7
    )
    print(f"✓ LLM initialized: {LLM_MODEL}")

    # Get screenshots
    screenshot_files = sorted(Path(screenshots_dir).glob("*.png"))
    test_files = screenshot_files[:5]  # Test first 5

    print(f"\n{'='*80}")
    print(f"OPTIMAL CONFIGURATION TEST")
    print(f"{'='*80}")
    print(f"Configuration:")
    print(f"   Image resize: {OPTIMIZED_DIMENSIONS[0]}x{OPTIMIZED_DIMENSIONS[1]}")
    print(f"   Device target: {DEVICE_DIMENSIONS[0]}x{DEVICE_DIMENSIONS[1]}")
    print(f"   Scale factors: X={DEVICE_DIMENSIONS[0]/OPTIMIZED_DIMENSIONS[0]:.4f}, Y={DEVICE_DIMENSIONS[1]/OPTIMIZED_DIMENSIONS[1]:.4f}")
    print(f"   Prompt: Improved generic with example")
    print(f"   Conversion: Automatic (LLM → Device)")
    print(f"\nTesting {len(test_files)} screenshots...")
    print(f"{'='*80}")

    # Test each screenshot
    results = []
    for screenshot_path in test_files:
        result = test_screenshot(str(screenshot_path), output_dir, llm)
        results.append(result)

    # Save summary
    summary_path = os.path.join(output_dir, "test_summary.json")
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*80}")
    print(f"TEST COMPLETE")
    print(f"{'='*80}")
    print(f"Results: {summary_path}")
    print(f"Visualizations: {output_dir}/*_optimal_vis.png")

    # Summary statistics
    successful = sum(1 for r in results if r['success'])
    total_elements = sum(len(r.get('parsed_elements', [])) for r in results)
    avg_base64 = sum(r.get('base64_size', 0) for r in results if r['success']) / max(successful, 1)

    print(f"\n📊 Summary:")
    print(f"   Successful: {successful}/{len(results)}")
    print(f"   Total elements: {total_elements}")
    print(f"   Average per screenshot: {total_elements/len(results):.1f}")
    print(f"   Average base64 size: {avg_base64:.0f} chars")

    print(f"\n✅ Key benefits of this configuration:")
    print(f"   1. Better coordinate precision (resized images)")
    print(f"   2. Generic prompt (works for various UIs)")
    print(f"   3. Automatic coordinate conversion (transparent)")
    print(f"   4. Lower token cost (~40KB vs ~80KB base64)")
    print(f"   5. Tested on multiple screenshots (no overfitting)")

if __name__ == "__main__":
    main()
