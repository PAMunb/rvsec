"""
RVAndroid tool implementation for monitored operations testing.

This module provides the RVAndroid tool with LLM-based testing capabilities
and hybrid variant configuration system for comprehensive monitored operations testing.
"""

from typing import Dict, Any, List

from rv_android_core.domain.app import App
from rv_android_core.commands.command import Command
from rv_android_core.domain.task import Task
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.llm.constants import LLMType, PromptStrategyType
from rv_screen_parser.constants import ScreenParserType, VisitorType


class RVAndroidTool(AbstractTool):
    """
    RVAndroid LLM-based testing tool for monitored operations testing.

    ### Architectural Decisions:
    - Inherits from AbstractTool for consistent tool integration
    - Implements LLM-based testing with configurable strategies and models
    - Supports hybrid variant system for both simple and complex configurations
    - Integrates with rv-android-core infrastructure for error handling and logging
    - Uses modern configuration management with PromptConfig and LLMConfig separation

    ### Role in the System:
    - Provides LLM-driven test generation for monitored operations
    - Supports multiple LLM backends (Ollama, OpenAI, Anthropic, etc.)
    - Enables configurable prompt strategies for different testing scenarios
    - Facilitates screen parsing and visitor-based UI analysis
    - Integrates with both JCA cryptography and generic monitored operations testing

    ### Key Features:
    - Multiple LLM backends with configurable models and parameters
    - Prompt strategy selection (standard, batch_action)
    - Screen parser integration (DroidBot, UIAutomator)
    - Visitor-based UI analysis (basic, detailed, default)
    - Hybrid variant system for flexibility and ease of use
    - Template-based prompt generation system

    ### Tool Variants:
    RVAndroid supports pre-configured variants for common configurations:
    - llama_batch_detailed: Ollama + Llama3.2 + Batch Action + Detailed Analysis
    - gpt4_standard_basic: OpenAI GPT-4 + Standard Strategy + Basic Analysis
    - claude_context_enhanced: Anthropic Claude + Context Strategy + Enhanced Analysis
    - Custom configurations via parameter override system
    """
    
    # Tool specification required by rv-tools registry
    TOOL_SPEC = None  # Will be set after get_tool_spec is defined

    def __init__(self, name: str, description: str, process_pattern: str):
        """
        Initialize RVAndroid tool with LLM-based testing capabilities.

        Args:
            name: Tool name
            description: Tool description
            process_pattern: Process pattern for tool execution
        """
        super().__init__(name, description, process_pattern)
        
        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_tools.builtin.rvandroid",
            {CONTEXT_COMPONENT: "RVAndroidTool"}
        )
        
        self.logger.info("RVAndroid tool initialized")

    @ErrorHandler.handle_errors(
        component="RVAndroidTool",
        operation="configure"
    )
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure the RVAndroid tool with LLM and prompt settings.

        ### Configuration Strategy:
        This method processes hybrid configuration that can include:
        - LLM backend configuration (llm_type, model, temperature, etc.)
        - Prompt configuration (strategy_type, parser_type, visitor_type)
        - Additional parameters for fine-tuning

        Args:
            config: Configuration dictionary with LLM and prompt settings
        """
        super().configure(config)
        
        # Log configuration details
        llm_info = f"LLM: {config.get('llm_backend', 'default')}"
        model_info = f"Model: {config.get('llm_model', 'default')}"
        strategy_info = f"Strategy: {config.get('prompt_strategy', 'default')}"
        
        self.logger.info(f"Configured RVAndroid tool - {llm_info}, {model_info}, {strategy_info}")

    @ErrorHandler.handle_errors(
        component="RVAndroidTool",
        operation="run"
    )
    def run(self, app: App, task: Task) -> Command:
        """
        Execute RVAndroid tool with LLM-based testing approach.

        ### Execution Strategy:
        This method coordinates the LLM-based testing process:
        1. Initialize LLM components based on configuration
        2. Set up prompt framework with configured strategy
        3. Execute testing loop with state analysis and action generation
        4. Handle results and generate appropriate commands

        Args:
            app: Application to test
            task: Task configuration and parameters

        Returns:
            Command object representing the tool execution
        """
        self.logger.info(f"Starting RVAndroid execution for app: {app.package_name}")
        
        # Create execution command
        # Note: Actual tool execution logic would be implemented here
        # This is a placeholder that follows the AbstractTool interface
        command = Command(
            name=f"rvandroid_{task.id}",
            description=f"RVAndroid LLM-based testing for {app.package_name}",
            command_line=f"python -m rvandroid_tool --app {app.package_name}",
            working_directory=task.working_directory,
            timeout=task.timeout if hasattr(task, 'timeout') else 3600
        )
        
        return command

    def get_supported_variants(self) -> List[str]:
        """
        Get list of supported RVAndroid variants.

        Returns:
            List of supported variant names
        """
        return list(RVANDROID_VARIANTS.keys())

    def get_variant_config(self, variant_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific variant.

        Args:
            variant_name: Name of the variant

        Returns:
            Configuration dictionary for the variant
        """
        return RVANDROID_VARIANTS.get(variant_name, {})


