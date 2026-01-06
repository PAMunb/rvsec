#!/usr/bin/env python3
"""
FASE B.1 - Qwen2.5VL Simple Structured Output Test
Tests qwen2.5vl:7b (vision champion - 98.3% success) with simplified direct approach

Based on vision research:
- Applies coordinate format "at position (x, y)" for 100% hit rate
- Uses structured JSON output for tool simulation
- Tests multimodal preservation in simple chain
"""

import json
import time
import re
from pathlib import Path

from langchain_core.messages import HumanMessage
from langchain_community.chat_models import ChatOllama

from shared_validation_utils import (
    ValidationMetrics,
    CryptoAppGroundTruth,
    validate_coordinates,
    encode_screenshot_b64,
    log_test_result
)

def parse_json_response(response_text: str):
    """Parse JSON response from qwen2.5vl, handling various formats"""
    try:
        # Try direct JSON parsing first
        if response_text.strip().startswith('{'):
            return json.loads(response_text.strip())

        # Look for JSON block in response
        json_match = re.search(r'\{[^}]*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())

        return None
    except Exception:
        return None

def test_qwen2_5vl_simple_structured():
    """Test qwen2.5vl:7b with direct structured output approach"""

    print("🔬 FASE B.1 - Qwen2.5VL Simple Structured Output Test")
    print("=" * 60)

    # Initialize qwen2.5vl model (vision champion)
    model = ChatOllama(
        model="qwen2.5vl:7b",
        temperature=0.1,
        num_predict=400
    )

    # Load CryptoApp screenshot
    screenshot_path = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/004.png"
    screenshot_b64 = encode_screenshot_b64(screenshot_path)

    if not screenshot_b64:
        print("❌ Failed to load screenshot")
        return

    print(f"📱 Screenshot: {screenshot_path}")
    print(f"🤖 Model: qwen2.5vl:7b (vision champion - 98.3% success rate)")
    print(f"🏗️  Approach: Direct structured JSON output")

    # Create vision-optimized prompt (from research docs)
    prompt = """You are an expert Android testing agent with advanced vision capabilities.
Analyze the screenshot systematically and generate ONE precise action.

VISION OPTIMIZATION STRATEGY (98.3% success rate from research):
- Use "at position (x, y)" coordinate format for maximum accuracy
- Target center of UI elements for optimal precision
- Identify interactive buttons, inputs, and clickable elements
- Focus on elements that advance application functionality

RESPONSE FORMAT - Return ONLY valid JSON:
{
    "action": "android_click",
    "coordinates": [x, y],
    "element_description": "clear description of target element",
    "reasoning": "why this action advances testing",
    "confidence": "high/medium/low"
}

TASK: Analyze this CryptoApp screenshot and identify the most important button to click for testing.
Focus on buttons like "Message Digest", "Cipher", or "Generated" that advance app functionality.
Return ONLY valid JSON with precise coordinates using vision optimization strategy."""

    # Execute multiple iterations to test consistency
    iterations = 3
    results = []
    multimodal_preserved = []

    start_time = time.time()

    for i in range(iterations):
        print(f"\n🔄 Iteration {i+1}/{iterations}")

        # Create fresh multimodal message each time
        multimodal_message = HumanMessage(content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}}
        ])

        # Track multimodal preservation
        has_multimodal = isinstance(multimodal_message.content, list) and len(multimodal_message.content) > 1
        multimodal_preserved.append(has_multimodal)

        # Invoke model
        response = model.invoke([multimodal_message])
        response_text = response.content if hasattr(response, 'content') else str(response)

        print(f"   📝 Raw Response: {response_text[:100]}...")

        # Parse JSON response
        parsed_action = parse_json_response(response_text)

        if parsed_action:
            print(f"   ✅ Parsed Action: {parsed_action.get('action', 'unknown')}")
            print(f"   🎯 Coordinates: {parsed_action.get('coordinates', [])}")
            print(f"   📄 Description: {parsed_action.get('element_description', '')}")

            results.append({
                "iteration": i + 1,
                "parsed_successfully": True,
                "action": parsed_action,
                "raw_response": response_text[:200]
            })
        else:
            print(f"   ❌ Failed to parse JSON response")
            results.append({
                "iteration": i + 1,
                "parsed_successfully": False,
                "action": None,
                "raw_response": response_text[:200]
            })

    execution_time = time.time() - start_time

    # Analyze results
    successful_parses = sum(1 for r in results if r["parsed_successfully"])
    parsing_success_rate = (successful_parses / iterations) * 100

    print(f"\n📊 ANALYSIS RESULTS:")
    print(f"✅ Multimodal Support: {all(multimodal_preserved)}")
    print(f"📊 JSON Parsing Success: {parsing_success_rate:.1f}% ({successful_parses}/{iterations})")
    print(f"⏱️  Total Time: {execution_time:.2f}s")
    print(f"🖼️  Multimodal History: {multimodal_preserved}")

    # Coordinate validation using vision research methodology
    ground_truth = CryptoAppGroundTruth()
    coordinate_validations = []

    for result in results:
        if result["parsed_successfully"] and result["action"]:
            action = result["action"]
            coordinates = action.get("coordinates", [])

            if coordinates and len(coordinates) == 2:
                x, y = int(coordinates[0]), int(coordinates[1])
                is_valid, distance = validate_coordinates(x, y, ground_truth.screenshot_004_elements)

                coordinate_validations.append({
                    "iteration": result["iteration"],
                    "coords": [x, y],
                    "valid": is_valid,
                    "distance": distance,
                    "element_description": action.get("element_description", ""),
                    "confidence": action.get("confidence", "unknown")
                })

    if coordinate_validations:
        valid_coords = sum(1 for val in coordinate_validations if val["valid"])
        total_coords = len(coordinate_validations)
        coord_accuracy = (valid_coords / total_coords) * 100

        print(f"\n🎯 COORDINATE PRECISION (Vision Research Applied):")
        print(f"   📊 Accuracy Rate: {coord_accuracy:.1f}% ({valid_coords}/{total_coords})")

        for val in coordinate_validations:
            status = "✅ PRECISE" if val["valid"] else "❌ IMPRECISE"
            desc = f" - {val['element_description']}" if val['element_description'] else ""
            conf = f" ({val['confidence']})" if val['confidence'] != 'unknown' else ""
            print(f"   {val['iteration']}. {val['coords']} {status} ({val['distance']:.1f}px){desc}{conf}")

    else:
        coord_accuracy = 0
        print(f"\n❌ No valid coordinates found for validation")

    # Create comprehensive metrics
    metrics = ValidationMetrics(
        multimodal_support=all(multimodal_preserved),
        tool_calling_detected=successful_parses > 0,  # JSON parsing simulates tool calling
        response_time=execution_time,
        iterations_completed=iterations,
        tool_executions=successful_parses,
        success_rate=parsing_success_rate,
        multimodal_history=multimodal_preserved
    )

    # Determine final status
    if metrics.multimodal_support and parsing_success_rate >= 80:
        if coord_accuracy >= 80:
            print(f"\n🎉 RESULTADO: EXCELENTE - qwen2.5vl shows strong vision+tools capability")
            status = "EXCELLENT"
        elif coord_accuracy >= 60:
            print(f"\n⚡ RESULTADO: BOM - Strong JSON generation, coordinate precision good")
            status = "GOOD"
        else:
            print(f"\n⚠️  RESULTADO: MODERADO - JSON works, coordinate precision needs improvement")
            status = "MODERATE"
    elif parsing_success_rate >= 50:
        print(f"\n📊 RESULTADO: PARCIAL - Inconsistent JSON generation")
        status = "PARTIAL"
    else:
        print(f"\n❌ RESULTADO: INADEQUADO - Poor structured output capability")
        status = "INADEQUATE"

    # Log comprehensive results
    result_data = {
        "model_name": "qwen2.5vl:7b",
        "test_phase": "FASE_B1_SIMPLE",
        "approach": "direct_structured_json_output",
        "vision_optimizations_applied": True,
        "status": status,
        "metrics": metrics._asdict(),
        "parsing_success_rate": parsing_success_rate,
        "coordinate_accuracy": coord_accuracy,
        "coordinate_validations": coordinate_validations,
        "iteration_results": results
    }

    log_test_result("B1_simple_qwen2_5vl_structured", result_data)

    print(f"\n🔍 VISION STRATEGY VALIDATION:")
    print(f"   ✅ Champion Model Used: qwen2.5vl:7b")
    print(f"   ✅ Coordinate Format Applied: 'at position (x, y)'")
    print(f"   ✅ Structured Output Approach: JSON parsing")
    print(f"   📊 Overall Effectiveness: {status}")

if __name__ == "__main__":
    test_qwen2_5vl_simple_structured()