# rvandroid/llm/dspy_llm.py
import logging
from typing import List, Dict, Any, Optional
import json
import os

# Importação básica do DSPy
import dspy

from rvandroid.llm.llm import LanguageModel

logger = logging.getLogger(__name__)


class DSPyLLM(LanguageModel):
    """
    Language model implementation using DSPy for generating text.
    Simplified to work with current DSPy API structure.
    """

    NAME = "dspy"
    # Models available for DSPy
    LLAMA = "llama3.2:3b"
    PHI = "phi3.5:3.8b"
    QWEN = "qwen2.5:3b"
    MISTRAL = "mistral:7b"

    MODELS = [LLAMA, PHI, QWEN, MISTRAL]

    def __init__(self, model_name: str, provider: str = "ollama", base_url: str = "http://localhost:11434",
                 use_cot: bool = True):
        """
        Initialize DSPyLLM with a model name and provider.

        Args:
            model_name: Name of the model
            provider: Provider for the model ('ollama', 'huggingface', 'openai', 'anthropic')
            base_url: Base URL for API (for Ollama)
            use_cot: Whether to use Chain of Thought reasoning (ignored in simplification)
        """
        super().__init__(model_name)
        self.provider = provider
        self.base_url = base_url
        self.use_cot = use_cot
        self._lm = None
        self.logger = logger

    @property
    def lm(self):
        """
        Returns (or initializes) the DSPy language model.

        Returns:
            DSPy language model instance
        """
        if self._lm is None:
            self.logger.info(f"Initializing DSPy with provider {self.provider}")

            try:
                if self.provider == "ollama":
                    # Tenta diferentes abordagens para acessar o Ollama
                    try:
                        # Tenta importar o Ollama da forma mais atual
                        from dspy.retrieve.ollama import Ollama
                        self._lm = Ollama(model=self.model_name, base_url=self.base_url)
                    except ImportError:
                        try:
                            # Tenta a abordagem alternativa
                            if hasattr(dspy, 'OllamaLocal'):
                                self._lm = dspy.OllamaLocal(model=self.model_name, base_url=self.base_url)
                            else:
                                # Uso genérico via LM interface
                                self._lm = dspy.LM(model=self.model_name, provider="ollama", base_url=self.base_url)
                        except (ImportError, AttributeError):
                            # Última tentativa usando configuração manual
                            self.logger.warning("Using manual Ollama configuration via OLLAMA_BASE_URL")
                            # Set environment variable for Ollama
                            os.environ["OLLAMA_BASE_URL"] = self.base_url
                            self._lm = dspy.OllamaAPI(model=self.model_name)
                else:
                    self.logger.warning(f"Provider {self.provider} may not be supported")
                    # Tenta uma abordagem genérica
                    self._lm = dspy.LM(provider=self.provider, model=self.model_name)

                # Configure DSPy to use this language model - tenta diferentes métodos
                try:
                    # Nova forma
                    dspy.configure(lm=self._lm)
                except AttributeError:
                    # Forma antiga
                    if hasattr(dspy.settings, 'configure'):
                        dspy.settings.configure(lm=self._lm)
                    # Se nada funcionar, o lm já configurado deve ser suficiente

                self.logger.info(f"Successfully initialized DSPy with {self.provider}")
            except Exception as e:
                self.logger.error(f"Error initializing DSPy: {e}")
                raise

        return self._lm

    def generate(self, messages: List[Dict[str, str]], max_new_tokens: int = 800) -> str:
        """
        Generates text based on the given messages using DSPy.

        Args:
            messages: List of message dictionaries
            max_new_tokens: Maximum number of tokens to generate

        Returns:
            Generated text
        """
        try:
            # Ensure LM is initialized
            _ = self.lm

            # Extract system and user prompts
            system_prompt = next((m["content"] for m in messages if m["role"] == "system"), "")
            user_prompt = next((m["content"] for m in messages if m["role"] == "user"), "")

            # Combine prompts para um formato simples
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"

            # Use a API básica do DSPy para gerar resposta
            if hasattr(self._lm, 'complete'):
                # Usa a API de completion
                response = self._lm.complete(combined_prompt, max_tokens=max_new_tokens)
            elif hasattr(self._lm, 'generate'):
                # Usa a API de generate
                response = self._lm.generate(combined_prompt, max_tokens=max_new_tokens)
            else:
                # Fallback - tenta chamar o lm como função
                response = self._lm(combined_prompt)

            # Converte para string se necessário
            if hasattr(response, 'text'):
                response_text = response.text
            elif isinstance(response, str):
                response_text = response
            else:
                response_text = str(response)

            # Tenta extrair JSON válido da resposta
            try:
                import re
                json_match = re.search(r'\[\s*{.*}\s*\]', response_text, re.DOTALL)
                if json_match:
                    json_text = json_match.group(0)
                    json.loads(json_text)  # Valida se é JSON
                    return json_text
            except:
                pass

            # Retorna resposta original
            return response_text

        except Exception as e:
            self.logger.error(f"Error generating text with DSPy: {e}")
            raise

    def clean(self) -> None:
        """
        Clean up resources.
        """
        self._lm = None
        self.logger.info("DSPy resources released")

    @staticmethod
    def models() -> List[str]:
        """
        Returns available models.

        Returns:
            List of model identifiers
        """
        return DSPyLLM.MODELS