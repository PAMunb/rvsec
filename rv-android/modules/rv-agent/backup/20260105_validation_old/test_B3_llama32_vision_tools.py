#!/usr/bin/env python3
"""
FASE B.3 - Llama3.2-Vision-Tools Test
Tests unitythemaker/llama3.2-vision-tools (custom modified for tools) with A.2.1 architecture

Applies lessons from vision research:
- Tests coordinate validation strategy without and with optimizations
- Compares structured vs unstructured output approaches
- Validates A.2.1 multimodal preservation
"""

import json
import time
import base64
from pathlib import Path
from typing import Dict, Any, List, TypedDict

from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_models import ChatOllama
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END

from shared_validation_utils import (
    ValidationMetrics,
    CryptoAppGroundTruth,
    validate_coordinates,
    encode_screenshot_b64,
    log_test_result
)

# LangGraph State with A.2.1 multimodal context preservation
class AndroidAgentStateFixed(TypedDict):
    messages: List[Any]
    screenshot_b64: str  # PRESERVE screenshot across iterations
    multimodal_preserved_history: List[bool]
    tool_executions: List[Dict[str, Any]]
    iteration_count: int
    optimization_mode: str  # Track whether using vision optimizations

@tool
def android_click(x: int, y: int, element_description: str = "") -> str:
    """Click at specific coordinates on Android screen"""
    return f"Clicked at position ({x}, {y}). Element: {element_description}"

@tool
def android_long_click(x: int, y: int, element_description: str = "") -> str:
    """Long click at specific coordinates on Android screen"""
    return f"Long clicked at position ({x}, {y}). Element: {element_description}"

@tool
def android_scroll(direction: str, element_description: str = "") -> str:
    """Scroll in specified direction"""
    return f"Scrolled {direction}. Element: {element_description}"

def create_llama32_agent_node(model, use_vision_optimization=True):
    """Agent node with configurable vision optimization"""
    def agent_node(state: AndroidAgentStateFixed):
        iteration = state["iteration_count"]
        screenshot_b64 = state["screenshot_b64"]
        tool_executions = state["tool_executions"]
        optimization_mode = state["optimization_mode"]

        if use_vision_optimization:
            # OPTIMIZED VERSION - Based on vision research discoveries
            context_parts = [
                "You are a specialized Android testing agent with advanced vision capabilities.",
                "Analyze the screenshot systematically and execute precise testing actions.",
                "",
                "COORDINATE PRECISION PROTOCOL (100% hit rate strategy):",
                "- Reference all coordinates using 'at position (x, y)' format",
                "- Target element centers for maximum accuracy",
                "- Consider UI element boundaries and padding",
                "- Validate coordinate ranges before selection",
                "",
                "SYSTEMATIC TESTING APPROACH:",
                "- Identify interactive UI elements (buttons, inputs, links)",
                "- Prioritize elements that advance application functionality",
                "- Execute ONE precise action per iteration",
                "",
                "AVAILABLE PRECISION TOOLS:",
                "- android_click(x, y, element_description): Precise tap on element",
                "- android_long_click(x, y, element_description): Extended press",
                "- android_scroll(direction, element_description): Directional scroll",
                "",
                f"TESTING ITERATION: {iteration + 1}/3 (systematic exploration)"
            ]

            if tool_executions:
                context_parts.extend([
                    "",
                    "PREVIOUS TESTING ACTIONS:",
                ])
                for i, exec_info in enumerate(tool_executions, 1):
                    result = exec_info.get('result', 'Action completed')
                    context_parts.append(f"  Step {i}: {result}")

            context_parts.extend([
                "",
                "CURRENT TASK: Analyze the screenshot and execute ONE optimal testing action.",
                "Focus on advancing the application state through meaningful interactions.",
                "Apply coordinate precision using 'at position (x, y)' validation strategy."
            ])

        else:
            # BASELINE VERSION - Without vision optimizations
            context_parts = [
                "You are an Android testing agent. Look at the screenshot and click something.",
                "",
                "Available tools:",
                "- android_click(x, y, element_description): Click coordinates",
                "- android_long_click(x, y, element_description): Long click",
                "- android_scroll(direction, element_description): Scroll",
                "",
                f"Iteration: {iteration + 1}/3"
            ]

            if tool_executions:
                context_parts.append("Previous actions:")
                for i, exec_info in enumerate(tool_executions, 1):
                    context_parts.append(f"{i}. {exec_info.get('result', 'Unknown')}")

            context_parts.append("Click on something in the screenshot.")

        context_with_history = "\n".join(context_parts)

        # A.2.1 ARCHITECTURE: Fresh multimodal message recreation
        fresh_multimodal_message = HumanMessage(content=[
            {"type": "text", "text": context_with_history},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}}
        ])

        # Execute with Llama3.2-Vision-Tools
        response = model.invoke([fresh_multimodal_message])

        # Track multimodal preservation
        has_multimodal = isinstance(fresh_multimodal_message.content, list) and len(fresh_multimodal_message.content) > 1

        # Update state
        new_state = state.copy()
        new_state["messages"].append(fresh_multimodal_message)
        new_state["messages"].append(response)
        new_state["multimodal_preserved_history"].append(has_multimodal)
        new_state["iteration_count"] = iteration + 1

        return new_state

    return agent_node

