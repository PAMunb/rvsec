# rvandroid/mcp/service/action_service.py
"""LLM action service using MCP."""

import asyncio
import logging
from typing import Dict, Any, Optional

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.mcp.language_model import LanguageModel
from rvandroid.mcp.mcp_data_structures import MCPConfiguration
from rvandroid.mcp.strategies.base_strategy import BasePromptStrategy
from rvandroid.mcp.strategies.single_action_strategy import SingleActionPromptStrategy


class LLMActionService:
    """Service for generating actions using LLMs with MCP."""

    def __init__(self,
                 static_data: Optional[StaticAnalysisData] = None,
                 config: Optional[ComponentConfigurator] = None):
        """Initialize LLM action service."""
        self.static_data = static_data
        self.config = config or ComponentConfigurator(static_data)
        self.logger = logging.getLogger(f"{__name__}")

        # Create model
        self.model = self._create_model()

        # Create strategy
        self.strategy = self._create_strategy()

        # Configuration for model
        self.model_config = MCPConfiguration(
            temperature=self.config.llm_config.temperature,
            max_tokens=self.config.llm_config.max_tokens
        )

    def _create_model(self) -> LanguageModel:
        """Create language model instance."""
        try:
            return self.config.create_llm()
        except Exception as e:
            self.logger.error(f"Error creating language model: {e}", exc_info=True)
            raise

    def _create_strategy(self) -> BasePromptStrategy:
        """Create prompt strategy instance."""
        try:
            return self.config.create_strategy(self.static_data)
        except Exception as e:
            self.logger.error(f"Error creating strategy: {e}", exc_info=True)
            # Fallback to SingleActionPromptStrategy
            return SingleActionPromptStrategy(self.static_data, self.config.create_parser())

    async def process_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process application state to generate actions."""
        try:
            # Generate actions using the strategy
            result = await self.strategy.generate_actions(self.model, state, self.model_config)
            return result
        except Exception as e:
            self.logger.error(f"Error processing state: {e}", exc_info=True)
            return {"error": str(e)}

    def process_state_sync(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process application state synchronously."""
        return asyncio.run(self.process_state(state))

    def update_config(self,
                      temperature: Optional[float] = None,
                      max_tokens: Optional[int] = None,
                      strategy_type: Optional[str] = None) -> None:
        """Update configuration parameters."""
        # Update model configuration
        if temperature is not None:
            self.model_config.temperature = temperature

        if max_tokens is not None:
            self.model_config.max_tokens = max_tokens

        # Update strategy if requested
        if strategy_type is not None and strategy_type != self.config.llm_config.strategy_type:
            self.config.set_strategy(strategy_type)
            self.strategy = self._create_strategy()

    def get_config_info(self) -> Dict[str, Any]:
        """Get current configuration information."""
        return {
            "model": {
                "type": self.config.llm_config.model_type,
                "name": self.config.llm_config.model_name,
                "temperature": self.model_config.temperature,
                "max_tokens": self.model_config.max_tokens
            },
            "strategy": {
                "type": self.config.llm_config.strategy_type,
                "class": self.strategy.__class__.__name__
            },
            "parser": {
                "type": self.config.llm_config.parser_type.name,
                "class": self.config.parser_class.__name__
            }
        }
