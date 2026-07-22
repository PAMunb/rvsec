#!/usr/bin/env python3
"""
FASE B.2 - Gemma3-Tools Multimodal Test
Tests PetrosStav/gemma3-tools:4b (current RVAgent model) with A.2.1 architecture

Applies vision optimizations:
- Coordinate validation strategy from vision research
- A.2.1 multimodal context preservation
- Comparison with previous individual success vs systematic testing
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

def create_gemma_agent_node(model):
    """Agent node optimized for Gemma3-tools with vision strategy"""
    def agent_node(state: AndroidAgentStateFixed):
        iteration = state["iteration_count"]
        screenshot_b64 = state["screenshot_b64"]
        tool_executions = state["tool_executions"]

        # Enhanced context with vision research optimizations
        context_parts = [
            "You are an expert Android testing agent with vision capabilities.",
            "Analyze the screenshot carefully and interact with meaningful UI elements.",
            "",
            "COORDINATE PRECISION STRATEGY (from vision research):",
            "- Always reference coordinates using 'at position (x, y)' format",
            "- Target center of UI elements for optimal accuracy",
            "- Consider element boundaries when clicking",
            "",
            "AVAILABLE TESTING ACTIONS:",
            "- android_click(x, y, element_description): Tap UI element",
            "- android_long_click(x, y, element_description): Long press element",
            "- android_scroll(direction, element_description): Scroll interface",
            "",
            f"CURRENT ITERATION: {iteration + 1}/3 (systematic testing)"
        ]

        if tool_executions:
            context_parts.extend([
                "",
                "TESTING HISTORY:",
            ])
            for i, exec_info in enumerate(tool_executions, 1):
                action = exec_info.get('result', 'Unknown action')
                context_parts.append(f"  {i}. {action}")

        context_parts.extend([
            "",
            "TASK: Identify and interact with ONE relevant UI element in the screenshot.",
            "Focus on buttons, inputs, or interactive elements that advance app functionality.",
            "Use precise coordinate targeting with 'at position (x, y)' references."
        ])

        context_with_history = "\n".join(context_parts)

        # A.2.1 CRITICAL FIX: Fresh multimodal message recreation
        fresh_multimodal_message = HumanMessage(content=[
            {"type": "text", "text": context_with_history},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}}
        ])

        # Invoke Gemma3-tools model
        response = model.invoke([fresh_multimodal_message])

        # Verify multimodal preservation
        has_multimodal = isinstance(fresh_multimodal_message.content, list) and len(fresh_multimodal_message.content) > 1

        # Update state with preservation tracking
        new_state = state.copy()
        new_state["messages"].append(fresh_multimodal_message)
        new_state["messages"].append(response)
        new_state["multimodal_preserved_history"].append(has_multimodal)
        new_state["iteration_count"] = iteration + 1

        return new_state

    return agent_node

def create_tool_execution_node():
    """Enhanced tool execution with detailed tracking"""
    def tool_node(state: AndroidAgentStateFixed):
        last_message = state["messages"][-1]
        tool_calls = getattr(last_message, 'tool_calls', [])

        if not tool_calls:
            return state

        # Process each tool call with enhanced tracking
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # Execute appropriate tool
            if tool_name == "android_click":
                result = android_click.invoke(tool_args)
            elif tool_name == "android_long_click":
                result = android_long_click.invoke(tool_args)
            elif tool_name == "android_scroll":
                result = android_scroll.invoke(tool_args)
            else:
                result = f"Unknown tool: {tool_name}"

            # Enhanced execution tracking
            execution_info = {
                "tool": tool_name,
                "args": tool_args,
                "result": result,
                "iteration": state["iteration_count"],
                "element_description": tool_args.get("element_description", "")
            }

            new_state = state.copy()
            new_state["tool_executions"].append(execution_info)

            return new_state

        return state

    return tool_node

def should_continue(state: AndroidAgentStateFixed):
    """Continue until 3 iterations complete"""
    return "continue" if state["iteration_count"] < 3 else "end"

def test_gemma3_tools_multimodal():
    """Test Gemma3-tools with enhanced A.2.1 architecture and vision optimizations"""

    print("🔬 FASE B.2 - Gemma3-Tools Multimodal Test")
    print("=" * 60)

    # Initialize Gemma3-tools model (current RVAgent model)
    model = ChatOllama(
        model="PetrosStav/gemma3-tools:4b",
        temperature=0.1,
        num_predict=150
    ).bind_tools([android_click, android_long_click, android_scroll])

    # Load CryptoApp screenshot for testing
    screenshot_path = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/004.png"
    screenshot_b64 = encode_screenshot_b64(screenshot_path)

    if not screenshot_b64:
        print("❌ Failed to load screenshot for testing")
        return

    print(f"📱 Screenshot: {screenshot_path}")
    print(f"🤖 Model: PetrosStav/gemma3-tools:4b (current RVAgent)")
    print(f"🏗️  Architecture: A.2.1 + Vision Optimizations")

    # Build LangGraph workflow with A.2.1 improvements
    workflow = StateGraph(AndroidAgentStateFixed)

    # Configure nodes
    workflow.add_node("agent", create_gemma_agent_node(model))
    workflow.add_node("tools", create_tool_execution_node())

    # Configure flow
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

    # Initialize state with screenshot preservation
    initial_state = AndroidAgentStateFixed(
        messages=[],
        screenshot_b64=screenshot_b64,  # A.2.1 PRESERVATION
        multimodal_preserved_history=[],
        tool_executions=[],
        iteration_count=0
    )

    # Execute systematic testing
    start_time = time.time()

    try:
        final_state = app.invoke(initial_state)
        execution_time = time.time() - start_time

        # Calculate comprehensive metrics
        metrics = ValidationMetrics(
            multimodal_support=len(final_state["multimodal_preserved_history"]) > 0 and all(final_state["multimodal_preserved_history"]),
            tool_calling_detected=len(final_state["tool_executions"]) > 0,
            response_time=execution_time,
            iterations_completed=final_state["iteration_count"],
            tool_executions=len(final_state["tool_executions"]),
            success_rate=100.0 if final_state["tool_executions"] and all(final_state["multimodal_preserved_history"]) else 0.0,
            multimodal_history=final_state["multimodal_preserved_history"]
        )

        # Apply coordinate validation from vision research
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
                    "element_description": exec_info.get("element_description", "")
                })

        # Display comprehensive results
        print(f"\n📊 SYSTEMATIC TEST RESULTS:")
        print(f"✅ Multimodal Preserved: {metrics.multimodal_support}")
        print(f"🛠️  Tool Calling Active: {metrics.tool_calling_detected}")
        print(f"⏱️  Total Time: {metrics.response_time:.2f}s")
        print(f"🔄 Completed Iterations: {metrics.iterations_completed}/3")
        print(f"🎯 Tool Executions: {metrics.tool_executions}")
        print(f"📈 Overall Success: {metrics.success_rate}%")
        print(f"🖼️  Multimodal History: {metrics.multimodal_history}")

        if coordinate_validations:
            print(f"\n🎯 COORDINATE PRECISION (Vision Strategy Applied):")
            valid_coords = sum(1 for val in coordinate_validations if val["valid"])
            total_coords = len(coordinate_validations)
            coord_success = (valid_coords / total_coords) * 100 if total_coords > 0 else 0

            for i, val in enumerate(coordinate_validations, 1):
                status = "✅ ACCURATE" if val["valid"] else "❌ OFF-TARGET"
                desc = f" ({val['element_description']})" if val['element_description'] else ""
                print(f"   {i}. {val['coords']} - {status} ({val['distance']:.1f}px){desc}")

            print(f"   📊 Coordinate Accuracy: {coord_success:.1f}% ({valid_coords}/{total_coords})")

        if final_state["tool_executions"]:
            print(f"\n🛠️  DETAILED ACTION LOG:")
            for i, exec_info in enumerate(final_state["tool_executions"], 1):
                iteration = exec_info.get("iteration", "?")
                result = exec_info.get("result", "No result")
                print(f"   [{iteration+1}] {result}")

        # Determine final status
        coord_accuracy = 0
        if coordinate_validations:
            coord_accuracy = sum(1 for val in coordinate_validations if val["valid"]) / len(coordinate_validations) * 100

        if metrics.multimodal_support and metrics.tool_calling_detected:
            if coord_accuracy >= 80:
                print(f"\n🎉 RESULTADO: SUCESSO TOTAL - A.2.1 + Vision Strategy Effective")
                status = "SUCCESS_TOTAL"
            elif coord_accuracy >= 50:
                print(f"\n⚡ RESULTADO: SUCESSO PARCIAL - Architecture works, coordinate tuning needed")
                status = "SUCCESS_PARTIAL"
            else:
                print(f"\n⚠️  RESULTADO: LIMITADO - Multimodal works, coordinate precision low")
                status = "LIMITED_SUCCESS"
        else:
            print(f"\n❌ RESULTADO: FALHA ARQUITETURAL")
            status = "ARCHITECTURE_FAILURE"

        # Comprehensive result logging
        result_data = {
            "model_name": "PetrosStav/gemma3-tools:4b",
            "test_phase": "FASE_B2",
            "architecture": "LangGraph_A2.1_enhanced_vision_strategy",
            "status": status,
            "metrics": metrics._asdict(),
            "coordinate_validations": coordinate_validations,
            "coordinate_accuracy": coord_accuracy,
            "tool_executions": final_state["tool_executions"],
            "vision_strategy_applied": True
        }

        log_test_result("B2_gemma3_tools_multimodal", result_data)

    except Exception as e:
        print(f"❌ Execution Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gemma3_tools_multimodal()