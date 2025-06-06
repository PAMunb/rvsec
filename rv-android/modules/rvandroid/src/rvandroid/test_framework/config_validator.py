"""
Configuration validator module for test framework.

This module provides validation services for test framework configurations,
ensuring that configurations are valid and compatible with the MCP architecture.
"""

from typing import Dict, List, Set, Tuple, Any, Optional

from rv_android_core.llm.constants import ScreenParserType, VisitorType, PromptStrategyType, LLMType
from rv_android_core.llm.ollama_llm import OllamaLLM
from rv_android_core.test_framework.config import ToolConfiguration


class ValidationError(Exception):
    """
    Exception raised for configuration validation errors.
    
    ### Architectural Decisions:
    - Uses standard exception model for error reporting
    - Provides detailed error context for debugging
    - Supports both single and multiple error reporting
    - Integrates with higher-level error handling mechanisms
    
    ### Role in the System:
    - Signals invalid configuration parameters
    - Provides clear error messages for troubleshooting
    - Prevents execution with invalid configurations
    - Enables consistent error handling across the framework
    """
    
    def __init__(self, message: str, errors: List[str] = None):
        """
        Initialize a validation error.
        
        Args:
            message: Main error message
            errors: List of specific validation errors
        """
        self.message = message
        self.errors = errors or []
        error_msg = f"{message}"
        if self.errors:
            error_details = "\n- " + "\n- ".join(self.errors)
            error_msg += f": {error_details}"
        super().__init__(error_msg)


