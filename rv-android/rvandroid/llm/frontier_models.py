from typing import List, Dict

from anthropic import Anthropic

from rvandroid.llm.llm import LanguageModel


class FrontierModel(LanguageModel):
    """
    Represents a language model that uses a frontier approach for generating text.
    """

    def __init__(self, model_name: str):
        super().__init__(model_name)
        self._client: Anthropic | None = None

    @property
    def client(self):
        if not self._client:
            self._client = Anthropic()
        return self._client

    def generate(self, messages: List[Dict[str, str]], max_new_tokens: int = 800):
        """
        Generates text based on the given prompt.
        """
        message = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=max_new_tokens,
            messages=[
                {"role": "user", "content": "Hello, Claude"}
            ]
        )
        return message.content

    def clean(self):
        self._client = None

    @staticmethod
    def models() -> List[str]:
        return ["Claude 3.5 sonnet"]

    def __str__(self):
        return f"{self.model_name}"
