"""
Coordinate Validator - Fixed Version using LLM+Tools directly.

Based on our research: Agent framework breaks multimodal, but LLM+Tools works perfectly.
"""

import json
import time
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# Add rv-agent to path for imports
import sys
rv_agent_path = str(Path(__file__).parent.parent / "src")
sys.path.insert(0, rv_agent_path)

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

from mock_device_adapter import MockDeviceAdapter
from simple_tools_with_explanation import create_validation_tools


def encode_image_to_base64(image_path: str) -> Optional[str]:
    """Encode image file to base64 string."""
    try:
        if not Path(image_path).exists():
            return None
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            return encoded_string
    except Exception as e:
        print(f"❌ Image encoding failed: {e}")
        return None


class CoordinateValidatorFixed:
    """
    Fixed coordinate validator using LLM+Tools directly (no Agent framework).

    This avoids the multimodal issues with Agent framework.
    """

    def __init__(self, model_name: str = "PetrosStav/gemma3-tools:4b"):
        """Initialize validator with specified model."""
        self.model_name = model_name
        self.results = []

        print(f"\n🔧 Initializing Fixed CoordinateValidator with {model_name}")

    def create_prompt_strategy(self, strategy: str, elements_desc: str) -> str:
        """Generate prompt based on strategy."""
        strategies = {
            "baseline": f"""You are testing an Android application. Look at the screenshot and interact with the UI.

Available elements on screen:
{elements_desc}

Choose an element to interact with and use the android_click tool.
IMPORTANT: Always provide an 'explanation' parameter describing why you chose this element and coordinates.
""",

            "coordinate_validation": f"""You are testing an Android application. Look at the UI elements listed below and choose ONE interactive element to click on.

UI Elements with exact coordinates:
{elements_desc}

IMPORTANT:
1. Use the EXACT coordinates provided in "at position (x, y)" format. Do not estimate coordinates.
2. Always provide an 'explanation' parameter describing why you chose this specific element.

Task: Select an element to test and use the android_click tool with its exact coordinates.
""",

            "spinner_focused": f"""You are testing an Android application. Pay special attention to Spinners and Dropdowns.

UI Elements on screen:
{elements_desc}

IMPORTANT:
1. If you see any Spinner, ComboBox, or dropdown elements, prioritize testing those first!
2. Otherwise, test any button or interactive element.
3. ALWAYS include an 'explanation' parameter describing why you chose this element.
4. If you're testing a Spinner, consider using the android_analyze_spinner tool.

Use android_click with the exact coordinates provided.
"""
        }

        return strategies.get(strategy, strategies["baseline"])

    def validate_single_screenshot(
        self,
        screenshot_path: str,
        xml_path: str,
        strategy: str = "baseline"
    ) -> Dict[str, Any]:
        """
        Validate coordinate generation for a single screenshot using LLM+Tools directly.
        """
        print(f"\n📸 Testing: {Path(screenshot_path).name} with strategy: {strategy}")

        # Initialize mock device with ground truth
        mock_device = MockDeviceAdapter(xml_path)

        # Get element descriptions for prompt
        elements_desc = mock_device.get_element_list_for_prompt()

        # Create tools with mock device
        tools = create_validation_tools(mock_device)

        # Initialize LLM
        print(f"🧠 Initializing {self.model_name}...")
        llm = ChatOllama(
            model=self.model_name,
            temperature=0.2,
            top_p=0.9,
            top_k=50,
            num_ctx=32768
        )

        # Bind tools to LLM (this works with multimodal!)
        llm_with_tools = llm.bind_tools(tools)

        # Create prompt based on strategy
        base_prompt = self.create_prompt_strategy(strategy, elements_desc)

        # Encode screenshot
        image_base64 = encode_image_to_base64(screenshot_path)
        if not image_base64:
            print(f"❌ Failed to encode image")
            return {
                "screenshot": Path(screenshot_path).name,
                "strategy": strategy,
                "error": "Image encoding failed",
                "success": False
            }

        # Execute LLM+Tools with multimodal input
        start_time = time.time()

        try:
            # Create multimodal message
            message = HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": f"""Look at this Android app screenshot and interact with an important UI element.

{base_prompt}

