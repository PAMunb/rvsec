"""
Unit tests for the ToolSpec class and related enums.

This module contains comprehensive tests for the ToolSpec class that provides
tool specification and metadata management for monitored operations testing tools.
"""

import pytest

from rv_android_core.tools.tool_spec import ToolSpec


class TestToolSpecInitialization:
    """Tests for ToolSpec initialization and validation."""

    def test_init_with_required_fields(self):
        """Test ToolSpec initialization with required fields only."""
        # Arrange & Act
        spec = ToolSpec(
            name="test_tool",
            description="Test tool description",
            url="http://github.com/test/tool",
            version="1.0.0"
        )

        # Assert
        assert spec.name == "test_tool"
        assert spec.description == "Test tool description"
        assert spec.url == "http://github.com/test/tool"
        assert spec.version == "1.0.0"
        assert spec.process_pattern is None

    def test_init_with_all_fields(self):
        """Test ToolSpec initialization with all fields."""
        # Arrange & Act
        spec = ToolSpec(
            name="comprehensive_tool",
            description="Comprehensive test tool",
            version="2.1.0",
            url="http://github.com/test/tool",
            process_pattern="com.comprehensive.tool"
        )

        # Assert
        assert spec.name == "comprehensive_tool"
        assert spec.description == "Comprehensive test tool"
        assert spec.version == "2.1.0"
        assert spec.url == "http://github.com/test/tool"
        assert spec.process_pattern == "com.comprehensive.tool"

    def test_init_positional_arguments(self):
        """Test ToolSpec initialization using positional arguments (validated_model)."""
        # Act
        spec = ToolSpec(
            "positional_tool",
            "Tool with positional args",
            "http://github.com/test/tool",
            "1.5.0"
        )

        # Assert
        assert spec.name == "positional_tool"
        assert spec.description == "Tool with positional args"
        assert spec.version == "1.5.0"
        assert spec.url == "http://github.com/test/tool"

    def test_init_mixed_positional_and_named(self):
        """Test ToolSpec initialization with mixed positional and named arguments."""
        # Act
        spec = ToolSpec(
            "mixed_tool",
            "Mixed args tool",
            "http://github.com/test/tool",
            version="3.0.0"
        )

        # Assert
        assert spec.name == "mixed_tool"
        assert spec.description == "Mixed args tool"
        assert spec.url == "http://github.com/test/tool"
        assert spec.version == "3.0.0"


class TestToolSpecFactoryMethods:
    """Tests for ToolSpec factory methods."""

    def test_create_builtin_spec_minimal(self):
        """Test creating builtin spec with minimal parameters."""
        # Act
        spec = ToolSpec.create_builtin_spec(
            name="monkey",
            description="Android Monkey testing tool",
            url="https://github.com/android/platform/frameworks/base/cmds/monkey"
        )

        # Assert
        assert spec.name == "monkey"
        assert spec.description == "Android Monkey testing tool"
        assert spec.url == "https://github.com/android/platform/frameworks/base/cmds/monkey"
        assert spec.version == "1.0.0"  # Default version
        assert spec.process_pattern is None

    def test_create_builtin_spec_full(self):
        """Test creating builtin spec with all parameters."""
        # Act
        spec = ToolSpec.create_builtin_spec(
            name="droidbot",
            description="Model-based Android testing tool",
            url="https://github.com/honeynet/droidbot",
            version="2.0.0",
            process_pattern="com.droidbot"
        )

        # Assert
        assert spec.name == "droidbot"
        assert spec.description == "Model-based Android testing tool"
        assert spec.version == "2.0.0"
        assert spec.url == "https://github.com/honeynet/droidbot"
        assert spec.process_pattern == "com.droidbot"

    def test_create_external_spec_minimal(self):
        """Test creating external spec with minimal parameters."""
        # Act
        spec = ToolSpec.create_external_spec(
            name="appium",
            description="Cross-platform mobile testing framework",
            url="https://github.com/appium/appium",
            version="1.0.0"
        )

        # Assert
        assert spec.name == "appium"
        assert spec.description == "Cross-platform mobile testing framework"
        assert spec.version == "1.0.0"  # Default version
        assert spec.url == "https://github.com/appium/appium"
        assert spec.process_pattern is None

    def test_create_external_spec_full(self):
        """Test creating external spec with all parameters."""
        # Act
        spec = ToolSpec.create_external_spec(
            name="maestro",
            description="Mobile UI testing framework",
            url="https://github.com/mobile-dev-tools/maestro",
            version="1.5.0",
            process_pattern="com.maestro"
        )

        # Assert
        assert spec.name == "maestro"
        assert spec.description == "Mobile UI testing framework"
        assert spec.version == "1.5.0"
        assert spec.url == "https://github.com/mobile-dev-tools/maestro"
        assert spec.process_pattern == "com.maestro"


class TestToolSpecSerialization:
    """Tests for ToolSpec serialization and deserialization methods."""

    @pytest.fixture
    def complete_spec(self):
        """Fixture providing a complete ToolSpec for serialization tests."""
        return ToolSpec(
            name="serialization_tool",
            description="Tool for testing serialization",
            version="1.2.3",
            url="http://github.com/test/serialization",
            process_pattern="com.serialization.tool"
        )

    @pytest.fixture
    def minimal_spec(self):
        """Fixture providing a minimal ToolSpec for serialization tests."""
        return ToolSpec(
            name="minimal_tool",
            description="Minimal tool",
            version="1.0.0",
            url="http://github.com/test/minimal"
        )

    def test_to_dict_complete_spec(self, complete_spec):
        """Test to_dict with complete specification."""
        # Act
        result = complete_spec.to_dict()

        # Assert
        expected = {
            "name": "serialization_tool",
            "description": "Tool for testing serialization",
            "version": "1.2.3",
            "url": "http://github.com/test/serialization",
            "process_pattern": "com.serialization.tool"
        }
        assert result == expected

    def test_to_dict_minimal_spec(self, minimal_spec):
        """Test to_dict with minimal specification."""
        # Act
        result = minimal_spec.to_dict()

        # Assert
        expected = {
            "name": "minimal_tool",
            "description": "Minimal tool",
            "version": "1.0.0",
            "url": "http://github.com/test/minimal",
            "process_pattern": None
        }
        assert result == expected

    def test_from_dict_complete_spec(self):
        """Test from_dict with complete specification data."""
        # Arrange
        data = {
            "name": "from_dict_tool",
            "description": "Tool created from dict",
            "version": "2.0.0",
            "url": "http://github.com/test/from_dict",
            "process_pattern": "com.from.dict"
        }

        # Act
        spec = ToolSpec.from_dict(data)

        # Assert
        assert spec.name == "from_dict_tool"
        assert spec.description == "Tool created from dict"
        assert spec.version == "2.0.0"
        assert spec.url == "http://github.com/test/from_dict"
        assert spec.process_pattern == "com.from.dict"

    def test_serialization_roundtrip(self, complete_spec):
        """Test that serialization and deserialization preserve data."""
        # Act
        dict_data = complete_spec.to_dict()
        restored_spec = ToolSpec.from_dict(dict_data)

        # Assert
        assert restored_spec.name == complete_spec.name
        assert restored_spec.description == complete_spec.description
        assert restored_spec.version == complete_spec.version
        assert restored_spec.url == complete_spec.url
        assert restored_spec.process_pattern == complete_spec.process_pattern
