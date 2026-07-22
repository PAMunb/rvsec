"""
Unit tests for ActionValidator and related dataclasses.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from rv_agent.validation.action_validator import (
    UIElement,
    ValidationResult,
    ActionValidator
)


# =============================================================================
# UIElement Dataclass Tests
# =============================================================================

class TestUIElement:
    """Tests for UIElement dataclass."""

    def test_ui_element_creation(self):
        """Test UIElement creation with all fields."""
        element = UIElement(
            bounds=((100, 200), (300, 400)),
            clickable=True,
            long_clickable=False,
            checkable=False,
            editable=False,
            class_name="android.widget.Button",
            resource_id="com.example:id/button1",
            text="Submit",
            content_desc="Submit button"
        )

        assert element.bounds == ((100, 200), (300, 400))
        assert element.clickable is True
        assert element.long_clickable is False
        assert element.text == "Submit"

    def test_contains_point_inside(self):
        """Test contains_point returns True for point inside bounds."""
        element = UIElement(
            bounds=((100, 100), (200, 200)),
            clickable=True,
            long_clickable=False,
            checkable=False,
            editable=False,
            class_name="Button",
            resource_id="",
            text="",
            content_desc=""
        )

        # Point inside
        assert element.contains_point(150, 150) is True
        # Edge cases
        assert element.contains_point(100, 100) is True  # Top-left corner
        assert element.contains_point(200, 200) is True  # Bottom-right corner
        assert element.contains_point(100, 200) is True  # Bottom-left corner
        assert element.contains_point(200, 100) is True  # Top-right corner

    def test_contains_point_outside(self):
        """Test contains_point returns False for point outside bounds."""
        element = UIElement(
            bounds=((100, 100), (200, 200)),
            clickable=True,
            long_clickable=False,
            checkable=False,
            editable=False,
            class_name="Button",
            resource_id="",
            text="",
            content_desc=""
        )

        # Points outside
        assert element.contains_point(50, 150) is False   # Left
        assert element.contains_point(250, 150) is False  # Right
        assert element.contains_point(150, 50) is False   # Above
        assert element.contains_point(150, 250) is False  # Below

    def test_str_with_text(self):
        """Test string representation with text."""
        element = UIElement(
            bounds=((0, 0), (100, 50)),
            clickable=True,
            long_clickable=False,
            checkable=False,
            editable=False,
            class_name="android.widget.TextView",
            resource_id="",
            text="Hello World",
            content_desc=""
        )

        str_repr = str(element)
        assert "TextView" in str_repr
        assert "Hello World" in str_repr

    def test_str_with_content_desc(self):
        """Test string representation with content_desc (no text)."""
        element = UIElement(
            bounds=((0, 0), (100, 50)),
            clickable=True,
            long_clickable=False,
            checkable=False,
            editable=False,
            class_name="android.widget.ImageButton",
            resource_id="",
            text="",
            content_desc="Menu button"
        )

        str_repr = str(element)
        assert "Menu button" in str_repr

    def test_str_with_resource_id(self):
        """Test string representation with resource_id only."""
        element = UIElement(
            bounds=((0, 0), (100, 50)),
            clickable=True,
            long_clickable=False,
            checkable=False,
            editable=False,
            class_name="android.widget.View",
            resource_id="com.example:id/container",
            text="",
            content_desc=""
        )

        str_repr = str(element)
        assert "container" in str_repr


# =============================================================================
# ValidationResult Dataclass Tests
# =============================================================================

class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_valid_result(self):
        """Test creating a valid result."""
        result = ValidationResult(
            valid=True,
            reason="Valid click action"
        )

        assert result.valid is True
        assert result.reason == "Valid click action"
        assert result.element is None

    def test_invalid_result_with_element(self):
        """Test creating an invalid result with element."""
        element = UIElement(
            bounds=((0, 0), (100, 100)),
            clickable=False,
            long_clickable=False,
            checkable=False,
            editable=False,
            class_name="TextView",
            resource_id="",
            text="Label",
            content_desc=""
        )

        result = ValidationResult(
            valid=False,
            reason="Element is not clickable",
            element=element
        )

        assert result.valid is False
        assert "not clickable" in result.reason
        assert result.element == element


# =============================================================================
# ActionValidator Tests
# =============================================================================

class TestActionValidatorInit:
    """Tests for ActionValidator initialization."""

    def test_init_creates_empty_state(self):
        """Test initialization creates empty state."""
        validator = ActionValidator()

        assert validator.current_elements == []
        assert validator.validation_history == []


class TestActionValidatorLoadUIElements:
    """Tests for ActionValidator.load_ui_elements()."""

    def _create_uiautomator_xml(self, tmp_path: Path, content: str) -> Path:
        """Helper to create UIAutomator XML file."""
        xml_path = tmp_path / "test.uiautomator"
        xml_path.write_text(content)
        return xml_path

    def test_load_basic_elements(self, tmp_path):
        """Test loading basic UI elements."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <hierarchy rotation="0">
            <node bounds="[0,0][1080,1920]" class="android.widget.FrameLayout"
                  clickable="false" long-clickable="false" checkable="false"
                  resource-id="" text="" content-desc="">
                <node bounds="[100,200][300,400]" class="android.widget.Button"
                      clickable="true" long-clickable="false" checkable="false"
                      resource-id="button1" text="Submit" content-desc="">
                </node>
            </node>
        </hierarchy>
        '''
        xml_path = self._create_uiautomator_xml(tmp_path, xml_content)

        validator = ActionValidator()
        count = validator.load_ui_elements(xml_path)

        assert count == 3  # hierarchy + 2 nodes
        assert len(validator.current_elements) == 3

    def test_load_parses_bounds_correctly(self, tmp_path):
        """Test that bounds are parsed correctly."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <hierarchy rotation="0">
            <node bounds="[42,101][316,172]" class="android.widget.Button"
                  clickable="true" long-clickable="false" checkable="false"
                  resource-id="" text="Test" content-desc="">
            </node>
        </hierarchy>
        '''
        xml_path = self._create_uiautomator_xml(tmp_path, xml_content)

        validator = ActionValidator()
        validator.load_ui_elements(xml_path)

        button = [e for e in validator.current_elements if e.class_name == "android.widget.Button"][0]
        assert button.bounds == ((42, 101), (316, 172))

    def test_load_parses_clickable_attribute(self, tmp_path):
        """Test that clickable attribute is parsed correctly."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <hierarchy rotation="0">
            <node bounds="[0,0][100,100]" class="Button"
                  clickable="true" long-clickable="false" checkable="false"
                  resource-id="" text="" content-desc="">
            </node>
            <node bounds="[0,0][100,100]" class="TextView"
                  clickable="false" long-clickable="false" checkable="false"
                  resource-id="" text="" content-desc="">
            </node>
        </hierarchy>
        '''
        xml_path = self._create_uiautomator_xml(tmp_path, xml_content)

        validator = ActionValidator()
        validator.load_ui_elements(xml_path)

        button = [e for e in validator.current_elements if e.class_name == "Button"][0]
        text = [e for e in validator.current_elements if e.class_name == "TextView"][0]

        assert button.clickable is True
        assert text.clickable is False

    def test_load_parses_editable_for_edittext(self, tmp_path):
        """Test that EditText elements are marked as editable."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <hierarchy rotation="0">
            <node bounds="[0,0][100,100]" class="android.widget.EditText"
                  clickable="true" long-clickable="false" checkable="false"
                  resource-id="" text="" content-desc="">
            </node>
        </hierarchy>
        '''
        xml_path = self._create_uiautomator_xml(tmp_path, xml_content)

        validator = ActionValidator()
        validator.load_ui_elements(xml_path)

        edittext = [e for e in validator.current_elements if "EditText" in e.class_name][0]
        assert edittext.editable is True

    def test_load_handles_malformed_bounds(self, tmp_path):
        """Test handling of malformed bounds."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <hierarchy rotation="0">
            <node bounds="invalid" class="Button"
                  clickable="true" long-clickable="false" checkable="false"
                  resource-id="" text="" content-desc="">
            </node>
        </hierarchy>
        '''
        xml_path = self._create_uiautomator_xml(tmp_path, xml_content)

        validator = ActionValidator()
        count = validator.load_ui_elements(xml_path)

        # Should still load, with default bounds
        assert count > 0
        button = [e for e in validator.current_elements if e.class_name == "Button"][0]
        assert button.bounds == ((0, 0), (0, 0))

    def test_load_handles_parse_error(self, tmp_path):
        """Test handling of XML parse error."""
        xml_path = tmp_path / "invalid.uiautomator"
        xml_path.write_text("not valid xml")

        validator = ActionValidator()
        count = validator.load_ui_elements(xml_path)

        assert count == 0
        assert validator.current_elements == []

    def test_load_clears_previous_elements(self, tmp_path):
        """Test that loading new elements clears previous ones."""
        xml1 = self._create_uiautomator_xml(
            tmp_path,
            '<hierarchy><node bounds="[0,0][100,100]" class="Button" clickable="true" long-clickable="false" checkable="false" resource-id="" text="" content-desc=""></node></hierarchy>'
        )
        xml2 = tmp_path / "second.uiautomator"
        xml2.write_text('<hierarchy><node bounds="[0,0][100,100]" class="TextView" clickable="false" long-clickable="false" checkable="false" resource-id="" text="" content-desc=""></node></hierarchy>')

        validator = ActionValidator()
        validator.load_ui_elements(xml1)
        assert any(e.class_name == "Button" for e in validator.current_elements)

        validator.load_ui_elements(xml2)
        assert not any(e.class_name == "Button" for e in validator.current_elements)


