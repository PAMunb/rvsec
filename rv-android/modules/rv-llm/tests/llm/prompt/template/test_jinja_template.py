
import pytest
import jinja2
from unittest.mock import MagicMock, patch

from rv_llm.llm.prompt.template.jinja_template import Jinja2Template, FragmentDictLoader


@pytest.fixture
def mock_logger():
    with patch("rv_llm.llm.prompt.template.jinja_template.LoggingManager.get_instance") as mock_mgr:
        mock_logger_instance = MagicMock()
        mock_mgr.return_value.get_logger.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def mock_error_handler():
    with patch("rv_llm.llm.prompt.template.jinja_template.ErrorHandler.get_instance") as mock_handler:
        mock_handler_instance = MagicMock()
        mock_handler.return_value = mock_handler_instance
        yield mock_handler_instance


class TestJinja2TemplateInitialization:
    """Tests for the initialization of Jinja2Template."""

    def test_basic_initialization(self, mock_logger, mock_error_handler):
        template = Jinja2Template("Hello {{ name }}", "test_name", "user")
        assert template.template_text == "Hello {{ name }}"
        assert template.name == "test_name"
        assert template.role == "user"
        assert template.required_variables == set()
        assert isinstance(template.jinja_env, jinja2.Environment)
        assert "name" in template.all_variables

    def test_initialization_with_required_variables(self, mock_logger, mock_error_handler):
        template = Jinja2Template("Hello {{ name }}", "test_name", "user", required_variables={"name"})
        assert template.required_variables == {"name"}

    def test_initialization_with_fragment_repository(self, mock_logger, mock_error_handler):
        fragments = {"frag1": "Fragment content"}
        template = Jinja2Template("Hello", "test_name", "user", fragment_repository=fragments)
        assert template.fragment_repository == fragments
        assert isinstance(template.jinja_env.loader, FragmentDictLoader)

    def test_initialization_with_invalid_template_text(self, mock_logger, mock_error_handler):
        template = Jinja2Template("Hello {{ name ", "test_name", "user")
        mock_error_handler.handle_error.assert_called_once()


class TestJinja2TemplateEnvironmentCreation:
    """Tests for the _create_jinja_environment method."""

    def test_environment_settings(self, mock_logger, mock_error_handler):
        template = Jinja2Template("", "test", "user")
        env = template._create_jinja_environment()
        assert isinstance(env.loader, FragmentDictLoader)
        assert isinstance(env.undefined, type(jinja2.StrictUndefined))
        assert env.trim_blocks is True
        assert env.lstrip_blocks is True
        assert env.keep_trailing_newline is True

    def test_custom_filters_and_tests(self, mock_logger, mock_error_handler):
        template = Jinja2Template("", "test", "user")
        env = template._create_jinja_environment()
        assert "default_if_none" in env.filters
        assert "empty" in env.tests
        assert env.filters["default_if_none"]("value", "default") == "value"
        assert env.filters["default_if_none"](None, "default") == "default"
        assert env.tests["empty"]("") is True
        assert env.tests["empty"]("not_empty") is False


class TestJinja2TemplateVariableExtraction:
    """Tests for the _extract_all_variables method."""

    def test_extract_simple_variables(self, mock_logger, mock_error_handler):
        template = Jinja2Template("Hello {{ name }} and {{ age }}", "test", "user")
        assert template.all_variables == {"name", "age"}

    def test_extract_variables_with_filters_and_functions(self, mock_logger, mock_error_handler):
        template = Jinja2Template("{{ name | upper }} {{ user.get_name() }} {{ loop.index }}", "test", "user")
        assert template.all_variables == {"name", "loop.index"}

    def test_extract_variables_from_control_structures(self, mock_logger, mock_error_handler):
        template_text = "{% if condition %}{{ var1}}{% for item in items %}{{ item }}{% endfor %}{% endif %}"
        template = Jinja2Template(template_text, "test", "user")
        assert template.all_variables == {"condition", "var1", "item"}

    def test_extract_no_variables(self, mock_logger, mock_error_handler):
        template = Jinja2Template("Just plain text.", "test", "user")
        assert template.all_variables == set()


