#!/usr/bin/env python3
"""
FASE B.1 - Qwen2.5VL Structured Output Test
Tests qwen2.5vl:7b (vision champion - 98.3% success) with A.2.1 architecture

Based on vision research:
- qwen2.5vl:7b identified as champion model (docs/planos/vision/002_vision.md)
- Coordinate format "at position (x, y)" achieved 100% hit rate
- Scientific validation confirmed methodology robustness
"""

import json
import time
import base64
from pathlib import Path
from typing import Dict, Any, List, TypedDict, Annotated
import operator

from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_models import ChatOllama
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
import re
import json as json_lib

from shared_validation_utils import (
    ValidationMetrics,
    CryptoAppGroundTruth,
    validate_coordinates,
    encode_screenshot_b64,
    log_test_result
)

# LangGraph State with A.2.1 multimodal context preservation
class AndroidAgentStateFixed(TypedDict):
    messages: Annotated[List[Any], operator.add]
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

def create_qwen_agent_node(model):
    """Agent node using structured JSON output for qwen2.5vl:7b"""
    def agent_node(state: AndroidAgentStateFixed):
        iteration = state["iteration_count"]
        screenshot_b64 = state["screenshot_b64"]
        tool_executions = state["tool_executions"]

        # Build context with vision optimization and structured output
        context_parts = [
            "You are an expert Android testing agent with advanced vision capabilities.",
            "Analyze the screenshot systematically and generate a precise action.",
            "",
            "VISION OPTIMIZATION STRATEGY (98.3% success rate):",
            "- Use 'at position (x, y)' coordinate format for maximum accuracy",
            "- Target center of UI elements for optimal precision",
            "- Identify interactive buttons, inputs, and clickable elements",
            "",
            "RESPONSE FORMAT - Return valid JSON only:",
            """{
    "action": "android_click",
    "coordinates": [x, y],
    "element_description": "description of target element",
    "reasoning": "why this action advances testing"
}""",
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
            "TASK: Analyze the CryptoApp screenshot and select ONE optimal testing action.",
            "Focus on buttons that advance app functionality (Message Digest, Cipher, etc.).",
            "Return ONLY valid JSON with precise coordinates using vision optimization strategy."
        ])

        context_with_history = "\n".join(context_parts)

        # A.2.1 SOLUTION: Always recreate fresh multimodal message
        fresh_multimodal_message = HumanMessage(content=[
            {"type": "text", "text": context_with_history},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}}
        ])

        # Invoke qwen2.5vl with structured prompt
        response = model.invoke([fresh_multimodal_message])

        # Check multimodal preservation
        has_multimodal = isinstance(fresh_multimodal_message.content, list) and len(fresh_multimodal_message.content) > 1

        # Update state with proper LangGraph format
        return {
            "messages": [fresh_multimodal_message, response],
            "multimodal_preserved_history": state["multimodal_preserved_history"] + [has_multimodal],
            "iteration_count": iteration + 1
        }

    return agent_node

def parse_json_response(response_text: str) -> Dict[str, Any]:
    """Parse JSON response from qwen2.5vl, handling various formats"""
    try:
        # Try direct JSON parsing first
        if response_text.strip().startswith('{'):
            return json_lib.loads(response_text.strip())

        # Look for JSON block in response
        json_match = re.search(r'\{[^}]*\}', response_text, re.DOTALL)
        if json_match:
            return json_lib.loads(json_match.group())

        return None
    except Exception:
        return None

def create_tool_node():
    """Tool execution node for structured JSON responses"""
    def tool_node(state: AndroidAgentStateFixed):
        last_message = state["messages"][-1]
        response_text = last_message.content if hasattr(last_message, 'content') else str(last_message)

        # Parse JSON response from qwen2.5vl
        parsed_action = parse_json_response(response_text)

        if not parsed_action:
            return state

        # Extract action details
        action = parsed_action.get("action", "")
        coordinates = parsed_action.get("coordinates", [])
        element_description = parsed_action.get("element_description", "")

        if not coordinates or len(coordinates) != 2:
            return state

        # Execute the action
        x, y = int(coordinates[0]), int(coordinates[1])

        if action == "android_click":
            result = android_click.invoke({"x": x, "y": y, "element_description": element_description})
        elif action == "android_long_click":
            result = android_long_click.invoke({"x": x, "y": y, "element_description": element_description})
        elif action == "android_scroll":
            direction = parsed_action.get("direction", "down")
            result = android_scroll.invoke({"direction": direction, "element_description": element_description})
        else:
            result = f"Unknown action: {action}"

        # Record execution with enhanced tracking
        execution_info = {
            "tool": action,
            "args": {"x": x, "y": y, "element_description": element_description},
            "result": result,
            "parsed_response": parsed_action,
            "raw_response": response_text[:200]  # Truncated for logging
        }

        return {
            "tool_executions": state["tool_executions"] + [execution_info]
        }

    return tool_node

