"""
RV-Agent Tool Module

Tool wrapper for rv-agent integration with rv-platform.

This module provides AbstractTool implementation that wraps rv-agent
for execution within the rv-platform task execution framework.

Key Components:
- RVAgentTool: AbstractTool implementation for rv-agent
- Config mapping: Converts platform Task/ToolConfig to RVAgentConfig

Integration:
- Registers as plugin via rv-tools plugin system
- Uses rv-agent AgentFactory for agent creation
- Supports static analysis data from platform task context
"""

from rvagent_tool.tools.rvagent.tool import RVAgentTool

__version__ = "0.1.0"
__all__ = ["RVAgentTool"]
