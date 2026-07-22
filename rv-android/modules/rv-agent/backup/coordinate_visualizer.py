#!/usr/bin/env python3
"""
Interactive Coordinate Visualizer with Gradio.

Visualizes LLM coordinates (optimized image) vs converted device coordinates (original image).
Helps validate the coordinate conversion pipeline.
"""

import gradio as gr
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from pathlib import Path

# Configuration
OPTIMIZED_DIMENSIONS = (724, 1288)
DEVICE_DIMENSIONS = (1080, 1920)
SCALE_X = DEVICE_DIMENSIONS[0] / OPTIMIZED_DIMENSIONS[0]  # 1.4917
SCALE_Y = DEVICE_DIMENSIONS[1] / OPTIMIZED_DIMENSIONS[1]  # 1.4907


def draw_click_marker(img: Image.Image, x: int, y: int, color: str = "red", label: str = "") -> Image.Image:
    """
    Draw a click marker (crosshair + circle) on image.

    Args:
        img: PIL Image
        x, y: Click coordinates
        color: Marker color
        label: Text label to display

    Returns:
        Image with marker drawn
    """
    img_copy = img.copy()
    draw = ImageDraw.Draw(img_copy)

    # Draw center circle
    radius = 15
    draw.ellipse(
        [(x - radius, y - radius), (x + radius, y + radius)],
        outline=color,
        width=4
    )

    # Draw center point
    draw.ellipse(
        [(x - 3, y - 3), (x + 3, y + 3)],
        fill=color
    )

    # Draw crosshair
    crosshair_size = 30
    draw.line([(x - crosshair_size, y), (x + crosshair_size, y)], fill=color, width=3)
    draw.line([(x, y - crosshair_size), (x, y + crosshair_size)], fill=color, width=3)

    # Draw label if provided
    if label:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        except:
            font = ImageFont.load_default()

        # Draw text background
        text_bbox = draw.textbbox((x + 25, y - 40), label, font=font)
        draw.rectangle(text_bbox, fill="black")
        draw.text((x + 25, y - 40), label, fill=color, font=font)

    return img_copy


def visualize_coordinates(image_path: str, llm_x: int, llm_y: int) -> tuple:
    """
    Main visualization function.

    Args:
        image_path: Path to original screenshot
        llm_x: X coordinate from LLM (optimized image scale)
        llm_y: Y coordinate from LLM (optimized image scale)

    Returns:
        Tuple of (optimized_image, original_image, info_text)
    """
    try:
        # Validate image path
        if not Path(image_path).exists():
            return None, None, f"❌ Error: File not found: {image_path}"

        # Load original image
        original_img = Image.open(image_path)
        original_size = original_img.size

        # Create optimized version (resize)
        optimized_img = original_img.resize(OPTIMIZED_DIMENSIONS, Image.Resampling.LANCZOS)

        # Validate coordinates are within bounds
        if not (0 <= llm_x < OPTIMIZED_DIMENSIONS[0] and 0 <= llm_y < OPTIMIZED_DIMENSIONS[1]):
            return None, None, f"❌ Error: Coordinates ({llm_x}, {llm_y}) out of bounds for optimized image {OPTIMIZED_DIMENSIONS}"

        # Convert coordinates to device scale
        device_x = int(llm_x * SCALE_X)
        device_y = int(llm_y * SCALE_Y)

        # Validate converted coordinates
        if not (0 <= device_x < original_size[0] and 0 <= device_y < original_size[1]):
            return None, None, f"❌ Error: Converted coordinates ({device_x}, {device_y}) out of bounds for original image {original_size}"

        # Draw markers
        optimized_with_marker = draw_click_marker(
            optimized_img,
            llm_x,
            llm_y,
            color="lime",
            label=f"LLM: ({llm_x}, {llm_y})"
        )

        original_with_marker = draw_click_marker(
            original_img,
            device_x,
            device_y,
            color="red",
            label=f"Device: ({device_x}, {device_y})"
        )

        # Create info text
        info = f"""✅ Coordinate Conversion Successful!

📊 Image Information:
   Original:  {original_size[0]}x{original_size[1]} pixels
   Optimized: {OPTIMIZED_DIMENSIONS[0]}x{OPTIMIZED_DIMENSIONS[1]} pixels

🔄 Scale Factors:
   X: {SCALE_X:.4f}
   Y: {SCALE_Y:.4f}

📍 LLM Coordinates (Optimized Image):
   Click at: ({llm_x}, {llm_y})
   ✅ Valid for {OPTIMIZED_DIMENSIONS[0]}x{OPTIMIZED_DIMENSIONS[1]} image

🎯 Device Coordinates (Original Image):
   Converted to: ({device_x}, {device_y})
   ✅ Valid for {original_size[0]}x{original_size[1]} image

🔍 Conversion Formula:
   device_x = llm_x × {SCALE_X:.4f} = {llm_x} × {SCALE_X:.4f} = {device_x}
   device_y = llm_y × {SCALE_Y:.4f} = {llm_y} × {SCALE_Y:.4f} = {device_y}

💡 Usage:
   - Green marker (LEFT):  LLM sees this in optimized image
   - Red marker (RIGHT):   android_click() clicks here on device
"""

        return optimized_with_marker, original_with_marker, info

    except Exception as e:
        return None, None, f"❌ Error: {str(e)}"


