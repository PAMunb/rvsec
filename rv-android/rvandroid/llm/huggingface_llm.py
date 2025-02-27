import logging
from typing import List, Dict

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

from rvandroid.llm.llm import LanguageModel

logger = logging.getLogger(__name__)

LLAMA = "meta-llama/Meta-Llama-3.1-8B-Instruct"  # needs permission
DEEPSEEK = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"  # "deepseek-ai/deepseek-llm-7b-chat"
QWEN = "Qwen/Qwen2.5-3B-Instruct"  # "Qwen/Qwen2.5-0.5B-Instruct" # "Qwen/Qwen2.5-3B-Instruct" # "Qwen/Qwen2.5-3B" # "Qwen/Qwen2.5-VL-7B-Instruct" "Qwen/Qwen2-7B-Instruct"
PHI = "microsoft/Phi-3.5-mini-instruct"
GRANITE = "ibm-granite/granite-3.1-8b-instruct"
FALCON = "tiiuae/Falcon3-3B-Instruct"
BERT = "google-bert/bert-base-uncased"
GPT2 = "openai-community/gpt2"
MISTRAL = "mistralai/Mistral-7B-Instruct-v0.3"


class HuggingFaceLLM(LanguageModel):  # More descriptive class name
    """
    A class for interacting with Hugging Face language models.

    Attributes:
        model_name (str): The name of the pre-trained model to use.
        _model (AutoModelForCausalLM): The loaded language model (lazy-loaded).
        _tokenizer (AutoTokenizer): The tokenizer for the model (lazy-loaded).
        _device (str): The device to use for model inference (e.g., "cuda", "cpu").
    """
    LLAMA = "meta-llama/Meta-Llama-3.1-8B-Instruct"  # needs permission
    DEEPSEEK = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"  # "deepseek-ai/deepseek-llm-7b-chat"
    QWEN = "Qwen/Qwen2.5-3B-Instruct"  # "Qwen/Qwen2.5-0.5B-Instruct" # "Qwen/Qwen2.5-3B-Instruct" # "Qwen/Qwen2.5-3B" # "Qwen/Qwen2.5-VL-7B-Instruct" "Qwen/Qwen2-7B-Instruct"
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
                    load_in_4bit=True,  # Load the model in 4-bit precision
                    # load_in_8bit=True
                    bnb_4bit_use_double_quant=True,
                    # This option uses double quantization, which further reduces memory usage and improves accuracy
                    bnb_4bit_compute_dtype=torch_dtype,  # This sets the data type for the quantized model
                    bnb_4bit_quant_type="nf4"
                    # This is the type of quantization to use, in this case, "nf4" stands for "normal float 4"
                )

                # Load the model    
                self._model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    device_map=self._device,
                    # This parameter allows you to specify how the model should be loaded on the device
                    quantization_config=quantization_config,
                    # This parameter allows you to specify the quantization configuration for the model
                    torch_dtype=torch_dtype
                )

                # TODO
                # if torch.cuda.is_available():
                #     print("GPU está disponível")
                #     # device = torch.device("cuda")  # Define o dispositivo como GPU
                # else:
                #     print("GPU não está disponível")
                #     # device = torch.device("cpu") 
                if self._device == "cuda":  # Only move to cuda if available
                    self._model.to(self._device)  # Explicit move to device after loading
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
            
            # If it doesn't have a pad_token, define one
            if tokenizer.pad_token is None:
                # Try to use a common padding token if it exists in the vocabulary
                if '<pad>' in tokenizer.get_vocab():
                    tokenizer.pad_token = '<pad>'
                # Otherwise, use the EOS token but ensure that attention mask is defined
                else:
                    tokenizer.pad_token = tokenizer.eos_token
                    # Nothing needs to be done here as we'll handle the mask in the generate method
            
            self._tokenizer = tokenizer
        return self._tokenizer

    def generate(self, messages: List[Dict[str, str]], max_new_tokens: int = 800) -> str:
        """Generates text based on the given messages."""

        # Apply chat template
        encoded_input = self.tokenizer.apply_chat_template(
            messages, return_tensors="pt", add_generation_prompt=True
        )
        
        # Explicitly create an attention mask (all tokens are attended to)
        attention_mask = torch.ones(encoded_input.shape, dtype=torch.long)
        
        # Move to the correct device
        inputs = encoded_input.to(self._device)
        attention_mask = attention_mask.to(self._device)

        # Get the input length to identify only new tokens later
        input_length = inputs.shape[1]

        with torch.no_grad():  # Important for inference
            outputs = self.model.generate(
                inputs, 
                attention_mask=attention_mask,
                max_new_tokens=max_new_tokens
            )
        
        # Extract only the newly generated tokens
        result = self.tokenizer.decode(outputs[0][input_length:], skip_special_tokens=True)

        del inputs, outputs, attention_mask  # Explicitly delete tensors to free memory
        torch.cuda.empty_cache()  # Explicitly clear CUDA cache after generation

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
