# rvandroid/llm/ollama_llm.py
"""Ollama language model implementation using the Model Context Protocol (MCP)."""
import logging
from typing import List, Optional, ClassVar

# Use official ollama library
from ollama import AsyncClient

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.adapter import AdapterRegistry
from rvandroid.llm.adapters.ollama_adapter import OllamaAdapter
from rvandroid.llm.data_structures import MCPMessage, MCPConfiguration, MCPTextContent, MCPRole
from rvandroid.llm.language_model import LanguageModel

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
    DEEPSEEK: ClassVar[str] = "deepseek-r1:1.5B"
    GEMMA: ClassVar[str] = "gemma3:4b"
    QWEN: ClassVar[str] = "qwen2.5:3b"
    PHI: ClassVar[str] = "phi3.5:3.8b"
    GRANITE: ClassVar[str] = "granite3.1-dense:8b"
    MISTRAL: ClassVar[str] = "mistral:7b"
    FALCON: ClassVar[str] = "falcon3:3b"

    # Define available models (subset for better performance)
    MODELS: ClassVar[List[str]] = [LLAMA, GEMMA, QWEN]

    def __init__(self, model_name: str = LLAMA, **kwargs):
        """
        Initialize Ollama language model.
        
        Args:
            model_name: Name of the Ollama model to use
            **kwargs: Additional arguments including:
                api_base: Base URL for Ollama API (default: http://localhost:11434)
                temperature: Sampling temperature (default: 0.7)
                max_tokens: Maximum tokens to generate (default: None)
        """
        self.api_base = kwargs.pop("api_base", "http://localhost:11434")
        super().__init__(model_name, **kwargs)
        # We don't create the client here, instead create it on demand in generate
        self._client = None
        self.logger.info(f"Initialized Ollama with model {model_name} at {self.api_base}")

    @property
    def client(self):
        """Get a fresh client for each request to avoid event loop issues."""
        # Always create a new client to avoid async loop sharing issues
        return AsyncClient(host=self.api_base)

    def _get_model_type(self) -> str:
        """Get model type string."""
        return self.NAME

    def _get_adapter(self) -> OllamaAdapter:
        """Get the appropriate MCP adapter for this model."""
        return OllamaAdapter()

    async def generate(self,
                       messages: List[MCPMessage],
                       config: Optional[MCPConfiguration] = None) -> MCPMessage:
        """
        Generate a response using Ollama.
        
        Args:
            messages: List of MCP messages representing the conversation
            config: Optional configuration parameters that override instance config
            
        Returns:
            MCPMessage containing the generated response
            
        Raises:
            ValueError: If the request is invalid for Ollama
            Exception: If an error occurs during generation
        """
        # Use provided config or instance config
        use_config = config or self.config

        # Validate request using adapter
        if not self.adapter.validate_request(messages, use_config):
            raise ValueError("Invalid request for Ollama")

        # Prepare messages using adapter
        prepared_messages = self.adapter.prepare_messages(messages)
        print(f"prepared_messages={prepared_messages}")

        # Prepare configuration using adapter
        prepared_config = self.adapter.prepare_config(use_config)

        try:
            # Generate response using Ollama
            response = await self.client.generate(
                model=prepared_config.pop("model"),
                prompt=prepared_messages["prompt"],
                options=prepared_config
            )
            print(f"\n\nresponse={response}")

            # Parse response using adapter
            return self.adapter.parse_response(response)

        except Exception as e:
            self.logger.error(f"Ollama request error: {e}")
            raise

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
        # Use a completely isolated approach that works under any circumstance
        import multiprocessing
        import json
        import tempfile
        import os

        # Helper function to format the messages into a simpler format for cross-process communication
        def _prepare_data():
            """Convert MCP data to a simple dict format for cross-process communication."""
            # Prepare messages in a simple format
            formatted_msgs = []
            for msg in messages:
                role = msg.role.value  # e.g., "system", "user"
                content = msg.get_text_content()
                formatted_msgs.append({"role": role, "content": content})

            # Prepare config
            use_config = config or self.config
            cfg_dict = {}
            if use_config:
                cfg_dict = {
                    "temperature": use_config.temperature,
                    "max_tokens": use_config.max_tokens,
                    "model_name": use_config.model_name,
                    "model_type": use_config.model_type
                }

            return {
                "messages": formatted_msgs,
                "config": cfg_dict,
                "model_name": self.model_name,
                "api_base": self.api_base
            }

        # Helper function that runs in a subprocess and calls Ollama directly
        def _run_ollama_call(data_dict, result_file):
            """Execute the Ollama call in a separate process."""
            try:
                import sys
                import os
                from ollama import Client

                # Extract the data needed for the call
                model_name = data_dict["model_name"]
                api_base = data_dict["api_base"]
                messages = data_dict["messages"]
                cfg = data_dict["config"]

                # Create a synchronous client
                client = Client(host=api_base)

                # Format prompt for the Ollama model
                prompt = ""
                for msg in messages:
                    if msg["role"] == "system":
                        prompt += f"<|system|>\n{msg['content']}\n"
                    elif msg["role"] == "user":
                        prompt += f"<|user|>\n{msg['content']}\n"
                    elif msg["role"] == "assistant":
                        prompt += f"<|assistant|>\n{msg['content']}\n"
                prompt += "<|assistant|>\n"
                print(f"\nprompt={prompt}")

                # Prepare options from config
                options = {}
                if "temperature" in cfg and cfg["temperature"] is not None:
                    options["temperature"] = cfg["temperature"]
                if "max_tokens" in cfg and cfg["max_tokens"] is not None:
                    options["num_predict"] = cfg["max_tokens"]

                # Call Ollama synchronously
                response = client.generate(
                    model=model_name,
                    prompt=prompt,
                    options=options
                )
                print(f"\n\nresponse={response}")

                # Write the result to the file
                result = {"success": True, "content": response["response"]}
                with open(result_file, 'w') as f:
                    json.dump(result, f)

            except Exception as e:
                # If an error occurs, write it to the result file
                err_result = {"success": False, "error": str(e)}
                with open(result_file, 'w') as f:
                    json.dump(err_result, f)

        # Prepare the data for cross-process communication
        data = _prepare_data()

        # Create a temporary file for the result
        with tempfile.NamedTemporaryFile(delete=False, mode="w") as temp:
            result_path = temp.name

        try:
            # Create and start a process for the Ollama call
            process = multiprocessing.Process(
                target=_run_ollama_call,
                args=(data, result_path)
            )
            process.start()

            # Wait for the process to finish (with timeout)
            process.join(timeout=60)  # 60 second timeout

            # If the process didn't finish, terminate it
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
                if process.is_alive():
                    process.kill()
                raise TimeoutError("Ollama call timed out after 60 seconds")

            # Read the result from the file
            with open(result_path, 'r') as f:
                result_data = json.load(f)

            # Process the result
            if result_data["success"]:
                # Create an MCP message from the response
                response_content = result_data["content"]
                mcp_response = MCPMessage(
                    role=MCPRole.ASSISTANT,
                    content=[MCPTextContent(text=response_content)]
                )
                return mcp_response
            else:
                # If there was an error, raise it
                raise RuntimeError(f"Ollama error: {result_data['error']}")

        finally:
            # Clean up the temporary file
            try:
                os.unlink(result_path)
            except (OSError, PermissionError):
                # Ignore errors during cleanup
                pass

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
    # Check if this LLM is already registered
    if OllamaLLM.NAME in ComponentConfigurator._registries.get('llm', {}).get_names():
        # Already registered, skip registration
        return

    # Register the LLM and adapter
    ComponentConfigurator.register_llm(OllamaLLM.NAME, OllamaLLM)
    AdapterRegistry.get_instance().register_adapter(OllamaLLM.NAME, OllamaAdapter)
