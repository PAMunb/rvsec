"""Template repository for the prompt system.

This module defines the TemplateRepository class, which is responsible for
loading, managing, and providing access to prompt templates.
"""

import json
import os
from typing import Any, Dict, List, Optional

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.config.component_configurator import ComponentConfigurator
from .prompt_template import PromptTemplate


# TODO deprecated
class TemplateRepository:
    """Repository for managing prompt templates.
    
    The TemplateRepository is responsible for loading templates from JSON files,
    providing access to templates, and creating messages for LLM communication.
    """

    def __init__(self, template_dir: Optional[str] = None):
        """Initialize the template repository.
        
        Args:
            template_dir: The directory containing template JSON files.
                If not provided, defaults to the "templates" directory
                in the same directory as this file.
        """
        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.prompt.template.repository",
            {CONTEXT_COMPONENT: "TemplateRepository"}
        )

        # Set up error handling
        self.error_handler = ErrorHandler.get_instance()

        # Set template directory
        self.template_dir = template_dir or os.path.join(
            os.path.dirname(__file__), "templates")

        # Ensure template directory exists
        os.makedirs(self.template_dir, exist_ok=True)

        # Initialize template cache
        self.templates: Dict[str, Dict[str, Any]] = {}
        self.template_objects: Dict[str, PromptTemplate] = {}

        # Load templates
        self._load_templates()

    def configure(self, config: ComponentConfigurator) -> None:
        """Configure the template repository with the given configuration.
        
        Args:
            config: The configuration to use.
        """
        self.logger.info("Configuring TemplateRepository")

        # Check if custom template directory is specified through llm config
        # The ComponentConfigurator doesn't have a get_value method
        # Let's check if it has the attribute directly
        if hasattr(config, 'llm_config') and hasattr(config.llm_config, 'template_dir'):
            custom_template_dir = config.llm_config.template_dir
            if custom_template_dir:
                self.template_dir = custom_template_dir
                self._load_templates()

    def _load_templates(self) -> None:
        """Load templates from JSON files in the template directory."""
        self.logger.info(f"Loading templates from {self.template_dir}")

        try:
            # If the directory doesn't exist or is empty, create default templates
            if not os.path.exists(self.template_dir) or not os.listdir(self.template_dir):
                self.logger.info("Template directory empty or not found, creating default templates")
                self._create_default_templates()

            # Load all JSON template files
            for filename in os.listdir(self.template_dir):
                if filename.endswith(".json"):
                    template_path = os.path.join(self.template_dir, filename)
                    template_name = filename.replace(".json", "")

                    try:
                        with open(template_path, "r") as f:
                            template_data = json.load(f)
                            self.templates[template_name] = template_data

                            # Create template objects for each role if they exist
                            for role in ["system", "user", "assistant"]:
                                if role in template_data:
                                    template_key = f"{template_name}.{role}"
                                    self.template_objects[template_key] = PromptTemplate(
                                        template_data[role],
                                        template_key,
                                        required_variables=template_data.get("required_variables", [])
                                    )

                            self.logger.debug(f"Loaded template: {template_name}")
                    except Exception as e:
                        self.logger.error(f"Error loading template {template_name}: {e}")
                        self.error_handler.handle_error(
                            e,
                            context={
                                "component": "TemplateRepository",
                                "template_path": template_path
                            }
                        )

            self.logger.info(f"Loaded {len(self.templates)} templates")
        except Exception as e:
            self.logger.error(f"Error loading templates: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "TemplateRepository",
                    "template_dir": self.template_dir
                }
            )

    def _create_default_templates(self) -> None:
        """Create default templates if the template directory is empty."""
        os.makedirs(self.template_dir, exist_ok=True)

        # Define default templates
        default_templates = {
            "exploration": {
                "system": (
                    "You are an Android testing assistant. Your task is to help test the Android "
                    "application by identifying UI elements and suggesting testing actions.\n\n"
                    "The current screen contains the following UI elements:\n"
                    "{screen_elements}\n\n"
                    "{#if ui_patterns}"
                    "I've identified the following UI patterns:\n"
                    "{ui_patterns}\n\n"
                    "{#endif}"
                    "{#if monitored_operations}"
                    "Pay attention to monitored operations:\n"
                    "{monitored_operations.summary}\n\n"
                    "{#endif}"
                ),
                "user": (
                    "Based on the current screen, suggest 3-5 testing actions that would help "
                    "explore the application functionality and potentially trigger monitored operations."
                    "{#if additional_guidelines}\n\n{additional_guidelines}{#endif}"
                ),
                "required_variables": ["screen_elements"],
                "max_tokens": 500
            },
            "action_feedback": {
                "system": (
                    "You are an Android testing assistant. Your task is to provide feedback on "
                    "testing actions and their results.\n\n"
                    "{#if previous_action}"
                    "Previous action: {previous_action}\n"
                    "Result: {action_result}\n\n"
                    "{#endif}"
                    "{#if monitored_operations}"
                    "Monitored operations detected: {monitored_operations.summary}\n\n"
                    "{#endif}"
                ),
                "user": (
                    "Analyze the result of the previous testing action and provide feedback "
                    "on what was discovered. Suggest follow-up actions based on the current state."
                    "{#if additional_guidelines}\n\n{additional_guidelines}{#endif}"
                ),
                "max_tokens": 400
            },
            "strategic_guidance": {
                "system": (
                    "You are an Android testing strategy advisor. Your task is to analyze the current "
                    "testing state and provide strategic guidance on how to proceed.\n\n"
                    "Testing progress: {testing_progress}\n"
                    "Covered areas: {covered_areas}\n"
                    "Unexplored areas: {unexplored_areas}\n\n"
                    "{#if monitored_operations}"
                    "Monitored operations detected so far: {monitored_operations.summary}\n\n"
                    "{#endif}"
                ),
                "user": (
                    "Based on the current testing state, provide strategic guidance on how to "
                    "proceed with testing. Consider the following aspects:\n"
                    "1. Areas that should be prioritized for testing\n"
                    "2. Testing approaches that might uncover more monitored operations\n"
                    "3. Suggestions for improving test coverage"
                    "{#if additional_guidelines}\n\n{additional_guidelines}{#endif}"
                ),
                "required_variables": ["testing_progress", "covered_areas", "unexplored_areas"],
                "max_tokens": 600
            },
            "monitored_operations": {
                "system": (
                    "You are a security operations analyzer. Your task is to analyze the monitored "
                    "operations detected in an Android application and provide insights.\n\n"
                    "Detected monitored operations:\n"
                    "{monitored_operations_details}\n\n"
                    "Application context:\n"
                    "{app_context}"
                ),
                "user": (
                    "Analyze the monitored operations detected in this application. Provide insights on:\n"
                    "1. What these operations indicate about the application's functionality\n"
                    "2. Any potential security implications\n"
                    "3. Recommendations for further testing"
                    "{#if additional_guidelines}\n\n{additional_guidelines}{#endif}"
                ),
                "required_variables": ["monitored_operations_details", "app_context"],
                "max_tokens": 700
            }
        }

        # Write default templates to files
        for name, template in default_templates.items():
            template_path = os.path.join(self.template_dir, f"{name}.json")
            try:
                with open(template_path, "w") as f:
                    json.dump(template, f, indent=2)
                self.logger.info(f"Created default template: {name}")
            except Exception as e:
                self.logger.error(f"Error creating default template {name}: {e}")
                self.error_handler.handle_error(
                    e,
                    context={
                        "component": "TemplateRepository",
                        "template_name": name
                    }
                )

    def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a template by name.
        
        Args:
            name: The name of the template.
            
        Returns:
            The template dictionary, or None if not found.
        """
        return self.templates.get(name)

    def get_template_object(self, name: str, role: str) -> Optional[PromptTemplate]:
        """Get a template object by name and role.
        
        Args:
            name: The name of the template.
            role: The role (system, user, assistant).
            
        Returns:
            The template object, or None if not found.
        """
        template_key = f"{name}.{role}"
        return self.template_objects.get(template_key)

    def update_template(self, name: str, template_data: Dict[str, Any]) -> None:
        """Update or create a template.
        
        Args:
            name: The name of the template.
            template_data: The template data to save.
        """
        try:
            # Save the template data
            self.templates[name] = template_data

            # Create template objects for each role if they exist
            for role in ["system", "user", "assistant"]:
                if role in template_data:
                    template_key = f"{name}.{role}"
                    self.template_objects[template_key] = PromptTemplate(
                        template_data[role],
                        template_key,
                        required_variables=template_data.get("required_variables", [])
                    )

            # Write the template to a file
            template_path = os.path.join(self.template_dir, f"{name}.json")
            with open(template_path, "w") as f:
                json.dump(template_data, f, indent=2)

            self.logger.info(f"Updated template: {name}")
        except Exception as e:
            self.logger.error(f"Error updating template {name}: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "TemplateRepository",
                    "template_name": name
                }
            )

    def create_messages(
            self,
            template_name: str,
            variables: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Create a list of messages using the specified template.
        
        Args:
            template_name: The name of the template to use.
            variables: Variables to substitute in the template.
            
        Returns:
            A list of message dictionaries with role and content.
            This format is used for backward compatibility with existing code.
        """
        try:
            template = self.get_template(template_name)

            if not template:
                self.logger.error(f"Template not found: {template_name}")
                return []

            messages = []

            # Create messages for each role in the template
            for role in ["system", "user", "assistant"]:
                if role in template:
                    template_obj = self.get_template_object(template_name, role)

                    if template_obj:
                        content = template_obj.render(variables)
                        messages.append({
                            "role": role,
                            "content": content
                        })

            return messages
        except Exception as e:
            self.logger.error(f"Error creating messages from template {template_name}: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "TemplateRepository",
                    "template_name": template_name
                }
            )
            return []

    def create_llm_messages(
            self,
            template_name: str,
            variables: Dict[str, Any]
    ) -> List["LLMMessage"]:
        """Create a list of LLMMessage objects using the specified template.
        
        Args:
            template_name: The name of the template to use.
            variables: Variables to substitute in the template.
            
        Returns:
            A list of LLMMessage objects.
        """
        from rv_llm.llm.data_structures import LLMMessage, LLMRole, LLMTextContent

        try:
            dict_messages = self.create_messages(template_name, variables)

            if not dict_messages:
                return []

            llm_messages = []
            for msg in dict_messages:
                role_value = msg["role"]
                content_text = msg["content"]

                # Convert role string to LLMRole enum
                role = LLMRole(role_value)

                # Create LLMMessage object
                llm_message = LLMMessage(
                    role=role,
                    content=[LLMTextContent(text=content_text)]
                )
                llm_messages.append(llm_message)

            return llm_messages
        except Exception as e:
            self.logger.error(f"Error creating LLM messages from template {template_name}: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "TemplateRepository",
                    "template_name": template_name
                }
            )
            return []
