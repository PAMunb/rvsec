# rvandroid/llm/dspy_llm.py
import json
import logging
import os
from typing import List, Dict

# Basic DSPy import
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

    # MODELS = [LLAMA, PHI, QWEN, MISTRAL]
    MODELS = [LLAMA, QWEN]

    def __init__(self, model_name: str, provider: str = "ollama", base_url: str = "http://localhost:11434",
                 use_cot: bool = True, **kwargs):
        """
        Initialize DSPyLLM with a model name and provider.

        Args:
            model_name: Name of the model
            provider: Provider for the model ('ollama', 'huggingface', 'openai', 'anthropic')
            base_url: Base URL for API (for Ollama)
            use_cot: Whether to use Chain of Thought reasoning
            **kwargs: Additional model parameters for generation
        """
        super().__init__(model_name)
        self.provider = provider
        self.base_url = base_url
        self.use_cot = use_cot
        self._lm = None
        self.logger = logger
        self.kwargs = kwargs

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
                    # Set environment variable for Ollama
                    os.environ["OLLAMA_BASE_URL"] = self.base_url

                    # Create properly formatted model name for LiteLLM
                    formatted_model = f"ollama/{self.model_name}"

                    # Try different approaches based on DSPy version
                    try:
                        # For newer DSPy versions
                        self._lm = dspy.LM(model=formatted_model)
                    except (ImportError, AttributeError, TypeError):
                        try:
                            # For older DSPy versions with OllamaAPI
                            if hasattr(dspy, 'OllamaAPI'):
                                self._lm = dspy.OllamaAPI(model=self.model_name)
                            # Use local Ollama approach
                            elif hasattr(dspy, 'OllamaLocal'):
                                self._lm = dspy.OllamaLocal(model=self.model_name, base_url=self.base_url)
                            else:
                                # Generic usage via LM interface with provider specified
                                self._lm = dspy.LM(model=self.model_name, provider="ollama")
                        except Exception as e:
                            self.logger.warning(f"Falling back to direct LiteLLM usage: {e}")
                            # Direct LiteLLM usage
                            import litellm
                            self._lm = dspy.LM(model=formatted_model)
                else:
                    # For other providers, format the model name appropriately
                    if self.provider == "huggingface":
                        formatted_model = f"huggingface/{self.model_name}"
                    elif self.provider == "openai":
                        formatted_model = self.model_name  # OpenAI models are already properly formatted
                    elif self.provider == "anthropic":
                        formatted_model = self.model_name  # Anthropic models are already properly formatted
                    else:
                        # For unknown providers, try direct naming
                        formatted_model = f"{self.provider}/{self.model_name}"

                    self._lm = dspy.LM(model=formatted_model)

                # Configure DSPy to use this language model - try different methods
                try:
                    # New approach
                    dspy.configure(lm=self._lm)
                except AttributeError:
                    # Old approach
                    if hasattr(dspy.settings, 'configure'):
                        dspy.settings.configure(lm=self._lm)
                    # If nothing works, the configured lm should be sufficient

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

            # Combine prompts into a simple format
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"

            # Use basic DSPy API to generate response
            try:
                # Try using the preferred complete method
                if hasattr(self._lm, 'complete'):
                    response = self._lm.complete(combined_prompt, max_tokens=max_new_tokens)
                # Fall back to generate method if complete is not available
                elif hasattr(self._lm, 'generate'):
                    response = self._lm.generate(combined_prompt, max_tokens=max_new_tokens)
                # Last resort: call the LM object directly
                else:
                    response = self._lm(combined_prompt)
            except Exception as e:
                self.logger.warning(f"Error in first generation attempt: {e}")

                # Try direct LiteLLM usage as fallback
                try:
                    import litellm
                    formatted_model = f"ollama/{self.model_name}"
                    response = litellm.completion(
                        model=formatted_model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        max_tokens=max_new_tokens
                    )
                    return response.choices[0].message.content
                except Exception as nested_e:
                    self.logger.error(f"LiteLLM fallback also failed: {nested_e}")
                    raise e  # Re-raise the original exception

            # Convert to string if necessary
            if hasattr(response, 'text'):
                response_text = response.text
            elif isinstance(response, str):
                response_text = response
            else:
                response_text = str(response)

            # Try to extract valid JSON from the response
            try:
                import re
                json_match = re.search(r'\[\s*{.*}\s*\]', response_text, re.DOTALL)
                if json_match:
                    json_text = json_match.group(0)
                    json.loads(json_text)  # Validate as JSON
                    return json_text
            except:
                pass

            # Return original response
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