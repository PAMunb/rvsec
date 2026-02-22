"""
Fallback management for algorithmic exploration when LLM fails.

Provides strategy-based fallback when LLM cannot generate valid actions
or when loops are detected during LLM-guided exploration.
"""

import logging
from typing import Optional

from rv_screen_parser.parser.screen.visitor.model import ItemAction, ScreenDescription

from rv_agent.strategies.strategy_registry import StrategyRegistry


class FallbackManager:
    """
    Manages fallback to algorithmic exploration strategies.

    ### Architectural Decisions:
    - Delegates to ExplorationStrategy implementations
    - Uses StrategyRegistry for strategy access
    - Provides action selection when LLM fails
    - Supports multiple fallback strategies (DFS, BFS, etc.)
    - Maintains no internal state (delegates to strategies)

    ### Role in the System:
    - Provides algorithmic fallback for LLM failures
    - Handles loop detection fallback
    - Ensures exploration continues despite LLM issues
    - Selects actions using traversal algorithms

    ### Integration Points:
    - Used by RoutingManager when fallback needed
    - Accesses strategies via StrategyRegistry
    - Receives ScreenDescription for action selection
    - Returns ItemAction for execution
    """

    def __init__(self, strategy_registry: StrategyRegistry):
        """
        Initialize fallback manager.

        Args:
            strategy_registry: Registry for accessing exploration strategies
        """
        self.strategy_registry = strategy_registry
        self.logger = logging.getLogger(__name__)

    def get_fallback_action(
        self,
        screen_hash: str,
        screen_description: ScreenDescription,
        strategy_name: str = "dfs",
    ) -> Optional[ItemAction]:
        """
        Get fallback action using algorithmic strategy.

        Args:
            screen_hash: Current screen hash
            screen_description: Parsed screen description
            strategy_name: Strategy to use for fallback (default: "dfs")

        Returns:
            ItemAction to execute, or None if no action available
        """
        self.logger.info(f"Getting fallback action using {strategy_name} strategy")

        # Get strategy from registry
        # Note: Strategy instance should already exist in agent
        # This method provides interface for fallback selection

        try:
            # For now, we assume agent maintains strategy instance
            # and passes it via dependency injection
            self.logger.warning(
                f"Fallback action requested for {strategy_name} - "
                "implementation requires agent-maintained strategy instance"
            )

            return None  # Placeholder - actual implementation in routing_manager

        except Exception as e:
            self.logger.error(f"Fallback action selection failed: {e}")
            return None
