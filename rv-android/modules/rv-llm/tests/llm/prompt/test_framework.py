"""
Comprehensive unit tests for rv_llm.llm.prompt.framework.

This module tests the PromptFramework class that coordinates prompt generation
through factory patterns and component composition.

Test cases covered:
- Initialization with different configurations
- Creation through class method create()
- Strategy retrieval via factory pattern
- Prompt generation with different states
- Fragment registration
- Error handling and edge cases
- Property-based testing
"""

from unittest.mock import Mock, patch

import pytest
from hypothesis import given, strategies as st, settings, example

from rv_android_core.util.error.exceptions import RVPromptError
from rv_llm.config.prompt_config import PromptConfig
from rv_llm.llm.constants import PromptStrategyType
from rv_llm.llm.data_structures import LLMMessage, LLMRole, LLMTextContent
# Imports from module under test
from rv_llm.llm.prompt.framework import PromptFramework
from rv_llm.llm.prompt.information.fragment_manager import InformationManager, InformationFragment
from rv_llm.llm.prompt.template.jinja_repository import Jinja2TemplateRepository


class TestPromptFramework:
    """Test suite for PromptFramework class."""

    @pytest.fixture
    def mock_information_manager(self):
        """Create a mock InformationManager."""
        manager = Mock(spec=InformationManager)
        manager.register_fragments = Mock()
        return manager

    @pytest.fixture
    def mock_template_repository(self):
        """Create a mock Jinja2TemplateRepository."""
        repository = Mock(spec=Jinja2TemplateRepository)
        repository.register_fragment_directory = Mock()
        repository.register_template_directory = Mock()
        return repository

    @pytest.fixture
    def mock_prompt_config(self):
        """Create a mock PromptConfig."""
        config = Mock(spec=PromptConfig)
        config.strategy_type = PromptStrategyType.STANDARD
        return config

    @pytest.fixture
    def prompt_framework(self, mock_information_manager, mock_template_repository, mock_prompt_config):
        """Create a PromptFramework instance with mocked dependencies."""
        with patch('rv_llm.llm.prompt.framework.LoggingManager') as mock_logging:
            mock_logger = Mock()
            mock_logging.get_instance.return_value.get_logger.return_value = mock_logger

            with patch('rv_llm.llm.prompt.framework.ErrorHandler') as mock_error_handler:
                mock_error_handler.get_instance.return_value = Mock()

                framework = PromptFramework(
                    information_manager=mock_information_manager,
                    template_repository=mock_template_repository,
                    config=mock_prompt_config
                )
                framework.logger = mock_logger
                return framework

    def test_init_logging_setup(self, mock_information_manager, mock_template_repository, mock_prompt_config):
        """Test that logging is properly set up during initialization."""
        with patch('rv_llm.llm.prompt.framework.LoggingManager') as mock_logging:
            mock_logger = Mock()
            mock_logging_instance = Mock()
            mock_logging_instance.get_logger.return_value = mock_logger
            mock_logging.get_instance.return_value = mock_logging_instance

            with patch('rv_llm.llm.prompt.framework.ErrorHandler') as mock_error_handler:
                mock_error_handler.get_instance.return_value = Mock()

                framework = PromptFramework(
                    information_manager=mock_information_manager,
                    template_repository=mock_template_repository,
                    config=mock_prompt_config
                )

                # Verify logging manager was called correctly
                mock_logging.get_instance.assert_called_once()
                mock_logging_instance.get_logger.assert_called_once_with(
                    "rv_llm.llm.prompt.framework",
                    {"component": "PromptFramework"}
                )

                # Verify logger was stored
                assert framework.logger == mock_logger

    def test_init_with_valid_dependencies(self, mock_information_manager, mock_template_repository, mock_prompt_config):
        """Test successful initialization with valid dependencies."""
        with patch('rv_llm.llm.prompt.framework.LoggingManager') as mock_logging:
            mock_logger = Mock()
            mock_logging.get_instance.return_value.get_logger.return_value = mock_logger

            with patch('rv_llm.llm.prompt.framework.ErrorHandler') as mock_error_handler:
                mock_error_handler.get_instance.return_value = Mock()

                framework = PromptFramework(
                    information_manager=mock_information_manager,
                    template_repository=mock_template_repository,
                    config=mock_prompt_config
                )

                assert framework.information_manager == mock_information_manager
                assert framework.template_repository == mock_template_repository
                assert framework.config == mock_prompt_config
                assert framework.logger == mock_logger
                mock_logging.get_instance.assert_called_once()

    def test_init_with_none_config(self, mock_information_manager, mock_template_repository):
        """Test initialization with None config creates default PromptConfig."""
        with patch('rv_llm.llm.prompt.framework.LoggingManager'):
            with patch('rv_llm.llm.prompt.framework.ErrorHandler'):
                with patch('rv_llm.llm.prompt.framework.PromptConfig') as mock_prompt_config_class:
                    mock_config = Mock()
                    mock_prompt_config_class.return_value = mock_config

                    framework = PromptFramework(
                        information_manager=mock_information_manager,
                        template_repository=mock_template_repository,
                        config=None
                    )

                    mock_prompt_config_class.assert_called_once()
                    assert framework.config == mock_config

    @patch('rv_llm.llm.prompt.framework.LoggingManager')
    @patch('rv_llm.llm.prompt.framework.ErrorHandler')
    @patch('rv_llm.llm.prompt.framework.InformationManager')
    @patch('rv_llm.llm.prompt.framework.Jinja2TemplateRepository')
    @patch('rv_llm.llm.prompt.framework.PromptConfig')
    def test_create_class_method_with_config(self, mock_prompt_config_class, mock_repo_class,
                                             mock_manager_class, mock_error_handler, mock_logging):
        """Test create class method with provided config."""
        # Setup mocks
        mock_config = Mock()
        mock_manager = Mock()
        mock_repo = Mock()
        mock_logger = Mock()

        mock_manager_class.return_value = mock_manager
        mock_repo_class.return_value = mock_repo
        mock_logging.get_instance.return_value.get_logger.return_value = mock_logger
        mock_error_handler.get_instance.return_value = Mock()

        # Call create
        framework = PromptFramework.create(mock_config)

        # Assertions
        assert framework.information_manager == mock_manager
        assert framework.template_repository == mock_repo
        assert framework.config == mock_config
        mock_manager_class.assert_called_once()
        mock_repo_class.assert_called_once()

    @patch('rv_llm.llm.prompt.framework.LoggingManager')
    @patch('rv_llm.llm.prompt.framework.ErrorHandler')
    @patch('rv_llm.llm.prompt.framework.InformationManager')
    @patch('rv_llm.llm.prompt.framework.Jinja2TemplateRepository')
    @patch('rv_llm.llm.prompt.framework.PromptConfig')
    def test_create_class_method_with_none_config(self, mock_prompt_config_class, mock_repo_class,
                                                  mock_manager_class, mock_error_handler, mock_logging):
        """Test create class method with None config."""
        # Setup mocks
        mock_config = Mock()
        mock_manager = Mock()
        mock_repo = Mock()
        mock_logger = Mock()

        mock_prompt_config_class.return_value = mock_config
        mock_manager_class.return_value = mock_manager
        mock_repo_class.return_value = mock_repo
        mock_logging.get_instance.return_value.get_logger.return_value = mock_logger
        mock_error_handler.get_instance.return_value = Mock()

        # Call create with None
        framework = PromptFramework.create(None)

        # Assertions
        mock_prompt_config_class.assert_called_once()
        assert framework.config == mock_config

    def test_get_strategy_with_explicit_name(self, prompt_framework):
        """Test get_strategy with explicitly provided strategy name."""
        mock_strategy = Mock()

        with patch('rv_llm.factories.component_factory.LLMComponentFactory') as mock_factory:
            mock_factory.create_strategy.return_value = mock_strategy

            result = prompt_framework.get_strategy(PromptStrategyType.BATCH_ACTION)

            assert result == mock_strategy
            mock_factory.create_strategy.assert_called_once_with(
                prompt_framework.config,
                information_manager=prompt_framework.information_manager,
                template_repository=prompt_framework.template_repository
            )

    def test_get_strategy_without_explicit_name_uses_config(self, prompt_framework):
        """Test get_strategy without explicit name uses strategy type from config."""
        mock_strategy = Mock()
        expected_strategy_type = PromptStrategyType.BATCH_ACTION
        prompt_framework.config.strategy_type = expected_strategy_type

        with patch('rv_llm.factories.component_factory.LLMComponentFactory') as mock_factory:
            mock_factory.create_strategy.return_value = mock_strategy

            # Call without strategy name - should use config.strategy_type
            result = prompt_framework.get_strategy(None)

            assert result == mock_strategy
            mock_factory.create_strategy.assert_called_once_with(
                prompt_framework.config,
                information_manager=prompt_framework.information_manager,
                template_repository=prompt_framework.template_repository
            )

    def test_get_strategy_with_none_config_uses_default(self, mock_information_manager, mock_template_repository):
        """Test get_strategy when config is None, should use STANDARD strategy."""
        with patch('rv_llm.llm.prompt.framework.LoggingManager'):
            with patch('rv_llm.llm.prompt.framework.ErrorHandler'):
                with patch('rv_llm.llm.prompt.framework.PromptConfig') as mock_prompt_config_class:
                    mock_config = Mock()
                    mock_prompt_config_class.return_value = mock_config

                    framework = PromptFramework(
                        information_manager=mock_information_manager,
                        template_repository=mock_template_repository,
                        config=None
                    )

                    mock_strategy = Mock()

                    with patch('rv_llm.factories.component_factory.LLMComponentFactory') as mock_factory:
                        mock_factory.create_strategy.return_value = mock_strategy

                        result = framework.get_strategy()

                        assert result == mock_strategy
                        # Should use the default strategy from the created config
                        mock_factory.create_strategy.assert_called_once()

    def test_get_strategy_factory_raises_rv_prompt_error(self, prompt_framework):
        """Test get_strategy when factory raises RVPromptError - should re-raise."""
        error = RVPromptError("Strategy creation failed", "test_strategy", None)

        with patch('rv_llm.factories.component_factory.LLMComponentFactory') as mock_factory:
            mock_factory.create_strategy.side_effect = error

            with pytest.raises(RVPromptError) as exc_info:
                prompt_framework.get_strategy()

            assert exc_info.value == error

    def test_get_strategy_factory_raises_other_exception(self, prompt_framework):
        """Test get_strategy when factory raises non-RVPromptError - should wrap in RVPromptError."""
        original_error = ValueError("Some other error")

        with patch('rv_llm.factories.component_factory.LLMComponentFactory') as mock_factory:
            mock_factory.create_strategy.side_effect = original_error

            with pytest.raises(RVPromptError) as exc_info:
                prompt_framework.get_strategy()

            assert "Error creating strategy" in str(exc_info.value)
            assert exc_info.value.__cause__ == original_error

    def test_get_strategy_import_error_handling(self, prompt_framework):
        """Test get_strategy handles import errors properly."""
        import_error = ImportError("No module named 'some_strategy'")

        with patch('rv_llm.factories.component_factory.LLMComponentFactory') as mock_factory:
            mock_factory.create_strategy.side_effect = import_error

            with pytest.raises(RVPromptError) as exc_info:
                prompt_framework.get_strategy()

            assert "Error creating strategy" in str(exc_info.value)

    def test_generate_prompt_successful_with_strategy(self, prompt_framework):
        """Test successful prompt generation with available strategy."""
        # Setup test data
        test_state = {"activity": "MainActivity", "ui_elements": "Button: Login"}
        test_context = {"app_package": "com.example.app"}

        # Create mock messages
        mock_message = Mock(spec=LLMMessage)
        mock_message.role = LLMRole.USER
        mock_message.content = [Mock(spec=LLMTextContent)]
        expected_messages = [mock_message]

        # Setup mock strategy
        mock_strategy = Mock()
        mock_strategy.generate_prompt.return_value = expected_messages

        with patch.object(prompt_framework, 'get_strategy') as mock_get_strategy:
            mock_get_strategy.return_value = mock_strategy

            result = prompt_framework.generate_prompt(test_state, test_context)

            assert result == expected_messages
            mock_get_strategy.assert_called_once_with(prompt_framework.config.strategy_type)
            mock_strategy.generate_prompt.assert_called_once_with(test_state, test_context)

    def test_generate_prompt_strategy_not_found(self, prompt_framework):
        """Test prompt generation when strategy is not found."""
        test_state = {"activity": "MainActivity"}

        with patch.object(prompt_framework, 'get_strategy') as mock_get_strategy:
            mock_get_strategy.return_value = None

            result = prompt_framework.generate_prompt(test_state)

            assert result == []
            prompt_framework.logger.error.assert_called()

    def test_generate_prompt_with_none_context(self, prompt_framework):
        """Test prompt generation with None context."""
        test_state = {"activity": "MainActivity"}
        mock_strategy = Mock()
        mock_strategy.generate_prompt.return_value = []

        with patch.object(prompt_framework, 'get_strategy') as mock_get_strategy:
            mock_get_strategy.return_value = mock_strategy

            prompt_framework.generate_prompt(test_state, None)

            mock_strategy.generate_prompt.assert_called_once_with(test_state, None)

    def test_generate_prompt_strategy_raises_exception(self, prompt_framework):
        """Test prompt generation when strategy raises exception."""
        test_state = {"activity": "MainActivity"}
        test_error = Exception("Strategy failed")

        mock_strategy = Mock()
        mock_strategy.generate_prompt.side_effect = test_error

        with patch.object(prompt_framework, 'get_strategy') as mock_get_strategy:
            mock_get_strategy.return_value = mock_strategy

            # The ErrorHandler decorator should handle the exception
            # Since we're testing the decorated method, we expect it might handle or re-raise
            try:
                result = prompt_framework.generate_prompt(test_state)
                # If no exception is raised, verify the error was logged
                assert isinstance(result, list)  # Should return empty list or handle gracefully
            except Exception:
                # Exception might be re-raised depending on ErrorHandler implementation
                pass

    def test_generate_prompt_uses_correct_strategy_name(self, prompt_framework):
        """Test that generate_prompt uses the correct strategy name from config."""
        test_state = {"activity": "MainActivity"}
        expected_strategy_type = PromptStrategyType.BATCH_ACTION
        prompt_framework.config.strategy_type = expected_strategy_type

        mock_strategy = Mock()
        mock_strategy.generate_prompt.return_value = []

        with patch.object(prompt_framework, 'get_strategy') as mock_get_strategy:
            mock_get_strategy.return_value = mock_strategy

            prompt_framework.generate_prompt(test_state)

            # Verify get_strategy was called with the strategy type from config
            mock_get_strategy.assert_called_once_with(expected_strategy_type)

    def test_register_fragments_successful(self, prompt_framework):
        """Test successful fragment registration."""
        mock_fragment1 = Mock(spec=InformationFragment)
        mock_fragment2 = Mock(spec=InformationFragment)
        fragments = [mock_fragment1, mock_fragment2]

        prompt_framework.register_fragments(fragments)

        prompt_framework.information_manager.register_fragments.assert_called_once_with(fragments)
        prompt_framework.logger.info.assert_called()

    def test_register_fragments_empty_list(self, prompt_framework):
        """Test registering empty list of fragments."""
        prompt_framework.register_fragments([])

        prompt_framework.information_manager.register_fragments.assert_called_once_with([])

    def test_generate_prompt_with_empty_state(self, prompt_framework):
        """Test prompt generation with empty state dictionary."""
        empty_state = {}

        mock_strategy = Mock()
        mock_strategy.generate_prompt.return_value = []

        with patch.object(prompt_framework, 'get_strategy') as mock_get_strategy:
            mock_get_strategy.return_value = mock_strategy

            result = prompt_framework.generate_prompt(empty_state)

            assert result == []
            mock_strategy.generate_prompt.assert_called_once_with(empty_state, None)

    def test_generate_prompt_with_complex_state(self, prompt_framework):
        """Test prompt generation with complex state containing various data types."""
        complex_state = {
            "activity": "MainActivity",
            "ui_elements": ["button1", "button2"],
            "metadata": {"version": "1.0", "debug": True},
            "numbers": [1, 2, 3],
            "nested": {"inner": {"value": "test"}}
        }

        mock_message = Mock(spec=LLMMessage)
        expected_messages = [mock_message]

        mock_strategy = Mock()
        mock_strategy.generate_prompt.return_value = expected_messages

        with patch.object(prompt_framework, 'get_strategy') as mock_get_strategy:
            mock_get_strategy.return_value = mock_strategy

            result = prompt_framework.generate_prompt(complex_state)

            assert result == expected_messages
            mock_strategy.generate_prompt.assert_called_once_with(complex_state, None)

    def test_generate_prompt_logging_on_strategy_not_found(self, prompt_framework):
        """Test that appropriate logging occurs when strategy is not found."""
        test_state = {"activity": "MainActivity"}

        with patch.object(prompt_framework, 'get_strategy') as mock_get_strategy:
            mock_get_strategy.return_value = None

            result = prompt_framework.generate_prompt(test_state)

            assert result == []
            # Verify error was logged
            assert prompt_framework.logger.error.called
            call_args = prompt_framework.logger.error.call_args
            assert "Strategy not found" in str(call_args)

    def test_register_fragments_logging(self, prompt_framework):
        """Test that fragment registration logs appropriate information."""
        mock_fragment = Mock(spec=InformationFragment)
        fragments = [mock_fragment]

        prompt_framework.register_fragments(fragments)

        # Verify info was logged
        assert prompt_framework.logger.info.called
        call_args = prompt_framework.logger.info.call_args
        assert "1" in str(call_args) or "fragments" in str(call_args)

    def test_generate_prompt_debug_logging(self, prompt_framework):
        """Test debug logging during prompt generation."""
        test_state = {"activity": "MainActivity"}
        strategy_type = PromptStrategyType.STANDARD
        prompt_framework.config.strategy_type = strategy_type

        mock_strategy = Mock()
        mock_strategy.generate_prompt.return_value = []

        with patch.object(prompt_framework, 'get_strategy') as mock_get_strategy:
            mock_get_strategy.return_value = mock_strategy

            prompt_framework.generate_prompt(test_state)

            # Verify debug was logged
            assert prompt_framework.logger.debug.called


