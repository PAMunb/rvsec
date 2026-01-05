"""
Tool Call Parser - Parses tool calls from LLM text responses.

Supports multiple output formats that vision models may produce:
1. JSON array: [{"name": "tool", "parameters": {...}}, ...]
2. Single JSON object: {"name": "tool", "parameters": {...}}
3. XML <tool_call> tags: <tool_call>{"name": ...}</tool_call>
4. Markdown code blocks: ```json {...} ```
5. Pythonic function calls: android_click(x=540, y=1054, ...)

Based on validation from rvsec-vision-llm benchmark (2,847 tests).
"""

import json
import re
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ParserResult:
    """Result of parsing tool calls from LLM response."""

    success: bool
    tool_calls: list[dict[str, Any]]
    strategy_used: str | None
    strategies_attempted: list[str] = field(default_factory=list)
    error_message: str | None = None
    json_fix_applied: bool = False
    raw_response_length: int = 0


class ParserStats:
    """Tracks parser statistics across multiple calls."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.total_calls = 0
        self.successful_parses = 0
        self.failed_parses = 0
        self.strategy_success_counts: dict[str, int] = {
            "native_tool_calls": 0,
            "xml_tool_call": 0,
            "json_array": 0,
            "json_object": 0,
            "markdown_code_block": 0,
            "pythonic_function": 0,
        }
        self.strategy_attempt_counts: dict[str, int] = {
            "xml_tool_call": 0,
            "json_array": 0,
            "json_object": 0,
            "markdown_code_block": 0,
            "pythonic_function": 0,
        }
        self.json_fixes_applied = 0
        self.failure_reasons: dict[str, int] = {}

    def record_success(self, strategy: str, json_fix_applied: bool = False):
        self.total_calls += 1
        self.successful_parses += 1
        if strategy in self.strategy_success_counts:
            self.strategy_success_counts[strategy] += 1
        if json_fix_applied:
            self.json_fixes_applied += 1

    def record_failure(self, reason: str = "unknown"):
        self.total_calls += 1
        self.failed_parses += 1
        self.failure_reasons[reason] = self.failure_reasons.get(reason, 0) + 1

    def record_attempt(self, strategy: str):
        if strategy in self.strategy_attempt_counts:
            self.strategy_attempt_counts[strategy] += 1

    def get_stats(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "successful_parses": self.successful_parses,
            "failed_parses": self.failed_parses,
            "success_rate": self.successful_parses / self.total_calls if self.total_calls > 0 else 0.0,
            "strategy_success_counts": dict(self.strategy_success_counts),
            "strategy_attempt_counts": dict(self.strategy_attempt_counts),
            "json_fixes_applied": self.json_fixes_applied,
            "failure_reasons": dict(self.failure_reasons),
        }


# Global instance for tracking
parser_stats = ParserStats()


def normalize_tool_args(args: dict[str, Any] | None) -> dict[str, Any]:
    """
    Normalize tool arguments by converting various coordinate formats.

    Handles multiple formats:
    - {"x": "681", "y": "777"} -> {"x": 681, "y": 777} (string to int)
    - {"x": 352.7, "y": 624.3} -> {"x": 352, "y": 624} (float to int)
    - {"x": [499, 510]} -> {"x": 499, "y": 510} (Qwen3-VL array in x)
    - {"coordinate": [464, 487]} -> {"x": 464, "y": 487} (Fara-7B format)
    - {"coordinates": [464, 487]} -> {"x": 464, "y": 487} (alternative)
    - {"bbox": [464, 487]} -> {"x": 464, "y": 487} (Fara-7B bbox format)
    - {"bbox_2d": [464, 487]} -> {"x": 464, "y": 487} (Fara-7B bbox_2d format)
    - {"bounds": [464, 487]} -> {"x": 464, "y": 487} (Fara-7B bounds format)
    - {"bndbox": [464, 487]} -> {"x": 464, "y": 487} (Fara-7B bndbox format)
    - {"center": [464, 487]} -> {"x": 464, "y": 487} (Fara-7B center format)
    - {"arguments": {"coordinate": [x, y]}} -> {"x": x, "y": y} (nested Fara-7B)

    Note: Qwen3-VL [0,1000) coords should be converted separately using
    denormalize_qwen_coords() after extraction.

    Args:
        args: Tool arguments dictionary (or None)

    Returns:
        Normalized arguments with integer x, y coordinates
    """
    if args is None:
        return {}

    normalized = {}

    # Handle nested 'arguments' dict (Fara-7B alternative format)
    if 'arguments' in args and isinstance(args['arguments'], dict):
        nested_args = args['arguments']
        nested_normalized = normalize_tool_args(nested_args)
        if 'x' in nested_normalized and 'y' in nested_normalized:
            normalized['x'] = nested_normalized['x']
            normalized['y'] = nested_normalized['y']
            if 'type' in nested_args:
                normalized['name'] = nested_args['type']
            for key, value in args.items():
                if key != 'arguments' and key not in normalized:
                    normalized[key] = value
            return normalized

    # Handle x as [x, y] array (Qwen3-VL format)
    if 'x' in args and isinstance(args['x'], list) and len(args['x']) >= 2:
        coord = args['x']
        normalized['x'] = int(coord[0]) if isinstance(coord[0], (int, float, str)) else coord[0]
        if 'y' not in args:
            normalized['y'] = int(coord[1]) if isinstance(coord[1], (int, float, str)) else coord[1]
        for key, value in args.items():
            if key != 'x':
                normalized[key] = value
        return normalized

    # Helper function to extract x,y from coordinate array
    def extract_coords_from_array(coord: list, key_to_skip: str) -> dict:
        result = {}
        if len(coord) >= 2:
            result['x'] = int(coord[0]) if isinstance(coord[0], (int, float, str)) else coord[0]
            result['y'] = int(coord[1]) if isinstance(coord[1], (int, float, str)) else coord[1]
        for k, v in args.items():
            if k != key_to_skip:
                result[k] = v
        return result

    # Handle various coordinate array formats (Fara-7B uses multiple)
    for coord_key in ('coordinate', 'coordinates', 'bbox', 'bbox_2d', 'bounds', 'bndbox', 'center'):
        if coord_key in args and isinstance(args[coord_key], list):
            coord = args[coord_key]
            if len(coord) >= 2:
                return extract_coords_from_array(coord, coord_key)

    # Standard processing for x, y format
    for key, value in args.items():
        if key in ('x', 'y'):
            if isinstance(value, str):
                try:
                    normalized[key] = int(value)
                except ValueError:
                    normalized[key] = value
            elif isinstance(value, float):
                normalized[key] = int(value)
            else:
                normalized[key] = value
        else:
            normalized[key] = value
    return normalized


def denormalize_qwen_coords(
    x: int | float,
    y: int | float,
    image_width: int = 1080,
    image_height: int = 1920,
) -> tuple[int, int]:
    """
    Convert Qwen3-VL [0, 1000) normalized coordinates to pixel coordinates.

    Qwen3-VL uses a normalized coordinate system where both x and y are in [0, 1000).
    See: https://github.com/QwenLM/Qwen3-VL/issues/1486

    Args:
        x: X coordinate in [0, 1000) range
        y: Y coordinate in [0, 1000) range
        image_width: Target image width
        image_height: Target image height

    Returns:
        Tuple of (pixel_x, pixel_y)
    """
    if 0 <= x < 1000 and 0 <= y < 1000:
        pixel_x = int((x / 1000) * image_width)
        pixel_y = int((y / 1000) * image_height)
        return pixel_x, pixel_y
    return int(x), int(y)


def parse_tool_calls_from_text(response_content: str, track_stats: bool = True) -> list[dict[str, Any]]:
    """
    Extract tool calls from LLM text response.

    Uses multiple pattern-matching strategies to handle different output formats.

    Args:
        response_content: Raw text response from LLM
        track_stats: Whether to track parser statistics (default True)

    Returns:
        List of tool call dicts with 'name' and 'args' keys
        Empty list if no tool calls found
    """
    if not response_content or not isinstance(response_content, str):
        logger.warning("Empty or invalid response content")
        if track_stats:
            parser_stats.record_failure("empty_response")
        return []

    logger.debug(f"Parsing tool calls from: {response_content[:200]}...")

    tool_calls = []
    json_fix_applied = False

    # Strategy 1: Extract JSON array [{"name": "...", "parameters": {...}}, ...]
    try:
        if track_stats:
            parser_stats.record_attempt("json_array")
        array_pattern = r'\[\s*\{[^\]]+\}\s*(?:,\s*\{[^\]]+\}\s*)*\]'
        array_match = re.search(array_pattern, response_content, re.DOTALL)

        if array_match:
            json_str = array_match.group()
            parsed = json.loads(json_str)

            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and 'name' in item:
                        args = item.get('parameters', item.get('arguments', item.get('args', {})))
                        tool_calls.append({
                            'name': item['name'],
                            'args': normalize_tool_args(args) if isinstance(args, dict) else {}
                        })

            if tool_calls:
                logger.info(f"Extracted {len(tool_calls)} tool calls (array format)")
                if track_stats:
                    parser_stats.record_success("json_array")
                return tool_calls

    except Exception as e:
        logger.debug(f"Array parsing failed: {e}")

    # Strategy 2: Extract single JSON object {"name": "...", "parameters": {...}}
    try:
        if track_stats:
            parser_stats.record_attempt("json_object")
        object_pattern = r'\{\s*"name"\s*:\s*"[^"]+"\s*,\s*"(?:parameters|arguments)"\s*:\s*\{[^}]*\}\s*\}'
        object_matches = re.finditer(object_pattern, response_content, re.DOTALL)

        for match in object_matches:
            json_str = match.group()
            parsed = json.loads(json_str)

            if isinstance(parsed, dict) and 'name' in parsed:
                args = parsed.get('parameters', parsed.get('arguments', parsed.get('args', {})))
                tool_calls.append({
                    'name': parsed['name'],
                    'args': normalize_tool_args(args) if isinstance(args, dict) else {}
                })

        if tool_calls:
            logger.info(f"Extracted {len(tool_calls)} tool calls (object format)")
            if track_stats:
                parser_stats.record_success("json_object")
            return tool_calls

    except Exception as e:
        logger.debug(f"Object parsing failed: {e}")

    # Strategy 3: Extract from XML <tool_call> tags (Qwen format)
    try:
        if track_stats:
            parser_stats.record_attempt("xml_tool_call")
        xml_pattern = r'<tool_call>\s*(.+?)\s*</tool_call>'
        xml_matches = re.finditer(xml_pattern, response_content, re.DOTALL)

        for match in xml_matches:
            json_str = match.group(1)
            fixed_json = _fix_malformed_json(json_str)
            parse_str = fixed_json if fixed_json else json_str
            if fixed_json:
                json_fix_applied = True

            try:
                parsed = json.loads(parse_str)
            except json.JSONDecodeError:
                if fixed_json:
                    try:
                        parsed = json.loads(json_str)
                    except json.JSONDecodeError:
                        continue
                else:
                    continue

            if isinstance(parsed, dict) and 'name' in parsed:
                args = parsed.get('arguments', parsed.get('parameters', parsed.get('args', {})))
                tool_calls.append({
                    'name': parsed['name'],
                    'args': normalize_tool_args(args) if isinstance(args, dict) else {}
                })

        if tool_calls:
            logger.info(f"Extracted {len(tool_calls)} tool calls (XML <tool_call> format)")
            if track_stats:
                parser_stats.record_success("xml_tool_call", json_fix_applied)
            return tool_calls

    except Exception as e:
        logger.debug(f"XML tool_call parsing failed: {e}")

    # Strategy 4: Extract from markdown code blocks
    try:
        if track_stats:
            parser_stats.record_attempt("markdown_code_block")
        code_block_pattern = r'```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```'
        code_matches = re.finditer(code_block_pattern, response_content, re.DOTALL)

        for match in code_matches:
            json_str = match.group(1)
            parsed = json.loads(json_str)

            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and 'name' in item:
                        args = item.get('parameters', item.get('arguments', item.get('args', {})))
                        tool_calls.append({
                            'name': item['name'],
                            'args': normalize_tool_args(args) if isinstance(args, dict) else {}
                        })
            elif isinstance(parsed, dict) and 'name' in parsed:
                args = parsed.get('parameters', parsed.get('arguments', parsed.get('args', {})))
                tool_calls.append({
                    'name': parsed['name'],
                    'args': normalize_tool_args(args) if isinstance(args, dict) else {}
                })
            # Gemma format: {"action": "android_click", "x": 480, "y": 1600}
            elif isinstance(parsed, dict) and 'action' in parsed:
                action = parsed.get('action', '')
                args = {k: v for k, v in parsed.items() if k != 'action'}
                tool_calls.append({
                    'name': action,
                    'args': normalize_tool_args(args) if args else {}
                })

        if tool_calls:
            logger.info(f"Extracted {len(tool_calls)} tool calls (code block format)")
            if track_stats:
                parser_stats.record_success("markdown_code_block")
            return tool_calls

    except Exception as e:
        logger.debug(f"Code block parsing failed: {e}")

    # Strategy 5: Extract pythonic function calls (Gemma format)
    try:
        if track_stats:
            parser_stats.record_attempt("pythonic_function")
        func_pattern = r'(android_click|android_type_text|android_long_click|android_swipe|android_back|android_home|android_scroll)\s*\(\s*([^)]+)\s*\)'
        func_matches = re.finditer(func_pattern, response_content, re.DOTALL)

        for match in func_matches:
            func_name = match.group(1)
            args_str = match.group(2)

            args = {}
            arg_pattern = r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^,\s)]+))'
            for arg_match in re.finditer(arg_pattern, args_str):
                key = arg_match.group(1)
                value = arg_match.group(2) or arg_match.group(3) or arg_match.group(4)

                if value:
                    try:
                        if '.' in value:
                            args[key] = float(value)
                        else:
                            args[key] = int(value)
                    except ValueError:
                        args[key] = value

            if args:
                tool_calls.append({
                    'name': func_name,
                    'args': normalize_tool_args(args)
                })

        if tool_calls:
            logger.info(f"Extracted {len(tool_calls)} tool calls (pythonic function format)")
            if track_stats:
                parser_stats.record_success("pythonic_function")
            return tool_calls

    except Exception as e:
        logger.debug(f"Pythonic function parsing failed: {e}")

    # All strategies failed
    logger.warning("No tool calls found in response")
    logger.debug(f"Full response content:\n{response_content}")
    if track_stats:
        if len(response_content) < 10:
            parser_stats.record_failure("response_too_short")
        elif "I cannot" in response_content or "I'm sorry" in response_content:
            parser_stats.record_failure("refusal")
        elif "android_click" not in response_content.lower() and "click" not in response_content.lower():
            parser_stats.record_failure("no_tool_mention")
        else:
            parser_stats.record_failure("parse_failed")

    return []


def parse_tool_calls_with_strategy(
    response_content: str,
    track_stats: bool = True
) -> tuple[list[dict[str, Any]], str]:
    """
    Extract tool calls from LLM text response, returning the strategy used.

    Args:
        response_content: Raw text response from LLM
        track_stats: Whether to track parser statistics (default True)

    Returns:
        Tuple of (list of tool call dicts, strategy name)
        Strategy names: "native", "xml", "json_array", "json_object", "markdown", "pythonic", "none"
    """
    if not response_content or not isinstance(response_content, str):
        logger.warning("Empty or invalid response content")
        if track_stats:
            parser_stats.record_failure("empty_response")
        return [], "none"

    logger.debug(f"Parsing tool calls from: {response_content[:200]}...")

    tool_calls = []

    # Strategy 1: Extract from XML <tool_call> tags (Qwen format) - most common
    try:
        if track_stats:
            parser_stats.record_attempt("xml_tool_call")
        xml_pattern = r'<tool_call>\s*(.+?)\s*</tool_call>'
        xml_matches = re.finditer(xml_pattern, response_content, re.DOTALL)

        for match in xml_matches:
            json_str = match.group(1)
            fixed_json = _fix_malformed_json(json_str)
            parse_str = fixed_json if fixed_json else json_str

            try:
                parsed = json.loads(parse_str)
            except json.JSONDecodeError:
                if fixed_json:
                    try:
                        parsed = json.loads(json_str)
                    except json.JSONDecodeError:
                        continue
                else:
                    continue

            if isinstance(parsed, dict) and 'name' in parsed:
                args = parsed.get('arguments', parsed.get('parameters', parsed.get('args', {})))
                tool_calls.append({
                    'name': parsed['name'],
                    'args': normalize_tool_args(args) if isinstance(args, dict) else {}
                })

        if tool_calls:
            logger.info(f"Extracted {len(tool_calls)} tool calls (XML format)")
            if track_stats:
                parser_stats.record_success("xml_tool_call")
            return tool_calls, "xml"

    except Exception as e:
        logger.debug(f"XML parsing failed: {e}")

    # Strategy 2: Extract JSON array
    try:
        if track_stats:
            parser_stats.record_attempt("json_array")
        array_pattern = r'\[\s*\{[^\]]+\}\s*(?:,\s*\{[^\]]+\}\s*)*\]'
        array_match = re.search(array_pattern, response_content, re.DOTALL)

        if array_match:
            parsed = json.loads(array_match.group())
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and 'name' in item:
                        args = item.get('parameters', item.get('arguments', item.get('args', {})))
                        tool_calls.append({
                            'name': item['name'],
                            'args': normalize_tool_args(args) if isinstance(args, dict) else {}
                        })

            if tool_calls:
                logger.info(f"Extracted {len(tool_calls)} tool calls (JSON array)")
                if track_stats:
                    parser_stats.record_success("json_array")
                return tool_calls, "json_array"

    except Exception as e:
        logger.debug(f"JSON array parsing failed: {e}")

    # Strategy 3: Extract single JSON object
    try:
        if track_stats:
            parser_stats.record_attempt("json_object")
        object_pattern = r'\{\s*"name"\s*:\s*"[^"]+"\s*,\s*"(?:parameters|arguments)"\s*:\s*\{[^}]*\}\s*\}'
        for match in re.finditer(object_pattern, response_content, re.DOTALL):
            parsed = json.loads(match.group())
            if isinstance(parsed, dict) and 'name' in parsed:
                args = parsed.get('parameters', parsed.get('arguments', parsed.get('args', {})))
                tool_calls.append({
                    'name': parsed['name'],
                    'args': normalize_tool_args(args) if isinstance(args, dict) else {}
                })

        if tool_calls:
            logger.info(f"Extracted {len(tool_calls)} tool calls (JSON object)")
            if track_stats:
                parser_stats.record_success("json_object")
            return tool_calls, "json_object"

    except Exception as e:
        logger.debug(f"JSON object parsing failed: {e}")

    # Strategy 4: Markdown code blocks with Gemma format support
    try:
        if track_stats:
            parser_stats.record_attempt("markdown_code_block")
        code_block_pattern = r'```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```'
        for match in re.finditer(code_block_pattern, response_content, re.DOTALL):
            parsed = json.loads(match.group(1))

            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and 'name' in item:
                        args = item.get('parameters', item.get('arguments', item.get('args', {})))
                        tool_calls.append({
                            'name': item['name'],
                            'args': normalize_tool_args(args) if isinstance(args, dict) else {}
                        })
            elif isinstance(parsed, dict) and 'name' in parsed:
                args = parsed.get('parameters', parsed.get('arguments', parsed.get('args', {})))
                tool_calls.append({
                    'name': parsed['name'],
                    'args': normalize_tool_args(args) if isinstance(args, dict) else {}
                })
            elif isinstance(parsed, dict) and 'action' in parsed:
                action = parsed.get('action', '')
                args = {k: v for k, v in parsed.items() if k != 'action'}
                tool_calls.append({
                    'name': action,
                    'args': normalize_tool_args(args) if args else {}
                })
                if tool_calls:
                    if track_stats:
                        parser_stats.record_success("markdown_code_block")
                    return tool_calls, "gemma"

        if tool_calls:
            logger.info(f"Extracted {len(tool_calls)} tool calls (markdown)")
            if track_stats:
                parser_stats.record_success("markdown_code_block")
            return tool_calls, "markdown"

    except Exception as e:
        logger.debug(f"Markdown parsing failed: {e}")

    # Strategy 5: Pythonic function calls
    try:
        if track_stats:
            parser_stats.record_attempt("pythonic_function")
        func_pattern = r'(android_click|android_type_text|android_long_click|android_swipe|android_back|android_home)\s*\(\s*([^)]+)\s*\)'
        for match in re.finditer(func_pattern, response_content, re.DOTALL):
            func_name = match.group(1)
            args_str = match.group(2)
            args = {}
            arg_pattern = r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^,\s)]+))'
            for arg_match in re.finditer(arg_pattern, args_str):
                key = arg_match.group(1)
                value = arg_match.group(2) or arg_match.group(3) or arg_match.group(4)
                if value:
                    try:
                        args[key] = float(value) if '.' in value else int(value)
                    except ValueError:
                        args[key] = value

            if args:
                tool_calls.append({
                    'name': func_name,
                    'args': normalize_tool_args(args)
                })

        if tool_calls:
            logger.info(f"Extracted {len(tool_calls)} tool calls (pythonic)")
            if track_stats:
                parser_stats.record_success("pythonic_function")
            return tool_calls, "pythonic"

    except Exception as e:
        logger.debug(f"Pythonic parsing failed: {e}")

    # All strategies failed
    logger.warning("No tool calls found in response")
    if track_stats:
        if len(response_content) < 10:
            parser_stats.record_failure("response_too_short")
        elif "I cannot" in response_content or "I'm sorry" in response_content:
            parser_stats.record_failure("refusal")
        elif "android_click" not in response_content.lower() and "click" not in response_content.lower():
            parser_stats.record_failure("no_tool_mention")
        else:
            parser_stats.record_failure("parse_failed")

    return [], "none"


def _fix_malformed_json(s: str) -> str | None:
    """
    Try to fix common JSON malformations from model output.

    Common issues:
    - "x": 352, 782 should be "x": 352, "y": 782
    - "x": [352, 782] should be "x": 352, "y": 782
    - "x": [499", "499"] malformed array with quotes (vLLM)
    - "x": = 100 equals sign instead of colon (vLLM)
    - "x": .91 should be "x": 0.91 (Qwen3-VL normalized coords)
    - "x":": 541 double colon (Qwen3-VL malformation)
    - "y": 473" missing leading quote on value
    - Truncated JSON missing closing braces
    """
    original = s

    # Pattern 0: Fix missing leading zero in floats: .91 -> 0.91 (Qwen3-VL)
    s = re.sub(
        r':\s*\.(\d+)',
        r': 0.\1',
        s
    )

    # Pattern 0b: Fix double colon: "x":": 541 -> "x": 541
    s = re.sub(
        r'"([xy])":\s*"?:\s*(\d+)',
        r'"\1": \2',
        s
    )

    # Pattern 0c: Fix numeric value with trailing quote only: "y": 473" -> "y": 473
    s = re.sub(
        r'"([xy])":\s*(\d+)"(\s*[,}])',
        r'"\1": \2\3',
        s
    )

    # Pattern 0d: "x": 867 335 -> "x": 867 (MiniCPM-V outputs two numbers with space)
    s = re.sub(
        r'"([xy])":\s*(\d+)\s+\d+',
        r'"\1": \2',
        s
    )

    # Pattern 1: "x": 352, 782 -> "x": 352, "y": 782
    s = re.sub(
        r'"x":\s*(\d+),\s*(\d+)',
        r'"x": \1, "y": \2',
        s
    )

    # Pattern 2: "x": [352, 782] -> "x": 352, "y": 782
    s = re.sub(
        r'"x":\s*\[\s*(\d+)\s*,\s*(\d+)\s*\]',
        r'"x": \1, "y": \2',
        s
    )

    # Pattern 3: "x": [499", "499"] -> "x": 499, "y": 499
    s = re.sub(
        r'"x":\s*\[\s*(\d+)"?,\s*"?(\d+)"?\s*\]',
        r'"x": \1, "y": \2',
        s
    )

    # Pattern 4: "x": = 100 -> "x": 100
    s = re.sub(
        r'"([xy])":\s*=\s*(\d+)',
        r'"\1": \2',
        s
    )

    # Pattern 5: Fix truncated JSON - add missing closing braces
    open_braces = s.count('{')
    close_braces = s.count('}')
    if open_braces > close_braces:
        s = s + '}' * (open_braces - close_braces)

    return s if s != original else None


# Backwards compatibility: keep old function name
def execute_tool_call(
    tool_call: dict[str, Any],
    device,
    converter
) -> dict[str, Any]:
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

    logger.info(f"Executing: {tool_name}({tool_args})")

    try:
        if tool_name == 'android_click':
            return _execute_click(tool_args, device, converter)

        elif tool_name == 'android_type_text':
            return _execute_type_text(tool_args, device, converter)

        elif tool_name == 'android_long_click':
            return _execute_long_click(tool_args, device, converter)

        elif tool_name == 'android_swipe':
            return _execute_swipe(tool_args, device)

        elif tool_name == 'android_scroll':
            return _execute_scroll(tool_args, device)

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


def _execute_click(args: dict, device, converter) -> dict[str, Any]:
    """Execute android_click tool."""
    element_description = args.get('element_description', 'unknown')
    x = args.get('x', 0)
    y = args.get('y', 0)

    try:
        converter.validate_optimized_coords(x, y)
    except ValueError as e:
        logger.warning(f"Coordinate validation failed: {e}")
        return {
            "success": False,
            "llm_coords": (x, y),
            "description": element_description,
            "action_type": "click",
            "error": f"Invalid coordinates: {e}"
        }

    device_x, device_y = converter.optimized_to_device(x, y)
    success = device.click(device_x, device_y)

    logger.info(
        f"Click: {element_description} "
        f"opt({x},{y}) -> dev({device_x},{device_y}) - "
        f"{'success' if success else 'failed'}"
    )

    return {
        "success": success,
        "llm_coords": (x, y),
        "device_coords": (device_x, device_y),
        "description": element_description,
        "action_type": "click"
    }


def _execute_type_text(args: dict, device, converter) -> dict[str, Any]:
    """Execute android_type_text tool."""
    element_description = args.get('element_description', 'unknown')
    x = args.get('x', 0)
    y = args.get('y', 0)
    text = args.get('text', '')

    try:
        converter.validate_optimized_coords(x, y)
    except ValueError as e:
        logger.warning(f"Coordinate validation failed: {e}")
        return {
            "success": False,
            "llm_coords": (x, y),
            "description": element_description,
            "action_type": "set_text",
            "text": text,
            "error": f"Invalid coordinates: {e}"
        }

    device_x, device_y = converter.optimized_to_device(x, y)
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

    input_success = device.input_text(text)

    logger.info(
        f"Text input: '{text}' into {element_description} "
        f"opt({x},{y}) -> dev({device_x},{device_y}) - "
        f"{'success' if input_success else 'failed'}"
    )

    return {
        "success": input_success,
        "llm_coords": (x, y),
        "device_coords": (device_x, device_y),
        "description": element_description,
        "action_type": "set_text",
        "text": text
    }


def _execute_long_click(args: dict, device, converter) -> dict[str, Any]:
    """Execute android_long_click tool."""
    element_description = args.get('element_description', 'unknown')
    x = args.get('x', 0)
    y = args.get('y', 0)

    try:
        converter.validate_optimized_coords(x, y)
    except ValueError as e:
        logger.warning(f"Coordinate validation failed: {e}")
        return {
            "success": False,
            "llm_coords": (x, y),
            "description": element_description,
            "action_type": "long_click",
            "error": f"Invalid coordinates: {e}"
        }

    device_x, device_y = converter.optimized_to_device(x, y)
    success = device.long_click(device_x, device_y)

    logger.info(
        f"Long click: {element_description} "
        f"opt({x},{y}) -> dev({device_x},{device_y}) - "
        f"{'success' if success else 'failed'}"
    )

    return {
        "success": success,
        "llm_coords": (x, y),
        "device_coords": (device_x, device_y),
        "description": element_description,
        "action_type": "long_click"
    }


def _execute_swipe(args: dict, device) -> dict[str, Any]:
    """Execute android_swipe tool."""
    direction = args.get('direction', 'up')
    distance = args.get('distance', 'medium')

    valid_directions = ['up', 'down', 'left', 'right']
    if direction not in valid_directions:
        error_msg = f"Invalid direction '{direction}'. Use: {', '.join(valid_directions)}"
        logger.warning(error_msg)
        return {
            "success": False,
            "action_type": "swipe",
            "direction": direction,
            "distance": distance,
            "error": error_msg
        }

    valid_distances = ['short', 'medium', 'long']
    if distance not in valid_distances:
        error_msg = f"Invalid distance '{distance}'. Use: {', '.join(valid_distances)}"
        logger.warning(error_msg)
        return {
            "success": False,
            "action_type": "swipe",
            "direction": direction,
            "distance": distance,
            "error": error_msg
        }

    success = device.swipe(direction, distance)

    logger.info(
        f"Swipe: {direction} ({distance}) - "
        f"{'success' if success else 'failed'}"
    )

    return {
        "success": success,
        "action_type": "swipe",
        "direction": direction,
        "distance": distance
    }


def _execute_scroll(args: dict, device) -> dict[str, Any]:
    """Execute android_scroll tool."""
    direction = args.get('direction', 'down')
    success = device.scroll(direction)

    logger.info(f"Scroll: {direction} - {'success' if success else 'failed'}")

    return {
        "success": success,
        "action_type": "scroll",
        "direction": direction
    }


def _execute_back(device) -> dict[str, Any]:
    """Execute android_back tool."""
    success = device.back()
    logger.info(f"Back button - {'success' if success else 'failed'}")
    return {"success": success, "action_type": "back"}


def _execute_home(device) -> dict[str, Any]:
    """Execute android_home tool."""
    success = device.home()
    logger.info(f"Home button - {'success' if success else 'failed'}")
    return {"success": success, "action_type": "home"}
