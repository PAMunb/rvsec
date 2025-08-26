# rvandroid/commands/circuit_breaker.py
"""
Circuit breaker pattern implementation for command execution resilience.

This module provides command-specific circuit breaker functionality to prevent
cascading failures in tool execution by temporarily disabling commands that
consistently fail.
"""

import hashlib
import threading
import time
from enum import Enum
from typing import Dict, Optional

from rv_android_core.commands.command import Command
from rv_android_core.util.error.exceptions import CircuitBreakerOpenError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class CircuitBreakerState(Enum):
    """
    Circuit breaker state enumeration.
    
    ### State Transitions:
    - CLOSED: Normal operation, commands execute normally
    - OPEN: Circuit breaker activated, commands are blocked
    - HALF_OPEN: Testing phase, limited commands allowed to test recovery
    """
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CommandCircuitBreaker:
    """
    Circuit breaker for command execution with failure tracking and recovery.
    
    ### Architectural Decisions:
    - Implements command-specific failure tracking to prevent cascading failures
    - Uses configurable thresholds for failure detection and recovery attempts
    - Provides state management for normal operation, protection, and testing phases
    - Integrates with existing logging infrastructure for monitoring and debugging
    - Supports thread-safe operations for concurrent command execution scenarios
    
    ### Role in the System:
    - Acts as a protective layer for command execution in tool workflows
    - Prevents resource exhaustion from repeatedly failing commands
    - Enables graceful degradation when commands consistently fail
    - Provides automatic recovery testing after failure periods
    - Facilitates system stability in tool execution environments
    
    ### Key Considerations:
    - Focuses on command execution failures, not timeout scenarios
    - Maintains per-command failure statistics for granular control
    - Supports configurable failure thresholds and retry counts
    - Provides clear state transitions and recovery mechanisms
    - Integrates with error handling infrastructure for consistent behavior
    
    ### Integration Strategy:
    - Designed for integration with AbstractTool command execution
    - Compatible with existing Command class without modification
    - Supports tool-level circuit breaker policies and configurations
    - Enables monitoring and metrics collection for system analysis
    - Provides clear extension points for custom circuit breaker behaviors
    
    ### Performance and Scalability:
    - Uses lightweight failure tracking with minimal memory overhead
    - Implements efficient command signature generation for identification
    - Supports concurrent access with thread-safe operations
    - Provides fast state checking for command execution decisions
    - Scales to handle multiple concurrent tool executions
    """

    def __init__(self, failure_threshold: int = 3, retry_count: int = 1):
        """
        Initialize circuit breaker with configurable parameters.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            retry_count: Number of attempts before transitioning to half-open
        """
        self.failure_threshold = failure_threshold
        self.retry_count = retry_count
        
        # Command-specific failure tracking
        self._failure_counts: Dict[str, int] = {}
        self._last_failure_time: Dict[str, float] = {}
        self._circuit_states: Dict[str, CircuitBreakerState] = {}
        self._attempt_counts: Dict[str, int] = {}
        
        # Thread safety for concurrent access
        self._lock = threading.Lock()
        
        # Initialize logging with context
        logging_manager = LoggingManager.get_instance()
        self._logger = logging_manager.get_logger(
            'rv_android_core.commands.circuit_breaker',
            {
                CONTEXT_COMPONENT: 'CommandCircuitBreaker'
            }
        )
    
    def _get_command_signature(self, command: Command) -> str:
        """
        Generate unique signature for command identification.
        
        Creates a hash-based signature from command and arguments for
        efficient command identification and failure tracking.
        
        Args:
            command: Command instance to generate signature for
            
        Returns:
            Unique string signature for the command
        """
        # Create signature from command and arguments using SHA-256
        signature_data = f"{command.command}:{':'.join(command.args)}"
        return hashlib.sha256(signature_data.encode()).hexdigest()[:16]
    
    def _get_circuit_state(self, command_signature: str) -> CircuitBreakerState:
        """
        Get current circuit state for command signature.
        
        Args:
            command_signature: Command signature to check
            
        Returns:
            Current circuit breaker state
        """
        return self._circuit_states.get(command_signature, CircuitBreakerState.CLOSED)
    
    def _set_circuit_state(self, command_signature: str, state: CircuitBreakerState):
        """
        Set circuit state for command signature.
        
        Args:
            command_signature: Command signature to update
            state: New circuit breaker state
        """
        self._circuit_states[command_signature] = state
        self._logger.debug(f"Circuit breaker state changed to {state.value} for command {command_signature}")
    
    def is_execution_allowed(self, command: Command) -> bool:
        """
        Check if command execution is allowed based on circuit breaker state.
        
        Determines whether a command should be executed based on its failure
        history and current circuit breaker state.
        
        Args:
            command: Command to check for execution permission
            
        Returns:
            True if execution is allowed, False if blocked
            
        Raises:
            CircuitBreakerOpenError: If circuit breaker is open for this command
        """
        with self._lock:
            command_signature = self._get_command_signature(command)
            state = self._get_circuit_state(command_signature)
            
            if state == CircuitBreakerState.CLOSED:
                # Normal operation - execution allowed
                return True
            
            elif state == CircuitBreakerState.OPEN:
                # Check if we should transition to half-open
                attempt_count = self._attempt_counts.get(command_signature, 0)
                
                if attempt_count >= self.retry_count:
                    # Transition to half-open for testing
                    self._set_circuit_state(command_signature, CircuitBreakerState.HALF_OPEN)
                    self._attempt_counts[command_signature] = 0
                    self._logger.info(f"Circuit breaker transitioning to half-open for command {command_signature}")
                    return True
                else:
                    # Still in open state - block execution
                    self._attempt_counts[command_signature] = attempt_count + 1
                    failure_count = self._failure_counts.get(command_signature, 0)
                    
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker is open for command execution",
                        command_signature=command_signature,
                        failure_count=failure_count
                    )
            
            elif state == CircuitBreakerState.HALF_OPEN:
                # Testing phase - allow limited execution
                return True
            
            return False
    
    def record_success(self, command: Command):
        """
        Record successful command execution.
        
        Resets failure counters and closes circuit breaker for successful
        command execution, enabling normal operation.
        
        Args:
            command: Command that executed successfully
        """
        with self._lock:
            command_signature = self._get_command_signature(command)
            
            # Reset failure tracking
            self._failure_counts[command_signature] = 0
            self._attempt_counts[command_signature] = 0
            
            # Close circuit breaker
            self._set_circuit_state(command_signature, CircuitBreakerState.CLOSED)
            
            self._logger.debug(f"Circuit breaker closed after successful execution for command {command_signature}")
    
    def record_failure(self, command: Command):
        """
        Record failed command execution.
        
        Increments failure counter and opens circuit breaker if threshold
        is exceeded, preventing further execution attempts.
        
        Args:
            command: Command that failed during execution
        """
        with self._lock:
            command_signature = self._get_command_signature(command)
            current_state = self._get_circuit_state(command_signature)
            
            # Increment failure count
            failure_count = self._failure_counts.get(command_signature, 0) + 1
            self._failure_counts[command_signature] = failure_count
            self._last_failure_time[command_signature] = time.time()
            
            self._logger.debug(f"Recorded failure #{failure_count} for command {command_signature}")
            
            # Check if threshold exceeded
            if failure_count >= self.failure_threshold:
                if current_state == CircuitBreakerState.HALF_OPEN:
                    # Failed during testing - reopen circuit
                    self._set_circuit_state(command_signature, CircuitBreakerState.OPEN)
                    self._attempt_counts[command_signature] = 0
                    self._logger.warning(f"Circuit breaker reopened after failed test for command {command_signature}")
                    
                elif current_state == CircuitBreakerState.CLOSED:
                    # First time opening circuit
                    self._set_circuit_state(command_signature, CircuitBreakerState.OPEN)
                    self._attempt_counts[command_signature] = 0
                    self._logger.warning(f"Circuit breaker opened after {failure_count} failures for command {command_signature}")
    
    def get_failure_count(self, command: Command) -> int:
        """
        Get failure count for specific command.
        
        Args:
            command: Command to get failure count for
            
        Returns:
            Number of recorded failures for the command
        """
        with self._lock:
            command_signature = self._get_command_signature(command)
            return self._failure_counts.get(command_signature, 0)
    
    def get_circuit_state(self, command: Command) -> CircuitBreakerState:
        """
        Get current circuit breaker state for command.
        
        Args:
            command: Command to check state for
            
        Returns:
            Current circuit breaker state
        """
        with self._lock:
            command_signature = self._get_command_signature(command)
            return self._get_circuit_state(command_signature)
    
    def reset_circuit(self, command: Command):
        """
        Reset circuit breaker state for specific command.
        
        Clears failure history and resets circuit breaker to closed state,
        useful for manual recovery or testing scenarios.
        
        Args:
            command: Command to reset circuit breaker for
        """
        with self._lock:
            command_signature = self._get_command_signature(command)
            
            # Clear all tracking data
            self._failure_counts[command_signature] = 0
            self._attempt_counts[command_signature] = 0
            self._last_failure_time.pop(command_signature, None)
            
            # Close circuit
            self._set_circuit_state(command_signature, CircuitBreakerState.CLOSED)
            
            self._logger.info(f"Circuit breaker reset for command {command_signature}")
    
    def get_statistics(self) -> Dict[str, Dict[str, any]]:
        """
        Get circuit breaker statistics for monitoring.
        
        Returns:
            Dictionary containing failure counts, states, and timing information
        """
        with self._lock:
            stats = {}
            
            for command_sig in self._failure_counts:
                stats[command_sig] = {
                    'failure_count': self._failure_counts.get(command_sig, 0),
                    'state': self._get_circuit_state(command_sig).value,
                    'attempt_count': self._attempt_counts.get(command_sig, 0),
                    'last_failure_time': self._last_failure_time.get(command_sig, 0)
                }
            
            return stats