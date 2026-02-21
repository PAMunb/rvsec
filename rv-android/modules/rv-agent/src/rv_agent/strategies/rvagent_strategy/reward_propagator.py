"""
N-step reward propagator for action value estimation.

Propagates rewards backward through recent action history to credit
earlier actions that contributed to positive outcomes (MOP reached,
new state discovered) or penalize actions that led to dead ends.

The propagator maintains a sliding window of recent (state, action)
pairs and, on each reward event, distributes discounted reward to
the N most recent actions using gamma-discounted backward propagation.
"""

import logging
from collections import deque
from typing import Tuple, Optional, TYPE_CHECKING

from rv_agent import tracking as track

if TYPE_CHECKING:
    from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
    from rv_agent.config.agent_config import RVAgentConfig

logger = logging.getLogger(__name__)

# Module-level constants (not calibratable - see design.md Decision D5)
REWARD_MOP_WEIGHT = 5.0
REWARD_PROPAGATION_N = 5
MAX_CUMULATIVE_REWARD_FACTOR = 3.0

# Reward values per event type
REWARD_VALUES = {
    "mop_reached": REWARD_MOP_WEIGHT,
    "new_activity": 2.0,
    "new_state": 1.0,
    "form_fill": 0.0,
    "same_state": -0.1,
}

# Priority order for reward types (highest first)
REWARD_PRIORITY = [
    "mop_reached",
    "new_activity",
    "new_state",
    "form_fill",
    "same_state",
]


class RewardPropagator:
    """
    Propagates rewards backward through recent action history.

    Uses N-step temporal difference with gamma discounting. When a reward
    event occurs (e.g., MOP method reached), the reward is distributed
    backward to the N most recent actions with exponential decay.

    Each action's cumulative reward is clamped to symmetric bounds
    [-MAX_CUMULATIVE_REWARD_FACTOR * REWARD_MOP_WEIGHT, +MAX_CUMULATIVE_REWARD_FACTOR * REWARD_MOP_WEIGHT]
    to prevent score inflation over long sessions.
    """

    def __init__(self, config: Optional["RVAgentConfig"] = None):
        gamma = config.reward_gamma if config else 0.8
        self.gamma = gamma
        self._action_history: deque = deque(maxlen=REWARD_PROPAGATION_N)
        self._upper_cap = MAX_CUMULATIVE_REWARD_FACTOR * REWARD_MOP_WEIGHT
        self._lower_cap = -MAX_CUMULATIVE_REWARD_FACTOR * REWARD_MOP_WEIGHT

    def record_action(
        self, state_hash: str, action_signature: Tuple[Tuple[int, int], str]
    ) -> None:
        """
        Record a (state, action) pair in the history window.

        Args:
            state_hash: Hash of the state where the action was executed
            action_signature: ((opt_x, opt_y), action_type) in optimized coordinate space
        """
        self._action_history.append((state_hash, action_signature))

    def propagate(self, reward_type: str, graph: "DynamicStateGraph") -> None:
        """
        Propagate reward backward through action history.

        Distributes reward to the N most recent actions using gamma discounting:
        action[-1] gets reward * gamma^0, action[-2] gets reward * gamma^1, etc.

        Args:
            reward_type: One of "mop_reached", "new_activity", "new_state", "form_fill", "same_state"
            graph: DynamicStateGraph to update action_cumulative_reward on ScreenNodes
        """
        base_reward = REWARD_VALUES.get(reward_type, 0.0)
        if base_reward == 0.0 and reward_type != "form_fill":
            return

        history = list(self._action_history)
        if not history:
            return

        for k, (state_hash, action_sig) in enumerate(reversed(history)):
            discounted_reward = base_reward * (self.gamma**k)

            node = graph.states.get(state_hash)
            if not node:
                continue

            current = node.action_cumulative_reward.get(action_sig, 0.0)
            new_value = current + discounted_reward

            # Clamp to symmetric bounds
            new_value = max(self._lower_cap, min(self._upper_cap, new_value))
            node.action_cumulative_reward[action_sig] = new_value

        track.reward_propagation(
            iter=0,
            reward_type=reward_type,
            reward_value=base_reward,
            steps_propagated=len(history),
        )
        logger.debug(
            f"Reward propagated: type={reward_type}, base={base_reward}, "
            f"history_len={len(history)}, gamma={self.gamma}"
        )

    def reset(self) -> None:
        """Clear action history."""
        self._action_history.clear()

    def __repr__(self) -> str:
        return (
            f"RewardPropagator(gamma={self.gamma}, history={len(self._action_history)})"
        )
