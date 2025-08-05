"""
Ollama language model implementation for local AI inference.

This module provides Ollama integration for local language model operations
in Android testing experiments and AI-driven analysis workflows.
"""
from typing import List, Optional, ClassVar

from ollama import ChatResponse, Client

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.config.llm_config import LLMConfig
from rv_llm.llm.data_structures import LLMMessage, LLMResponse, LLMRole
from rv_llm.llm.language_model import LanguageModel


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
    LLAMA: ClassVar[str] = "llama3.2:1b"
    DEEPSEEK: ClassVar[str] = "deepseek-r1:1.5B"
    GEMMA: ClassVar[str] = "gemma3:4b"
    QWEN: ClassVar[str] = "qwen3:1.7b"
    PHI: ClassVar[str] = "phi4-mini-reasoning:3.8b"
    GRANITE: ClassVar[str] = "granite3.3:2b"
    # MISTRAL: ClassVar[str] = "mistral:7b"
    FALCON: ClassVar[str] = "falcon3:3b"

    # Define available models
    MODELS: ClassVar[List[str]] = [LLAMA, DEEPSEEK, GEMMA, QWEN, PHI, GRANITE, FALCON]

    def __init__(self, config: LLMConfig):
        """
        Initialize Ollama language model.
        
        Args:
            config: LLMConfig object containing model-specific parameters
        """
        # Initialize base class
        super().__init__(config)

        # Initialize client lazily
        self._client: Optional[Client] = None

        # Setup logging and error handling
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "rv_llm.llm.ollama",
            {CONTEXT_COMPONENT: self.__class__.__name__}
        )
        self.error_handler = ErrorHandler.get_instance()

        self.logger.info(f"Initialized Ollama with model {self.config.model} at {self.config.base_url}")

    @property
    def client(self):
        """
        Get or create the Ollama client.
        
        Returns:
            Ollama Client instance
        """
        if self._client is None:
            self._client = Client(host=self.config.base_url)
        return self._client

    def generate(self, messages: List[LLMMessage], config: Optional[LLMConfig] = None) -> LLMResponse:
        """
        Generate text based on the input messages.
        
        Args:
            messages: List of LLMMessage objects
            
        Returns:
            LLMResponse with generated text and performance metrics
        """

        try:
            # Format messages for Ollama
            formatted_msgs = []
            for message in messages:
                formatted_msg = self.format_message(message)
                print(f">>> formatted_msg=\n{formatted_msg} ...")
                formatted_msgs.append(formatted_msg)

            # Update config
            self.update_config(config)

            # Extract generation parameters
            options = self.create_options()

            self.logger.info(f"Calling Ollama with model: {self.config.model}, options: {options}")
            # TODO voltar debug self.logger.debug(f"Calling Ollama with model: {self.model_name}, options: {options}")

            print(f">>> messages=\n{formatted_msgs}")
            print(f">>> options=\n{options}")

            # Call Ollama chat API synchronously
            response: ChatResponse = self.client.chat(
                model=self.config.model,
                messages=formatted_msgs,
                options=options,
                stream=False,
                think=self.config.think,
                keep_alive="60s"
            )

            print(f"<<< response=\n{response}")
            print(f"response.total_duration={response.total_duration}")

            # Create and return a LLM response from the Ollama response
            return self.create_response(response)

        except Exception as e:
            error_msg = f"Error generating text from Ollama: {str(e)}"
            self.logger.error(error_msg)
            from rv_android_core.util.error.exceptions import RVAndroidError
            error = RVAndroidError(error_msg)
            self.error_handler.handle_error(error)
            raise

    def update_config(self, config):
        if config is not None:
            if config.temperature:
                self.config.temperature = config.temperature
            if config.max_tokens:
                self.config.max_tokens = config.max_tokens
            if config.top_p:
                self.config.top_p = config.top_p
            if config.top_k:
                self.config.top_k = config.top_k
            if config.think:
                self.config.think = config.think
            if config.vision:
                self.config.vision = config.vision

    def create_response(self, response: ChatResponse):
        llm_response = LLMResponse(content=response.message.content)
        # Add performance metrics from Ollama
        llm_response.done_reason = response.done_reason
        llm_response.total_duration = response.total_duration
        llm_response.load_duration = response.load_duration
        llm_response.input_tokens = response.prompt_eval_count
        llm_response.input_tokens_duration = response.prompt_eval_duration
        llm_response.output_tokens = response.eval_count
        llm_response.output_tokens_duration = response.eval_duration
        return llm_response

    def create_options(self):
        options = {
            "temperature": self.config.temperature,
            "num_predict": self.config.max_tokens,
            "top_p": self.config.top_p,
            "top_k": self.config.top_k
        }
        return options

    def format_message(self, message):
        content = message.get_text_content()
        formatted_msg = {
            "role": message.role.value,
            "content": content
        }
        if LLMRole.USER == message.role and self.config.vision:
            images = message.get_image_content()
            if images and len(images) > 0:
                formatted_msg["images"] = images
        return formatted_msg

    def cleanup(self):
        """
        Clean up any resources. Called when the service is shutting down.
        """
        # Nothing specific to clean up in this implementation
        if self._client:
            # Release reference to client
            self._client = None

        self.logger.info("Cleaned up Ollama LLM resources")
