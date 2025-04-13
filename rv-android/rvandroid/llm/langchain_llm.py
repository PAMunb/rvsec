# rvandroid/llm/langchain_llm.py
import json
import logging
from typing import List, Dict, Optional, Any

# Use try-except to handle langchain vs langchain-community imports
try:
    # Try the new recommended import
    from langchain_community.llms import Ollama
except ImportError:
    # Fall back to the deprecated import
    try:
        from langchain.llms import Ollama
    except ImportError:
        # Define a stub if both imports fail
        class Ollama:
            def __init__(self, *args, **kwargs):
                raise ImportError("Could not import Ollama from langchain or langchain_community")
# Basic imports with fallback
try:
    # Try the new recommended import path
    from langchain_community.memory import ConversationBufferMemory
except ImportError:
    try:
        # Fall back to the deprecated import path
        from langchain.memory import ConversationBufferMemory
    except ImportError:
        # Define a stub if both imports fail
        class ConversationBufferMemory:
            def __init__(self, *args, **kwargs):
                raise ImportError("Could not import ConversationBufferMemory from langchain or langchain_community")

from rvandroid.llm.language_model import LanguageModel
from rvandroid.llm.data_structures import MCPMessage, MCPConfiguration
from rvandroid.llm.adapters.langchain_adapter import LangchainAdapter
from rvandroid.util.error.error_handler import ErrorHandler

logger = logging.getLogger(__name__)


class SimpleJsonParser:
    """Simple JSON parser for internal use."""

    def parse(self, text: str) -> Dict:
        try:
            # Try to find the start and end of JSON in the string
            start_idx = text.find('[')
            end_idx = text.rfind(']') + 1

            if start_idx == -1 or end_idx <= start_idx:
                # Try to find a JSON object if it's not an array
                start_idx = text.find('{')
                end_idx = text.rfind('}') + 1

            if start_idx != -1 and end_idx > start_idx:
                json_text = text[start_idx:end_idx]
                return json.loads(json_text)

            # If extraction fails, try to parse the complete text
            return json.loads(text)
        except Exception as e:
            logger.warning(f"JSON parsing failed: {e}")
            return {"error": "Failed to parse JSON", "raw_text": text}


