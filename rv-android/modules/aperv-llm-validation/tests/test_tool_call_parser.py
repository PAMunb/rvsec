"""Tests for tool_call_parser — exercises all three parse paths and malformed JSON fixes."""

import json

import pytest

from aperv_llm_validation.pipeline.tool_call_parser import fix_malformed_json, parse


# ---------------------------------------------------------------------------
# Helpers to build OpenAI-format response dicts
# ---------------------------------------------------------------------------


def _response_with_content(content: str) -> dict:
    """Build an OpenAI response dict with text content only."""
    return {
        "choices": [
            {
                "message": {
                    "content": content,
                    "tool_calls": None,
                }
            }
        ]
    }


def _response_with_tool_call(name: str, arguments: dict) -> dict:
    """Build an OpenAI response dict with a native tool call."""
    return {
        "choices": [
            {
                "message": {
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": name,
                                "arguments": json.dumps(arguments),
                            }
                        }
                    ],
                }
            }
        ]
    }


def _response_with_reasoning(content: str, reasoning: str) -> dict:
    """Build a response dict with reasoning field."""
    return {
        "choices": [
            {
                "message": {
                    "content": content,
                    "reasoning": reasoning,
                    "tool_calls": None,
                }
            }
        ]
    }


# ---------------------------------------------------------------------------
# Test native tool_calls format
# ---------------------------------------------------------------------------


class TestNativeToolCalls:
    def test_click(self):
        response = _response_with_tool_call("click", {"x": 540, "y": 399})
        action = parse(response)
        assert action is not None
        assert action.action_type == "click"
        assert action.x == 540
        assert action.y == 399
        assert action.parse_level == "native"

    def test_long_click(self):
        response = _response_with_tool_call("long_click", {"x": 750, "y": 960})
        action = parse(response)
        assert action is not None
        assert action.action_type == "long_click"
        assert action.x == 750
        assert action.y == 960

    def test_type_text(self):
        response = _response_with_tool_call(
            "type_text", {"x": 300, "y": 500, "text": "hello"}
        )
        action = parse(response)
        assert action is not None
        assert action.action_type == "type_text"
        assert action.x == 300
        assert action.y == 500
        assert action.text == "hello"

    def test_back(self):
        response = _response_with_tool_call("back", {})
        action = parse(response)
        assert action is not None
        assert action.action_type == "back"
        assert action.x == 0
        assert action.y == 0

    def test_float_coordinates(self):
        """Native tool_calls may have float coordinates (e.g., 540.0)."""
        response = _response_with_tool_call("click", {"x": 540.0, "y": 399.0})
        action = parse(response)
        assert action is not None
        assert action.x == 540
        assert action.y == 399


# ---------------------------------------------------------------------------
# Test XML tag format
# ---------------------------------------------------------------------------


class TestXmlTagFormat:
    def test_tool_call_tag(self):
        content = '<tool_call>{"name": "click", "arguments": {"x": 540, "y": 399}}</tool_call>'
        action = parse(_response_with_content(content))
        assert action is not None
        assert action.action_type == "click"
        assert action.x == 540
        assert action.y == 399
        assert action.parse_level == "xml_tag"

    def test_function_call_tag(self):
        content = '<function_call>{"name": "long_click", "arguments": {"x": 200, "y": 300}}</function_call>'
        action = parse(_response_with_content(content))
        assert action is not None
        assert action.action_type == "long_click"
        assert action.x == 200
        assert action.y == 300

    def test_type_text_xml(self):
        content = '<tool_call>{"name": "type_text", "arguments": {"x": 300, "y": 500, "text": "hello"}}</tool_call>'
        action = parse(_response_with_content(content))
        assert action is not None
        assert action.action_type == "type_text"
        assert action.text == "hello"

    def test_back_xml(self):
        content = '<tool_call>{"name": "back", "arguments": {}}</tool_call>'
        action = parse(_response_with_content(content))
        assert action is not None
        assert action.action_type == "back"
        assert action.x == 0
        assert action.y == 0


# ---------------------------------------------------------------------------
# Test inline JSON format
# ---------------------------------------------------------------------------


