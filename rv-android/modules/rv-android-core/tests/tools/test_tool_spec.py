"""
Unit tests for the ToolSpec class and related enums.

This module contains comprehensive tests for the ToolSpec class that provides
tool specification and metadata management for monitored operations testing tools.
"""

import pytest
from typing import Dict, List, Any

from rv_android_core.tools.tool_spec import (
    ToolSpec,
    ToolType,
    ToolCategory
)


class TestToolTypeEnum:
    """Tests for the ToolType enumeration."""

    def test_tool_type_values(self):
        """Test that ToolType enum has expected values."""
        # Assert
        assert ToolType.BUILTIN.value == "builtin"
        assert ToolType.EXTERNAL.value == "external"
        assert ToolType.PLUGIN.value == "plugin"
        assert ToolType.GUI_TESTING.value == "gui_testing"
        assert ToolType.MACHINE_LEARNING.value == "machine_learning"

    def test_tool_type_membership(self):
        """Test ToolType enum membership."""
        # Assert
        assert "builtin" in [t.value for t in ToolType]
        assert "external" in [t.value for t in ToolType]
        assert "plugin" in [t.value for t in ToolType]
        assert "gui_testing" in [t.value for t in ToolType]
        assert "machine_learning" in [t.value for t in ToolType]

    def test_tool_type_count(self):
        """Test expected number of ToolType values."""
        # Assert
        assert len(ToolType) == 5


class TestToolCategoryEnum:
    """Tests for the ToolCategory enumeration."""

    def test_tool_category_values(self):
        """Test that ToolCategory enum has expected values."""
        # Assert
        assert ToolCategory.RANDOM_TESTING.value == "random_testing"
        assert ToolCategory.MODEL_BASED.value == "model_based"
        assert ToolCategory.AI_GUIDED.value == "ai_guided"
        assert ToolCategory.SYSTEMATIC.value == "systematic"
        assert ToolCategory.HYBRID.value == "hybrid"

    def test_tool_category_membership(self):
        """Test ToolCategory enum membership."""
        # Assert
        assert "random_testing" in [c.value for c in ToolCategory]
        assert "model_based" in [c.value for c in ToolCategory]
        assert "ai_guided" in [c.value for c in ToolCategory]
        assert "systematic" in [c.value for c in ToolCategory]
        assert "hybrid" in [c.value for c in ToolCategory]

    def test_tool_category_count(self):
        """Test expected number of ToolCategory values."""
        # Assert
        assert len(ToolCategory) == 5


class TestToolSpecInitialization:
    """Tests for ToolSpec initialization and validation."""

    def test_init_with_required_fields(self):
        """Test ToolSpec initialization with required fields only."""
        # Arrange & Act
        spec = ToolSpec(
            name="test_tool",
            description="Test tool description",
            version="1.0.0",
            tool_type=ToolType.BUILTIN,
            category=ToolCategory.RANDOM_TESTING
        )

        # Assert
        assert spec.name == "test_tool"
        assert spec.description == "Test tool description"
        assert spec.version == "1.0.0"
        assert spec.tool_type == ToolType.BUILTIN
        assert spec.category == ToolCategory.RANDOM_TESTING
        assert spec.process_pattern is None
        assert spec.dependencies == []
        assert spec.capabilities == []
        assert spec.configuration_schema == {}
        assert spec.author is None

    def test_init_with_all_fields(self):
        """Test ToolSpec initialization with all fields."""
        # Arrange & Act
        spec = ToolSpec(
            name="comprehensive_tool",
            description="Comprehensive test tool",
            version="2.1.0",
            tool_type=ToolType.EXTERNAL,
            category=ToolCategory.AI_GUIDED,
            process_pattern="com.comprehensive.tool",
            dependencies=["adb", "python"],
            capabilities=["ui_testing", "performance_analysis"],
            configuration_schema={"timeout": {"type": "integer", "default": 60}},
            author="Test Author"
        )

        # Assert
        assert spec.name == "comprehensive_tool"
        assert spec.description == "Comprehensive test tool"
        assert spec.version == "2.1.0"
        assert spec.tool_type == ToolType.EXTERNAL
        assert spec.category == ToolCategory.AI_GUIDED
        assert spec.process_pattern == "com.comprehensive.tool"
        assert spec.dependencies == ["adb", "python"]
        assert spec.capabilities == ["ui_testing", "performance_analysis"]
        assert spec.configuration_schema == {"timeout": {"type": "integer", "default": 60}}
        assert spec.author == "Test Author"

    def test_init_positional_arguments(self):
        """Test ToolSpec initialization using positional arguments (validated_model)."""
        # Act
        spec = ToolSpec(
            "positional_tool",
            "Tool with positional args",
            "1.5.0",
            ToolType.PLUGIN,
            ToolCategory.MODEL_BASED
        )

        # Assert
        assert spec.name == "positional_tool"
        assert spec.description == "Tool with positional args"
        assert spec.version == "1.5.0"
        assert spec.tool_type == ToolType.PLUGIN
        assert spec.category == ToolCategory.MODEL_BASED

    def test_init_mixed_positional_and_named(self):
        """Test ToolSpec initialization with mixed positional and named arguments."""
        # Act
        spec = ToolSpec(
            "mixed_tool",
            "Mixed args tool",
            "3.0.0",
            tool_type=ToolType.GUI_TESTING,
            category=ToolCategory.SYSTEMATIC,
            author="Mixed Author"
        )

        # Assert
        assert spec.name == "mixed_tool"
        assert spec.description == "Mixed args tool"
        assert spec.version == "3.0.0"
        assert spec.tool_type == ToolType.GUI_TESTING
        assert spec.category == ToolCategory.SYSTEMATIC
        assert spec.author == "Mixed Author"

    def test_init_with_empty_lists(self):
        """Test ToolSpec initialization with explicitly empty lists."""
        # Act
        spec = ToolSpec(
            name="empty_lists_tool",
            description="Tool with empty lists",
            version="1.0.0",
            tool_type=ToolType.BUILTIN,
            category=ToolCategory.RANDOM_TESTING,
            dependencies=[],
            capabilities=[]
        )

        # Assert
        assert spec.dependencies == []
        assert spec.capabilities == []


