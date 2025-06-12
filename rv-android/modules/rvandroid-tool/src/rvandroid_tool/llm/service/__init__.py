# rvandroid/llm/service/__init__.py
"""
Service components for the LLM-based action generation system.

This package contains specialized components that handle different aspects
of the LLM-based action generation workflow:

- action_generator.py: Generates framework-compatible actions
- llm_manager.py: Manages language model instances and interactions
- prompt_processor.py: Handles prompt creation and management
- response_processor.py: Processes and validates LLM responses
- state_enricher.py: Enriches application state with UI information
- state_analyzer.py: Analyzes application state and context
- transition_manager.py: Manages application navigation models
"""

from rvandroid_tool.llm.service.action_generator import ActionGenerator
from rvandroid_tool.llm.service.llm_manager import LLMManager
from rvandroid_tool.llm.service.response_processor import ResponseProcessor
from rvandroid_tool.llm.service.state_analyzer import StateAnalyzer
from rvandroid_tool.llm.service.state_enricher import StateEnricher
from rvandroid_tool.llm.service.transition_manager import TransitionManager

__all__ = [
    'ActionGenerator',
    'LLMManager',
    'StateEnricher',
    'ResponseProcessor',
    'StateAnalyzer',
    'TransitionManager'
]
