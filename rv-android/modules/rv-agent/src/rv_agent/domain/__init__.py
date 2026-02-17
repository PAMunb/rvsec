"""
Domain models for RV-Agent.

Contains core data models for the exploration workflow:
- AgentState: Complete state for LangGraph workflow
- ScreenNode: Node representing a unique UI structure state
- Transition: State transition with action sequence
- ActionNormalizer: Unified action format converter
- Exceptions: RVAgentError, DeviceError, LLMError, ValidationError
"""

from rv_agent.domain.state import AgentState
from rv_agent.domain.screen_node import ScreenNode, Transition
from rv_agent.domain.action import ActionNormalizer, TOOL_TO_ACTION
from rv_agent.domain.exceptions import (
    RVAgentError,
    DeviceError,
    LLMError,
    ValidationError,
)

__all__ = [
    "AgentState",
    "ScreenNode",
    "Transition",
    "ActionNormalizer",
    "TOOL_TO_ACTION",
    "RVAgentError",
    "DeviceError",
    "LLMError",
    "ValidationError",
]
