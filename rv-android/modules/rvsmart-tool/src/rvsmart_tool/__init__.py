"""
RVSmart Tool Module

Tool wrapper for rvsmart integration with rv-platform.

This module provides AbstractTool implementation that wraps the RVSmart
Java exploration agent for execution within the rv-platform task execution
framework. RVSmart runs inside the Android emulator via app_process,
performing algorithmic or hybrid LLM-guided UI exploration.

Key Components:
- RVSmartTool: AbstractTool implementation for rvsmart
- JAR resolution: Locates rvsmart.jar across multiple search paths
- Metrics extraction: Parses RVSMART_METRICS from trace output

Integration:
- Registers as external tool via rv-platform on import
- Uses JarResolver for JAR file discovery
- Pushes JAR and config files to device via ADB
"""

from rvsmart_tool.tools.rvsmart.tool import RVSmartTool

__version__ = "0.1.0"
__all__ = ["RVSmartTool"]
