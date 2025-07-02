import pytest
import re  # Import regex module
from unittest.mock import Mock, MagicMock, patch
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Type, Optional

# Importar as classes reais a serem testadas/mockadas
from rv_tools.interfaces.plugin_interface import ToolPlugin
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.exceptions import ToolRegistrationError, PluginError
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT


# --- Fixtures Reutilizáveis ---

@pytest.fixture(autouse=True)
def reset_singletons():
    """Resets singleton instances before each test."""
    try:
        from rv_tools.registry.registry import ToolRegistry
        ToolRegistry.reset_instance()
    except (ImportError, AttributeError):
        pass  # Ignore if not present or not a singleton


@pytest.fixture
def mock_logging_manager_instance():
    """Provides a mock for LoggingManager.get_instance() return value."""
    mock_manager_instance = MagicMock(autospec=True)
    mock_manager_instance.get_logger.return_value = MagicMock(
        spec_set=['info', 'debug', 'error', 'warning', 'critical'])
    return mock_manager_instance


@pytest.fixture
def mock_error_handler_instance():
    """Provides a mock for ErrorHandler.get_instance() return value."""
    mock_handler_instance = MagicMock(autospec=True)

    # Configure handle_error to re-raise the exception for easier testing with pytest.raises
    def mock_handle_error_side_effect(e, context):
        raise e

    mock_handler_instance.handle_error.side_effect = mock_handle_error_side_effect
    mock_handler_instance.error_context = MagicMock()
    return mock_handler_instance


@pytest.fixture
def mock_tool_registry():
    """Provides a mock ToolRegistry instance."""
    mock_registry = MagicMock(autospec=True)
    mock_registry.register_tool = Mock()
    mock_registry.register_variant = Mock()
    mock_registry.has_tool.return_value = True
    return mock_registry


# --- Implementação Mínima Concreta de ToolPlugin para Teste ---
class ConcreteToolPlugin(ToolPlugin):
    """A minimal concrete implementation of ToolPlugin for testing abstract methods."""

    def __init__(self, name="concrete_plugin", version="0.1.0", description="Test plugin",
                 tool_names_list: List[str] = None,
                 tool_class_map: Dict[str, Type[AbstractTool]] = None,
                 tool_spec_map: Dict[str, ToolSpec] = None,
                 tool_variants_map: Dict[str, List[str]] = None,
                 variant_config_map: Dict[str, Dict[str, Any]] = None):

        self._name = name
        self._version = version
        self._description = description
        self._tool_names_list = tool_names_list if tool_names_list is not None else ["mock_tool"]
        self._tool_class_map = tool_class_map if tool_class_map is not None else {
            "mock_tool": MagicMock(spec=AbstractTool)}
        self._tool_spec_map = tool_spec_map if tool_spec_map is not None else {
            "mock_tool": ToolSpec(name="mock_tool", description="A mock tool", url="http://mock.com", version="1.0.0")}
        self._tool_variants_map = tool_variants_map if tool_variants_map is not None else {}
        self._variant_config_map = variant_config_map if variant_config_map is not None else {}

        super().__init__()  # Now safe to call parent's init

    def get_plugin_name(self) -> str:
        return self._name

    def get_plugin_version(self) -> str:
        return self._version

    def get_plugin_description(self) -> str:
        return self._description

    def get_tool_names(self) -> List[str]:
        return self._tool_names_list

    def get_tool_class(self, tool_name: str) -> Type[AbstractTool]:
        if tool_name not in self._tool_class_map:
            raise ToolRegistrationError(f"Tool class {tool_name} not found in plugin.")
        return self._tool_class_map[tool_name]

    def get_tool_spec(self, tool_name: str) -> ToolSpec:
        if tool_name not in self._tool_spec_map:
            raise ToolRegistrationError(f"Tool spec {tool_name} not found in plugin.")
        return self._tool_spec_map[tool_name]

    def get_tool_variants(self, tool_name: str) -> List[str]:
        return self._tool_variants_map.get(tool_name, [])

    def get_variant_config(self, tool_name: str, variant_name: str) -> Dict[str, Any]:
        return self._variant_config_map.get(f"{tool_name}:{variant_name}", {})


