"""
LLM Client for SGLang backend with Qwen3-VL vision model.

Handles multimodal LLM communication using LangChain ChatOpenAI
with SGLang's OpenAI-compatible API.

Based on validation from rvsec-vision-llm benchmark (2,847 tests).
"""

import base64
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.llm.tools.tool_call_parser import (
    normalize_tool_args,
    parse_tool_calls_with_strategy,
    parser_stats,
)
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription


logger = logging.getLogger(__name__)


# Android tools for LangChain tool calling
@tool
def android_click(x: int, y: int, element_description: str = "", reasoning: str = "") -> dict:
    """Click on a UI element at coordinates (x, y).

    Args:
        x: X coordinate in optimized image space (0-704).
        y: Y coordinate in optimized image space (0-1248).
        element_description: Description of element being clicked.
        reasoning: Why this element was chosen.

    Returns:
        Success status with coordinates.
    """
    return {"success": True, "x": x, "y": y, "element_description": element_description}


@tool
def android_type_text(x: int, y: int, text: str, element_description: str = "") -> dict:
    """Type text into a text field at coordinates (x, y).

    Args:
        x: X coordinate of text field.
        y: Y coordinate of text field.
        text: Text to type.
        element_description: Description of the text field.

    Returns:
        Success status with coordinates and text.
    """
    return {"success": True, "x": x, "y": y, "text": text, "element_description": element_description}


@tool
def android_long_click(x: int, y: int, element_description: str = "") -> dict:
    """Long press on element at coordinates (x, y).

    Args:
        x: X coordinate.
        y: Y coordinate.
        element_description: Description of element.

    Returns:
        Success status with coordinates.
    """
    return {"success": True, "x": x, "y": y, "element_description": element_description}


@tool
def android_swipe(direction: str, distance: str = "medium") -> dict:
    """Swipe in a direction.

    Args:
        direction: Swipe direction ('up', 'down', 'left', 'right').
        distance: Swipe distance ('short', 'medium', 'long').

    Returns:
        Success status with swipe parameters.
    """
    return {"success": True, "direction": direction, "distance": distance}


@tool
def android_scroll(direction: str) -> dict:
    """Scroll the screen.

    Args:
        direction: Scroll direction ('up', 'down').

    Returns:
        Success status with direction.
    """
    return {"success": True, "direction": direction}


@tool
def android_back() -> dict:
    """Press the back button.

    Returns:
        Success status.
    """
    return {"success": True, "action": "back"}


@tool
def android_home() -> dict:
    """Press the home button.

    Returns:
        Success status.
    """
    return {"success": True, "action": "home"}


def get_android_tools() -> list:
    """Get list of Android tools for LangChain.

    Returns:
        List of tool objects ready for bind_tools().
    """
    return [
        android_click,
        android_type_text,
        android_long_click,
        android_swipe,
        android_scroll,
        android_back,
        android_home,
    ]


