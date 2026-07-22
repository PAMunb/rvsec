"""
Stuck recovery mechanism for detecting and recovering from blocked states.

Monitors consecutive same-state iterations and triggers recovery actions
(Backtrack BFS or app restart) when the agent appears stuck.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class StuckRecovery:
    """
    Detects when the agent is stuck in the same state and triggers recovery.

    Two-level recovery strategy:
    1. Backtrack BFS: Navigate to nearest unsaturated ancestor state
    2. Restart: Force stop and relaunch app if backtrack fails

    The counter resets when the state changes or after triggering recovery.
    """

    def __init__(self, max_blocks: int = 10):
        """
        Initialize stuck recovery tracker.

        Args:
            max_blocks: Number of consecutive same-state iterations before recovery
        """
        self.max_blocks = max_blocks
        self.state_block_counter = 0
        self.last_state_hash: Optional[str] = None
        self.total_recoveries = 0
        self.total_restarts = 0

    def check(self, current_hash: str, is_form_action: bool = False) -> Optional[str]:
        """
        Check if stuck and return recovery action if needed.

        Args:
            current_hash: Current state hash
            is_form_action: Whether the last action was a form action (SET_TEXT,
                TEXT_CHANGE, or checkable widget). When True, the block counter
                is NOT incremented because form actions legitimately keep the
                same screen hash while changing internal state.

        Returns:
            "restart" if blocked for too long, None otherwise
        """
        if current_hash == self.last_state_hash:
            if not is_form_action:
                self.state_block_counter += 1
            logger.debug(
                f"Same state detected ({self.state_block_counter}/{self.max_blocks}): "
                f"{current_hash[:8]}..."
            )
        else:
            if self.state_block_counter > 0:
                logger.debug(
                    f"State changed after {self.state_block_counter} iterations: "
                    f"{self.last_state_hash[:8] if self.last_state_hash else 'None'} -> "
                    f"{current_hash[:8]}"
                )
            self.state_block_counter = 0
            self.last_state_hash = current_hash

        if self.state_block_counter >= self.max_blocks:
            logger.warning(
                f"Stuck recovery triggered: same state for {self.state_block_counter} iterations"
            )
            self.state_block_counter = 0
            self.total_recoveries += 1
            return "restart"

        return None

    def record_restart(self) -> None:
        """Record that a restart was actually performed."""
        self.total_restarts += 1
        logger.info(f"App restart recorded (total: {self.total_restarts})")

    def reset(self) -> None:
        """Reset counters for new exploration session."""
        self.state_block_counter = 0
        self.last_state_hash = None
        logger.debug("StuckRecovery state reset")

    def get_statistics(self) -> dict:
        """
        Get stuck recovery statistics.

        Returns:
            Dictionary with recovery metrics
        """
        return {
            "total_recoveries_triggered": self.total_recoveries,
            "total_restarts": self.total_restarts,
            "current_block_counter": self.state_block_counter,
            "max_blocks_threshold": self.max_blocks,
        }
