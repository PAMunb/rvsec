"""
Agent module for RV-Agent.

Contains the main agent implementation and supporting components.

Components:
- RVAgent: Main autonomous Android testing agent
- AgentFactory: Factory for creating configured agent instances
- DeviceInterface: Android device interaction interface
- DynamicStateGraph: Graph-based state tracking

Note: RVAgent and AgentFactory are not imported here to avoid circular
dependencies with strategies. Import them directly:
    from rv_agent.agent.rv_agent import RVAgent
    from rv_agent.agent.agent_factory import AgentFactory
"""

from rv_agent.agent.device_interface import DeviceInterface
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph, compute_screen_hash_from_description

__all__ = [
    "DeviceInterface",
    "DynamicStateGraph",
    "compute_screen_hash_from_description",
]
