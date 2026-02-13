# # rvandroid/rvdroid/strategy/__init__.py
#
# """
# Strategy module for RVDroid.
#
# This module provides a framework for creating and using different strategies
# for Android app testing.
# """
#
# # Import all strategy implementations
# from rvdroid_tool.strategy.basic_strategies import (
#     RandomStrategy,
#     SystematicStrategy,
#     SecurityFocusedStrategy
# )
# # Import strategy base classes
# from rvdroid_tool.strategy.strategy import Strategy, StrategyRegistry
# from rvdroid_tool.strategy.visual_aware_strategy import VisualAwareStrategy
#
#
# # Register all strategies with the registry
# def register_strategies():
#     """Register all available strategies with the StrategyRegistry."""
#     StrategyRegistry.register(RandomStrategy)
#     StrategyRegistry.register(SystematicStrategy)
#     StrategyRegistry.register(SecurityFocusedStrategy)
#     StrategyRegistry.register(VisualAwareStrategy)
#
#
# # Register strategies when this module is imported
# register_strategies()
