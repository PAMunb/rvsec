"""
Agent state model for LangGraph workflow.

This module re-exports AgentState from the domain layer for backward compatibility.
The canonical location is now rv_agent.domain.state.
"""

from rv_agent.domain.state import AgentState

__all__ = ["AgentState"]
