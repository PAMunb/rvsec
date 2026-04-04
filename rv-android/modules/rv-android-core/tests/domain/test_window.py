# tests/model/test_window.py
import pytest
from rv_android_core.domain.widget import Widget, WidgetType
from rv_android_core.domain.window import Window, Windows, WindowType

from .test_framework import ModelTestBase


class TestWindowType(ModelTestBase):
    """
    Unit tests for the WindowType enum.

    Tests cover enum values and string conversion functionality.
    """

    def test_enum_values(self):
        """Test that WindowType enum has the expected values."""
        assert WindowType.ACTIVITY.value == 1
        assert WindowType.OPTIONSMENU.value == 2
        assert WindowType.CONTEXTMENU.value == 3
        assert WindowType.DIALOG.value == 4
        assert WindowType.FRAGMENT.value == 5

    def test_from_string(self):
        """Test conversion from string to WindowType."""
        assert WindowType.from_string("ACT") == WindowType.ACTIVITY
        assert WindowType.from_string("OPTIONS_MENU") == WindowType.OPTIONSMENU
        assert WindowType.from_string("CONTEXT_MENU") == WindowType.CONTEXTMENU
        assert WindowType.from_string("DIALOG") == WindowType.DIALOG
        assert WindowType.from_string("FRAGMENT") == WindowType.FRAGMENT

        # Test invalid inputs
        assert WindowType.from_string("NONEXISTENT") is None
        assert WindowType.from_string("") is None
        assert WindowType.from_string(None) is None


class TestWindow(ModelTestBase):
    """
    Unit tests for the Window class.

    Tests cover initialization, widget management, and JSON conversion.
    """

    @pytest.fixture
    def window(self):
        """Create a standard window for testing."""
        return Window("com.example.TestActivity")

    @pytest.fixture
    def widget(self):
        """Create a standard widget for testing."""
        return Widget("widget1", "Button1", WidgetType.BUTTON)

    def test_initialization(self, window):
        """Test that Window initializes with correct attributes."""
        assert window.id == ""
        assert window.name == "com.example.TestActivity"
        assert window.type == WindowType.ACTIVITY
        assert window.layout_file == ""
        assert len(window.widgets) == 0
        assert len(window.fields) == 0

    def test_add_widget(self, window, widget):
        """Test adding widgets to a window."""
        # Add widget successfully
        result = window.add_widget(widget)
        assert result is True
        assert str(widget.id) in window.widgets
        assert window.widgets[str(widget.id)] == widget

        # Try to add the same widget again
        result = window.add_widget(widget)
        assert result is False  # Already exists
        assert len(window.widgets) == 1

        # Test adding a widget with the same ID but different object
        different_widget = Widget("widget1", "Different Button", WidgetType.BUTTON)
        result = window.add_widget(different_widget)
        assert result is False
        # The original widget should still be in the dictionary
        assert window.widgets[str(widget.id)] == widget

    def test_get_widget(self, window, widget):
        """Test retrieving widgets by ID."""
        # Add widget first
        window.add_widget(widget)

        # Get by ID
        retrieved = window.get_widget(str(widget.id))
        assert retrieved is not None
        assert retrieved == widget

        # Try to get non-existent widget
        assert window.get_widget("non-existent-id") is None

    def test_get_widget_by_name(self, window, widget):
        """Test retrieving widgets by name."""
        # Add widget first
        window.add_widget(widget)

        # Get by name
        retrieved = window.get_widget_by_name(widget.name)
        assert retrieved is not None
        assert retrieved == widget

        # Try to get non-existent widget
        assert window.get_widget_by_name("Non-existent Widget") is None

        # Add a second widget with a different name
        widget2 = Widget("widget2", "Button2", WidgetType.BUTTON)
        window.add_widget(widget2)

        # Both widgets should be retrievable by name
        assert window.get_widget_by_name("Button1") == widget
        assert window.get_widget_by_name("Button2") == widget2

    def test_to_json(self, window, widget):
        """Test conversion to JSON format."""
        # Add widget and field
        window.add_widget(widget)
        window.fields.add("test_field")

        # Set additional properties
        window.id = "test_window_id"
        window.layout_file = "test_layout.xml"

        # Convert to JSON
        json_data = window.to_json()

        # Verify JSON structure
        assert json_data["id"] == "test_window_id"
        assert json_data["name"] == "com.example.TestActivity"
        assert json_data["type"] == "ACTIVITY"
        assert json_data["layout_file"] == "test_layout.xml"
        assert len(json_data["widgets"]) == 1
        assert json_data["widgets"][0] == widget.to_json()
        assert json_data["fields"] == ["test_field"]

    def test_str_representation(self, window):
        """Test string representation."""
        # Set properties
        window.id = "test_id"
        window.type = WindowType.DIALOG
        window.layout_file = "dialog_layout.xml"

        # Get string representation
        str_rep = str(window)

        # Verify string contains important information
        assert "Window=" in str_rep
        assert "id=test_id" in str_rep
        assert "name=com.example.TestActivity" in str_rep
        assert "type=WindowType.DIALOG" in str_rep
        assert "layout_file=dialog_layout.xml" in str_rep

    def test_repr_representation(self, window):
        """Test repr representation."""
        repr_value = repr(window)
        assert repr_value == "com.example.TestActivity"


