"""
Prompt Strategy Module

Provides a hierarchy of strategies for generating prompts for LLMs.
This module follows a strategy pattern with a standard interface and
specialized implementations for different prompt generation approaches.

This is the core component of the LLM-driven testing system, as the
quality of prompts directly impacts the quality of generated actions.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

from rv_android_core.domain.static import StaticAnalysisData
from rv_llm.llm.data_structures import LLMRole
from rv_screen_parser.parser.screen.base_parser import BaseScreenParser


class PromptStrategy(ABC):
    """
    Abstract base class for prompt generation strategies.
    Defines the interface for all prompt generation strategies.

    ### Architectural Decisions:
    - Follows the Strategy Pattern for prompt generation
    - Provides a common interface for all strategies
    - Enables dynamic strategy selection based on configuration
    - Supports different parser types for screen parsing
    - Integrates with static analysis data for enhanced context

    ### Role in the System:
    - Core component of the LLM-driven testing system
    - Translates application state into effective prompts
    - Coordinates with parsers and static analysis
    - Provides extensibility for custom prompt generation approaches
    """

    def __init__(self,
                 static_data: Optional["StaticAnalysisData"] = None,
                 parser: Optional[BaseScreenParser] = None):
        """
        Initialize the prompt strategy.

        Args:
            static_data: Static analysis data (optional)
            parser: Either a ParserType enum value, a BaseScreenParser instance, 
                    or None to use the default parser type
        """
        self.static_data = static_data
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Handle the parser parameter
        if isinstance(parser, BaseScreenParser):
            self.parser = parser
        else:
            raise TypeError(
                f"parser must be a ParserType enum value or a BaseScreenParser instance, got {type(parser)}")

    @abstractmethod
    def generate_system_prompt(self) -> str:
        """
        Generate the system prompt that defines the LLM's role and constraints.

        Returns:
            String containing the system prompt
        """
        pass

    @abstractmethod
    def generate_user_prompt(self, state: Dict[str, Any]) -> str:
        """
        Generate the user prompt based on state.

        Args:
            state: Current application state

        Returns:
            User prompt
        """
        pass

    def generate_prompts(self, state: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Generate prompts from the current state.

        Args:
            state: Current state dictionary

        Returns:
            List of prompt messages in the format expected by the LLM
        """
        return [
            {"role": LLMRole.SYSTEM.value, "content": self.generate_system_prompt()},
            {"role": LLMRole.USER.value, "content": self.generate_user_prompt(state)}
        ]
