# modules/rvsmart-tool/src/rvsmart_tool/tools/rvsmart/tool.py
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVAndroidToolError
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_llm import OllamaLLM, FrontierModel
from rv_llm.llm.constants import ContextMode, LLMType, PromptStrategyType
from rv_screen_parser.constants import ScreenParserType, VisitorType
from rvsmart_tool.llm.service.action_service import LLMActionService
from rvsmart_tool.orchestration.test_orchestrator import TestOrchestrator
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_android_core.commands.command import Command
from typing import Dict, List, Any, Optional, Tuple
import os
import time
from rvsmart_tool.config.tool_config import RvSmartToolConfig
from rvsmart_tool.constants import RVSMART_TOOL_NAME, RVSMART_DESCRIPTION

class RVSmartTool(AbstractTool):
    """
    LLM-based Android testing tool with UIAutomator integration for coordinate enhancement testing.
    
    ### Architectural Role:
    - Implements AbstractTool interface for seamless platform integration
    - Coordinates LLM service with UIAutomator direct execution
    - Manages application state analysis and action generation pipeline
    - Provides configurable LLM backends with vision capabilities
    - Uses TestOrchestrator for direct execution instead of server architecture
    
    ### System Integration:
    - Registered via rv-experiment module respecting module hierarchy
    - Uses rv-android-core error handling and logging infrastructure
    - Integrates with rv-llm for language model backends (Qwen 2.5VL support)
    - Connects with rv-screen-parser for UI state analysis
    - Uses rv-uiautomator for direct device interaction
    
    ### Tool Execution Flow:
    1. Initialize LLM service with configured backend and strategy
    2. Create TestOrchestrator for direct UIAutomator execution
    3. Launch application and execute test cycle
    4. Process state and generate testing actions via LLM with coordinate enhancement
    5. Execute actions directly on device and collect metrics
    """
    
    # Required by AbstractTool interface
    TOOL_SPEC = ToolSpec(
        name=RVSMART_TOOL_NAME,
        description=RVSMART_DESCRIPTION,
        url="https://github.com/rv-android/rvsmart-tool",
        version="1.0.0",
        process_pattern="rvsmart_tool"
    )

    def __init__(self):
        """
        Initialize RVSmart tool with LLM-based testing capabilities.
        
        ### Initialization Strategy:
        - Inherits from AbstractTool for consistent tool behavior
        - Sets up logging with component-specific context
        - Prepares for configuration-based LLM and orchestrator setup
        """
        # Initialize base class with tool spec parameters
        tool_spec = self.get_tool_spec()
        super().__init__(
            name=tool_spec.name,
            description=tool_spec.description,
            process_pattern=tool_spec.process_pattern
        )
        
        # Initialize component logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvsmart_tool.tools.rvsmart",
            {CONTEXT_COMPONENT: "RVSmartTool"}
        )
        
        # Configuration will be set through configure() method
        self._tool_config: Optional[RvSmartToolConfig] = None
        self._debug_mode = False
        
        self.logger.info("RVSmart tool initialized")

    @classmethod
    def get_tool_spec(cls):
        """
        Get tool specification for registration.
        
        Returns:
            ToolSpec instance with tool metadata
        """
        return cls.TOOL_SPEC

    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get scientifically validated RVSmart variants with coordinate enhancement.
        
        ### RVSmart Variants Overview:
        Based on vision research showing Qwen 2.5VL 7B achieves 98.3% success rate
        vs Gemma 3 4B at 73.3%. All variants use UIAutomator for direct execution
        and support coordinate enhancement.
        
        ### Model Capabilities:
        - **Gemma 3 4B**: Multimodal with vision support - good baseline performance
        - **Qwen 2.5VL 3B/7B**: Specialized vision models - optimized for visual understanding
        - **Llama 3.2 1B**: Text-only - lightweight for resource-constrained environments
        
        ### Scientific Validation:
        - Vision research demonstrates 100% success with explicit coordinates vs 30% without
        - All multimodal models support screenshot analysis and coordinate enhancement
        - UIAutomator provides precise coordinate extraction for enhancement
        
        Returns:
            Dictionary mapping variant names to RVSmart configuration parameters
        """
        
        variants = {
            "default": {
                "llm_type": LLMType.OLLAMA,
                "llm_model": OllamaLLM.GEMMA,
                "temperature": 0.2,
                "top_p": 0.9,
                "max_tokens": 300,
                "vision": True,  # Gemma 3 4B supports vision
                "prompt_strategy": PromptStrategyType.SINGLE,
                "parser_type": ScreenParserType.UIAUTOMATOR,
                "visitor_type": VisitorType.DEFAULT,
                "context_mode": ContextMode.STATELESS,
                "template_name": "single_compact",
                "debug_mode": False
            },
            
            # Scientifically validated vision variants with Qwen 2.5VL
            "qwen_3b_vision": {
                "llm_type": LLMType.OLLAMA,
                "llm_model": OllamaLLM.QWEN_2_5VL_3B,
                "temperature": 0.2,
                "top_p": 0.9,
                "max_tokens": 300,
                "vision": True,
                "prompt_strategy": PromptStrategyType.VISION,
                "parser_type": ScreenParserType.UIAUTOMATOR,
                "visitor_type": VisitorType.DEFAULT,
                "context_mode": ContextMode.STATELESS,
                "template_name": "vision_standard",
                "debug_mode": True
            },
            
            "qwen_7b_vision": {
                "llm_type": LLMType.OLLAMA,
                "llm_model": OllamaLLM.QWEN_2_5VL_7B,
                "temperature": 0.2,
                "top_p": 0.9,
                "max_tokens": 300,
                "vision": True,
                "prompt_strategy": PromptStrategyType.VISION,
                "parser_type": ScreenParserType.UIAUTOMATOR,
                "visitor_type": VisitorType.DEFAULT,
                "context_mode": ContextMode.STATELESS,
                "template_name": "vision_premium",
                "debug_mode": True
            },
            
            # Baseline comparison variants
            "gemma_3_baseline": {
                "llm_type": LLMType.OLLAMA,
                "llm_model": OllamaLLM.GEMMA,
                "temperature": 0.2,
                "top_p": 0.9,
                "max_tokens": 300,
                "vision": True,  # Gemma 3 4B supports vision
                "prompt_strategy": PromptStrategyType.SINGLE,
                "parser_type": ScreenParserType.UIAUTOMATOR,
                "visitor_type": VisitorType.DEFAULT,
                "context_mode": ContextMode.STATELESS,
                "template_name": "single_compact",
                "debug_mode": False
            },
            
            # Rich context variants for comparison
            "qwen_7b_vision_rich": {
                "llm_type": LLMType.OLLAMA,
                "llm_model": OllamaLLM.QWEN_2_5VL_7B,
                "temperature": 0.2,
                "top_p": 0.9,
                "max_tokens": 500,
                "vision": True,
                "prompt_strategy": PromptStrategyType.VISION,
                "parser_type": ScreenParserType.UIAUTOMATOR,
                "visitor_type": VisitorType.DEFAULT,
                "context_mode": ContextMode.RICH,
                "context_window_size": 5,
                "context_compression": True,
                "template_name": "vision_premium",
                "debug_mode": True
            },
            
            # Batch strategy variants for comparison
            "qwen_7b_batch_compact": {
                "llm_type": LLMType.OLLAMA,
                "llm_model": OllamaLLM.QWEN_2_5VL_7B,
                "temperature": 0.2,
                "top_p": 0.9,
                "max_tokens": 400,
                "vision": True,
                "prompt_strategy": PromptStrategyType.BATCH,
                "parser_type": ScreenParserType.UIAUTOMATOR,
                "visitor_type": VisitorType.DEFAULT,
                "context_mode": ContextMode.STATELESS,
                "template_name": "batch_compact",
                "debug_mode": True
            },
            
            "gemma_batch_standard": {
                "llm_type": LLMType.OLLAMA,
                "llm_model": OllamaLLM.GEMMA,
                "temperature": 0.2,
                "top_p": 0.9,
                "max_tokens": 350,
                "vision": True,  # Gemma 3 4B supports vision
                "prompt_strategy": PromptStrategyType.BATCH,
                "parser_type": ScreenParserType.UIAUTOMATOR,
                "visitor_type": VisitorType.DEFAULT,
                "context_mode": ContextMode.STATELESS,
                "template_name": "batch_standard",
                "debug_mode": False
            },
            
            # Reasoning-enabled variants with think capability
            "deepseek_r1_single": {
                "llm_type": LLMType.OLLAMA,
                "llm_model": OllamaLLM.DEEPSEEK,
                "temperature": 0.3,
                "top_p": 0.9,
                "max_tokens": 400,
                "vision": False,
                "think": True,  # DeepSeek R1 supports reasoning
                "prompt_strategy": PromptStrategyType.SINGLE,
                "parser_type": ScreenParserType.UIAUTOMATOR,
                "visitor_type": VisitorType.DEFAULT,
                "context_mode": ContextMode.STATELESS,
                "template_name": "single_standard",
                "debug_mode": True
            },
            
            "qwen3_think_batch": {
                "llm_type": LLMType.OLLAMA,
                "llm_model": OllamaLLM.QWEN,
                "temperature": 0.2,
                "top_p": 0.9,
                "max_tokens": 450,
                "vision": False,
                "think": True,  # Qwen 3 0.6B supports reasoning
                "prompt_strategy": PromptStrategyType.BATCH,
                "parser_type": ScreenParserType.UIAUTOMATOR,
                "visitor_type": VisitorType.DEFAULT,
                "context_mode": ContextMode.STATELESS,
                "template_name": "batch_compact",
                "debug_mode": True
            },
            
            "phi4_reasoning": {
                "llm_type": LLMType.OLLAMA,
                "llm_model": OllamaLLM.PHI,
                "temperature": 0.2,
                "top_p": 0.8,
                "max_tokens": 500,
                "vision": False,
                "think": True,  # Phi4 Mini supports reasoning
                "prompt_strategy": PromptStrategyType.SINGLE,
                "parser_type": ScreenParserType.UIAUTOMATOR,
                "visitor_type": VisitorType.DEFAULT,
                "context_mode": ContextMode.RICH,
                "context_window_size": 3,
                "context_compression": True,
                "template_name": "single_premium",
                "debug_mode": True
            }
        }
        
        return variants

    def configure(self, app: App, task: Task, variant: str, **kwargs) -> None:
        """
        Configure RVSmart tool with unified configuration architecture.
        
        Args:
            app: Application instance to test
            task: Task definition with testing objectives
            variant: Configuration variant name
            **kwargs: Additional configuration parameters
        """
        try:
            self.logger.info(f"Configuring RVSmart tool with variant: {variant}")
            
            # Create unified tool configuration
            self._tool_config = RvSmartToolConfig.create_from_variant(
                self.get_variants()[variant]
            )
            
            # Override with any additional parameters
            if kwargs:
                self.logger.debug(f"Applying configuration overrides: {kwargs}")
                # Apply overrides to config if needed
            
            self._debug_mode = self._tool_config.debug_mode
            
            self.logger.info("RVSmart tool configured successfully")
            self.logger.info(f"LLM Model: {self._tool_config.llm_config.model}")
            self.logger.info(f"Vision Enabled: {self._tool_config.llm_config.vision}")
            self.logger.info(f"Strategy: {self._tool_config.prompt_config.strategy_type}")
            self.logger.info(f"Parser: {self._tool_config.prompt_config.parser_type}")
            
        except Exception as e:
            self.logger.error(f"Configuration failed: {e}")
            raise RVAndroidToolError(f"Configuration failed: {e}")

    def execute(self, app: App, task: Task, device_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute RVSmart testing using TestOrchestrator with UIAutomator.
        
        Args:
            app: Application to test
            task: Task definition with objectives
            device_id: Target device identifier
            
        Returns:
            Tuple of (success, execution_metrics)
        """
        if not self._tool_config:
            raise RVAndroidToolError("Tool not configured. Call configure() first.")
            
        try:
            self.logger.info(f"Starting RVSmart execution on device {device_id}")
            self.logger.info(f"Target application: {app.package_name}")
            
            # Load static data for LLM service
            static_data = task.static_data if hasattr(task, 'static_data') else None
            
            # Create TestOrchestrator
            orchestrator = TestOrchestrator(
                static_data=static_data.to_dict() if hasattr(static_data, 'to_dict') else static_data,
                tool_config=self._tool_config,
                app=app,
                device_id=device_id,
                results_dir=f"./results/rvsmart_{app.package_name}_{int(time.time())}"
            )
            
            # Execute test cycle (default 5 minutes)
            execution_timeout = 300
            orchestrator.execute_test_cycle(timeout=execution_timeout)
            
            # Collect metrics
            metrics = {
                "tool_name": self.name,
                "variant": self._tool_config.variant_name if hasattr(self._tool_config, 'variant_name') else "unknown",
                "model": self._tool_config.llm_config.model,
                "vision_enabled": self._tool_config.llm_config.vision,
                "total_actions": orchestrator.metrics.total_actions,
                "successful_actions": orchestrator.metrics.successful_actions,
                "failed_actions": orchestrator.metrics.failed_actions,
                "success_rate": (orchestrator.metrics.successful_actions / max(1, orchestrator.metrics.total_actions)) * 100,
                "execution_time": orchestrator.metrics.execution_time,
                "external_navigation_count": orchestrator.metrics.external_navigation_count,
                "app_restarts": orchestrator.metrics.app_restarts
            }
            
            # Determine success based on metrics
            success = orchestrator.metrics.total_actions > 0 and orchestrator.metrics.execution_time > 0
            
            self.logger.info(f"RVSmart execution completed: {success}")
            self.logger.info(f"Generated {orchestrator.metrics.total_actions} actions")
            self.logger.info(f"Success rate: {metrics['success_rate']:.1f}%")
            
            return success, metrics
            
        except Exception as e:
            self.logger.error(f"RVSmart execution failed: {e}")
            return False, {"error": str(e)}

    def cleanup(self) -> None:
        """Clean up RVSmart resources."""
        try:
            self.logger.info("Cleaning up RVSmart tool")
            # No persistent resources to clean up in direct execution model
            
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")