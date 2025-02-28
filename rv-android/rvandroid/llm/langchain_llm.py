# rvandroid/llm/langchain_llm.py
from typing import List, Dict, Optional
import logging

from langchain.llms import BaseLLM
from langchain.chat_models import ChatOpenAI, ChatAnthropic
from langchain.schema import SystemMessage, HumanMessage
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.llms import HuggingFacePipeline, Ollama

from rvandroid.llm.llm import LanguageModel

logger = logging.getLogger(__name__)


class LangchainLLM(LanguageModel):
    """
    Language model implementation using LangChain for generating text.
    Provides a unified interface to different LLM providers through LangChain.
    """

    # Models available for LangChain
    LLAMA = "llama3.2:3b"
    PHI = "microsoft/Phi-3.5-mini-instruct"
    QWEN = "Qwen/Qwen2.5-3B-Instruct"
    MISTRAL = "mistralai/Mistral-7B-Instruct-v0.3"
    CLAUDE = "claude-3-5-sonnet-20241022"
    GPT_4 = "gpt-4-turbo-2024-04-09"

    # Group by provider
    LOCAL_MODELS = [PHI, QWEN, MISTRAL]
    OLLAMA_MODELS = [LLAMA]
    OPENAI_MODELS = [GPT_4]
    ANTHROPIC_MODELS = [CLAUDE]

    # All models
    MODELS = LOCAL_MODELS + OLLAMA_MODELS + OPENAI_MODELS + ANTHROPIC_MODELS

    def __init__(
            self,
            model_name: str,
            provider: str = "ollama",
            base_url: str = "http://localhost:11434",
            api_key: Optional[str] = None
    ):
        """
        Initialize LangchainLLM with a model name and provider.

        Args:
            model_name: Name of the model
            provider: Provider for the model ('ollama', 'huggingface', 'openai', 'anthropic')
            base_url: Base URL for API (for Ollama)
            api_key: API key for cloud providers (for OpenAI, Anthropic)
        """
        super().__init__(model_name)
        self.provider = provider
        self.base_url = base_url
        self.api_key = api_key
        self._llm = None
        self._chain = None
        self.logger = logger

    @property
    def llm(self) -> BaseLLM:
        """
        Returns (or initializes) the LangChain LLM instance.

        Returns:
            LangChain LLM instance
        """
        if self._llm is None:
            self.logger.info(f"Initializing LangChain with provider {self.provider}")

            if self.provider == "ollama":
                self._llm = Ollama(model=self.model_name, base_url=self.base_url)

            elif self.provider == "huggingface":
                import torch
                from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM

                # Load the model and tokenizer
                tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    device_map="auto",
                    torch_dtype=torch.bfloat16
                )

                # Create the pipeline
                hf_pipeline = pipeline(
                    task="text-generation",
                    model=model,
                    tokenizer=tokenizer,
                    max_new_tokens=800
                )

                self._llm = HuggingFacePipeline(pipeline=hf_pipeline)

            elif self.provider == "openai":
                if not self.api_key:
                    raise ValueError("API key required for OpenAI")

                self._llm = ChatOpenAI(
                    model_name=self.model_name,
                    openai_api_key=self.api_key,
                    temperature=0.7
                )

            elif self.provider == "anthropic":
                if not self.api_key:
                    raise ValueError("API key required for Anthropic")

                self._llm = ChatAnthropic(
                    model_name=self.model_name,
                    anthropic_api_key=self.api_key,
                    temperature=0.7
                )

            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            self.logger.info(f"Successfully initialized LangChain LLM with {self.provider}")

        return self._llm

    @property
    def chain(self):
        """
        Returns (or initializes) the LangChain chain for chat completion.

        Returns:
            LangChain chain instance
        """
        if self._chain is None:
            # Create a prompt template for chat
            prompt = ChatPromptTemplate.from_messages([
                ("system", "{system}"),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{human}")
            ])

            self._chain = LLMChain(llm=self.llm, prompt=prompt)

        return self._chain

    def generate(self, messages: List[Dict[str, str]], max_new_tokens: int = 800) -> str:
        """
        Generates text based on the given messages.

        Args:
            messages: List of message dictionaries
            max_new_tokens: Maximum number of tokens to generate

        Returns:
            Generated text
        """
        try:
            # Extract system and user messages
            system_content = ""
            chat_history = []
            human_content = ""

            for msg in messages:
                if msg["role"] == "system":
                    system_content = msg["content"]
                elif msg["role"] == "user":
                    human_content = msg["content"]
                elif msg["role"] == "assistant":
                    # Add previous turn to chat history
                    chat_history.append(HumanMessage(content=human_content))
                    chat_history.append(SystemMessage(content=msg["content"]))
                    human_content = ""

            # Generate response using LangChain
            response = self.chain.run(
                system=system_content,
                chat_history=chat_history,
                human=human_content
            )

            return response

        except Exception as e:
            self.logger.error(f"Error generating text with LangChain: {e}")
            raise

    def clean(self) -> None:
        """
        Clean up resources.
        """
        self._llm = None
        self._chain = None
        self.logger.info("LangChain resources released")

    @staticmethod
    def models() -> List[str]:
        """
        Returns available models.

        Returns:
            List of model identifiers
        """
        return LangchainLLM.MODELS