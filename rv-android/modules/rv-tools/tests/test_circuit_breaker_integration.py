"""
Integration tests for circuit breaker functionality with rv-tools.

Tests the integration of circuit breaker pattern with tool execution
and registry components in the rv-tools module.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from rv_tools.registry.registry import ToolRegistry
from rv_tools.registry.factory import ToolFactory
from rv_android_core.commands.circuit_breaker import CommandCircuitBreaker, CircuitBreakerState
from rv_android_core.commands.command import Command
from rv_android_core.util.error.exceptions import CircuitBreakerOpenError, RVToolExecutionError
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec


class MockFailingTool(AbstractTool):
    """Mock tool that can be configured to fail for testing circuit breaker."""

    def __init__(self, name="mock_failing_tool", description="Mock tool for testing", process_pattern="mock"):
        super().__init__(name, description, process_pattern)
        self.should_fail = False
        self.execution_count = 0

    def execute_tool_specific_logic(self, task, app):
        """Execute tool logic, fail if configured to do so."""
        self.execution_count += 1
        
        if self.should_fail:
            # Create a failing command to trigger circuit breaker
            failing_command = Command("false", [], timeout=30)
            with open(task.result.trace_file, 'wb') as trace_file:
                self._execute_and_check_command(failing_command, stdout=trace_file)
        else:
            # Create a successful command
            success_command = Command("echo", ["success"], timeout=30)
            with open(task.result.trace_file, 'wb') as trace_file:
                self._execute_and_check_command(success_command, stdout=trace_file)


class TestCircuitBreakerIntegration:
    """Test suite for circuit breaker integration with tools."""

    def setup_method(self):
        """Set up test environment before each test."""
        # Reset tool registry for clean tests
        ToolRegistry.reset_instance()
        self.registry = ToolRegistry.get_instance()
        
        # Create temporary file for trace file
        self.temp_trace_file = tempfile.NamedTemporaryFile(mode='w+b', delete=False)
        self.temp_trace_file.close()
        
        # Create mock task and app
        self.mock_task = Mock()
        self.mock_task.id = "test_task_123"
        self.mock_task.result = Mock()
        self.mock_task.result.trace_file = self.temp_trace_file.name
        
        self.mock_app = Mock()
        self.mock_app.name = "test.apk"
        self.mock_app.package_name = "com.test.app"
    
    def teardown_method(self):
        """Clean up test environment after each test."""
        # Clean up temporary trace file
        try:
            os.unlink(self.temp_trace_file.name)
        except (OSError, FileNotFoundError):
            pass  # File might already be deleted

    def test_circuit_breaker_opens_after_failures(self):
        """Test that circuit breaker opens after consecutive failures."""
        # Arrange
        tool = MockFailingTool()
        tool.should_fail = True
        
        # Configure circuit breaker with low threshold for testing
        tool.circuit_breaker = CommandCircuitBreaker(failure_threshold=2, retry_count=1)
        
        # Mock file operations
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            # First failure
            with pytest.raises(RVToolExecutionError):
                tool.execute(self.mock_task, self.mock_app)
            
            # Second failure - should open circuit breaker
            with pytest.raises(RVToolExecutionError):
                tool.execute(self.mock_task, self.mock_app)
            
            # Third attempt - should be blocked by circuit breaker
            with pytest.raises(CircuitBreakerOpenError):
                tool.execute(self.mock_task, self.mock_app)

    def test_circuit_breaker_recovery_after_success(self):
        """Test that circuit breaker closes after successful execution."""
        # Arrange
        tool = MockFailingTool()
        tool.circuit_breaker = CommandCircuitBreaker(failure_threshold=2, retry_count=1)
        
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            # Cause failures to open circuit breaker
            tool.should_fail = True
            with pytest.raises(RVToolExecutionError):
                tool.execute(self.mock_task, self.mock_app)
            with pytest.raises(RVToolExecutionError):
                tool.execute(self.mock_task, self.mock_app)
            
            # Verify circuit is open
            with pytest.raises(CircuitBreakerOpenError):
                tool.execute(self.mock_task, self.mock_app)
            
            # Allow one execution (transition to half-open)
            tool.should_fail = False
            tool.execute(self.mock_task, self.mock_app)  # Should succeed and close circuit
            
            # Verify circuit is closed - next execution should work
            tool.execute(self.mock_task, self.mock_app)

    def test_different_tools_have_separate_circuit_breakers(self):
        """Test that different tool instances have separate circuit breaker states."""
        # Arrange
        tool1 = MockFailingTool(name="tool1")
        tool2 = MockFailingTool(name="tool2")
        
        # Configure both with low thresholds
        tool1.circuit_breaker = CommandCircuitBreaker(failure_threshold=2, retry_count=1)
        tool2.circuit_breaker = CommandCircuitBreaker(failure_threshold=2, retry_count=1)
        
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            # Fail tool1 enough to open its circuit breaker
            tool1.should_fail = True
            with pytest.raises(RVToolExecutionError):
                tool1.execute(self.mock_task, self.mock_app)
            with pytest.raises(RVToolExecutionError):
                tool1.execute(self.mock_task, self.mock_app)
            
            # tool1 should be blocked
            with pytest.raises(CircuitBreakerOpenError):
                tool1.execute(self.mock_task, self.mock_app)
            
            # tool2 should still work (separate circuit breaker)
            tool2.should_fail = False
            tool2.execute(self.mock_task, self.mock_app)  # Should succeed


    def test_circuit_breaker_statistics_tracking(self):
        """Test that circuit breaker statistics are properly tracked."""
        # Arrange
        tool = MockFailingTool()
        tool.circuit_breaker = CommandCircuitBreaker(failure_threshold=3, retry_count=2)
        
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            # Initial state - no statistics
            stats = tool.circuit_breaker.get_statistics()
            assert len(stats) == 0
            
            # Record some failures
            tool.should_fail = True
            with pytest.raises(RVToolExecutionError):
                tool.execute(self.mock_task, self.mock_app)
            with pytest.raises(RVToolExecutionError):
                tool.execute(self.mock_task, self.mock_app)
            
            # Check statistics
            stats = tool.circuit_breaker.get_statistics()
            assert len(stats) == 1
            
            # Get the command signature (there should be one entry)
            command_signature = list(stats.keys())[0]
            command_stats = stats[command_signature]
            
            assert command_stats['failure_count'] == 2
            assert command_stats['state'] == CircuitBreakerState.CLOSED.value
            
            # Trigger circuit breaker opening
            with pytest.raises(RVToolExecutionError):
                tool.execute(self.mock_task, self.mock_app)
            
            # Check updated statistics
            stats = tool.circuit_breaker.get_statistics()
            command_stats = stats[command_signature]
            assert command_stats['failure_count'] == 3
            assert command_stats['state'] == CircuitBreakerState.OPEN.value

    def test_circuit_breaker_reset_functionality(self):
        """Test manual circuit breaker reset functionality."""
        # Arrange
        tool = MockFailingTool()
        tool.circuit_breaker = CommandCircuitBreaker(failure_threshold=2, retry_count=1)
        
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            # Open circuit breaker with failures
            tool.should_fail = True
            with pytest.raises(RVToolExecutionError):
                tool.execute(self.mock_task, self.mock_app)
            with pytest.raises(RVToolExecutionError):
                tool.execute(self.mock_task, self.mock_app)
            
            # Verify circuit is open
            with pytest.raises(CircuitBreakerOpenError):
                tool.execute(self.mock_task, self.mock_app)
            
            # Reset circuit breaker manually
            test_command = Command("false", [], timeout=30)
            tool.circuit_breaker.reset_circuit(test_command)
            
            # Verify circuit is now closed and allows execution
            tool.should_fail = False
            tool.execute(self.mock_task, self.mock_app)  # Should succeed

    def test_circuit_breaker_thread_safety_integration(self):
        """Test circuit breaker thread safety in tool execution context."""
        import threading
        import time

        # Arrange
        tool = MockFailingTool()
        tool.circuit_breaker = CommandCircuitBreaker(failure_threshold=5, retry_count=2)
        execution_results = []
        
        def execute_tool_repeatedly():
            """Execute tool multiple times and collect results."""
            # Create a separate temporary file for each thread to avoid conflicts
            thread_temp_file = tempfile.NamedTemporaryFile(mode='w+b', delete=False)
            thread_temp_file.close()
            
            # Create a separate mock task for each thread
            thread_mock_task = Mock()
            thread_mock_task.id = f"test_task_{threading.current_thread().ident}"
            thread_mock_task.result = Mock()
            thread_mock_task.result.trace_file = thread_temp_file.name
            
            try:
                for i in range(10):
                    try:
                        # Alternate between success and failure
                        tool.should_fail = (i % 3 == 0)  # Fail every 3rd execution
                        tool.execute(thread_mock_task, self.mock_app)
                        execution_results.append(f"thread_{threading.current_thread().ident}_success_{i}")
                    except (RVToolExecutionError, CircuitBreakerOpenError) as e:
                        execution_results.append(f"thread_{threading.current_thread().ident}_failed_{i}_{type(e).__name__}")
                    
                    # Small delay to allow thread interleaving
                    time.sleep(0.001)
            finally:
                # Clean up thread-specific temporary file
                try:
                    os.unlink(thread_temp_file.name)
                except (OSError, FileNotFoundError):
                    pass
        
        # Start multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=execute_tool_repeatedly)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify that we got results from all threads and no crashes occurred
        assert len(execution_results) == 30  # 3 threads * 10 executions each
        
        # Verify circuit breaker is still in a valid state
        test_command = Command("echo", ["test"], timeout=30)
        state = tool.circuit_breaker.get_circuit_state(test_command)
        assert state in [CircuitBreakerState.CLOSED, CircuitBreakerState.OPEN, CircuitBreakerState.HALF_OPEN]