class TestToolSpecFactoryMethods:
    """Tests for ToolSpec factory methods."""

    def test_create_builtin_spec_minimal(self):
        """Test creating builtin spec with minimal parameters."""
        # Act
        spec = ToolSpec.create_builtin_spec(
            name="monkey",
            description="Android Monkey testing tool",
            category=ToolCategory.RANDOM_TESTING
        )

        # Assert
        assert spec.name == "monkey"
        assert spec.description == "Android Monkey testing tool"
        assert spec.version == "1.0.0"  # Default version
        assert spec.tool_type == ToolType.BUILTIN
        assert spec.category == ToolCategory.RANDOM_TESTING
        assert spec.process_pattern is None
        assert spec.capabilities == []

    def test_create_builtin_spec_full(self):
        """Test creating builtin spec with all parameters."""
        # Act
        spec = ToolSpec.create_builtin_spec(
            name="droidbot",
            description="Model-based Android testing tool",
            category=ToolCategory.MODEL_BASED,
            version="2.0.0",
            process_pattern="com.droidbot",
            capabilities=["model_based_testing", "ui_exploration"]
        )

        # Assert
        assert spec.name == "droidbot"
        assert spec.description == "Model-based Android testing tool"
        assert spec.version == "2.0.0"
        assert spec.tool_type == ToolType.BUILTIN
        assert spec.category == ToolCategory.MODEL_BASED
        assert spec.process_pattern == "com.droidbot"
        assert spec.capabilities == ["model_based_testing", "ui_exploration"]

    def test_create_external_spec_minimal(self):
        """Test creating external spec with minimal parameters."""
        # Act
        spec = ToolSpec.create_external_spec(
            name="appium",
            description="Cross-platform mobile testing framework",
            category=ToolCategory.SYSTEMATIC,
            dependencies=["node", "npm", "appium"]
        )

        # Assert
        assert spec.name == "appium"
        assert spec.description == "Cross-platform mobile testing framework"
        assert spec.version == "1.0.0"  # Default version
        assert spec.tool_type == ToolType.EXTERNAL
        assert spec.category == ToolCategory.SYSTEMATIC
        assert spec.dependencies == ["node", "npm", "appium"]
        assert spec.process_pattern is None
        assert spec.capabilities == []
        assert spec.author is None

    def test_create_external_spec_full(self):
        """Test creating external spec with all parameters."""
        # Act
        spec = ToolSpec.create_external_spec(
            name="maestro",
            description="Mobile UI testing framework",
            category=ToolCategory.SYSTEMATIC,
            dependencies=["java", "maestro-cli"],
            version="1.5.0",
            process_pattern="com.maestro",
            capabilities=["flow_testing", "ui_automation"],
            author="Mobile Dev Tools"
        )

        # Assert
        assert spec.name == "maestro"
        assert spec.description == "Mobile UI testing framework"
        assert spec.version == "1.5.0"
        assert spec.tool_type == ToolType.EXTERNAL
        assert spec.category == ToolCategory.SYSTEMATIC
        assert spec.dependencies == ["java", "maestro-cli"]
        assert spec.process_pattern == "com.maestro"
        assert spec.capabilities == ["flow_testing", "ui_automation"]
        assert spec.author == "Mobile Dev Tools"


