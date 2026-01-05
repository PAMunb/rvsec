"""
JSON Tool Call Parser - Parses tool calls from LLM text responses.

When qwen-vision-tools-v1 receives images, it returns tool calls as JSON text
instead of using LangChain's tool_calls mechanism. This parser extracts and
executes those tool calls.

The model returns either:
1. List format: [{"name": "tool", "parameters": {...}}, ...]
2. Single format: {"name": "tool", "parameters": {...}}
3. Inline JSON with function calls
"""

import json
import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def _normalize_tool_args(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize tool arguments by converting string numbers to integers.

    LLM sometimes generates {"x": "681", "y": "777"} instead of {"x": 681, "y": 777}.
    This function converts string coordinates to integers.

    Args:
        args: Tool arguments dictionary

    Returns:
        Normalized arguments with integer coordinates
    """
    normalized = {}
    for key, value in args.items():
        # Convert string numbers to integers for coordinate fields
        if key in ('x', 'y') and isinstance(value, str):
            try:
                normalized[key] = int(value)
            except ValueError:
                normalized[key] = value  # Keep as-is if conversion fails
        else:
            normalized[key] = value
    return normalized


def parse_tool_calls_from_text(response_content: str) -> List[Dict[str, Any]]:
    """
    Extract tool calls from LLM text response.

    The qwen-vision-tools-v1 model returns tool calls as JSON text when
    processing images. This function extracts those calls using multiple
    pattern-matching strategies.

    Args:
        response_content: Raw text response from LLM

    Returns:
        List of tool call dicts with 'name' and 'args' keys
        Empty list if no tool calls found
    """
    if not response_content or not isinstance(response_content, str):
        logger.warning("Empty or invalid response content")
        return []

    logger.debug(f"Parsing tool calls from: {response_content[:200]}...")

    tool_calls = []

    # Strategy 1: Extract JSON array [{"name": "...", "parameters": {...}}, ...]
    try:
        array_pattern = r'\[\s*\{[^\]]+\}\s*(?:,\s*\{[^\]]+\}\s*)*\]'
        array_match = re.search(array_pattern, response_content, re.DOTALL)

        if array_match:
            json_str = array_match.group()
            parsed = json.loads(json_str)

            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and 'name' in item:
                        tool_calls.append({
                            'name': item['name'],
                            'args': item.get('parameters', item.get('args', {}))
                        })

            if tool_calls:
                logger.info(f"✅ Extracted {len(tool_calls)} tool calls (array format)")
                return tool_calls

    except Exception as e:
        logger.debug(f"Array parsing failed: {e}")

    # Strategy 2: Extract single JSON object {"name": "...", "parameters": {...}}
    try:
        object_pattern = r'\{\s*"name"\s*:\s*"[^"]+"\s*,\s*"parameters"\s*:\s*\{[^}]+\}\s*\}'
        object_matches = re.finditer(object_pattern, response_content, re.DOTALL)

        for match in object_matches:
            json_str = match.group()
            parsed = json.loads(json_str)

            if isinstance(parsed, dict) and 'name' in parsed:
                tool_calls.append({
                    'name': parsed['name'],
                    'args': parsed.get('parameters', parsed.get('args', {}))
                })

        if tool_calls:
            logger.info(f"✅ Extracted {len(tool_calls)} tool calls (object format)")
            return tool_calls

    except Exception as e:
        logger.debug(f"Object parsing failed: {e}")

    # Strategy 3: Extract from XML <tool_call> tags (Qwen2.5-VL format)
    try:
        xml_pattern = r'<tool_call>\s*(.+?)\s*</tool_call>'
        xml_matches = re.finditer(xml_pattern, response_content, re.DOTALL)

        for match in xml_matches:
            json_str = match.group(1)
            parsed = json.loads(json_str)

            if isinstance(parsed, dict) and 'name' in parsed:
                args = parsed.get('arguments', parsed.get('parameters', parsed.get('args', {})))
                tool_calls.append({
                    'name': parsed['name'],
                    'args': _normalize_tool_args(args)
                })

        if tool_calls:
            logger.info(f"✅ Extracted {len(tool_calls)} tool calls (XML <tool_call> format)")
            return tool_calls

    except Exception as e:
        logger.debug(f"XML tool_call parsing failed: {e}")

    # Strategy 4: Extract from markdown code blocks
    try:
        code_block_pattern = r'```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```'
        code_matches = re.finditer(code_block_pattern, response_content, re.DOTALL)

        for match in code_matches:
            json_str = match.group(1)
            parsed = json.loads(json_str)

            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and 'name' in item:
                        tool_calls.append({
                            'name': item['name'],
                            'args': item.get('parameters', item.get('args', {}))
                        })
            elif isinstance(parsed, dict) and 'name' in parsed:
                tool_calls.append({
                    'name': parsed['name'],
                    'args': parsed.get('parameters', parsed.get('args', {}))
                })

        if tool_calls:
            logger.info(f"✅ Extracted {len(tool_calls)} tool calls (code block format)")
            return tool_calls

    except Exception as e:
        logger.debug(f"Code block parsing failed: {e}")

    logger.warning("❌ No tool calls found in response")
    logger.debug(f"Full response content:\n{response_content}")

    return []


def execute_tool_call(
    tool_call: Dict[str, Any],
    device,
    converter
) -> Dict[str, Any]:
    """
    Execute a single parsed tool call.

    Args:
        tool_call: Dict with 'name' and 'args' keys
        device: DeviceInterface instance
        converter: CoordinateConverter instance

    Returns:
        Execution result dict with 'success', 'action_type', etc.
    """
    tool_name = tool_call.get('name', '')
    tool_args = tool_call.get('args', {})

    logger.info(f"🔧 Executing: {tool_name}({tool_args})")

    try:
        if tool_name == 'android_click':
            return _execute_click(tool_args, device, converter)

        elif tool_name == 'android_type_text':
            return _execute_type_text(tool_args, device, converter)

        elif tool_name == 'android_long_click':
            return _execute_long_click(tool_args, device, converter)

        elif tool_name == 'android_swipe':
            return _execute_swipe(tool_args, device)

        elif tool_name == 'android_back':
            return _execute_back(device)

        elif tool_name == 'android_home':
            return _execute_home(device)

        else:
            logger.warning(f"Unknown tool: {tool_name}")
            return {
                "success": False,
                "action_type": "unknown",
                "error": f"Unknown tool: {tool_name}"
            }

    except Exception as e:
        logger.error(f"Tool execution failed: {e}", exc_info=True)
        return {
            "success": False,
            "action_type": tool_name.replace('android_', ''),
            "error": str(e)
        }


def _execute_click(args: Dict, device, converter) -> Dict[str, Any]:
    """Execute android_click tool."""
    element_description = args.get('element_description', 'unknown')
    x = args.get('x', 0)
    y = args.get('y', 0)

    # Validate coordinates
    try:
        converter.validate_optimized_coords(x, y)
    except ValueError as e:
        logger.warning(f"❌ Coordinate validation failed: {e}")
        return {
            "success": False,
            "llm_coords": (x, y),
            "description": element_description,
            "action_type": "click",
            "error": f"Invalid coordinates: {e}"
        }

    # Convert to device coordinates
    device_x, device_y = converter.optimized_to_device(x, y)

    # Execute click
    success = device.click(device_x, device_y)

    logger.info(
        f"✅ Click: {element_description} "
        f"opt({x},{y}) → dev({device_x},{device_y}) - "
        f"{'success' if success else 'failed'}"
    )

    return {
        "success": success,
        "llm_coords": (x, y),
        "description": element_description,
        "action_type": "click"
    }


def _execute_type_text(args: Dict, device, converter) -> Dict[str, Any]:
    """Execute android_type_text tool."""
    element_description = args.get('element_description', 'unknown')
    x = args.get('x', 0)
    y = args.get('y', 0)
    text = args.get('text', '')

    # Validate coordinates
    try:
        converter.validate_optimized_coords(x, y)
    except ValueError as e:
        logger.warning(f"❌ Coordinate validation failed: {e}")
        return {
            "success": False,
            "llm_coords": (x, y),
            "description": element_description,
            "action_type": "set_text",
            "text": text,
            "error": f"Invalid coordinates: {e}"
        }

    # Convert to device coordinates
    device_x, device_y = converter.optimized_to_device(x, y)

    # Click to focus
    click_success = device.click(device_x, device_y)
    if not click_success:
        logger.warning(f"Failed to click text field at dev({device_x},{device_y})")
        return {
            "success": False,
            "llm_coords": (x, y),
            "description": element_description,
            "action_type": "set_text",
            "text": text,
            "error": "Click failed"
        }

    # Input text
    input_success = device.input_text(text)

    logger.info(
        f"✅ Text input: '{text}' into {element_description} "
        f"opt({x},{y}) → dev({device_x},{device_y}) - "
        f"{'success' if input_success else 'failed'}"
    )

    return {
        "success": input_success,
        "llm_coords": (x, y),
        "description": element_description,
        "action_type": "set_text",
        "text": text
    }


def _execute_long_click(args: Dict, device, converter) -> Dict[str, Any]:
    """Execute android_long_click tool."""
    element_description = args.get('element_description', 'unknown')
    x = args.get('x', 0)
    y = args.get('y', 0)

    # Validate coordinates
    try:
        converter.validate_optimized_coords(x, y)
    except ValueError as e:
        logger.warning(f"❌ Coordinate validation failed: {e}")
        return {
            "success": False,
            "llm_coords": (x, y),
            "description": element_description,
            "action_type": "long_click",
            "error": f"Invalid coordinates: {e}"
        }

    # Convert to device coordinates
    device_x, device_y = converter.optimized_to_device(x, y)

    # Execute long click
    success = device.long_click(device_x, device_y)

    logger.info(
        f"✅ Long click: {element_description} "
        f"opt({x},{y}) → dev({device_x},{device_y}) - "
        f"{'success' if success else 'failed'}"
    )

    return {
        "success": success,
        "llm_coords": (x, y),
        "description": element_description,
        "action_type": "long_click"
    }


def _execute_swipe(args: Dict, device) -> Dict[str, Any]:
    """Execute android_swipe tool."""
    direction = args.get('direction', 'up')
    distance = args.get('distance', 'medium')

    # Validate direction
    valid_directions = ['up', 'down', 'left', 'right']
    if direction not in valid_directions:
        error_msg = f"Invalid direction '{direction}'. Use: {', '.join(valid_directions)}"
        logger.warning(f"❌ {error_msg}")
        return {
            "success": False,
            "action_type": "swipe",
            "direction": direction,
            "distance": distance,
            "error": error_msg
        }

    # Validate distance
    valid_distances = ['short', 'medium', 'long']
    if distance not in valid_distances:
        error_msg = f"Invalid distance '{distance}'. Use: {', '.join(valid_distances)}"
        logger.warning(f"❌ {error_msg}")
        return {
            "success": False,
            "action_type": "swipe",
            "direction": direction,
            "distance": distance,
            "error": error_msg
        }

    # Execute swipe
    success = device.swipe(direction, distance)

    logger.info(
        f"↔️ Swipe: {direction} ({distance}) - "
        f"{'success' if success else 'failed'}"
    )

    return {
        "success": success,
        "action_type": "swipe",
        "direction": direction,
        "distance": distance
    }


def _execute_back(device) -> Dict[str, Any]:
    """Execute android_back tool."""
    success = device.back()

    logger.info(f"🏠 Back button - {'success' if success else 'failed'}")

    return {
        "success": success,
        "action_type": "back"
    }


def _execute_home(device) -> Dict[str, Any]:
    """Execute android_home tool."""
    success = device.home()

    logger.info(f"🏠 Home button - {'success' if success else 'failed'}")

    return {
        "success": success,
        "action_type": "home"
    }
