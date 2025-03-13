import logging
from typing import List, Dict

from ollama import ChatResponse, Client

from rvandroid.llm.llm import LanguageModel

logger = logging.getLogger(__name__)


class OllamaLLM(LanguageModel):
    """
    Language model implementation that uses Ollama API.
    Provides access to locally running Ollama models.
    """
    NAME = "ollama"

    # Available model definitions
    LLAMA = "llama3.2:3b"
    DEEPSEEK = "deepseek-r1:1.5B"
    GEMMA = "gemma3:4b"
    QWEN = "qwen2.5:3b"
    PHI = "phi3.5:3.8b"
    GRANITE = "granite3.1-dense:8b"
    MISTRAL = "mistral:7b"
    FALCON = "falcon3:3b"

    MODELS = [LLAMA, DEEPSEEK, GEMMA, QWEN, PHI, GRANITE, MISTRAL, FALCON]

    def __init__(self, model_name: str, base_url: str = "http://localhost:11434"):
        """
        Initialize the OllamaLLM.

        Args:
            model_name: Name of the Ollama model
            base_url: Base URL for the Ollama API
        """
        super().__init__(model_name)
        self.base_url = base_url
        print(f"***** base_url={self.base_url}")
        self._client = None
        self.logger = logger

    @property
    def client(self) -> Client:
        """
        Get or initialize the Ollama client.

        Returns:
            Ollama Client instance
        """
        print(f"***** client={self.base_url}")
        if not self._client:
            print("iniciando .....................")
            self.logger.info(f"Initializing Ollama client with base URL: {self.base_url}")
            try:
                self._client = Client(host=self.base_url)
                print(f"client iniciado ..................... {self._client}")
                # Pull model to ensure it's available (this is non-blocking if already pulled)
                self.logger.info(f"Ensuring model {self.model_name} is available")
                self._client.pull(self.model_name)
                self.logger.info(f"Model {self.model_name} is ready")
            except Exception as e:
                self.logger.error(f"Error initializing Ollama client: {e}")
                raise

        return self._client

    def generate(self, messages: List[Dict[str, str]], max_new_tokens: int = 800) -> str:
        """
        Generate text using the Ollama model.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_new_tokens: Maximum number of tokens to generate (not directly used by Ollama)

        Returns:
            Generated text

        Raises:
            Exception: If generation fails
        """
        try:
            # Convert max_new_tokens to Ollama num_predict if needed
            options = {}
            if max_new_tokens:
                options["num_predict"] = max_new_tokens

            self.logger.debug(f"Generating with {self.model_name} using {len(messages)} messages")
            response: ChatResponse = self.client.chat(
                model=self.model_name,
                messages=messages,
                options=options,
                keep_alive=True  # Keep model loaded for potential subsequent requests
            )

            return response.message.content
        except Exception as e:
            self.logger.error(f"Error generating text with Ollama: {e}")
            raise

    def clean(self) -> None:
        """
        Clean up resources by releasing the client.
        """
        self._client = None
        self.logger.info("Ollama client released")

    @staticmethod
    def models() -> List[str]:
        """
        Returns a list of available models.

        Returns:
            List of model identifiers
        """
        return OllamaLLM.MODELS
