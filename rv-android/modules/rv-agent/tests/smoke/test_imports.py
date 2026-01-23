"""
Module import tests.

Validates that all rv_agent modules import without error.
"""

import pytest


pytestmark = pytest.mark.smoke


class TestImports:
    """Test module imports."""

    def test_import_rv_agent_package(self):
        """Main rv_agent package imports."""
        import rv_agent

        assert rv_agent is not None

    def test_import_agent_modules(self):
        """Agent modules import without error."""
        from rv_agent.agent import rv_agent
        from rv_agent.agent import agent_factory

        assert rv_agent is not None
        assert agent_factory is not None

    def test_import_config(self):
        """Config module imports."""
        from rv_agent.config import agent_config
        from rv_agent.config.agent_config import RVAgentConfig

        assert agent_config is not None
        assert RVAgentConfig is not None

    def test_import_llm_modules(self):
        """LLM modules import without error."""
        from rv_agent.llm import llm_client
        from rv_agent.llm.llm_client import LLMClient, get_android_tools

        assert llm_client is not None
        assert LLMClient is not None
        assert get_android_tools is not None

    def test_import_tools(self):
        """Tool modules import without error."""
        from rv_agent.llm.tools import tool_call_parser
        from rv_agent.llm.tools.tool_call_parser import (
            parse_tool_calls_with_strategy,
            normalize_tool_args,
        )

        assert tool_call_parser is not None
        assert parse_tool_calls_with_strategy is not None
        assert normalize_tool_args is not None

    def test_import_strategies(self):
        """Strategy modules import without error."""
        from rv_agent.strategies import base_strategy
        from rv_agent.strategies import dfs_strategy
        from rv_agent.strategies import greedy_strategy
        from rv_agent.strategies import strategy_registry

        assert base_strategy is not None
        assert dfs_strategy is not None
        assert greedy_strategy is not None
        assert strategy_registry is not None

    def test_import_execution(self):
        """Execution modules import without error."""
        from rv_agent.execution import tool_executor

        assert tool_executor is not None

    def test_import_memory(self):
        """Memory modules import without error."""
        from rv_agent.memory import memory_coordinator
        from rv_agent.memory import agent_memory

        assert memory_coordinator is not None
        assert agent_memory is not None

    def test_import_routing(self):
        """Routing modules import without error."""
        from rv_agent.routing import routing_manager
        from rv_agent.routing import fallback_manager

        assert routing_manager is not None
        assert fallback_manager is not None

    def test_import_services(self):
        """Services modules import without error."""
        from rv_agent.services import screen_analyzer
        from rv_agent.services import vision_service

        assert screen_analyzer is not None
        assert vision_service is not None

    def test_import_ui_module(self):
        """UI modules import without error."""
        from rv_agent.ui import rvagent_visitor
        from rv_agent.ui.rvagent_visitor import RVAgentVisitor

        assert rvagent_visitor is not None
        assert RVAgentVisitor is not None

    def test_no_circular_dependencies(self):
        """No circular imports between core modules."""
        # Import all modules in different orders
        from rv_agent.llm.llm_client import LLMClient
        from rv_agent.config.agent_config import RVAgentConfig

        # Reimport in different order
        from rv_agent.config.agent_config import RVAgentConfig as RC2
        from rv_agent.llm.llm_client import LLMClient as LC2

        assert RC2 is RVAgentConfig
        assert LC2 is LLMClient

    def test_import_prompts(self):
        """Prompt modules import without error."""
        from rv_agent.prompts import v12

        assert v12 is not None
        assert hasattr(v12, "SYSTEM_PROMPT")
        assert hasattr(v12, "build_user_message")
