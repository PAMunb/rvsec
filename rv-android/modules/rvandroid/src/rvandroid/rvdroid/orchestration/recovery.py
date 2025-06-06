# rvandroid/rvdroid/orchestration/recovery.py

"""
Error recovery system for RVDroid.

This module provides components for detecting and recovering from
errors during testing, ensuring robustness and resilience.
"""

from enum import Enum, auto
from typing import Dict, Any, Optional, Callable, List, Tuple

from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.performance_monitor import PerformanceMonitor


class ErrorSeverity(Enum):
    """
    Severity levels for errors encountered during testing.
    
    These levels help prioritize and determine appropriate recovery strategies.
    """
    LOW = auto()      # Minor issues that don't affect testing flow
    MEDIUM = auto()   # Issues that affect current operation but can be recovered
    HIGH = auto()     # Serious issues requiring significant recovery effort
    CRITICAL = auto() # Fatal issues that may require restarting the app/emulator


class RecoveryStrategy(Enum):
    """
    Recovery strategies for different error types.
    
    These strategies represent increasingly aggressive approaches to recovery.
    """
    RETRY = auto()           # Simple retry of the failed operation
    ALTERNATIVE = auto()     # Try an alternative approach to achieve the same goal
    BACK_NAVIGATION = auto() # Navigate back and try a different path
    APP_RESET = auto()       # Reset the application state
    EMULATOR_RESET = auto()  # Reset the emulator (last resort)


class RecoveryManager:
    """
    Manager for error detection and recovery in RVDroid.
    
    ### Architectural Decisions:
    - Implements a hierarchical error recovery system
    - Uses severity-based strategy selection
    - Provides component-specific recovery mechanisms
    - Supports graceful degradation for unrecoverable errors
    - Maintains recovery history for adaptive strategies
    
    ### Role in the System:
    - Detects and classifies errors during testing
    - Selects and applies appropriate recovery strategies
    - Tracks recovery attempts and success rates
    - Provides feedback to guide future testing
    - Ensures testing can continue despite transient failures
    """
    
    def __init__(self, max_recovery_attempts: int = 3):
        """
        Initialize the recovery manager.
        
        Args:
            max_recovery_attempts: Maximum recovery attempts before escalation
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.orchestration.recovery",
            {CONTEXT_COMPONENT: "RecoveryManager"}
        )
        
        # Initialize performance monitoring
        self.performance_monitor = PerformanceMonitor.get_instance()
        
        # Set recovery limits
        self.max_recovery_attempts = max_recovery_attempts
        
        # Recovery strategy mappings
        self.strategy_mapping: Dict[ErrorSeverity, List[RecoveryStrategy]] = {
            ErrorSeverity.LOW: [RecoveryStrategy.RETRY, RecoveryStrategy.ALTERNATIVE],
            ErrorSeverity.MEDIUM: [RecoveryStrategy.RETRY, RecoveryStrategy.ALTERNATIVE, 
                                 RecoveryStrategy.BACK_NAVIGATION],
            ErrorSeverity.HIGH: [RecoveryStrategy.ALTERNATIVE, RecoveryStrategy.BACK_NAVIGATION, 
                               RecoveryStrategy.APP_RESET],
            ErrorSeverity.CRITICAL: [RecoveryStrategy.APP_RESET, RecoveryStrategy.EMULATOR_RESET]
        }
        
        # Strategy handlers
        self.strategy_handlers: Dict[RecoveryStrategy, Callable] = {}
        
        # Recovery history
        self.recovery_attempts: Dict[str, int] = {}  # Error type -> attempt count
        self.recovery_successes: Dict[str, int] = {}  # Error type -> success count
        
        self.logger.info("Recovery manager initialized")
    
    def register_strategy_handler(self, strategy: RecoveryStrategy, handler: Callable) -> None:
        """
        Register a handler for a recovery strategy.
        
        Args:
            strategy: The recovery strategy
            handler: Function to implement the strategy
        """
        self.strategy_handlers[strategy] = handler
        self.logger.debug(f"Registered handler for {strategy.name}")
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> bool:
        """
        Handle an error by applying appropriate recovery strategies.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            
        Returns:
            True if recovery successful, False otherwise
        """
        error_type = type(error).__name__
        context = context or {}
        
        # Determine error severity
        severity = self._classify_error(error, context)
        self.logger.info(f"Handling {severity.name} severity error: {error_type}")
        
        # Update recovery attempt count
        self.recovery_attempts[error_type] = self.recovery_attempts.get(error_type, 0) + 1
        
        # Get appropriate strategies for this severity
        strategies = self.strategy_mapping.get(severity, [])
        
        # Try strategies in order
        for strategy in strategies:
            handler = self.strategy_handlers.get(strategy)
            if not handler:
                self.logger.warning(f"No handler registered for {strategy.name}")
                continue
            
            self.logger.info(f"Attempting recovery with {strategy.name}")
            
            # Attempt recovery
            with self.performance_monitor.measure_time(f"recovery_{strategy.name}"):
                try:
                    success = handler(error, context)
                    if success:
                        self.logger.info(f"Recovery successful with {strategy.name}")
                        # Update success count
                        self.recovery_successes[error_type] = \
                            self.recovery_successes.get(error_type, 0) + 1
                        return True
                except Exception as e:
                    self.logger.error(f"Error in recovery handler {strategy.name}: {e}")
            
            self.logger.warning(f"Recovery failed with {strategy.name}")
        
        self.logger.error(f"All recovery strategies failed for {error_type}")
        return False
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about recovery attempts and successes.
        
        Returns:
            Dictionary with recovery statistics
        """
        stats = {
            "total_attempts": sum(self.recovery_attempts.values()),
            "total_successes": sum(self.recovery_successes.values()),
            "success_rate": 0.0,
            "error_types": {}
        }
        
        # Calculate overall success rate
        if stats["total_attempts"] > 0:
            stats["success_rate"] = stats["total_successes"] / stats["total_attempts"]
        
        # Add per-error-type statistics
        for error_type in self.recovery_attempts.keys():
            attempts = self.recovery_attempts.get(error_type, 0)
            successes = self.recovery_successes.get(error_type, 0)
            success_rate = successes / attempts if attempts > 0 else 0.0
            
            stats["error_types"][error_type] = {
                "attempts": attempts,
                "successes": successes,
                "success_rate": success_rate
            }
        
        return stats
    
    def _classify_error(self, error: Exception, context: Dict[str, Any]) -> ErrorSeverity:
        """
        Classify an error's severity based on type and context.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            
        Returns:
            ErrorSeverity level
        """
        error_type = type(error).__name__
        
        # Classify based on error type
        if error_type in ["ADBError", "EmulatorError", "DeviceNotFoundError"]:
            return ErrorSeverity.CRITICAL
        
        if error_type in ["UIAutomator2Error", "TimeoutError", "ConnectionError"]:
            return ErrorSeverity.HIGH
        
        if error_type in ["ElementNotFoundError", "ActionFailedError"]:
            return ErrorSeverity.MEDIUM
        
        # Consider context
        critical_keywords = ["crash", "anr", "not responding", "device offline"]
        error_message = str(error).lower()
        
        if any(keyword in error_message for keyword in critical_keywords):
            return ErrorSeverity.CRITICAL
        
        # Default to MEDIUM severity
        return ErrorSeverity.MEDIUM
