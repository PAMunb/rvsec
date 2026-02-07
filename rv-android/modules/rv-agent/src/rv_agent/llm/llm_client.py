"""
LLM client for vision-based action generation.

Handles multimodal LLM communication using LangChain with SGLang backend.
"""

import base64
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.domain.exceptions import LLMError
from rv_agent.llm.tools.sglang_tools import get_android_tools
from rv_agent.llm.tools.tool_call_parser import (
    normalize_tool_args,
    parse_tool_calls_with_strategy,
    parser_stats,
)
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription


logger = logging.getLogger(__name__)


class LLMClient:
    """
    Vision LLM client for action generation using SGLang backend.

    Wraps LangChain ChatOpenAI for multimodal inference with tool calling.
    Handles message construction, tool binding, and response parsing.

    ### Key Design Decisions:

    1. HYBRID TOOL CALL PARSING
       Problem: SGLang doesn't have official tool calling support for Qwen3-VL.
       The behavior is non-deterministic: ~50% native tool_calls, ~50% XML in content.
       Solution: Try native tool_calls first, then parse from content if empty.
       Supports multiple formats: XML (Hermes), JSON array, JSON object, markdown.

    2. STATELESS LLM CONTEXT
       Problem: Full conversation history would exceed context limits quickly.
       Solution: Build fresh messages each iteration from summaries (~2500 tokens).
       No conversation memory - each call is independent with summarized context.

    3. COORDINATE NORMALIZATION
       The LLM returns coordinates in Qwen3-VL's [0, 1000) normalized space.
       ActionNormalizer (separate component) converts to device pixels.
       This separation keeps LLMClient focused on LLM interaction.

    4. NAVIGATION HINTS
       WTG (Window Transition Graph) analysis provides hints about which actions
       lead to unvisited screens. These hints are included in the user message
       to guide the LLM toward unexplored app areas.

    ### Integration Points:
    - Receives configuration via RVAgentConfig
    - Uses prompt module for message construction
    - Returns raw tool calls for ActionNormalizer
    - Reports metrics to caller
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
        llm_kwargs = {
            "base_url": lc_config["base_url"],
            "model": lc_config["model"],
            "temperature": lc_config["temperature"],
            "max_tokens": lc_config["max_tokens"],
            "top_p": lc_config.get("top_p", 0.95),
            "api_key": lc_config["api_key"],
        }
        # Add extra_body for top_k (SGLang supports, OpenAI doesn't)
        if "extra_body" in lc_config:
            llm_kwargs["extra_body"] = lc_config["extra_body"]
        self.llm = ChatOpenAI(**llm_kwargs)

        # Bind tools
        self.tools = get_android_tools()
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # Token tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_calls = 0
        self.total_latency_ms = 0

        # Extract top_k for logging
        top_k = lc_config.get("extra_body", {}).get("top_k", -1)

        self.logger.info(
            f"LLMClient initialized: "
            f"model={lc_config['model']}, "
            f"server={lc_config['base_url']}, "
            f"temperature={lc_config['temperature']}, "
            f"top_p={lc_config.get('top_p')}, "
            f"top_k={top_k}, "
            f"tools={len(self.tools)}"
        )

    def generate_action(
        self,
        screen_description: ScreenDescription,
        screenshot_b64: str,
        ui_elements_text: str,
        iteration: int = 0,
        last_action_summary: Optional[str] = None,
        navigation_hint: str = "",
        screen_line: str = "",
        temperature: float = None,
        top_p: float = None,
        top_k: int = None,
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Generate action decision using LLM with multimodal input.

        Args:
            screen_description: Parsed screen description
            screenshot_b64: Base64-encoded optimized screenshot
            ui_elements_text: Formatted UI elements text
            iteration: Current iteration number
            last_action_summary: Summary of last executed action
            navigation_hint: Optional navigation guidance from WTG analysis
            screen_line: Screen info (activity, coverage, visit count)
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
        self.logger.info(
            f"Generating action (iteration={iteration}, retry={retry_count})"
        )

        start_time = time.perf_counter()

        try:
            # Build messages
            messages = self._build_messages(
                ui_elements_text=ui_elements_text,
                screenshot_b64=screenshot_b64,
                iteration=iteration,
                last_action_summary=last_action_summary,
                navigation_hint=navigation_hint,
                screen_line=screen_line,
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

        except LLMError:
            raise
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self.logger.error(f"LLM invocation failed: {e}", exc_info=True)
            raise LLMError(f"LLM invocation failed: {e}") from e

    def _build_messages(
        self,
        ui_elements_text: str,
        screenshot_b64: str,
        iteration: int,
        last_action_summary: Optional[str],
        navigation_hint: str = "",
        screen_line: str = "",
    ) -> List:
        """
        Build LangChain messages with multimodal content.

        Args:
            ui_elements_text: Formatted UI elements
            screenshot_b64: Base64-encoded screenshot
            iteration: Current iteration
            last_action_summary: Last action summary
            navigation_hint: Optional navigation guidance from WTG
            screen_line: Screen info (activity, coverage, visit count)

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

        user_text = self.prompt_module.build_user_message(
            state_info,
            navigation_hint=navigation_hint,
            screen_line=screen_line,
        )

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
                normalized_args = (
                    normalize_tool_args(raw_args) if isinstance(raw_args, dict) else {}
                )
                tool_calls.append(
                    {
                        "name": tc.get("name", tc.get("function", {}).get("name")),
                        "args": normalized_args,
                        "id": tc.get("id"),
                    }
                )
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
            "avg_latency_ms": (
                self.total_latency_ms / self.total_calls if self.total_calls > 0 else 0
            ),
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