class LangchainLLM(LanguageModel):
    """
    Language model implementation using LangChain for generating text using MCP.
    Provides a unified interface to different LLM providers through LangChain.
    """
    
    # Models available for LangChain
    LLAMA = "llama3.2:3b"
    PHI = "phi3.5:3.8b"
    QWEN = "qwen2.5:3b"
    MISTRAL = "mistral:7b"

    # All models - only ones known to work with Ollama
    MODELS = [LLAMA, PHI, QWEN, MISTRAL]

    def __init__(
            self,
            model_name: str,
            provider: str = "ollama",
            base_url: str = "http://localhost:11434",
            api_key: Optional[str] = None,
            use_memory: bool = False,
            use_json_parser: bool = True,
            **kwargs
    ):
        """
        Initialize LangchainLLM with a model name and provider.

        Args:
            model_name: Name of the model
            provider: Provider for the model ('ollama' is the only supported one in this version)
            base_url: Base URL for API (for Ollama)
            api_key: API key (not used in this version)
            use_memory: Whether to enable conversation memory
            use_json_parser: Whether to use JSON output parsing
            **kwargs: Additional model parameters for generation
        """
        # Initialize the language model base class
        super().__init__(model_name)
        
        # Set up model properties
        self.provider = provider
        self.base_url = base_url
        self.api_key = api_key
        self.use_memory = use_memory
        self.use_json_parser = use_json_parser
        self._llm = None
        self._chain = None
        self._memory = None
        self._parser = SimpleJsonParser()  # Use our simple implementation
        self.logger = logger
        self.kwargs = kwargs
        self.error_handler = ErrorHandler.get_instance()

        # Add base_url to kwargs for the adapter
        self.kwargs["base_url"] = base_url
        
        # Initialize components as needed
        if self.use_memory:
            self._memory = ConversationBufferMemory(return_messages=True)

    def _get_model_type(self) -> str:
        """Get model type string."""
        return "langchain"

    def _get_adapter(self):
        """Get the appropriate MCP adapter for this model."""
        return LangchainAdapter()

    @property
    def llm(self):
        """
        Returns (or initializes) the LangChain LLM instance.

        Returns:
            LangChain LLM instance
        """
        if self._llm is None:
            self.logger.info(f"Initializing LangChain with provider {self.provider}")

            try:
                # Extract LangChain-specific parameters
                model_kwargs = {
                    "temperature": self.kwargs.get("temperature", 0.2)
                }
                
                # Add other kwargs (excluding those already used)
                for key, value in self.kwargs.items():
                    if key not in ["temperature"] and key != "max_tokens":
                        model_kwargs[key] = value
                        
                if self.provider == "ollama":
                    self._llm = Ollama(
                        model=self.model_name,
                        base_url=self.base_url,
                        **model_kwargs
                    )
                else:
                    # For this version, we only support Ollama
                    self.logger.warning(
                        f"Provider {self.provider} not supported in this version, falling back to Ollama")
                    self._llm = Ollama(
                        model=self.model_name,
                        base_url=self.base_url,
                        **model_kwargs
                    )

                self.logger.info(f"Successfully initialized LangChain LLM with {self.provider}")
            except Exception as e:
                error_msg = f"Error initializing LangChain LLM: {str(e)}"
                self.logger.error(error_msg)
                from rvandroid.util.exceptions import RVAndroidError
                error = RVAndroidError(error_msg)
                self.error_handler.handle_error(error)
                raise

        return self._llm

    async def generate(self, messages: List[MCPMessage], config: Optional[MCPConfiguration] = None) -> MCPMessage:
        """Generate a response using the language model asynchronously."""
        # Use synchronous implementation for now
        return self.generate_sync(messages, config)

    def generate_sync(self, messages: List[MCPMessage], config: Optional[MCPConfiguration] = None) -> MCPMessage:
        """
        Generate text based on the input messages synchronously using MCP.

        Args:
            messages: List of MCPMessage objects
            config: Optional MCPConfiguration object

        Returns:
            MCPMessage with the generated response
        """
        # Use provided config or default
        _config = config or self.config
        
        try:
            # Get MCP adapter
            adapter = self._get_adapter()
            
            # Validate request
            if not adapter.validate_request(messages, _config):
                error_msg = "Invalid request for Langchain model"
                self.logger.error(error_msg)
                self.error_handler.handle_error("langchain_invalid_request", error_msg)
                raise ValueError(error_msg)
            
            # Format messages using the adapter
            request_data = adapter.prepare_messages(messages)
            prompt = request_data.get("prompt", "")
            
            # Format configuration using the adapter
            lc_config = adapter.prepare_config(_config)
            
            # Generate with Langchain
            llm = self.llm
            response = llm(prompt)
            
            # Parse JSON if needed
            if self.use_json_parser and ("[" in response or "{" in response):
                try:
                    parsed = self._parser.parse(response)
                    response = json.dumps(parsed)
                except Exception as e:
                    self.logger.warning(f"JSON parsing failed: {e}, returning raw response")
                
            # Parse response using the adapter
            return adapter.parse_response(response)
            
        except Exception as e:
            error_msg = f"Error generating text with LangChain: {str(e)}"
            self.logger.error(error_msg)
            self.error_handler.handle_error("langchain_generation_error", error_msg)
            raise

    def cleanup(self) -> None:
        """
        Clean up resources.
        """
        self._llm = None
        self._chain = None
        self._memory = None  # Clear conversation memory
        self.logger.info("LangChain resources released")

    @staticmethod
    def models() -> List[str]:
        """
        Returns available models.

        Returns:
            List of model identifiers
        """
        return LangchainLLM.MODELS