def create_gradio_interface():
    """Create Gradio interface for coordinate visualization."""

    # Example screenshots for quick testing
    example_dir = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk"
    examples = []

    if Path(example_dir).exists():
        screenshots = sorted(Path(example_dir).glob("*.png"))[:5]
        # Add examples with known good coordinates
        examples = [
            [str(screenshots[0]), 362, 181],  # MESSAGE DIGEST button center
            [str(screenshots[0]), 362, 331],  # CIPHER button center
            [str(screenshots[0]), 362, 481],  # GENERATED button center
        ] if screenshots else []

    # Create interface
    with gr.Blocks(title="RV-Agent Coordinate Visualizer") as demo:
        gr.Markdown("""
        # 🎯 RV-Agent Coordinate Visualizer

        Visualize coordinate conversion from **LLM scale** (724x1288 optimized image)
        to **Device scale** (1080x1920 original image).

        This tool helps validate that `android_click()` correctly converts coordinates!
        """)

        with gr.Row():
            with gr.Column():
                gr.Markdown("### 📥 Input Parameters")

                image_path_input = gr.Textbox(
                    label="Screenshot Path",
                    placeholder="/path/to/screenshot.png",
                    info="Path to the original screenshot (1080x1920)"
                )

                with gr.Row():
                    llm_x_input = gr.Number(
                        label="LLM X Coordinate",
                        value=362,
                        precision=0,
                        info="X coordinate from LLM (0-724)"
                    )
                    llm_y_input = gr.Number(
                        label="LLM Y Coordinate",
                        value=181,
                        precision=0,
                        info="Y coordinate from LLM (0-1288)"
                    )

                visualize_btn = gr.Button("🔍 Visualize Conversion", variant="primary")

                gr.Markdown("""
                ### 📋 Quick Guide

                1. **Screenshot Path**: Paste the path to your original screenshot
                2. **LLM Coordinates**: Enter the x,y coordinates provided by the LLM
                   - These are relative to the optimized image (724x1288)
                   - Example: MESSAGE DIGEST button center = (362, 181)
                3. Click **Visualize** to see both views

                **Note**: Use examples below for quick testing!
                """)

        with gr.Row():
            with gr.Column():
                gr.Markdown("### 🟢 Optimized Image (LLM View)")
                gr.Markdown("*This is what the LLM sees (724x1288)*")
                optimized_output = gr.Image(
                    label="Optimized Image (724x1288)",
                    type="pil"
                )

            with gr.Column():
                gr.Markdown("### 🔴 Original Image (Device View)")
                gr.Markdown("*This is where android_click() clicks (1080x1920)*")
                original_output = gr.Image(
                    label="Original Image (1080x1920)",
                    type="pil"
                )

        with gr.Row():
            info_output = gr.Textbox(
                label="📊 Conversion Information",
                lines=25,
                max_lines=30
            )

        # Connect button to function
        visualize_btn.click(
            fn=visualize_coordinates,
            inputs=[image_path_input, llm_x_input, llm_y_input],
            outputs=[optimized_output, original_output, info_output]
        )

        # Add examples if available
        if examples:
            gr.Markdown("### 📚 Example Coordinates (CryptoApp)")
            gr.Examples(
                examples=examples,
                inputs=[image_path_input, llm_x_input, llm_y_input],
                outputs=[optimized_output, original_output, info_output],
                fn=visualize_coordinates,
                cache_examples=False
            )

        gr.Markdown("""
        ---
        ### 🔧 Technical Details

        **Coordinate Conversion Pipeline:**
        ```
        1. LLM analyzes OPTIMIZED image (724x1288)
        2. LLM provides coordinates: (llm_x, llm_y)
        3. android_click() converts to DEVICE scale:
           - device_x = llm_x × 1.4917
           - device_y = llm_y × 1.4907
        4. Click executed at (device_x, device_y) on 1080x1920 screen
        ```

        **Color Legend:**
        - 🟢 **Green marker**: LLM coordinates on optimized image
        - 🔴 **Red marker**: Converted coordinates on original image

        **Files:**
        - Implementation: `android_tools.py:192-223`
        - Device interface: `device_interface.py:127-147`
        - Documentation: `COORDINATE_CONVERSION_SUMMARY.md`
        """)

    return demo


def main():
    """Launch Gradio interface."""
    print("="*80)
    print("🎯 RV-Agent Coordinate Visualizer")
    print("="*80)
    print(f"Configuration:")
    print(f"   Optimized dimensions: {OPTIMIZED_DIMENSIONS[0]}x{OPTIMIZED_DIMENSIONS[1]}")
    print(f"   Device dimensions:    {DEVICE_DIMENSIONS[0]}x{DEVICE_DIMENSIONS[1]}")
    print(f"   Scale factors:        X={SCALE_X:.4f}, Y={SCALE_Y:.4f}")
    print("="*80)

    demo = create_gradio_interface()

    # Launch with sharing disabled (local only)
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        inbrowser=True
    )


if __name__ == "__main__":
    main()
