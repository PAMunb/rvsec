#!/usr/bin/env python3
"""Quick test of vLLM server with Qwen3-VL-4B-FP8."""

import os
import sys
from openai import OpenAI

def test_text_only():
    """Test simple text query."""
    print("=" * 80)
    print("TEST 1: Simple Text Query")
    print("=" * 80)

    client = OpenAI(
        base_url="http://localhost:8000/v1",
        api_key="EMPTY"
    )

    try:
        response = client.chat.completions.create(
            model="./models/qwen3-vl-4b-fp8",
            messages=[
                {"role": "user", "content": "Say hello in one short sentence."}
            ],
            temperature=0.6,
            max_tokens=50,
            timeout=60.0
        )

        print(f"✅ Response received!")
        print(f"Content: {response.choices[0].message.content}")
        print(f"Finish reason: {response.choices[0].finish_reason}")
        print(f"Tokens: {response.usage.total_tokens}")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_vision_query():
    """Test vision query with screenshot."""
    print("\n" + "=" * 80)
    print("TEST 2: Vision Query (Screenshot Description)")
    print("=" * 80)

    # Use a screenshot if available
    screenshot_dir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-agent/screenshots"

    if not os.path.exists(screenshot_dir):
        print(f"⚠️  Screenshot directory not found: {screenshot_dir}")
        print("Skipping vision test")
        return None

    # Find first screenshot
    screenshots = [f for f in os.listdir(screenshot_dir) if f.endswith('.png')]
    if not screenshots:
        print(f"⚠️  No screenshots found in {screenshot_dir}")
        print("Skipping vision test")
        return None

    screenshot_path = os.path.join(screenshot_dir, screenshots[0])
    print(f"Using screenshot: {screenshot_path}")

    # Read and encode screenshot
    import base64
    with open(screenshot_path, 'rb') as f:
        screenshot_b64 = base64.b64encode(f.read()).decode('utf-8')

    client = OpenAI(
        base_url="http://localhost:8000/v1",
        api_key="EMPTY"
    )

    try:
        response = client.chat.completions.create(
            model="./models/qwen3-vl-4b-fp8",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this Android app screen in one sentence."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{screenshot_b64}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.6,
            max_tokens=100,
            timeout=60.0
        )

        print(f"✅ Response received!")
        print(f"Content: {response.choices[0].message.content}")
        print(f"Finish reason: {response.choices[0].finish_reason}")
        print(f"Tokens: {response.usage.total_tokens}")

        # Check for loop
        if response.choices[0].finish_reason == 'length':
            print("⚠️  WARNING: Finished due to 'length' (possible loop)")
        else:
            print(f"✅ Finish reason: {response.choices[0].finish_reason} (no loop)")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🧪 vLLM Quick Test - Qwen3-VL-4B-FP8\n")

    # Test 1: Simple text
    text_ok = test_text_only()

    if not text_ok:
        print("\n❌ Text test failed. Stopping.")
        sys.exit(1)

    # Test 2: Vision
    vision_ok = test_vision_query()

    if vision_ok is None:
        print("\n⚠️  Vision test skipped (no screenshots)")
    elif not vision_ok:
        print("\n❌ Vision test failed")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Text query: {'✅ PASS' if text_ok else '❌ FAIL'}")
    print(f"Vision query: {'✅ PASS' if vision_ok else '⚠️ SKIPPED' if vision_ok is None else '❌ FAIL'}")
    print("\nNext: Integrate with RVAgent in agent_factory.py")
