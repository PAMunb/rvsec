"""
RV-Agent: Autonomous Android Testing Agent with LangChain and ReAct Pattern

This module implements an autonomous Android testing agent that uses LangChain
framework with ReAct (Reasoning and Acting) patterns to intelligently explore
Android applications.

Key Features:
- Process isolation architecture with full framework support
- Coordinate enhancement for 100% action success rate
- Memory components for intelligent exploration
- Scientific validation based on Phase 0 results

Architecture:
- MVP-First strategy: Standalone client with optional server integration
- LangChain direct integration (Ollama, Anthropic, OpenAI)
- rv-uiautomator integration for device control
- Extensive debugging and metrics collection
"""

__version__ = "0.1.0"
__author__ = "RV-Android Team"

# Core components (temporary - avoid circular imports during development)
# from .core.agent import RVAgent  # Will be implemented after DeviceInterface
from .config.agent_config import RVAgentConfig

# Constants
from .constants import RVAgentConstants

__all__ = [
    # "RVAgent",  # Coming soon
    "RVAgentConfig",
    "RVAgentConstants",
]
