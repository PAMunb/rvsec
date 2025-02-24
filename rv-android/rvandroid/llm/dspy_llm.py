# rvandroid/llm/dspy_llm.py
from typing import List, Dict
import dspy
from dspy.teleprompt import BootstrapFewShot

from rvandroid.llm.llm import LanguageModel


class DSPyLLM(LanguageModel):
    """
    A language model implementation using DSPy for generating text.
    Supports a programmable approach to prompt engineering.
    """
    
    # Models available for DSPy (these should be models that work well with DSPy)
    LLAMA = "llama3.2:3b"
    PHI = "phi3.5:3.8b"
    QWEN = "qwen2.5:3b"
    MISTRAL = "mistral:7b"
    
    MODELS = [LLAMA, PHI, QWEN, MISTRAL]
    
    def __init__(self, model_name: str, provider: str = "ollama", base_url: str = "http://localhost:11434"):
        """
        Initialize DSPyLLM with a model name and provider.
        
        Args:
            model_name: Name of the model
            provider: Provider for the model ('ollama')
            base_url: Base URL for Ollama API (if using Ollama)
        """
        super().__init__(model_name)
        self.provider = provider
        self.base_url = base_url
        self._model = None
        self._predictor = None
    
    @property
    def model(self):
        """
        Returns (or initializes) the DSPy model.
        """
        if self._model is None:
            if self.provider == "ollama":
                self._model = dspy.OllamaLocal(
                    model=self.model_name,
                    base_url=self.base_url
                )
                dspy.settings.configure(lm=self._model)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        return self._model
    
    def generate(self, messages: List[Dict[str, str]], max_new_tokens: int = 800) -> str:
        """
        Generates text based on the given messages using DSPy.
        
        Args:
            messages: List of message dictionaries
            max_new_tokens: Maximum number of tokens to generate
            
        Returns:
            Generated text
        """
        # Ensure model is initialized
        _ = self.model
        
        # Extract system and user prompts
        system_prompt = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_prompt = next((m["content"] for m in messages if m["role"] == "user"), "")
        
        # Define a simple DSPy module for generating responses
        class ActionGenerator(dspy.Module):
            def __init__(self, system_prompt):
                super().__init__()
                self.system_prompt = system_prompt
            
            def forward(self, user_input):
                prompt = f"{self.system_prompt}\n\n{user_input}"
                response = dspy.Predict("response")(prompt=prompt)
                return response.response
        
        # Create and optimize the generator
        generator = ActionGenerator(system_prompt)
        
        # For more complex scenarios, we could use BootstrapFewShot or other techniques
        # optimized_generator = BootstrapFewShot(generator, metric=..., num_trials=5)
        
        # Generate the response
        response = generator(user_input=user_prompt)
        
        return response
    
    def clean(self):
        """
        Clean up resources.
        """
        self._model = None
        self._predictor = None
    
    @staticmethod
    def models() -> List[str]:
        """
        Returns available models.
        """
        return DSPyLLM.MODELS
    
    def __str__(self):
        return f"DSPy({self.provider}): {self.model_name}"