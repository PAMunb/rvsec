"""
Unit tests for the CommandCircuitBreaker class.

Tests the circuit breaker pattern implementation for command execution
resilience, including state transitions, failure tracking, and recovery.
"""

import pytest
import threading
import time
from unittest.mock import MagicMock

from rv_android_core.commands.circuit_breaker import CommandCircuitBreaker, CircuitBreakerState
from rv_android_core.commands.command import Command
from rv_android_core.util.exceptions import CircuitBreakerOpenError


class TestCommandCircuitBreaker:
    """Test suite for CommandCircuitBreaker functionality."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.circuit_breaker = CommandCircuitBreaker(failure_threshold=3, retry_count=1)
        self.test_command = Command("echo", ["test"], timeout=30)
        self.failing_command = Command("false", [], timeout=30)

    def test_initial_state_is_closed(self):
        """Test that circuit breaker starts in closed state."""
        state = self.circuit_breaker.get_circuit_state(self.test_command)
        assert state == CircuitBreakerState.CLOSED

    def test_execution_allowed_when_closed(self):
        """Test that execution is allowed when circuit is closed."""
        result = self.circuit_breaker.is_execution_allowed(self.test_command)
        assert result is True

    def test_failure_tracking(self):
        """Test that failures are properly tracked."""
        # Record some failures
        self.circuit_breaker.record_failure(self.test_command)
        self.circuit_breaker.record_failure(self.test_command)
        
        failure_count = self.circuit_breaker.get_failure_count(self.test_command)
        assert failure_count == 2

    def test_circuit_opens_after_threshold(self):
        """Test that circuit opens after failure threshold is reached."""
        # Record failures up to threshold
        for _ in range(3):  # threshold is 3
            self.circuit_breaker.record_failure(self.test_command)
        
        state = self.circuit_breaker.get_circuit_state(self.test_command)
        assert state == CircuitBreakerState.OPEN

    def test_execution_blocked_when_open(self):
        """Test that execution is blocked when circuit is open."""
        # Open the circuit
        for _ in range(3):
            self.circuit_breaker.record_failure(self.test_command)
        
        # Execution should be blocked
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            self.circuit_breaker.is_execution_allowed(self.test_command)
        
        assert "Circuit breaker is open" in str(exc_info.value)
        assert exc_info.value.command_signature is not None
        assert exc_info.value.failure_count == 3

    def test_transition_to_half_open(self):
        """Test transition from open to half-open state."""
        # Open the circuit
        for _ in range(3):
            self.circuit_breaker.record_failure(self.test_command)
        
        # First attempt should be blocked
        with pytest.raises(CircuitBreakerOpenError):
            self.circuit_breaker.is_execution_allowed(self.test_command)
        
        # Second attempt should transition to half-open and allow execution
        result = self.circuit_breaker.is_execution_allowed(self.test_command)
        assert result is True
        
        state = self.circuit_breaker.get_circuit_state(self.test_command)
        assert state == CircuitBreakerState.HALF_OPEN

    def test_success_closes_circuit(self):
        """Test that success closes the circuit."""
        # Open the circuit
        for _ in range(3):
            self.circuit_breaker.record_failure(self.test_command)
        
        # Transition to half-open
        with pytest.raises(CircuitBreakerOpenError):
            self.circuit_breaker.is_execution_allowed(self.test_command)
        self.circuit_breaker.is_execution_allowed(self.test_command)
        
        # Record success
        self.circuit_breaker.record_success(self.test_command)
        
        state = self.circuit_breaker.get_circuit_state(self.test_command)
        assert state == CircuitBreakerState.CLOSED
        
        # Failure count should be reset
        failure_count = self.circuit_breaker.get_failure_count(self.test_command)
        assert failure_count == 0

    def test_failure_in_half_open_reopens_circuit(self):
        """Test that failure in half-open state reopens the circuit."""
        # Open the circuit
        for _ in range(3):
            self.circuit_breaker.record_failure(self.test_command)
        
        # Transition to half-open
        with pytest.raises(CircuitBreakerOpenError):
            self.circuit_breaker.is_execution_allowed(self.test_command)
        self.circuit_breaker.is_execution_allowed(self.test_command)
        
        # Record failure in half-open state
        self.circuit_breaker.record_failure(self.test_command)
        
        state = self.circuit_breaker.get_circuit_state(self.test_command)
        assert state == CircuitBreakerState.OPEN

    def test_different_commands_tracked_separately(self):
        """Test that different commands have separate circuit breaker states."""
        command1 = Command("echo", ["test1"], timeout=30)
        command2 = Command("echo", ["test2"], timeout=30)
        
        # Fail only command1
        for _ in range(3):
            self.circuit_breaker.record_failure(command1)
        
        # command1 should be open, command2 should be closed
        state1 = self.circuit_breaker.get_circuit_state(command1)
        state2 = self.circuit_breaker.get_circuit_state(command2)
        
        assert state1 == CircuitBreakerState.OPEN
        assert state2 == CircuitBreakerState.CLOSED

    def test_reset_circuit(self):
        """Test that circuit can be reset manually."""
        # Open the circuit
        for _ in range(3):
            self.circuit_breaker.record_failure(self.test_command)
        
        assert self.circuit_breaker.get_circuit_state(self.test_command) == CircuitBreakerState.OPEN
        
        # Reset the circuit
        self.circuit_breaker.reset_circuit(self.test_command)
        
        state = self.circuit_breaker.get_circuit_state(self.test_command)
        assert state == CircuitBreakerState.CLOSED
        
        failure_count = self.circuit_breaker.get_failure_count(self.test_command)
        assert failure_count == 0

    def test_command_signature_generation(self):
        """Test that command signatures are generated consistently."""
        command1 = Command("echo", ["test"], timeout=30)
        command2 = Command("echo", ["test"], timeout=30)
        command3 = Command("echo", ["different"], timeout=30)
        
        sig1 = self.circuit_breaker._get_command_signature(command1)
        sig2 = self.circuit_breaker._get_command_signature(command2)
        sig3 = self.circuit_breaker._get_command_signature(command3)
        
        # Same commands should have same signature
        assert sig1 == sig2
        
        # Different commands should have different signatures
        assert sig1 != sig3

    def test_statistics(self):
        """Test that circuit breaker statistics are collected correctly."""
        # Record some failures
        self.circuit_breaker.record_failure(self.test_command)
        self.circuit_breaker.record_failure(self.test_command)
        
        stats = self.circuit_breaker.get_statistics()
        
        assert len(stats) == 1
        command_signature = self.circuit_breaker._get_command_signature(self.test_command)
        assert command_signature in stats
        
        command_stats = stats[command_signature]
        assert command_stats['failure_count'] == 2
        assert command_stats['state'] == CircuitBreakerState.CLOSED.value
        assert command_stats['attempt_count'] == 0

    def test_thread_safety(self):
        """Test that circuit breaker is thread-safe."""
        def record_failures():
            for _ in range(10):
                self.circuit_breaker.record_failure(self.test_command)
        
        def record_successes():
            for _ in range(10):
                self.circuit_breaker.record_success(self.test_command)
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            t1 = threading.Thread(target=record_failures)
            t2 = threading.Thread(target=record_successes)
            threads.extend([t1, t2])
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Circuit breaker should still be in a valid state
        state = self.circuit_breaker.get_circuit_state(self.test_command)
        assert state in [CircuitBreakerState.CLOSED, CircuitBreakerState.OPEN, CircuitBreakerState.HALF_OPEN]

    def test_configurable_thresholds(self):
        """Test that failure threshold and retry count are configurable."""
        # Test with different threshold
        custom_circuit_breaker = CommandCircuitBreaker(failure_threshold=5, retry_count=2)
        
        # Should require 5 failures to open
        for _ in range(4):
            custom_circuit_breaker.record_failure(self.test_command)
        
        state = custom_circuit_breaker.get_circuit_state(self.test_command)
        assert state == CircuitBreakerState.CLOSED
        
        # 5th failure should open it
        custom_circuit_breaker.record_failure(self.test_command)
        state = custom_circuit_breaker.get_circuit_state(self.test_command)
        assert state == CircuitBreakerState.OPEN
        
        # Should require 2 retry attempts before half-open
        with pytest.raises(CircuitBreakerOpenError):
            custom_circuit_breaker.is_execution_allowed(self.test_command)
        
        with pytest.raises(CircuitBreakerOpenError):
            custom_circuit_breaker.is_execution_allowed(self.test_command)
        
        # Third attempt should transition to half-open
        result = custom_circuit_breaker.is_execution_allowed(self.test_command)
        assert result is True
        
        state = custom_circuit_breaker.get_circuit_state(self.test_command)
        assert state == CircuitBreakerState.HALF_OPEN

    def test_empty_args_command(self):
        """Test circuit breaker with commands that have no arguments."""
        empty_command = Command("pwd", [], timeout=30)
        
        # Should work normally
        result = self.circuit_breaker.is_execution_allowed(empty_command)
        assert result is True
        
        self.circuit_breaker.record_failure(empty_command)
        failure_count = self.circuit_breaker.get_failure_count(empty_command)
        assert failure_count == 1