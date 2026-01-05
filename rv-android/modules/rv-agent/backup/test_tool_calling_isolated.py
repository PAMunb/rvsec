"""
Isolated Tool Calling Test - qwen-vision-tools-v1 with CryptoApp

Purpose:
- Test if qwen-vision-tools-v1 generates tool calls with Android screenshot
- Isolate the tool calling mechanism from rv_agent complexity
- Determine if issue is in model or integration

Expected Result:
- Model should generate tool_calls in response
- At minimum, should call android_click or android_type_text
"""

import base64
import logging
from pathlib import Path
from typing import Dict, Any

from langchain_core.tools import tool
from langchain_ollama import ChatOllama

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)


# Define 3 Android tools with clear docstrings
@tool
def android_click(element_description: str, x: int, y: int) -> Dict[str, Any]:
    """
    Click on buttons, images, checkboxes, switches, and other clickable UI elements.

    USE FOR: Button, ImageButton, ImageView, CheckBox, Switch, RadioButton, Tab, MenuItem, Icon
    DO NOT USE FOR: EditText (use android_type_text instead)

    Args:
        element_description: Human-readable element description
        x: X coordinate in image space
        y: Y coordinate in image space

    Returns:
        Structured result with execution status
    """
    logger.info(f"✅ TOOL CALLED: android_click({element_description}, {x}, {y})")
    return {
        "success": True,
        "action_type": "click",
        "description": element_description,
        "coords": (x, y)
    }


@tool
def android_type_text(element_description: str, x: int, y: int, text: str) -> Dict[str, Any]:
    """
    Type text into text input fields. ALWAYS use this for EditText elements.

    USE FOR: EditText, AutoCompleteTextView, any text input field
    DO NOT USE: android_click on EditText elements - use this tool instead

    Args:
        element_description: Human-readable element description (e.g., "Email field")
        x: X coordinate in image space
        y: Y coordinate in image space
        text: Text to type (e.g., "user@example.com", "password123")

    Returns:
        Structured result with text metadata
    """
    logger.info(f"✅ TOOL CALLED: android_type_text({element_description}, {x}, {y}, '{text}')")
    return {
        "success": True,
        "action_type": "set_text",
        "description": element_description,
        "coords": (x, y),
        "text": text
    }


@tool
def android_swipe(direction: str, distance: str = "medium") -> Dict[str, Any]:
    """
    Swipe/scroll screen in specified direction to reveal more content.

    USE FOR: Scrolling lists, revealing hidden content
    DO NOT USE: For clicking elements - use android_click instead

    Args:
        direction: Swipe direction - "up", "down", "left", "right"
        distance: Swipe distance - "short", "medium", "long" (default: "medium")

    Returns:
        Structured result
    """
    logger.info(f"✅ TOOL CALLED: android_swipe({direction}, {distance})")
    return {
        "success": True,
        "action_type": "swipe",
        "direction": direction,
        "distance": distance
    }


def load_image_base64(image_path: Path) -> str:
    """Load image and convert to base64."""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def test_tool_calling(image_path: Path):
    """
    Test if qwen-vision-tools-v1 generates tool calls.

    Args:
        image_path: Path to CryptoApp screenshot
    """
    logger.info("=" * 80)
    logger.info("🔬 ISOLATED TOOL CALLING TEST")
    logger.info("=" * 80)
    logger.info(f"Model: qwen-vision-tools-v1")
    logger.info(f"Image: {image_path}")
    logger.info(f"Tools: android_click, android_type_text, android_swipe")
    logger.info("")

    # Load screenshot
    if not image_path.exists():
        logger.error(f"❌ Image not found: {image_path}")
        return False

    logger.info(f"📷 Loading screenshot: {image_path.name}")
    image_base64 = load_image_base64(image_path)
    logger.info(f"✅ Image loaded: {len(image_base64)} bytes (base64)")
    logger.info("")

    # Create model with tool support
    logger.info("🤖 Initializing qwen-vision-tools-v1...")
    llm = ChatOllama(
        model="qwen-vision-tools-v1",
        temperature=0.1,
        num_ctx=32768
    )

    # Bind tools
    logger.info("🔧 Binding tools to model...")
    tools = [android_click, android_type_text, android_swipe]
    llm_with_tools = llm.bind_tools(tools)
    logger.info(f"✅ {len(tools)} tools bound")
    logger.info("")

    # Create test prompt
    prompt = """You are analyzing an Android application screen.

This is a CryptoApp screen for generating cryptographic hashes.

Look at the screenshot and identify:
1. Any text input fields (EditText) - these need text typed into them
2. Any buttons that can be clicked
3. Any dropdown selectors (Spinners)

Based on what you see, use the appropriate Android tools to interact with the app.

IMPORTANT:
- For text input fields, use android_type_text (NOT android_click)
- For buttons, use android_click
- Provide realistic coordinates based on the image dimensions

What actions should be taken with this screen?"""

    # Send message with image
    logger.info("📤 Sending message to model...")
    logger.info(f"Prompt: {prompt[:100]}...")
    logger.info("")

    message = {
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": f"data:image/png;base64,{image_base64}"}
        ]
    }

    try:
        response = llm_with_tools.invoke([message])

        logger.info("=" * 80)
        logger.info("📥 RESPONSE RECEIVED")
        logger.info("=" * 80)

        # Check for tool calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            logger.info(f"✅ SUCCESS! Model generated {len(response.tool_calls)} tool call(s)")
            logger.info("")

            for i, tool_call in enumerate(response.tool_calls, 1):
                logger.info(f"Tool Call #{i}:")
                logger.info(f"  Name: {tool_call.get('name', 'unknown')}")
                logger.info(f"  Args: {tool_call.get('args', {})}")
                logger.info("")

            return True

        else:
            logger.error("❌ FAILURE! No tool calls generated")
            logger.error(f"Response type: {type(response)}")
            logger.error(f"Response content: {response.content if hasattr(response, 'content') else 'N/A'}")
            logger.error("")

            if hasattr(response, 'additional_kwargs'):
                logger.error(f"Additional kwargs: {response.additional_kwargs}")

            return False

    except Exception as e:
        logger.error(f"❌ ERROR during model invocation: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    # Test with CryptoApp screenshot from dataset
    dataset_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
    cryptoapp_dir = dataset_dir / "cryptoapp.apk"

    # Try to find a screenshot file
    screenshot_files = list(cryptoapp_dir.glob("*.png")) if cryptoapp_dir.exists() else []

    if not screenshot_files:
        logger.error(f"❌ No screenshots found in {cryptoapp_dir}")
        logger.info("Please provide path to CryptoApp screenshot:")
        logger.info("  Example: python test_tool_calling_isolated.py /path/to/screenshot.png")
        exit(1)

    # Use first screenshot
    screenshot_path = screenshot_files[0]

    logger.info(f"🎯 Testing with: {screenshot_path}")
    logger.info("")

    success = test_tool_calling(screenshot_path)

    logger.info("=" * 80)
    if success:
        logger.info("✅ TEST PASSED: Model generated tool calls successfully")
        logger.info("   → Issue is likely in rv_agent.py integration")
    else:
        logger.info("❌ TEST FAILED: Model did not generate tool calls")
        logger.info("   → Issue is with model configuration or tool binding")
    logger.info("=" * 80)

    exit(0 if success else 1)