class TestActionValidatorFindElementAt:
    """Tests for ActionValidator.find_element_at()."""

    def test_find_element_at_center(self):
        """Test finding element at center of bounds."""
        validator = ActionValidator()
        validator.current_elements = [
            UIElement(
                bounds=((100, 100), (200, 200)),
                clickable=True,
                long_clickable=False,
                checkable=False,
                editable=False,
                class_name="Button",
                resource_id="btn1",
                text="Click me",
                content_desc=""
            )
        ]

        element = validator.find_element_at(150, 150)
        assert element is not None
        assert element.resource_id == "btn1"

    def test_find_element_at_no_match(self):
        """Test finding element at empty area."""
        validator = ActionValidator()
        validator.current_elements = [
            UIElement(
                bounds=((100, 100), (200, 200)),
                clickable=True,
                long_clickable=False,
                checkable=False,
                editable=False,
                class_name="Button",
                resource_id="",
                text="",
                content_desc=""
            )
        ]

        element = validator.find_element_at(50, 50)
        assert element is None

    def test_find_element_at_returns_smallest(self):
        """Test that smallest containing element is returned."""
        validator = ActionValidator()
        validator.current_elements = [
            UIElement(
                bounds=((0, 0), (1080, 1920)),  # Large container
                clickable=False,
                long_clickable=False,
                checkable=False,
                editable=False,
                class_name="FrameLayout",
                resource_id="container",
                text="",
                content_desc=""
            ),
            UIElement(
                bounds=((100, 100), (200, 200)),  # Smaller button inside
                clickable=True,
                long_clickable=False,
                checkable=False,
                editable=False,
                class_name="Button",
                resource_id="button",
                text="",
                content_desc=""
            )
        ]

        element = validator.find_element_at(150, 150)
        assert element is not None
        assert element.resource_id == "button"  # Should be the smaller one


