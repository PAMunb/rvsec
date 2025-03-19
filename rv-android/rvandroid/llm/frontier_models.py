# rvandroid/llm/frontier_models.py
import json
import logging
import os
from typing import List, Dict, Optional

import boto3
import google.generativeai as genai
import openai
# Import model providers
from anthropic import Anthropic

from rvandroid.llm.llm import LanguageModel

# Configure logger
logger = logging.getLogger(__name__)


class FrontierModel(LanguageModel):
    """
    Language model implementation that uses frontier models like Claude, ChatGPT, Gemini, etc.
    Handles initialization and interaction with various API providers.
    """

    # Available frontier models with consistent versioning
    CLAUDE_SONNET = "claude-3-5-sonnet-20241022"
    CLAUDE_OPUS = "claude-3-opus-20240229"
    CLAUDE_HAIKU = "claude-3-haiku-20240307"

    GPT_4 = "gpt-4-turbo-2024-04-09"
    GPT_3_5 = "gpt-3.5-turbo-0125"

    GEMINI_PRO = "gemini-pro"
    GEMINI_ULTRA = "gemini-ultra"

    NOVA_ULTRA = "anthropic.claude-3-ultra-20240229"
    NOVA_SONNET = "anthropic.claude-3-sonnet-20240229"

    # Group models by provider
    ANTHROPIC_MODELS = [CLAUDE_SONNET, CLAUDE_OPUS, CLAUDE_HAIKU]
    OPENAI_MODELS = [GPT_4, GPT_3_5]
    GOOGLE_MODELS = [GEMINI_PRO, GEMINI_ULTRA]
    AMAZON_MODELS = [NOVA_ULTRA, NOVA_SONNET]

    # All models
    MODELS = ANTHROPIC_MODELS + OPENAI_MODELS + GOOGLE_MODELS + AMAZON_MODELS

    def __init__(self, model_name: str, provider: Optional[str] = None, api_key: Optional[str] = None, **kwargs):
        """
        Initialize the FrontierModel with a model name and provider.

        Args:
            model_name: Name of the model to use
            provider: Provider name ('anthropic', 'openai', 'google', 'amazon')
                     If None, provider will be inferred from model_name
            api_key: API key for the service (optional, can also use environment variables)
            **kwargs: Additional model configuration parameters
        """
        super().__init__(model_name)

        # Determine provider if not specified
        if provider is None:
            provider = self._infer_provider(model_name)

        self.provider = provider
        self.api_key = api_key
        self._client = None
        self.kwargs = kwargs
        self.logger = logger

        # Log initialization
        self.logger.info(f"Initializing FrontierModel with {provider} provider and model {model_name}")

    def _infer_provider(self, model_name: str) -> str:
        """
        Infer the provider from the model name.

        Args:
            model_name: Name of the model

        Returns:
            Provider name

        Raises:
            ValueError: If provider can't be inferred
        """
        if model_name in self.ANTHROPIC_MODELS:
            return "anthropic"
        elif model_name in self.OPENAI_MODELS:
            return "openai"
        elif model_name in self.GOOGLE_MODELS:
            return "google"
        elif model_name in self.AMAZON_MODELS:
            return "amazon"
        else:
            # Try to match by prefix
            if model_name.startswith("claude"):
                return "anthropic"
            elif model_name.startswith("gpt"):
                return "openai"
            elif model_name.startswith("gemini"):
                return "google"
            elif model_name.startswith("anthropic."):
                return "amazon"

            raise ValueError(f"Could not infer provider for model: {model_name}")

    @property
    def client(self):
        """
        Get or initialize the appropriate client for the provider.

        Returns:
            API client

        Raises:
            ValueError: If client initialization fails
        """
        if self._client is not None:
            return self._client

        # Initialize client based on provider
        if self.provider == "anthropic":
            api_key = self.api_key or os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("Anthropic API key not provided")

            self._client = Anthropic(api_key=api_key)

        elif self.provider == "openai":
            api_key = self.api_key or os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key not provided")

            self._client = openai.OpenAI(api_key=api_key)

        elif self.provider == "google":
            api_key = self.api_key or os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("Google API key not provided")

            genai.configure(api_key=api_key)
            self._client = genai

        elif self.provider == "amazon":
            # AWS credentials are typically in environment variables or config files
            region = self.kwargs.get("region") or os.environ.get("AWS_REGION", "us-east-1")
            self._client = boto3.client(
                service_name='bedrock-runtime',
                region_name=region
            )
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

        return self._client

    def generate(self, messages: List[Dict[str, str]], max_new_tokens: int = 800) -> str:
        """
        Generate text based on the input messages.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_new_tokens: Maximum number of tokens to generate

        Returns:
            Generated text

        Raises:
            Exception: If generation fails
        """
        try:
            # Call appropriate provider's generation method
            if self.provider == "anthropic":
                return self._generate_anthropic(messages, max_new_tokens)
            elif self.provider == "openai":
                return self._generate_openai(messages, max_new_tokens)
            elif self.provider == "google":
                return self._generate_google(messages, max_new_tokens)
            elif self.provider == "amazon":
                return self._generate_amazon(messages, max_new_tokens)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        except Exception as e:
            self.logger.error(f"Error generating text with {self.provider}: {e}")
            raise

    def _generate_anthropic(self, messages: List[Dict[str, str]], max_new_tokens: int) -> str:
        """
        Generate text using Anthropic's Claude models.

        Args:
            messages: List of message dictionaries
            max_new_tokens: Maximum number of tokens to generate

        Returns:
            Generated text
        """
        temperature = self.kwargs.get("temperature", 0.7)

        try:
            message = self.client.messages.create(
                model=self.model_name,
                max_tokens=max_new_tokens,
                temperature=temperature,
                messages=messages
            )
            return message.content[0].text
        except Exception as e:
            self.logger.error(f"Anthropic API error: {e}")
            raise

    def _generate_openai(self, messages: List[Dict[str, str]], max_new_tokens: int) -> str:
        """
        Generate text using OpenAI models.

        Args:
            messages: List of message dictionaries
            max_new_tokens: Maximum number of tokens to generate

        Returns:
            Generated text
        """
        temperature = self.kwargs.get("temperature", 0.7)

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_new_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            raise

    def _generate_google(self, messages: List[Dict[str, str]], max_new_tokens: int) -> str:
        """
        Generate text using Google Gemini models.

        Args:
            messages: List of message dictionaries
            max_new_tokens: Maximum number of tokens to generate

        Returns:
            Generated text
        """
        temperature = self.kwargs.get("temperature", 0.7)

        try:
            # Adapt messages format for Gemini
            gemini_messages = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                gemini_messages.append({"role": role, "parts": [{"text": msg["content"]}]})

            model = self.client.GenerativeModel(
                model_name=self.model_name,
                generation_config={"temperature": temperature}
            )

            response = model.generate_content(
                gemini_messages,
                generation_config={"max_output_tokens": max_new_tokens}
            )

            return response.text
        except Exception as e:
            self.logger.error(f"Google API error: {e}")
            raise

    def _generate_amazon(self, messages: List[Dict[str, str]], max_new_tokens: int) -> str:
        """
        Generate text using Amazon Bedrock models.

        Args:
            messages: List of message dictionaries
            max_new_tokens: Maximum number of tokens to generate

        Returns:
            Generated text
        """
        temperature = self.kwargs.get("temperature", 0.7)

        try:
            # Format request body based on underlying model provider
            if self.model_name.startswith("anthropic."):
                # Format for Claude models on Bedrock
                request_body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_new_tokens,
                    "temperature": temperature,
                    "messages": messages
                }
            else:
                # Generic fallback (this may need customization for other model types)
                request_body = {
                    "max_tokens": max_new_tokens,
                    "temperature": temperature,
                    "messages": messages
                }

            # Invoke the model
            response = self.client.invoke_model(
                modelId=self.model_name,
                body=json.dumps(request_body)
            )

            # Parse response
            response_body = json.loads(response['body'].read().decode('utf-8'))

            # Extract content based on model provider
            if self.model_name.startswith("anthropic."):
                return response_body.get('content', [])[0].get('text', '')

            # Generic fallback (extract 'text' or similar field)
            return response_body.get('text', response_body.get('generated_text', ''))

        except Exception as e:
            self.logger.error(f"Amazon Bedrock API error: {e}")
            raise

    def clean(self) -> None:
        """
        Clean up resources by clearing client references.
        """
        self._client = None
        self.logger.info(f"Released {self.provider} client resources")

    @staticmethod
    def models() -> List[str]:
        """
        Returns available models.

        Returns:
            List of model identifiers
        """
        return FrontierModel.MODELS