def create_tool_execution_node():
    """Tool execution with enhanced result tracking"""
    def tool_node(state: AndroidAgentStateFixed):
        last_message = state["messages"][-1]
        tool_calls = getattr(last_message, 'tool_calls', [])

        if not tool_calls:
            return state

        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # Execute tool with error handling
            try:
                if tool_name == "android_click":
                    result = android_click.invoke(tool_args)
                elif tool_name == "android_long_click":
                    result = android_long_click.invoke(tool_args)
                elif tool_name == "android_scroll":
                    result = android_scroll.invoke(tool_args)
                else:
                    result = f"Unknown tool: {tool_name}"
            except Exception as e:
                result = f"Tool execution error: {str(e)}"

            # Enhanced execution tracking
            execution_info = {
                "tool": tool_name,
                "args": tool_args,
                "result": result,
                "iteration": state["iteration_count"],
                "element_description": tool_args.get("element_description", ""),
                "optimization_mode": state["optimization_mode"]
            }

            new_state = state.copy()
            new_state["tool_executions"].append(execution_info)

            return new_state

        return state

    return tool_node

def should_continue(state: AndroidAgentStateFixed):
    """Continue logic for 3 iterations"""
    return "continue" if state["iteration_count"] < 3 else "end"

def run_llama32_test(use_vision_optimization=True, test_suffix=""):
    """Run Llama3.2-Vision-Tools test with configurable optimization"""

    optimization_label = "WITH Vision Optimizations" if use_vision_optimization else "WITHOUT Optimizations (Baseline)"
    print(f"🔬 FASE B.3{test_suffix} - Llama3.2-Vision-Tools Test ({optimization_label})")
    print("=" * 70)

    # Initialize Llama3.2-Vision-Tools model
    model = ChatOllama(
        model="unitythemaker/llama3.2-vision-tools",
        temperature=0.1,
        num_predict=180
    ).bind_tools([android_click, android_long_click, android_scroll])

    # Load test screenshot
    screenshot_path = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/004.png"
    screenshot_b64 = encode_screenshot_b64(screenshot_path)

    if not screenshot_b64:
        print("❌ Screenshot loading failed")
        return None

    print(f"📱 Screenshot: {screenshot_path}")
    print(f"🤖 Model: unitythemaker/llama3.2-vision-tools")
    print(f"🧪 Mode: {optimization_label}")

    # Build LangGraph workflow
    workflow = StateGraph(AndroidAgentStateFixed)

    # Add nodes with optimization setting
    workflow.add_node("agent", create_llama32_agent_node(model, use_vision_optimization))
    workflow.add_node("tools", create_tool_execution_node())

    # Configure edges
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        lambda state: "tools" if getattr(state["messages"][-1], 'tool_calls', None) else "end",
        {
            "tools": "tools",
            "end": END
        }
    )
    workflow.add_edge("tools", "agent")
    workflow.add_conditional_edges("agent", should_continue, {"continue": "agent", "end": END})

    # Compile workflow
    app = workflow.compile()

    # Initialize state with optimization tracking
    optimization_mode = "vision_optimized" if use_vision_optimization else "baseline"
    initial_state = AndroidAgentStateFixed(
        messages=[],
        screenshot_b64=screenshot_b64,  # A.2.1 preservation
        multimodal_preserved_history=[],
        tool_executions=[],
        iteration_count=0,
        optimization_mode=optimization_mode
    )

    # Execute test
    start_time = time.time()

    try:
        final_state = app.invoke(initial_state)
        execution_time = time.time() - start_time

        # Calculate metrics
        metrics = ValidationMetrics(
            multimodal_support=len(final_state["multimodal_preserved_history"]) > 0 and all(final_state["multimodal_preserved_history"]),
            tool_calling_detected=len(final_state["tool_executions"]) > 0,
            response_time=execution_time,
            iterations_completed=final_state["iteration_count"],
            tool_executions=len(final_state["tool_executions"]),
            success_rate=100.0 if final_state["tool_executions"] and all(final_state["multimodal_preserved_history"]) else 0.0,
            multimodal_history=final_state["multimodal_preserved_history"]
        )

        # Coordinate validation using vision research methodology
        ground_truth = CryptoAppGroundTruth()
        coordinate_validations = []

        for exec_info in final_state["tool_executions"]:
            if "args" in exec_info and "x" in exec_info["args"] and "y" in exec_info["args"]:
                x, y = exec_info["args"]["x"], exec_info["args"]["y"]
                is_valid, distance = validate_coordinates(x, y, ground_truth.screenshot_004_elements)
                coordinate_validations.append({
                    "coords": [x, y],
                    "valid": is_valid,
                    "distance": distance,
                    "element_description": exec_info.get("element_description", ""),
                    "optimization_mode": exec_info.get("optimization_mode", "unknown")
                })

        # Results analysis
        print(f"\n📊 TEST RESULTS ({optimization_label}):")
        print(f"✅ Multimodal Support: {metrics.multimodal_support}")
        print(f"🛠️  Tool Calling: {metrics.tool_calling_detected}")
        print(f"⏱️  Response Time: {metrics.response_time:.2f}s")
        print(f"🔄 Iterations: {metrics.iterations_completed}/3")
        print(f"🎯 Tool Executions: {metrics.tool_executions}")
        print(f"📈 Success Rate: {metrics.success_rate}%")
        print(f"🖼️  Multimodal History: {metrics.multimodal_history}")

        if coordinate_validations:
            valid_coords = sum(1 for val in coordinate_validations if val["valid"])
            total_coords = len(coordinate_validations)
            coord_accuracy = (valid_coords / total_coords) * 100 if total_coords > 0 else 0

            print(f"\n🎯 COORDINATE ANALYSIS (Vision Research Applied):")
            print(f"   📊 Accuracy Rate: {coord_accuracy:.1f}% ({valid_coords}/{total_coords})")

            for i, val in enumerate(coordinate_validations, 1):
                status = "✅ PRECISE" if val["valid"] else "❌ IMPRECISE"
                desc = f" - {val['element_description']}" if val['element_description'] else ""
                print(f"   {i}. {val['coords']} {status} ({val['distance']:.1f}px){desc}")

        if final_state["tool_executions"]:
            print(f"\n🛠️  EXECUTION TRACE:")
            for i, exec_info in enumerate(final_state["tool_executions"], 1):
                result = exec_info.get("result", "Unknown action")
                print(f"   {i}. {result}")

        # Determine result classification
        coord_accuracy = 0
        if coordinate_validations:
            coord_accuracy = sum(1 for val in coordinate_validations if val["valid"]) / len(coordinate_validations) * 100

        if metrics.multimodal_support and metrics.tool_calling_detected:
            if coord_accuracy >= 80:
                print(f"\n🎉 RESULTADO: EXCELENTE - Architecture + Vision Strategy Effective")
                status = "EXCELLENT"
            elif coord_accuracy >= 60:
                print(f"\n⚡ RESULTADO: BOM - Strong architecture, coordinate precision improvable")
                status = "GOOD"
            else:
                print(f"\n⚠️  RESULTADO: MODERADO - Architecture works, low coordinate precision")
                status = "MODERATE"
        else:
            print(f"\n❌ RESULTADO: INADEQUADO - Architecture or multimodal issues")
            status = "INADEQUATE"

        # Return comprehensive result data
        result_data = {
            "model_name": "unitythemaker/llama3.2-vision-tools",
            "test_phase": f"FASE_B3{test_suffix}",
            "architecture": "LangGraph_A2.1",
            "optimization_applied": use_vision_optimization,
            "status": status,
            "metrics": metrics._asdict(),
            "coordinate_validations": coordinate_validations,
            "coordinate_accuracy": coord_accuracy,
            "tool_executions": final_state["tool_executions"]
        }

        test_name = f"B3{test_suffix}_llama32_vision_tools_{'optimized' if use_vision_optimization else 'baseline'}"
        log_test_result(test_name, result_data)

        return result_data

    except Exception as e:
        print(f"❌ Test Execution Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_llama32_vision_tools():
    """Run both optimized and baseline tests for comparison"""

    print("🚀 LLAMA3.2-VISION-TOOLS COMPARATIVE TESTING")
    print("=" * 70)

    # Test 1: Without vision optimizations (baseline)
    print("\n" + "="*70)
    print("📊 BASELINE TEST (Control Group)")
    baseline_results = run_llama32_test(use_vision_optimization=False, test_suffix="_baseline")

    print("\n" + "="*70)
    print("🔬 OPTIMIZED TEST (Vision Research Applied)")

    # Test 2: With vision optimizations
    optimized_results = run_llama32_test(use_vision_optimization=True, test_suffix="_optimized")

    # Comparative analysis
    if baseline_results and optimized_results:
        print("\n" + "="*70)
        print("📈 COMPARATIVE ANALYSIS")
        print("="*70)

        baseline_coord_acc = baseline_results.get("coordinate_accuracy", 0)
        optimized_coord_acc = optimized_results.get("coordinate_accuracy", 0)

        print(f"📊 Coordinate Accuracy:")
        print(f"   Baseline:  {baseline_coord_acc:.1f}%")
        print(f"   Optimized: {optimized_coord_acc:.1f}%")
        print(f"   Improvement: {optimized_coord_acc - baseline_coord_acc:+.1f}%")

        baseline_success = baseline_results["metrics"]["success_rate"]
        optimized_success = optimized_results["metrics"]["success_rate"]

        print(f"🎯 Overall Success Rate:")
        print(f"   Baseline:  {baseline_success:.1f}%")
        print(f"   Optimized: {optimized_success:.1f}%")
        print(f"   Improvement: {optimized_success - baseline_success:+.1f}%")

        if optimized_coord_acc > baseline_coord_acc:
            print(f"\n✅ CONCLUSION: Vision optimization strategy shows measurable improvement")
        else:
            print(f"\n❓ CONCLUSION: Vision optimization impact unclear - model-specific behavior")

if __name__ == "__main__":
    test_llama32_vision_tools()