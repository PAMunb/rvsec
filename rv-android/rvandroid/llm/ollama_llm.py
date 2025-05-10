# rvandroid/llm/ollama_llm.py
"""Ollama language model implementation."""
import logging
import time
from typing import List, Optional, ClassVar, Dict, Any

# Use official ollama library
from ollama import ChatResponse, Client

from rvandroid.llm.data_structures import LLMMessage, LLMResponse
from rvandroid.llm.language_model import LanguageModel
from rvandroid.llm.llm_config import LLMConfiguration
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.logging.constants import CONTEXT_COMPONENT


class OllamaLLM(LanguageModel):
    """
    A specialized language model integration for local AI inference using the Ollama platform.

    ### Architectural Decisions:
    - Implements a flexible, locally-hosted language model interface
    - Supports direct integration with Ollama's model serving capabilities
    - Provides configurable model selection and execution strategies
    - Enables efficient, privacy-preserving local AI inference
    - Uses native Ollama chat formatting for optimal compatibility

    ### Role in the System:
    - Acts as a concrete implementation of the LanguageModel abstract base class
    - Facilitates local AI-driven testing and analysis workflows
    - Supports multiple open-source language models without external API dependencies
    - Provides a standardized interface for text generation using local models
    - Enables flexible AI model configuration for experimental testing

    ### Key Considerations:
    - Manages model initialization and resource allocation
    - Handles various Ollama-hosted model backends
    - Supports configurable base URL and model selection
    - Implements robust error handling for model interactions
    - Provides direct message formatting for optimal performance

    ### Performance and Scalability:
    - Designed for efficient local AI inference
    - Minimizes network and computational overhead
    - Supports various model sizes and complexities
    - Adaptable to different computational resources
    - Enables offline and privacy-preserving AI-driven testing
    """
    NAME = "ollama"

    # Available model definitions
    LLAMA: ClassVar[str] = "llama3.2:3b"
    DEEPSEEK: ClassVar[str] = "deepseek-r1:1.5B"
    GEMMA: ClassVar[str] = "gemma3:4b"
    QWEN: ClassVar[str] = "qwen3:8b"
    PHI: ClassVar[str] = "phi4-mini-reasoning:3.8b"
    GRANITE: ClassVar[str] = "granite3.3:2b"
    MISTRAL: ClassVar[str] = "mistral:7b"
    FALCON: ClassVar[str] = "falcon3:3b"

    # Define available models
    MODELS: ClassVar[List[str]] = [LLAMA, DEEPSEEK, GEMMA, QWEN, PHI, GRANITE, MISTRAL, FALCON]

    def __init__(self, model_name: str = LLAMA, **kwargs):
        """
        Initialize Ollama language model.
        
        Args:
            model_name: Name of the Ollama model to use
            **kwargs: Additional arguments including:
                base_url: Base URL for Ollama API (default: http://localhost:11434)
                temperature: Sampling temperature (default: 0.2)
                max_tokens: Maximum tokens to generate (default: None)
        """
        # Extract base_url before passing kwargs to parent constructor
        self.api_base = kwargs.pop("base_url", "http://localhost:11434")
        
        # Initialize base class
        super().__init__(model_name, **kwargs)
        
        # Initialize client lazily
        self._client = None
        
        # Setup logging and error handling
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "llm.ollama", 
            {CONTEXT_COMPONENT: self.__class__.__name__}
        )
        self.error_handler = ErrorHandler.get_instance()
        
        self.logger.info(f"Initialized Ollama with model {model_name} at {self.api_base}")

    @property
    def client(self):
        """
        Get or create the Ollama client.
        
        Returns:
            Ollama Client instance
        """
        if self._client is None:
            self._client = Client(host=self.api_base)
        return self._client

    def generate(self,
                 messages: List[LLMMessage],
                 config: Optional[LLMConfiguration] = None) -> LLMResponse:
        """
        Generate text based on the input messages.
        
        Args:
            messages: List of LLMMessage objects
            config: Optional LLMConfiguration for generation parameters
            
        Returns:
            LLMResponse with generated text and performance metrics
        """
        # Use provided config or default
        _config = config or self.default_config
        
        try:
            # Start timing the operation
            start_time = time.time()
            
            # Format messages for Ollama
            formatted_msgs = []
            for message in messages:
                content = message.get_text_content()
                formatted_msgs.append({
                    "role": message.role.value,
                    "content": content
                })
            
            # Extract generation parameters
            options = {}
            if _config and _config.temperature is not None:
                options["temperature"] = _config.temperature
            else:
                options["temperature"] = 0.2
                
            if _config and _config.max_tokens is not None:
                options["num_predict"] = _config.max_tokens
                
            # Add top_p if specified and less than 1.0
            if _config and hasattr(_config, 'top_p') and _config.top_p < 1.0:
                options["top_p"] = _config.top_p
                
            self.logger.debug(f"Calling Ollama with model: {self.model_name}, options: {options}")

            # Call Ollama chat API synchronously
            response: ChatResponse = self.client.chat(
                model=self.model_name,
                messages=formatted_msgs,
                options=options
            )
            
            # Create an LLM response from the Ollama response
            llm_response = LLMResponse(response.message.content)
            
            # Add performance metrics from Ollama
            llm_response.done_reason = response.done_reason
            llm_response.total_duration = response.total_duration
            llm_response.load_duration = response.load_duration
            llm_response.input_tokens = response.prompt_eval_count
            llm_response.input_tokens_duration = response.prompt_eval_duration
            llm_response.output_tokens = response.eval_count
            llm_response.output_tokens_duration = response.eval_duration
            
            return llm_response
            
        except Exception as e:
            error_msg = f"Error generating text from Ollama: {str(e)}"
            self.logger.error(error_msg)
            from rvandroid.util.exceptions import RVAndroidError
            error = RVAndroidError(error_msg)
            self.error_handler.handle_error(error)
            raise

    @classmethod
    def models(cls) -> List[str]:
        """
        Get a list of available models for this type.
        
        Returns:
            List of available model names
        """
        return cls.MODELS

    def cleanup(self):
        """
        Clean up any resources. Called when the service is shutting down.
        """
        # Nothing specific to clean up in this implementation
        if self._client:
            # Release reference to client
            self._client = None
            
        self.logger.info("Cleaned up Ollama LLM resources")


# Register the model
def register():
    """Register Ollama model with the configurator."""
    from rvandroid.config.component_configurator import ComponentConfigurator
    
    # Check if this LLM is already registered
    if OllamaLLM.NAME in ComponentConfigurator._registries.get('llm', {}).get_names():
        # Already registered, skip registration
        return

    # Register the LLM
    ComponentConfigurator.register_llm(OllamaLLM.NAME, OllamaLLM)