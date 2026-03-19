"""Tests for prompt builder — replicates ApePromptBuilder behavior."""

from __future__ import annotations

from aperv_llm_validation.data.models import Widget
from aperv_llm_validation.pipeline.prompt_builder import (
    build_messages,
    build_system_message,
    build_tool_schema,
    build_user_text,
    build_widget_list,
)


def _make_button(text: str = "OK", bounds: tuple[int, int, int, int] = (0, 300, 1080, 450)) -> Widget:
    return Widget(
        class_name="android.widget.Button",
        text=text,
        content_desc="",
        resource_id="com.example:id/btn",
        bounds=bounds,
        clickable=True,
        long_clickable=False,
        editable=False,
        checkable=False,
        enabled=True,
    )


def _make_edit_text() -> Widget:
    return Widget(
        class_name="android.widget.EditText",
        text="",
        content_desc="",
        resource_id="com.example:id/input",
        bounds=(0, 500, 1080, 600),
        clickable=True,
        long_clickable=False,
        editable=True,
        checkable=False,
        enabled=True,
    )


class TestBuildWidgetList:
    """Tests for build_widget_list formatting."""

    def test_format_single_button(self):
        """Widget list line format: [0] Button "OK" @(500,207) (v:0)."""
        widgets = [_make_button("OK", (0, 300, 1080, 450))]
        result = build_widget_list(widgets, 1080, 1080)
        # center = (540, 375), normX = int(540/1080*1000) = 500, normY = int(375/1080*1000) = 347
        assert result.startswith('[0] Button "OK"')
        assert "(v:0)" in result

    def test_format_multiple_widgets(self):
        widgets = [
            _make_button("A", (0, 0, 100, 100)),
            _make_button("B", (100, 100, 200, 200)),
        ]
        result = build_widget_list(widgets, 1080, 1920)
        lines = result.strip().split("\n")
        assert len(lines) == 2
        assert lines[0].startswith("[0]")
        assert lines[1].startswith("[1]")

    def test_normalized_coordinates(self):
        """Verify normX = int((centerX / device_w) * 1000)."""
        # bounds (0, 0, 1080, 750) -> center (540, 375)
        # normX = int(540/1080*1000) = 500
        # normY = int(375/1920*1000) = 195
        widgets = [_make_button("Test", (0, 0, 1080, 750))]
        result = build_widget_list(widgets, 1080, 1920)
        assert "@(500,195)" in result

    def test_content_desc_used_when_no_text(self):
        """content_desc is used as display text when text is empty."""
        widget = Widget(
            class_name="android.widget.ImageView",
            text="",
            content_desc="More options",
            resource_id="",
            bounds=(975, 73, 1080, 199),
            clickable=True,
            long_clickable=True,
            editable=False,
            checkable=False,
            enabled=True,
        )
        result = build_widget_list([widget], 1080, 1920)
        assert '"More options"' in result

    def test_empty_widget_list(self):
        result = build_widget_list([], 1080, 1920)
        assert result == ""

    def test_simple_class_name_extraction(self):
        """Full class name is shortened: android.widget.Button -> Button."""
        widgets = [_make_button()]
        result = build_widget_list(widgets, 1080, 1920)
        assert "Button" in result
        assert "android.widget.Button" not in result


class TestBuildSystemMessage:
    """Tests for build_system_message — exact replica of Java."""

    def test_contains_agent_role(self):
        msg = build_system_message(include_type_text=False)
        assert "You are an Android UI testing agent exploring an app." in msg

    def test_contains_dialog_instruction(self):
        msg = build_system_message(include_type_text=False)
        assert "DIALOG: If permission/error dialog visible, dismiss it first (click Allow/OK)." in msg

    def test_contains_priority_instruction(self):
        msg = build_system_message(include_type_text=False)
        assert "PRIORITY: [DM]/[M] elements > unvisited (v:0) > visited." in msg

    def test_contains_avoid_instruction(self):
        msg = build_system_message(include_type_text=False)
        assert "AVOID: status bar (top), navigation bar (bottom)." in msg

    def test_contains_core_tools(self):
        msg = build_system_message(include_type_text=False)
        assert "click(x, y)" in msg
        assert "long_click(x, y)" in msg
        assert "back()" in msg

    def test_without_type_text(self):
        msg = build_system_message(include_type_text=False)
        assert "type_text(x, y, text)" not in msg

    def test_with_type_text(self):
        msg = build_system_message(include_type_text=True)
        assert "type_text(x, y, text)" in msg

    def test_contains_json_response_instruction(self):
        msg = build_system_message(include_type_text=False)
        assert 'Respond with one JSON: {"name": "<action>", "arguments": {<args>}}' in msg

    def test_contains_rules_section(self):
        msg = build_system_message(include_type_text=False)
        assert "RULES: Don't click same position twice." in msg
        assert "Use type_text for input fields with valid data" in msg

    def test_contains_coordinate_space(self):
        msg = build_system_message(include_type_text=False)
        assert "Tools (coordinates in [0,1000) normalized space):" in msg

    def test_include_reasoning_does_not_change_text(self):
        """include_reasoning only affects tool schema, not system message text."""
        msg_no = build_system_message(include_type_text=False, include_reasoning=False)
        msg_yes = build_system_message(include_type_text=False, include_reasoning=True)
        assert msg_no == msg_yes