class TestWindows(ModelTestBase):
    """
    Unit tests for the Windows class.

    Tests cover window and widget management across multiple windows.
    """

    @pytest.fixture
    def windows(self):
        """Create a Windows container for testing."""
        return Windows()

    @pytest.fixture
    def window(self):
        """Create a standard window for testing."""
        return Window("com.example.TestActivity")

    @pytest.fixture
    def window2(self):
        """Create a second window for testing."""
        return Window("com.example.SecondActivity")

    @pytest.fixture
    def widget(self):
        """Create a standard widget for testing."""
        return Widget("widget1", "Button1", WidgetType.BUTTON)

    def test_initialization(self, windows):
        """Test that Windows initializes with empty collections."""
        assert len(windows.windows) == 0
        assert len(windows.widgets) == 0

    def test_add_window(self, windows, window):
        """Test adding a window."""
        # Add window successfully
        result = windows.add_window(window)
        assert result is True
        assert window in windows.windows
        assert len(windows.windows) == 1

        # Try to add the same window again
        result = windows.add_window(window)
        assert result is False  # Already exists
        assert len(windows.windows) == 1

    def test_create_new_window(self, windows):
        """Test creating and adding a new window."""
        # Create window with just the name
        window = windows.create_new_window("com.example.NewActivity")
        assert window.name == "com.example.NewActivity"
        assert window.id == ""
        assert window.type == WindowType.ACTIVITY
        assert window in windows.windows

        # Create window with name and ID
        window_with_id = windows.create_new_window(
            "com.example.AnotherActivity", "activity_id"
        )
        assert window_with_id.name == "com.example.AnotherActivity"
        assert window_with_id.id == "activity_id"
        assert window_with_id in windows.windows

        # Test special case for Menu
        menu_window = windows.create_new_window("android.view.Menu")
        assert menu_window.type == WindowType.OPTIONSMENU

    def test_update_widgets_of_window(self, windows, window, widget):
        """Test updating global widgets when adding windows with widgets."""
        # Add widget to window
        window.add_widget(widget)

        # Add window to windows container
        windows.add_window(window)

        # Widget should be in global widgets dictionary
        assert widget.id in windows.widgets
        assert windows.widgets[widget.id] == widget

    def test_get_window_by_id(self, windows, window):
        """Test retrieving windows by ID."""
        # Set window ID and add to windows
        window.id = "test_id"
        windows.add_window(window)

        # Get by ID
        retrieved = windows.get_window_by_id("test_id")
        assert retrieved is not None
        assert retrieved == window

        # Try to get non-existent window
        assert windows.get_window_by_id("non-existent-id") is None

    def test_get_window(self, windows, window):
        """Test retrieving windows by name."""
        # Add window
        windows.add_window(window)

        # Get by name
        retrieved = windows.get_window("com.example.TestActivity")
        assert retrieved is not None
        assert retrieved == window

        # Try to get non-existent window
        assert windows.get_window("com.example.NonExistentActivity") is None

    def test_add_widget(self, windows, window, widget):
        """Test adding a widget to a window through Windows class."""
        # Add window first
        windows.add_window(window)

        # Add widget to window
        result = windows.add_widget(window, widget)
        assert result is True

        # Widget should be in both window and global widgets
        assert str(widget.id) in window.widgets
        assert widget.id in windows.widgets

        # Try to add the same widget again
        result = windows.add_widget(window, widget)
        assert result is False  # Already exists

    def test_get_widget(self, windows, window, widget):
        """Test retrieving widgets from global widget dictionary."""
        # Add window with widget
        window.add_widget(widget)
        windows.add_window(window)

        # Get widget
        retrieved = windows.get_widget(widget.id)
        assert retrieved is not None
        assert retrieved == widget

        # Try to get non-existent widget
        assert windows.get_widget("non-existent-id") is None

    def test_to_json(self, windows, window, window2, widget):
        """Test conversion to JSON format."""
        # Add widgets and windows
        window.add_widget(widget)
        windows.add_window(window)
        windows.add_window(window2)

        # Convert to JSON
        json_data = windows.to_json()

        # Verify JSON structure
        assert "windows" in json_data
        assert len(json_data["windows"]) == 2

        # Verify windows are included
        window_names = [w["name"] for w in json_data["windows"]]
        assert "com.example.TestActivity" in window_names
        assert "com.example.SecondActivity" in window_names

        # Find the first window and verify its widgets
        first_window = next(
            w for w in json_data["windows"] if w["name"] == "com.example.TestActivity"
        )
        assert len(first_window["widgets"]) == 1
        assert first_window["widgets"][0] == widget.to_json()