class TestToolSpecCapabilities:
    """Tests for ToolSpec capability management methods."""

    @pytest.fixture
    def spec_with_capabilities(self):
        """Fixture providing a ToolSpec with multiple capabilities."""
        return ToolSpec(
            name="multi_capability_tool",
            description="Tool with multiple capabilities",
            version="1.0.0",
            tool_type=ToolType.PLUGIN,
            category=ToolCategory.HYBRID,
            capabilities=["ui_testing", "performance_analysis", "security_testing", "accessibility_testing"]
        )

    @pytest.fixture
    def spec_without_capabilities(self):
        """Fixture providing a ToolSpec with no capabilities."""
        return ToolSpec(
            name="basic_tool",
            description="Basic tool without capabilities",
            version="1.0.0",
            tool_type=ToolType.BUILTIN,
            category=ToolCategory.RANDOM_TESTING
        )

    def test_has_capability_existing(self, spec_with_capabilities):
        """Test has_capability for existing capabilities."""
        # Act & Assert
        assert spec_with_capabilities.has_capability("ui_testing") is True
        assert spec_with_capabilities.has_capability("performance_analysis") is True
        assert spec_with_capabilities.has_capability("security_testing") is True
        assert spec_with_capabilities.has_capability("accessibility_testing") is True

    def test_has_capability_missing(self, spec_with_capabilities):
        """Test has_capability for non-existing capabilities."""
        # Act & Assert
        assert spec_with_capabilities.has_capability("missing_capability") is False
        assert spec_with_capabilities.has_capability("") is False
        assert spec_with_capabilities.has_capability("INVALID") is False

    def test_has_capability_no_capabilities(self, spec_without_capabilities):
        """Test has_capability when tool has no capabilities."""
        # Act & Assert
        assert spec_without_capabilities.has_capability("any_capability") is False
        assert spec_without_capabilities.has_capability("ui_testing") is False

    def test_is_compatible_with_all_requirements_met(self, spec_with_capabilities):
        """Test is_compatible_with when all requirements are met."""
        # Arrange
        requirements = ["ui_testing", "performance_analysis"]

        # Act
        result = spec_with_capabilities.is_compatible_with(requirements)

        # Assert
        assert result is True

    def test_is_compatible_with_partial_requirements_met(self, spec_with_capabilities):
        """Test is_compatible_with when only some requirements are met."""
        # Arrange
        requirements = ["ui_testing", "missing_capability"]

        # Act
        result = spec_with_capabilities.is_compatible_with(requirements)

        # Assert
        assert result is False

    def test_is_compatible_with_no_requirements_met(self, spec_with_capabilities):
        """Test is_compatible_with when no requirements are met."""
        # Arrange
        requirements = ["missing_capability", "another_missing"]

        # Act
        result = spec_with_capabilities.is_compatible_with(requirements)

        # Assert
        assert result is False

    def test_is_compatible_with_empty_requirements(self, spec_with_capabilities):
        """Test is_compatible_with with empty requirements list."""
        # Arrange
        requirements = []

        # Act
        result = spec_with_capabilities.is_compatible_with(requirements)

        # Assert
        assert result is True  # Empty requirements should always be satisfied

    def test_is_compatible_with_no_capabilities(self, spec_without_capabilities):
        """Test is_compatible_with when tool has no capabilities."""
        # Arrange
        requirements = ["ui_testing"]

        # Act
        result = spec_without_capabilities.is_compatible_with(requirements)

        # Assert
        assert result is False

    def test_is_compatible_with_single_requirement(self, spec_with_capabilities):
        """Test is_compatible_with with single requirement."""
        # Act & Assert
        assert spec_with_capabilities.is_compatible_with(["ui_testing"]) is True
        assert spec_with_capabilities.is_compatible_with(["missing_capability"]) is False


