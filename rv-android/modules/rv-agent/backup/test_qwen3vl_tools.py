"""
Test Qwen3-VL Tool Calling Capabilities

Tests qwen3-vl:4b and qwen3-vl:8b with:
1. Tool calling without image (datetime)
2. Tool calling with image (UI element click)

References:
- https://ollama.com/library/qwen3-vl
- Custom Modelfiles for tool calling in this directory
"""

import base64
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ollama import chat

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================================
# FAKE TOOLS (for testing)
# ============================================================================

def get_current_datetime() -> Dict[str, str]:
    """
    Get current date and time.

    Returns:
        Dict with 'date', 'time', 'day_of_week'
    """
    now = datetime.now()
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day_of_week": now.strftime("%A"),
        "timestamp": now.isoformat()
    }


def android_click(element_description: str, x: int, y: int) -> Dict[str, Any]:
    """
    Fake Android click tool.

    Args:
        element_description: Description of element to click
        x: X coordinate
        y: Y coordinate

    Returns:
        Success status
    """
    logger.info(f"🖱️  FAKE CLICK: '{element_description}' at ({x}, {y})")
    return {
        "success": True,
        "element": element_description,
        "coords": (x, y),
        "message": f"Clicked '{element_description}' at coordinates ({x}, {y})"
    }


# ============================================================================
# TOOL DEFINITIONS (for Ollama)
# ============================================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_datetime",
            "description": "Get the current date and time",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "android_click",
            "description": "Click on an Android UI element at specified coordinates",
            "parameters": {
                "type": "object",
                "properties": {
                    "element_description": {
                        "type": "string",
                        "description": "Description of the UI element to click"
                    },
                    "x": {
                        "type": "integer",
                        "description": "X coordinate of the element center"
                    },
                    "y": {
                        "type": "integer",
                        "description": "Y coordinate of the element center"
                    }
                },
                "required": ["element_description", "x", "y"]
            }
        }
    }
]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_image_base64(image_path: str) -> str:
    """Load image and convert to base64"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def execute_tool_call(tool_call: Dict) -> Any:
    """Execute a tool call and return result"""
    function_name = tool_call['function']['name']

    # DEBUG: Show raw arguments type and value
    raw_arguments = tool_call['function']['arguments']
    logger.info(f"🔧 Executing tool: {function_name}")
    logger.info(f"   Raw arguments type: {type(raw_arguments)}")
    logger.info(f"   Raw arguments value: {raw_arguments}")

    # Handle both dict and string formats
    if isinstance(raw_arguments, dict):
        arguments = raw_arguments
        logger.info(f"   ✅ Arguments already parsed as dict")
    else:
        arguments = json.loads(raw_arguments)
        logger.info(f"   ✅ Arguments parsed from JSON string")

    logger.info(f"   Final arguments: {arguments}")

    if function_name == "get_current_datetime":
        return get_current_datetime()
    elif function_name == "android_click":
        return android_click(**arguments)
    else:
        raise ValueError(f"Unknown tool: {function_name}")


def print_section(title: str):
    """Print section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_result(label: str, value: Any):
    """Print result with formatting"""
    print(f"\n{label}:")
    if isinstance(value, dict):
        print(json.dumps(value, indent=2, ensure_ascii=False))
    else:
        print(f"  {value}")


# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def test_without_image(model: str):
    """
    Test 1: Tool calling without image

    Question: "Que dia é hoje?"
    Expected: Should call get_current_datetime() tool
    """
    print_section(f"TEST 1: Tool Calling WITHOUT Image - {model}")

    messages = [
        {
            "role": "user",
            "content": "Que dia é hoje? Use a ferramenta disponível para descobrir."
        }
    ]

    logger.info(f"🤖 Testing {model} without image...")
    logger.info(f"   Question: {messages[0]['content']}")

    try:
        response = chat(
            model=model,
            messages=messages,
            tools=TOOLS,
        )

        # DEBUG: Print full response (ChatResponse object)
        logger.info("=" * 80)
        logger.info("🔍 FULL RESPONSE DEBUG:")
        logger.info(f"   Response type: {type(response)}")
        logger.info(f"   Response dir: {[attr for attr in dir(response) if not attr.startswith('_')]}")
        logger.info(f"   Message type: {type(response.message)}")
        logger.info(f"   Message dir: {[attr for attr in dir(response.message) if not attr.startswith('_')]}")
        logger.info(f"   Message content: {getattr(response.message, 'content', '[No content]')}")

        # Check for tool_calls attribute
        if hasattr(response.message, 'tool_calls') and response.message.tool_calls:
            logger.info(f"   Tool calls found: {len(response.message.tool_calls)}")
            # Convert to dict for JSON serialization
            tool_calls_list = []
            for tc in response.message.tool_calls:
                tool_calls_list.append({
                    'function': {
                        'name': tc.function.name,
                        'arguments': tc.function.arguments
                    }
                })
            logger.info(f"   Tool calls structure: {json.dumps(tool_calls_list, indent=2, ensure_ascii=False)}")
        else:
            logger.info(f"   Tool calls: None")
        logger.info("=" * 80)

        # Print response
        print_result("Response message", getattr(response.message, 'content', '[No content]'))

        # Check if tool was called
        if hasattr(response.message, 'tool_calls') and response.message.tool_calls:
            print("\n✅ Tool calls detected:")
            for i, tool_call in enumerate(response.message.tool_calls, 1):
                print(f"\n  Tool Call #{i}:")
                print(f"    Function: {tool_call['function']['name']}")
                print(f"    Arguments: {tool_call['function']['arguments']}")

                # Execute tool
                result = execute_tool_call(tool_call)
                print_result(f"    Result", result)

                # Add tool result to messages and get final response
                messages.append(response.message)
                messages.append({
                    "role": "tool",
                    "content": json.dumps(result)
                })

                final_response = chat(
                    model=model,
                    messages=messages
                )

                print_result("  Final response", final_response.message.content)
        else:
            print("\n❌ No tool calls detected")
            print("   Model may not support tool calling or needs custom template")

        return response

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        print(f"\n❌ ERROR: {e}")
        return None


def test_with_image(model: str, image_path: str):
    """
    Test 2: Tool calling with image

    Image: CryptoApp screenshot with MESSAGE DIGEST button
    Question: "Clique no botão MESSAGE DIGEST"
    Expected: Should call android_click() with correct coordinates
    """
    print_section(f"TEST 2: Tool Calling WITH Image - {model}")

    # Load image
    logger.info(f"📷 Loading image: {image_path}")
    image_b64 = load_image_base64(image_path)

    messages = [
        {
            "role": "user",
            "content": "Analyze this Android app screenshot and click on the 'MESSAGE DIGEST' button. Use the android_click tool with the button coordinates.",
            "images": [image_b64]
        }
    ]

    logger.info(f"🤖 Testing {model} with image...")
    logger.info(f"   Image: {Path(image_path).name}")
    logger.info(f"   Image size (base64): {len(image_b64)} chars")
    logger.info(f"   Question: Click MESSAGE DIGEST button")

    try:
        response = chat(
            model=model,
            messages=messages,
            tools=TOOLS,
        )

        # DEBUG: Print full response (ChatResponse object)
        logger.info("=" * 80)
        logger.info("🔍 FULL RESPONSE DEBUG:")
        logger.info(f"   Response type: {type(response)}")
        logger.info(f"   Response dir: {[attr for attr in dir(response) if not attr.startswith('_')]}")
        logger.info(f"   Message type: {type(response.message)}")
        logger.info(f"   Message dir: {[attr for attr in dir(response.message) if not attr.startswith('_')]}")
        logger.info(f"   Message content: {getattr(response.message, 'content', '[No content]')}")

        # Check for tool_calls attribute
        if hasattr(response.message, 'tool_calls') and response.message.tool_calls:
            logger.info(f"   Tool calls found: {len(response.message.tool_calls)}")
            # Convert to dict for JSON serialization
            tool_calls_list = []
            for tc in response.message.tool_calls:
                tool_calls_list.append({
                    'function': {
                        'name': tc.function.name,
                        'arguments': tc.function.arguments
                    }
                })
            logger.info(f"   Tool calls structure: {json.dumps(tool_calls_list, indent=2, ensure_ascii=False)}")
        else:
            logger.info(f"   Tool calls: None")
        logger.info("=" * 80)

        # Print response
        print_result("Response message", getattr(response.message, 'content', '[No content]'))

        # Check if tool was called
        if hasattr(response.message, 'tool_calls') and response.message.tool_calls:
            print("\n✅ Tool calls detected:")
            for i, tool_call in enumerate(response.message.tool_calls, 1):
                print(f"\n  Tool Call #{i}:")
                print(f"    Function: {tool_call['function']['name']}")
                print(f"    Arguments: {tool_call['function']['arguments']}")

                # Execute tool
                result = execute_tool_call(tool_call)
                print_result(f"    Result", result)

                # Validate coordinates (MESSAGE DIGEST button is roughly at 540, 273)
                if tool_call['function']['name'] == 'android_click':
                    args = json.loads(tool_call['function']['arguments'])
                    expected_x, expected_y = 540, 273
                    tolerance = 100

                    x_diff = abs(args['x'] - expected_x)
                    y_diff = abs(args['y'] - expected_y)

                    if x_diff <= tolerance and y_diff <= tolerance:
                        print(f"\n  ✅ Coordinates ACCURATE!")
                        print(f"     Expected: ({expected_x}, {expected_y})")
                        print(f"     Got: ({args['x']}, {args['y']})")
                        print(f"     Difference: ({x_diff}px, {y_diff}px)")
                    else:
                        print(f"\n  ⚠️  Coordinates may be OFF")
                        print(f"     Expected: ({expected_x}, {expected_y})")
                        print(f"     Got: ({args['x']}, {args['y']})")
                        print(f"     Difference: ({x_diff}px, {y_diff}px)")

                # Add tool result to messages and get final response
                messages.append(response.message)
                messages.append({
                    "role": "tool",
                    "content": json.dumps(result)
                })

                final_response = chat(
                    model=model,
                    messages=messages
                )

                print_result("  Final response", final_response.message.content)
        else:
            print("\n❌ No tool calls detected")
            print("   Model response may be text-only")

        return response

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        print(f"\n❌ ERROR: {e}")
        return None