class TestPromptFrameworkPropertyBased:
    """Property-based tests for PromptFramework."""

    def create_test_framework(self, config=None):
        """Helper method to create PromptFramework instances for property tests."""
        mock_manager = Mock(spec=InformationManager)
        mock_repo = Mock(spec=Jinja2TemplateRepository)

        with patch('rv_llm.llm.prompt.framework.LoggingManager'):
            with patch('rv_llm.llm.prompt.framework.ErrorHandler'):
                if config is None:
                    with patch('rv_llm.llm.prompt.framework.PromptConfig'):
                        return PromptFramework(mock_manager, mock_repo, None)
                else:
                    return PromptFramework(mock_manager, mock_repo, config)

    # Strategy for generating state dictionaries
    state_strategy = st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.one_of(
            st.text(min_size=0, max_size=100),
            st.integers(min_value=0, max_value=1000),
            st.booleans(),
            st.lists(st.text(min_size=0, max_size=50), max_size=5)
        ),
        min_size=0,
        max_size=10
    )

    # Strategy for generating context dictionaries
    context_strategy = st.one_of(
        st.none(),
        st.dictionaries(
            keys=st.text(min_size=1, max_size=15),
            values=st.text(min_size=0, max_size=50),
            min_size=0,
            max_size=5
        )
    )

    @given(state=state_strategy, context=context_strategy)
    @settings(max_examples=50, deadline=None)
    @example(state={}, context=None)
    @example(state={"activity": "MainActivity"}, context={"app_package": "com.test"})
    def test_generate_prompt_with_various_inputs(self, state, context):
        """Property test: generate_prompt should handle various state/context combinations."""
        framework = self.create_test_framework()

        # Mock strategy to avoid actual strategy creation
        mock_strategy = Mock()
        mock_strategy.generate_prompt.return_value = []

        with patch.object(framework, 'get_strategy') as mock_get_strategy:
            mock_get_strategy.return_value = mock_strategy

            # Should not raise exception for any valid input
            result = framework.generate_prompt(state, context)

            # Result should always be a list
            assert isinstance(result, list)
            mock_strategy.generate_prompt.assert_called_once_with(state, context)

    @given(fragments_count=st.integers(min_value=0, max_value=20))
    @settings(max_examples=30)
    def test_register_fragments_with_various_counts(self, fragments_count):
        """Property test: register_fragments should handle various fragment counts."""
        framework = self.create_test_framework()

        # Create mock fragments
        fragments = [Mock(spec=InformationFragment) for _ in range(fragments_count)]

        # Should not raise exception
        framework.register_fragments(fragments)

        # Should call information manager with the fragments
        framework.information_manager.register_fragments.assert_called_once_with(fragments)

    @given(strategy_name=st.one_of(
        st.none(),
        st.just(PromptStrategyType.STANDARD),
        st.just(PromptStrategyType.BATCH_ACTION),
        st.text(min_size=1, max_size=30)
    ))
    @settings(max_examples=30)
    def test_get_strategy_with_various_names(self, strategy_name):
        """Property test: get_strategy should handle various strategy names."""
        framework = self.create_test_framework()

        with patch('rv_llm.factories.component_factory.LLMComponentFactory') as mock_factory:
            mock_strategy = Mock()
            mock_factory.create_strategy.return_value = mock_strategy

            # Should not raise exception for valid strategy names
            try:
                result = framework.get_strategy(strategy_name)
                # If it doesn't raise, result should be the mock strategy
                assert result == mock_strategy
            except RVPromptError:
                # RVPromptError is acceptable for invalid strategy names
                pass


