# rvandroid/llm/langchain_llm.py
from typing import List, Dict

from langchain.llms import BaseLLM
from langchain.schema import SystemMessage, HumanMessage
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.llms import HuggingFacePipeline, Ollama

from rvandroid.llm.llm import LanguageModel


class LangchainLLM(LanguageModel):
    """
    A language model implementation using LangChain for generating text.
    Supports using HuggingFace models or Ollama models via LangChain's interfaces.
    """
    
    # Models available for LangChain
    LLAMA = "llama3.2:3b"
    PHI = "microsoft/Phi-3.5-mini-instruct"
    QWEN = "Qwen/Qwen2.5-3B-Instruct"
    MISTRAL = "mistralai/Mistral-7B-Instruct-v0.3"
    
    MODELS = [LLAMA, PHI, QWEN, MISTRAL]
    
    def __init__(self, model_name: str, provider: str = "ollama", base_url: str = "http://localhost:11434"):
        """
        Initialize LangchainLLM with a model name and provider.
        
        Args:
            model_name: Name of the model
            provider: Provider for the model ('ollama' or 'huggingface')
            base_url: Base URL for Ollama API (if using Ollama)
        """
        super().__init__(model_name)
        self.provider = provider
        self.base_url = base_url
        self._llm = None
        self._chain = None
    
    @property
    def llm(self) -> BaseLLM:
        """
        Returns (or initializes) the LangChain LLM instance.
        """
        if self._llm is None:
            if self.provider == "ollama":
                self._llm = Ollama(model=self.model_name, base_url=self.base_url)
            elif self.provider == "huggingface":
                import torch
                from transformers import pipeline
                
                # Load the model pipeline
                hf_pipeline = pipeline(
                    task="text-generation",
                    model=self.model_name,
                    device_map="auto",
                    torch_dtype=torch.bfloat16,
                    max_new_tokens=800
                )
                
                self._llm = HuggingFacePipeline(pipeline=hf_pipeline)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        return self._llm
    
    @property
    def chain(self):
        """
        Returns (or initializes) the LangChain chain for chat completion.
        """
        if self._chain is None:
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
    
    def clean(self):
        """
        Clean up resources.
        """
        self._llm = None
        self._chain = None
    
    @staticmethod
    def models() -> List[str]:
        """
        Returns available models.
        """
        return LangchainLLM.MODELS
    
    def __str__(self):
        return f"Langchain({self.provider}): {self.model_name}"