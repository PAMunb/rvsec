"""
Configuration generator module for test framework.

This module provides utilities for generating valid tool configurations
for testing with the RV-Android framework.
"""

import itertools
from typing import Dict, List, Set, Tuple, Any, Optional, Iterator

from rvandroid.test_framework.config import ToolConfiguration, TestSuite
from rvandroid.test_framework.config_validator import validate_configuration, ConfigurationValidator


class ConfigurationGenerator:
    """
    Generator for tool configurations.
    
    Creates valid tool configurations for testing with RV-Android,
    automatically validating them against compatibility rules.
    
    ### Key Responsibilities:
    - Generates valid tool configurations based on specified parameters
    - Provides preset configurations for common testing scenarios
    - Filters configurations by specified criteria
    - Validates all generated configurations
    """
    
    def __init__(self):
        """Initialize the configuration generator."""
        self.validator = ConfigurationValidator()
    
    def generate_rvandroid_configuration(self, 
                                        llm_type: str = "ollama",
                                        llm_model: str = None,
                                        strategy_type: str = "composable_single_action",
                                        visitor_type: str = "enhanced",
                                        timeout: int = 300,
                                        temperature: float = 0.2,
                                        max_tokens: int = 800) -> ToolConfiguration:
        """
        Generate a standard RVAndroid configuration.
        
        Args:
            llm_type: LLM provider type
            llm_model: LLM model name (if None, will use a default for the specified llm_type)
            strategy_type: Prompt strategy type
            visitor_type: Visitor type for parsing
            timeout: Timeout in seconds
            temperature: Temperature parameter for LLM
            max_tokens: Maximum tokens for LLM
            
        Returns:
            A validated ToolConfiguration instance
        """
        # Import LLM classes for constants
        from rvandroid.llm.ollama_llm import OllamaLLM
        from rvandroid.llm.huggingface_llm import HuggingFaceLLM
        from rvandroid.llm.dspy_llm import DSPyLLM
        
        # Import ConfigurationValidator for LangchainLLM and FrontierModel constants
        from rvandroid.test_framework.config_validator import ConfigurationValidator, LANGCHAIN_NAME
        
        # Try to import FrontierModel if available
        try:
            from rvandroid.llm.frontier_models import FrontierModel
        except ImportError:
            from rvandroid.test_framework.config_validator import FrontierModel
        
        # Use appropriate default model based on LLM type if not specified
        if llm_model is None:
            if llm_type == OllamaLLM.NAME:
                llm_model = OllamaLLM.LLAMA
            elif llm_type == HuggingFaceLLM.NAME:
                llm_model = HuggingFaceLLM.LLAMA
            elif llm_type == DSPyLLM.NAME:
                llm_model = HuggingFaceLLM.LLAMA  # Using HuggingFace model for DSPy
            elif llm_type == LANGCHAIN_NAME:
                llm_model = "llama3.2:3b"  # Default Ollama model for Langchain
            elif llm_type == FrontierModel.NAME:
                llm_model = FrontierModel.CLAUDE_SONNET
            else:
                # Default fallback
                llm_model = OllamaLLM.LLAMA
        
        config = ToolConfiguration(
            tool_name="rvandroid",
            timeout=timeout,
            llm_type=llm_type,
            llm_model=llm_model,
            temperature=temperature,
            max_tokens=max_tokens,
            strategy_type=strategy_type,
            parser_type="droidbot",  # RVAndroid only works with droidbot parser
            visitor_type=visitor_type,
            use_static_analysis=True,
            static_analysis_level="detailed",
            use_screenshot_analysis=False
        )
        
        # Validate the configuration
        is_valid, errors = self.validator.validate_configuration(config)
        if not is_valid:
            error_str = "\n".join(errors)
            raise ValueError(f"Invalid RVAndroid configuration:\n{error_str}")
        
        return config
    
    def generate_rvdroid_configuration(self,
                                      llm_type: str = "ollama",
                                      llm_model: str = None, 
                                      strategy_type: str = "composable_single_action",
                                      visitor_type: str = "enhanced",
                                      timeout: int = 300,
                                      temperature: float = 0.2,
                                      max_tokens: int = 800,
                                      use_screenshot_analysis: bool = True) -> ToolConfiguration:
        """
        Generate a standard RVDroid configuration.
        
        Args:
            llm_type: LLM provider type
            llm_model: LLM model name (if None, will use a default for the specified llm_type)
            strategy_type: Prompt strategy type
            visitor_type: Visitor type for parsing
            timeout: Timeout in seconds
            temperature: Temperature parameter for LLM
            max_tokens: Maximum tokens for LLM
            use_screenshot_analysis: Whether to use screenshot analysis
            
        Returns:
            A validated ToolConfiguration instance
        """
        # Import LLM classes for constants
        from rvandroid.llm.ollama_llm import OllamaLLM
        from rvandroid.llm.huggingface_llm import HuggingFaceLLM
        from rvandroid.llm.dspy_llm import DSPyLLM
        
        # Import ConfigurationValidator for LangchainLLM and FrontierModel constants
        from rvandroid.test_framework.config_validator import ConfigurationValidator, LANGCHAIN_NAME
        
        # Try to import FrontierModel if available
        try:
            from rvandroid.llm.frontier_models import FrontierModel
        except ImportError:
            from rvandroid.test_framework.config_validator import FrontierModel
        
        # Use appropriate default model based on LLM type if not specified
        if llm_model is None:
            if llm_type == OllamaLLM.NAME:
                llm_model = OllamaLLM.LLAMA
            elif llm_type == HuggingFaceLLM.NAME:
                llm_model = HuggingFaceLLM.LLAMA
            elif llm_type == DSPyLLM.NAME:
                llm_model = HuggingFaceLLM.LLAMA  # Using HuggingFace model for DSPy
            elif llm_type == LANGCHAIN_NAME:
                llm_model = "llama3.2:3b"  # Default Ollama model for Langchain
            elif llm_type == FrontierModel.NAME:
                llm_model = FrontierModel.CLAUDE_SONNET
            else:
                # Default fallback
                llm_model = OllamaLLM.LLAMA
        
        config = ToolConfiguration(
            tool_name="rvdroid",
            timeout=timeout,
            llm_type=llm_type,
            llm_model=llm_model,
            temperature=temperature,
            max_tokens=max_tokens,
            strategy_type=strategy_type,
            parser_type="uiautomator",  # RVDroid only works with uiautomator parser
            visitor_type=visitor_type,
            use_static_analysis=True,
            static_analysis_level="standard",
            use_screenshot_analysis=use_screenshot_analysis,
            screenshot_analysis_level="standard",
            extra_params={"use_llm": True}
        )
        
        # Validate the configuration
        is_valid, errors = self.validator.validate_configuration(config)
        if not is_valid:
            error_str = "\n".join(errors)
            raise ValueError(f"Invalid RVDroid configuration:\n{error_str}")
        
        return config
    
    def generate_all_combinations(self, 
                                 tools: List[str] = None,
                                 llm_types: List[str] = None,
                                 models: Dict[str, List[str]] = None,
                                 strategy_types: List[str] = None,
                                 visitor_types: List[str] = None,
                                 timeouts: List[int] = None,
                                 static_analysis_levels: List[str] = None,
                                 use_screenshot_analysis: List[bool] = None) -> List[ToolConfiguration]:
        """
        Generate all valid combinations of configuration parameters.
        
        Args:
            tools: List of tools to include
            llm_types: List of LLM provider types
            models: Dictionary mapping LLM types to model names
            strategy_types: List of strategy types
            visitor_types: List of visitor types
            timeouts: List of timeouts in seconds
            static_analysis_levels: List of static analysis levels
            use_screenshot_analysis: List of boolean values for screenshot analysis
            
        Returns:
            List of valid ToolConfiguration instances
        """
        # Define defaults if not provided
        if tools is None:
            tools = ["rvandroid", "rvdroid"]
        
        if llm_types is None:
            llm_types = ["ollama"]
        
        if models is None:
            # Import LLM classes for constants
            from rvandroid.llm.ollama_llm import OllamaLLM
            from rvandroid.llm.huggingface_llm import HuggingFaceLLM
            from rvandroid.llm.dspy_llm import DSPyLLM
            
            # Import constants from config_validator
            from rvandroid.test_framework.config_validator import LANGCHAIN_NAME, LANGCHAIN_MODELS
            
            # Try to import FrontierModel if available
            try:
                from rvandroid.llm.frontier_models import FrontierModel
            except ImportError:
                from rvandroid.test_framework.config_validator import FrontierModel
            
            models = {
                OllamaLLM.NAME: [OllamaLLM.LLAMA],
                HuggingFaceLLM.NAME: [HuggingFaceLLM.LLAMA],
                DSPyLLM.NAME: [HuggingFaceLLM.LLAMA],  # Using HuggingFace model for DSPy
                LANGCHAIN_NAME: [LANGCHAIN_MODELS[0]],  # Use first LangchainLLM model
                FrontierModel.NAME: [FrontierModel.CLAUDE_SONNET]
            }
        
        if strategy_types is None:
            strategy_types = ["composable_single_action"]
        
        if visitor_types is None:
            visitor_types = ["enhanced"]
        
        if timeouts is None:
            timeouts = [300]
        
        if static_analysis_levels is None:
            static_analysis_levels = ["detailed"]
        
        if use_screenshot_analysis is None:
            use_screenshot_analysis = [False, True]
        
        # Temperature and max_tokens are fixed for simplicity
        temperature = 0.2
        max_tokens = 800
        
        valid_configurations = []
        
        # Generate configs for RVAndroid
        if "rvandroid" in tools:
            for llm_type in llm_types:
                # Skip if no models for this LLM type
                if llm_type not in models:
                    continue
                
                for model in models[llm_type]:
                    for strategy in strategy_types:
                        for visitor in visitor_types:
                            for timeout in timeouts:
                                for static_level in static_analysis_levels:
                                    try:
                                        config = ToolConfiguration(
                                            tool_name="rvandroid",
                                            timeout=timeout,
                                            llm_type=llm_type,
                                            llm_model=model,
                                            temperature=temperature,
                                            max_tokens=max_tokens,
                                            strategy_type=strategy,
                                            parser_type="droidbot",  # Fixed for RVAndroid
                                            visitor_type=visitor,
                                            use_static_analysis=True,
                                            static_analysis_level=static_level,
                                            use_screenshot_analysis=False  # Screenshot analysis not supported in RVAndroid
                                        )
                                        
                                        # Validate the configuration
                                        is_valid, errors = self.validator.validate_configuration(config)
                                        if is_valid:
                                            valid_configurations.append(config)
                                    except Exception as e:
                                        # Skip invalid configurations
                                        pass
        
        # Generate configs for RVDroid
        if "rvdroid" in tools:
            for llm_type in llm_types:
                # Skip if no models for this LLM type
                if llm_type not in models:
                    continue
                
                for model in models[llm_type]:
                    for strategy in strategy_types:
                        for visitor in visitor_types:
                            for timeout in timeouts:
                                for static_level in static_analysis_levels:
                                    for use_screenshot in use_screenshot_analysis:
                                        try:
                                            config = ToolConfiguration(
                                                tool_name="rvdroid",
                                                timeout=timeout,
                                                llm_type=llm_type,
                                                llm_model=model,
                                                temperature=temperature,
                                                max_tokens=max_tokens,
                                                strategy_type=strategy,
                                                parser_type="uiautomator",  # Fixed for RVDroid
                                                visitor_type=visitor,
                                                use_static_analysis=True,
                                                static_analysis_level=static_level,
                                                use_screenshot_analysis=use_screenshot,
                                                screenshot_analysis_level="standard",
                                                extra_params={"use_llm": True}
                                            )
                                            
                                            # Validate the configuration
                                            is_valid, errors = self.validator.validate_configuration(config)
                                            if is_valid:
                                                valid_configurations.append(config)
                                        except Exception as e:
                                            # Skip invalid configurations
                                            pass
        
        return valid_configurations
    
    def generate_minimal_test_suite(self) -> TestSuite:
        """
        Generate a minimal test suite with basic configurations.
        
        Returns:
            TestSuite with basic configurations for both tools
        """
        configs = []
        
        # Add RVAndroid with ollama
        configs.append(self.generate_rvandroid_configuration())
        
        # Add RVDroid with ollama
        configs.append(self.generate_rvdroid_configuration())
        
        # Create and return test suite
        return TestSuite(
            name="Minimal Test Suite",
            description="Basic configurations for RVAndroid and RVDroid",
            tool_configurations=configs,
            repetitions=1
        )
    
    def generate_plateau_test_suite(self, 
                                   tool_name: str = "rvandroid",
                                   timeouts: List[int] = [60, 120, 180, 300, 600]) -> TestSuite:
        """
        Generate a test suite specifically for plateau analysis.
        
        Args:
            tool_name: Tool to use for plateau analysis
            timeouts: List of timeouts to analyze
            
        Returns:
            TestSuite with configurations using different timeouts
        """
        configs = []
        
        for timeout in timeouts:
            if tool_name == "rvandroid":
                config = self.generate_rvandroid_configuration(timeout=timeout)
                configs.append(config)
            elif tool_name == "rvdroid":
                config = self.generate_rvdroid_configuration(timeout=timeout)
                configs.append(config)
        
        return TestSuite(
            name=f"Plateau Analysis - {tool_name}",
            description=f"Test suite for analyzing metric plateaus with different timeouts for {tool_name}",
            tool_configurations=configs,
            repetitions=1
        )
    
    def generate_comparative_test_suite(self) -> TestSuite:
        """
        Generate a test suite for comparing different configurations.
        
        Returns:
            TestSuite with various configurations for comparison
        """
        # Import LLM classes for constants
        from rvandroid.llm.ollama_llm import OllamaLLM
        from rvandroid.llm.dspy_llm import DSPyLLM
        from rvandroid.llm.huggingface_llm import HuggingFaceLLM
        
        configs = []
        
        # RVAndroid configurations
        strategies = ["basic", "single_action", "composable_single_action"]
        
        # Ollama configurations
        for strategy in strategies:
            configs.append(self.generate_rvandroid_configuration(
                llm_type=OllamaLLM.NAME,
                llm_model=OllamaLLM.LLAMA,
                strategy_type=strategy
            ))
        
        # DSPy configurations
        for strategy in strategies:
            configs.append(self.generate_rvandroid_configuration(
                llm_type=DSPyLLM.NAME,
                llm_model=HuggingFaceLLM.LLAMA,  # Using HuggingFace model for DSPy
                strategy_type=strategy
            ))
        
        # RVDroid configurations with ollama
        for strategy in strategies:
            configs.append(self.generate_rvdroid_configuration(
                llm_type=OllamaLLM.NAME,
                llm_model=OllamaLLM.LLAMA,
                strategy_type=strategy,
                use_screenshot_analysis=True
            ))
            
            # Also add without screenshot analysis for comparison
            configs.append(self.generate_rvdroid_configuration(
                llm_type=OllamaLLM.NAME,
                llm_model=OllamaLLM.LLAMA,
                strategy_type=strategy,
                use_screenshot_analysis=False
            ))
        
        return TestSuite(
            name="Comparative Test Suite",
            description="Test suite for comparing different configurations of RVAndroid and RVDroid",
            tool_configurations=configs,
            repetitions=1
        )


# Convenience functions
def create_minimal_test_suite() -> TestSuite:
    """
    Create a minimal test suite with basic configurations.
    
    Returns:
        TestSuite with basic configurations
    """
    generator = ConfigurationGenerator()
    return generator.generate_minimal_test_suite()


def create_plateau_test_suite(tool_name: str = "rvandroid", 
                             timeouts: List[int] = [60, 120, 180, 300, 600]) -> TestSuite:
    """
    Create a test suite for plateau analysis.
    
    Args:
        tool_name: Tool to use for plateau analysis
        timeouts: List of timeouts to analyze
        
    Returns:
        TestSuite for plateau analysis
    """
    generator = ConfigurationGenerator()
    return generator.generate_plateau_test_suite(tool_name, timeouts)


def create_comparative_test_suite() -> TestSuite:
    """
    Create a test suite for comparing different configurations.
    
    Returns:
        TestSuite for configuration comparison
    """
    generator = ConfigurationGenerator()
    return generator.generate_comparative_test_suite()