# rvandroid/mcp/templates/repository.py
"""Fragment repository for MCP templates."""

import logging
from typing import Dict, Any, List, Optional

from rvandroid.mcp.templates.template import TemplateFragment
from rvandroid.mcp.templates.library import PromptLibrary


class FragmentRepository:
    """Repository for managing template fragments."""

    def __init__(self):
        """Initialize fragment repository."""
        self.library = PromptLibrary.get_instance()
        self.logger = logging.getLogger(f"{__name__}")

    def register_system_fragments(self):
        """Register system-related fragments."""
        # System introduction fragment
        system_intro = TemplateFragment(
            name="system_introduction",
            content="You are an AI assistant helping to test Android applications by generating appropriate UI actions. Your goal is to thoroughly explore the application's functionality, focusing on monitored operations and comprehensive testing coverage.",
            version="1.0.0"
        )
        self.library.register_fragment("system_introduction", system_intro)

        # Role definition fragment
        role_definition = TemplateFragment(
            name="role_definition",
            content="As a testing assistant, your task is to analyze the current application state and suggest the most effective actions to take for thorough testing. You should prioritize actions that might trigger monitored operations while ensuring broad application coverage.",
            version="1.0.0"
        )
        self.library.register_fragment("role_definition", role_definition)

        # Testing objectives fragment
        testing_objectives = TemplateFragment(
            name="testing_objectives",
            content="TESTING OBJECTIVES:\n1. Explore all parts of the application systematically\n2. Prioritize testing of functionality with monitored operations\n3. Attempt to trigger monitored operations\n4. Test both valid and invalid inputs\n5. Maximize code and UI coverage",
            version="1.0.0"
        )
        self.library.register_fragment("testing_objectives", testing_objectives)

    def register_ui_pattern_fragments(self):
        """Register UI pattern-specific fragments."""
        # Dialog guidelines fragment
        dialog_guidelines = TemplateFragment(
            name="dialog_guidelines",
            content="DIALOG GUIDELINES:\n1. Test all dialog buttons and options\n2. Check dialog dismissal behavior\n3. Verify error message display\n4. Test dialog input validation\n5. Check dialog behavior on configuration changes",
            version="1.0.0"
        )
        self.library.register_fragment("dialog_guidelines", dialog_guidelines)

        # Tabs guidelines fragment
        tabs_guidelines = TemplateFragment(
            name="tabs_guidelines",
            content="TABS GUIDELINES:\n1. Navigate through all available tabs\n2. Check content loading in each tab\n3. Test tab switching behavior\n4. Verify tab state persistence\n5. Look for interactions between tab content",
            version="1.0.0"
        )
        self.library.register_fragment("tabs_guidelines", tabs_guidelines)

        # Dropdown guidelines fragment
        dropdown_guidelines = TemplateFragment(
            name="dropdown_guidelines",
            content="DROPDOWN GUIDELINES:\n1. Open dropdown to view all options\n2. Select different options to test behavior\n3. Check default selection\n4. Test dropdown state after rotation\n5. Verify dropdown appearance and positioning",
            version="1.0.0"
        )
        self.library.register_fragment("dropdown_guidelines", dropdown_guidelines)

    def register_response_format_fragments(self):
        """Register response format fragments."""
        # Single action format fragment
        single_action_format = TemplateFragment(
            name="single_action_format",
            content="RESPONSE FORMAT:\nRespond with exactly ONE action in the following JSON format:\n\n```json\n{\n  \"action\": {\n    \"type\": \"click\", // Type of action: click, long_click, text, swipe, back, etc.\n    \"element_id\": \"button_login\", // ID of the element to interact with\n    \"text\": \"username\", // For text actions, the text to enter\n    \"reason\": \"Clicking the login button to attempt authentication\"\n  }\n}\n```\n\nEnsure your response is ONLY valid JSON that can be parsed directly.",
            version="1.0.0"
        )
        self.library.register_fragment("single_action_format", single_action_format)

        # Batch action format fragment
        batch_action_format = TemplateFragment(
            name="batch_action_format",
            content="RESPONSE FORMAT:\nRespond with a sequence of related actions in the following JSON format:\n\n```json\n{\n  \"actions\": [\n    {\n      \"type\": \"text\",\n      \"element_id\": \"edit_username\",\n      \"text\": \"testuser\",\n      \"reason\": \"Entering test username\"\n    },\n    {\n      \"type\": \"click\",\n      \"element_id\": \"button_login\",\n      \"reason\": \"Submitting the login form\"\n    }\n  ],\n  \"pattern\": \"form_submission\",\n  \"objective\": \"Testing the login functionality\"\n}\n```\n\nEnsure your response is ONLY valid JSON that can be parsed directly.",
            version="1.0.0"
        )
        self.library.register_fragment("batch_action_format", batch_action_format)
       