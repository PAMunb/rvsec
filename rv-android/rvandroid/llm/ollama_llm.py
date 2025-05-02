# rvandroid/llm/ollama_llm.py
"""Ollama language model implementation using the Model Context Protocol (MCP)."""
import logging
from typing import List, Optional, ClassVar

# Use official ollama library
from ollama import AsyncClient, ChatResponse

from rvandroid.llm.adapter import AdapterRegistry
from rvandroid.llm.adapters.ollama_adapter import OllamaAdapter
from rvandroid.llm.data_structures import LLMMessage, LLMTextContent, LLMRole, LLMResponse
from rvandroid.llm.language_model import LanguageModel
from rvandroid.llm.llm_config import LLMConfiguration
from ollama import Client

logger = logging.getLogger(__name__)


class OllamaLLM(LanguageModel):
    """
    A specialized language model integration for local AI inference using the Ollama platform.

    ### Architectural Decisions:
    - Implements a flexible, locally-hosted language model interface
    - Supports direct integration with Ollama's model serving capabilities
    - Provides configurable model selection and execution strategies
    - Enables efficient, privacy-preserving local AI inference

    ### Role in the System:
    - Acts as a concrete implementation of the LanguageModel abstract base class
    - Facilitates local AI-driven testing and analysis workflows
    - Supports multiple open-source language models without external API dependencies
    - Provides a standardized interface for text generation using local models
    - Enables flexible AI model configuration for experimental testing

    ### Key Considerations:
    - Manages complex model initialization and resource allocation
    - Handles various Ollama-hosted model backends
    - Supports configurable base URL and model selection
    - Implements robust error handling for model interactions
    - Provides efficient model pulling and initialization mechanisms

    ### Integration Strategy:
    - Implements the Model Context Protocol for standardized communication
    - Compatible with multiple local AI model providers
    - Supports dynamic model selection and configuration
    - Enables seamless swapping of AI backends
    - Provides a consistent interface for text generation

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
    DEEPSEEK: ClassVar[str] = "deepseek-r1:7b"
    GEMMA: ClassVar[str] = "gemma3:4b"
    QWEN: ClassVar[str] = "qwen3:8b"
    PHI: ClassVar[str] = "phi4-mini-reasoning:3.8b"
    GRANITE: ClassVar[str] = "granite3.3:2b"
    MISTRAL: ClassVar[str] = "mistral:7b"
    FALCON: ClassVar[str] = "falcon3:3b"

    # Define available models (subset for better performance)
    # MODELS: ClassVar[List[str]] = [LLAMA, GEMMA, QWEN]
    MODELS: ClassVar[List[str]] = [LLAMA, DEEPSEEK, GEMMA, QWEN, PHI, GRANITE, MISTRAL, FALCON]

    def __init__(self, model_name: str = LLAMA, **kwargs):
        """
        Initialize Ollama language model.
        
        Args:
            model_name: Name of the Ollama model to use
            **kwargs: Additional arguments including:
                api_base: Base URL for Ollama API (default: http://localhost:11434)
                temperature: Sampling temperature (default: 0.2)
                max_tokens: Maximum tokens to generate (default: None)
        """
        print(f"OllamaLLM ::: {kwargs}")
        self.api_base = kwargs.pop("base_url", "http://localhost:11434")
        print(f"OllamaLLM ::: base_url={self.api_base}")
        super().__init__(model_name, **kwargs)
        # We don't create the client here, instead create it on demand in generate
        self._client = None
        self.logger.info(f"Initialized Ollama with model {model_name} at {self.api_base}")

    @property
    def client(self):
        if self._client is None:
            self._client = Client(host=self.api_base)
        return self._client

    def _get_model_type(self) -> str:
        """Get model type string."""
        return self.NAME

    def _get_adapter(self) -> OllamaAdapter:
        """Get the appropriate MCP adapter for this model."""
        return OllamaAdapter()

    # async def generate(self,
    #                    messages: List[LLMMessage],
    #                    config: Optional[MCPConfiguration] = None) -> LLMMessage:
    #     """
    #     Generate a response using Ollama's chat API.
    #
    #     Updated implementation uses Ollama's chat API which provides better
    #     handling of conversation contexts and message formatting.
    #
    #     Args:
    #         messages: List of MCP messages representing the conversation
    #         config: Optional configuration parameters that override instance config
    #
    #     Returns:
    #         LLMMessage containing the generated response
    #
    #     Raises:
    #         ValueError: If the request is invalid for Ollama
    #         Exception: If an error occurs during generation
    #     """
    #     # Use provided config or instance config
    #     use_config = config or self.config
    #
    #     # Validate request using adapter
    #     if not self.adapter.validate_request(messages, use_config):
    #         raise ValueError("Invalid request for Ollama")
    #
    #     # Prepare messages using adapter
    #     prepared_data = self.adapter.prepare_messages(messages)
    #
    #     # Prepare configuration using adapter
    #     prepared_config = self.adapter.prepare_config(use_config)
    #
    #     try:
    #         # Use chat API instead of generate API
    #         response = await self.client.chat(
    #             model=prepared_config.pop("model"),
    #             messages=prepared_data["messages"],
    #             options=prepared_config
    #         )
    #
    #         # Parse response using adapter
    #         return self.adapter.parse_response(response)
    #
    #     except Exception as e:
    #         self.logger.error(f"Ollama request error: {e}")
    #         raise

    def generate(self,
                 messages: List[LLMMessage],
                 config: Optional[LLMConfiguration] = None) -> LLMResponse:
        print(f" ***** generate: messages: {type(messages)} ::: {messages}")
        print(f" ***** generate: config: {type(config)} ::: {config}")
        # Prepare messages in a simple format
        formatted_msgs = self.adapter.prepare_messages(messages)["messages"]
        print(f"formatted_msgs={formatted_msgs}")
        for xxx in formatted_msgs:
            print(f"role={xxx['role']}, content=\n{xxx['content']}")

        options = {}
        if config.temperature is not None:
            options["temperature"] = config.temperature
        else:
            options["temperature"] = 0.2
        if config.max_tokens is not None:
            options["num_predict"] = config.max_tokens

        print(f"Calling Ollama with model: {self.model_name}, options: {options}")
        for msg in messages:
            print(f"Message: {msg}")

        # Call Ollama chat API synchronously
        response: ChatResponse = self.client.chat(
            model=self.model_name,
            messages=formatted_msgs,
            options=options
        )
        print(f"\n*** Response: {response["message"]["content"]} :::: {response}")

        # Create an LLM message from the response
        llm_response = LLMResponse(response.message.content)
        llm_response.done_reason = response.done_reason
        llm_response.total_duration = response.total_duration
        llm_response.load_duration = response.load_duration
        llm_response.input_tokens = response.prompt_eval_count
        llm_response.input_tokens_duration = response.prompt_eval_duration
        llm_response.output_tokens = response.eval_count
        llm_response.output_tokens_duration = response.eval_duration
        print(f"llm_response={llm_response}")
        return llm_response

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
        # Nothing to clean up in this implementation since we use a subprocess approach
        # that isolates each request in its own process
        self.logger.info("Cleaning up Ollama LLM resources")


# Register the model and adapter - will be called after the adapter class is defined
def register():
    """Register Ollama model with the configurator and registry."""
    from rvandroid.config.component_configurator import ComponentConfigurator
    # Check if this LLM is already registered
    if OllamaLLM.NAME in ComponentConfigurator._registries.get('llm', {}).get_names():
        # Already registered, skip registration
        return

    # Register the LLM and adapter
    ComponentConfigurator.register_llm(OllamaLLM.NAME, OllamaLLM)
    AdapterRegistry.get_instance().register_adapter(OllamaLLM.NAME, OllamaAdapter)