def test_vision_only(model: str, image_path: str):
    """
    Test 3: Vision understanding without tools

    Just verify the model can see and understand the image
    """
    print_section(f"TEST 3: Vision Understanding (No Tools) - {model}")

    image_b64 = load_image_base64(image_path)

    messages = [
        {
            "role": "user",
            "content": "Describe this Android app screenshot. What UI elements do you see? List the buttons and their approximate positions.",
            "images": [image_b64]
        }
    ]

    logger.info(f"🤖 Testing {model} vision understanding...")

    try:
        response = chat(
            model=model,
            messages=messages
        )

        print_result("Vision response", response.message.content)
        return response

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        print(f"\n❌ ERROR: {e}")
        return None


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Run all tests on both models"""

    # Configuration - Testing only 4b for initial validation
    models = [
        "qwen3-vl:4b",
        # "qwen3-vl:8b"  # Will test after 4b validation
    ]

    image_path = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/001.png"

    # Check image exists
    if not Path(image_path).exists():
        logger.error(f"Image not found: {image_path}")
        return

    print("\n" + "=" * 80)
    print("  QWEN3-VL TOOL CALLING TESTS")
    print("=" * 80)
    print(f"\nModels to test: {', '.join(models)}")
    print(f"Image: {Path(image_path).name}")
    print(f"Image resolution: 1080x1920 (CryptoApp)")

    results = {}

    for model in models:
        print("\n\n" + "🔵" * 40)
        print(f"  TESTING MODEL: {model}")
        print("🔵" * 40)

        results[model] = {}

        # Test 1: Without image
        results[model]['test1'] = test_without_image(model)

        # Test 2: With image
        results[model]['test2'] = test_with_image(model, image_path)

        # Test 3: Vision only
        results[model]['test3'] = test_vision_only(model, image_path)

    # Summary
    print_section("SUMMARY")

    for model in models:
        print(f"\n📊 {model}:")

        # Test 1
        test1 = results[model]['test1']
        if test1 and 'tool_calls' in test1['message']:
            print(f"  ✅ Test 1 (No Image + Tools): Tool calling WORKS")
        else:
            print(f"  ❌ Test 1 (No Image + Tools): No tool calls")

        # Test 2
        test2 = results[model]['test2']
        if test2 and 'tool_calls' in test2['message']:
            print(f"  ✅ Test 2 (Image + Tools): Tool calling WORKS")
        else:
            print(f"  ❌ Test 2 (Image + Tools): No tool calls")

        # Test 3
        test3 = results[model]['test3']
        if test3:
            print(f"  ✅ Test 3 (Vision Only): Response received")
        else:
            print(f"  ❌ Test 3 (Vision Only): Failed")

    print("\n" + "=" * 80)
    print("  TESTS COMPLETE")
    print("=" * 80)

    print("\n💡 Next Steps:")
    print("   - If tool calling doesn't work: Create custom Modelfile")
    print("   - If coordinates are off: Fine-tune prompt or use bounding boxes")
    print("   - Compare 4b vs 8b accuracy and speed")
    print(f"\n📄 References:")
    print(f"   - Modelfile examples: {Path(__file__).parent / 'Modelfile.qwen-vision-tools-v*'}")
    print(f"   - LangGraph integration: {Path(__file__).parent / 'TOOLS_LANGGRAPH.md'}")


if __name__ == "__main__":
    main()