class TestActionValidatorValidateClick:
    """Tests for ActionValidator.validate_click()."""

    def test_validate_click_on_clickable(self):
        """Test validating click on clickable element."""
        validator = ActionValidator()
        validator.current_elements = [
            UIElement(
                bounds=((100, 100), (200, 200)),
                clickable=True,
                long_clickable=False,
                checkable=False,
                editable=False,
                class_name="Button",
                resource_id="",
                text="Submit",
                content_desc=""
            )
        ]

        result = validator.validate_click(150, 150)

        assert result.valid is True
        assert result.element is not None
        assert len(validator.validation_history) == 1

    def test_validate_click_on_non_clickable(self):
        """Test validating click on non-clickable element."""
        validator = ActionValidator()
        validator.current_elements = [
            UIElement(
                bounds=((100, 100), (200, 200)),
                clickable=False,
                long_clickable=False,
                checkable=False,
                editable=False,
                class_name="TextView",
                resource_id="",
                text="Label",
                content_desc=""
            )
        ]

        result = validator.validate_click(150, 150)

        assert result.valid is False
        assert "not clickable" in result.reason
        assert result.element is not None

    def test_validate_click_on_empty_area(self):
        """Test validating click on empty area."""
        validator = ActionValidator()
        validator.current_elements = []

        result = validator.validate_click(500, 500)

        assert result.valid is False
        assert "No element" in result.reason
        assert result.element is None

    def test_validate_click_records_history(self):
        """Test that click validation is recorded in history."""
        validator = ActionValidator()
        validator.current_elements = [
            UIElement(
                bounds=((0, 0), (100, 100)),
                clickable=True,
                long_clickable=False,
                checkable=False,
                editable=False,
                class_name="Button",
                resource_id="",
                text="",
                content_desc=""
            )
        ]

        validator.validate_click(50, 50)

        assert len(validator.validation_history) == 1
        assert validator.validation_history[0]['action'] == 'click'
        assert validator.validation_history[0]['x'] == 50
        assert validator.validation_history[0]['y'] == 50


