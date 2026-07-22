"""
Plateau Detector - Detects when exploration has reached a plateau.

A plateau is reached when the exploration stops discovering new states or
executing new MOP methods for a sustained period (window_size iterations).

This allows automatic termination without manually setting iteration limits.
"""

import logging
from collections import deque
from typing import Any, Deque, Dict

logger = logging.getLogger(__name__)


class PlateauDetector:
    """
    Monitors exploration progress and detects plateaus.

    Tracks two metrics per iteration:
    1. New states discovered (bool)
    2. New MOP methods executed (bool)

    Plateau is reached when BOTH metrics are False for window_size consecutive iterations.

    Example:
        window_size = 10
        Last 10 iterations: no new states, no new MOP methods
        → Plateau detected → Exploration should terminate
    """

    def __init__(self, window_size: int = 10):
        """
        Initialize plateau detector.

        Args:
            window_size: Number of iterations to check for plateau (default: 10)
        """
        if window_size < 1:
            raise ValueError(f"window_size must be >= 1, got {window_size}")

        self.window_size = window_size

        # Sliding window of discovery events
        self.state_discovery: Deque[bool] = deque(maxlen=window_size)
        self.mop_execution: Deque[bool] = deque(maxlen=window_size)

        # Tracking set of MOP methods seen (for new detection)
        self.mop_methods_seen: set = set()

        # Statistics
        self.total_iterations = 0
        self.total_states_discovered = 0
        self.total_mop_methods_executed = 0

        logger.info(f"PlateauDetector initialized with window_size={window_size}")

    def record_iteration(self, discovered_new_state: bool, new_mop_method: str = None):
        """
        Record exploration metrics for current iteration.

        Args:
            discovered_new_state: True if this iteration discovered a new state
            new_mop_method: MOP method signature if executed, None otherwise
        """
        self.total_iterations += 1

        # Record state discovery
        self.state_discovery.append(discovered_new_state)
        if discovered_new_state:
            self.total_states_discovered += 1

        # Record MOP execution
        reached_new_mop = False
        if new_mop_method and new_mop_method not in self.mop_methods_seen:
            self.mop_methods_seen.add(new_mop_method)
            reached_new_mop = True
            self.total_mop_methods_executed += 1

        self.mop_execution.append(reached_new_mop)

        # Log if window is full and plateau detected
        if len(self.state_discovery) == self.window_size:
            if self.is_plateau_reached():
                logger.warning(
                    f"Plateau detected: no progress in last {self.window_size} iterations"
                )

    def is_plateau_reached(self) -> bool:
        """
        Check if exploration has plateaued.

        Returns:
            True if plateau detected (no discoveries in window_size iterations)
        """
        # Need full window to detect plateau
        if len(self.state_discovery) < self.window_size:
            return False

        # Plateau = no new states AND no new MOP in entire window
        no_new_states = not any(self.state_discovery)
        no_new_mop = not any(self.mop_execution)

        return no_new_states and no_new_mop

    def get_progress_in_window(self) -> Dict[str, int]:
        """
        Get progress metrics within current window.

        Returns:
            Dictionary with states and MOP discovered in window
        """
        return {
            "states_in_window": sum(self.state_discovery),
            "mop_in_window": sum(self.mop_execution),
        }

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive plateau detection metrics.

        Returns:
            Dictionary with all tracking metrics
        """
        progress = self.get_progress_in_window()

        return {
            # Configuration
            "window_size": self.window_size,
            "iterations_tracked": len(self.state_discovery),
            # Window metrics
            "states_in_window": progress["states_in_window"],
            "mop_in_window": progress["mop_in_window"],
            # Total metrics
            "total_iterations": self.total_iterations,
            "total_states_discovered": self.total_states_discovered,
            "total_mop_methods_executed": self.total_mop_methods_executed,
            "unique_mop_methods": len(self.mop_methods_seen),
            # Status
            "plateau_reached": self.is_plateau_reached(),
        }

    def reset(self):
        """
        Reset plateau detector state.

        Useful for restarting exploration after manual intervention.
        """
        self.state_discovery.clear()
        self.mop_execution.clear()
        self.mop_methods_seen.clear()
        self.total_iterations = 0
        self.total_states_discovered = 0
        self.total_mop_methods_executed = 0

        logger.info("PlateauDetector reset")

    def __repr__(self) -> str:
        """String representation for debugging."""
        metrics = self.get_metrics()
        return (
            f"PlateauDetector(window={self.window_size}, "
            f"iterations={metrics['total_iterations']}, "
            f"plateau={metrics['plateau_reached']})"
        )
