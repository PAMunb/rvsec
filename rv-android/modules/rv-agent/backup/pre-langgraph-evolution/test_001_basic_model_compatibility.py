#!/usr/bin/env python3
"""
Test 001: Basic Model Compatibility - Vision Understanding + Tool-Calling

Focus: CryptoApp validation - our controlled test application
- Source code: /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/examples/cryptoapp
- APK: /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/cryptoapp.apk
- Screenshots: /home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/

This prototype tests which models support both:
1. Vision understanding (identify CryptoApp UI elements)
2. Tool-calling capabilities (click on buttons, input text)

Expected CryptoApp MainActivity elements:
- Title: "CryptoApp"
- Button: "Message Digest"
- Button: "Cipher"
- Button: "Generated"

Models to test:
- unitythemaker/llama3.2-vision-tools:latest
- MrScarySpaceCat/gemma3-tools:4b
- PetrosStav/gemma3-tools:4b
- orieg/gemma3-tools:4b
- llama3.2-vision:latest
- moondream:1.8b
- llava:7b
- llava-llama3:8b
"""

import sys
import json
import base64
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import xml.etree.ElementTree as ET

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage


@dataclass
class ModelTestResult:
    """Result from testing a model."""
    model_name: str
    supports_vision: bool
    vision_description: Optional[str]
    supports_tools: bool
    tool_calls_made: List[Dict]
    error: Optional[str]
    ui_elements_found: int
    clickable_elements_found: int


@dataclass
class TestData:
    """Test data from screenshot collection."""
    app_name: str
    screenshot_path: Path
    uiautomator_path: Path
    ui_dump: str
    total_elements: int
    clickable_elements: int


# Simple tools for testing
@tool
def android_click(coordinates: str, element_description: str = "") -> str:
    """
    Click on an Android UI element at the specified coordinates.

    Args:
        coordinates: Coordinates in format 'x,y' (e.g., '245,678')
        element_description: Description of the element being clicked

    Returns:
        Success message with action performed
    """
    try:
        x, y = map(int, coordinates.split(','))
        result = f"CLICKED at position ({x}, {y})"
        if element_description:
            result += f" on {element_description}"
        return result
    except Exception as e:
        return f"ERROR: {str(e)}"


@tool
def android_input(text: str, coordinates: str = "") -> str:
    """
    Input text into an Android text field.

    Args:
        text: Text to input
        coordinates: Optional coordinates to tap first (format 'x,y')

    Returns:
        Success message with action performed
    """
    result = f"INPUT text '{text}'"
    if coordinates:
        result += f" at position {coordinates}"
    return result


def setup_logging():
    """Setup detailed logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('test_001_results.log')
        ]
    )
    return logging.getLogger(__name__)


def load_test_data(screenshot_dir: Path, app_name: str, img_number: str = "001") -> TestData:
    """Load test data from the screenshot collection."""
    app_dir = screenshot_dir / app_name
    screenshot_path = app_dir / f"{img_number}.png"
    uiautomator_path = app_dir / f"{img_number}.uiautomator"

    # Load and parse UI dump
    with open(uiautomator_path, 'r') as f:
        ui_dump = f.read()

    # Count elements in UI dump
    try:
        root = ET.fromstring(ui_dump)
        total_elements = len(root.findall(".//node"))
        clickable_elements = len([
            node for node in root.findall(".//node")
            if node.get('clickable') == 'true'
        ])
    except:
        total_elements = 0
        clickable_elements = 0

    return TestData(
        app_name=app_name,
        screenshot_path=screenshot_path,
        uiautomator_path=uiautomator_path,
        ui_dump=ui_dump,
        total_elements=total_elements,
        clickable_elements=clickable_elements
    )


def encode_image(image_path: Path) -> str:
    """Encode image to base64 for model input."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')


