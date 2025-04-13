# rvandroid/llm/dspy_llm.py
"""DSPy language model implementation using the Model Context Protocol (MCP)."""

import asyncio
import logging
from typing import List, Optional, ClassVar

import dspy

from rvandroid.llm.data_structures import MCPMessage, MCPConfiguration
from rvandroid.llm.language_model import LanguageModel
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.adapter import AdapterRegistry
from rvandroid.llm.adapters.dspy_adapter import DSPyAdapter

logger = logging.getLogger(__name__)


class DSPyLLM(LanguageModel):
    """
    Language model implementation using DSPy for generating text.
    
    ### Architectural Decisions:
    - Integrates DSPy's programming framework with the MCP system
    - Uses Ollama as the backend provider for local model execution
    - Implements the standard LanguageModel interface with DSPy specifics
    - Provides a bridge between structured programming and MCP
    
    ### Role in the System:
    - Enables programmatic interactions with language models
    - Supports more structured prompt approaches through DSPy
    - Maintains compatibility with the MCP system for standardized communication
    - Provides an alternative approach for complex reasoning tasks
    
    ### Integration Strategy:
    - DSPy's programming model is wrapped in the MCP interface
    - Provides the full power of DSPy while maintaining MCP compatibility
    - Enables seamless switching between different model implementations
    """

    NAME = "dspy"
    
    # Models available for DSPy (using Ollama as provider)
    LLAMA: ClassVar[str] = "llama3.2:3b"
    PHI: ClassVar[str] = "phi3.5:3.8b"
    QWEN: ClassVar[str] = "qwen2.5:3b"
    MISTRAL: ClassVar[str] = "mistral:7b"

    # Define available models (subset for better performance)
    MODELS: ClassVar[List[str]] = [LLAMA, QWEN]

    def __init__(self, model_name: str = LLAMA, **kwargs):
        """
        Initialize DSPy language model with Ollama as the backend.
        
        Args:
            model_name: Name of the model to use
            **kwargs: Additional arguments including:
                api_base: Base URL for Ollama API (default: http://localhost:11434)
                temperature: Sampling temperature (default: 0.7)
                max_tokens: Maximum tokens to generate (default: None)
        """
        self.api_base = kwargs.pop("api_base", "http://localhost:11434")  # Ollama default URL
        super().__init__(model_name, **kwargs)

        # Set up DSPy model with Ollama
        config = {}
        if self.api_base:
            config["api_base"] = self.api_base

        # Initialize the model with Ollama as provider
        try:
            self.model = dspy.OllamaLocal(
                model=model_name,
                api_base=self.api_base
            )
            self.logger.info(f"Initialized DSPy with Ollama model {model_name} at {self.api_base}")
        except Exception as e:
            self.logger.error(f"Failed to initialize DSPy model: {e}")
            # Create a placeholder that will raise an error when used
            self.model = None

    def _get_model_type(self) -> str:
        """Get model type string."""
        return self.NAME

    def _get_adapter(self) -> DSPyAdapter:
        """Get the appropriate MCP adapter for this model."""
        return DSPyAdapter()

    async def generate(self,
                       messages: List[MCPMessage],
                       config: Optional[MCPConfiguration] = None) -> MCPMessage:
        """
        Generate a response using DSPy with Ollama.
        
        Args:
            messages: List of MCP messages representing the conversation
            config: Optional configuration parameters that override instance config
            
        Returns:
            MCPMessage containing the generated response
            
        Raises:
            ValueError: If the request is invalid or the model is not initialized
            Exception: If an error occurs during generation
        """
        # Check if model was properly initialized
        if self.model is None:
            raise ValueError("DSPy model is not initialized properly")
            
        # Use provided config or instance config
        use_config = config or self.config

        # Validate request using adapter
        if not self.adapter.validate_request(messages, use_config):
            raise ValueError("Invalid request for DSPy")

        # Prepare messages using adapter
        prepared_messages = self.adapter.prepare_messages(messages)

        # Prepare configuration using adapter
        prepared_config = self.adapter.prepare_config(use_config)

        try:
            # Generate response using DSPy with Ollama
            prompt = self._prepare_prompt(prepared_messages["messages"])

            # Run in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.complete(
                    prompt=prompt,
                    temperature=prepared_config.get("temperature", 0.7),
                    max_tokens=prepared_config.get("max_tokens", None)
                )
            )

            # Parse response using adapter
            return self.adapter.parse_response({"content": response})

        except Exception as e:
            self.logger.error(f"DSPy generation error: {e}")
            raise

    def _prepare_prompt(self, messages):
        """
        Convert messages to prompt format compatible with Ollama models.
        
        Args:
            messages: List of formatted message dictionaries
            
        Returns:
            Formatted prompt string for Ollama
        """
        prompt = ""

        for message in messages:
            role = message["role"]
            content = message["content"]

            if role == "system":
                prompt += f"<|system|>\n{content}\n"
            elif role == "user":
                prompt += f"<|user|>\n{content}\n"
            elif role == "assistant":
                prompt += f"<|assistant|>\n{content}\n"
            elif role == "tool":
                prompt += f"<|tool|>\n{content}\n"

        prompt += "<|assistant|>\n"
        return prompt

    def generate_sync(self,
                      messages: List[MCPMessage],
                      config: Optional[MCPConfiguration] = None) -> MCPMessage:
        """
        Generate a response synchronously.
        
        Args:
            messages: List of MCP messages representing the conversation
            config: Optional configuration parameters
            
        Returns:
            MCPMessage containing the generated response
        """
        # For DSPy, we'll use a simpler approach since its core client isn't using async
        # but we'll still use ThreadPoolExecutor to isolate the execution
        
        from concurrent.futures import ThreadPoolExecutor
        import threading
        
        # Helper function to run DSPy in a separate thread
        def run_dspy_in_thread():
            # Convert messages to a format DSPy can use
            prompt = self._prepare_prompt([{
                "role": msg.role.value,
                "content": msg.get_text_content()
            } for msg in messages])
            
            # Use config if provided, otherwise use defaults
            use_config = config or self.config
            temperature = getattr(use_config, "temperature", 0.7)
            max_tokens = getattr(use_config, "max_tokens", 800)
            
            # Execute DSPy directly (it doesn't use asyncio internally)
            if not self.model:
                raise ValueError("DSPy model not initialized")
            
            # Call the model
            response = self.model.complete(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Create and return MCP response
            return MCPMessage(
                role=MCPRole.ASSISTANT,
                content=[MCPTextContent(text=response)]
            )
        
        # Execute in a thread pool to isolate from any potential issues in the server
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_dspy_in_thread)
            return future.result(timeout=60)  # 60 second timeout
        
    @classmethod
    def models(cls) -> List[str]:
        """
        Get a list of available models for this type.
        
        Returns:
            List of available model names
        """
        return cls.MODELS


# Register the model - will be called after the adapter class is defined
def register():
    """Register DSPy model with the configurator and registry."""
    # Check if this LLM is already registered
    if DSPyLLM.NAME in ComponentConfigurator._registries.get('llm', {}).get_names():
        # Already registered, skip registration
        return
        
    # Register the LLM and adapter
    ComponentConfigurator.register_llm(DSPyLLM.NAME, DSPyLLM)
    AdapterRegistry.get_instance().register_adapter(DSPyLLM.NAME, DSPyAdapter)
