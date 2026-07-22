#!/usr/bin/env python3
"""
Test script to evaluate LLM coordinate extraction without image resizing.
Tests on multiple screenshots with a generic prompt to avoid overfitting.
"""

import os
import base64
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

# LLM Configuration
LLM_BASE_URL = "http://localhost:11434"
LLM_MODEL = "qwen-vision-tools-v1"

def encode_image_to_base64(image_path: str) -> str:
    """Encode image to base64 without resizing."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_image_dimensions(image_path: str) -> tuple[int, int]:
    """Get original image dimensions."""
    img = Image.open(image_path)
    return img.size  # (width, height)

def analyze_screenshot_generic_prompt(image_path: str, image_b64: str, width: int, height: int, llm: ChatOllama) -> dict:
    """
    Analyze screenshot with GENERIC prompt (no overfitting).

    Args:
        image_path: Path to screenshot
        image_b64: Base64 encoded image
        width: Image width in pixels
        height: Image height in pixels
        llm: ChatOllama instance

    Returns:
        Dict with LLM response and metadata
    """

    # GENERIC PROMPT - works for any Android screenshot
    prompt = f"""Analyze this Android application screenshot and identify all interactive UI elements.

The image dimensions are {width}x{height} pixels.

For each clickable element (buttons, text fields, tabs, icons, etc), provide:
1. Element name or text label
2. Center coordinates as: center=(x, y)
3. Bounding box as: box=(x, y, width, height)

Use this exact format for each element:
- ELEMENT_NAME: center=(x, y), box=(x, y, w, h)

