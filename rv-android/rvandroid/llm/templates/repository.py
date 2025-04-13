# rvandroid/llm/templates/repository.py
"""Fragment repository for MCP templates."""

import logging
from typing import Dict, Any, List, Optional

from rvandroid.llm.templates.template import TemplateFragment
from rvandroid.llm.templates.library import PromptLibrary
from rvandroid.util.error.error_handler import ErrorHandler


class FragmentRepository:
    """
    Repository for managing template fragments.
    
    Provides a specialized interface for working with template fragments,
    organized by purpose and use case. Enables easy registration and retrieval
    of fragments for different testing scenarios.
    """

    def __init__(self):
        """Initialize fragment repository."""
        self.library = PromptLibrary.get_instance()
        self.logger = logging.getLogger(__name__)
        self.error_handler = ErrorHandler.get_instance()
        self._initialize_fragments()

    def _initialize_fragments(self):
        """Initialize all fragment categories."""
        self.register_system_fragments()
        self.register_ui_pattern_fragments()
        self.register_response_format_fragments()
        self.register_monitored_operations_fragments()

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
            content="TESTING OBJECTIVES:\n1. Explore all parts of the application systematically\n2. Prioritize testing of methods that affect monitored operations\n3. Attempt to trigger monitored operations with different inputs\n4. Test both valid and invalid inputs\n5. Maximize code and UI coverage",
            version="1.0.0"
        )
        self.library.register_fragment("testing_objectives", testing_objectives)

    def register_ui_pattern_fragments(self):
        """Register UI pattern-specific fragments."""
        # Already initialized in PromptLibrary, just add any additional fragments here
        
        # Dropdown guidelines fragment
        dropdown_guidelines = TemplateFragment(
            name="dropdown_guidelines",
            content="DROPDOWN GUIDELINES:\n1. Open dropdown to view all options\n2. Select different options to test behavior\n3. Check default selection\n4. Test dropdown state after rotation\n5. Verify dropdown appearance and positioning",
            version="1.0.0"
        )
        self.library.register_fragment("dropdown_guidelines", dropdown_guidelines)
        
        # Search guidelines fragment
        search_guidelines = TemplateFragment(
            name="search_guidelines",
            content="SEARCH GUIDELINES:\n1. Enter different search queries\n2. Test searching with valid and invalid inputs\n3. Check behavior with empty search\n4. Test search result navigation\n5. Check search history functionality if available",
            version="1.0.0"
        )
        self.library.register_fragment("search_guidelines", search_guidelines)

    def register_response_format_fragments(self):
        """Register response format fragments."""
        # Single action format fragment already initialized in PromptLibrary
        # Add any specialized response format fragments here
        
        # Detailed action format fragment
        detailed_action_format = TemplateFragment(
            name="detailed_action_format",
            content="RESPONSE FORMAT:\nRespond with exactly ONE action in the following JSON format:\n\n```json\n{\n  \"action\": {\n    \"type\": \"click\", // Type of action: click, long_click, text, swipe, back, etc.\n    \"element_id\": \"button_login\", // ID of the element to interact with\n    \"text\": \"username\", // For text actions, the text to enter\n    \"reason\": \"Clicking the login button to attempt authentication\",\n    \"expected_result\": \"Login screen should transition to the home screen\",\n    \"monitored_operations\": [\"Authentication\", \"NetworkAccess\"]\n  }\n}\n```\n\nEnsure your response is ONLY valid JSON that can be parsed directly.",
            version="1.0.0"
        )
        self.library.register_fragment("detailed_action_format", detailed_action_format)

    def register_monitored_operations_fragments(self):
        """Register fragments related to monitored operations."""
        # General monitored operations fragment
        monitored_ops = TemplateFragment(
            name="monitored_operations",
            content="MONITORED OPERATIONS:\nThe application is being monitored for specific operations. Your task is to test these operations thoroughly with different inputs and scenarios. When suggesting actions, prioritize those that might trigger monitored operations.",
            version="1.0.0"
        )
        self.library.register_fragment("monitored_operations", monitored_ops)
        
        # Cryptography operations fragment
        crypto_ops = TemplateFragment(
            name="crypto_operations",
            content="CRYPTOGRAPHY OPERATIONS:\nThe application contains cryptographic operations that are being monitored for proper usage. When testing, look for features that might involve encryption, decryption, key management, secure storage, or data protection. Prioritize testing these features thoroughly.",
            version="1.0.0"
        )
        self.library.register_fragment("crypto_operations", crypto_ops)
        
        # General programming operations fragment
        general_ops = TemplateFragment(
            name="general_programming_operations",
            content="GENERAL PROGRAMMING OPERATIONS:\nThe application is being monitored for proper usage of programming constructs like iterators, collections, resources, and error handling. When testing, look for features that might involve extensive data processing, resource management, or error conditions.",
            version="1.0.0"
        )
        self.library.register_fragment("general_programming_operations", general_ops)

    def get_ui_pattern_fragment(self, pattern_type: str) -> Optional[TemplateFragment]:
        """
        Get a fragment for a specific UI pattern.
        
        Args:
            pattern_type: Type of UI pattern (form, list, tabs, dialog, navigation)
            
        Returns:
            TemplateFragment for the pattern or None if not found
        """
        fragment_name = f"{pattern_type}_guidelines"
        return self.library.get_fragment(fragment_name)

    def get_specialized_fragments(self, topic: str) -> List[TemplateFragment]:
        """
        Get specialized fragments for a specific topic.
        
        Args:
            topic: Topic to get fragments for (e.g., "crypto", "programming", "ui")
            
        Returns:
            List of relevant TemplateFragment instances
        """
        fragments = []
        
        if topic == "crypto":
            fragments.append(self.library.get_fragment("crypto_operations"))
        elif topic == "programming":
            fragments.append(self.library.get_fragment("general_programming_operations"))
        elif topic == "ui":
            patterns = ["form", "list", "tabs", "dialog", "navigation", "dropdown", "search"]
            for pattern in patterns:
                fragment = self.get_ui_pattern_fragment(pattern)
                if fragment:
                    fragments.append(fragment)
        
        return [f for f in fragments if f is not None]