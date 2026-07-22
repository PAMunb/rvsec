"""
LLM interaction management for agent decision-making.

Handles multimodal LLM communication with tool calling support,
response parsing, and token tracking.
"""

import time
import logging
import httpx
from typing import Dict, List, Any, Optional

import torch
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
from qwen_vl_utils import process_vision_info

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.language_models import BaseChatModel

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.llm.tools import json_parser
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription


class LLMClient:
    """
    Manages LLM invocations with multimodal input and tool calling.

    ### Architectural Decisions:
    - Stateless message construction (no history accumulation)
    - Multimodal input support (text + screenshot)
    - Native tool calling with JSON/XML fallback parsing
    - Progressive sampling for retry handling
    - Token usage tracking for performance monitoring

    ### Role in the System:
    - Generates action decisions via LLM
    - Constructs prompts from agent state
    - Parses tool calls from LLM responses
    - Tracks token consumption and latency
    - Handles LLM errors gracefully

    ### Integration Points:
    - Used by RVAgent assistant node
    - Receives ScreenDescription for UI formatting
    - Returns AIMessage with tool calls
    - Provides token metrics for reporting
    """

    def __init__(
        self,
        config: RVAgentConfig,
        llm: BaseChatModel,
        prompt_module: Any
    ):
        """
        Initialize LLM client.

        Args:
            config: Agent configuration
            llm: Configured LLM instance (ChatOpenAI with vLLM backend or None for hf_direct)
            prompt_module: Prompt module (e.g., v13) with SYSTEM_PROMPT and build_user_message
        """
        self.config = config
        self.llm = llm
        self.prompt_module = prompt_module

        self.logger = logging.getLogger(__name__)

        # Check if using HF direct backend
        self.use_hf_direct = config.llm_provider == "hf_direct"

        if self.use_hf_direct:
            # Initialize HuggingFace Transformers direct backend
            self.logger.info("Initializing HuggingFace Transformers direct backend...")

            llm_config = config.get_langchain_config()
            self.model_path = llm_config.get('model', './models/qwen3-vl-4b-fp8')

            # Load processor and model
            self.logger.info(f"Loading model from {self.model_path}...")
            self.processor = AutoProcessor.from_pretrained(self.model_path)
            self.model = Qwen3VLForConditionalGeneration.from_pretrained(
                self.model_path,
                device_map="auto"
            )

            # Define Android tools for apply_chat_template
            self.android_tools = self._create_android_tools()

            self.logger.info(f"✅ HF Direct initialized: model={self.model_path}, tools={len(self.android_tools)}")
        else:
            # Initialize for direct vLLM HTTP API calls (Phase 2: JSON parser approach)
            llm_config = config.get_langchain_config()
            self.base_url = llm_config.get('base_url', 'http://localhost:8000/v1')
            self.model_name = llm_config.get('model', './models/qwen3-vl-4b-fp8')
            self.http_client = httpx.Client(timeout=httpx.Timeout(config.llm_timeout, connect=5.0))

            self.logger.info(f"LLMClient initialized (vLLM JSON parser mode): base_url={self.base_url}, model={self.model_name}")

    def generate_action(
        self,
        screen_description: ScreenDescription,
        screenshot_b64: str,
        ui_elements_text: str,
        iteration: int = 0,
        last_action_summary: Optional[str] = None,
        temperature: float = 0.1,
        top_p: float = 0.9,
        top_k: int = 40,
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
            temperature: LLM sampling temperature
            top_p: LLM nucleus sampling parameter
            top_k: LLM top-k sampling parameter
            retry_count: Current retry count for progressive sampling

        Returns:
            Dictionary with:
            - response: AIMessage with tool calls
            - tokens_input: Input tokens consumed
            - tokens_output: Output tokens generated
            - time_ms: LLM latency in milliseconds
            - success: Whether invocation succeeded
        """
        self.logger.info(
            f"Generating action (retry={retry_count}, temp={temperature}, "
            f"top_p={top_p}, top_k={top_k})"
        )

        # Route to HF direct or vLLM based on configuration
        if self.use_hf_direct:
            return self._generate_action_hf_direct(
                screen_description=screen_description,
                screenshot_b64=screenshot_b64,
                ui_elements_text=ui_elements_text,
                iteration=iteration,
                last_action_summary=last_action_summary,
                temperature=temperature,
                retry_count=retry_count
            )

        start_time = time.time()

        try:
            # Build stateless messages
            messages = self._build_messages(
                ui_elements_text=ui_elements_text,
                screenshot_b64=screenshot_b64,
                iteration=iteration,
                last_action_summary=last_action_summary
            )

            self.logger.info(f"Messages constructed: {len(messages)} (System + Human)")

            # DEBUG: Log full prompt for troubleshooting
            self.logger.info("="*80)
            self.logger.info("📝 FULL PROMPT SENT TO LLM:")
            for i, msg in enumerate(messages):
                msg_type = type(msg).__name__
                self.logger.info(f"\n--- Message {i+1}/{len(messages)} ({msg_type}) ---")
                if hasattr(msg, 'content'):
                    if isinstance(msg.content, list):
                        # Multi-modal content (vision)
                        for j, item in enumerate(msg.content):
                            if isinstance(item, dict):
                                if item.get('type') == 'text':
                                    text = item.get('text', '')
                                    self.logger.info(f"  [text {j+1}]: {text[:500]}...")
                                elif item.get('type') == 'image_url':
                                    self.logger.info(f"  [image {j+1}]: <base64 image>")
                    else:
                        # Text-only content
                        self.logger.info(f"{msg.content[:1000]}...")
            self.logger.info("="*80)

            # Convert messages to OpenAI format for direct HTTP API call
            api_messages = self._convert_messages_to_openai_format(messages)

            # Prepare vLLM API request (Phase 2: JSON parser approach - NO native tool calling)
            api_request = {
                "model": self.model_name,
                "messages": api_messages,
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": 2048,
                "extra_body": {
                    "top_k": top_k,
                    "repetition_penalty": 1.1
                }
            }

            self.logger.info(f"🌐 Calling vLLM API (JSON parser mode): {self.base_url}/chat/completions")
            self.logger.info(f"📦 Request: model={self.model_name}, temp={temperature}, top_p={top_p}, top_k={top_k}")

            # Invoke vLLM with direct HTTP call
            try:
                http_response = self.http_client.post(
                    f"{self.base_url}/chat/completions",
                    json=api_request,
                    timeout=60.0  # 60-second timeout to prevent 10+ minute hangs
                )
                http_response.raise_for_status()  # Raise exception for 4xx/5xx status codes
                api_response = http_response.json()

            except httpx.TimeoutException as te:
                self.logger.error(f"⏱️  LLM timeout after 60s: {te}")
                llm_time_ms = (time.time() - start_time) * 1000
                empty_response = AIMessage(content="")
                return {
                    "action": None,
                    "has_tool_calls": False,
                    "reasoning": "",
                    "response": empty_response,
                    "tokens_input": 0,
                    "tokens_output": 0,
                    "time_ms": llm_time_ms,
                    "success": False
                }
            except httpx.HTTPStatusError as he:
                self.logger.error(f"❌ HTTP error {he.response.status_code}: {he.response.text}")
                llm_time_ms = (time.time() - start_time) * 1000
                empty_response = AIMessage(content="")
                return {
                    "action": None,
                    "has_tool_calls": False,
                    "reasoning": "",
                    "response": empty_response,
                    "tokens_input": 0,
                    "tokens_output": 0,
                    "time_ms": llm_time_ms,
                    "success": False
                }

            llm_time_ms = (time.time() - start_time) * 1000

            # DEBUG: Log raw response
            self.logger.info("="*80)
            self.logger.info(f"📬 RAW LLM RESPONSE ({llm_time_ms:.1f}ms):")
            self.logger.info(f"API response keys: {api_response.keys()}")
            self.logger.info(f"Full response: {api_response}")
            self.logger.info("="*80)

            # Extract response content from vLLM (Phase 2: rely on JSON parser)
            choice = api_response.get('choices', [{}])[0]
            message = choice.get('message', {})
            content = message.get('content', '') or ''  # Ensure never None

            # Extract token usage
            usage = api_response.get('usage', {})
            tokens_input = usage.get('prompt_tokens', 0)
            tokens_output = usage.get('completion_tokens', 0)

            # Create AIMessage with content (no native tool calls)
            response = AIMessage(content=content)
            response.tool_calls = []  # Start empty

            # Parse tool calls from content using JSON/XML parser
            # This is the ONLY way to extract actions in Phase 2
            self._parse_and_inject_tool_calls(response)

            # Extract action from tool_calls for rv_agent interface
            has_tool_calls = hasattr(response, 'tool_calls') and bool(response.tool_calls)
            action = None
            reasoning = ""

            if has_tool_calls:
                # Extract first tool call as action
                first_tool = response.tool_calls[0]
                action = {
                    'tool_name': first_tool.get('name'),  # Use 'tool_name' for LLM format (ToolExecutor will map to action_type)
                    'tool_args': first_tool.get('args', {}),
                    'tool_id': first_tool.get('id')
                }
                self.logger.info(f"✅ Extracted action: {action['tool_name']} with args {action['tool_args']}")

                # Extract reasoning from content if present
                if response.content:
                    reasoning = response.content[:500]  # First 500 chars
            else:
                self.logger.warning("⚠️  No tool calls found in response")
                # DEBUG: Print full response content when no tool calls
                self.logger.error(
                    f"🔍 FULL LLM RESPONSE (no tool calls):\n"
                    f"{'='*80}\n"
                    f"{response.content}\n"
                    f"{'='*80}"
                )

            self.logger.info(
                f"LLM Response: {llm_time_ms:.1f}ms, "
                f"tokens: {tokens_input} in / {tokens_output} out, "
                f"has_tool_calls: {has_tool_calls}"
            )

            # Log FULL response content to understand LLM reasoning
            if response.content:
                self.logger.info(f"💭 LLM Reasoning (full):\n{response.content}")
            else:
                self.logger.info("💭 LLM Reasoning: <empty>")

            return {
                "action": action,                  # ✅ ADD: Extracted action dict
                "has_tool_calls": has_tool_calls,  # ✅ ADD: Boolean flag
                "reasoning": reasoning,            # ✅ ADD: LLM reasoning text
                "response": response,              # Keep for debugging
                "tokens_input": tokens_input,
                "tokens_output": tokens_output,
                "time_ms": llm_time_ms,
                "success": True
            }

        except Exception as e:
            self.logger.error(f"LLM invocation failed: {e}", exc_info=True)
            llm_time_ms = (time.time() - start_time) * 1000

            # Return empty response with proper format
            empty_response = AIMessage(content="")

            return {
                "action": None,                # ✅ No action on error
                "has_tool_calls": False,       # ✅ No tool calls on error
                "reasoning": "",               # ✅ No reasoning on error
                "response": empty_response,
                "tokens_input": 0,
                "tokens_output": 0,
                "time_ms": llm_time_ms,
                "success": False
            }

    def _build_messages(
        self,
        ui_elements_text: str,
        screenshot_b64: str,
        iteration: int,
        last_action_summary: Optional[str]
    ) -> List:
        """
        Build stateless messages for LLM invocation.

        Constructs SystemMessage + HumanMessage with multimodal content.
        Does not accumulate message history (stateless architecture).

        Args:
            ui_elements_text: Formatted UI elements
            screenshot_b64: Base64-encoded screenshot
            iteration: Current iteration number
            last_action_summary: Summary of last action

        Returns:
            List of [SystemMessage, HumanMessage]
        """
        # Get system prompt
        system_text = self.prompt_module.SYSTEM_PROMPT

        # Build user message with minimal context
        state_info = {
            'ui_elements': [ui_elements_text],
            'last_action': last_action_summary,
            'iteration': iteration
        }
        user_text = self.prompt_module.build_user_message(state_info)

        # Log UI elements for debugging coordinate issues
        self.logger.info(f"📋 UI Elements sent to LLM:\n{ui_elements_text}")

        # Log full prompt on iteration 1 (0-indexed)
        if iteration == 1:
            full_prompt = f"{system_text}\n\n{user_text}"
            self.logger.info(
                f"\n{'='*80}\nFULL PROMPT (Iteration 2):\n{'='*80}\n"
                f"{full_prompt}\n{'='*80}"
            )

        # Construct messages with separate roles
        system_message = SystemMessage(content=system_text)

        human_message = HumanMessage(content=[
            {"type": "text", "text": user_text},
            {"type": "image_url", "image_url": {
                "url": f"data:image/png;base64,{screenshot_b64}"
            }}
        ])

        return [system_message, human_message]

    def _extract_token_usage(self, response: AIMessage) -> tuple[int, int]:
        """
        Extract token usage from LLM response metadata.

        Args:
            response: AIMessage from LLM

        Returns:
            Tuple of (input_tokens, output_tokens)
        """
        tokens_input = 0
        tokens_output = 0

        # Try usage_metadata first (standard format)
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            tokens_input = response.usage_metadata.get('input_tokens', 0)
            tokens_output = response.usage_metadata.get('output_tokens', 0)
        # Try response_metadata (Ollama format)
        elif hasattr(response, 'response_metadata') and response.response_metadata:
            metadata = response.response_metadata
            tokens_input = metadata.get('prompt_eval_count', 0)
            tokens_output = metadata.get('eval_count', 0)

        return tokens_input, tokens_output

    def _parse_and_inject_tool_calls(self, response: AIMessage):
        """
        Parse tool calls from response and inject if missing.

        Handles both native tool calling and JSON/XML fallback parsing.
        Modifies response object in-place.

        Args:
            response: AIMessage to process
        """
        # Check for native tool calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            self.logger.info(f"Native tool calls: {len(response.tool_calls)}")
            for tc in response.tool_calls:
                self.logger.info(f"  - {tc['name']} with args: {tc['args']}")
            return

        # Attempt JSON/XML parsing fallback
        self.logger.warning("No native tool calls - attempting JSON/XML parsing...")

        # DEBUG: Log content being parsed
        if not response.content or len(str(response.content).strip()) == 0:
            self.logger.error("Empty or invalid response content")
        else:
            self.logger.info(f"Parsing content ({len(str(response.content))} chars): {str(response.content)[:500]}...")

        parsed_calls = json_parser.parse_tool_calls_from_text(response.content)

        if parsed_calls:
            self.logger.info(f"Parsed {len(parsed_calls)} tool calls from text")

            # Convert to LangChain format and inject
            response.tool_calls = [
                {
                    'name': tc['name'],
                    'args': tc['args'],
                    'id': f"call_{i}",
                    'type': 'tool_call'
                }
                for i, tc in enumerate(parsed_calls)
            ]

            for tc in response.tool_calls:
                self.logger.info(f"  - {tc['name']} with args: {tc['args']}")
        else:
            self.logger.warning("No tool calls found in text either")

    def _convert_messages_to_openai_format(self, messages: List) -> List[Dict[str, Any]]:
        """
        Convert LangChain messages to OpenAI API format.

        Handles multimodal content (text + images) for vision models.

        Args:
            messages: List of LangChain Message objects

        Returns:
            List of message dictionaries in OpenAI format
        """
        api_messages = []

        for msg in messages:
            if isinstance(msg, SystemMessage):
                api_messages.append({
                    "role": "system",
                    "content": msg.content
                })
            elif isinstance(msg, HumanMessage):
                # Handle multimodal content
                if isinstance(msg.content, list):
                    # Multi-modal message (vision)
                    content_parts = []
                    for item in msg.content:
                        if isinstance(item, dict):
                            if item.get('type') == 'text':
                                content_parts.append({
                                    "type": "text",
                                    "text": item.get('text', '')
                                })
                            elif item.get('type') == 'image_url':
                                content_parts.append({
                                    "type": "image_url",
                                    "image_url": item.get('image_url', {})
                                })
                    api_messages.append({
                        "role": "user",
                        "content": content_parts
                    })
                else:
                    # Text-only message
                    api_messages.append({
                        "role": "user",
                        "content": msg.content
                    })
            elif isinstance(msg, AIMessage):
                api_messages.append({
                    "role": "assistant",
                    "content": msg.content
                })

        return api_messages

    def _create_android_tools(self) -> List:
        """
        Create Android tool definitions for HF apply_chat_template.

        Returns:
            List of Python functions with proper docstrings for HF tool calling
        """
        def android_click(x: int, y: int):
            """
            Click on a UI element at the specified coordinates.

            Args:
                x: X coordinate (pixels from left edge)
                y: Y coordinate (pixels from top edge)
            """
            pass

        def android_type_text(x: int, y: int, text: str):
            """
            Type text into an input field.

            Args:
                x: X coordinate of the input field
                y: Y coordinate of the input field
                text: Text to type
            """
            pass

        def android_scroll(direction: str):
            """
            Scroll the screen in a direction.

            Args:
                direction: Direction to scroll (choices: ["up", "down", "left", "right"])
            """
            pass

        def android_back():
            """Press the back button."""
            pass

        def android_home():
            """Press the home button."""
            pass

        return [android_click, android_type_text, android_scroll, android_back, android_home]

    def _generate_action_hf_direct(
        self,
        screen_description: ScreenDescription,
        screenshot_b64: str,
        ui_elements_text: str,
        iteration: int,
        last_action_summary: Optional[str],
        temperature: float,
        retry_count: int
    ) -> Dict[str, Any]:
        """
        Generate action using HuggingFace Transformers direct with native tool calling.

        Uses processor.apply_chat_template(tools=...) for native tool calling support.

        Args:
            screen_description: Parsed screen description
            screenshot_b64: Base64-encoded optimized screenshot
            ui_elements_text: Formatted UI elements text
            iteration: Current iteration number
            last_action_summary: Summary of last executed action
            temperature: LLM sampling temperature
            retry_count: Current retry count

        Returns:
            Dictionary with response, tokens, timing, and success status
        """
        import base64
        import io
        from PIL import Image

        self.logger.info("🤖 Generating action with HF Transformers direct")

        start_time = time.time()

        try:
            # Build messages
            messages = self._build_messages(
                ui_elements_text=ui_elements_text,
                screenshot_b64=screenshot_b64,
                iteration=iteration,
                last_action_summary=last_action_summary
            )

            # Convert to HF format
            hf_messages = []
            screenshot_path = None

            for msg in messages:
                if isinstance(msg, SystemMessage):
                    hf_messages.append({
                        "role": "system",
                        "content": [{"type": "text", "text": msg.content}]
                    })
                elif isinstance(msg, HumanMessage):
                    # Save screenshot to temp file for HF processing
                    if isinstance(msg.content, list):
                        content_parts = []
                        for item in msg.content:
                            if isinstance(item, dict):
                                if item.get('type') == 'text':
                                    content_parts.append({"type": "text", "text": item.get('text', '')})
                                elif item.get('type') == 'image_url':
                                    # Decode base64 image and save to temp file
                                    image_url = item.get('image_url', {}).get('url', '')
                                    if image_url.startswith('data:image'):
                                        # Extract base64 data
                                        base64_data = image_url.split(',')[1]
                                        image_bytes = base64.b64decode(base64_data)
                                        image = Image.open(io.BytesIO(image_bytes))

                                        # Save to temp file
                                        screenshot_path = f"/tmp/rvagent_screenshot_{iteration}.png"
                                        image.save(screenshot_path)

                                        content_parts.append({"type": "image", "image": screenshot_path})

                        hf_messages.append({"role": "user", "content": content_parts})

            # Apply chat template with tools
            self.logger.info(f"📝 Applying chat template with {len(self.android_tools)} tools...")
            text = self.processor.apply_chat_template(
                hf_messages,
                tools=self.android_tools,
                tokenize=False,
                add_generation_prompt=True
            )

            # Process vision info
            image_inputs, video_inputs = process_vision_info(hf_messages)

            # Tokenize
            inputs = self.processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt"
            )
            inputs = inputs.to(self.model.device)

            # Generate
            self.logger.info("🎨 Generating response...")
            with torch.no_grad():
                generated_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=512,
                    temperature=temperature,
                    do_sample=temperature > 0.001
                )

            # Decode (only new tokens)
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            response_text = self.processor.batch_decode(
                generated_ids_trimmed,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False
            )[0]

            llm_time_ms = (time.time() - start_time) * 1000

            self.logger.info(f"✅ Generated in {llm_time_ms:.1f}ms")
            self.logger.info(f"📝 Response:\n{response_text}")

            # Create AIMessage
            response = AIMessage(content=response_text)
            response.tool_calls = []

            # Parse tool calls from response using existing JSON parser
            self._parse_and_inject_tool_calls(response)

            # Extract action
            has_tool_calls = bool(response.tool_calls)
            action = None
            reasoning = ""

            if has_tool_calls:
                first_tool = response.tool_calls[0]
                action = {
                    'tool_name': first_tool.get('name'),
                    'tool_args': first_tool.get('args', {}),
                    'tool_id': first_tool.get('id')
                }
                self.logger.info(f"✅ Extracted action: {action['tool_name']} with args {action['tool_args']}")
                reasoning = response_text[:500]
            else:
                self.logger.warning("⚠️  No tool calls found in HF response")

            # Estimate tokens (rough approximation)
            tokens_input = len(text.split()) * 1.3  # Approximate
            tokens_output = len(response_text.split()) * 1.3

            # Cleanup
            if screenshot_path:
                import os
                try:
                    os.remove(screenshot_path)
                except:
                    pass

            return {
                "action": action,
                "has_tool_calls": has_tool_calls,
                "reasoning": reasoning,
                "response": response,
                "tokens_input": int(tokens_input),
                "tokens_output": int(tokens_output),
                "time_ms": llm_time_ms,
                "success": True
            }

        except Exception as e:
            self.logger.error(f"HF Direct generation failed: {e}", exc_info=True)
            llm_time_ms = (time.time() - start_time) * 1000

            return {
                "action": None,
                "has_tool_calls": False,
                "reasoning": "",
                "response": AIMessage(content=""),
                "tokens_input": 0,
                "tokens_output": 0,
                "time_ms": llm_time_ms,
                "success": False
            }

    def cleanup(self):
        """
        Clean up GPU memory by unloading model and processor.

        Call this when done with the LLM to free GPU resources.
        """
        if self.use_hf_direct:
            self.logger.info("🧹 Cleaning up HF Direct resources...")

            if hasattr(self, "model") and self.model is not None:
                del self.model
                self.model = None

            if hasattr(self, "processor") and self.processor is not None:
                del self.processor
                self.processor = None

            # Clear CUDA cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            self.logger.info("✅ GPU memory cleaned up")
        else:
            # Close HTTP client for vLLM
            if hasattr(self, "http_client"):
                self.http_client.close()
                self.logger.info("✅ vLLM HTTP client closed")

