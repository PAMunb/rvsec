import logging
import os
from typing import List, Dict, Any

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

from rvandroid.llm.llm import LanguageModel

logger = logging.getLogger(__name__)  


LLAMA = "meta-llama/Meta-Llama-3.1-8B-Instruct" # needs permission
DEEPSEEK = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B" # "deepseek-ai/deepseek-llm-7b-chat"
QWEN = "Qwen/Qwen2.5-3B-Instruct" # "Qwen/Qwen2.5-0.5B-Instruct" # "Qwen/Qwen2.5-3B-Instruct" # "Qwen/Qwen2.5-3B" # "Qwen/Qwen2.5-VL-7B-Instruct" "Qwen/Qwen2-7B-Instruct"
PHI = "microsoft/Phi-3.5-mini-instruct"
GRANITE = "ibm-granite/granite-3.1-8b-instruct"
FALCON = "tiiuae/Falcon3-3B-Instruct"

# LLAMA = "meta-llama/Meta-Llama-3.1-8B-Instruct" # needs permission
# QWEN = "Qwen/Qwen2.5-3B-Instruct" # "Qwen/Qwen2.5-0.5B-Instruct" # "Qwen/Qwen2.5-3B-Instruct" # "Qwen/Qwen2.5-3B" # "Qwen/Qwen2.5-VL-7B-Instruct" "Qwen/Qwen2-7B-Instruct"
# QWEN_0_5B = "Qwen/Qwen2.5-0.5B-Instruct"
# # PHI2 = "microsoft/phi-2"
# PHI3 = "microsoft/Phi-3-mini-4k-instruct"
# PHI3_5="microsoft/Phi-3.5-mini-instruct"
# GEMMA2 = "google/gemma-2-2b-it" # needs permission: https://huggingface.co/google/gemma-2-2b-it
# STARCODER2 = "bigcode/starcoder2-3b"
# FALCON= "tiiuae/Falcon3-3B-Instruct" # tiiuae/Falcon3-7B-Instruct # https://falconllm.tii.ae/
# GRANITE = "ibm-granite/granite-3.1-8b-instruct"
# DEEPSEEK = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B" # "deepseek-ai/deepseek-llm-7b-chat"
# DEEPSEEK_CHAT = "deepseek-ai/deepseek-llm-7b-chat"

# MODELS = [
#     LLAMA,
#     QWEN,
#     QWEN_0_5B,
#     PHI3,
#     PHI3_5,
#     GEMMA2,
#     STARCODER2,
#     FALCON,
#     GRANITE,
#     DEEPSEEK,
#     DEEPSEEK_CHAT,
# ]

class HuggingFaceLLM(LanguageModel):  # More descriptive class name
    """
    A class for interacting with Hugging Face language models.

    Attributes:
        model_name (str): The name of the pre-trained model to use.
        _model (AutoModelForCausalLM): The loaded language model (lazy-loaded).
        _tokenizer (AutoTokenizer): The tokenizer for the model (lazy-loaded).
        _device (str): The device to use for model inference (e.g., "cuda", "cpu").
    """
    LLAMA = "meta-llama/Meta-Llama-3.1-8B-Instruct" # needs permission
    DEEPSEEK = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B" # "deepseek-ai/deepseek-llm-7b-chat"
    QWEN = "Qwen/Qwen2.5-3B-Instruct" # "Qwen/Qwen2.5-0.5B-Instruct" # "Qwen/Qwen2.5-3B-Instruct" # "Qwen/Qwen2.5-3B" # "Qwen/Qwen2.5-VL-7B-Instruct" "Qwen/Qwen2-7B-Instruct"
    PHI = "microsoft/Phi-3.5-mini-instruct"    
    GRANITE = "ibm-granite/granite-3.1-8b-instruct"
    MISTRAL = "mistralai/Mistral-7B-Instruct-v0.3"
    FALCON = "tiiuae/Falcon3-3B-Instruct"

    MODELS = [LLAMA, DEEPSEEK, QWEN, PHI, GRANITE, MISTRAL, FALCON]

    def __init__(self, model_name: str, device: str = "cuda"):
        """Initializes the HuggingFaceLLM with a model name and device."""
        super().__init__(model_name)
        self._model = None
        self._tokenizer = None
        self._device = device 


    @property
    def model(self) -> AutoModelForCausalLM:
        """Loads and returns the language model (lazy-loaded)."""
        if self._model is None:
            logger.info(f"Loading model {self.model_name} on {self._device}...")
            try:
                # Consider float16 if bfloat16 is not supported
                torch_dtype = torch.bfloat16 if self._device == "cuda" else torch.float32

                # Quantization is a process that reduces the size and precision of a model's parameters, 
                # making it more efficient in terms of memory and time usage. It does this by representing 
                # numerical values ​​with fewer bits, which allows large models to run on lower-powered devices.
                quantization_config = BitsAndBytesConfig(  
                    load_in_4bit=True, # Load the model in 4-bit precision
                    # load_in_8bit=True
                    bnb_4bit_use_double_quant=True, # This option uses double quantization, which further reduces memory usage and improves accuracy
                    bnb_4bit_compute_dtype=torch_dtype, # This sets the data type for the quantized model
                    bnb_4bit_quant_type="nf4" # This is the type of quantization to use, in this case, "nf4" stands for "normal float 4"
                )

                # Load the model    
                self._model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    device_map=self._device,  # This parameter allows you to specify how the model should be loaded on the device
                    quantization_config=quantization_config, # This parameter allows you to specify the quantization configuration for the model
                    torch_dtype=torch_dtype
                )
                
                # if torch.cuda.is_available():
                #     print("GPU está disponível")
                #     # device = torch.device("cuda")  # Define o dispositivo como GPU
                # else:
                #     print("GPU não está disponível")
                #     # device = torch.device("cpu") 
                if self._device == "cuda": # Only move to cuda if available
                    self._model.to(self._device) # Explicit move to device after loading
            except Exception as e:
                logger.error(f"Error loading model: {e}")
                raise  # Re-raise the exception for proper handling
        return self._model

    @property
    def tokenizer(self) -> AutoTokenizer:
        """Loads and returns the tokenizer (lazy-loaded)."""
        if self._tokenizer is None:
            logger.info(f"Loading tokenizer for {self.model_name}...")
            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            tokenizer.pad_token = tokenizer.eos_token  # Set pad token if needed
            self._tokenizer = tokenizer
        return self._tokenizer

    def generate(self, messages: List[Dict[str, str]], max_new_tokens: int = 800) -> str:
        """Generates text based on the given messages."""

        inputs = self.tokenizer.apply_chat_template(
            messages, return_tensors="pt", add_generation_prompt=True
        ).to(self._device)  # Use the correct device

        with torch.no_grad():  # Important for inference
            outputs = self.model.generate(inputs, max_new_tokens=max_new_tokens)

        result = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        del inputs, outputs # Explicitly delete tensors to free memory
        torch.cuda.empty_cache() # Explicitly clear CUDA cache after generation

        return result

    def clean(self):
        """Unloads the model and tokenizer from memory."""

        if hasattr(self, '_model') and self._model is not None:
            del self._model
            self._model = None

        if hasattr(self, '_tokenizer') and self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None

        torch.cuda.empty_cache()  # Clear CUDA cache
        logger.info("Model and tokenizer unloaded, CUDA cache cleared.")

    @staticmethod    
    def models() -> List[str]:
        # return [model.name for model in self.client.models()]
        return HuggingFaceLLM.MODELS

    def __str__(self):
        return f"HF: {self.model_name}"        
    