# rvandroid/llm/templates/library.py
"""Template library for Model Context Protocol."""

import logging
import os
import json
from typing import Dict, Any, Optional, List
import re

from rvandroid.llm.data_structures import MCPMessage, MCPRole, MCPTextContent
from rvandroid.llm.templates.template import MCPPromptTemplate, TemplateFragment
from rvandroid.util.error.error_handler import ErrorHandler


class PromptLibrary:
    """
    Library for storing and retrieving prompt templates.
    
    A centralized registry for template management, providing version control,
    template inheritance, and fragment reuse. The library manages both templates
    and fragments, enabling composition and specialization of templates.
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        """
        Get singleton instance of PromptLibrary.
        
        Returns:
            PromptLibrary singleton instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Initialize prompt library with base templates and fragments."""
        self.templates = {}  # Dict[str, Dict[str, MCPPromptTemplate]]
        self.fragments = {}  # Dict[str, Dict[str, TemplateFragment]]
        self.categories = {}  # Dict[str, List[str]]
        self.logger = logging.getLogger(__name__)
        self.error_handler = ErrorHandler.get_instance()
        self._initialize_base_templates()
        self._initialize_fragments()

    def _initialize_base_templates(self):
        """Initialize base templates for common use cases."""
        # System base template
        system_base = MCPPromptTemplate(
            name="system_base",
            template_data={
                "messages": [
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "text",
                                "text": "You are an AI assistant helping to test Android applications by generating appropriate UI actions. Your task is to analyze the current app state and suggest the MOST EFFECTIVE NEXT ACTION to take for testing the application thoroughly.\n\nFocus on:\n1. {exploration_goal}\n2. Maximizing code coverage by targeting untested UI elements\n3. Prioritizing testing of methods of interest that directly or indirectly affect monitored operations\n4. Testing complete workflows from start to finish\n\n{response_format}\n\n{#if additional_guidelines}{additional_guidelines}{#endif}"
                            }
                        ]
                    }
                ],
                "required_vars": ["exploration_goal", "response_format"]
            },
            version="1.0.0"
        )
        self.register_template("system_base", system_base, "base")

        # User base template
        user_base = MCPPromptTemplate(
            name="user_base",
            template_data={
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Current Activity: {activity}\n\nUI Elements and Actions:\n{ui_elements}\n\n{#if action_history}Action History:\n{action_history}{#endif}\n\n{#if summary}Summary:\n{summary}{#endif}"
                            }
                        ]
                    }
                ],
                "required_vars": ["activity", "ui_elements"]
            },
            version="1.0.0"
        )
        self.register_template("user_base", user_base, "base")

        # Single action response format
        single_action_format = MCPPromptTemplate(
            name="single_action_format",
            template_data={
                "messages": [
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "text",
                                "text": "RESPONSE FORMAT:\nRespond with exactly ONE action in the following JSON format:\n\n```json\n{\n  \"action\": {\n    \"type\": \"click\", // Type of action: click, long_click, text, swipe, back, etc.\n    \"element_id\": \"button_login\", // ID of the element to interact with\n    \"text\": \"username\", // For text actions, the text to enter\n    \"reason\": \"Clicking the login button to attempt authentication\"\n  }\n}\n```\n\nEnsure your response is ONLY valid JSON that can be parsed directly."
                            }
                        ]
                    }
                ]
            },
            version="1.0.0"
        )
        self.register_template("single_action_format", single_action_format, "response_format")
        
        # Batch action response format
        batch_action_format = MCPPromptTemplate(
            name="batch_action_format",
            template_data={
                "messages": [
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "text",
                                "text": "RESPONSE FORMAT:\nRespond with a sequence of related actions in the following JSON format:\n\n```json\n{\n  \"pattern_type\": \"form|list|tabs|dialog|navigation|custom\",\n  \"actions\": [\n    {\n      \"action_id\": \"5\",  \n      \"params\": {},  \n      \"explanation\": \"Why this action is included in the batch\"\n    },\n    {\n      \"action_id\": \"8\",\n      \"params\": {},\n      \"explanation\": \"Why this action logically follows the previous one\"\n    }\n  ],\n  \"batch_explanation\": \"Overall explanation of why these actions form a logical batch\"\n}\n```\n\nEnsure your response is ONLY valid JSON that can be parsed directly."
                            }
                        ]
                    }
                ]
            },
            version="1.0.0"
        )
        self.register_template("batch_action_format", batch_action_format, "response_format")

    def _initialize_fragments(self):
        """Initialize common fragments used across templates."""
        # Form guidelines fragment
        form_guidelines = TemplateFragment(
            name="form_guidelines",
            content="FORM GUIDELINES:\n1. Fill all required fields before submitting\n2. Use relevant, valid test data for each field type\n3. Test both valid and invalid inputs\n4. Test field validation behavior\n5. Check form submission with minimum required fields",
            version="1.0.0"
        )
        self.register_fragment("form_guidelines", form_guidelines)

        # List guidelines fragment
        list_guidelines = TemplateFragment(
            name="list_guidelines",
            content="LIST GUIDELINES:\n1. Explore different items in the list\n2. Scroll to see more items if available\n3. Test item selection behaviors\n4. Check for item-specific actions\n5. Look for search, filter, or sort functionality",
            version="1.0.0"
        )
        self.register_fragment("list_guidelines", list_guidelines)
        
        # Tabs guidelines fragment
        tabs_guidelines = TemplateFragment(
            name="tabs_guidelines",
            content="TABS GUIDELINES:\n1. Navigate through all available tabs\n2. Check content loading in each tab\n3. Test tab switching behavior\n4. Verify tab state persistence\n5. Look for interactions between tab content",
            version="1.0.0"
        )
        self.register_fragment("tabs_guidelines", tabs_guidelines)

        # Dialog guidelines fragment
        dialog_guidelines = TemplateFragment(
            name="dialog_guidelines",
            content="DIALOG GUIDELINES:\n1. Test all dialog buttons and options\n2. Check dialog dismissal behavior\n3. Verify error message display\n4. Test dialog input validation\n5. Check dialog behavior on configuration changes",
            version="1.0.0"
        )
        self.register_fragment("dialog_guidelines", dialog_guidelines)

        # Navigation guidelines fragment
        navigation_guidelines = TemplateFragment(
            name="navigation_guidelines",
            content="NAVIGATION GUIDELINES:\n1. Explore main navigation elements (menus, drawers, tabs)\n2. Test back navigation functionality\n3. Check for home/up button behavior\n4. Verify navigation hierarchy\n5. Test navigation between related screens",
            version="1.0.0"
        )
        self.register_fragment("navigation_guidelines", navigation_guidelines)

    def register_template(self, name: str, template: MCPPromptTemplate, category: str = None) -> None:
        """
        Register a template in the library.
        
        Args:
            name: Template name/identifier
            template: MCPPromptTemplate instance
            category: Optional category for organization
        """
        if name not in self.templates:
            self.templates[name] = {}

        self.templates[name][template.version] = template
        self.logger.debug(f"Registered template '{name}' version {template.version}")
        
        # Add to category if specified
        if category:
            if category not in self.categories:
                self.categories[category] = []
            if name not in self.categories[category]:
                self.categories[category].append(name)

    def get_template(self, name: str, version: str = None) -> Optional[MCPPromptTemplate]:
        """
        Get a template by name and optional version.
        
        Args:
            name: Template identifier
            version: Optional version string (default: latest)
            
        Returns:
            MCPPromptTemplate instance or None if not found
        """
        if name not in self.templates:
            self.logger.warning(f"Template '{name}' not found")
            return None

        if version is None:
            # Get latest version
            versions = list(self.templates[name].keys())
            if not versions:
                return None

            # Sort using semantic versioning
            versions.sort(key=lambda v: [int(x) for x in v.split('.')])
            version = versions[-1]

        if version not in self.templates[name]:
            self.logger.warning(f"Version '{version}' of template '{name}' not found")
            return None

        return self.templates[name][version]

    def register_fragment(self, name: str, fragment: TemplateFragment) -> None:
        """
        Register a fragment in the library.
        
        Args:
            name: Fragment name/identifier
            fragment: TemplateFragment instance
        """
        if name not in self.fragments:
            self.fragments[name] = {}

        self.fragments[name][fragment.version] = fragment
        self.logger.debug(f"Registered fragment '{name}' version {fragment.version}")

    def get_fragment(self, name: str, version: str = None) -> Optional[TemplateFragment]:
        """
        Get a fragment by name and optional version.
        
        Args:
            name: Fragment identifier
            version: Optional version string (default: latest)
            
        Returns:
            TemplateFragment instance or None if not found
        """
        if name not in self.fragments:
            self.logger.warning(f"Fragment '{name}' not found")
            return None

        if version is None:
            # Get latest version
            versions = list(self.fragments[name].keys())
            if not versions:
                return None

            # Sort using semantic versioning
            versions.sort(key=lambda v: [int(x) for x in v.split('.')])
            version = versions[-1]

        if version not in self.fragments[name]:
            self.logger.warning(f"Version '{version}' of fragment '{name}' not found")
            return None

        return self.fragments[name][version]

    def derive_template(self,
                        name: str,
                        base_name: str,
                        base_version: str = None,
                        modifications: Dict[str, Any] = None,
                        version_increment: str = "minor") -> Optional[MCPPromptTemplate]:
        """
        Create a new template version derived from an existing one.
        
        Args:
            name: Name for the new template
            base_name: Name of the base template
            base_version: Optional version of the base template
            modifications: Dictionary of modifications to apply
            version_increment: Type of version increment ("major", "minor", "patch")
            
        Returns:
            New MCPPromptTemplate instance or None if base template not found
        """
        # Get base template
        base_template = self.get_template(base_name, base_version)
        if not base_template:
            self.logger.warning(f"Base template '{base_name}' not found")
            return None

        # Create derived template
        derived = base_template.derive(name, modifications, version_increment)

        # Register derived template
        self.register_template(name, derived)

        return derived
        
    def get_templates_by_category(self, category: str) -> List[str]:
        """
        Get names of templates in a category.
        
        Args:
            category: Category name
            
        Returns:
            List of template names in the category
        """
        return self.categories.get(category, [])