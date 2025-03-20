import pytest

from rvandroid.model.widget import Widget, WidgetType
from rvandroid.model.window import Window, Windows, WindowType


class TestWindowType:
    """Tests for the WindowType enum"""

    def test_window_type_values(self):
        """Test WindowType enum values"""
        assert WindowType.ACTIVITY.value == 1
        assert WindowType.OPTIONSMENU.value == 2
        assert WindowType.CONTEXTMENU.value == 3
        assert WindowType.DIALOG.value == 4
        assert WindowType.FRAGMENT.value == 5

    def test_from_string(self):
        """Test from_string method"""
        assert WindowType.from_string("ACT") == WindowType.ACTIVITY
        assert WindowType.from_string("OPTIONS_MENU") == WindowType.OPTIONSMENU
        assert WindowType.from_string("CONTEXT_MENU") == WindowType.CONTEXTMENU
        assert WindowType.from_string("DIALOG") == WindowType.DIALOG
        assert WindowType.from_string("FRAGMENT") == WindowType.FRAGMENT
        assert WindowType.from_string("UNKNOWN") is None


class TestWindow:
    """Tests for the Window class"""

    @pytest.fixture
    def sample_window(self):
        """Create a sample window for testing"""
        return Window("MainActivity")

    @pytest.fixture
    def sample_widget(self):
        """Create a sample widget for testing"""
        return Widget("button1", "login_button", WidgetType.BUTTON)

    def test_window_initialization(self, sample_window):
        """Test Window constructor"""
        assert sample_window.id == ""
        assert sample_window.name == "MainActivity"
        assert sample_window.type == WindowType.ACTIVITY
        assert sample_window.layout_file == ""
        assert sample_window.widgets == {}
        assert sample_window.fields == set()

    def test_add_widget(self, sample_window, sample_widget):
        """Test adding a widget to a window"""
        # First add should succeed
        result = sample_window.add_widget(sample_widget)
        assert result is True
        assert "button1" in sample_window.widgets
        assert sample_window.widgets["button1"] == sample_widget

        # Second add should fail (duplicate)
        result = sample_window.add_widget(sample_widget)
        assert result is False

    def test_get_widget(self, sample_window, sample_widget):
        """Test getting a widget by ID"""
        sample_window.add_widget(sample_widget)

        # Get existing widget
        widget = sample_window.get_widget("button1")
        assert widget == sample_widget

        # Get non-existent widget
        widget = sample_window.get_widget("nonexistent")
        assert widget is None

    def test_get_widget_by_name(self, sample_window, sample_widget):
        """Test getting a widget by name"""
        sample_window.add_widget(sample_widget)

        # Get existing widget
        widget = sample_window.get_widget_by_name("login_button")
        assert widget == sample_widget

        # Get non-existent widget
        widget = sample_window.get_widget_by_name("nonexistent")
        assert widget is None

    def test_to_json(self, sample_window, sample_widget):
        """Test to_json method"""
        sample_window.id = "main_activity"
        sample_window.add_widget(sample_widget)
        sample_window.fields.add("user_data")

        json_data = sample_window.to_json()
        assert json_data["id"] == "main_activity"
        assert json_data["name"] == "MainActivity"
        assert json_data["type"] == "ACTIVITY"
        assert len(json_data["widgets"]) == 1
        assert "user_data" in json_data["fields"]

    def test_string_representation(self, sample_window):
        """Test __str__ method"""
        sample_window.id = "main_activity"
        string_repr = str(sample_window)

        assert "Window=" in string_repr
        assert "id=main_activity" in string_repr
        assert "name=MainActivity" in string_repr

    def test_repr(self, sample_window):
        """Test __repr__ method"""
        assert repr(sample_window) == "MainActivity"


class TestWindows:
    """Tests for the Windows class"""

    @pytest.fixture
    def windows_manager(self):
        """Create a Windows manager for testing"""
        return Windows()

    @pytest.fixture
    def sample_window(self):
        """Create a sample window for testing"""
        window = Window("MainActivity")
        window.id = "main_activity"
        return window

    @pytest.fixture
    def sample_widget(self):
        """Create a sample widget for testing"""
        return Widget("button1", "login_button", WidgetType.BUTTON)

    def test_add_window(self, windows_manager, sample_window):
        """Test adding a window"""
        # First add should succeed
        result = windows_manager.add_window(sample_window)
        assert result is True
        assert sample_window in windows_manager.windows

        # Second add should fail (duplicate)
        result = windows_manager.add_window(sample_window)
        assert result is False

    def test_create_new_window(self, windows_manager):
        """Test creating a new window"""
        # Create regular window
        window = windows_manager.create_new_window("SettingsActivity", "settings")
        assert window.name == "SettingsActivity"
        assert window.id == "settings"
        assert window.type == WindowType.ACTIVITY
        assert window in windows_manager.windows

        # Create menu window
        menu_window = windows_manager.create_new_window("android.view.Menu")
        assert menu_window.type == WindowType.OPTIONSMENU

    def test_get_window_by_id(self, windows_manager, sample_window):
        """Test getting a window by ID"""
        windows_manager.add_window(sample_window)

        # Get existing window
        window = windows_manager.get_window_by_id("main_activity")
        assert window == sample_window

        # Get non-existent window
        window = windows_manager.get_window_by_id("nonexistent")
        assert window is None

    def test_get_window(self, windows_manager, sample_window):
        """Test getting a window by name"""
        windows_manager.add_window(sample_window)

        # Get existing window
        window = windows_manager.get_window("MainActivity")
        assert window == sample_window

        # Get non-existent window
        window = windows_manager.get_window("NonExistentActivity")
        assert window is None

    def test_add_widget(self, windows_manager, sample_window, sample_widget):
        """Test adding a widget to a window"""
        windows_manager.add_window(sample_window)

        # Add widget
        result = windows_manager.add_widget(sample_window, sample_widget)
        assert result is True
        assert sample_widget.id in windows_manager.widgets
        assert windows_manager.widgets[sample_widget.id] == sample_widget

        # Adding the same widget should fail
        result = windows_manager.add_widget(sample_window, sample_widget)
        assert result is False

    def test_get_widget(self, windows_manager, sample_window, sample_widget):
        """Test getting a widget"""
        windows_manager.add_window(sample_window)
        windows_manager.add_widget(sample_window, sample_widget)

        # Get existing widget
        widget = windows_manager.get_widget("button1")
        assert widget == sample_widget

        # Get non-existent widget
        widget = windows_manager.get_widget("nonexistent")
        assert widget is None

    def test_to_json(self, windows_manager, sample_window):
        """Test to_json method"""
        windows_manager.add_window(sample_window)

        json_data = windows_manager.to_json()
        assert "windows" in json_data
        assert len(json_data["windows"]) == 1
       