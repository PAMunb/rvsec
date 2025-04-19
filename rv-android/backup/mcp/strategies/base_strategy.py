# rvandroid/mcp/strategies/base_strategy.py
"""Base strategy implementation using MCP."""

import logging
import re
from abc import ABC
from typing import Dict, Any, List, Optional

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.mcp.language_model import LanguageModel
from rvandroid.mcp.mcp_data_structures import MCPMessage, MCPRole, MCPTextContent, MCPConfiguration
from rvandroid.mcp.templates.library import PromptLibrary
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser
from rvandroid.parser.screen.parser_factory import ParserFactory, ParserType


class BasePromptStrategy(ABC):
    """Base class for prompt strategies using MCP."""

    def __init__(self,
                 static_data: Optional[StaticAnalysisData] = None,
                 parser: Optional[AbstractScreenParser] = None,
                 **kwargs):
        """Initialize base prompt strategy."""
        self.static_data = static_data
        self.parser = parser or ParserFactory.create(ParserType.DROIDBOT)
        self.library = PromptLibrary.get_instance()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Template versions to use
        self.system_template_name = "system_base"
        self.system_template_version = None  # Use latest
        self.user_template_name = "user_base"
        self.user_template_version = None  # Use latest

        # Customization parameters
        self.exploration_goal = "Systematically exploring the application to find monitored operations and potential specification violations"
        self.response_format_name = "single_action_format"
        self.additional_guidelines = None

        # Process kwargs
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        # Initialize templates
        self._initialize_templates()

    def _initialize_templates(self):
        """Initialize templates needed by this strategy."""
        self.system_template = self.library.get_template(
            self.system_template_name,
            self.system_template_version
        )

        self.user_template = self.library.get_template(
            self.user_template_name,
            self.user_template_version
        )

        if not self.system_template or not self.user_template:
            self.logger.error("Failed to initialize templates")
            raise ValueError("Templates not found")

    def generate_system_prompt(self) -> List[MCPMessage]:
        """Generate system messages."""
        if not self.system_template:
            self.logger.warning("System template not found")
            return []

        variables = {
            "exploration_goal": self.exploration_goal,
            "response_format": self._get_response_format()
        }

        if self.additional_guidelines:
            variables["additional_guidelines"] = self.additional_guidelines

        return self.system_template.render(variables)

    def generate_user_prompt(self, state: Dict[str, Any]) -> List[MCPMessage]:
        """Generate user messages based on application state."""
        if not self.user_template:
            self.logger.warning("User template not found")
            return []

        try:
            # Process screen description
            screen_description = self.process_screen(state)

            # Get activity name
            activity = self.parser.get_activity_name(state)

            # Format UI elements for the prompt
            ui_elements = self._format_ui_elements(screen_description, state)

            # Format action history
            action_history = self._format_action_history(state)

            # Generate optional summary
            summary = self._generate_summary(activity, screen_description, state)

            # Prepare variables
            variables = {
                "activity": activity,
                "ui_elements": ui_elements,
            }

            if action_history:
                variables["action_history"] = action_history

            if summary:
                variables["summary"] = summary

            return self.user_template.render(variables)

        except Exception as e:
            self.logger.error(f"Error generating user prompt: {e}", exc_info=True)
            # Return basic message as fallback
            return [MCPMessage(
                role=MCPRole.USER,
                content=[MCPTextContent(text="Please suggest a testing action for this Android application.")]
            )]

    def process_screen(self, state: Dict[str, Any]) -> Any:
        """Process screen data to generate structured description."""
        return self.parser.parse_state(state)

    def _format_ui_elements(self, screen_description: Any, state: Dict[str, Any]) -> str:
        """Format UI elements for prompt display."""
        # Default implementation
        formatted = []

        for item in screen_description.items:
            item_desc = f"* {item.description}"
            formatted.append(item_desc)

            # Add actions
            for action in item.actions:
                mop_tag = ""
                if getattr(action, "directly_reaches_mop", False):
                    mop_tag = " [CRITICAL: Directly reaches monitored operation]"
                elif getattr(action, "reaches_mop", False):
                    mop_tag = " [IMPORTANT: Can reach monitored operation]"

                action_desc = f"  - {action.text} (action_id: \"{action.id}\"){mop_tag}"
                formatted.append(action_desc)

        return "\n".join(formatted)

    def _format_action_history(self, state: Dict[str, Any]) -> Optional[str]:
        """Format action history for prompt display."""
        history = state.get("action_history", [])
        if not history:
            return None

        # Limit to last 10 actions
        recent_actions = history[-10:] if len(history) > 10 else history

        formatted = []
        for i, action in enumerate(recent_actions):
            formatted.append(f"{i + 1}. {action}")

        return "\n".join(formatted)

    def _generate_summary(self, activity: str, screen_description: Any, state: Dict[str, Any]) -> Optional[str]:
        """Generate optional summary of current state."""
        # Default implementation - no summary
        return None

    def _get_response_format(self) -> str:
        """Get response format instructions."""
        format_fragment = self.library.get_fragment(self.response_format_name)
        if not format_fragment:
            self.logger.warning(f"Response format fragment '{self.response_format_name}' not found")
            return "Please suggest one action to take in this application."

        rendered = format_fragment.render({})
        if isinstance(rendered, str):
            return rendered
        elif isinstance(rendered, MCPTextContent):
            return rendered.text
        elif isinstance(rendered, list) and rendered and isinstance(rendered[0], MCPTextContent):
            return rendered[0].text
        else:
            return "Please suggest one action to take in this application."

    def generate_messages(self, state: Dict[str, Any]) -> List[MCPMessage]:
        """Generate all messages for the prompt."""
        system_messages = self.generate_system_prompt()
        user_messages = self.generate_user_prompt(state)

        # Combine messages
        return system_messages + user_messages

    async def generate_actions(self, model: LanguageModel, state: Dict[str, Any],
                               config: Optional[MCPConfiguration] = None) -> Dict[str, Any]:
        """Generate actions using the language model."""
        try:
            # Generate messages
            messages = self.generate_messages(state)

            # Get model response
            response = await model.generate(messages, config)

            # Process response
            return self.process_response(response, state)

        except Exception as e:
            self.logger.error(f"Error generating actions: {e}", exc_info=True)
            return {"error": str(e)}

    def process_response(self, response: MCPMessage, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process model response to extract actions."""
        try:
            # Get response text
            text = response.get_text_content()

            # Try to extract JSON
            json_match = re.search(r'```json\s*(.+?)\s*```', text, re.DOTALL)
            if not json_match:
                json_match = re.search(r'{.+}', text, re.DOTALL)

            if json_match:
                json_text = json_match.group(1) if '```json' in text else json_match.group(0)

                # Parse JSON
                import json
                return json.loads(json_text)
            else:
                self.logger.warning("Failed to extract JSON from response")
                return {"error": "No valid JSON found in response"}

        except Exception as e:
            self.logger.error(f"Error processing response: {e}", exc_info=True)
            return {"error": str(e)}
