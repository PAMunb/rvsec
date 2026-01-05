#!/usr/bin/env python3
"""
Test JSON parser with DETAILED logging - All 28/29 apps, all images.

This script captures:
- LLM responses (full text)
- Tool calls extracted (name + arguments)
- Element types identified
- Tool distribution analysis

NO EXECUTION - Just preparation!
"""

import base64
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama

from rv_agent.llm.tools import json_parser
from rv_agent.llm.tools.android_tools import create_android_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def classify_element(element_description: str) -> str:
    """Classify UI element from description."""
    if not element_description:
        return "Unknown"

    desc_lower = element_description.lower()

    if 'button' in desc_lower:
        return 'Button'
    elif 'text' in desc_lower or 'field' in desc_lower or 'input' in desc_lower or 'edit' in desc_lower:
        return 'Text Field/Input'
    elif 'icon' in desc_lower:
        return 'Icon'
    elif 'menu' in desc_lower:
        return 'Menu'
    elif 'list' in desc_lower:
        return 'List'
    elif 'card' in desc_lower:
        return 'Card'
    elif 'tab' in desc_lower:
        return 'Tab'
    elif 'checkbox' in desc_lower or 'check' in desc_lower:
        return 'Checkbox'
    elif 'switch' in desc_lower or 'toggle' in desc_lower:
        return 'Switch/Toggle'
    elif 'image' in desc_lower or 'photo' in desc_lower or 'img' in desc_lower:
        return 'Image'
    elif 'label' in desc_lower:
        return 'Label'
    elif 'scroll' in desc_lower:
        return 'Scrollable'
    else:
        return 'Other/Generic'


def test_single_screenshot_detailed(llm_with_tools, screenshot_path: Path, app_name: str) -> Dict[str, Any]:
    """Test JSON parser with detailed logging."""

    try:
        # Load image
        with open(screenshot_path, 'rb') as f:
            image_base64 = base64.b64encode(f.read()).decode('utf-8')

        # Create prompt
        prompt = f"""You are analyzing an Android application screenshot for {app_name}.

Look at the screenshot and identify what actions should be taken.

IMPORTANT RULES:
- For text input fields (EditText), use android_type_text (NOT android_click)
- For buttons, use android_click
- For scrollable content, use android_swipe
- Provide realistic coordinates based on the image dimensions (728x1288)

What actions should be taken with this screen?"""

        # Send message with image
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": f"data:image/png;base64,{image_base64}"}
            ]
        )

        # Get response
        response = llm_with_tools.invoke([message])

        # Extract LLM response text
        llm_response_text = response.content if hasattr(response, 'content') else ""

        # Initialize result
        result = {
            "success": False,
            "screenshot": screenshot_path.name,
            "app_name": app_name,
            "llm_response": llm_response_text,  # FULL LLM RESPONSE
            "tool_calls": [],
            "tool_calls_count": 0,
            "method": "none",
            "elements": []
        }

        # Check for native tool_calls first
        if hasattr(response, 'tool_calls') and response.tool_calls:
            result["success"] = True
            result["method"] = "native"
            result["tool_calls_count"] = len(response.tool_calls)

            for tc in response.tool_calls:
                tool_call_detail = {
                    "name": tc.get('name', 'unknown'),
                    "arguments": tc.get('args', {})
                }
                result["tool_calls"].append(tool_call_detail)

                # Extract element info
                args = tc.get('args', {})
                elem_desc = args.get('element_description', args.get('description', ''))
                if elem_desc:
                    elem_type = classify_element(elem_desc)
                    result["elements"].append({
                        "description": elem_desc,
                        "type": elem_type
                    })
        else:
            # Parse from JSON/XML text
            parsed_calls = json_parser.parse_tool_calls_from_text(llm_response_text)

            if parsed_calls:
                result["success"] = True
                result["method"] = "json_parser"
                result["tool_calls_count"] = len(parsed_calls)

                for tc in parsed_calls:
                    tool_call_detail = {
                        "name": tc.get('name', 'unknown'),
                        "arguments": tc.get('args', {})
                    }
                    result["tool_calls"].append(tool_call_detail)

                    # Extract element info
                    args = tc.get('args', {})
                    elem_desc = args.get('element_description', args.get('description', ''))
                    if elem_desc:
                        elem_type = classify_element(elem_desc)
                        result["elements"].append({
                            "description": elem_desc,
                            "type": elem_type
                        })

        return result

    except Exception as e:
        logger.error(f"Error testing {screenshot_path.name}: {e}")
        return {
            "success": False,
            "screenshot": screenshot_path.name,
            "app_name": app_name,
            "llm_response": "",
            "tool_calls": [],
            "tool_calls_count": 0,
            "method": "error",
            "elements": [],
            "error": str(e)
        }