class LLMClient:
    """
    LangChain-based client for SGLang vision LLM inference.

    Wraps ChatOpenAI for SGLang's OpenAI-compatible endpoint.
    Provides tool binding, multimodal message construction,
    and fallback parsing for tool calls.
    """

    def __init__(self, config: RVAgentConfig, prompt_module: Any):
        """Initialize client with configuration.

        Args:
            config: RVAgent configuration with SGLang settings.
            prompt_module: Prompt module with SYSTEM_PROMPT and build_user_message.
        """
        self.config = config
        self.prompt_module = prompt_module
        self.logger = logging.getLogger(__name__)

        # Get LangChain config
        lc_config = config.get_langchain_config()

        # Initialize LangChain ChatOpenAI for SGLang
        self.llm = ChatOpenAI(
            base_url=lc_config["base_url"],
            model=lc_config["model"],
            temperature=lc_config["temperature"],
            max_tokens=lc_config["max_tokens"],
            api_key=lc_config["api_key"],
            model_kwargs=lc_config.get("model_kwargs", {}),
        )

        # Bind tools
        self.tools = get_android_tools()
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # Token tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_calls = 0
        self.total_latency_ms = 0

        self.logger.info(
            f"LLMClient initialized: "
            f"model={lc_config['model']}, "
            f"server={lc_config['base_url']}, "
            f"tools={len(self.tools)}"
        )

    def generate_action(
        self,
        screen_description: ScreenDescription,
        screenshot_b64: str,
        ui_elements_text: str,
        iteration: int = 0,
        last_action_summary: Optional[str] = None,
        temperature: float = None,
        top_p: float = None,
        top_k: int = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Generate action decision using LLM with multimodal input.

        Args:
            screen_description: Parsed screen description
            screenshot_b64: Base64-encoded optimized screenshot
            ui_elements_text: Formatted UI elements text
            iteration: Current iteration number
            last_action_summary: Summary of last executed action
            temperature: Override temperature (uses config default if None)
            top_p: Override top_p (uses config default if None)
            top_k: Override top_k (unused in ChatOpenAI)
            retry_count: Current retry count for progressive sampling

        Returns:
            Dictionary with:
            - response: AIMessage with tool calls
            - tokens_input: Input tokens consumed
            - tokens_output: Output tokens generated
            - time_ms: LLM latency in milliseconds
            - success: Whether invocation succeeded
            - parser_strategy: Strategy used to extract tool calls
        """
        self.logger.info(f"Generating action (iteration={iteration}, retry={retry_count})")

        start_time = time.perf_counter()

        try:
            # Build messages
            messages = self._build_messages(
                ui_elements_text=ui_elements_text,
                screenshot_b64=screenshot_b64,
                iteration=iteration,
                last_action_summary=last_action_summary
            )

            self.logger.debug(f"Built {len(messages)} messages")

            # Invoke LLM
            response = self.llm_with_tools.invoke(messages)
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Extract token usage
            tokens_input, tokens_output = self._extract_token_usage(response)

            # Extract tool calls with fallback parsing
            tool_calls, parser_strategy = self._extract_tool_calls(response)

            # Inject tool calls into response if found via parser
            if tool_calls and not response.tool_calls:
                response.tool_calls = tool_calls

            # Update tracking
            self.total_input_tokens += tokens_input
            self.total_output_tokens += tokens_output
            self.total_calls += 1
            self.total_latency_ms += latency_ms

            self.logger.info(
                f"LLM response: "
                f"tool_calls={len(tool_calls)}, "
                f"strategy={parser_strategy}, "
                f"tokens={tokens_input}+{tokens_output}, "
                f"latency={latency_ms:.0f}ms"
            )

            return {
                "response": response,
                "tokens_input": tokens_input,
                "tokens_output": tokens_output,
                "time_ms": latency_ms,
                "success": True,
                "parser_strategy": parser_strategy,
            }

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self.logger.error(f"LLM invocation failed: {e}", exc_info=True)

            return {
                "response": None,
                "tokens_input": 0,
                "tokens_output": 0,
                "time_ms": latency_ms,
                "success": False,
                "error": str(e),
                "parser_strategy": "none",
            }

    def _build_messages(
        self,
        ui_elements_text: str,
        screenshot_b64: str,
        iteration: int,
        last_action_summary: Optional[str]
    ) -> List:
        """
        Build LangChain messages with multimodal content.

        Args:
            ui_elements_text: Formatted UI elements
            screenshot_b64: Base64-encoded screenshot
            iteration: Current iteration
            last_action_summary: Last action summary

        Returns:
            List of LangChain messages
        """
        # System prompt from module
        system_prompt = self.prompt_module.SYSTEM_PROMPT

        # Build user message
        state_info = {
            "ui_elements": [ui_elements_text],
            "last_action": last_action_summary,
            "iteration": iteration,
        }
        user_text = self.prompt_module.build_user_message(state_info)

        # Create multimodal human message
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=[
                    {"type": "text", "text": user_text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{screenshot_b64}",
                        },
                    },
                ]
            ),
        ]

        return messages

    def _extract_token_usage(self, response: AIMessage) -> tuple[int, int]:
        """
        Extract token usage from response metadata.

        Args:
            response: AIMessage from LLM

        Returns:
            Tuple of (input_tokens, output_tokens)
        """
        input_tokens = 0
        output_tokens = 0

        if hasattr(response, "response_metadata"):
            meta = response.response_metadata
            if "token_usage" in meta:
                usage = meta["token_usage"]
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
            elif "usage" in meta:
                usage = meta["usage"]
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)

        return input_tokens, output_tokens

    def _extract_tool_calls(self, response: AIMessage) -> tuple[list[dict], str]:
        """
        Extract tool calls from LLM response.

        Uses native tool calls if available, otherwise falls back to
        parsing tool calls from text content.

        Args:
            response: AIMessage from LLM

        Returns:
            Tuple of (list of tool call dicts, parser_strategy used)
        """
        tool_calls = []
        parser_strategy = "none"

        # Try native tool calls first
        if hasattr(response, "tool_calls") and response.tool_calls:
            parser_strategy = "native"
            for tc in response.tool_calls:
                raw_args = tc.get("args", tc.get("arguments", {}))
                normalized_args = normalize_tool_args(raw_args) if isinstance(raw_args, dict) else {}
                tool_calls.append({
                    "name": tc.get("name", tc.get("function", {}).get("name")),
                    "args": normalized_args,
                    "id": tc.get("id"),
                })
            self.logger.debug(f"Native tool calls: {len(tool_calls)}")

        # Fallback: parse from text content
        if not tool_calls and response.content:
            parsed, fallback_strategy = parse_tool_calls_with_strategy(response.content)
            if parsed:
                tool_calls = parsed
                parser_strategy = fallback_strategy
            self.logger.debug(f"Fallback parsed: {len(parsed)} via {fallback_strategy}")

        return tool_calls, parser_strategy

    def get_stats(self) -> dict:
        """Get client statistics.

        Returns:
            Dictionary with token usage and call statistics.
        """
        return {
            "total_calls": self.total_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_latency_ms": self.total_latency_ms,
            "avg_latency_ms": self.total_latency_ms / self.total_calls if self.total_calls > 0 else 0,
            "parser_stats": parser_stats.get_stats(),
        }

    def reset_stats(self):
        """Reset client statistics."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_calls = 0
        self.total_latency_ms = 0
        parser_stats.reset()

    def cleanup(self):
        """Cleanup resources."""
        self.logger.info("LLMClient cleanup complete")