class TestInlineJsonFormat:
    def test_json_in_text(self):
        content = (
            "I will click the login button. "
            '{"name": "click", "arguments": {"x": 100, "y": 200}}'
        )
        action = parse(_response_with_content(content))
        assert action is not None
        assert action.action_type == "click"
        assert action.x == 100
        assert action.y == 200
        assert action.parse_level == "inline_json"

    def test_json_surrounded_by_text(self):
        content = (
            'Let me tap the button.\n'
            '{"name": "click", "arguments": {"x": 500, "y": 600}}\n'
            'This should open the settings.'
        )
        action = parse(_response_with_content(content))
        assert action is not None
        assert action.action_type == "click"
        assert action.x == 500
        assert action.y == 600


# ---------------------------------------------------------------------------
# Test malformed JSON fixes
# ---------------------------------------------------------------------------


class TestMalformedJsonFixes:
    def test_missing_y_key(self):
        """'x': 352, 782 -> 'x': 352, 'y': 782"""
        malformed = '{"name": "click", "arguments": {"x": 352, 782}}'
        fixed = fix_malformed_json(malformed)
        assert '"y": 782' in fixed

    def test_missing_y_key_parse(self):
        content = '{"name": "click", "arguments": {"x": 540, 399}}'
        action = parse(_response_with_content(content))
        assert action is not None
        assert action.action_type == "click"
        assert action.x == 540
        assert action.y == 399

    def test_array_coords(self):
        """'x': [352, 782] -> 'x': 352, 'y': 782"""
        malformed = '{"name": "click", "arguments": {"x": [352, 782]}}'
        fixed = fix_malformed_json(malformed)
        assert '"x": 352' in fixed
        assert '"y": 782' in fixed

    def test_array_coords_parse(self):
        content = '{"name": "click", "arguments": {"x": [540, 399]}}'
        action = parse(_response_with_content(content))
        assert action is not None
        assert action.x == 540
        assert action.y == 399

    def test_missing_leading_zero(self):
        """: .91 -> : 0.91"""
        malformed = '{"confidence": .91}'
        fixed = fix_malformed_json(malformed)
        assert "0.91" in fixed

    def test_truncated_json(self):
        """Auto-close unbalanced braces."""
        truncated = '{"name": "click", "arguments": {"x": 100, "y": 200}'
        fixed = fix_malformed_json(truncated)
        # Should be valid JSON after fix
        obj = json.loads(fixed)
        assert obj["name"] == "click"

    def test_truncated_json_parse(self):
        content = '{"name": "click", "arguments": {"x": 100, "y": 200}'
        action = parse(_response_with_content(content))
        assert action is not None
        assert action.action_type == "click"
        assert action.x == 100
        assert action.y == 200


# ---------------------------------------------------------------------------
# Test reasoning extraction
# ---------------------------------------------------------------------------


class TestReasoningExtraction:
    def test_reasoning_field(self):
        content = '<tool_call>{"name": "click", "arguments": {"x": 500, "y": 600}}</tool_call>'
        reasoning_text = "I see a login button in the center of the screen."
        response = _response_with_reasoning(content, reasoning_text)
        action = parse(response)
        assert action is not None
        assert action.reasoning == reasoning_text

    def test_no_reasoning(self):
        content = '<tool_call>{"name": "click", "arguments": {"x": 500, "y": 600}}</tool_call>'
        action = parse(_response_with_content(content))
        assert action is not None
        assert action.reasoning is None


# ---------------------------------------------------------------------------
# Test no tool call found
# ---------------------------------------------------------------------------


class TestNoToolCall:
    def test_conversational_response(self):
        content = "This is just a plain text response with no tool calls at all."
        action = parse(_response_with_content(content))
        assert action is None

    def test_null_response(self):
        action = parse(None)
        assert action is None

    def test_empty_content(self):
        response = {"choices": [{"message": {"content": "", "tool_calls": None}}]}
        action = parse(response)
        assert action is None

    def test_malformed_response_structure(self):
        action = parse({"not_choices": []})
        assert action is None
