#!/usr/bin/env python3
"""
Test JSON parser with all screenshots from all 28/29 apps.

Validates that the JSON parser can extract tool calls from screenshots
across different applications and UI patterns.
"""

import base64
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
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


def test_single_screenshot(llm_with_tools, screenshot_path: Path, app_name: str) -> Dict[str, Any]:
    """Test JSON parser with a single screenshot."""

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

        # Check for native tool_calls first
        if hasattr(response, 'tool_calls') and response.tool_calls:
            return {
                "success": True,
                "method": "native",
                "tool_calls_count": len(response.tool_calls),
                "screenshot": screenshot_path.name
            }

        # Parse from JSON text
        tool_calls = json_parser.parse_tool_calls_from_text(response.content)

        if tool_calls:
            return {
                "success": True,
                "method": "json_parser",
                "tool_calls_count": len(tool_calls),
                "screenshot": screenshot_path.name
            }
        else:
            return {
                "success": False,
                "method": "none",
                "tool_calls_count": 0,
                "screenshot": screenshot_path.name,
                "response_preview": response.content[:200] if hasattr(response, 'content') else "No content"
            }

    except Exception as e:
        logger.error(f"Error testing {screenshot_path.name}: {e}")
        return {
            "success": False,
            "method": "error",
            "tool_calls_count": 0,
            "screenshot": screenshot_path.name,
            "error": str(e)
        }


def test_all_apps():
    """Test JSON parser with all apps."""

    print("=" * 80)
    print("🧪 TEST JSON PARSER - All 28/29 Apps")
    print("=" * 80)
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

    # Statistics
    stats = {
        "total_apps": 0,
        "total_screenshots": 0,
        "successful_parses": 0,
        "failed_parses": 0,
        "native_tool_calls": 0,
        "json_parser_used": 0,
        "errors": 0,
        "apps_results": {}
    }

    # Test each app
    for app_dir in app_dirs:
        app_name = app_dir.name
        screenshots = list(app_dir.glob("*.png"))

        if not screenshots:
            logger.warning(f"No screenshots found for {app_name}")
            continue

        stats["total_apps"] += 1

        print(f"📱 Testing {app_name} ({len(screenshots)} screenshots)...")

        app_stats = {
            "total": len(screenshots),
            "success": 0,
            "failed": 0,
            "native": 0,
            "json_parser": 0,
            "errors": 0,
            "results": []
        }

        # Test each screenshot
        for i, screenshot in enumerate(screenshots, 1):
            stats["total_screenshots"] += 1

            # Show progress every 10 screenshots
            if i % 10 == 0 or i == len(screenshots):
                print(f"   Progress: {i}/{len(screenshots)} screenshots tested")

            result = test_single_screenshot(llm_with_tools, screenshot, app_name)
            app_stats["results"].append(result)

            if result["success"]:
                stats["successful_parses"] += 1
                app_stats["success"] += 1

                if result["method"] == "native":
                    stats["native_tool_calls"] += 1
                    app_stats["native"] += 1
                elif result["method"] == "json_parser":
                    stats["json_parser_used"] += 1
                    app_stats["json_parser"] += 1
            elif result["method"] == "error":
                stats["errors"] += 1
                app_stats["errors"] += 1
            else:
                stats["failed_parses"] += 1
                app_stats["failed"] += 1

        stats["apps_results"][app_name] = app_stats

        success_rate = (app_stats["success"] / app_stats["total"] * 100) if app_stats["total"] > 0 else 0
        print(f"   ✅ {app_name}: {app_stats['success']}/{app_stats['total']} successful ({success_rate:.1f}%)")
        print()

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

    overall_success_rate = (stats['successful_parses'] / stats['total_screenshots'] * 100) if stats['total_screenshots'] > 0 else 0
    json_parser_usage = (stats['json_parser_used'] / stats['successful_parses'] * 100) if stats['successful_parses'] > 0 else 0

    print(f"📈 Overall success rate: {overall_success_rate:.1f}%")
    print(f"🔧 JSON parser usage: {json_parser_usage:.1f}% of successful parses")
    print()

    # Save detailed results
    output_file = Path("test_json_parser_all_apps_results.json")
    with open(output_file, 'w') as f:
        json.dump(stats, f, indent=2)

    print(f"💾 Detailed results saved to: {output_file}")
    print()

    # Determine success
    success = overall_success_rate >= 70.0  # 70% success rate threshold

    return success


if __name__ == "__main__":
    success = test_all_apps()

    print("=" * 80)
    if success:
        print("✅ JSON PARSER ALL APPS TEST PASSED")
    else:
        print("❌ JSON PARSER ALL APPS TEST FAILED")
    print("=" * 80)

    exit(0 if success else 1)