Provide precise pixel coordinates relative to the {width}x{height} image."""

    # Call LLM using LangChain
    try:
        message_content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
        ]

        messages = [
            SystemMessage("You are an expert in Android UI analysis, identifying UI elements and their precise coordinates."),
            HumanMessage(content=message_content)
        ]

        response = llm.invoke(messages)
        llm_response = response.content

        return {
            "success": True,
            "image_path": image_path,
            "dimensions": {"width": width, "height": height},
            "prompt_type": "generic",
            "resized": False,
            "response": llm_response,
            "metadata": response.response_metadata if hasattr(response, 'response_metadata') else None
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Exception: {str(e)}",
            "image_path": image_path
        }

def parse_coordinates_from_response(response_text: str) -> list[dict]:
    """
    Extract coordinates from LLM response.

    Returns:
        List of dicts with parsed element data
    """
    elements = []
    lines = response_text.split('\n')

    for line in lines:
        line = line.strip()
        if not line or not ':' in line:
            continue

        # Look for pattern: "ELEMENT_NAME: center=(x, y), box=(x, y, w, h)"
        if 'center=' in line and 'box=' in line:
            try:
                # Extract element name
                name_part = line.split(':')[0].strip('- ').strip()

                # Extract center
                center_start = line.find('center=(') + 8
                center_end = line.find(')', center_start)
                center_str = line[center_start:center_end]
                center_x, center_y = map(int, center_str.split(','))

                # Extract box
                box_start = line.find('box=(') + 5
                box_end = line.find(')', box_start)
                box_str = line[box_start:box_end]
                box_parts = [int(x.strip()) for x in box_str.split(',')]

                if len(box_parts) == 4:
                    elements.append({
                        "name": name_part,
                        "center": {"x": center_x, "y": center_y},
                        "box": {
                            "x": box_parts[0],
                            "y": box_parts[1],
                            "width": box_parts[2],
                            "height": box_parts[3]
                        }
                    })
            except:
                continue

    return elements

def visualize_coordinates(image_path: str, elements: list[dict], output_path: str):
    """Create visualization with bounding boxes and centers."""
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)

    colors = ['lime', 'cyan', 'yellow', 'magenta', 'orange']

    for idx, element in enumerate(elements):
        color = colors[idx % len(colors)]

        # Draw bounding box
        box = element['box']
        x, y, w, h = box['x'], box['y'], box['width'], box['height']
        draw.rectangle([(x, y), (x + w, y + h)], outline=color, width=3)

        # Draw center point
        center = element['center']
        cx, cy = center['x'], center['y']
        radius = 8
        draw.ellipse(
            [(cx - radius, cy - radius), (cx + radius, cy + radius)],
            fill=color,
            outline='white',
            width=2
        )

        # Draw label
        label = f"{element['name'][:20]}"
        draw.text((x + 5, y - 20), label, fill=color)

    img.save(output_path)
    print(f"   Visualization saved: {output_path}")

def test_screenshot(image_path: str, output_dir: str, llm: ChatOllama) -> dict:
    """Test single screenshot with full resolution."""
    print(f"\n{'='*80}")
    print(f"Testing: {Path(image_path).name}")
    print(f"{'='*80}")

    # Get original dimensions
    width, height = get_image_dimensions(image_path)
    print(f"Original dimensions: {width}x{height}")

    # Encode image (no resize)
    image_b64 = encode_image_to_base64(image_path)
    print(f"Base64 size: {len(image_b64)} chars")

    # Analyze with generic prompt
    print(f"Analyzing with GENERIC prompt...")
    result = analyze_screenshot_generic_prompt(image_path, image_b64, width, height, llm)

    if not result["success"]:
        print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
        return result

    print(f"✅ LLM response received")
    print(f"\nResponse preview:\n{result['response'][:500]}...")

    # Parse coordinates
    elements = parse_coordinates_from_response(result['response'])
    print(f"\n📊 Extracted {len(elements)} elements with coordinates")

    # Show parsed elements
    for element in elements[:5]:  # Show first 5
        print(f"   - {element['name']}: center={element['center']}, box={element['box']}")

    if len(elements) > 5:
        print(f"   ... and {len(elements) - 5} more")

    # Create visualization
    vis_filename = Path(image_path).stem + "_fullres_vis.png"
    vis_path = os.path.join(output_dir, vis_filename)
    visualize_coordinates(image_path, elements, vis_path)

    # Add parsed data to result
    result['parsed_elements'] = elements
    result['visualization_path'] = vis_path

    return result

def main():
    """Test multiple screenshots."""
    screenshots_dir = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk"
    output_dir = "/tmp/fullres_test_results"

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Initialize LLM
    print("Initializing LLM...")
    llm = ChatOllama(
        model=LLM_MODEL,
        base_url=LLM_BASE_URL,
        temperature=0.7
    )
    print(f"✓ LLM initialized: {LLM_MODEL}")

    # Get all screenshots
    screenshot_files = sorted(Path(screenshots_dir).glob("*.png"))

    # Test subset (first 5 screenshots to avoid long execution)
    test_files = screenshot_files[:5]

    print(f"\n{'='*80}")
    print(f"FULL RESOLUTION TEST - NO IMAGE RESIZING")
    print(f"{'='*80}")
    print(f"Screenshots directory: {screenshots_dir}")
    print(f"Total screenshots: {len(screenshot_files)}")
    print(f"Testing first {len(test_files)} screenshots")
    print(f"Output directory: {output_dir}")
    print(f"Prompt: GENERIC (no overfitting)")
    print(f"{'='*80}")

    # Test each screenshot
    results = []
    for screenshot_path in test_files:
        result = test_screenshot(str(screenshot_path), output_dir, llm)
        results.append(result)

    # Save results summary
    summary_path = os.path.join(output_dir, "test_summary.json")
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*80}")
    print(f"TEST COMPLETE")
    print(f"{'='*80}")
    print(f"Results saved: {summary_path}")
    print(f"Visualizations saved: {output_dir}/*.png")

    # Summary statistics
    successful = sum(1 for r in results if r['success'])
    total_elements = sum(len(r.get('parsed_elements', [])) for r in results)

    print(f"\n📊 Summary:")
    print(f"   Successful: {successful}/{len(results)}")
    print(f"   Total elements extracted: {total_elements}")
    print(f"   Average per screenshot: {total_elements/len(results):.1f}")

    print(f"\n💡 Key differences from previous approach:")
    print(f"   ✓ NO image resizing (original {get_image_dimensions(str(test_files[0]))[0]}x{get_image_dimensions(str(test_files[0]))[1]})")
    print(f"   ✓ GENERIC prompt (works for any Android screenshot)")
    print(f"   ✓ Multiple screenshots tested (avoids overfitting)")
    print(f"   ✓ Visualizations show coordinate accuracy")

if __name__ == "__main__":
    main()
