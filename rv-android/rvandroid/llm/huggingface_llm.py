# rvandroid/llm/huggingface_llm.py
import logging
from typing import List, Dict, Optional

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

from rvandroid.llm.language_model import LanguageModel
from rvandroid.llm.data_structures import LLMMessage
from rvandroid.llm.adapters.huggingface_adapter import HuggingFaceAdapter
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.util.error.error_handler import ErrorHandler

logger = logging.getLogger(__name__)


class HuggingFaceLLM(LanguageModel):
    """
    A class for interacting with Hugging Face language models using MCP.
    Provides efficient loading and generation with quantization support.
    """
    NAME = "huggingface"
    
    # Available model definitions
    LLAMA = "meta-llama/Meta-Llama-3.1-8B-Instruct"
    DEEPSEEK = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"
    GEMMA = "google/gemma-3-4b-it"
    QWEN = "Qwen/Qwen2.5-3B-Instruct"
    PHI = "microsoft/Phi-3.5-mini-instruct"
    GRANITE = "ibm-granite/granite-3.1-8b-instruct"
    FALCON = "tiiuae/Falcon3-3B-Instruct"
    MISTRAL = "mistralai/Mistral-7B-Instruct-v0.3"

    # MODELS = [LLAMA, DEEPSEEK, GEMMA, QWEN, PHI, GRANITE, FALCON, MISTRAL]
    MODELS = [LLAMA, GEMMA, QWEN]

    def __init__(self, model_name: str, device: str = "cuda", **kwargs):
        """
        Initialize the HuggingFaceLLM.

        Args:
            model_name: Name of the Hugging Face model
            device: Device to use for inference ('cuda' or 'cpu')
            **kwargs: Additional model parameters for generation
        """
        # Initialize the language model base class
        super().__init__(model_name)
        
        # Set up model properties
        self._model = None
        self._tokenizer = None
        self._device = device
        self.logger = logger
        self.kwargs = kwargs
        self.error_handler = ErrorHandler.get_instance()
        
        # Store device in kwargs for the adapter
        self.kwargs["device"] = device

    def _get_model_type(self) -> str:
        """Get model type string."""
        return "huggingface"

    def _get_adapter(self):
        """Get the appropriate MCP adapter for this model."""
        return HuggingFaceAdapter()

    @property
    def model(self) -> AutoModelForCausalLM:
        """
        Loads and returns the language model (lazy-loaded).

        Returns:
            AutoModelForCausalLM instance
        """
        if self._model is None:
            self.logger.info(f"Loading model {self.model_name} on {self._device}...")
            try:
                # Determine appropriate dtype based on device and capabilities
                torch_dtype = torch.bfloat16 if self._device == "cuda" else torch.float32

                # Configure quantization for more efficient loading
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_compute_dtype=torch_dtype,
                    bnb_4bit_quant_type="nf4"
                )

                # Load the model with quantization if on CUDA
                if self._device == "cuda":
                    self._model = AutoModelForCausalLM.from_pretrained(
                        self.model_name,
                        device_map=self._device,
                        quantization_config=quantization_config,
                        torch_dtype=torch_dtype
                    )
                else:
                    # Load without quantization for CPU
                    self._model = AutoModelForCausalLM.from_pretrained(
                        self.model_name,
                        device_map=self._device,
                        torch_dtype=torch_dtype
                    )

                self.logger.info(f"Successfully loaded model {self.model_name}")
            except Exception as e:
                error_msg = f"Error loading model: {str(e)}"
                self.logger.error(error_msg)
                from rvandroid.util.exceptions import RVAndroidError
                error = RVAndroidError(error_msg)
                self.error_handler.handle_error(error)
                raise

        return self._model

    @property
    def tokenizer(self) -> AutoTokenizer:
        """
        Loads and returns the tokenizer (lazy-loaded).

        Returns:
            AutoTokenizer instance
        """
        if self._tokenizer is None:
            self.logger.info(f"Loading tokenizer for {self.model_name}...")
            try:
                tokenizer = AutoTokenizer.from_pretrained(self.model_name)

                # If it doesn't have a pad_token, define one
                if tokenizer.pad_token is None:
                    # Try to use a common padding token if it exists in the vocabulary
                    if '<pad>' in tokenizer.get_vocab():
                        tokenizer.pad_token = '<pad>'
                    # Otherwise, use the EOS token
                    else:
                        tokenizer.pad_token = tokenizer.eos_token

                self._tokenizer = tokenizer
                self.logger.info(f"Successfully loaded tokenizer for {self.model_name}")
            except Exception as e:
                error_msg = f"Error loading tokenizer: {str(e)}"
                self.logger.error(error_msg)
                from rvandroid.util.exceptions import RVAndroidError
                error = RVAndroidError(error_msg)
                self.error_handler.handle_error(error)
                raise

        return self._tokenizer

    def generate(self, messages: List[LLMMessage], config = None) -> LLMMessage:
        """
        Generate text based on the input messages synchronously using MCP.

        Args:
            messages: List of LLMMessage objects
            config: Optional MCPConfiguration object

        Returns:
            LLMMessage with the generated response
        """
        # Use provided config or default
        _config = config or self.config
        
        try:
            # Get MCP adapter
            adapter = self._get_adapter()
            
            # Validate request
            if not adapter.validate_request(messages, _config):
                error_msg = "Invalid request for HuggingFace model"
                self.logger.error(error_msg)
                from rvandroid.util.exceptions import RVAndroidError
                error = RVAndroidError(error_msg)
                self.error_handler.handle_error(error)
                raise ValueError(error_msg)
            
            # Format messages using the adapter
            hf_messages = []
            for message in messages:
                content = message.get_text_content()
                hf_messages.append({
                    "role": message.role.value,
                    "content": content
                })
            
            # Format configuration using the adapter
            generation_config = adapter.prepare_config(_config)
            max_new_tokens = generation_config.pop("max_new_tokens", 800)
            
            # Apply chat template to format the messages
            encoded_input = self.tokenizer.apply_chat_template(
                hf_messages, return_tensors="pt", add_generation_prompt=True
            )

            # Create attention mask (all tokens are attended to)
            attention_mask = torch.ones(encoded_input.shape, dtype=torch.long)

            # Move tensors to the correct device
            inputs = encoded_input.to(self._device)
            attention_mask = attention_mask.to(self._device)

            # Get the input length to identify only new tokens later
            input_length = inputs.shape[1]

            # Configure generation parameters
            generation_params = {
                "attention_mask": attention_mask,
                "max_new_tokens": max_new_tokens,
                **generation_config
            }
                
            # Generate text
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs, 
                    **generation_params
                )

            # Extract only the newly generated tokens
            result = self.tokenizer.decode(outputs[0][input_length:], skip_special_tokens=True)

            # Clean up memory
            del inputs, outputs, attention_mask
            if self._device == "cuda":
                torch.cuda.empty_cache()
                
            # Parse response using the adapter
            return adapter.parse_response(result)
            
        except Exception as e:
            error_msg = f"Error generating text: {str(e)}"
            self.logger.error(error_msg)
            from rvandroid.util.exceptions import RVAndroidError
            error = RVAndroidError(error_msg)
            self.error_handler.handle_error(error)
            raise

    def cleanup(self):
        """
        Unloads the model and tokenizer from memory to free resources.
        """
        if hasattr(self, '_model') and self._model is not None:
            del self._model
            self._model = None

        if hasattr(self, '_tokenizer') and self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None

        if self._device == "cuda":
            torch.cuda.empty_cache()

        self.logger.info("Model and tokenizer unloaded, resources freed")

    @staticmethod
    def models() -> List[str]:
        """
        Returns a list of available models.

        Returns:
            List of model identifiers
        """
        return HuggingFaceLLM.MODELS


# Register the model
def register():
    """Register HuggingFace model with the configurator."""
    # Check if this LLM is already registered
    if "huggingface" in ComponentConfigurator._registries.get('llm', {}).get_names():
        # Already registered, skip registration
        return
        
    # Register the LLM
    ComponentConfigurator.register_llm("huggingface", HuggingFaceLLM)
    # Register adapter if needed
    # AdapterRegistry.get_instance().register_adapter("huggingface", HuggingFaceAdapter)