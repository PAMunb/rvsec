"""
Unit tests for the prompt_formatter service.
"""
import pytest
from unittest.mock import patch
from rv_agent.services import prompt_formatter


class TestPromptFormatter:
    """Test suite for prompt formatting functions."""

    # --- Tests for validate_coordinate_format ---

    @pytest.mark.parametrize("description, expected", [
        ("Button 'OK' at position (100, 200)", True),
        ("TextView 'Welcome' at position (50, 80)", True),
        ("Element at position (0, 0)", True),
        ("Button 'Cancel'", False),
        ("Image (100, 200)", False),
        ("at position (a, b)", False),
        ("at position (100,200)", False), # Missing space
    ])
    def test_validate_coordinate_format(self, description, expected):
        """Test the validation of the critical coordinate format."""
        assert prompt_formatter.validate_coordinate_format(description) == expected

    # --- Tests for create_react_prompt_with_coordinates ---

    def test_create_react_prompt_with_coordinates(self):
        """Test the creation of the main ReAct prompt."""
        ui_elements = "1. Button 'OK' at position (100, 200)\n2. Input field at position (100, 300)"
        context = "Previous action was 'CLICK'."
        
        prompt = prompt_formatter.create_react_prompt_with_coordinates(ui_elements, context)
        
        assert "{ui_elements}" not in prompt
        assert "{context}" not in prompt
        assert ui_elements in prompt
        assert context in prompt
        assert "GOAL: Systematically test Android applications" in prompt

    def test_create_react_prompt_without_context(self):
        """Test prompt creation when no extra context is provided."""
        ui_elements = "1. Button 'OK' at position (100, 200)"
        
        prompt = prompt_formatter.create_react_prompt_with_coordinates(ui_elements)
        
        assert ui_elements in prompt
        # Check that the context section is empty and doesn't add extra newlines
        assert "\n\n\nRESPONSE FORMAT" in prompt

    # --- Tests for format_ui_elements_for_llm ---

    @patch('rv_agent.services.prompt_formatter.extract_clickable_elements_with_coords')
    def test_format_ui_elements_for_llm_with_elements(self, mock_extract):
        """Test formatting when UI elements are found."""
        mock_extract.return_value = [
            {'description': "Button 'OK' at position (100, 200)"},
            {'description': "Input field 'Username' at position (100, 300)"},
        ]
        
        xml_content = "<dummy_xml />"
        formatted_string = prompt_formatter.format_ui_elements_for_llm(xml_content)
        
        mock_extract.assert_called_once_with(xml_content)
        assert formatted_string == "1. Button 'OK' at position (100, 200)\n2. Input field 'Username' at position (100, 300)"

    @patch('rv_agent.services.prompt_formatter.extract_clickable_elements_with_coords')
    def test_format_ui_elements_for_llm_no_elements(self, mock_extract):
        """Test formatting when no UI elements are found."""
        mock_extract.return_value = []
        
        xml_content = "<dummy_xml />"
        formatted_string = prompt_formatter.format_ui_elements_for_llm(xml_content)
        
        mock_extract.assert_called_once_with(xml_content)
        assert formatted_string == "No interactive elements available."

    # --- Tests for extract_coordinates_from_llm_response ---

    def test_extract_coordinates_from_llm_response_valid(self):
        """Test extraction from a valid JSON response."""
        response_text = '{"action_type": "click", "coordinates": [123, 456]}'
        success, coords, parsed = prompt_formatter.extract_coordinates_from_llm_response(response_text)
        assert success is True
        assert coords == (123, 456)
        assert parsed["action_type"] == "click"

    def test_extract_coordinates_from_llm_response_with_markdown(self):
        """Test extraction from a JSON response wrapped in markdown."""
        response_text = '```json\n{"coordinates": [10, 20]}\n```'
        success, coords, parsed = prompt_formatter.extract_coordinates_from_llm_response(response_text)
        assert success is True
        assert coords == (10, 20)

    def test_extract_coordinates_from_llm_response_invalid_json(self):
        """Test extraction from a malformed JSON string."""
        response_text = '{"coordinates": [10, 20]' # Missing closing brace
        success, coords, parsed = prompt_formatter.extract_coordinates_from_llm_response(response_text)
        assert success is False
        assert coords is None
        assert "error" in parsed
        assert parsed["raw_response"] == response_text

    @pytest.mark.parametrize("invalid_response", [
        '{"coordinates": "not a list"}',
        '{"coordinates": [10]}', # Not enough elements
        '{"coordinates": [10, "a"]}', # Wrong type
        '{"no_coordinates_key": "value"}',
        'just plain text',
    ])
    def test_extract_coordinates_from_llm_response_bad_structure(self, invalid_response):
        """Test various structurally invalid JSON responses."""
        success, coords, parsed = prompt_formatter.extract_coordinates_from_llm_response(invalid_response)
        assert success is False
        assert coords is None

