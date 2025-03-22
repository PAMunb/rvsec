import pytest

from rvandroid.domain.widget import Widget, WidgetType, WidgetEvent, WidgetEventType


class TestWidgetEventType:
    """Tests for the WidgetEventType enum"""

    def test_widget_event_type_values(self):
        """Test WidgetEventType enum values"""
        assert WidgetEventType.CLICK.value == 1
        assert WidgetEventType.LONG_CLICK.value == 2
        assert WidgetEventType.SCROLL.value == 3
        assert WidgetEventType.DRAG.value == 4
        assert WidgetEventType.HOVER.value == 5
        assert WidgetEventType.TOUCH.value == 6
        assert WidgetEventType.FOCUS.value == 7
        assert WidgetEventType.KEY.value == 8
        assert WidgetEventType.TEXT_CHANGE.value == 9
        assert WidgetEventType.GESTURE.value == 10
        assert WidgetEventType.SELECTION.value == 11
        assert WidgetEventType.OTHER.value == 12


class TestWidgetEvent:
    """Tests for the WidgetEvent class"""

    @pytest.fixture
    def sample_event(self):
        """Create a sample widget event for testing"""
        return WidgetEvent(
            WidgetEventType.CLICK,
            "com.example.MainActivity",
            "onClick",
            "com.example.MainActivity.onClick(android.view.View)"
        )

    def test_widget_event_initialization(self, sample_event):
        """Test WidgetEvent constructor"""
        assert sample_event.type == WidgetEventType.CLICK
        assert sample_event.clazz == "com.example.MainActivity"
        assert sample_event.method == "onClick"
        assert sample_event.signature == "com.example.MainActivity.onClick(android.view.View)"

    def test_to_json(self, sample_event):
        """Test to_json method"""
        json_data = sample_event.to_json()
        assert json_data["type"] == "CLICK"
        assert json_data["signature"] == "com.example.MainActivity.onClick(android.view.View)"

    def test_equality(self, sample_event):
        """Test equality comparison"""
        # Same event
        event2 = WidgetEvent(
            WidgetEventType.CLICK,
            "com.example.MainActivity",
            "onClick",
            "com.example.MainActivity.onClick(android.view.View)"
        )
        assert sample_event == event2

        # Different type
        event3 = WidgetEvent(
            WidgetEventType.LONG_CLICK,
            "com.example.MainActivity",
            "onClick",
            "com.example.MainActivity.onClick(android.view.View)"
        )
        assert sample_event != event3

        # Different signature
        event4 = WidgetEvent(
            WidgetEventType.CLICK,
            "com.example.MainActivity",
            "onClick",
            "com.example.MainActivity.onClick()"
        )
        assert sample_event != event4

        # Different object type
        assert sample_event != "not an event"

    def test_hash(self, sample_event):
        """Test hash computation"""
        expected_hash = hash((sample_event.signature, sample_event.type))
        assert hash(sample_event) == expected_hash

    def test_widget_event_string_representation(self, sample_event):  # Renomeado para evitar confusão
        """Test __str__ method"""
        string_repr = str(sample_event)

        assert "WidgetEvent=" in string_repr
        assert "type=WidgetEventType.CLICK" in string_repr  # Corrigido para corresponder à saída real
        assert "clazz=com.example.MainActivity" in string_repr
        assert "method=onClick" in string_repr

    def test_repr(self, sample_event):
        """Test __repr__ method"""
        assert repr(sample_event) == "(CLICK,com.example.MainActivity.onClick(android.view.View))"


