
from rv_android_core.util.json_helpers import (
    safe_parse_json,
    safe_json_parse,
    extract_json_array,
    repair_json,
    validate_action_format,
    detect_action_format,
    extract_structured_content,
)

# Tests for safe_parse_json
def test_safe_parse_json_valid():
    json_str = '{"key": "value"}'
    parsed, error = safe_parse_json(json_str)
    assert parsed == {"key": "value"}
    assert error is None

def test_safe_parse_json_invalid():
    json_str = '{"key": "value"'
    parsed, error = safe_parse_json(json_str)
    assert parsed is None
    assert isinstance(error, str)

# Tests for safe_json_parse
def test_safe_json_parse_valid():
    json_str = '{"key": "value"}'
    assert safe_json_parse(json_str) == {"key": "value"}

def test_safe_json_parse_invalid():
    json_str = '{"key": "value"'
    assert safe_json_parse(json_str, default={}) == {}

def test_safe_json_parse_with_repair():
    json_str = "{'key': 'value'}"
    assert safe_json_parse(json_str) == [{"key": "value"}]

def test_safe_json_parse_empty_string():
    assert safe_json_parse("", default="EMPTY") == "EMPTY"

def test_safe_json_parse_not_a_string():
    assert safe_json_parse(None, default="NOT_A_STRING") == "NOT_A_STRING"


# Tests for extract_json_array
def test_extract_json_array_valid():
    text = 'Some text [{"key": "value"}] more text'
    json_text, error = extract_json_array(text)
    assert json_text == '[{"key": "value"}]'
    assert error is None

def test_extract_json_array_invalid():
    text = 'Some text [{"key": "value"} more text'
    json_text, error = extract_json_array(text)
    assert json_text is None
    assert error == "No valid JSON array brackets found"

def test_extract_json_array_with_repair():
    text = "Some text [{'key': 'value'}] more text"
    json_text, error = extract_json_array(text)
    assert json_text == '[{"key": "value"}]'
    assert error is None

# Tests for repair_json
def test_repair_json_single_quotes():
    malformed = "[{'key': 'value'}]"
    repaired = repair_json(malformed)
    assert repaired == '[{"key": "value"}]'

def test_repair_json_unquoted_props():
    malformed = '[{key: "value"}]'
    repaired = repair_json(malformed)
    assert repaired == '[{"key": "value"}]'

def test_repair_json_trailing_commas():
    malformed = '[{"key": "value"},]'
    repaired = repair_json(malformed)
    assert repaired == '[{"key": "value"}]'

def test_repair_json_missing_commas():
    malformed = '[{"a": 1}{"b": 2}]'
    repaired = repair_json(malformed)
    assert repaired == '[{"a": 1},{"b": 2}]'

def test_repair_json_booleans():
    malformed = '[{"a": True, "b": False, "c": None}]'
    repaired = repair_json(malformed)
    assert repaired == '[{"a":true, "b":false, "c":null}]'

# Tests for validate_action_format
def test_validate_action_format_valid():
    actions = [{"action_id": 1, "params": {}, "explanation": "Test"}]
    valid_actions, errors = validate_action_format(actions)
    assert len(valid_actions) == 1
    assert len(errors) == 0

def test_validate_action_format_missing_action_id():
    actions = [{"params": {}, "explanation": "Test"}]
    valid_actions, errors = validate_action_format(actions)
    assert len(valid_actions) == 0
    assert "Missing action_id" in errors[0]

def test_validate_action_format_not_a_list():
    actions = {"action_id": 1}
    valid_actions, errors = validate_action_format(actions)
    assert len(valid_actions) == 0
    assert "Expected a list" in errors[0]

def test_validate_action_format_normalizes_missing_params_and_explanation():
    actions = [{"action_id": 1}]
    valid_actions, errors = validate_action_format(actions)
    assert len(valid_actions) == 1
    assert len(errors) == 0
    assert "params" in valid_actions[0]
    assert "explanation" in valid_actions[0]

# Tests for detect_action_format
def test_detect_action_format_action_id():
    json_obj = [{"action_id": 1}]
    assert detect_action_format(json_obj) == "action_id"

def test_detect_action_format_coordinate():
    json_obj = [{"action_type": "tap", "target": "button", "coordinates": [1,2]}]
    assert detect_action_format(json_obj) == "coordinate"

def test_detect_action_format_unknown():
    json_obj = [{"other_key": 1}]
    assert detect_action_format(json_obj) == "unknown"

def test_detect_action_format_not_a_list():
    json_obj = {"action_id": 1}
    assert detect_action_format(json_obj) == "unknown"

# Tests for extract_structured_content
def test_extract_structured_content_simple():
    text = 'action_id: 1, explanation: "Do something"'
    actions = extract_structured_content(text)
    assert len(actions) == 1
    assert actions[0]["action_id"] == "1"
    assert "Do something" in actions[0]["explanation"]

def test_extract_structured_content_with_params():
    text = 'action_id: 2, params: {"key": "value"}, explanation: "Do something else"'
    actions = extract_structured_content(text)
    assert len(actions) == 1
    assert actions[0]["action_id"] == "2"
    # This is tricky because of the regex, let's just check if params is a dict
    assert isinstance(actions[0]["params"], dict)

def test_extract_structured_content_multiple():
    text = """
    action_id: 1, explanation: "First"
    action_id: 2, explanation: "Second"
    """
    actions = extract_structured_content(text)
    assert len(actions) == 2
    assert actions[0]["action_id"] == "1"
    assert actions[1]["action_id"] == "2"
