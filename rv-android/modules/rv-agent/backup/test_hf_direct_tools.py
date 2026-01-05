#!/usr/bin/env python3
"""
Test HuggingFace Transformers direct tool calling with Qwen3-VL.

This test bypasses vLLM and LangChain, using HuggingFace Transformers
directly with apply_chat_template(tools=...) for native tool calling support.
"""

import json
import re
import time
from pathlib import Path

import torch
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration, BitsAndBytesConfig
from qwen_vl_utils import process_vision_info


def android_click(x: int, y: int):
    """
    Click on a UI element at the specified coordinates.

    Args:
        x: X coordinate (pixels from left edge)
        y: Y coordinate (pixels from top edge)
    """
    pass


def android_type_text(x: int, y: int, text: str):
    """
    Type text into an input field.

    Args:
        x: X coordinate of the input field
        y: Y coordinate of the input field
        text: Text to type
    """
    pass


def android_scroll(direction: str):
    """
    Scroll the screen in a direction.

    Args:
        direction: Direction to scroll (choices: ["up", "down", "left", "right"])
    """
    pass


def android_back():
    """
    Press the back button.
    """
    pass


def android_home():
    """
    Press the home button.
    """
    pass


# Tool list
TOOLS = [android_click, android_type_text, android_scroll, android_back, android_home]


def parse_tool_calls_xml(response_text: str) -> list[dict]:
    """Parse tool calls from XML <tool_call> tags."""
    tool_calls = []

    xml_pattern = r'<tool_call>\s*(.+?)\s*</tool_call>'
    xml_matches = re.finditer(xml_pattern, response_text, re.DOTALL)

    for match in xml_matches:
        json_str = match.group(1)
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, dict) and 'name' in parsed:
                tool_calls.append({
                    'name': parsed['name'],
                    'args': parsed.get('arguments', parsed.get('parameters', parsed.get('args', {})))
                })
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse tool call JSON: {e}")
            print(f"   Raw JSON: {json_str}")

    return tool_calls


def test_hf_direct_cryptoapp():
    """Test HF Transformers direct tool calling with CryptoApp screenshot."""

    print("=" * 80)
    print("🧪 Testing HuggingFace Transformers Direct Tool Calling")
    print("=" * 80)

    # Find a screenshot
    screenshots_dir = Path(__file__).parent / "screenshots"
    screenshot_files = list(screenshots_dir.glob("*.png"))

    if not screenshot_files:
        print("❌ No screenshots found!")
        return

    screenshot_path = str(screenshot_files[0])
    print(f"📸 Using screenshot: {screenshot_path}")

    # Load model and processor
    print("\n🔄 Loading Qwen3-VL model and processor...")
    model_path = "./models/qwen3-vl-4b-fp8"

    start_load = time.time()

    # Load model with FP8 quantization (already in model) on GPU
    print("   Loading FP8 model on GPU...")
    processor = AutoProcessor.from_pretrained(model_path)
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        model_path,
        device_map="auto"
    )
    load_time = time.time() - start_load
    print(f"✅ Model loaded in {load_time:.2f}s (FP8 on GPU)")

    # System prompt
    system_prompt = """You are an Android UI testing agent for systematic application exploration.

COORDINATE SYSTEM:
- Screen resolution: 704x1248 pixels
- Use EXACT coordinates from UI element descriptions below

CRITICAL RULES:
1. One action at a time
2. Click only on visible, interactive elements
3. Prefer unexplored UI elements
4. Use coordinates from element descriptions

Response format:
1) Thought: one concise sentence explaining the next move
2) Action: a short imperative describing what to do
3) A single <tool_call>...</tool_call> block

Example:
Thought: I need to click the login button.
Action: Click on the "Login" button.
<tool_call>
{"name": "android_click", "arguments": {"x": 352, "y": 620}}
</tool_call>
"""

    # User query
    user_query = "What action should I take to explore this Android app screen?"

    # Create messages with image
    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": system_prompt}]
        },
        {
            "role": "user",
            "content": [
                {"type": "image", "image": screenshot_path},
                {"type": "text", "text": user_query}
            ]
        }
    ]

    print("\n🔄 Applying chat template with tools...")
    print(f"   Tools: {[tool.__name__ for tool in TOOLS]}")

    # Apply chat template with tools
    start_template = time.time()
    try:
        text = processor.apply_chat_template(
            messages,
            tools=TOOLS,  # ← Native tool calling support!
            tokenize=False,
            add_generation_prompt=True
        )

        image_inputs, video_inputs = process_vision_info(messages)

        inputs = processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt"
        )

        inputs = inputs.to(model.device)
        template_time = time.time() - start_template
        print(f"✅ Chat template applied in {template_time:.2f}s")

    except Exception as e:
        print(f"❌ Error applying chat template: {e}")
        import traceback
        traceback.print_exc()
        return

    # Generate response
    print("\n🤖 Generating response...")
    start_gen = time.time()

    with torch.no_grad():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.2,
            do_sample=True
        )

    gen_time = time.time() - start_gen

    # Decode response (only new tokens)
    generated_ids_trimmed = [
        out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    response_text = processor.batch_decode(
        generated_ids_trimmed,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False
    )[0]

    print(f"✅ Generated in {gen_time:.2f}s")

    # Print full response
    print("\n" + "=" * 80)
    print("📝 FULL LLM RESPONSE:")
    print("=" * 80)
    print(response_text)
    print("=" * 80)

    # Parse tool calls
    print("\n🔍 Parsing tool calls...")
    tool_calls = parse_tool_calls_xml(response_text)

    if tool_calls:
        print(f"✅ Extracted {len(tool_calls)} tool call(s):")
        for i, tc in enumerate(tool_calls, 1):
            print(f"\n   {i}. {tc['name']}")
            print(f"      Args: {json.dumps(tc['args'], indent=6)}")
    else:
        print("❌ No tool calls extracted!")

    # Performance summary
    print("\n" + "=" * 80)
    print("⏱️  PERFORMANCE SUMMARY:")
    print("=" * 80)
    print(f"Model Load:      {load_time:.2f}s")
    print(f"Template Apply:  {template_time:.2f}s")
    print(f"Generation:      {gen_time:.2f}s")
    print(f"TOTAL:           {load_time + template_time + gen_time:.2f}s")
    print("=" * 80)

    # Cleanup memory
    print("\n🧹 Cleaning up memory...")
    del model
    del processor
    del inputs
    del generated_ids
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    print("✅ Memory cleaned up")


if __name__ == "__main__":
    test_hf_direct_cryptoapp()
