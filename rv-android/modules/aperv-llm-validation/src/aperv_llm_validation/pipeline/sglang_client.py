"""HTTP client for the OpenAI-compatible SGLang inference server.

Wraps the OpenAI Python client with retry logic and health checking.
Replicates the interface of Java's SglangClient (commit b2852dd).
"""

from __future__ import annotations

import logging
import time

import httpx
from openai import OpenAI

from aperv_llm_validation.constants import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_RETRIES,
    DEFAULT_SGLANG_URL,
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)


class SglangClient:
    """Client for OpenAI-compatible SGLang inference server.

    Supports multimodal messages (image + text) and tool calling.
    Retries on timeout/connection errors with exponential backoff.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_SGLANG_URL,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        retries: int = DEFAULT_RETRIES,
    ):
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        self.retries = retries

        self._client = OpenAI(
            base_url=base_url,
            api_key="not-needed",
            timeout=float(timeout_seconds),
        )

    def call(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        extra_body: dict | None = None,
    ) -> dict:
        """Send a chat completion request and return the raw response as a dict.

        Retries up to self.retries times with exponential backoff on
        timeout or connection errors.
        """
        last_error: Exception | None = None

        for attempt in range(self.retries):
            try:
                kwargs: dict = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                }
                if tools:
                    kwargs["tools"] = tools
                if extra_body:
                    kwargs["extra_body"] = extra_body

                response = self._client.chat.completions.create(**kwargs)
                return response.model_dump()

            except Exception as e:
                last_error = e
                if attempt < self.retries - 1:
                    wait = 2**attempt
                    logger.warning(
                        "SGLang request failed (attempt %d/%d): %s. Retrying in %ds...",
                        attempt + 1,
                        self.retries,
                        e,
                        wait,
                    )
                    time.sleep(wait)

        raise last_error  # type: ignore[misc]

    def health_check(self) -> bool:
        """Check if the SGLang server is reachable by querying GET /v1/models.

        Returns True if the server responds, False otherwise.
        """
        try:
            url = f"{self.base_url}/models"
            response = httpx.get(url, timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