class TestActionValidatorValidateLongClick:
    """Tests for ActionValidator.validate_long_click()."""

    def test_validate_long_click_on_long_clickable(self):
        """Test validating long click on long-clickable element."""
        validator = ActionValidator()
        validator.current_elements = [
            UIElement(
                bounds=((100, 100), (200, 200)),
                clickable=True,
                long_clickable=True,
                checkable=False,
                editable=False,
                class_name="ListItem",
                resource_id="",
                text="Item",
                content_desc=""
            )
        ]

        result = validator.validate_long_click(150, 150)

        assert result.valid is True
        assert result.element is not None

    def test_validate_long_click_on_non_long_clickable(self):
        """Test validating long click on element without long-click support."""
        validator = ActionValidator()
        validator.current_elements = [
            UIElement(
                bounds=((100, 100), (200, 200)),
                clickable=True,
                long_clickable=False,
                checkable=False,
                editable=False,
                class_name="Button",
                resource_id="",
                text="Submit",
                content_desc=""
            )
        ]

        result = validator.validate_long_click(150, 150)

        assert result.valid is False
        assert "does not support long click" in result.reason

    def test_validate_long_click_on_empty_area(self):
        """Test validating long click on empty area."""
        validator = ActionValidator()
        validator.current_elements = []

        result = validator.validate_long_click(500, 500)

        assert result.valid is False
        assert "No element" in result.reason


class TestActionValidatorValidateTypeText:
    """Tests for ActionValidator.validate_type_text()."""

    def test_validate_type_text_on_editable(self):
        """Test validating type text on editable element."""
        validator = ActionValidator()
        validator.current_elements = [
            UIElement(
                bounds=((100, 100), (400, 150)),
                clickable=True,
                long_clickable=False,
                checkable=False,
                editable=True,
                class_name="android.widget.EditText",
                resource_id="username",
                text="",
                content_desc="Username field"
            )
        ]

        result = validator.validate_type_text(250, 125, "john_doe")

        assert result.valid is True
        assert result.element is not None

    def test_validate_type_text_on_non_editable(self):
        """Test validating type text on non-editable element."""
        validator = ActionValidator()
        validator.current_elements = [
            UIElement(
                bounds=((100, 100), (400, 150)),
                clickable=False,
                long_clickable=False,
                checkable=False,
                editable=False,
                class_name="android.widget.TextView",
                resource_id="label",
                text="Username:",
                content_desc=""
            )
        ]

        result = validator.validate_type_text(250, 125, "text")

        assert result.valid is False
        assert "not editable" in result.reason

    def test_validate_type_text_on_empty_area(self):
        """Test validating type text on empty area."""
        validator = ActionValidator()
        validator.current_elements = []

        result = validator.validate_type_text(500, 500, "text")

        assert result.valid is False
        assert "No element" in result.reason

    def test_validate_type_text_records_text(self):
        """Test that type text validation records the text."""
        validator = ActionValidator()
        validator.current_elements = [
            UIElement(
                bounds=((0, 0), (100, 100)),
                clickable=True,
                long_clickable=False,
                checkable=False,
                editable=True,
                class_name="EditText",
                resource_id="",
                text="",
                content_desc=""
            )
        ]

        validator.validate_type_text(50, 50, "hello world")

        assert validator.validation_history[0]['text'] == "hello world"


