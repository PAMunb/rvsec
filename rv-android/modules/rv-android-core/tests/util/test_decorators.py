
import pytest
from unittest.mock import MagicMock, patch
from rv_android_core.util.decorators import task_phase, log_execution
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager

# Tests for task_phase decorator
class TestTaskPhaseDecorator:

    @pytest.fixture
    def decorated_obj(self):
        class Decorated:
            def __init__(self):
                self.logger = MagicMock()
                self.logger.with_context.return_value.__enter__ = MagicMock()
                self.logger.with_context.return_value.__exit__ = MagicMock()

            def _get_task_context(self):
                return {"task_id": "123"}

            @task_phase("test_phase")
            def my_method(self, a, b):
                return a + b

        return Decorated()

    def test_task_phase_calls_method(self, decorated_obj):
        result = decorated_obj.my_method(1, 2)
        assert result == 3

    def test_task_phase_logs_start(self, decorated_obj):
        decorated_obj.my_method(1, 2)
        decorated_obj.logger.debug.assert_called_with("Starting phase: test_phase")

    @patch.object(ErrorHandler, 'get_instance')
    def test_task_phase_uses_error_handler(self, mock_get_instance, decorated_obj):
        mock_error_handler = MagicMock()
        mock_error_handler.error_context.return_value.__enter__ = MagicMock()
        mock_error_handler.error_context.return_value.__exit__ = MagicMock()
        mock_get_instance.return_value = mock_error_handler

        decorated_obj.my_method(1, 2)
        mock_error_handler.error_context.assert_called_once()

    def test_task_phase_without_error_handling(self):
        class Decorated:
            def __init__(self):
                self.logger = MagicMock()
                self.logger.with_context.return_value.__enter__ = MagicMock()
                self.logger.with_context.return_value.__exit__ = MagicMock()

            @task_phase("test_phase", handle_task_errors=False)
            def my_method(self):
                pass

        obj = Decorated()
        obj.my_method()


# Tests for log_execution decorator
class TestLogExecutionDecorator:

    @patch.object(LoggingManager, 'get_instance')
    def test_log_execution_adds_logger(self, mock_get_instance):
        mock_logging_manager = MagicMock()
        mock_get_instance.return_value = mock_logging_manager

        @log_execution("my_prefix")
        class MyClass:
            def __init__(self):
                pass

        instance = MyClass()
        assert hasattr(instance, 'logger')
        mock_logging_manager.get_logger.assert_called_with("my_prefix.MyClass", {})

    @patch.object(LoggingManager, 'get_instance')
    def test_log_execution_with_component(self, mock_get_instance):
        mock_logging_manager = MagicMock()
        mock_get_instance.return_value = mock_logging_manager

        @log_execution("my_prefix", component_name="my_component")
        class MyClass:
            def __init__(self):
                pass

        instance = MyClass()
        assert hasattr(instance, 'logger')
        mock_logging_manager.get_logger.assert_called_with(
            "my_prefix.MyClass",
            {"component": "my_component"}
        )