# Pre-configured variants for RVAndroid tool
RVANDROID_VARIANTS = {
    "llama_batch_detailed": {
        "llm_backend": LLMType.OLLAMA,
        "llm_model": "llama3.2:3b",
        "llm_base_url": "http://localhost:11434",
        "llm_temperature": 0.2,
        "llm_max_tokens": 800,
        "prompt_strategy": PromptStrategyType.BATCH_ACTION,
        "screen_parser": ScreenParserType.DROIDBOT,
        "visitor_type": VisitorType.DETAILED,
        "max_context_length": 8192,
        "description": "Ollama Llama3.2 with batch action strategy and detailed analysis"
    },
    "gpt4_standard_basic": {
        "llm_backend": LLMType.FRONTIER,
        "llm_model": "gpt-4",
        "llm_provider": "openai",
        "llm_temperature": 0.3,
        "llm_max_tokens": 600,
        "prompt_strategy": PromptStrategyType.STANDARD,
        "screen_parser": ScreenParserType.DROIDBOT,
        "visitor_type": VisitorType.BASIC,
        "max_context_length": 16384,
        "description": "OpenAI GPT-4 with standard strategy and basic analysis"
    },
    "claude_context_enhanced": {
        "llm_backend": LLMType.FRONTIER,
        "llm_model": "claude-3-5-sonnet-20241022",
        "llm_provider": "anthropic",
        "llm_temperature": 0.1,
        "llm_max_tokens": 1000,
        "prompt_strategy": PromptStrategyType.STANDARD,
        "screen_parser": ScreenParserType.UIAUTOMATOR,
        "visitor_type": VisitorType.DEFAULT,
        "max_context_length": 32768,
        "description": "Anthropic Claude with context strategy and enhanced analysis"
    },
    "local_llama_fast": {
        "llm_backend": LLMType.OLLAMA,
        "llm_model": "llama3.2:1b",
        "llm_base_url": "http://localhost:11434",
        "llm_temperature": 0.4,
        "llm_max_tokens": 400,
        "prompt_strategy": PromptStrategyType.STANDARD,
        "screen_parser": ScreenParserType.DROIDBOT,
        "visitor_type": VisitorType.BASIC,
        "max_context_length": 4096,
        "description": "Fast local Llama3.2 1B model for quick testing"
    },
    "gemini_comprehensive": {
        "llm_backend": LLMType.FRONTIER,
        "llm_model": "gemini-pro",
        "llm_provider": "google",
        "llm_temperature": 0.2,
        "llm_max_tokens": 800,
        "prompt_strategy": PromptStrategyType.BATCH_ACTION,
        "screen_parser": ScreenParserType.UIAUTOMATOR,
        "visitor_type": VisitorType.DETAILED,
        "max_context_length": 16384,
        "description": "Google Gemini Pro with comprehensive analysis"
    }
}


def register_rvandroid_variants(registry):
    """
    Register RVAndroid variants in the tool registry.
    
    ### Variant Registration Strategy:
    This function registers pre-configured variants that provide common
    configurations for different use cases. Each variant includes:
    - LLM backend configuration
    - Prompt strategy settings
    - Screen parser and visitor configuration
    - Performance-optimized parameters
    
    Args:
        registry: ToolRegistry instance
    """
    for variant_name, config in RVANDROID_VARIANTS.items():
        registry.register_variant("rvandroid", variant_name, config)
    
    # Log successful registration
    logging_manager = LoggingManager.get_instance()
    logger = logging_manager.get_logger(
        "rv_tools.builtin.rvandroid",
        {CONTEXT_COMPONENT: "RVAndroidVariants"}
    )
    logger.info(f"Registered {len(RVANDROID_VARIANTS)} RVAndroid variants")


def get_tool_spec() -> ToolSpec:
    """
    Get the tool specification for RVAndroid.

    Returns:
        ToolSpec instance for RVAndroid tool
    """
    return ToolSpec(
        name="rvandroid",
        description="LLM-based testing tool for monitored operations",
        url="https://github.com/rvandroid/rvandroid-tool",
        version="1.0.0",
        process_pattern="rvandroid_tool"
    )


# Set the TOOL_SPEC after the function is defined
RVAndroidTool.TOOL_SPEC = get_tool_spec()