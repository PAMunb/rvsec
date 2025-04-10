# rvandroid/llm/prompt/__init__.py
"""
Prompt strategies for interacting with LLMs.
"""

# Import classes for registration
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.prompt.base_prompt_strategy import BasePromptStrategy
from rvandroid.llm.prompt.composable_prompt_strategy import ComposablePromptStrategy
from rvandroid.llm.prompt.composable_single_action_strategy import ComposableSingleActionStrategy
from rvandroid.llm.prompt.dspy_single_action_prompt_strategy import DSPySingleActionPromptStrategy
from rvandroid.llm.prompt.prompt_strategy_basic_001 import BasicPromptStrategy001
from rvandroid.llm.prompt.prompt_strategy_dspy import DSPyPromptStrategy
from rvandroid.llm.prompt.prompt_strategy_frontier import FrontierPromptStrategy
from rvandroid.llm.prompt.single_action_prompt_strategy import SingleActionPromptStrategy
from rvandroid.llm.prompt.flow_based_batch_action_strategy import FlowBasedBatchActionStrategy

# Register flow-based batch action strategy
try:
    # Only register if not already registered
    if not ComponentConfigurator._registries['strategy'].has("flow_based_batch_action"):
        ComponentConfigurator.register_strategy("flow_based_batch_action", FlowBasedBatchActionStrategy)
    
    # Also register single action strategy if not already registered
    if not ComponentConfigurator._registries['strategy'].has("single_action"):
        ComponentConfigurator.register_strategy("single_action", SingleActionPromptStrategy)
except Exception as e:
    # Strategy might already be registered
    pass