class TestToolSpecSerialization:
    """Tests for ToolSpec serialization and deserialization methods."""

    @pytest.fixture
    def complete_spec(self):
        """Fixture providing a complete ToolSpec for serialization tests."""
        return ToolSpec(
            name="serialization_tool",
            description="Tool for testing serialization",
            version="1.2.3",
            tool_type=ToolType.EXTERNAL,
            category=ToolCategory.AI_GUIDED,
            process_pattern="com.serialization.tool",
            dependencies=["python", "tensorflow"],
            capabilities=["ml_testing", "data_analysis"],
            configuration_schema={
                "model_path": {"type": "string", "required": True},
                "batch_size": {"type": "integer", "default": 32}
            },
            author="Serialization Tester"
        )

    @pytest.fixture
    def minimal_spec(self):
        """Fixture providing a minimal ToolSpec for serialization tests."""
        return ToolSpec(
            name="minimal_tool",
            description="Minimal tool",
            version="1.0.0",
            tool_type=ToolType.BUILTIN,
            category=ToolCategory.RANDOM_TESTING
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
            "tool_type": "external",
            "category": "ai_guided",
            "process_pattern": "com.serialization.tool",
            "dependencies": ["python", "tensorflow"],
            "capabilities": ["ml_testing", "data_analysis"],
            "configuration_schema": {
                "model_path": {"type": "string", "required": True},
                "batch_size": {"type": "integer", "default": 32}
            },
            "author": "Serialization Tester"
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
            "tool_type": "builtin",
            "category": "random_testing",
            "process_pattern": None,
            "dependencies": [],
            "capabilities": [],
            "configuration_schema": {},
            "author": None
        }
        assert result == expected

    def test_from_dict_complete_spec(self):
        """Test from_dict with complete specification data."""
        # Arrange
        data = {
            "name": "from_dict_tool",
            "description": "Tool created from dict",
            "version": "2.0.0",
            "tool_type": "plugin",
            "category": "model_based",
            "process_pattern": "com.from.dict",
            "dependencies": ["java", "gradle"],
            "capabilities": ["integration_testing", "unit_testing"],
            "configuration_schema": {"timeout": {"type": "integer"}},
            "author": "Dict Creator"
        }

        # Act
        spec = ToolSpec.from_dict(data)

        # Assert
        assert spec.name == "from_dict_tool"
        assert spec.description == "Tool created from dict"
        assert spec.version == "2.0.0"
        assert spec.tool_type == ToolType.PLUGIN
        assert spec.category == ToolCategory.MODEL_BASED
        assert spec.process_pattern == "com.from.dict"
        assert spec.dependencies == ["java", "gradle"]
        assert spec.capabilities == ["integration_testing", "unit_testing"]
        assert spec.configuration_schema == {"timeout": {"type": "integer"}}
        assert spec.author == "Dict Creator"

    def test_from_dict_minimal_spec(self):
        """Test from_dict with minimal specification data."""
        # Arrange
        data = {
            "name": "minimal_from_dict",
            "description": "Minimal from dict",
            "version": "1.0.0",
            "tool_type": "builtin",
            "category": "random_testing"
        }

        # Act
        spec = ToolSpec.from_dict(data)

        # Assert
        assert spec.name == "minimal_from_dict"
        assert spec.description == "Minimal from dict"
        assert spec.version == "1.0.0"
        assert spec.tool_type == ToolType.BUILTIN
        assert spec.category == ToolCategory.RANDOM_TESTING
        assert spec.process_pattern is None
        assert spec.dependencies == []
        assert spec.capabilities == []
        assert spec.configuration_schema == {}
        assert spec.author is None

    def test_serialization_roundtrip(self, complete_spec):
        """Test that serialization and deserialization preserve data."""
        # Act
        dict_data = complete_spec.to_dict()
        restored_spec = ToolSpec.from_dict(dict_data)

        # Assert
        assert restored_spec.name == complete_spec.name
        assert restored_spec.description == complete_spec.description
        assert restored_spec.version == complete_spec.version
        assert restored_spec.tool_type == complete_spec.tool_type
        assert restored_spec.category == complete_spec.category
        assert restored_spec.process_pattern == complete_spec.process_pattern
        assert restored_spec.dependencies == complete_spec.dependencies
        assert restored_spec.capabilities == complete_spec.capabilities
        assert restored_spec.configuration_schema == complete_spec.configuration_schema
        assert restored_spec.author == complete_spec.author

    def test_from_dict_missing_optional_fields(self):
        """Test from_dict handles missing optional fields gracefully."""
        # Arrange
        data = {
            "name": "missing_optionals",
            "description": "Tool with missing optionals",
            "version": "1.0.0",
            "tool_type": "external",
            "category": "systematic"
            # Missing optional fields: process_pattern, dependencies, capabilities, etc.
        }

        # Act
        spec = ToolSpec.from_dict(data)

        # Assert
        assert spec.name == "missing_optionals"
        assert spec.process_pattern is None
        assert spec.dependencies == []
        assert spec.capabilities == []
        assert spec.configuration_schema == {}
        assert spec.author is None
