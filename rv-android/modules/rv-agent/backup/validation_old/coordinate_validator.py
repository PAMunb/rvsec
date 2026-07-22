"""
Coordinate Validation for Gemma3-tools model.

Tests coordinate generation accuracy using different prompt strategies
without requiring emulator or real device.
"""

import json
import time
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# Add rv-agent to path for imports
import sys
from pathlib import Path
rv_agent_path = str(Path(__file__).parent.parent / "src")
sys.path.insert(0, rv_agent_path)

from langchain_ollama import ChatOllama
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
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


class CoordinateValidator:
    """
    Validates coordinate generation accuracy for vision models.

    Tests different prompt strategies and collects metrics.
    """

    def __init__(self, model_name: str = "PetrosStav/gemma3-tools:4b"):
        """
        Initialize validator with specified model.

        Args:
            model_name: Ollama model name with tool-calling support
        """
        self.model_name = model_name
        self.results = []

        print(f"\n🔧 Initializing CoordinateValidator with {model_name}")

    def create_prompt_strategy(self, strategy: str, elements_desc: str) -> str:
        """
        Generate prompt based on strategy.

        Args:
            strategy: Prompt strategy name
            elements_desc: Formatted element descriptions

        Returns:
            Complete prompt for the strategy
        """
        strategies = {
            "baseline": f"""
You are testing an Android application. Look at the screenshot and interact with the UI.

Available elements on screen:
{elements_desc}

Choose an element to interact with and use the appropriate tool (android_click, android_input, etc).
IMPORTANT: Always provide an 'explanation' parameter describing why you chose this element and coordinates.
""",

            "coordinate_validation": f"""
You are testing an Android application. Look at the UI elements listed below and choose ONE interactive element to click on.

UI Elements with exact coordinates:
{elements_desc}

IMPORTANT:
1. Use the EXACT coordinates provided in "at position (x, y)" format. Do not estimate coordinates.
2. Always provide an 'explanation' parameter describing why you chose this specific element.

Task: Select an element to test and use the android_click tool with its exact coordinates.
""",

            "enhanced_description": f"""
You are an Android UI testing agent. Your goal is to systematically test all UI elements.

Current screen contains these interactive elements:
{elements_desc}

Instructions:
1. Analyze the list of available elements
2. Choose an element that would be important to test
3. Use the android_click tool with the element's coordinates (format: "x,y")
4. ALWAYS include an 'explanation' parameter describing your reasoning

Focus on buttons, inputs, and interactive controls.
""",

            "element_priority": f"""
You are testing an Android app. Interact with UI elements to explore functionality.

Available UI elements (with testing priority):
{elements_desc}

Testing priorities:
- [UNTESTED] = High priority, never been tested
- Buttons = Important for navigation
- Spinners/Dropdowns = Often missed, test these!
- Text inputs = Test data entry

Choose an element and use android_click with its coordinates.
IMPORTANT: Include an 'explanation' parameter explaining which priority guided your choice.
""",

            "spinner_focused": f"""
You are testing an Android application. Pay special attention to Spinners and Dropdowns.

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
        Validate coordinate generation for a single screenshot.

        Args:
            screenshot_path: Path to screenshot PNG
            xml_path: Path to UIAutomator XML
            strategy: Prompt strategy to use

        Returns:
            Validation results dictionary
        """
        print(f"\n📸 Testing: {Path(screenshot_path).name} with strategy: {strategy}")

        # Initialize mock device with ground truth
        mock_device = MockDeviceAdapter(xml_path)

        # Get element descriptions for prompt
        elements_desc = mock_device.get_element_list_for_prompt()

        # Create validation tools with explanation support
        tools = create_validation_tools(mock_device)

        # Initialize LLM with tool-calling
        print(f"🧠 Initializing {self.model_name}...")
        llm = ChatOllama(
            model=self.model_name,
            temperature=0.2,  # Phase 0 optimal
            top_p=0.9,
            top_k=50,
            num_ctx=32768
        )

        # Create prompt based on strategy
        base_prompt = self.create_prompt_strategy(strategy, elements_desc)

        # Create agent prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", base_prompt),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])

        # Create tool-calling agent
        agent = create_tool_calling_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=3,
            handle_parsing_errors=True
        )

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

        # Execute agent with vision input
        start_time = time.time()

        try:
            # Create proper text-only input since the model works better this way
            # Include the strategy prompt and element descriptions
            user_input = f"""Look at this Android app screenshot and interact with an important UI element.

{base_prompt}

Image: data:image/png;base64,{image_base64}

Your task: Choose one UI element from the list above and use the appropriate tool (android_click, android_input, etc.) with proper coordinates and explanation."""

            # Execute agent with text input that includes image
            print("🤖 Executing agent...")
            result = agent_executor.invoke({"input": user_input})

            response_time = time.time() - start_time

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
                "agent_output": str(result.get("output", ""))[:500]  # Truncate for readability
            }

            # Print summary
            print(f"\n📊 Results for {strategy}:")
            print(f"  - Total clicks: {metrics['total_clicks']}")
            print(f"  - Hit rate: {metrics['hit_rate']:.1f}%")
            print(f"  - Avg distance: {metrics['avg_distance']:.1f}px")
            print(f"  - Response time: {response_time:.2f}s")

            return validation_result

        except Exception as e:
            print(f"❌ Agent execution failed: {e}")
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
        """
        Validate multiple screenshots across apps and strategies.

        Args:
            dataset_path: Base path to screenshot dataset
            apps: List of app directories to test
            strategies: List of prompt strategies to test
            samples_per_app: Number of samples per app

        Returns:
            Aggregated validation results
        """
        dataset_path = Path(dataset_path)
        all_results = []

        print(f"\n🚀 Starting validation suite")
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
        """
        Aggregate validation results and compute statistics.

        Args:
            results: List of individual validation results

        Returns:
            Aggregated statistics and analysis
        """
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

            strategy_stats[strategy] = {
                "total_tests": len(strategy_results),
                "total_clicks": total_clicks,
                "total_hits": total_hits,
                "hit_rate": (total_hits / total_clicks * 100) if total_clicks > 0 else 0,
                "avg_distance": avg_distance,
                "avg_response_time": avg_response_time
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

    def save_results(self, results: Dict[str, Any], output_path: str):
        """Save validation results to JSON file."""
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to: {output_path}")


def main():
    """Run coordinate validation tests."""
    # Initialize validator
    validator = CoordinateValidator(model_name="PetrosStav/gemma3-tools:4b")

    # Define test configuration
    dataset_path = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    test_apps = [
        "cryptoapp.apk",  # Our simple app
        "byrne.utilities.hashpass_2.apk",  # Similar to cryptoapp
        # "com.hwloc.lstopo_271.apk",  # Dynamic elements
        # "org.secuso.privacyfriendlyludo_5.apk"  # Game with dynamic fields
    ]

    strategies = [
        "baseline",
        "coordinate_validation",
        "enhanced_description",
        "element_priority",
        "spinner_focused"
    ]

    # Run validation
    results = validator.validate_dataset(
        dataset_path=dataset_path,
        apps=test_apps,
        strategies=strategies,
        samples_per_app=3  # Start with few samples for testing
    )

    # Save results
    output_path = f"validation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    validator.save_results(results, output_path)

    # Print summary
    print("\n" + "="*60)
    print("📊 VALIDATION SUMMARY")
    print("="*60)

    if "strategy_stats" in results:
        for strategy, stats in results["strategy_stats"].items():
            print(f"\n{strategy}:")
            print(f"  Hit Rate: {stats['hit_rate']:.1f}%")
            print(f"  Avg Distance: {stats['avg_distance']:.1f}px")
            print(f"  Response Time: {stats['avg_response_time']:.2f}s")

        print(f"\n🏆 Best Strategy: {results['best_strategy']['name']} "
              f"({results['best_strategy']['hit_rate']:.1f}% hit rate)")


if __name__ == "__main__":
    main()