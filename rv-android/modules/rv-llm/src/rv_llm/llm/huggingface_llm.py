# rvandroid/llm/huggingface_llm.py
"""HuggingFace language model implementation."""

import time
from typing import List, Optional

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.config.llm_config import LLMConfig
from rv_llm.llm.data_structures import LLMMessage, LLMResponse
from rv_llm.llm.language_model import LanguageModel


class HuggingFaceLLM(LanguageModel):
    """
    A specialized language model integration for HuggingFace transformers models.

    ### Architectural Decisions:
    - Implements a highly optimized integration with Hugging Face transformers library
    - Supports quantized model loading for efficient memory usage
    - Provides configurable device placement (CPU/CUDA)
    - Enables lazy loading of models to minimize resource consumption
    - Uses optimized generation parameters for best performance
    - Implements efficient token management for context handling

    ### Role in the System:
    - Acts as a concrete implementation of the LanguageModel abstract base class
    - Facilitates local AI-driven testing using high-quality open models
    - Supports a wide range of HuggingFace transformer models
    - Handles model initialization, tokenization, and generation
    - Tracks performance metrics for system evaluation
    - Provides device-aware execution for optimal performance

    ### Key Considerations:
    - Manages complex model initialization and resource allocation
    - Handles memory constraints through quantization options
    - Implements device-appropriate dtype selection and memory optimizations
    - Tracks detailed performance metrics for generation analysis
    - Provides consistent interface across model implementations
    """
    NAME = "huggingface"

    # Available model definitions
    LLAMA = "meta-llama/Meta-Llama-3.1-8B-Instruct"
    DEEPSEEK = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"  # "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"
    GEMMA = "google/gemma-3-4b-it"
    QWEN = "Qwen/Qwen2.5-3B-Instruct"
    PHI = "microsoft/Phi-3.5-mini-instruct"
    GRANITE = "ibm-granite/granite-3.1-8b-instruct"
    FALCON = "tiiuae/Falcon3-3B-Instruct"
    MISTRAL = "mistralai/Mistral-7B-Instruct-v0.3"

    # Default set of models to use (can be extended/modified via configuration)
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
        super().__init__(model_name, **kwargs)

        # Set up model properties
        self._model = None
        self._tokenizer = None
        self._device = device

        # Store device in kwargs for consistency
        self.kwargs["device"] = device

        # Setup logging and error handling
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "rv_llm.llm.huggingface",
            {CONTEXT_COMPONENT: self.__class__.__name__}
        )
        self.error_handler = ErrorHandler.get_instance()

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
                from rv_android_core.util.error.exceptions import RVAndroidError
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
                from rv_android_core.util.error.exceptions import RVAndroidError
                error = RVAndroidError(error_msg)
                self.error_handler.handle_error(error)
                raise

        return self._tokenizer

    def generate(self, messages: List[LLMMessage], config: Optional[LLMConfig] = None) -> LLMResponse:
        """
        Generate text based on the input messages.

        Args:
            messages: List of LLMMessage objects
            config: Optional LLMConfig object

        Returns:
            LLMResponse containing the generated text and performance metrics
        """
        # Use provided config or default
        _config = config or self.default_config

        try:
            # Track performance metrics
            start_time = time.time()
            load_start_time = start_time

            # Format messages for HuggingFace
            hf_messages = []
            for message in messages:
                content = message.get_text_content()
                hf_messages.append({
                    "role": message.role.value,
                    "content": content
                    # "content": message.to_message_dict()
                })

            # Extract generation parameters from config
            max_new_tokens = _config.max_tokens if _config and _config.max_tokens is not None else 1000
            temperature = _config.temperature if _config and _config.temperature is not None else 0.2
            top_p = _config.kwargs.get("top_p", 1.0)

            # Ensure model and tokenizer are loaded
            _ = self.model  # This triggers lazy loading
            _ = self.tokenizer

            # Record model load time
            load_end_time = time.time()
            load_duration = (load_end_time - load_start_time) * 1000  # Convert to ms

            # Start tokenization timer
            tokenization_start = time.time()

            # Apply chat template to format the messages
            encoded_input = self.tokenizer.apply_chat_template(
                hf_messages, return_tensors="pt", add_generation_prompt=True
            )

            # Get the input length to identify only new tokens later
            input_length = encoded_input.shape[1]
            input_tokens = input_length

            # Create attention mask (all tokens are attended to)
            attention_mask = torch.ones(encoded_input.shape, dtype=torch.long)

            # Move tensors to the correct device
            inputs = encoded_input.to(self._device)
            attention_mask = attention_mask.to(self._device)

            # End tokenization timer
            tokenization_end = time.time()
            input_tokens_duration = (tokenization_end - tokenization_start) * 1000  # Convert to ms

            # Configure generation parameters
            generation_params = {
                "attention_mask": attention_mask,
                "max_new_tokens": max_new_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "do_sample": temperature > 0.001,  # Only use sampling if temperature is non-zero
            }

            # Start generation timer
            generation_start = time.time()

            # Generate text
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    **generation_params
                )

            # End generation timer
            generation_end = time.time()
            output_tokens_duration = (generation_end - generation_start) * 1000  # Convert to ms

            # Extract only the newly generated tokens
            output_tokens = outputs.shape[1] - input_length
            result = self.tokenizer.decode(outputs[0][input_length:], skip_special_tokens=True)

            # Clean up memory
            del inputs, outputs, attention_mask
            if self._device == "cuda":
                torch.cuda.empty_cache()

            # Calculate total duration
            end_time = time.time()
            total_duration = (end_time - start_time) * 1000  # Convert to ms

            # Create and return response with performance metrics
            response = LLMResponse(
                content=result,
            )

            # Add performance metrics
            response.done_reason = "stop"
            response.total_duration = total_duration
            response.load_duration = load_duration
            response.input_tokens = input_tokens
            response.input_tokens_duration = input_tokens_duration
            response.output_tokens = output_tokens
            response.output_tokens_duration = output_tokens_duration

            return response

        except Exception as e:
            error_msg = f"Error generating text: {str(e)}"
            self.logger.error(error_msg)
            from rv_android_core.util.error.exceptions import RVAndroidError
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

    @property
    def default_config(self) -> LLMConfig:
        """
        Returns the default configuration for this model.
        
        Returns:
            LLMConfig with default settings
        """
        return LLMConfig(
            model_type=self.NAME,
            model_name=self.model_name,
            max_tokens=1000,
            temperature=0.2,
            top_p=1.0,
            top_k=40
        )

# Legacy register function removed - now using LLMFactory for component creation