class TestJinja2TemplateRender:
    """Tests for the render method."""

    def test_render_success(self, mock_logger, mock_error_handler):
        template = Jinja2Template("Hello {{ name }}!", "test", "user")
        rendered_text = template.render({"name": "World"})
        assert rendered_text == "Hello World!"
        mock_logger.debug.assert_called()

    def test_render_with_missing_required_variables(self, mock_logger, mock_error_handler):
        template = Jinja2Template("Hello {{ name }} and {{ age }}!", "test", "user", required_variables={"name", "age"})
        rendered_text = template.render({"name": "World"})
        assert rendered_text == "Hello World and [MISSING_REQUIRED_VARIABLE:age]!"
        mock_logger.warning.assert_called_once_with("Missing required variables: age")

    def test_render_with_external_fragments(self, mock_logger, mock_error_handler):
        base_template = "{% include 'my_fragment' %}"
        # Create a mock FragmentDictLoader instance
        mock_loader_instance = MagicMock(spec=FragmentDictLoader)
        mock_loader_instance.get_source.return_value = ("External Fragment Content", None, lambda: True)

        # Patch _create_jinja_environment to return an environment with our mock loader
        with patch.object(Jinja2Template, '_create_jinja_environment') as mock_create_env:
            mock_env = MagicMock(spec=jinja2.Environment)
            mock_env.loader = mock_loader_instance
            mock_env.from_string.return_value = MagicMock()
            mock_env.from_string.return_value.render.return_value = "External Fragment Content"
            mock_create_env.return_value = mock_env

            template = Jinja2Template(base_template, "test", "user")
            external_fragments = {"my_fragment": "External Fragment Content"}
            rendered_text = template.render({}, external_fragments=external_fragments)
            assert rendered_text == "External Fragment Content"
            mock_logger.debug.assert_called()

    def test_render_template_error(self, mock_logger, mock_error_handler):
        template = Jinja2Template("{{ non_existent_var }}", "test", "user")
        rendered_text = template.render({})
        assert "TEMPLATE ERROR" in rendered_text
        mock_error_handler.handle_error.assert_called_once()

    def test_render_unexpected_error(self, mock_logger, mock_error_handler):
        template = Jinja2Template("{{ name }}", "test", "user")
        with patch.object(template.compiled_template, "render", side_effect=Exception("Unexpected")):
            rendered_text = template.render({"name": "World"})
            assert "UNEXPECTED ERROR" in rendered_text
            mock_error_handler.handle_error.assert_called_once()


class TestFragmentDictLoader:
    """Tests for the FragmentDictLoader."""

    def test_get_source_direct_match(self, mock_logger, mock_error_handler):
        fragments = {"my_fragment": "Content"}
        loader = FragmentDictLoader(fragments)
        source, _, _ = loader.get_source(MagicMock(), "my_fragment")
        assert source == "Content"
        mock_logger.debug.assert_called_with("Found fragment 'my_fragment' with direct match")

    def test_get_source_prefixed_match(self, mock_logger, mock_error_handler):
        fragments = {"fragments/my_fragment": "Content"}
        loader = FragmentDictLoader(fragments)
        source, _, _ = loader.get_source(MagicMock(), "my_fragment")
        assert source == "Content"
        mock_logger.debug.assert_called_with("Found fragment 'my_fragment' with prefix 'fragments/'")

    def test_get_source_case_insensitive_match(self, mock_logger, mock_error_handler):
        fragments = {"My_Fragment": "Content"}
        loader = FragmentDictLoader(fragments)
        source, _, _ = loader.get_source(MagicMock(), "my_fragment")
        assert source == "Content"
        mock_logger.debug.assert_called_with("Found fragment 'my_fragment' with case-insensitive match to 'My_Fragment'")

    def test_get_source_not_found(self, mock_logger, mock_error_handler):
        loader = FragmentDictLoader({})
        with pytest.raises(jinja2.exceptions.TemplateNotFound):
            loader.get_source(MagicMock(), "non_existent_fragment")
        mock_logger.warning.assert_called_with("Fragment not found: 'non_existent_fragment'")
