from ollama import ChatResponse, Client
from typing import List, Dict

from rvandroid.llm.llm import LanguageModel


class OllamaLLM(LanguageModel):
    LLAMA = "llama3.2:3b" # "llama3.2:1b"
    DEEPSEEK = "deepseek-r1:1.5B"
    QWEN = "qwen2.5:3b"
    PHI = "phi3.5:3.8b"
    GRANITE = "granite3.1-dense:8b"
    FALCON = "falcon3:3b"
    NOMIC_EMBED_TEXT = "nomic-embed-text:latest"

    MODELS = [LLAMA, DEEPSEEK, QWEN, PHI, GRANITE, FALCON]

    def __init__(self, model_name: str, base_url="http://localhost:11434"):     
        super().__init__(model_name)        
        self.base_url = base_url    
        self._client: Client | None = None          

    @property
    def client(self):
        if not self._client:
            self._client = Client(self.base_url)
            self._client.pull(self.model_name)
        return self._client

    def generate(self, messages: List[Dict[str, str]]):
        response: ChatResponse = self.client.chat(
            model=self.model_name, 
            messages=messages,
            keep_alive=True
        )
        # return response['message']['content']
        return response.message.content
            
    def clean(self):           
        self._client = None

    @staticmethod    
    def models() -> List[str]:
        return OllamaLLM.MODELS

    def __str__(self):
        return f"Ollama: {self.model_name}"
    