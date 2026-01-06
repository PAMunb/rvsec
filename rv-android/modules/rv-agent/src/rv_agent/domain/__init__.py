"""
Domain models for RV-Agent.

Contains core data models for the exploration workflow:
- AgentState: Complete state for LangGraph workflow
- ScreenNode: Node representing a unique UI structure state
- Transition: State transition with action sequence
"""

from rv_agent.domain.state import AgentState
from rv_agent.domain.screen_node import ScreenNode, Transition, MAX_FAILURE_ATTEMPTS

__all__ = [
    "AgentState",
    "ScreenNode",
    "Transition",
    "MAX_FAILURE_ATTEMPTS",
]
