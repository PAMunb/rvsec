# rvandroid/rvdroid/core/lifecycle.py

"""
Component lifecycle management for RVDroid.

This module provides classes for managing the lifecycle of RVDroid components,
including initialization, execution phases, and graceful shutdown.
"""

import enum
import time
from typing import Dict, Any, Optional, Callable, List

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class ExecutionPhase(enum.Enum):
    """
    Execution phases for the RVDroid testing lifecycle.
    
    Defines the standard phases of execution for the RVDroid
    testing process, from initialization to termination.
    """
    INITIALIZATION = "initialization"
    EXPLORATION = "exploration"
    CONSULTATION = "consultation"
    ADAPTATION = "adaptation"
    RECOVERY = "recovery"
    TERMINATION = "termination"


class LifecycleManager:
    """
    Manages the lifecycle and execution phases of RVDroid.
    
    ### Architectural Decisions:
    - Implements a phase-based execution model for structured testing
    - Manages transitions between execution phases
    - Provides comprehensive phase timing and statistics
    - Supports timeout handling and emergency shutdown
    - Enables custom handlers for phase entry and exit events
    
    ### Role in the System:
    - Coordinates the overall testing lifecycle
    - Enforces phase sequencing and timing constraints
    - Provides execution metrics and statistics
    - Enables customizable phase transition behaviors
    - Supports graceful error recovery and termination
    """
    
    def __init__(self, timeout: int = 3600):
        """
        Initialize the lifecycle manager.
        
        Args:
            timeout: Maximum execution time in seconds (default: 1 hour)
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.core.lifecycle_manager",
            {CONTEXT_COMPONENT: "LifecycleManager"}
        )
        
        # Initialize error handler
        self.error_handler = ErrorHandler.get_instance()
        
        # Lifecycle timing
        self.timeout = timeout
        self.start_time = 0
        self.end_time = 0
        
        # Phase management
        self.current_phase = None
        self.phase_start_time = 0
        self.execution_running = False
        
        # Standard phase sequence
        self.phase_sequence = [
            ExecutionPhase.INITIALIZATION,
            ExecutionPhase.EXPLORATION,
            ExecutionPhase.CONSULTATION,
            ExecutionPhase.ADAPTATION,
            ExecutionPhase.EXPLORATION,  # Return to exploration after adaptation
            ExecutionPhase.TERMINATION
        ]
        
        # Phase timings for statistics
        self.phase_timings = {
            ExecutionPhase.INITIALIZATION: 60,    # 1 minute for initialization
            ExecutionPhase.EXPLORATION: 300,      # 5 minutes for exploration
            ExecutionPhase.CONSULTATION: 60,      # 1 minute for consultation
            ExecutionPhase.ADAPTATION: 60,        # 1 minute for adaptation
            ExecutionPhase.RECOVERY: 120,         # 2 minutes for recovery
            ExecutionPhase.TERMINATION: 60        # 1 minute for termination
        }
        
        # Phase statistics
        self.phase_stats = {phase: {"entries": 0, "total_time": 0} for phase in ExecutionPhase}
        
        # Phase handlers
        self.phase_handlers = {}
        
    def start_execution(self) -> bool:
        """
        Start the execution lifecycle.
        
        Returns:
            True if execution started successfully, False otherwise
        """
        if self.execution_running:
            self.logger.warning("Execution already running")
            return False
            
        self.logger.info("Starting execution lifecycle")
        
        # Reset statistics
        self.start_time = time.time()
        self.end_time = 0
        
        # Start with initialization phase
        self.execution_running = True
        self._transition_to_phase(ExecutionPhase.INITIALIZATION)
        
        return True
        
    def stop_execution(self) -> bool:
        """
        Stop the execution lifecycle gracefully.
        
        Returns:
            True if execution stopped successfully, False otherwise
        """
        if not self.execution_running:
            self.logger.warning("Execution not running")
            return False
            
        self.logger.info("Stopping execution lifecycle")
        
        # Transition to termination phase
        self._transition_to_phase(ExecutionPhase.TERMINATION)
        
        # Update execution state and record end time
        self.execution_running = False
        self.end_time = time.time()
        
        return True
        
    def emergency_stop(self) -> None:
        """
        Perform an emergency stop of the execution lifecycle.
        
        This method immediately stops execution without phase transitions.
        """
        self.logger.warning("Emergency stopping execution lifecycle")
        
        # Record current phase for statistics
        if self.current_phase:
            phase_duration = time.time() - self.phase_start_time
            self.phase_stats[self.current_phase]["total_time"] += phase_duration
        
        # Update execution state and record end time
        self.execution_running = False
        self.end_time = time.time()
        
    def transition_to_next_phase(self) -> bool:
        """
        Transition to the next phase in the standard sequence.
        
        Returns:
            True if transition successful, False otherwise
        """
        if not self.execution_running:
            self.logger.warning("Cannot transition: execution not running")
            return False
            
        if not self.current_phase:
            self.logger.warning("Cannot transition: no current phase")
            return False
            
        # Find current phase index in sequence
        try:
            current_index = self.phase_sequence.index(self.current_phase)
            next_index = current_index + 1
            
            # Check if we reached the end of the sequence
            if next_index >= len(self.phase_sequence):
                self.logger.info("Reached end of phase sequence")
                return self.stop_execution()
                
            # Transition to next phase
            next_phase = self.phase_sequence[next_index]
            return self._transition_to_phase(next_phase)
            
        except ValueError:
            self.logger.error(f"Current phase {self.current_phase} not found in sequence")
            return False
            
    def _transition_to_phase(self, phase: ExecutionPhase) -> bool:
        """
        Transition to a specific phase.
        
        Args:
            phase: Phase to transition to
            
        Returns:
            True if transition successful, False otherwise
        """
        if not self.execution_running and phase != ExecutionPhase.TERMINATION:
            self.logger.warning(f"Cannot transition to {phase}: execution not running")
            return False
            
        # Record end of current phase
        if self.current_phase:
            # Call exit handler if registered
            self._call_phase_handler(self.current_phase, "exit")
            
            # Update phase statistics
            phase_duration = time.time() - self.phase_start_time
            self.phase_stats[self.current_phase]["total_time"] += phase_duration
            
        # Set new phase
        self.logger.info(f"Transitioning to phase: {phase.value}")
        self.current_phase = phase
        self.phase_start_time = time.time()
        self.phase_stats[phase]["entries"] += 1
        
        # Call entry handler if registered
        self._call_phase_handler(phase, "entry")
        
        return True
        
    def register_phase_handler(self, phase: ExecutionPhase,
                              on_entry: Optional[Callable] = None,
                              on_exit: Optional[Callable] = None) -> None:
        """
        Register handlers for phase transitions.
        
        Args:
            phase: Phase to register handlers for
            on_entry: Function to call when entering this phase
            on_exit: Function to call when exiting this phase
        """
        if phase not in self.phase_handlers:
            self.phase_handlers[phase] = {"entry": None, "exit": None}
            
        if on_entry:
            self.phase_handlers[phase]["entry"] = on_entry
            
        if on_exit:
            self.phase_handlers[phase]["exit"] = on_exit
            
        self.logger.debug(f"Registered handlers for phase: {phase.value}")
        
    def _call_phase_handler(self, phase: ExecutionPhase, event_type: str) -> None:
        """
        Call a registered phase handler.
        
        Args:
            phase: Phase the event is for
            event_type: Type of event ("entry" or "exit")
        """
        if phase in self.phase_handlers and self.phase_handlers[phase][event_type]:
            try:
                self.phase_handlers[phase][event_type]()
            except Exception as e:
                self.logger.error(f"Error in {phase.value} {event_type} handler: {e}")
                self.error_handler.handle_error(
                    "lifecycle_handler_error",
                    str(e),
                    context={"phase": phase.value, "event_type": event_type}
                )
        
    def get_current_phase(self) -> Optional[ExecutionPhase]:
        """
        Get the current execution phase.
        
        Returns:
            Current execution phase or None if not started
        """
        return self.current_phase
        
    def is_timeout_reached(self) -> bool:
        """
        Check if the global execution timeout has been reached.
        
        Returns:
            True if timeout reached, False otherwise
        """
        if not self.execution_running or self.start_time == 0:
            return False
            
        elapsed_time = time.time() - self.start_time
        return elapsed_time >= self.timeout
        
    def is_phase_timeout_reached(self) -> bool:
        """
        Check if the current phase timeout has been reached.
        
        Returns:
            True if phase timeout reached, False otherwise
        """
        if not self.execution_running or not self.current_phase or self.phase_start_time == 0:
            return False
            
        phase_duration = time.time() - self.phase_start_time
        phase_timeout = self.phase_timings.get(self.current_phase, 300)  # Default 5 minutes
        
        return phase_duration >= phase_timeout
        
    def get_phase_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about phase execution.
        
        Returns:
            Dictionary with phase statistics
        """
        stats = {
            "total_execution_time": 0,
            "phases": {}
        }
        
        # Calculate total execution time
        if self.start_time > 0:
            if self.end_time > 0:
                stats["total_execution_time"] = self.end_time - self.start_time
            else:
                stats["total_execution_time"] = time.time() - self.start_time
        
        # Add current phase information
        if self.current_phase:
            current_phase_duration = time.time() - self.phase_start_time
            stats["current_phase"] = {
                "name": self.current_phase.value,
                "duration": current_phase_duration
            }
        
        # Add phase statistics
        for phase, phase_stats in self.phase_stats.items():
            stats["phases"][phase.value] = {
                "entries": phase_stats["entries"],
                "total_time": phase_stats["total_time"]
            }
            
            # If this is the current phase, add in-progress time
            if phase == self.current_phase:
                stats["phases"][phase.value]["total_time"] += time.time() - self.phase_start_time
        
        return stats