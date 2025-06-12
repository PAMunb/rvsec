import pytest
import threading
import time
import gc
import weakref
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from contextlib import contextmanager

from rv_android_core.util.error.error_handler import ErrorHandler, error_context
from rv_android_core.util.exceptions import (
    RVAndroidError, RVTaskError, RVTaskExecutionError, RVTaskConfigurationError,
    RVTaskTimeoutError, RVToolError, RVToolExecutionError, RVToolConfigurationError,
    RVExperimentError, RVExperimentSetupError, RVExperimentExecutionError,
    RVParsingError, RVLLMError, RVPromptError
)


class TestErrorHandlerEdgeCases:
    """Edge cases and performance tests for ErrorHandler."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test."""
        ErrorHandler._instance = None
        yield
        ErrorHandler._instance = None

    @pytest.fixture
    def mock_logging_manager(self):
        """Mock LoggingManager for edge case testing."""
        with patch('rv_android_core.util.error.error_handler.LoggingManager') as mock_manager:
            mock_instance = Mock()
            mock_logger = Mock()
            mock_logger.with_context.return_value = contextmanager(lambda: (yield mock_logger))()
            mock_instance.get_logger.return_value = mock_logger
            mock_manager.get_instance.return_value = mock_instance
            yield mock_manager, mock_instance, mock_logger

    @pytest.fixture
    def error_handler(self, mock_logging_manager):
        """Create ErrorHandler instance for edge case testing."""
        return ErrorHandler.get_instance()

    def test_singleton_race_condition_stress(self, mock_logging_manager):
        """Stress test singleton race condition with many threads."""
        instances = []
        barriers = threading.Barrier(50)  # 50 threads

        def create_instance_with_barrier():
            barriers.wait()  # All threads start at the same time
            instance = ErrorHandler.get_instance()
            instances.append(instance)

        # Create many threads
        threads = [threading.Thread(target=create_instance_with_barrier) for _ in range(50)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # All instances should be identical
        assert len(instances) == 50
        assert len(set(id(instance) for instance in instances)) == 1

    def test_error_handler_with_none_attributes(self, error_handler):
        """Test error handling with errors that have None attributes."""
        # Create errors with None attributes
        task_error = RVTaskError("Test error", task_id=None)
        tool_error = RVToolError("Test error", tool_name=None)
        exp_error = RVExperimentError("Test error", experiment_id=None)
        parsing_error = RVParsingError("Test error", parser_type=None)
        llm_error = RVLLMError("Test error", model_name=None)
        prompt_error = RVPromptError("Test error", strategy=None)

        errors = [task_error, tool_error, exp_error, parsing_error, llm_error, prompt_error]

        # Should handle all errors without issues
        for error in errors:
            error_handler.handle_error(error)

        # Verify all were processed
        stats = error_handler.get_error_statistics()
        assert len(stats["error_counts"]) == 6

    def test_error_handler_with_empty_string_attributes(self, error_handler):
        """Test error handling with errors that have empty string attributes."""
        task_error = RVTaskError("Test error", task_id="")
        tool_error = RVToolError("Test error", tool_name="")
        exp_error = RVExperimentError("Test error", experiment_id="")

        for error in [task_error, tool_error, exp_error]:
            error_handler.handle_error(error)

        # Should handle gracefully
        assert len(error_handler._error_counts) == 3

    def test_error_handler_with_unicode_and_special_characters(self, error_handler):
        """Test error handling with unicode and special characters."""
        special_errors = [
            RVTaskError("Error with émojis 🚨💥🔥", task_id="task_ñ_123"),
            RVToolError("错误信息中文测试", tool_name="инструмент"),
            RVParsingError("Erreur avec caractères spéciaux: áéíóú", parser_type="ñ_parser"),
            RVLLMError("エラーメッセージ", model_name="model_ß"),
        ]

        for error in special_errors:
            error_handler.handle_error(error, {"unicode_key": "ключ_value_值"})

        # Should handle all unicode errors
        assert len(error_handler._error_counts) == 4

    def test_error_handler_with_very_long_strings(self, error_handler):
        """Test error handling with very long error messages and attributes."""
        long_message = "x" * 10000  # Very long message
        long_task_id = "task_" + "y" * 5000
        long_context_value = "z" * 8000

        error = RVTaskError(long_message, task_id=long_task_id)
        context = {
            "long_key": long_context_value,
            "normal_key": "normal_value"
        }

        # Should handle without memory issues
        error_handler.handle_error(error, context)
        assert "RVTaskError" in error_handler._error_counts

    def test_error_handler_with_deep_context_nesting(self, error_handler):
        """Test error handling with deeply nested context dictionaries."""
        # Create deeply nested context
        deep_context = {"level_0": {}}
        current = deep_context["level_0"]

        for i in range(1, 100):  # 100 levels deep
            current[f"level_{i}"] = {}
            current = current[f"level_{i}"]

        current["data"] = "deep_value"

        # Should handle deep nesting
        error_handler.handle_error(RVTaskError("Deep context test"), deep_context)
        assert "RVTaskError" in error_handler._error_counts

    def test_error_handler_callback_exception_isolation(self, error_handler):
        """Test that exceptions in one callback don't affect others."""
        call_log = []

        def good_callback_1(error, context):
            call_log.append("good_1")
            return False

        def failing_callback(error, context):
            call_log.append("failing")
            raise RuntimeError("Callback failed")

        def good_callback_2(error, context):
            call_log.append("good_2")
            return False

        # Register callbacks
        error_handler.register_error_callback(good_callback_1)
        error_handler.register_error_callback(failing_callback)
        error_handler.register_error_callback(good_callback_2)

        # Handle error
        error_handler.handle_error(RVTaskError("Callback isolation test"))

        # All callbacks should have been called despite failure
        assert "good_1" in call_log
        assert "failing" in call_log
        assert "good_2" in call_log

    def test_error_handler_memory_leak_prevention(self, error_handler):
        """Test that error handler doesn't create memory leaks."""
        # Create objects that could potentially leak
        leak_test_objects = []

        class LeakTestObject:
            def __init__(self, data):
                self.data = data

        def callback_with_references(error, context):
            # Create objects that could potentially be held
            obj = LeakTestObject(f"data_{len(leak_test_objects)}")
            leak_test_objects.append(obj)
            return False

        error_handler.register_error_callback(callback_with_references)

        # Create weak references to track garbage collection
        weak_refs = []
        for i in range(100):
            error_handler.handle_error(RVTaskError(f"Leak test {i}"))
            if leak_test_objects:
                weak_refs.append(weakref.ref(leak_test_objects[-1]))

        # Clear explicit references
        leak_test_objects.clear()

        # Force garbage collection
        gc.collect()

        # Some weak references should be dead (indicating proper cleanup)
        dead_refs = sum(1 for ref in weak_refs if ref() is None)
        assert dead_refs > 0, "Expected some objects to be garbage collected"

    def test_error_handler_performance_with_large_history(self, error_handler):
        """Test performance with large error history."""
        start_time = time.time()

        # Generate many errors quickly
        for i in range(1000):
            error_handler.handle_error(RVTaskError(f"Performance test {i}"))

        end_time = time.time()
        duration = end_time - start_time

        # Should complete in reasonable time (less than 5 seconds)
        assert duration < 5.0

        # History should be capped
        assert len(error_handler._error_history) == 100

        # But counts should track all
        assert error_handler._error_counts["RVTaskError"] == 1000

    def test_error_handler_with_recursive_error_attributes(self, error_handler):
        """Test handling of errors with recursive attribute structures."""
        # Create error with self-referencing attributes
        error = RVTaskError("Recursive test")
        error.recursive_attr = error  # Self-reference

        # Should handle without infinite recursion
        try:
            error_handler.handle_error(error)
            assert "RVTaskError" in error_handler._error_counts
        except RecursionError:
            pytest.fail("Should handle recursive error attributes gracefully")

    def test_error_context_manager_exception_chaining(self, error_handler):
        """Test exception chaining in error context manager."""
        original_error = ValueError("Original error")

        def handler_that_raises(error, context):
            if isinstance(error, RVTaskError):
                return True  # Claim to handle it
            return False

        error_handler.register_handler(RVTaskError, handler_that_raises)

        # Context manager should handle the error and not re-raise
        try:
            with error_handler.error_context(component="TestComponent"):
                raise RVTaskError("Context manager test")
            # Should reach here since error was handled
        except RVTaskError:
            pytest.fail("Error should have been handled by context manager")

    def test_error_handler_with_builtin_handler_conflicts(self, error_handler):
        """Test behavior when custom handlers conflict with built-in handlers."""
        custom_calls = []

        def custom_task_handler(error, context):
            custom_calls.append("custom_called")
            return True  # Override built-in behavior

        # Register custom handler for same type as built-in
        error_handler.register_handler(RVTaskError, custom_task_handler)

        # Handle error
        error_handler.handle_error(RVTaskError("Conflict test"))

        # Custom handler should be called
        assert "custom_called" in custom_calls

    def test_decorator_with_method_arguments_and_return_values(self, error_handler):
        """Test decorator preserves method arguments and return values."""

        @ErrorHandler.handle_errors(component="TestClass", phase="method")
        def method_with_args(self, arg1, arg2, kwarg1=None, kwarg2="default"):
            return f"result_{arg1}_{arg2}_{kwarg1}_{kwarg2}"

        # Test with various argument combinations
        class TestClass:
            pass

        instance = TestClass()

        # Normal call should work
        result = method_with_args(instance, "a", "b", kwarg1="c", kwarg2="d")
        assert result == "result_a_b_c_d"

        # With positional args
        result = method_with_args(instance, "x", "y")
        assert result == "result_x_y_None_default"

    def test_decorator_with_generator_functions(self, error_handler):
        """Test decorator with generator functions."""

        @ErrorHandler.handle_errors(component="Generator", reraise=False)
        def error_generator():
            yield 1
            yield 2
            raise RVTaskError("Generator error")
            yield 3  # Should not reach this

        # Generator should work until error
        gen = error_generator()
        assert next(gen) == 1
        assert next(gen) == 2

        # Next call should handle error and stop iteration
        with pytest.raises(StopIteration):
            next(gen)

    def test_decorator_with_async_simulation(self, error_handler):
        """Test decorator behavior with simulated async patterns."""
        execution_log = []

        @ErrorHandler.handle_errors(component="AsyncSimulation", reraise=False)
        def simulated_async_operation(operation_id, should_fail=False):
            execution_log.append(f"start_{operation_id}")

            if should_fail:
                raise RVTaskError(f"Async operation {operation_id} failed")

            execution_log.append(f"success_{operation_id}")
            return f"result_{operation_id}"

        # Simulate multiple async operations
        operations = [
            (1, False),  # Success
            (2, True),  # Failure
            (3, False),  # Success
            (4, True),  # Failure
        ]

        results = []
        for op_id, should_fail in operations:
            result = simulated_async_operation(op_id, should_fail)
            results.append(result)

        # Verify execution pattern
        assert "start_1" in execution_log
        assert "success_1" in execution_log
        assert "start_2" in execution_log
        assert "success_2" not in execution_log  # Failed

        # Results should include successes and None for failures
        assert results[0] == "result_1"
        assert results[1] is None  # Failed operation
        assert results[2] == "result_3"
        assert results[3] is None  # Failed operation

    def test_error_handler_with_class_method_and_static_method(self, error_handler):
        """Test decorator with class methods and static methods."""

        class TestClass:
            @classmethod
            @ErrorHandler.handle_errors(component="ClassMethod", reraise=False)
            def class_method(cls, should_fail=False):
                if should_fail:
                    raise RVTaskError("Class method error")
                return "class_method_success"

            @staticmethod
            @ErrorHandler.handle_errors(component="StaticMethod", reraise=False)
            def static_method(should_fail=False):
                if should_fail:
                    raise RVTaskError("Static method error")
                return "static_method_success"

        # Test class method
        result = TestClass.class_method(should_fail=False)
        assert result == "class_method_success"

        result = TestClass.class_method(should_fail=True)
        assert result is None  # Error handled

        # Test static method
        result = TestClass.static_method(should_fail=False)
        assert result == "static_method_success"

        result = TestClass.static_method(should_fail=True)
        assert result is None  # Error handled

    def test_error_statistics_with_extreme_values(self, error_handler):
        """Test error statistics with extreme values and edge cases."""
        # Test with zero errors
        stats = error_handler.get_error_statistics()
        assert stats["error_counts"] == {}
        assert stats["recent_errors"] == []

        # Generate exactly the history limit
        for i in range(100):
            error_handler.handle_error(RVTaskError(f"Limit test {i}"))

        stats = error_handler.get_error_statistics()
        assert len(stats["recent_errors"]) == 10  # Should return last 10
        assert stats["error_counts"]["RVTaskError"] == 100

        # Clear and verify
        error_handler.clear_statistics()
        stats = error_handler.get_error_statistics()
        assert stats["error_counts"] == {}
        assert stats["recent_errors"] == []

    def test_context_creation_with_special_values(self, error_handler):
        """Test context creation with special values."""
        # Test with various special values
        context = error_handler.create_context(
            none_value=None,
            empty_string="",
            zero_value=0,
            false_value=False,
            empty_list=[],
            empty_dict={},
            unicode_key="🔑",
            nested_value={"inner": {"deep": "value"}}
        )

        # Should preserve all values including falsy ones
        assert context["none_value"] is None
        assert context["empty_string"] == ""
        assert context["zero_value"] == 0
        assert context["false_value"] is False
        assert context["empty_list"] == []
        assert context["empty_dict"] == {}
        assert context["unicode_key"] == "🔑"
        assert context["nested_value"]["inner"]["deep"] == "value"

    def test_global_error_context_with_exceptions_in_context_creation(self):
        """Test global error_context with exceptions during context creation."""
        # This should work even if there are issues with context processing
        with error_context(component="GlobalTest", **{"invalid\x00key": "value"}):
            # Should execute without issues
            pass

    def test_error_handler_repr_and_str_methods(self, error_handler):
        """Test string representations don't cause issues."""
        # These methods might not be explicitly defined but should work
        error = RVTaskError("Test for repr", task_id="test_123")

        # Should be able to convert to string without issues
        str_repr = str(error)
        assert "Test for repr" in str_repr

        # Handle the error
        error_handler.handle_error(error)
        assert "RVTaskError" in error_handler._error_counts

    def test_error_handler_with_weakref_callbacks(self, error_handler):
        """Test error handler behavior with weak reference callbacks."""
        callback_calls = []

        class CallbackHolder:
            def callback_method(self, error, context):
                callback_calls.append("weak_callback_called")
                return False

        holder = CallbackHolder()
        error_handler.register_error_callback(holder.callback_method)

        # Generate error while holder exists
        error_handler.handle_error(RVTaskError("Weak ref test 1"))
        assert len(callback_calls) == 1

        # Delete holder
        del holder
        gc.collect()

        # Generate another error - callback might still work or fail gracefully
        error_handler.handle_error(RVTaskError("Weak ref test 2"))
        # Should not crash regardless of callback state

    def test_error_handler_thread_local_behavior(self, error_handler):
        """Test error handler behavior across different threads."""
        thread_results = {}

        def thread_worker(thread_id):
            # Each thread handles errors independently
            for i in range(5):
                error = RVTaskError(f"Thread {thread_id} error {i}")
                error_handler.handle_error(error, {"thread_id": thread_id})

            # Get statistics from this thread's perspective
            stats = error_handler.get_error_statistics()
            thread_results[thread_id] = stats["error_counts"]["RVTaskError"]

        # Start multiple threads
        threads = [threading.Thread(target=thread_worker, args=(i,)) for i in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All threads should see the same global error count
        expected_total = 25  # 5 threads * 5 errors each
        final_stats = error_handler.get_error_statistics()
        assert final_stats["error_counts"]["RVTaskError"] == expected_total

        # Each thread should have seen the accumulated count
        for thread_id, count in thread_results.items():
            assert count <= expected_total  # Could be any value up to total