class TestBuildToolSchema:
    """Tests for OpenAI tool schema generation."""

    def test_base_tools_count(self):
        """Without type_text: click, long_click, back = 3 tools."""
        tools = build_tool_schema(include_type_text=False)
        assert len(tools) == 3
        names = [t["function"]["name"] for t in tools]
        assert names == ["click", "long_click", "back"]

    def test_with_type_text_adds_fourth_tool(self):
        """With type_text: click, long_click, type_text, back = 4 tools."""
        tools = build_tool_schema(include_type_text=True)
        assert len(tools) == 4
        names = [t["function"]["name"] for t in tools]
        assert "type_text" in names

    def test_type_text_conditional(self):
        """type_text only present when include_type_text=True."""
        tools_without = build_tool_schema(include_type_text=False)
        tools_with = build_tool_schema(include_type_text=True)
        names_without = {t["function"]["name"] for t in tools_without}
        names_with = {t["function"]["name"] for t in tools_with}
        assert "type_text" not in names_without
        assert "type_text" in names_with

    def test_click_has_xy_params(self):
        tools = build_tool_schema(include_type_text=False)
        click = [t for t in tools if t["function"]["name"] == "click"][0]
        params = click["function"]["parameters"]
        assert "x" in params["properties"]
        assert "y" in params["properties"]
        assert params["properties"]["x"]["type"] == "integer"

    def test_type_text_has_text_param(self):
        tools = build_tool_schema(include_type_text=True)
        type_text = [t for t in tools if t["function"]["name"] == "type_text"][0]
        params = type_text["function"]["parameters"]
        assert "text" in params["properties"]
        assert "text" in params["required"]

    def test_back_has_no_required_params(self):
        tools = build_tool_schema(include_type_text=False)
        back = [t for t in tools if t["function"]["name"] == "back"][0]
        assert back["function"]["parameters"]["required"] == []

    def test_reasoning_parameter_added(self):
        """When include_reasoning=True, all tools get an optional reasoning parameter."""
        tools = build_tool_schema(include_type_text=True, include_reasoning=True)
        for tool in tools:
            params = tool["function"]["parameters"]
            assert "reasoning" in params["properties"]
            assert params["properties"]["reasoning"]["type"] == "string"
            # reasoning is optional — not in required
            assert "reasoning" not in params.get("required", [])

    def test_reasoning_parameter_absent(self):
        """When include_reasoning=False, no reasoning parameter."""
        tools = build_tool_schema(include_type_text=True, include_reasoning=False)
        for tool in tools:
            params = tool["function"]["parameters"]
            assert "reasoning" not in params["properties"]

    def test_tool_type_is_function(self):
        tools = build_tool_schema(include_type_text=False)
        for tool in tools:
            assert tool["type"] == "function"


class TestBuildUserText:
    """Tests for build_user_text."""

    def test_screen_header(self):
        result = build_user_text("com.example.MainActivity", [], 1080, 1920)
        assert 'Screen "MainActivity":' in result

    def test_unknown_activity(self):
        result = build_user_text("", [], 1080, 1920)
        assert 'Screen "Unknown":' in result

    def test_simple_activity_name(self):
        result = build_user_text("com.example.app.LoginActivity", [], 1080, 1920)
        assert '"LoginActivity"' in result

    def test_includes_widget_list(self):
        widgets = [_make_button("Login")]
        result = build_user_text("com.example.MainActivity", widgets, 1080, 1920)
        assert "Login" in result
        assert "[0]" in result


class TestBuildMessages:
    """Tests for build_messages — the main 2-message builder."""

    def test_returns_two_messages(self):
        messages = build_messages("abc123", [_make_button()], "com.example.Main", 1080, 1920)
        assert len(messages) == 2

    def test_first_message_is_system(self):
        messages = build_messages("abc123", [_make_button()], "com.example.Main", 1080, 1920)
        assert messages[0]["role"] == "system"
        assert isinstance(messages[0]["content"], str)

    def test_second_message_is_user(self):
        messages = build_messages("abc123", [_make_button()], "com.example.Main", 1080, 1920)
        assert messages[1]["role"] == "user"

    def test_user_message_has_two_content_parts(self):
        messages = build_messages("abc123", [_make_button()], "com.example.Main", 1080, 1920)
        content = messages[1]["content"]
        assert isinstance(content, list)
        assert len(content) == 2

    def test_user_message_image_first_text_second(self):
        messages = build_messages("abc123", [_make_button()], "com.example.Main", 1080, 1920)
        content = messages[1]["content"]
        assert content[0]["type"] == "image_url"
        assert content[1]["type"] == "text"

    def test_image_url_format(self):
        messages = build_messages("abc123", [_make_button()], "com.example.Main", 1080, 1920)
        image_url = messages[1]["content"][0]["image_url"]["url"]
        assert image_url == "data:image/jpeg;base64,abc123"

    def test_empty_base64(self):
        messages = build_messages("", [_make_button()], "com.example.Main", 1080, 1920)
        image_url = messages[1]["content"][0]["image_url"]["url"]
        assert image_url == "data:image/jpeg;base64,"

    def test_none_base64(self):
        messages = build_messages(None, [_make_button()], "com.example.Main", 1080, 1920)
        image_url = messages[1]["content"][0]["image_url"]["url"]
        assert image_url == "data:image/jpeg;base64,"

    def test_system_message_includes_type_text_when_editable(self):
        """When editable widgets present, system message includes type_text."""
        widgets = [_make_button(), _make_edit_text()]
        messages = build_messages("abc", widgets, "com.example.Main", 1080, 1920)
        system_text = messages[0]["content"]
        assert "type_text(x, y, text)" in system_text

    def test_system_message_excludes_type_text_when_no_editable(self):
        """When no editable widgets, system message excludes type_text."""
        messages = build_messages("abc", [_make_button()], "com.example.Main", 1080, 1920)
        system_text = messages[0]["content"]
        assert "type_text(x, y, text)" not in system_text