class TestActionValidatorValidateSystemAction:
    """Tests for ActionValidator.validate_system_action()."""

    def test_validate_back_action(self):
        """Test validating BACK action."""
        validator = ActionValidator()

        result = validator.validate_system_action("BACK")

        assert result.valid is True
        assert "BACK" in result.reason

    def test_validate_home_action(self):
        """Test validating HOME action."""
        validator = ActionValidator()

        result = validator.validate_system_action("HOME")

        assert result.valid is True
        assert "HOME" in result.reason

    def test_system_action_records_history(self):
        """Test that system actions are recorded in history."""
        validator = ActionValidator()

        validator.validate_system_action("BACK")

        assert len(validator.validation_history) == 1
        assert validator.validation_history[0]['action'] == 'back'


class TestActionValidatorGetElementTypeDistribution:
    """Tests for ActionValidator.get_element_type_distribution()."""

    def test_get_distribution_basic(self):
        """Test getting element type distribution."""
        validator = ActionValidator()
        validator.current_elements = [
            UIElement(bounds=((0, 0), (100, 100)), clickable=True, long_clickable=False,
                      checkable=False, editable=False, class_name="android.widget.Button",
                      resource_id="", text="", content_desc=""),
            UIElement(bounds=((0, 0), (100, 100)), clickable=False, long_clickable=False,
                      checkable=False, editable=False, class_name="android.widget.TextView",
                      resource_id="", text="", content_desc=""),
            UIElement(bounds=((0, 0), (100, 100)), clickable=True, long_clickable=False,
                      checkable=False, editable=False, class_name="android.widget.Button",
                      resource_id="", text="", content_desc=""),
        ]

        distribution = validator.get_element_type_distribution()

        assert distribution["Button"] == 2
        assert distribution["TextView"] == 1

    def test_get_distribution_empty(self):
        """Test getting distribution from empty elements."""
        validator = ActionValidator()
        distribution = validator.get_element_type_distribution()

        assert distribution == {}


class TestActionValidatorGetInteractiveElements:
    """Tests for ActionValidator.get_interactive_elements()."""

    def test_get_interactive_elements(self):
        """Test getting interactive elements."""
        validator = ActionValidator()
        validator.current_elements = [
            UIElement(bounds=((0, 0), (100, 100)), clickable=True, long_clickable=False,
                      checkable=False, editable=False, class_name="Button",
                      resource_id="", text="", content_desc=""),
            UIElement(bounds=((0, 0), (100, 100)), clickable=False, long_clickable=False,
                      checkable=False, editable=False, class_name="TextView",
                      resource_id="", text="", content_desc=""),
            UIElement(bounds=((0, 0), (100, 100)), clickable=False, long_clickable=True,
                      checkable=False, editable=False, class_name="ListItem",
                      resource_id="", text="", content_desc=""),
            UIElement(bounds=((0, 0), (100, 100)), clickable=False, long_clickable=False,
                      checkable=False, editable=True, class_name="EditText",
                      resource_id="", text="", content_desc=""),
        ]

        interactive = validator.get_interactive_elements()

        assert len(interactive) == 3  # Button, ListItem, EditText


class TestActionValidatorGetValidationSummary:
    """Tests for ActionValidator.get_validation_summary()."""

    def test_get_summary_basic(self):
        """Test getting validation summary."""
        validator = ActionValidator()
        validator.current_elements = [
            UIElement(bounds=((0, 0), (100, 100)), clickable=True, long_clickable=False,
                      checkable=False, editable=False, class_name="Button",
                      resource_id="", text="", content_desc=""),
        ]

        # Perform some validations
        validator.validate_click(50, 50)  # Valid
        validator.validate_click(500, 500)  # Invalid - no element
        validator.validate_system_action("BACK")  # Valid

        summary = validator.get_validation_summary()

        assert summary['total_actions'] == 3
        assert summary['valid_actions'] == 2
        assert summary['invalid_actions'] == 1
        assert summary['valid_rate'] == pytest.approx(2/3)
        assert summary['action_types']['click'] == 2
        assert summary['action_types']['back'] == 1

    def test_get_summary_empty(self):
        """Test getting summary with no validations."""
        validator = ActionValidator()
        summary = validator.get_validation_summary()

        assert summary['total_actions'] == 0
        assert summary['valid_actions'] == 0
        assert summary['valid_rate'] == 0.0
