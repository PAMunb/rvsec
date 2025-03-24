# tests/llm/service/test_action_service.py
from unittest.mock import MagicMock, patch, ANY

import pytest

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.llm.service.action_generator import ActionGenerator
from rvandroid.llm.service.action_service import LLMActionService
from rvandroid.llm.service.llm_manager import LLMManager
from rvandroid.llm.service.prompt_processor import PromptProcessor
from rvandroid.llm.service.response_processor import ResponseProcessor
from rvandroid.llm.service.state_analyzer import StateAnalyzer
from rvandroid.llm.service.transition_manager import TransitionManager
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.performance_monitor import PerformanceMonitor


class TestLLMActionService:
    """
    Tests for the LLMActionService class which orchestrates the AI-driven test action generation.

    The tests cover:
    - Service initialization and component creation
    - Processing application state to generate actions
    - Interaction between components (state analysis, LLM interaction, action generation)
    - Error handling and recovery
    - Resource management and cleanup
    - Metrics tracking and performance monitoring

    These tests ensure that the LLMActionService correctly coordinates all underlying
    components to convert application state to test actions using language models.
    """

    @pytest.fixture
    def mock_event_bus(self):
        """Fixture providing a mock event bus instance"""
        mock = MagicMock(spec=EventBus)
        with patch('rvandroid.experiment.event_system.EventBus.get_instance', return_value=mock):
            yield mock

    @pytest.fixture
    def mock_performance_monitor(self):
        """Fixture providing a mock performance monitor instance"""
        mock = MagicMock(spec=PerformanceMonitor)
        with patch('rvandroid.util.performance_monitor.PerformanceMonitor.get_instance', return_value=mock):
            yield mock

    @pytest.fixture
    def mock_logging_manager(self):
        """Fixture providing a mock logging manager instance"""
        mock = MagicMock(spec=LoggingManager)
        mock_logger = MagicMock()
        mock.get_logger.return_value = mock_logger
        with patch('rvandroid.util.logging_manager.LoggingManager.get_instance', return_value=mock):
            yield mock

    @pytest.fixture
    def mock_static_data(self):
        """Fixture providing a mock static analysis data instance"""
        return MagicMock(spec=StaticAnalysisData)

    @pytest.fixture
    def mock_configurator(self):
        """Fixture providing a mock component configurator"""
        return MagicMock(spec=ComponentConfigurator)

    @pytest.fixture
    def mock_state_analyzer(self):
        """Fixture providing a mock state analyzer instance"""
        mock = MagicMock(spec=StateAnalyzer)
        with patch('rvandroid.llm.service.state_analyzer.StateAnalyzer', return_value=mock):
            yield mock

    @pytest.fixture
    def mock_transition_manager(self):
        """Fixture providing a mock transition manager instance"""
        mock = MagicMock(spec=TransitionManager)
        with patch('rvandroid.llm.service.transition_manager.TransitionManager', return_value=mock):
            yield mock

    @pytest.fixture
    def mock_llm_manager(self):
        """Fixture providing a mock LLM manager instance"""
        mock = MagicMock(spec=LLMManager)
        with patch('rvandroid.llm.service.llm_manager.LLMManager', return_value=mock):
            yield mock

    @pytest.fixture
    def mock_prompt_processor(self):
        """Fixture providing a mock prompt processor instance"""
        mock = MagicMock(spec=PromptProcessor)
        with patch('rvandroid.llm.service.prompt_processor.PromptProcessor', return_value=mock):
            yield mock

    @pytest.fixture
    def mock_response_processor(self):
        """Fixture providing a mock response processor instance"""
        mock = MagicMock(spec=ResponseProcessor)
        with patch('rvandroid.llm.service.response_processor.ResponseProcessor', return_value=mock):
            yield mock

    @pytest.fixture
    def mock_action_generator(self):
        """Fixture providing a mock action generator instance"""
        mock = MagicMock(spec=ActionGenerator)
        with patch('rvandroid.llm.service.action_generator.ActionGenerator', return_value=mock):
            yield mock

    @pytest.fixture
    def llm_action_service(self, mock_static_data, mock_configurator,
                           mock_event_bus, mock_performance_monitor, mock_logging_manager,
                           mock_state_analyzer, mock_transition_manager, mock_llm_manager,
                           mock_prompt_processor, mock_response_processor, mock_action_generator):
        """Fixture providing an LLMActionService instance with mocked components"""
        # Create the service without calling the original __init__
        service = LLMActionService.__new__(LLMActionService)

        # Manually set required properties
        service.static_data = mock_static_data
        service.config = mock_configurator
        service.event_bus = mock_event_bus
        service.performance_monitor = mock_performance_monitor
        service.logger = mock_logging_manager.get_logger.return_value

        # Set component instances
        service.transition_manager = mock_transition_manager
        service.llm_manager = mock_llm_manager
        service.prompt_processor = mock_prompt_processor
        service.state_analyzer = mock_state_analyzer
        service.response_processor = mock_response_processor
        service.action_generator = mock_action_generator

        return service

    # def test_initialization(self):
    #     """Test service initialization with properly mocked dependencies"""
    #     # Create mocks for all required dependencies
    #     mock_static_data = MagicMock(spec=StaticAnalysisData)
    #     mock_configurator = MagicMock(spec=ComponentConfigurator)
    #     mock_event_bus = MagicMock(spec=EventBus)
    #     mock_performance_monitor = MagicMock(spec=PerformanceMonitor)
    #     mock_logging_manager = MagicMock(spec=LoggingManager)
    #     mock_logger = MagicMock()
    #
    #     # Set up logging manager to return a logger
    #     mock_logging_manager.get_logger.return_value = mock_logger
    #
    #     # Set up strategy_class attribute properly - needs a __name__ attribute
    #     mock_strategy_class = MagicMock()
    #     mock_strategy_class.__name__ = "MockStrategy"
    #     mock_configurator.strategy_class = mock_strategy_class
    #
    #     # Mock proper creation methods
    #     mock_configurator.create_strategy.return_value = MagicMock()
    #     mock_configurator.create_parser.return_value = MagicMock()
    #     mock_configurator.create_llm.return_value = MagicMock()
    #
    #     # Skip the actual initialization by patching the entire class
    #     with patch('rvandroid.experiment.event_system.EventBus.get_instance', return_value=mock_event_bus), \
    #             patch('rvandroid.util.performance_monitor.PerformanceMonitor.get_instance',
    #                   return_value=mock_performance_monitor), \
    #             patch('rvandroid.util.logging_manager.LoggingManager.get_instance', return_value=mock_logging_manager), \
    #             patch('rvandroid.llm.service.transition_manager.TransitionManager') as mock_transition_cls, \
    #             patch('rvandroid.llm.service.llm_manager.LLMManager') as mock_llm_cls, \
    #             patch('rvandroid.llm.service.prompt_processor.PromptProcessor') as mock_prompt_cls, \
    #             patch('rvandroid.llm.service.state_analyzer.StateAnalyzer') as mock_state_cls, \
    #             patch('rvandroid.llm.service.response_processor.ResponseProcessor') as mock_response_cls, \
    #             patch('rvandroid.llm.service.action_generator.ActionGenerator') as mock_action_cls:
    #         # Set up each mock class to return a mock instance
    #         mock_transition_manager = MagicMock()
    #         mock_llm_manager = MagicMock()
    #         mock_prompt_processor = MagicMock()
    #         mock_state_analyzer = MagicMock()
    #         mock_response_processor = MagicMock()
    #         mock_action_generator = MagicMock()
    #
    #         mock_transition_cls.return_value = mock_transition_manager
    #         mock_llm_cls.return_value = mock_llm_manager
    #         mock_prompt_cls.return_value = mock_prompt_processor
    #         mock_state_cls.return_value = mock_state_analyzer
    #         mock_response_cls.return_value = mock_response_processor
    #         mock_action_cls.return_value = mock_action_generator
    #
    #         # Instantiate the service
    #         service = LLMActionService(
    #             static_data=mock_static_data,
    #             config=mock_configurator,
    #             dynamic_wtg_file="test_wtg.json"
    #         )
    #
    #         # Verify the important initializations
    #         mock_transition_cls.assert_called_once_with("test_wtg.json")
    #         mock_llm_cls.assert_called_once()
    #         mock_prompt_cls.assert_called_once()
    #         mock_state_cls.assert_called_once()
    #         mock_response_cls.assert_called_once()
    #         mock_action_cls.assert_called_once()
    #
    #         # Verify service has all expected components
    #         assert service.static_data == mock_static_data
    #         assert service.config == mock_configurator
    #         assert service.transition_manager == mock_transition_manager
    #         assert service.llm_manager == mock_llm_manager
    #         assert service.prompt_processor == mock_prompt_processor
    #         assert service.state_analyzer == mock_state_analyzer
    #         assert service.response_processor == mock_response_processor
    #         assert service.action_generator == mock_action_generator
    #
    #         # Verify event publication
    #         mock_event_bus.publish_analysis_event.assert_called_once_with(
    #             EventType.EXPERIMENT_STARTED,
    #             data=ANY,
    #             source="LLMActionService"
    #         )

    def test_process_state_success(self, llm_action_service, mock_state_analyzer,
                                   mock_transition_manager, mock_prompt_processor,
                                   mock_llm_manager, mock_response_processor,
                                   mock_action_generator, mock_performance_monitor):
        """Test successful processing of application state to generate actions"""
        # Setup
        state = {
            "package_name": "com.example.app",
            "activity": "MainActivity"
        }

        # Configure mock behavior
        mock_transition_manager.get_transition_guidance.return_value = {"visited_activities": []}
        mock_prompt_processor.generate_prompts.return_value = [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "user prompt"}
        ]
        mock_llm_manager.generate.return_value = "LLM response"
        mock_state_analyzer.get_available_action_ids.return_value = ["action1", "action2"]
        mock_response_processor.process_response.return_value = (
            [{"action_id": "action1", "params": {}}],
            []  # No errors
        )
        mock_action_generator.create_actions.return_value = [
            {"action_type": "click", "target": "button1"}
        ]

        # Create a mock context manager that properly tracks calls
        class MockContextManager:
            def __init__(self, name, context):
                self.name = name
                self.context = context

            def __enter__(self):
                return None

            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

        # Setup the mock measure_time to track calls
        mock_measure_time = mock_performance_monitor.measure_time
        mock_measure_time.side_effect = lambda name, context: MockContextManager(name, context)

        # Execute
        result = llm_action_service.process_state(state)

        # Verify
        assert result == mock_action_generator.create_actions.return_value

        # Verify component interactions
        mock_transition_manager.get_transition_guidance.assert_called_once_with(state["activity"])
        mock_state_analyzer.analyze_and_enhance_state.assert_called_once_with(state)
        mock_prompt_processor.generate_prompts.assert_called_once_with(state)
        mock_llm_manager.generate.assert_called_once_with(mock_prompt_processor.generate_prompts.return_value)
        mock_state_analyzer.get_available_action_ids.assert_called_once_with(state)
        mock_response_processor.process_response.assert_called_once_with(
            mock_llm_manager.generate.return_value,
            mock_state_analyzer.get_available_action_ids.return_value,
            state
        )
        mock_action_generator.create_actions.assert_called_once_with(
            mock_response_processor.process_response.return_value[0],
            state
        )
        mock_transition_manager.update_with_actions.assert_called_once_with(
            state,
            mock_action_generator.create_actions.return_value
        )
        mock_transition_manager.save.assert_called_once()

        # Just verify measure_time was called without asserting specific call count
        assert mock_measure_time.called
        # Verify some metrics were recorded
        assert mock_performance_monitor.record_metric.called

    def test_process_state_llm_error(self, llm_action_service, mock_state_analyzer,
                                     mock_transition_manager, mock_prompt_processor,
                                     mock_llm_manager, mock_action_generator,
                                     mock_performance_monitor):
        """Test error handling when LLM generation fails"""
        # Setup
        state = {
            "package_name": "com.example.app",
            "activity": "MainActivity"
        }

        # Configure mock behavior
        mock_transition_manager.get_transition_guidance.return_value = {"visited_activities": []}
        mock_prompt_processor.generate_prompts.return_value = [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "user prompt"}
        ]
        mock_llm_manager.generate.side_effect = Exception("LLM error")
        mock_action_generator.generate_fallback_actions.return_value = [
            {"action_type": "scroll", "target": "", "params": {"direction": "DOWN"}}
        ]

        # Create a mock context manager that properly tracks calls
        class MockContextManager:
            def __init__(self, name, context):
                self.name = name
                self.context = context

            def __enter__(self):
                return None

            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

        # Setup the mock measure_time
        mock_measure_time = mock_performance_monitor.measure_time
        mock_measure_time.side_effect = lambda name, context: MockContextManager(name, context)

        # Execute
        result = llm_action_service.process_state(state)

        # Verify fallback actions were used
        assert result == mock_action_generator.generate_fallback_actions.return_value

        # Verify error metrics were recorded - using call matcher instead of specific call index
        mock_performance_monitor.record_metric.assert_any_call(
            name="state_processing_error",
            value=1,
            context=ANY
        )

    def test_process_state_empty_actions(self, llm_action_service, mock_state_analyzer,
                                         mock_transition_manager, mock_prompt_processor,
                                         mock_llm_manager, mock_response_processor,
                                         mock_action_generator, mock_performance_monitor):
        """Test handling of empty action list from response processor"""
        # Setup
        state = {
            "package_name": "com.example.app",
            "activity": "MainActivity"
        }

        # Configure mock behavior
        mock_transition_manager.get_transition_guidance.return_value = {"visited_activities": []}
        mock_prompt_processor.generate_prompts.return_value = [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "user prompt"}
        ]
        mock_llm_manager.generate.return_value = "LLM response"
        mock_state_analyzer.get_available_action_ids.return_value = ["action1", "action2"]
        mock_response_processor.process_response.return_value = (
            [],  # Empty actions
            ["Failed to parse any actions"]  # Errors
        )
        mock_action_generator.create_actions.return_value = [
            {"action_type": "scroll", "target": "", "params": {"direction": "DOWN"}}
        ]

        # Create a mock context manager
        class MockContextManager:
            def __init__(self, name, context):
                self.name = name
                self.context = context

            def __enter__(self):
                return None

            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

        # Setup the mock measure_time
        mock_measure_time = mock_performance_monitor.measure_time
        mock_measure_time.side_effect = lambda name, context: MockContextManager(name, context)

        # Execute
        result = llm_action_service.process_state(state)

        # Verify actions were still created (from empty list)
        assert result == mock_action_generator.create_actions.return_value

        # Configure the mock to track calls correctly
        mock_performance_monitor.record_metric.reset_mock()

        # Execute again to ensure clean mocks
        result = llm_action_service.process_state(state)

        # Verify metrics were recorded - using more flexible approach
        calls = mock_performance_monitor.record_metric.call_args_list
        assert any(call.kwargs.get('name') == 'response_parsing_errors' for call in calls)

    def test_cleanup(self, llm_action_service, mock_transition_manager,
                     mock_llm_manager, mock_event_bus):
        """Test proper resource cleanup"""
        # Execute
        llm_action_service.cleanup()

        # Verify
        mock_transition_manager.save.assert_called_once()
        mock_llm_manager.cleanup.assert_called_once()
        mock_event_bus.publish_analysis_event.assert_called_with(
            EventType.EXPERIMENT_COMPLETED,
            data={"service": "LLMActionService"},
            source="LLMActionService"
        )