def test_all_apps_detailed():
    """Test JSON parser with detailed logging for all apps."""

    print("=" * 80)
    print("🧪 TEST JSON PARSER - DETAILED ANALYSIS - All 28/29 Apps")
    print("=" * 80)
    print()
    print("⚠️  This will collect:")
    print("   - Full LLM responses")
    print("   - Detailed tool calls (name + arguments)")
    print("   - Element classifications")
    print("   - Tool distribution statistics")
    print()

    # Find dataset directory
    dataset_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")

    if not dataset_dir.exists():
        print(f"❌ Dataset directory not found: {dataset_dir}")
        return False

    # Create model v2 (with vision+tools template)
    print("📋 Creating LLM with qwen-vision-tools-v2...")
    llm = ChatOllama(
        model="qwen-vision-tools-v2",
        temperature=0.00001,
    )

    # Bind Android tools (for schema injection)
    android_tools = create_android_tools()
    llm_with_tools = llm.bind_tools(android_tools)

    print(f"✅ LLM configured with {len(android_tools)} tools")
    print()

    # Collect all apps
    app_dirs = [d for d in dataset_dir.iterdir() if d.is_dir()]
    app_dirs.sort()

    print(f"📱 Found {len(app_dirs)} apps")
    print()

    # Global statistics
    stats = {
        "total_apps": 0,
        "total_screenshots": 0,
        "successful_parses": 0,
        "failed_parses": 0,
        "native_tool_calls": 0,
        "json_parser_used": 0,
        "errors": 0,
        "tool_distribution": {},  # Counter for tools
        "element_distribution": {},  # Counter for elements
        "detailed_results": []  # All detailed results
    }

    tool_counter = Counter()
    element_counter = Counter()

    # Test each app
    for app_dir in app_dirs:
        app_name = app_dir.name
        screenshots = list(app_dir.glob("*.png"))

        if not screenshots:
            logger.warning(f"No screenshots found for {app_name}")
            continue

        stats["total_apps"] += 1

        print(f"📱 Testing {app_name} ({len(screenshots)} screenshots)...")

        # Test each screenshot
        for i, screenshot in enumerate(screenshots, 1):
            stats["total_screenshots"] += 1

            # Show progress every 10 screenshots
            if i % 10 == 0 or i == len(screenshots):
                print(f"   Progress: {i}/{len(screenshots)} screenshots tested")

            # Test with detailed logging
            result = test_single_screenshot_detailed(llm_with_tools, screenshot, app_name)
            stats["detailed_results"].append(result)

            # Update statistics
            if result["success"]:
                stats["successful_parses"] += 1

                if result["method"] == "native":
                    stats["native_tool_calls"] += 1
                elif result["method"] == "json_parser":
                    stats["json_parser_used"] += 1

                # Count tools
                for tc in result["tool_calls"]:
                    tool_name = tc["name"]
                    tool_counter[tool_name] += 1

                # Count elements
                for elem in result["elements"]:
                    elem_type = elem["type"]
                    element_counter[elem_type] += 1

            elif result["method"] == "error":
                stats["errors"] += 1
            else:
                stats["failed_parses"] += 1

        success_rate = ((stats["successful_parses"] - (stats["failed_parses"] + stats["errors"])) /
                       stats["total_screenshots"] * 100) if stats["total_screenshots"] > 0 else 0
        print(f"   ✅ {app_name}: Processed")
        print()

    # Convert counters to dict
    stats["tool_distribution"] = dict(tool_counter)
    stats["element_distribution"] = dict(element_counter)

    # Print final statistics
    print("=" * 80)
    print("📊 FINAL STATISTICS")
    print("=" * 80)
    print()

    print(f"📱 Total apps tested: {stats['total_apps']}")
    print(f"📷 Total screenshots tested: {stats['total_screenshots']}")
    print()

    print(f"✅ Successful parses: {stats['successful_parses']}")
    print(f"   - Native tool_calls: {stats['native_tool_calls']}")
    print(f"   - JSON parser used: {stats['json_parser_used']}")
    print()

    print(f"❌ Failed parses: {stats['failed_parses']}")
    print(f"⚠️  Errors: {stats['errors']}")
    print()

    # Tool distribution
    print("=" * 80)
    print("🔧 TOOL DISTRIBUTION")
    print("=" * 80)
    print()

    total_tools = sum(tool_counter.values())
    for tool, count in tool_counter.most_common():
        percentage = (count / total_tools * 100) if total_tools > 0 else 0
        bar = "█" * int(percentage / 2)
        print(f"   {tool:30s}: {count:4d} ({percentage:5.1f}%) {bar}")
    print()

    # Element distribution
    print("=" * 80)
    print("📱 ELEMENT TYPE DISTRIBUTION")
    print("=" * 80)
    print()

    total_elements = sum(element_counter.values())
    for elem, count in element_counter.most_common():
        percentage = (count / total_elements * 100) if total_elements > 0 else 0
        bar = "█" * int(percentage / 2)
        print(f"   {elem:30s}: {count:4d} ({percentage:5.1f}%) {bar}")
    print()

    # Save detailed results
    output_file = Path("test_json_parser_detailed_results.json")
    with open(output_file, 'w') as f:
        json.dump(stats, f, indent=2)

    print(f"💾 Detailed results saved to: {output_file}")
    print(f"   - File contains:")
    print(f"     * Full LLM responses for all {stats['total_screenshots']} screenshots")
    print(f"     * Detailed tool calls with arguments")
    print(f"     * Element classifications")
    print(f"     * Complete statistics")
    print()

    overall_success_rate = (stats['successful_parses'] / stats['total_screenshots'] * 100) if stats['total_screenshots'] > 0 else 0
    print(f"📈 Overall success rate: {overall_success_rate:.1f}%")
    print()

    # Determine success
    success = overall_success_rate >= 70.0

    return success


if __name__ == "__main__":
    success = test_all_apps_detailed()

    print("=" * 80)
    if success:
        print("✅ JSON PARSER DETAILED ANALYSIS PASSED")
    else:
        print("❌ JSON PARSER DETAILED ANALYSIS FAILED")
    print("=" * 80)

    exit(0 if success else 1)
