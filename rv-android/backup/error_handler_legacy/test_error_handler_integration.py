import pytest
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager

from rv_android_core.util.error.error_handler import ErrorHandler, error_context
from rv_android_core.util.exceptions import (
    RVAndroidError, RVTaskError, RVTaskExecutionError, RVTaskConfigurationError,
    RVToolError, RVToolExecutionError, RVToolConfigurationError,
    RVExperimentError, RVExperimentSetupError, RVExperimentExecutionError,
    RVParsingError, RVLLMError, RVPromptError
)


class TestErrorHandlerIntegration:
    """Integration tests for ErrorHandler with real scenarios."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test."""
        ErrorHandler._instance = None
        yield
        ErrorHandler._instance = None

    @pytest.fixture
    def mock_logging_manager(self):
        """Mock LoggingManager for integration testing."""
        with patch('rv_android_core.util.error.error_handler.LoggingManager') as mock_manager:
            mock_instance = Mock()
            mock_logger = Mock()
            mock_logger.with_context.return_value = contextmanager(lambda: (yield mock_logger))()
            mock_instance.get_logger.return_value = mock_logger
            mock_manager.get_instance.return_value = mock_instance
            yield mock_manager, mock_instance, mock_logger

    @pytest.fixture
    def error_handler(self, mock_logging_manager):
        """Create ErrorHandler instance for integration testing."""
        return ErrorHandler.get_instance()

    def test_real_world_task_execution_scenario(self, error_handler):
        """Test a real-world task execution error scenario."""
        # Simulate a task execution pipeline with multiple error points
        task_id = "integration_task_001"

        # Custom handler for task errors
        task_errors_handled = []

        def task_error_handler(error, context):
            if isinstance(error, RVTaskError):
                task_errors_handled.append({
                    'error': error,
                    'context': context,
                    'timestamp': time.time()
                })
                return True
            return False

        error_handler.register_handler(RVTaskError, task_error_handler)

        # Simulate task configuration error
        with error_handler.error_context(component="TaskExecutor", phase="configuration"):
            config_error = RVTaskConfigurationError(
                "Failed to parse task configuration",
                task_id=task_id
            )
            error_handler.handle_error(config_error, {"config_file": "task.json"})

        # Simulate task execution error
        with error_handler.error_context(component="TaskExecutor", phase="execution"):
            exec_error = RVTaskExecutionError(
                "Task execution failed due to tool crash",
                task_id=task_id
            )
            error_handler.handle_error(exec_error, {"step": "tool_launch"})

        # Verify both errors were handled
        assert len(task_errors_handled) == 2
        assert any("configuration" in str(e['error']) for e in task_errors_handled)
        assert any("execution" in str(e['error']) for e in task_errors_handled)

        # Verify statistics
        stats = error_handler.get_error_statistics()
        assert stats["error_counts"]["RVTaskConfigurationError"] == 1
        assert stats["error_counts"]["RVTaskExecutionError"] == 1

    def test_tool_chain_error_propagation(self, error_handler):
        """Test error propagation through a tool execution chain."""
        tool_execution_log = []

        def tool_error_logger(error, context):
            tool_execution_log.append({
                'tool': getattr(error, 'tool_name', 'unknown'),
                'message': error.message if hasattr(error, 'message') else str(error),
                'context': context
            })
            return False  # Don't handle, just log

        error_handler.register_handler(RVToolError, tool_error_logger)

        # Simulate tool chain: Monkey -> DroidBot -> Custom Tool
        tools = [
            ("monkey", "Monkey tool crashed during event generation"),
            ("droidbot", "DroidBot failed to connect to device"),
            ("custom_tool", "Custom tool timeout after 300 seconds")
        ]

        for tool_name, error_msg in tools:
            with error_handler.error_context(component="ToolRunner", phase="execution"):
                tool_error = RVToolExecutionError(error_msg, tool_name=tool_name)
                error_handler.handle_error(tool_error, {"timeout": 300, "device": "emulator-5554"})

        # Verify all tools were logged
        assert len(tool_execution_log) == 3
        logged_tools = [entry['tool'] for entry in tool_execution_log]
        assert "monkey" in logged_tools
        assert "droidbot" in logged_tools
        assert "custom_tool" in logged_tools

    def test_experiment_lifecycle_error_handling(self, error_handler):
        """Test error handling throughout an experiment lifecycle."""
        experiment_id = "exp_integration_001"
        experiment_errors = []

        @ErrorHandler.handle_errors(component="ExperimentRunner", phase="lifecycle")
        def simulate_experiment_phase(phase_name, should_fail=False):
            if should_fail:
                if phase_name == "setup":
                    raise RVExperimentSetupError(
                        f"Setup failed in {phase_name}",
                        experiment_id=experiment_id
                    )
                elif phase_name == "execution":
                    raise RVExperimentExecutionError(
                        f"Execution failed in {phase_name}",
                        experiment_id=experiment_id
                    )
            return f"{phase_name}_success"

        # Track experiment errors
        def experiment_error_tracker(error, context):
            if isinstance(error, RVExperimentError):
                experiment_errors.append({
                    'phase': context.get('phase', 'unknown'),
                    'error_type': type(error).__name__,
                    'experiment_id': getattr(error, 'experiment_id', None)
                })
            return False

        error_handler.register_handler(RVExperimentError, experiment_error_tracker)

        # Simulate experiment phases
        phases = [
            ("initialization", False),
            ("setup", True),  # This will fail
            ("execution", True),  # This will also fail
            ("cleanup", False)
        ]

        for phase_name, should_fail in phases:
            result = simulate_experiment_phase(phase_name, should_fail)
            if not should_fail:
                assert result == f"{phase_name}_success"

        # Verify experiment errors were tracked
        assert len(experiment_errors) == 2
        assert any(e['error_type'] == 'RVExperimentSetupError' for e in experiment_errors)
        assert any(e['error_type'] == 'RVExperimentExecutionError' for e in experiment_errors)

    def test_llm_and_prompt_error_integration(self, error_handler):
        """Test LLM and prompt error handling integration."""
        llm_interactions = []

        def llm_error_handler(error, context):
            if isinstance(error, (RVLLMError, RVPromptError)):
                llm_interactions.append({
                    'error_type': type(error).__name__,
                    'model': getattr(error, 'model_name', None),
                    'strategy': getattr(error, 'strategy_name', None),
                    'context': context
                })
                # Handle prompt errors but not LLM errors
                return isinstance(error, RVPromptError)
            return False

        error_handler.register_handler(RVLLMError, llm_error_handler)
        error_handler.register_handler(RVPromptError, llm_error_handler)

        # Simulate LLM processing chain
        with error_handler.error_context(component="LLMProcessor", phase="generation"):
            # Prompt strategy error (should be handled)
            prompt_error = RVPromptError(
                "Invalid prompt template",
                strategy="completion_strategy"
            )
            error_handler.handle_error(prompt_error, {"template": "invalid.txt"})

            # LLM model error (should not be handled)
            llm_error = RVLLMError(
                "Model timeout after 60 seconds",
                model_name="gpt-4"
            )
            error_handler.handle_error(llm_error, {"timeout": 60})

        # Verify interactions
        assert len(llm_interactions) == 2
        prompt_interaction = next(i for i in llm_interactions if i['error_type'] == 'RVPromptError')
        llm_interaction = next(i for i in llm_interactions if i['error_type'] == 'RVLLMError')

        assert prompt_interaction['strategy'] == "completion_strategy"
        assert llm_interaction['model'] == "gpt-4"

    def test_parsing_error_with_different_parsers(self, error_handler):
        """Test parsing error handling with different parser types."""
        parsing_results = []

        def parsing_error_handler(error, context):
            if isinstance(error, RVParsingError):
                parsing_results.append({
                    'parser_type': getattr(error, 'parser_type', 'unknown'),
                    'file': context.get('file', 'unknown'),
                    'line': context.get('line', -1)
                })
                return True  # Handle all parsing errors
            return False

        error_handler.register_handler(RVParsingError, parsing_error_handler)

        # Simulate different parser failures
        parsers = [
            ("xml", "config.xml", 42),
            ("json", "data.json", 15),
            ("csv", "results.csv", 100),
            ("yaml", "settings.yaml", 8)
        ]

        for parser_type, filename, line_num in parsers:
            with error_handler.error_context(component="DataParser", phase="parsing"):
                parse_error = RVParsingError(
                    f"Parse error in {filename}",
                    parser_type=parser_type
                )
                error_handler.handle_error(
                    parse_error,
                    {"file": filename, "line": line_num}
                )

        # Verify all parsing errors were handled
        assert len(parsing_results) == 4
        parser_types = [r['parser_type'] for r in parsing_results]
        assert set(parser_types) == {"xml", "json", "csv", "yaml"}

    def test_error_handler_with_complex_inheritance_chain(self, error_handler):
        """Test error handling with complex inheritance chains."""
        inheritance_tracking = []

        def track_error_hierarchy(error, context):
            inheritance_tracking.append({
                'error_class': error.__class__.__name__,
                'mro': [cls.__name__ for cls in error.__class__.__mro__],
                'is_rv_android_error': isinstance(error, RVAndroidError),
                'is_task_error': isinstance(error, RVTaskError),
                'is_execution_error': isinstance(error, RVTaskExecutionError)
            })
            return False

        error_handler.register_error_callback(track_error_hierarchy)

        # Test with different levels of inheritance
        errors = [
            RVAndroidError("Base error"),
            RVTaskError("Task error", task_id="test"),
            RVTaskExecutionError("Execution error", task_id="test"),
            RVTaskConfigurationError("Config error", task_id="test")
        ]

        for error in errors:
            error_handler.handle_error(error)

        # Verify inheritance tracking
        assert len(inheritance_tracking) == 4

        # Check base error
        base_tracking = inheritance_tracking[0]
        assert base_tracking['error_class'] == 'RVAndroidError'
        assert base_tracking['is_rv_android_error'] is True
        assert base_tracking['is_task_error'] is False

        # Check task execution error
        exec_tracking = inheritance_tracking[2]
        assert exec_tracking['error_class'] == 'RVTaskExecutionError'
        assert exec_tracking['is_rv_android_error'] is True
        assert exec_tracking['is_task_error'] is True
        assert exec_tracking['is_execution_error'] is True

    def test_concurrent_error_handling_with_shared_state(self, error_handler):
        """Test concurrent error handling with shared state modification."""
        shared_state = {"counter": 0, "errors": []}
        state_lock = threading.Lock()

        def stateful_error_handler(error, context):
            with state_lock:
                shared_state["counter"] += 1
                shared_state["errors"].append({
                    "thread_id": threading.current_thread().ident,
                    "error_type": type(error).__name__,
                    "timestamp": time.time()
                })
            return True

        error_handler.register_handler(RVTaskError, stateful_error_handler)

        def worker_thread(thread_id):
            for i in range(5):
                error = RVTaskError(f"Thread {thread_id} error {i}")
                error_handler.handle_error(error, {"thread_id": thread_id, "iteration": i})
                time.sleep(0.01)  # Small delay to increase chance of race conditions

        # Start multiple worker threads
        threads = [threading.Thread(target=worker_thread, args=(i,)) for i in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Verify shared state consistency
        assert shared_state["counter"] == 50  # 10 threads * 5 errors each
        assert len(shared_state["errors"]) == 50

        # Verify all threads contributed
        thread_ids = set(error["thread_id"] for error in shared_state["errors"])
        assert len(thread_ids) == 10

    def test_error_handler_callback_ordering(self, error_handler):
        """Test that error handler callbacks are executed in registration order."""
        execution_order = []

        def callback_1(error, context):
            execution_order.append("callback_1")
            return False

        def callback_2(error, context):
            execution_order.append("callback_2")
            return False

        def callback_3(error, context):
            execution_order.append("callback_3")
            return True  # This one handles the error

        def callback_4(error, context):
            execution_order.append("callback_4")
            return False  # Should not be called since callback_3 handled it

        # Register callbacks in specific order
        error_handler.register_error_callback(callback_1)
        error_handler.register_error_callback(callback_2)
        error_handler.register_error_callback(callback_3)
        error_handler.register_error_callback(callback_4)

        # Handle an error
        error_handler.handle_error(RVTaskError("Test error"))

        # Verify execution order (callback_4 should not be called)
        assert execution_order == ["callback_1", "callback_2", "callback_3"]

    def test_error_context_nesting(self, error_handler):
        """Test nested error contexts."""
        context_stack = []

        def context_tracker(error, context):
            context_stack.append(context.copy())
            return False

        error_handler.register_error_callback(context_tracker)

        # Test nested contexts
        with error_handler.error_context(component="OuterComponent", level="1"):
            with error_handler.error_context(component="InnerComponent", level="2"):
                with error_handler.error_context(component="DeepComponent", level="3"):
                    error_handler.handle_error(RVTaskError("Nested context error"))

        # Verify deepest context was used
        assert len(context_stack) == 1
        context = context_stack[0]
        assert context["component"] == "DeepComponent"
        assert context["level"] == "3"

    def test_error_handler_with_circular_references(self, error_handler):
        """Test error handler behavior with circular references in context."""
        # Create circular reference in context
        context_a = {"name": "A"}
        context_b = {"name": "B", "ref": context_a}
        context_a["ref"] = context_b

        # Should handle circular references gracefully
        try:
            error_handler.handle_error(RVTaskError("Circular reference test"), context_a)
            # If we get here, the handler managed the circular reference
            assert "RVTaskError" in error_handler._error_counts
        except RecursionError:
            pytest.fail("Error handler should handle circular references gracefully")

    def test_error_handler_memory_efficiency(self, error_handler):
        """Test memory efficiency with large error contexts."""
        import sys

        # Create a large context
        large_context = {
            f"key_{i}": f"value_{i}" * 100 for i in range(1000)
        }

        # Measure memory before
        initial_size = sys.getsizeof(error_handler._error_history)

        # Handle error with large context
        error_handler.handle_error(RVTaskError("Large context test"), large_context)

        # Verify error was handled
        assert "RVTaskError" in error_handler._error_counts

        # History should not grow unboundedly large
        final_size = sys.getsizeof(error_handler._error_history)
        # Allow some growth but not proportional to context size
        assert (final_size - initial_size) < len(str(large_context))

    def test_error_handler_with_exception_during_logging(self, error_handler, mock_logging_manager):
        """Test error handler behavior when logging itself fails."""
        _, _, mock_logger = mock_logging_manager

        # Make logger raise exception
        mock_logger.error.side_effect = Exception("Logging failed")

        # Should still handle the error gracefully
        try:
            error_handler.handle_error(RVTaskError("Test with logging failure"))
            # Error should still be counted even if logging fails
            assert "RVTaskError" in error_handler._error_counts
        except Exception as e:
            # Should not propagate logging exceptions
            pytest.fail(f"Error handler should not propagate logging exceptions: {e}")

    def test_global_error_context_with_nested_calls(self):
        """Test global error_context function with nested function calls."""
        call_stack = []

        def level_1():
            call_stack.append("level_1_start")
            with error_context(component="Level1", function="level_1"):
                level_2()
            call_stack.append("level_1_end")

        def level_2():
            call_stack.append("level_2_start")
            with error_context(component="Level2", function="level_2"):
                level_3()
            call_stack.append("level_2_end")

        def level_3():
            call_stack.append("level_3_start")
            with error_context(component="Level3", function="level_3"):
                # This should work without issues
                pass
            call_stack.append("level_3_end")

        # Execute nested calls
        level_1()

        # Verify all levels executed
        expected_stack = [
            "level_1_start", "level_2_start", "level_3_start",
            "level_3_end", "level_2_end", "level_1_end"
        ]
        assert call_stack == expected_stack