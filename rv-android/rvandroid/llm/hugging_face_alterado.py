import logging
from typing import List, Dict
import os

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

from rvandroid.llm.llm import LanguageModel

logger = logging.getLogger(__name__)

# Global variable to track if model is already loaded - singleton pattern
_LOADED_MODELS = {}

class HuggingFaceLLM(LanguageModel):
    """
    A class for interacting with Hugging Face language models with optimized loading.

    Attributes:
        model_name (str): The name of the pre-trained model to use.
        _model (AutoModelForCausalLM): The loaded language model (lazy-loaded).
        _tokenizer (AutoTokenizer): The tokenizer for the model (lazy-loaded).
        _device (str): The device to use for model inference (e.g., "cuda", "cpu").
    """
    LLAMA = "meta-llama/Meta-Llama-3.1-8B-Instruct"  # needs permission
    DEEPSEEK = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"
    QWEN = "Qwen/Qwen2.5-3B-Instruct"
    PHI = "microsoft/Phi-3.5-mini-instruct"
    GRANITE = "ibm-granite/granite-3.1-8b-instruct"
    MISTRAL = "mistralai/Mistral-7B-Instruct-v0.3"
    FALCON = "tiiuae/Falcon3-3B-Instruct"

    MODELS = [LLAMA, DEEPSEEK, QWEN, PHI, GRANITE, MISTRAL, FALCON]

    def __init__(self, model_name: str, device: str = "cuda"):
        """Initializes the HuggingFaceLLM with a model name and device."""
        super().__init__(model_name)
        self._device = device
        
        # Forcefully disable progress bars at multiple levels
        os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
        os.environ["TRANSFORMERS_VERBOSITY"] = "error"
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        
        # Check if we already have this model loaded globally
        global _LOADED_MODELS
        model_key = f"{model_name}_{device}"
        
        if model_key in _LOADED_MODELS:
            self._model, self._tokenizer = _LOADED_MODELS[model_key]
            logger.info(f"Using already loaded model {model_name}")
        else:
            self._model = None
            self._tokenizer = None

    @property
    def model(self) -> AutoModelForCausalLM:
        """Loads and returns the language model (lazy-loaded with optimizations)."""
        # If model already loaded, return it
        if self._model is not None:
            return self._model
            
        # Check if it's in the global cache
        global _LOADED_MODELS
        model_key = f"{self.model_name}_{self._device}"
        
        if model_key in _LOADED_MODELS:
            self._model, self._tokenizer = _LOADED_MODELS[model_key]
            return self._model
        
        logger.info(f"Loading model {self.model_name} on {self._device}...")
        
        # Determine appropriate dtype
        torch_dtype = torch.float16
        if self._device == "cuda" and torch.cuda.is_available():
            try:
                if torch.cuda.is_bf16_supported():
                    torch_dtype = torch.bfloat16
            except:
                pass
        
        # Prepare quantization config for CUDA
        if self._device == "cuda" and torch.cuda.is_available():
            try:
                # Quantization configuration
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_compute_dtype=torch_dtype,
                    bnb_4bit_quant_type="nf4"
                )
                
                # Load the model with quantization
                self._model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    device_map="auto",
                    torch_dtype=torch_dtype,
                    quantization_config=quantization_config,
                    low_cpu_mem_usage=True,
                )
            except Exception as e:
                logger.warning(f"Error loading with quantization: {e}. Falling back to standard loading.")
                self._model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    device_map="auto",
                    torch_dtype=torch_dtype,
                    low_cpu_mem_usage=True,
                )
        else:
            # Standard loading for CPU
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map="cpu",
                torch_dtype=torch_dtype,
                low_cpu_mem_usage=True,
            )
        
        # Load tokenizer together with model to avoid repeated loading
        self._load_tokenizer()
        
        # Store in global cache
        _LOADED_MODELS[model_key] = (self._model, self._tokenizer)
        
        return self._model

    def _load_tokenizer(self):
        """Internal method to load tokenizer"""
        logger.info(f"Loading tokenizer for {self.model_name}...")
        
        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        
        # If it doesn't have a pad_token, define one
        if tokenizer.pad_token is None:
            if '<pad>' in tokenizer.get_vocab():
                tokenizer.pad_token = '<pad>'
            else:
                tokenizer.pad_token = tokenizer.eos_token
        
        self._tokenizer = tokenizer

    @property
    def tokenizer(self) -> AutoTokenizer:
        """Loads and returns the tokenizer (lazy-loaded)."""
        if self._tokenizer is None:
            self._load_tokenizer()
            
            # Also ensure model is loaded to avoid sequential loading messages
            if self._model is None:
                _ = self.model
                
        return self._tokenizer

    def generate(self, messages: List[Dict[str, str]], max_new_tokens: int = 800) -> str:
        """Generates text based on the given messages."""
        # Ensure model and tokenizer are loaded
        model = self.model
        tokenizer = self.tokenizer

        # Apply chat template
        encoded_input = tokenizer.apply_chat_template(
            messages, return_tensors="pt", add_generation_prompt=True
        )
        
        # Explicitly create an attention mask
        attention_mask = torch.ones(encoded_input.shape, dtype=torch.long)
        
        # Move to the correct device
        inputs = encoded_input.to(self._device)
        attention_mask = attention_mask.to(self._device)

        # Get the input length to identify only new tokens later
        input_length = inputs.shape[1]

        with torch.no_grad():
            outputs = model.generate(
                inputs, 
                attention_mask=attention_mask,
                max_new_tokens=max_new_tokens,
                pad_token_id=tokenizer.pad_token_id,
            )
        
        # Extract only the newly generated tokens
        result = tokenizer.decode(outputs[0][input_length:], skip_special_tokens=True)

        del inputs, outputs, attention_mask  # Free memory
        torch.cuda.empty_cache()

        return result

    def clean(self):
        """Unloads the model and tokenizer from memory."""
        global _LOADED_MODELS
        model_key = f"{self.model_name}_{self._device}"
        
        if model_key in _LOADED_MODELS:
            del _LOADED_MODELS[model_key]
            
        if hasattr(self, '_model') and self._model is not None:
            del self._model
            self._model = None

        if hasattr(self, '_tokenizer') and self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None

        torch.cuda.empty_cache()
        logger.info("Model and tokenizer unloaded, CUDA cache cleared.")

    @staticmethod
    def models() -> List[str]:
        return HuggingFaceLLM.MODELS

    def __str__(self):
        return f"HF: {self.model_name}"
    