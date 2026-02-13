# rvandroid/rvdroid/orchestration/lifecycle.py

"""
Lifecycle management for RVDroid.

This module provides components for managing the testing lifecycle,
including initialization, execution cycles, and termination.
"""

import time
from enum import Enum, auto
from typing import Dict, Any, Optional, Callable, List

from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.performance_monitor import PerformanceMonitor


class ExecutionPhase(Enum):
    """
    Phases of the RVDroid execution lifecycle.
    
    These phases represent the different states of the testing execution,
    providing a clear framework for component coordination and timing.
    """
    INITIALIZATION = auto()
    EXPLORATION = auto()  # Active exploration phase
    CONSULTATION = auto()  # Consulting LLM for guidance
    ADAPTATION = auto()    # Adapting strategies based on guidance
    RECOVERY = auto()      # Error recovery phase
    TERMINATION = auto()


class LifecycleManager:
    """
    Manager for the RVDroid execution lifecycle.
    
    ### Architectural Decisions:
    - Implements a centralized lifecycle management system
    - Uses a phase-based approach to organize execution flow
    - Provides clear phase transitions and lifecycle events
    - Employs a timeout system for resource management
    - Supports both normal and emergency termination sequences
    
    ### Role in the System:
    - Manages the overall execution flow of RVDroid
    - Coordinates timing between exploration and consultation
    - Ensures proper initialization and termination of components
    - Provides hooks for phase-specific behavior
    - Implements timeout handling for graceful termination
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
            "rvdroid.orchestration.lifecycle",
            {CONTEXT_COMPONENT: "LifecycleManager"}
        )
        
        # Initialize performance monitoring
        self.performance_monitor = PerformanceMonitor.get_instance()
        
        # Set timeout
        self.timeout = timeout
        self.start_time = 0
        
        # Initialize execution state
        self.current_phase = ExecutionPhase.INITIALIZATION
        self.execution_running = False
        
        # Phase timing settings
        self.phase_timings = {
            ExecutionPhase.EXPLORATION: 300,  # 5 minutes of exploration
            ExecutionPhase.CONSULTATION: 60,  # 1 minute for LLM consultation
            ExecutionPhase.ADAPTATION: 30,    # 30 seconds for adaptation
        }
        
        # Phase entry/exit handlers
        self.phase_handlers: Dict[ExecutionPhase, Dict[str, List[Callable]]] = {
            phase: {"entry": [], "exit": []} for phase in ExecutionPhase
        }
        
        # Phase transition times
        self.phase_times: Dict[ExecutionPhase, float] = {
            phase: 0.0 for phase in ExecutionPhase
        }
        
        self.logger.info("Lifecycle manager initialized with timeout: {}s".format(timeout))
    
    def register_phase_handler(self, phase: ExecutionPhase, 
                              on_entry: Optional[Callable] = None,
                              on_exit: Optional[Callable] = None) -> None:
        """
        Register handlers for phase entry and exit events.
        
        Args:
            phase: The execution phase to register handlers for
            on_entry: Optional callback when entering the phase
            on_exit: Optional callback when exiting the phase
        """
        if on_entry:
            self.phase_handlers[phase]["entry"].append(on_entry)
        
        if on_exit:
            self.phase_handlers[phase]["exit"].append(on_exit)
    
    def start_execution(self) -> bool:
        """
        Start the execution lifecycle.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self.execution_running:
            self.logger.warning("Execution already running")
            return False
        
        self.logger.info("Starting execution lifecycle")
        
        # Record start time
        self.start_time = time.time()
        self.execution_running = True
        
        # Set initial phase
        self._transition_to_phase(ExecutionPhase.INITIALIZATION)
        
        return True
    
    def stop_execution(self) -> None:
        """
        Stop the execution lifecycle gracefully.
        """
        if not self.execution_running:
            self.logger.warning("Execution not running")
            return
        
        self.logger.info("Stopping execution lifecycle")
        
        # Transition to termination phase
        self._transition_to_phase(ExecutionPhase.TERMINATION)
        
        # Mark execution as stopped
        self.execution_running = False
    
    def emergency_stop(self) -> None:
        """
        Perform emergency stop of execution.
        This bypasses normal phase transitions.
        """
        self.logger.warning("Emergency stop requested")
        
        # Record phase for logging but don't run handlers
        self.current_phase = ExecutionPhase.TERMINATION
        self.execution_running = False
        
        self.logger.info("Execution emergency stopped")
    
    def is_timeout_reached(self) -> bool:
        """
        Check if execution timeout has been reached.
        
        Returns:
            True if timeout reached, False otherwise
        """
        if not self.execution_running or self.start_time == 0:
            return False
        
        elapsed_time = time.time() - self.start_time
        return elapsed_time >= self.timeout
    
    def get_remaining_time(self) -> float:
        """
        Get remaining execution time in seconds.
        
        Returns:
            Remaining time in seconds, or 0 if timeout reached/not running
        """
        if not self.execution_running or self.start_time == 0:
            return 0.0
        
        elapsed_time = time.time() - self.start_time
        remaining = max(0.0, self.timeout - elapsed_time)
        
        return remaining
    
    def get_current_phase(self) -> ExecutionPhase:
        """
        Get the current execution phase.
        
        Returns:
            Current ExecutionPhase
        """
        return self.current_phase
    
    def is_phase_timeout_reached(self) -> bool:
        """
        Check if the current phase timeout has been reached.
        
        Returns:
            True if current phase timeout reached, False otherwise
        """
        # Some phases don't have timeouts
        if self.current_phase not in self.phase_timings:
            return False
        
        phase_start = self.phase_times[self.current_phase]
        phase_timeout = self.phase_timings[self.current_phase]
        
        elapsed = time.time() - phase_start
        return elapsed >= phase_timeout
    
    def transition_to_next_phase(self) -> bool:
        """
        Transition to the next logical phase in the execution cycle.
        
        Returns:
            True if transitioned, False if cycle complete or not running
        """
        if not self.execution_running:
            return False
        
        # Define phase cycle
        phase_cycle = {
            ExecutionPhase.INITIALIZATION: ExecutionPhase.EXPLORATION,
            ExecutionPhase.EXPLORATION: ExecutionPhase.CONSULTATION,
            ExecutionPhase.CONSULTATION: ExecutionPhase.ADAPTATION,
            ExecutionPhase.ADAPTATION: ExecutionPhase.EXPLORATION,
            ExecutionPhase.RECOVERY: ExecutionPhase.EXPLORATION,
            ExecutionPhase.TERMINATION: None  # End of cycle
        }
        
        next_phase = phase_cycle.get(self.current_phase)
        if next_phase is None:
            return False
        
        return self._transition_to_phase(next_phase)
    
    def get_phase_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about phase timings.
        
        Returns:
            Dictionary with phase timing statistics
        """
        current_time = time.time()
        stats = {}
        
        # Calculate time spent in each phase
        for phase in ExecutionPhase:
            if self.phase_times[phase] > 0:
                if phase == self.current_phase:
                    # For current phase, use current time as end time
                    duration = current_time - self.phase_times[phase]
                else:
                    # For completed phases, use the next phase's start time
                    # This is approximate since we don't track phase end times directly
                    next_phase_idx = list(ExecutionPhase).index(phase) + 1
                    if next_phase_idx < len(ExecutionPhase):
                        next_phase = list(ExecutionPhase)[next_phase_idx]
                        if self.phase_times[next_phase] > 0:
                            duration = self.phase_times[next_phase] - self.phase_times[phase]
                        else:
                            duration = 0
                    else:
                        duration = 0
                
                stats[phase.name] = {
                    "start_time": self.phase_times[phase] - self.start_time,
                    "duration": duration
                }
        
        # Add general execution stats
        stats["total_execution_time"] = current_time - self.start_time if self.start_time > 0 else 0
        stats["current_phase"] = self.current_phase.name
        stats["remaining_time"] = self.get_remaining_time()
        
        return stats
    
    def _transition_to_phase(self, new_phase: ExecutionPhase) -> bool:
        """
        Internal method to handle phase transitions.
        
        Args:
            new_phase: The phase to transition to
            
        Returns:
            True if transition successful, False otherwise
        """
        if not self.execution_running and new_phase != ExecutionPhase.TERMINATION:
            self.logger.warning(f"Cannot transition to {new_phase.name}: execution not running")
            return False
        
        old_phase = self.current_phase
        self.logger.info(f"Transitioning from {old_phase.name} to {new_phase.name}")
        
        # Call exit handlers for old phase
        with self.performance_monitor.measure_time(f"phase_transition_exit_{old_phase.name}"):
            for handler in self.phase_handlers[old_phase]["exit"]:
                try:
                    handler()
                except Exception as e:
                    self.logger.error(f"Error in exit handler for {old_phase.name}: {e}")
        
        # Update phase
        self.current_phase = new_phase
        self.phase_times[new_phase] = time.time()
        
        # Call entry handlers for new phase
        with self.performance_monitor.measure_time(f"phase_transition_entry_{new_phase.name}"):
            for handler in self.phase_handlers[new_phase]["entry"]:
                try:
                    handler()
                except Exception as e:
                    self.logger.error(f"Error in entry handler for {new_phase.name}: {e}")
        
        self.logger.info(f"Transitioned to {new_phase.name}")
        return True