# --- Testes para plugin_interface.py ---

class TestToolPluginInterface:

    @pytest.fixture(autouse=True)
    def setup_mocks_for_interface_test(self, mock_logging_manager_instance, mock_error_handler_instance):
        """Patch singletons for all tests in this class."""
        with patch('rv_android_core.util.logging.manager.LoggingManager.get_instance',
                   return_value=mock_logging_manager_instance), \
                patch('rv_android_core.util.error.error_handler.ErrorHandler.get_instance',
                      return_value=mock_error_handler_instance):
            yield

    @pytest.mark.unit
    def test_initialization(self, mock_logging_manager_instance, mock_error_handler_instance):
        """Test the __init__ method of the abstract class via a concrete implementation."""
        plugin = ConcreteToolPlugin()

        assert hasattr(plugin, 'logger')
        assert hasattr(plugin, 'error_handler')
        assert plugin.logger is mock_logging_manager_instance.get_logger.return_value
        assert plugin.error_handler is mock_error_handler_instance

        mock_logging_manager_instance.get_logger.assert_called_once_with(
            "rv_tools.plugin.concrete_plugin",
            {CONTEXT_COMPONENT: "ToolPlugin"}
        )

    @pytest.mark.unit
    def test_abstract_methods_raise_not_implemented_error(self):
        """Test that abstract methods raise NotImplementedError if not overridden."""
        mock_plugin = MagicMock(spec=ToolPlugin)

        mock_plugin.get_plugin_name.side_effect = NotImplementedError
        mock_plugin.get_plugin_version.side_effect = NotImplementedError
        mock_plugin.get_plugin_description.side_effect = NotImplementedError
        mock_plugin.get_tool_names.side_effect = NotImplementedError
        mock_plugin.get_tool_class.side_effect = NotImplementedError
        mock_plugin.get_tool_spec.side_effect = NotImplementedError

        with pytest.raises(NotImplementedError):
            mock_plugin.get_plugin_name()
        with pytest.raises(NotImplementedError):
            mock_plugin.get_tool_class("any_tool")
        with pytest.raises(NotImplementedError):
            mock_plugin.get_plugin_version()
        with pytest.raises(NotImplementedError):
            mock_plugin.get_plugin_description()
        with pytest.raises(NotImplementedError):
            mock_plugin.get_tool_names()
        with pytest.raises(NotImplementedError):
            mock_plugin.get_tool_spec("any_tool")

    @pytest.mark.unit
    def test_default_get_tool_variants(self):
        """Test the default implementation of get_tool_variants."""
        plugin = ConcreteToolPlugin(tool_names_list=["tool1"], tool_variants_map={})
        assert plugin.get_tool_variants("tool1") == []
        assert plugin.get_tool_variants("non_existent_tool") == []

    @pytest.mark.unit
    def test_default_get_variant_config(self):
        """Test the default implementation of get_variant_config."""
        plugin = ConcreteToolPlugin(tool_names_list=["tool1"], variant_config_map={})
        assert plugin.get_variant_config("tool1", "variantA") == {}
        assert plugin.get_variant_config("non_existent_tool", "variantB") == {}

    @pytest.mark.unit
    def test_get_plugin_metadata(self):
        """Test get_plugin_metadata returns correct dictionary."""
        plugin = ConcreteToolPlugin(name="test_plugin", version="1.2.3", description="My test plugin",
                                    tool_names_list=["t1", "t2"])
        metadata = plugin.get_plugin_metadata()
        assert metadata == {
            "name": "test_plugin",
            "version": "1.2.3",
            "description": "My test plugin",
            "tool_names": ["t1", "t2"],
            "plugin_type": "external_tool"
        }

    @pytest.mark.unit
    def test_str_and_repr(self):
        """Test __str__ and __repr__ methods."""
        plugin = ConcreteToolPlugin(name="my_plugin", version="1.0.0")
        assert str(plugin) == "ConcreteToolPlugin(name='my_plugin', version='1.0.0')"
        assert repr(plugin) == "ConcreteToolPlugin(name='my_plugin', version='1.0.0', tools=['mock_tool'])"

    @pytest.mark.unit
    # IMPORTANT: Patch the ErrorHandler.handle_errors decorator itself to prevent it from swallowing exceptions
    @patch('rv_android_core.util.error.error_handler.ErrorHandler.handle_errors',
           side_effect=lambda component, phase: (lambda f: f))
    def test_register_tools_happy_path(self, mock_handle_errors_decorator, mock_tool_registry,
                                       mock_logging_manager_instance):
        """Test successful registration of tools and variants."""
        mock_tool_class = MagicMock(spec=AbstractTool)
        mock_tool_spec = ToolSpec(name="test_tool", description="desc", url="url", version="1.0.0")

        plugin = ConcreteToolPlugin(
            tool_names_list=["test_tool"],
            tool_class_map={"test_tool": mock_tool_class},
            tool_spec_map={"test_tool": mock_tool_spec},
            tool_variants_map={"test_tool": ["fast", "thorough"]},
            variant_config_map={
                "test_tool:fast": {"timeout": 60},
                "test_tool:thorough": {"timeout": 1800, "depth": 10}
            }
        )

        plugin.register_tools(mock_tool_registry)

        mock_tool_registry.register_tool.assert_called_once_with("test_tool", mock_tool_class, mock_tool_spec)
        plugin.logger.info.assert_called_once_with("Registered tool: test_tool")

        mock_tool_registry.register_variant.assert_any_call("test_tool", "fast", {"timeout": 60})
        mock_tool_registry.register_variant.assert_any_call("test_tool", "thorough", {"timeout": 1800, "depth": 10})
        assert mock_tool_registry.register_variant.call_count == 2
        plugin.logger.debug.assert_any_call("Registered variant 'fast' for tool: test_tool")
        plugin.logger.debug.assert_any_call("Registered variant 'thorough' for tool: test_tool")

    @pytest.mark.unit
    @patch('rv_android_core.util.error.error_handler.ErrorHandler.handle_errors',
           side_effect=lambda component, phase: (lambda f: f))
    def test_register_tools_no_variants(self, mock_handle_errors_decorator, mock_tool_registry,
                                        mock_logging_manager_instance):
        """Test registration when no variants are available."""
        mock_tool_class = MagicMock(spec=AbstractTool)
        mock_tool_spec = ToolSpec(name="test_tool_no_variant", description="desc", url="url", version="1.0.0")

        plugin = ConcreteToolPlugin(
            tool_names_list=["test_tool_no_variant"],
            tool_class_map={"test_tool_no_variant": mock_tool_class},
            tool_spec_map={"test_tool_no_variant": mock_tool_spec},
            tool_variants_map={},  # No variants
            variant_config_map={}
        )

        plugin.register_tools(mock_tool_registry)

        mock_tool_registry.register_tool.assert_called_once_with("test_tool_no_variant", mock_tool_class,
                                                                 mock_tool_spec)
        plugin.logger.info.assert_called_once_with("Registered tool: test_tool_no_variant")
        mock_tool_registry.register_variant.assert_not_called()

    # @pytest.mark.unit
    # # IMPORTANT: Patch the ErrorHandler.handle_errors decorator to allow exceptions to pass through
    # @patch('rv_android_core.util.error.error_handler.ErrorHandler.handle_errors',
    #        side_effect=lambda component, phase: (lambda f: f))
    # def test_register_tools_get_tool_spec_fails(self, mock_handle_errors_decorator, mock_tool_registry,
    #                                             mock_error_handler_instance, mock_logging_manager_instance):
    #     """Test register_tools when get_tool_spec raises an error."""
    #     mock_tool_class = MagicMock(spec=AbstractTool)
    #
    #     plugin = ConcreteToolPlugin(
    #         tool_names_list=["failing_tool"],
    #         tool_class_map={"failing_tool": mock_tool_class},
    #         tool_spec_map={},  # This will cause get_tool_spec to fail by not having the key
    #     )
    #
    #     with pytest.raises(ToolRegistrationError) as excinfo:
    #         plugin.register_tools(mock_tool_registry)
    #
    #     # Verify the message using regex match for robustness
    #     # The message includes the original exception's string as well, like:
    #     # "Failed to register tools from plugin 'concrete_plugin': ToolRegistrationError: Tool spec failing_tool not found in plugin."
    #     expected_regex = r"Failed to register tools from plugin 'concrete_plugin': ToolRegistrationError: Tool spec failing_tool not found in plugin\."
    #     assert re.search(expected_regex, str(excinfo.value)) is not None
    #     mock_tool_registry.register_tool.assert_not_called()
    #     mock_tool_registry.register_variant.assert_not_called()
    #     mock_error_handler_instance.handle_error.assert_called_once()  # ErrorHandler should still be called via the decorator
    #     plugin.logger.info.assert_not_called()

    # @pytest.mark.unit
    # # Patch the ErrorHandler.handle_errors decorator to allow exceptions to pass through
    # @patch('rv_android_core.util.error.error_handler.ErrorHandler.handle_errors',
    #        side_effect=lambda component, phase: (lambda f: f))
    # def test_register_tools_registry_registration_fails(self, mock_handle_errors_decorator, mock_tool_registry,
    #                                                     mock_error_handler_instance, mock_logging_manager_instance):
    #     """Test register_tools when registry.register_tool raises an error."""
    #     mock_tool_class = MagicMock(spec=AbstractTool)
    #     mock_tool_spec = ToolSpec(name="failing_registry_tool", description="desc", url="url", version="1.0.0")
    #
    #     plugin = ConcreteToolPlugin(
    #         tool_names_list=["failing_registry_tool"],
    #         tool_class_map={"failing_registry_tool": mock_tool_class},
    #         tool_spec_map={"failing_registry_tool": mock_tool_spec},
    #     )
    #     # Make registry.register_tool raise an error
    #     mock_tool_registry.register_tool.side_effect = ToolRegistrationError("Registry rejected tool")
    #
    #     with pytest.raises(ToolRegistrationError) as excinfo:
    #         plugin.register_tools(mock_tool_registry)
    #
    #     expected_regex = r"Failed to register tools from plugin 'concrete_plugin': ToolRegistrationError: Registry rejected tool"
    #     assert re.search(expected_regex, str(excinfo.value)) is not None
    #     mock_tool_registry.register_tool.assert_called_once()
    #     mock_tool_registry.register_variant.assert_not_called()
    #     mock_error_handler_instance.handle_error.assert_called_once()
    #     plugin.logger.info.assert_not_called()

    @pytest.mark.unit
    def test_create_tool_instance_happy_path(self):
        """Test successful creation of a tool instance."""
        mock_tool_class = MagicMock(spec=AbstractTool)
        mock_tool_instance = mock_tool_class.return_value
        mock_tool_instance.configure = Mock()
        mock_tool_spec = ToolSpec(name="my_tool", description="desc", url="url", version="1.0.0",
                                  process_pattern="my_tool_proc.*")

        plugin = ConcreteToolPlugin(
            tool_names_list=["my_tool"],
            tool_class_map={"my_tool": mock_tool_class},
            tool_spec_map={"my_tool": mock_tool_spec}
        )

        config = {"timeout": 300, "param1": "value1"}
        tool_instance = plugin.create_tool_instance("my_tool", config)

        assert tool_instance is mock_tool_instance
        mock_tool_class.assert_called_once_with(
            name=mock_tool_spec.name,
            description=mock_tool_spec.description,
            process_pattern=mock_tool_spec.process_pattern
        )
        mock_tool_instance.configure.assert_called_once_with(config)

    @pytest.mark.unit
    def test_create_tool_instance_no_config(self):
        """Test tool instance creation without configuration."""
        mock_tool_class = MagicMock(spec=AbstractTool)
        mock_tool_instance = mock_tool_class.return_value
        mock_tool_instance.configure = Mock()
        mock_tool_spec = ToolSpec(name="my_tool", description="desc", url="url", version="1.0.0")

        plugin = ConcreteToolPlugin(
            tool_names_list=["my_tool"],
            tool_class_map={"my_tool": mock_tool_class},
            tool_spec_map={"my_tool": mock_tool_spec}
        )

        tool_instance = plugin.create_tool_instance("my_tool")

        assert tool_instance is mock_tool_instance
        mock_tool_instance.configure.assert_not_called()

    @pytest.mark.unit
    def test_create_tool_instance_tool_not_provided_by_plugin(self):
        """Test create_tool_instance when tool name is not provided by plugin."""
        plugin = ConcreteToolPlugin(tool_names_list=["existing_tool"])

        with pytest.raises(ToolRegistrationError) as excinfo:
            plugin.create_tool_instance("non_existent_tool")

        assert "Tool 'non_existent_tool' is not provided by plugin 'concrete_plugin'" in str(excinfo.value)

    @pytest.mark.unit
    def test_create_tool_instance_tool_class_fails(self, mock_error_handler_instance):
        """Test create_tool_instance when getting tool class fails."""
        plugin = ConcreteToolPlugin(
            tool_names_list=["failing_tool"],
            tool_class_map={},  # This will make get_tool_class fail
            tool_spec_map={"failing_tool": ToolSpec(name="failing_tool", description="", url="", version="")}
        )

        with pytest.raises(ToolRegistrationError) as excinfo:
            plugin.create_tool_instance("failing_tool")

        expected_regex = r"Failed to create tool instance 'failing_tool': ToolRegistrationError: Tool class failing_tool not found in plugin\."
        assert re.search(expected_regex, str(excinfo.value)) is not None
        mock_error_handler_instance.handle_error.assert_not_called()

    @pytest.mark.unit
    def test_create_tool_instance_tool_spec_fails(self, mock_error_handler_instance):
        """Test create_tool_instance when getting tool spec fails."""
        plugin = ConcreteToolPlugin(
            tool_names_list=["failing_tool"],
            tool_class_map={"failing_tool": MagicMock(spec=AbstractTool)},
            tool_spec_map={}  # This will make get_tool_spec fail
        )

        with pytest.raises(ToolRegistrationError) as excinfo:
            plugin.create_tool_instance("failing_tool")

        expected_regex = r"Failed to create tool instance 'failing_tool': ToolRegistrationError: Tool spec failing_tool not found in plugin\."
        assert re.search(expected_regex, str(excinfo.value)) is not None
        mock_error_handler_instance.handle_error.assert_not_called()

    @pytest.mark.unit
    def test_create_tool_instance_tool_instantiation_fails(self, mock_error_handler_instance):
        """Test create_tool_instance when the tool class constructor raises an error."""
        mock_tool_class = MagicMock(spec=AbstractTool)
        mock_tool_class.side_effect = Exception("Tool constructor failed")
        mock_tool_spec = ToolSpec(name="failing_constructor_tool", description="", url="", version="")

        plugin = ConcreteToolPlugin(
            tool_names_list=["failing_constructor_tool"],
            tool_class_map={"failing_constructor_tool": mock_tool_class},
            tool_spec_map={"failing_constructor_tool": mock_tool_spec}
        )

        with pytest.raises(ToolRegistrationError) as excinfo:
            plugin.create_tool_instance("failing_constructor_tool")

        expected_regex = r"Failed to create tool instance 'failing_constructor_tool': Tool constructor failed"
        assert re.search(expected_regex, str(excinfo.value)) is not None
        mock_tool_class.assert_called_once()
        mock_error_handler_instance.handle_error.assert_not_called()