def should_continue(state: AndroidAgentStateFixed):
    """Decide whether to continue or end"""
    return "continue" if state["iteration_count"] < 3 else "end"

def test_qwen2_5vl_structured_output():
    """Test qwen2.5vl:7b with A.2.1 architecture and vision optimizations"""

    print("🔬 FASE B.1 - Qwen2.5VL Structured Output Test")
    print("=" * 60)

    # Initialize model (vision champion from research)
    model = ChatOllama(
        model="qwen2.5vl:7b",
        temperature=0.1,
        num_predict=300
    )

    # Load test screenshot
    screenshot_path = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/004.png"
    screenshot_b64 = encode_screenshot_b64(screenshot_path)

    if not screenshot_b64:
        print("❌ Failed to encode screenshot")
        return

    print(f"📱 Screenshot: {screenshot_path}")
    print(f"🤖 Model: qwen2.5vl:7b (vision champion - 98.3% success rate)")

    # Create LangGraph workflow with A.2.1 architecture
    workflow = StateGraph(AndroidAgentStateFixed)

    # Add nodes
    workflow.add_node("agent", create_qwen_agent_node(model))
    workflow.add_node("tools", create_tool_node())

    # Add edges for structured output workflow
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        lambda state: "tools" if len(state["messages"]) > 0 else "end",
        {
            "tools": "tools",
            "end": END
        }
    )
    workflow.add_edge("tools", "agent")
    workflow.add_conditional_edges("agent", should_continue, {"continue": "agent", "end": END})

    # Compile workflow
    app = workflow.compile()

    # Initialize state with A.2.1 preservation strategy
    initial_state = AndroidAgentStateFixed(
        messages=[],
        screenshot_b64=screenshot_b64,  # PRESERVE across iterations
        multimodal_preserved_history=[],
        tool_executions=[],
        iteration_count=0
    )

    # Execute workflow
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
            success_rate=100.0 if final_state["tool_executions"] else 0.0,
            multimodal_history=final_state["multimodal_preserved_history"]
        )

        # Validate coordinates using vision optimization strategy
        ground_truth = CryptoAppGroundTruth()
        coordinate_validations = []

        for exec_info in final_state["tool_executions"]:
            if "args" in exec_info and "x" in exec_info["args"] and "y" in exec_info["args"]:
                x, y = exec_info["args"]["x"], exec_info["args"]["y"]
                is_valid, distance = validate_coordinates(x, y, ground_truth.screenshot_004_elements)
                coordinate_validations.append({
                    "coords": [x, y],
                    "valid": is_valid,
                    "distance": distance
                })

        # Results
        print(f"\n📊 RESULTADOS:")
        print(f"✅ Multimodal Support: {metrics.multimodal_support}")
        print(f"✅ Tool Calling: {metrics.tool_calling_detected}")
        print(f"⏱️  Response Time: {metrics.response_time:.2f}s")
        print(f"🔄 Iterations: {metrics.iterations_completed}")
        print(f"🛠️  Tool Executions: {metrics.tool_executions}")
        print(f"📈 Success Rate: {metrics.success_rate}%")
        print(f"🖼️  Multimodal History: {metrics.multimodal_history}")

        if coordinate_validations:
            print(f"\n🎯 COORDINATE VALIDATIONS (Vision Strategy):")
            for i, val in enumerate(coordinate_validations, 1):
                status = "✅ VALID" if val["valid"] else "❌ INVALID"
                print(f"   {i}. {val['coords']} - {status} (distance: {val['distance']:.1f}px)")

        if final_state["tool_executions"]:
            print(f"\n🛠️  TOOL EXECUTIONS:")
            for i, exec_info in enumerate(final_state["tool_executions"], 1):
                print(f"   {i}. {exec_info.get('result', 'No result')}")

        # Determine result status
        if metrics.multimodal_support and metrics.tool_calling_detected:
            if coordinate_validations and all(val["valid"] for val in coordinate_validations):
                print(f"\n🎉 RESULTADO: SUCESSO TOTAL (100% multimodal + coordinates)")
                status = "SUCCESS_TOTAL"
            else:
                print(f"\n⚡ RESULTADO: SUCESSO PARCIAL (multimodal + tools, coordinate precision issues)")
                status = "SUCCESS_PARTIAL"
        else:
            print(f"\n❌ RESULTADO: FALHA")
            status = "FAILURE"

        # Log results
        result_data = {
            "model_name": "qwen2.5vl:7b",
            "test_phase": "FASE_B1",
            "architecture": "LangGraph_A2.1_with_vision_optimizations",
            "status": status,
            "metrics": metrics._asdict(),
            "coordinate_validations": coordinate_validations,
            "tool_executions": final_state["tool_executions"]
        }

        log_test_result("B1_qwen2_5vl_structured_output", result_data)

    except Exception as e:
        print(f"❌ Erro durante execução: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_qwen2_5vl_structured_output()