def test_vision_understanding(model_name: str, test_data: TestData, logger) -> Tuple[bool, str, int, int]:
    """Test if model can understand and describe the CryptoApp screenshot."""
    logger.info(f"Testing vision understanding for {model_name}")

    try:
        # Initialize model
        llm = ChatOllama(
            model=model_name,
            temperature=0.25,
            base_url="http://localhost:11434"
        )

        # Encode image
        image_base64 = encode_image(test_data.screenshot_path)

        # Create prompt with image - specific for CryptoApp
        prompt = """Analyze this CryptoApp Android screenshot and provide:
1. The app title or name visible on screen
2. List all buttons you can see (especially "Message Digest", "Cipher", "Generated")
3. For each button, provide its position in format "at position (x, y)"
4. Any other UI elements like text fields or labels

Be very specific about button names and their exact coordinates."""

        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
            ]
        )

        # Get response
        response = llm.invoke([message])
        description = response.content

        # Count CryptoApp specific elements mentioned
        cryptoapp_buttons = ['message digest', 'cipher', 'generated']
        buttons_found = sum(1 for button in cryptoapp_buttons if button.lower() in description.lower())

        # Count UI elements mentioned
        ui_keywords = ['button', 'text', 'field', 'input', 'cryptoapp', 'title']
        ui_elements_found = sum(1 for keyword in ui_keywords if keyword.lower() in description.lower())

        # Check for coordinate format "at position (x, y)"
        import re
        coordinates_found = len(re.findall(r'at position \(\d+,\s*\d+\)', description))

        logger.info(f"  CryptoApp buttons found: {buttons_found}/3")
        logger.info(f"  Coordinates in correct format: {coordinates_found}")

        logger.info(f"✅ {model_name} - Vision test passed")
        logger.debug(f"Description: {description[:200]}...")

        return True, description, ui_elements_found, buttons_found

    except Exception as e:
        logger.error(f"❌ {model_name} - Vision test failed: {e}")
        return False, str(e), 0, 0


def test_tool_calling(model_name: str, test_data: TestData, vision_description: str, logger) -> Tuple[bool, List[Dict]]:
    """Test if model can call tools to interact with CryptoApp."""
    logger.info(f"Testing tool-calling for {model_name}")

    try:
        # Initialize model with tools
        llm = ChatOllama(
            model=model_name,
            temperature=0.25,
            base_url="http://localhost:11434"
        )

        # Bind tools
        tools = [android_click, android_input]
        llm_with_tools = llm.bind_tools(tools)

        # Create prompt asking for CryptoApp specific actions
        prompt = f"""Based on the CryptoApp screen you analyzed:
{vision_description[:500]}

Now perform these specific actions using the available tools:
1. Click on the "Message Digest" button using android_click tool
2. Click on the "Cipher" button using android_click tool

Remember to use the exact format: android_click(coordinates="x,y", element_description="button name")
Use the coordinates you identified earlier."""

        # Invoke with tools
        response = llm_with_tools.invoke(prompt)

        # Check for tool calls
        tool_calls = []
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_calls.append({
                    'name': tool_call.get('name', 'unknown'),
                    'args': tool_call.get('args', {})
                })
                logger.info(f"  Tool call: {tool_call}")

        if tool_calls:
            logger.info(f"✅ {model_name} - Tool-calling test passed ({len(tool_calls)} calls)")
            return True, tool_calls
        else:
            logger.warning(f"⚠️ {model_name} - No tool calls detected")
            return False, []

    except Exception as e:
        logger.error(f"❌ {model_name} - Tool-calling test failed: {e}")
        return False, []