class TestWidgetType:
    """Tests for the WidgetType enum"""

    def test_widget_type_values(self):
        """Test WidgetType enum values"""
        assert WidgetType.BUTTON.value == "android.widget.Button"
        assert WidgetType.CHECKBOX.value == "android.widget.CheckBox"
        assert WidgetType.EDIT_TEXT.value == "android.widget.EditText"
        assert WidgetType.OTHER.value == "OTHER"

    def test_from_string(self):
        """Test from_string method"""
        assert WidgetType.from_string("BUTTON") == WidgetType.BUTTON
        assert WidgetType.from_string("TEXT_VIEW") == WidgetType.TEXT_VIEW
        assert WidgetType.from_string("NONEXISTENT") == WidgetType.OTHER

    def test_from_class_name(self):
        """Test from_class_name method"""
        assert WidgetType.from_class_name("android.widget.Button") == WidgetType.BUTTON
        assert WidgetType.from_class_name("android.widget.EditText") == WidgetType.EDIT_TEXT
        assert WidgetType.from_class_name("android.something.Unknown") == WidgetType.OTHER


class TestWidget:
    """Tests for the Widget class"""

    @pytest.fixture
    def sample_widget(self):
        """Create a sample widget for testing"""
        return Widget("button1", "login_button", WidgetType.BUTTON)

    @pytest.fixture
    def sample_event(self):
        """Create a sample widget event for testing"""
        return WidgetEvent(
            WidgetEventType.CLICK,
            "com.example.MainActivity",
            "onClick",
            "com.example.MainActivity.onClick(android.view.View)"
        )

    def test_widget_initialization(self, sample_widget):
        """Test Widget constructor"""
        assert sample_widget.id == "button1"
        assert sample_widget.name == "login_button"
        assert sample_widget.type == WidgetType.BUTTON
        assert sample_widget.text == ""
        assert sample_widget.hint == ""
        assert sample_widget.field == ""
        assert sample_widget.input_type == ""
        assert sample_widget.entries == []
        assert sample_widget.events == set()

    def test_add_event(self, sample_widget, sample_event):
        """Test adding an event to a widget"""
        # First add should succeed
        result = sample_widget.add_event(sample_event)
        assert result is True
        assert sample_event in sample_widget.events

        # Second add should fail (duplicate)
        result = sample_widget.add_event(sample_event)
        assert result is False
        assert len(sample_widget.events) == 1

    def test_to_json(self, sample_widget, sample_event):
        """Test to_json method"""
        sample_widget.text = "Login"
        sample_widget.hint = "Enter credentials"
        sample_widget.field = "loginButton"
        sample_widget.input_type = "text"
        sample_widget.entries = ["user1", "user2"]
        sample_widget.add_event(sample_event)

        json_data = sample_widget.to_json()

        assert json_data["id"] == "button1"
        assert json_data["name"] == "login_button"
        assert json_data["type"] == "BUTTON"
        assert json_data["text"] == "Login"
        assert json_data["hint"] == "Enter credentials"
        assert json_data["field"] == "loginButton"
        assert json_data["input_type"] == "text"
        assert json_data["entries"] == ["user1", "user2"]
        assert len(json_data["events"]) == 1
        assert json_data["events"][0]["type"] == "CLICK"

    def test_equality(self, sample_widget):
        """Test equality comparison"""
        # Same widget
        widget2 = Widget("button1", "another_name", WidgetType.BUTTON)
        assert sample_widget == widget2

        # Different id
        widget3 = Widget("button2", "login_button", WidgetType.BUTTON)
        assert sample_widget != widget3

        # Different object type
        assert sample_widget != "not a widget"

    def test_hash(self, sample_widget):
        """Test hash computation"""
        assert hash(sample_widget) == hash(sample_widget.id)

    def test_widget_string_representation(self, sample_widget):  # Renomeado para evitar confusão
        """Test __str__ method"""
        sample_widget.text = "Login"
        string_repr = str(sample_widget)

        assert "Widget=" in string_repr
        assert "id=button1" in string_repr
        assert "type=WidgetType.BUTTON" in string_repr  # Corrigido para corresponder à saída real
        assert "name=login_button" in string_repr
        assert "text=Login" in string_repr

    def test_repr(self, sample_widget):
        """Test __repr__ method"""
        assert repr(sample_widget) == "button1"