Choose one element and use the appropriate tool with exact coordinates and explanation."""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        }
                    }
                ]
            )

            # Execute LLM with tools
            print("🤖 Executing LLM+Tools...")
            response = llm_with_tools.invoke([message])

            response_time = time.time() - start_time

            # Process tool calls if any
            if hasattr(response, 'tool_calls') and response.tool_calls:
                print(f"✅ Tool calls detected: {len(response.tool_calls)}")

                for tool_call in response.tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']

                    print(f"🔧 Executing tool: {tool_name}")
                    print(f"   Args: {tool_args}")

                    # Find and execute the tool
                    for tool in tools:
                        if tool.name == tool_name:
                            try:
                                result = tool.func(**tool_args)
                                print(f"   Result: {result}")
                            except Exception as e:
                                print(f"   Error: {e}")
                            break
            else:
                print("❌ No tool calls detected")

            # Get validation metrics
            metrics = mock_device.get_validation_metrics()

            # Prepare result
            validation_result = {
                "screenshot": Path(screenshot_path).name,
                "xml": Path(xml_path).name,
                "strategy": strategy,
                "model": self.model_name,
                "response_time": response_time,
                "success": True,
                "metrics": metrics,
                "llm_output": str(response.content)[:500],
                "tool_calls": getattr(response, 'tool_calls', [])
            }

            # Print summary
            print(f"\n📊 Results for {strategy}:")
            print(f"  - Total clicks: {metrics['total_clicks']}")
            print(f"  - Hit rate: {metrics['hit_rate']:.1f}%")
            print(f"  - Avg distance: {metrics['avg_distance']:.1f}px")
            print(f"  - Response time: {response_time:.2f}s")
            print(f"  - Tool calls: {len(getattr(response, 'tool_calls', []))}")

            return validation_result

        except Exception as e:
            print(f"❌ LLM+Tools execution failed: {e}")
            return {
                "screenshot": Path(screenshot_path).name,
                "strategy": strategy,
                "error": str(e),
                "success": False,
                "response_time": time.time() - start_time
            }

    def validate_dataset(
        self,
        dataset_path: str,
        apps: List[str],
        strategies: List[str],
        samples_per_app: int = 5
    ) -> Dict[str, Any]:
        """Validate multiple screenshots using fixed LLM+Tools approach."""
        dataset_path = Path(dataset_path)
        all_results = []

        print(f"\n🚀 Starting Fixed Validation Suite")
        print(f"  - Apps: {apps}")
        print(f"  - Strategies: {strategies}")
        print(f"  - Samples per app: {samples_per_app}")

        for app in apps:
            app_path = dataset_path / app

            if not app_path.exists():
                print(f"⚠️ App directory not found: {app}")
                continue

            # Get available screenshots
            screenshots = sorted(app_path.glob("*.png"))[:samples_per_app]

            for screenshot in screenshots:
                # Find corresponding XML
                xml_path = screenshot.with_suffix(".uiautomator")

                if not xml_path.exists():
                    print(f"⚠️ XML not found for {screenshot.name}")
                    continue

                # Test each strategy
                for strategy in strategies:
                    result = self.validate_single_screenshot(
                        str(screenshot),
                        str(xml_path),
                        strategy
                    )
                    result["app"] = app
                    all_results.append(result)

                    # Small delay to avoid overloading
                    time.sleep(1)

        # Aggregate results
        return self.aggregate_results(all_results)

    def aggregate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate validation results and compute statistics."""
        # Filter successful results
        successful = [r for r in results if r.get("success", False)]

        if not successful:
            return {
                "error": "No successful validations",
                "total_tests": len(results),
                "successful_tests": 0
            }

        # Aggregate by strategy
        by_strategy = {}
        for result in successful:
            strategy = result["strategy"]
            if strategy not in by_strategy:
                by_strategy[strategy] = []
            by_strategy[strategy].append(result)

        # Compute statistics per strategy
        strategy_stats = {}
        for strategy, strategy_results in by_strategy.items():
            total_clicks = sum(r["metrics"]["total_clicks"] for r in strategy_results)
            total_hits = sum(r["metrics"]["hits"] for r in strategy_results)
            avg_distance = sum(r["metrics"]["avg_distance"] for r in strategy_results) / len(strategy_results)
            avg_response_time = sum(r["response_time"] for r in strategy_results) / len(strategy_results)
            total_tool_calls = sum(len(r.get("tool_calls", [])) for r in strategy_results)

            strategy_stats[strategy] = {
                "total_tests": len(strategy_results),
                "total_clicks": total_clicks,
                "total_hits": total_hits,
                "hit_rate": (total_hits / total_clicks * 100) if total_clicks > 0 else 0,
                "avg_distance": avg_distance,
                "avg_response_time": avg_response_time,
                "total_tool_calls": total_tool_calls
            }

        # Find best strategy
        best_strategy = max(strategy_stats.items(), key=lambda x: x[1]["hit_rate"])

        return {
            "timestamp": datetime.now().isoformat(),
            "model": self.model_name,
            "total_tests": len(results),
            "successful_tests": len(successful),
            "strategy_stats": strategy_stats,
            "best_strategy": {
                "name": best_strategy[0],
                "hit_rate": best_strategy[1]["hit_rate"]
            },
            "raw_results": results
        }


def main():
    """Run fixed coordinate validation tests."""
    # Initialize fixed validator
    validator = CoordinateValidatorFixed(model_name="PetrosStav/gemma3-tools:4b")

    # Define test configuration
    dataset_path = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    test_apps = [
        "cryptoapp.apk"  # Start with our simple app
    ]

    strategies = [
        "baseline",
        "coordinate_validation",
        "spinner_focused"
    ]

    # Run validation
    results = validator.validate_dataset(
        dataset_path=dataset_path,
        apps=test_apps,
        strategies=strategies,
        samples_per_app=1  # Start with 1 screenshot
    )

    # Save results
    output_path = f"validation_results_fixed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    # Print summary
    print("\n" + "="*60)
    print("📊 FIXED VALIDATION SUMMARY")
    print("="*60)

    if "strategy_stats" in results:
        for strategy, stats in results["strategy_stats"].items():
            print(f"\n{strategy}:")
            print(f"  Hit Rate: {stats['hit_rate']:.1f}%")
            print(f"  Avg Distance: {stats['avg_distance']:.1f}px")
            print(f"  Response Time: {stats['avg_response_time']:.2f}s")
            print(f"  Tool Calls: {stats['total_tool_calls']}")

        print(f"\n🏆 Best Strategy: {results['best_strategy']['name']} "
              f"({results['best_strategy']['hit_rate']:.1f}% hit rate)")

    print(f"\n💾 Results saved to: {output_path}")


if __name__ == "__main__":
    main()