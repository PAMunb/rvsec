"""
Test Qwen3-VL with official mobile_agent.ipynb format.

This test uses the EXACT system prompt and parsing approach from:
https://github.com/QwenLM/Qwen3-VL/blob/main/cookbooks/mobile_agent.ipynb

Goal: Validate if XML <tool_call> format works with vLLM.
"""

import json
import base64
from openai import OpenAI
from PIL import Image


def encode_image(image_path):
    """Encode image to base64."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def test_qwen3vl_official_format():
    """Test using official Qwen3-VL format."""

    print("="*80)
    print("🧪 Testing Qwen3-VL Official Format (mobile_agent.ipynb)")
    print("="*80)

    # System prompt from official notebook (EXACT copy)
    system_prompt = """

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{"type": "function", "function": {"name": "mobile_use", "description": "Use a touchscreen to interact with a mobile device, and take screenshots.\\n* This is an interface to a mobile device with touchscreen. You can perform actions like clicking, typing, swiping, etc.\\n* Some applications may take time to start or process actions, so you may need to wait and take successive screenshots to see the results of your actions.\\n* The screen's resolution is 1080x1920.\\n* Make sure to click any buttons, links, icons, etc with the cursor tip in the center of the element. Don't click boxes on their edges unless asked.", "parameters": {"properties": {"action": {"description": "The action to perform. The available actions are:\\n* `click`: Click the point on the screen with coordinate (x, y).\\n* `type`: Input the specified text into the activated input box.\\n* `swipe`: Swipe from the starting point with coordinate (x, y) to the end point with coordinates2 (x2, y2).\\n* `back`: Press the back button.\\n* `home`: Press the home button.\\n* `enter`: Press the enter button.", "enum": ["click", "type", "swipe", "back", "home", "enter"], "type": "string"}, "coordinate": {"description": "(x, y): The x (pixels from the left edge) and y (pixels from the top edge) coordinates. Required only by `action=click` and `action=swipe`.", "type": "array"}, "coordinate2": {"description": "(x, y): The end point coordinates. Required only by `action=swipe`.", "type": "array"}, "text": {"description": "Required only by `action=type`.", "type": "string"}}, "required": ["action"], "type": "object"}}}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>

# Response format

Response format for every step:
1) Thought: one concise sentence explaining the next move (no multi-step reasoning).
2) Action: a short imperative describing what to do in the UI.
3) A single <tool_call>...</tool_call> block containing only the JSON: {"name": <function-name>, "arguments": <args-json-object>}.

Rules:
- Output exactly in the order: Thought, Action, <tool_call>.
- Be brief: one sentence for Thought, one for Action.
- Do not output anything else outside those three parts.
"""

    # Use a test screenshot (you can replace with actual path)
    screenshot_path = "/tmp/test_screenshot.png"

    # Create a dummy screenshot if doesn't exist
    if not os.path.exists(screenshot_path):
        img = Image.new('RGB', (1080, 1920), color='white')
        img.save(screenshot_path)
        print(f"Created dummy screenshot: {screenshot_path}")

    base64_image = encode_image(screenshot_path)

    # User query
    instruction = "Click on the search button"
    user_query = f"The user query: {instruction}."

    print(f"\n📝 Instruction: {instruction}")
    print(f"🖼️  Screenshot: {screenshot_path}")

    # Initialize OpenAI client pointing to vLLM
    client = OpenAI(
        api_key="EMPTY",
        base_url="http://localhost:8000/v1",
    )

    # Build messages in OpenAI format
    messages = [
        {
            "role": "system",
            "content": [
                {"type": "text", "text": system_prompt},
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_query},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                },
            ],
        }
    ]

    print("\n🌐 Calling vLLM with official format...")

    # Call LLM
    completion = client.chat.completions.create(
        model="./models/qwen3-vl-4b-fp8",
        messages=messages,
        temperature=0.1,
        max_tokens=512,
    )

    output_text = completion.choices[0].message.content

    print("\n" + "="*80)
    print("📬 RAW LLM RESPONSE:")
    print("="*80)
    print(output_text)
    print("="*80)

    # Parse action using official parsing approach
    try:
        # Official parsing: split by <tool_call> tags
        if '<tool_call>' in output_text and '</tool_call>' in output_text:
            tool_call_text = output_text.split('<tool_call>\n')[1].split('\n</tool_call>')[0]
            action = json.loads(tool_call_text)

            print("\n✅ Successfully parsed action:")
            print(json.dumps(action, indent=2))

            print(f"\n🎯 Action type: {action['arguments']['action']}")
            if 'coordinate' in action['arguments']:
                print(f"📍 Coordinates: {action['arguments']['coordinate']}")
            if 'text' in action['arguments']:
                print(f"✍️  Text: {action['arguments']['text']}")

            return True
        else:
            print("\n❌ No <tool_call> tags found in response")
            print("Response does not follow expected format")
            return False

    except Exception as e:
        print(f"\n❌ Failed to parse action: {e}")
        print(f"Error type: {type(e).__name__}")
        return False


if __name__ == "__main__":
    import os

    success = test_qwen3vl_official_format()

    print("\n" + "="*80)
    if success:
        print("✅ TEST PASSED: Official format works with vLLM!")
        print("Next step: Integrate this format into rv_agent prompts")
    else:
        print("❌ TEST FAILED: Format not working as expected")
        print("Need to investigate further")
    print("="*80)
