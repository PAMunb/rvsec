"""
Built-in testing tools for monitored operations.

This package contains implementations of standard testing tools that are
integrated directly into the RV-Tools framework.

### Available Tools:
- **APE**: Android Programmatic Events testing tool with CEGAR-based exploration
- **Monkey**: Android UI/Application exerciser monkey with pseudo-random events
- **Ares**: Docker-based systematic UI exploration framework
- **DroidBot**: Lightweight UI-guided testing framework with policy-based exploration  
- **DroidMate**: JAR-based systematic test input generator for research
- **FastBot**: Model-based testing tool with reinforcement learning capabilities
- **Humanoid**: Human-like testing tool with computer vision and NLP
- **QTesting**: Reinforcement learning based intelligent testing framework

### Tool Categories:
- **Random Testing**: Monkey
- **Model-Based**: APE, DroidBot, DroidMate, Ares
- **AI-Guided**: FastBot, Humanoid, QTesting
- **Systematic**: DroidMate, Ares
- **Docker-Based**: Ares
- **Learning-Based**: FastBot, Humanoid, QTesting

### Structure:
Each tool is implemented as a separate package within builtin/ with:
- tool.py: Main tool implementation extending ConfigurableTool
- __init__.py: Package exports
- Additional tool-specific modules and resources as needed
"""

# Import all available built-in tools
from .ape import APETool
from .monkey import MonkeyTool
from .ares import AresTool
from .droidbot import DroidBotTool
from .droidmate import DroidMateTool
from .fastbot import FastBotTool
from .humanoid import HumanoidTool
from .qtesting import QTestingTool

# Tool registry for built-in tools
BUILTIN_TOOLS = [
    APETool,
    MonkeyTool,
    AresTool,
    DroidBotTool,
    DroidMateTool,
    FastBotTool,
    HumanoidTool,
    QTestingTool,
]

# Tool class mapping for dynamic loading
BUILTIN_TOOL_CLASSES = {
    "ape": APETool,
    "monkey": MonkeyTool,
    "ares": AresTool,
    "droidbot": DroidBotTool,
    "droidmate": DroidMateTool,
    "fastbot": FastBotTool,
    "humanoid": HumanoidTool,
    "qtesting": QTestingTool,
}

__all__ = [
    "APETool",
    "MonkeyTool",
    "AresTool", 
    "DroidBotTool",
    "DroidMateTool",
    "FastBotTool",
    "HumanoidTool",
    "QTestingTool",
    "BUILTIN_TOOLS",
    "BUILTIN_TOOL_CLASSES"
]