class ConfigurationValidator:
    """
    Validator for tool configurations.
    
    Ensures that tool configurations are valid and compatible with
    the messages architecture.
    
    ### Key Responsibilities:
    - Validates configuration parameters against defined rules
    - Checks compatibility between components
    - Validates LLM-specific configuration parameters
    - Provides detailed error messages for invalid configurations
    - Prevents execution of incompatible configurations
    """
    
    # Define LLM model types
    LLM_OLLAMA = OllamaLLM.NAME
    
    # LLM models
    LLM_OLLAMA_MODELS = OllamaLLM.MODELS
    
    # Define constants for Frontier and other model types
    FRONTIER_NAME = "frontier"
    FRONTIER_MODELS = ["claude-3-sonnet-20240229", "claude-3-opus-20240229"]
    
    # Define known compatibility rules
    TOOL_PARSER_COMPATIBILITY = {
        "rvandroid": [ScreenParserType.DROIDBOT],
        "rvdroid": [ScreenParserType.UIAUTOMATOR]
    }
    
    PARSER_VISITOR_COMPATIBILITY = {
        ScreenParserType.DROIDBOT: [VisitorType.BASIC, VisitorType.DEFAULT, VisitorType.DETAILED],
        ScreenParserType.UIAUTOMATOR: [VisitorType.BASIC, VisitorType.DEFAULT, VisitorType.DETAILED]
    }
    
    # MCP strategy types
    VALID_STRATEGY_TYPES = PromptStrategyType.ALL
    
    # Valid LLM types
    # VALID_LLM_TYPES = [ LLMType.OLLAMA, LLMType.DSPY, LLMType.LANGCHAIN, LLMType.FRONTIER, LLMType.HUGGINGFACE]
    VALID_LLM_TYPES = [LLMType.OLLAMA]
    
    VALID_STATIC_ANALYSIS_LEVELS = ["basic", "standard", "detailed"]  # TODO remover
    VALID_SCREENSHOT_ANALYSIS_LEVELS = ["basic", "standard", "detailed"]
    VALID_MONITORED_OPERATIONS_PRIORITIES = ["high", "medium", "low"]
    
    # Model-specific validation
    MODEL_COMPATIBILITY = {
        LLM_OLLAMA: LLM_OLLAMA_MODELS,
        FRONTIER_NAME: FRONTIER_MODELS
    }
    
    def __init__(self):
        """Initialize the configuration validator."""
        pass
    
    def validate_configuration(self, config: ToolConfiguration) -> Tuple[bool, List[str]]:
        """
        Validate a tool configuration.
        
        Args:
            config: The configuration to validate
            
        Returns:
            Tuple containing (is_valid, list_of_errors)
        """
        errors = []
        
        # Check tool name
        if config.tool_name not in self.TOOL_PARSER_COMPATIBILITY:
            errors.append(f"Invalid tool name: {config.tool_name}. Valid tools: {list(self.TOOL_PARSER_COMPATIBILITY.keys())}")
        
        # Check LLM type
        if config.llm_type not in self.VALID_LLM_TYPES:
            errors.append(f"Invalid LLM type: {config.llm_type}. Valid types: {self.VALID_LLM_TYPES}")
        
        # Check LLM model compatibility
        if config.llm_type in self.MODEL_COMPATIBILITY:
            if config.llm_model not in self.MODEL_COMPATIBILITY[config.llm_type]:
                errors.append(f"Invalid model for {config.llm_type}: {config.llm_model}. "
                             f"Valid models: {self.MODEL_COMPATIBILITY[config.llm_type]}")
        
        # Check strategy type
        if config.strategy_type not in self.VALID_STRATEGY_TYPES:
            errors.append(f"Invalid strategy type: {config.strategy_type}. Valid types: {self.VALID_STRATEGY_TYPES}")
        
        # Check tool-parser compatibility
        if config.tool_name in self.TOOL_PARSER_COMPATIBILITY:
            valid_parsers = self.TOOL_PARSER_COMPATIBILITY[config.tool_name]
            if config.parser_type not in valid_parsers:
                errors.append(f"Parser '{config.parser_type}' is not compatible with tool '{config.tool_name}'. "
                             f"Valid parsers: {valid_parsers}")
        
        # Check parser-visitor compatibility
        if config.parser_type in self.PARSER_VISITOR_COMPATIBILITY:
            valid_visitors = self.PARSER_VISITOR_COMPATIBILITY[config.parser_type]
            if config.visitor_type not in valid_visitors:
                errors.append(f"Visitor '{config.visitor_type}' is not compatible with parser '{config.parser_type}'. "
                             f"Valid visitors: {valid_visitors}")
        
        # Check static analysis level
        if config.use_static_analysis and config.static_analysis_level not in self.VALID_STATIC_ANALYSIS_LEVELS:
            errors.append(f"Invalid static analysis level: {config.static_analysis_level}. "
                         f"Valid levels: {self.VALID_STATIC_ANALYSIS_LEVELS}")
        
        # Check screenshot analysis level
        if config.use_screenshot_analysis and config.screenshot_analysis_level not in self.VALID_SCREENSHOT_ANALYSIS_LEVELS:
            errors.append(f"Invalid screenshot analysis level: {config.screenshot_analysis_level}. "
                         f"Valid levels: {self.VALID_SCREENSHOT_ANALYSIS_LEVELS}")
        
        # Check monitored operations priority
        if config.monitored_operations_priority not in self.VALID_MONITORED_OPERATIONS_PRIORITIES:
            errors.append(f"Invalid monitored operations priority: {config.monitored_operations_priority}. "
                         f"Valid priorities: {self.VALID_MONITORED_OPERATIONS_PRIORITIES}")
        
        # Validate numeric parameters
        if config.temperature < 0.0 or config.temperature > 1.0:
            errors.append(f"Invalid temperature: {config.temperature}. Must be between 0.0 and 1.0")
        
        if config.max_tokens <= 0:
            errors.append(f"Invalid max_tokens: {config.max_tokens}. Must be greater than 0")
        
        # Validate MCP configuration
        if not config.use_mcp:
            errors.append("MCP must be enabled for all configurations. Legacy LLM implementations are no longer supported.")
        
        # Specific tool validations
        if config.tool_name == "rvdroid" and config.use_screenshot_analysis:
            # Ensure necessary parameters for screenshot analysis are present for RVDroid
            if "use_llm" not in config.extra_params or not config.extra_params["use_llm"]:
                errors.append(f"Screenshot analysis in RVDroid requires 'use_llm' to be set to true in extra_params")
        
        return len(errors) == 0, errors
    
    def validate_configurations(self, configs: List[ToolConfiguration]) -> Dict[str, List[str]]:
        """
        Validate multiple tool configurations.
        
        Args:
            configs: List of configurations to validate
            
        Returns:
            Dictionary mapping configuration IDs to lists of errors
        """
        validation_results = {}
        
        for config in configs:
            is_valid, errors = self.validate_configuration(config)
            if not is_valid:
                validation_results[config.get_id()] = errors
        
        return validation_results


# Convenience function for validation
def validate_configuration(config: ToolConfiguration) -> Tuple[bool, List[str]]:
    """
    Validate a single tool configuration.
    
    Args:
        config: Configuration to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    validator = ConfigurationValidator()
    return validator.validate_configuration(config)


def validate_configurations(configs: List[ToolConfiguration]) -> Dict[str, List[str]]:
    """
    Validate multiple tool configurations.
    
    Args:
        configs: List of configurations to validate
        
    Returns:
        Dictionary mapping configuration IDs to lists of errors
    """
    validator = ConfigurationValidator()
    return validator.validate_configurations(configs)