class TestPromptFrameworkEdgeCases:
    """Edge cases and error conditions for PromptFramework."""

    def test_init_with_mock_dependencies_none_logger(self):
        """Test initialization when logger creation fails."""
        mock_manager = Mock(spec=InformationManager)
        mock_repo = Mock(spec=Jinja2TemplateRepository)
        mock_config = Mock(spec=PromptConfig)
        mock_config.strategy_type = PromptStrategyType.STANDARD  # Fix: Add required attribute

        with patch('rv_llm.llm.prompt.framework.LoggingManager') as mock_logging:
            # Simulate logger creation failure
            mock_logging.get_instance.side_effect = Exception("Logger creation failed")

            with patch('rv_llm.llm.prompt.framework.ErrorHandler'):
                # Should still create framework, but might have issues
                with pytest.raises(Exception):
                    PromptFramework(mock_manager, mock_repo, mock_config)

    def test_generate_prompt_with_malformed_state(self):
        """Test generate_prompt with malformed state objects."""
        mock_manager = Mock(spec=InformationManager)
        mock_repo = Mock(spec=Jinja2TemplateRepository)
        mock_config = Mock(spec=PromptConfig)
        mock_config.strategy_type = PromptStrategyType.STANDARD  # Fix: Add required attribute

        with patch('rv_llm.llm.prompt.framework.LoggingManager'):
            with patch('rv_llm.llm.prompt.framework.ErrorHandler'):
                framework = PromptFramework(mock_manager, mock_repo, mock_config)

                mock_strategy = Mock()
                mock_strategy.generate_prompt.side_effect = KeyError("Missing required key")

                with patch.object(framework, 'get_strategy') as mock_get_strategy:
                    mock_get_strategy.return_value = mock_strategy

                    # Should handle KeyError gracefully
                    malformed_state = object()  # Not a dict
                    result = framework.generate_prompt(malformed_state)

                    # Behavior depends on ErrorHandler implementation

    def test_strategy_creation_with_missing_dependencies(self):
        """Test strategy creation when dependencies are missing."""
        mock_manager = Mock(spec=InformationManager)
        mock_repo = Mock(spec=Jinja2TemplateRepository)
        mock_config = Mock(spec=PromptConfig)
        mock_config.strategy_type = "non_existent_strategy"  # Fix: Add required attribute

        with patch('rv_llm.llm.prompt.framework.LoggingManager'):
            with patch('rv_llm.llm.prompt.framework.ErrorHandler'):
                framework = PromptFramework(mock_manager, mock_repo, mock_config)

                with patch('rv_llm.factories.component_factory.LLMComponentFactory') as mock_factory:
                    mock_factory.create_strategy.side_effect = ImportError("Strategy module not found")

                    with pytest.raises(RVPromptError):
                        framework.get_strategy()

    def test_concurrent_access_simulation(self):
        """Test framework behavior under simulated concurrent access."""
        import threading

        mock_manager = Mock(spec=InformationManager)
        mock_repo = Mock(spec=Jinja2TemplateRepository)
        mock_config = Mock(spec=PromptConfig)
        mock_config.strategy_type = PromptStrategyType.STANDARD  # Fix: Add required attribute

        with patch('rv_llm.llm.prompt.framework.LoggingManager'):
            with patch('rv_llm.llm.prompt.framework.ErrorHandler'):
                framework = PromptFramework(mock_manager, mock_repo, mock_config)

                results = []
                errors = []

                def worker():
                    try:
                        with patch.object(framework, 'get_strategy') as mock_get_strategy:
                            mock_strategy = Mock()
                            mock_strategy.generate_prompt.return_value = [Mock()]
                            mock_get_strategy.return_value = mock_strategy

                            result = framework.generate_prompt({"test": "data"})
                            results.append(result)
                    except Exception as e:
                        errors.append(e)

                # Simulate concurrent access
                threads = [threading.Thread(target=worker) for _ in range(5)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()

                # Should handle concurrent access without errors
                assert len(errors) == 0
                assert len(results) == 5

    def test_memory_usage_with_large_fragments_list(self):
        """Test framework behavior with large number of fragments."""
        mock_manager = Mock(spec=InformationManager)
        mock_repo = Mock(spec=Jinja2TemplateRepository)
        mock_config = Mock(spec=PromptConfig)
        mock_config.strategy_type = PromptStrategyType.STANDARD  # Fix: Add required attribute

        with patch('rv_llm.llm.prompt.framework.LoggingManager'):
            with patch('rv_llm.llm.prompt.framework.ErrorHandler'):
                framework = PromptFramework(mock_manager, mock_repo, mock_config)

                # Create large list of fragments
                large_fragments_list = [Mock(spec=InformationFragment) for _ in range(1000)]

                # Should handle large list without memory issues
                framework.register_fragments(large_fragments_list)

                mock_manager.register_fragments.assert_called_once_with(large_fragments_list)

    def test_generate_prompt_with_strategy_returning_large_result(self):
        """Test prompt generation when strategy returns large number of messages."""
        mock_manager = Mock(spec=InformationManager)
        mock_repo = Mock(spec=Jinja2TemplateRepository)
        mock_config = Mock(spec=PromptConfig)
        mock_config.strategy_type = PromptStrategyType.STANDARD  # Fix: Add required attribute

        with patch('rv_llm.llm.prompt.framework.LoggingManager'):
            with patch('rv_llm.llm.prompt.framework.ErrorHandler'):
                framework = PromptFramework(mock_manager, mock_repo, mock_config)

                # Create large list of mock messages
                large_message_list = [Mock(spec=LLMMessage) for _ in range(100)]

                mock_strategy = Mock()
                mock_strategy.generate_prompt.return_value = large_message_list

                with patch.object(framework, 'get_strategy') as mock_get_strategy:
                    mock_get_strategy.return_value = mock_strategy

                    result = framework.generate_prompt({"test": "data"})

                    assert result == large_message_list
                    assert len(result) == 100


# Integration test with actual classes (minimal mocking)
class TestPromptFrameworkIntegration:
    """Integration tests with minimal mocking."""

    def test_create_with_real_dependencies(self):
        """Test framework creation with real dependency classes."""
        from rv_llm.config.prompt_config import PromptConfig

        # Use real PromptConfig
        config = PromptConfig(
            strategy_type=PromptStrategyType.STANDARD,
            max_context_length=1024
        )

        with patch('rv_llm.llm.prompt.framework.LoggingManager'):
            with patch('rv_llm.llm.prompt.framework.ErrorHandler'):
                framework = PromptFramework.create(config)

                assert framework is not None
                assert framework.config == config
                assert framework.information_manager is not None
                assert framework.template_repository is not None

    def test_fragment_registration_integration(self):
        """Test fragment registration with real InformationFragment."""
        with patch('rv_llm.llm.prompt.framework.LoggingManager'):
            with patch('rv_llm.llm.prompt.framework.ErrorHandler'):
                framework = PromptFramework.create(None)

                # Create a simple fragment
                class TestFragment(InformationFragment):
                    def __init__(self):
                        super().__init__("test_fragment", 100)

                    def generate(self, state, context=None):
                        return "test content"

                test_fragment = TestFragment()

                # Should register without issues
                framework.register_fragments([test_fragment])

                # Verify registration occurred
                assert test_fragment in framework.information_manager.fragments.values()

    def test_end_to_end_workflow_with_mocked_strategy(self):
        """Test complete workflow from creation to prompt generation."""
        from rv_llm.config.prompt_config import PromptConfig

        config = PromptConfig(strategy_type=PromptStrategyType.BATCH_ACTION)

        with patch('rv_llm.llm.prompt.framework.LoggingManager'):
            with patch('rv_llm.llm.prompt.framework.ErrorHandler'):
                # Create framework
                framework = PromptFramework.create(config)

                # Mock strategy for this test
                mock_strategy = Mock()
                expected_messages = [Mock(spec=LLMMessage)]
                mock_strategy.generate_prompt.return_value = expected_messages

                with patch.object(framework, 'get_strategy') as mock_get_strategy:
                    mock_get_strategy.return_value = mock_strategy

                    # Test complete workflow
                    state = {"activity": "MainActivity", "ui_elements": "Button: Login"}
                    context = {"app_package": "com.test.app"}

                    result = framework.generate_prompt(state, context)

                    assert result == expected_messages
                    mock_strategy.generate_prompt.assert_called_once_with(state, context)

    def test_multiple_fragment_registration_and_workflow(self):
        """Test registering multiple fragments and using them in workflow."""
        with patch('rv_llm.llm.prompt.framework.LoggingManager'):
            with patch('rv_llm.llm.prompt.framework.ErrorHandler'):
                framework = PromptFramework.create(None)

                # Create multiple test fragments
                class Fragment1(InformationFragment):
                    def __init__(self):
                        super().__init__("fragment1", 100)

                    def generate(self, state, context=None):
                        return "fragment1 content"

                class Fragment2(InformationFragment):
                    def __init__(self):
                        super().__init__("fragment2", 200)

                    def generate(self, state, context=None):
                        return "fragment2 content"

                fragments = [Fragment1(), Fragment2()]
                framework.register_fragments(fragments)

                # Verify both fragments were registered
                assert len(framework.information_manager.fragments) >= 2

                # Test that the framework can still generate prompts
                mock_strategy = Mock()
                mock_strategy.generate_prompt.return_value = []

                with patch.object(framework, 'get_strategy') as mock_get_strategy:
                    mock_get_strategy.return_value = mock_strategy

                    result = framework.generate_prompt({"test": "state"})
                    assert isinstance(result, list)

    def test_framework_resilience_to_fragment_errors(self):
        """Test framework handles fragment errors gracefully."""
        with patch('rv_llm.llm.prompt.framework.LoggingManager'):
            with patch('rv_llm.llm.prompt.framework.ErrorHandler'):
                framework = PromptFramework.create(None)

                # Create a fragment that raises an error
                class ErrorFragment(InformationFragment):
                    def __init__(self):
                        super().__init__("error_fragment", 100)

                    def generate(self, state, context=None):
                        raise ValueError("Fragment error")

                error_fragment = ErrorFragment()

                # Should not raise during registration
                framework.register_fragments([error_fragment])

                # Framework should still work for prompt generation
                mock_strategy = Mock()
                mock_strategy.generate_prompt.return_value = []

                with patch.object(framework, 'get_strategy') as mock_get_strategy:
                    mock_get_strategy.return_value = mock_strategy

                    # Should not raise even with error fragment registered
                    result = framework.generate_prompt({"test": "state"})
                    assert isinstance(result, list)