def unload_ollama_models():
    """Unload current models from GPU memory."""
    import subprocess
    import time

    try:
        # Get list of running models
        result = subprocess.run(["ollama", "ps"], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            # Skip header line
            for line in lines[1:]:
                if line.strip():
                    # Extract model name (first column)
                    model_name = line.split()[0]
                    if model_name and model_name != "NAME":
                        print(f"🔄 Stopping model: {model_name}")
                        subprocess.run(["ollama", "stop", model_name], check=False, capture_output=True)

        # Wait for GPU memory to be freed
        time.sleep(3)

    except Exception as e:
        print(f"⚠️ Warning: Could not stop models: {e}")
        pass


def test_model(model_name: str, test_data: TestData, logger) -> ModelTestResult:
    """Complete test of a model's capabilities."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing model: {model_name}")
    logger.info(f"{'='*60}")

    # Unload any previous model first
    unload_ollama_models()

    # Test vision understanding
    vision_success, vision_desc, ui_elements, clickable_elements = test_vision_understanding(
        model_name, test_data, logger
    )

    # Test tool calling (only if vision works)
    tools_success = False
    tool_calls = []

    if vision_success and vision_desc != "":
        tools_success, tool_calls = test_tool_calling(
            model_name, test_data, vision_desc, logger
        )

    result = ModelTestResult(
        model_name=model_name,
        supports_vision=vision_success,
        vision_description=vision_desc if vision_success else None,
        supports_tools=tools_success,
        tool_calls_made=tool_calls,
        error=None if (vision_success or tools_success) else vision_desc,
        ui_elements_found=ui_elements,
        clickable_elements_found=clickable_elements
    )

    # Summary for this model
    logger.info(f"\nModel: {model_name}")
    logger.info(f"  Vision: {'✅' if vision_success else '❌'}")
    logger.info(f"  Tools: {'✅' if tools_success else '❌'}")
    logger.info(f"  UI Elements Found: {ui_elements}")
    logger.info(f"  CryptoApp Buttons Found: {clickable_elements}/3")
    if tool_calls:
        logger.info(f"  Tool Calls Made: {len(tool_calls)}")

    return result


def save_results(results: List[ModelTestResult], test_data: TestData):
    """Save test results to JSON file."""
    output = {
        'test_data': {
            'app': test_data.app_name,
            'screenshot': str(test_data.screenshot_path),
            'total_ui_elements': test_data.total_elements,
            'clickable_elements': test_data.clickable_elements
        },
        'model_results': []
    }

    for result in results:
        output['model_results'].append({
            'model': result.model_name,
            'vision_support': result.supports_vision,
            'tool_support': result.supports_tools,
            'ui_elements_found': result.ui_elements_found,
            'clickable_found': result.clickable_elements_found,
            'tool_calls': result.tool_calls_made,
            'vision_sample': result.vision_description[:200] if result.vision_description else None,
            'error': result.error
        })

    with open('test_001_results.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n📊 Results saved to test_001_results.json")


def main():
    """Main test execution focused on CryptoApp."""
    logger = setup_logging()

    print("🚀 RVAgent Test 001: Basic Model Compatibility - CryptoApp Focus")
    print("=" * 70)

    # Models to test
    models = [
        "unitythemaker/llama3.2-vision-tools:latest",
        "MrScarySpaceCat/gemma3-tools:4b",
        "PetrosStav/gemma3-tools:4b",
        "orieg/gemma3-tools:4b",
        "llama3.2-vision:latest",
        "moondream:1.8b",
        "llava:7b",
        "llava-llama3:8b"
    ]

    # Load CryptoApp test data - MainActivity screenshot
    screenshot_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
    test_data = load_test_data(screenshot_dir, "cryptoapp.apk", "001")

    print(f"\n📱 CryptoApp Test Data:")
    print(f"  App: {test_data.app_name}")
    print(f"  Screenshot: {test_data.screenshot_path.name} (MainActivity)")
    print(f"  Expected: 3 main buttons (Message Digest, Cipher, Generated)")
    print(f"  UI Elements in dump: {test_data.total_elements}")
    print(f"  Clickable in dump: {test_data.clickable_elements}")

    # Test each model
    results = []
    for model_name in models:
        try:
            result = test_model(model_name, test_data, logger)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to test {model_name}: {e}")
            results.append(ModelTestResult(
                model_name=model_name,
                supports_vision=False,
                vision_description=None,
                supports_tools=False,
                tool_calls_made=[],
                error=str(e),
                ui_elements_found=0,
                clickable_elements_found=0
            ))

    # Summary
    print("\n" + "=" * 70)
    print("📊 FINAL SUMMARY")
    print("=" * 70)

    vision_capable = [r for r in results if r.supports_vision]
    tools_capable = [r for r in results if r.supports_tools]
    both_capable = [r for r in results if r.supports_vision and r.supports_tools]

    print(f"\n✅ Vision Support: {len(vision_capable)}/{len(models)}")
    for r in vision_capable:
        print(f"  - {r.model_name} (found {r.clickable_elements_found}/3 CryptoApp buttons)")

    print(f"\n✅ Tool-Calling Support: {len(tools_capable)}/{len(models)}")
    for r in tools_capable:
        print(f"  - {r.model_name} ({len(r.tool_calls_made)} tool calls)")

    print(f"\n🏆 Both Vision + Tools: {len(both_capable)}/{len(models)}")
    for r in both_capable:
        print(f"  ⭐ {r.model_name} (buttons: {r.clickable_elements_found}/3, calls: {len(r.tool_calls_made)})")

    # Save results
    save_results(results, test_data)

    # Recommend best model for CryptoApp
    if both_capable:
        # Sort by CryptoApp buttons found (better app understanding)
        best = sorted(both_capable, key=lambda x: (x.clickable_elements_found, len(x.tool_calls_made)), reverse=True)[0]
        print(f"\n🎯 RECOMMENDED MODEL FOR CRYPTOAPP: {best.model_name}")
        print(f"   - CryptoApp Buttons: {best.clickable_elements_found}/3 correctly identified")
        print(f"   - Tool Calls: {len(best.tool_calls_made)} successful")
        print(f"   - Ready for CryptoApp testing!")
    else:
        print("\n⚠️ No models support both vision and tool-calling!")
        print("   This is critical for RVAgent - need to find compatible model")

    return len(both_capable) > 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)